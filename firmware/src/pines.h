// Pines del ESP32 DevKit V1 (WROOM-32). Fuente: docs/CABLEADO.md
#pragma once

// AS608 por UART2. TX del sensor medido a 3.3 V: va directo.
constexpr int PIN_HUELLA_RX = 16;  // RX2 <- TXD del AS608
constexpr int PIN_HUELLA_TX = 17;  // TX2 -> RXD del AS608

// Teclado 4x4. El conector quedó al revés en la caja (pin 1 del teclado en GPIO4 … pin 8 en GPIO13);
// medido en P4 el 14 de noviembre: la tecla 1 salía como D. En lugar de recablear se invierte aquí.
// Pines del teclado: 1-4 filas, 5-8 columnas.
constexpr int PINES_FILAS[4] = {4, 32, 33, 25};     // pines 1, 2, 3, 4 del teclado
constexpr int PINES_COLUMNAS[4] = {26, 27, 14, 13}; // pines 5, 6, 7, 8 del teclado

// OLED I2C
constexpr int PIN_SDA = 21;
constexpr int PIN_SCL = 22;

// Servos
constexpr int PIN_SERVO_1 = 18;
constexpr int PIN_SERVO_2 = 19;

// LEDs
constexpr int PIN_LED_VERDE = 23;
constexpr int PIN_LED_ROJO = 5;
