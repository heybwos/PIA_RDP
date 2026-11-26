# Cableado

Placa: ESP32 DevKit V1 con módulo **ESP32-WROOM-32**. Diagrama completo en `docs/conexiones.html`.

> **Dos advertencias antes de conectar nada**
>
> 1. **Mide el TX del AS608.** Alimenta solo el sensor a 5 V y mide TX contra GND en reposo. Unos 3.3 V: directo a GPIO16. Unos 5 V: divisor (1 kΩ en serie, 2 kΩ a GND). No pongas el divisor sin medir.
>    **Medido el 13 de noviembre: unos 3.3 V. Va directo, sin divisor.**
> 2. **Conecta el AS608 por la serigrafía de su placa, nunca por el color de los cables.** La hoja de datos se contradice con los colores.

| Componente | Pin del componente | ESP32 | Nota |
|---|---|---|---|
| AS608 | Vi | 5 V (VIN con USB) | |
| | GND | GND | |
| | TXD | GPIO16 (RX2) | Directo (TX medido a 3.3 V) |
| | RXD | GPIO17 (TX2) | Directo |
| Teclado 4×4 | Pines 1, 2, 3, 4 (filas) | GPIO13, 14, 27, 26 | Sin alimentación ni GND. **Recableado el 25 de noviembre** al orden del plan original. Calibrado con `test_teclado_crudo`: las 16 teclas correctas |
| | Pines 5, 6, 7, 8 (columnas) | GPIO25, 33, 32, 4 | |
| OLED | SDA / SCL | GPIO21 / GPIO22 | |
| | VCC / GND | 3.3 V / GND | |
| Servo 1 (compartimento 1) | Señal | GPIO18 | Alimentación a 5 V, nunca del pin de 3.3 V. Cerrado 0°, abierto 90° (P4.5) |
| Servo 2 (compartimento 2) | Señal | GPIO19 | Cerrado 0°, abierto 90° (P4.5) |

**Resultado de P4 (14 de noviembre):** OLED en 0x3C ✅ (el módulo rotula SCL como SCK). Teclado ✅ tras invertir el orden de pines en `pines.h`. Servos ✅ uno a la vez, sin brownout, alimentados con 5 V de un USB de monitor (0.9 A) con GND común; para la demo, cargador de 5 V y 2 A o power bank. LEDs ⏳ sin conectar.
| LED verde | Ánodo, con 220 Ω | GPIO23 | |
| LED rojo | Ánodo, con 220 Ω | GPIO5 | Puede parpadear débil al encender |

Pines elegidos para evitar los de arranque (0, 2, 5\*, 12, 15), los de la flash (6 a 11) y UART0 (1 y 3, el USB). \*GPIO5 solo maneja un LED, no afecta el arranque.

Si la placa resulta ser **WROVER**, GPIO16 y 17 están ocupados por la PSRAM: hay que mover la UART2 del sensor a otros pines libres y cambiar `firmware/src/pines.h`.
