"""Fase 2 del rostro, parte 3: normalización fotométrica.

CLAHE (ecualización adaptativa con límite de contraste) y máscara elíptica que quita
fondo, cabello y cuello. Fuera de la máscara el valor es 0.5 (gris neutro), igual que
la maqueta. Devuelve los histogramas de antes y después, dentro de la máscara.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .alineacion import LADO

BINS = 32


def _mascara(lado: int) -> np.ndarray:
    c = (np.arange(lado) - lado / 2 + 0.5) / (lado / 2)
    u, v = np.meshgrid(c, c)
    return (u / 0.8) ** 2 + (v / 0.97) ** 2 <= 1


MASCARA = _mascara(LADO)
# CLAHE suave: en ORL (luz controlada) clip 1.0 y rejilla 2x2 dio EER 10.0 % contra 11.2 %
# con 2.0 y 4x4, y 13 % con ecualización global (13 de noviembre). Se conserva CLAHE porque
# es lo que compensa la luz del salón con la cámara (R8); se revisa en N7 con caras reales.
_CLAHE = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(2, 2))


@dataclass
class Normalizada:
    imagen: np.ndarray          # float32 64 x 64 en 0..1
    hist_antes: np.ndarray      # 32 bins
    hist_despues: np.ndarray


def normalizar(alineada: np.ndarray) -> Normalizada:
    eq = _CLAHE.apply(alineada)
    # Estira dentro de la máscara para que cada cara use todo el rango
    dentro = eq[MASCARA].astype(np.float32)
    lo, hi = np.percentile(dentro, 1), np.percentile(dentro, 99)
    img = np.clip((eq.astype(np.float32) - lo) / ((hi - lo) or 1.0), 0, 1)
    img[~MASCARA] = 0.5
    ha = np.histogram(alineada[MASCARA], bins=BINS, range=(0, 256))[0]
    hd = np.histogram(img[MASCARA], bins=BINS, range=(0, 1))[0]
    return Normalizada(img.astype(np.float32), ha, hd)
