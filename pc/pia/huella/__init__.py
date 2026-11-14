"""Pipeline de huella: imagen en gris -> etapas -> minucias -> puntaje en [0, 1].

    from pia import huella
    r = huella.procesar(img, "as608")
    m = huella.comparar(r_plantilla, r)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from . import minucias as _minucias
from .imagen import desempacar, leer
from .matching import ResultadoMatching
from .matching import comparar as _comparar
from .minucias import Minucia
from .parametros import PERFILES, Perfil, perfil
from .preproceso import Preproceso, preprocesar

__all__ = ["procesar", "comparar", "ResultadoHuella", "ResultadoMatching", "Minucia",
           "Perfil", "PERFILES", "perfil", "leer", "desempacar"]


@dataclass
class ResultadoHuella:
    etapas: dict[str, np.ndarray]
    minucias: list[Minucia]
    calidad: float          # 0..1: área útil por coherencia media del campo de orientación
    pre: Preproceso = field(repr=False)
    duracion_ms: float = 0.0


def procesar(img: np.ndarray, perfil_: str | Perfil = "as608") -> ResultadoHuella:
    t0 = time.perf_counter()
    p = perfil(perfil_)
    pre = preprocesar(img, p)
    mins = _minucias.extraer(pre, p)
    area = float(pre.mascara_bloques.mean())
    coh = float(pre.coherencia[pre.mascara_bloques > 0].mean()) if area else 0.0
    etapas = {
        "original": img[: pre.mascara.shape[0], : pre.mascara.shape[1]],
        "normalizada": pre.normalizada,
        "segmentacion": pre.mascara,
        "orientacion": pre.orientacion_bloques,
        "gabor": pre.gabor,
        "binaria": pre.binaria,
        "esqueleto": pre.esqueleto,
    }
    return ResultadoHuella(etapas, mins, area * coh, pre, (time.perf_counter() - t0) * 1000)


def comparar(a: ResultadoHuella | list[Minucia], b: ResultadoHuella | list[Minucia]) -> ResultadoMatching:
    ma = a.minucias if isinstance(a, ResultadoHuella) else a
    mb = b.minucias if isinstance(b, ResultadoHuella) else b
    return _comparar(ma, mb)
