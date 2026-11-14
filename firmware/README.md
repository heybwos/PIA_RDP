# Firmware

ESP32 DevKit V1 (WROOM-32), PlatformIO. Cada entorno de `platformio.ini` compila un solo programa.

| Entorno | Qué hace |
|---|---|
| `test_huella_imagen` | Compuerta G1: baja la imagen cruda del AS608. Se usa con `pc/scripts/bajar_huella.py`. |

## Compilar y cargar

En VS Code con PlatformIO: abrir la carpeta `firmware/`, elegir el entorno y "Upload". Desde la terminal:

```
%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -e test_huella_imagen -t upload --upload-port COM5
```

Cierra el monitor serie antes de correr el script de la PC: los dos no pueden tener el puerto abierto.

Sin PlatformIO: Arduino IDE 2, placa "DOIT ESP32 DEVKIT V1"; copia `src/pruebas/test_huella_imagen.cpp`, `src/config.h` y `src/pines.h` a un sketch y cambia los `#include "../..."` por `#include "..."`.

Compilado en la PC el 13 de noviembre de 2026 con `espressif32@6.9.0`: sin errores.
