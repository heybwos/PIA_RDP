"""Base de datos (SQLite) y archivos de datos/. Esquema de la sección 4.3 del roadmap.

Las imágenes crudas son la fuente de verdad; plantillas, alineados, modelos y vectores son
caché que se puede regenerar.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from . import pin as pin_
from .huella import Minucia, ResultadoHuella
from .rostro import Modelo, ResultadoRostro

VERSION_ESQUEMA = "1"
VERSION_ALGORITMO = "n2-n3-2026-11-13"

ESQUEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usuarios (
  id TEXT PRIMARY KEY CHECK (length(id) = 2), nombre TEXT NOT NULL,
  nivel INTEGER NOT NULL CHECK (nivel IN (1, 2)),
  pin_hash BLOB NOT NULL, pin_sal BLOB NOT NULL, pin_iter INTEGER NOT NULL,
  activo INTEGER NOT NULL DEFAULT 1, creado_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS muestras_huella (
  id INTEGER PRIMARY KEY, usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  fuente TEXT NOT NULL, archivo TEXT NOT NULL, ancho INTEGER NOT NULL, alto INTEGER NOT NULL,
  creada_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plantillas_huella (
  muestra_id INTEGER PRIMARY KEY REFERENCES muestras_huella(id) ON DELETE CASCADE,
  version_algoritmo TEXT NOT NULL, perfil TEXT NOT NULL, n_minucias INTEGER NOT NULL,
  minucias BLOB NOT NULL, calidad REAL NOT NULL, creada_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS muestras_rostro (
  id INTEGER PRIMARY KEY, usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  fuente TEXT NOT NULL, archivo TEXT NOT NULL, archivo_alineado TEXT NOT NULL,
  deteccion TEXT NOT NULL, creada_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS modelos_rostro (
  id INTEGER PRIMARY KEY, dominio TEXT NOT NULL, archivo TEXT NOT NULL,
  k INTEGER NOT NULL, varianza REAL NOT NULL, n_entrenamiento INTEGER NOT NULL,
  activo INTEGER NOT NULL DEFAULT 0, creado_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vectores_rostro (
  muestra_id INTEGER NOT NULL REFERENCES muestras_rostro(id) ON DELETE CASCADE,
  modelo_id INTEGER NOT NULL REFERENCES modelos_rostro(id) ON DELETE CASCADE,
  pesos BLOB NOT NULL, PRIMARY KEY (muestra_id, modelo_id));
CREATE TABLE IF NOT EXISTS calibraciones (
  id INTEGER PRIMARY KEY, factor TEXT NOT NULL, dominio TEXT NOT NULL,
  umbral REAL NOT NULL, eer REAL, far REAL, frr REAL, n_genuinos INTEGER, n_impostores INTEGER,
  modelo_id INTEGER REFERENCES modelos_rostro(id), parametros TEXT,
  activa INTEGER NOT NULL DEFAULT 0, creada_en TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bitacora (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, modo TEXT NOT NULL,
  usuario_id TEXT, nombre TEXT, pin_ok INTEGER NOT NULL,
  fuente_huella TEXT, fuente_rostro TEXT, puntaje_huella REAL, huella_norm REAL,
  distancia_rostro REAL, rostro_norm REAL, fusion REAL,
  decision INTEGER NOT NULL, motivo TEXT, duracion_ms INTEGER,
  archivo_huella TEXT, archivo_rostro TEXT);
CREATE INDEX IF NOT EXISTS bitacora_fecha ON bitacora(fecha);
"""

TIPOS = {"T": 0.0, "B": 1.0}


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def dominio_rostro(fuente: str) -> str:
    """camara -> camara; orl, sintetico y demás datasets -> dataset."""
    return "camara" if fuente == "camara" else "dataset"


def minucias_a_blob(ms: list[Minucia]) -> bytes:
    return np.array([[m.x, m.y, m.t, TIPOS[m.tipo]] for m in ms], np.float32).reshape(-1, 4).tobytes()


def blob_a_minucias(b: bytes) -> list[Minucia]:
    a = np.frombuffer(b, np.float32).reshape(-1, 4)
    return [Minucia(int(x), int(y), float(t), "B" if k >= 0.5 else "T") for x, y, t, k in a]


def guardar_png(ruta: Path, img: np.ndarray) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise IOError(f"No se pudo codificar {ruta}")
    buf.tofile(str(ruta))


def leer_png(ruta: Path, color: bool = False) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(str(ruta), np.uint8), cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise IOError(f"No se pudo leer {ruta}")
    return img


