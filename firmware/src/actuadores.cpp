#include "actuadores.h"

#include <Arduino.h>
#include <ESP32Servo.h>

#include "config.h"
#include "pines.h"

static Servo servos[2];
static const int PINES_SERVO[2] = {PIN_SERVO_1, PIN_SERVO_2};
static uint32_t msEntre = MS_ENTRE_SERVOS, msAbierto = MS_ABIERTO;
static int angAbierto = ANG_ABIERTO;

// Cola de movimientos: cada paso mueve un servo y espera msEntre antes del siguiente
struct Paso {
  int servo;
  int angulo;
};
static Paso cola[6];
static int nCola = 0, iCola = 0;
static uint32_t tSiguiente = 0, tCerrar = 0;
static bool abiertos = false, cerradoAuto = false;

static void mover(int s, int ang) {
  if (!servos[s].attached()) servos[s].attach(PINES_SERVO[s], 500, 2400);
  servos[s].write(ang);
}

static void encolar(int s, int ang) {
  if (nCola < 6) cola[nCola++] = {s, ang};
}

void actuadoresIniciar() {
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  actuadoresLeds(false, false);
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  for (int s = 0; s < 2; s++) {
    servos[s].setPeriodHertz(50);
    mover(s, ANG_CERRADO);
    delay(MS_ENTRE_SERVOS);  // solo en el arranque: no dos servos a la vez
  }
}

void actuadoresLeds(bool verde, bool rojo) {
  digitalWrite(PIN_LED_VERDE, verde ? HIGH : LOW);
  digitalWrite(PIN_LED_ROJO, rojo ? HIGH : LOW);
}

void actuadoresAcceso(int nivel) {
  nCola = iCola = 0;
  if (nivel <= 0) {
    actuadoresLeds(false, true);
    return;
  }
  actuadoresLeds(true, false);
  encolar(0, angAbierto);
  if (nivel >= 2) encolar(1, angAbierto);
  tSiguiente = millis();
  abiertos = true;
  cerradoAuto = false;
  tCerrar = 0;
}

void actuadoresCerrarTodo() {
  nCola = iCola = 0;
  encolar(0, ANG_CERRADO);
  encolar(1, ANG_CERRADO);
  tSiguiente = millis();
  abiertos = false;
  tCerrar = 0;
}

void actuadoresTick() {
  uint32_t ahora = millis();
  if (iCola < nCola && (int32_t)(ahora - tSiguiente) >= 0) {
    mover(cola[iCola].servo, cola[iCola].angulo);
    iCola++;
    tSiguiente = ahora + msEntre;
    if (iCola == nCola && abiertos && msAbierto) tCerrar = ahora + msAbierto;  // 0: sin cierre automático
  }
  if (abiertos && tCerrar && (int32_t)(ahora - tCerrar) >= 0) {
    actuadoresCerrarTodo();
    actuadoresLeds(false, false);
    cerradoAuto = true;
  }
}

bool actuadoresOcupados() { return abiertos || iCola < nCola; }

void actuadoresMover(int servo, int angulo) {
  // Control manual: se agrega a la cola para respetar el tiempo entre servos (nunca dos a la vez)
  if (servo < 0 || servo > 1 || angulo < 0 || angulo > 180) return;
  if (iCola >= nCola) {  // cola vacía: se reinicia
    nCola = iCola = 0;
    if ((int32_t)(millis() - tSiguiente) > 0) tSiguiente = millis();
  }
  if (nCola >= 6) return;
  encolar(servo, angulo);
  tCerrar = 0;  // un movimiento manual cancela el cierre automático pendiente
}

void actuadoresAutoCierre(uint32_t ms) { msAbierto = ms; }

bool actuadoresCerradosSolos() { return cerradoAuto; }

void actuadoresConfig(uint32_t ms1, uint32_t ms2, int ang) {
  if (ms1) msEntre = ms1;
  if (ms2) msAbierto = ms2;
  if (ang > 0 && ang <= 180) angAbierto = ang;
}
