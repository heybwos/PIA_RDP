# Plan del sistema real: del modo Simular al ESP32

Plan elaborado y verificado por Fable 5.2 (supervisor) el 12 de noviembre de 2026. **Todavía no se ejecuta.** Lo ejecutará Opus 5.5 por fases; Fable revisa y aprueba cada una con el protocolo de la sección 6.

## 1. Respuesta corta

- **¿Ya existen la lógica y los algoritmos reales?** No. El repositorio solo tiene `docs/`: no hay `pc/`, `firmware/`, `app/` ni `config.toml`. La maqueta trae implementaciones reales en JavaScript, pero sobre datos sintéticos. Viola-Jones y la alineación del rostro son falsos, y no existen la frecuencia de crestas, el PIN con hash, el registro de usuarios ni el firmware.
- **¿Hay que esperar a saber cómo llegan los datos del sensor?** No para construir: todo se valida con FVC2002, ORL/LFW y un ESP32 falso que hable el protocolo. Sí hay que hacer **ya** la prueba de imagen cruda del AS608: si falla, hay que comprar un R307, y eso tarda días.

## 2. Inventario de lo que existe

| Pieza | Estado |
|---|---|
| Normalización y segmentación de huella | Solo en la maqueta; real |
| Campo de orientación | Solo en la maqueta; real y fiel (Sobel, mínimos cuadrados, suavizado sobre 2θ) |
| Frecuencia de crestas por bloque | **No existe** (frecuencia fija de 1/8.9, ajustada al generador sintético) |
| Gabor | Solo en la maqueta; simplificado (una sola frecuencia) |
| Binarización y adelgazamiento | Solo en la maqueta; real (Zhang-Suen) |
| Minucias por número de cruce | Solo en la maqueta; real, pero sin dirección (ángulo en [0, π)) |
| Eliminación de minucias falsas | Parcial: faltan los espolones cortos |
| Matching por grafos | Solo en la maqueta; la estructura sirve, pero depende del orden de los vecinos y exige el mismo tipo de minucia, lo que falla con huellas reales |
| Viola-Jones | **Falso**: usa las posiciones conocidas del generador |
| Alineación geométrica | **Falso**: la cara se genera ya alineada |
| Normalización fotométrica | Solo en la maqueta; real |
| Eigenfaces/PCA | Solo en la maqueta; real y fiel |
| Distancia euclidiana con umbral | Solo en la maqueta; real |
| Distancia al espacio de caras | Parcial: se calcula, pero no rechaza |
| Fusión y decisión | Solo en la maqueta; coincide con la regla acordada |
| PIN con PBKDF2 | **No existe** (comparación en texto plano) |
| Calibración FAR/FRR/EER | Parcial: solo rostro y sobre las mismas imágenes de entrenamiento |
| Registro de usuarios | **No existe** |
| Bitácora | Solo en memoria, sin SQLite |
| Protocolo serial | Solo el CRC32 y el empaquetado; el modo ESP32 es un botón falso |
| Firmware | **No existe** |

**Se porta casi directo del JS:** orientación, adelgazamiento (o `skeletonize`), número de cruce, PCA, fusión, CRC32 y la secuencia del orquestador.
**Se escribe nuevo:** frecuencia por bloque, Gabor con frecuencia local, espolones, dirección de minucia, matching sin depender del orden de vecinos, Viola-Jones, alineación, rechazo por espacio de caras, PBKDF2, calibración con datos separados, registro, bitácora y todo el firmware.

## 3. Lo que depende del hardware y cómo se absorbe

| Incógnita | Cómo se absorbe sin rehacer |
|---|---|
| Que el AS608 entregue la imagen cruda | Si no, se compra un R307 o FPM10; el parser no cambia (mismo protocolo de paquetes) |
| Orden de los nibbles | `orden_nibbles = "alto" \| "bajo" \| "auto"` en `config.toml`, con un detector y una prueba con ambos órdenes |
| Resolución y tamaño reales | El mensaje lleva `ancho:alto:bpp`; el parser valida la longitud y no asume 36,864 bytes |
| Calidad a 4 bits y periodo de crestas | Perfiles `[huella.fvc]` y `[huella.as608]` en `config.toml`; en la fase 1a se mide el EER de FVC a 8 y a 4 bits |
| Baudios del sensor y del USB | Configurables; el firmware prueba 57600 y 115200 al arrancar |
| Umbrales con huellas del AS608 | La calibración recibe una carpeta; las capturas reales van a `datos/as608/` y pasan por las mismas pruebas |
| Orden de pines del teclado | Arreglos en `firmware/include/config.h`, confirmados con `test_teclado` |
| IP o índice de DroidCam | `config.toml` |

Tiempo estimado de la transferencia de la huella (cálculo, sin medir): unos 7.0 s a 57600 baudios y 3.5 s a 115200, contando las cabeceras de los 288 paquetes.

## 4. Decisiones tomadas (12 de noviembre de 2026)

