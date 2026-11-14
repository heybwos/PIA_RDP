"""Pipeline de huella sobre el banco sintético (pc/tests/fixtures/huellas_sinteticas).

    pytest pc/tests/test_huella.py -s      (-s para ver el EER)

El banco sale de la maqueta: node pc/scripts/exportar_sinteticos.js
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import huella  # noqa: E402

BANCO = Path(__file__).parent / "fixtures" / "huellas_sinteticas"


def eer(genuinos: np.ndarray, impostores: np.ndarray) -> tuple[float, float]:
    """Tasa de error igual y su umbral (puntaje >= umbral se acepta)."""
    umbrales = np.unique(np.concatenate([genuinos, impostores, [0.0, 1.01]]))
    mejor = (1.0, 0.0, 1.0)
    for u in umbrales:
        far = float((impostores >= u).mean())
        frr = float((genuinos < u).mean())
        if abs(far - frr) < mejor[2]:
            mejor = ((far + frr) / 2, float(u), abs(far - frr))
    return mejor[0], mejor[1]


@pytest.fixture(scope="module")
def banco() -> dict[str, huella.ResultadoHuella]:
    archivos = sorted(BANCO.glob("*.bin"))
    assert len(archivos) >= 16, "Falta el banco sintético: node pc/scripts/exportar_sinteticos.js"
    return {f.stem: huella.procesar(huella.leer(f), "sintetico") for f in archivos}


def test_formato_as608():
    datos = bytes([0xAB]) * huella.imagen.BYTES_AS608
    img = huella.desempacar(datos, nibble_alto_primero=True)
    assert img.shape == (288, 256)
    assert img[0, 0] == 0xA * 17 and img[0, 1] == 0xB * 17
    assert huella.desempacar(datos, nibble_alto_primero=False)[0, 0] == 0xB * 17


def test_etapas_completas(banco):
    r = next(iter(banco.values()))
    for etapa in ("original", "normalizada", "segmentacion", "orientacion", "gabor", "binaria", "esqueleto"):
        assert etapa in r.etapas
    assert r.etapas["esqueleto"].shape == (288, 256)
    assert 0 < r.calidad <= 1
    assert all(0 <= m.t < np.pi and m.tipo in "TB" for m in r.minucias)


def test_minucias_suficientes(banco):
    cuantas = [len(r.minucias) for r in banco.values()]
    assert min(cuantas) >= 10, cuantas


def test_misma_imagen_puntaje_uno(banco):
    r = next(iter(banco.values()))
    assert huella.comparar(r, r).puntaje == pytest.approx(1.0)


def test_pocas_minucias_puntaje_cero():
    pocas = [huella.Minucia(10 * i, 10 * i, 0.0, "T") for i in range(3)]
    assert huella.comparar(pocas, pocas).puntaje == 0.0


def test_genuinos_contra_impostores(banco):
    plantillas = {k[:4]: v for k, v in banco.items() if k.endswith("imp0")}
    muestras = {k: v for k, v in banco.items() if not k.endswith("imp0")}
    gen, imp = [], []
    for ida, a in plantillas.items():
        for k, b in muestras.items():
            (gen if k.startswith(ida) else imp).append(huella.comparar(a, b).puntaje)
    gen, imp = np.array(gen), np.array(imp)
    tasa, umbral = eer(gen, imp)
    ms = np.mean([r.duracion_ms for r in banco.values()])
    print(f"\n  Banco sintético: {len(gen)} genuinos, {len(imp)} impostores")
    print(f"  Genuinos  {gen.min():.3f} .. {gen.max():.3f}  (media {gen.mean():.3f})")
    print(f"  Impostores {imp.min():.3f} .. {imp.max():.3f}  (media {imp.mean():.3f})")
    print(f"  EER = {tasa:.3f} con umbral {umbral:.3f};  {ms:.0f} ms por huella")
    assert gen.mean() > 3 * imp.mean()
    assert tasa <= 0.05
