"""Ventana de captura de rostro con vista previa (registro y segunda tanda de calibración).

Muestra la cámara en vivo con los rectángulos de Viola-Jones. Al presionar Espacio toma
`n` cuadros que tengan rostro y los dos ojos, separados `intervalo` segundos (para que la
persona gire un poco la cabeza entre uno y otro). Q o Esc cancela.
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from . import rostro
from .camara import Camara


def capturar_cuadros(cam: Camara, n: int, titulo: str = "PIA - registro de rostro",
                     intervalo: float = 0.4, limite_s: float = 40.0) -> list[np.ndarray]:
    cv2.namedWindow(titulo, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(titulo, cv2.WND_PROP_TOPMOST, 1)
    tomados: list[np.ndarray] = []
    capturando, ultimo, inicio = False, 0.0, 0.0
    try:
        while True:
            cuadro = cam.capturar()
            r = rostro.procesar(cuadro, permitir_relleno=False)
            ok = r.hay_rostro and len(r.deteccion.ojos) == 2
            if capturando and ok and time.monotonic() - ultimo >= intervalo:
                tomados.append(cuadro.copy())
                ultimo = time.monotonic()
                if len(tomados) >= n:
                    return tomados
            if capturando and time.monotonic() - inicio > limite_s:
                return tomados  # se devuelve lo que haya; quien llama decide si alcanza
            img = cuadro.copy()
            if r.deteccion.rostro:
                x, y, w, h = r.deteccion.rostro
                cv2.rectangle(img, (x, y), (x + w, y + h), (92, 207, 143) if ok else (48, 146, 255), 3)
            for x, y, w, h in r.deteccion.ojos:
                cv2.rectangle(img, (x, y), (x + w, y + h), (48, 146, 255), 2)
            if capturando:
                texto = f"Capturando {len(tomados)}/{n}: gira un poco la cabeza"
            else:
                texto = "Listo: Espacio para capturar" if ok else "Acomodate: rostro y dos ojos"
            cv2.rectangle(img, (0, 0), (img.shape[1], 44), (20, 20, 20), -1)
            cv2.putText(img, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (92, 207, 143) if ok else (80, 160, 255), 2, cv2.LINE_AA)
            esc = min(1.0, 900 / img.shape[0])
            cv2.imshow(titulo, cv2.resize(img, None, fx=esc, fy=esc) if esc < 1 else img)
            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord("q"), ord("Q")) or cv2.getWindowProperty(titulo, cv2.WND_PROP_VISIBLE) < 1:
                return []
            if k == ord(" ") and not capturando:
                capturando, inicio = True, time.monotonic()
    finally:
        cv2.destroyWindow(titulo)
