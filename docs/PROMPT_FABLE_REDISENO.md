# Prompt para Claude Code (Fable 5.2): rediseño estilo Apple de la app y vista por etapas

> Cómo usarlo: abre el repositorio en VS Code (Windows), inicia Claude Code con Fable 5.2 y pega todo lo que está debajo de la línea. Necesita en el repositorio `docs/maqueta/acceso_biometrico.html`, `docs/CONTEXTO_PIA_RDP.md` y `docs/PROMPT_FABLE_5_2.md`.

---

## Contexto

`docs/maqueta/acceso_biometrico.html` es la maqueta del modo **Simular** de la app del PIA (sistema biométrico con PIN, huella y rostro). Es un solo archivo HTML que corre en el navegador. Aunque los datos son sintéticos, los algoritmos sí se ejecutan:
- **Huella:** Gabor, Zhang-Suen, minucias por número de cruce y matching por grafos.
- **Rostro:** PCA con Jacobi y distancia euclidiana.
- **Decisión:** fusión de puntajes.

Tu trabajo es **rediseñarla con el lenguaje visual de Apple** (Human Interface Guidelines y el material de vidrio que Apple llama Liquid Glass), **cambiar el fondo** y **agregar una vista por etapas**. Lo que salga de aquí será la referencia visual que después seguirá la app real (fase 3 de `docs/PROMPT_FABLE_5_2.md`).

Lee primero la maqueta completa y `docs/CONTEXTO_PIA_RDP.md`. Responde, comenta el código y escribe la interfaz en español.

Si en esta sesión están las skills `apple-glassmorphism`, `impecable`, `anti-ia-slop` (o con un nombre parecido), `dataviz` o `humanizer`, cárgalas antes de empezar. Las reglas de abajo ya resumen lo esencial; si alguna skill no existe, no te detengas a preguntar.

## Qué NO cambia

- **Los algoritmos y los números.** No toques la lógica de huella, rostro, PCA ni fusión, salvo para conectarla con la nueva interfaz. Estos resultados tienen que seguir saliendo igual (son tu prueba de regresión):

  | Escenario | Resultado esperado |
  |---|---|
  | Usuario legítimo nivel 1 (ID 07) | Concedido, nivel 1 |
  | Usuario legítimo nivel 2 (ID 12) | Concedido, nivel 2 |
  | Impostor de huella | Negado: la huella no pasa su umbral |
  | Impostor de rostro | Negado: el rostro no pasa su umbral |
  | PIN incorrecto | Negado sin pedir huella ni rostro |

- **La regla de decisión:** cada factor debe pasar su propio umbral (0.50 normalizado) y la suma ponderada 0.5/0.5 debe llegar a 0.60.
- **La honestidad de lo que se muestra:**
  - Se queda el aviso "Datos sintéticos".
  - Ninguna animación inventa datos.
  - El rectángulo de Viola-Jones se sigue presentando como posición conocida del generador, no como una detección real.
- **La réplica de la OLED** sigue siendo de 1 bit y sin acentos, porque la fuente por defecto de Adafruit GFX no los tiene.
- **Todo lo que funciona ahora:** el teclado manual, el modo ESP32 con su error de "no se encontró", las velocidades, el "paso a paso" y la bitácora.

## 1. Lenguaje visual de Apple

Aplica los principios de la HIG: el contenido es lo principal, la interfaz se retira (deferencia), hay jerarquía clara y la profundidad tiene significado. Aquí el contenido son la huella, el rostro y los puntajes; los controles son secundarios.

### Color

Usa el sistema semántico de Apple para modo oscuro, como tokens:
- **Fondos:** `systemBackground`, `secondarySystemBackground` y `tertiarySystemBackground`.
- **Texto:** `label`, `secondaryLabel` y `tertiaryLabel`.
- **Rellenos y líneas:** `separator` y `fill`.
- **Estados:** `systemGreen`, `systemRed` y `systemOrange`.

Los valores de referencia de la HIG para modo oscuro son estos. Verifícalos antes de usarlos y no los presentes como "oficiales" si no los confirmaste:

| Token | Valor |
|---|---|
| Fondos | `#000000`, `#1C1C1E`, `#2C2C2E` |
| `label` | `#FFFFFF` |
| `secondaryLabel` | `rgba(235,235,245,.6)` |
| `tertiaryLabel` | `rgba(235,235,245,.3)` |
| `separator` | `rgba(84,84,88,.65)` |
| `systemGreen` | `#30D158` |
| `systemRed` | `#FF453A` |
| `systemOrange` | `#FF9F0A` |

Reglas:
- **Los grises son neutros.** Quita el matiz verde que hoy tienen los neutros de la maqueta.
- **Un solo color de acento, como el "tint" de las apps de Apple:** el verde FIME (`--verde-fime`, valor provisional por confirmar). Va en el control seleccionado, el botón principal, el paso activo y los elementos interactivos.
- **Éxito y error usan `systemGreen` y `systemRed`.** Como el éxito y el acento son verdes, distínguelos siempre por algo más que el color: icono, texto o forma.
- **Nada de colores fuera de este sistema.** Las visualizaciones (minucias, histogramas, distribuciones) usan el acento y los colores de estado; las bifurcaciones van en `systemOrange`.

