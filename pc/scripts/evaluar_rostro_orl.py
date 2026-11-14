"""Mide el pipeline de rostro en ORL: detección de Viola-Jones y verificación con Eigenfaces.

    python pc/scripts/evaluar_rostro_orl.py [--carpeta datos/datasets/orl]

Protocolo (sección 4.5 del roadmap): por persona, 6 imágenes para registrar y 4 para
verificar. El modelo se entrena con las de registro de las 40 personas. Genuino: una
imagen de prueba contra los 6 vectores de su persona (distancia mínima). Impostor: contra
los de cada una de las otras 39.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import rostro  # noqa: E402
from pia.rostro.eigenfaces import distancia_minima  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]


def eer(gen: np.ndarray, imp: np.ndarray) -> tuple[float, float]:
    """Para distancias: se acepta si d < umbral."""
    mejor = (1.0, 0.0, 1.0)
    for u in np.unique(np.concatenate([gen, imp])):
        far, frr = float((imp < u).mean()), float((gen >= u).mean())
        if abs(far - frr) < mejor[2]:
            mejor = ((far + frr) / 2, float(u), abs(far - frr))
    return mejor[0], mejor[1]


def cargar_orl(carpeta: Path):
    personas = sorted((p for p in carpeta.glob("s*") if p.is_dir()), key=lambda p: int(p.name[1:]))
    return {p.name: [cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
                     for f in sorted(p.glob("*.pgm"), key=lambda f: int(f.stem))] for p in personas}


def evaluar(carpeta: Path, registro: int = 6, imprimir: bool = True) -> dict:
    datos = cargar_orl(carpeta)
    metodos, sin_relleno = Counter(), 0
    proc = {}
    for pid, imgs in datos.items():
        proc[pid] = []
        for g in imgs:
            sin_relleno += rostro.detectar(g, permitir_relleno=False).rostro is not None
            r = rostro.procesar(g)
            metodos[r.alineado.metodo] += 1
            proc[pid].append(r)
    total = sum(len(v) for v in proc.values())
    con_relleno = total - metodos["sin_rostro"]

    entren = np.array([r.vector for v in proc.values() for r in v[:registro]])
    modelo = rostro.entrenar(entren)
    vect = {pid: modelo.proyectar(np.array([r.vector for r in v[:registro]])) for pid, v in proc.items()}
    gen, imp, aciertos, pruebas = [], [], 0, 0
    for pid, v in proc.items():
        for r in v[registro:]:
            w = modelo.proyectar(r.vector)
            dists = {otro: distancia_minima(w, vs) for otro, vs in vect.items()}
            gen.append(dists[pid])
            imp.extend(d for o, d in dists.items() if o != pid)
            aciertos += min(dists, key=dists.get) == pid
            pruebas += 1
    gen, imp = np.array(gen), np.array(imp)
    tasa, umbral = eer(gen, imp)
    res = dict(total=total, sin_relleno=sin_relleno, con_relleno=con_relleno, metodos=dict(metodos),
               k=modelo.k, varianza=modelo.varianza_explicada, eer=tasa, umbral=umbral,
               rango1=aciertos / pruebas, genuinos=gen, impostores=imp)
    if imprimir:
        print(f"ORL: {total} imágenes, {len(datos)} personas")
        print(f"Viola-Jones sin relleno: {sin_relleno}/{total} = {sin_relleno / total:.1%}")
        print(f"Viola-Jones con relleno: {con_relleno}/{total} = {con_relleno / total:.1%}")
        print(f"Alineación: {dict(metodos)}")
        print(f"Eigenfaces: k = {modelo.k} componentes, varianza {modelo.varianza_explicada:.1%}")
        print(f"Genuinos  d = {gen.min():.2f} .. {gen.max():.2f} (media {gen.mean():.2f})")
        print(f"Impostores d = {imp.min():.2f} .. {imp.max():.2f} (media {imp.mean():.2f})")
        print(f"EER = {tasa:.1%} con umbral d < {umbral:.2f};  identificación rango 1 = {aciertos / pruebas:.1%}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carpeta", type=Path, default=RAIZ / "datos" / "datasets" / "orl")
    args = ap.parse_args()
    for flujo in (sys.stdout,):
        flujo.reconfigure(errors="replace")
    if not args.carpeta.exists():
        print(f"No está ORL en {args.carpeta}. Corre: python pc/scripts/descargar_datasets.py orl")
        return 2
    evaluar(args.carpeta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
