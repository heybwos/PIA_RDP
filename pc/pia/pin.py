"""PIN con PBKDF2-HMAC-SHA256.

Un PIN de 4 dígitos tiene 10,000 combinaciones: el hash evita guardarlo en claro, no lo
vuelve fuerte contra quien tenga la base. Así se dice en el reporte.
"""

from __future__ import annotations

import hashlib
import hmac
import os

ITERACIONES = 200_000


def hashear(pin: str, sal: bytes | None = None, iteraciones: int = ITERACIONES) -> tuple[bytes, bytes, int]:
    if not (pin.isdigit() and len(pin) == 4):
        raise ValueError("El PIN es de 4 dígitos")
    sal = sal or os.urandom(16)
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), sal, iteraciones), sal, iteraciones


def verificar(pin: str, hash_: bytes, sal: bytes, iteraciones: int) -> bool:
    if not pin.isdigit():
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", pin.encode(), sal, iteraciones)
    return hmac.compare_digest(calculado, hash_)
