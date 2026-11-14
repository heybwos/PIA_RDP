"""Fuentes de rostro detrás de una sola interfaz: archivo de dataset, URL (DroidCam) e índice.

Para la URL se intenta primero cv2.VideoCapture; si no abre, un lector MJPEG propio.
Si la cámara no responde se lanza CamaraError con qué revisar. Nunca se devuelve una
imagen de relleno.
"""

from __future__ import annotations

import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np


class CamaraError(RuntimeError):
    def __init__(self, mensaje: str, que_revisar: str):
        super().__init__(mensaje)
        self.que_revisar = que_revisar


class Camara:
    fuente = "camara"

    def capturar(self) -> np.ndarray:
        raise NotImplementedError

    def cerrar(self) -> None:
        pass


class CamaraArchivo(Camara):
    """Una imagen de un dataset (ORL u otro). Fuente: orl, sintetico..."""

    def __init__(self, ruta: str | Path, fuente: str = "orl"):
        self.ruta, self.fuente = Path(ruta), fuente

    def capturar(self) -> np.ndarray:
        img = cv2.imdecode(np.fromfile(str(self.ruta), np.uint8), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise CamaraError(f"No se pudo leer {self.ruta}", "¿Está el dataset en datos/datasets/?")
        return img


def _leer_mjpeg(url: str, limite_s: float = 5.0) -> np.ndarray:
    """Lee un cuadro de un flujo multipart/x-mixed-replace buscando los marcadores JPEG."""
    fin = time.monotonic() + limite_s
    with urllib.request.urlopen(url, timeout=limite_s) as r:
        buf = b""
        while time.monotonic() < fin:
            trozo = r.read(16384)
            if not trozo:
                break
            buf += trozo
            a = buf.find(b"\xff\xd8")
            b = buf.find(b"\xff\xd9", a + 2)
            if a >= 0 and b > a:
                img = cv2.imdecode(np.frombuffer(buf[a : b + 2], np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    return img
                buf = buf[b + 2 :]
    raise TimeoutError("sin cuadro JPEG completo")


class CamaraURL(Camara):
    """DroidCam: http://<IP>:4747/video. Se queda con el cuadro más reciente."""

    def __init__(self, url: str):
        self.url = url
        self.cap: cv2.VideoCapture | None = None

    def capturar(self) -> np.ndarray:
        if self.cap is None:
            cap = cv2.VideoCapture(self.url)
            self.cap = cap if cap.isOpened() else False  # False = usar el lector propio
        if self.cap:
            for _ in range(3):  # descarta cuadros viejos del búfer
                self.cap.grab()
            ok, img = self.cap.retrieve()
            if ok and img is not None:
                return img
        try:
            return _leer_mjpeg(self.url)
        except Exception as e:  # noqa: BLE001
            raise CamaraError(f"La cámara no responde en {self.url}: {e}",
                              "Abre DroidCam en el celular, misma red WiFi, y revisa la IP y el puerto "
                              "en config.toml ([camara].url). Prueba la URL en el navegador.") from e

    def cerrar(self) -> None:
        if self.cap:
            self.cap.release()


class CamaraIndice(Camara):
    def __init__(self, indice: int):
        self.cap = cv2.VideoCapture(indice)

    def capturar(self) -> np.ndarray:
        ok, img = self.cap.read() if self.cap.isOpened() else (False, None)
        if not ok:
            raise CamaraError("La cámara por índice no entrega cuadros",
                              "Revisa [camara].indice en config.toml o conecta DroidCam por USB.")
        return img

    def cerrar(self) -> None:
        self.cap.release()


def desde_config(cfg) -> Camara:
    fuente = cfg.valor("camara.fuente", "url")
    if fuente == "archivo":  # pruebas: una imagen fija de un dataset
        return CamaraArchivo(cfg.valor("camara.archivo"), cfg.valor("camara.fuente_archivo", "orl"))
    if fuente == "indice":
        return CamaraIndice(int(cfg.valor("camara.indice", 0)))
    return CamaraURL(cfg.valor("camara.url"))
