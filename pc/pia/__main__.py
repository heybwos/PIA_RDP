"""python -m pia  (desde pc/)  ->  http://127.0.0.1:8000"""

import argparse

import uvicorn

from .servidor import crear_app

ap = argparse.ArgumentParser(prog="python -m pia")
ap.add_argument("--puerto", type=int, default=8000)
args = ap.parse_args()
print(f"Abre http://127.0.0.1:{args.puerto}")
uvicorn.run(crear_app(), host="127.0.0.1", port=args.puerto, log_level="warning")
