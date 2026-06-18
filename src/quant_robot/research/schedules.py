from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


def rebalance_phase_dates(dates: Iterable[object], *, interval: int, offset: int = 0) -> list[date]:
    if interval < 1:
        raise ValueError("interval must be at least 1")
    if offset < 0 or offset >= interval:
        raise ValueError("offset must be between 0 and interval - 1")
    normalized = sorted({pd.to_datetime(item).date() for item in dates})
    return normalized[offset::interval]
