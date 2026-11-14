"""El ESP32 real (o el falso por socket://) detrás de la interfaz Dispositivo.

Un hilo lee el puerto: en modo línea reparte las líneas a una cola asyncio; tras
`IMG:<bytes>` pasa a modo binario, lee exactamente esos bytes por bloques (cada bloque
se emite como filas para dibujar el barrido real) y vuelve a modo línea con `IMG:FIN`.
Otro task manda PING cada segundo.
"""

from __future__ import annotations

import asyncio
import threading
import time
import unicodedata
import zlib
from dataclasses import dataclass

import numpy as np
import serial
from serial.tools import list_ports

from ..huella.imagen import ANCHO, desempacar
from .base import CapturaCancelada, Dispositivo, Emisor, ErrorDispositivo, imagen_json

MS_ESPERA_LINEA = 25.0


def sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


@dataclass
class Saludo:
    puerto: str
    version: str
    sensor: bool
    oled: bool


def _saludar(puerto: str, baudios: int, limite_s: float = 4.0) -> Saludo | None:
    """Abre el puerto, espera HOLA (el ESP32 suele reiniciarse al abrir) o lo pide con RESET."""
    try:
        s = serial.serial_for_url(puerto, baudrate=baudios, timeout=0.2)
    except (serial.SerialException, OSError, ValueError):
        return None
    try:
        fin = time.monotonic() + limite_s
        pedido = False
        buf = b""
        while time.monotonic() < fin:
            buf += s.read(256)
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                t = ln.decode("ascii", "replace").strip()
                if t.startswith("HOLA:"):
                    p = t.split(":")
                    if len(p) >= 4:
                        return Saludo(puerto, p[1], p[2] == "OK", p[3] == "OK")
            if not pedido and time.monotonic() > fin - limite_s / 2:
                s.write(b"RESET\n")
                pedido = True
        return None
    finally:
        s.close()


def buscar(baudios: int = 921600, extra: list[str] | None = None, solo_extra: bool = False) -> list[dict]:
    """Lista los puertos serie y los que contestan HOLA. solo_extra: no toca los COM reales (pruebas)."""
    res = []
    puertos = ([] if solo_extra else [p.device for p in list_ports.comports()]) + list(extra or [])
    for p in puertos:
        sal = _saludar(p, baudios)
        res.append({"puerto": p, "responde": sal is not None,
                    **({"version": sal.version, "sensor": sal.sensor, "oled": sal.oled} if sal else {})})
    return res


