// Calibración del teclado sin depender de pines.h.
// Escanea todos los GPIO libres: pone uno en LOW y lee los demás con pull-up.
// Cada tecla presionada imprime los dos GPIO que une. Con las 16 teclas en orden
// (1 2 3 A 4 5 6 B 7 8 9 C * 0 # D) se deducen filas y columnas para pines.h.
#include <Arduino.h>

#include "../config.h"

// GPIO candidatos: los 8 del teclado. GPIO 2 queda fuera: el LED azul de la placa
// lo jala a LOW y la prueba lo confundía con una tecla presionada.
static const int CANDIDATOS[] = {4, 13, 14, 25, 26, 27, 32, 33};
static const int N = sizeof(CANDIDATOS) / sizeof(CANDIDATOS[0]);

static int parA = -1, parB = -1;
static unsigned long desde = 0;
static bool reportado = false;
static int contador = 0;

static void todosEntrada() {
  for (int i = 0; i < N; i++) pinMode(CANDIDATOS[i], INPUT_PULLUP);
}

// Devuelve el primer par de GPIO unidos (a < b) o false si no hay ninguno.
static bool escanear(int &a, int &b) {
  for (int i = 0; i < N; i++) {
    todosEntrada();
    pinMode(CANDIDATOS[i], OUTPUT);
    digitalWrite(CANDIDATOS[i], LOW);
    delayMicroseconds(50);
    for (int j = 0; j < N; j++) {
      if (j == i) continue;
      if (digitalRead(CANDIDATOS[j]) == LOW) {
        a = min(CANDIDATOS[i], CANDIDATOS[j]);
        b = max(CANDIDATOS[i], CANDIDATOS[j]);
        todosEntrada();
        return true;
      }
    }
  }
  todosEntrada();
  return false;
}

void setup() {
  Serial.begin(USB_BAUDIOS);
  todosEntrada();
  delay(300);
  Serial.println("test_teclado_crudo: presiona 1 2 3 A 4 5 6 B 7 8 9 C * 0 # D (una por una)");
}

void loop() {
  int a, b;
  if (escanear(a, b)) {
    if (a != parA || b != parB) {
      parA = a;
      parB = b;
      desde = millis();
      reportado = false;
    } else if (!reportado && millis() - desde > 40) {
      contador++;
      Serial.printf("Tecla #%d: GPIO %d - GPIO %d\n", contador, a, b);
      reportado = true;
    }
  } else {
    parA = parB = -1;
    reportado = false;
  }
  delay(5);
}
