"""Estimación del ancho de la calle para SEAC.

Este módulo contiene el procesamiento de imagen utilizado para crear
la máscara de asfalto, detectar bordes, estimar la orientación de la
vía y medir secciones transversales consistentes.
"""

from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from PIL import Image

__all__ = ["detectar_bordes_calle"]

def diferencia_angulos(angulo_1: float, angulo_2: float) -> float:
    """Diferencia minima entre orientaciones de linea, en radianes."""
    diferencia = abs(angulo_1 - angulo_2) % math.pi
    return min(diferencia, math.pi - diferencia)


def distancia_punto_segmento(
    punto: tuple[float, float], puntos_linea: tuple[int, int, int, int]
) -> float:
    """Distancia euclidiana entre un punto y un segmento finito."""
    x_1, y_1, x_2, y_2 = puntos_linea
    inicio = np.array([x_1, y_1], dtype=float)
    vector = np.array([x_2 - x_1, y_2 - y_1], dtype=float)
    longitud_cuadrada = float(np.dot(vector, vector))
    if longitud_cuadrada == 0.0:
        return float(np.linalg.norm(np.asarray(punto) - inicio))
    t = float(np.dot(np.asarray(punto) - inicio, vector) / longitud_cuadrada)
    t = min(1.0, max(0.0, t))
    return float(np.linalg.norm(np.asarray(punto) - (inicio + t * vector)))


def datos_linea(linea: np.ndarray, centro: tuple[float, float]) -> dict[str, Any]:
    """Obtiene geometria util de un segmento producido por HoughLinesP."""
    x_1, y_1, x_2, y_2 = (float(valor) for valor in linea)
    dx = x_2 - x_1
    dy = y_2 - y_1
    longitud = math.hypot(dx, dy)
    puntos = (int(x_1), int(y_1), int(x_2), int(y_2))
    return {
        "puntos": puntos,
        "longitud_px": longitud,
        "angulo": math.atan2(dy, dx) % math.pi,
        "distancia_segmento_centro_px": distancia_punto_segmento(centro, puntos),
    }