### Tipografía

- **No uses SF Pro ni SF Mono.** Su licencia no permite usarlas en una app web que corre en Windows, y en Windows `-apple-system` no existe. Usa **Inter** (la sustituta habitual de SF) para la interfaz y **JetBrains Mono** para los datos. Guárdalas localmente en `docs/maqueta/fonts/` con su licencia, porque la demo debe funcionar sin internet. Quita el enlace a Google Fonts.
- **Escala inspirada en la de macOS**, un poco más grande porque se va a proyectar: 28 (título) / 20 / 17 (encabezado de panel, semibold) / 15 (cuerpo) / 13 (secundario) / 12 (etiquetas).
- **Números tabulares** en todo lo que cambia.
- **Sin etiquetas en mayúsculas con espaciado ancho** en todas partes. Apple usa poco las versalitas; déjalas solo para encabezados de grupo muy pequeños, si acaso.

### Forma

- **Radios concéntricos:** el radio interno es el radio externo menos el padding. Esto es central en el lenguaje actual de Apple.
- **Controles en cápsula:** botones, controles segmentados y chips de estado.
- **Objetivos táctiles de al menos 44 px.**
- **Espaciado en múltiplos de 4 y 8.**
- **Iconos de línea**, de 1.5 a 2 px y con terminaciones redondeadas. Usa un set abierto como Lucide (ISC), guardado localmente; no copies SF Symbols. Nada de emojis.

## 2. Vidrio (aproximación de Liquid Glass en web)

En la web no existe el material real de Apple; lo que se construye con CSS es una aproximación. Además, Apple ya bajó la transparencia en sus versiones recientes, así que **no la exageres**.

- **Dónde sí:** en lo que flota sobre el contenido:
  - La barra de herramientas superior (fija, con el contenido pasando por debajo al hacer scroll).
  - Los controles segmentados.
  - El navegador de etapas (sección 4).
  - La píldora de explicación de abajo.
  - El panel del modo ESP32 y cualquier modal.
- **Dónde no:** en las superficies de datos (huella, cámara, eigenfaces, gráficas). Van sobre superficies opacas `secondarySystemBackground` para que las imágenes conserven su contraste.
- **Receta:**
  - Fondo `rgba` neutro con alfa de 0.18 a 0.35 (más opaco en la barra superior, 0.6 a 0.75, para que se lea).
  - `backdrop-filter: blur(20–30px) saturate(140–160%)`, con `-webkit-`.
  - Borde de 1 px con `rgba(255,255,255,.08–.15)`.
  - Borde especular (degradado en el canto) solo en la barra superior y en el navegador de etapas.
  - Sombra difusa.
- **Límites:**
  - Máximo dos capas de vidrio encimadas.
  - Respaldo casi opaco cuando no hay `backdrop-filter` o con `prefers-reduced-transparency`.
  - No pongas vidrio encima de canvas que se están animando.
  - No uses filtros SVG de refracción o desplazamiento salvo que compruebes que corren a 60 fps en Chrome y Edge en Windows. Si no, déjalos fuera.

## 3. Fondo nuevo

Quita la retícula y los dos manchones verdes radiales que tiene ahora la maqueta. El nuevo fondo debe verse profesional y darle al vidrio algo que difuminar:

- **Base:** casi negra y neutra.
- **Encima:** 2 o 3 campos de color grandes y muy difuminados, con poca saturación: un verde FIME profundo y un azul petróleo o gris azulado oscuro, colocados para que queden detrás de la barra superior y de la píldora inferior. La idea son los fondos de escritorio oscuros de macOS, no una aurora llamativa.
- **Remate:** grano muy fino (opacidad de 2 a 4 %) para evitar el banding, y una viñeta suave.
- **Estático.** Si quieres algo de movimiento, que sea una deriva lentísima (ciclo de 60 s o más), desactivada con `prefers-reduced-motion`. Pero el estático es preferible: así el blur no recalcula en cada cuadro.
- **Hecho una sola vez:** con degradados de CSS o un canvas o WebP pre-renderizado, no recalculado.
- Debe verse bien en una laptop de 1366 × 768 y en un proyector de 1920 × 1080.
- **Contraste:** el texto sobre vidrio, en el punto más claro del fondo, debe tener al menos 4.5:1. Mídelo.

**Propón dos variantes del fondo**, con capturas de cada una en las dos vistas, y **espera a que yo elija** antes de seguir con lo demás.

## 4. Nueva vista por etapas

Agrega a la barra superior un control segmentado **"Vista: Completa | Por etapa"**.
- **Completa** es la de ahora: todos los paneles a la vez.
- **Por etapa** muestra **solo la etapa actual** a todo lo ancho, con las visualizaciones más grandes.

