"""Fault-tolerant incremental daily market data updater with automatic retries and backfill."""
from __future__ import annotations

from datetime import date, timedelta
import time
from typing import Any, Callable

import pandas as pd

from quant_robot.assets.universe import resolve_asset
from quant_robot.data.adapters.base import FetchRequest
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.adapters.yfinance_adapter import YFinanceAdapter
from quant_robot.storage.market_cache import MarketCache


def fetch_symbol_bars(
    market: str,
    symbol: str,
    *,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
    retry_delay: float = 1.5,
    tushare_adapter: TushareAdapter | None = None,
    yfinance_adapter: YFinanceAdapter | None = None,
) -> pd.DataFrame:
    """Fetch daily OHLCV bars for one symbol with exponential-backoff retries."""
    market_upper = market.strip().upper()
    asset = resolve_asset(symbol, market_upper)

    def _call() -> pd.DataFrame:
        if market_upper in {"CN_ETF", "CN"}:
            return _fetch_cn_tushare(asset, start_date, end_date, adapter=tushare_adapter)
        if market_upper in {"US_ETF", "US", "HK"}:
            return _fetch_yfinance(asset, start_date, end_date, adapter=yfinance_adapter)
        raise ValueError(f"Unsupported live update market: {market_upper}")

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            frame = _call()
            return frame
        except Exception as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(retry_delay * (2**attempt))
    assert last_error is not None
    raise RuntimeError(f"Failed to fetch {market_upper}:{symbol} after {max_retries} attempts: {last_error}") from last_error


def update_universe_cache(
    cache: MarketCache,
    market: str,
    symbols: list[str],
    *,
    default_start: str = "2020-01-01",
    end_date: str | None = None,
    overlap_days: int = 7,
    full_refresh: bool = False,
    fetcher: Callable[..., pd.DataFrame] = fetch_symbol_bars,
) -> dict[str, Any]:
    """Incrementally update cache for every symbol. Automatically catches up any missed days."""
    today = pd.to_datetime(end_date).date() if end_date else date.today()
    end_str = today.isoformat()
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for symbol in symbols:
        sym = symbol.strip().upper()
        last = None if full_refresh else cache.last_date(market, sym)
        if last is not None:
            # Overlap a few days to catch dividend/split revisions cleanly; fetch full history if adj_factor shifts.
            fetch_start = max(pd.to_datetime(default_start).date(), last - timedelta(days=overlap_days)).isoformat()
        else:
            fetch_start = default_start

        try:
            incoming = fetcher(market, sym, start_date=fetch_start, end_date=end_str)
            if not incoming.empty:
                # If corporate action/split shifted adj_close on overlap dates (common with yfinance),
                # automatically refresh full history so the entire adj_close series stays consistent.
                if last is not None and _adj_close_shifted(cache.load_symbol(market, sym), incoming):
                    incoming = fetcher(market, sym, start_date=default_start, end_date=end_str)
                    cache.symbol_path(market, sym).unlink(missing_ok=True)
                merged = cache.upsert_symbol(market, sym, incoming)
                rows_added = len(incoming)
            else:
                merged = cache.load_symbol(market, sym)
                rows_added = 0
            results.append(
                {
                    "market": market.upper(),
                    "symbol": sym,
                    "status": "ok",
                    "fetched_rows": int(rows_added),
                    "total_rows": int(len(merged)),
                    "first_date": str(merged["date"].min()) if not merged.empty else None,
                    "last_date": str(merged["date"].max()) if not merged.empty else None,
                }
            )
        except Exception as exc:
            existing = cache.load_symbol(market, sym)
            errors.append({"market": market.upper(), "symbol": sym, "error": str(exc)})
            results.append(
                {
                    "market": market.upper(),
                    "symbol": sym,
                    "status": "error_using_cache" if not existing.empty else "error",
                    "error": str(exc),
                    "total_rows": int(len(existing)),
                    "last_date": str(existing["date"].max()) if not existing.empty else None,
                }
            )
    return {
        "market": market.upper(),
        "updated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "ok_count": sum(1 for r in results if r["status"] == "ok"),
        "error_count": len(errors),
        "symbols": results,
        "errors": errors,
    }


