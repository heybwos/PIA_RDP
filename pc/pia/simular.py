"""Modo Simular: usuarios de prueba, calibración de los dominios de dataset y escenarios.

Huella: FVC2002 DB1_B (10 dedos x 8 impresiones; 1 a 5 para registrar, 6 a 8 para
verificar). Rostro: ORL (40 personas x 10; 1 a 6 para registrar, 7 a 10 para verificar).
Los usuarios y escenarios son los de la maqueta (docs/ESTADO_DEL_PROYECTO.md).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import calibracion, huella, registro, rostro
from .almacen import Almacen
from .camara import CamaraArchivo
from .dispositivos import DispositivoSimulado
from .rostro.eigenfaces import distancia_minima

DB_HUELLA = "DB1_B"
FUENTE_HUELLA = "fvc2002"

# id, nombre, nivel, PIN, dedo FVC2002, persona ORL
USUARIOS = [
    ("07", "Ana T.", 1, "4821", 103, 3),
    ("12", "Luis G.", 2, "1593", 107, 7),
]

# clave: (nombre, id tecleado, PIN tecleado, dedo, impresión, persona ORL, imagen, esperado)
# Imágenes de prueba elegidas por margen contra el umbral de rostro (13 de noviembre, umbral 8.76):
# persona 3, imágenes 7 a 10: d = 8.29, 8.25, 8.46, 7.53 -> la 10. Persona 7: 4.43, 8.62, 4.14, 6.58.
# Persona 20 contra el usuario 07: 9.93, 10.92, 9.78, 12.41. Con otras imágenes la persona 3
# puede caer del lado equivocado: es la tasa de error real de Eigenfaces en ORL (EER ~8 %).
ESCENARIOS = {
    "l1": ("Usuario legítimo de nivel 1", "07", "4821", 103, 6, 3, 10, "Concedido, nivel 1"),
    "l2": ("Usuario legítimo de nivel 2", "12", "1593", 107, 6, 7, 7, "Concedido, nivel 2"),
    "ih": ("Impostor de huella", "12", "1593", 101, 6, 7, 9, "Negado"),
    "ir": ("Impostor de rostro", "07", "4821", 103, 7, 20, 8, "Negado"),
    "pin": ("PIN incorrecto", "07", "4812", 103, 6, 3, 10, "Negado"),
}


def ruta_huella(datasets: Path, dedo: int, imp: int) -> Path:
    return datasets / "fvc2002" / DB_HUELLA / f"{dedo}_{imp}.tif"


def ruta_rostro(datasets: Path, persona: int, img: int) -> Path:
    return datasets / "orl" / f"s{persona}" / f"{img}.pgm"


def _gris(ruta: Path) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(str(ruta), np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Falta {ruta}. Corre: python pc/scripts/descargar_datasets.py")
    return img


def calibrar_huella_dataset(alm: Almacen, datasets: Path) -> calibracion.Resultado:
    carpeta = datasets / "fvc2002" / DB_HUELLA
    res = {f.stem: huella.procesar(_gris(f), FUENTE_HUELLA) for f in sorted(carpeta.glob("*.tif"))}
    dedos = sorted({k.split("_")[0] for k in res})
    gen, imp = [], []
    for a in dedos:
        tpls = [res[f"{a}_{j}"] for j in range(1, 6)]
        for b in dedos:
            for j in range(6, 9):
                s = max(huella.comparar(t, res[f"{b}_{j}"]).puntaje for t in tpls)
                (gen if a == b else imp).append(s)
    r = calibracion.por_eer(gen, imp, mayor_es_mejor=True)
    alm.guardar_calibracion("huella", FUENTE_HUELLA, r.umbral, r.eer, r.far, r.frr, r.n_genuinos, r.n_impostores,
                            parametros={"perfil": FUENTE_HUELLA, "base": DB_HUELLA, "registro": "1-5", "prueba": "6-8",
                                        "distribucion": calibracion.distribucion(gen, imp)})
    return r


def calibrar_rostro_dataset(alm: Almacen, datasets: Path) -> calibracion.Resultado:
    mid, modelo = alm.modelo_activo("dataset")
    vect, pruebas = {}, {}
    for p in range(1, 41):
        caras = [rostro.procesar(_gris(ruta_rostro(datasets, p, j))) for j in range(1, 11)]
        vect[p] = modelo.proyectar(np.array([c.vector for c in caras[:6]]))
        pruebas[p] = [modelo.proyectar(c.vector) for c in caras[6:]]
    gen, imp = [], []
    for p, ws in pruebas.items():
        for w in ws:
            for q, vs in vect.items():
                (gen if p == q else imp).append(distancia_minima(w, vs))
    r = calibracion.por_eer(gen, imp, mayor_es_mejor=False)
    alm.guardar_calibracion("rostro", "dataset", r.umbral, r.eer, r.far, r.frr, r.n_genuinos, r.n_impostores,
                            modelo_id=mid, parametros={"dataset": "orl", "registro": "1-6", "prueba": "7-10",
                                                       "distribucion": calibracion.distribucion(gen, imp)})
    return r


def sembrar(alm: Almacen, datasets: Path, imprimir=print) -> dict:
    personas_usadas = {u[5] for u in USUARIOS} | {e[5] for e in ESCENARIOS.values()}
    fondo = registro.caras_de_fondo(datasets / "orl", excluir=personas_usadas)
    imprimir(f"Fondo del modelo de rostro: {len(fondo)} caras de ORL")
    for id_, nombre, nivel, pin, dedo, persona in USUARIOS:
        if alm.usuario(id_):
            alm.borrar_usuario(id_)
        huellas = [(_gris(ruta_huella(datasets, dedo, j)), FUENTE_HUELLA) for j in range(1, 6)]
        caras = [(_gris(ruta_rostro(datasets, persona, j)), "orl") for j in range(1, 7)]
        inf = registro.registrar(alm, id_, nombre, nivel, pin, huellas, caras, fondo=fondo, reentrenar_modelo=False)
        imprimir(f"Usuario {id_} {nombre}: {inf.huellas_ok} huellas, {inf.rostros_ok} rostros"
                 + (f" (rechazadas: {inf.huellas_rechazadas})" if inf.huellas_rechazadas else ""))
    mid = registro.reentrenar(alm, "dataset", fondo)
    imprimir(f"Modelo de rostro 'dataset' #{mid}: k = {alm.modelo_activo('dataset')[1].k}")
    rh = calibrar_huella_dataset(alm, datasets)
    imprimir(f"Calibración huella fvc2002: umbral {rh.umbral:.3f}, EER {rh.eer:.1%}")
    rr = calibrar_rostro_dataset(alm, datasets)
    imprimir(f"Calibración rostro dataset: umbral {rr.umbral:.2f}, EER {rr.eer:.1%}")
    esc = escenarios(datasets)
    (alm.carpeta / "escenarios.json").write_text(json.dumps(esc, ensure_ascii=False, indent=2), "utf-8")
    return esc


def sembrar_prueba_esp32(alm: Almacen, datasets: Path, fixtures: Path) -> dict:
    """SOLO para pruebas con el ESP32 falso, en una carpeta de datos aparte (nunca en datos/):
    usuario 21 (nivel 2, PIN 2468) con huellas sintéticas en formato AS608 y rostro de ORL s5,
    y calibración 'as608' sacada del banco sintético. La calibración real del AS608 es de N7."""
    if not alm.modelo_activo("dataset"):
        sembrar(alm, datasets, imprimir=lambda *_: None)
    if alm.usuario("21"):
        alm.borrar_usuario("21")
    huellas = [(huella.leer(fixtures / f"id01_imp{k}.bin"), "as608") for k in range(3)]
    caras = [(_gris(ruta_rostro(datasets, 5, j)), "orl") for j in range(1, 7)]
    registro.registrar(alm, "21", "Prueba ESP32", 2, "2468", huellas, caras, reentrenar_modelo=False)
    fondo = registro.caras_de_fondo(datasets / "orl", excluir={u[5] for u in USUARIOS} | {5, 20})
    registro.reentrenar(alm, "dataset", fondo)
    calibrar_rostro_dataset(alm, datasets)
    res = {f.stem: huella.procesar(huella.leer(f), "as608") for f in sorted(fixtures.glob("*.bin"))}
    gen, imp = [], []
    for a in {k[:4] for k in res}:
        for b in res:
            if b.endswith("imp0"):
                continue
            (gen if b.startswith(a) else imp).append(huella.comparar(res[f"{a}_imp0"], res[b]).puntaje)
    r = calibracion.por_eer(gen, imp, mayor_es_mejor=True)
    alm.guardar_calibracion("huella", "as608", r.umbral, r.eer, r.far, r.frr, r.n_genuinos, r.n_impostores,
                            parametros={"origen": "banco sintético (solo pruebas)",
                                        "distribucion": calibracion.distribucion(gen, imp)})
    return {"id": "21", "pin": "2468", "rostro": str(ruta_rostro(datasets, 5, 8)),
            "huella": str(fixtures / "id01_imp3.bin")}


@dataclass
class Escenario:
    clave: str
    nombre: str
    id: str
    pin: str
    huella: str
    rostro: str
    esperado: str


def escenarios(datasets: Path) -> dict[str, dict]:
    return {k: Escenario(k, n, i, p, str(ruta_huella(datasets, d, imp)), str(ruta_rostro(datasets, per, img)), esp).__dict__
            for k, (n, i, p, d, imp, per, img, esp) in ESCENARIOS.items()}


def cargar_escenarios(alm: Almacen) -> dict[str, dict]:
    f = alm.carpeta / "escenarios.json"
    return json.loads(f.read_text("utf-8")) if f.exists() else {}


def preparar(esc: dict, velocidad: float = 1.0, ms_entre_servos: int = 300):
    """Escenario -> (dispositivo simulado, cámara de dataset)."""
    disp = DispositivoSimulado(esc["id"], esc["pin"], esc["huella"], FUENTE_HUELLA, velocidad=velocidad,
                               ms_entre_servos=ms_entre_servos)
    return disp, CamaraArchivo(esc["rostro"], "orl")
