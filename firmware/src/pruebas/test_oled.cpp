// P4.2: dos líneas de texto y una barra que avanza. El monitor imprime la dirección I2C.
#include <Arduino.h>

#include "../config.h"
#include "../pantalla.h"

void setup() {
  Serial.begin(USB_BAUDIOS);
  delay(300);
  uint8_t dir = pantallaIniciar();
  if (dir) Serial.printf("test_oled: pantalla en 0x%02X\n", dir);
  else Serial.println("test_oled: NO responde en 0x3C ni 0x3D. Revisa SDA 21, SCL 22, VCC 3.3 V y GND");
}

void loop() {
  static uint32_t t = 0;
  static int i = 0;
  if (millis() - t < 100) return;
  t = millis();
  pantallaMostrar("Prueba OLED", "PIA RDP FIME");
  pantallaBarra((i++ % 51) / 50.0f);
}
