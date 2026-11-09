# Contexto del proyecto: PIA de Reconocimiento de Patrones

Archivo de contexto para trabajar el proyecto con Claude Code. Reúne qué es el proyecto, qué hardware se usa, cómo se conecta, cómo se divide el software y en qué va el diseño 3D de la caja.

Última actualización: 9 de noviembre de 2026.

---

## 1. Datos generales

| Dato | Valor |
|---|---|
| Materia | Reconocimiento de Patrones (RDP) |
| Escuela | FIME, UANL |
| Profesor | Antonio Juárez Alonso |
| Grupo | 003, LMV, hora N2 |
| Alumno | Nestor (Mecatrónica) |
| Tipo de entrega | PIA en equipo: demostración física funcionando + reporte técnico al final |
| Avance presentado | 2 de noviembre de 2026 (idea y plan de trabajo) |
| Entrega final | Aproximadamente 4 semanas después del avance; fecha exacta por confirmar |

**Título del PIA:** Diseño e implementación de un sistema de reconocimiento biométrico multimodal para control y acceso de información confidencial (según jerarquía).

**Petición del profesor:** quiere ver algo físico actuar en la demo, no solo una respuesta en pantalla.

El proyecto se hace desde cero. No reutiliza el código de las actividades AF4 y AF5 (reconocimiento facial y control de acceso a carpeta), aunque se pueden consultar como referencia.

---

## 2. Qué tiene que hacer el sistema

Un usuario se identifica con **tres factores**: PIN numérico, huella dactilar y rostro. Según quién sea, el sistema le da acceso a un **nivel de información**:

| Nivel | Nombre | Acceso |
|---|---|---|
| 1 | Lector | Consulta documentos generales, sin editar |
| 2 | Editor | Consulta y edita, y entra a información sensible (por ejemplo, Compras) |

**Decisión pendiente:** si todos los usuarios deben pasar los tres factores, o si cada factor verificado sube un nivel.

### Fases obligatorias del PIA

Los métodos están fijados por la especificación del PIA. Hay que implementarlos tal cual, aunque existan métodos más modernos.

| Fase | Huella | Rostro |
|---|---|---|
| 1. Percepción y captura | Módulo dactilar (óptico o capacitivo) | Módulo facial (LiDAR o cámara; se usa cámara) |
| 2. Preprocesamiento | Estimación del campo de orientación, realce direccional con filtros de Gabor, binarización, adelgazamiento | Detección de rostro con Viola-Jones, alineación geométrica, normalización fotométrica |
| 3. Extracción de características | Minucias (terminaciones y bifurcaciones) con posición espacial y orientación | PCA para proyectar el rostro en el subespacio de Eigenfaces (vector de pesos) |
| 4. Matching y clasificación | Algoritmo basado en grafos sobre las minucias | Distancia euclidiana entre el vector de pesos y los de la base de datos, con umbral |
| 5. Actuación | Decisión de acceso por nivel | Decisión de acceso por nivel |

**Regla importante:** el sensor de huella trae su propio algoritmo de comparación interno. **No se usa.** El sensor solo captura la imagen cruda; las fases 2 a 4 se programan en el proyecto.

### Calibración

Los umbrales de huella y rostro se calibran con pruebas de falsa aceptación (FAR) y falso rechazo (FRR). La decisión final combina los puntajes de huella y rostro con pesos.

---

## 3. Hardware

### Lista de componentes

