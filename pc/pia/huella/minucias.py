"""Fase 3 de la huella: extracción de minucias por número de cruce."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .parametros import Perfil
from .preproceso import Preproceso


@dataclass(frozen=True)
class Minucia:
    x: int
    y: int
    t: float      # dirección en [0, π)
    tipo: str     # "T" terminación, "B" bifurcación

    def como_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "t": round(self.t, 4), "tipo": self.tipo}


def extraer(pre: Preproceso, p: Perfil) -> list[Minucia]:
    sk = pre.esqueleto.astype(np.int8)
    H, W = sk.shape
    B = p.bloque
    # Los 8 vecinos en orden circular: N, NE, E, SE, S, SO, O, NO
    desp = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    pad = np.pad(sk, 1)
    vec = [pad[1 + dy : 1 + dy + H, 1 + dx : 1 + dx + W] for dy, dx in desp]
    cn = sum(np.abs(vec[k] - vec[(k + 1) % 8]) for k in range(8)) // 2

    m = p.margen_minucias
    valido = np.zeros((H, W), bool)
    valido[m : H - m, m : W - m] = True
    interior = np.kron(pre.bloques_interiores, np.ones((B, B), np.uint8)).astype(bool)
    interior = np.pad(interior, ((0, H - interior.shape[0]), (0, W - interior.shape[1])))
    sel = (sk == 1) & valido & interior & ((cn == 1) | (cn == 3))

    ys, xs = np.nonzero(sel)
    tipos = np.where(cn[ys, xs] == 1, "T", "B")
    ts = np.mod(pre.orientacion[ys, xs] + np.pi / 2, np.pi)

    # Limpieza: minucias muy cercanas entre sí son ruido (espolones, puentes, cortes)
    pts = np.stack([xs, ys], axis=1).astype(np.float32)
    if len(pts):
        d = np.hypot(*(pts[:, None, :] - pts[None, :, :]).transpose(2, 0, 1))
        np.fill_diagonal(d, np.inf)
        quedan = (d >= p.distancia_min_minucias).all(axis=1)
    else:
        quedan = np.zeros(0, bool)
    return [Minucia(int(x), int(y), float(t), str(k))
            for x, y, t, k, q in zip(xs, ys, ts, tipos, quedan) if q]
