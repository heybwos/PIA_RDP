# Plan para la laptop de la demo

Escrito el 25 de noviembre de 2026. Entrega y demo: **viernes 27 de noviembre**. Registro de los compañeros:
**jueves 26, en el salón de la presentación** (misma luz, mismo lugar y misma red que el viernes).

Estado de partida: la caja armada funciona completa con la PC de escritorio (commit `de01507`). La laptop tiene
una versión anterior del repositorio y le falta todo lo de la sesión del 25 de noviembre: fechas,
teclado recalibrado, opciones de Simular ocultas en modo ESP32 y animaciones de la app.

Cuando el usuario diga "ya estoy en la laptop", Claude Code sigue este documento en orden y marca cada casilla.

### Avance al 26 de noviembre (en el salón)

- [x] Laptop al día (rama, `instalar.ps1` con el respaldo de la USB, pruebas en verde). Caja en COM3 y luego COM8.
- [x] La WiFi **FIME aísla a los clientes**: la laptop no ve al celular. Cámara por el **hotspot** (`url_respaldo`,
      `10.28.183.166`); `[camara] url` se deja vacía. Con la laptop en el hotspot no hay internet (ni Claude).
- [x] Registrados en el salón: **Nestor (21)** otra vez (cara nueva, mismas huellas), **Orlando (33)**, **Sandra (14)**, **Luis (15)** y **Santiago (99)**,
      pulgar y cara, con segunda tanda. Altas con `pc\scripts\alta_companero.py` (hace todo, con pausa para el hotspot).
- [x] Rostro recalibrado con criterio **EER**: umbral 10.18 (FAR = FRR = 8 % con 5 usuarios; 10 % con 4 y 6.7 % con 3). Con FAR 0 el FRR era 45 %.
- [ ] Prueba de aceptación (10 genuinos y 10 impostores por persona) y anotar los números.
- [ ] Copiar el respaldo más reciente (`datos\respaldos\pia_20261126_*.zip`) a la USB.
- La huella **no** se recalibró: el banco sigue siendo de los 6 dedos de Nestor (paso 2.3.2 omitido por tiempo).

---

## 0. Antes de dejar la PC de escritorio

Los datos biométricos **no viajan por git** (`datos/` está en `.gitignore`). Viajan en un ZIP por USB.

- [ ] Crear el respaldo: `.\.venv\Scripts\python.exe pc\scripts\respaldo.py crear` → queda en `datos\respaldos\pia_<fecha>.zip`.
      Lleva el usuario 21 (Nestor), el banco de huellas del AS608 (6 dedos de Nestor), la segunda tanda de rostro
      y las calibraciones activas.
- [x] Respaldo creado el 25 nov: `datos\respaldos\pia_20261125_230030.zip` (31 MB, verificado).
- [ ] Copiar ese ZIP a la USB (y una segunda copia en otro lado).
- [ ] Confirmar que GitHub tiene el último commit de la rama `claude/exciting-davinci-aqy6kg`.

## 1. Poner la laptop al día (en casa, antes del salón)

- [ ] `git fetch` y `git checkout claude/exciting-davinci-aqy6kg` y `git pull`. Si `git status` muestra cambios
      locales viejos, revisarlos con el usuario antes de descartar nada.
- [ ] Si la laptop ya tiene su propia carpeta `datos/` con algo útil, respaldarla primero:
      `respaldo.py crear` (en la laptop) y guardar ese ZIP aparte.
- [ ] Instalar y restaurar: `& .\pc\scripts\instalar.ps1 -Respaldo <ruta del ZIP de la USB> -Probar`.
      Debe terminar con las pruebas de pytest en verde.
- [ ] El instalador avisa si falta **PlatformIO** (VS Code + extensión PlatformIO IDE) o el driver **CH340**.
      Los dos hacen falta: para registrar se carga `test_huella_imagen` y al final otra vez `esp32dev`.