| Componente | Modelo | Función |
|---|---|---|
| Microcontrolador | ESP32 DevKit V1, módulo **ESP32-WROOM-32** (no WROVER) | Lee teclado y sensor, mueve servos, maneja OLED y LEDs, habla con la PC por USB |
| Sensor de huella | **AS608** (óptico, con cable de conector) | Captura la imagen de la huella |
| Teclado | Matricial **4×4 de membrana** (0–9, A–D, `*`, `#`) | Captura el PIN |
| Cámara | **Celular con DroidCam**, por WiFi | Captura el rostro |
| Pantalla | OLED 0.96" I2C, controlador SSD1306, 128×64 | Muestra instrucciones y resultado |
| Actuadores | 2 servomotores **SG90** (5 V, 180°) | Liberan el seguro de cada compartimento de la caja |
| Indicadores | LED verde y LED rojo de 5 mm, con resistencia de 220 Ω | Acceso concedido / denegado |
| Varios | Capacitor de 470 µF (10 V o más), resistencia de 10 kΩ, placa perforada, zócalos hembra 1×15, cables Dupont | Montaje y protección |

### 3.1 Sensor de huella AS608

Datos de la hoja de datos del módulo que se compró:

| Dato | Valor |
|---|---|
| Interfaz | UART TTL |
| Velocidad | 57600 baudios por defecto (9600 × N, N de 1 a 12) |
| Imagen | 256 × 288 píxeles; por UART se envía a 4 bits por píxel (unos 36,864 bytes) |
| Comando para bajar la imagen | UpImage (código 0x0A) |
| Consumo | Hasta 120–150 mA |
| Medidas del módulo | 45.1 × 20.3 × 18.6 mm (bloque con punta en cuña; la ventana está sobre la cuña) |
| Ventana de lectura | 16 × 18 mm según la hoja (la tienda dice 19.5 × 15.5 mm) |
| Montaje | Sin orejas para tornillos; tiene una ranura vertical a cada lado |

**Voltaje:** la hoja de datos dice 3.3 a 5 V y la tienda dice 3.6 a 6 V. Se alimenta a **5 V**, que entra en los dos rangos.

**Conector de 8 pines:** D−, D+, Vt, WAK, GND, RXD, TXD, Vi. Solo se usan **Vi, GND, TXD y RXD**. En la foto de la hoja, D−, D+, Vt y WAK aparecen como "NC".

**Cuidado con los colores de los cables:** la misma hoja de datos se contradice (una tabla dice negro = TXD, el ejemplo de Arduino dice negro = GND). **Conectar siempre por la serigrafía de la placa, nunca por el color.**

**Antes de conectarlo al ESP32:** el ESP32 trabaja a 3.3 V y no tolera 5 V en sus pines. Alimentar solo el sensor a 5 V y medir con multímetro el pin **TX contra GND** en reposo:
- Si marca unos 3.3 V: TX va directo al GPIO16.
- Si marca unos 5 V: poner un divisor (1 kΩ en serie, 2 kΩ a GND) entre TX y GPIO16.
- No poner el divisor sin medir: si la señal ya es de 3.3 V, el divisor la baja a unos 2.2 V y el ESP32 puede no leerla.

**Prueba de imagen cruda (primera tarea del proyecto):** la hoja muestra el programa **SFGDemo** (Windows) con botones Capture, Download Image y Save Image. Probar con SFGDemo, conectando el sensor por un adaptador USB-serial o usando el ESP32 como puente serial. Si guarda la imagen, el módulo sí entrega la imagen cruda.

**Librerías:**
- `Adafruit_Fingerprint`: para verificar que el sensor responde. En ESP32 usar `HardwareSerial` (Serial2), **no** `SoftwareSerial`.
- `FPM` (brianrho): tiene el ejemplo `image_to_pc` con un script de Python para bajar la imagen a la PC. Documenta sensores R30x y FPM10; el AS608 usa el mismo protocolo, pero hay que confirmarlo con la prueba.

**Plan B si no entrega la imagen:** cambiar a un sensor R307 o FPM10 (el R307 requiere 5 V).

### 3.2 Teclado 4×4

