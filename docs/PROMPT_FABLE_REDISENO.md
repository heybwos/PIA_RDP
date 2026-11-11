# Prompt para Claude Code (Fable 5.2): rediseño estilo Apple de la app y vista por etapas

> Cómo usarlo: abre el repositorio, inicia Claude Code con Fable 5.2 y pega todo lo que está debajo de la línea. Necesita en el repositorio `docs/maqueta/acceso_biometrico.html`, `docs/CONTEXTO_PIA_RDP.md` y `docs/PROMPT_FABLE_5_2.md`.
>
> Este prompt ya se ejecutó una vez (11 nov 2026). Las ambigüedades que tenía y cómo se resolvieron están en `docs/REVISION_REDISENO.md`; esta versión ya las incorpora.

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
- **El gancho de pruebas:** la página expone `window.__pia`. Con `__pia.S.instant=true` y `await __pia.run(__pia.SCN.l1,{seed:11})` corre una verificación instantánea y el resultado queda en `__pia.S.lastResult`, que debe llenarse también cuando el PIN falla.
- **Se abre con doble clic, sin servidor.** Es un documento HTML completo (`<!doctype>`, `lang="es"`, charset y `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`). Nada se carga desde una CDN.

## 1. Lenguaje visual de Apple

Aplica los principios de la HIG: el contenido es lo principal, la interfaz se retira (deferencia), hay jerarquía clara y la profundidad tiene significado. Aquí el contenido son la huella, el rostro y los puntajes; los controles son secundarios.

### Color

Usa el sistema semántico de Apple para modo oscuro, como tokens:
- **Fondos:** `systemBackground`, `secondarySystemBackground` y `tertiarySystemBackground`.
- **Texto:** `label`, `secondaryLabel` y `tertiaryLabel`.
- **Rellenos y líneas:** `separator` y `fill`.
- **Estados:** `systemGreen`, `systemRed` y `systemOrange`.

Valores de referencia para modo oscuro. Los tres colores de estado se confirmaron en la tabla "System colors" de la HIG el 11 nov 2026; vuelve a revisarlos si pasó tiempo. Los fondos, los textos y el separador no están en la HIG: son valores de UIKit medidos por la comunidad, así que no los presentes como oficiales.

| Token | Valor |
|---|---|
| Fondos | `#000000`, `#1C1C1E`, `#2C2C2E` |
| `label` | `#FFFFFF` |
| `secondaryLabel` | `rgba(235,235,245,.6)` |
| `tertiaryLabel` | `rgba(235,235,245,.3)` |
| `separator` | `rgba(84,84,88,.65)` |
| `systemGreen` | `#30D158` |
| `systemRed` | `#FF4245` |
| `systemOrange` | `#FF9230` |

Reglas:
- **Los grises son neutros.** Quita el matiz verde que hoy tienen los neutros de la maqueta, también en las imágenes de la huella (fondo, máscara y esqueleto).
- **Un solo color de acento, como el "tint" de las apps de Apple:** el verde FIME (`--verde-fime`, valor provisional `#1F9F5C`, por confirmar). Va en el control seleccionado, el botón principal, el paso activo y los elementos interactivos.
  - Como relleno lleva **texto oscuro**: el blanco sobre este verde da 3.4:1.
  - Para texto y trazos finos sobre oscuro usa un **acento claro derivado del mismo token** (el verde con 38 % de blanco, calculado, no escrito a mano), porque el verde directo da 4.1:1 sobre `#2C2C2E`.
- **`tertiaryLabel` no se usa en texto** (2.5:1). Todo el texto va en `label` o `secondaryLabel`.
- **Éxito y error usan `systemGreen` y `systemRed`.** Como el éxito y el acento son verdes, distínguelos siempre por algo más que el color: icono, texto o forma.
- **Nada de colores fuera de este sistema.** Las visualizaciones (minucias, histogramas, distribuciones) usan el acento y los colores de estado; las bifurcaciones van en `systemOrange`.

