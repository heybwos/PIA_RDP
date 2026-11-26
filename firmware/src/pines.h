// Pines del ESP32 DevKit V1 (WROOM-32). Fuente: docs/CABLEADO.md
#pragma once

// AS608 por UART2. TX del sensor medido a 3.3 V: va directo.
constexpr int PIN_HUELLA_RX = 16;  // RX2 <- TXD del AS608
constexpr int PIN_HUELLA_TX = 17;  // TX2 -> RXD del AS608

// Teclado 4x4. Recableado el 25 de noviembre; calibrado con el entorno test_teclado_crudo
// (cada tecla imprime los dos GPIO que une). Ya no hace falta la inversión del 14 de noviembre.
// Filas: 1 2 3 A / 4 5 6 B / 7 8 9 C / * 0 # D. Columnas: 1 4 7 * / 2 5 8 0 / 3 6 9 # / A B C D.
constexpr int PINES_FILAS[4] = {13, 14, 27, 26};
constexpr int PINES_COLUMNAS[4] = {25, 33, 32, 4};

// OLED I2C
constexpr int PIN_SDA = 21;
constexpr int PIN_SCL = 22;

// Servos
constexpr int PIN_SERVO_1 = 18;
constexpr int PIN_SERVO_2 = 19;

// LEDs
constexpr int PIN_LED_VERDE = 23;
constexpr int PIN_LED_ROJO = 5;
