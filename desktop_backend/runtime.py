from __future__ import annotations

import os
import socket

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 0
ENV_PORT_NAME = "DESKTOP_BACKEND_PORT"


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def select_runtime_port(host: str = DEFAULT_HOST, preferred_port: int | None = None) -> int:
    preferred = _coerce_port(preferred_port)
    if preferred is not None and _is_port_available(host, preferred):
        return preferred

    env_port = _coerce_port(os.getenv(ENV_PORT_NAME))
    if env_port is not None and _is_port_available(host, env_port):
        return env_port

    return DEFAULT_PORT


def _coerce_port(value: object) -> int | None:
    try:
        port = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return port if port > 0 else None
