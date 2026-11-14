// Compuerta G1: ¿el AS608 entrega la imagen cruda?
//
// Habla con el sensor por UART2 implementando los paquetes a mano (sin librería),
// y manda la imagen a la PC con el marco de docs/PROTOCOLO.md:
//   IMG:<bytes>\n <bytes crudos> IMG:FIN:<crc32>\n
//
// Se usa con pc/scripts/bajar_huella.py, que manda PEDIR_HUELLA.
// Comandos por USB: PEDIR_HUELLA, PARAMS, PING, RESET.
//
// A diferencia del firmware principal, esta prueba junta la imagen completa en RAM
// antes de mandarla: así <bytes> es el número real de bytes que entregó el sensor.

#include <Arduino.h>
#include "../config.h"
#include "../pines.h"

static const char *VERSION = "test_huella_imagen";

// ---------------------------------------------------------------- paquetes AS608

enum : uint8_t {
  PID_COMANDO = 0x01,
  PID_DATOS = 0x02,
  PID_RESPUESTA = 0x07,
  PID_FIN_DATOS = 0x08,
};

enum : uint8_t {
  CMD_GEN_IMG = 0x01,
  CMD_UP_IMAGE = 0x0A,
  CMD_READ_SYS_PARA = 0x0F,
  CMD_VFY_PWD = 0x13,
};

enum Lectura { LEIDO, SIN_RESPUESTA, SUMA_MALA, MUY_LARGO };

static const char *textoLectura(Lectura r) {
  switch (r) {
    case LEIDO: return "ok";
    case SIN_RESPUESTA: return "sin_respuesta";
    case SUMA_MALA: return "suma_mala";
    case MUY_LARGO: return "muy_largo";
  }
  return "?";
}

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

// Lee un byte con tiempo límite. Devuelve -1 si no llega.
static int leerByte(uint32_t ms) {
  uint32_t t0 = millis();
  while (!Serial2.available()) {
    if (millis() - t0 > ms) return -1;
    delay(0);
  }
  return Serial2.read();
}

// Lee un paquete completo. 'contenido' recibe solo el contenido (sin la suma).
static Lectura leerPaquete(uint8_t &pid, uint8_t *contenido, uint16_t max, uint16_t &n,
                           uint32_t msPrimerByte) {
  // Sincroniza con la cabecera EF 01
  uint32_t t0 = millis();
  int previo = -1;
  while (true) {
    int b = leerByte(MS_TIMEOUT_BYTE);
    if (b < 0) {
      if (millis() - t0 > msPrimerByte) return SIN_RESPUESTA;
      continue;
    }
    if (previo == 0xEF && b == 0x01) break;
    previo = b;
    if (millis() - t0 > msPrimerByte + MS_TIMEOUT_BYTE) return SIN_RESPUESTA;
  }
  uint8_t cab[7];  // dirección (4), PID, LEN_H, LEN_L
  for (int i = 0; i < 7; i++) {
    int b = leerByte(MS_TIMEOUT_BYTE);
    if (b < 0) return SIN_RESPUESTA;
    cab[i] = (uint8_t)b;
  }
  pid = cab[4];
  uint16_t len = ((uint16_t)cab[5] << 8) | cab[6];
  if (len < 2) return MUY_LARGO;
  n = len - 2;
  if (n > max) return MUY_LARGO;
  uint16_t suma = pid + cab[5] + cab[6];
  for (uint16_t i = 0; i < n; i++) {
    int b = leerByte(MS_TIMEOUT_BYTE);
    if (b < 0) return SIN_RESPUESTA;
    contenido[i] = (uint8_t)b;
    suma += (uint8_t)b;
  }
  int sh = leerByte(MS_TIMEOUT_BYTE);
  int sl = leerByte(MS_TIMEOUT_BYTE);
  if (sh < 0 || sl < 0) return SIN_RESPUESTA;
  if ((((uint16_t)sh << 8) | (uint16_t)sl) != suma) return SUMA_MALA;
  return LEIDO;
}

