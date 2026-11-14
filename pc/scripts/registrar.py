"""Registro de usuarios por consola (sección 4.4 del roadmap).

Con el ESP32 (huellas del AS608 con test_huella_imagen) y DroidCam:
    python pc/scripts/registrar.py --id 03 --nombre "Nestor" --nivel 2 --puerto COM4

Con imágenes ya guardadas (por ejemplo, de bajar_huella.py):
    python pc/scripts/registrar.py --id 03 --nombre "Nestor" --nivel 2 \
        --huellas datos/pruebas/huella_*.bin --rostros fotos/*.png --fuente-rostro camara

El PIN se pide por teclado (no se escribe en la línea de comandos).
"""

from __future__ import annotations

import argparse
import getpass
import glob
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import camara, config, huella, registro  # noqa: E402
from pia.almacen import Almacen, leer_png  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]


def huellas_del_sensor(puerto: str, n: int, nibble_alto: bool) -> list:
    sys.path.insert(0, str(Path(__file__).parent))
    import bajar_huella as bh

    enlace = bh.Enlace(puerto, 921600)
    try:
        if not bh.esperar_esp32(enlace):
            raise SystemExit("El ESP32 no responde (¿cargaste test_huella_imagen?)")
        imgs = []
        while len(imgs) < n:
            print(f"\nHuella {len(imgs) + 1} de {n}: levanta el dedo y vuelve a ponerlo.")
            enlace.enviar("PEDIR_HUELLA")
            datos = None
            while True:
                ln = enlace.linea(25.0)
                if ln is None or ln.startswith("HUELLA:ERR"):
                    print(f"  {ln or 'sin respuesta'}; se repite")
                    break
                if ln.startswith("IMG:") and not ln.startswith("IMG:FIN"):
                    datos = enlace.bytes_exactos(int(ln.split(":")[1]))
                    enlace.linea(3.0)
                    break
            if datos:
                imgs.append(huella.desempacar(datos, nibble_alto))
        return imgs
    finally:
        enlace.cerrar()


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--nivel", type=int, choices=(1, 2), required=True)
    ap.add_argument("--puerto", help="COM del ESP32 para capturar huellas del AS608")
    ap.add_argument("--huellas", nargs="*", default=[], help="archivos .bin o imágenes")
    ap.add_argument("--fuente-huella", default="as608")
    ap.add_argument("--rostros", nargs="*", default=[], help="imágenes; si no hay, se toman de la cámara")
    ap.add_argument("--fuente-rostro", default="camara")
    ap.add_argument("--n-huellas", type=int)
    ap.add_argument("--n-rostros", type=int)
    args = ap.parse_args()

    cfg = config.cargar()
    alm = Almacen(cfg.carpeta_datos)
    if alm.usuario(args.id):
        print(f"El ID {args.id} ya existe.")
        return 2
    pin = getpass.getpass("PIN de 4 dígitos: ")
    if pin != getpass.getpass("Repite el PIN: "):
        print("No coinciden.")
        return 2

    nibble_alto = bool(cfg.valor("huella.nibble_alto_primero", True))
    n_h = args.n_huellas or int(cfg.valor("registro.capturas_huella", 5))
    if args.puerto:
        imgs_h = huellas_del_sensor(args.puerto, n_h, nibble_alto)
    else:
        imgs_h = [huella.leer(f, nibble_alto) for p in args.huellas for f in sorted(glob.glob(p))]

    n_r = args.n_rostros or int(cfg.valor("registro.cuadros_rostro", 15))
    if args.rostros:
        cuadros = [leer_png(Path(f), color=True) for p in args.rostros for f in sorted(glob.glob(p))]
    else:
        cam = camara.desde_config(cfg)
        print(f"\nMira a la cámara y gira un poco la cabeza. {n_r} cuadros...")
        cuadros = []
        for _ in range(n_r):
            cuadros.append(cam.capturar())
            time.sleep(0.5)
        cam.cerrar()

    fondo = registro.caras_de_fondo(cfg.carpeta_datos / "datasets" / "orl", excluir=set())
    inf = registro.registrar(alm, args.id, args.nombre, args.nivel, pin,
                             [(i, args.fuente_huella) for i in imgs_h], [(c, args.fuente_rostro) for c in cuadros],
                             fondo=fondo)
    print(f"\nUsuario {args.id} registrado: {inf.huellas_ok} huellas, {inf.rostros_ok} rostros.")
    for m in inf.huellas_rechazadas:
        print(f"  Huella rechazada: {m}")
    if inf.rostros_rechazados:
        print(f"  {inf.rostros_rechazados} cuadros sin rostro (no cuentan)")
    if inf.huellas_ok < 3 or inf.rostros_ok < 10:
        print("  AVISO: por debajo del mínimo (3 huellas, 10 rostros). Conviene borrar y repetir.")
    print("  Recalibra el rostro de ese dominio (calibrar.py, N7).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
