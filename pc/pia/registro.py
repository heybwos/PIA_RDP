"""Alta de usuarios (sección 4.4 del roadmap) y reentrenamiento de Eigenfaces.

1. Valida el ID y guarda el usuario con el PIN en hash.
2. Cada huella: guarda el crudo, procesa y guarda la plantilla. Calidad baja no cuenta.
3. Cada cuadro de rostro: guarda el crudo, detecta, alinea y normaliza. Sin rostro no cuenta.
4. Reentrena el modelo del dominio afectado (con un fondo de caras del dataset), vuelve a
   proyectar a todos los usuarios de ese dominio y activa el modelo nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import huella, rostro
from .almacen import Almacen, dominio_rostro

MIN_MINUCIAS = 10
MIN_CALIDAD = 0.05


@dataclass
class Informe:
    huellas_ok: int = 0
    huellas_rechazadas: list[str] = field(default_factory=list)
    rostros_ok: int = 0
    rostros_rechazados: int = 0
    modelos: dict[str, int] = field(default_factory=dict)


def agregar_huella(alm: Almacen, id_: str, img: np.ndarray, fuente: str, perfil: str) -> tuple[bool, str]:
    r = huella.procesar(img, perfil)
    if len(r.minucias) < MIN_MINUCIAS or r.calidad < MIN_CALIDAD:
        return False, f"calidad baja ({len(r.minucias)} minucias, calidad {r.calidad:.2f}); repite la captura"
    alm.agregar_huella(id_, img, fuente, r, perfil)
    return True, f"{len(r.minucias)} minucias"


def agregar_rostro(alm: Almacen, id_: str, cuadro: np.ndarray, fuente: str) -> bool:
    r = rostro.procesar(cuadro, permitir_relleno=fuente != "camara")
    if not r.hay_rostro:
        return False
    alm.agregar_rostro(id_, cuadro, fuente, r)
    return True


def caras_de_fondo(carpeta_orl: Path, excluir: set[int], personas: int = 20, por_persona: int = 6) -> list[np.ndarray]:
    """Caras del dataset que no son usuarios, para que el subespacio no salga diminuto."""
    if not carpeta_orl.exists():
        return []
    import cv2

    caras = []
    ids = [i for i in range(1, 41) if i not in excluir][:personas]
    for i in ids:
        for j in range(1, por_persona + 1):
            f = carpeta_orl / f"s{i}" / f"{j}.pgm"
            if f.exists():
                r = rostro.procesar(cv2.imread(str(f), cv2.IMREAD_GRAYSCALE))
                if r.hay_rostro:
                    caras.append(r.normalizada.imagen)
    return caras


def reentrenar(alm: Almacen, dominio: str, fondo: list[np.ndarray] | None = None,
               meta_varianza: float = 0.95) -> int | None:
    muestras = alm.muestras_rostro(dominio)
    if not muestras:
        return None
    caras = [alm.cara_normalizada(m) for m in muestras] + list(fondo or [])
    modelo = rostro.entrenar(np.array(caras), meta_varianza)
    mid = alm.guardar_modelo(dominio, modelo, len(caras))
    alm.guardar_vectores(mid, {m["id"]: modelo.proyectar(alm.cara_normalizada(m)) for m in muestras})
    return mid


def registrar(alm: Almacen, id_: str, nombre: str, nivel: int, pin: str,
              huellas: list[tuple[np.ndarray, str]], rostros: list[tuple[np.ndarray, str]],
              perfil_huella: dict[str, str] | None = None, fondo: list[np.ndarray] | None = None,
              reentrenar_modelo: bool = True) -> Informe:
    """huellas y rostros: listas de (imagen, fuente). perfil_huella: fuente -> perfil."""
    perfil_huella = perfil_huella or {}
    alm.crear_usuario(id_, nombre, nivel, pin)
    inf = Informe()
    for img, fuente in huellas:
        ok, msg = agregar_huella(alm, id_, img, fuente, perfil_huella.get(fuente, fuente))
        if ok:
            inf.huellas_ok += 1
        else:
            inf.huellas_rechazadas.append(msg)
    dominios = set()
    for cuadro, fuente in rostros:
        if agregar_rostro(alm, id_, cuadro, fuente):
            inf.rostros_ok += 1
            dominios.add(dominio_rostro(fuente))
        else:
            inf.rostros_rechazados += 1
    if reentrenar_modelo:
        for d in dominios:
            inf.modelos[d] = reentrenar(alm, d, fondo)
    return inf
