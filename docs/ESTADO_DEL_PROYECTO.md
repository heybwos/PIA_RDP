# Estado del proyecto: PIA de Reconocimiento de Patrones

Este archivo resume en qué va el proyecto: qué se decidió, qué está hecho y qué sigue. Sirve para retomar el trabajo en otra PC o en una sesión nueva de Claude Code.

Última actualización: 13 de noviembre de 2026.

**Orden de lectura para retomar:**
1. Este archivo.
2. `docs/CONTEXTO_PIA_RDP.md`, que trae el hardware, los pines, los métodos obligatorios y los riesgos. Donde los dos se contradigan, este archivo es el más reciente.

---

## 1. Resumen en una tabla

| Parte | Estado |
|---|---|
| Contexto del proyecto | Listo (`docs/CONTEXTO_PIA_RDP.md`) |
| Prompt para construir el sistema completo | Listo, sin ejecutar (`docs/PROMPT_FABLE_5_2.md`) |
| Maqueta visual del modo Simular | **Terminada.** Rediseñada al estilo Apple y cerrada con mediciones en Windows (`docs/maqueta/acceso_biometrico.html`) |
| Revisión crítica del rediseño | Lista (`docs/REVISION_REDISENO.md`, 24 puntos) |
| Sistema real (Python, firmware, app conectada) | **No empezado.** No hay código del sistema todavía, solo documentos y la maqueta. |
| Pruebas con hardware | **No empezadas.** El hardware no se ha conectado. |

## 2. Decisiones tomadas

Resuelven lo que el contexto original dejaba pendiente. No hay que volver a discutirlas, salvo que aparezca un dato nuevo.

| Tema | Decisión |
|---|---|
| Tipo de app | **Web local:** Python (FastAPI + WebSocket) procesa y sirve la interfaz, y la interfaz corre en el navegador (`localhost`). Debe funcionar sin internet. El frontend no lleva Node ni paso de build. |
| Niveles | **Los tres factores son obligatorios** para todos. El nivel (1 Lector, 2 Editor) es un atributo del usuario registrado. |
| Identidad | **Verificación 1:1:** ID de 2 dígitos + `#`, luego PIN de 4 dígitos + `#`. `*` borra y `D` cancela. |
| Regla de acceso | Se concede si el PIN es correcto, **cada factor pasa su propio umbral** (0.50 normalizado) **y** la suma ponderada 0.5/0.5 llega a **0.60**. La regla anterior (piso de 0.35 y fusión de 0.50) dejaba pasar a un impostor de rostro con buena huella; se cambió por eso. |
| Modo Simular | Usa datasets públicos con el pipeline real: huella de **FVC2002** (subconjuntos B); rostro de **ORL/AT&T** o **LFW**, eligiendo el que dé mejor tasa de detección de Viola-Jones medida. El teclado se simula en pantalla. |
| Quién manda | **La PC orquesta** todo el flujo; el ESP32 es un periférico. Si la PC deja de responder 5 s, el ESP32 niega el acceso y no abre nada. |
| Comunicación | USB a **921600 baudios** (configurable, respaldo de 115200). El sensor se sube a 115200 si lo acepta: a 57600 la imagen tarda unos 6.4 s y a 115200 unos 3.2 s. La imagen se reenvía mientras llega del sensor, enmarcada con `IMG:<bytes>:<crc32>` … `IMG:FIN`. Cada tecla se manda al momento (`TECLA:<c>`). |
| OLED | Sin acentos, porque la fuente por defecto de Adafruit GFX no los tiene. |
| Firmware | **PlatformIO**, con entornos de prueba por módulo. |
| Dónde se programa | Claude Code con **Fable 5.2**, en VS Code y Windows, **por fases**, deteniéndose al final de cada una para revisión. |
| Estilo visual | Lenguaje de **Apple (HIG) en modo oscuro**, con grises neutros y el **verde FIME como único acento** (valor provisional). Vidrio solo en lo que flota; los datos van sobre superficies opacas. Letras Inter y JetBrains Mono, guardadas localmente. |
| Vista por etapas | Control "Vista: Completa \| Por etapa". En "Por etapa" se ve solo la etapa actual: PIN → Huella → Rostro → Actuación, con transiciones animadas. **La maqueta arranca en "Por etapa"**; recuerda la última vista elegida, y `?vista=completa` en la URL abre la completa sin guardarla. |
| Pantalla de la demo | Navegador en **pantalla completa (F11)** y en modo Simular. El alto mínimo soportado sin scroll es 768 px de viewport. |

