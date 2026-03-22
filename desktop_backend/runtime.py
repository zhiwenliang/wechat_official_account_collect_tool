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
    env_port = os.getenv(ENV_PORT_NAME)
    candidates: list[int] = []

    if env_port:
        try:
            candidates.append(int(env_port))
        except ValueError:
            pass

    if preferred_port is not None:
        candidates.append(int(preferred_port))

    candidates.append(DEFAULT_PORT)

    for candidate in candidates:
        if candidate <= 0:
            return DEFAULT_PORT
        if _is_port_available(host, candidate):
            return candidate

    return DEFAULT_PORT