### Tipografía

- **No uses SF Pro ni SF Mono.** Su licencia no permite usarlas en una app web que corre en Windows, y en Windows `-apple-system` no existe. Usa **Inter** (la sustituta habitual de SF) para la interfaz y **JetBrains Mono** para los datos. Guárdalas localmente en `docs/maqueta/fonts/` con su licencia (paquetes `@fontsource/inter` y `@fontsource/jetbrains-mono`, subconjunto `latin`, pesos 400, 500 y 600, en `.woff2`) y cárgalas con `@font-face` y rutas relativas, porque la demo debe funcionar sin internet. Quita el enlace a Google Fonts. El subconjunto `latin` no trae flechas (`→`, `←`) ni letras griegas (`σ`): no las uses en los textos. Los canvas que escriben texto (la OLED, la cámara) deben esperar a que cargue la fuente.
- **Escala inspirada en la de macOS**, un poco más grande porque se va a proyectar: 28 (título) / 20 / 17 (encabezado de panel, semibold) / 15 (cuerpo) / 13 (secundario) / 12 (etiquetas).
- **Números tabulares** en todo lo que cambia.
- **Sin etiquetas en mayúsculas con espaciado ancho** en todas partes. Apple usa poco las versalitas; déjalas solo para encabezados de grupo muy pequeños, si acaso.

### Forma

- **Radios concéntricos:** el radio interno es el radio externo menos el padding, como variable CSS. El padding tiene que ser menor que el radio (por ejemplo, radio 24 y padding 16) para que el interno no dé 0.
- **Controles en cápsula:** botones, controles segmentados y chips de estado.
- **Objetivos táctiles de al menos 44 px.** Un control puede verse más bajo si su zona de toque llega a 44 px.
- **Espaciado en múltiplos de 4 y 8.**
- **Iconos de línea**, de 1.5 a 2 px y con terminaciones redondeadas. Usa Lucide (ISC, paquete `lucide-static`): los iconos van en línea como SVG y los originales, con su licencia, en `docs/maqueta/icons/`. No copies SF Symbols. Nada de emojis.

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
  - Fondo `rgba` neutro con alfa de 0.18 a 0.35 **solo en lo que tiene únicamente el fondo detrás** (selector, velocidad, botón secundario, panel ESP32). En lo que recibe contenido por debajo al hacer scroll (barra, navegador y pie), 0.7 a 0.75, y el texto secundario sobre ese vidrio sube a 0.82 de opacidad.
  - `backdrop-filter: blur(20–30px) saturate(140–160%)`, con `-webkit-`.
  - Borde de 1 px con `rgba(255,255,255,.08–.15)`.
  - Borde especular (degradado en el canto) solo en la barra superior y en el navegador de etapas.
  - Sombra difusa.
- **Límites:**
  - Máximo dos capas de vidrio encimadas, y solo una con `backdrop-filter`: los controles que van dentro de la barra llevan un relleno translúcido, no su propio blur (anidado no difumina nada).
  - Respaldo casi opaco cuando no hay `backdrop-filter` o con `prefers-reduced-transparency`.
  - Evita el vidrio encima de canvas que se están animando: en la vista por etapa, ajusta las visualizaciones al alto libre para que no queden bajo el pie. En la vista completa es inevitable; mide el costo.
  - No uses filtros SVG de refracción o desplazamiento salvo que compruebes que corren a 60 fps en Chrome y Edge en Windows. Si no, déjalos fuera.

## 3. Fondo nuevo

Quita la retícula y los dos manchones verdes radiales que tiene ahora la maqueta. El nuevo fondo debe verse profesional y darle al vidrio algo que difuminar:

