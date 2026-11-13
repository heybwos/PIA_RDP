# Revisión crítica del prompt de rediseño y decisiones tomadas

Revisión de `docs/PROMPT_FABLE_REDISENO.md` y de `docs/maqueta/acceso_biometrico.html` hecha antes de programar, el 11 de noviembre de 2026. Cada punto dice qué se encontró, cómo se resolvió y si está **verificado** (lo comprobé con una fuente, con el código o con una medición) o es un **supuesto**.

El prompt ya quedó corregido con estas resoluciones. Los resultados de las pruebas están en la sección 4.

## 1. Contradicciones y ambigüedades del prompt

| # | Qué decía el prompt | Problema | Resolución | Estado |
|---|---|---|---|---|
| 1 | `systemRed #FF453A`, `systemOrange #FF9F0A` | La HIG vigente publica otros valores para modo oscuro: rojo `255,66,69` y naranja `255,146,48`. El verde `48,209,88` sí coincide. | Uso `#FF4245`, `#FF9230` y `#30D158`. | Verificado en la página de color de la HIG (tabla "System colors", consultada el 11 nov 2026). |
| 2 | Fondos, `label`, `secondaryLabel`, `tertiaryLabel`, `separator` como "valores de la HIG" | La HIG no publica esos valores; son colores dinámicos de UIKit. Solo pude confirmar que `#1C1C1E` y `#2C2C2E` coinciden con `systemGray6` y `systemGray5` en oscuro. | Se usan como tokens y en el código se anotan como "medidos por la comunidad", no como oficiales. | Verificado que no están en la HIG. Los valores en sí son un supuesto. |
| 3 | `tertiaryLabel` como color de texto | Sobre `#1C1C1E` da 2.5:1. No sirve para texto. | Todo el texto usa `label` o `secondaryLabel`. `tertiaryLabel` queda solo en bordes de figuras. | Verificado (calculado). |
| 4 | Verde FIME como acento en botones y en "elementos interactivos" | `#1F9F5C` con texto blanco da 3.4:1, y como texto sobre `#2C2C2E` da 4.1:1. Ninguno llega a 4.5:1. | El relleno usa `--verde-fime` con texto oscuro (5.7:1). Para texto y trazos finos se deriva `--acento-claro` (el mismo verde con 38 % de blanco), calculado en el script a partir del token, así que al confirmar el verde con la FIME solo se cambia un valor. | Verificado (calculado). |
| 5 | "Radio interno = radio externo menos el padding" | Con el radio y el padding de 20 px que tenía la maqueta, la fórmula da 0. | Paneles con radio 24 y padding 16 (interno 8). En la vista por etapa, 32 y 24 (interno 8). Es una variable CSS, no un número repetido. | Verificado en el código. |
| 6 | Vidrio con alfa de 0.18 a 0.35 y contraste medido "en el punto más claro del fondo" | El peor caso no es el fondo: es la huella cruda, casi blanca, cuando pasa por debajo del pie o del navegador al hacer scroll. Con alfa 0.35 el texto secundario no se lee. | Tres niveles de vidrio: 0.32 para lo que solo tiene el fondo detrás (selector, velocidad, Reiniciar, panel ESP32), 0.75 para la barra, el navegador y el pie, y texto secundario al 82 % de opacidad sobre ellos. El contraste se mide también con la huella cruda debajo. | Medido, ver sección 4. |
| 7 | "Los controles segmentados van en vidrio" y además van dentro de la barra, que ya es vidrio | Un `backdrop-filter` anidado no difumina nada nuevo: el del padre lo aísla. Sería costo sin efecto. | Los segmentados de la barra llevan solo un relleno translúcido. El de velocidad, que está sobre el fondo, sí lleva vidrio. Nunca hay más de una capa con blur encimada. | Supuesto sobre el motor (comportamiento conocido de Chromium, no lo medí aparte). |
| 8 | "No pongas vidrio encima de canvas que se están animando" y, a la vez, barra fija "con el contenido pasando por debajo" y pie fijo | En la vista completa es inevitable que un canvas animado quede bajo el pie. | En la vista por etapa las visualizaciones se ajustan al alto libre para no quedar bajo el pie. En la completa se acepta y se mide el costo en cuadros por segundo. | Medido, ver sección 4. |
| 9 | "Nada se anima fuera de la vista" y "si el usuario se regresa, la vista deja de seguir el flujo" | Si el usuario se aparta, la etapa en curso queda fuera de la vista. El prompt no decía si la verificación se pausa. | La verificación sigue (el dispositivo real tampoco espera a la pantalla). La regla aplica solo mientras la vista sigue el flujo: el orquestador espera el fin de la transición antes de animar. Al volver, se redibuja lo que depende del tamaño. | Verificado con prueba. |
| 10 | "Detente y espera mi elección" (fondo) y "detente y pregúntame" | Bloquea una ejecución sin supervisión. | Se hacen las dos variantes, se elige una con justificación y la otra queda en `data-fondo="b"`. Los choques se resuelven y se documentan aquí. | Decisión. |
| 11 | "Etapa 4: la fila nueva de la bitácora" y "sin DOM duplicado" | Mostrar la fila en dos lugares duplicaría DOM. | El panel Bitácora acompaña a la etapa 4. En esa vista muestra solo el último registro y un botón "Ver bitácora completa" lo expande. | Verificado en el código. |
| 12 | "Sigue visible el indicador de las fases 1 a 4" | La maqueta tenía un solo indicador global de 5 fases en la barra. Con huella y rostro en pantallas distintas, uno solo no puede decir en qué fase quedó cada factor. | Cada factor tiene su indicador de fases 1 a 4 en el encabezado de su panel. PIN y Actuación llevan una etiqueta fija ("Fase 1 · Captura", "Fase 5 · Actuación"). | Decisión de diseño. |
| 13 | El navegador de etapas solo se describe para la vista por etapa | En la vista completa se perdía el resumen del avance. | El navegador se ve en las dos vistas. En la completa, elegir un paso desplaza la página a su panel, y el flujo también la desplaza si el panel activo no está a la vista. Si el usuario mueve la página durante la verificación, deja de arrastrarlo y aparece la misma cápsula "En curso". | Verificado con prueba. |
| 14 | "Funciona sin internet: corta la red y recarga" | Al abrir con doble clic (`file://`) la página nunca usa la red, así que esa prueba pasa aunque algo esté mal. | Además de cortar la red, se comprueba que no se haga ninguna petición que no sea `file:` o `data:` y que las seis fuentes carguen. | Verificado con prueba. |
| 15 | "Commit" al final y "Windows" en el encabezado | El commit lo hace el usuario; el entorno puede no ser Windows. | El prompt ya no pide commit y describe la verificación sin depender del sistema. | Decisión. |

