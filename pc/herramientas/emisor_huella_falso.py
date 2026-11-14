"""Imita al ESP32 con test_huella_imagen, por TCP, para probar bajar_huella.py sin hardware.

    python pc/herramientas/emisor_huella_falso.py            (escucha en 127.0.0.1:5333)
    python pc/scripts/bajar_huella.py --puerto socket://127.0.0.1:5333

Manda una huella sintética de 256 x 288 a 4 bits, nibble alto primero, con el marco
de docs/PROTOCOLO.md. Con --ritmo la manda por partes a la velocidad real del sensor.
Con --falla crc|corte prueba los caminos de error del script.
"""

from __future__ import annotations

import argparse
import socket
import time
import zlib

import numpy as np

ANCHO, ALTO = 256, 288


def huella_sintetica(semilla: int = 7) -> bytes:
    rng = np.random.default_rng(semilla)
    y, x = np.mgrid[0:ALTO, 0:ANCHO].astype(np.float32)
    cx, cy = ANCHO / 2 + rng.uniform(-10, 10), ALTO / 2 + rng.uniform(-10, 10)
    r = np.hypot((x - cx) * 1.1, y - cy)
    ang = np.arctan2(y - cy, x - cx)
    crestas = 0.5 + 0.5 * np.sin(r / 1.45 + 2.0 * np.sin(ang * 2) + rng.uniform(0, 6))
    mascara = (((x - cx) / 110) ** 2 + ((y - cy) / 135) ** 2) < 1
    img = np.where(mascara, crestas * 13 + rng.normal(0, 0.8, crestas.shape), 15)
    px = np.clip(np.round(img), 0, 15).astype(np.uint8).reshape(-1)
    return bytes((px[0::2] << 4) | px[1::2])  # nibble alto primero


def atender(con: socket.socket, args) -> None:
    def tx(texto: str) -> None:
        con.sendall((texto + "\n").encode())

    tx("HOLA:test_huella_imagen:OK:NA")
    tx("DIAG:paquete=128 bytes baudios=57600")
    buf = b""
    while True:
        datos = con.recv(256)
        if not datos:
            return
        buf += datos
        while b"\n" in buf:
            ln, buf = buf.split(b"\n", 1)
            cmd = ln.decode().strip()
            if cmd == "PING":
                tx("PONG")
            elif cmd in ("PARAMS", "RESET"):
                tx("DIAG:paquete=128 bytes baudios=57600")
                tx("OK:PARAMS" if cmd == "PARAMS" else "HOLA:test_huella_imagen:OK:NA")
            elif cmd == "PEDIR_HUELLA":
                img = huella_sintetica()
                tx("HUELLA:ESPERA")
                time.sleep(0.5)
                tx("HUELLA:DEDO")
                crc = zlib.crc32(img)
                if args.falla == "crc":
                    crc ^= 1
                cuerpo = img[: len(img) // 2] if args.falla == "corte" else img
                tx(f"DIAG:bytes={len(cuerpo)} esperados={len(img)} ms=0")
                tx(f"IMG:{len(img)}")
                paso = 4096
                for i in range(0, len(cuerpo), paso):
                    con.sendall(cuerpo[i : i + paso])
                    if args.ritmo:
                        time.sleep(paso / 5760)  # 57600 baudios ~ 5760 B/s
                if args.falla == "corte":
                    continue  # se queda callado: el script debe detectar el corte
                tx(f"IMG:FIN:{crc:08x}")
            elif cmd:
                tx(f"ERR:desconocido:{cmd}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=5333)
    ap.add_argument("--ritmo", action="store_true", help="velocidad real del sensor")
    ap.add_argument("--falla", choices=["crc", "corte"])
    ap.add_argument("--una", action="store_true", help="atiende una conexión y sale")
    args = ap.parse_args()
    with socket.create_server(("127.0.0.1", args.puerto)) as srv:
        print(f"ESP32 falso en socket://127.0.0.1:{args.puerto}")
        while True:
            con, _ = srv.accept()
            with con:
                try:
                    atender(con, args)
                except (ConnectionResetError, BrokenPipeError):
                    pass
            if args.una:
                return


if __name__ == "__main__":
    main()