// Manda un comando y lee la respuesta. Devuelve el código de confirmación, o -1.
static uint8_t respuesta[64];
static uint16_t respuestaN = 0;

static int comando(const uint8_t *datos, uint16_t n, uint32_t ms = 1000) {
  while (Serial2.available()) Serial2.read();
  enviarPaquete(PID_COMANDO, datos, n);
  uint8_t pid;
  Lectura r = leerPaquete(pid, respuesta, sizeof respuesta, respuestaN, ms);
  if (r != LEIDO) {
    Serial.printf("DIAG:cmd %02X %s\n", datos[0], textoLectura(r));
    return -1;
  }
  if (pid != PID_RESPUESTA || respuestaN < 1) {
    Serial.printf("DIAG:cmd %02X pid %02X n %u\n", datos[0], pid, respuestaN);
    return -1;
  }
  return respuesta[0];
}

// ---------------------------------------------------------------- CRC-32 (zlib)

static uint32_t crc32(const uint8_t *p, size_t n) {
  uint32_t c = 0xFFFFFFFF;
  for (size_t i = 0; i < n; i++) {
    c ^= p[i];
    for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320 & (0 - (c & 1)));
  }
  return ~c;
}

// ---------------------------------------------------------------- pasos

static bool saludar() {
  uint8_t pwd[5] = {CMD_VFY_PWD, (uint8_t)(HUELLA_PASSWORD >> 24), (uint8_t)(HUELLA_PASSWORD >> 16),
                    (uint8_t)(HUELLA_PASSWORD >> 8), (uint8_t)HUELLA_PASSWORD};
  int cc = comando(pwd, sizeof pwd);
  Serial.printf("DIAG:VfyPwd cc=%d a %lu baudios\n", cc, (unsigned long)HUELLA_BAUDIOS);
  return cc == 0x00;
}

// Si el sensor no contesta a 57600, prueba 9600*N con N de 1 a 12 y dice cuál responde.
static void buscarBaudios() {
  uint8_t pwd[5] = {CMD_VFY_PWD, 0, 0, 0, 0};
  for (int nn = 1; nn <= 12; nn++) {
    uint32_t b = 9600UL * nn;
    if (b == HUELLA_BAUDIOS) continue;
    Serial2.updateBaudRate(b);
    delay(50);
    int cc = comando(pwd, sizeof pwd, 300);
    if (cc >= 0) {
      Serial.printf("DIAG:el sensor responde a %lu (cc=%d)\n", (unsigned long)b, cc);
      Serial2.updateBaudRate(HUELLA_BAUDIOS);
      return;
    }
  }
  Serial2.updateBaudRate(HUELLA_BAUDIOS);
  Serial.println("DIAG:no responde a ningun baudio; revisa Vi 5V, GND, TX-RX");
}

static void imprimirParametros() {
  uint8_t c = CMD_READ_SYS_PARA;
  int cc = comando(&c, 1);
  if (cc != 0x00 || respuestaN < 17) {
    Serial.printf("DIAG:ReadSysPara cc=%d n=%u\n", cc, respuestaN);
    return;
  }
  const uint8_t *p = respuesta + 1;
  auto u16 = [&](int i) { return (unsigned)((p[i] << 8) | p[i + 1]); };
  unsigned tamPaquete = 32u << u16(12);
  unsigned long baudios = 9600UL * u16(14);
  Serial.printf("DIAG:estado=%04X id=%04X capacidad=%u seg=%u\n", u16(0), u16(2), u16(4), u16(6));
  Serial.printf("DIAG:paquete=%u bytes baudios=%lu\n", tamPaquete, baudios);
}

static uint8_t *imagen = nullptr;
static const size_t IMG_MAX = IMG_BYTES + 4096;  // margen por si el sensor manda de más