## 2. Problemas encontrados en la maqueta original

| # | Problema | Resolución | Estado |
|---|---|---|---|
| 16 | El archivo no tenía `<!doctype>`, `<html>`, `<meta charset>` ni `<meta viewport>`. Abierto con doble clic entraba en modo quirks y, en un móvil, se dibujaba a 980 px de ancho. | Se agregó el esqueleto completo con `lang="es"`, charset y viewport. | Verificado: `innerWidth` da 390 en la prueba de móvil. |
| 17 | Cargaba IBM Plex desde Google Fonts. Sin internet, la OLED y las gráficas cambiaban de fuente. | Inter y JetBrains Mono locales con `@font-face` y rutas relativas. El arranque espera a que cargue la fuente del canvas de la OLED. | Verificado con prueba sin red. |
| 18 | El subconjunto `latin` de las fuentes no trae `→` ni `σ` (su `unicode-range` solo incluye `↑` y `↓`). Esos caracteres saldrían con otra fuente. | Los textos visibles ya no usan flechas ni letras griegas: "ESP32 a PC", "+3.2° a 0°", "desviaciones estándar". Queda una `σ` en una explicación del pie ("σ = 4 px"), ver pendientes. | Verificado en el CSS de fontsource. |
| 19 | `S.lastResult` no se actualizaba cuando el PIN fallaba: conservaba el resultado de la verificación anterior. Una prueba automática que lo leyera daba un falso resultado. | Ahora se limpia al empezar y se llena también en el caso de PIN incorrecto (con `pin:false`, `pidioHuella:false`, `pidioRostro:false`). | Verificado: era la única diferencia en la prueba de regresión. |
| 20 | La casilla "Mostrar dígitos" no devolvía los dígitos al volver a marcarla (leía un `data-v` que nunca se escribía). | Se guarda el estado de las casillas y se repinta. | Verificado con prueba. |
| 21 | Los estados se distinguían solo por el color de un punto (verde, rojo, ámbar). | Cada estado lleva icono y texto. En el navegador, aprobado es un círculo con palomita y rechazado un cuadro redondeado con equis. En las minucias la leyenda dice la forma (círculo o cuadro). En la gráfica de distancia el marcador cambia de forma. | Verificado en capturas. |
| 22 | Los neutros y las imágenes de la huella tenían matiz verde (fondo `[12,18,15]`, esqueleto verde). | Grises neutros. El esqueleto es gris claro y el acento queda para lo que se quiere señalar (minucias, pares, barrido). | Verificado en capturas. |
| 23 | El texto de Viola-Jones decía "Rostro y ojos detectados", aunque el rectángulo sale de la posición que conoce el generador. | El pie ahora lo dice: "posición conocida del generador, no una detección real". | Verificado en el código. |
| 24 | Objetivos táctiles de 32 a 42 px en segmentados, selector y botones. | Todos a 44 px o más. Los segmentos miden 36 px a la vista y amplían su zona de toque a 44 px con un seudoelemento. | Medido, ver sección 4. |

