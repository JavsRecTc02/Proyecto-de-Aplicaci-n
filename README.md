
# SEAC: Sistema de estimación de parámetros geométricos de una calle 

## Descripción

Este proyecto corresponde al desarrollo de un sistema automatizado para la estimación de parámetros físicos y geométricos de una vía, principalmente su **ancho**, utilizando  **geolocalización GPS, imágenes satelitales como método principal y procesamiento de imágenes capturadas mediante una cámara**.

El sistema busca complementar soluciones existentes de medición de velocidad vehicular basadas en modelos de detección como **YOLO**, proporcionando información sobre el entorno físico de la vía que permita mejorar la calibración y precisión de dichas estimaciones.

## La propuesta utiliza una arquitectura en la que la adquisición de datos puede realizarse mediante hardware embebido, mientras que el procesamiento y análisis de la información puede realizarse posteriormente en un sistema externo.

# Arquitectura general

Actualmente, el desarrollo se divide en varias etapas:

```text
┌──────────────────────┐
│      NEO-6M GPS      │
└──────────┬───────────┘
           │
           │ Datos NMEA
           ▼
┌──────────────────────┐
│       Python Rpi4    │
│                      │
│ Validación de datos  │
│ GPS + satélites      │
│ + HDOP               │
└──────────┬───────────┘
           │
           │ 10 mediciones válidas
           ▼
┌──────────────────────┐
│        Python        │
│                      │
│ Análisis estadístico │
│ Promedio             │
│ Dispersión           │
│ Desviación           │
└──────────┬───────────┘
           │
           │ Latitud/Longitud promedio
           ▼
┌──────────────────────┐
│ Imágenes satelitales │
│      Esri World      │
│       Imagery        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Mosaico de teselas   │
│        3 × 3         │
│                      │
│ + posición GPS       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Análisis geométrico  │
│       de la vía      │
└──────────────────────┘
```

La arquitectura final incorporará además una cámara para utilizar información visual de la escena vial, de acuerdo con los objetivos establecidos para el proyecto.

---

# Etapa 1 — Adquisición de datos GPS

## Hardware

Para la adquisición de las coordenadas se utiliza un módulo **NEO-6M GPS**, conectado a la RaspBerry pi 4 mediante comunicación serial.

La conexión utilizada actualmente es:

| Componente   |        Rpi4    |
| ------------ | -------------: |
| NEO-6M TX    |          Pin RX|
| NEO-6M RX    |          Pin TX|
| Baud rate    |           9600 |
| Comunicación | SoftwareSerial |

La Rpi4 se encarga de recibir continuamente las sentencias NMEA generadas por el módulo GPS y procesarlas mediante la biblioteca `pymea2`.

---

# Validación de las mediciones GPS

No todas las mediciones proporcionadas por el GPS se consideran confiables para el sistema.

Antes de almacenar una medición, el programa verifica que estén disponibles:

* Coordenadas GPS válidas.
* Número de satélites válido.
* Valor de HDOP válido.

Posteriormente se aplican criterios mínimos de calidad:

```text
Satélites ≥ 4
HDOP ≤ 2.0
```

Además, las mediciones válidas deben estar separadas por un intervalo mínimo de:

```text
2 segundos
```

Esto evita tomar múltiples muestras prácticamente simultáneas y permite obtener una serie de mediciones distribuidas temporalmente.

---

# Obtención de las 10 mediciones

El sistema establece como objetivo:

```cpp
const int MEDICIONES_OBJETIVO = 10;
```

Por lo tanto, el Arduino continúa recibiendo y evaluando datos hasta obtener **10 mediciones que cumplan todos los criterios de validación**.

Cada medición se transmite por el puerto serial utilizando el siguiente formato:

```text
GPS,indice,latitud,longitud,satelites,HDOP
```

Por ejemplo:

![Imagen satelital](docs/mediciones.jpeg)

Cada registro contiene:

