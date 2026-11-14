"""Fase 2 del rostro, parte 2: alineación geométrica a 64 x 64.

Con dos ojos: rota para dejarlos horizontales, escala a una distancia fija entre ellos y
los coloca en posiciones fijas. Sin ojos: respaldo documentado, recorte centrado del
rectángulo del rostro con proporciones fijas, marcado como "respaldo".
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .deteccion import Deteccion, Rect

LADO = 64
OJO_Y = 0.40          # altura de los ojos en la cara alineada (fracción del lado)
OJO_X = (0.33, 0.67)  # posición horizontal de cada ojo (medido en ORL: mejor que 0.36 / 0.30-0.70)
# Respaldo: el rectángulo de Haar va de la frente a la barbilla; se toma su parte central
RESPALDO_MARGEN_X = 0.10
RESPALDO_MARGEN_ARRIBA = 0.06


@dataclass
class Alineado:
    imagen: np.ndarray            # uint8 64 x 64
    metodo: str                   # "ojos", "respaldo" o "sin_rostro"
    angulo_grados: float = 0.0
    matriz: np.ndarray | None = None  # transformación afín cuadro -> 64 x 64


def _centro(r: Rect) -> tuple[float, float]:
    return r[0] + r[2] / 2, r[1] + r[3] / 2


def alinear(gris: np.ndarray, det: Deteccion) -> Alineado:
    if det.rostro is None:
        # Sin rostro (solo para datasets ya recortados): toda la imagen, rotulado
        h, w = gris.shape
        lado = min(h, w)
        y0, x0 = (h - lado) // 2, (w - lado) // 2
        return Alineado(cv2.resize(gris[y0 : y0 + lado, x0 : x0 + lado], (LADO, LADO),
                                   interpolation=cv2.INTER_AREA), "sin_rostro")

    if len(det.ojos) == 2:
        (xi, yi), (xd, yd) = _centro(det.ojos[0]), _centro(det.ojos[1])
        dist = float(np.hypot(xd - xi, yd - yi))
        x, y, w, h = det.rostro
        if 0.25 * w < dist < 0.65 * w:  # descarta pares absurdos (ceja con ojo, ojo con nariz)
            ang = float(np.degrees(np.arctan2(yd - yi, xd - xi)))
            escala = (OJO_X[1] - OJO_X[0]) * LADO / dist
            medio = ((xi + xd) / 2, (yi + yd) / 2)
            M = cv2.getRotationMatrix2D(medio, ang, escala)
            M[0, 2] += LADO * (OJO_X[0] + OJO_X[1]) / 2 - medio[0]
            M[1, 2] += LADO * OJO_Y - medio[1]
            img = cv2.warpAffine(gris, M, (LADO, LADO), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
            return Alineado(img, "ojos", ang, M)

    x, y, w, h = det.rostro
    x0 = x + w * RESPALDO_MARGEN_X
    y0 = y + h * RESPALDO_MARGEN_ARRIBA
    lado = w * (1 - 2 * RESPALDO_MARGEN_X)
    escala = LADO / lado
    M = np.array([[escala, 0, -x0 * escala], [0, escala, -y0 * escala]], np.float64)
    img = cv2.warpAffine(gris, M, (LADO, LADO), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    return Alineado(img, "respaldo", 0.0, M)