| # | Decisión |
|---|---|
| 1 | **OpenCV 4.14.0.94** en un venv aislado. La 5.0.0 instalada globalmente no trae `cv2.CascadeClassifier` ni los XML de Haar (comprobado). La fase 0 confirma que la 4.14 sí los trae. |
| 2 | **Imagen por trozos**, uno por paquete del sensor, y cierre con `IMG:FIN:<total>:<crc32>` o `IMG:ERR:<motivo>`. El ESP32 no conoce el CRC antes de reenviar los datos. |
| 3 | El encabezado de la imagen lleva `ancho:alto:bpp`. |
| 4 | Los entornos de prueba del firmware se adelantan a una **fase H**, justo después de la fase 0. |
| 5 | Sensor a 57600 baudios al principio; se sube a 115200 solo cuando todo funcione (el cambio se guarda en el sensor). |
| 6 | Modo Simular con semilla fija, botón "otra muestra" y las tasas reales a la vista. |
| 7 | Eigenfaces de la demo real se entrena con el dataset más los cuadros de DroidCam de los registrados, todos por el mismo pipeline. |
| 8 | Se registran **3 o 4 personas del equipo**, al menos una por nivel, más alguien sin registrar que haga de impostor. |
| 9 | La biometría real se queda en `datos/` (fuera de git) y se usa solo con el permiso de cada persona. |
| 10 | La demo se presenta en **esta misma PC**. Entrega confirmada: **viernes 27 de noviembre de 2026**. |
| 11 | **Tope de EER del 15 %** en los datasets: si se pasa, se detiene el trabajo, se reporta el número con una hipótesis y decide el usuario, sin tocar los datos. |
| — | Alcance: PC y firmware. Interfaz: la maqueta terminada (los algoritmos pasan a Python y la página solo muestra). Ejecuta Opus 5.5 y supervisa Fable 5.2. |

## 5. Fases

| Fase | Fechas | Tareas y archivos | Criterios de aceptación | Estado al cerrar |
|---|---|---|---|---|
| **0 Entorno** | 13 nov | `.venv` con Python 3.14, `requirements.txt` con versiones fijas, estructura de carpetas, `.gitignore`, `config.toml`, `pc/scripts/descargar_datasets.py`, README | Instalación limpia y `pip check` sin errores; carga de `haarcascade_frontalface_default.xml` y `haarcascade_eye.xml`; `git ls-files` sin `datos/` | Probado |
| **H Pruebas de hardware** | 13-14 nov | `firmware/platformio.ini` con `test_huella_imagen`, `test_teclado`, `test_oled`, `test_servos` y `test_leds`; `pc/scripts/guardar_huella.py`; `docs/CABLEADO.md` | `pio run` compila los 5 entornos; pines iguales a la sección 4 del contexto; el script guarda PNG y `.bin` desde un flujo grabado | Compila, sin probar en placa |
| **1a Huella** | 14-17 nov | `pc/pia/huella/` (preproceso, orientación, frecuencia, Gabor, minucias, grafos), `pc/pia/calibracion.py`, pruebas y volcado de etapas | Rejilla sintética: error de orientación < 5° y de periodo < 0.5 px; esqueleto de 1 px; puntaje 1.0 contra sí misma y ≥ 0.8 contra una copia rotada y trasladada; EER en DB1_B reportado a 8 y a 4 bits, con tope de 15 %; ≤ 2 s por imagen | Probado en FVC; sin probar en AS608 |
| **1b Rostro** | 17-18 nov | `pc/pia/rostro/` (detección, alineación, fotometría, Eigenfaces) y `pc/pia/fusion.py` | Tasa de Viola-Jones en ORL (con relleno y reescalado) y en LFW, mínimo 90 % en la elegida; UᵀU = I con error < 1e-6; mismo subespacio que `np.linalg.svd`; EER con registro y prueba separados, tope de 15 %; una imagen que no es rostro se rechaza por espacio de caras | Probado en dataset; sin probar con DroidCam |
| **2 Backend y protocolo** | 18-20 nov | `orquestador.py`, `dispositivos/` (interfaz, simulado, ESP32, protocolo), `registro.py`, `bitacora.py`, `servidor.py`, `camara.py`, `pc/scripts/esp32_falso.py` y `docs/PROTOCOLO.md` | Verificación completa por consola; los 5 escenarios con sus tasas sobre 20 muestras; parser correcto con lecturas de 1 byte, CRC malo, corte a media imagen y `TECLA` intercalada; el detector de nibbles acierta en los dos órdenes; sin `PING`, el ESP32 falso niega; la base no guarda el PIN en claro | Probado contra el ESP32 falso |
| **3 App** | 20-23 nov | `app/` a partir de la maqueta: se quitan generadores y algoritmos en JS y se añade el cliente WebSocket; vista de Registro | Sin `processFinger`, `trainPCA` ni `renderFinger` en `app/`; los 5 escenarios correctos desde el backend; 0 errores de consola y 0 peticiones externas; cabe sin scroll en 1366×768 y 1920×1080; ningún cuadro pasa de 33 ms mientras procesa | Probado en Simular |
| **4 Firmware principal** | 21-24 nov (en paralelo con la 3) | `firmware/src/` (teclado, huella, OLED, actuadores, protocolo, máquina de estados); `DispositivoESP32` contra el ESP32 falso | `pio run` compila; sin `delay()` en el ciclo; sin comandos de matching del sensor; servos cerrados al arrancar y corte a los 5 s sin `PING` | Compila, sin probar en placa |
| **5 Integración y demo** | 25-28 nov | Flujo real completo, registro de las personas del equipo, recalibración con capturas del AS608 y `docs/DEMO.md` | 10 verificaciones reales seguidas sin reinicio; FAR y FRR medidos con el equipo (pocos datos, se dice); 20 ciclos de servo sin brownout | Probado con hardware solo lo que el usuario ejecute y registre |
| Colchón | 29-30 nov | Ensayo y reporte | | |

