# Prompt para Claude Code (Fable 5.2): sistema biométrico multimodal del PIA

> Cómo usarlo: abre el repositorio en VS Code (Windows), inicia Claude Code con el modelo Fable 5.2 y pega todo lo que está debajo de la línea. El archivo `docs/CONTEXTO_PIA_RDP.md` debe estar en el repositorio.

---

## Tu papel y el objetivo

Vas a construir, desde cero y en este repositorio, el sistema completo del PIA de Reconocimiento de Patrones (FIME, UANL): un control de acceso por niveles con tres factores (PIN, huella y rostro) y una app web local que muestra, de forma visual y animada, lo que pasa en cada fase del reconocimiento.

El hardware todavía no está conectado. Escribe todo como si fuera a conectarse y cargarse tal cual, pero nunca digas que algo "funciona con el hardware" si no se probó con el hardware. Lo que sí se tiene que poder probar de punta a punta, sin hardware, es el modo **Simular**.

Antes de escribir código, lee completo `docs/CONTEXTO_PIA_RDP.md`. Es la fuente de verdad sobre hardware, pines, métodos obligatorios y riesgos. Las decisiones de la siguiente sección resuelven los puntos que ese archivo deja pendientes y tienen prioridad sobre él.

Responde, escribe los comentarios del código, los mensajes de commit y todos los textos de la interfaz en **español**.

## Decisiones ya tomadas (no las reabras)

1. **App:** web local. Un backend en Python (FastAPI + WebSocket) hace todo el procesamiento y sirve la interfaz, que corre en el navegador en `localhost`. Debe funcionar **sin internet** el día de la demo.
2. **Política de acceso:** los tres factores son obligatorios para todos. El nivel (1 = Lector, 2 = Editor) es un atributo del usuario registrado, no un premio por factores.
3. **Identidad:** verificación 1:1. En el teclado el usuario escribe su **ID de 2 dígitos + `#`** y luego su **PIN de 4 dígitos + `#`**. `*` borra el último dígito y `D` cancela. Huella y rostro se comparan solo contra ese usuario.
4. **Modo Simular:** usa datasets públicos que pasan por el pipeline real (no resultados fijos). El teclado se simula en pantalla.
5. **Herramientas:** firmware con **PlatformIO**. Tú corres dentro de Claude Code en VS Code, en Windows, con Python 3.14 y sin compilador de C++.
6. **Forma de trabajo:** por fases, con una revisión al final de cada una (ver "Fases y puntos de revisión"). Al terminar una fase **te detienes y esperas mi visto bueno**.
7. **Estética:** oscura, con acentos en verde FIME y glassmorphism usado con criterio (detalles en "Diseño de la app").

## Restricciones duras

- **Los métodos de las fases 2 a 4 están fijados por el PIA.** Impleméntalos tal cual: campo de orientación, Gabor, binarización, adelgazamiento, minucias, matching por grafos, Viola-Jones, alineación, normalización fotométrica, PCA/Eigenfaces y distancia euclidiana con umbral. Nada de redes neuronales, nada de `face_recognition` ni `dlib`, y **nunca** el matching interno del AS608: el sensor solo entrega la imagen cruda.
- **PCA se implementa con NumPy** (centrado, truco de la matriz pequeña Aᵀ·A o SVD, proyección y reconstrucción), para que el método quede visible en el código. scikit-learn solo puede usarse para descargar datasets o comparar resultados, nunca como la implementación.
- **Solo dependencias con wheels para Python 3.14 en Windows.** Antes de fijar una dependencia, verifica que se instala en esa versión. Si alguna no tiene wheel, detente, avísame y propón una alternativa (por ejemplo, un venv con Python 3.13 usando el lanzador `py`). No asumas que se instala.
- **El frontend no necesita Node ni un paso de build.** HTML, CSS y JavaScript con módulos ES, servidos por FastAPI. Si usas alguna librería de JS, guárdala en `app/vendor/` con su licencia; nada se carga desde una CDN. Las fuentes también van locales.
- **Firmware y PC por separado:** `firmware/` no importa nada de `pc/` y viceversa. Lo único que comparten es el protocolo documentado en `docs/PROTOCOLO.md`.
- **Pines y conexiones:** exactamente los de la sección 4 del contexto. No cambies un pin sin decírmelo y explicar por qué.
- **Datasets:** nunca se suben al repositorio (van en `.gitignore`). Se descargan con un script, y si una URL ya no sirve, el script imprime instrucciones claras para la descarga manual.

