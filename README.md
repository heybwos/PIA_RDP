# PIA RDP: control de acceso biométrico

Control de acceso por niveles con tres factores (PIN, huella y rostro) para el PIA de Reconocimiento
de Patrones (FIME, UANL). Una caja con ESP32, teclado 4×4, sensor de huella AS608, OLED y dos servos;
una PC con Python que procesa huella (Gabor, minucias, matching por grafos) y rostro (Viola-Jones,
alineación, Eigenfaces), y una app web local que muestra cada fase con datos reales.

Estado y siguientes pasos: [`docs/ESTADO_DEL_PROYECTO.md`](docs/ESTADO_DEL_PROYECTO.md). Plan: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Poner a funcionar en una PC (Windows)

Requisitos: Python 3.12–3.14, git, VS Code con la extensión **PlatformIO IDE** (para el firmware) y el
driver **CH340** del ESP32.

```powershell
git clone https://github.com/heybwos/PIA_RDP.git
cd PIA_RDP
git checkout claude/exciting-davinci-aqy6kg
& .\pc\scripts\instalar.ps1 -Respaldo D:\ruta\pia_AAAAMMDD_HHMMSS.zip -Probar
```

- `instalar.ps1` crea `.venv`, instala dependencias, baja ORL y FVC2002 a `datos/datasets/`, restaura el
  respaldo (usuarios, calibraciones, banco de huellas y `config.toml`) y corre las pruebas.
- **Los datos biométricos no están en git** (`datos/` está en `.gitignore`). Se pasan en el ZIP de respaldo
  (USB o Drive). Se crea en la PC original con `.\.venv\Scripts\python.exe pc\scripts\respaldo.py crear`.
- Sin respaldo, el instalador siembra solo el modo Simular (usuarios de prueba 07 y 12).

Actualizar después: `git pull` y, si cambió `pc/requirements.txt`, volver a correr `instalar.ps1`.

## Arrancar

```powershell
& .\pc\scripts\arrancar.ps1                  # backend en http://127.0.0.1:8000
& .\pc\scripts\arrancar.ps1 -CargarFirmware  # primero carga el firmware (mantén BOOT al ver "Connecting...")
```

Abre `http://127.0.0.1:8000` (Ctrl + F5 tras actualizar).

- **Simular:** elige un escenario y pulsa Iniciar verificación.
- **ESP32:** botón ESP32 → Buscar ESP32 (una vez). En la caja: `ID#PIN#`, el dedo en el sensor y la
  cara dentro del óvalo de la cámara. Tras el resultado, "Intentar de nuevo" o `#` en la caja.
- **Servos:** botón en la barra superior para mover los compartimentos a mano.
- **Datos:** botón en la barra superior (abre otra pestaña). Muestra, solo para consulta, las huellas con sus minucias, las caras alineadas, el modelo de Eigenfaces (cara media, eigenfaces y reconstrucción), las calibraciones y el banco de huellas. Las imágenes empiezan difuminadas; se actualiza sola cuando alguien se registra.

### Cámara (IP Webcam en Android)

En la app IP Webcam: Video resolution 640×480, "Start server". Celular en vertical y en la misma red
que la laptop. Para probar y guardar la URL:

```powershell
.\.venv\Scripts\python.exe pc\scripts\probar_camara.py --url http://<IP del celular>:8080/video --guardar-url
.\.venv\Scripts\python.exe pc\scripts\probar_camara.py --vista
```

## Comandos útiles

| Qué | Comando (desde la raíz) |
|---|---|
| Alta completa (firmware de captura, registro, segunda tanda, recalibrar rostro, firmware principal) | `.\.venv\Scripts\python.exe pc\scripts\alta_companero.py --id 14 --nombre "X" --nivel 1` (app apagada; mantener BOOT dos veces) |
| Registrar a alguien (AS608 + cámara) | `.\.venv\Scripts\python.exe pc\scripts\registrar.py --id 03 --nombre "X" --nivel 2 --puerto COM4 --fuente-rostro camara` (firmware `test_huella_imagen`) |
| Segunda tanda de cara | `.\.venv\Scripts\python.exe pc\scripts\capturar_rostros.py --id 03` |
| Banco de huellas para calibrar | `.\.venv\Scripts\python.exe pc\scripts\capturar_banco.py --puerto COM4` (firmware `test_huella_imagen`) |
| Calibrar | `.\.venv\Scripts\python.exe pc\scripts\calibrar.py --factor huella --dominio as608 --activar` / `--factor rostro --dominio camara --criterio far0 --activar` |
| Cargar un entorno del firmware | `& .\pc\scripts\prueba_modulo.ps1 -Entorno test_huella_imagen -Puerto COM4 -SinMonitor` |
| Respaldo | `.\.venv\Scripts\python.exe pc\scripts\respaldo.py crear` / `restaurar <zip>` |
| Pruebas | `.\.venv\Scripts\python.exe -m pytest pc\tests -q` |
| Regresión de la app | `npm i playwright` (una vez) y `node app\pruebas\regresion.js`, `node app\pruebas\regresion_esp32.js` |

## Estructura

| Carpeta | Qué hay |
|---|---|
| `firmware/` | PlatformIO: `esp32dev` (principal) y entornos de prueba por módulo |
| `pc/pia/` | Backend: `huella/`, `rostro/`, `almacen.py`, `orquestador.py`, `servidor.py`, `dispositivos/` |
| `pc/scripts/` | Instalar, arrancar, registrar, calibrar, respaldo, pruebas de hardware |
| `pc/herramientas/` | ESP32 falso, DroidCam falso, siembra de pruebas |
| `app/` | Interfaz web (sin build) y regresiones de Playwright |
| `docs/` | Roadmap, estado, protocolo, eventos, cableado, contexto y la maqueta original |
| `datos/` | **Local, fuera de git**: base SQLite, imágenes, modelos, datasets, respaldos |