## 3. Decisiones de diseño que conviene revisar

1. **Fondo elegido: A ("Bosque y petróleo").** Pone el verde FIME profundo detrás de la barra y el azul petróleo detrás del pie, como pedía el prompt, y le da al vidrio más que difuminar. El B ("Grafito") es más neutro y casi plano detrás de la barra. Para cambiar: en la primera línea del archivo, `<html lang="es" data-fondo="a">` pasa a `data-fondo="b"`. También se puede probar en la consola con `document.documentElement.dataset.fondo='b'`.
2. **Texto oscuro sobre el verde FIME** en el botón principal y en el segmento seleccionado. Apple usaría blanco, pero con este verde no alcanza el contraste (punto 4).
3. **La verificación no se pausa** si el usuario se aparta de la etapa en curso (punto 9).
4. **El navegador de etapas aparece también en la vista completa** (punto 13).
5. **La barra y el navegador solo quedan fijos** en pantallas de 860 px de ancho o más y 620 px de alto o más. En móvil ocuparían un tercio de la pantalla.
6. **La vista por etapa arranca en la etapa 4** cuando se abre la página, porque muestra una verificación ya resuelta. "Reiniciar" lleva a la etapa 1.
7. **La transición no se escala con la velocidad** (2×, 0.5×): siempre dura 500 ms.
8. **La OLED y los LED conservan sus colores de hardware** (blanco azulado, verde y rojo encendidos). Son réplicas del dispositivo, no parte de la interfaz.
9. **Sin filtros SVG de refracción.** No hay forma de comprobar aquí que corran a 60 cuadros en Chrome y Edge sobre Windows, así que se dejaron fuera, como pedía el prompt.
10. **Para forzar el respaldo sin View Transitions** se puede abrir la página con `?sinvt=1`.

## 4. Verificación

Hecha con Playwright y Chromium sin interfaz en un contenedor Linux, el 11 de noviembre de 2026. Los scripts quedaron fuera del repositorio. La evidencia está en `docs/maqueta/capturas/`.