- Matriz pasiva de 8 pines: 1 a 4 son filas, 5 a 8 son columnas. **No lleva alimentación ni GND.**
- El orden puede variar. Comprobar con multímetro: al presionar `1` debe haber continuidad entre el pin 1 y el pin 5.
- Librería `Keypad`. Usa pull-up internas, así que los 8 pines deben ser de entrada/salida con pull-up. **No usar GPIO34, 35, 36 ni 39** (son solo de entrada y sin pull-up).
- Es de membrana con adhesivo. Para que todas las teclas registren, debe ir pegado sobre una superficie completa; sin respaldo, las teclas fallan y las pistas de plata se agrietan.

### 3.3 Cámara: celular con DroidCam

- Se usa la cámara del celular como cámara web con la app **DroidCam**, conectada por WiFi a la PC.
- Dos formas de leerla desde Python con OpenCV:
  1. Con el cliente de DroidCam instalado en la PC, aparece como cámara web virtual: `cv2.VideoCapture(<índice>)`.
  2. Leyendo directo el video que transmite la app por la red: `cv2.VideoCapture("http://<IP_del_celular>:4747/video")`. **Verificar en la app la IP, el puerto y la ruta**, porque pueden cambiar según la versión.
- La cámara no va dentro de la caja.
- Eigenfaces es sensible a la iluminación: en la demo usar luz fija y uniforme sobre la cara.

### 3.4 Servos SG90

- Alimentación a 5 V. **Nunca desde el pin de 3.3 V**: sus picos de corriente reinician el ESP32.
- La señal sale directo de un GPIO del ESP32 (3.3 V basta).
- Mover un servo a la vez (unos 300 ms entre uno y otro) y poner el capacitor de 470 µF entre 5 V y GND cerca de los servos.
- Librería sugerida: `ESP32Servo`.

### 3.5 Alimentación

- **Plan principal:** todo desde el USB de la laptop. El ESP32 siempre va conectado por USB, porque manda datos a la PC.
- **Si el ESP32 se reinicia** al mover los servos (en el monitor serial aparece "Brownout detector was triggered"): alimentar servos y sensor con un **cargador de celular de 5 V y 2 A**, uniendo su GND con el GND del ESP32.
- **Opción extra:** fuente de 12 V / 2 A con un regulador **XL4015** ajustado a 5.0 V (ajustar con multímetro y sin carga antes de conectar). No es necesario comprarlo si la prueba con USB funciona.
- Con fuente externa: **no** conectar sus 5 V al VIN del ESP32 mientras el ESP32 esté conectado por USB. Solo unir tierras.

---

## 4. Conexiones al ESP32

Pines elegidos para evitar los pines de arranque (0, 2, 5, 12, 15), los de la memoria flash (6 a 11) y UART0 (1 y 3, que usa el USB).

| Componente | Pin del componente | ESP32 |
|---|---|---|
| AS608 | Vi | 5 V (VIN del ESP32 con USB, o fuente externa de 5 V) |
| | GND | GND |
| | TXD | GPIO16 (RX2), directo o con divisor según la medición |
| | RXD | GPIO17 (TX2) |
| Teclado | Filas F1, F2, F3, F4 | GPIO13, 14, 27, 26 |
| | Columnas C1, C2, C3, C4 | GPIO25, 33, 32, 4 |
| OLED | SDA / SCL | GPIO21 / GPIO22 |
| | VCC / GND | 3V3 / GND |
| Servo 1 (compartimento 1) | Señal | GPIO18 |
| Servo 2 (compartimento 2) | Señal | GPIO19 |
| Servos | V+ / GND | 5 V / GND |
| LED verde | Ánodo, con 220 Ω | GPIO23 |
| LED rojo | Ánodo, con 220 Ω | GPIO5 (puede parpadear débil al encender; no afecta) |

```cpp
// Teclado
byte rowPins[4] = {13, 14, 27, 26};
byte colPins[4] = {25, 33, 32, 4};

// Sensor de huella en UART2
Serial2.begin(57600, SERIAL_8N1, 16, 17);  // RX2 = 16, TX2 = 17
```

Si la placa resulta ser WROVER, GPIO16 y 17 están ocupados por la PSRAM: usar otros pines libres para la UART2.

