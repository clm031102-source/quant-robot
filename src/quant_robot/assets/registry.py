from __future__ import annotations

from collections.abc import Iterable

from quant_robot.assets.models import Asset


class AssetRegistry:
    def __init__(self, assets: Iterable[Asset]) -> None:
        self._assets = {}
        for asset in assets:
            if asset.asset_id in self._assets:
                raise ValueError(f"Duplicate asset_id: {asset.asset_id}")
            self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> Asset:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"Unknown asset_id: {asset_id}") from exc

    def all(self) -> list[Asset]:
        return list(self._assets.values())
