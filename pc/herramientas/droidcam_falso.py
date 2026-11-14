"""Servidor MJPEG que imita a DroidCam (/video) con caras de ORL, para probar camara.py.

    python pc/herramientas/droidcam_falso.py [--puerto 4747] [--carpeta datos/datasets/orl/s3]

Publica en http://127.0.0.1:<puerto>/video un cuadro de 640 x 480 con una cara en medio,
cambiando de imagen cada segundo.
"""

from __future__ import annotations

import argparse
import itertools
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]


def cuadros(carpeta: Path):
    caras = [cv2.imread(str(f), cv2.IMREAD_GRAYSCALE) for f in sorted(carpeta.glob("*.pgm"))]
    if not caras:
        raise SystemExit(f"No hay .pgm en {carpeta}")
    for cara in itertools.cycle(caras):
        lienzo = np.full((480, 640), 90, np.uint8)
        grande = cv2.resize(cara, (184, 224))
        lienzo[128:352, 228:412] = grande
        ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(lienzo, cv2.COLOR_GRAY2BGR))
        yield jpg.tobytes()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=4747)
    ap.add_argument("--carpeta", type=Path, default=RAIZ / "datos" / "datasets" / "orl" / "s3")
    args = ap.parse_args()
    fuente = cuadros(args.carpeta)

    class Manejador(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path != "/video":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    jpg = next(fuente)
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                     + f"Content-Length: {len(jpg)}\r\n\r\n".encode() + jpg + b"\r\n")
                    time.sleep(1.0)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *a):
            pass

    print(f"DroidCam falso en http://127.0.0.1:{args.puerto}/video")
    ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador).serve_forever()


if __name__ == "__main__":
    main()
