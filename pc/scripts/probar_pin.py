"""Comprueba el PIN de un usuario registrado sin mostrarlo.

    python pc/scripts/probar_pin.py --id 21
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import config  # noqa: E402
from pia.almacen import Almacen  # noqa: E402

sys.stdout.reconfigure(errors="replace")
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--id", required=True)
args = ap.parse_args()
alm = Almacen(config.cargar().carpeta_datos)
u = alm.usuario(args.id)
if not u:
    sys.exit(f"El ID {args.id} no está registrado.")
pin = getpass.getpass(f"PIN de {u['nombre']} (ID {args.id}; no se ve al escribir): ")
print("Correcto: el PIN coincide." if alm.verificar_pin(args.id, pin) else "No coincide.")
