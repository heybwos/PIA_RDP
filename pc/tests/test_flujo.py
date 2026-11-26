"""Base de datos, PIN, fusión, cámara, orquestador y servidor.

    pytest pc/tests/test_flujo.py -s

Las pruebas de punta a punta necesitan datos/datasets (descargar_datasets.py); si no están,
se saltan. Escriben en una carpeta temporal, nunca en datos/.
"""

from __future__ import annotations

import asyncio
import shutil
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


@pytest.mark.skipif(not HAY_DATASETS, reason="sin datasets")
def test_rostro_en_vivo_espera_cara_dentro_de_la_guia(tmp_path, monkeypatch):
    """Con cámara real se toma el cuadro solo cuando la cara está dentro de la guía, y se
    indica qué ajustar (sin cara, cara chica y descentrada)."""
    import cv2

    from pia import camara, orquestador

    monkeypatch.setattr(orquestador, "REACCION_S", 0.0)
    monkeypatch.setattr(orquestador, "MANTENER_S", 0.0)
    cara = cv2.imread(str(DATASETS / "orl" / "s3" / "1.pgm"), cv2.IMREAD_GRAYSCALE)

    def lienzo(ancho, cx, cy):  # retrato de 480 x 640 con la cara de `ancho` px centrada en (cx, cy)
        c = np.full((640, 480), 90, np.uint8)
        g = cv2.resize(cara, (ancho, int(ancho * 112 / 92)))
        y0, x0 = cy - g.shape[0] // 2, cx - ancho // 2
        c[y0 : y0 + g.shape[0], x0 : x0 + ancho] = g
        return c

    vacio = np.full((640, 480), 90, np.uint8)
    chica = lienzo(90, 240, 270)
    centrada = lienzo(200, 240, 290)
    orq = orquestador.Orquestador(Almacen(tmp_path), config.cargar(), None)
    for img, esperado in ((vacio, "No te veo"), (chica, "Acércate"), (centrada, "Así está bien")):
        from pia import rostro
        _, pista, _ = orquestador.evaluar_posicion(rostro.procesar(img, permitir_relleno=False), 480, 640)
        assert pista.startswith(esperado), (esperado, pista)

    class Secuencia(camara.Camara):
        def __init__(self):
            self.cuadros = [vacio, chica, centrada]
            self.i = 0

        def _capturar(self):
            c = self.cuadros[min(self.i, len(self.cuadros) - 1)]
            self.i += 1
            return c

    eventos = []

    async def emitir(t, d):
        eventos.append((t, d))

    orq.emitir = emitir
    cam = Secuencia()
    cuadro = asyncio.run(orq._cuadro_rostro(cam))
    assert cuadro is centrada and cam.i == 3
    vivos = [d for t, d in eventos if t == "rostro_vivo"]
    assert vivos[-1]["estado"] == "tomado" and any(d.get("estado") == "ajusta" for d in vivos)


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
    # cargar_escenarios calcula las rutas desde <carpeta>/datasets: se copia lo que usa Simular
    for sub in ("orl", Path("fvc2002") / simular.DB_HUELLA):
        shutil.copytree(DATASETS / sub, carpeta / "datasets" / sub)
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


def test_caja_espera_a_la_app_y_reintenta_huella(sembrado):
    """La caja actúa (ACCESO, servos) solo después de que la app mostró el veredicto, y una
    huella débil pide hasta 3 capturas sin volver a teclear el PIN."""
    alm, cfg = sembrado
    orden: list[str] = []

    async def emitir(tipo, datos):
        if tipo in ("huella_reintento", "veredicto", "servo", "leds"):
            orden.append(tipo)
        if tipo == "serie" and datos["linea"].startswith("ACCESO"):
            orden.append("ACCESO")

    async def esperar(punto, limite):
        orden.append(f"espera:{punto}")

    escs = simular.cargar_escenarios(alm)

    async def correr(clave):
        orq = Orquestador(alm, cfg, emitir)
        orq.esperar = esperar
        disp, cam = simular.preparar(escs[clave], velocidad=0)
        disp.permite_reintentos = True  # como el sensor real
        return await orq.verificar(disp, cam)

    r = asyncio.run(correr("l2"))
    assert r.concedido
    i_ver, i_esp = orden.index("veredicto"), orden.index("espera:veredicto")
    assert i_ver < i_esp < orden.index("ACCESO") < orden.index("servo")
    assert orden.index("espera:huella") < i_ver
    orden.clear()
    r = asyncio.run(correr("ih"))  # impostor de huella: puntaje bajo en cada intento
    assert not r.concedido
    assert orden.count("huella_reintento") == 2 and orden.count("espera:huella") == 3


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


