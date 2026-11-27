# Estado del proyecto: PIA de Reconocimiento de Patrones

Resumen para retomar el trabajo en otra PC o en una sesión nueva de Claude Code.

**Última actualización: 26 de noviembre de 2026 (jueves), en el salón.** Entrega: **viernes 27 de noviembre de 2026** (se movió del martes 17).
El estado de la maqueta anterior (13 de noviembre) está en el historial de git de este archivo.

**En la laptop de la demo:** seguir `docs/PLAN_LAPTOP.md`. El 26 nov se registraron en el salón Nestor (de nuevo),
Orlando, Sandra, Luis, Santiago e Ivan, y se recalibró el rostro (secciones 3 y 4). Altas nuevas: `pc\scripts\alta_companero.py`.
Reporte: `docs/reporte/` (borrador).

**Orden de lectura para retomar:**
1. Este archivo.
2. `CLAUDE.md` (raíz): comandos, reglas y trampas conocidas.
3. `docs/ROADMAP.md`: el plan día por día; el bloque N7 trae el estado de la calibración y los pasos pendientes.
4. `docs/PROTOCOLO.md` (serie ESP32 ↔ PC) y `docs/EVENTOS.md` (WebSocket backend ↔ app) cuando haya que tocar esas partes.

---

## 1. Resumen

| Parte | Estado |
|---|---|
| Hardware | ESP32 (CH340: COM4 en la PC de escritorio; en la laptop cambia, COM3 o COM8), AS608, teclado 4×4, OLED SSD1306 (0x3C), 2 servos SG90. **LEDs sin conectar.** |
| Firmware (`firmware/`) | `esp32dev` cargado y funcionando. Entornos de prueba por módulo aprobados en P4. |
| Backend (`pc/pia/`) | Pipeline de huella y rostro, base SQLite, orquestador, FastAPI + WebSocket. 38 pruebas pasan. Sección Datos (`app/datos.html`, `pc/pia/seccion_datos.py`): consulta de solo lectura de usuarios, modelo de rostro, calibración y banco. |
| App (`app/`) | Modo Simular y modo ESP32 de punta a punta. Regresiones de Playwright OK. |
| Compuertas | **G1** (imagen del AS608) y **G2** (verificación real con la caja, nivel 2 concedido) cumplidas. |
| Calibración | Rostro recalibrado en el salón el 26 nov con 3 personas reales; huella sigue con el banco de un solo usuario (sección 3). |
| Pendiente | Prueba de aceptación (10 genuinos y 10 impostores por persona), más compañeros si llegan, N8 (`docs/DEMO.md`), terminar el reporte, LEDs. |

## 2. Cómo se usa (resumen; los detalles en `README.md`)

- Instalar en una PC nueva: `& .\pc\scripts\instalar.ps1 -Respaldo <zip>`.
- Arrancar: `& .\pc\scripts\arrancar.ps1` y abrir `http://127.0.0.1:8000` (Ctrl + F5 tras actualizar).
- Modo ESP32: botón **ESP32** → **Buscar ESP32** (una vez). La verificación empieza tecleando en la caja: `ID#PIN#`, dedo, cara dentro del óvalo.
- Tras la decisión todo se queda en la etapa 4 (servos abiertos si se concedió) hasta **"Intentar de nuevo"** o la tecla **`#`**: los servos se cierran uno a uno y empieza otra.
- Botón **Servos** (barra superior): control manual de los compartimentos, fuera de la verificación.
- Cámara: **IP Webcam** (Android) a 640×480, celular en vertical (`rotacion = 90`), URL `http://<IP del celular>:8080/video` en `config.toml`.

## 3. Calibración activa

| Factor | Dominio | Umbral | FAR | FRR | Datos |
|---|---|---|---|---|---|
| Huella | `as608` | 0.180 | 0 % | 33 % | Banco de 6 dedos de **una sola persona** × 8 capturas (18 genuinos, 90 impostores). EER 16.7 %. |
| Rostro | `camara` | **10.24** | 7.7 % | 8.3 % | 26 nov, en el salón. Criterio **EER** (8.0 %). Segunda tanda de 14, 15, 21, 33, 88 y 99 (60 genuinos) contra los demás usuarios y 160 caras de ORL (1260 impostores). Modelo de Eigenfaces con 210 caras, k = 96. EER con 3, 4, 5 y 6 usuarios: 6.7 %, 10 %, 8 % y 8.0 %. |

Rostro: con criterio FAR 0 el umbral quedaba en 9.25 y rechazaba al 45 % de los genuinos (las distancias de genuinos
e impostores se enciman entre 8.2 y 10.9), por eso se eligió el EER. Un impostor de cara aún tiene que pasar la huella,
con su propio umbral, y la fusión (0.60). Prueba del 26 nov: Sandra con el ID y PIN de Nestor pasó el rostro
(0.541 normalizado) pero la huella la rechazó (0.356) y la fusión dio 0.448: **acceso negado**.
| Huella | `fvc2002` | 0.150 | — | — | Modo Simular (EER 0.2 %). |
| Rostro | `dataset` | 8.75 | — | — | Modo Simular, ORL (EER 8.2 %). |

