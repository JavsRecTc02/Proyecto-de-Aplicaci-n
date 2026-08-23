import math
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt


# ============================================================
# COORDENADA PROMEDIO DEL GPS
# ============================================================

LATITUD = 9.92600040
LONGITUD = -84.00004424


# ============================================================
# CONFIGURACIÓN
# ============================================================

ZOOM = 19

TILE_SIZE = 256

# 3x3 teselas
RADIO_TESSELAS = 1


# ============================================================
# LAT/LON → COORDENADAS DE PÍXEL GLOBAL
# ============================================================

def latlon_a_pixel(latitud, longitud, zoom):

    n = 2 ** zoom

    pixel_x = (
        (longitud + 180.0)
        / 360.0
        * n
        * TILE_SIZE
    )

    lat_rad = math.radians(latitud)

    pixel_y = (
        (
            1.0
            - math.asinh(math.tan(lat_rad))
            / math.pi
        )
        / 2.0
        * n
        * TILE_SIZE
    )

    return pixel_x, pixel_y


# ============================================================
# LAT/LON → TILE
# ============================================================

def latlon_a_tile(latitud, longitud, zoom):

    pixel_x, pixel_y = latlon_a_pixel(
        latitud,
        longitud,
        zoom
    )

    tile_x = int(pixel_x // TILE_SIZE)
    tile_y = int(pixel_y // TILE_SIZE)

    return tile_x, tile_y


# ============================================================
# DESCARGAR TILE
# ============================================================

def obtener_tile(x, y, zoom):

    url = (
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/"
        "World_Imagery/MapServer/"
        f"tile/{zoom}/{y}/{x}"
    )

    print(
        f"Descargando tesela: "
        f"X={x}, Y={y}, Z={zoom}"
    )

    respuesta = requests.get(
        url,
        timeout=30
    )

    respuesta.raise_for_status()

    return Image.open(
        BytesIO(respuesta.content)
    ).convert("RGB")


# ============================================================
# PROGRAMA
# ============================================================

print("Obteniendo imagen satelital...")
print(f"Latitud:  {LATITUD}")
print(f"Longitud: {LONGITUD}")
print(f"Zoom:     {ZOOM}")
print()


# ============================================================
# TESela CENTRAL
# ============================================================

tile_x, tile_y = latlon_a_tile(
    LATITUD,
    LONGITUD,
    ZOOM
)

print(
    f"Tesela central: "
    f"X={tile_x}, Y={tile_y}"
)

print()


# ============================================================
# CREAR MOSAICO
# ============================================================

numero_teselas = (
    2 * RADIO_TESSELAS + 1
)

tamano_mosaico = (
    numero_teselas * TILE_SIZE
)

mosaico = Image.new(
    "RGB",
    (
        tamano_mosaico,
        tamano_mosaico
    )
)


# ============================================================
# DESCARGAR LAS 9 TESELAS
# ============================================================

for dy in range(
    -RADIO_TESSELAS,
    RADIO_TESSELAS + 1
):

    for dx in range(
        -RADIO_TESSELAS,
        RADIO_TESSELAS + 1
    ):

        x = tile_x + dx
        y = tile_y + dy

        tile = obtener_tile(
            x,
            y,
            ZOOM
        )

        posicion_x = (
            (dx + RADIO_TESSELAS)
            * TILE_SIZE
        )

        posicion_y = (
            (dy + RADIO_TESSELAS)
            * TILE_SIZE
        )

        mosaico.paste(
            tile,
            (
                posicion_x,
                posicion_y
            )
        )


# ============================================================
# CALCULAR POSICIÓN DEL GPS DENTRO DEL MOSAICO
# ============================================================

pixel_x_global, pixel_y_global = (
    latlon_a_pixel(
        LATITUD,
        LONGITUD,
        ZOOM
    )
)


# Coordenada del extremo superior izquierdo
# del mosaico

pixel_x_inicio = (
    (tile_x - RADIO_TESSELAS)
    * TILE_SIZE
)

pixel_y_inicio = (
    (tile_y - RADIO_TESSELAS)
    * TILE_SIZE
)


# Posición del GPS dentro de nuestra imagen

pixel_x = (
    pixel_x_global
    - pixel_x_inicio
)

pixel_y = (
    pixel_y_global
    - pixel_y_inicio
)


print()
print(
    f"Posición GPS en imagen:"
)

print(
    f"Pixel X: {pixel_x:.2f}"
)

print(
    f"Pixel Y: {pixel_y:.2f}"
)


# ============================================================
# DIBUJAR MARCADOR
# ============================================================

draw = ImageDraw.Draw(mosaico)

radio = 10

draw.ellipse(
    (
        pixel_x - radio,
        pixel_y - radio,
        pixel_x + radio,
        pixel_y + radio
    ),
    outline="red",
    width=4
)


# Cruz

draw.line(
    (
        pixel_x - 15,
        pixel_y,
        pixel_x + 15,
        pixel_y
    ),
    fill="red",
    width=3
)

draw.line(
    (
        pixel_x,
        pixel_y - 15,
        pixel_x,
        pixel_y + 15
    ),
    fill="red",
    width=3
)


# ============================================================
# GUARDAR
# ============================================================

nombre_archivo = (
    "imagen_satelital_gps.png"
)

mosaico.save(
    nombre_archivo
)

print()
print(
    f"Imagen guardada como: "
    f"{nombre_archivo}"
)


# ============================================================
# MOSTRAR
# ============================================================

plt.figure(
    figsize=(10, 10)
)

plt.imshow(mosaico)

plt.title(
    "Esri World Imagery - "
    "Posición promedio GPS"
)

plt.axis("off")

plt.show()