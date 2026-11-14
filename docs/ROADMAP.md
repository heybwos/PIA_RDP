# Roadmap ejecutable: del repositorio actual a la demo del martes 17

Escrito el viernes 13 de noviembre de 2026. Entrega: **martes 17 de noviembre de 2026**.

Este documento es el plan que va a ejecutar otra sesión (Claude Opus 5.5) cuando el usuario lo apruebe. Sustituye al calendario de 4 semanas de `docs/CONTEXTO_PIA_RDP.md` y a las "Fases y puntos de revisión" de `docs/PROMPT_FABLE_5_2.md`. Todo lo demás de esos dos documentos sigue vigente (métodos obligatorios, pines, restricciones duras, dirección visual), salvo las correcciones que se listan en la sección 1.4.

Convenciones:
- **Nube** = la sesión de Claude Code en la nube. **PC** = la laptop Windows del usuario.
- **Verificado** = lo comprobé hoy con un comando o leyendo el archivo. **Supuesto** = no se comprobó; lleva su forma de comprobarlo.
- Los bloques se llaman `N#` (nube) y `P#` (PC). Las horas son de Monterrey.

---

## 1. Resumen de una pantalla

### 1.1 Objetivo

El martes 17, frente al profesor: una persona teclea su ID y su PIN en el teclado físico, pone el dedo en el AS608, mira al celular con DroidCam, y la caja abre el compartimento que le toca (o enciende el LED rojo). La app en el navegador muestra cada fase con datos reales del pipeline en Python. Además, el modo Simular corre completo sin hardware, y los usuarios registrados (huellas y caras) quedan guardados en disco.

### 1.2 Ruta crítica

```
Hoy (vie)   P1 cableado y medición ──► N1 firmware de prueba de imagen ──► P2 ¿el AS608 entrega la imagen?  ◄── COMPUERTA G1
                                                                                │ sí                │ no
Vie-sáb     N2 huella en Python ─► N3 rostro ─► N4 base de datos y backend      ▼                   ▼
Sáb         N5 app conectada (Simular de punta a punta)                  P3 banco de huellas   Plan B (sección 6, R1)
Sáb-dom     N6 firmware completo + ESP32 falso ─► P4 pruebas por módulo ─► P5 primera verificación con hardware  ◄── G2
Dom         P6 registro real + N7 calibración con datos reales
Lun         N8 correcciones, P7 ensayos, N9 reporte.  18:00 se congela el código.
Mar         P8 lista previa y demo. No se toca el código.
```

Lo que está en la ruta crítica y no se puede recortar: la imagen del AS608 (G1), el pipeline de huella y rostro en Python, el protocolo serie con el firmware, el registro de usuarios reales y la calibración con datos reales. Todo lo demás tiene línea de recorte.

### 1.3 Las tres decisiones o riesgos más importantes

1. **La imagen cruda del AS608 se prueba hoy, antes que cualquier otra cosa.** Nadie la ha probado. El primer entregable de la nube (bloque N1, tope de 90 minutos) es el firmware de prueba y el script que guarda el PNG. Si falla, el plan B ya está diseñado: el modo ESP32 puede tomar la huella de un banco de imágenes mientras el resto del hardware es real, y se dice en la demo (sección 6, R1).
2. **Cuatro días no alcanzan para todo el alcance de `PROMPT_FABLE_5_2.md`.** Se recorta de entrada: las vistas Calibración y Ajustes no se hacen en la app (quedan como script y `config.toml`), el Registro empieza como script de consola y la revisión "fase por fase con visto bueno" se cambia por dos compuertas (G1 y G2). El detalle está en 1.5.
3. **La nube no llega ni a PlatformIO ni a los datasets** (verificado hoy, sección 1.6). Si el usuario no abre esos hosts en el entorno de la nube, el firmware se compila en la PC y la nube trabaja con un banco sintético exportado de la maqueta. El plan funciona de las dos formas, pero abrir los hosts ahorra horas (pregunta abierta 1).

### 1.4 Correcciones a lo ya escrito (decididas aquí, con su razón)

| # | Qué decía | Problema | Qué queda |
|---|---|---|---|
| C1 | La imagen va como `IMG:<bytes>:<crc32>`, datos, `IMG:FIN` y "se reenvía mientras llega" | El ESP32 no puede conocer el CRC antes de recibir la imagen completa. Las dos cosas a la vez son imposibles. | El CRC va al final: `IMG:<bytes>`, datos crudos, `IMG:FIN:<crc32>`. La imagen sigue llegando por partes. |
| C2 | "Al terminar una fase te detienes y esperas mi visto bueno" | Cada parada cuesta horas que no hay. | Commit y push al final de cada bloque, con resumen corto. Solo se detiene en G1 y G2. El usuario prueba en paralelo. |
| C3 | Subir el sensor a 115200 baudios | El cambio se guarda en la memoria del sensor; si algo sale mal, deja de responder a 57600 y se pierde tiempo. Ahorra unos 3 s por captura. | Se queda en 57600 (unos 6.5 s por imagen). Subirlo es lo último de la lista, solo si sobra tiempo. |
| C4 | Cinco vistas en la app | No caben. | Verificación (con bitácora) y Registro. Calibración y Ajustes, fuera de la app. |
| C5 | Simular usa solo datasets públicos | En la nube no se pueden bajar. | Se agrega un tercer banco, `sintetico`, exportado de la maqueta. Sirve para las pruebas automáticas y como respaldo. En la app se rotula como sintético. |
| C6 | `opencv-python` sin fijar versión | PyPI ya publica la 5.0.0.93. **Supuesto:** en OpenCV 5 los clasificadores Haar pudieron salir del módulo principal. | Fijar `opencv-python>=4.10,<5` salvo que la comprobación de N1 demuestre que la 5 trae `cv2.CascadeClassifier` y los XML. |

### 1.5 Qué se recorta desde hoy y qué se recorta si hay atraso

**Recortado desde hoy (no se hace):**
- Vista Calibración en la app. Queda `pc/scripts/calibrar.py`, que imprime los números y guarda las gráficas en PNG para el reporte.
- Vista Ajustes. Se edita `config.toml` a mano.
- Filtros de la bitácora.
- Comparación medida ORL contra LFW. Se usa ORL; solo si Viola-Jones detecta menos del 80 % con relleno de bordes se pasa a LFW.
- Los pendientes cosméticos de la maqueta (la `σ`, anunciar las flechas, el verde FIME oficial).
- Sensor a 115200 baudios (C3).

**Orden de sacrificio si un día se atrasa** (se corta de arriba hacia abajo):

| Orden | Se sacrifica | Lo que queda en su lugar |
|---|---|---|
| 1 | Vista Registro en la app | `pc/scripts/registrar.py` por consola (se hace primero de todos modos) |
| 2 | "Paso a paso" y velocidades con datos en vivo | Una sola velocidad |
| 3 | Vista "Completa" | Solo la vista "Por etapa", que es la que se usa en la demo |
| 4 | Animaciones intermedias de rostro (alineación animada, reconstrucción progresiva) | Se muestran las imágenes finales de cada paso, sin animar |
| 5 | Dataset real en Simular | Banco sintético rotulado |
| 6 | Entornos de prueba `test_oled` y `test_leds` separados | Un solo `test_perifericos` |
| 7 | Reporte con todas las figuras generadas | Figuras tomadas de capturas de pantalla de la app |

**Lo que no se sacrifica nunca:** los métodos obligatorios del PIA, el PIN con hash, la regla de decisión, guardar las imágenes crudas, la calibración con huellas reales y la seguridad del firmware (servos cerrados al arrancar y al perder la PC).

### 1.6 Comprobaciones de red hechas hoy desde la nube

Todas con `curl -sI` y tiempo límite de 12 s. Solo se comprobó que el host responde; no se descargó ni instaló nada.

| Destino | Resultado | Consecuencia |
|---|---|---|
| `pypi.org`, `files.pythonhosted.org` | Responde (200 / 302) | `pip install` funciona en la nube. |
| `registry.npmjs.org` | Responde (200) | Playwright y utilidades de Node disponibles. |
| `dl.platformio.org`, `api.registry.platformio.org`, `registry.platformio.org`, `dl.registry.platformio.org` | **Bloqueado**: el proxy contesta 403 a la conexión (denegado por política) | PlatformIO se puede instalar con pip, pero no puede bajar la plataforma ESP32 ni las librerías. **En la nube no se compila con PlatformIO.** |
| `downloads.arduino.cc`, `dl.espressif.com` | Bloqueado | Tampoco sirve la ruta normal de Arduino. |
| `github.com/.../releases/download/...` (probado con `arduino-cli`, el índice de `arduino-esp32` y el toolchain `xtensa-esp-elf`) | Responde (200) | **Supuesto:** se puede compilar en la nube con `arduino-cli` bajando todo de GitHub. No está probado; tope de 45 minutos (bloque N6). |
| `git ls-remote https://github.com/adafruit/Adafruit_SSD1306` | Responde | Las librerías de Arduino se pueden clonar con git. |
| `raw.githubusercontent.com` | Responde (200 con el XML de Haar de OpenCV) | Sirve para archivos sueltos. |
| `codeload.github.com`, `api.github.com` | 403 | No hay descarga de ZIP de ramas ni búsqueda por API. |
| `bias.csr.unibo.it` (FVC2002), por http y https | **Bloqueado** | FVC2002 no se baja en la nube. |
| `ndownloader.figshare.com/files/5976027` (la URL que usa `fetch_olivetti_faces`, citada de memoria del código de scikit-learn) y `figshare.com` | **Bloqueado** | Olivetti/ORL no se baja en la nube. |
| `cam-orl.co.uk`, `www.cl.cam.ac.uk` (ORL original) | Bloqueado | Igual. |
| `ndownloader.figshare.com/files/5976018` y `vis-www.cs.umass.edu` (LFW) | Bloqueado | Igual. |
| `kaggle.com`, `huggingface.co`, `zenodo.org`, `archive.org` | Bloqueado | No hay espejos por ahí. |