def _fetch_cn_tushare(
    asset,
    start_date: str,
    end_date: str,
    *,
    adapter: TushareAdapter | None = None,
) -> pd.DataFrame:
    ts_adapter = adapter or TushareAdapter(max_retries=3, retry_sleep_seconds=1.0, request_sleep_seconds=0.15)
    req = FetchRequest(start=start_date, end=end_date, frequency="1d")
    bars = ts_adapter.fetch_ohlcv(asset, req)
    if bars.empty:
        return bars
    bars = bars.copy()
    # Apply Tushare adj_factor if available so splits & dividends are reflected in adj_close.
    try:
        if asset.market.upper() == "CN_ETF":
            adj_raw = ts_adapter._call(
                ts_adapter.client.fund_adj,
                ts_code=asset.symbol,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
        else:
            adj_raw = ts_adapter.fetch_adj_factor(asset.symbol, start_date, end_date)
        if adj_raw is not None and not adj_raw.empty and "adj_factor" in adj_raw.columns:
            adj = adj_raw.copy()
            date_col = "trade_date" if "trade_date" in adj.columns else "date"
            adj["date"] = pd.to_datetime(adj[date_col]).dt.date
            adj["adj_factor"] = pd.to_numeric(adj["adj_factor"], errors="coerce")
            adj = adj[["date", "adj_factor"]].dropna().drop_duplicates("date", keep="last").sort_values("date")
            if not adj.empty:
                bars = bars.merge(adj, on="date", how="left")
                bars["adj_factor"] = bars["adj_factor"].ffill().bfill().fillna(1.0)
                # Use backward-adjusted total-return price (close * adj_factor) so historical values
                # remain invariant across incremental updates when new dividends/splits occur.
                bars["adj_close"] = bars["close"] * bars["adj_factor"]
                bars = bars.drop(columns=["adj_factor"])
    except Exception:
        # If adj_factor endpoint is unavailable for a symbol, fall back cleanly to raw close.
        pass
    bars["source"] = "tushare"
    return bars


def _fetch_yfinance(
    asset,
    start_date: str,
    end_date: str,
    *,
    adapter: YFinanceAdapter | None = None,
) -> pd.DataFrame:
    yf_adapter = adapter or YFinanceAdapter()
    # yfinance end parameter is exclusive, so add 1 day to include end_date cleanly.
    end_exclusive = (pd.to_datetime(end_date).date() + timedelta(days=1)).isoformat()
    req = FetchRequest(start=start_date, end=end_exclusive, frequency="1d")
    bars = yf_adapter.fetch_ohlcv(asset, req)
    if bars.empty:
        return bars
    bars = bars.copy()
    end_d = pd.to_datetime(end_date).date()
    bars = bars[bars["date"] <= end_d].copy()
    bars["source"] = "yfinance"
    return bars


def _adj_close_shifted(existing: pd.DataFrame, incoming: pd.DataFrame, tol: float = 1e-3) -> bool:
    if existing.empty or incoming.empty:
        return False
    left = existing[["date", "adj_close"]].copy()
    right = incoming[["date", "adj_close"]].copy()
    left["date"] = pd.to_datetime(left["date"]).dt.date
    right["date"] = pd.to_datetime(right["date"]).dt.date
    merged = left.merge(right, on="date", suffixes=("_old", "_new"))
    if merged.empty:
        return False
    old_vals = pd.to_numeric(merged["adj_close_old"], errors="coerce")
    new_vals = pd.to_numeric(merged["adj_close_new"], errors="coerce")
    valid = (old_vals > 0) & (new_vals > 0)
    if not valid.any():
        return False
    rel_diff = ((new_vals[valid] - old_vals[valid]).abs() / old_vals[valid]).max()
    return bool(rel_diff > tol)
