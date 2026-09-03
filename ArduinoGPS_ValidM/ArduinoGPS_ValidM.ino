#include <SoftwareSerial.h>
#include <TinyGPS++.h>

SoftwareSerial gps(4, 3);  // RX, TX
TinyGPSPlus gpsData;

// Configuración
const int MEDICIONES_OBJETIVO = 10;
const unsigned long INTERVALO_MEDICION = 2000; // 2 segundos

int medicionesValidas = 0;
unsigned long ultimaMedicion = 0;

void setup() {
  Serial.begin(9600);
  gps.begin(9600);

  Serial.println("Iniciando NEO-6M...");
  Serial.println("Esperando mediciones validas...");
}

void loop() {

  // Leer continuamente los datos del GPS
  while (gps.available()) {

    char c = gps.read();

    // Procesar el carácter recibido
    if (gpsData.encode(c)) {

      // Verificar si se actualizó la posición
      if (gpsData.location.isUpdated()) {

        // Verificar que tenemos los datos necesarios
        if (gpsData.location.isValid() &&
            gpsData.satellites.isValid() &&
            gpsData.hdop.isValid()) {

          int satelites = gpsData.satellites.value();
          double hdop = gpsData.hdop.hdop();

          // Verificar criterios de calidad
          if (satelites >= 4 && hdop <= 2.0) {

            // Verificar intervalo de 2 segundos
            unsigned long tiempoActual = millis();

            if (tiempoActual - ultimaMedicion >= INTERVALO_MEDICION) {

              medicionesValidas++;
              ultimaMedicion = tiempoActual;

              // Enviar medición
              Serial.print("GPS,");
              Serial.print(medicionesValidas);
              Serial.print(",");
              Serial.print(gpsData.location.lat(), 8);
              Serial.print(",");
              Serial.print(gpsData.location.lng(), 8);
              Serial.print(",");
              Serial.print(satelites);
              Serial.print(",");
              Serial.println(hdop, 2);

              // Verificar si ya tenemos las 10 mediciones
              if (medicionesValidas >= MEDICIONES_OBJETIVO) {

                Serial.println("FIN_MEDICIONES");

                // Detener adquisición
                while (true) {
                  // Esperar
                }
              }
            }
          }
        }
      }
    }
  }
}