| Campo       | Descripción                       |
| ----------- | --------------------------------- |
| `GPS`       | Identificador del tipo de dato    |
| `indice`    | Número de medición                |
| `latitud`   | Latitud registrada                |
| `longitud`  | Longitud registrada               |
| `satelites` | Satélites utilizados/recibidos    |
| `HDOP`      | Indicador de precisión geométrica |

Cuando se obtienen las 10 mediciones, Arduino transmite:

```text
FIN_MEDICIONES
```

y detiene la adquisición.

---

# Etapa 2 — Procesamiento de los datos GPS

Una vez obtenidas las mediciones GPS, los datos son procesados mediante **Python**.

Esta etapa se encuentra implementada en el módulo:

```text
gps.py
```

El objetivo de esta etapa es validar las mediciones obtenidas y determinar una posición representativa de la ubicación donde se realizó la captura.

En lugar de utilizar directamente una única medición, el sistema procesa el conjunto de mediciones almacenadas en el archivo de entrada.

Cada registro GPS contiene:

```text
GPS,número,latitud,longitud,satélites,HDOP
```

El módulo verifica que las coordenadas sean válidas antes de utilizarlas.

---

# Análisis de las mediciones GPS

A partir de las mediciones válidas se calculan diferentes parámetros que permiten conocer la posición representativa y la dispersión de los datos.

Actualmente se calculan:

* Cantidad de mediciones válidas.
* Latitud promedio.
* Longitud promedio.
* Latitud mínima.
* Latitud máxima.
* Longitud mínima.
* Longitud máxima.
* Desviación estándar de la latitud.
* Desviación estándar de la longitud.
* Rango de latitud expresado en metros.
* Rango de longitud expresado en metros.
* Distancia de cada medición con respecto a la coordenada promedio.
* Distancia promedio con respecto al punto promedio.
* Distancia máxima con respecto al punto promedio.

El archivo de entrada también contiene el número de satélites y el valor HDOP de cada medición. Estos datos son leídos y almacenados por el módulo GPS, aunque actualmente no son utilizados para calcular la coordenada promedio.

---

# Coordenada promedio

A partir de las mediciones válidas se obtiene una coordenada representativa mediante:

```text
Latitud promedio
Longitud promedio
```

El proceso puede representarse de la siguiente manera:

```text
Mediciones GPS
      ↓
Validación
      ↓
Latitudes y longitudes válidas
      ↓
Promedio
      ↓
Coordenada representativa
```

Esta coordenada se utiliza posteriormente como referencia para obtener la imagen satelital correspondiente.

![Imagen tabla](docs/tabla_promedio.png)

---

# Etapa 3 — Obtención de imágenes satelitales

Una vez determinada la coordenada promedio, el sistema utiliza la latitud y longitud para localizar la región correspondiente dentro del sistema de teselas de Esri.

Esta etapa se encuentra implementada en el módulo:

```text
esri.py
```

La fuente utilizada actualmente es:

```text
Esri World Imagery
```

mediante el servicio:

```text
ArcGIS World_Imagery
```

---

# ¿Qué es una tesela?

Los servicios de mapas dividen las imágenes del planeta en pequeñas imágenes cuadradas denominadas **teselas** (*tiles*).

Cada tesela utilizada por el sistema tiene:

```text
256 × 256 píxeles
```

y se identifica mediante tres parámetros:

```text
X → posición horizontal
Y → posición vertical
Z → nivel de zoom
```

El nivel de zoom determina el nivel de detalle de la imagen.

A mayor valor de `zoom`, mayor nivel de detalle y menor área geográfica representada por cada tesela.

Actualmente el valor predeterminado es:

```text
Zoom = 19
```

---

# Conversión de coordenadas GPS

Para determinar qué parte del mapa corresponde a la coordenada GPS promedio, el sistema transforma la posición geográfica utilizando la proyección **Web Mercator**.

El proceso es:

```text
Latitud / Longitud
        ↓
Web Mercator
        ↓
Píxel global
        ↓
Tesela X/Y
```

La función:

```python
latlon_a_pixel_global()
```

