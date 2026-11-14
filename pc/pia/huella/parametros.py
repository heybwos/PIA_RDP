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
    # Ajustado en N7 (14 de noviembre) con el banco real del AS608: 6 dedos x 8 capturas,
    # 5 plantillas y 3 pruebas por dedo (18 genuinos, 90 impostores). Rejilla de 144
    # combinaciones (pc/scripts/explorar_parametros.py): el perfil de la maqueta daba EER 34 %;
    # este, 16.7 % y FRR 33 % con FAR = 0. La imagen del sensor usa ~8 de 16 niveles: CLAHE y
    # una segmentación más sensible recuperan crestas; con distancia mínima 6 salen ~33 minucias.
    # Aflojar las tolerancias del matching subía también a los impostores: se quedan igual.
    "as608": Perfil("as608", ecualizar=True, umbral_varianza=0.004, distancia_min_minucias=6.0),
    "fvc2002": Perfil("fvc2002"),
}


def perfil(nombre: str | Perfil, **cambios) -> Perfil:
    p = nombre if isinstance(nombre, Perfil) else PERFILES[nombre]
    return replace(p, **cambios) if cambios else p
