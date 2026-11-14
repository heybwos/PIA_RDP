"""Fase 4 de la huella: matching por grafos de minucias.

Estructuras locales (k = 4 vecinos más cercanos, con distancia, ángulo relativo y
orientación relativa) para proponer correspondencias, y consolidación global: cada
candidata fija una rotación y traslación, y se cuentan las minucias que caen a menos
de 10 px con dirección compatible. Puntaje = m² / (nA · nB).
Port de knn y matchMinutiae de la maqueta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .minucias import Minucia

K = 4
CANDIDATAS = 40
DIST_PAR = 10.0
ANG_PAR = 0.3


def _ang_pi(a):
    return np.mod(a, np.pi)


def _d_pi(a, b):
    d = _ang_pi(a - b)
    return np.minimum(d, np.pi - d)


@dataclass
class ResultadoMatching:
    puntaje: float
    pares: list[tuple[int, int]] = field(default_factory=list)
    aristas_a: list[tuple[int, int]] = field(default_factory=list)
    aristas_b: list[tuple[int, int]] = field(default_factory=list)


def _arreglos(M: list[Minucia]):
    x = np.array([m.x for m in M], np.float64)
    y = np.array([m.y for m in M], np.float64)
    t = np.array([m.t for m in M], np.float64)
    tipo = np.array([m.tipo for m in M])
    return x, y, t, tipo


def _vecinos(x, y):
    d = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
    np.fill_diagonal(d, np.inf)
    orden = np.argsort(d, axis=1, kind="stable")[:, :K]
    return orden, np.take_along_axis(d, orden, axis=1)


def _descriptores(x, y, t):
    vec, dist = _vecinos(x, y)
    ang = _ang_pi(np.arctan2(y[vec] - y[:, None], x[vec] - x[:, None]) - t[:, None])
    ori = _ang_pi(t[vec] - t[:, None])
    return vec, dist, ang, ori


def _aristas(vec) -> list[tuple[int, int]]:
    tres = vec[:, :3]
    e = []
    for i, fila in enumerate(tres):
        for j in fila:
            if i < j or i not in tres[j]:
                e.append((i, int(j)))
    return e


def comparar(A: list[Minucia], B: list[Minucia]) -> ResultadoMatching:
    if len(A) < K + 1 or len(B) < K + 1:
        return ResultadoMatching(0.0)
    xa, ya, ta, tipa = _arreglos(A)
    xb, yb, tb, tipb = _arreglos(B)
    va, da, aa, oa = _descriptores(xa, ya, ta)
    vb, db, ab, ob = _descriptores(xb, yb, tb)

    # Costo local de cada par (i de A, j de B) del mismo tipo
    costo = (
        np.abs(da[:, None, :] - db[None, :, :]).sum(2) / 8
        + _d_pi(aa[:, None, :], ab[None, :, :]).sum(2) / 0.35
        + _d_pi(oa[:, None, :], ob[None, :, :]).sum(2) / 0.35
    )
    costo[tipa[:, None] != tipb[None, :]] = np.inf
    plano = np.argsort(costo, axis=None, kind="stable")[:CANDIDATAS]
    plano = plano[np.isfinite(costo.flat[plano])]

    mejor_m, mejores = 0, []
    for c in plano:
        i0, j0 = np.unravel_index(c, costo.shape)
        for giro in (0.0, np.pi):
            rot = tb[j0] - ta[i0] + giro
            co, si = np.cos(rot), np.sin(rot)
            X, Y = xa - xa[i0], ya - ya[i0]
            px, py = co * X - si * Y + xb[j0], si * X + co * Y + yb[j0]
            d = np.hypot(px[:, None] - xb[None, :], py[:, None] - yb[None, :])
            d[_d_pi(ta[:, None] + rot, tb[None, :]) >= ANG_PAR] = np.inf
            usado = np.zeros(len(B), bool)
            pares = []
            for i in range(len(A)):  # codicioso en orden, como la maqueta
                fila = np.where(usado, np.inf, d[i])
                j = int(np.argmin(fila))
                if fila[j] < DIST_PAR:
                    usado[j] = True
                    pares.append((i, j))
            if len(pares) > mejor_m:
                mejor_m, mejores = len(pares), pares

    return ResultadoMatching(mejor_m * mejor_m / (len(A) * len(B)), mejores, _aristas(va), _aristas(vb))
