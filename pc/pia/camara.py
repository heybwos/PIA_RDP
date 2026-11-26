"""Fuentes de rostro detrás de una sola interfaz: archivo de dataset, URL (DroidCam) e índice.

Para la URL se intenta primero cv2.VideoCapture; si no abre, un lector MJPEG propio.
Si la cámara no responde se lanza CamaraError con qué revisar. Nunca se devuelve una
imagen de relleno.
"""

from __future__ import annotations

import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np


class CamaraError(RuntimeError):
    def __init__(self, mensaje: str, que_revisar: str):
        super().__init__(mensaje)
        self.que_revisar = que_revisar


ROTACIONES = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def rotar(img: np.ndarray, grados: int) -> np.ndarray:
    """Gira en sentido horario. Con el celular en vertical, DroidCam suele mandar el cuadro de lado."""
    r = ROTACIONES.get(int(grados) % 360)
    return img if r is None else cv2.rotate(img, r)


class Camara:
    fuente = "camara"
    rotacion = 0

    def capturar(self) -> np.ndarray:
        return rotar(self._capturar(), self.rotacion)

    def _capturar(self) -> np.ndarray:
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


def _ocupado(url: str) -> bool:
    """DroidCam responde una página HTML "DroidCam is Busy" cuando ya tiene un cliente."""
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            if "text/html" in r.headers.get("Content-Type", ""):
                return b"Busy" in r.read(4096)
    except Exception:  # noqa: BLE001
        pass
    return False


class CamaraURL(Camara):
    """DroidCam: http://<IP>:4747/video. Se queda con el cuadro más reciente."""

    def __init__(self, url: str):
        self.url = url
        self.cap: cv2.VideoCapture | None = None

    def _capturar(self) -> np.ndarray:
        if self.cap is None:
            cap = cv2.VideoCapture(self.url)
            self.cap = cap if cap.isOpened() else False  # False = usar el lector propio
        if self.cap:
            for _ in range(3):  # descarta cuadros viejos del búfer
                self.cap.grab()
            ok, img = self.cap.retrieve()
            if ok and img is not None:
                return img
            # DroidCam acepta un solo cliente: se suelta antes de probar el lector propio
            self.cap.release()
            self.cap = False
        try:
            return _leer_mjpeg(self.url)
        except Exception as e:  # noqa: BLE001
            ocupado = _ocupado(self.url)
            raise CamaraError(f"La cámara no responde en {self.url}: {'DroidCam está ocupado' if ocupado else e}",
                              "DroidCam acepta un solo cliente: cierra la pestaña del navegador o el cliente de "
                              "PC que lo esté usando, o reinicia la app en el celular." if ocupado else
                              "Abre IP Webcam (o DroidCam) en el celular, misma red WiFi, y revisa la IP y el puerto "
                              "en config.toml ([camara].url y url_respaldo). Prueba la URL en el navegador.") from e

    def cerrar(self) -> None:
        if self.cap:
            self.cap.release()


class CamaraIndice(Camara):
    def __init__(self, indice: int):
        self.cap = cv2.VideoCapture(indice)

    def _capturar(self) -> np.ndarray:
        ok, img = self.cap.read() if self.cap.isOpened() else (False, None)
        if not ok:
            raise CamaraError("La cámara por índice no entrega cuadros",
                              "Revisa [camara].indice en config.toml o conecta DroidCam por USB.")
        return img

    def cerrar(self) -> None:
        self.cap.release()


def _responde(url: str, limite_s: float = 1.5) -> bool:
    """¿Hay algo escuchando en el host y puerto de la URL? Solo abre y cierra un socket TCP:
    no baja video ni ocupa el único cliente que acepta DroidCam."""
    p = urllib.parse.urlsplit(url)
    if not p.hostname:
        return False
    try:
        with socket.create_connection((p.hostname, p.port or (443 if p.scheme == "https" else 80)), timeout=limite_s):
            return True
    except OSError:
        return False


def elegir_url(cfg) -> str:
    """[camara].url es la principal (WiFi de la facultad) y url_respaldo la del hotspot del celular.
    Se usa la primera que contesta; si ninguna contesta, la principal, y su error dice qué revisar."""
    urls = [u for u in (cfg.valor("camara.url", ""), cfg.valor("camara.url_respaldo", "")) if u]
    for i, u in enumerate(urls):
        if _responde(u):
            if i:
                print(f"Cámara: la URL principal no contesta; se usa la de respaldo {u}", flush=True)
            return u
    return urls[0] if urls else ""


def desde_config(cfg) -> Camara:
    fuente = cfg.valor("camara.fuente", "url")
    if fuente == "archivo":  # pruebas: una imagen fija de un dataset
        return CamaraArchivo(cfg.valor("camara.archivo"), cfg.valor("camara.fuente_archivo", "orl"))
    cam = CamaraIndice(int(cfg.valor("camara.indice", 0))) if fuente == "indice" else CamaraURL(elegir_url(cfg))
    cam.rotacion = int(cfg.valor("camara.rotacion", 0))
    return cam
