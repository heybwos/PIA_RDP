"""Fase 2 de la huella: de imagen en gris a esqueleto.

Normalización, segmentación por varianza de bloques, campo de orientación por
gradientes (suavizado sobre 2θ), realce con banco de Gabor orientado, binarización y
adelgazamiento. Es el port de processFinger de la maqueta; los comentarios dicen dónde
se aparta.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from skimage.morphology import skeletonize

from .parametros import Perfil

_KERNELS: dict[tuple, list[np.ndarray]] = {}


def _kernels_gabor(p: Perfil) -> list[np.ndarray]:
    clave = (p.gabor_orientaciones, p.gabor_radio, p.gabor_sigma, p.gabor_frecuencia)
    if clave not in _KERNELS:
        r = p.gabor_radio
        j, i = np.mgrid[-r : r + 1, -r : r + 1].astype(np.float32)  # j = fila (y), i = columna (x)
        env = np.exp(-(i * i + j * j) / (2 * p.gabor_sigma**2))
        ks = []
        for b in range(p.gabor_orientaciones):
            phi = b * np.pi / p.gabor_orientaciones
            k = env * np.cos(2 * np.pi * p.gabor_frecuencia * (i * np.cos(phi) + j * np.sin(phi)))
            ks.append((k - k.mean()).astype(np.float32))
        _KERNELS[clave] = ks
    return _KERNELS[clave]


@dataclass
class Preproceso:
    normalizada: np.ndarray    # float32, media 0 y desviación 1
    mascara_bloques: np.ndarray  # uint8 (bh, bw): 1 = huella
    bloques_interiores: np.ndarray  # máscara de bloques erosionada (para minucias)
    mascara: np.ndarray        # uint8 (H, W)
    orientacion_bloques: np.ndarray  # float32 (bh, bw), radianes, dirección del gradiente
    coherencia: np.ndarray     # float32 (bh, bw), 0..1
    orientacion: np.ndarray    # float32 (H, W), por píxel
    gabor: np.ndarray          # float32 (H, W)
    binaria: np.ndarray        # uint8 (H, W): 1 = cresta
    esqueleto: np.ndarray      # uint8 (H, W)


def _mayoria(bm: np.ndarray) -> np.ndarray:
    """Filtro de mayoría 3x3 contando solo vecinos dentro de la rejilla (como la maqueta)."""
    uno = np.ones((3, 3), np.float32)
    c = cv2.filter2D(bm.astype(np.float32), -1, uno, borderType=cv2.BORDER_CONSTANT)
    t = cv2.filter2D(np.ones_like(bm, np.float32), -1, uno, borderType=cv2.BORDER_CONSTANT)
    return (c * 2 > t).astype(np.uint8)


def preprocesar(img: np.ndarray, p: Perfil) -> Preproceso:
    if img.ndim != 2:
        raise ValueError("Se espera una imagen en gris")
    B = p.bloque
    H, W = img.shape
    # Recorta a múltiplo del bloque (FVC2002 no mide 256 x 288)
    H, W = H - H % B, W - W % B
    img = img[:H, :W]
    bh, bw = H // B, W // B

    if p.ecualizar:
        img = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
    f = img.astype(np.float32) / 255.0
    sd = float(f.std()) or 1.0
    norm = (f - f.mean()) / sd

    # Segmentación por varianza de bloques
    bloques = f.reshape(bh, B, bw, B)
    bm = (bloques.var(axis=(1, 3)) > p.umbral_varianza).astype(np.uint8)
    for _ in range(p.pasadas_mayoria):
        bm = _mayoria(bm)
    interior = np.zeros_like(bm)
    interior[1:-1, 1:-1] = (
        bm[1:-1, 1:-1] & bm[1:-1, :-2] & bm[1:-1, 2:] & bm[:-2, 1:-1] & bm[2:, 1:-1]
    )
    mascara = np.kron(bm, np.ones((B, B), np.uint8))

    # Gradientes de Sobel (sin borde, como la maqueta)
    gx = cv2.Sobel(norm, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(norm, cv2.CV_32F, 0, 1, ksize=3)
    for g in (gx, gy):
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 0

    # Campo de orientación por bloque, ventana de B + 8 px, con imágenes integrales
    def integral(a: np.ndarray) -> np.ndarray:
        return cv2.integral(a.astype(np.float64))

    Ia, Ib, Ie = integral(gx * gx - gy * gy), integral(2 * gx * gy), integral(gx * gx + gy * gy)
    vx = np.zeros((bh, bw), np.float32)
    vy = np.zeros((bh, bw), np.float32)
    for by in range(bh):
        y0, y1 = max(1, by * B - 4), min(H - 1, by * B + B + 4)
        for bx in range(bw):
            x0, x1 = max(1, bx * B - 4), min(W - 1, bx * B + B + 4)
            s = lambda I: I[y1, x1] - I[y0, x1] - I[y1, x0] + I[y0, x0]  # noqa: E731
            e = s(Ie) or 1.0
            vx[by, bx] = s(Ia) / e
            vy[by, bx] = s(Ib) / e

    # Suavizado [1 2 1] sobre 2θ, normalizado por los pesos dentro de la rejilla
    k = np.outer([1, 2, 1], [1, 2, 1]).astype(np.float32)
    peso = cv2.filter2D(np.ones_like(vx), -1, k, borderType=cv2.BORDER_CONSTANT)
    sx = cv2.filter2D(vx, -1, k, borderType=cv2.BORDER_CONSTANT) / peso
    sy = cv2.filter2D(vy, -1, k, borderType=cv2.BORDER_CONSTANT) / peso
    coherencia = np.hypot(sx, sy).astype(np.float32)
    orient_bloques = (0.5 * np.arctan2(sy, sx)).astype(np.float32)

    # Orientación por píxel: interpolación bilineal del campo 2θ
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fx = np.clip((xx - B / 2) / B, 0, bw - 1)
    fy = np.clip((yy - B / 2) / B, 0, bh - 1)
    x0 = np.minimum(bw - 2, fx.astype(int))
    y0 = np.minimum(bh - 2, fy.astype(int))
    fx -= x0
    fy -= y0

    def bilineal(c: np.ndarray) -> np.ndarray:
        return (
            c[y0, x0] * (1 - fx) * (1 - fy)
            + c[y0, x0 + 1] * fx * (1 - fy)
            + c[y0 + 1, x0] * (1 - fx) * fy
            + c[y0 + 1, x0 + 1] * fx * fy
        )

    orientacion = (0.5 * np.arctan2(bilineal(sy), bilineal(sx))).astype(np.float32)

    # Banco de Gabor: se filtra con cada orientación y cada píxel toma la suya
    ks = _kernels_gabor(p)
    nb = len(ks)
    idx = np.round(np.mod(orientacion, np.pi) / np.pi * nb).astype(int) % nb
    gabor = np.zeros((H, W), np.float32)
    for b, kb in enumerate(ks):
        sel = idx == b
        if sel.any():
            gabor[sel] = cv2.filter2D(norm, cv2.CV_32F, kb, borderType=cv2.BORDER_CONSTANT)[sel]
    r = p.gabor_radio
    borde = np.zeros((H, W), bool)
    borde[r : H - r, r : W - r] = True
    gabor[~(borde & (mascara > 0))] = 0

    binaria = ((mascara > 0) & (gabor < 0)).astype(np.uint8)
    # Aparte de la maqueta: skimage en lugar de su Zhang-Suen propio
    esqueleto = skeletonize(binaria.astype(bool)).astype(np.uint8)

    return Preproceso(norm, bm, interior, mascara, orient_bloques, coherencia, orientacion,
                      gabor, binaria, esqueleto)
