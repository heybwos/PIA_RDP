"""Máquina de estados de una verificación: PIN -> huella -> rostro -> decisión.

Emite los eventos de docs/EVENTOS.md en el mismo orden que los pasos de run() en la
maqueta. El backend manda rápido; la app anima a su ritmo. El cálculo pesado corre en un
hilo (asyncio.to_thread) para no trabar el WebSocket.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from . import fusion, huella, rostro
from .almacen import Almacen, dominio_rostro, guardar_png
from .camara import Camara, CamaraError
from .config import Config
from .dispositivos.base import Dispositivo, Emisor, imagen_json, _nada

PASOS_RECONSTRUCCION = (1, 5, 10, 20)
N_EIGENFACES_VISTA = 8


@dataclass
class Resultado:
    concedido: bool
    nivel: int
    motivo: str
    fila: dict


class ErrorVerificacion(Exception):
    def __init__(self, mensaje: str, que_revisar: str = ""):
        super().__init__(mensaje)
        self.que_revisar = que_revisar


class Orquestador:
    def __init__(self, alm: Almacen, cfg: Config, emitir: Emisor | None = None):
        self.alm, self.cfg = alm, cfg
        self.emitir: Emisor = emitir or _nada
        self._modelos_enviados: set[int] = set()

    async def _etapa(self, n: int, estado: str, dato: str = "") -> None:
        await self.emitir("etapa", {"n": n, "estado": estado, "dato": dato})

    async def verificar(self, disp: Dispositivo, camara: Camara, modo: str = "simular") -> Resultado:
        disp.emitir = self.emitir
        t0 = time.perf_counter()
        fila: dict[str, Any] = {"modo": modo, "pin_ok": 0, "decision": 0}
        try:
            return await self._verificar(disp, camara, fila, t0)
        except (ErrorVerificacion, CamaraError) as e:
            await self.emitir("error", {"mensaje": str(e), "que_revisar": getattr(e, "que_revisar", "")})
            fila.update(decision=0, motivo=f"error: {e}")
            return await self._cerrar(disp, fila, t0, fusion.Decision(False, 0, 0, 0, 0, f"error: {e}"))

    async def _verificar(self, disp: Dispositivo, camara: Camara, fila: dict, t0: float) -> Resultado:
        # ---------------------------------------------------------------- 1. PIN
        await self._etapa(1, "curso")
        id_, pin = await disp.leer_pin()
        usuario = self.alm.usuario(id_)
        fila.update(usuario_id=id_, nombre=usuario["nombre"] if usuario else None)
        pin_ok = usuario is not None and await asyncio.to_thread(self.alm.verificar_pin, id_, pin)
        fila["pin_ok"] = int(pin_ok)
        if not pin_ok:
            motivo = "PIN incorrecto" if usuario else "ID no registrado"
            await self._etapa(1, "no", motivo)
            await self._etapa(2, "omit")
            await self._etapa(3, "omit")
            return await self._cerrar(disp, fila, t0, fusion.Decision(False, 0, 0, 0, 0, motivo))
        await self._etapa(1, "ok", f"ID {id_}")

        # ---------------------------------------------------------------- 2. Huella
        await self._etapa(2, "curso")
        img, fuente_h = await disp.capturar_huella()
        fila["fuente_huella"] = fuente_h
        cal_h = self.alm.calibracion_activa("huella", fuente_h)
        if not cal_h:
            raise ErrorVerificacion(f"No hay calibración de huella para '{fuente_h}'",
                                    "Corre pc/scripts/sembrar_simular.py o calibrar.py")
        plantillas = self.alm.plantillas(id_, [fuente_h])
        if not plantillas:
            raise ErrorVerificacion(f"El usuario {id_} no tiene huellas de '{fuente_h}'",
                                    "Regístralo con huellas de esa fuente")
        r_h = await asyncio.to_thread(huella.procesar, img, fuente_h)
        await self._emitir_huella(r_h)
        mejor, mejor_p = None, None
        for p in plantillas:
            m = await asyncio.to_thread(huella.comparar, p["minucias"], r_h.minucias)
            if mejor is None or m.puntaje > mejor.puntaje:
                mejor, mejor_p = m, p
        umbral_h = cal_h["umbral"]
        await self.emitir("huella_matching", {
            "puntaje": mejor.puntaje, "umbral": umbral_h, "pares": mejor.pares,
            "aristas_a": mejor.aristas_a, "aristas_b": mejor.aristas_b, "muestra_id": mejor_p["muestra_id"],
            "plantilla": {"minucias": [m.como_dict() for m in mejor_p["minucias"]]},
        })
        fila["puntaje_huella"] = mejor.puntaje
        await self._etapa(2, "ok" if mejor.puntaje >= umbral_h else "no", f"{mejor.puntaje:.2f}")

        # ---------------------------------------------------------------- 3. Rostro
        await self._etapa(3, "curso")
        await disp.mostrar("Mira a la", "camara")
        cuadro = await asyncio.to_thread(camara.capturar)
        fuente_r = camara.fuente
        dom = dominio_rostro(fuente_r)
        fila["fuente_rostro"] = fuente_r
        activo = self.alm.modelo_activo(dom)
        cal_r = self.alm.calibracion_activa("rostro", dom)
        if not activo or not cal_r:
            raise ErrorVerificacion(f"No hay modelo o calibración de rostro para '{dom}'",
                                    "Registra usuarios con rostro de esa fuente y calibra")
        mid, modelo = activo
        r_r = await asyncio.to_thread(rostro.procesar, cuadro, modelo, fuente_r != "camara")
        await self._emitir_rostro(cuadro, r_r, mid, modelo, fuente_r)
        if not r_r.hay_rostro:
            raise ErrorVerificacion("No se detectó un rostro", "Mira de frente a la cámara, con buena luz")
        vect = self.alm.vectores(id_, mid)
        if len(vect) == 0:
            raise ErrorVerificacion(f"El usuario {id_} no tiene vectores en el modelo de '{dom}'",
                                    "Regístralo con rostro de esa fuente")
        d, _ = rostro.comparar(r_r.pesos, vect, cal_r["umbral"])
        await self.emitir("rostro_distancia", {"distancia": d, "umbral": cal_r["umbral"],
                                               "distancia_espacio": r_r.distancia_espacio})
        fila["distancia_rostro"] = d
        await self._etapa(3, "ok" if d < cal_r["umbral"] else "no", f"d {d:.2f}")

        # ---------------------------------------------------------------- 4. Decisión
        dc = self.cfg.valor
        s_h = fusion.normalizar_huella(mejor.puntaje, umbral_h)
        s_r = fusion.normalizar_rostro(d, cal_r["umbral"])
        dec = fusion.decidir(usuario["nivel"], s_h, s_r, dc("decision.peso_huella", 0.5), dc("decision.peso_rostro", 0.5),
                             dc("decision.umbral_factor", 0.5), dc("decision.umbral_fusion", 0.6))
        await self.emitir("fusion", {"huella": s_h, "rostro": s_r, "fusion": dec.fusion,
                                     "pesos": {"huella": dc("decision.peso_huella", 0.5),
                                               "rostro": dc("decision.peso_rostro", 0.5)},
                                     "umbral_factor": dc("decision.umbral_factor", 0.5),
                                     "umbral_fusion": dc("decision.umbral_fusion", 0.6)})
        fila.update(huella_norm=s_h, rostro_norm=s_r, fusion=dec.fusion)
        if dc("datos.guardar_intentos", True):
            fila.update(self._guardar_intento(id_, img, cuadro))
        return await self._cerrar(disp, fila, t0, dec)

    async def _cerrar(self, disp: Dispositivo, fila: dict, t0: float, dec: fusion.Decision) -> Resultado:
        await self._etapa(4, "curso")
        fila.update(decision=dec.nivel if dec.concedido else 0, motivo=dec.motivo or None,
                    duracion_ms=int((time.perf_counter() - t0) * 1000))
        await self.emitir("veredicto", {"concedido": dec.concedido, "nivel": dec.nivel, "motivo": dec.motivo})
        if dec.concedido:
            await disp.mostrar("Acceso concedido", f"Nivel {dec.nivel}")
        else:
            await disp.mostrar("Acceso negado", dec.motivo[:16])
        await disp.actuar(dec.nivel if dec.concedido else 0)
        guardada = self.alm.agregar_bitacora(fila)
        await self.emitir("bitacora_fila", guardada)
        await self._etapa(4, "ok" if dec.concedido else "no", f"Nivel {dec.nivel}" if dec.concedido else "Negado")
        return Resultado(dec.concedido, dec.nivel, dec.motivo, guardada)

    async def _emitir_huella(self, r: huella.ResultadoHuella) -> None:
        e = r.etapas
        await self.emitir("huella_etapa", {"nombre": "normalizada", "imagen": imagen_json(e["normalizada"])})
        await self.emitir("huella_etapa", {"nombre": "segmentacion", "imagen": imagen_json(e["segmentacion"] * 255)})
        await self.emitir("huella_etapa", {
            "nombre": "orientacion", "bloque": r.pre.mascara.shape[0] // r.pre.mascara_bloques.shape[0],
            "angulos": imagen_json(r.pre.orientacion_bloques), "coherencia": imagen_json(r.pre.coherencia),
            "mascara": imagen_json(r.pre.mascara_bloques * 255)})
        await self.emitir("huella_etapa", {"nombre": "gabor", "imagen": imagen_json(e["gabor"])})
        await self.emitir("huella_etapa", {"nombre": "binaria", "imagen": imagen_json(e["binaria"] * 255)})
        await self.emitir("huella_etapa", {"nombre": "esqueleto", "imagen": imagen_json(e["esqueleto"] * 255)})
        await self.emitir("huella_minucias", {"minucias": [m.como_dict() for m in r.minucias], "calidad": r.calidad})

    async def _emitir_rostro(self, cuadro: np.ndarray, r: rostro.ResultadoRostro, mid: int,
                             modelo: rostro.Modelo, fuente: str) -> None:
        await self.emitir("rostro_cuadro", {"imagen": imagen_json(rostro.a_gris(cuadro)), "fuente": fuente})
        await self.emitir("rostro_deteccion", {"rostro": r.deteccion.rostro, "ojos": r.deteccion.ojos,
                                               "con_relleno": r.deteccion.con_relleno})
        await self.emitir("rostro_alineado", {"imagen": imagen_json(r.alineado.imagen), "metodo": r.alineado.metodo,
                                              "angulo": r.alineado.angulo_grados})
        await self.emitir("rostro_normalizado", {"imagen": imagen_json(r.normalizada.imagen),
                                                 "hist_antes": r.normalizada.hist_antes.tolist(),
                                                 "hist_despues": r.normalizada.hist_despues.tolist()})
        if mid not in self._modelos_enviados:
            lado = modelo.lado
            await self.emitir("rostro_pca", {
                "modelo_id": mid, "k": modelo.k, "varianza": modelo.varianza_explicada,
                "media": imagen_json(modelo.media.reshape(lado, lado)),
                "eigenfaces": [imagen_json(u.reshape(lado, lado)) for u in modelo.eigenfaces[:N_EIGENFACES_VISTA]]})
            self._modelos_enviados.add(mid)
        if r.pesos is not None:
            await self.emitir("rostro_pesos", {"pesos": r.pesos.tolist()})
            pasos = sorted({c for c in PASOS_RECONSTRUCCION if c < modelo.k} | {modelo.k})
            await self.emitir("rostro_reconstruccion", {"pasos": [
                {"componentes": c, "imagen": imagen_json(modelo.reconstruir(r.pesos, c).reshape(modelo.lado, modelo.lado))}
                for c in pasos]})

    def _guardar_intento(self, id_: str, img: np.ndarray, cuadro: np.ndarray) -> dict:
        ahora = datetime.now()
        base = f"intentos/{ahora:%Y%m%d}/{ahora:%H%M%S_%f}_{id_}"
        guardar_png(self.alm.ruta(base + "_huella.png"), img)
        guardar_png(self.alm.ruta(base + "_rostro.png"), cuadro)
        return {"archivo_huella": base + "_huella.png", "archivo_rostro": base + "_rostro.png"}