**Importante:** el contenedor no tiene GPU (Chromium dibuja con SwiftShader, por software). Eso afecta a la medición de cuadros por segundo y no dice nada de Chrome o Edge en Windows.

### Probado y pasa

| Prueba | Resultado |
|---|---|
| Regresión de algoritmos contra la maqueta original (5 escenarios × semillas 11, 4242 y 7) | Los 12 casos que llegan a huella y rostro dan exactamente los mismos números (puntaje, distancia, normalizados y fusión). En los 15, el veredicto, el motivo, los LED y los compartimentos coinciden. |
| Los 5 escenarios en las dos vistas (semilla 11) | 10 de 10. Nivel 1 y nivel 2 concedidos; impostor de huella negado con huella normalizada 0.11 (rostro pasa); impostor de rostro negado con rostro 0.46 (huella pasa, y la fusión 0.73 sola habría pasado); PIN incorrecto negado sin pedir huella ni rostro. |
| Flujo en tiempo real en la vista por etapa (l1, ih, ir a 2× y pin a 0.5×) | Secuencia de etapas 1,2,3,4 y, con PIN incorrecto, 1,4. Cada panel se activó con su etapa ya visible y la transición terminada. |
| Flujo en tiempo real en la vista completa (l2 a 2×) | Concedido nivel 2; la página se desplazó sola hasta el panel activo. |
| Regresar a una etapa anterior durante la verificación | Aparece "En curso: Huella", luego cambia a "En curso: Rostro" sin mover la vista; al pulsarla vuelve a la etapa en curso y se oculta. |
| Flechas y clic en el navegador al terminar | Secuencia esperada 3, 2, 3, 1 y no pasa de la etapa 1. |
| Teclado manual | 07 # 4821 # concede nivel 1; el ID 99 da "no está registrado"; la casilla "Mostrar dígitos" oculta y vuelve a mostrar. |
| Modo ESP32 | Panel visible, botón de inicio y teclas desactivados, "Buscando…" y luego "No se encontró ningún ESP32"; el navegador de etapas sigue funcionando. |
| Paso a paso | 16 pulsaciones de "Siguiente" para una verificación completa; sin pulsar no avanza; al cambiar a 2× continúa. "Reiniciar" deja todo en pendiente y en la etapa 1. |
| `localStorage` | Por defecto Completa; recuerda "Por etapa" al recargar; con `localStorage` bloqueado arranca en Completa y no lanza errores. (Desde el cierre, el valor por defecto es "Por etapa"; ver "Cierre en Windows".) |
| Respaldo sin View Transitions (`?sinvt=1`) | Navega con opacidad y `transform` en 514 a 581 ms. |
| Errores en la consola | 0 en todas las pruebas. |
| Peticiones fuera de `file:` y `data:` | 0. Con la red cortada y recargando: las 6 fuentes cargan y la verificación corre. |
| Scroll horizontal | Ninguno a 1440 × 900, 1366 × 768 y 390 × 844 (con `innerWidth` real de 390), en la vista completa y en las 4 etapas. |
| `prefers-reduced-motion` | La transición queda en fundidos de 150 ms sin movimiento de grupos; el indicador de espera no pulsa; el flujo llega bien a la etapa 4. El cambio completo tardó 286 ms en este equipo. |
| `prefers-reduced-transparency` (emulado por CDP) | Barra, navegador, pie, segmentado y selector quedan sin `backdrop-filter` y con fondo al 97 %. |
| Objetivos táctiles | 39 controles revisados, ninguno menor de 44 px. |
| Números tabulares | En Inter, "1111" y "0000" miden lo mismo (51.84 px) con `tabular-nums`. |
| Transición normal | Animaciones de 500 ms con `vt-entra-der` y `vt-sale-izq` (y las inversas hacia atrás), más los grupos de título e indicador. |

### Contraste medido sobre vidrio

