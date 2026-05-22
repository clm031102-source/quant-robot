from __future__ import annotations

import os


class SecretMissingError(RuntimeError):
    pass


def get_env_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def require_env_secret(name: str) -> str:
    value = get_env_secret(name)
    if value is None:
        raise SecretMissingError(f"Required environment secret is missing: {name}")
    return value