Otros datos comprobados:
- En la nube, `python3` es 3.13.18 y solo trae `numpy`, `pillow` y `uvicorn` de lo que hace falta. El resto se instala con pip.
- **Wheels para Python 3.14 en Windows** (leído de los metadatos de PyPI, no instalado): `numpy 2.5.4`, `scipy 1.18.1`, `scikit-image 0.26.0`, `websockets 17.4`, `pillow 13.0.0` y `pydantic-core 2.50.4` publican `cp314-win_amd64`; `opencv-python` publica `cp37-abi3-win_amd64`, que vale para 3.14; `pyserial`, `fastapi` y `uvicorn` son de Python puro. El riesgo de "no hay wheel para 3.14" baja mucho, pero sigue sin probarse una instalación real en la PC (bloque P1).

---

## 2. Calendario día por día

Cada bloque dice dónde se hace, qué archivos toca, cómo se sabe que terminó y qué se recorta. Los topes de tiempo son máximos: si un bloque llega a su tope, se aplica su recorte y se sigue.

Regla para la sesión de la nube: al terminar cada bloque, commit y push a `claude/exciting-davinci-aqy6kg` con mensaje en español, y un resumen de 5 líneas (qué se hizo, cómo se prueba, qué quedó verificado y qué no). El usuario hace `git pull` y corre su lista. La nube **no espera**: sigue con el siguiente bloque, salvo en G1 y G2.

### Viernes 13 (hoy)

#### P1. Preparar la PC y el cableado. PC, ahora mismo, sin esperar a la nube

- **Objetivo:** que cuando llegue el firmware de prueba, solo falte cargarlo.
- **Tareas:**
  1. Instalar VS Code con la extensión PlatformIO IDE y el driver del USB de la placa (CP210x o CH340, según el chip que traiga).
  2. Alimentar **solo el AS608** a 5 V y medir con el multímetro TX contra GND. Anotar el valor. Si da unos 5 V, armar el divisor (1 kΩ en serie, 2 kΩ a GND). Si da unos 3.3 V, directo.
  3. Cablear el AS608 al ESP32 por la serigrafía: Vi a 5 V, GND, TXD a GPIO16, RXD a GPIO17.
  4. Instalar DroidCam en el celular y anotar la IP y el puerto que muestra.
  5. Comprobar Python: `py -3.14 --version` y `py -3.13 --version`.
  6. Bajar los datasets a mano mientras tanto (los enlaces y carpetas están en la sección 5, lista P1).
- **Terminado cuando:** están anotados el voltaje de TX, el puerto COM de la placa, la IP de DroidCam y la versión de Python.
- **Si se atrasa:** los puntos 4 y 6 pasan al sábado. Los puntos 1 a 3 no se pueden mover.
- **Atajo opcional:** si quiere adelantarse a la nube, la librería `FPM` (brianrho) trae el ejemplo `image_to_pc` para Arduino IDE. Si lo corre y obtiene la imagen, G1 queda resuelta antes. **Supuesto:** el contexto dice que el ejemplo existe y documenta R30x y FPM10; con el AS608 no se ha probado.

#### N1. Entorno, protocolo y prueba de imagen del AS608. Nube, tope 90 minutos

- **Objetivo:** darle al usuario lo mínimo para resolver G1.
- **Tareas:**
  1. Estructura de carpetas de la sección 3, `.gitignore` (con `datos/`, `.venv/`, `.pio/`, `__pycache__/` y `config.toml`), `config.ejemplo.toml` (se copia a `config.toml` al arrancar si no existe) y `pc/requirements.txt` con versiones fijas.
  2. `docs/PROTOCOLO.md`: el contrato completo (sección 3.4). Se escribe antes que cualquiera de los dos lados.
  3. `firmware/platformio.ini` con el entorno `test_huella_imagen` y `firmware/src/pruebas/test_huella_imagen.cpp`:
     - `Serial2.setRxBufferSize(4096)` antes de `Serial2.begin(57600, SERIAL_8N1, 16, 17)`.
     - Implementar a mano los paquetes del AS608 (cabecera `EF01`, dirección `FFFFFFFF`, PID, longitud, suma): `VfyPwd` o `ReadSysPara` para saludar, `GenImg` (0x01) en ciclo hasta detectar dedo, `UpImage` (0x0A).
     - Reenviar por USB cada paquete de datos conforme llega, con el marco de C1. Imprimir antes una línea de diagnóstico con el código de confirmación de cada comando y los parámetros del sensor (tamaño de paquete, baudios).
  4. `pc/scripts/bajar_huella.py`: abre el puerto, espera el marco, verifica el CRC, guarda `datos/pruebas/huella_<hora>.bin` y **dos** PNG (nibble alto primero y nibble bajo primero), e imprime tamaño, media, desviación y cuántos bytes llegaron. Usa solo `pyserial`, `numpy` y `pillow`.
  5. `docs/CABLEADO.md` con la tabla de pines del contexto y las dos advertencias (medir TX; conectar por serigrafía).
  6. Comprobar C6: instalar `opencv-python` en la nube y ejecutar `cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').empty()`. Fijar la versión según el resultado.
  7. Probar `bajar_huella.py` contra un emisor falso (un script que manda una imagen sintética con el mismo marco por `socket://`), para que el usuario no depure el script y el sensor a la vez.
- **Terminado cuando:** hay push, el script pasa contra el emisor falso y el usuario tiene los comandos exactos de la lista P2.
- **Recorte:** si no se puede compilar en la nube (lo esperado, ver 1.6), el firmware se entrega **sin compilar** y se dice así. El usuario lo compila en P2 y pega los errores si los hay. No gastar aquí el intento con `arduino-cli`; eso es de N6.

#### P2. COMPUERTA G1: ¿el AS608 entrega la imagen? PC, en cuanto llegue N1

- **Objetivo:** un PNG de una huella real guardado en disco.
- **Tareas:** lista P2 de la sección 5.
- **Terminado cuando:** el usuario le pasa a la nube uno de estos tres resultados:
  - **G1-A:** llega la imagen completa (36,864 bytes) y uno de los dos PNG se ve como huella. Se anota cuál orden de nibbles es el bueno. Se sigue el plan.
  - **G1-B:** el sensor responde pero `UpImage` da error o llegan menos bytes. Se aplica el diagnóstico de R1 (30 minutos) antes de declarar el plan B.
  - **G1-C:** el sensor no responde. Es cableado, voltaje o baudios, no el plan B: se revisa con la lista de R1.
- **Si se atrasa:** G1 tiene que estar resuelta **el viernes en la noche**. Si a las 12:00 del sábado no hay imagen, se activa el plan B sin más discusión y se sigue intentando en paralelo.

#### N2. Pipeline de huella en Python. Nube, viernes tarde, en paralelo con P2

- **Objetivo:** de imagen en escala de grises a puntaje de matching en [0, 1], con las etapas intermedias disponibles.
- **Tareas:**
  1. **Banco sintético para pruebas:** con Playwright, abrir `docs/maqueta/acceso_biometrico.html` y exportar con `window.__pia.renderFinger(fingerParams(id), {...})` 8 identidades × 4 impresiones (256 × 288) a `pc/tests/fixtures/huellas_sinteticas/`. Son sintéticas, pesan poco y sí se suben al repositorio. Guardar el script en `pc/scripts/exportar_sinteticos.js`.
  2. `pc/pia/huella/preproceso.py`: normalización, segmentación por varianza de bloques, campo de orientación por gradientes suavizado sobre 2θ, frecuencia de crestas, banco de Gabor (con `cv2.filter2D` por orientación), binarización y `skimage.morphology.skeletonize`.
  3. `pc/pia/huella/minucias.py`: número de cruce, orientación, y limpieza (borde de la máscara, espolones, pares cercanos).
  4. `pc/pia/huella/matching.py`: grafo de k vecinos (k = 4, como la maqueta) con distancias, ángulos relativos y tipo; correspondencias locales y consolidación con alineación global. Puntaje m² / (nA · nB). La maqueta (`processFinger`, `thin`, `knn`, `matchMinutiae`, líneas 683 a 773) es la referencia que ya funciona: portar su lógica, no reinventarla.
  5. `pc/pia/huella/parametros.py`: un perfil por fuente (`sintetico`, `fvc2002`, `as608`) con tamaño de bloque, frecuencia esperada y sigma. El perfil `as608` empieza igual al sintético (misma resolución, 256 × 288) y se ajusta en N7.
  6. `pc/pia/huella/__init__.py` expone `procesar(img, perfil) -> ResultadoHuella` (con `etapas: dict[str, ndarray]`, `minucias`, `calidad`) y `comparar(a, b) -> ResultadoMatching` (con `puntaje`, `pares`).
  7. `pc/tests/test_huella.py`: misma identidad contra distinta identidad en el banco sintético; el EER se imprime.
  8. En cuanto llegue la primera imagen real de P2, pasarla por el pipeline y volcar las etapas a PNG para ver qué falla.
- **Terminado cuando:** `pytest pc/tests/test_huella.py` pasa, el EER en el banco sintético queda reportado y hay un volcado de las 7 etapas de una imagen.
- **Recorte:** frecuencia de crestas por bloque se cambia por una frecuencia fija por perfil. La triangulación de Delaunay no se intenta.

### Sábado 14

#### N3. Pipeline de rostro en Python. Nube, viernes noche o sábado temprano

