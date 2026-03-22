from __future__ import annotations

import argparse

from .runtime import DEFAULT_HOST, DEFAULT_PORT
from .server import DesktopBackendServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the desktop backend sidecar server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred port to bind.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    server = DesktopBackendServer(host=args.host, port=args.port)

    try:
        server.start()
        print(f"desktop-backend listening on http://{server.host}:{server.port}")
        server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