- [ ] Conectar la caja y ver en qué COM aparece (en la PC original era COM4). Usar ese puerto en todos los comandos.
- [ ] Prueba rápida sin hardware: `& .\pc\scripts\arrancar.ps1`, abrir `http://127.0.0.1:8000` con Ctrl + F5 y correr
      una verificación en Simular. Debe verse la píldora deslizante y, en modo ESP32, desaparecer escenario/rostro/velocidad.
- [ ] Opcional: `npm i --no-save playwright` y las dos regresiones de `CLAUDE.md`.

- [ ] **Cámara: dos URL.** `[camara] url` es la **principal** (IP Webcam en la WiFi de la facultad) y
      `url_respaldo` la del **hotspot del celular** (`http://10.28.183.166:8080/video`, vista el 25 nov). Antes de cada
      verificación el backend prueba la principal (1.5 s) y, si no contesta, usa el respaldo solo; en la consola
      del backend sale "se usa la de respaldo". Si la laptop ya tenía `config.toml`, ni el instalador ni el respaldo
      lo reemplazan: guardar el hotspot con (celular en hotspot y la laptop conectada a él)
      `.\.venv\Scripts\python.exe pc\scripts\probar_camara.py --url http://10.28.183.166:8080/video --guardar-url --respaldo`.
      No editar `config.toml` con `Set-Content -Encoding utf8`: en PowerShell 5.1 agrega BOM y el backend ya no lo lee.
      Android puede cambiar la IP del hotspot al apagarlo y prenderlo: revisarla en la pantalla de IP Webcam.

El ESP32 de la caja ya tiene el firmware `esp32dev` con los pines nuevos del teclado: no hace falta cargarlo en casa.

## 2. En el salón, jueves 26 (registro y calibración)

### 2.1 Preparar el lugar (se queda igual hasta el viernes)

- [ ] Celular en su soporte, en vertical, a la altura de la cara, en el lugar exacto donde va a estar en la demo.
      Anotar dónde (foto del montaje) para repetirlo el viernes.
- [ ] Luz: la del salón a la hora de la demo. Evitar ventana detrás de la persona.
- [ ] Red **principal: WiFi de la facultad**, con la laptop y el celular conectados a ella. Leer la IP en la pantalla de
      IP Webcam y guardarla como principal:
      `.\.venv\Scripts\python.exe pc\scripts\probar_camara.py --url http://<IP en la facultad>:8080/video --guardar-url`.
      Si la red de la facultad no deja que la laptop vea al celular (la prueba falla), pasar los dos al **hotspot** del
      celular: el backend cambia solo a `url_respaldo`. Revisar que la IP del hotspot siga siendo `10.28.183.166`.
- [ ] Probar la cámara: `.\.venv\Scripts\python.exe pc\scripts\probar_camara.py` (IP Webcam a 640 × 480, `rotacion = 90`).

### 2.2 Datos de cada compañero (llenar antes de empezar)

| ID (2 dígitos) | Nombre | Nivel (1 Lector, 2 Editor) | Dedos para el banco | PIN (lo teclea él, no se anota aquí) |
|---|---|---|---|---|
| 21 | Nestor | 2 | ya en el banco | — |
|  |  |  |  | — |
|  |  |  |  | — |
|  |  |  |  | — |

Al menos una persona por nivel y alguien **sin registrar** que haga de impostor. Pedir permiso a cada uno:
su huella y su cara se quedan solo en la laptop (`datos/`), nunca en git.

### 2.3 Orden de trabajo

El orden importa: todo lo que usa la huella cruda va con el firmware de prueba, y se carga `esp32dev` una sola vez al final.

1. [ ] Cargar el firmware de prueba (mantener **BOOT** al ver `Connecting...`):
       `& .\pc\scripts\prueba_modulo.ps1 -Entorno test_huella_imagen -Puerto COMx -SinMonitor`
2. [ ] **Banco de huellas** de cada compañero (sirve para calibrar, no son usuarios). Cada dedo es una identidad;
       nombres `<persona>_<dedo>`:
       `python pc\scripts\capturar_banco.py --puerto COMx --dedos <n> --capturas 8`