- **Objetivo:** de un cuadro de cámara a distancia euclidiana y decisión, con las etapas intermedias.
- **Tareas:**
  1. `pc/pia/rostro/deteccion.py`: Viola-Jones con los Haar de OpenCV (rostro y ojos). Devuelve rectángulos reales.
  2. `pc/pia/rostro/alineacion.py`: rotar para dejar los ojos horizontales, escalar a distancia fija entre ojos y recortar a 64 × 64. **Respaldo documentado** si no hay ojos: recorte centrado del rectángulo del rostro con proporciones fijas; el resultado lo marca como `alineacion: "respaldo"`.
  3. `pc/pia/rostro/normalizacion.py`: CLAHE y máscara elíptica; histogramas de antes y después.
  4. `pc/pia/rostro/eigenfaces.py`: PCA con NumPy (centrado, truco de AᵀA, k por varianza del 95 %), proyección, reconstrucción con 1…k componentes y distancia al espacio de caras. Sin scikit-learn.
  5. `pc/pia/rostro/__init__.py` expone `procesar(cuadro) -> ResultadoRostro` y `comparar(pesos, vectores_usuario, umbral)`.
  6. Datos para probar en la nube, en este orden: (a) el dataset real si el usuario abrió los hosts; (b) clonar con git un espejo público de ORL en GitHub, comprobando que sean 400 imágenes de 92 × 112; (c) `skimage.data.astronaut()` para una prueba de humo de Viola-Jones y `skimage.data.lfw_subset()` para las pruebas de PCA. **Supuesto:** que esos dos vienen dentro del wheel de scikit-image; si piden descarga, usar caras sintéticas exportadas de la maqueta con `renderCamera`.
  7. `pc/scripts/descargar_datasets.py`: baja FVC2002 (DB1_B a DB4_B) y ORL a `datos/datasets/`; si falla, imprime la URL y la carpeta exacta donde dejar el ZIP a mano. Se prueba de verdad en la PC.
  8. `pc/tests/test_rostro.py`.
- **Terminado cuando:** las pruebas pasan y está medida la tasa de detección de Viola-Jones sobre el dataset que se haya conseguido (o queda escrito que no se pudo medir en la nube y se mide en P3).
- **Recorte:** LFW no se toca. Si ORL no se consigue en la nube, la medición se hace en la PC con un script de una línea.

#### N4. Base de datos, registro, orquestador y backend. Nube, sábado mañana

- **Objetivo:** una verificación simulada completa desde la consola, guardada en la bitácora.
- **Tareas:**
  1. `pc/pia/almacen.py`: esquema de la sección 4, alta, baja y consulta. `pc/pia/pin.py`: PBKDF2.
  2. `pc/pia/registro.py`: alta de usuario con N capturas; guarda crudo, procesa, guarda plantilla y vector; reentrena Eigenfaces del dominio afectado.
  3. `pc/pia/fusion.py`: normalización con los umbrales de la calibración activa y la regla (cada factor ≥ 0.50, fusión ≥ 0.60).
  4. `pc/pia/dispositivos/base.py` (interfaz `Dispositivo`) y `simulado.py` (teclas del escenario, huella del banco entregada por partes al ritmo de 57600 baudios, caja virtual).
  5. `pc/pia/camara.py`: tres fuentes detrás de una interfaz: `dataset`, `url` (DroidCam) e `indice`. Para `url`, primero `cv2.VideoCapture`; si no abre, un lector MJPEG propio con `urllib` (multipart, unas 30 líneas). Error claro si no responde; nunca imagen de relleno.
  6. `pc/herramientas/droidcam_falso.py`: servidor que publica `/video` en MJPEG con caras del banco, para probar `camara.py` en la nube.
  7. `pc/pia/orquestador.py`: máquina de estados asíncrona que emite los eventos de `docs/EVENTOS.md` (sección 3.3). Escribir ese documento primero.
  8. `pc/pia/servidor.py`: FastAPI, WebSocket `/ws`, estáticos de `app/`. `pc/pia/__main__.py` para arrancar con `python -m pia`.
  9. `pc/scripts/sembrar_simular.py`: registra los usuarios de prueba 07 (nivel 1) y 12 (nivel 2) con identidades del banco y deja listos los cinco escenarios.
  10. `pc/scripts/verificar_consola.py --escenario l1`: corre una verificación y la imprime.
  11. `pc/scripts/registrar.py`: registro por consola (sirve para Simular y para ESP32).
  12. `pc/scripts/respaldo.py`: crear, restaurar y borrar (sección 4.6).
- **Terminado cuando:** los cinco escenarios dan por consola el resultado esperado de `ESTADO_DEL_PROYECTO.md` (dos concedidos, tres negados), hay 5 filas en la bitácora y `pytest` pasa.
- **Recorte:** el respaldo se reduce a "copiar la carpeta `datos/`", documentado.

#### N5. La app conectada al backend, en modo Simular. Nube, sábado tarde

- **Objetivo:** el modo Simular de punta a punta en el navegador, con los datos que manda Python.
- **Tareas:** las de la sección 3.2 (cómo se reutiliza la maqueta). En resumen: copiar la maqueta a `app/`, separar CSS y JS, borrar generadores y algoritmos del JS, y cambiar `run()` por un consumidor de eventos del WebSocket. Agregar el interruptor "Rostro: Dataset | DroidCam" junto al selector de escenario y la etiqueta de banco (FVC2002, ORL o sintético). Agregar el parámetro `?sinvidrio=1`, que quita todo `backdrop-filter` (respaldo de rendimiento para la laptop de la demo).
- **Prueba:** `app/pruebas/regresion.js`, adaptada de `docs/maqueta/pruebas/regresion.js`: levanta el servidor, corre los cinco escenarios y revisa el veredicto, cero errores de consola y cero peticiones fuera de `localhost`. Capturas a 1440 × 900 de las cuatro etapas.
- **Terminado cuando:** la regresión pasa en la nube y hay capturas.
- **Recorte:** en este orden, los puntos 2, 3 y 4 de la tabla de 1.5.

#### N6. Firmware completo, `DispositivoESP32` y ESP32 falso. Nube, sábado tarde y noche (puede ir en paralelo con N5)

- **Objetivo:** el modo ESP32 de punta a punta contra un ESP32 falso, y el firmware listo para cargar.
- **Tareas:**
  1. `firmware/src/`: `main.cpp` (máquina de estados sin `delay()`), `protocolo.*`, `teclado.*`, `huella.*` (lo de N1, convertido en módulo), `pantalla.*`, `actuadores.*`, `pines.h`, `config.h`.
  2. Entornos de prueba en `platformio.ini`: `test_teclado`, `test_oled`, `test_leds`, `test_servos` (uno a la vez; imprime el motivo del último reinicio con `esp_reset_reason()` para delatar un brownout) y el `test_huella_imagen` de N1. **Estos cuatro se entregan primero**, para que el usuario empiece P4 mientras se termina el firmware principal.
  3. Seguridad: servos a cerrado en `setup()`; sin `PING` en 5 s, LED rojo, OLED "Sin conexion con la PC" y nada se abre; tiempo límite por fase; después de abrir, cierre automático tras `t_abierto` (configurable desde la PC al conectar).
  4. `pc/pia/dispositivos/esp32.py`: abre el puerto con `serial.serial_for_url(...)`, así el mismo código acepta `COM5` y `socket://127.0.0.1:5333`. Lector que alterna entre modo línea y modo binario de tamaño exacto. `PING` cada segundo.
  5. `pc/herramientas/esp32_falso.py`: servidor TCP que habla el protocolo completo: `HOLA`, teclas según un guion, imagen por partes al ritmo de 57600 baudios, responde a `MSG`, `ACCESO` y `PING`. Con opciones para inyectar fallas: CRC malo, corte a media imagen, silencio, tecla `D`.
  6. `pc/tests/test_protocolo.py`: verificación completa contra el ESP32 falso, más los cuatro casos de falla.
  7. Botón "Buscar ESP32" de la app conectado de verdad: lista los puertos (`serial.tools.list_ports`), intenta el saludo y muestra versión, sensor y OLED.
  8. **Compilación en la nube, tope 45 minutos:** intentar con `arduino-cli` bajado de GitHub Releases, el núcleo ESP32 desde su índice en GitHub y las librerías clonadas con git. Si funciona, dejar `firmware/compilar_nube.sh`. Si no, se declara "sin compilar en la nube" y se compila en la PC.
- **Terminado cuando:** `test_protocolo.py` pasa; en la app, el modo ESP32 apuntando al ESP32 falso completa una verificación; el firmware está entregado, compilado o marcado como no compilado.
- **Recorte:** punto 6 de la tabla de 1.5. La inyección de fallas se queda en dos casos (CRC malo y silencio).

#### P3. Banco de huellas reales y DroidCam. PC, sábado tarde (necesita G1-A)

- **Objetivo:** tener imágenes reales para ajustar y calibrar, y saber que la cámara se lee.
- **Tareas:** lista P3 de la sección 5: instalar el entorno de Python, leer DroidCam con el script de prueba, bajar los datasets con el script y capturar el banco de huellas (sección 4.5).
- **Terminado cuando:** existe `datos/banco_as608/` con al menos 6 identidades × 8 capturas, y `probar_camara.py` muestra el rostro detectado.
- **Si se atrasa:** el banco mínimo son 4 dedos del propio usuario × 6 capturas (cada dedo cuenta como una identidad distinta). Menos que eso no permite calibrar.

#### P4. Pruebas por módulo del hardware. PC, sábado tarde o noche

- **Objetivo:** confirmar teclado, OLED, LEDs y servos uno por uno, antes de integrarlos.
- **Tareas:** lista P4 de la sección 5.
- **Terminado cuando:** cada entorno de prueba da su resultado esperado, o el usuario reporta cuál falla y con qué mensaje.
- **Si se atrasa:** se prueban solo teclado y servos (son los que traen sorpresas: orden de pines y brownout). OLED y LEDs se ven directo en la integración.

### Domingo 15

#### P5. COMPUERTA G2: primera verificación con hardware real. PC, domingo antes de las 14:00

- **Objetivo:** un flujo completo con el firmware principal, aunque los umbrales todavía sean provisionales.
- **Tareas:** lista P5.
- **Terminado cuando:** ID y PIN en el teclado físico aparecen en la app, la huella se dibuja por partes, se captura el rostro, llega una decisión, y el LED y los servos responden. No importa todavía si la decisión es correcta.
- **Si a las 14:00 no se cumple:** la nube deja todo lo demás y atiende solo esto, con los registros del puerto que mande el usuario (`pc/scripts/monitor_serie.py` los guarda en un archivo). Si a las 20:00 sigue sin salir, se pasa al modo degradado D1 (sección 6, R9).

#### P6 y N7. Registro real y calibración con datos reales. PC y nube, domingo tarde

