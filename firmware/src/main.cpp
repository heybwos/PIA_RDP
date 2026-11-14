// Firmware principal: máquina de estados sin delay() (docs/PROTOCOLO.md).
//
// SIN_PC    sin PING en 5 s: LED rojo, OLED "Sin conexion con la PC", servos cerrados, teclado ignorado
// REPOSO    espera la primera tecla
// TECLEANDO arma ID (2 dígitos + #) y PIN (4 dígitos + #); * borra, D cancela
// ESPERA_PC el PIN ya se mandó; atiende MSG, PEDIR_HUELLA, ACCESO, CONFIG
// HUELLA    GenImg cada 100 ms hasta que hay dedo (tiempo límite), luego UpImage y envío
// ACTUANDO  servos abiertos; al cerrarse solos vuelve a REPOSO
//
// Seguridad: servos cerrados en setup(); al perder la PC se cierran y nada se abre;
// cada fase tiene tiempo límite.

#include <Arduino.h>
#include <esp_system.h>

#include "actuadores.h"
#include "config.h"
#include "huella.h"
#include "pantalla.h"
#include "pines.h"
#include "protocolo.h"
#include "teclado.h"

enum Estado { SIN_PC, REPOSO, TECLEANDO, ESPERA_PC, HUELLA, ACTUANDO };
static Estado estado = SIN_PC;
static uint32_t tUltimoPing = 0, tFase = 0, tGenImg = 0;
static bool hubo_ping = false;
static String id, pin;
static bool enPin = false;

static void cambiar(Estado e) {
  estado = e;
  tFase = millis();
}

static void hola() {
  protocoloEnviarf("HOLA:%s:%s:%s", FIRMWARE_VERSION, huellaOk() ? "OK" : "ERR", pantallaOk() ? "OK" : "ERR");
}

static void aReposo(const char *l1 = "Listo", const char *l2 = "Teclea tu ID") {
  id = pin = "";
  enPin = false;
  actuadoresLeds(false, false);
  pantallaMostrar(l1, l2);
  cambiar(REPOSO);
}

static void aSinPc() {
  actuadoresCerrarTodo();
  actuadoresLeds(false, true);
  pantallaMostrar("Sin conexion", "con la PC");
  id = pin = "";
  enPin = false;
  cambiar(SIN_PC);
}

static void barraHuella(float p) { pantallaBarra(p); }

static void tecla(char k) {
  protocoloEnviarf("TECLA:%c", k);
  if (k == 'D') {
    protocoloEnviar("CANCELA");
    aReposo("Cancelado", "Teclea tu ID");
    return;
  }
  if (estado == REPOSO) cambiar(TECLEANDO);
  tFase = millis();
  String &campo = enPin ? pin : id;
  size_t largo = enPin ? 4 : 2;
  if (k == '*') {
    if (campo.length()) campo.remove(campo.length() - 1);
  } else if (k == '#') {
    if (!enPin && id.length() == 2) {
      enPin = true;
    } else if (enPin && pin.length() == 4) {
      protocoloEnviarf("PIN:%s:%s", id.c_str(), pin.c_str());
      pantallaMostrar("Verificando", "PIN...");
      cambiar(ESPERA_PC);
      return;
    }
  } else if (k >= '0' && k <= '9' && campo.length() < largo) {
    campo += k;
  }
  char l1[20], l2[20];
  snprintf(l1, sizeof l1, "ID %s", id.c_str());
  if (enPin) {
    String estrellas;
    for (size_t i = 0; i < pin.length(); i++) estrellas += '*';
    snprintf(l2, sizeof l2, "PIN %s", estrellas.c_str());
  } else {
    snprintf(l2, sizeof l2, "y presiona #");
  }
  pantallaMostrar(l1, l2);
}

