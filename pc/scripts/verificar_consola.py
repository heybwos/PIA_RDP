"""Corre una verificación simulada y la imprime.

    python pc/scripts/verificar_consola.py --escenario l1
    python pc/scripts/verificar_consola.py --todos
    python pc/scripts/verificar_consola.py --escenario l1 --eventos     (cada evento)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import config, simular  # noqa: E402
from pia.almacen import Almacen  # noqa: E402
from pia.orquestador import Orquestador  # noqa: E402


async def correr(alm: Almacen, cfg, claves: list[str], ver_eventos: bool, velocidad: float) -> int:
    escs = simular.cargar_escenarios(alm)
    if not escs:
        print("No hay escenarios. Corre: python pc/scripts/sembrar_simular.py")
        return 2

    async def emitir(tipo, datos):
        if tipo == "error":
            print(f"  ERROR: {datos['mensaje']} -> {datos['que_revisar']}")
        elif ver_eventos:
            corto = {k: v for k, v in datos.items() if not isinstance(v, (dict, list)) or k in ("rostro", "ojos")}
            print(f"  · {tipo} {corto}")

    orq = Orquestador(alm, cfg, emitir)
    fallos = 0
    for clave in claves:
        e = escs[clave]
        disp, cam = simular.preparar(e, velocidad, int(cfg.valor("actuadores.ms_entre_servos", 300)))
        r = await orq.verificar(disp, cam, "simular")
        f = r.fila
        obtenido = f"Concedido, nivel {r.nivel}" if r.concedido else "Negado"
        ok = obtenido == e["esperado"]
        fallos += not ok
        print(f"[{clave}] {e['nombre']}: {obtenido}" + ("" if r.concedido else f" ({r.motivo})")
              + f"  {'OK' if ok else 'ESPERADO: ' + e['esperado']}")
        if f.get("puntaje_huella") is not None:
            print(f"      huella {f['puntaje_huella']:.3f} -> {f['huella_norm']:.2f}   "
                  f"rostro d {f['distancia_rostro']:.2f} -> {f['rostro_norm']:.2f}   "
                  f"fusión {f['fusion']:.2f}   {f['duracion_ms']} ms")
    return 1 if fallos else 0


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--escenario", choices=list(simular.ESCENARIOS))
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--eventos", action="store_true")
    ap.add_argument("--velocidad", type=float, default=0.0, help="1 = ritmo real; 0 = sin esperas")
    args = ap.parse_args()
    claves = list(simular.ESCENARIOS) if args.todos or not args.escenario else [args.escenario]
    cfg = config.cargar()
    return asyncio.run(correr(Almacen(cfg.carpeta_datos), cfg, claves, args.eventos, args.velocidad))


if __name__ == "__main__":
    sys.exit(main())