- **Objetivo:** umbrales propios del AS608 y de la cámara con la luz real, y los usuarios de la demo registrados.
- **Tareas:**
  1. (Nube) Ajustar el perfil `as608` de `parametros.py` con las imágenes reales: tamaño de bloque, frecuencia, sigma de Gabor, umbral de segmentación. Si el usuario no puede pasar imágenes a la nube (pregunta abierta 3), la nube entrega `pc/scripts/explorar_parametros.py`, que prueba una rejilla de valores en la PC y reporta el mejor EER.
  2. (PC) `python pc/scripts/calibrar.py --factor huella --dominio as608 --banco datos/banco_as608`: pares genuinos e impostores, curvas FAR y FRR, EER, umbral propuesto y PNG en `datos/calibracion/`.
  3. (PC) Registrar a los usuarios de la demo con `registrar.py` o con la vista Registro (sección 4.5).
  4. (PC) `python pc/scripts/calibrar.py --factor rostro --dominio camara`: genuinos de los registrados (dos tandas, con minutos de diferencia) contra impostores (los demás registrados y las caras del dataset pasadas por el mismo pipeline).
  5. (PC) Activar la calibración (`--activar`) y hacer 10 intentos genuinos y 10 de impostor por persona. Anotar aciertos.
- **Terminado cuando:** hay una calibración activa por factor para los dominios `as608` y `camara`, y en la tanda de 20 intentos no pasa ningún impostor. Se acepta un rechazo falso de hasta 2 de cada 10 (se reintenta en la demo).
- **Recorte:** si el EER de huella con el AS608 sale mayor de 15 %, no se sigue afinando el algoritmo: se suben las capturas de registro a 5, se usa el máximo de los puntajes contra todas las plantillas y se elige el umbral con FAR = 0 en el banco, aceptando más rechazos falsos. Se reporta el número tal cual.

#### N8a. Vista Registro en la app. Nube, domingo, solo si G2 se cumplió a tiempo

- **Objetivo:** registrar desde el navegador: ID, nombre, nivel, PIN; contador de capturas de huella; vista previa de la cámara y captura de 15 cuadros; resumen de calidad.
- **Terminado cuando:** un registro completo en Simular pasa en Playwright y deja las mismas filas y archivos que `registrar.py`.
- **Recorte:** es el primer punto de la tabla de 1.5. Si G2 se atrasó, este bloque no se hace.

### Lunes 16

#### N8. Correcciones de integración y robustez. Nube, lunes mañana

- **Objetivo:** que la demo aguante errores humanos.
- **Tareas:** arreglar lo que salió en P5 y P6. Casos que se tienen que ver bien en la OLED y en la app: dedo mal puesto (reintento sin reiniciar todo), sin rostro en el cuadro (reintento con mensaje), cámara caída, cable desconectado y reconectado, tecla `D`. `docs/DEMO.md`: guion de 5 minutos, lista previa y solución de problemas (brownout, COM ocupado, DroidCam sin conexión, huella con ruido).
- **Terminado cuando:** cada caso está probado contra el ESP32 falso y el usuario los repite una vez con hardware.
- **Recorte:** los reintentos se cambian por "se niega el acceso y se vuelve a empezar".

#### P7. Ensayos de la demo. PC, lunes tarde

- **Objetivo:** tres ensayos completos, seguidos, sin tocar el código, con la laptop, el celular y la red que se van a usar el martes.
- **Tareas:** lista P7. Incluye medir los cuadros por segundo de las transiciones en la laptop y decidir si se desactiva el vidrio.
- **Terminado cuando:** tres ensayos seguidos salen bien y hay un respaldo de `datos/` en una USB.
- **Regla:** **a las 18:00 del lunes se congela el código.** Después solo se aceptan cambios en `config.toml` y en documentos.

#### N9. Reporte técnico. Nube, lunes (en paralelo con N8 y P7)

- **Objetivo:** que el reporte se arme con resultados reales y no a última hora.
- **Tareas:**
  1. `pc/scripts/figuras_reporte.py`: genera en `docs/reporte/figuras/` las etapas de huella y de rostro, las eigenfaces, la reconstrucción, y las curvas FAR/FRR con datos sintéticos o de dataset. Las figuras con datos reales las genera el usuario en su PC con el mismo script (`--banco datos/banco_as608`), porque los datos biométricos no salen de su máquina.
  2. `docs/reporte/borrador.md`: una sección por fase del PIA (captura, preprocesamiento, extracción, matching, actuación), más arquitectura, protocolo, base de datos, calibración con los números reales, resultados (FAR, FRR, EER), limitaciones y conclusiones. Cada afirmación de desempeño cita el número medido.
  3. El usuario lo pasa a su plantilla (portada UANL-FIME) y completa lo que es del equipo.
- **Terminado cuando:** existe el borrador completo con los huecos marcados `[DATO REAL: ...]` donde falta un número de la PC.
- **Recorte:** punto 7 de la tabla de 1.5.
- **Nota:** el esqueleto del reporte se puede adelantar el sábado o domingo en cualquier rato en que la nube esté esperando al usuario. No dejarlo todo para el lunes.

### Martes 17

#### P8. Día de la entrega. PC

- Sin cambios de código.
- Lista previa P8 (sección 5), una hora antes.
- Llevar: respaldo en USB, cargador de 5 V y 2 A por si hay brownout, cable USB de repuesto, y el plan de red de R6.

---

## 3. Arquitectura y estructura de carpetas

### 3.1 Estructura final

```
firmware/
  platformio.ini            Entorno principal y entornos de prueba; librerías con versión fija
  src/
    main.cpp                Máquina de estados
    protocolo.{h,cpp}       Líneas, marco de imagen, PING
    teclado.{h,cpp}  huella.{h,cpp}  pantalla.{h,cpp}  actuadores.{h,cpp}
    pines.h  config.h
    pruebas/                test_huella_imagen.cpp, test_teclado.cpp, test_oled.cpp, test_leds.cpp, test_servos.cpp
  compilar_nube.sh          Solo si el intento con arduino-cli funciona
pc/
  requirements.txt
  pia/
    __main__.py             python -m pia
    config.py               Lee config.toml con tomllib
    huella/                 preproceso.py, minucias.py, matching.py, parametros.py
    rostro/                 deteccion.py, alineacion.py, normalizacion.py, eigenfaces.py
    fusion.py  pin.py
    almacen.py              SQLite y archivos
    registro.py  calibracion.py
    camara.py
    dispositivos/           base.py, simulado.py, esp32.py
    orquestador.py  servidor.py
  herramientas/             esp32_falso.py, droidcam_falso.py
  scripts/                  bajar_huella.py, capturar_banco.py, probar_camara.py, descargar_datasets.py,
                            sembrar_simular.py, registrar.py, verificar_consola.py, calibrar.py,
                            explorar_parametros.py, respaldo.py, monitor_serie.py, figuras_reporte.py,
                            exportar_sinteticos.js
  tests/                    pytest; fixtures/ con el banco sintético
app/
  index.html
  css/estilos.css           El <style> de la maqueta, tal cual
  js/                       principal.js, conexion.js, cola.js, dibujo_huella.js, dibujo_rostro.js,
                            panel_frontal.js, etapas.js, registro.js, iconos.js, util.js
  fonts/  icons/            Copiados de docs/maqueta/
  pruebas/regresion.js
datos/                      Ignorado por git (sección 4.1)
config.ejemplo.toml         En git. config.toml es la copia local, ignorada por git
docs/                       Lo que ya hay, más PROTOCOLO.md, EVENTOS.md, CABLEADO.md, DEMO.md, reporte/
```

`firmware/` y `pc/` no se importan entre sí. Lo único que comparten es `docs/PROTOCOLO.md`.

### 3.2 Cómo se reutiliza la maqueta

`docs/maqueta/acceso_biometrico.html` tiene 1,534 líneas: CSS de la 8 a la 427, HTML de la 429 a la 613 y un solo `<script>` de la 615 a la 1532. **La maqueta no se modifica**: se copia a `app/` y se trabaja sobre la copia. Queda en `docs/` como referencia visual y como fuente del banco sintético.

| Parte de la maqueta | Líneas | Destino | Qué se hace |
|---|---|---|---|
| Tokens, componentes, vidrio, transiciones (CSS) | 8–427 | `app/css/estilos.css` | Se copia tal cual. Solo se cambian las rutas de las fuentes. |
| Barra, navegador de etapas, controles, los cinco paneles (HTML) | 429–613 | `app/index.html` | Se copia. Se agregan el interruptor de rostro, la etiqueta de banco y el acceso a Registro. |
| Utilidades (`clamp`, `fmt`, `crc32`, ángulos) | 617–638 | `js/util.js` | Se reutiliza. |
| **Generador de huellas** (`fingerParams`, `renderFinger`) | 640–673 | — | **Se elimina** de la app. Sigue en la maqueta para exportar el banco sintético. |
| **Algoritmos de huella** (`GAB_K`, `processFinger`, `thin`, `knn`, `matchMinutiae`) | 675–773 | — | **Se elimina.** Se porta a Python en N2. |
| Iconos (`IC`, `ic`) | 775–790 | `js/iconos.js` | Se reutiliza. |
| **Generador de caras y PCA** (`faceParams` … `renderCamera`, `normalizeFace`, `jacobi`, `trainPCA`) | 792–894 | — | **Se elimina.** Se porta a Python en N3. |
| Colores de estado, `est()` | 896–919 | `js/util.js` | Se reutiliza. |
| Dibujo de huella (`stageCanvases`, `drawMinutia`, `drawStage`, `STAGES`) | 921–973 | `js/dibujo_huella.js` | Se reutiliza. Hoy lee un objeto `F` calculado en el navegador; pasa a leer el mismo objeto armado con lo que manda el backend. Las constantes `FW` y `FH` dejan de ser fijas: el tamaño viene en el evento (FVC2002 no mide 256 × 288). |
| `USERS`, `SCN`, estado `S` | 975–990 | — | `USERS` y `SCN` **se eliminan**: los usuarios y escenarios los manda el backend al conectar. `S` se queda sin los campos de algoritmo. |
| Ritmo (`wait`, `anim`, `caption`, `beat`) | 992–1009 | `js/cola.js` | Se reutiliza como base de la cola de eventos. |
| Navegador de etapas y transiciones (`pintarNav`, `transicion`, `mostrarEtapa`, `etapaFlujo`, `navUsuario`, `setVista`) | 1011–1118 | `js/etapas.js` | Se reutiliza tal cual. Es la parte más probada de la maqueta. |
| Teclado, OLED, LEDs, monitor serie, casillas, caja SVG, servos | 1120–1187 | `js/panel_frontal.js` | Se reutiliza. Las teclas, en lugar de llamar a `manualKey`, mandan `{tipo:"tecla"}` al backend. |
| Dibujo de rostro (`drawGray`, `camDraw`, `histSVG`, `weightsSVG`, `distSVG`, `drawOverlay`) | 1189–1246 | `js/dibujo_rostro.js` | Se reutiliza. `camDraw` dibuja el cuadro real y los rectángulos reales de Viola-Jones; se quita la nota de "posición conocida del generador". |
| `resetUI`, `verdict`, `logRow` | 1248–1278 | `js/principal.js` | Se reutiliza. |
| **`run()`**: el orquestador | 1280–1452 | `js/principal.js` | **Se reemplaza.** Ver abajo. |
| `manualKey`, botones, `setMode`, "Buscar ESP32" | 1454–1512 | `js/principal.js` | Se reescribe sobre mensajes al backend. El texto y los estados del panel ESP32 se conservan. |
| `boot()` | 1514–1531 | `js/principal.js` | Se reemplaza: conecta el WebSocket, pide el estado y, si hay una verificación previa en la bitácora, la muestra resuelta. |