## 3. La maqueta (`docs/maqueta/acceso_biometrico.html`)

Es un solo HTML que se abre con doble clic, sin servidor ni internet. Muestra la app en modo Simular.

**Qué es real y qué no:**
- **Real (se calcula en el navegador):**
  - Huella: Gabor orientado, adelgazamiento de Zhang-Suen, minucias por número de cruce y matching por grafos de 4 vecinos.
  - Rostro: PCA con eigenvectores (Jacobi) y distancia euclidiana con umbral sacado de FAR/FRR.
  - Decisión: fusión de puntajes.
- **Sintético:** las huellas y las caras las genera la página; no son datasets reales.
- **Viola-Jones no se ejecuta:** el rectángulo del rostro y los ojos son las posiciones conocidas del generador, y la página lo dice.

**Números de la maqueta.** Son de datos sintéticos y no sirven como umbrales del sistema real.

| Dato | Valor |
|---|---|
| Umbral de huella | 0.30. El puntaje es m² / (nA · nB), con m = pares en correspondencia. |
| Eigenfaces | k = 38 para el 95.1 % de la varianza; 72 imágenes de entrenamiento (12 identidades × 6). |
| Umbral de rostro | Distancia ≈ 4.93, con EER ≈ 1.4 % en los datos sintéticos. |

**Usuarios de prueba:**

| ID | Usuario | Nivel | PIN |
|---|---|---|---|
| 07 | Ana T. | 1 (Lector) | 4821 |
| 12 | Luis G. | 2 (Editor) | 1593 |

**Escenarios y resultado esperado.** `docs/maqueta/pruebas/regresion.js` los comprueba y todos pasan.

| Escenario | Resultado esperado |
|---|---|
| Usuario legítimo de nivel 1 | Concedido, nivel 1 |
| Usuario legítimo de nivel 2 | Concedido, nivel 2 |
| Impostor de huella | Negado |
| Impostor de rostro | Negado |
| PIN incorrecto | Negado |

**Cambiar de fondo:** en la línea 2 del HTML, `data-fondo="a"` pasa a `"b"`. Está elegido el A.

**Link publicado:** https://claude.ai/artifact/ByghMje85waN9nQ8px4T8r. Muestra la versión final (rediseño y cierre), con las fuentes Inter y JetBrains Mono publicadas junto a la página. Es privado: para que otros lo abran hay que compartirlo desde el menú Share de la página.

## 4. Estado de la maqueta (rediseño y cierre)

Fable 5.2 hizo el rediseño y lo verificó en un contenedor Linux sin GPU. El cierre se hizo en Windows con GPU real: Fable 5.2 dio el plan, los criterios y la verificación, y Opus 5.5 ejecutó los cambios. El detalle está en `docs/REVISION_REDISENO.md`, sección 4.

**Hecho y probado:**
- Los cinco escenarios dan exactamente los mismos números que antes del cierre (15 casos: 5 escenarios × semillas 11, 4242 y 7).
- **Transiciones fluidas en Windows:** el cuadro más largo dura 19 ms. Los 11–14 cuadros por segundo eran del contenedor sin GPU; no hace falta bajar el desenfoque.
- **Todas las etapas caben sin scroll** en 1280×800, 1366×768, 1440×900, 1536×864 y 1920×1080 (el proyector), con al menos 12 px de margen sobre el pie.
- La `σ` se cambió por texto; no queda ningún carácter fuera de las fuentes locales.
- Las flechas del teclado se anuncian junto al navegador de etapas ("Cambiar de etapa", desde 1280 px de ancho).
- La maqueta arranca en "Por etapa".
- Cero errores en la consola, incluso con la pestaña oculta durante una verificación, y cero peticiones externas.
- Sin scroll horizontal; la vista completa quedó idéntica al píxel.
- Evidencia del rediseño: 9 capturas JPEG y un video de 43 s en `docs/maqueta/capturas/`.

**Límites conocidos:**
- Con menos de 768 px de alto de viewport (ventana sin maximizar) o con el panel del modo ESP32 abierto, las etapas necesitan scroll.
- Sin probar: navegador sin `backdrop-filter` y lectores de pantalla.

**Pendiente, fuera del código:**
1. El verde FIME sigue provisional: hay que confirmar el valor oficial. Se cambia solo `--verde-fime` (línea 33) y hay que volver a medir el contraste del texto oscuro sobre el verde.
2. Unos 28 PNG pesados (unos 15 MB) quedaron en el historial de git por un commit de punto de control. Ya no están en los archivos, pero siguen ocupando espacio al clonar. Recomendación: no reescribir la rama; usar squash al hacer el PR.

