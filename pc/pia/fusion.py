"""Decisión: normalización con la calibración activa y regla de fusión.

Normalización (la misma de la maqueta): cada factor queda en 0.50 justo en su umbral.
  huella: s_h = clamp(puntaje / (2 · umbral_huella), 0, 1)        (más puntaje = mejor)
  rostro: s_r = clamp(1 − distancia / (2 · umbral_rostro), 0, 1)  (menos distancia = mejor)
Regla: PIN correcto, s_h ≥ 0.50, s_r ≥ 0.50 y 0.5·s_h + 0.5·s_r ≥ 0.60.
(La regla anterior de la maqueta, piso 0.35 y fusión 0.50, dejaba pasar a un impostor de
rostro con buena huella.)
"""

from __future__ import annotations

from dataclasses import dataclass


def _clamp(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def normalizar_huella(puntaje: float, umbral: float) -> float:
    return _clamp(puntaje / (2 * umbral))


def normalizar_rostro(distancia: float, umbral: float) -> float:
    return _clamp(1 - distancia / (2 * umbral))


@dataclass
class Decision:
    concedido: bool
    nivel: int
    huella: float
    rostro: float
    fusion: float
    motivo: str


def decidir(nivel_usuario: int, s_huella: float, s_rostro: float, peso_huella: float = 0.5,
            peso_rostro: float = 0.5, umbral_factor: float = 0.50, umbral_fusion: float = 0.60) -> Decision:
    f = peso_huella * s_huella + peso_rostro * s_rostro
    h_ok, r_ok = s_huella >= umbral_factor, s_rostro >= umbral_factor
    if not h_ok and not r_ok:
        motivo = "ni huella ni rostro pasan su umbral"
    elif not h_ok:
        motivo = "la huella no pasa su umbral"
    elif not r_ok:
        motivo = "el rostro no pasa su umbral"
    elif f < umbral_fusion:
        motivo = f"el puntaje fusionado no llega a {umbral_fusion:.2f}"
    else:
        return Decision(True, nivel_usuario, s_huella, s_rostro, f, "")
    return Decision(False, 0, s_huella, s_rostro, f, motivo)
