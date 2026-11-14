"""Registra los usuarios de prueba 07 (nivel 1) y 12 (nivel 2) con identidades del dataset,
calibra los dominios fvc2002 y dataset, y deja listos los cinco escenarios.

    python pc/scripts/sembrar_simular.py

Necesita datos/datasets/ (python pc/scripts/descargar_datasets.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import config, simular  # noqa: E402
from pia.almacen import Almacen  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    cfg = config.cargar()
    alm = Almacen(cfg.carpeta_datos)
    simular.sembrar(alm, cfg.carpeta_datos / "datasets")
    print("Escenarios: " + ", ".join(simular.ESCENARIOS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