Recuerda la elección con `localStorage`, con try/catch, y si falla, la vista por defecto es Completa.

**Etapas y contenido:**

| # | Etapa | Contenido |
|---|---|---|
| 1 | PIN | OLED, LEDs, casillas de ID y PIN, teclado (más grande) y tráfico serie |
| 2 | Huella | Captura y plantilla lado a lado y grandes, tira de etapas y métricas |
| 3 | Rostro | Cámara grande, alineado, normalizado, histograma, eigenfaces, pesos, reconstrucción y distancia |
| 4 | Actuación | Fusión, veredicto, compartimentos con servos y la fila nueva de la bitácora (con acceso a la bitácora completa) |

**Navegador de etapas** (vidrio, en cápsula, debajo de la barra superior):
- Cuatro pasos. Cada uno muestra su estado: pendiente, en curso, aprobado o rechazado (con icono y forma, no solo color) y su dato clave al terminar, por ejemplo "Huella 0.81" o "Rostro d = 1.78".
- El indicador del paso activo se desliza de un paso al otro, como el selector de un control segmentado de Apple.
- Dentro de Huella y Rostro sigue visible el indicador de las fases 1 a 4 del PIA.

**Comportamiento:**
- **Durante una verificación**, la vista sigue sola el flujo: PIN → Huella → Rostro → Actuación. Si el PIN es incorrecto, salta directo a Actuación.
- **Antes de empezar las animaciones de una etapa, el orquestador espera a que termine la transición.** Nada se anima fuera de la vista.
- **Si el usuario se regresa a una etapa anterior durante la verificación**, la vista deja de seguir el flujo y aparece una cápsula "En curso: Rostro" para volver.
- **Al terminar**, se puede recorrer con clic en el navegador o con las flechas ← y →.
- **Funciona igual** con todas las velocidades, con el "paso a paso", con el teclado manual y en modo ESP32.
- **Sin DOM duplicado:** las dos vistas usan los mismos paneles y el mismo estado; solo cambia el acomodo (por ejemplo, con un atributo `data-vista` en la rejilla). Al mostrar un panel, vuelve a dibujar lo que depende del tamaño, como las líneas del matching.

**Transición:**
- Usa la **View Transitions API** (`document.startViewTransition`), que existe en Chrome y Edge.
- **Hacia adelante:** la etapa nueva entra desde la derecha con un poco de escala y desenfoque mientras la anterior sale hacia la izquierda. **Hacia atrás**, al revés.
- **Duración** de 450 a 550 ms, con una curva de salida tipo Apple (`cubic-bezier(.32,.72,0,1)`), sin rebote exagerado.
- **Morphing:** el indicador del navegador y el título del panel pasan de una etapa a la otra con `view-transition-name`.
- **Sin la API:** respaldo con opacidad y `transform`.
- **Con `prefers-reduced-motion`:** solo un fundido de 150 ms.

## 5. Movimiento

- Respuesta de los controles de 150 a 250 ms, revelado de resultados de 400 a 1200 ms y transiciones de etapa de 450 a 550 ms.
- Curvas tipo resorte, suaves.
- Nada se mueve por adorno. Lo único que se repite sin fin es el indicador discreto de "esperando".
- Revisa que las transiciones vayan a 60 fps: mide los cuadros con `requestAnimationFrame` o con el panel Performance y reporta el resultado.

## 6. Cómo verificar y entregar

1. **Fondo primero:** las dos variantes, con capturas, y te detienes a esperar mi elección.
2. **Después, el rediseño completo y la vista por etapas.** Verifica con Playwright si está disponible (si no, dime exactamente qué abrir y qué revisar):
   - Los cinco escenarios de la tabla dan el resultado esperado, en las dos vistas.
   - Cero errores en la consola.
   - No hay scroll horizontal a 1440 × 900, 1366 × 768 y 390 × 844.
   - Capturas de las dos vistas a 1440 × 900 y de la vista por etapas en cada una de sus 4 etapas.
   - Un video o GIF corto de una verificación completa en la vista por etapas.
   - Una prueba con `prefers-reduced-motion` y otra con `prefers-reduced-transparency` emulados.
   - Contraste medido del texto sobre vidrio.
   - Funciona sin internet: corta la red y recarga.
3. **Commit** con mensaje en español y un resumen con: qué cambió, qué verificaste (con la evidencia), qué no pudiste verificar y las decisiones que tomaste por tu cuenta.
4. **Actualiza la sección "Diseño de la app" de `docs/PROMPT_FABLE_5_2.md`** para que apunte a esta maqueta como referencia aprobada de la fase 3.

Si algo de este prompt choca con lo que encuentres (un valor de color que no coincide con la HIG, una API que no funciona en Edge, una fuente sin licencia libre), detente y pregúntame en lugar de resolverlo en silencio.
