"""Fase 2 del rostro, parte 1: detección con Viola-Jones (cascadas de Haar de OpenCV).

Devuelve los rectángulos reales que entrega OpenCV, en coordenadas del cuadro original.
OpenCV no expone la ventana deslizante ni las etapas de la cascada: no se simulan.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

Rect = tuple[int, int, int, int]  # x, y, ancho, alto


@dataclass
class Deteccion:
    rostro: Rect | None
    ojos: list[Rect] = field(default_factory=list)  # 0, 1 o 2; si son 2: [izquierdo, derecho] de la imagen
    con_relleno: bool = False   # True si hizo falta agregar borde (caras ya recortadas, como ORL)
    candidatos: int = 0         # rostros que encontró la cascada antes de quedarse con el mayor


_CASCADAS: dict[str, cv2.CascadeClassifier] = {}


def _cascada(nombre: str) -> cv2.CascadeClassifier:
    if nombre not in _CASCADAS:
        c = cv2.CascadeClassifier(cv2.data.haarcascades + nombre)
        if c.empty():
            raise RuntimeError(f"OpenCV no trae {nombre}; revisa la versión (se fija opencv-python<5)")
        _CASCADAS[nombre] = c
    return _CASCADAS[nombre]


def _rostros(gris: np.ndarray) -> list[Rect]:
    lado = min(gris.shape)
    r = _cascada("haarcascade_frontalface_default.xml").detectMultiScale(
        gris, scaleFactor=1.1, minNeighbors=5, minSize=(max(24, lado // 5),) * 2
    )
    return [tuple(int(v) for v in x) for x in r]


def _ojos(gris: np.ndarray, rostro: Rect) -> list[Rect]:
    x, y, w, h = rostro
    roi = gris[max(0, y) : y + h * 11 // 20, max(0, x) : x + w]  # mitad superior del rostro, un poco más
    # La cascada de ojos falla con ojos de ~10 px: se lleva el rostro a ~200 px de ancho
    f = max(1.0, 200 / w)
    if f > 1:
        roi = cv2.resize(roi, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    ws = int(w * f)
    encontrados = _cascada("haarcascade_eye.xml").detectMultiScale(
        roi, scaleFactor=1.1, minNeighbors=4, minSize=(max(8, ws // 8),) * 2, maxSize=(ws // 2,) * 2
    )
    ox, oy = max(0, x), max(0, y)
    ojos = [(int(a / f) + ox, int(b / f) + oy, int(c / f), int(d / f)) for a, b, c, d in encontrados]
    centro = x + w / 2
    izq = [o for o in ojos if o[0] + o[2] / 2 < centro]
    der = [o for o in ojos if o[0] + o[2] / 2 >= centro]
    if izq and der:
        # Uno de cada lado; si hay varios, el de mayor área (las cejas suelen salir más chicas)
        return [max(izq, key=lambda o: o[2] * o[3]), max(der, key=lambda o: o[2] * o[3])]
    return ojos[:1]


def detectar(gris: np.ndarray, permitir_relleno: bool = True) -> Deteccion:
    """Busca el rostro mayor y sus ojos. Si no hay rostro y se permite, reintenta con borde
    replicado y la imagen al doble (las caras de ORL vienen recortadas al ras)."""
    caras = _rostros(gris)
    if caras:
        r = max(caras, key=lambda c: c[2] * c[3])
        return Deteccion(r, _ojos(gris, r), False, len(caras))
    if not permitir_relleno:
        return Deteccion(None)
    h, w = gris.shape
    p = max(h, w) // 3
    grande = cv2.resize(cv2.copyMakeBorder(gris, p, p, p, p, cv2.BORDER_REPLICATE), None, fx=2, fy=2)
    caras = _rostros(grande)
    if not caras:
        return Deteccion(None, con_relleno=True)
    a = lambda r: (r[0] // 2 - p, r[1] // 2 - p, r[2] // 2, r[3] // 2)  # noqa: E731  a coordenadas originales
    r = max(caras, key=lambda c: c[2] * c[3])
    ojos = [a(o) for o in _ojos(grande, r)]
    return Deteccion(a(r), ojos, True, len(caras))
