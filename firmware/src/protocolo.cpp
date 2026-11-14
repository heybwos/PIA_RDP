#include "protocolo.h"

#include <stdarg.h>

#include "config.h"

static String pendiente;

void protocoloIniciar() {
  Serial.setRxBufferSize(1024);
  Serial.begin(USB_BAUDIOS);
  pendiente.reserve(80);
}

bool protocoloLinea(String &linea) {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      linea = pendiente;
      linea.trim();
      pendiente = "";
      if (linea.length()) return true;
      continue;
    }
    if (pendiente.length() < 64) pendiente += c;
  }
  return false;
}

void protocoloEnviar(const char *texto) {
  Serial.print(texto);
  Serial.print('\n');
}

void protocoloEnviarf(const char *fmt, ...) {
  char buf[96];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  protocoloEnviar(buf);
}