**Cómo se reemplaza `run()`.** Hoy `run()` calcula y anima en la misma función. Se parte en dos:
- El **cálculo** se va al orquestador de Python, que emite eventos en el mismo orden que los pasos de `run()`.
- La **animación** se queda: cada bloque de `run()` (el barrido de la huella, `stageAnim`, las minucias escalonadas, el matching, la cámara, la alineación, las eigenfaces, la reconstrucción, la fusión, el veredicto) se convierte en una función `alRecibir_<evento>(datos)` que conserva sus duraciones y sus textos de pie. `js/cola.js` las ejecuta en orden: el backend manda rápido y la cola anima a su ritmo; si la cola pasa de cierto tamaño, las animaciones restantes se acortan (la animación nunca frena al pipeline).

**Formato de las imágenes.** Para que `drawStage` no cambie, las etapas llegan como arreglos, no como PNG: cada evento JSON lleva `ancho`, `alto`, `tipo` (`u8` o `f32`) y `datos` en base64. Una huella de 256 × 288 en `u8` son unos 98 kB en base64; por `localhost` no es problema. La orientación llega como arreglo por bloque y las minucias como lista de `{x, y, t, tipo}`. La imagen cruda de la huella llega en eventos `huella_filas` (un bloque de filas cada uno) para dibujar el barrido real.

**Prohibido en la app:** calcular algo del reconocimiento en JavaScript. Si un valor aparece en pantalla, vino del backend.

### 3.3 Eventos entre backend y app (`docs/EVENTOS.md`)

Lista de partida; el orquestador la fija en N4 antes de programar.

- **Backend a app:** `estado` (modo, conexión, usuarios, escenarios, bancos, calibración activa), `etapa`, `tecla`, `casillas`, `oled`, `serie`, `leds`, `huella_inicio`, `huella_filas`, `huella_fin`, `huella_etapa` (segmentación, orientación, Gabor, binaria, esqueleto), `huella_minucias`, `huella_matching`, `rostro_cuadro`, `rostro_deteccion`, `rostro_alineado`, `rostro_normalizado`, `rostro_pca` (media y primeras eigenfaces, una vez por modelo), `rostro_pesos`, `rostro_reconstruccion`, `rostro_distancia`, `fusion`, `veredicto`, `servo`, `bitacora_fila`, `error` (con `que_revisar`).
- **App a backend:** `iniciar` (escenario, fuente de rostro), `tecla`, `cancelar`, `modo`, `buscar_puertos`, `conectar`, y los del registro (`registro_iniciar`, `registro_capturar_huella`, `registro_capturar_rostro`, `registro_guardar`, `usuario_borrar`).

### 3.4 Protocolo serie (`docs/PROTOCOLO.md`)

Es el del prompt principal, con la corrección C1 y lo que le faltaba para ser implementable.

- USB a 921600 baudios, configurable; respaldo en 115200. Líneas de texto terminadas en `\n`, de 64 caracteres como máximo.
- **ESP32 a PC:**
  - `HOLA:<versión>:<sensor OK|ERR>:<oled OK|ERR>` al arrancar y como respuesta a `RESET`.
  - `TECLA:<c>` en cuanto se presiona.
  - `PIN:<id>:<pin>` al cerrar con `#`. El firmware arma ID y PIN (`*` borra, `D` manda `CANCELA`).
  - `HUELLA:ESPERA`, `HUELLA:DEDO` y `HUELLA:ERR:<código>` (sin dedo en el tiempo límite, error del sensor con su código de confirmación).
  - `IMG:<bytes>` seguido de exactamente `<bytes>` bytes crudos y luego `IMG:FIN:<crc32 en hex>`.
  - `PONG`, `OK:<comando>`, `ERR:<motivo>`.
- **PC a ESP32:** `MSG:<línea1>|<línea2>` (sin acentos), `PEDIR_PIN`, `PEDIR_HUELLA`, `ACCESO:0|1|2`, `CONFIG:<clave>:<valor>` (tiempos de servo y de fase), `RESET`, `PING`.
- **Imagen:** 256 × 288, 4 bits por píxel, 36,864 bytes; cada byte lleva dos píxeles. El orden de nibbles se decide en la PC (`config.toml`, `huella.nibble_alto_primero`), con el resultado de G1. El ESP32 no toca los datos.
- **Lectura en la PC:** tras la línea `IMG:<bytes>`, el lector pasa a modo binario, lee el número exacto de bytes con tiempo límite por bloque, y vuelve a modo línea. Si se corta, descarta, pide `RESET` y lo reporta.
- **Vida:** `PING` de la PC cada segundo. Sin `PING` por 5 s (fuera de una transferencia de imagen), el ESP32 pasa a estado seguro.
- **Supuesto a confirmar en P2:** que el AS608 manda los datos en paquetes de 128 bytes y que el último paquete lleva PID `0x08`. El firmware no debe depender del tamaño: lee la longitud de cada cabecera.

### 3.5 Los dos modos y sus fuentes

| | Simular | ESP32 |
|---|---|---|
| Teclado | En pantalla | Físico (se refleja en pantalla) |
| Huella | Banco: FVC2002 o sintético. Llega por partes al ritmo de 57600 baudios, rotulada como simulada | AS608 real. Con el plan B: banco, rotulado |
| Rostro | Dataset (por defecto) **o DroidCam en vivo**, con el interruptor | DroidCam |
| OLED, LEDs, caja | Réplicas en pantalla | Reales, y las réplicas reflejan lo mismo |
| Umbrales | Calibración del dominio de cada fuente | Calibración `as608` y `camara` |

`config.toml` (valores de ejemplo):

```toml
[serie]
puerto = "auto"            # "COM5", "auto" o "socket://127.0.0.1:5333" (ESP32 falso)
baudios = 921600

[huella]
fuente_esp32 = "sensor"    # "sensor" o "banco" (plan B)
nibble_alto_primero = true
banco_simular = "fvc2002"  # "fvc2002" o "sintetico"

[camara]
fuente = "url"             # "url", "indice" o "dataset"
url = "http://192.168.1.50:4747/video"
indice = 1
rostro_simular = "dataset" # "dataset" o "camara"

[decision]
peso_huella = 0.5
peso_rostro = 0.5
umbral_factor = 0.50
umbral_fusion = 0.60

[registro]
capturas_huella = 5
cuadros_rostro = 15

[actuadores]
ms_entre_servos = 300
ms_abierto = 8000

[datos]
carpeta = "datos"
guardar_intentos = true
```

---

## 4. Diseño de la base de datos de huellas y caras

### 4.1 Carpetas

Todo vive en `datos/`, ignorado por git. Nada biométrico entra al repositorio.

```
datos/
  pia.db                              SQLite: usuarios, plantillas, vectores, calibraciones, bitácora
  usuarios/<id>/
    huellas/<fuente>_<nn>.png         Imagen cruda, 8 bits, sin pérdida
    rostros/<fuente>_<nn>.png         Cuadro crudo completo de la cámara o del dataset
    rostros/alineados/<fuente>_<nn>.png   Rostro alineado y normalizado, 64 × 64 (se puede regenerar)
  modelos/eigenfaces_<dominio>_<fecha>.npz   Cara media, eigenfaces, valores propios
  banco_as608/<identidad>/<nn>.png    Capturas para calibrar (no son usuarios)
  intentos/<fecha>/<hora>_<id>_huella.png, _rostro.png   Lo capturado en cada verificación
  calibracion/                        Gráficas y CSV de puntajes
  datasets/fvc2002/, datasets/orl/    Descargados
  pruebas/                            Salidas de bajar_huella.py
  respaldos/pia_<fecha>.zip
```

`<fuente>` es `as608`, `fvc2002` o `sintetico` para huella, y `camara`, `orl` o `sintetico` para rostro.

### 4.2 Qué se guarda crudo y qué procesado

| Dato | Crudo | Procesado | Por qué |
|---|---|---|---|
| Huella | PNG de 8 bits (los 4 bits del sensor multiplicados por 17), ya con el orden de nibbles correcto | Plantilla de minucias en la base | El crudo permite **volver a extraer** las plantillas cuando cambien los parámetros de Gabor o de limpieza al calibrar con el AS608. Sin crudo, cada ajuste obligaría a registrar a todos otra vez. |
| Rostro | Cuadro completo en PNG | Rostro alineado (archivo) y vector de pesos (base) | El vector depende del modelo de Eigenfaces. Cada alta **reentrena** el modelo, y hay que volver a proyectar a todos desde sus imágenes. |
| Intentos | Huella y cuadro de cada verificación (si `guardar_intentos` está activo) | Puntajes en la bitácora | Sirven para recalibrar con intentos reales y como evidencia para el reporte. Se apaga en `config.toml` si no se quiere guardar. |