**Decisiones que tomó Fable y conviene revisar:**
- Texto oscuro sobre el verde FIME, porque el blanco daba 3.4:1.
- Vidrio al 0.75 en la barra, el navegador de etapas y el pie, por legibilidad.
- La verificación no se pausa si el usuario se regresa a una etapa anterior.
- El navegador de etapas también aparece en la vista completa.
- Fases 1 a 4 dentro de cada panel (huella y rostro), en lugar de un solo indicador en la barra.
- La vista por etapas arranca en la etapa 4, con la verificación de ejemplo ya resuelta.
- En la vista por etapa la bitácora se compacta y, con poco alto (≤ 800 px), se reducen algunos márgenes y la OLED, para que todo quepa.
- `systemRed` y `systemOrange` se ajustaron a la guía actual de Apple: `#FF4245` y `#FF9230`.

## 5. Archivos del repositorio

| Ruta | Qué es |
|---|---|
| `docs/ESTADO_DEL_PROYECTO.md` | Este archivo |
| `docs/CONTEXTO_PIA_RDP.md` | Contexto original: materia, hardware, pines, métodos y riesgos |
| `docs/PROMPT_FABLE_5_2.md` | Prompt para construir el sistema completo por fases (0 a 5) |
| `docs/PROMPT_FABLE_REDISENO.md` | Prompt del rediseño, ya corregido con la revisión |
| `docs/REVISION_REDISENO.md` | Revisión crítica y tablas de verificación del rediseño |
| `docs/maqueta/acceso_biometrico.html` | Maqueta rediseñada |
| `docs/maqueta/fonts/`, `docs/maqueta/icons/` | Fuentes e iconos locales, con licencias |
| `docs/maqueta/capturas/` | Capturas y video de la verificación |
| `docs/maqueta/pruebas/regresion.js` | Prueba de los cinco escenarios |

La rama de trabajo es `claude/exciting-davinci-aqy6kg` en `heybwos/PIA_RDP`. No se ha abierto ningún pull request.

## 6. Siguientes pasos, en orden

1. **Semana 1 del plan (hardware):** son las primeras pruebas y no dependen del software:
   - Probar la imagen cruda del AS608 con SFGDemo.
   - Medir el TX del sensor contra GND antes de conectarlo al ESP32.
   - Leer el teclado, leer DroidCam desde Python y mover los servos sin que se reinicie el ESP32.
2. **Ejecutar `docs/PROMPT_FABLE_5_2.md` desde la fase 0** (entorno y dependencias en Python 3.14). Revisar al final de cada fase.
3. **Calibrar de nuevo los umbrales con huellas reales del AS608.** Los de los datasets no sirven tal cual para ese sensor.
4. **Confirmar el verde FIME** y, si cambia, volver a medir el contraste de la maqueta.

## 7. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| El AS608 no entrega la imagen cruda | Sin probar. Es lo primero. Plan B: R307 o FPM10. |
| El orden de los nibbles de la imagen de 4 bits | Sin confirmar. El prompt pide hacerlo configurable y detectarlo con una prueba. |
| Algunas dependencias de Python no tienen wheel para 3.14 | Sin verificar. El prompt pide comprobarlo en la fase 0, con respaldo en Python 3.13. |
| Viola-Jones no detecta las caras recortadas de ORL | Sin medir. El prompt pide medirlo y, si falla, usar LFW. |
| Rendimiento del vidrio en la laptop de la demo | Medido en Windows con GPU: cuadro más largo de 19 ms en las transiciones. Si la laptop de la demo es otra, conviene repetir la prueba. |
| El cerrojo del servo choca con el gancho si la tapa se cierra trabada | Sin revisar en el diseño 3D. |

## 8. Cómo retomar con Claude Code

En la PC nueva, abre una terminal en la carpeta donde quieras el proyecto.

Baja el proyecto:
```bash
git clone -b claude/exciting-davinci-aqy6kg https://github.com/heybwos/PIA_RDP.git
```

Entra a la carpeta:
```bash
cd PIA_RDP
```

Abre la carpeta en VS Code e inicia Claude Code con Fable 5.2. Para empezar el sistema, pega `docs/PROMPT_FABLE_5_2.md`. La maqueta ya está terminada; para verla, abre `docs/maqueta/acceso_biometrico.html` con doble clic.