def crear_mascara_asfalto(
    bgr: np.ndarray,
    mascara_roi: np.ndarray,
    saturacion_maxima: int,
    textura_maxima: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Genera una mascara amplia de superficies compatibles con asfalto.

    La mascara solo reduce vegetacion y superficies muy coloridas; no decide
    por si sola que una region sea una calle.
    """
    filtrada = cv2.bilateralFilter(bgr, d=9, sigmaColor=50, sigmaSpace=50)
    hsv = cv2.cvtColor(filtrada, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(filtrada, cv2.COLOR_BGR2LAB)
    gris = cv2.cvtColor(filtrada, cv2.COLOR_BGR2GRAY)

    gris_float = gris.astype(np.float32)
    media = cv2.blur(gris_float, (9, 9))
    varianza_local = cv2.blur(gris_float**2, (9, 9)) - media**2
    cromaticidad = np.sqrt(
        (lab[:, :, 1].astype(float) - 128.0) ** 2
        + (lab[:, :, 2].astype(float) - 128.0) ** 2
    )

    mascara = (
        (hsv[:, :, 1] <= saturacion_maxima)
        & (hsv[:, :, 2] >= 35)
        & (hsv[:, :, 2] <= 210)
        & (cromaticidad <= 45.0)
        & (varianza_local <= textura_maxima)
        & (mascara_roi > 0)
    ).astype(np.uint8) * 255

    cierre = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    apertura = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, cierre)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, apertura)
    return filtrada, gris, mascara


def estimar_orientacion_calle(
    lineas: list[dict[str, Any]],
    metros_por_pixel: float,
    roi_metros: float,
    tolerancia_angulo_grados: float,
) -> tuple[float, float] | None:
    """Estima la direccion dominante cerca del GPS mediante un histograma."""
    candidatas = [
        linea
        for linea in lineas
        if linea["distancia_segmento_centro_px"] * metros_por_pixel
        <= 0.75 * roi_metros
    ]
    if not candidatas:
        return None

    tamano_bin = 5.0
    histograma = np.zeros(int(180 / tamano_bin), dtype=float)
    pesos = []
    for linea in candidatas:
        distancia_m = linea["distancia_segmento_centro_px"] * metros_por_pixel
        longitud_m = linea["longitud_px"] * metros_por_pixel
        peso = longitud_m / (1.0 + distancia_m / 3.0)
        indice = int(math.degrees(linea["angulo"]) // tamano_bin) % len(histograma)
        histograma[indice] += peso
        pesos.append(peso)

    indice_dominante = int(np.argmax(histograma))
    angulo_base = math.radians(indice_dominante * tamano_bin + tamano_bin / 2.0)
    tolerancia = math.radians(tolerancia_angulo_grados)
    cercanas = [
        linea
        for linea in candidatas
        if diferencia_angulos(linea["angulo"], angulo_base) <= tolerancia
    ]
    if not cercanas:
        return None

    suma_coseno = sum(
        linea["longitud_px"] * math.cos(2.0 * linea["angulo"])
        for linea in cercanas
    )
    suma_seno = sum(
        linea["longitud_px"] * math.sin(2.0 * linea["angulo"])
        for linea in cercanas
    )
    angulo = (0.5 * math.atan2(suma_seno, suma_coseno)) % math.pi
    confianza = float(histograma[indice_dominante] / max(sum(pesos), 1e-9))
    return angulo, confianza


def valor_vecindad(imagen: np.ndarray, punto: np.ndarray) -> int:
    """Devuelve el maximo de una vecindad 3x3 o cero fuera de la imagen."""
    x, y = np.rint(punto).astype(int)
    alto, ancho = imagen.shape[:2]
    if not (1 <= x < ancho - 1 and 1 <= y < alto - 1):
        return 0
    return int(np.max(imagen[y - 1 : y + 2, x - 1 : x + 2]))


def agrupar_posiciones(
    posiciones: list[float], distancia_maxima: float = 2.0
) -> list[float]:
    """Agrupa pixeles consecutivos que representan un mismo borde."""
    if not posiciones:
        return []
    grupos = [[posiciones[0]]]
    for posicion in posiciones[1:]:
        if posicion - grupos[-1][-1] <= distancia_maxima:
            grupos[-1].append(posicion)
        else:
            grupos.append([posicion])
    return [float(np.median(grupo)) for grupo in grupos]


def soporte_borde(
    bordes: np.ndarray,
    punto: np.ndarray,
    direccion: np.ndarray,
    metros_por_pixel: float,
) -> float:
    """Mide cuanto continua un borde en la direccion de la carretera."""
    alcance_px = max(3, int(round(4.0 / metros_por_pixel)))
    desplazamientos = range(-alcance_px, alcance_px + 1, 2)
    valores = [
        valor_vecindad(bordes, punto + desplazamiento * direccion) > 0
        for desplazamiento in desplazamientos
    ]
    return float(np.mean(valores)) if valores else 0.0


def medir_seccion_transversal(
    centro_seccion: np.ndarray,
    direccion: np.ndarray,
    normal: np.ndarray,
    bordes: np.ndarray,
    mascara_asfalto: np.ndarray,
    metros_por_pixel: float,
    ancho_minimo_m: float,
    ancho_maximo_m: float,
    desplazamiento_centro_maximo_m: float,
) -> dict[str, Any] | None:
    """Selecciona los dos bordes mas coherentes de una seccion transversal."""
    alcance_px = int(math.ceil(ancho_maximo_m / metros_por_pixel))
    posiciones = [
        float(t)
        for t in range(-alcance_px, alcance_px + 1)
        if valor_vecindad(bordes, centro_seccion + t * normal) > 0
    ]
    posiciones = agrupar_posiciones(posiciones)
    if len(posiciones) < 2:
        return None

    mejor = None
    mejor_puntaje = -math.inf
    margen_px = max(2, int(round(1.5 / metros_por_pixel)))
    for indice, borde_1 in enumerate(posiciones):
        for borde_2 in posiciones[indice + 1 :]:
            ancho_m = (borde_2 - borde_1) * metros_por_pixel
            if not ancho_minimo_m <= ancho_m <= ancho_maximo_m:
                continue

            desplazamiento_m = abs((borde_1 + borde_2) / 2.0) * metros_por_pixel
            if desplazamiento_m > desplazamiento_centro_maximo_m:
                continue

            punto_1 = centro_seccion + borde_1 * normal
            punto_2 = centro_seccion + borde_2 * normal
            soporte_1 = soporte_borde(bordes, punto_1, direccion, metros_por_pixel)
            soporte_2 = soporte_borde(bordes, punto_2, direccion, metros_por_pixel)

            interior = [
                valor_vecindad(mascara_asfalto, centro_seccion + t * normal) > 0
                for t in range(
                    int(math.ceil(borde_1 + 2)),
                    int(math.floor(borde_2 - 2)) + 1,
                )
            ]
            posiciones_exteriores = list(
                range(round(borde_1) - margen_px, round(borde_1) - 1)
            ) + list(range(round(borde_2) + 2, round(borde_2) + margen_px + 1))
            exterior = [
                valor_vecindad(mascara_asfalto, centro_seccion + t * normal) > 0
                for t in posiciones_exteriores
            ]
            proporcion_interior = float(np.mean(interior)) if interior else 0.0
            proporcion_exterior = float(np.mean(exterior)) if exterior else 1.0
            contraste_mascara = proporcion_interior - proporcion_exterior

            puntaje = (
                3.0 * (soporte_1 + soporte_2)
                + 2.0 * contraste_mascara
                + proporcion_interior
                - 0.35 * desplazamiento_m
            )
            if puntaje > mejor_puntaje:
                mejor_puntaje = puntaje
                mejor = {
                    "ancho_m": ancho_m,
                    "borde_1": punto_1,
                    "borde_2": punto_2,
                    "centro": centro_seccion,
                    "soporte_promedio": (soporte_1 + soporte_2) / 2.0,
                    "contraste_mascara": contraste_mascara,
                    "calidad": (
                        (soporte_1 + soporte_2) / 2.0
                        + 0.5 * max(0.0, contraste_mascara)
                    ),
                }
    return mejor


def filtrar_mediciones_consistentes(
    mediciones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Selecciona el grupo mas numeroso de anchos similares entre si."""
    if len(mediciones) < 3:
        return []
    ordenadas = sorted(mediciones, key=lambda medicion: medicion["ancho_m"])
    tolerancia_m = 1.5
    mejor_grupo: list[dict[str, Any]] = []
    mejor_criterio = (-1, -math.inf, -math.inf)
    for inicio in range(len(ordenadas)):
        grupo = []
        for medicion in ordenadas[inicio:]:
            if medicion["ancho_m"] - ordenadas[inicio]["ancho_m"] > tolerancia_m:
                break
            grupo.append(medicion)
        anchos = [medicion["ancho_m"] for medicion in grupo]
        criterio = (
            len(grupo),
            sum(medicion["calidad"] for medicion in grupo),
            -float(np.std(anchos)),
        )
        if criterio > mejor_criterio:
            mejor_criterio = criterio
            mejor_grupo = grupo
    return mejor_grupo if len(mejor_grupo) >= 3 else []


def detectar_bordes_calle(
    mosaico: Image.Image,
    posicion_gps: tuple[float, float],
    metros_por_pixel: float,
    roi_metros: float,
    canny_bajo: int | None,
    canny_alto: int | None,
    longitud_minima_m: float,
    ancho_minimo_m: float,
    ancho_maximo_m: float,
    tolerancia_angulo_grados: float,
    saturacion_maxima: int,
    textura_maxima: float,
) -> dict[str, Any]:
    """Estima el ancho a partir de varias secciones transversales."""
    bgr = cv2.cvtColor(np.asarray(mosaico), cv2.COLOR_RGB2BGR)
    centro = (int(round(posicion_gps[0])), int(round(posicion_gps[1])))
    radio_roi_px = max(10, int(round(roi_metros / metros_por_pixel)))
    mascara_roi = np.zeros(bgr.shape[:2], dtype=np.uint8)
    cv2.circle(mascara_roi, centro, radio_roi_px, 255, thickness=-1)

    filtrada, gris, mascara_asfalto = crear_mascara_asfalto(
        bgr, mascara_roi, saturacion_maxima, textura_maxima
    )
    contraste = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gris)
    valores = contraste[mascara_asfalto > 0]
    if not valores.size:
        valores = contraste[mascara_roi > 0]
    mediana = float(np.median(valores)) if valores.size else 128.0
    if canny_bajo is None:
        canny_bajo = max(0, int(0.67 * mediana))
    if canny_alto is None:
        canny_alto = min(255, int(1.33 * mediana))
    if canny_alto <= canny_bajo:
        canny_alto = min(255, canny_bajo + 1)

    bordes = cv2.Canny(
        contraste, canny_bajo, canny_alto, apertureSize=3, L2gradient=True
    )
    mascara_dilatada = cv2.dilate(
        mascara_asfalto, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    )
    bordes = cv2.bitwise_and(bordes, mascara_dilatada)
    bordes = cv2.bitwise_and(bordes, mascara_roi)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bordes_unidos = cv2.morphologyEx(bordes, cv2.MORPH_CLOSE, kernel)

    longitud_minima_px = max(8, int(round(longitud_minima_m / metros_por_pixel)))
    lineas_hough = cv2.HoughLinesP(
        bordes_unidos,
        rho=1,
        theta=np.pi / 180.0,
        threshold=20,
        minLineLength=longitud_minima_px,
        maxLineGap=max(3, int(round(3.0 / metros_por_pixel))),
    )
    lineas: list[dict[str, Any]] = []
    if lineas_hough is not None:
        for linea in np.asarray(lineas_hough).reshape(-1, 4):
            if not np.array_equal(linea[:2], linea[2:]):
                lineas.append(datos_linea(linea, posicion_gps))

    orientacion = estimar_orientacion_calle(
        lineas, metros_por_pixel, roi_metros, tolerancia_angulo_grados
    )
    resultado_visual = filtrada.copy()
    for linea in lineas:
        x_1, y_1, x_2, y_2 = linea["puntos"]
        cv2.line(resultado_visual, (x_1, y_1), (x_2, y_2), (0, 140, 255), 1)
    cv2.circle(resultado_visual, centro, radio_roi_px, (255, 200, 0), 2)
    cv2.drawMarker(
        resultado_visual, centro, (255, 0, 0), cv2.MARKER_CROSS, 24, 2
    )

    mediciones: list[dict[str, Any]] = []
    mediciones_validas: list[dict[str, Any]] = []
    angulo_grados = None
    confianza_orientacion = 0.0
    if orientacion is not None:
        angulo, confianza_orientacion = orientacion
        angulo_grados = math.degrees(angulo)
        direccion = np.array([math.cos(angulo), math.sin(angulo)])
        normal = np.array([-math.sin(angulo), math.cos(angulo)])
        centro_array = np.asarray(posicion_gps, dtype=float)

        # Trece cortes, separados 1 m, permiten descartar autos y sombras
        # sin depender de una unica pareja de bordes.
        for desplazamiento_m in np.linspace(-6.0, 6.0, 13):
            centro_seccion = centro_array + direccion * (
                desplazamiento_m / metros_por_pixel
            )
            medicion = medir_seccion_transversal(
                centro_seccion,
                direccion,
                normal,
                bordes_unidos,
                mascara_asfalto,
                metros_por_pixel,
                ancho_minimo_m,
                ancho_maximo_m,
                min(5.0, ancho_maximo_m / 2.0),
            )
            if medicion is not None:
                medicion["desplazamiento_m"] = float(desplazamiento_m)
                mediciones.append(medicion)

        mediciones_validas = filtrar_mediciones_consistentes(mediciones)
        largo_flecha = int(round(8.0 / metros_por_pixel))
        inicio = tuple(np.rint(centro_array - direccion * largo_flecha).astype(int))
        fin = tuple(np.rint(centro_array + direccion * largo_flecha).astype(int))
        cv2.arrowedLine(resultado_visual, inicio, fin, (255, 0, 255), 2)

        ids_validos = {id(medicion) for medicion in mediciones_validas}
        for medicion in mediciones:
            es_valida = id(medicion) in ids_validos
            color = (0, 255, 0) if es_valida else (255, 255, 0)
            punto_1 = tuple(np.rint(medicion["borde_1"]).astype(int))
            punto_2 = tuple(np.rint(medicion["borde_2"]).astype(int))
            cv2.line(resultado_visual, punto_1, punto_2, color, 3 if es_valida else 1)

    ancho_estimado_m = None
    confianza = 0.0
    if len(mediciones_validas) >= 3:
        anchos = [medicion["ancho_m"] for medicion in mediciones_validas]
        ancho_estimado_m = float(np.median(anchos))
        dispersion = float(np.std(anchos))
        consistencia = max(0.0, 1.0 - dispersion / max(ancho_estimado_m, 1e-9))
        cobertura = min(1.0, len(mediciones_validas) / 5.0)
        confianza = float(consistencia * cobertura * confianza_orientacion)
        if confianza >= 0.55:
            nivel_confianza = "alta"
        elif confianza >= 0.30:
            nivel_confianza = "media"
        else:
            nivel_confianza = "baja"
        texto = (
            f"Ancho: {ancho_estimado_m:.2f} m | confianza {nivel_confianza}"
        )
        color_texto = (0, 255, 0)
    else:
        nivel_confianza = "insuficiente"
        texto = "No hay 3 secciones transversales consistentes"
        color_texto = (0, 0, 255)
    cv2.putText(
        resultado_visual,
        texto,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color_texto,
        2,
        cv2.LINE_AA,
    )

    resultado = {
        "gris_contraste": contraste,
        "mascara_asfalto": mascara_asfalto,
        "bordes_canny": bordes_unidos,
        "resultado_visual": resultado_visual,
        "cantidad_lineas": len(lineas),
        "angulo_calle_grados": angulo_grados,
        "confianza_orientacion": confianza_orientacion,
        "cantidad_secciones_candidatas": len(mediciones),
        "cantidad_secciones_validas": len(mediciones_validas),
        "anchos_candidatos_m": [float(m["ancho_m"]) for m in mediciones],
        "anchos_validos_m": [float(m["ancho_m"]) for m in mediciones_validas],
        "ancho_estimado_m": ancho_estimado_m,
        "confianza": confianza,
        "nivel_confianza": nivel_confianza,
        "canny_bajo_usado": canny_bajo,
        "canny_alto_usado": canny_alto,
        "radio_roi_px": radio_roi_px,
    }
    return resultado
