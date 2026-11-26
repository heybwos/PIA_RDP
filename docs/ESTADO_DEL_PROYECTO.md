# Estado del proyecto: PIA de Reconocimiento de Patrones

Resumen para retomar el trabajo en otra PC o en una sesión nueva de Claude Code.

**Última actualización: 25 de noviembre de 2026 (miércoles).** Entrega: **viernes 27 de noviembre de 2026** (se movió del martes 17).
El estado de la maqueta anterior (13 de noviembre) está en el historial de git de este archivo.

**Orden de lectura para retomar:**
1. Este archivo.
2. `CLAUDE.md` (raíz): comandos, reglas y trampas conocidas.
3. `docs/ROADMAP.md`: el plan día por día; el bloque N7 trae el estado de la calibración y los pasos pendientes.
4. `docs/PROTOCOLO.md` (serie ESP32 ↔ PC) y `docs/EVENTOS.md` (WebSocket backend ↔ app) cuando haya que tocar esas partes.

---

## 1. Resumen

| Parte | Estado |
|---|---|
| Hardware | ESP32 (CH340, COM4), AS608, teclado 4×4, OLED SSD1306 (0x3C), 2 servos SG90. **LEDs sin conectar.** |
| Firmware (`firmware/`) | `esp32dev` cargado y funcionando. Entornos de prueba por módulo aprobados en P4. |
| Backend (`pc/pia/`) | Pipeline de huella y rostro, base SQLite, orquestador, FastAPI + WebSocket. 33 pruebas pasan. |
| App (`app/`) | Modo Simular y modo ESP32 de punta a punta. Regresiones de Playwright OK. |
| Compuertas | **G1** (imagen del AS608) y **G2** (verificación real con la caja, nivel 2 concedido) cumplidas. |
| Calibración | Activa pero **provisional** (ver sección 3). |
| Pendiente | P6 (registrar a los compañeros el **jueves 26**, recalibrar y prueba de aceptación), N8 (robustez y `docs/DEMO.md`), N9 (reporte), LEDs. |

## 2. Cómo se usa (resumen; los detalles en `README.md`)

- Instalar en una PC nueva: `& .\pc\scripts\instalar.ps1 -Respaldo <zip>`.
- Arrancar: `& .\pc\scripts\arrancar.ps1` y abrir `http://127.0.0.1:8000` (Ctrl + F5 tras actualizar).
- Modo ESP32: botón **ESP32** → **Buscar ESP32** (una vez). La verificación empieza tecleando en la caja: `ID#PIN#`, dedo, cara dentro del óvalo.
- Tras la decisión todo se queda en la etapa 4 (servos abiertos si se concedió) hasta **"Intentar de nuevo"** o la tecla **`#`**: los servos se cierran uno a uno y empieza otra.
- Botón **Servos** (barra superior): control manual de los compartimentos, fuera de la verificación.
- Cámara: **IP Webcam** (Android) a 640×480, celular en vertical (`rotacion = 90`), URL `http://<IP del celular>:8080/video` en `config.toml`.

## 3. Calibración activa (provisional)

| Factor | Dominio | Umbral | FAR | FRR | Datos |
|---|---|---|---|---|---|
| Huella | `as608` | 0.180 | 0 % | 33 % | Banco de 6 dedos de **una sola persona** × 8 capturas (18 genuinos, 90 impostores). EER 16.7 %. |
| Rostro | `camara` | 8.511 | 0 % | 10 % | 10 cuadros de la segunda tanda del usuario 21 contra **160 caras de ORL** (no de cámara). EER 10 %. |
| Huella | `fvc2002` | 0.150 | — | — | Modo Simular (EER 0.2 %). |
| Rostro | `dataset` | 8.75 | — | — | Modo Simular, ORL (EER 8.2 %). |

Perfil `as608` ajustado en N7: CLAHE, umbral de varianza 0.004, distancia mínima de minucias 6 (EER 34 % → 16.7 %).
**Recalibrar cuando se sumen los compañeros**: pasos exactos en `docs/ROADMAP.md`, bloque N7, "PENDIENTE".

## 4. Usuarios registrados

| ID | Nombre | Nivel | Huella | Rostro |
|---|---|---|---|---|
| 21 | Nestor | 2 | 5 capturas del AS608 | 15 cuadros de cámara |
| 07, 12 | Ana T., Luis G. | 1, 2 | FVC2002 | ORL |

07 y 12 son los usuarios de prueba del modo Simular (PIN 4821 y 1593). El PIN real del 21 no está en ningún archivo (solo su hash).

## 5. Qué se corrigió con el hardware real (para no repetirlo)

| Problema | Causa | Arreglo |
|---|---|---|
| El ESP32 borraba el PIN cada segundo | `millis()` tomado antes de leer el `PING` (resta sin signo) | `firmware/src/main.cpp`, comentado |
| Huella "CRC incorrecto" | Redibujar la OLED en cada paquete desbordaba el búfer de UART2 | Barra cada 32 paquetes (`huella.cpp`) |
| Teclas cambiadas | Conector del teclado al revés (14 nov); recableado el 25 nov | `pines.h` con el orden medido por `test_teclado_crudo` (filas 13, 14, 27, 26; columnas 25, 33, 32, 4) |
| Cámara girada 90° y marca de agua | Celular en vertical; DroidCam gratis | `rotacion = 90`; se usa IP Webcam |
| Foto del rostro instantánea | Se tomaba el primer cuadro | Vista en vivo con óvalo guía, cuenta regresiva y 1.5 s dentro de la guía |
| Servos antes que la animación | El backend actuaba al calcular | La caja espera el aviso "listo" de la app |
| La app mostraba JS viejo | Caché de Edge | `Cache-Control: no-cache` |

## 6. Siguientes pasos, en orden

**Calendario:** jueves 26 = registrar a los compañeros y recalibrar; viernes 27 = entrega y demo.

1. **N8:** `docs/DEMO.md` (guion de 5 minutos, lista previa, solución de problemas) y robustez que falte.
2. **P6 con los compañeros (jueves 26):** sumar sus dedos al banco, registrarlos (huella y cámara), segunda tanda, recalibrar los dos factores y la prueba de aceptación (10 genuinos y 10 impostores por persona).
3. **N9:** reporte técnico con los números reales y las gráficas de `datos/calibracion/`.
4. Hardware: conectar los LEDs (verde GPIO23, rojo GPIO5, 220 Ω) y conseguir un cargador de 5 V / 2 A o power bank para los servos.
5. El viernes 27, antes de la demo: registrar de nuevo las caras **en el salón** (luz real) y probar la red (IP Webcam).

## 7. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| Huella del AS608 débil (4 bits, área chica) | EER 16.7 % con dedos de una sola persona. Mitigado con FAR = 0, reintentos (hasta 3) y la fusión con el rostro. Recalibrar con más gente. |
| Luz del salón distinta para Eigenfaces | Registrar las caras en el salón el día de la demo. |
| Red de la escuela aísla celular y laptop | Plan: hotspot del celular con la laptop conectada a él. Probar antes. |
| Brownout de los servos con otra fuente | Probado sin brownout con 5 V / 0.9 A (USB de monitor). Llevar cargador de 2 A. |
