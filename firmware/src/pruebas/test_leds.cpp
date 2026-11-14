// P4.3: verde y rojo alternan cada segundo.
#include <Arduino.h>

#include "../config.h"
#include "../pines.h"

void setup() {
  Serial.begin(USB_BAUDIOS);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  delay(300);
  Serial.println("test_leds: verde (GPIO23) y rojo (GPIO5) alternan cada segundo");
}

void loop() {
  static uint32_t t = 0;
  static bool verde = false;
  if (millis() - t < 1000) return;
  t = millis();
  verde = !verde;
  digitalWrite(PIN_LED_VERDE, verde);
  digitalWrite(PIN_LED_ROJO, !verde);
  Serial.println(verde ? "verde" : "rojo");
}
