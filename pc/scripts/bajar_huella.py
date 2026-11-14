"""Compuerta G1: baja una imagen cruda del AS608 a través del ESP32.

Uso:
    python pc/scripts/bajar_huella.py --puerto COM5
    python pc/scripts/bajar_huella.py --puerto socket://127.0.0.1:5333   (emisor falso)

Manda PEDIR_HUELLA, espera el marco IMG:<bytes> ... IMG:FIN:<crc32> (docs/PROTOCOLO.md),
verifica el CRC y guarda en datos/pruebas/:
    huella_<hora>.bin        los bytes crudos
    huella_<hora>_alto.png   nibble alto primero
    huella_<hora>_bajo.png   nibble bajo primero
Uno de los dos PNG debe verse como huella; el otro, con ruido de grano.

Solo usa pyserial, numpy y pillow.
"""

from __future__ import annotations

import argparse
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import serial
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
ANCHO, ALTO = 256, 288
BYTES_ESPERADOS = ANCHO * ALTO // 2  # 36864


class Enlace:
    """Lector con modo línea y modo binario sobre el mismo búfer."""

    def __init__(self, puerto: str, baudios: int):
        self.ser = serial.serial_for_url(puerto, baudrate=baudios, timeout=0.1, do_not_open=True)
        self.ser.open()
        self.buf = bytearray()

    def _llenar(self) -> bool:
        datos = self.ser.read(max(1, self.ser.in_waiting))
        if datos:
            self.buf += datos
            return True
        return False

    def linea(self, limite_s: float) -> str | None:
        fin = time.monotonic() + limite_s
        while True:
            i = self.buf.find(b"\n")
            if i >= 0:
                crudo = bytes(self.buf[:i])
                del self.buf[: i + 1]
                return crudo.decode("ascii", errors="replace").strip("\r")
            if time.monotonic() > fin:
                return None
            self._llenar()

    def bytes_exactos(self, n: int, limite_bloque_s: float = 3.0) -> bytes | None:
        ultimo = time.monotonic()
        mostrado = -1
        while len(self.buf) < n:
            if self._llenar():
                ultimo = time.monotonic()
            elif time.monotonic() - ultimo > limite_bloque_s:
                print(f"\n  Corte: llegaron {len(self.buf)} de {n} bytes.")
                return None
            pct = min(100, len(self.buf) * 100 // n)
            if pct // 5 != mostrado:
                mostrado = pct // 5
                print(f"\r  Recibiendo {min(len(self.buf), n):>6}/{n} bytes", end="", flush=True)
        print(f"\r  Recibiendo {n:>6}/{n} bytes")
        datos = bytes(self.buf[:n])
        del self.buf[:n]
        return datos

    def descartar(self, espera_s: float = 0.5) -> None:
        """Tira lo que quede de una transferencia cortada."""
        time.sleep(espera_s)
        self.ser.reset_input_buffer()
        self.buf.clear()

    def enviar(self, texto: str) -> None:
        self.ser.write((texto + "\n").encode("ascii"))
        self.ser.flush()

    def cerrar(self) -> None:
        self.ser.close()


def desempacar(datos: bytes, alto_primero: bool) -> np.ndarray:
    """4 bits por píxel -> imagen de 8 bits, ANCHO de ancho."""
    a = np.frombuffer(datos, dtype=np.uint8)
    hi, lo = a >> 4, a & 0x0F
    pares = (hi, lo) if alto_primero else (lo, hi)
    px = np.stack(pares, axis=1).reshape(-1)
    filas = len(px) // ANCHO
    px = px[: filas * ANCHO].reshape(filas, ANCHO)
    return (px * 17).astype(np.uint8)  # 0..15 -> 0..255


def esperar_esp32(enlace: Enlace) -> bool:
    """Al abrir el puerto el ESP32 suele reiniciarse: espera HOLA, si no, PING."""
    fin = time.monotonic() + 4.0
    while time.monotonic() < fin:
        ln = enlace.linea(0.3)
        if ln is None:
            continue
        print(f"  < {ln}")
        if ln.startswith("HOLA:"):
            if ":ERR:" in ln:
                print("  El ESP32 responde, pero el sensor NO (G1-C). Revisa la lista R1.")
            return True
    for _ in range(3):
        enlace.enviar("PING")
        ln = enlace.linea(1.0)
        while ln is not None and ln != "PONG":
            print(f"  < {ln}")
            ln = enlace.linea(0.5)
        if ln == "PONG":
            print("  < PONG")
            enlace.enviar("PARAMS")
            return True
    return False


def una_captura(enlace: Enlace, salida: Path) -> bool:
    enlace.enviar("PEDIR_HUELLA")
    while True:
        ln = enlace.linea(25.0)
        if ln is None:
            print("  El ESP32 no contestó en 25 s.")
            return False
        if ln == "HUELLA:ESPERA":
            print("  Coloca el dedo y no lo muevas unos 7 s...")
            continue
        if ln == "HUELLA:DEDO":
            print("  Dedo detectado. Bajando la imagen (a 57600 baudios tarda unos 6.5 s).")
            continue
        if ln.startswith("HUELLA:ERR"):
            print(f"  Error del sensor: {ln}")
            return False
        if ln.startswith("IMG:") and not ln.startswith("IMG:FIN"):
            n = int(ln.split(":")[1])
            break
        print(f"  < {ln[:80]}")

    datos = enlace.bytes_exactos(n)
    if datos is None:
        enlace.descartar()
        enlace.enviar("RESET")
        return False
    fin = enlace.linea(3.0)
    if not fin or not fin.startswith("IMG:FIN:"):
        print(f"  Falta la línea IMG:FIN (llegó: {fin[:40] if fin else None!r}).")
        print("  Sobran o faltan bytes en la imagen: revisa los baudios USB (prueba 115200).")
        enlace.descartar()
        return False
    crc_esp = int(fin.split(":")[2], 16)
    crc_pc = zlib.crc32(datos) & 0xFFFFFFFF
    if crc_esp != crc_pc:
        print(f"  CRC incorrecto: ESP32 {crc_esp:08x}, PC {crc_pc:08x}. Imagen descartada.")
        return False
    print(f"  CRC correcto ({crc_pc:08x}).")

    salida.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now()
    base = salida / f"huella_{ahora:%Y%m%d_%H%M%S}_{ahora.microsecond // 1000:03d}"
    base.with_suffix(".bin").write_bytes(datos)
    alto = desempacar(datos, True)
    bajo = desempacar(datos, False)
    Image.fromarray(alto).save(f"{base}_alto.png")
    Image.fromarray(bajo).save(f"{base}_bajo.png")

    completa = "completa" if n == BYTES_ESPERADOS else f"INCOMPLETA (se esperaban {BYTES_ESPERADOS})"
    print(f"  Bytes: {n} -> {completa}")
    print(f"  Tamaño: {alto.shape[1]} x {alto.shape[0]} px")
    niveles = alto // 17
    print(f"  Media: {niveles.mean():.2f}  Desviación: {niveles.std():.2f}  (niveles 0 a 15)")
    print(f"  Guardado: {base}.bin, _alto.png, _bajo.png")
    return n == BYTES_ESPERADOS


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", required=True, help="COM5, /dev/ttyUSB0 o socket://127.0.0.1:5333")
    ap.add_argument("--baudios", type=int, default=921600)
    ap.add_argument("--veces", type=int, default=1, help="capturas seguidas")
    ap.add_argument("--salida", type=Path, default=RAIZ / "datos" / "pruebas")
    args = ap.parse_args()
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(errors="replace")

    try:
        enlace = Enlace(args.puerto, args.baudios)
    except serial.SerialException as e:
        print(f"No se pudo abrir {args.puerto}: {e}")
        print("¿Está abierto el monitor serie de PlatformIO? Ciérralo. ¿Es el COM correcto?")
        return 2

    try:
        print(f"Conectado a {args.puerto} a {args.baudios} baudios.")
        if not esperar_esp32(enlace):
            print("El ESP32 no responde. ¿Cargaste test_huella_imagen? ¿Coinciden los baudios?")
            return 2
        buenas = 0
        for i in range(args.veces):
            print(f"\nCaptura {i + 1} de {args.veces}")
            buenas += una_captura(enlace, args.salida)
        print(f"\nResultado: {buenas} de {args.veces} capturas completas con CRC correcto.")
        return 0 if buenas == args.veces else 1
    finally:
        enlace.cerrar()


if __name__ == "__main__":
    sys.exit(main())
