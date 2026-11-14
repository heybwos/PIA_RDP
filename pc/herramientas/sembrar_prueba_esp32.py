"""Siembra una carpeta de datos APARTE para probar la app en modo ESP32 con el ESP32 falso.

    python pc/herramientas/sembrar_prueba_esp32.py datos/prueba_esp32
    python pc/herramientas/esp32_falso.py --repetir
    cd pc && python -m pia --datos ../datos/prueba_esp32 --camara-archivo ../datos/datasets/orl/s5/8.pgm
    -> http://127.0.0.1:8000/?puerto=socket://127.0.0.1:5333, botón ESP32, Buscar ESP32

Crea el usuario 21 (nivel 2, PIN 2468) con huellas sintéticas y rostro de ORL. Nunca uses la
carpeta datos/ normal: la calibración 'as608' de aquí sale del banco sintético.
"""

from __future__ import annotations

import sys
from pathlib import Path

PC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PC))
from pia import config, simular  # noqa: E402
from pia.almacen import Almacen  # noqa: E402

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
carpeta = Path(sys.argv[1]).resolve()
if carpeta == config.cargar().carpeta_datos.resolve():
    raise SystemExit("Usa una carpeta aparte, no datos/.")
alm = Almacen(carpeta)
d = simular.sembrar_prueba_esp32(alm, config.RAIZ / "datos" / "datasets", PC / "tests" / "fixtures" / "huellas_sinteticas")
print(f"Listo en {carpeta}: usuario {d['id']}, PIN {d['pin']}, rostro {d['rostro']}")