---

## 5. Arquitectura del software

El ESP32 no tiene la capacidad de hacer el procesamiento de imagen. El trabajo se divide así:

| Parte | Dónde corre | Qué hace |
|---|---|---|
| Firmware | ESP32 (Arduino / C++) | Lee el PIN del teclado, captura y manda la imagen de la huella, recibe la decisión, maneja OLED, LEDs y servos |
| Procesamiento | PC (Python) | Recibe la huella, captura el rostro de DroidCam, ejecuta las fases 2 a 4, decide el nivel y le responde al ESP32 |

Comunicación entre ambos por el **puerto serial del USB**. Propuesta de mensajes (por definir en el código):

| Sentido | Mensaje | Significado |
|---|---|---|
| ESP32 → PC | `PIN:<usuario>:<pin>` | PIN capturado |
| ESP32 → PC | `IMG:<bytes>` + datos | Imagen cruda de la huella |
| PC → ESP32 | `MSG:<texto>` | Texto para la OLED (por ejemplo, "Mire a la cámara") |
| PC → ESP32 | `ACCESO:1` / `ACCESO:2` / `ACCESO:0` | Nivel concedido o acceso negado |

**Flujo de una verificación:**
1. El usuario teclea su PIN; el ESP32 lo manda a la PC.
2. La OLED pide la huella; el ESP32 captura la imagen y la manda a la PC.
3. La PC captura el rostro con DroidCam.
4. La PC procesa huella y rostro, combina los puntajes con el PIN y decide el nivel.
5. El ESP32 recibe el nivel: LED verde y abre el servo del compartimento 1 (nivel 1) o de los dos (nivel 2), o LED rojo si se niega.
6. Cada intento se guarda en una bitácora.

**Stack:**
- **PC:** Python con OpenCV, NumPy y scikit-image (y pyserial). La PC de desarrollo es Windows con Python 3.14 y sin CMake ni compilador de C++: evitar librerías que haya que compilar, como dlib o face_recognition.
- **ESP32:** Arduino IDE o PlatformIO, con `Adafruit_Fingerprint` o `FPM`, `Keypad`, `ESP32Servo` y `Adafruit_SSD1306`.
- **Programación:** el código se escribe con **Claude Code** (extensión de VS Code).

---

## 6. Diseño 3D de la caja

Caja impresa en PLA en la impresora de la FIME. Área máxima de impresión: **200 × 200 mm de base y 250 mm de alto**. Todas las piezas caben.

### Distribución

| Zona | Contenido |
|---|---|
| Frente inclinado (41°) | Panel con teclado (izquierda), OLED, LEDs y sensor de huella (derecha) |
| Arriba | Dos compartimentos con tapa abatible: 1 = Lector, 2 = Editor (carpeta de "Compras") |
| Abajo | Cámara de electrónica: ESP32 en zócalos sobre placa perforada, salida USB atrás |

**Medidas exteriores:** unos 170 × 154 × 116 mm, con pared de 2.4 mm.

### Mecanismos

