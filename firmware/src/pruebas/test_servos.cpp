// P4.4 y P4.5: servos por comandos, para elegir los ángulos de cerrado y abierto de cada uno.
// Se usa con app/herramientas/servos.html (Web Serial) o con el monitor serie.
//
// Comandos (una línea cada uno):
//   M <servo> <angulo>          mueve el servo 1 o 2 al ángulo (0-180)
//   P <c1> <a1> <c2> <a2>       prueba: abre y cierra el servo 1 y luego el 2, uno a la vez
//   ?                           repite el motivo del último reinicio
// Respuestas: "OK M 1 90", "OK P", "ERR …". Al arrancar imprime el motivo del último reinicio:
// si dice BROWNOUT, poner el capacitor de 470 uF; si sigue, fuente de 5 V y 2 A con tierras unidas.
// Ningún servo se mueve hasta recibir un comando.
#include <Arduino.h>
#include <ESP32Servo.h>
#include <esp_system.h>

#include "../config.h"
#include "../pines.h"

static Servo servos[2];
static const int PINES[2] = {PIN_SERVO_1, PIN_SERVO_2};

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

static void mover(int s, int ang) {
  if (!servos[s].attached()) {
    servos[s].setPeriodHertz(50);
    servos[s].attach(PINES[s], 500, 2400);
  }
  servos[s].write(ang);
}

static bool valido(int a) { return a >= 0 && a <= 180; }

static void comando(String l) {
  l.trim();
  if (!l.length()) return;
  if (l == "?") {
    Serial.printf("Motivo del ultimo reinicio: %s\n", motivo(esp_reset_reason()));
    return;
  }
  char c = l[0];
  int v[4] = {-1, -1, -1, -1};
  int n = sscanf(l.c_str() + 1, "%d %d %d %d", &v[0], &v[1], &v[2], &v[3]);
  if (c == 'M' && n == 2 && (v[0] == 1 || v[0] == 2) && valido(v[1])) {
    mover(v[0] - 1, v[1]);
    Serial.printf("OK M %d %d\n", v[0], v[1]);
  } else if (c == 'P' && n == 4 && valido(v[0]) && valido(v[1]) && valido(v[2]) && valido(v[3])) {
    // uno a la vez; aquí sí se usa delay: es una prueba, no el firmware principal
    for (int s = 0; s < 2; s++) {
      mover(s, v[2 * s + 1]);
      Serial.printf("Servo %d abierto (%d)\n", s + 1, v[2 * s + 1]);
      delay(1200);
      mover(s, v[2 * s]);
      Serial.printf("Servo %d cerrado (%d)\n", s + 1, v[2 * s]);
      delay(MS_ENTRE_SERVOS + 500);
    }
    Serial.println("OK P");
  } else {
    Serial.printf("ERR comando: %s\n", l.c_str());
  }
}

void setup() {
  Serial.begin(USB_BAUDIOS);
  delay(300);
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  Serial.printf("test_servos: Motivo del ultimo reinicio: %s\n", motivo(esp_reset_reason()));
  Serial.println("LISTO. Comandos: M <servo> <angulo> | P <c1> <a1> <c2> <a2> | ?");
}

void loop() {
  static String linea;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      comando(linea);
      linea = "";
    } else if (linea.length() < 40) {
      linea += c;
    }
  }
}
