# Guía para Claude Code en este repositorio

Proyecto: control de acceso biométrico (PIN + huella + rostro) para el PIA de Reconocimiento de Patrones,
FIME UANL. Entrega el **viernes 27 de noviembre de 2026** (se movió del martes 17). Antes de trabajar, lee
`docs/ESTADO_DEL_PROYECTO.md` (qué está hecho y qué sigue) y, para el plan, `docs/ROADMAP.md`.

## Reglas

- **Todo en español**: textos de la app, mensajes de commit, comentarios y docs. Sin acentos solo en la OLED.
- **Nunca subir datos biométricos a git.** `datos/` está en `.gitignore`; los datos viajan en el ZIP de
  `pc/scripts/respaldo.py`. No agregues imágenes de huellas o caras reales a `pc/tests/fixtures/`.
- Los métodos están fijados por el PIA (campo de orientación, Gabor, minucias, grafos, Viola-Jones,
  alineación, CLAHE, Eigenfaces con NumPy, distancia euclidiana). Nada de redes neuronales, `dlib`,
  `face_recognition`, scikit-learn para PCA ni el matching interno del AS608.
- La app solo dibuja: todo valor del reconocimiento lo calcula Python (`docs/EVENTOS.md`).
- Rama de trabajo: `claude/exciting-davinci-aqy6kg` en `heybwos/PIA_RDP`. Commit y push al terminar cada bloque.

## Entorno (Windows)

- Python en `.venv` (`.\.venv\Scripts\python.exe`). Instalar todo: `& .\pc\scripts\instalar.ps1`.
- PlatformIO: `%USERPROFILE%\.platformio\penv\Scripts\pio.exe`. El ESP32 es CH340 (COM4 en la PC original;
  en la laptop cambia al reconectar, COM3 o COM8: buscarlo con `Get-PnpDevice` o dejar que `alta_companero.py` lo detecte).
- **El sandbox de los comandos no puede abrir puertos COM**: carga de firmware, monitores serie y scripts
  que usan el ESP32 se corren en una pestaña de la terminal del usuario (no en Bash).
- **Cargar firmware**: el usuario tiene que **mantener BOOT** al ver `Connecting....` (si no:
  "Wrong boot mode 0x13").
- **"Could not open COM4, the port doesn't exist"** = el puerto está ocupado (backend, monitor serie,
  la página `app/herramientas/servos.html` en Edge, o Windows no lo soltó). Cerrar eso; si no, que el
  usuario desconecte y reconecte el USB.
- La cámara es IP Webcam (`http://<IP>:8080/video`, `rotacion = 90`). DroidCam solo acepta un cliente.
- Tras cambiar `app/`, el usuario debe recargar con Ctrl + F5.

### En la laptop de la demo (26 nov)

- **Los `.ps1` están bloqueados** por la política de ejecución. No cambiarla: correr
  `powershell -NoProfile -ExecutionPolicy Bypass -File <script.ps1>` o llamar a Python directo
  (`arrancar.ps1` = `..\.venv\Scripts\python.exe -m pia` desde `pc\`).
- **El puerto 8000 lo ocupa otro programa**: arrancar con `python -m pia --puerto 8001`.
- **La WiFi FIME aísla a los equipos**: la cámara va por el hotspot del celular (`[camara] url_respaldo`).
  Con la laptop en el hotspot no hay internet y **Claude no responde**: dejar en la terminal del usuario
  programas que corran solos y pausen para cambiar de red (`alta_companero.py`, `registrar.py`).
- Altas de compañeros: `pc\scripts\alta_companero.py` con la app apagada (usa el puerto de la caja).

## Comandos

```powershell
& .\pc\scripts\arrancar.ps1 [-CargarFirmware]           # backend en http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m pytest pc\tests -q        # 38 pruebas (las de ORL/FVC necesitan datos\datasets)
.\.venv\Scripts\python.exe pc\scripts\alta_companero.py --id <ID> --nombre "<nombre>" --nivel <1|2>   # alta completa
node docs\reporte\reporte.js; powershell -ExecutionPolicy Bypass -File docs\reporte\actualizar_word.ps1   # reporte (npm docx)
node app\pruebas\regresion.js; node app\pruebas\regresion_esp32.js   # requieren `npm i playwright` (usa Edge)
.\.venv\Scripts\python.exe pc\scripts\verificar_consola.py --todos   # 5 escenarios de Simular
& .\pc\scripts\prueba_modulo.ps1 -Entorno <entorno> -Puerto COM4 [-SinMonitor]
```

Firmware: `esp32dev` (principal) habla `docs/PROTOCOLO.md`. Los scripts de huella cruda
(`bajar_huella.py`, `capturar_banco.py`, `registrar.py --puerto`) necesitan el entorno `test_huella_imagen`.

## Datos

`datos/pia.db` (SQLite, esquema en `pc/pia/almacen.py`), `datos/usuarios/<id>/` (crudos), `modelos/`,
`banco_as608/`, `rostros_tanda2/`, `calibracion/`, `datasets/` (ORL, FVC2002; se bajan con
`descargar_datasets.py`). Las calibraciones activas y su origen están en `docs/ESTADO_DEL_PROYECTO.md`.
