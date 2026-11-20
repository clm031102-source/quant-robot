"""Clean per-symbol Parquet market data cache with fast incremental updates."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.storage.atomic import atomic_write

CACHE_COLUMNS = ["date", "symbol", "market", "open", "high", "low", "close", "adj_close", "volume", "amount", "source"]


def safe_symbol_filename(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "_").replace(".", "_") + ".parquet"


class MarketCache:
    """Stores clean, deduplicated daily OHLCV bars per (market, symbol)."""

    def __init__(self, cache_root: str | Path) -> None:
        self.root = Path(cache_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def symbol_path(self, market: str, symbol: str) -> Path:
        return self.root / market.upper() / safe_symbol_filename(symbol)

    def load_symbol(self, market: str, symbol: str) -> pd.DataFrame:
        path = self.symbol_path(market, symbol)
        if not path.is_file():
            return pd.DataFrame(columns=CACHE_COLUMNS)
        frame = pd.read_parquet(path)
        if frame.empty:
            return pd.DataFrame(columns=CACHE_COLUMNS)
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        return frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)

    def last_date(self, market: str, symbol: str) -> date | None:
        frame = self.load_symbol(market, symbol)
        if frame.empty:
            return None
        return max(frame["date"])

    def upsert_symbol(self, market: str, symbol: str, incoming: pd.DataFrame) -> pd.DataFrame:
        cleaned = _clean_bars(incoming, market=market, symbol=symbol)
        existing = self.load_symbol(market, symbol)
        if existing.empty:
            merged = cleaned
        elif cleaned.empty:
            merged = existing
        else:
            merged = pd.concat([existing, cleaned], ignore_index=True)
            merged = merged.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
        path = self.symbol_path(market, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, lambda tmp: merged.to_parquet(tmp, index=False))
        return merged

    def load_universe(
        self,
        market: str,
        symbols: list[str],
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        pieces: list[pd.DataFrame] = []
        for symbol in symbols:
            df = self.load_symbol(market, symbol)
            if not df.empty:
                pieces.append(df)
        if not pieces:
            return pd.DataFrame(columns=CACHE_COLUMNS)
        combined = pd.concat(pieces, ignore_index=True)
        combined["date"] = pd.to_datetime(combined["date"]).dt.date
        if start_date:
            start_d = pd.to_datetime(start_date).date()
            combined = combined[combined["date"] >= start_d]
        if end_date:
            end_d = pd.to_datetime(end_date).date()
            combined = combined[combined["date"] <= end_d]
        return combined.sort_values(["date", "symbol"]).reset_index(drop=True)

    def summary(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self.root.exists():
            return rows
        for market_dir in sorted(p for p in self.root.iterdir() if p.is_dir()):
            for pq in sorted(market_dir.glob("*.parquet")):
                try:
                    df = pd.read_parquet(pq, columns=["date", "symbol", "source"])
                except Exception:
                    continue
                if df.empty:
                    continue
                dates = pd.to_datetime(df["date"]).dt.date
                rows.append(
                    {
                        "market": market_dir.name,
                        "symbol": str(df["symbol"].iloc[0]),
                        "rows": int(len(df)),
                        "first_date": str(dates.min()),
                        "last_date": str(dates.max()),
                        "source": str(df["source"].iloc[-1]),
                    }
                )
        return rows


def _clean_bars(frame: pd.DataFrame, *, market: str, symbol: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=CACHE_COLUMNS)
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["symbol"] = symbol.strip().upper()
    df["market"] = market.strip().upper()
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "adj_close" not in df.columns or df["adj_close"].isna().all():
        df["adj_close"] = df["close"]
    else:
        df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce").fillna(df["close"])
    if "amount" not in df.columns:
        df["amount"] = df["close"] * df["volume"]
    else:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(df["close"] * df["volume"])
    if "source" not in df.columns:
        df["source"] = "unknown"
    valid = df.dropna(subset=["date", "open", "high", "low", "close", "adj_close"])
    valid = valid[(valid["close"] > 0) & (valid["open"] > 0) & (valid["adj_close"] > 0)].copy()
    return valid[CACHE_COLUMNS].sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
