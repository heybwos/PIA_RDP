// P4.4 y P4.5: servo 1 abre y cierra, luego el 2; nunca los dos a la vez.
// Imprime el motivo del último reinicio: si dice "brownout", poner el capacitor de 470 uF;
// si sigue, alimentar los servos con un cargador de 5 V y 2 A uniendo las tierras.
// Por el monitor se puede mandar un ángulo (por ejemplo "75") para probar el cerrojo.
#include <Arduino.h>
#include <ESP32Servo.h>
#include <esp_system.h>

#include "../config.h"
#include "../pines.h"

static Servo s1, s2;
static int angulo = ANG_ABIERTO;

static const char *motivo(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "encendido";
    case ESP_RST_BROWNOUT: return "BROWNOUT (caida de voltaje)";
    case ESP_RST_SW: return "reinicio por software";
    case ESP_RST_PANIC: return "falla (panic)";
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT: return "watchdog";
    case ESP_RST_EXT: return "boton EN";
    default: return "otro";
  }
}

void setup() {
  Serial.begin(USB_BAUDIOS);
  delay(300);
  Serial.printf("test_servos: Motivo del ultimo reinicio: %s\n", motivo(esp_reset_reason()));
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  s1.setPeriodHertz(50);
  s2.setPeriodHertz(50);
  s1.attach(PIN_SERVO_1, 500, 2400);
  s1.write(ANG_CERRADO);
  delay(MS_ENTRE_SERVOS);
  s2.attach(PIN_SERVO_2, 500, 2400);
  s2.write(ANG_CERRADO);
  Serial.println("Manda un numero (0-180) para cambiar el angulo de apertura");
}

void loop() {
  static uint32_t t = 0;
  static int paso = 0;
  if (Serial.available()) {
    int a = Serial.parseInt();
    if (a > 0 && a <= 180) {
      angulo = a;
      Serial.printf("Angulo de apertura: %d\n", angulo);
    }
  }
  if (millis() - t < 1500) return;
  t = millis();
  switch (paso++ % 4) {
    case 0: s1.write(angulo); Serial.println("Servo 1 abierto"); break;
    case 1: s1.write(ANG_CERRADO); Serial.println("Servo 1 cerrado"); break;
    case 2: s2.write(angulo); Serial.println("Servo 2 abierto"); break;
    case 3: s2.write(ANG_CERRADO); Serial.println("Servo 2 cerrado"); break;
  }
}