def test_modulo_servos_por_websocket(sembrado):
    """El módulo Servos mueve uno a la vez (en Simular, solo el dibujo) y respeta los ángulos."""
    from fastapi.testclient import TestClient

    from pia.servidor import crear_app

    _, cfg = sembrado
    with TestClient(crear_app(cfg)) as cliente, cliente.websocket_connect("/ws") as ws:
        ws.receive_json()  # estado
        ws.send_json({"tipo": "servo", "n": "ambos", "accion": "abrir"})
        movs = [ws.receive_json() for _ in range(2)]
        assert [(m["tipo"], m["n"], m["angulo"], m["abierto"]) for m in movs] == [("servo", 1, 90, True), ("servo", 2, 90, True)]
        ws.send_json({"tipo": "servo", "n": 2, "angulo": 45})
        m = ws.receive_json()
        assert (m["n"], m["angulo"], m["abierto"], m["manual"]) == (2, 45, True, True)
        ws.send_json({"tipo": "servo", "n": 1, "accion": "cerrar"})
        assert ws.receive_json()["angulo"] == 0


def test_seccion_datos_solo_lectura_y_se_llena_sola(sembrado):
    """/api/datos: sin PIN, imágenes y minucias de cada muestra, nada fuera de datos/, y un alta
    nueva aparece sin reiniciar el servidor. Va al final: agrega un usuario al almacén compartido."""
    from fastapi.testclient import TestClient

    from pia import registro
    from pia.huella import leer
    from pia.servidor import crear_app

    alm, cfg = sembrado
    with TestClient(crear_app(cfg)) as cliente:
        d = cliente.get("/api/datos").json()
        assert {u["id"] for u in d["usuarios"]} == {"07", "12"} and all(u["de_prueba"] for u in d["usuarios"])
        assert "pin" not in str(d["usuarios"]).lower()
        assert {m["dominio"] for m in d["modelos"]} == {"dataset"} and {c["factor"] for c in d["calibraciones"]} == {"huella", "rostro"}
        u = d["usuarios"][0]
        h, r = u["huellas"][0], u["rostros"][0]
        assert cliente.get(f"/api/datos/huella/{h['id']}.png").headers["content-type"] == "image/png"
        ms = cliente.get(f"/api/datos/huella/{h['id']}/minucias").json()
        assert len(ms) == h["n_minucias"] and {"x", "y", "t", "tipo"} <= set(ms[0])
        rec = cliente.get(f"/api/datos/rostro/{r['id']}/reconstruccion.png?k=5")
        assert rec.status_code == 200 and rec.content[:4] == b"\x89PNG"
        assert cliente.get("/api/datos/modelo/dataset/media.png").status_code == 200
        assert cliente.get("/api/datos/modelo/dataset/eigenface/9999.png").status_code == 404
        assert cliente.get("/api/datos/modelo/camara/media.png").status_code == 404
        assert cliente.get("/api/datos/banco/..%2F..%2Fpia.db/01.png").status_code == 404
        assert cliente.get("/api/datos/tanda2/07/..%2Fpia.db").status_code == 404

        img = leer(DATASETS / "fvc2002" / simular.DB_HUELLA / "105_1.tif")
        registro.registrar(alm, "33", "Nuevo", 1, "1357", [(img, "fvc2002")], [], {"fvc2002": "fvc2002"})
        try:
            nuevo = next(u for u in cliente.get("/api/datos").json()["usuarios"] if u["id"] == "33")
            assert nuevo["nombre"] == "Nuevo" and len(nuevo["huellas"]) == 1
        finally:
            alm.borrar_usuario("33")


def test_pestana_oculta_no_adelanta_a_la_caja(tmp_path):
    """Con dos pestañas abiertas, la oculta (anima al instante) no puede soltar los servos antes que la
    visible. Si la última visible se oculta, la caja sigue sola; sin ninguna visible, no espera."""
    from pia.servidor import Estado

    est = Estado(config.cargar(datos__carpeta=str(tmp_path)), Almacen(tmp_path))
    est.modo = "esp32"
    visible, oculta = object(), object()
    est.clientes |= {visible, oculta}
    est.visibilidad(oculta, False)

    async def caso():
        t = asyncio.create_task(est.esperar_app("veredicto", 5))
        await asyncio.sleep(0.05)
        est.listo_de(oculta, "veredicto")
        await asyncio.sleep(0.05)
        assert not t.done()                       # el aviso de la oculta no cuenta
        est.listo_de(visible, "veredicto")
        await asyncio.wait_for(t, 1)              # el de la visible sí

        t = asyncio.create_task(est.esperar_app("huella", 5))
        await asyncio.sleep(0.05)
        est.visibilidad(visible, False)           # se oculta la última visible
        await asyncio.wait_for(t, 1)
        await asyncio.wait_for(est.esperar_app("veredicto", 5), 1)   # nadie la ve: no espera

    asyncio.run(caso())
    est.alm.cerrar()
