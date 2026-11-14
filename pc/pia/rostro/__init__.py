"""Pipeline de rostro: cuadro -> Viola-Jones -> alineación -> normalización -> Eigenfaces.

    from pia import rostro
    r = rostro.procesar(cuadro, modelo)          # cuadro BGR o gris
    d, acepta = rostro.comparar(r.pesos, vectores_usuario, umbral)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import cv2
import numpy as np

from .alineacion import LADO, Alineado, alinear
from .deteccion import Deteccion, detectar
from .eigenfaces import Modelo, distancia_minima, entrenar
from .normalizacion import MASCARA, Normalizada, normalizar

__all__ = ["procesar", "comparar", "ResultadoRostro", "Modelo", "entrenar", "detectar", "alinear",
           "normalizar", "MASCARA", "LADO"]


@dataclass
class ResultadoRostro:
    deteccion: Deteccion
    alineado: Alineado
    normalizada: Normalizada
    pesos: np.ndarray | None = None
    distancia_espacio: float | None = None
    duracion_ms: float = 0.0

    @property
    def hay_rostro(self) -> bool:
        return self.deteccion.rostro is not None

    @property
    def vector(self) -> np.ndarray:
        return self.normalizada.imagen.reshape(-1)


def a_gris(cuadro: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY) if cuadro.ndim == 3 else cuadro


def procesar(cuadro: np.ndarray, modelo: Modelo | None = None, permitir_relleno: bool = True) -> ResultadoRostro:
    t0 = time.perf_counter()
    gris = a_gris(cuadro)
    det = detectar(gris, permitir_relleno)
    ali = alinear(gris, det)
    nor = normalizar(ali.imagen)
    r = ResultadoRostro(det, ali, nor)
    if modelo is not None:
        r.pesos = modelo.proyectar(nor.imagen)
        r.distancia_espacio = modelo.distancia_al_espacio(nor.imagen)
    r.duracion_ms = (time.perf_counter() - t0) * 1000
    return r


def comparar(pesos: np.ndarray, vectores_usuario: np.ndarray, umbral: float) -> tuple[float, bool]:
    """Distancia euclidiana mínima contra los vectores del usuario; acepta si es menor al umbral."""
    d = distancia_minima(pesos, vectores_usuario)
    return d, d < umbral