Las plantillas y los vectores son **caché**: se pueden borrar y regenerar con `python pc/scripts/respaldo.py reprocesar`. Las imágenes crudas son la fuente de verdad.

### 4.3 Esquema SQLite

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);   -- version_esquema, version_algoritmo

CREATE TABLE usuarios (
  id         TEXT PRIMARY KEY CHECK (length(id) = 2),              -- "07"
  nombre     TEXT NOT NULL,
  nivel      INTEGER NOT NULL CHECK (nivel IN (1, 2)),
  pin_hash   BLOB NOT NULL,                                        -- PBKDF2-HMAC-SHA256, 32 bytes
  pin_sal    BLOB NOT NULL,                                        -- 16 bytes de os.urandom
  pin_iter   INTEGER NOT NULL,                                     -- 200000
  activo     INTEGER NOT NULL DEFAULT 1,
  creado_en  TEXT NOT NULL
);

CREATE TABLE muestras_huella (
  id          INTEGER PRIMARY KEY,
  usuario_id  TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  fuente      TEXT NOT NULL,                                       -- as608 | fvc2002 | sintetico
  archivo     TEXT NOT NULL,                                       -- ruta relativa a datos/
  ancho INTEGER NOT NULL, alto INTEGER NOT NULL,
  creada_en   TEXT NOT NULL
);

CREATE TABLE plantillas_huella (
  muestra_id        INTEGER PRIMARY KEY REFERENCES muestras_huella(id) ON DELETE CASCADE,
  version_algoritmo TEXT NOT NULL,
  perfil            TEXT NOT NULL,                                 -- perfil de parametros.py usado
  n_minucias        INTEGER NOT NULL,
  minucias          BLOB NOT NULL,                                 -- float32, N × 4: x, y, ángulo, tipo
  calidad           REAL NOT NULL,                                 -- fracción de primer plano
  creada_en         TEXT NOT NULL
);

CREATE TABLE muestras_rostro (
  id          INTEGER PRIMARY KEY,
  usuario_id  TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  fuente      TEXT NOT NULL,                                       -- camara | orl | sintetico
  archivo     TEXT NOT NULL,
  archivo_alineado TEXT NOT NULL,
  deteccion   TEXT NOT NULL,                                       -- JSON: rectángulo, ojos, alineacion normal|respaldo
  creada_en   TEXT NOT NULL
);

CREATE TABLE modelos_rostro (
  id        INTEGER PRIMARY KEY,
  dominio   TEXT NOT NULL,                                         -- camara | dataset
  archivo   TEXT NOT NULL,                                         -- .npz
  k INTEGER NOT NULL, varianza REAL NOT NULL, n_entrenamiento INTEGER NOT NULL,
  activo    INTEGER NOT NULL DEFAULT 0,
  creado_en TEXT NOT NULL
);

CREATE TABLE vectores_rostro (
  muestra_id INTEGER NOT NULL REFERENCES muestras_rostro(id) ON DELETE CASCADE,
  modelo_id  INTEGER NOT NULL REFERENCES modelos_rostro(id) ON DELETE CASCADE,
  pesos      BLOB NOT NULL,                                        -- float32, k valores
  PRIMARY KEY (muestra_id, modelo_id)
);

CREATE TABLE calibraciones (
  id INTEGER PRIMARY KEY,
  factor  TEXT NOT NULL,                                           -- huella | rostro
  dominio TEXT NOT NULL,                                           -- as608 | fvc2002 | sintetico | camara | dataset
  umbral REAL NOT NULL, eer REAL, far REAL, frr REAL,
  n_genuinos INTEGER, n_impostores INTEGER,
  modelo_id INTEGER REFERENCES modelos_rostro(id),                 -- solo rostro
  parametros TEXT,                                                 -- JSON: perfil y versión usados
  activa INTEGER NOT NULL DEFAULT 0,
  creada_en TEXT NOT NULL
);