static void comandoPc(const String &l) {
  if (l == "PING") {
    tUltimoPing = millis();
    if (!hubo_ping || estado == SIN_PC) {
      hubo_ping = true;
      aReposo();
    }
    protocoloEnviar("PONG");
    return;
  }
  if (l == "RESET") {
    actuadoresCerrarTodo();
    hola();
    aReposo();
    return;
  }
  if (estado == SIN_PC) {
    protocoloEnviar("ERR:sin_ping");
    return;
  }
  if (l.startsWith("MSG:")) {
    String t = l.substring(4);
    int s = t.indexOf('|');
    pantallaMostrar((s < 0 ? t : t.substring(0, s)).c_str(), s < 0 ? "" : t.substring(s + 1).c_str());
    protocoloEnviar("OK:MSG");
  } else if (l == "PEDIR_PIN") {
    aReposo("Teclea tu ID", "y presiona #");
    protocoloEnviar("OK:PEDIR_PIN");
  } else if (l == "PEDIR_HUELLA") {
    if (!huellaOk()) {
      protocoloEnviar("HUELLA:ERR:SENSOR");
      return;
    }
    pantallaMostrar("Coloca el dedo", "en el sensor");
    protocoloEnviar("HUELLA:ESPERA");
    cambiar(HUELLA);
  } else if (l.startsWith("ACCESO:")) {
    int nivel = l.substring(7).toInt();
    actuadoresAcceso(nivel);
    if (nivel > 0) {
      cambiar(ACTUANDO);
    } else {
      cambiar(ESPERA_PC);  // LED rojo unos segundos y vuelve a reposo por tiempo
      tFase = millis() - MS_FASE_PC + 4000;
    }
    protocoloEnviar("OK:ACCESO");
  } else if (l.startsWith("CONFIG:")) {
    int a = l.indexOf(':', 7);
    String clave = l.substring(7, a), valor = l.substring(a + 1);
    if (clave == "ms_servos") actuadoresConfig(valor.toInt(), 0, 0);
    else if (clave == "ms_abierto") actuadoresConfig(0, valor.toInt(), 0);
    else if (clave == "ang_abierto") actuadoresConfig(0, 0, valor.toInt());
    else {
      protocoloEnviar("ERR:config");
      return;
    }
    protocoloEnviarf("OK:CONFIG:%s", clave.c_str());
  } else {
    protocoloEnviar("ERR:desconocido");
  }
}

void setup() {
  actuadoresIniciar();  // primero: servos cerrados
  protocoloIniciar();
  pantallaIniciar();
  tecladoIniciar();
  pantallaMostrar("Iniciando", "");
  huellaIniciar();
  hola();
  aSinPc();
}

void loop() {
  uint32_t ahora = millis();
  String l;
  while (protocoloLinea(l)) comandoPc(l);

  // Vida: sin PING en 5 s, estado seguro (nunca durante una imagen: esa fase bloquea)
  if (estado != SIN_PC && ahora - tUltimoPing > MS_SIN_PING) aSinPc();

  actuadoresTick();
  char k = tecladoLeer();

  switch (estado) {
    case SIN_PC:
      break;
    case REPOSO:
      if (k) tecla(k);
      break;
    case TECLEANDO:
      if (k) tecla(k);
      if (millis() - tFase > MS_FASE_PIN) {
        protocoloEnviar("CANCELA");
        aReposo("Tiempo agotado", "Teclea tu ID");
      }
      break;
    case ESPERA_PC:
      if (k == 'D') tecla(k);
      if (millis() - tFase > MS_FASE_PC) aReposo();
      break;
    case HUELLA:
      if (k == 'D') {
        tecla(k);
        break;
      }
      if (ahora - tGenImg >= 100) {
        tGenImg = ahora;
        int cc = huellaGenImg();
        if (cc == 0x00) {
          protocoloEnviar("HUELLA:DEDO");
          pantallaMostrar("Leyendo huella", "no muevas el dedo");
          huellaEnviarImagen(barraHuella);
          tUltimoPing = millis();  // la transferencia bloquea unos 7 s: no cuenta como silencio
          pantallaMostrar("Huella recibida", "Procesando...");
          cambiar(ESPERA_PC);
        } else if (millis() - tFase > MS_ESPERA_DEDO) {
          protocoloEnviar("HUELLA:ERR:TIEMPO");
          pantallaMostrar("Sin dedo", "intenta de nuevo");
          cambiar(ESPERA_PC);
        }
      }
      break;
    case ACTUANDO:
      if (!actuadoresOcupados()) aReposo();
      break;
  }
}
