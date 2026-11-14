"""Respaldo y borrado de datos/ (sección 4.6 del roadmap).

    python pc/scripts/respaldo.py crear
    python pc/scripts/respaldo.py restaurar datos/respaldos/pia_20261116_190000.zip
    python pc/scripts/respaldo.py borrar-usuario 07
    python pc/scripts/respaldo.py borrar-todo --confirmo

`crear` copia pia.db con la API de respaldo de SQLite (no el archivo abierto) y empaqueta
usuarios/, modelos/, banco_as608/, calibracion/, escenarios.json y config.toml.
`reprocesar` (regenerar plantillas y vectores desde los crudos) se hace en N7.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import config, registro  # noqa: E402
from pia.almacen import Almacen  # noqa: E402

CARPETAS = ["usuarios", "modelos", "banco_as608", "calibracion"]
SUELTOS = ["escenarios.json"]


def crear(cfg) -> Path:
    datos = cfg.carpeta_datos
    destino = datos / "respaldos" / f"pia_{datetime.now():%Y%m%d_%H%M%S}.zip"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "pia.db"
        with sqlite3.connect(datos / "pia.db") as src, sqlite3.connect(copia) as dst:
            src.backup(dst)
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(copia, "pia.db")
            for c in CARPETAS:
                for f in (datos / c).rglob("*") if (datos / c).exists() else []:
                    if f.is_file():
                        z.write(f, f.relative_to(datos).as_posix())
            for s in SUELTOS:
                if (datos / s).exists():
                    z.write(datos / s, s)
            cfg_local = config.RAIZ / "config.toml"
            if cfg_local.exists():
                z.write(cfg_local, "config.toml")
    return destino


def restaurar(cfg, zip_: Path) -> None:
    datos = cfg.carpeta_datos
    with zipfile.ZipFile(zip_) as z:
        for info in z.infolist():
            if info.filename == "config.toml":
                continue  # la configuración local no se pisa
            destino = (datos / info.filename).resolve()
            if not destino.is_relative_to(datos.resolve()):
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(z.read(info))


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cfg = config.cargar()
    orden = sys.argv[1]
    if orden == "crear":
        print(f"Respaldo: {crear(cfg)}")
    elif orden == "restaurar" and len(sys.argv) > 2:
        restaurar(cfg, Path(sys.argv[2]))
        print("Restaurado.")
    elif orden == "borrar-usuario" and len(sys.argv) > 2:
        alm = Almacen(cfg.carpeta_datos)
        dominios = {m["fuente"] for m in alm.muestras_rostro(id_=sys.argv[2])}
        alm.borrar_usuario(sys.argv[2])
        fondo = registro.caras_de_fondo(cfg.carpeta_datos / "datasets" / "orl", excluir=set())
        for d in {"camara" if f == "camara" else "dataset" for f in dominios}:
            registro.reentrenar(alm, d, fondo)
        print(f"Usuario {sys.argv[2]} borrado (la bitácora conserva sus intentos).")
    elif orden == "borrar-todo":
        if "--confirmo" not in sys.argv:
            print("Borra usuarios, banco, intentos, modelos y la base. Agrega --confirmo.")
            return 2
        for c in CARPETAS + ["intentos"]:
            shutil.rmtree(cfg.carpeta_datos / c, ignore_errors=True)
        for s in SUELTOS + ["pia.db"]:
            (cfg.carpeta_datos / s).unlink(missing_ok=True)
        print("Borrado. Quedan datasets/, pruebas/ y respaldos/.")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
