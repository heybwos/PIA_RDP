// AS608 por UART2: paquetes a mano (sin librería) y envío de la imagen cruda a la PC.
#pragma once
#include <stdint.h>

bool huellaIniciar();  // saluda con VfyPwd; true si el sensor responde
bool huellaOk();
// Un GenImg: 0x00 = hay dedo e imagen tomada, 0x02 = sin dedo, otro = error, -1 = sin respuesta.
int huellaGenImg();
// UpImage y reenvío a la PC por partes con el marco IMG:<bytes> … IMG:FIN:<crc32>.
// Anuncia siempre IMG_BYTES; si el sensor entrega menos, rellena con ceros y manda un CRC
// invertido a propósito para que la PC descarte la imagen. Devuelve true si llegó completa.
// `progreso` se llama con 0..1 para la barra de la OLED.
bool huellaEnviarImagen(void (*progreso)(float));
