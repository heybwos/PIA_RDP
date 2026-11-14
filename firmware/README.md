# Firmware

ESP32 DevKit V1 (WROOM-32), PlatformIO. Cada entorno de `platformio.ini` compila un solo programa.

| Entorno | Qué hace |
|---|---|
| `esp32dev` | **Principal.** Máquina de estados sin `delay()`: teclado, AS608, OLED, LEDs y servos, protocolo de `docs/PROTOCOLO.md`. |
| `test_teclado` | P4.1: imprime cada tecla presionada. |
| `test_oled` | P4.2: dos líneas y una barra; imprime la dirección I2C encontrada. |
| `test_leds` | P4.3: verde y rojo alternan cada segundo. |
| `test_servos` | P4.4 y P4.5: servos por comandos (`M <servo> <ángulo>`, `P <c1> <a1> <c2> <a2>`); imprime el motivo del último reinicio (delata un brownout). Se usa con `app/herramientas/servos.html` en Edge o Chrome (Web Serial) para elegir los ángulos. |
| `test_huella_imagen` | G1: baja la imagen cruda del AS608 (con `pc/scripts/bajar_huella.py`). |

Librerías con versión fija: Keypad 3.1.1, Adafruit SSD1306 2.5.13, Adafruit GFX 1.11.11, Adafruit BusIO 1.16.2, ESP32Servo 3.0.6.

## Compilar y cargar

En VS Code con PlatformIO: abrir la carpeta `firmware/`, elegir el entorno y "Upload". Desde la terminal (en la raíz del repo):

```
%USERPROFILE%\.platformio\penv\Scripts\pio.exe run -d firmware -e esp32dev -t upload --upload-port COM4
%USERPROFILE%\.platformio\penv\Scripts\pio.exe device monitor -d firmware -p COM4
```

Con esta placa (CH340) hay que **mantener presionado BOOT** cuando aparece `Connecting....` hasta que empiece `Writing at ...`.

Cierra el monitor serie antes de usar la app o un script de la PC: los dos no pueden tener el puerto abierto.

Sin PlatformIO: Arduino IDE 2, placa "DOIT ESP32 DEVKIT V1"; instala las librerías de arriba y abre los `.cpp` de `src/` como sketch.

Compilado en la PC el 14 de noviembre de 2026 con `espressif32@6.9.0`: los seis entornos compilan sin errores. `esp32dev` usa 7.0 % de RAM y 24.6 % de flash. `test_huella_imagen` se probó con el sensor real (G1-A). P4 (14 de noviembre): `test_oled`, `test_teclado` y `test_servos` cargados y aprobados en la placa; `test_leds` pendiente (LEDs sin conectar); `esp32dev` todavía no se ha cargado (P5).

Para cargar un entorno y abrir su monitor desde la raíz del repo: `& .\pc\scripts\prueba_modulo.ps1 -Entorno test_teclado -Puerto COM4` (con `-SinMonitor` deja el puerto libre).