class Almacen:
    def __init__(self, carpeta: str | Path):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.carpeta / "pia.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)
        self.db.execute("PRAGMA foreign_keys = ON")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
            self.db.execute("INSERT OR REPLACE INTO meta VALUES ('version_algoritmo', ?)", (VERSION_ALGORITMO,))
        self._modelos: dict[int, Modelo] = {}

    def cerrar(self) -> None:
        self.db.close()

    def ruta(self, relativa: str) -> Path:
        return self.carpeta / relativa

    def _sql(self, consulta: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.db.execute(consulta, args).fetchall()

    def _escribir(self, consulta: str, args: tuple = ()) -> int:
        with self._lock, self.db:
            return self.db.execute(consulta, args).lastrowid

    # ------------------------------------------------------------------ usuarios
    def crear_usuario(self, id_: str, nombre: str, nivel: int, pin: str) -> None:
        if not (len(id_) == 2 and id_.isdigit()):
            raise ValueError("El ID es de 2 dígitos")
        if self.usuario(id_):
            raise ValueError(f"El ID {id_} ya existe")
        h, s, it = pin_.hashear(pin)
        self._escribir("INSERT INTO usuarios (id, nombre, nivel, pin_hash, pin_sal, pin_iter, creado_en) "
                       "VALUES (?,?,?,?,?,?,?)", (id_, nombre, nivel, h, s, it, ahora()))

    def usuario(self, id_: str) -> dict | None:
        r = self._sql("SELECT id, nombre, nivel FROM usuarios WHERE id = ? AND activo = 1", (id_,))
        return dict(r[0]) if r else None

    def usuarios(self) -> list[dict]:
        return [dict(r) for r in self._sql("SELECT id, nombre, nivel FROM usuarios WHERE activo = 1 ORDER BY id")]

    def verificar_pin(self, id_: str, pin: str) -> bool:
        r = self._sql("SELECT pin_hash, pin_sal, pin_iter FROM usuarios WHERE id = ? AND activo = 1", (id_,))
        return bool(r) and pin_.verificar(pin, r[0]["pin_hash"], r[0]["pin_sal"], r[0]["pin_iter"])

    def borrar_usuario(self, id_: str) -> None:
        self._escribir("DELETE FROM usuarios WHERE id = ?", (id_,))
        shutil.rmtree(self.carpeta / "usuarios" / id_, ignore_errors=True)

    # ------------------------------------------------------------------ huella
    def agregar_huella(self, id_: str, img: np.ndarray, fuente: str, r: ResultadoHuella, perfil: str) -> int:
        n = len(self._sql("SELECT id FROM muestras_huella WHERE usuario_id = ? AND fuente = ?", (id_, fuente)))
        rel = f"usuarios/{id_}/huellas/{fuente}_{n + 1:02d}.png"
        guardar_png(self.ruta(rel), img)
        mid = self._escribir("INSERT INTO muestras_huella (usuario_id, fuente, archivo, ancho, alto, creada_en) "
                             "VALUES (?,?,?,?,?,?)", (id_, fuente, rel, img.shape[1], img.shape[0], ahora()))
        self._escribir("INSERT INTO plantillas_huella VALUES (?,?,?,?,?,?,?)",
                       (mid, VERSION_ALGORITMO, perfil, len(r.minucias), minucias_a_blob(r.minucias),
                        r.calidad, ahora()))
        return mid

    def plantillas(self, id_: str, fuentes: list[str] | None = None) -> list[dict]:
        filas = self._sql(
            "SELECT m.id, m.fuente, m.archivo, p.minucias, p.perfil FROM muestras_huella m "
            "JOIN plantillas_huella p ON p.muestra_id = m.id WHERE m.usuario_id = ? ORDER BY m.id", (id_,))
        return [{"muestra_id": f["id"], "fuente": f["fuente"], "archivo": f["archivo"], "perfil": f["perfil"],
                 "minucias": blob_a_minucias(f["minucias"])}
                for f in filas if fuentes is None or f["fuente"] in fuentes]

    # ------------------------------------------------------------------ rostro
    def agregar_rostro(self, id_: str, cuadro: np.ndarray, fuente: str, r: ResultadoRostro) -> int:
        n = len(self._sql("SELECT id FROM muestras_rostro WHERE usuario_id = ? AND fuente = ?", (id_, fuente)))
        rel = f"usuarios/{id_}/rostros/{fuente}_{n + 1:02d}.png"
        rel_al = f"usuarios/{id_}/rostros/alineados/{fuente}_{n + 1:02d}.png"
        guardar_png(self.ruta(rel), cuadro)
        guardar_png(self.ruta(rel_al), (r.normalizada.imagen * 255).round().astype(np.uint8))
        det = {"rostro": r.deteccion.rostro, "ojos": r.deteccion.ojos, "alineacion": r.alineado.metodo,
               "con_relleno": r.deteccion.con_relleno}
        return self._escribir("INSERT INTO muestras_rostro (usuario_id, fuente, archivo, archivo_alineado, "
                              "deteccion, creada_en) VALUES (?,?,?,?,?,?)",
                              (id_, fuente, rel, rel_al, json.dumps(det), ahora()))

    def muestras_rostro(self, dominio: str | None = None, id_: str | None = None) -> list[dict]:
        filas = [dict(f) for f in self._sql("SELECT * FROM muestras_rostro ORDER BY id")]
        return [f for f in filas
                if (dominio is None or dominio_rostro(f["fuente"]) == dominio) and (id_ is None or f["usuario_id"] == id_)]

    def cara_normalizada(self, muestra: dict) -> np.ndarray:
        return leer_png(self.ruta(muestra["archivo_alineado"])).astype(np.float32) / 255.0

    # ------------------------------------------------------------------ modelos
    def guardar_modelo(self, dominio: str, modelo: Modelo, n: int) -> int:
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        rel = f"modelos/eigenfaces_{dominio}_{fecha}.npz"
        self.ruta(rel).parent.mkdir(parents=True, exist_ok=True)
        modelo.guardar(self.ruta(rel))
        with self._lock, self.db:
            self.db.execute("UPDATE modelos_rostro SET activo = 0 WHERE dominio = ?", (dominio,))
            mid = self.db.execute("INSERT INTO modelos_rostro (dominio, archivo, k, varianza, n_entrenamiento, "
                                  "activo, creado_en) VALUES (?,?,?,?,?,1,?)",
                                  (dominio, rel, modelo.k, modelo.varianza_explicada, n, ahora())).lastrowid
        self._modelos[mid] = modelo
        return mid

    def modelo_activo(self, dominio: str) -> tuple[int, Modelo] | None:
        r = self._sql("SELECT id, archivo FROM modelos_rostro WHERE dominio = ? AND activo = 1", (dominio,))
        if not r:
            return None
        mid = r[0]["id"]
        if mid not in self._modelos:
            self._modelos[mid] = Modelo.cargar(self.ruta(r[0]["archivo"]))
        return mid, self._modelos[mid]

    def guardar_vectores(self, modelo_id: int, vectores: dict[int, np.ndarray]) -> None:
        with self._lock, self.db:
            self.db.executemany("INSERT OR REPLACE INTO vectores_rostro VALUES (?,?,?)",
                                [(m, modelo_id, np.asarray(p, np.float32).tobytes()) for m, p in vectores.items()])

    def vectores(self, id_: str, modelo_id: int) -> np.ndarray:
        filas = self._sql("SELECT v.pesos FROM vectores_rostro v JOIN muestras_rostro m ON m.id = v.muestra_id "
                          "WHERE m.usuario_id = ? AND v.modelo_id = ?", (id_, modelo_id))
        return np.array([np.frombuffer(f["pesos"], np.float32) for f in filas])

    # ------------------------------------------------------------------ calibración
    def guardar_calibracion(self, factor: str, dominio: str, umbral: float, eer: float | None = None,
                            far: float | None = None, frr: float | None = None, n_genuinos: int | None = None,
                            n_impostores: int | None = None, modelo_id: int | None = None,
                            parametros: dict | None = None) -> int:
        with self._lock, self.db:
            self.db.execute("UPDATE calibraciones SET activa = 0 WHERE factor = ? AND dominio = ?", (factor, dominio))
            return self.db.execute(
                "INSERT INTO calibraciones (factor, dominio, umbral, eer, far, frr, n_genuinos, n_impostores, "
                "modelo_id, parametros, activa, creada_en) VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
                (factor, dominio, umbral, eer, far, frr, n_genuinos, n_impostores, modelo_id,
                 json.dumps(parametros or {}), ahora())).lastrowid

    def calibracion_activa(self, factor: str, dominio: str) -> dict | None:
        r = self._sql("SELECT * FROM calibraciones WHERE factor = ? AND dominio = ? AND activa = 1", (factor, dominio))
        return dict(r[0]) if r else None

    # ------------------------------------------------------------------ bitácora
    def agregar_bitacora(self, fila: dict[str, Any]) -> dict:
        fila = {"fecha": ahora(), **fila}
        cols = ", ".join(fila)
        marcas = ", ".join("?" for _ in fila)
        fid = self._escribir(f"INSERT INTO bitacora ({cols}) VALUES ({marcas})", tuple(fila.values()))
        return {"id": fid, **fila}

    def bitacora(self, limite: int = 50) -> list[dict]:
        return [dict(f) for f in self._sql("SELECT * FROM bitacora ORDER BY id DESC LIMIT ?", (limite,))]