class DispositivoESP32(Dispositivo):
    nombre = "esp32"
    simulado = False

    def __init__(self, puerto: str, baudios: int = 921600, emitir: Emisor | None = None,
                 nibble_alto_primero: bool = True, fuente_huella: str = "as608",
                 ms_entre_servos: int = 300, ms_abierto: int = 8000):
        super().__init__(emitir)
        self.puerto, self.baudios = puerto, baudios
        self.nibble_alto = nibble_alto_primero
        self.fuente_huella = fuente_huella
        self.ms_entre_servos, self.ms_abierto = ms_entre_servos, ms_abierto
        self.ser: serial.SerialBase | None = None
        self.saludo: Saludo | None = None
        self._cola: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._hilo: threading.Thread | None = None
        self._vivo = False
        self._ping: asyncio.Task | None = None
        self._lock_tx = threading.Lock()
        self.en_transferencia = False
        self.limite_huella_s = 35.0  # 15 s para el dedo + ~8 s de imagen + margen

    # ------------------------------------------------------------------ conexión
    async def conectar(self) -> Saludo:
        self._loop = asyncio.get_running_loop()
        self._cola = asyncio.Queue()
        try:
            self.ser = await asyncio.to_thread(serial.serial_for_url, self.puerto, baudrate=self.baudios, timeout=0.1)
        except (serial.SerialException, OSError, ValueError) as e:
            raise ErrorDispositivo(f"No se pudo abrir {self.puerto}: {e}",
                                   "Cierra el monitor serie de PlatformIO y revisa el puerto") from e
        self._vivo = True
        self._hilo = threading.Thread(target=self._leer, daemon=True)
        self._hilo.start()
        self._tx("RESET")
        fin = time.monotonic() + 5
        while time.monotonic() < fin:
            try:
                tipo, dato = await asyncio.wait_for(self._cola.get(), 0.5)
            except asyncio.TimeoutError:
                continue
            if tipo == "linea" and dato.startswith("HOLA:"):
                p = dato.split(":")
                self.saludo = Saludo(self.puerto, p[1], p[2] == "OK", p[3] == "OK")
                break
        if not self.saludo:
            await self.cerrar()
            raise ErrorDispositivo(f"{self.puerto} no contestó HOLA",
                                   "¿Está cargado el firmware principal (esp32dev)? ¿Coinciden los baudios?")
        self._ping = asyncio.create_task(self._latido())
        self._tx(f"CONFIG:ms_servos:{self.ms_entre_servos}")
        self._tx(f"CONFIG:ms_abierto:{self.ms_abierto}")
        return self.saludo

    async def cerrar(self) -> None:
        self._vivo = False
        if self._ping:
            self._ping.cancel()
        if self.ser:
            try:
                self.ser.close()
            except Exception:  # noqa: BLE001
                pass

    @property
    def conectado(self) -> bool:
        return self._vivo and self.ser is not None

    async def _latido(self) -> None:
        while self._vivo:
            if not self.en_transferencia:
                self._tx("PING", eco=False)
            await asyncio.sleep(1.0)

    def _tx(self, linea: str, eco: bool = True) -> None:
        if not self.ser:
            return
        with self._lock_tx:
            try:
                self.ser.write((linea + "\n").encode("ascii", "replace"))
            except (serial.SerialException, OSError):
                self._poner("caida", None)
        if eco and self._loop:
            asyncio.run_coroutine_threadsafe(self.emitir("serie", {"dir": "out", "linea": linea}), self._loop)

    def _poner(self, tipo: str, dato) -> None:
        if self._loop and self._cola is not None:
            self._loop.call_soon_threadsafe(self._cola.put_nowait, (tipo, dato))

    # ------------------------------------------------------------------ hilo lector
    def _leer(self) -> None:
        buf = b""
        while self._vivo:
            try:
                buf += self.ser.read(max(1, self.ser.in_waiting))
            except (serial.SerialException, OSError, TypeError, AttributeError):
                self._poner("caida", None)
                return
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                t = ln.decode("ascii", "replace").strip()
                if not t:
                    continue
                if t.startswith("IMG:") and not t.startswith("IMG:FIN"):
                    buf = self._leer_imagen(int(t.split(":")[1]), buf)
                else:
                    self._poner("linea", t)

    def _leer_imagen(self, n: int, buf: bytes) -> bytes:
        self.en_transferencia = True
        self._poner("img_inicio", n)
        datos = bytearray()
        ultimo = time.monotonic()
        bloque = ANCHO // 2 * 16  # 16 filas
        enviado = 0
        while len(datos) < n:
            if buf:
                tomar = min(len(buf), n - len(datos))
                datos += buf[:tomar]
                buf = buf[tomar:]
                ultimo = time.monotonic()
            else:
                try:
                    buf = self.ser.read(max(1, self.ser.in_waiting))
                except (serial.SerialException, OSError):
                    break
                if not buf and time.monotonic() - ultimo > 3.0:
                    break
            while len(datos) - enviado >= bloque or (len(datos) == n and enviado < n):
                fin = min(enviado + bloque, len(datos))
                self._poner("img_bloque", (enviado, bytes(datos[enviado:fin])))
                enviado = fin
        if len(datos) < n:
            self._poner("img_corte", len(datos))
            self.en_transferencia = False
            return b""
        # la línea IMG:FIN viene después de los datos
        while b"\n" not in buf:
            try:
                r = self.ser.read(max(1, self.ser.in_waiting))
            except (serial.SerialException, OSError):
                break
            if not r and time.monotonic() - ultimo > 3.0:
                break
            buf += r
        fin_ln, _, buf = buf.partition(b"\n")
        t = fin_ln.decode("ascii", "replace").strip()
        crc_ok = t.startswith("IMG:FIN:") and int(t.split(":")[2], 16) == (zlib.crc32(bytes(datos)) & 0xFFFFFFFF)
        self._poner("linea", t)
        self._poner("img_fin", (bytes(datos), crc_ok))
        self.en_transferencia = False
        return buf

    async def _siguiente(self, limite: float | None = MS_ESPERA_LINEA):
        try:
            item = await asyncio.wait_for(self._cola.get(), limite)
        except asyncio.TimeoutError as e:
            raise ErrorDispositivo("El ESP32 no contestó a tiempo", "Revisa el cable USB y el firmware") from e
        if item[0] == "caida":
            self._vivo = False
            raise ErrorDispositivo("Se perdió la conexión con el ESP32", "Reconecta el USB y pulsa Buscar ESP32")
        if item[0] == "linea" and not item[1].startswith(("PONG", "OK:", "TECLA:")):  # las teclas las pinta el evento tecla
            await self.emitir("serie", {"dir": "in", "linea": self._enmascarar(item[1])})
        return item

    @staticmethod
    def _enmascarar(t: str) -> str:
        if t.startswith("PIN:"):
            p = t.split(":")
            return f"PIN:{p[1]}:{'*' * len(p[2]) if len(p) > 2 else ''}"
        return t

    # ------------------------------------------------------------------ interfaz
    async def leer_pin(self) -> tuple[str, str]:
        """Espera sin límite a que alguien teclee en la caja (la verificación empieza en el teclado)."""
        id_ = pin = ""
        en_pin = False
        while True:
            tipo, t = await self._siguiente(limite=None)
            if tipo != "linea":
                continue
            if t.startswith("TECLA:"):
                c = t[6:7]
                await self.emitir("tecla", {"c": c})
                if c == "*":
                    if en_pin:
                        pin = pin[:-1]
                    else:
                        id_ = id_[:-1]
                elif c == "#":
                    if not en_pin and len(id_) == 2:
                        en_pin = True
                elif c.isdigit():
                    if en_pin and len(pin) < 4:
                        pin += c
                    elif not en_pin and len(id_) < 2:
                        id_ += c
                await self.emitir("casillas", {"id": id_, "pin": "*" * len(pin), "fase": "pin" if en_pin else "id"})
            elif t == "CANCELA":
                id_ = pin = ""
                en_pin = False
                await self.emitir("casillas", {"id": "", "pin": "", "fase": "id"})
            elif t.startswith("PIN:"):
                p = t.split(":")
                return p[1], p[2]

    async def capturar_huella(self) -> tuple[np.ndarray, str]:
        self._tx("PEDIR_HUELLA")
        await self.emitir("oled", {"l1": "Coloca el dedo", "l2": "en el sensor"})
        crudo = bytearray()
        # límite total: los PONG de cada segundo no deben mantener viva una espera sin imagen
        fin = time.monotonic() + self.limite_huella_s
        while True:
            restante = fin - time.monotonic()
            if restante <= 0 and not self.en_transferencia:
                raise ErrorDispositivo("El ESP32 no contestó con la huella a tiempo",
                                       "Revisa el sensor (¿HUELLA:ERR en el tráfico serie?) y el cable")
            tipo, dato = await self._siguiente(limite=max(restante, 5.0))
            if tipo == "linea":
                if dato.startswith("HUELLA:ERR"):
                    raise ErrorDispositivo(f"El sensor respondió {dato}",
                                           "Sin dedo a tiempo o error del AS608: intenta de nuevo")
                if dato == "CANCELA":
                    raise CapturaCancelada()
            elif tipo == "img_inicio":
                await self.emitir("huella_inicio", {"ancho": ANCHO, "alto": dato * 2 // ANCHO,
                                                     "fuente": self.fuente_huella, "simulada": False})
            elif tipo == "img_bloque":
                inicio, b = dato
                crudo += b
                filas = desempacar(b, self.nibble_alto)
                await self.emitir("huella_filas", {"y0": inicio * 2 // ANCHO, "filas": imagen_json(filas)})
            elif tipo == "img_corte":
                raise ErrorDispositivo(f"La imagen se cortó a los {dato} bytes", "Revisa el cable; si se repite, baja a 115200")
            elif tipo == "img_fin":
                datos, crc_ok = dato
                await self.emitir("huella_fin", {"bytes": len(datos), "crc_ok": crc_ok, "ms": 0})
                if not crc_ok:
                    raise ErrorDispositivo("La imagen llegó con el CRC incorrecto", "Repite la captura")
                return desempacar(datos, self.nibble_alto), self.fuente_huella

    async def mostrar(self, l1: str, l2: str = "") -> None:
        l1, l2 = sin_acentos(l1)[:21], sin_acentos(l2)[:21]
        self._tx(f"MSG:{l1}|{l2}")
        await self.emitir("oled", {"l1": l1, "l2": l2})

    async def actuar(self, nivel: int) -> None:
        self._tx(f"ACCESO:{nivel}")
        if nivel == 0:
            await self.emitir("leds", {"verde": False, "rojo": True})
            return
        await self.emitir("leds", {"verde": True, "rojo": False})
        for n in range(1, nivel + 1):  # el firmware los mueve uno a la vez; la app refleja lo mismo
            await self.emitir("servo", {"n": n, "abierto": True})
            await asyncio.sleep(self.ms_entre_servos / 1000)

    async def reiniciar(self) -> None:
        self._tx("PEDIR_PIN")
