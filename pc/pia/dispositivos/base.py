"""Interfaz común del ESP32 real (esp32.py, N6) y del simulado (simulado.py).

El orquestador solo habla con esta interfaz. Cada dispositivo emite por `emitir` los
eventos de su lado (teclas, OLED, LEDs, servos, líneas del protocolo serie).
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

import numpy as np

Emisor = Callable[[str, dict[str, Any]], Awaitable[None]]


async def _nada(tipo: str, datos: dict[str, Any]) -> None:
    return None


def imagen_json(a: np.ndarray) -> dict[str, Any]:
    """Imagen -> {ancho, alto, tipo, datos base64} (docs/EVENTOS.md)."""
    a = np.ascontiguousarray(a)
    if a.dtype == np.uint8:
        tipo = "u8"
    else:
        a, tipo = a.astype("<f4"), "f32"
    return {"ancho": int(a.shape[1]), "alto": int(a.shape[0]), "tipo": tipo,
            "datos": base64.b64encode(a.tobytes()).decode("ascii")}


class CapturaCancelada(Exception):
    pass


class Dispositivo(ABC):
    nombre = "base"
    simulado = True

    def __init__(self, emitir: Emisor | None = None):
        self.emitir: Emisor = emitir or _nada

    @abstractmethod
    async def leer_pin(self) -> tuple[str, str]:
        """Espera ID (2 dígitos) y PIN (4 dígitos); emite tecla y casillas."""

    @abstractmethod
    async def capturar_huella(self) -> tuple[np.ndarray, str]:
        """Devuelve (imagen uint8, fuente). Emite huella_inicio, huella_filas y huella_fin."""

    @abstractmethod
    async def mostrar(self, l1: str, l2: str = "") -> None:
        """Texto en la OLED (sin acentos)."""

    @abstractmethod
    async def actuar(self, nivel: int) -> None:
        """0: LED rojo. 1: LED verde y servo 1. 2: LED verde y servos 1 y 2."""

    async def reiniciar(self) -> None:
        await self.mostrar("Listo", "Teclea tu ID")
