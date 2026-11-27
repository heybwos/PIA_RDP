"""Alta completa de un compañero: huella en el AS608 y cara en la cámara del salón.

    .venv\\Scripts\\python.exe pc\\scripts\\alta_companero.py --id 14 --nombre "Sandra" --nivel 1
    ... --desde 2      (si el firmware de captura ya está cargado)

Pasos: firmware de captura (BOOT), registro (PIN, 5 capturas, pausa para el hotspot, 15 cuadros),
segunda tanda (10 cuadros), calibración del rostro (EER) y firmware principal otra vez (BOOT).
El puerto de la caja se detecta solo (CH340). La app debe estar apagada: usa ese puerto.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from serial.tools import list_ports

RAIZ = Path(__file__).resolve().parents[2]
PY = str(RAIZ / ".venv" / "Scripts" / "python.exe")
PIO = str(Path(os.environ["USERPROFILE"]) / ".platformio" / "penv" / "Scripts" / "pio.exe")
S = RAIZ / "pc" / "scripts"

ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True)
ap.add_argument("--nombre", required=True)
ap.add_argument("--nivel", required=True, choices=["1", "2"])
ap.add_argument("--desde", type=int, default=1)
ap.add_argument("--puerto")
a = ap.parse_args()

puerto = a.puerto or next((p.device for p in list_ports.comports() if "CH340" in (p.description or "")), None)
if not puerto:
    sys.exit("No encuentro la caja (CH340). Conecta el USB y vuelve a correr esto.")
print(f"Caja en {puerto}. Alta de {a.nombre} (ID {a.id}, nivel {a.nivel}).")


def firmware(entorno: str) -> list[str]:
    return [PIO, "run", "-d", str(RAIZ / "firmware"), "-e", entorno, "-t", "upload", "--upload-port", puerto]


PASOS = [
    ("Cargar el firmware de captura. MANTÉN BOOT en el ESP32 cuando salga 'Connecting...'",
     firmware("test_huella_imagen"), False),
    (f"Registro de {a.nombre}: PIN (2 veces); 5 veces el PULGAR en el sensor; pausa para el hotspot; Espacio en la cámara",
     [PY, str(S / "registrar.py"), "--id", a.id, "--nombre", a.nombre, "--nivel", a.nivel,
      "--puerto", puerto, "--fuente-rostro", "camara"], False),
    (f"Segunda tanda de la cara de {a.nombre} (Espacio en la ventana; que gire un poco la cabeza)",
     [PY, str(S / "capturar_rostros.py"), "--id", a.id], True),
    ("Calibración del rostro (cámara, criterio EER)",
     [PY, str(S / "calibrar.py"), "--factor", "rostro", "--dominio", "camara", "--criterio", "eer", "--activar"], False),
    ("Volver a cargar el firmware principal. MANTÉN BOOT cuando salga 'Connecting...'",
     firmware("esp32dev"), True),
]

for i, (titulo, cmd, pausa) in enumerate(PASOS, 1):
    if i < a.desde:
        continue
    print(f"\n===== Paso {i} de {len(PASOS)}: {titulo} =====", flush=True)
    if pausa:
        input("Presiona Enter cuando estés listo... ")
    if subprocess.run(cmd, cwd=RAIZ).returncode != 0:
        print(f"\nEl paso {i} falló. Revisa el mensaje de arriba. Para seguir desde ahí: --desde {i}")
        sys.exit(1)

subprocess.run([PY, str(S / "respaldo.py"), "crear"], cwd=RAIZ)
print(f"\nListo: {a.nombre} ({a.id}) registrado, rostro recalibrado, respaldo creado y la caja con el firmware principal.")
