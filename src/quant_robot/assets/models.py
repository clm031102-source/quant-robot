from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Asset:
    asset_id: str
    symbol: str
    market: str
    exchange: str
    asset_type: str
    currency: str
    timezone: str
    calendar: str
    name: str = ""
    is_active: bool = True
    lot_size: float = 1.0
    tick_size: float = 0.01

    def __post_init__(self) -> None:
        required = {
            "asset_id": self.asset_id,
            "symbol": self.symbol,
            "market": self.market,
            "exchange": self.exchange,
            "asset_type": self.asset_type,
            "currency": self.currency,
            "timezone": self.timezone,
            "calendar": self.calendar,
        }
        empty = [name for name, value in required.items() if not str(value).strip()]
        if empty:
            raise ValueError(f"Asset required fields are empty: {', '.join(empty)}")
