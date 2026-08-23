import math
import numpy as np
import matplotlib.pyplot as plt


ARCHIVO = "mediciones_gps.txt"


def leer_mediciones(archivo):
    """
    Lee las mediciones GPS desde un archivo TXT.

    Formato:
    GPS,numero,latitud,longitud,satelites,hdop
    """

    mediciones = []

    with open(archivo, "r", encoding="utf-8") as f:

        for linea in f:

            linea = linea.strip()

            # Ignorar líneas vacías
            if not linea:
                continue

            # Final de las mediciones
            if linea == "FIN_MEDICIONES":
                break

            partes = linea.split(",")

            if partes[0] != "GPS":
                continue

            medicion = {
                "numero": int(partes[1]),
                "latitud": float(partes[2]),
                "longitud": float(partes[3]),
                "satelites": int(partes[4]),
                "hdop": float(partes[5])
            }

            mediciones.append(medicion)

    return mediciones


def distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos coordenadas GPS
    utilizando la fórmula de Haversine.

    Resultado en metros.
    """

    R = 6371000.0  # Radio aproximado de la Tierra en metros

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def analizar_mediciones(mediciones):

    latitudes = np.array(
        [m["latitud"] for m in mediciones]
    )

    longitudes = np.array(
        [m["longitud"] for m in mediciones]
    )

    # ==========================
    # PROMEDIOS
    # ==========================

    latitud_promedio = np.mean(latitudes)
    longitud_promedio = np.mean(longitudes)

    # ==========================
    # MÍNIMOS Y MÁXIMOS
    # ==========================

    latitud_minima = np.min(latitudes)
    latitud_maxima = np.max(latitudes)

    longitud_minima = np.min(longitudes)
    longitud_maxima = np.max(longitudes)

    # ==========================
    # DESVIACIÓN ESTÁNDAR
    # ==========================

    desviacion_latitud = np.std(
        latitudes,
        ddof=1
    )

    desviacion_longitud = np.std(
        longitudes,
        ddof=1
    )

    # ==========================
    # CONVERSIÓN APROXIMADA A METROS
    # ==========================

    latitud_rad = math.radians(latitud_promedio)

    metros_por_grado_latitud = (
        111132.92
        - 559.82 * math.cos(2 * latitud_rad)
        + 1.175 * math.cos(4 * latitud_rad)
    )

    metros_por_grado_longitud = (
        111412.84 * math.cos(latitud_rad)
        - 93.5 * math.cos(3 * latitud_rad)
    )

    rango_latitud_m = (
        latitud_maxima - latitud_minima
    ) * metros_por_grado_latitud

    rango_longitud_m = (
        longitud_maxima - longitud_minima
    ) * metros_por_grado_longitud

    # ==========================
    # DISTANCIA DE CADA PUNTO
    # AL PROMEDIO
    # ==========================

    distancias = []

    for m in mediciones:

        distancia = distancia_haversine(
            latitud_promedio,
            longitud_promedio,
            m["latitud"],
            m["longitud"]
        )

        distancias.append(distancia)

    distancias = np.array(distancias)

    distancia_maxima = np.max(distancias)
    distancia_promedio = np.mean(distancias)

    # ==========================
    # RESULTADOS
    # ==========================

    resultados = {
        "latitud_promedio": latitud_promedio,
        "longitud_promedio": longitud_promedio,

        "latitud_minima": latitud_minima,
        "latitud_maxima": latitud_maxima,

        "longitud_minima": longitud_minima,
        "longitud_maxima": longitud_maxima,

        "desviacion_latitud": desviacion_latitud,
        "desviacion_longitud": desviacion_longitud,

        "rango_latitud_m": rango_latitud_m,
        "rango_longitud_m": rango_longitud_m,

        "distancias": distancias,
        "distancia_maxima": distancia_maxima,
        "distancia_promedio": distancia_promedio
    }

    return resultados


def mostrar_resultados(mediciones, resultados):

    print("\n")
    print("=" * 55)
    print("             ANÁLISIS DE MEDICIONES GPS")
    print("=" * 55)

    print("\n--- POSICIÓN PROMEDIO ---")

    print(
        f"Latitud promedio:       "
        f"{resultados['latitud_promedio']:.8f}"
    )

    print(
        f"Longitud promedio:      "
        f"{resultados['longitud_promedio']:.8f}"
    )

    print("\n--- DISPERSIÓN ---")

    print(
        f"Latitud mínima:          "
        f"{resultados['latitud_minima']:.8f}"
    )

    print(
        f"Latitud máxima:          "
        f"{resultados['latitud_maxima']:.8f}"
    )

    print(
        f"Longitud mínima:         "
        f"{resultados['longitud_minima']:.8f}"
    )

    print(
        f"Longitud máxima:         "
        f"{resultados['longitud_maxima']:.8f}"
    )

    print(
        f"Rango latitudinal:       "
        f"{resultados['rango_latitud_m']:.3f} m"
    )

    print(
        f"Rango longitudinal:      "
        f"{resultados['rango_longitud_m']:.3f} m"
    )

    print("\n--- ESTADÍSTICA ---")

    print(
        f"Desviación estándar latitud:  "
        f"{resultados['desviacion_latitud']:.8f}°"
    )

    print(
        f"Desviación estándar longitud: "
        f"{resultados['desviacion_longitud']:.8f}°"
    )

    print("\n--- DISTANCIA RESPECTO AL PROMEDIO ---")

    for i, distancia in enumerate(
        resultados["distancias"], start=1
    ):

        print(
            f"Medición {i:2d}: "
            f"{distancia:.3f} m"
        )

    print(
        f"\nDistancia promedio al centro: "
        f"{resultados['distancia_promedio']:.3f} m"
    )

    print(
        f"Distancia máxima al centro:    "
        f"{resultados['distancia_maxima']:.3f} m"
    )

    print("\n" + "=" * 55)


def graficar_mediciones(mediciones, resultados):

    latitudes = np.array(
        [m["latitud"] for m in mediciones]
    )

    longitudes = np.array(
        [m["longitud"] for m in mediciones]
    )

    lat_promedio = resultados["latitud_promedio"]
    lon_promedio = resultados["longitud_promedio"]

    plt.figure(figsize=(8, 6))

    plt.scatter(
        longitudes,
        latitudes,
        label="Mediciones GPS"
    )

    plt.scatter(
        lon_promedio,
        lat_promedio,
        marker="x",
        s=100,
        label="Posición promedio"
    )

    # Numerar las mediciones
    for i, m in enumerate(mediciones, start=1):

        plt.annotate(
            str(i),
            (
                m["longitud"],
                m["latitud"]
            )
        )

    plt.xlabel("Longitud")
    plt.ylabel("Latitud")

    plt.title(
        "Dispersión de las mediciones GPS"
    )

    plt.legend()
    plt.grid(True)

    plt.show()


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

mediciones = leer_mediciones(ARCHIVO)

if len(mediciones) == 0:

    print("No se encontraron mediciones GPS.")

else:

    print(
        f"Se encontraron "
        f"{len(mediciones)} mediciones."
    )

    resultados = analizar_mediciones(
        mediciones
    )

    mostrar_resultados(
        mediciones,
        resultados
    )

    graficar_mediciones(
        mediciones,
        resultados
    )