// OLED SSD1306 128x64 por I2C (SDA 21, SCL 22). Texto sin acentos.
#pragma once
#include <stdint.h>

// Busca la pantalla en 0x3C y 0x3D. Devuelve la dirección encontrada o 0.
uint8_t pantallaIniciar();
bool pantallaOk();
void pantallaMostrar(const char *l1, const char *l2 = "");
// Barra de progreso 0..1 debajo del texto; negativo la quita.
void pantallaBarra(float progreso);
