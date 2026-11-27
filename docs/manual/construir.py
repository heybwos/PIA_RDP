"""Arma el manual de capacitación (HTML -> PDF con Edge).

    python docs\\manual\\construir.py            (usa el Python del sistema: necesita PyMuPDF para el índice)

- Une docs/manual/capitulos/*.html en orden.
- <!--CODIGO ruta inicio-fin--> se reemplaza por esas líneas EXACTAS del archivo del repositorio
  (con números de línea): ningún fragmento de código del manual está escrito a mano.
- Imprime con Edge, busca en qué página cae cada capítulo y vuelve a imprimir con el índice numerado.
Salida: docs/manual/Manual_PIA_RDP.pdf
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HTML = AQUI / "manual.html"
PDF = AQUI / "Manual_PIA_RDP.pdf"


def bloque_codigo(m: re.Match) -> str:
    ruta, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    lineas = (RAIZ / ruta).read_text("utf-8").splitlines()
    if b > len(lineas):
        raise SystemExit(f"{ruta} tiene {len(lineas)} líneas; se pidió hasta {b}")
    filas = "".join(f'<span class="ln">{n}</span>{html.escape(lineas[n - 1]) or " "}\n' for n in range(a, b + 1))
    return (f'<div class="codigo"><div class="codigo-cab"><span>{ruta}</span><span>líneas {a}–{b}</span></div>'
            f"<pre>{filas}</pre></div>")


def armar(paginas: dict[str, int] | None = None) -> list[tuple[str, str]]:
    cuerpo = "".join(p.read_text("utf-8") for p in sorted((AQUI / "capitulos").glob("*.html")))
    cuerpo = re.sub(r"<!--CODIGO (\S+) (\d+)-(\d+)-->", bloque_codigo, cuerpo)
    caps = re.findall(r'<h1 id="(c\d+)"[^>]*>(.*?)</h1>', cuerpo)
    subs = re.findall(r'<h2 id="(c\d+-\d+)"[^>]*>(.*?)</h2>', cuerpo)
    filas = []
    for cid, tit in caps:
        filas.append(f'<li class="toc-cap"><a href="#{cid}">{tit}</a><span>{(paginas or {}).get(cid, "")}</span></li>')
        for sid, st in subs:
            if sid.split("-")[0] == cid:
                filas.append(f'<li class="toc-sub"><a href="#{sid}">{st}</a><span>{(paginas or {}).get(sid, "")}</span></li>')
    plantilla = (AQUI / "plantilla.html").read_text("utf-8")
    HTML.write_text(plantilla.replace("{{INDICE}}", "\n".join(filas)).replace("{{CUERPO}}", cuerpo), "utf-8")
    return [(c, re.sub("<[^>]+>", "", t)) for c, t in caps] + [(s, re.sub("<[^>]+>", "", t)) for s, t in subs]


def imprimir() -> None:
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
                    f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, capture_output=True, timeout=240)


def paginas_de(titulos: list[tuple[str, str]]) -> dict[str, int]:
    import fitz  # PyMuPDF

    doc = fitz.open(PDF)
    textos = [" ".join(p.get_text().split()) for p in doc]
    inicio = next(i for i, t in enumerate(textos) if i > 1 and "capítulo 1" in t.lower())
    res = {}
    for clave, tit in titulos:
        buscado = " ".join(html.unescape(tit).split())
        for i in range(inicio, len(textos)):
            if buscado in textos[i]:
                res[clave] = i + 1
                break
    return res


if __name__ == "__main__":
    titulos = armar()
    imprimir()
    if "--sin-indice" not in sys.argv:
        pags = paginas_de(titulos)
        faltan = [t for c, t in titulos if c not in pags]
        if faltan:
            print("Sin página para:", faltan)
        armar(pags)
        imprimir()
    import fitz

    print(f"{PDF} · {fitz.open(PDF).page_count} páginas")
