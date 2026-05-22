from __future__ import annotations

import importlib.util
from collections.abc import Callable
from typing import Any

from quant_robot.config.secrets import get_env_secret
from quant_robot.data.readiness import check_parquet_readiness


PROVIDERS = {
    "tushare": {"package": "tushare", "credential": "TUSHARE_TOKEN", "markets": ["CN"]},
    "akshare": {"package": "akshare", "credential": None, "markets": ["CN", "HK", "US"]},
    "yfinance": {"package": "yfinance", "credential": None, "markets": ["HK", "US"]},
    "ccxt": {"package": "ccxt", "credential": None, "markets": ["CRYPTO"]},
}


def build_provider_status(
    dependency_available: Callable[[str], bool] | None = None,
    secret_loader: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    dependency_available = dependency_available or _dependency_available
    secret_loader = secret_loader or get_env_secret
    providers = {}
    for name, config in PROVIDERS.items():
        dependency_ready = dependency_available(str(config["package"]))
        credential = config["credential"]
        credential_ready = True if credential is None else bool(secret_loader(str(credential)))
        missing = []
        if not dependency_ready:
            missing.append(f"{config['package']} package is not installed")
        if credential is not None and not credential_ready:
            missing.append(f"{credential} is not set")
        providers[name] = {
            "ready": dependency_ready and credential_ready,
            "package": config["package"],
            "markets": config["markets"],
            "requires_token": credential is not None,
            "credential": credential,
            "missing": missing,
        }
    return {
        "providers": providers,
        "parquet": check_parquet_readiness(dependency_available),
    }


def _dependency_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