convierte la latitud y longitud en una posición dentro de la cuadrícula global de píxeles utilizada por el servicio de mapas.

Posteriormente, a partir de esos valores se determina la tesela que contiene la coordenada GPS.

---

# Generación del mosaico satelital

Una única tesela puede no proporcionar suficiente contexto alrededor de la posición GPS.

Por esta razón, con la configuración predeterminada se utiliza un radio de una tesela alrededor de la tesela central.

Esto produce un mosaico de:

```text
3 × 3 teselas
```

distribuidas de la siguiente manera:

```text
┌───────────┬───────────┬───────────┐
│ X-1,Y-1   │ X,Y-1     │ X+1,Y-1   │
├───────────┼───────────┼───────────┤
│ X-1,Y     │ X,Y       │ X+1,Y     │
├───────────┼───────────┼───────────┤
│ X-1,Y+1   │ X,Y+1     │ X+1,Y+1   │
└───────────┴───────────┴───────────┘
```

Como cada tesela posee:

```text
256 × 256 píxeles
```

el mosaico generado tiene:

```text
768 × 768 píxeles
```

El número de teselas puede modificarse mediante el parámetro:

```text
--radio-teselas
```

---

# Ubicación de la coordenada GPS dentro del mosaico

Además de obtener la imagen satelital, el sistema determina exactamente en qué posición del mosaico se encuentra la coordenada GPS promedio.

El procedimiento es:

```text
Coordenada GPS promedio
          ↓
Píxel global
          ↓
Origen del mosaico
          ↓
Píxel relativo dentro de la imagen
```

Como resultado se obtiene una posición:

```text
(x, y)
```

que representa el punto GPS dentro de la imagen satelital.

Esta posición funciona posteriormente como centro de referencia para el análisis de la vía.

---

# Resolución cartográfica

Para convertir las mediciones realizadas sobre la imagen desde píxeles hacia metros, el sistema calcula la resolución cartográfica local.

La función:

```python
resolucion_metros_por_pixel()
```

calcula aproximadamente cuántos metros representa cada píxel para una latitud y nivel de zoom determinados.

El resultado se expresa como:

```text
metros / píxel
```

Esta relación permite convertir posteriormente las distancias detectadas en la imagen a unidades reales.

---

# Marcador de posición

Para facilitar la comprobación visual, el sistema genera una copia del mosaico satelital con la posición GPS marcada.

El marcador está compuesto por:

* Un círculo.
* Una cruz.
* La posición correspondiente a la coordenada promedio.

La imagen original sin marcador también se conserva, ya que es utilizada durante el procesamiento de imagen para evitar que el marcador interfiera con la detección de bordes.

![Imagen satelital](docs/imagen_sat.png)

---

# Etapa 4 — Estimación del ancho de la calle

La estimación del ancho de la vía se encuentra implementada en el módulo:

```text
estimacion_ancho.py
```

Esta etapa utiliza la imagen satelital, la posición GPS y la resolución cartográfica obtenidas anteriormente.

El proceso general es:

```text
Imagen satelital
        ↓
Región de interés alrededor del GPS
        ↓
Máscara aproximada de asfalto
        ↓
Detección de bordes
        ↓
Estimación de orientación de la calle
        ↓
Secciones transversales
        ↓
Medición entre bordes
        ↓
Conversión de píxeles a metros
        ↓
Filtrado de mediciones
        ↓
Ancho estimado
```

---

# Región de interés

El sistema utiliza una región circular alrededor del punto GPS para limitar la zona de análisis.

El tamaño de esta región se define mediante:

```text
--roi-metros
```

Por ejemplo:

```bash
--roi-metros 20
```

establece una región de interés de aproximadamente 20 metros alrededor de la posición GPS.

---

# Máscara aproximada de asfalto

Antes de detectar los bordes se genera una máscara que intenta conservar las superficies visualmente compatibles con la vía.

Para esto se analizan características relacionadas con:

* Saturación.
* Luminosidad.
* Cromaticidad.
* Textura local.

