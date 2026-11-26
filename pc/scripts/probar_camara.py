"""P3: comprueba que DroidCam se lee desde Python y que Viola-Jones encuentra el rostro.

    python pc/scripts/probar_camara.py --url http://192.168.1.50:4747/video
    python pc/scripts/probar_camara.py                 (usa [camara] de config.toml)
    python pc/scripts/probar_camara.py --indice 1      (DroidCam por USB con su cliente)

Toma cuadros durante unos segundos, imprime cuántos tienen rostro y ojos, cuánto tarda cada
uno, y guarda el último cuadro con los rectángulos y su cara alineada y normalizada en
datos/pruebas/camara_<hora>.png. Con --guardar-url escribe la URL en config.toml; con --respaldo
la escribe como url_respaldo (la que se usa si la principal no contesta):

    python pc/scripts/probar_camara.py --url http://<IP en la WiFi de la facultad>:8080/video --guardar-url
    python pc/scripts/probar_camara.py --url http://10.28.183.166:8080/video --guardar-url --respaldo
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


def vista_en_vivo(cam: camara.Camara, rot: int, segundos: float) -> list[np.ndarray] | None:
    """Ventana con la cámara en vivo y los rectángulos de Viola-Jones para acomodarse.
    Espacio: mide durante `segundos` y devuelve esos cuadros (sin rotar). Q o Esc: sale."""
    titulo = "PIA - camara (Espacio: medir, Q: salir)"
    cv2.namedWindow(titulo, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(titulo, cv2.WND_PROP_TOPMOST, 1)  # al frente: si no, queda detrás de otras ventanas
    print("Abriendo la ventana 'PIA - camara'... (si no la ves, búscala en la barra de tareas)", flush=True)
    midiendo, fin, crudos, primero = False, 0.0, [], True
    try:
        while True:
            crudo = cam._capturar()
            cuadro = camara.rotar(crudo, rot)
            r = rostro.procesar(cuadro, permitir_relleno=False)
            img = cuadro.copy()
            ok = r.hay_rostro and len(r.deteccion.ojos) == 2
            if r.deteccion.rostro:
                x, y, w, h = r.deteccion.rostro
                cv2.rectangle(img, (x, y), (x + w, y + h), (92, 207, 143) if ok else (48, 146, 255), 3)
            for x, y, w, h in r.deteccion.ojos:
                cv2.rectangle(img, (x, y), (x + w, y + h), (48, 146, 255), 2)
            if midiendo:
                crudos.append(crudo)
                texto = f"Midiendo... {max(0, fin - time.monotonic()):.0f} s"
                if time.monotonic() >= fin:
                    return crudos
            else:
                texto = "Rostro y ojos OK - Espacio para medir" if ok else "Acomodate: sin rostro con los dos ojos"
            cv2.rectangle(img, (0, 0), (img.shape[1], 56), (20, 20, 20), -1)
            cv2.putText(img, texto, (14, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (92, 207, 143) if ok else (80, 160, 255), 2, cv2.LINE_AA)
            alto = 900
            esc = min(1.0, alto / img.shape[0])
            cv2.imshow(titulo, cv2.resize(img, None, fx=esc, fy=esc))
            if primero:
                print(f"Primer cuadro: {img.shape[1]} x {img.shape[0]}. Ventana abierta.", flush=True)
                primero = False
            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord("q"), ord("Q")):
                return None
            if k == ord(" ") and not midiendo:
                midiendo, fin = True, time.monotonic() + segundos
            if cv2.getWindowProperty(titulo, cv2.WND_PROP_VISIBLE) < 1:
                return None
    finally:
        cv2.destroyAllWindows()


def guardar_url(url: str, rotacion: int | None, clave: str = "url") -> None:
    ruta = config.RAIZ / "config.toml"
    config.cargar()  # crea config.toml desde el ejemplo si no existe
    texto = ruta.read_text("utf-8")
    patron = rf'(?m)^{clave}\s*=\s*".*?"'
    if re.search(patron, texto):
        texto = re.sub(patron, f'{clave} = "{url}"', texto, count=1)
    else:  # url_respaldo en un config.toml anterior: va debajo de url
        texto = re.sub(r"(?m)^(url\s*=.*)$", lambda m: f'{m.group(1)}\n{clave} = "{url}"', texto, count=1)
    texto = re.sub(r'(?m)^fuente\s*=\s*"(url|indice|dataset|archivo)"', 'fuente = "url"', texto, count=1)
    if rotacion is not None:
        if re.search(r"(?m)^rotacion\s*=", texto):
            texto = re.sub(r"(?m)^rotacion\s*=\s*\d+", f"rotacion = {rotacion}", texto, count=1)
        else:
            texto = re.sub(r"(?m)^(url\s*=.*)$", rf"\1\nrotacion = {rotacion}", texto, count=1)
    ruta.write_text(texto, "utf-8")
    print(f"config.toml: [camara] {clave} = {url}" + (f", rotacion = {rotacion}" if rotacion is not None else ""))


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url")
    ap.add_argument("--indice", type=int)
    ap.add_argument("--segundos", type=float, default=6.0)
    ap.add_argument("--guardar-url", action="store_true", help="guarda la URL y la mejor rotación en config.toml")
    ap.add_argument("--respaldo", action="store_true", help="con --guardar-url: la guarda como url_respaldo (hotspot)")
    ap.add_argument("--rotacion", type=int, choices=[0, 90, 180, 270], help="fija la rotación en lugar de probar las cuatro")
    ap.add_argument("--vista", action="store_true", help="ventana en vivo para acomodarse; Espacio mide")
    args = ap.parse_args()
    cfg = config.cargar()
    if args.indice is not None:
        cam, origen = camara.CamaraIndice(args.indice), f"índice {args.indice}"
    else:
        url = args.url or camara.elegir_url(cfg)
        cam, origen = camara.CamaraURL(url), url
    crudos, lecturas = [], [0.0]
    try:
        if args.vista:
            rot = args.rotacion if args.rotacion is not None else int(cfg.valor("camara.rotacion", 0))
            print(f"Vista en vivo de {origen} (rotación {rot}°). Acomódate y presiona Espacio para medir.")
            crudos = vista_en_vivo(cam, rot, args.segundos)
            if not crudos:
                print("Cerrado sin medir.")
                return 0
            args.rotacion = rot
        else:
            print(f"Leyendo {origen} durante {args.segundos:.0f} s. Mira a la cámara de frente.")
            fin = time.monotonic() + args.segundos
            lecturas = []
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
        guardar_url(args.url, rot if ojos else None, "url_respaldo" if args.respaldo else "url")
    return 0 if con_rostro else 1


if __name__ == "__main__":
    sys.exit(main())
