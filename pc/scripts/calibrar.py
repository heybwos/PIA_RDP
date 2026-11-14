"""N7 / P6: calibración de umbrales con datos reales.

Huella (banco del AS608, sección 4.5):
    python pc/scripts/calibrar.py --factor huella --dominio as608 [--activar]
  5 capturas de plantilla y 3 de prueba por identidad; puntaje = máximo contra las plantillas.

Rostro con cámara (usuarios registrados con fuente "camara"):
    python pc/scripts/calibrar.py --factor rostro --dominio camara [--activar]
  Genuinos: la segunda tanda de cada usuario (datos/rostros_tanda2/<id>/, se captura con
  pc/scripts/capturar_rostros.py minutos después del registro) contra sus vectores.
  Impostores: esas mismas tandas contra los demás usuarios, y caras de ORL (imágenes 7 a 10
  de las 40 personas) pasadas por el mismo pipeline contra cada usuario.

Umbral (--criterio):
  eer   el del EER.
  far0  apenas por encima del impostor más alto (ningún impostor del banco pasa).
  auto  (por defecto) far0 si el EER pasa de 15 % (recorte de N7 en el roadmap), si no eer.
Guarda curvas FAR/FRR y distribuciones en datos/calibracion/<factor>_<dominio>.png y .csv.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import calibracion, config, huella, rostro  # noqa: E402
from pia.almacen import Almacen  # noqa: E402
from pia.rostro.eigenfaces import distancia_minima  # noqa: E402

N_PLANTILLAS = 5


def huella_banco(carpeta: Path, perfil_: str) -> tuple[list[float], list[float], dict]:
    banco = {d.name: [huella.leer(f) for f in sorted(d.glob("*.png"))]
             for d in sorted(p for p in carpeta.iterdir() if p.is_dir())}
    banco = {k: v for k, v in banco.items() if len(v) > N_PLANTILLAS}
    R = {k: [huella.procesar(i, perfil_) for i in v] for k, v in banco.items()}
    gen, imp = [], []
    for k, rs in R.items():
        for k2, rs2 in R.items():
            for x in rs2[N_PLANTILLAS:]:
                s = max(huella.comparar(t, x).puntaje for t in rs[:N_PLANTILLAS])
                (gen if k == k2 else imp).append(s)
    return gen, imp, {"banco": str(carpeta), "identidades": len(banco), "perfil": perfil_,
                      "registro": f"1-{N_PLANTILLAS}", "prueba": f"{N_PLANTILLAS + 1}+"}


def rostro_camara(alm: Almacen, cfg) -> tuple[list[float], list[float], dict, int]:
    activo = alm.modelo_activo("camara")
    if not activo:
        raise SystemExit("No hay modelo de rostro 'camara': registra al menos un usuario con cámara.")
    mid, modelo = activo
    usuarios = sorted({m["usuario_id"] for m in alm.muestras_rostro("camara")})
    vect = {u: alm.vectores(u, mid) for u in usuarios}
    tandas = cfg.carpeta_datos / "rostros_tanda2"
    pruebas: dict[str, list[np.ndarray]] = {}
    for u in usuarios:
        for f in sorted((tandas / u).glob("*.png")):
            r = rostro.procesar(cv2.imdecode(np.fromfile(str(f), np.uint8), cv2.IMREAD_COLOR), modelo, False)
            if r.hay_rostro:
                pruebas.setdefault(u, []).append(r.pesos)
    if not pruebas:
        raise SystemExit(f"No hay segunda tanda en {tandas}. Captúrala con pc/scripts/capturar_rostros.py --id <ID>")
    gen, imp = [], []
    for u, ws in pruebas.items():
        for w in ws:
            for u2, vs in vect.items():
                (gen if u == u2 else imp).append(distancia_minima(w, vs))
    n_dataset = 0
    orl = cfg.carpeta_datos / "datasets" / "orl"
    for p in range(1, 41):
        for j in range(7, 11):
            f = orl / f"s{p}" / f"{j}.pgm"
            if not f.exists():
                continue
            r = rostro.procesar(cv2.imread(str(f), cv2.IMREAD_GRAYSCALE), modelo)
            if r.hay_rostro:
                n_dataset += 1
                imp.extend(distancia_minima(r.pesos, vs) for vs in vect.values())
    info = {"usuarios": usuarios, "con_tanda2": sorted(pruebas), "impostores_dataset": n_dataset, "modelo_id": mid}
    return gen, imp, info, mid


def grafica(gen, imp, umbral: float, mayor_es_mejor: bool, titulo: str, destino: Path) -> None:
    """Distribuciones y curvas FAR/FRR dibujadas con OpenCV (sin dependencias extra)."""
    W, H, m = 900, 520, 60
    img = np.full((H, W, 3), 255, np.uint8)
    g, i = np.asarray(gen), np.asarray(imp)
    lo, hi = float(min(g.min(), i.min())), float(max(g.max(), i.max()))
    hi = hi if hi > lo else lo + 1
    X = lambda v: int(m + (v - lo) / (hi - lo) * (W - 2 * m))  # noqa: E731
    base = H - m
    bordes = np.linspace(lo, hi, 41)
    hg, hi_ = np.histogram(g, bordes)[0], np.histogram(i, bordes)[0]
    tope = max(hg.max() / len(g), hi_.max() / len(i))
    for k in range(40):
        for h, n, color in ((hi_, len(i), (80, 80, 230)), (hg, len(g), (90, 170, 60))):
            alto = int(h[k] / n / tope * (H * 0.45))
            cv2.rectangle(img, (X(bordes[k]) + 1, base - alto), (X(bordes[k + 1]) - 1, base), color, 1)
    us = np.linspace(lo, hi, 200)
    for curva, color in ((lambda u: (i >= u).mean() if mayor_es_mejor else (i < u).mean(), (40, 40, 200)),
                         (lambda u: (g < u).mean() if mayor_es_mejor else (g >= u).mean(), (40, 140, 40))):
        pts = np.array([[X(u), int(base - curva(u) * (H - 2 * m))] for u in us], np.int32)
        cv2.polylines(img, [pts], False, color, 2, cv2.LINE_AA)
    cv2.line(img, (X(umbral), m), (X(umbral), base), (0, 0, 0), 1)
    cv2.line(img, (m, base), (W - m, base), (0, 0, 0), 1)
    t = lambda s, x, y, c=(0, 0, 0): cv2.putText(img, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1, cv2.LINE_AA)  # noqa: E731
    t(titulo, m, 30)
    t(f"umbral {umbral:.3f}", X(umbral) + 6, m + 14)
    t("genuinos / FRR", W - 330, 30, (40, 140, 40))
    t("impostores / FAR", W - 180, 30, (40, 40, 200))
    t(f"{lo:.2f}", m - 10, base + 20)
    t(f"{hi:.2f}", W - m - 20, base + 20)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".png", img)[1].tofile(str(destino))


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--factor", choices=["huella", "rostro"], required=True)
    ap.add_argument("--dominio", required=True, help="huella: as608 | rostro: camara")
    ap.add_argument("--banco", type=Path, help="carpeta del banco de huellas (por defecto datos/banco_as608)")
    ap.add_argument("--criterio", choices=["auto", "eer", "far0"], default="auto")
    ap.add_argument("--activar", action="store_true", help="guarda la calibración como activa")
    args = ap.parse_args()
    cfg = config.cargar()
    alm = Almacen(cfg.carpeta_datos)
    mayor = args.factor == "huella"
    modelo_id = None
    if args.factor == "huella":
        gen, imp, info = huella_banco(args.banco or cfg.carpeta_datos / "banco_as608", args.dominio)
    else:
        gen, imp, info, modelo_id = rostro_camara(alm, cfg)
    if len(gen) < 3 or len(imp) < 3:
        print(f"Muy pocos pares (genuinos {len(gen)}, impostores {len(imp)}).")
        return 2
    g, i = np.array(gen), np.array(imp)
    r = calibracion.por_eer(g, i, mayor_es_mejor=mayor)
    u_far0 = float(i.max()) + 1e-6 if mayor else float(i.min()) - 1e-6
    frr_far0 = float((g < u_far0).mean()) if mayor else float((g >= u_far0).mean())
    criterio = args.criterio if args.criterio != "auto" else ("far0" if r.eer > 0.15 else "eer")
    umbral = u_far0 if criterio == "far0" else r.umbral
    far, frr = calibracion.tasas(g, i, umbral, mayor)
    print(f"{args.factor} / {args.dominio}: {len(g)} genuinos, {len(i)} impostores")
    print(f"  Genuinos   {g.min():.3f} .. {g.max():.3f} (media {g.mean():.3f})")
    print(f"  Impostores {i.min():.3f} .. {i.max():.3f} (media {i.mean():.3f})")
    print(f"  EER {r.eer:.1%} con umbral {r.umbral:.3f}")
    print(f"  FAR = 0 con umbral {u_far0:.3f}: FRR {frr_far0:.1%}")
    print(f"  Elegido ({criterio}): umbral {umbral:.3f} -> FAR {far:.1%}, FRR {frr:.1%}")
    for k, v in info.items():
        print(f"  {k}: {v}")
    nombre = f"{args.factor}_{args.dominio}"
    carpeta = cfg.carpeta_datos / "calibracion"
    grafica(g, i, umbral, mayor, f"{args.factor} {args.dominio}: EER {r.eer:.1%}, umbral {umbral:.3f} ({criterio})",
            carpeta / f"{nombre}.png")
    with open(carpeta / f"{nombre}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tipo", "valor"])
        w.writerows([("genuino", v) for v in g] + [("impostor", v) for v in i])
    print(f"  Gráfica y puntajes: {carpeta / nombre}.png / .csv")
    if args.activar:
        cid = alm.guardar_calibracion(args.factor, args.dominio, umbral, r.eer, far, frr, len(g), len(i),
                                      modelo_id=modelo_id,
                                      parametros={**info, "criterio": criterio, "umbral_eer": r.umbral,
                                                  "umbral_far0": u_far0, "frr_far0": frr_far0,
                                                  "distribucion": calibracion.distribucion(g, i)})
        print(f"  Calibración #{cid} activa.")
    else:
        print("  (no se activó: agrega --activar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