También se utilizan operaciones morfológicas para reducir pequeñas discontinuidades.

La máscara no determina por sí sola qué región corresponde a una calle, sino que ayuda a reducir elementos como vegetación o superficies con características poco compatibles con el asfalto.

---

# Detección de bordes

Sobre la imagen procesada se utiliza:

```text
Canny Edge Detection
```

para detectar cambios significativos de intensidad que puedan corresponder a los límites de la vía.

Los umbrales utilizados por Canny pueden indicarse manualmente mediante:

```text
--canny-bajo
--canny-alto
```

Si no se proporcionan, el sistema determina automáticamente valores a partir de las características de intensidad de la imagen.

---

# Estimación de la orientación de la calle

Una vez detectados los bordes, se utiliza:

```text
HoughLinesP
```

para identificar segmentos de línea presentes en la imagen.

Los segmentos cercanos a la posición GPS son analizados para determinar la orientación predominante de la vía.

El proceso puede representarse como:

```text
Segmentos detectados
        ↓
Orientaciones
        ↓
Histograma angular
        ↓
Orientación dominante
```

Esta orientación representa aproximadamente la dirección longitudinal de la calle.

---

# Secciones transversales

Una vez determinada la orientación de la calle, se obtiene una dirección perpendicular a esta.

Sobre esta dirección se realizan múltiples mediciones transversales.

Actualmente se utilizan:

```text
13 secciones
```

distribuidas entre aproximadamente:

```text
-6 m y +6 m
```

con respecto al punto GPS.

El uso de múltiples secciones permite disminuir la dependencia de una única medición que podría verse afectada por:

* Vehículos.
* Sombras.
* Vegetación.
* Imperfecciones de la imagen.
* Bordes que no correspondan a la calle.

---

# Medición del ancho de la calle

En cada sección transversal se buscan dos bordes que puedan representar los límites opuestos de la vía.

La distancia detectada inicialmente se encuentra en píxeles.

Esta distancia se convierte a metros mediante la resolución cartográfica calculada anteriormente:

```text
Distancia entre bordes en píxeles
                ×
         Metros por píxel
                ↓
          Ancho en metros
```

También se verifica que la medición se encuentre dentro del intervalo de ancho permitido.

Por ejemplo:

```bash
--ancho-minimo-m 3
--ancho-maximo-m 10
```

---

# Filtrado de mediciones

No todas las mediciones transversales detectadas son utilizadas para obtener el resultado final.

El sistema busca grupos de mediciones cuyos valores de ancho sean similares y descarta aquellas que sean inconsistentes.

Para generar una estimación final se requieren al menos:

```text
3 secciones transversales consistentes
```

Una vez seleccionadas las mediciones válidas, el ancho final se obtiene mediante:

```text
Mediana de los anchos válidos
```

El uso de la mediana permite reducir la influencia de valores atípicos.

---

# Nivel de confianza

Además del ancho estimado, el sistema calcula un valor de confianza asociado al resultado.

Este valor considera principalmente:

* La dispersión entre las mediciones válidas.
* La cantidad de secciones válidas.
* La confianza asociada a la orientación detectada.

Actualmente el resultado puede clasificarse como:

```text
Alta
Media
Baja
Insuficiente
```

---

# Resultados generados

Al ejecutar el pipeline se genera la carpeta:

```text
resultados_seac/
```

que contiene diferentes etapas del procesamiento:

```text
01_imagen_satelital.png
02_imagen_con_gps.png
03_contraste_grises.png
04_mascara_asfalto.png
05_bordes_canny.png
06_secciones_transversales.png
reporte.json
```

### `01_imagen_satelital.png`

Mosaico original obtenido desde Esri.

### `02_imagen_con_gps.png`

Mosaico con la posición GPS promedio marcada.

### `03_contraste_grises.png`

Imagen en escala de grises utilizada durante el procesamiento.

### `04_mascara_asfalto.png`

Máscara aproximada de las regiones compatibles con la superficie de la vía.

