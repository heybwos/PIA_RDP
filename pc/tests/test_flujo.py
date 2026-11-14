"""Base de datos, PIN, fusión, cámara, orquestador y servidor.

    pytest pc/tests/test_flujo.py -s

Las pruebas de punta a punta necesitan datos/datasets (descargar_datasets.py); si no están,
se saltan. Escriben en una carpeta temporal, nunca en datos/.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

PC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PC))
from pia import calibracion, config, fusion, pin, simular  # noqa: E402
from pia.almacen import Almacen, blob_a_minucias, minucias_a_blob  # noqa: E402
from pia.huella import Minucia  # noqa: E402
from pia.orquestador import Orquestador  # noqa: E402

DATASETS = PC.parent / "datos" / "datasets"
HAY_DATASETS = (DATASETS / "orl" / "s1").exists() and (DATASETS / "fvc2002" / "DB1_B").exists()


# ---------------------------------------------------------------- piezas
def test_pin_hash():
    h, s, it = pin.hashear("4821")
    assert len(h) == 32 and len(s) == 16 and it == 200_000
    assert pin.verificar("4821", h, s, it)
    assert not pin.verificar("4812", h, s, it)
    with pytest.raises(ValueError):
        pin.hashear("12a4")


def test_fusion_regla():
    assert fusion.normalizar_huella(0.30, 0.30) == 0.5
    assert fusion.normalizar_rostro(10.0, 10.0) == 0.5
    assert fusion.decidir(2, 0.9, 0.8).concedido
    # Impostor de rostro con huella perfecta: la fusión llega a 0.69 pero el rostro no pasa
    d = fusion.decidir(1, 1.0, 0.38)
    assert not d.concedido and d.fusion > 0.6 and "rostro" in d.motivo
    d = fusion.decidir(1, 0.55, 0.55)
    assert not d.concedido and "fusionado" in d.motivo


def test_calibracion_eer():
    r = calibracion.por_eer([0.8, 0.9, 0.7], [0.1, 0.2, 0.3], mayor_es_mejor=True)
    assert r.eer == 0 and 0.3 < r.umbral <= 0.7
    r = calibracion.por_eer([1, 2, 3], [7, 8, 9], mayor_es_mejor=False)
    assert r.eer == 0 and 3 < r.umbral <= 7


def test_almacen_usuario_y_minucias(tmp_path):
    alm = Almacen(tmp_path)
    alm.crear_usuario("07", "Ana", 1, "4821")
    assert alm.verificar_pin("07", "4821") and not alm.verificar_pin("07", "0000")
    assert not alm.verificar_pin("99", "4821")
    with pytest.raises(ValueError):
        alm.crear_usuario("07", "Otra", 1, "1111")
    ms = [Minucia(10, 20, 1.25, "T"), Minucia(30, 40, 0.5, "B")]
    back = blob_a_minucias(minucias_a_blob(ms))
    assert [(m.x, m.y, m.tipo) for m in back] == [(10, 20, "T"), (30, 40, "B")]
    alm.borrar_usuario("07")
    assert alm.usuario("07") is None
    alm.cerrar()


# ---------------------------------------------------------------- cámara
def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(not HAY_DATASETS, reason="sin datasets")
def test_camara_url_con_droidcam_falso():
    from pia import camara, rostro

    puerto = _puerto_libre()
    proc = subprocess.Popen([sys.executable, str(PC / "herramientas" / "droidcam_falso.py"), "--puerto", str(puerto)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.5)
        cam = camara.CamaraURL(f"http://127.0.0.1:{puerto}/video")
        img = cam.capturar()
        cam.cerrar()
        assert img.shape[:2] == (480, 640)
        assert rostro.procesar(img, permitir_relleno=False).hay_rostro
    finally:
        proc.kill()


def test_camara_sin_respuesta_no_inventa():
    from pia import camara

    with pytest.raises(camara.CamaraError) as e:
        camara.CamaraURL(f"http://127.0.0.1:{_puerto_libre()}/video").capturar()
    assert "DroidCam" in e.value.que_revisar


# ---------------------------------------------------------------- punta a punta
@pytest.fixture(scope="module")
def sembrado(tmp_path_factory):
    if not HAY_DATASETS:
        pytest.skip("sin datasets: python pc/scripts/descargar_datasets.py")
    carpeta = tmp_path_factory.mktemp("datos")
    alm = Almacen(carpeta)
    simular.sembrar(alm, DATASETS, imprimir=lambda *_: None)
    cfg = config.cargar(datos__carpeta=str(carpeta), datos__guardar_intentos=True)
    yield alm, cfg
    alm.cerrar()


def test_cinco_escenarios_y_bitacora(sembrado):
    alm, cfg = sembrado
    eventos: list[str] = []

    async def emitir(tipo, datos):
        eventos.append(tipo)

    async def correr():
        orq = Orquestador(alm, cfg, emitir)
        out = {}
        for clave, e in simular.cargar_escenarios(alm).items():
            disp, cam = simular.preparar(e, velocidad=0)
            out[clave] = (await orq.verificar(disp, cam), e["esperado"])
        return out

    antes = len(alm.bitacora(1000))
    res = asyncio.run(correr())
    for clave, (r, esperado) in res.items():
        obtenido = f"Concedido, nivel {r.nivel}" if r.concedido else "Negado"
        assert obtenido == esperado, f"{clave}: {obtenido} ({r.motivo})"
    assert sum(r.concedido for r, _ in res.values()) == 2
    assert len(alm.bitacora(1000)) - antes == 5
    assert "error" not in eventos
    for t in ("huella_filas", "huella_etapa", "huella_matching", "rostro_deteccion", "rostro_pca",
              "rostro_reconstruccion", "fusion", "veredicto", "servo", "bitacora_fila"):
        assert t in eventos, t
    fila = res["l1"][0].fila
    assert (alm.carpeta / fila["archivo_huella"]).exists()


def test_servidor_websocket(sembrado):
    from fastapi.testclient import TestClient

    from pia.servidor import crear_app

    _, cfg = sembrado
    with TestClient(crear_app(cfg)) as cliente, cliente.websocket_connect("/ws") as ws:
        estado = ws.receive_json()
        assert estado["tipo"] == "estado" and {u["id"] for u in estado["usuarios"]} == {"07", "12"}
        ws.send_json({"tipo": "iniciar", "escenario": "l2", "velocidad": 0})
        tipos, veredicto = [], None
        for _ in range(500):
            m = ws.receive_json()
            tipos.append(m["tipo"])
            if m["tipo"] == "veredicto":
                veredicto = m
                break
        assert veredicto and veredicto["concedido"] and veredicto["nivel"] == 2
        assert tipos.index("huella_inicio") < tipos.index("huella_matching") < tipos.index("rostro_cuadro")
        img = next(m for m in [veredicto] if m)  # noqa: F841
        assert cliente.get("/api/bitacora").json()[0]["decision"] == 2