**Imprescindible para la demo:** fases 0, H, 1a, 1b y 2, la vista de verificación en vivo, el registro (aunque sea por script), la calibración por script, el firmware principal y la fase 5.

**Opcional (se recorta primero):** vistas de Calibración y Ajustes en la app, filtros de la bitácora, comparación completa con LFW si ORL pasa, sensor a 115200, video de Playwright y triangulación de Delaunay.

### Pruebas de hardware en paralelo (las hace el usuario)

| Prueba | Cuándo | Qué entrega | Dónde entra |
|---|---|---|---|
| TX del AS608 contra GND con multímetro | Ya | 3.3 V o 5 V | `CABLEADO.md`; condiciona conectar el sensor |
| Continuidad del teclado | Ya | Orden de pines | `config.h`, fase H |
| DroidCam desde Windows | Ya | URL o índice, y 20 cuadros guardados | `config.toml`; revisión de la fase 1b |
| **Imagen cruda** (SFGDemo o `test_huella_imagen`) | **A más tardar el 16 nov** | Sí o no, y 5 capturas `.bin` | Decisión de comprar un R307; orden de nibbles y perfil `[huella.as608]` en la revisión de la fase 1a |
| Sensor a 115200 y USB a 921600 | Después de la fase H | Sí o no, y tiempo medido | `config.toml`; fase 4 |
| Servos y brownout, OLED, LEDs | Después de la fase H | Ángulos y fuente necesaria | `config.h`; fase 4 |
| 8 capturas por dedo de 3 o 4 personas | Después de la fase 4 | Datos reales | Recalibración de la fase 5 |

## 6. Protocolo de verificación de Fable al final de cada fase

1. **Repositorio:** árbol limpio, un commit por fase y revisión del diff. `git ls-files` sin datasets, biometría ni base de usuarios.
2. **Reproducibilidad:** venv nuevo desde `requirements.txt` y `pip check`.
3. **Pruebas:** Fable corre `pytest` por su cuenta; no toma la salida del reporte.
4. **Métricas:** calibración con la misma semilla; EER, FAR, FRR y tasa de detección deben coincidir con lo reportado.
5. **Auditoría de métodos:** `sklearn` solo en scripts de descarga o comparación; nada de `cv2.face`, `dlib`, `face_recognition`, `torch` ni `onnx`; en el firmware, ningún comando `Match`, `Search`, `Img2Tz` ni `fingerFastSearch`.
6. **Prueba contra resultados fijos:** cambiar la muestra de un escenario legítimo por la de otra identidad debe cambiar el veredicto.
7. **Invariantes de los algoritmos** sobre casos sintéticos con respuesta conocida.
8. **Protocolo:** lecturas fragmentadas, CRC malo, los dos órdenes de nibble y corte de `PING`.
9. **App:** los 5 escenarios, consola, red, cinco resoluciones y tiempo de cuadro.
10. **Firmware:** `pio run` de todos los entornos y pines contra la tabla del contexto.
11. **Etiquetas:** cada "probado" lleva un comando y una salida que se pueden repetir; lo demás se rotula "compila, sin probar" o "sin probar".

## 7. Entorno comprobado (12 de noviembre de 2026)

- Python 3.14 en `C:\Users\PC\AppData\Local\Programs\Python\Python314` (no hay 3.13). Todas las dependencias tienen wheel para 3.14 en Windows según PyPI: numpy 2.5.4, scipy 1.18.1, opencv-python 4.14.0.94 (abi3), scikit-image 0.26.0, scikit-learn 1.9.1 (solo para descargar datasets), fastapi 0.162.5, uvicorn 0.54.0, websockets 17.4, pyserial 3.5, pytest 9.2.0 y pillow 13.0.0.
- PlatformIO Core 6.1.19 con la plataforma `espressif32` ya instalada.
- FVC2002 `DB1_B.zip` y `DB3_B.zip` responden en `bias.csr.unibo.it`.
- Sin verificar: que la URL de Olivetti responda a una descarga normal, y que el `TestClient` de FastAPI funcione con la versión de `httpx` disponible.
- pyserial acepta `socket://127.0.0.1:<puerto>`, así que el ESP32 falso no necesita un driver de puerto virtual.