## Arquitectura

**Quién manda:** la PC orquesta todo el flujo con una máquina de estados. El ESP32 es un periférico con interfaz local: lee el teclado, captura la huella, dibuja la OLED y mueve LEDs y servos cuando la PC se lo ordena. Así hay un solo lugar donde se toman las decisiones.

**Abstracción de dispositivo:** una interfaz `Dispositivo` con dos implementaciones:
- `DispositivoSimulado`: teclado virtual, huellas del dataset y caja virtual.
- `DispositivoESP32`: puerto serial real.

El orquestador, los algoritmos y la app no saben cuál de las dos está activa. Los botones **Simular** y **ESP32** de la app eligen la implementación.

**Estructura propuesta** (ajústala si tienes una razón y dímela):

```
firmware/                 Proyecto PlatformIO (env principal + envs de prueba por módulo)
pc/
  pia/
    huella/               Preprocesamiento, minucias, matching por grafos
    rostro/               Viola-Jones, alineación, normalización, Eigenfaces
    fusion.py             Normalización de puntajes, fusión ponderada, decisión
    orquestador.py        Máquina de estados de una verificación
    dispositivos/         Interfaz Dispositivo, simulado y ESP32 (protocolo serial)
    camara.py             DroidCam por URL o índice de cámara virtual
    registro.py           Alta de usuarios (enrolamiento)
    bitacora.py           SQLite
    calibracion.py        FAR, FRR, EER y elección de umbrales
    servidor.py           FastAPI + WebSocket, sirve app/
  scripts/                Descarga de datasets, calibración, pruebas por consola
  tests/                  pytest
app/                      Interfaz web (sin build)
datos/                    Datasets y base de usuarios (ignorado por git)
config.toml               Puerto, baudios, URL de DroidCam, umbrales, pesos, tiempos de servo
docs/                     Contexto, protocolo, guía de cableado, guía de la demo
```

La configuración se lee con `tomllib` (biblioteca estándar). Ningún valor que pueda cambiar en la demo (puerto COM, IP del celular, umbrales) va escrito en el código.

## Protocolo serial (documéntalo en `docs/PROTOCOLO.md`)

Toma como base la propuesta del contexto y complétala. Lo que tiene que cumplir:

- **USB a 921600 baudios**, configurable. Si el adaptador USB de la placa no los aguanta, se baja a 115200 desde `config.toml`.
- **Líneas de texto terminadas en `\n`** para los mensajes, con longitud máxima definida.
- **Cada tecla se manda en cuanto se presiona** (`TECLA:<c>`), además del `PIN:<id>:<pin>` final. La app la necesita para animar el teclado en tiempo real.
- **La imagen de huella se reenvía mientras llega del sensor**, sin esperar a tenerla completa. Va enmarcada así: una línea `IMG:<bytes>:<crc32>`, luego los bytes crudos y luego `IMG:FIN`. La PC la va leyendo por partes y le manda el avance a la app para dibujar la huella línea por línea. Verifica el CRC.
- **Formato de la imagen:** 256 × 288 a 4 bits por píxel. El orden de los nibbles (alto primero o bajo primero) no está confirmado. Hazlo configurable y deja una prueba que lo detecte. Sube el sensor a 115200 baudios si el módulo lo acepta: a 57600, la transferencia sola tarda unos 6.4 s.
- **Mensajes de la PC al ESP32:** `MSG:<línea1>|<línea2>` para la OLED, `PEDIR_HUELLA`, `ACCESO:0|1|2`, `RESET` y un `PING`/`PONG` de vida.
- **Al conectarse:** el ESP32 manda `HOLA:<versión>:<estado del sensor>:<estado de la OLED>`.
- **Seguridad del lado del ESP32:** al arrancar, los servos van a la posición de cerrado. Si la PC deja de responder (sin `PING` en 5 s), la OLED muestra "Sin conexión con la PC", se enciende el LED rojo y no se abre nada. Cada fase tiene tiempo límite y, si se vence, todo vuelve a reposo.
- **Servos:** se mueve uno a la vez, con 300 ms entre uno y otro. Después de abrir, regresan a la posición de cerrado tras un tiempo configurable. Avísame si ves un problema con el cerrojo; por ejemplo, que el brazo del servo choque con el gancho si la tapa se cierra mientras está trabado.