CREATE TABLE bitacora (
  id INTEGER PRIMARY KEY,
  fecha TEXT NOT NULL,
  modo  TEXT NOT NULL,                                             -- simular | esp32
  usuario_id TEXT, nombre TEXT,                                    -- copia; sin llave foránea, para que sobreviva al borrado
  pin_ok INTEGER NOT NULL,
  fuente_huella TEXT, fuente_rostro TEXT,
  puntaje_huella REAL, huella_norm REAL,
  distancia_rostro REAL, rostro_norm REAL,
  fusion REAL,
  decision INTEGER NOT NULL,                                       -- 0 negado, 1 o 2 nivel concedido
  motivo TEXT,
  duracion_ms INTEGER,
  archivo_huella TEXT, archivo_rostro TEXT
);
CREATE INDEX bitacora_fecha ON bitacora(fecha);
```

Notas de diseño:
- **Una sola base y la fuente en cada muestra**, en lugar de dos bases (una para Simular y otra para lo real). Así un usuario puede tener huella de dataset y rostro de cámara, que es justo lo que pide el interruptor de rostro en Simular. Un usuario se puede verificar en un modo si tiene muestras de las fuentes que ese modo usa.
- **Umbrales por dominio.** La verificación toma la calibración activa del dominio de donde vino la captura. Así los umbrales de FVC2002 nunca se aplican a una huella del AS608.
- **Un modelo de Eigenfaces por dominio** (`dataset` y `camara`). El de `camara` se entrena con las caras de cámara de todos los registrados **más** un fondo de caras del dataset pasadas por el mismo pipeline. Sin ese fondo, con 3 o 4 personas el subespacio sale tan pequeño que la distancia no discrimina. Es una decisión de diseño; su efecto real se mide en N7.
- **El PIN:** `hashlib.pbkdf2_hmac('sha256', pin, sal, 200000)` y comparación con `hmac.compare_digest`. Un PIN de 4 dígitos tiene 10,000 combinaciones: el hash evita guardarlo en claro, no lo vuelve fuerte. Decirlo así en el reporte.
- **Comparación:** huella = el puntaje máximo contra las plantillas del usuario. Rostro = la distancia mínima contra los vectores del usuario en el modelo activo.

### 4.4 Qué pasa al registrar

1. Se valida que el ID no exista y se guarda el usuario con el PIN ya en hash.
2. Por cada captura de huella: se guarda el crudo, se procesa y se guarda la plantilla. Si la calidad es baja (pocas minucias o poco primer plano), se pide repetir y no cuenta.
3. Por cada cuadro de rostro: se guarda el crudo, se detecta, se alinea y se normaliza. Si no hay rostro, no cuenta.
4. Se reentrena el modelo del dominio afectado, se vuelven a proyectar **todos** los usuarios de ese dominio y se activa el modelo nuevo.
5. La calibración de rostro de ese dominio queda marcada como "anterior al último modelo". La app lo avisa; se recalibra con `calibrar.py`.

### 4.5 Cuántas capturas y de dónde

| | Simular | ESP32 |
|---|---|---|
| Huella | 5 impresiones de una identidad del banco para registrar; las otras 3 quedan para verificar (FVC2002 trae 8 por dedo). | **5 capturas** del mismo dedo, levantándolo y volviéndolo a poner cada vez. A unos 7 s por captura, menos de un minuto. Mínimo aceptable: 3. |
| Rostro | Dataset: 6 imágenes para registrar y 4 para verificar (ORL trae 10 por persona). Con el interruptor en DroidCam: igual que ESP32. | **15 cuadros** de DroidCam en unos 8 s, pidiendo girar un poco la cabeza. Mínimo aceptable: 10 con rostro detectado. Se registra con la misma luz y en el mismo lugar que la demo. |

**Banco para calibrar la huella** (no son usuarios; va en `datos/banco_as608/`):
- Meta: 8 identidades × 8 capturas = 64 imágenes, unos 15 minutos. Da 224 pares genuinos y 1,792 de impostor.
- **Cada dedo es una identidad distinta.** Una sola persona puede aportar hasta 10. Así se puede calibrar aunque el equipo no esté.
- De las 8 capturas, 5 hacen de registro y 3 de prueba, igual que en el uso real.
- Variar a propósito: presión, un poco de giro, dedo algo seco. La demo no va a ser más limpia que eso.

**Para calibrar el rostro** no existe ese truco. Genuinos: los registrados, en dos tandas separadas por minutos. Impostores: los demás registrados y las caras del dataset. Con pocas personas la estimación de FAR es débil; se dice así en el reporte.

### 4.6 Respaldo y borrado

- `python pc/scripts/respaldo.py crear`: ZIP con `pia.db` (copiada con la API de respaldo de SQLite, no copiando el archivo abierto), `usuarios/`, `modelos/`, `banco_as608/`, `calibracion/` y `config.toml`. Va a `datos/respaldos/`. **Hacer uno el lunes después del último ensayo y llevarlo en USB.**
- `python pc/scripts/respaldo.py restaurar <zip>`.
- `python pc/scripts/respaldo.py reprocesar`: regenera plantillas, alineados, modelos y vectores desde los crudos.
- **Borrar un usuario** (app o script): borra sus filas (en cascada), su carpeta, reentrena el modelo de su dominio. La bitácora conserva sus intentos con el ID y el nombre.
- `python pc/scripts/respaldo.py borrar-todo --confirmo`: borra usuarios, banco, intentos y modelos. Para después de la entrega: son huellas y caras de personas reales.

---

## 5. Listas de pruebas para el usuario en Windows

Todos los comandos son de PowerShell, desde la raíz del repositorio y después de `git pull`. Si un resultado no coincide, copiar la salida completa y pasársela a la sesión de la nube.

### P1. Preparación (viernes, sin esperar a la nube)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | `py -3.14 --version` y `py -3.13 --version` | Al menos una responde. Anotar cuáles. |
| 2 | Conectar el ESP32 por USB y abrir el Administrador de dispositivos, "Puertos (COM y LPT)" | Aparece un puerto (CP210x o CH340). Anotar el número. Si no aparece: el cable es solo de carga o falta el driver. |
| 3 | AS608 alimentado a 5 V, sin conectar al ESP32: medir TX contra GND | Unos 3.3 V (directo) o unos 5 V (divisor). Anotar. |
| 4 | Cablear el AS608 por la serigrafía | Vi a 5 V, GND a GND, TXD a GPIO16, RXD a GPIO17. |
| 5 | Abrir DroidCam en el celular, misma red WiFi que la laptop | La app muestra IP y puerto. En el navegador de la laptop, `http://<IP>:4747/video` muestra el video. |
| 6 | Bajar a mano FVC2002 (DB1_B a DB4_B, desde `bias.csr.unibo.it/fvc2002`) y ORL/AT&T | Los ZIP quedan en `datos\datasets\`. Si no se puede, se intenta con el script en P3. |

### P2. Imagen del AS608 (viernes, compuerta G1)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | En VS Code con PlatformIO: abrir `firmware/`, elegir el entorno `test_huella_imagen`, "Upload" | Compila y carga. La primera vez tarda varios minutos (baja la plataforma). Si no compila, pegar el error. |
| 2 | Cerrar el monitor serie de PlatformIO | Puerto libre. |
| 3 | `py -3.14 -m venv .venv` ; `.venv\Scripts\Activate.ps1` ; `pip install pyserial numpy pillow` | Instala sin compilar nada. |
| 4 | `python pc\scripts\bajar_huella.py --puerto COM5` | Imprime los parámetros del sensor y "Coloca el dedo". |
| 5 | Poner el dedo y no moverlo unos 7 s | Avance hasta `36864 bytes`, "CRC correcto" y tres archivos en `datos\pruebas\`. |
| 6 | Abrir los dos PNG | **Uno** se ve como huella, con crestas claras. Anotar cuál (alto o bajo primero). El otro se ve con ruido de grano. |
| 7 | Repetir 3 veces | Las tres llegan completas. |

Reportar a la nube: G1-A, G1-B o G1-C (bloque P2 de la sección 2), el orden de nibbles, y adjuntar o describir un PNG (pregunta abierta 3).

### P3. Entorno, DroidCam y banco de huellas (sábado)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | `pip install -r pc\requirements.txt` | Todo se instala con wheels. Si algo intenta compilar: borrar `.venv`, crear con `py -3.13` y repetir. |
| 2 | `python -c "import cv2; print(cv2.__version__, not cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').empty())"` | Imprime la versión y `True`. |
| 3 | `pytest pc\tests -q` | Todas pasan (algunas se saltan si falta un dataset). |
| 4 | `python pc\scripts\probar_camara.py --url http://<IP>:4747/video` | Ventana con el video, rectángulo en el rostro y en los ojos, y los cuadros por segundo. Probar también `--indice 1` si está instalado el cliente de DroidCam. |
| 5 | `python pc\scripts\descargar_datasets.py` | Baja y descomprime, o dice exactamente qué archivo dejar en qué carpeta. |
| 6 | `python pc\scripts\capturar_banco.py --puerto COM5 --identidad dedo01 --capturas 8` y repetir con `dedo02` … `dedo08` | 8 PNG por identidad en `datos\banco_as608\`. El script avisa si una captura salió con poca área y la repite. |

### P4. Módulos del hardware (sábado)

Cargar cada entorno desde PlatformIO y abrir su monitor serie.

| # | Entorno | Qué hacer | Resultado esperado |
|---|---|---|---|
| 1 | `test_teclado` | Presionar las 16 teclas en orden | El monitor imprime exactamente la tecla presionada. Si salen cambiadas, anotar cuál sale por cuál: se corrige el orden de pines. |
| 2 | `test_oled` | Mirar la pantalla | Dos líneas de texto y una barra que avanza. Si queda negra: revisar SDA 21, SCL 22 y la dirección (el monitor imprime la que encontró). |
| 3 | `test_leds` | Mirar los LEDs | Verde y rojo alternan cada segundo. |
| 4 | `test_servos` | Mirar los servos y el monitor | Servo 1 abre y cierra, luego el 2, nunca los dos a la vez. El monitor imprime "Motivo del ultimo reinicio: encendido". Si dice "brownout": poner el capacitor de 470 µF; si sigue, alimentar los servos con el cargador de 5 V y 2 A uniendo las tierras. |
| 5 | `test_servos` | Revisar el cerrojo en la caja | El brazo libra el gancho al abrir y vuelve debajo al cerrar. Anotar los ángulos que sirven. |

### P5. Primera verificación con hardware (domingo, compuerta G2)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | Cargar el entorno principal (`esp32dev`) | La OLED muestra "Sin conexion con la PC" y el LED rojo, hasta que arranque la app. |
| 2 | `python -m pia` y abrir `http://localhost:8000` | La app abre en modo Simular. Correr "Usuario legítimo · nivel 2": concedido. |
| 3 | Botón ESP32, "Buscar ESP32" | Aparece el puerto, la versión del firmware, "Sensor: OK", "OLED: OK". |
| 4 | `python pc\scripts\registrar.py --id 21 --nombre "..." --nivel 2` | Pide el PIN, 5 huellas y 15 cuadros. Termina con "Usuario 21 registrado". |
| 5 | En el teclado físico: `21#`, PIN, `#` | Cada tecla se ilumina en la app al presionarla. |
| 6 | Poner el dedo | La huella se dibuja por partes en la app en unos 7 s, y pasan las etapas. |
| 7 | Mirar al celular | Cuadro con el rostro detectado, y las etapas de rostro. |
| 8 | Esperar la decisión | LED y OLED responden. Si se concede: abre el servo 1 y, 300 ms después, el 2; se cierran solos. Fila nueva en la bitácora. |
| 9 | Desconectar el USB a media verificación | Nada se abre. Al reconectar y pulsar "Buscar ESP32", vuelve a funcionar. |

### P6. Calibración y prueba de aceptación (domingo)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | `python pc\scripts\calibrar.py --factor huella --dominio as608 --banco datos\banco_as608 --activar` | Imprime EER, umbral, FAR y FRR, y guarda la gráfica. Pasar los números a la nube. |
| 2 | Registrar a todos los de la demo | Cada uno con su ID, nivel y PIN. |
| 3 | `python pc\scripts\calibrar.py --factor rostro --dominio camara --activar` | Igual que el punto 1. |
| 4 | 10 intentos genuinos por persona | Al menos 8 de 10 concedidos. |
| 5 | 10 intentos de impostor por persona (ID y PIN de otro, con su propio dedo y cara) | **0 de 10 concedidos.** Si pasa uno, avisar: se sube el umbral. |
| 6 | Un intento con cada dedo equivocado y con la cara tapada a medias | Negado, con un mensaje que dice por qué. |

### P7. Ensayos (lunes)

| # | Qué hacer | Resultado esperado |
|---|---|---|
| 1 | Montar todo como el martes: laptop, celular en su soporte, la luz, la red | Igual que en el salón, en lo posible. |
| 2 | Abrir la app en Chrome o Edge, vista "Por etapa", y cambiar de etapa varias veces | Transiciones fluidas. Si se traban, abrir con `?sinvidrio=1` y dejarlo así. |
| 3 | Cortar el internet de la laptop (dejando la red local con el celular) y recargar | La app carga completa. |
| 4 | Ensayo completo: nivel 1 concedido, nivel 2 concedido, impostor negado, PIN incorrecto negado | Los cuatro correctos, tres veces seguidas. |
| 5 | Un caso en modo Simular con el interruptor de rostro en DroidCam | Funciona. |
| 6 | `python pc\scripts\respaldo.py crear` y copiar el ZIP a una USB | Respaldo hecho. |
| 7 | Tomar el tiempo del guion de `docs/DEMO.md` | Cabe en el tiempo que da el profesor. |

### P8. Lista previa (martes, una hora antes)

| # | Qué revisar | Resultado esperado |
|---|---|---|
| 1 | Laptop con cargador; celular con batería y sin bloqueo de pantalla | — |
| 2 | Celular y laptop en la misma red (o el plan de R6) y la IP de DroidCam puesta en `config.toml` | `probar_camara.py` muestra video. |
| 3 | ESP32 conectado, `python -m pia`, "Buscar ESP32" | Conectado, sensor y OLED en OK. |
| 4 | Una verificación de prueba con la luz del salón | Concedida. Si la luz cambió mucho y se niega: registrar de nuevo el rostro ahí mismo (un minuto por persona). |
| 5 | Limpiar la ventana del sensor | — |

---

## 6. Riesgos y supuestos

Cada uno dice si está verificado o es un supuesto, y qué hacer si sale mal.

