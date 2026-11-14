// Ajustes del firmware. Si cambias USB_BAUDIOS, cambia también [serie].baudios en config.toml.
#pragma once
#include <stdint.h>

constexpr uint32_t USB_BAUDIOS = 921600;   // respaldo: 115200
constexpr uint32_t HUELLA_BAUDIOS = 57600; // no se cambia (corrección C3)
constexpr uint32_t HUELLA_PASSWORD = 0x00000000;
constexpr uint32_t HUELLA_DIRECCION = 0xFFFFFFFF;

constexpr int IMG_ANCHO = 256;
constexpr int IMG_ALTO = 288;
constexpr int IMG_BYTES = IMG_ANCHO * IMG_ALTO / 2;  // 4 bits por píxel: 36864

constexpr uint32_t MS_ESPERA_DEDO = 15000;   // tiempo límite para poner el dedo
constexpr uint32_t MS_TIMEOUT_BYTE = 1000;   // silencio máximo del sensor entre bytes