- **Base:** casi negra y neutra.
- **Encima:** 2 o 3 campos de color grandes y muy difuminados, con poca saturación: un verde FIME profundo y un azul petróleo o gris azulado oscuro, colocados para que queden detrás de la barra superior y de la píldora inferior. La idea son los fondos de escritorio oscuros de macOS, no una aurora llamativa.
- **Remate:** grano muy fino (opacidad de 2 a 4 %) para evitar el banding, y una viñeta suave.
- **Estático.** Si quieres algo de movimiento, que sea una deriva lentísima (ciclo de 60 s o más), desactivada con `prefers-reduced-motion`. Pero el estático es preferible: así el blur no recalcula en cada cuadro.
- **Hecho una sola vez:** con degradados de CSS o un canvas o WebP pre-renderizado, no recalculado.
- Debe verse bien en una laptop de 1366 × 768 y en un proyector de 1920 × 1080.
- **Contraste:** el texto sobre vidrio debe tener al menos 4.5:1, tanto en el punto más claro del fondo como en el peor caso real, que es la huella cruda (casi blanca) pasando por debajo de la barra y del navegador. Mide los dos.

**Haz dos variantes del fondo**, con una captura de cada una. Elige la mejor con una justificación y deja la otra disponible con `data-fondo="a"` o `data-fondo="b"` en `<html>`. No te detengas a esperar mi elección: la reviso al final. (En la primera ejecución quedaron A, "Bosque y petróleo", que es la elegida, y B, "Grafito".)

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
| 4 | Actuación | Fusión, veredicto, compartimentos con servos y el panel de la bitácora, que en esta vista muestra solo el último registro y un botón para ver la bitácora completa |

**Navegador de etapas** (vidrio, en cápsula, debajo de la barra superior). Se ve en las dos vistas; en la completa, elegir un paso desplaza la página hasta su panel:
- Cuatro pasos. Cada uno muestra su estado: pendiente, en curso, aprobado, rechazado o "no se pidió" (con icono y forma, no solo color) y su dato clave al terminar, por ejemplo "Huella 0.81" o "Rostro d = 1.78".
- El indicador del paso activo se desliza de un paso al otro, como el selector de un control segmentado de Apple.
- Huella y Rostro llevan cada uno, en el encabezado de su panel, su propio indicador de las fases 1 a 4 del PIA, porque cada factor avanza por separado. PIN y Actuación llevan una etiqueta fija ("Fase 1 · Captura", "Fase 5 · Actuación").

**Comportamiento:**
- **Durante una verificación**, la vista sigue sola el flujo: PIN → Huella → Rostro → Actuación. Si el PIN es incorrecto, salta directo a Actuación.
- **Antes de empezar las animaciones de una etapa, el orquestador espera a que termine la transición.** Mientras la vista sigue el flujo, nada se anima fuera de la vista. En la vista completa, el equivalente es desplazar la página hasta el panel activo.
- **Si el usuario se regresa a una etapa anterior durante la verificación**, la vista deja de seguir el flujo y aparece una cápsula "En curso: Rostro" para volver. **La verificación no se pausa**: sigue en segundo plano, igual que el dispositivo real. En la vista completa pasa lo mismo si el usuario mueve la página.
- **En cualquier momento** se puede recorrer con clic en el navegador o con las flechas izquierda y derecha del teclado (salvo cuando el foco está en un selector o un campo).
- **Funciona igual** con todas las velocidades, con el "paso a paso", con el teclado manual y en modo ESP32.
- **Sin DOM duplicado:** las dos vistas usan los mismos paneles y el mismo estado; solo cambia el acomodo (por ejemplo, con un atributo `data-vista` en la rejilla). Al mostrar un panel, vuelve a dibujar lo que depende del tamaño, como las líneas del matching.

