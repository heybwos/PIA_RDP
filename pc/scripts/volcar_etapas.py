"""Pasa huellas por el pipeline y guarda una lámina PNG con las 7 etapas y las minucias.

    python pc/scripts/volcar_etapas.py datos/pruebas/*.bin --perfil as608
    python pc/scripts/volcar_etapas.py a.bin b.bin --comparar     (puntajes entre todas)

Las láminas van a datos/etapas/ (no se suben a git).
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import huella  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]


def _a_u8(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / ((hi - lo) or 1) * 255, 0, 255).astype(np.uint8)


def _orientacion(r: huella.ResultadoHuella) -> np.ndarray:
    base = cv2.cvtColor(r.etapas["original"], cv2.COLOR_GRAY2BGR)
    B = r.pre.mascara.shape[0] // r.pre.mascara_bloques.shape[0]
    for by, bx in zip(*np.nonzero(r.pre.mascara_bloques)):
        th = r.pre.orientacion_bloques[by, bx] + np.pi / 2  # dirección de la cresta
        cx, cy = bx * B + B / 2, by * B + B / 2
        dx, dy = np.cos(th) * B * 0.45, np.sin(th) * B * 0.45
        cv2.line(base, (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy)), (0, 140, 255), 1)
    return base


def lamina(r: huella.ResultadoHuella) -> np.ndarray:
    e = r.etapas
    gris = lambda a: cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)  # noqa: E731
    seg = gris(e["original"]).copy()
    seg[e["segmentacion"] == 0] = (seg[e["segmentacion"] == 0] * 0.35).astype(np.uint8)
    mins = gris(255 - e["esqueleto"] * 255)
    for m in r.minucias:
        color = (0, 0, 220) if m.tipo == "T" else (200, 90, 0)
        cv2.circle(mins, (m.x, m.y), 4, color, 1)
        cv2.line(mins, (m.x, m.y), (int(m.x + 9 * np.cos(m.t)), int(m.y + 9 * np.sin(m.t))), color, 1)
    paneles = [
        ("original", gris(e["original"])),
        ("normalizada", gris(_a_u8(e["normalizada"]))),
        ("segmentacion", seg),
        ("orientacion", _orientacion(r)),
        ("gabor", gris(_a_u8(e["gabor"]))),
        ("binaria", gris(255 - e["binaria"] * 255)),
        (f"minucias ({len(r.minucias)})", mins),
    ]
    filas = []
    for nombre, p in paneles:
        p = p.copy()
        cv2.putText(p, nombre, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 0), 1, cv2.LINE_AA)
        filas.append(p)
    return np.hstack(filas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivos", nargs="+")
    ap.add_argument("--perfil", default="as608")
    ap.add_argument("--salida", type=Path, default=RAIZ / "datos" / "etapas")
    ap.add_argument("--comparar", action="store_true")
    args = ap.parse_args()
    rutas = [Path(f) for patron in args.archivos for f in sorted(glob.glob(patron))]
    args.salida.mkdir(parents=True, exist_ok=True)
    res = {}
    for ruta in rutas:
        r = huella.procesar(huella.leer(ruta), args.perfil)
        res[ruta.stem] = r
        destino = args.salida / f"{ruta.stem}_etapas.png"
        cv2.imwrite(str(destino), lamina(r))
        print(f"{ruta.name}: {len(r.minucias)} minucias, calidad {r.calidad:.2f}, "
              f"{r.duracion_ms:.0f} ms -> {destino.name}")
    if args.comparar and len(res) > 1:
        print("\nPuntajes:")
        nombres = list(res)
        for i, a in enumerate(nombres):
            for b in nombres[i + 1 :]:
                print(f"  {a} vs {b}: {huella.comparar(res[a], res[b]).puntaje:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
