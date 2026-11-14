"""Baja los datasets públicos a datos/datasets/ (no se suben a git).

    python pc/scripts/descargar_datasets.py            (ORL y FVC2002 DB1_B a DB4_B)
    python pc/scripts/descargar_datasets.py orl

- ORL / AT&T: 40 personas x 10 imágenes de 92 x 112, PGM. -> datos/datasets/orl/s1..s40/
- FVC2002 set B: 4 bases x 10 dedos x 8 impresiones, TIF. -> datos/datasets/fvc2002/DB1_B/...

Si una descarga falla, el script dice la URL y la carpeta donde dejar el ZIP a mano;
al volver a correrlo, lo descomprime.
"""

from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "datos" / "datasets"

FUENTES = {
    "orl": [("att_faces.zip", "https://www.cl.cam.ac.uk/research/dtg/attarchive/pub/data/att_faces.zip")],
    "fvc2002": [(f"DB{i}_B.zip", f"http://bias.csr.unibo.it/fvc2002/Downloads/DB{i}_B.zip") for i in range(1, 5)],
}


def bajar(url: str, archivo: Path) -> bool:
    if archivo.exists() and archivo.stat().st_size > 0:
        return True
    print(f"  Bajando {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pia-datasets/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(archivo.with_suffix(".parcial"), "wb") as f:
            while bloque := r.read(1 << 16):
                f.write(bloque)
        archivo.with_suffix(".parcial").replace(archivo)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FALLÓ: {e}")
        print(f"  Bájalo a mano desde {url}\n  y déjalo como {archivo}")
        return False


def descomprimir(archivo: Path, carpeta: Path) -> int:
    carpeta.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(archivo) as z:
        for info in z.infolist():
            destino = (carpeta / info.filename).resolve()
            if not destino.is_relative_to(carpeta.resolve()):  # nada fuera de la carpeta
                continue
            if info.is_dir():
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(z.read(info))
            n += 1
    return n


def main() -> int:
    pedidos = sys.argv[1:] or list(FUENTES)
    ok = True
    for nombre in pedidos:
        print(f"[{nombre}]")
        carpeta = DESTINO / nombre
        carpeta.mkdir(parents=True, exist_ok=True)
        for zip_nombre, url in FUENTES[nombre]:
            archivo = carpeta / zip_nombre
            if not bajar(url, archivo):
                ok = False
                continue
            sub = carpeta if nombre == "orl" else carpeta / archivo.stem
            print(f"  {zip_nombre}: {descomprimir(archivo, sub)} archivos")
    if (DESTINO / "orl").exists():
        pgm = list((DESTINO / "orl").rglob("*.pgm"))
        print(f"ORL: {len(pgm)} imágenes (se esperan 400)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
