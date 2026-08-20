#include <SoftwareSerial.h>

SoftwareSerial gps(4, 3);  // RX, TX

void setup() {
  Serial.begin(9600);
  gps.begin(9600);

  Serial.println("Iniciando NEO-6M");
}

void loop() {
  while (gps.available()) {
    char c = gps.read();
    Serial.write(c);
  }
}

