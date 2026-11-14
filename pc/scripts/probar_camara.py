"""P3: comprueba que DroidCam se lee desde Python y que Viola-Jones encuentra el rostro.

    python pc/scripts/probar_camara.py --url http://192.168.1.50:4747/video
    python pc/scripts/probar_camara.py                 (usa [camara] de config.toml)
    python pc/scripts/probar_camara.py --indice 1      (DroidCam por USB con su cliente)

Toma cuadros durante unos segundos, imprime cuántos tienen rostro y ojos, cuánto tarda cada
uno, y guarda el último cuadro con los rectángulos y su cara alineada y normalizada en
datos/pruebas/camara_<hora>.png. Con --guardar-url escribe la URL en config.toml.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import camara, config, rostro  # noqa: E402


def lamina(cuadro: np.ndarray, r: rostro.ResultadoRostro) -> np.ndarray:
    img = cuadro.copy() if cuadro.ndim == 3 else cv2.cvtColor(cuadro, cv2.COLOR_GRAY2BGR)
    if r.deteccion.rostro:
        x, y, w, h = r.deteccion.rostro
        cv2.rectangle(img, (x, y), (x + w, y + h), (92, 207, 143), 2)
    for x, y, w, h in r.deteccion.ojos:
        cv2.rectangle(img, (x, y), (x + w, y + h), (48, 146, 255), 2)
    alto = img.shape[0]
    cara = cv2.resize(cv2.cvtColor(r.alineado.imagen, cv2.COLOR_GRAY2BGR), (alto // 2, alto // 2), interpolation=cv2.INTER_NEAREST)
    norm = (r.normalizada.imagen * 255).astype(np.uint8)
    norm = cv2.resize(cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR), (alto // 2, alto // 2), interpolation=cv2.INTER_NEAREST)
    return np.hstack([img, np.vstack([cara, norm])])


def guardar_url(url: str, rotacion: int | None) -> None:
    ruta = config.RAIZ / "config.toml"
    config.cargar()  # crea config.toml desde el ejemplo si no existe
    texto = ruta.read_text("utf-8")
    texto = re.sub(r'(?m)^url\s*=\s*".*?"', f'url = "{url}"', texto, count=1)
    texto = re.sub(r'(?m)^fuente\s*=\s*"(url|indice|dataset|archivo)"', 'fuente = "url"', texto, count=1)
    if rotacion is not None:
        if re.search(r"(?m)^rotacion\s*=", texto):
            texto = re.sub(r"(?m)^rotacion\s*=\s*\d+", f"rotacion = {rotacion}", texto, count=1)
        else:
            texto = re.sub(r"(?m)^(url\s*=.*)$", rf"\1\nrotacion = {rotacion}", texto, count=1)
    ruta.write_text(texto, "utf-8")
    print(f"config.toml: [camara] url = {url}" + (f", rotacion = {rotacion}" if rotacion is not None else ""))


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url")
    ap.add_argument("--indice", type=int)
    ap.add_argument("--segundos", type=float, default=6.0)
    ap.add_argument("--guardar-url", action="store_true", help="guarda la URL y la mejor rotación en config.toml")
    ap.add_argument("--rotacion", type=int, choices=[0, 90, 180, 270], help="fija la rotación en lugar de probar las cuatro")
    args = ap.parse_args()
    cfg = config.cargar()
    if args.indice is not None:
        cam, origen = camara.CamaraIndice(args.indice), f"índice {args.indice}"
    else:
        url = args.url or cfg.valor("camara.url")
        cam, origen = camara.CamaraURL(url), url
    print(f"Leyendo {origen} durante {args.segundos:.0f} s. Mira a la cámara de frente.")
    crudos, lecturas = [], []
    fin = time.monotonic() + args.segundos
    try:
        while time.monotonic() < fin:
            t0 = time.perf_counter()
            crudos.append(cam._capturar())  # sin rotar: se prueban las cuatro orientaciones abajo
            lecturas.append((time.perf_counter() - t0) * 1000)
    except camara.CamaraError as e:
        print(f"ERROR: {e}\n  Qué revisar: {e.que_revisar}")
        return 2
    finally:
        cam.cerrar()
    muestra = crudos[:: max(1, len(crudos) // 20)]  # hasta ~20 cuadros por orientación
    mejor = None
    print(f"Cuadros: {len(crudos)} de {crudos[0].shape[1]} x {crudos[0].shape[0]}. Por orientación ({len(muestra)} cuadros):")
    for g in ([args.rotacion] if args.rotacion is not None else [0, 90, 180, 270]):
        res = [rostro.procesar(camara.rotar(c, g), permitir_relleno=False) for c in muestra]
        ojos = sum(len(r.deteccion.ojos) == 2 for r in res)
        caras = sum(r.hay_rostro for r in res)
        print(f"  rotación {g:3d}°: rostro {caras}/{len(res)}, con los dos ojos {ojos}/{len(res)}")
        clave = (ojos, caras)
        if mejor is None or clave > mejor[0]:
            ultimo = next(((camara.rotar(c, g), r) for c, r in zip(muestra, res) if len(r.deteccion.ojos) == 2),
                          next(((camara.rotar(c, g), r) for c, r in zip(muestra, res) if r.hay_rostro),
                               (camara.rotar(muestra[-1], g), res[-1])))
            mejor = (clave, g, np.mean([r.duracion_ms for r in res]))
    (ojos, caras), rot, proc = mejor
    cuadro, r = ultimo
    print(f"Mejor orientación: {rot}° (rostro con ojos en {ojos} de {len(muestra)}).")
    print(f"Tiempo medio: lectura {np.mean(lecturas):.0f} ms, Viola-Jones + alineación + normalización {proc:.0f} ms.")
    con_rostro = caras
    destino = config.cargar().carpeta_datos / "pruebas" / f"camara_{datetime.now():%Y%m%d_%H%M%S}.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".png", lamina(cuadro, r))[1].tofile(str(destino))
    print(f"Último cuadro con rostro: {destino}")
    if args.guardar_url and args.url:
        guardar_url(args.url, rot if ojos else None)
    return 0 if con_rostro else 1


if __name__ == "__main__":
    sys.exit(main())
