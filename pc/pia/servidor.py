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
from .dispositivos import DispositivoESP32, ErrorDispositivo, esp32
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
        self.esp32: DispositivoESP32 | None = None
        self.tarea_esp32: asyncio.Task | None = None

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
        if self.modo == "simular":
            conexion = "simulado"
        elif self.esp32 and self.esp32.conectado:
            s = self.esp32.saludo
            conexion = {"puerto": s.puerto, "version": s.version, "sensor": s.sensor, "oled": s.oled}
        else:
            conexion = "sin conectar"
        return {"modo": self.modo, "conexion": conexion,
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

    # ------------------------------------------------------------------ modo ESP32
    async def buscar_puertos(self, extra: str | None = None, solo: bool = False) -> None:
        extras = [p for p in {extra, self.cfg.valor("serie.puerto")} if p and p.startswith("socket://")]
        lista = await asyncio.to_thread(esp32.buscar, int(self.cfg.valor("serie.baudios", 921600)), extras,
                                        solo and bool(extras))
        await self.difundir("puertos", {"puertos": lista})

    async def desconectar(self) -> None:
        if self.tarea_esp32 and not self.tarea_esp32.done():
            self.tarea_esp32.cancel()
        if self.esp32:
            await self.esp32.cerrar()
        self.esp32 = None

    async def conectar(self, puerto: str) -> None:
        await self.desconectar()
        c = self.cfg.valor
        disp = DispositivoESP32(puerto, int(c("serie.baudios", 921600)), self.difundir,
                                bool(c("huella.nibble_alto_primero", True)), "as608",
                                int(c("actuadores.ms_entre_servos", 300)), int(c("actuadores.ms_abierto", 8000)))
        try:
            await disp.conectar()
        except ErrorDispositivo as e:
            await self.difundir("error", {"mensaje": str(e), "que_revisar": e.que_revisar})
            return
        self.esp32 = disp
        self.modo = "esp32"
        await self.difundir("estado", self.resumen())
        self.tarea_esp32 = asyncio.create_task(self._ciclo_esp32())

    async def _ciclo_esp32(self) -> None:
        """Cada verificación empieza cuando alguien teclea en la caja."""
        disp = self.esp32
        await disp.mostrar("Listo", "Teclea tu ID")
        while disp.conectado:
            cam = camara_.desde_config(self.cfg)
            try:
                await self.orq.verificar(disp, cam, "esp32")
            finally:
                cam.cerrar()
            await self.difundir("estado", self.resumen())
            if disp.conectado:
                await asyncio.sleep(1.0)
                await disp.mostrar("Listo", "Teclea tu ID")
        await self.difundir("estado", self.resumen())


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
                    if est.modo == "simular":
                        await est.desconectar()
                    await est.difundir("estado", est.resumen())
                elif tipo == "buscar_puertos":
                    await est.buscar_puertos(msg.get("puerto"), bool(msg.get("solo")))
                elif tipo == "conectar":
                    await est.conectar(msg.get("puerto", ""))
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
