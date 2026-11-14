#include "huella.h"

#include <Arduino.h>

#include "config.h"
#include "pines.h"
#include "protocolo.h"

enum : uint8_t { PID_COMANDO = 0x01, PID_DATOS = 0x02, PID_RESPUESTA = 0x07, PID_FIN_DATOS = 0x08 };
static bool ok = false;

static void enviarPaquete(uint8_t pid, const uint8_t *datos, uint16_t n) {
  uint16_t len = n + 2;
  uint16_t suma = pid + (len >> 8) + (len & 0xFF);
  uint8_t cab[9] = {0xEF, 0x01,
                    (uint8_t)(HUELLA_DIRECCION >> 24), (uint8_t)(HUELLA_DIRECCION >> 16),
                    (uint8_t)(HUELLA_DIRECCION >> 8), (uint8_t)HUELLA_DIRECCION,
                    pid, (uint8_t)(len >> 8), (uint8_t)(len & 0xFF)};
  for (uint16_t i = 0; i < n; i++) suma += datos[i];
  Serial2.write(cab, sizeof cab);
  Serial2.write(datos, n);
  Serial2.write((uint8_t)(suma >> 8));
  Serial2.write((uint8_t)(suma & 0xFF));
  Serial2.flush();
}

static int leerByte(uint32_t ms) {
  uint32_t t0 = millis();
  while (!Serial2.available()) {
    if (millis() - t0 > ms) return -1;
    delay(0);
  }
  return Serial2.read();
}

// 0 bien, -1 sin respuesta, -2 suma mala, -3 muy largo
static int leerPaquete(uint8_t &pid, uint8_t *contenido, uint16_t max, uint16_t &n, uint32_t msPrimer) {
  uint32_t t0 = millis();
  int previo = -1;
  while (true) {
    int b = leerByte(50);
    if (b < 0) {
      if (millis() - t0 > msPrimer) return -1;
      continue;
    }
    if (previo == 0xEF && b == 0x01) break;
    previo = b;
  }
  uint8_t cab[7];
  for (int i = 0; i < 7; i++) {
    int b = leerByte(MS_TIMEOUT_BYTE);
    if (b < 0) return -1;
    cab[i] = (uint8_t)b;
  }
  pid = cab[4];
  uint16_t len = ((uint16_t)cab[5] << 8) | cab[6];
  if (len < 2 || len - 2 > max) return -3;
  n = len - 2;
  uint16_t suma = pid + cab[5] + cab[6];
  for (uint16_t i = 0; i < n; i++) {
    int b = leerByte(MS_TIMEOUT_BYTE);
    if (b < 0) return -1;
    contenido[i] = (uint8_t)b;
    suma += (uint8_t)b;
  }
  int sh = leerByte(MS_TIMEOUT_BYTE), sl = leerByte(MS_TIMEOUT_BYTE);
  if (sh < 0 || sl < 0) return -1;
  return ((((uint16_t)sh << 8) | (uint16_t)sl) == suma) ? 0 : -2;
}

static int comando(const uint8_t *datos, uint16_t n, uint32_t ms = 1000) {
  while (Serial2.available()) Serial2.read();
  enviarPaquete(PID_COMANDO, datos, n);
  uint8_t pid, resp[32];
  uint16_t rn;
  if (leerPaquete(pid, resp, sizeof resp, rn, ms) != 0 || pid != PID_RESPUESTA || rn < 1) return -1;
  return resp[0];
}

bool huellaIniciar() {
  Serial2.setRxBufferSize(4096);
  Serial2.begin(HUELLA_BAUDIOS, SERIAL_8N1, PIN_HUELLA_RX, PIN_HUELLA_TX);
  delay(600);  // el AS608 tarda en arrancar (solo en setup)
  uint8_t pwd[5] = {0x13, (uint8_t)(HUELLA_PASSWORD >> 24), (uint8_t)(HUELLA_PASSWORD >> 16),
                    (uint8_t)(HUELLA_PASSWORD >> 8), (uint8_t)HUELLA_PASSWORD};
  ok = comando(pwd, sizeof pwd) == 0x00;
  return ok;
}

bool huellaOk() { return ok; }

int huellaGenImg() {
  uint8_t c = 0x01;
  return comando(&c, 1, 600);
}

// CRC-32 (zlib) incremental
static uint32_t crcActualizar(uint32_t c, const uint8_t *p, size_t n) {
  for (size_t i = 0; i < n; i++) {
    c ^= p[i];
    for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320 & (0 - (c & 1)));
  }
  return c;
}

bool huellaEnviarImagen(void (*progreso)(float)) {
  uint8_t up = 0x0A;
  int cc = comando(&up, 1);
  if (cc != 0x00) {
    protocoloEnviarf("HUELLA:ERR:0A:%02X", cc < 0 ? 0xFF : cc);
    return false;
  }
  protocoloEnviarf("IMG:%d", IMG_BYTES);
  Serial.flush();
  uint32_t crc = 0xFFFFFFFF;
  size_t total = 0;
  uint8_t buf[300];
  bool fin = false;
  while (!fin && total < (size_t)IMG_BYTES) {
    uint8_t pid;
    uint16_t n;
    int r = leerPaquete(pid, buf, sizeof buf, n, 2000);
    if (r == -1 || r == -3) break;  // corte: se rellena abajo
    if (r == -2 || (pid != PID_DATOS && pid != PID_FIN_DATOS)) continue;
    size_t cabe = min((size_t)n, (size_t)IMG_BYTES - total);
    Serial.write(buf, cabe);  // se reenvía conforme llega
    crc = crcActualizar(crc, buf, cabe);
    total += cabe;
    fin = (pid == PID_FIN_DATOS);
    if (progreso) progreso((float)total / IMG_BYTES);
  }
  bool completa = total == (size_t)IMG_BYTES;
  if (!completa) {  // mantiene el marco: rellena y obliga a la PC a descartar
    memset(buf, 0, sizeof buf);
    while (total < (size_t)IMG_BYTES) {
      size_t k = min(sizeof buf, (size_t)IMG_BYTES - total);
      Serial.write(buf, k);
      crc = crcActualizar(crc, buf, k);
      total += k;
    }
  }
  Serial.flush();
  uint32_t final_ = ~crc;
  protocoloEnviarf("IMG:FIN:%08lx", (unsigned long)(completa ? final_ : ~final_));
  return completa;
}
