"""Lee config.toml (raíz del repo). Si no existe, lo copia de config.ejemplo.toml."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]


class Config(dict):
    """dict con acceso por punto: cfg["huella"]["nibble_alto_primero"] o cfg.get_ruta("datos.carpeta")."""

    def valor(self, ruta: str, defecto: Any = None) -> Any:
        nodo: Any = self
        for parte in ruta.split("."):
            if not isinstance(nodo, dict) or parte not in nodo:
                return defecto
            nodo = nodo[parte]
        return nodo

    @property
    def carpeta_datos(self) -> Path:
        c = Path(self.valor("datos.carpeta", "datos"))
        return c if c.is_absolute() else RAIZ / c


def cargar(ruta: str | Path | None = None, **sobrescribir: Any) -> Config:
    ruta = Path(ruta) if ruta else RAIZ / "config.toml"
    if not ruta.exists():
        ejemplo = RAIZ / "config.ejemplo.toml"
        if ruta == RAIZ / "config.toml" and ejemplo.exists():
            shutil.copyfile(ejemplo, ruta)
        else:
            ruta = ejemplo
    with open(ruta, "rb") as f:
        cfg = Config(tomllib.load(f))
    for clave, valor in sobrescribir.items():  # carpeta_datos="..." en pruebas
        seccion, _, nombre = clave.partition("__")
        cfg.setdefault(seccion, {})[nombre] = valor
    return cfg