static void capturar() {
  // 1. Esperar el dedo con GenImg
  Serial.println("HUELLA:ESPERA");
  uint8_t gen = CMD_GEN_IMG;
  uint32_t t0 = millis();
  int ultimo = -2;
  while (true) {
    int cc = comando(&gen, 1);
    if (cc == 0x00) break;
    if (cc != ultimo && cc != 0x02) Serial.printf("DIAG:GenImg cc=%d\n", cc);
    ultimo = cc;
    if (millis() - t0 > MS_ESPERA_DEDO) {
      Serial.println("HUELLA:ERR:TIEMPO");
      return;
    }
    delay(80);
  }
  Serial.println("HUELLA:DEDO");

  // 2. UpImage: respuesta y luego paquetes de datos hasta PID 0x08
  uint8_t up = CMD_UP_IMAGE;
  int cc = comando(&up, 1);
  if (cc != 0x00) {
    Serial.printf("HUELLA:ERR:0A:%02X\n", cc < 0 ? 0xFF : cc);
    return;
  }
  size_t total = 0;
  unsigned paquetes = 0, malos = 0, tamPrimero = 0;
  uint8_t buf[300];
  uint32_t tInicio = millis();
  bool fin = false;
  while (!fin) {
    uint8_t pid;
    uint16_t n;
    Lectura r = leerPaquete(pid, buf, sizeof buf, n, 2000);
    if (r == SIN_RESPUESTA) {
      Serial.printf("DIAG:corte tras %u paquetes\n", paquetes);
      break;
    }
    if (r != LEIDO) {
      malos++;
      if (r == MUY_LARGO) break;
      continue;  // suma mala: se cuenta y se sigue (los bytes se pierden)
    }
    if (pid != PID_DATOS && pid != PID_FIN_DATOS) {
      Serial.printf("DIAG:pid inesperado %02X\n", pid);
      continue;
    }
    if (paquetes == 0) tamPrimero = n;
    paquetes++;
    size_t cabe = min((size_t)n, IMG_MAX - total);
    memcpy(imagen + total, buf, cabe);
    total += cabe;
    fin = (pid == PID_FIN_DATOS);
  }
  uint32_t ms = millis() - tInicio;
  Serial.printf("DIAG:paquetes=%u tam=%u malos=%u fin=%d\n", paquetes, tamPrimero, malos, fin);
  Serial.printf("DIAG:bytes=%u esperados=%d ms=%lu\n", (unsigned)total, IMG_BYTES,
                (unsigned long)ms);

  // 3. Marco hacia la PC
  if (total == 0) {
    Serial.println("HUELLA:ERR:SIN_DATOS");
    return;
  }
  uint32_t crc = crc32(imagen, total);
  Serial.printf("IMG:%u\n", (unsigned)total);
  Serial.flush();
  Serial.write(imagen, total);
  Serial.flush();
  Serial.printf("IMG:FIN:%08lx\n", (unsigned long)crc);
}

// ---------------------------------------------------------------- programa

static bool sensorOk = false;

static void arrancar() {
  sensorOk = saludar();
  if (!sensorOk) buscarBaudios();
  else imprimirParametros();
  Serial.printf("HOLA:%s:%s:NA\n", VERSION, sensorOk ? "OK" : "ERR");
}

void setup() {
  Serial.begin(USB_BAUDIOS);
  Serial2.setRxBufferSize(4096);
  Serial2.begin(HUELLA_BAUDIOS, SERIAL_8N1, PIN_HUELLA_RX, PIN_HUELLA_TX);
  imagen = (uint8_t *)malloc(IMG_MAX);
  delay(600);  // el AS608 tarda en arrancar
  if (!imagen) Serial.println("DIAG:sin memoria para la imagen");
  arrancar();
}

static String linea;

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c != '\n') {
      if (linea.length() < 64) linea += c;
      continue;
    }
    linea.trim();
    if (linea == "PING") {
      Serial.println("PONG");
    } else if (linea == "RESET") {
      arrancar();
    } else if (linea == "PARAMS") {
      imprimirParametros();
      Serial.println("OK:PARAMS");
    } else if (linea == "PEDIR_HUELLA") {
      if (!imagen) Serial.println("ERR:sin_memoria");
      else capturar();
    } else if (linea.length()) {
      Serial.printf("ERR:desconocido:%s\n", linea.c_str());
    }
    linea = "";
  }
}