Se oculta el texto, se captura el vidrio y se toma su píxel más claro. Mínimo aceptable: 4.5:1.

| Caso | Vidrio | Texto principal | Texto secundario | Acento claro |
|---|---|---|---|---|
| Fondo A en reposo | Barra superior | 12.09 | 7.45 | 5.77 |
| Fondo A en reposo | Navegador (con indicador) | 10.49 | 6.58 | 5.01 |
| Fondo A en reposo | Pie | 16.82 | 9.90 | 8.02 |
| Fondo A en reposo | Segmentado de velocidad | 16.22 | 5.79 | 7.74 |
| Fondo A en reposo | Selector de escenario | 16.08 | 5.75 | 7.67 |
| Fondo B en reposo | Barra superior | 12.42 | 7.63 | 5.92 |
| Fondo B en reposo | Navegador (con indicador) | 10.04 | 6.33 | 4.79 |
| Peor caso: huella cruda debajo | Barra superior | 7.31 | 4.78 | 3.48 (no se usa en la barra) |
| Peor caso: huella cruda debajo | Navegador (con indicador) | 9.16 | 5.83 | 4.37 (solo en un borde, no en texto) |
| Peor caso: huella cruda debajo | Pie (movido sobre la huella para la prueba) | 10.18 | 6.41 | 4.86 |

En la primera vuelta el texto secundario fallaba: 4.03 en el navegador en reposo y 3.12 a 3.29 con la huella debajo. Se corrigió subiendo el vidrio de la barra a 0.75 y el del navegador y el pie a 0.75, el texto secundario sobre vidrio a 0.82 de opacidad y bajando el relleno del indicador. Los números de la tabla son los de después.

Sobre superficies opacas (calculado): texto secundario 5.95 sobre `#1C1C1E` y 5.27 sobre `#2C2C2E`; acento claro 8.11 y 6.65; texto oscuro sobre verde FIME 5.66; `systemRed` 4.96; `systemGreen` 8.42; `systemOrange` 7.62.

### Falló en el contenedor y quedó resuelto en el cierre

| Prueba | Resultado en el contenedor | Cierre en Windows |
|---|---|---|
| 60 cuadros por segundo en las transiciones | 11 a 14 cuadros por segundo (cuadro más largo de 100 a 133 ms), dibujando por software. | Cuadro más largo de 19 ms con GPU real. El problema era del contenedor. |
| Que cada etapa quepa sin scroll sobre el pie | Etapa 2 a 1440 × 900: 47 px tapados. Etapa 1 a 1366 × 768: 10 px. | Todas caben en cinco tamaños; ver la tabla de abajo. |

### Cierre en Windows (12 y 13 de noviembre de 2026)

Hecho en Windows 11 con GPU real, en el navegador Chromium del panel de Claude, sobre un servidor local (`python -m http.server`). Fable 5.2 dio el plan, los criterios de aceptación y la verificación; Opus 5.5 hizo los cambios.

**Hallazgos que cambiaron el plan:**
- A 1280 × 800 la etapa 2 se pasaba 146 px y la 4, 32 px. A 1536 × 864 (laptop 1080p al 125 %), la 4 se pasaba 12 px. Se agregaron los dos tamaños a los criterios.
- Causa de la etapa 2: `.fp-lado` necesita 476 px para poner tira y métricas en dos columnas. A 1440 y a 1280 medía unos 460 px, así que se apilaban.
- `body` reservaba 96 px abajo: aunque la etapa cupiera, aparecía una barra de scroll vertical que movía el ancho 15 px entre etapas.
- Con la pestaña oculta, `startViewTransition` se omite y su promesa `ready` se rechazaba sin que nadie la atrapara: un error en la consola por cada cambio de etapa. Pasaba si el presentador cambiaba de ventana durante una verificación.
- Para medir con iframes hay que dejarlos dentro de la pantalla: fuera de ella Chromium no ejecuta el `ResizeObserver` y `--cab-h` se queda en 132 px en lugar de 140.

