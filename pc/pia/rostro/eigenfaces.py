"""Fases 3 y 4 del rostro: Eigenfaces con NumPy (sin scikit-learn).

Entrenamiento:
  1. Cada cara normalizada (64 x 64) es un vector x de d = 4096 valores.
  2. Cara media μ; matriz centrada A (n x d) con una cara por fila.
  3. Truco de la matriz pequeña: en lugar de la covarianza d x d (4096 x 4096) se
     resuelve A·Aᵀ (n x n). Si A·Aᵀ v = λ v, entonces Aᵀv es eigenvector de Aᵀ·A con el
     mismo λ. Se normaliza cada Aᵀv a norma 1: esas son las eigenfaces.
  4. k = el menor número de componentes cuya varianza acumulada llega a la meta (95 %).
Proyección: w = U (x − μ), el vector de pesos.
Reconstrucción: x̂ = μ + Σ wᵢ uᵢ con 1…k componentes.
Distancia al espacio de caras: ‖x − x̂‖ (alta si la imagen no es una cara).
Matching: distancia euclidiana entre vectores de pesos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Modelo:
    media: np.ndarray        # (d,)
    eigenfaces: np.ndarray   # (k, d), filas ortonormales
    valores: np.ndarray      # (k,) varianza de cada componente
    varianza_explicada: float
    lado: int = 64

    @property
    def k(self) -> int:
        return len(self.valores)

    def proyectar(self, x: np.ndarray) -> np.ndarray:
        """Una cara (lado x lado o vector) o varias (n x d) -> pesos."""
        x = np.asarray(x, np.float64)
        x = x.reshape(-1) if x.ndim == 2 and x.shape == (self.lado, self.lado) else x
        return (x - self.media) @ self.eigenfaces.T

    def reconstruir(self, pesos: np.ndarray, componentes: int | None = None) -> np.ndarray:
        c = self.k if componentes is None else componentes
        return self.media + pesos[..., :c] @ self.eigenfaces[:c]

    def distancia_al_espacio(self, x: np.ndarray) -> float:
        v = np.asarray(x, np.float64).reshape(-1)
        return float(np.linalg.norm(v - self.reconstruir(self.proyectar(v))))

    def guardar(self, ruta: str | Path) -> None:
        np.savez_compressed(ruta, media=self.media, eigenfaces=self.eigenfaces, valores=self.valores,
                            varianza_explicada=self.varianza_explicada, lado=self.lado)

    @classmethod
    def cargar(cls, ruta: str | Path) -> "Modelo":
        z = np.load(ruta)
        return cls(z["media"], z["eigenfaces"], z["valores"], float(z["varianza_explicada"]), int(z["lado"]))


def entrenar(caras: np.ndarray, meta_varianza: float = 0.95, k_max: int | None = None) -> Modelo:
    """caras: (n, lado, lado) o (n, d)."""
    caras = np.asarray(caras, np.float64)
    lado = caras.shape[1] if caras.ndim == 3 else int(np.sqrt(caras.shape[1]))
    X = caras.reshape(len(caras), -1)
    n = len(X)
    if n < 2:
        raise ValueError("Hacen falta al menos 2 caras para entrenar")
    media = X.mean(axis=0)
    A = X - media
    L = A @ A.T / (n - 1)                     # n x n en lugar de d x d
    vals, vecs = np.linalg.eigh(L)            # ascendente
    orden = np.argsort(vals)[::-1]
    vals, vecs = vals[orden], vecs[:, orden]
    utiles = vals > vals[0] * 1e-10           # el último es ~0 por el centrado
    vals, vecs = vals[utiles], vecs[:, utiles]
    U = (A.T @ vecs).T                        # (r, d): Aᵀv
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    acumulada = np.cumsum(vals) / vals.sum()
    k = int(np.searchsorted(acumulada, meta_varianza) + 1)
    if k_max:
        k = min(k, k_max)
    k = min(k, len(vals))
    return Modelo(media, U[:k], vals[:k], float(acumulada[k - 1]), lado)


def distancia_minima(pesos: np.ndarray, vectores: np.ndarray) -> float:
    """Distancia euclidiana mínima entre un vector de pesos y los del usuario."""
    vectores = np.atleast_2d(vectores)
    return float(np.linalg.norm(vectores - pesos, axis=1).min())
