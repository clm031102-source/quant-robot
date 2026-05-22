from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from quant_robot.config.secrets import get_env_secret


def check_tushare_readiness(
    dependency_available: Callable[[str], bool] | None = None,
    secret_loader: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    dependency_available = dependency_available or _dependency_available
    secret_loader = secret_loader or get_env_secret
    missing = []
    if not dependency_available("tushare"):
        missing.append("tushare package is not installed")
    if not secret_loader("TUSHARE_TOKEN"):
        missing.append("TUSHARE_TOKEN is not set")
    return {
        "source": "tushare",
        "ready": not missing,
        "missing": missing,
    }


def check_parquet_readiness(dependency_available: Callable[[str], bool] | None = None) -> dict[str, Any]:
    dependency_available = dependency_available or _dependency_available
    ready = dependency_available("pyarrow") or dependency_available("fastparquet")
    return {
        "feature": "parquet",
        "ready": ready,
        "missing": [] if ready else ["pyarrow or fastparquet package is not installed"],
    }


def _dependency_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
