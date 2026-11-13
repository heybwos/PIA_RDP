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
| Maqueta visual del modo Simular | Hecha y rediseñada al estilo Apple (`docs/maqueta/acceso_biometrico.html`) |
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
| Vista por etapas | Control "Vista: Completa \| Por etapa". En "Por etapa" se ve solo la etapa actual: PIN → Huella → Rostro → Actuación, con transiciones animadas. |

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

**Link publicado:** https://claude.ai/artifact/ByghMje85waN9nQ8px4T8r. **Todavía muestra la versión anterior al rediseño.**

## 4. Dónde se quedó Fable (rediseño)

Fable 5.2 terminó el rediseño y lo verificó; después se detuvo para cuidar el límite de uso. El detalle está en `docs/REVISION_REDISENO.md`.

**Hecho y probado:**
- Los cinco escenarios dan el mismo resultado en las dos vistas, con los mismos números que la maqueta original.
- Cero errores en la consola y cero peticiones externas.
- Sin scroll horizontal a 1440×900, 1366×768 y 390×844.
- Contraste del texto sobre vidrio: mínimo 4.78:1.
- Los 39 controles miden 44 px o más.
- Funciona con `prefers-reduced-motion` y `prefers-reduced-transparency`.
- Evidencia: 9 capturas JPEG y un video de 43 s en `docs/maqueta/capturas/`.

**Falló o quedó pendiente:**
1. **Transiciones a 11–14 cuadros por segundo** en el servidor de pruebas, que no tiene tarjeta gráfica. Hay que medirlo en Windows con Chrome o Edge; si también se traba, lo primero es reducir el desenfoque del vidrio.
2. **Dos etapas no caben completas en pantalla:** en la de huella a 1440×900, la píldora de abajo tapa 47 px de la métrica de matching; en la de PIN a 1366×768, 10 px.
3. Queda una `σ` en un pie de texto que la fuente local no trae.
4. Los atajos de flechas no se anuncian en la interfaz.
5. Sin probar: proyector de 1920×1080, navegador sin `backdrop-filter` y lectores de pantalla.
6. El verde FIME sigue provisional: hay que confirmar el valor oficial.
7. Unos 28 PNG pesados (unos 15 MB) quedaron en el historial de git por un commit de punto de control. Ya no están en los archivos, pero siguen ocupando espacio al clonar.

**Decisiones que tomó Fable y conviene revisar:**
- Texto oscuro sobre el verde FIME, porque el blanco daba 3.4:1.
- Vidrio al 0.75 en la barra, el navegador de etapas y el pie, por legibilidad.
- La verificación no se pausa si el usuario se regresa a una etapa anterior.
- El navegador de etapas también aparece en la vista completa.
- Fases 1 a 4 dentro de cada panel (huella y rostro), en lugar de un solo indicador en la barra.
- La vista por etapas arranca en la etapa 4, con la verificación de ejemplo ya resuelta.
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

1. **Revisar la maqueta en Windows:** que las transiciones vayan fluidas en Chrome o Edge, y arreglar las dos etapas que no caben. Es un ajuste chico.
2. **Decidir** si la vista por etapas debe ser la vista inicial para la demo. Hoy arranca en "Completa".
3. **Semana 1 del plan (hardware):** son las primeras pruebas y no dependen del software:
   - Probar la imagen cruda del AS608 con SFGDemo.
   - Medir el TX del sensor contra GND antes de conectarlo al ESP32.
   - Leer el teclado, leer DroidCam desde Python y mover los servos sin que se reinicie el ESP32.
4. **Ejecutar `docs/PROMPT_FABLE_5_2.md` desde la fase 0** (entorno y dependencias en Python 3.14). Revisar al final de cada fase.
5. **Calibrar de nuevo los umbrales con huellas reales del AS608.** Los de los datasets no sirven tal cual para ese sensor.

## 7. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| El AS608 no entrega la imagen cruda | Sin probar. Es lo primero. Plan B: R307 o FPM10. |
| El orden de los nibbles de la imagen de 4 bits | Sin confirmar. El prompt pide hacerlo configurable y detectarlo con una prueba. |
| Algunas dependencias de Python no tienen wheel para 3.14 | Sin verificar. El prompt pide comprobarlo en la fase 0, con respaldo en Python 3.13. |
| Viola-Jones no detecta las caras recortadas de ORL | Sin medir. El prompt pide medirlo y, si falla, usar LFW. |
| Rendimiento del vidrio en la laptop de la demo | Pendiente de medir en Windows (punto 1 de la sección 4). |
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

Abre la carpeta en VS Code e inicia Claude Code con Fable 5.2. Para empezar el sistema, pega `docs/PROMPT_FABLE_5_2.md`. Para pulir primero la maqueta, pide algo como: "Lee `docs/ESTADO_DEL_PROYECTO.md` y arregla los pendientes 1 a 4 de la sección 4".
