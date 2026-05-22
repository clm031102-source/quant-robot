from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.util import find_spec

import pandas as pd

from quant_robot.assets.models import Asset


class OptionalDependencyError(ImportError):
    pass


@dataclass(frozen=True, slots=True)
class FetchRequest:
    start: str
    end: str
    frequency: str = "1d"
    adjustment: str = "none"


class MarketDataAdapter(ABC):
    name: str

    @abstractmethod
    def supports(self, asset: Asset) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        raise NotImplementedError


def require_optional_dependency(module_name: str, package_name: str | None = None) -> None:
    if find_spec(module_name) is None:
        install_name = package_name or module_name
        raise OptionalDependencyError(f"Adapter requires optional dependency: {install_name}")
