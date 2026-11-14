"""Modo ESP32 contra el ESP32 falso (pc/herramientas/esp32_falso.py) por socket://.

    pytest pc/tests/test_protocolo.py -s

Una verificación completa y los casos de falla: CRC malo, corte a media imagen, silencio y
cancelación con D. Usa una carpeta temporal sembrada con sembrar_prueba_esp32 (nunca datos/).
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

PC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PC))
from pia import config, simular  # noqa: E402
from pia.almacen import Almacen  # noqa: E402
from pia.camara import CamaraArchivo  # noqa: E402
from pia.dispositivos import DispositivoESP32  # noqa: E402
from pia.dispositivos.esp32 import buscar  # noqa: E402
from pia.orquestador import Orquestador  # noqa: E402

DATASETS = PC.parent / "datos" / "datasets"
FIXTURES = PC / "tests" / "fixtures" / "huellas_sinteticas"
pytestmark = pytest.mark.skipif(not (DATASETS / "orl" / "s1").exists(), reason="sin datasets")


def _puerto() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Falso:
    def __init__(self, *args: str):
        self.puerto = _puerto()
        self.proc = subprocess.Popen([sys.executable, str(PC / "herramientas" / "esp32_falso.py"), "--puerto",
                                      str(self.puerto), "--guion", "21#2468#", "--rapido", *args],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.proc.stdout.readline()  # "ESP32 falso en ..."
        self.url = f"socket://127.0.0.1:{self.puerto}"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.proc.kill()


@pytest.fixture(scope="module")
def preparado(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("datos_esp32")
    alm = Almacen(carpeta)
    datos = simular.sembrar_prueba_esp32(alm, DATASETS, FIXTURES)
    cfg = config.cargar(datos__carpeta=str(carpeta))
    yield alm, cfg, datos
    alm.cerrar()


def correr(alm, cfg, datos, *falla: str):
    eventos: list[tuple[str, dict]] = []

    async def emitir(t, d):
        eventos.append((t, d))

    async def principal():
        with Falso(*falla) as f:
            disp = DispositivoESP32(f.url, emitir=emitir)
            disp.limite_huella_s = 4.0  # el falso es inmediato con --rapido
            await disp.conectar()
            try:
                return await asyncio.wait_for(
                    Orquestador(alm, cfg, emitir).verificar(disp, CamaraArchivo(datos["rostro"]), "esp32"), 60)
            finally:
                await disp.cerrar()

    return asyncio.run(principal()), eventos


def test_buscar_encuentra_al_falso():
    with Falso() as f:
        lista = buscar(extra=[f.url])
    yo = next(p for p in lista if p["puerto"] == f.url)
    assert yo["responde"] and yo["version"] == "falso-1.0" and yo["sensor"] and yo["oled"]


def test_verificacion_completa(preparado):
    alm, cfg, datos = preparado
    r, ev = correr(alm, cfg, datos)
    tipos = [t for t, _ in ev]
    assert r.concedido and r.nivel == 2, r.motivo
    assert tipos.count("tecla") == 8
    assert sum(1 for t in tipos if t == "huella_filas") == 18  # 288 filas en bloques de 16
    assert ("huella_fin", ) and next(d for t, d in ev if t == "huella_fin")["crc_ok"]
    assert r.fila["modo"] == "esp32" and r.fila["fuente_huella"] == "as608"
    lineas = [d["linea"] for t, d in ev if t == "serie" and d["dir"] == "in"]
    assert any(l.startswith("PIN:21:****") for l in lineas)  # el PIN no se muestra
    assert "ACCESO:2" in [d["linea"] for t, d in ev if t == "serie" and d["dir"] == "out"]


@pytest.mark.parametrize("falla,texto", [("crc", "CRC"), ("corte", "cortó"), ("silencio", "a tiempo")])
def test_fallas_de_imagen(preparado, falla, texto):
    alm, cfg, datos = preparado
    t0 = time.monotonic()
    r, ev = correr(alm, cfg, datos, "--falla", falla)
    assert not r.concedido
    errores = [d["mensaje"] for t, d in ev if t == "error"]
    assert errores and texto in errores[0], errores
    assert r.fila.get("pin_ok") == 1 and "error" in (r.fila.get("motivo") or "")
    assert time.monotonic() - t0 < 60


def test_cancelar_con_d(preparado):
    alm, cfg, datos = preparado
    r, ev = correr(alm, cfg, datos, "--falla", "cancela")
    # D borra lo tecleado y el guion completo vuelve a entrar: la verificación sigue y concede
    assert r.concedido
    casillas = [d for t, d in ev if t == "casillas"]
    assert any(c["id"] == "" for c in casillas[2:])
