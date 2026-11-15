# Eventos entre el backend y la app

WebSocket en `ws://127.0.0.1:8000/ws`. Cada mensaje es un objeto JSON `{"tipo": "...", ...datos}`.
El backend calcula; la app solo dibuja. Si un valor aparece en pantalla, vino de aquí.

## Imágenes

Toda imagen va como `{"ancho": W, "alto": H, "tipo": "u8" | "f32", "datos": "<base64>"}`, fila por fila.
`u8`: 0..255. `f32`: float32 little-endian (la app reescala a su rango).

## Backend → app

| Tipo | Datos | Cuándo |
|---|---|---|
| `estado` | `modo`, `conexion`, `usuarios` [{id, nombre, nivel}], `escenarios` [{clave, nombre, esperado}], `bancos`, `calibracion` {huella, rostro} | Al conectar y cuando cambia algo |
| `etapa` | `n` (1 PIN, 2 huella, 3 rostro, 4 decisión), `estado` (`curso`, `ok`, `no`, `omit`), `dato` | Al entrar y salir de cada etapa |
| `tecla` | `c` | Cada tecla (física o del escenario) |
| `casillas` | `id`, `pin` (asteriscos), `fase` (`id` o `pin`) | Tras cada tecla |
| `oled` | `l1`, `l2` | Texto de la pantalla |
| `serie` | `dir` (`in` ESP32→PC, `out` PC→ESP32), `linea` | Cada línea del protocolo (el PIN va enmascarado) |
| `leds` | `verde`, `rojo` (bool) | |
| `huella_inicio` | `ancho`, `alto`, `fuente`, `simulada` (bool) | Empieza a llegar la imagen |
| `huella_filas` | `y0`, `filas` (imagen u8 de esas filas) | Un bloque de filas, al ritmo real |
| `huella_fin` | `bytes`, `crc_ok`, `ms` | Imagen completa |
| `huella_etapa` | `nombre` (`normalizada`, `segmentacion`, `orientacion`, `gabor`, `binaria`, `esqueleto`), `imagen`, y en `orientacion`: `bloque`, `angulos` (f32 por bloque), `coherencia`, `mascara` | Cada etapa del preproceso |
| `huella_minucias` | `minucias` [{x, y, t, tipo}], `calidad` | |
| `huella_matching` | `puntaje`, `umbral`, `pares` [[i, j]], `plantilla` {minucias, esqueleto}, `aristas_a`, `aristas_b`, `muestra_id` | Contra la mejor plantilla del usuario |
| `rostro_vivo` | `imagen` (u8, 240 px de ancho), `rostro`, `ojos` (en esa escala), `estado` (`preparate`, `buscando`, `estable`, `tomado`), `falta_s`, `seguidos`, `necesarios`, `limite_s` | Solo con cámara real: ~8 por segundo hasta que hay rostro con dos ojos en 3 cuadros seguidos (tras 2 s de reacción; límite 20 s). La app los dibuja sin esperar la cola |
| `huella_reintento` | `intento`, `de`, `puntaje`, `umbral` | Huella débil (normalizada < 0.6): se pide otra captura sin volver a teclear el PIN; hasta 3, se queda la mejor. `huella_matching` trae `intento` y `de` |
| `rostro_cuadro` | `imagen` (u8, gris), `fuente` | Cuadro capturado |
| `rostro_deteccion` | `rostro` [x, y, w, h] o null, `ojos` [[x, y, w, h]…], `con_relleno` | Rectángulos reales de Viola-Jones |
| `rostro_alineado` | `imagen` (64×64 u8), `metodo` (`ojos`, `respaldo`, `sin_rostro`), `angulo` | |
| `rostro_normalizado` | `imagen` (64×64 f32), `hist_antes`, `hist_despues` (32 bins) | |
| `rostro_pca` | `modelo_id`, `k`, `varianza`, `media` (f32), `eigenfaces` [f32 × 8] | Una vez por modelo |
| `rostro_pesos` | `pesos` (lista de k) | |
| `rostro_reconstruccion` | `pasos` [{componentes, imagen f32}] | Con 1, 5, 10, 20 y k componentes |
| `rostro_distancia` | `distancia`, `umbral`, `distancia_espacio` | |
| `fusion` | `huella`, `rostro` (normalizados 0..1), `fusion`, `pesos` {huella, rostro}, `umbral_factor`, `umbral_fusion` | |
| `veredicto` | `concedido`, `nivel`, `motivo` | |
| `servo` | `n` (1 o 2), `abierto` | Cada servo, uno a la vez |
| `bitacora_fila` | la fila insertada en `bitacora` | |
| `error` | `mensaje`, `que_revisar` | Cualquier falla; nunca se sustituye por datos inventados |
| `puertos` | `puertos` [{puerto, responde, version, sensor, oled}] | Respuesta a `buscar_puertos`. Un `version` que empieza con `test_` es un firmware de prueba: la app no se conecta sola |

En modo ESP32 el estado trae `conexion` = {puerto, version, sensor, oled}. Cada verificación empieza sola cuando alguien teclea en la caja: la app limpia los paneles al recibir `etapa` 1 en `curso`.

## App → backend

| Tipo | Datos |
|---|---|
| `iniciar` | `escenario` (`l1`, `l2`, `ih`, `ir`, `pin`), `fuente_rostro` (`dataset` o `camara`) |
| `tecla` | `c` |
| `cancelar` | — |
| `listo` | `punto` (`huella`, `veredicto`) | Solo en modo ESP32: la app terminó de animar ese punto. El backend espera este aviso (máximo 30 s) antes de encender la cámara y antes de mandar `ACCESO` a la caja, para que lo físico vaya al ritmo de la pantalla |
| `modo` | `modo` (`simular` o `esp32`) |
| `buscar_puertos` | `puerto` (opcional, `socket://…` del ESP32 falso), `solo` (true: no prueba los COM reales) |
| `conectar` | `puerto` |
| `registro_iniciar`, `registro_capturar_huella`, `registro_capturar_rostro`, `registro_guardar`, `usuario_borrar` | Se fijan en N8a |
