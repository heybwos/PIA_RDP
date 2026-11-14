"""Dispositivo simulado: teclas del escenario, huella del banco por partes, caja virtual.

La huella llega por bloques de filas al ritmo que tendría por el AS608 a 57600 baudios
(unos 5,760 bytes por segundo con 4 bits por píxel), rotulada como simulada.
`velocidad` = 1 es tiempo real; 0 no espera (pruebas).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from ..huella import leer
from .base import Dispositivo, Emisor, imagen_json

BYTES_POR_SEGUNDO = 5760
FILAS_POR_BLOQUE = 16


class DispositivoSimulado(Dispositivo):
    nombre = "simulado"
    simulado = True

    def __init__(self, id_: str, pin: str, archivo_huella: str | Path, fuente_huella: str,
                 emitir: Emisor | None = None, velocidad: float = 1.0, ms_entre_servos: int = 300,
                 ms_abierto: int = 8000):
        super().__init__(emitir)
        self.id, self.pin = id_, pin
        self.archivo_huella, self.fuente_huella = Path(archivo_huella), fuente_huella
        self.velocidad = velocidad
        self.ms_entre_servos, self.ms_abierto = ms_entre_servos, ms_abierto

    async def _esperar(self, s: float) -> None:
        if self.velocidad > 0:
            await asyncio.sleep(s * self.velocidad)

    async def leer_pin(self) -> tuple[str, str]:
        await self.mostrar("Teclea tu ID", "y #")
        id_ = pin = ""
        for c in self.id + "#":
            await self._esperar(0.25)
            await self.emitir("tecla", {"c": c})
            if c != "#":
                id_ += c
            await self.emitir("casillas", {"id": id_, "pin": "", "fase": "id"})
        await self.mostrar(f"ID {self.id}", "PIN y #")
        for c in self.pin + "#":
            await self._esperar(0.25)
            await self.emitir("tecla", {"c": c})
            if c != "#":
                pin += c
            await self.emitir("casillas", {"id": id_, "pin": "*" * len(pin), "fase": "pin"})
        await self.emitir("serie", {"dir": "in", "linea": f"PIN:{id_}:{'*' * len(pin)}"})
        return id_, pin

    async def capturar_huella(self) -> tuple[np.ndarray, str]:
        await self.emitir("serie", {"dir": "out", "linea": "PEDIR_HUELLA"})
        await self.mostrar("Pon tu dedo", "en el sensor")
        await self.emitir("serie", {"dir": "in", "linea": "HUELLA:ESPERA"})
        await self._esperar(0.8)
        img = leer(self.archivo_huella)
        h, w = img.shape
        await self.emitir("serie", {"dir": "in", "linea": "HUELLA:DEDO"})
        await self.emitir("huella_inicio", {"ancho": w, "alto": h, "fuente": self.fuente_huella, "simulada": True})
        n_bytes = h * w // 2
        await self.emitir("serie", {"dir": "in", "linea": f"IMG:{n_bytes}"})
        bloques = range(0, h, FILAS_POR_BLOQUE)
        pausa = n_bytes / BYTES_POR_SEGUNDO / len(bloques)
        for y0 in bloques:
            await self._esperar(pausa)
            await self.emitir("huella_filas", {"y0": y0, "filas": imagen_json(img[y0 : y0 + FILAS_POR_BLOQUE])})
        await self.emitir("serie", {"dir": "in", "linea": "IMG:FIN:(simulada)"})
        await self.emitir("huella_fin", {"bytes": n_bytes, "crc_ok": True,
                                         "ms": int(n_bytes / BYTES_POR_SEGUNDO * 1000)})
        return img, self.fuente_huella

    async def mostrar(self, l1: str, l2: str = "") -> None:
        await self.emitir("oled", {"l1": l1, "l2": l2})
        await self.emitir("serie", {"dir": "out", "linea": f"MSG:{l1}|{l2}"})

    async def actuar(self, nivel: int) -> None:
        await self.emitir("serie", {"dir": "out", "linea": f"ACCESO:{nivel}"})
        if nivel == 0:
            await self.emitir("leds", {"verde": False, "rojo": True})
            return
        await self.emitir("leds", {"verde": True, "rojo": False})
        for n in range(1, nivel + 1):  # uno a la vez
            await self.emitir("servo", {"n": n, "abierto": True})
            await self._esperar(self.ms_entre_servos / 1000)
