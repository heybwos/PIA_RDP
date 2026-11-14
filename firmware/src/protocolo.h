// Líneas de texto por USB (docs/PROTOCOLO.md). Lectura sin bloquear.
#pragma once
#include <Arduino.h>

void protocoloIniciar();
// Devuelve true cuando hay una línea completa en `linea` (sin \r\n, máximo 64 caracteres).
bool protocoloLinea(String &linea);
void protocoloEnviar(const char *texto);
void protocoloEnviarf(const char *fmt, ...);
