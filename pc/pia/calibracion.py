"""Umbrales por EER a partir de puntajes genuinos e impostores.

Huella: se acepta si puntaje ≥ umbral. Rostro: se acepta si distancia < umbral.
Los umbrales candidatos son los puntos medios entre valores consecutivos observados
(más uno por debajo y otro por encima de todos), así el umbral nunca cae justo sobre
una muestra. Se elige el de menor |FAR − FRR|; en empate, el de menor FAR.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Resultado:
    umbral: float
    eer: float
    far: float
    frr: float
    n_genuinos: int
    n_impostores: int


def tasas(g: np.ndarray, i: np.ndarray, u: float, mayor_es_mejor: bool) -> tuple[float, float]:
    if mayor_es_mejor:
        return float((i >= u).mean()), float((g < u).mean())
    return float((i < u).mean()), float((g >= u).mean())


def por_eer(genuinos, impostores, mayor_es_mejor: bool) -> Resultado:
    g, i = np.asarray(genuinos, float), np.asarray(impostores, float)
    v = np.unique(np.concatenate([g, i]))
    candidatos = np.concatenate([[v[0] - 1e-6], (v[:-1] + v[1:]) / 2, [v[-1] + 1e-6]])
    mejor = None
    for u in candidatos:
        far, frr = tasas(g, i, u, mayor_es_mejor)
        clave = (abs(far - frr), far)
        if mejor is None or clave < mejor[0]:
            mejor = (clave, float(u), far, frr)
    _, u, far, frr = mejor
    return Resultado(u, (far + frr) / 2, far, frr, len(g), len(i))
