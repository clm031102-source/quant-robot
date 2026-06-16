from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path


class SecretMissingError(RuntimeError):
    pass


def get_env_secret(name: str, dotenv_paths: Iterable[str | Path] | None = None) -> str | None:
    value = os.environ.get(name)
    stripped = _strip_secret(value)
    if stripped is not None:
        return stripped
    paths = _default_dotenv_paths() if dotenv_paths is None else dotenv_paths
    return _get_dotenv_secret(name, paths)


def require_env_secret(name: str) -> str:
    value = get_env_secret(name)
    if value is None:
        raise SecretMissingError(f"Required environment secret is missing: {name}")
    return value


def _get_dotenv_secret(name: str, dotenv_paths: Iterable[str | Path]) -> str | None:
    for path_value in dotenv_paths:
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            key, value = _parse_dotenv_line(line)
            if key == name:
                stripped = _strip_secret(value)
                if stripped is not None:
                    return stripped
    return None


def _default_dotenv_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate not in paths:
            paths.append(candidate)
    return tuple(paths)


def _parse_dotenv_line(line: str) -> tuple[str | None, str | None]:
    text = line.strip()
    if not text or text.startswith("#"):
        return None, None
    if text.startswith("export "):
        text = text[len("export ") :].strip()
    if "=" not in text:
        return None, None
    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None, None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def _strip_secret(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
