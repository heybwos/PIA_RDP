"""ESP32 falso por TCP: habla el protocolo completo de docs/PROTOCOLO.md.

    python pc/herramientas/esp32_falso.py --guion "21#2468#"
    (en la app: modo ESP32, puerto socket://127.0.0.1:5333)

Al llegar el primer PING teclea el guion (TECLA:… y PIN:id:pin). Con PEDIR_HUELLA manda una
imagen de 256 x 288 a 4 bits por partes, al ritmo de 57600 baudios (o de golpe con --rapido).
Responde a MSG, ACCESO, CONFIG, PING y RESET.

Fallas: --falla crc (CRC malo), corte (se calla a media imagen), silencio (no contesta a
PEDIR_HUELLA), cancela (teclea el ID, luego D, y después el guion completo).
"""

from __future__ import annotations

import argparse
import asyncio
import zlib
from pathlib import Path

PC = Path(__file__).resolve().parents[1]
HUELLA_DEFECTO = PC / "tests" / "fixtures" / "huellas_sinteticas" / "id01_imp3.bin"
BYTES_POR_SEGUNDO = 5760


class Falso:
    def __init__(self, guion: str, huella: Path, rapido: bool, falla: str | None, repetir: bool):
        self.guion, self.rapido, self.falla, self.repetir = guion, rapido, falla, repetir
        self.imagen = huella.read_bytes()
        if len(self.imagen) != 36864:
            raise SystemExit(f"{huella} no mide 36,864 bytes (formato AS608)")

    async def atender(self, r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        def tx(t: str) -> None:
            w.write((t + "\n").encode())

        tecleado = False
        tareas: list[asyncio.Task] = []

        async def teclear():
            await asyncio.sleep(0 if self.rapido else 0.8)
            secuencia = self.guion
            if self.falla == "cancela":
                secuencia = self.guion.split("#")[0] + "D" + self.guion
            id_, pin, en_pin = "", "", False
            for c in secuencia:
                await asyncio.sleep(0 if self.rapido else 0.25)
                tx(f"TECLA:{c}")
                if c == "D":
                    tx("CANCELA")
                    id_, pin, en_pin = "", "", False
                elif c == "#":
                    if en_pin and len(pin) == 4:
                        tx(f"PIN:{id_}:{pin}")
                    elif len(id_) == 2:
                        en_pin = True
                elif c.isdigit():
                    if en_pin:
                        pin += c
                    else:
                        id_ += c
                await w.drain()

        async def enviar_huella():
            tx("HUELLA:ESPERA")
            await w.drain()
            await asyncio.sleep(0 if self.rapido else 0.6)
            tx("HUELLA:DEDO")
            datos = self.imagen
            tx(f"IMG:{len(datos)}")
            crc = zlib.crc32(datos)
            if self.falla == "crc":
                crc ^= 1
            paso = 1024
            limite = len(datos) // 2 if self.falla == "corte" else len(datos)
            for i in range(0, limite, paso):
                w.write(datos[i : min(i + paso, limite)])
                await w.drain()
                if not self.rapido:
                    await asyncio.sleep(paso / BYTES_POR_SEGUNDO)
            if self.falla == "corte":
                return
            tx(f"IMG:FIN:{crc:08x}")
            await w.drain()

        tx("HOLA:falso-1.0:OK:OK")
        await w.drain()
        try:
            while ln := await r.readline():
                cmd = ln.decode().strip()
                if cmd == "PING":
                    tx("PONG")
                    if not tecleado:
                        tecleado = True
                        tareas.append(asyncio.create_task(teclear()))
                elif cmd == "RESET":
                    tx("HOLA:falso-1.0:OK:OK")
                elif cmd.startswith("MSG:"):
                    tx("OK:MSG")
                elif cmd.startswith("CONFIG:"):
                    tx(f"OK:CONFIG:{cmd.split(':')[1]}")
                elif cmd == "PEDIR_PIN":
                    tx("OK:PEDIR_PIN")
                elif cmd == "PEDIR_HUELLA":
                    if self.falla != "silencio":
                        tareas.append(asyncio.create_task(enviar_huella()))
                elif cmd.startswith("ACCESO:"):
                    tx("OK:ACCESO")
                    if self.repetir:
                        async def otra():
                            await asyncio.sleep(3)
                            await teclear()
                        tareas.append(asyncio.create_task(otra()))
                elif cmd:
                    tx("ERR:desconocido")
                await w.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            for t in tareas:
                t.cancel()
            w.close()


async def servir(puerto: int, falso: Falso) -> None:
    srv = await asyncio.start_server(falso.atender, "127.0.0.1", puerto)
    print(f"ESP32 falso en socket://127.0.0.1:{puerto}", flush=True)
    async with srv:
        await srv.serve_forever()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=5333)
    ap.add_argument("--guion", default="21#2468#", help="teclas: ID # PIN #")
    ap.add_argument("--huella", type=Path, default=HUELLA_DEFECTO, help=".bin de 36,864 bytes")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--falla", choices=["crc", "corte", "silencio", "cancela"])
    ap.add_argument("--repetir", action="store_true", help="vuelve a teclear el guion después de cada ACCESO")
    a = ap.parse_args()
    asyncio.run(servir(a.puerto, Falso(a.guion, a.huella, a.rapido, a.falla, a.repetir)))


if __name__ == "__main__":
    main()