3. [ ] Opcional: `python pc\scripts\explorar_parametros.py`. Si otro perfil gana con claridad, cambiar `as608` en
       `pc\pia\huella\parametros.py` y **volver a registrar** a los que ya estaban (todavía no existe `respaldo.py reprocesar`).
4. [ ] Calibrar huella: `python pc\scripts\calibrar.py --factor huella --dominio as608 --activar`
       (con `--criterio far0` si el EER sigue arriba de 15 %).
5. [ ] **Registrar** a cada compañero. El script captura las huellas del AS608 y los cuadros de IP Webcam en el momento,
       y extrae él mismo las **minucias** (plantilla) y los pesos de Eigenfaces. No hay que preparar nada a mano:
       `python pc\scripts\registrar.py --id <ID> --nombre "<nombre>" --nivel <1|2> --puerto COMx --fuente-rostro camara`
       Cada alta reentrena el modelo de rostro `camara`.
6. [ ] **Nestor otra vez**: su cara se registró con la luz de su casa. Volver a registrarlo en el salón:
       `python pc\scripts\respaldo.py borrar-usuario 21` y luego `registrar.py` con `--id 21`.
7. [ ] **Segunda tanda** de rostro de cada uno, unos minutos después de su registro:
       `python pc\scripts\capturar_rostros.py --id <ID>`
8. [ ] Calibrar rostro, ahora con impostores reales de cámara (cada compañero contra los demás):
       `python pc\scripts\calibrar.py --factor rostro --dominio camara --criterio far0 --activar`
9. [ ] Cargar otra vez el firmware principal (BOOT): `& .\pc\scripts\arrancar.ps1 -CargarFirmware -Puerto COMx`
10. [ ] **Prueba de aceptación**: por persona, 10 intentos genuinos y 10 como impostor (alguien teclea su ID y PIN y pone
        su propio dedo y cara). Anotar aceptados/rechazados: son los FAR y FRR del reporte.
11. [ ] Respaldo final: `respaldo.py crear` → copiar a la USB (dos copias).

Tiempo aproximado: unos 15 minutos por persona (banco, registro y segunda tanda) más la calibración y la prueba de aceptación.

## 3. Viernes 27, antes de la demo

- [ ] Montar el celular igual que el jueves (foto del montaje). WiFi de la facultad; si falla, hotspot (el backend cambia
      solo). En cualquiera de las dos, revisar en IP Webcam que la IP sea la guardada; la de la facultad puede cambiar de un día a otro.
- [ ] `& .\pc\scripts\arrancar.ps1`, abrir la app con Ctrl + F5 → **ESP32** → **Buscar ESP32** (debe ponerse verde: "Conectado").
- [ ] Una verificación de nivel 1, una de nivel 2 y una de impostor. "Intentar de nuevo" (o `#`) cierra los servos.
- [ ] Cargador de 5 V / 2 A a la mano por si hay brownout con los servos.
- [ ] Si la laptop va lenta con las transiciones: abrir `http://127.0.0.1:8000/?sinvidrio=1`.

## 4. Problemas conocidos

| Síntoma | Qué hacer |
|---|---|
| `Could not open COMx, the port doesn't exist` | El puerto está ocupado (backend, monitor serie o `servos.html` en Edge). Cerrarlo; si no, desconectar y reconectar el USB. |
| `Wrong boot mode 0x13` al cargar firmware | Mantener BOOT mientras sale `Connecting....`. |
| Cámara sin imagen | Revisar la IP en la app IP Webcam y en `config.toml`. DroidCam solo acepta un cliente: usar IP Webcam. |
| Muchos rechazos de rostro | La luz cambió respecto al registro: registrar de nuevo en el lugar y recalibrar rostro (pasos 5–8). |
| Huella débil | El sistema pide hasta 3 intentos: dedo plano y cubriendo el sensor. |
| Teclas cambiadas | Correr `test_teclado_crudo` (ver `docs/CABLEADO.md`) y corregir `firmware/src/pines.h`. |
