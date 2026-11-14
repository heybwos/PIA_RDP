"""Un perfil de parámetros por fuente de huella.

Los valores de `sintetico` son los de la maqueta (docs/maqueta/acceso_biometrico.html,
processFinger). `as608` empieza igual (misma resolución, 256 x 288) y se ajusta en N7
con capturas reales. `fvc2002` se ajusta cuando se tenga el dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Perfil:
    nombre: str
    bloque: int = 16              # px por bloque (segmentación y orientación)
    umbral_varianza: float = 0.0085  # varianza mínima de un bloque (imagen en 0..1) para ser huella
    pasadas_mayoria: int = 2      # filtro de mayoría 3x3 sobre la máscara de bloques
    gabor_orientaciones: int = 24
    gabor_radio: int = 7          # kernel de (2r+1) x (2r+1)
    gabor_sigma: float = 4.0
    gabor_frecuencia: float = 1 / 8.9  # 1 / periodo de crestas en px (fija por perfil: recorte de N2)
    margen_minucias: int = 12     # px desde el borde de la imagen
    distancia_min_minucias: float = 9.0  # pares más cercanos se descartan (ruido)
    ecualizar: bool = False       # CLAHE antes de normalizar (imágenes de poco contraste)


PERFILES: dict[str, Perfil] = {
    "sintetico": Perfil("sintetico"),
    "as608": Perfil("as608"),
    "fvc2002": Perfil("fvc2002"),
}


def perfil(nombre: str | Perfil, **cambios) -> Perfil:
    p = nombre if isinstance(nombre, Perfil) else PERFILES[nombre]
    return replace(p, **cambios) if cambios else p
