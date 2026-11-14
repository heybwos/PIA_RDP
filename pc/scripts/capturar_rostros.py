"""N7 / P6: segunda tanda de rostro para calibrar (minutos después del registro).

    python pc/scripts/capturar_rostros.py --id 21             (10 cuadros)
    python pc/scripts/capturar_rostros.py --id 21 --n 15

Abre la cámara de config.toml con vista previa; Espacio captura. Guarda los cuadros crudos en
datos/rostros_tanda2/<id>/. calibrar.py --factor rostro --dominio camara los usa como
genuinos de ese usuario y como impostores contra los demás.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import camara, config, vista  # noqa: E402
from pia.almacen import Almacen, guardar_png  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()
    cfg = config.cargar()
    alm = Almacen(cfg.carpeta_datos)
    u = alm.usuario(args.id)
    if not u:
        print(f"El ID {args.id} no está registrado.")
        return 2
    print(f"Segunda tanda de {u['nombre']} (ID {args.id}): {args.n} cuadros. Acomódate y presiona Espacio.")
    cam = camara.desde_config(cfg)
    try:
        cuadros = vista.capturar_cuadros(cam, args.n, f"PIA - tanda 2 de {args.id}")
    except camara.CamaraError as e:
        print(f"ERROR: {e}\n  Qué revisar: {e.que_revisar}")
        return 2
    finally:
        cam.cerrar()
    if not cuadros:
        print("Cancelado.")
        return 1
    carpeta = cfg.carpeta_datos / "rostros_tanda2" / args.id
    sello = datetime.now().strftime("%H%M%S")
    for k, c in enumerate(cuadros, 1):
        guardar_png(carpeta / f"{sello}_{k:02d}.png", c)
    print(f"{len(cuadros)} cuadros en {carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