**Cambios:**
1. Encaje de la vista por etapa: margen inferior de 84 px solo en esa vista; `--alto-vis` y la columna del teclado con 10 px más de holgura; la huella deja al menos 524 px a la tira y las métricas; gráficas de compartimentos más bajas; bitácora compacta; y, con 800 px de alto o menos, rejilla, OLED, ranuras del PIN y columna de fusión más apretadas. Todo bajo `data-vista="etapa"` y 1000 px de ancho o más.
2. "σ = 4 px" pasó a "desviación estándar de 4 px". La `θ` de un comentario pasó a `theta`.
3. Pista de las flechas a la izquierda del navegador de etapas, desde 1280 px de ancho: dos teclas dibujadas con iconos de Lucide (`arrow-left` es nuevo) y el texto "Cambiar de etapa". El navegador lleva `aria-keyshortcuts` y `title`.
4. La maqueta arranca en "Por etapa". `?vista=completa` o `?vista=etapa` en la URL mandan sobre lo guardado y no se guardan.
5. `t.ready.catch(()=>{})` en la transición.

**Encaje medido.** Distancia del borde inferior de la etapa al borde superior del pie (negativo = cabe), sin scroll vertical ni horizontal en ningún caso:

| Viewport | Etapa 1 | Etapa 2 | Etapa 3 | Etapa 4 |
|---|---|---|---|---|
| 1280 × 800 | −17 | −20 | −16 | −57 |
| 1366 × 768 | −12 | −17 | −13 | −24 |
| 1440 × 900 | −17 | −30 | −45 | −69 |
| 1536 × 864 | −17 | −17 | −16 | −58 |
| 1920 × 1080 | −17 | −193 | −214 | −244 |

**Comprobado además:**
- Los 15 casos de regresión (5 escenarios × semillas 11, 4242 y 7) dan los mismos 13 valores que antes del cierre, al dígito.
- La vista completa no cambió: los rectángulos de los 5 paneles son idénticos a 1366 × 768, 1440 × 900 y 1920 × 1080.
- 0 caracteres fuera del subconjunto latin de las fuentes en el HTML, sin contar comentarios.
- Arranque: sin nada guardado abre "Por etapa" en la etapa 4; con "completa" guardado abre la completa; `?vista=` manda y no escribe en `localStorage`.
- La pista de las flechas no se encima con el navegador y la cabecera sigue midiendo 140 px.

### Límites conocidos

- Con menos de 768 px de alto de viewport (ventana sin maximizar) o con el panel del modo ESP32 abierto (unos 70 px más), las etapas necesitan scroll. La demo va en pantalla completa (F11).
- En 390 × 844 todas las etapas requieren scroll, como es de esperar.

### No probado

- Un navegador sin `backdrop-filter` (la regla `@supports` está escrita pero no se ejecutó).
- Lectores de pantalla y navegación completa con teclado, más allá de las flechas.
- Edge en Windows: el cierre se midió en el Chromium del panel de Claude, con el mismo motor.
- El video se grabó a 1280 × 720, no a 1440 × 900.

### Pendientes conocidos

- El verde FIME sigue siendo provisional.

### Evidencia

| Archivo | Qué muestra |
|---|---|
| `capturas/completa_1440.jpg` | Vista completa a 1440 × 900 |
| `capturas/etapa_1_1440.jpg` a `etapa_4_1440.jpg` | Las 4 etapas a 1440 × 900 |
| `capturas/etapa_movil_390.jpg` | Vista por etapa a 390 × 844 |
| `capturas/fondo_a.jpg`, `capturas/fondo_b.jpg` | Las dos variantes del fondo (etapa 4) |
| `capturas/contraste_peor_caso.jpg` | La huella cruda bajo la barra y el navegador |
| `capturas/verificacion_por_etapas.webm` | Una verificación completa a 1× en la vista por etapa (unos 43 s) |
