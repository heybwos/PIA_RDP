# Protocolo serie ESP32 ↔ PC

Contrato único entre `firmware/` y `pc/`. Ninguno de los dos lados se programa contra otra cosa.

## Enlace

- USB (UART0 del ESP32) a **921600 baudios**, 8N1. Respaldo: 115200 (`firmware/src/config.h` y `config.toml`, los dos iguales).
- Líneas de texto ASCII terminadas en `\n`, de **64 caracteres como máximo**. Sin acentos.
- La PC ignora las líneas que no reconoce. Las que empiezan con `DIAG:` son diagnóstico: se muestran o se guardan, nunca cambian el estado.

## ESP32 → PC

| Línea | Cuándo |
|---|---|
| `HOLA:<version>:<sensor OK\|ERR>:<oled OK\|ERR>` | Al arrancar y como respuesta a `RESET`. |
| `TECLA:<c>` | En cuanto se presiona una tecla. |
| `PIN:<id>:<pin>` | Al cerrar con `#`. El firmware arma ID y PIN (`*` borra). |
| `CANCELA` | Tecla `D`. |
| `HUELLA:ESPERA` | Esperando dedo. |
| `HUELLA:DEDO` | `GenImg` devolvió 0x00; empieza `UpImage`. |
| `HUELLA:ERR:<codigo>` | Sin dedo en el tiempo límite (`TIEMPO`), o el código de confirmación del sensor en hex (`ERR:0A:01`, comando y código). |
| `IMG:<bytes>` | Le siguen **exactamente** `<bytes>` bytes crudos y después la línea `IMG:FIN:<crc32>`. |
| `IMG:FIN:<crc32>` | CRC-32 (el de zlib, IEEE 802.3) de los bytes crudos, en hex de 8 dígitos en minúsculas. |
| `PONG` | Respuesta a `PING`. |
| `OK:<comando>` / `ERR:<motivo>` | Respuesta a un comando. |
| `DIAG:<texto>` | Diagnóstico libre. |

### Marco de imagen (corrección C1)

```
IMG:36864\n
<36864 bytes crudos>
IMG:FIN:1a2b3c4d\n
```

El CRC va **al final** porque el ESP32 no lo conoce hasta recibir la imagen completa del sensor.

- **Imagen:** 256 × 288 píxeles, 4 bits por píxel: 36,864 bytes, dos píxeles por byte, fila por fila de arriba abajo.
- **Orden de nibbles:** lo decide la PC (`huella.nibble_alto_primero` en `config.toml`). El ESP32 no toca los datos.
- **Firmware de prueba (`test_huella_imagen`):** junta la imagen completa en RAM y luego la manda, para que `<bytes>` sea el número real de bytes recibidos del sensor (diagnóstico de G1-B). El firmware principal la reenvía por partes conforme llega.
- **Lectura en la PC:** tras `IMG:<bytes>` el lector pasa a modo binario, lee exactamente `<bytes>` con tiempo límite por bloque, y vuelve a modo línea. Si se corta o el CRC no coincide, descarta la imagen, manda `RESET` y lo reporta.

## PC → ESP32

| Línea | Efecto |
|---|---|
| `MSG:<linea1>\|<linea2>` | Texto para la OLED. |
| `PEDIR_PIN` | Empieza la captura de ID y PIN. |
| `PEDIR_HUELLA` | Empieza la captura de huella (`HUELLA:ESPERA` … `IMG:FIN`). |
| `ACCESO:0\|1\|2` | Decisión: LED rojo, o LED verde y compartimento 1, o los dos. |
| `CONFIG:<clave>:<valor>` | Tiempos de servo y de fase. |
| `RESET` | Vuelve al estado inicial y responde `HOLA`. |
| `PING` | Responde `PONG`. |
| `PARAMS` | Solo en `test_huella_imagen`: vuelve a imprimir los parámetros del sensor. |

## Vida

`PING` de la PC cada segundo. Sin `PING` por 5 s (fuera de una transferencia de imagen), el ESP32 pasa a estado seguro: servos cerrados, LED rojo apagado, OLED "Sin conexion".

## Paquetes del AS608 (lado ESP32, a 57600 baudios)

```
EF 01 | FF FF FF FF | PID | LEN_H LEN_L | contenido | SUMA_H SUMA_L
```

- `PID`: 0x01 comando, 0x02 datos, 0x07 respuesta, 0x08 último paquete de datos.
- `LEN` = bytes de contenido + 2 (la suma).
- `SUMA` = PID + LEN_H + LEN_L + todos los bytes del contenido, en 16 bits.
- Comandos usados: `VfyPwd` 0x13, `ReadSysPara` 0x0F, `GenImg` 0x01, `UpImage` 0x0A.
- **Verificado en G1 (13 de noviembre, 3 de 3 capturas):** 288 paquetes de datos de 128 bytes, el último con PID 0x08, sin errores de suma; 36,864 bytes en unos 7.7 s desde `UpImage`. `ReadSysPara`: paquete de 128 bytes, 57600 baudios, capacidad 300, seguridad 3. El firmware lee la longitud de cada cabecera; no depende del tamaño.
- **Orden de nibbles: alto primero** (verificado: con ese orden la diferencia entre píxeles vecinos es la misma dentro de un byte y entre bytes, 0.24 contra 0.24; con el orden bajo, entre bytes sube a 0.65).