## Algoritmos

### Huella

1. Normalización por media y varianza, y segmentación del primer plano por varianza de bloques.
2. Campo de orientación por gradientes (mínimos cuadrados por bloque), suavizado como campo vectorial (sobre 2θ).
3. Frecuencia de crestas por bloque.
4. Realce con un banco de filtros de Gabor orientados según el campo.
5. Binarización y adelgazamiento (`skimage.morphology.skeletonize`).
6. Minucias por número de cruce (terminaciones y bifurcaciones), cada una con posición y orientación.
7. Eliminación de minucias falsas: cerca del borde de la máscara, espolones cortos y pares demasiado cercanos.
8. **Matching por grafos:** describe cada minucia por su vecindad (k vecinos o triangulación de Delaunay) con rasgos invariantes a rotación y traslación: distancias, ángulos relativos y tipo. Busca correspondencias entre los grafos locales y consolídalas con una alineación global. El puntaje sale en [0, 1]. Documenta en el código qué variante elegiste y por qué.

Los parámetros que dependen de la resolución (tamaño de bloque, frecuencia esperada) deben poder cambiarse, porque las imágenes del dataset y las del AS608 no tienen el mismo tamaño ni calidad.

### Rostro

1. Viola-Jones con los cascades de Haar que trae OpenCV: rostro y ojos.
2. Alineación geométrica: rotar hasta que los ojos queden horizontales, escalar a una distancia fija entre ojos y recortar a un tamaño fijo. Si no se detectan los ojos, usa un respaldo documentado.
3. Normalización fotométrica: ecualización de histograma o CLAHE, más una máscara elíptica.
4. Eigenfaces con NumPy: cara media, eigenfaces y número de componentes elegido por varianza explicada (meta: 95 %, configurable). El vector de pesos es la proyección.
5. Distancia euclidiana contra los vectores registrados de ese usuario, con umbral. Calcula también la distancia al espacio de caras (error de reconstrucción) para rechazar imágenes que no son un rostro.

### Fusión y decisión

- El PIN es una condición obligatoria. Se guarda con hash PBKDF2 (`hashlib`) y sal; nunca en texto plano.
- Los puntajes de huella y rostro se normalizan con lo obtenido en la calibración y se combinan con pesos configurables (por defecto 0.5 y 0.5).
- Se concede acceso si el PIN es correcto, **cada factor pasa su propio umbral** (0.50 normalizado) y la suma ponderada llega a 0.60. El nivel concedido es el del usuario. (En la maqueta, la regla anterior, con un piso de 0.35 y una fusión de 0.50, dejaba pasar a un impostor de rostro cuando su huella era buena.)
- Cada intento va a la bitácora (SQLite) con: fecha, ID, resultado por factor, puntajes, decisión y modo (Simular o ESP32).

### Calibración

Un script y una vista en la app que calculan las distribuciones de puntajes genuinos e impostores, las curvas de FAR y FRR, el EER y los umbrales propuestos. Hay que repetirla con imágenes reales del AS608, porque los umbrales del dataset no sirven tal cual para ese sensor. Dilo en la documentación.

### Registro de usuarios

Desde la app: ID, nombre, nivel y PIN; de 3 a 5 capturas de huella (en Simular salen del dataset, en ESP32 del sensor real), y de 10 a 20 cuadros del rostro de DroidCam (en Simular, del dataset). Al registrar a alguien se vuelve a entrenar la base de Eigenfaces.

## Datasets para el modo Simular

