// Ajustes del firmware. Si cambias USB_BAUDIOS, cambia también [serie].baudios en config.toml.
#pragma once
#include <stdint.h>

#define FIRMWARE_VERSION "1.0"

constexpr uint32_t USB_BAUDIOS = 921600;   // respaldo: 115200
constexpr uint32_t HUELLA_BAUDIOS = 57600; // no se cambia (corrección C3)
constexpr uint32_t HUELLA_PASSWORD = 0x00000000;
constexpr uint32_t HUELLA_DIRECCION = 0xFFFFFFFF;

constexpr int IMG_ANCHO = 256;
constexpr int IMG_ALTO = 288;
constexpr int IMG_BYTES = IMG_ANCHO * IMG_ALTO / 2;  // 4 bits por píxel: 36864

constexpr uint32_t MS_ESPERA_DEDO = 15000;   // tiempo límite para poner el dedo
constexpr uint32_t MS_TIMEOUT_BYTE = 1000;   // silencio máximo del sensor entre bytes

// Seguridad y tiempos (los de servos se pueden cambiar desde la PC con CONFIG:<clave>:<valor>)
constexpr uint32_t MS_SIN_PING = 5000;       // sin PING de la PC: estado seguro
constexpr uint32_t MS_FASE_PIN = 30000;      // tiempo límite para teclear ID y PIN
constexpr uint32_t MS_FASE_PC = 60000;       // tiempo límite esperando a la PC (rostro, decisión)
constexpr uint32_t MS_ENTRE_SERVOS = 300;    // nunca dos servos a la vez
constexpr uint32_t MS_ABIERTO = 8000;        // cierre automático
constexpr int ANG_CERRADO = 0;
constexpr int ANG_ABIERTO = 90;