**Transición:**
- Usa la **View Transitions API** (`document.startViewTransition`), que existe en Chrome y Edge.
- **Hacia adelante:** la etapa nueva entra desde la derecha con un poco de escala y desenfoque mientras la anterior sale hacia la izquierda. **Hacia atrás**, al revés.
- **Duración** de 450 a 550 ms, con una curva de salida tipo Apple (`cubic-bezier(.32,.72,0,1)`), sin rebote exagerado. No se escala con la velocidad de la simulación.
- **La barra, el navegador y el pie** llevan su propio `view-transition-name` para que la etapa no pase por encima de ellos al deslizarse.
- **Morphing:** el indicador del navegador y el título del panel pasan de una etapa a la otra con `view-transition-name`.
- **Sin la API:** respaldo con opacidad y `transform`. Debe poder forzarse para probarlo (por ejemplo, con `?sinvt=1`).
- **Con `prefers-reduced-motion`:** solo un fundido de 150 ms.

## 5. Movimiento

- Respuesta de los controles de 150 a 250 ms, revelado de resultados de 400 a 1200 ms y transiciones de etapa de 450 a 550 ms.
- Curvas tipo resorte, suaves.
- Nada se mueve por adorno. Lo único que se repite sin fin es el indicador discreto de "esperando".
- Revisa que las transiciones vayan a 60 fps: mide los cuadros con `requestAnimationFrame` y reporta el número, junto con el renderizador (GPU o software). En un equipo sin GPU la medición no vale para la demo: dilo. En la primera ejecución, sin GPU, dio 11 a 14 cuadros; falta medirlo en la laptop de la demo.

## 6. Cómo verificar y entregar

1. **Revisión crítica antes de programar.** Lee el prompt y la maqueta como un revisor exigente. Anota ambigüedades, contradicciones, supuestos débiles y riesgos, decide cada uno y distingue lo que verificaste de lo que supones. Si ya existe `docs/REVISION_REDISENO.md`, actualízalo en lugar de empezar de cero.
2. **Fondo:** las dos variantes, una captura de cada una y tu elección justificada. No te detengas.
3. **Después, el rediseño completo y la vista por etapas.** Verifica con Playwright (si no está disponible, dime exactamente qué abrir y qué revisar):
   - Los cinco escenarios de la tabla dan el resultado esperado, en las dos vistas, y los números coinciden con los de la maqueta anterior con la misma semilla.
   - En la vista por etapa, la secuencia de etapas es 1, 2, 3, 4 (o 1, 4 con PIN incorrecto) y cada panel se activa con la transición ya terminada.
   - Cero errores en la consola.
   - No hay scroll horizontal a 1440 × 900, 1366 × 768 y 390 × 844.
   - Capturas: la vista completa y las 4 etapas a 1440 × 900, la vista por etapa a 390 × 844 y una de cada fondo. En JPEG con calidad 80 (el grano del fondo hace que un PNG pese unos 700 KB), en `docs/maqueta/capturas/`, con menos de 4 MB en total.
   - Un solo video `.webm`, a 1×, de una verificación completa en la vista por etapa, de 60 s o menos.
   - Una prueba con `prefers-reduced-motion` y otra con `prefers-reduced-transparency` emulados.
   - Contraste medido del texto sobre vidrio, en reposo y en el peor caso.
   - Cuadros por segundo de las transiciones.
   - Funciona sin internet: corta la red y recarga, y además comprueba que la página no haga ninguna petición que no sea `file:` o `data:` (abierta con doble clic, cortar la red por sí solo no prueba nada).
   - Los scripts de prueba no van en el repositorio.
4. **No hagas commit ni push.** Deja los cambios en el árbol de trabajo y entrega un resumen con: qué cambió, qué verificaste (con la evidencia), qué falló con su número, qué no pudiste verificar y las decisiones que tomaste por tu cuenta.
5. **Actualiza la sección "Diseño de la app" de `docs/PROMPT_FABLE_5_2.md`** para que apunte a esta maqueta como referencia de la fase 3.

Si algo de este prompt choca con lo que encuentres (un valor de color que no coincide con la HIG, una API que no funciona en Edge, una fuente sin licencia libre), no te detengas: decide, explica por qué en una o dos frases y déjalo anotado en `docs/REVISION_REDISENO.md` para que yo lo revise.