- **Huella:** FVC2002, subconjuntos B (de uso libre para investigación). Script de descarga con instrucciones manuales si falla.
- **Rostro:** la opción preferida es ORL/AT&T (vía `sklearn.datasets.fetch_olivetti_faces`), porque tiene iluminación controlada, que es el caso en que Eigenfaces funciona bien. Pero esas imágenes vienen ya recortadas y Viola-Jones puede no detectarlas. **Compruébalo**: mide la tasa de detección (prueba con relleno de bordes y reescalado). Si es baja, usa LFW sin recorte (`fetch_lfw_people(slice_=None, min_faces_per_person=20)`) y reporta la exactitud de cada opción. No escojas sin medir.
- **Escenarios** que se eligen en la app: usuario legítimo de nivel 1, usuario legítimo de nivel 2, impostor de huella, impostor de rostro y PIN incorrecto. Los usuarios simulados son identidades del dataset ya registradas por un script.
- En Simular, la llegada de la huella imita la transferencia real (por partes, a la velocidad configurada) y la app lo indica como simulado.

## Cámara

DroidCam por URL (`http://<IP>:4747/video`, configurable) o por el índice de la cámara virtual. Si la cámara no responde, la app muestra un error claro con qué revisar (misma red WiFi, IP, que la app esté abierta). Nunca usa una imagen de relleno sin avisar.

## Diseño de la app

### Skills

Si en esta sesión existen las skills `impecable`, `anti-ia-slop` (o con un nombre parecido), `apple-glassmorphism`, `dataviz` y `humanizer`, cárgalas antes de diseñar:
- `humanizer`: para los textos de la interfaz y la documentación.
- `dataviz`: para las gráficas de FAR/FRR, las distribuciones y las barras de pesos.

Si no existen, sigue las reglas de abajo, que ya las resumen. No te detengas a preguntar por ellas.

### Vistas

1. **Verificación en vivo** (la principal). Arriba, una barra con:
   - Los botones **Simular** y **ESP32**.
   - El estado de la conexión: puerto, versión del firmware, sensor y OLED.
   - Un indicador por pasos de las 5 fases del PIA.

   Debajo, los paneles de cada factor, que se activan en orden. Un control **"Vista: Completa | Por etapa"** permite ver todos los paneles a la vez o solo la etapa actual (PIN → Huella → Rostro → Actuación), con transiciones entre etapas. El detalle está en la sección 4 de `docs/PROMPT_FABLE_REDISENO.md`.
2. **Registro** de usuarios.
3. **Bitácora**, con filtros.
4. **Calibración**: distribuciones y curvas de FAR/FRR, EER y umbral actual sobre la curva.
5. **Ajustes**: lo de `config.toml` que tiene sentido cambiar en la demo.

### Qué se ve en cada fase (con datos reales del pipeline)

Toda visualización muestra datos intermedios reales que manda el backend: imágenes, campos, minucias, vectores y puntajes. **Ninguna animación inventa datos.** Si algo no existe en el algoritmo (por ejemplo, la ventana de búsqueda de Viola-Jones, que OpenCV no expone), no se simula como si fuera real.

- **Teclado:** réplica de la matriz 4×4 en el mismo orden que el físico. La tecla presionada se ilumina con una respuesta corta. Las casillas del ID y del PIN se van llenando. Los dígitos del PIN se muestran enmascarados, con un ajuste "mostrar teclas en la demo" activado por defecto (al iluminar la tecla, el dígito se ve de todos modos; dilo en la interfaz).
- **Huella:**
  - Barrido de la imagen conforme llegan los bytes.
  - Luego una tira de etapas, cada una con su imagen real: original → máscara → campo de orientación (segmentos por bloque coloreados por ángulo) → Gabor (aparece con un barrido) → binaria → esqueleto (se dibuja) → minucias, que aparecen escalonadas con símbolos distintos para terminación y bifurcación y una marca de orientación.
  - El matching se ve con las dos plantillas lado a lado: las aristas del grafo, las líneas entre pares correspondientes y el puntaje subiendo contra la línea del umbral.
- **Rostro:**
  - El cuadro capturado con el rectángulo del rostro y de los ojos.
  - La alineación como una transformación animada hacia la pose canónica.
  - El antes y después de la normalización, con su histograma.
  - La cara media y una cuadrícula con las primeras eigenfaces.
  - El vector de pesos como barras.
  - La reconstrucción progresiva con 1, 2, …, k componentes, que es la visual estrella y es honesta.
  - Por último, la distancia del usuario colocada sobre una recta con las distribuciones de genuinos e impostores de la calibración y el umbral marcado.
