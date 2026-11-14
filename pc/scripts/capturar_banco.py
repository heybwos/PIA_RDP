"""P3: banco de huellas del AS608 para calibrar (no son usuarios). Sección 4.5 del roadmap.

    python pc/scripts/capturar_banco.py --puerto COM4               (te pregunta cada dedo)
    python pc/scripts/capturar_banco.py --puerto COM4 --dedos 6 --capturas 8

Necesita el firmware test_huella_imagen. Cada dedo es una identidad distinta: una sola persona
puede aportar hasta 10. Guarda en datos/banco_as608/<identidad>/<nn>.png (8 bits).
Varía a propósito: presión, un poco de giro, dedo algo seco. La demo no será más limpia.
Cada captura se pasa por el pipeline: si salen menos de 8 minucias se descarta y se repite.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bajar_huella as bh  # noqa: E402
from pia import config, huella  # noqa: E402
from pia.almacen import guardar_png  # noqa: E402

MIN_MINUCIAS = 8


def capturar(enlace: bh.Enlace, nibble_alto: bool) -> np.ndarray | None:
    enlace.enviar("PEDIR_HUELLA")
    while True:
        ln = enlace.linea(25.0)
        if ln is None:
            print("    El ESP32 no contestó.")
            return None
        if ln == "HUELLA:ESPERA":
            print("    Pon el dedo...", flush=True)
        elif ln == "HUELLA:DEDO":
            print("    Leyendo (unos 7 s, no lo muevas)...", flush=True)
        elif ln.startswith("HUELLA:ERR"):
            print(f"    {ln}: no detectó dedo a tiempo.")
            return None
        elif ln.startswith("IMG:") and not ln.startswith("IMG:FIN"):
            n = int(ln.split(":")[1])
            datos = enlace.bytes_exactos(n)
            fin = enlace.linea(3.0)
            if datos is None or not fin or not fin.startswith("IMG:FIN:"):
                enlace.descartar()
                print("    Imagen cortada; se repite.")
                return None
            import zlib

            if int(fin.split(":")[2], 16) != zlib.crc32(datos) & 0xFFFFFFFF or n != huella.imagen.BYTES_AS608:
                print("    CRC incorrecto o imagen incompleta; se repite.")
                return None
            return huella.desempacar(datos, nibble_alto)


def nombre_valido(t: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", t.strip().lower()).strip("_")


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", required=True)
    ap.add_argument("--dedos", type=int, default=8)
    ap.add_argument("--capturas", type=int, default=8)
    args = ap.parse_args()

    cfg = config.cargar()
    nibble_alto = bool(cfg.valor("huella.nibble_alto_primero", True))
    banco = cfg.carpeta_datos / "banco_as608"
    banco.mkdir(parents=True, exist_ok=True)

    enlace = bh.Enlace(args.puerto, 921600)
    try:
        if not bh.esperar_esp32(enlace):
            print("El ESP32 no responde. ¿Está cargado test_huella_imagen? ¿Monitor serie cerrado?")
            return 2
        enlace.descartar(0.3)
        for d in range(args.dedos):
            existentes = sorted(p.name for p in banco.iterdir() if p.is_dir())
            sugerido = f"dedo_{len(existentes) + 1:02d}"
            print(f"\n=== Dedo {d + 1} de {args.dedos} === (ya hay {len(existentes)} en el banco)")
            print("Nombre de la identidad, por ejemplo nestor_indice_der (Enter = "
                  f"{sugerido}, 'fin' para terminar): ", end="", flush=True)
            t = input().strip()
            if t.lower() == "fin":
                break
            ident = nombre_valido(t) or sugerido
            carpeta = banco / ident
            ya = len(list(carpeta.glob("*.png"))) if carpeta.exists() else 0
            print(f"Identidad '{ident}': {ya} capturas previas. Faltan {max(0, args.capturas - ya)}.")
            resultados = []
            k = ya
            while k < args.capturas:
                print(f"  Captura {k + 1} de {args.capturas}: levanta el dedo y vuelve a ponerlo"
                      + (" (cambia un poco la presión o el giro)" if k else ""))
                time.sleep(1.5)
                img = capturar(enlace, nibble_alto)
                if img is None:
                    continue
                r = huella.procesar(img, "as608")
                if len(r.minucias) < MIN_MINUCIAS:
                    print(f"    Solo {len(r.minucias)} minucias (calidad {r.calidad:.2f}): se descarta. "
                          "Pon más superficie del dedo.")
                    continue
                guardar_png(carpeta / f"{k + 1:02d}.png", img)
                resultados.append(r)
                print(f"    OK: {len(r.minucias)} minucias, calidad {r.calidad:.2f}")
                k += 1
            if len(resultados) >= 2:  # retroalimentación: qué tanto se parece a sí mismo
                p = [huella.comparar(resultados[0], x).puntaje for x in resultados[1:]]
                print(f"  Parecido con la primera: media {np.mean(p):.2f}, mínimo {min(p):.2f}")
        total = sum(len(list(p.glob('*.png'))) for p in banco.iterdir() if p.is_dir())
        ids = [p.name for p in banco.iterdir() if p.is_dir()]
        print(f"\nBanco: {len(ids)} identidades, {total} capturas en {banco}")
        return 0
    finally:
        enlace.cerrar()


if __name__ == "__main__":
    sys.exit(main())
