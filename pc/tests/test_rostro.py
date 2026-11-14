"""Pipeline de rostro.

    pytest pc/tests/test_rostro.py -s

Las pruebas de PCA usan datos aleatorios y no dependen de nada. Viola-Jones se prueba con
skimage.data.astronaut() (viene en el paquete). La prueba de ORL corre solo si el dataset
está en datos/datasets/orl (python pc/scripts/descargar_datasets.py orl).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import rostro  # noqa: E402
from pia.rostro.eigenfaces import distancia_minima  # noqa: E402

ORL = Path(__file__).resolve().parents[2] / "datos" / "datasets" / "orl"


@pytest.fixture(scope="module")
def caras_aleatorias():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(5, 64 * 64))
    return rng.normal(size=(30, 5)) @ base + 0.01 * rng.normal(size=(30, 64 * 64))


def test_eigenfaces_ortonormales(caras_aleatorias):
    m = rostro.entrenar(caras_aleatorias, meta_varianza=0.999)
    gram = m.eigenfaces @ m.eigenfaces.T
    assert np.allclose(gram, np.eye(m.k), atol=1e-8)


def test_truco_matriz_pequena_igual_a_svd(caras_aleatorias):
    m = rostro.entrenar(caras_aleatorias, meta_varianza=0.999)
    A = caras_aleatorias - caras_aleatorias.mean(0)
    _, s, vt = np.linalg.svd(A, full_matrices=False)
    for i in range(m.k):  # mismo subespacio, signo libre
        assert abs(abs(m.eigenfaces[i] @ vt[i]) - 1) < 1e-6
    assert np.allclose(m.valores, (s[: m.k] ** 2) / (len(A) - 1))


def test_k_por_varianza(caras_aleatorias):
    m = rostro.entrenar(caras_aleatorias, meta_varianza=0.95)
    assert m.varianza_explicada >= 0.95
    assert m.k <= 5  # los datos tienen 5 direcciones reales


def test_reconstruccion_y_distancia_al_espacio(caras_aleatorias):
    m = rostro.entrenar(caras_aleatorias, meta_varianza=0.999)
    x = caras_aleatorias[3]
    assert np.linalg.norm(x - m.reconstruir(m.proyectar(x))) < 1.0
    ruido = np.random.default_rng(1).normal(size=x.shape) * 3
    assert m.distancia_al_espacio(ruido) > 10 * m.distancia_al_espacio(x)


def test_guardar_y_cargar(tmp_path, caras_aleatorias):
    m = rostro.entrenar(caras_aleatorias)
    m.guardar(tmp_path / "m.npz")
    m2 = rostro.Modelo.cargar(tmp_path / "m.npz")
    assert np.allclose(m.proyectar(caras_aleatorias[0]), m2.proyectar(caras_aleatorias[0]))


def test_comparar_distancia_minima():
    v = np.array([[0.0, 0.0], [3.0, 4.0]])
    assert distancia_minima(np.array([3.0, 0.0]), v) == pytest.approx(3.0)
    d, acepta = rostro.comparar(np.array([3.0, 4.0]), v, umbral=1.0)
    assert d == 0 and acepta


def test_viola_jones_astronauta():
    data = pytest.importorskip("skimage.data")
    try:
        img = data.astronaut()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"astronaut() no disponible: {e}")
    r = rostro.procesar(img[:, :, ::-1].copy())  # RGB -> BGR
    assert r.hay_rostro and not r.deteccion.con_relleno
    x, y, w, h = r.deteccion.rostro
    assert 150 < x + w / 2 < 280 and 50 < y + h / 2 < 170  # la cara está arriba al centro
    assert r.alineado.imagen.shape == (64, 64)
    assert r.normalizada.imagen.min() >= 0 and r.normalizada.imagen.max() <= 1
    assert np.all(r.normalizada.imagen[~rostro.MASCARA] == 0.5)


def test_sin_rostro_no_inventa():
    ruido = np.random.default_rng(2).integers(0, 255, (240, 320), dtype=np.uint8)
    r = rostro.procesar(ruido, permitir_relleno=False)
    assert not r.hay_rostro
    assert r.alineado.metodo == "sin_rostro"


@pytest.mark.skipif(not ORL.exists(), reason="ORL no descargado")
def test_orl_deteccion_y_eer():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from evaluar_rostro_orl import evaluar

    r = evaluar(ORL, imprimir=True)
    assert r["con_relleno"] / r["total"] >= 0.95
    assert r["eer"] <= 0.15
    assert r["rango1"] >= 0.70