- **Fusión y actuación:** los dos puntajes normalizados se combinan en un indicador con el umbral. La caja aparece como un SVG con sus dos tapas: se abren las que correspondan al nivel, el LED virtual se pone verde o rojo, y hay una réplica exacta de la OLED de 128 × 64 que muestra lo mismo que la pantalla física.
- **Modo explicación:** un control de velocidad (tiempo real o cámara lenta) y una opción que pausa en cada etapa con un pie de una línea que explica qué se hizo. Sirve para exponer en clase.

### Dirección visual

La referencia visual de la fase 3 es la maqueta rediseñada `docs/maqueta/acceso_biometrico.html` (se abre con doble clic; capturas y video en `docs/maqueta/capturas/`). La app sigue sus tokens (`:root`), sus componentes y sus transiciones. Las decisiones de diseño, las mediciones y lo que quedó pendiente están en `docs/REVISION_REDISENO.md`; léelo antes de diseñar. Si la app necesita algo que la maqueta no tiene (Registro, Calibración, Ajustes), aplica las reglas de las secciones 1 a 5 de `docs/PROMPT_FABLE_REDISENO.md`. En resumen:

- **Lenguaje de Apple (HIG) en modo oscuro:**
  - Grises neutros semánticos (`systemBackground`, `label`, `separator`…).
  - El verde FIME como único color de acento, con valor provisional por confirmar. Como relleno lleva texto oscuro; para texto y trazos finos se usa el acento claro derivado del mismo token.
  - `systemGreen` (`#30D158`), `systemRed` (`#FF4245`) y `systemOrange` (`#FF9230`) para los estados, siempre con icono o texto además del color.
- **Tipografía:** Inter y JetBrains Mono guardadas localmente (SF Pro no se puede usar en Windows). Reutiliza `docs/maqueta/fonts/` y los iconos de Lucide de `docs/maqueta/icons/`. El subconjunto `latin` no trae flechas ni letras griegas.
- **Forma:** radios concéntricos, controles en cápsula y objetivos de al menos 44 px.
- **Vidrio solo en lo que flota:** barra superior, controles segmentados, navegador de etapas, píldora de explicación y modales. Los datos van sobre superficies opacas. Máximo dos capas de vidrio, con respaldo para `prefers-reduced-transparency`. La barra, el navegador y el pie van al 75 % de opacidad para que el texto se lea cuando pasa contenido claro por debajo (contraste medido de 4.78:1 o más).
- **Fondo:** estático, casi negro, con campos de color difuminados y poco saturados, y grano fino. Sin retícula. La variante elegida es la A (`data-fondo="a"`); la B queda como alternativa.
- **Pendiente de la maqueta que la app debe resolver:** medir los cuadros por segundo de las transiciones en la laptop de la demo (en el contenedor sin GPU dieron 11 a 14), y que la etapa de Huella quepa completa sobre el pie a 1440 × 900.

### Animación

- **Cada animación explica algo:** que llegó un dato, que terminó una etapa o que se tomó una decisión. Nada se mueve por adorno.
- **Duraciones:** de 150 a 250 ms para respuestas de la interfaz y de 400 a 1200 ms para revelar resultados. Curvas de salida suaves. Escalonado corto en las listas (minucias, eigenfaces).
- **Lo único que se repite sin fin** es el indicador de "esperando", y discreto.
- **La animación nunca frena al pipeline:** se anima conforme llegan los datos, y si llegan más rápido, la cola se compacta.
- **Con `prefers-reduced-motion`**, todo pasa a transiciones de opacidad.
- **Herramientas:** Canvas 2D para las imágenes y los campos, SVG para la caja, el teclado y las gráficas, y Web Animations API o CSS. Usa una librería solo si de verdad ahorra trabajo, y guárdala en `vendor/`.

### Lo que no debe tener (anti "IA genérica")

- Degradados morados o azul-violeta.
- Neón brillante por todos lados.
- Texto con degradado.
- Iconos de destellos o estrellitas de "IA".
- Emojis.
- Métricas o textos de relleno.
- Un "hero" de bienvenida.
- Una cuadrícula de tarjetas idénticas.
- Sombras de color.
- Frases de marketing.

