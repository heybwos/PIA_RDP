"""[camara].url (WiFi de la facultad) es la principal; url_respaldo (hotspot) se usa si la principal no contesta."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pia import camara  # noqa: E402
from pia.config import Config  # noqa: E402


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _cfg(url: str, respaldo: str) -> Config:
    return Config({"camara": {"fuente": "url", "url": url, "url_respaldo": respaldo}})


def test_principal_que_contesta_gana():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0)); srv.listen()
        principal = f"http://127.0.0.1:{srv.getsockname()[1]}/video"
        assert camara.elegir_url(_cfg(principal, f"http://127.0.0.1:{_puerto_libre()}/video")) == principal


def test_sin_principal_se_usa_el_respaldo():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0)); srv.listen()
        respaldo = f"http://127.0.0.1:{srv.getsockname()[1]}/video"
        assert camara.elegir_url(_cfg(f"http://127.0.0.1:{_puerto_libre()}/video", respaldo)) == respaldo
        assert camara.elegir_url(_cfg("", respaldo)) == respaldo  # principal aún sin llenar


def test_ninguna_contesta_queda_la_principal():
    principal = f"http://127.0.0.1:{_puerto_libre()}/video"
    assert camara.elegir_url(_cfg(principal, f"http://127.0.0.1:{_puerto_libre()}/video")) == principal