### `05_bordes_canny.png`

Bordes detectados mediante Canny.

### `06_secciones_transversales.png`

Resultado visual en el que se muestran los segmentos detectados, la orientación estimada y las secciones utilizadas para calcular el ancho.

---

# Arquitectura modular

El software se encuentra dividido en módulos independientes con responsabilidades específicas.

```text
mediciones_gps.txt
        │
        ▼
┌──────────────────┐
│      gps.py      │
│ Procesamiento GPS│
└────────┬─────────┘
         │
         │ Coordenada promedio
         ▼
┌──────────────────┐
│     esri.py      │
│ Imagen satelital │
└────────┬─────────┘
         │
         │ Mosaico + resolución
         ▼
┌────────────────────────┐
│ estimacion_ancho.py    │
│ Procesamiento de imagen│
│ y estimación del ancho │
└───────────┬────────────┘
            │
            ▼
       Ancho estimado
```

El archivo:

```text
seac_pipeline.py
```

actúa como coordinador del flujo general y utiliza las interfaces proporcionadas por cada módulo.

La estructura actual del software es:

```text
SEAC/
│
├── seac_pipeline.py
├── gps.py
├── esri.py
├── estimacion_ancho.py
├── mediciones_gps.txt
└── resultados_seac/
```

La separación en módulos permite modificar o sustituir un componente sin alterar la lógica interna de los demás, siempre que se mantenga la interfaz definida entre ellos.

Por ejemplo, el proveedor de imágenes satelitales podría ser sustituido por otro servicio manteniendo una interfaz equivalente para obtener el mosaico y su información asociada.

---

# Ejecución

El pipeline completo puede ejecutarse mediante:

```bash
py seac_pipeline.py mediciones_gps.txt
```

También es posible modificar diferentes parámetros del procesamiento.

Por ejemplo:

```bash
py seac_pipeline.py mediciones_gps.txt --roi-metros 20 --ancho-maximo-m 10 --mostrar
```

En este caso:

```text
mediciones_gps.txt
```

corresponde al archivo que contiene las mediciones obtenidas mediante el GPS.

```text
--roi-metros 20
```

establece una región de interés de 20 metros alrededor de la posición GPS.

```text
--ancho-maximo-m 10
```

establece en 10 metros el ancho máximo considerado durante la búsqueda de los límites de la vía.

```text
--mostrar
```

permite mostrar visualmente el resultado final del procesamiento.

---

# Tecnologías utilizadas

## Hardware

* Módulo GPS NEO-6M.
* Raspberry Pi 4.
* Cámara compatible CSI o USB para futuras etapas.

## Software

### Python

* Python 3.
* NumPy.
* OpenCV.
* Pillow.
* `urllib`.
* `math`.
* `argparse`.
* `json`.

### Procesamiento de imágenes

* Conversión de espacios de color.
* Filtrado bilateral.
* CLAHE.
* Operaciones morfológicas.
* Canny Edge Detection.
* HoughLinesP.

### Datos geoespaciales

* Coordenadas GPS.
* Latitud.
* Longitud.
* HDOP.
* Número de satélites.
* Web Mercator.
* Teselas (*tiles*).
* Resolución cartográfica en metros por píxel.
* Imágenes satelitales.
* Esri World Imagery.
* ArcGIS REST API.

---

# Consideraciones actuales

La resolución calculada por el sistema corresponde a la escala cartográfica de Web Mercator para la latitud y el nivel de zoom utilizados.

Esta resolución no garantiza por sí sola la resolución espacial nativa ni la precisión posicional de la fotografía satelital.

Por esta razón, las estimaciones de ancho obtenidas deberán ser evaluadas posteriormente mediante su comparación con mediciones reales o valores de referencia.

---

# Documentación de Esri

Consultar el [tutorial de múltiples capas](https://developers.arcgis.com/openlayers/maps/raster-tile-basemaps/display-multiple-basemap-layers/) para acceder a documentación relacionada con los mapas base de Esri.
---
