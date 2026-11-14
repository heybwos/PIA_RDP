// Teclado matricial 4x4 (librería Keypad). Filas GPIO 13, 14, 27, 26; columnas 25, 33, 32, 4.
#pragma once

void tecladoIniciar();
// Devuelve la tecla recién presionada ('0'-'9', 'A'-'D', '*', '#') o 0 si no hay.
char tecladoLeer();
