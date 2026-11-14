"""Backend: FastAPI con WebSocket en /ws y los estáticos de app/.

    python -m pia            (desde pc/)  ->  http://127.0.0.1:8000

Una verificación a la vez. Los eventos van a todos los clientes conectados.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import camara as camara_, config, simular
from .almacen import Almacen
from .orquestador import Orquestador

RAIZ = Path(__file__).resolve().parents[2]


def _a_json(o: Any) -> Any:
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o).__name__)


class Estado:
    def __init__(self, cfg: config.Config, alm: Almacen):
        self.cfg, self.alm = cfg, alm
        self.clientes: set[WebSocket] = set()
        self.tarea: asyncio.Task | None = None
        self.modo = "simular"
        self.orq = Orquestador(alm, cfg, self.difundir)

    async def difundir(self, tipo: str, datos: dict[str, Any]) -> None:
        texto = json.dumps({"tipo": tipo, **datos}, default=_a_json, ensure_ascii=False)
        for ws in list(self.clientes):
            try:
                await ws.send_text(texto)
            except Exception:  # noqa: BLE001
                self.clientes.discard(ws)

    def resumen(self) -> dict[str, Any]:
        escs = simular.cargar_escenarios(self.alm)
        cal = {f"{f}_{d}": c["umbral"] for f, d in (("huella", "fvc2002"), ("huella", "as608"),
                                                    ("rostro", "dataset"), ("rostro", "camara"))
               if (c := self.alm.calibracion_activa(f, d))}
        return {"modo": self.modo, "conexion": "simulado" if self.modo == "simular" else "sin conectar",
                "usuarios": self.alm.usuarios(),
                "escenarios": [{"clave": k, "nombre": e["nombre"], "esperado": e["esperado"]} for k, e in escs.items()],
                "bancos": {"huella": "fvc2002", "rostro": "orl"}, "calibracion": cal,
                "ocupado": bool(self.tarea and not self.tarea.done())}

    async def iniciar(self, escenario: str, fuente_rostro: str = "dataset", velocidad: float = 1.0) -> None:
        if self.tarea and not self.tarea.done():
            await self.difundir("error", {"mensaje": "Ya hay una verificación en curso", "que_revisar": "Espera o cancela"})
            return
        escs = simular.cargar_escenarios(self.alm)
        if escenario not in escs:
            await self.difundir("error", {"mensaje": f"No existe el escenario '{escenario}'",
                                          "que_revisar": "Corre pc/scripts/sembrar_simular.py"})
            return
        disp, cam = simular.preparar(escs[escenario], velocidad, int(self.cfg.valor("actuadores.ms_entre_servos", 300)))
        if fuente_rostro == "camara":
            cam = camara_.desde_config(self.cfg)

        async def correr():
            try:
                await self.orq.verificar(disp, cam, self.modo)
            finally:
                cam.cerrar()
                await self.difundir("estado", self.resumen())

        self.tarea = asyncio.create_task(correr())

    async def cancelar(self) -> None:
        if self.tarea and not self.tarea.done():
            self.tarea.cancel()
            await self.difundir("error", {"mensaje": "Verificación cancelada", "que_revisar": ""})


def crear_app(cfg: config.Config | None = None) -> FastAPI:
    cfg = cfg or config.cargar()
    est = Estado(cfg, Almacen(cfg.carpeta_datos))
    app = FastAPI(title="PIA acceso biométrico")
    app.state.estado = est

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        est.clientes.add(sock)
        await sock.send_text(json.dumps({"tipo": "estado", **est.resumen()}, default=_a_json, ensure_ascii=False))
        try:
            while True:
                msg = json.loads(await sock.receive_text())
                tipo = msg.get("tipo")
                if tipo == "iniciar":
                    await est.iniciar(msg.get("escenario", "l1"), msg.get("fuente_rostro", "dataset"),
                                      float(msg.get("velocidad", 1.0)))
                elif tipo == "cancelar":
                    await est.cancelar()
                elif tipo == "modo":
                    est.modo = msg.get("modo", "simular")
                    await est.difundir("estado", est.resumen())
                elif tipo == "estado":
                    await sock.send_text(json.dumps({"tipo": "estado", **est.resumen()}, default=_a_json))
                else:
                    await sock.send_text(json.dumps({"tipo": "error", "mensaje": f"Mensaje no soportado: {tipo}",
                                                     "que_revisar": "docs/EVENTOS.md"}))
        except WebSocketDisconnect:
            est.clientes.discard(sock)

    @app.get("/api/bitacora")
    async def bitacora(limite: int = 50):
        return est.alm.bitacora(limite)

    carpeta_app = RAIZ / "app"
    if (carpeta_app / "index.html").exists():
        app.mount("/", StaticFiles(directory=carpeta_app, html=True), name="app")
    else:
        @app.get("/")
        async def inicio():
            return HTMLResponse("<p>Backend del PIA en marcha. La app (app/) llega en N5. "
                                "WebSocket en <code>/ws</code>, bitácora en <code>/api/bitacora</code>.</p>")

    return app
