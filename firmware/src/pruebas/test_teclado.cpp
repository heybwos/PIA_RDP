// P4.1: presiona las 16 teclas en orden; el monitor imprime cada una.
// Si salen cambiadas, anota cuál sale por cuál: se corrige el orden en pines.h.
#include <Arduino.h>

#include "../config.h"
#include "../teclado.h"

void setup() {
  Serial.begin(USB_BAUDIOS);
  tecladoIniciar();
  delay(300);
  Serial.println("test_teclado: presiona 1 2 3 A 4 5 6 B 7 8 9 C * 0 # D");
}

void loop() {
  char k = tecladoLeer();
  if (k) Serial.printf("Tecla: %c\n", k);
}
