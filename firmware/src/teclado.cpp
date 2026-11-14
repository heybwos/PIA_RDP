#include "teclado.h"

#include <Arduino.h>
#include <Keypad.h>

#include "pines.h"

static const char TECLAS[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'},
};
static byte filas[4] = {(byte)PINES_FILAS[0], (byte)PINES_FILAS[1], (byte)PINES_FILAS[2], (byte)PINES_FILAS[3]};
static byte columnas[4] = {(byte)PINES_COLUMNAS[0], (byte)PINES_COLUMNAS[1], (byte)PINES_COLUMNAS[2],
                           (byte)PINES_COLUMNAS[3]};
static Keypad teclado(makeKeymap(TECLAS), filas, columnas, 4, 4);

void tecladoIniciar() { teclado.setDebounceTime(30); }

char tecladoLeer() {
  char k = teclado.getKey();
  return k == NO_KEY ? 0 : k;
}