Perfil `as608` ajustado en N7: CLAHE, umbral de varianza 0.004, distancia mínima de minucias 6 (EER 34 % → 16.7 %).
**Recalibrar cuando se sumen los compañeros**: pasos exactos en `docs/ROADMAP.md`, bloque N7, "PENDIENTE".

## 4. Usuarios registrados

| ID | Nombre | Nivel | Huella | Rostro |
|---|---|---|---|---|
| 21 | Nestor | 2 | 5 capturas del AS608 (las del 14 nov) | 15 cuadros de cámara (salón, 26 nov) + segunda tanda |
| 33 | Orlando | 1 | 5 capturas del pulgar (26 nov) | 15 cuadros (salón) + segunda tanda |
| 14 | Sandra | 1 | 5 capturas del pulgar (26 nov) | 15 cuadros (salón) + segunda tanda |
| 15 | Luis | 1 | 5 capturas del pulgar (26 nov) | 15 cuadros (salón) + segunda tanda |
| 99 | Santiago | 2 | 5 capturas del pulgar (26 nov) | 15 cuadros (salón) + segunda tanda |
| 88 | Ivan | 1 | 5 capturas del pulgar (26 nov; 66 a 86 minucias, muchas más que los demás: posible ruido) | 15 cuadros (salón) + segunda tanda |
| 07, 12 | Ana T., Luis G. | 1, 2 | FVC2002 | ORL |

07 y 12 son los usuarios de prueba del modo Simular (PIN 4821 y 1593). Los PIN reales no están en ningún archivo (solo su hash).
Respaldo más reciente: `datos\respaldos\pia_20261126_*.zip` (copiarlo a la USB).

## 5. Qué se corrigió con el hardware real (para no repetirlo)

| Problema | Causa | Arreglo |
|---|---|---|
| El ESP32 borraba el PIN cada segundo | `millis()` tomado antes de leer el `PING` (resta sin signo) | `firmware/src/main.cpp`, comentado |
| Huella "CRC incorrecto" | Redibujar la OLED en cada paquete desbordaba el búfer de UART2 | Barra cada 32 paquetes (`huella.cpp`) |
| Teclas cambiadas | Conector del teclado al revés (14 nov); recableado el 25 nov | `pines.h` con el orden medido por `test_teclado_crudo` (filas 13, 14, 27, 26; columnas 25, 33, 32, 4) |
| Cámara girada 90° y marca de agua | Celular en vertical; DroidCam gratis | `rotacion = 90`; se usa IP Webcam |
| Foto del rostro instantánea | Se tomaba el primer cuadro | Vista en vivo con óvalo guía, cuenta regresiva y 1.5 s dentro de la guía |
| Servos antes que la animación | El backend actuaba al calcular | La caja espera el aviso "listo" de la app |
| Servos otra vez antes que la animación (26 nov) | Una segunda pestaña oculta animaba al instante y mandaba "listo" primero | Solo cuenta el "listo" de una pestaña visible (`visible` en `docs/EVENTOS.md`) |
| La cámara no contesta en la WiFi FIME | La red aísla a los clientes (misma subred /19, sin ping ni ARP) | Cámara por el hotspot del celular (`url_respaldo`); `registrar.py` pausa antes de la cámara para cambiar de red |
| Rostro rechazado en el salón | Caras registradas con la luz de la casa | Registro de nuevo en el salón y recalibración |
| La app mostraba JS viejo | Caché de Edge | `Cache-Control: no-cache` |

## 6. Siguientes pasos, en orden

**Calendario:** jueves 26 = registrar a los compañeros y recalibrar; viernes 27 = entrega y demo.

1. **Prueba de aceptación:** por persona (14, 15, 21, 33, 88, 99), 10 intentos genuinos y 10 de impostor (otro teclea su ID y PIN y pone su dedo y su cara). Anotar aceptados y rechazados por factor y del sistema: van al reporte (sección de resultados en `docs/reporte/`).
2. **Más compañeros**, si llegan: `pc\scripts\alta_companero.py --id <ID> --nombre "<nombre>" --nivel <1|2>` con la app apagada.
3. **Reporte:** completar `docs/reporte/` con los números de la prueba de aceptación.
4. **N8:** `docs/DEMO.md` (guion de 5 minutos, lista previa, solución de problemas).
5. Hardware: conectar los LEDs (verde GPIO23, rojo GPIO5, 220 Ω) y llevar un cargador de 5 V / 2 A para los servos.
6. El viernes 27: misma posición del celular y misma luz; laptop y celular en el hotspot; revisar la IP en IP Webcam.

## 7. Riesgos abiertos

| Riesgo | Estado |
|---|---|
| Huella del AS608 débil (4 bits, área chica) | EER 16.7 % con dedos de una sola persona. Mitigado con FAR = 0, reintentos (hasta 3) y la fusión con el rostro. Recalibrar con más gente. |
| Luz del salón distinta para Eigenfaces | Caras registradas en el salón el 26 nov. Repetir la misma posición y luz el viernes. |
| Red de la escuela aísla celular y laptop | **Confirmado el 26 nov** (WiFi FIME). Se usa el hotspot del celular; con la laptop en el hotspot no hay internet. |
| Brownout de los servos con otra fuente | Probado sin brownout con 5 V / 0.9 A (USB de monitor). Llevar cargador de 2 A. |
