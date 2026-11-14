"""Lectura de imágenes de huella en el formato del AS608 (4 bits por píxel)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

ANCHO, ALTO = 256, 288
BYTES_AS608 = ANCHO * ALTO // 2


def desempacar(datos: bytes, nibble_alto_primero: bool = True, ancho: int = ANCHO) -> np.ndarray:
    """Bytes de 4 bits por píxel -> imagen uint8 en 0..255."""
    a = np.frombuffer(datos, dtype=np.uint8)
    hi, lo = a >> 4, a & 0x0F
    px = np.stack((hi, lo) if nibble_alto_primero else (lo, hi), axis=1).reshape(-1)
    filas = len(px) // ancho
    return (px[: filas * ancho].reshape(filas, ancho) * 17).astype(np.uint8)


def leer(ruta: str | Path, nibble_alto_primero: bool = True) -> np.ndarray:
    """Lee .bin del AS608 o cualquier imagen que abra OpenCV (en gris)."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".bin":
        return desempacar(ruta.read_bytes(), nibble_alto_primero)
    import cv2

    img = cv2.imdecode(np.fromfile(str(ruta), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"No se pudo leer {ruta}")
    return img