- **Cerrojo de cada tapa:** el brazo de un servo SG90 se pone debajo de un gancho que baja de la tapa. Al conceder acceso, el servo gira 90° y libera la tapa. La fuerza de jalar la tapa no hace girar el servo, solo carga su eje.
- **Las tapas no se abren solas:** hace falta un resorte pequeño o un imán que las empuje, o se levantan con la mano. Pendiente de decidir.
- **Bisagras impresas:** 2 por tapa, con pasador M3 × 16 y tuerca.
- **Panel frontal desmontable:** lengüeta abajo que entra bajo un labio, 2 pares de imanes de neodimio de 6 × 3 mm arriba y repisa perimetral que aguanta la presión al teclear. Los cables del panel deben llegar a la placa con conectores (Dupont o JST), no soldados, con 8 a 10 cm de holgura.
- **Teclado:** pegado con su adhesivo en un bolsillo de 0.8 mm, con ranura para la cinta. Para poder quitarlo: dejar el papel del adhesivo y usar cinta doble cara removible.
- **Sensor AS608:** la zona de la ventana asoma por un hueco del panel (unos 20.5 × 18 mm, por confirmar); el resto queda en una cuna impresa, con costillas en las ranuras laterales del módulo. Dejar 10 mm libres detrás para el conector.
- **OLED:** atornillada por detrás del panel con 4 tornillos M2 × 5; el panel tiene la ventana de la pantalla.
- **Tapa inferior desmontable:** 4 tornillos M3 directo al plástico (barreno de 2.7 mm, sin insertos).
- **Placa perforada:** 4 tornillos M3 directo a postes en la tapa inferior.
- **Pasos de cable:** ranura de la cinta del teclado, hueco del sensor, ventana de la OLED, barrenos de los LEDs, barreno de Ø10 en el piso para cada servo, salida USB de 12 × 8 mm.

### Archivos

- STEP v1 generado con CadQuery (script paramétrico `caja_pia.py`): cuerpo, tapa inferior, tapa 1, tapa 2 y ensamble con piezas de referencia. Ejes iguales a SolidWorks (Y arriba, Z al frente).
- Se edita en **SolidWorks 2025**. El STEP llega sin historial de operaciones.
- Para imprimir se exporta a **STL en milímetros con resolución fina** (o 3MF si el laminador es PrusaSlicer, Bambu Studio u OrcaSlicer).

### Pendiente en el modelo

- Panel desmontable (lengüeta, labio, repisa, cavidades de 6.2 mm para imanes).
- Cuna del AS608 con sus medidas reales.
- Cambiar barrenos de insertos (4 mm) a barrenos de 2.7 mm para tornillo directo.
- Largo de los postes según el largo de los tornillos M3 disponibles (dato pendiente).
- Confirmar con vernier, al tener las piezas: AS608, OLED, teclado (ancho de la cinta) y ESP32.

---

## 7. Plan de trabajo

| Semana | Objetivo |
|---|---|
| 1 | Hardware y captura: probar la imagen cruda del AS608 (SFGDemo y luego FPM), medir el TX del sensor, leer el teclado, leer DroidCam desde Python, probar servos sin reiniciar el ESP32 |
| 2 | Preprocesamiento y extracción: Gabor, binarización y adelgazamiento; Viola-Jones y normalización; minucias y Eigenfaces |
| 3 | Matching y pruebas: grafos de minucias, distancia euclidiana, umbrales con FAR y FRR |
| 4 | Integración y entrega: comunicación ESP32–PC, niveles, servos, bitácora, ensayo de la demo y reporte |

---

## 8. Riesgos

| Riesgo | Qué hacer |
|---|---|
| El AS608 no entrega la imagen cruda | Probarlo antes que nada; plan B con R307 o FPM10 |
| TX del sensor a 5 V daña el ESP32 | Medir antes de conectar; divisor solo si hace falta |
| El ESP32 se reinicia al mover servos | Un servo a la vez, capacitor, y si sigue, cargador de 5 V aparte |
| Huellas de baja calidad | Varias capturas por persona al registrarla; ajustar umbrales |
| Eigenfaces falla con cambios de luz | Normalización fotométrica y luz controlada en la demo |
| Medidas de piezas distintas a las de la hoja de datos | Medir con vernier antes de imprimir |

---

## 9. Indicaciones para Claude Code

- Responder y comentar el código en **español**.
- Los métodos de las fases 2 a 4 están definidos por el PIA: implementarlos, no sustituirlos por redes neuronales ni por el matching interno del sensor.
- Construir por etapas y probar cada módulo con hardware real antes de integrar: primero el sensor, luego el teclado, la cámara, los servos y al final la comunicación completa.
- Mantener separados el firmware del ESP32 y el código de Python de la PC.
- Las medidas marcadas "por confirmar" no son definitivas.
