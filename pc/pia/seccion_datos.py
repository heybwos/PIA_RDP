"""Sección Datos de la app (app/datos.html): consulta de lo registrado, solo lectura.

Todo sale de datos/ y de la base; nada se escribe. Las imágenes que no existen como archivo
(eigenfaces, cara media, reconstrucciones) las calcula Python y la app solo las muestra.

    GET /api/datos                                     resumen: usuarios, modelos, calibraciones, banco
    GET /api/datos/huella/{muestra}.png                huella registrada (cruda)
    GET /api/datos/huella/{muestra}/minucias           [{x, y, t, tipo}] de su plantilla
    GET /api/datos/rostro/{muestra}.png?alineado=1     cuadro de la cámara o cara alineada (64 x 64)
    GET /api/datos/rostro/{muestra}/reconstruccion.png?k=N
    GET /api/datos/modelo/{dominio}/media.png
    GET /api/datos/modelo/{dominio}/eigenface/{i}.png
    GET /api/datos/tanda2/{id}/{archivo}               segunda tanda de rostro (calibración)
    GET /api/datos/banco/{identidad}/{archivo}         banco de huellas del AS608 (calibración)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from .almacen import Almacen, dominio_rostro

NOMBRE = re.compile(r"[\w\-]+")
ARCHIVO = re.compile(r"[\w\-]+\.png")
EIGENFACES_MAX = 16


def _png(img: np.ndarray) -> Response:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(500, "No se pudo codificar la imagen")
    return Response(buf.tobytes(), media_type="image/png")


def _a_gris(v: np.ndarray, lado: int, estirar: bool = False) -> np.ndarray:
    """Vector de una cara -> imagen de 8 bits. estirar: min-max (eigenfaces, que tienen signo)."""
    v = np.asarray(v, np.float64).reshape(lado, lado)
    if estirar:
        v = (v - v.min()) / ((v.max() - v.min()) or 1.0)
    return (np.clip(v, 0, 1) * 255).round().astype(np.uint8)


def _imagenes(carpeta: Path) -> list[str]:
    return sorted(f.name for f in carpeta.glob("*.png")) if carpeta.is_dir() else []


def _archivo_seguro(base: Path, carpeta: str, archivo: str) -> Path:
    """Solo nombres simples dentro de base: nada de rutas ni '..'."""
    if not (NOMBRE.fullmatch(carpeta) and ARCHIVO.fullmatch(archivo)):
        raise HTTPException(404, "No existe")
    ruta = base / carpeta / archivo
    if not ruta.is_file():
        raise HTTPException(404, "No existe")
    return ruta


def resumen(alm: Almacen) -> dict:
    rostros = alm.muestras_rostro()
    tandas = alm.carpeta / "rostros_tanda2"
    usuarios = []
    for u in alm.usuarios_con_fecha():
        huellas = [{k: h[k] for k in ("id", "fuente", "ancho", "alto", "creada_en", "perfil", "n_minucias", "calidad")}
                   for h in alm.muestras_huella(u["id"])]
        caras = [{"id": r["id"], "fuente": r["fuente"], "dominio": dominio_rostro(r["fuente"]),
                  "creada_en": r["creada_en"], "alineacion": json.loads(r["deteccion"]).get("alineacion")}
                 for r in rostros if r["usuario_id"] == u["id"]]
        reales = any(h["fuente"] == "as608" for h in huellas) or any(c["fuente"] == "camara" for c in caras)
        usuarios.append({**u, "de_prueba": not reales, "huellas": huellas, "rostros": caras,
                         "tanda2": _imagenes(tandas / u["id"])})

    modelos = []
    for m in alm.modelos_activos():
        act = alm.modelo_activo(m["dominio"])
        if not act:
            continue
        modelo = act[1]
        acumulada = np.cumsum(modelo.valores) / modelo.valores.sum() * modelo.varianza_explicada
        modelos.append({**m, "lado": modelo.lado, "eigenfaces": min(EIGENFACES_MAX, modelo.k),
                        "acumulada": [round(float(a), 4) for a in acumulada]})

    calibraciones = []
    for c in alm.calibraciones_activas():
        p = json.loads(c["parametros"] or "{}")
        calibraciones.append({
            **{k: c[k] for k in ("factor", "dominio", "umbral", "eer", "far", "frr", "n_genuinos", "n_impostores",
                                 "creada_en")},
            "criterio": p.get("criterio", "eer"), "umbral_eer": p.get("umbral_eer"),
            "mayor_es_mejor": c["factor"] == "huella", "distribucion": p.get("distribucion")})

    banco_dir = alm.carpeta / "banco_as608"
    banco = [{"identidad": d.name, "archivos": _imagenes(d)}
             for d in sorted(banco_dir.iterdir()) if d.is_dir()] if banco_dir.is_dir() else []
    return {"usuarios": usuarios, "modelos": modelos, "calibraciones": calibraciones, "banco": banco}


def router(alm: Almacen) -> APIRouter:
    r = APIRouter(prefix="/api/datos")

    def muestra_rostro(mid: int) -> dict:
        m = next((x for x in alm.muestras_rostro() if x["id"] == mid), None)
        if not m:
            raise HTTPException(404, f"No existe la muestra de rostro {mid}")
        return m

    def modelo(dominio: str):
        act = alm.modelo_activo(dominio) if dominio in ("camara", "dataset") else None
        if not act:
            raise HTTPException(404, f"No hay modelo de rostro '{dominio}'")
        return act[1]

    @r.get("")
    def datos():
        return resumen(alm)

    @r.get("/huella/{mid}.png")
    def huella(mid: int):
        m = alm.muestras_huella(muestra_id=mid)
        if not m:
            raise HTTPException(404, f"No existe la huella {mid}")
        return FileResponse(alm.ruta(m[0]["archivo"]), media_type="image/png")

    @r.get("/huella/{mid}/minucias")
    def minucias(mid: int):
        if not alm.muestras_huella(muestra_id=mid):
            raise HTTPException(404, f"No existe la huella {mid}")
        return [{"x": m.x, "y": m.y, "t": round(m.t, 4), "tipo": m.tipo} for m in alm.minucias_de(mid)]

    @r.get("/rostro/{mid}.png")
    def rostro(mid: int, alineado: int = 0):
        m = muestra_rostro(mid)
        return FileResponse(alm.ruta(m["archivo_alineado"] if alineado else m["archivo"]), media_type="image/png")

    @r.get("/rostro/{mid}/reconstruccion.png")
    def reconstruccion(mid: int, k: int | None = None):
        m = muestra_rostro(mid)
        mod = modelo(dominio_rostro(m["fuente"]))
        pesos = mod.proyectar(alm.cara_normalizada(m))
        c = mod.k if k is None else max(1, min(mod.k, k))
        return _png(_a_gris(mod.reconstruir(pesos, c), mod.lado))

    @r.get("/modelo/{dominio}/media.png")
    def media(dominio: str):
        mod = modelo(dominio)
        return _png(_a_gris(mod.media, mod.lado))

    @r.get("/modelo/{dominio}/eigenface/{i}.png")
    def eigenface(dominio: str, i: int):
        mod = modelo(dominio)
        if not 0 <= i < mod.k:
            raise HTTPException(404, f"El modelo tiene {mod.k} eigenfaces")
        return _png(_a_gris(mod.eigenfaces[i], mod.lado, estirar=True))

    @r.get("/tanda2/{id_}/{archivo}")
    def tanda2(id_: str, archivo: str):
        return FileResponse(_archivo_seguro(alm.carpeta / "rostros_tanda2", id_, archivo), media_type="image/png")

    @r.get("/banco/{identidad}/{archivo}")
    def banco(identidad: str, archivo: str):
        return FileResponse(_archivo_seguro(alm.carpeta / "banco_as608", identidad, archivo), media_type="image/png")

    return r
