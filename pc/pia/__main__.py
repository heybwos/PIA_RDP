"""python -m pia  (desde pc/)  ->  http://127.0.0.1:8000

Opciones para pruebas (no hacen falta en el uso normal):
  --datos <carpeta>          otra carpeta de datos (por ejemplo, una sembrada para el ESP32 falso)
  --camara-archivo <imagen>  rostro fijo de un dataset en lugar de DroidCam
"""

import argparse
from pathlib import Path

import uvicorn

from . import config
from .servidor import crear_app

ap = argparse.ArgumentParser(prog="python -m pia")
ap.add_argument("--puerto", type=int, default=8000)
ap.add_argument("--datos")
ap.add_argument("--camara-archivo")
args = ap.parse_args()
extra = {}
if args.datos:  # relativo a la carpeta desde donde se corre, no a la raíz del repo
    extra["datos__carpeta"] = str(Path(args.datos).resolve())
if args.camara_archivo:
    extra.update(camara__fuente="archivo", camara__archivo=str(Path(args.camara_archivo).resolve()))
print(f"Abre http://127.0.0.1:{args.puerto}")
uvicorn.run(crear_app(config.cargar(**extra)), host="127.0.0.1", port=args.puerto, log_level="warning")