| # | Riesgo | Estado | Si sale mal |
|---|---|---|---|
| **R1** | **El AS608 no entrega la imagen cruda con UpImage.** | **Supuesto** que sí la entrega (la hoja de datos lista el comando 0x0A). Nadie lo ha probado. Se resuelve hoy en P2. | **Diagnóstico de 30 minutos:** (1) leer el código de confirmación de `UpImage` que imprime el firmware; (2) confirmar que `GenImg` devolvió 0x00 justo antes; (3) probar a 57600 y con `ReadSysPara` ver los baudios reales; (4) revisar los 5 V con el sensor encendido; (5) ampliar el búfer de `Serial2` y bajar el USB a 115200 para descartar pérdida de bytes. **Plan B si no hay imagen el sábado a las 12:00:** `huella.fuente_esp32 = "banco"`. El teclado, la OLED, los LEDs, los servos y la cámara siguen siendo reales; el AS608 solo detecta que hay un dedo (`GenImg`) y la imagen sale de FVC2002, asignada al usuario al registrarlo. La app y la OLED lo rotulan, y se le dice al profesor. Cuesta poco porque el dispositivo simulado ya entrega huellas del banco. **En paralelo**, conseguir un R307 o FPM10 en una tienda local o con entrega en un día; usan el mismo protocolo, así que el firmware no cambia. **Nunca** se usa el matching interno del sensor. |
| R2 | El orden de los nibbles. | Supuesto: alto primero. | Se decide mirando los dos PNG en P2. Es una línea en `config.toml`. |
| R3 | Las huellas del AS608 dan pocas minucias o un EER alto (imagen de 4 bits, área pequeña, dedo seco). | Supuesto. Es el riesgo técnico más probable después de R1. | Recorte del bloque N7: 5 plantillas por usuario, puntaje máximo, umbral con FAR = 0, hasta 2 reintentos por verificación. Se reporta el EER real. No se cambia de método. |
| R4 | El firmware no se puede compilar en la nube. | **Verificado** que PlatformIO no puede (403 del proxy). Supuesto que `arduino-cli` desde GitHub sí. | Se compila en la PC. El costo es una o dos vueltas de "pegar el error". Por eso los entornos de prueba se entregan pronto y son chicos. Se evita si el usuario abre los hosts (pregunta 1). |
| R5 | Los datasets no se pueden bajar en la nube. | **Verificado** (bloqueados). Supuesto que desde la PC sí se puede; no se probó. | En la nube: banco sintético y, si se encuentra, un espejo en GitHub. En la PC: script y, si falla, descarga manual. Último recurso: Simular con el banco sintético, rotulado. |
| R6 | DroidCam no conecta en el salón (la WiFi de la escuela suele aislar a los equipos entre sí, o no hay señal). | Supuesto. | En este orden: (1) zona WiFi del celular, con la laptop conectada a ella; (2) "Zona con cobertura inalámbrica móvil" de Windows, con el celular conectado a la laptop; (3) DroidCam por USB con su cliente, leído por índice. Probar (1) y (3) el lunes. |
| R7 | `cv2.VideoCapture` no abre la URL de DroidCam, o entrega cuadros con retraso. | Supuesto que abre. | `camara.py` cae solo al lector MJPEG propio. Para el retraso: descartar cuadros viejos y quedarse con el último. |
| R8 | Eigenfaces falla con la luz del salón. | Supuesto, y probable: es la debilidad conocida del método. | CLAHE y máscara elíptica; registrar con la misma luz; y el punto 4 de la lista P8 (registrar el rostro de nuevo en el salón). |
| R9 | La integración con hardware no cierra el domingo (G2). | — | Modos degradados, en orden: **D1** huella desde el banco con todo lo demás real (igual que el plan B de R1). **D2** la app en Simular mostrando el pipeline, y el ESP32 mostrando teclado, OLED, LEDs y servos con una decisión mandada desde la app. **D3** Simular y los entornos de prueba por módulo. En los tres se dice con claridad qué es real y qué no. |
| R10 | El ESP32 se reinicia al mover los servos. | Supuesto que el USB aguanta. Se ve en P4. | Capacitor de 470 µF; luego cargador de 5 V y 2 A con tierras unidas. Llevar el cargador el martes. |
| R11 | El adaptador USB de la placa no aguanta 921600 baudios. | Supuesto que sí. | `baudios = 115200` en `config.toml` y en `firmware/src/config.h`. La imagen tarda lo mismo: el cuello es el sensor a 57600. |
| R12 | Una dependencia no se instala en Python 3.14. | **Verificado** en los metadatos de PyPI que hay wheels. Sin probar la instalación. | Entorno con `py -3.13`. |
| R13 | `opencv-python` 5 ya no trae los clasificadores Haar. | Supuesto. Se comprueba en N1. | Fijar `opencv-python<5`. |
| R14 | Viola-Jones no detecta las caras de ORL (vienen recortadas). | Sin medir. | Relleno de bordes y reescalado; si no llega al 80 %, alineación de respaldo para el dataset, rotulada. LFW solo si sobra tiempo. Esto afecta a Simular, no a la demo con cámara. |
| R15 | Las transiciones se traban en la laptop. | Sin medir en Windows. En la nube, sin tarjeta gráfica, dieron 11 a 14 cuadros por segundo. | `?sinvidrio=1` quita el `backdrop-filter`. Si aun así se traban, vista "Completa". |
| R16 | PlatformIO no se instala o no compila en la PC. | Supuesto que sí. | Arduino IDE 2 con las mismas librerías: los `.cpp` de `src/` se pueden abrir como sketch. La nube deja las instrucciones en `firmware/README.md`. |
| R17 | El cerrojo del servo choca con el gancho, o la caja no está impresa. | Sin revisar. No es de software. | Se ve en P4, punto 5. Si la caja no está, la demo se hace con el montaje en placa y los servos a la vista: sigue siendo "algo físico que actúa". |
| R18 | La sesión de la nube y el usuario se pisan en git. | — | La nube es la única que escribe código. El usuario no edita archivos del repositorio, salvo `config.toml`, que está ignorado por git (se sube `config.ejemplo.toml`). |
| R19 | El tiempo de proceso en Python es largo y la demo se siente lenta. | Supuesto: menos de 2 s por factor. | Medirlo en N2 y N3 y registrarlo en la bitácora (`duracion_ms`). Si la huella pasa de 3 s: menos orientaciones de Gabor. |

**Supuesto general sobre el tiempo:** el calendario supone que el usuario puede dedicar varias horas el viernes y el sábado, y que la sesión de la nube puede trabajar bloques largos sin que se agote el límite de uso. Si el límite corta la sesión, se retoma leyendo este archivo y el último resumen de bloque; por eso cada bloque termina con commit.

---

## 7. Preguntas abiertas

Solo las que cambian el plan. Cada una trae lo que se hará si no hay respuesta.

1. **¿Puedes abrir en el entorno de la nube estos hosts?** `dl.platformio.org`, `api.registry.platformio.org`, `dl.registry.platformio.org`, `registry.platformio.org`, `bias.csr.unibo.it` y `ndownloader.figshare.com`. Con eso la nube compila el firmware y baja los datasets, y te ahorras vueltas de "pegar errores". **Si no:** el firmware se compila en tu PC y la nube trabaja con el banco sintético (el plan ya lo contempla).
2. **¿A qué hora es la entrega del martes y el reporte tiene formato obligatorio?** El plan supone que el martes no se trabaja y que el lunes a las 18:00 se congela el código. Si la entrega es en la tarde, queda la mañana del martes como colchón, no como tiempo de desarrollo. **Si no hay respuesta:** el reporte se entrega como borrador en Markdown con figuras, para que lo pases a tu plantilla.
3. **¿Puedes pasarle a la nube imágenes reales de tu propia huella?** Hacen falta unas 10 o 20 capturas del AS608 para ajustar los parámetros en N7. Son un dato biométrico tuyo y el repositorio está en GitHub: no las subas si el repositorio es público. **Si no:** el ajuste se hace en tu PC con `explorar_parametros.py`, que es más lento y más a ciegas. Las huellas de tus compañeros no salen de tu PC en ningún caso.
4. **¿Cuántas personas van a aparecer en la demo y cuándo están disponibles para registrarse?** Lo ideal es registrarlas el domingo en la tarde. **Si no hay respuesta:** se registra solo a ti con dos IDs (nivel 1 con un dedo, nivel 2 con otro) y el impostor se demuestra con otro dedo y con la cara de otra persona.

### Respuestas del usuario (13 de noviembre)

1. **Hosts abiertos.** Esta sesión ya usa un entorno con acceso a los servidores de PlatformIO (comprobado: responde), a `ndownloader.figshare.com` y a `figshare.com` (comprobado: Olivetti/ORL se descarga). Para bajar Olivetti hace falta además el host de almacenamiento al que redirige figshare (`*.r2.cloudflarestorage.com`); hoy sí respondió. **FVC2002 sigue sin bajar:** `bias.csr.unibo.it` falla por su certificado TLS en https y no responde por http. Para FVC2002 sigue valiendo el plan: descarga manual en la PC o el banco sintético. No se desactiva la verificación TLS.
2. **Hora de entrega:** sin confirmar. Se mantiene el plan: el código se congela el lunes a las 18:00.
3. **El repositorio era público y el usuario lo hará privado.** Mientras sea público, no se suben huellas ni caras reales. Cuando sea privado, se pueden subir de 10 a 20 capturas de huella de un solo integrante que dé su permiso, en `pc/tests/fixtures/as608/`, para ajustar los parámetros. Los datos de los demás nunca salen de la PC.
4. **Son 6 personas en la demo.**
   - **Registro:** unos 2 minutos por persona (5 huellas y 15 cuadros), unos 15 minutos en total. Se hace el domingo en la tarde.
   - **Prueba de aceptación P6:** 60 intentos genuinos y 60 de impostor, unos 40 minutos. Si no hay tiempo, 5 y 5 por persona.
   - **Rostro:** con 6 personas, la estimación de FAR mejora, aunque sigue siendo débil.
   - **IDs y niveles:** se reparten entre nivel 1 y nivel 2.

### Decisiones que tomé sin preguntar (y por qué)

- **Dos compuertas en lugar de visto bueno por fase** (C2): cada parada cuesta horas.
- **CRC al final del marco de imagen** (C1): lo otro es imposible con reenvío por partes.
- **Sensor a 57600 baudios** (C3): 3 segundos menos no valen el riesgo de dejar el sensor mudo.
- **Una sola base con la fuente por muestra** (4.3): es lo único que permite el interruptor de rostro en Simular sin duplicar usuarios.
- **Imágenes como arreglos en JSON, no PNG** (3.2): así las funciones de dibujo de la maqueta se reutilizan sin tocarlas.
- **ESP32 falso por `socket://`** (N6): `pyserial` lo abre igual que un COM, funciona en la nube y en Windows, y no requiere instalar puertos virtuales.
- **Banco sintético exportado de la maqueta** (C5): da pruebas automáticas desde la primera hora sin depender de la red.
- **Registro por consola primero, vista después** (1.5): el registro tiene que existir el domingo; la vista es mejora.
- **La maqueta no se toca**: es la referencia visual y la fuente del banco sintético.
