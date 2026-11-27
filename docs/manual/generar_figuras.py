"""Figuras del manual: cada etapa de la huella y del rostro con el código real del proyecto.

Usa solo datos públicos (FVC2002 DB1_B y ORL): ninguna huella ni cara del equipo.
    .\\.venv\\Scripts\\python.exe docs\\manual\\generar_figuras.py
Salida: docs/manual/figuras/*.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "pc"))
from pia import huella, rostro  # noqa: E402
from pia.huella.preproceso import _kernels_gabor  # noqa: E402

SAL = Path(__file__).resolve().parent / "figuras"
SAL.mkdir(exist_ok=True)
DATOS = RAIZ / "datos" / "datasets"
VERDE, NARANJA = (154, 196, 116), (48, 146, 255)  # BGR


def u8(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    lo, hi = float(a.min()), float(a.max())
    return np.zeros(a.shape, np.uint8) if hi == lo else ((a - lo) / (hi - lo) * 255).astype(np.uint8)


def guardar(nombre: str, img: np.ndarray, escala: int = 1) -> None:
    if escala > 1:
        img = cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)
    cv2.imencode(".png", img)[1].tofile(str(SAL / nombre))
    print("  ", nombre, img.shape[1], "x", img.shape[0])


# ------------------------------------------------------------------ huella
def figuras_huella() -> None:
    ruta = DATOS / "fvc2002" / "DB1_B" / "101_1.tif"
    img = huella.leer(ruta)
    r = huella.procesar(img, "fvc2002")
    e, pre = r.etapas, r.pre
    guardar("h1_original.png", e["original"])
    guardar("h2_normalizada.png", u8(e["normalizada"]))
    seg = cv2.cvtColor(e["original"], cv2.COLOR_GRAY2BGR)
    seg[e["segmentacion"] == 0] = (seg[e["segmentacion"] == 0] * 0.25).astype(np.uint8)
    guardar("h3_segmentacion.png", seg)
    # orientación: un segmento por bloque, perpendicular al gradiente (= dirección de la cresta)
    claro = (255 - (255 - e["original"].astype(np.float32)) * 0.35).astype(np.uint8)
    ori = cv2.resize(cv2.cvtColor(claro, cv2.COLOR_GRAY2BGR), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    B = pre.mascara.shape[0] // pre.mascara_bloques.shape[0]
    for by in range(pre.mascara_bloques.shape[0]):
        for bx in range(pre.mascara_bloques.shape[1]):
            if not pre.mascara_bloques[by, bx]:
                continue
            t = pre.orientacion_bloques[by, bx] + np.pi / 2
            cx, cy, L = bx * B + B / 2, by * B + B / 2, B * 0.42 * (0.4 + 0.6 * pre.coherencia[by, bx])
            p1 = (int(2 * (cx - L * np.cos(t))), int(2 * (cy - L * np.sin(t))))
            p2 = (int(2 * (cx + L * np.cos(t))), int(2 * (cy + L * np.sin(t))))
            cv2.line(ori, p1, p2, (30, 110, 20), 3, cv2.LINE_AA)
    guardar("h4_orientacion.png", ori)
    guardar("h5_gabor.png", u8(e["gabor"]))
    guardar("h6_binaria.png", 255 - e["binaria"] * 255)
    guardar("h7_esqueleto.png", 255 - e["esqueleto"] * 255)
    mi = cv2.cvtColor(255 - e["esqueleto"] * 200, cv2.COLOR_GRAY2BGR)
    mi = cv2.resize(mi, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    for m in r.minucias:
        c = (m.x * 2, m.y * 2)
        d = (int(c[0] + 16 * np.cos(m.t)), int(c[1] + 16 * np.sin(m.t)))
        col = VERDE if m.tipo == "T" else NARANJA
        if m.tipo == "T":
            cv2.circle(mi, c, 7, col, 2, cv2.LINE_AA)
        else:
            cv2.rectangle(mi, (c[0] - 7, c[1] - 7), (c[0] + 7, c[1] + 7), col, 2, cv2.LINE_AA)
        cv2.line(mi, c, d, col, 2, cv2.LINE_AA)
    guardar("h8_minucias.png", mi)
    nT = sum(m.tipo == "T" for m in r.minucias)
    print(f"   minucias: {len(r.minucias)} ({nT} T, {len(r.minucias) - nT} B), calidad {r.calidad:.2f}")
    # kernels de Gabor (4 de las 24 orientaciones)
    ks = _kernels_gabor(huella.perfil("fvc2002"))
    tiles = [u8(ks[i]) for i in (0, 6, 12, 18)]
    tiles = [cv2.resize(t, (90, 90), interpolation=cv2.INTER_NEAREST) for t in tiles]
    sep = np.full((90, 8), 255, np.uint8)
    guardar("h_gabor_kernels.png", np.hstack([tiles[0], sep, tiles[1], sep, tiles[2], sep, tiles[3]]))
    # comparación genuina e impostora (puntajes reales del matching)
    gen = huella.procesar(huella.leer(DATOS / "fvc2002" / "DB1_B" / "101_2.tif"), "fvc2002")
    imp = huella.procesar(huella.leer(DATOS / "fvc2002" / "DB1_B" / "102_1.tif"), "fvc2002")
    print(f"   puntaje 101_1 vs 101_2 (misma persona): {huella.comparar(r, gen).puntaje:.3f}")
    print(f"   puntaje 101_1 vs 102_1 (otra persona):  {huella.comparar(r, imp).puntaje:.3f}")


# ------------------------------------------------------------------ rostro
def figuras_rostro() -> None:
    orl = DATOS / "orl"
    cara = cv2.imread(str(orl / "s1" / "1.pgm"), cv2.IMREAD_GRAYSCALE)
    r = rostro.procesar(cara)
    det = cv2.cvtColor(cara, cv2.COLOR_GRAY2BGR)
    if r.deteccion.rostro:
        x, y, w, h = r.deteccion.rostro
        cv2.rectangle(det, (x, y), (x + w, y + h), VERDE, 1)
    for x, y, w, h in r.deteccion.ojos:
        cv2.rectangle(det, (x, y), (x + w, y + h), NARANJA, 1)
    guardar("r1_deteccion.png", det, 2)
    guardar("r2_alineada.png", r.alineado.imagen, 3)
    guardar("r3_normalizada.png", (r.normalizada.imagen * 255).astype(np.uint8), 3)
    print(f"   detección: rostro {r.deteccion.rostro}, ojos {len(r.deteccion.ojos)}, "
          f"relleno {r.deteccion.con_relleno}, alineación '{r.alineado.metodo}' {r.alineado.angulo_grados:.1f}°")
    # modelo de Eigenfaces de ejemplo: 40 personas x 5 fotos de ORL
    caras = []
    for s in range(1, 41):
        for i in range(1, 6):
            c = cv2.imread(str(orl / f"s{s}" / f"{i}.pgm"), cv2.IMREAD_GRAYSCALE)
            caras.append(rostro.procesar(c).normalizada.imagen)
    modelo = rostro.entrenar(np.array(caras))
    print(f"   modelo ORL: {len(caras)} caras, k = {modelo.k}, varianza {modelo.varianza_explicada:.3f}")
    guardar("r4_media.png", u8(modelo.media.reshape(64, 64)), 3)
    eig = [u8(modelo.eigenfaces[i].reshape(64, 64)) for i in range(6)]
    sep = np.full((64, 4), 255, np.uint8)
    fila = eig[0]
    for e_ in eig[1:]:
        fila = np.hstack([fila, sep, e_])
    guardar("r5_eigenfaces.png", fila, 3)
    x = r.normalizada.imagen.reshape(-1)
    w_ = modelo.proyectar(x)
    recs = []
    for c in (1, 5, 10, 20, modelo.k):
        recs.append(u8(np.clip(modelo.reconstruir(w_, c), 0, 1).reshape(64, 64)))
    fila = recs[0]
    for rc in recs[1:]:
        fila = np.hstack([fila, sep, rc])
    guardar("r6_reconstruccion.png", fila, 3)
    # distancias reales: misma persona (s1/6) y otra (s2/1)
    misma = modelo.proyectar(rostro.procesar(cv2.imread(str(orl / "s1" / "6.pgm"), 0)).normalizada.imagen)
    otra = modelo.proyectar(rostro.procesar(cv2.imread(str(orl / "s2" / "6.pgm"), 0)).normalizada.imagen)
    print(f"   distancia s1/1 vs s1/6 (misma persona): {np.linalg.norm(w_ - misma):.2f}")
    print(f"   distancia s1/1 vs s2/6 (otra persona):  {np.linalg.norm(w_ - otra):.2f}")
    print(f"   pesos (primeros 5): {np.round(w_[:5], 2).tolist()}")


if __name__ == "__main__":
    print("Huella (FVC2002 DB1_B 101_1):")
    figuras_huella()
    print("Rostro (ORL s1/1):")
    figuras_rostro()