Los textos son cortos, directos y en español natural, por ejemplo: "Coloca el dedo en el sensor", "Huella recibida (36,864 bytes)", "Mira a la cámara".

Cada vista tiene sus estados reales bien diseñados: vacío, cargando, error y sin conexión.

## Firmware (PlatformIO)

- Placa `esp32dev` (ESP32-WROOM-32). Las librerías van fijas por versión en `platformio.ini`: `Keypad`, `ESP32Servo`, `Adafruit SSD1306`, `Adafruit GFX`, y `Adafruit Fingerprint` o `FPM`.
- **Huella:**
  - `HardwareSerial` en Serial2 (RX = 16, TX = 17), nunca `SoftwareSerial`.
  - Implementa GenImg y UpImage tú mismo si la librería no deja reenviar los paquetes de datos mientras llegan. Es el protocolo de paquetes documentado del AS608: cabecera `EF01`, dirección, PID, longitud y checksum.
- **Estructura:** una máquina de estados sin `delay()` en el ciclo principal, con módulos separados para teclado, huella, OLED, actuadores y protocolo.
- **Entornos de prueba por módulo**, que siguen el plan de la semana 1 del contexto:
  - `test_huella_imagen`: captura, descarga e imprime estadísticas, y trae un script de Python que guarda la imagen como PNG.
  - `test_teclado`: imprime cada tecla, para confirmar el orden de los pines.
  - `test_oled`.
  - `test_servos`: mueve uno a la vez y reporta reinicios por brownout.
  - `test_leds`.
- **Guía de cableado** en `docs/CABLEADO.md`, basada en la sección 4 del contexto. Incluye la advertencia de medir el TX del AS608 antes de conectarlo y la de conectar por la serigrafía de la placa, no por el color de los cables.

## Fases y puntos de revisión

Al final de cada fase haz commit (mensajes en español) y entrégame un resumen con:
1. Qué hiciste.
2. Cómo lo pruebo yo (comandos exactos para PowerShell).
3. **Qué está verificado y qué no**, con la evidencia: salida de pruebas, métricas y capturas.
4. Riesgos o decisiones que necesito tomar.

Después espera mi visto bueno.

- **Fase 0, entorno:** verifica Python y crea el venv. Instala y comprueba cada dependencia en 3.14, crea la estructura, `.gitignore`, `config.toml` de ejemplo, un README breve y el script de descarga de datasets.
- **Fase 1, algoritmos:** huella y rostro completos, con pruebas de pytest y volcado de imágenes intermedias. Reporta el EER y los FAR/FRR en los datasets, más la tasa de detección de Viola-Jones de cada dataset de rostro. Aquí se decide qué dataset de rostro usar.
- **Fase 2, backend:** orquestador, `DispositivoSimulado`, registro, bitácora, calibración y API WebSocket. Una verificación simulada completa debe correr desde la consola, sin la app.
- **Fase 3, app:** todas las vistas y animaciones conectadas al backend real en modo Simular. Si Playwright está disponible, entrega capturas (y un GIF o video corto del flujo); si no, dime qué abrir para revisarla. Revisa el contraste y el rendimiento: la animación no debe trabarse al procesar.
- **Fase 4, firmware:** proyecto PlatformIO que compila, los entornos de prueba, `DispositivoESP32` en la PC, `docs/PROTOCOLO.md` y `docs/CABLEADO.md`. Entrégame una lista de pruebas con hardware en orden, cada una con su resultado esperado.
- **Fase 5, integración y demo:** modo ESP32 de punta a punta (lo que se pueda verificar sin hardware se verifica con un ESP32 falso que hable el protocolo por un puerto virtual o un *loopback*), `docs/DEMO.md` con el guion de la presentación y una sección de solución de problemas: brownout, COM ocupado, DroidCam sin conexión e imagen de huella con ruido.

## Cómo reportar

- Distingue siempre entre "probado", "compila pero no se probó" y "sin probar".
- Si un resultado es malo (por ejemplo, un EER alto), repórtalo con el número y una hipótesis. No ajustes los datos de prueba para que se vea mejor.
- Si una instrucción de este prompt choca con lo que encuentres (una librería que no existe, un dataset caído, un pin en conflicto), detente y pregúntame en lugar de improvisar en silencio.
