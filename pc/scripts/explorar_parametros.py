"""N7: busca los parámetros del perfil de huella que mejor separan el banco del AS608.

    python pc/scripts/explorar_parametros.py                    (banco datos/banco_as608)
    python pc/scripts/explorar_parametros.py --rapido           (rejilla chica)

Protocolo igual al uso real (sección 4.5): por identidad, 5 capturas de plantilla y 3 de
prueba; el puntaje de una prueba es el máximo contra las 5 plantillas. Genuinos: pruebas
contra su identidad; impostores: contra las demás. Reporta EER, el umbral con FAR = 0 y
cuántos genuinos pasarían con ese umbral (FRR). Ordena por EER y desempata por FRR a FAR 0.

Con pocas identidades el EER tiene mucho ruido: elige una combinación razonable entre las
mejores, no solo la primera. Se guarda la tabla en datos/calibracion/exploracion_huella.csv.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import calibracion, config, huella  # noqa: E402
from pia.huella.parametros import perfil  # noqa: E402

N_PLANTILLAS = 5


def cargar_banco(carpeta: Path) -> dict[str, list[np.ndarray]]:
    banco = {}
    for d in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        imgs = [huella.leer(f) for f in sorted(d.glob("*.png"))]
        if len(imgs) >= N_PLANTILLAS + 1:
            banco[d.name] = imgs
    return banco


def puntajes(banco: dict[str, list[np.ndarray]], p) -> tuple[np.ndarray, np.ndarray, float]:
    R = {k: [huella.procesar(i, p) for i in v] for k, v in banco.items()}
    gen, imp = [], []
    for k, rs in R.items():
        tpl = rs[:N_PLANTILLAS]
        for k2, rs2 in R.items():
            for x in rs2[N_PLANTILLAS:]:
                s = max(huella.comparar(t, x).puntaje for t in tpl)
                (gen if k == k2 else imp).append(s)
    nmin = float(np.mean([len(x.minucias) for rs in R.values() for x in rs]))
    return np.array(gen), np.array(imp), nmin


def far_cero(gen: np.ndarray, imp: np.ndarray) -> tuple[float, float]:
    """Umbral apenas arriba del impostor más alto y el FRR que deja."""
    u = float(imp.max()) + 1e-6 if len(imp) else 0.0
    return u, float((gen < u).mean())


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banco", type=Path)
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--mostrar", type=int, default=12)
    args = ap.parse_args()
    cfg = config.cargar()
    carpeta = args.banco or cfg.carpeta_datos / "banco_as608"
    banco = cargar_banco(carpeta)
    if len(banco) < 3:
        print(f"Hacen falta al menos 3 identidades con 6+ capturas en {carpeta} (hay {len(banco)}).")
        return 2
    n_gen = sum(len(v) - N_PLANTILLAS for v in banco.values())
    print(f"Banco: {len(banco)} identidades; {n_gen} genuinos y {n_gen * (len(banco) - 1)} impostores por combinación.")

    if args.rapido:
        rejilla = dict(ecualizar=[False, True], umbral_varianza=[0.0085, 0.004], distancia_min_minucias=[9.0, 6.0],
                       gabor_frecuencia=[1 / 8.9, 1 / 10], gabor_sigma=[4.0])
    else:
        rejilla = dict(ecualizar=[False, True], umbral_varianza=[0.0085, 0.006, 0.004, 0.003],
                       distancia_min_minucias=[9.0, 6.0, 4.0], gabor_frecuencia=[1 / 8.9, 1 / 10, 1 / 11],
                       gabor_sigma=[4.0, 3.0])
    claves = list(rejilla)
    combos = list(itertools.product(*rejilla.values()))
    filas = []
    t0 = time.monotonic()
    for i, valores in enumerate(combos, 1):
        cambios = dict(zip(claves, valores))
        gen, imp, nmin = puntajes(banco, perfil("as608", **cambios))
        r = calibracion.por_eer(gen, imp, mayor_es_mejor=True)
        u0, frr0 = far_cero(gen, imp)
        filas.append({**cambios, "eer": r.eer, "umbral_eer": r.umbral, "umbral_far0": u0, "frr_far0": frr0,
                      "genuino_medio": float(gen.mean()), "impostor_max": float(imp.max()), "minucias": nmin})
        if i % 10 == 0 or i == len(combos):
            print(f"  {i}/{len(combos)} combinaciones ({time.monotonic() - t0:.0f} s)", flush=True)
    filas.sort(key=lambda f: (round(f["eer"], 4), f["frr_far0"]))
    destino = cfg.carpeta_datos / "calibracion" / "exploracion_huella.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"\nMejores {args.mostrar} (tabla completa en {destino}):")
    print(" ecual  var     dmin  frec   sigma |  EER   FRR@FAR0  gen.med  imp.max  minucias")
    for f in filas[: args.mostrar]:
        print(f" {str(f['ecualizar']):5s}  {f['umbral_varianza']:.4f}  {f['distancia_min_minucias']:3.0f}  "
              f"1/{1 / f['gabor_frecuencia']:4.1f}  {f['gabor_sigma']:3.0f}  | {f['eer']:5.1%}  {f['frr_far0']:6.1%}   "
              f"{f['genuino_medio']:.3f}    {f['impostor_max']:.3f}   {f['minucias']:5.1f}")
    actual = next(f for f in filas if not f["ecualizar"] and f["umbral_varianza"] == 0.0085
                  and f["distancia_min_minucias"] == 9.0 and abs(f["gabor_frecuencia"] - 1 / 8.9) < 1e-9
                  and f["gabor_sigma"] == 4.0)
    print(f"\nPerfil actual: EER {actual['eer']:.1%}, FRR con FAR 0 {actual['frr_far0']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
