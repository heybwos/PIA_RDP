// LEDs y servos. Los servos se mueven uno a la vez y se cierran solos (sin delay: actuadoresTick()).
#pragma once
#include <stdint.h>

void actuadoresIniciar();          // servos a cerrado, LEDs apagados
void actuadoresLeds(bool verde, bool rojo);
void actuadoresAcceso(int nivel);  // 0: rojo. 1: verde y servo 1. 2: verde, servo 1 y luego servo 2
void actuadoresCerrarTodo();       // estado seguro: cierra en secuencia
void actuadoresTick();             // llamar en cada loop()
bool actuadoresOcupados();         // true mientras hay servos abiertos o en movimiento
void actuadoresConfig(uint32_t msEntreServos, uint32_t msAbierto, int angAbierto);
