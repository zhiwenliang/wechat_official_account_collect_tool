from __future__ import annotations


def parse_int(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(query.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def parse_bool(query: dict[str, list[str]], key: str) -> bool:
    value = query.get(key, ["false"])[0]
    return str(value).lower() in {"1", "true", "yes", "on"}
