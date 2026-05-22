from __future__ import annotations

import pandas as pd


def map_tushare_daily(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
    _require_columns(frame, required, "tushare daily")
    mapped = pd.DataFrame(
        {
            "symbol": frame["ts_code"],
            "date": pd.to_datetime(frame["trade_date"], format="%Y%m%d").dt.date,
            "open": pd.to_numeric(frame["open"], errors="coerce"),
            "high": pd.to_numeric(frame["high"], errors="coerce"),
            "low": pd.to_numeric(frame["low"], errors="coerce"),
            "close": pd.to_numeric(frame["close"], errors="coerce"),
            "volume": pd.to_numeric(frame["vol"], errors="coerce") * 100.0,
            "amount": pd.to_numeric(frame["amount"], errors="coerce") * 1000.0,
        }
    )
    return mapped.sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_adj_factor(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, ["ts_code", "trade_date", "adj_factor"], "tushare adj_factor")
    return pd.DataFrame(
        {
            "symbol": frame["ts_code"],
            "date": pd.to_datetime(frame["trade_date"], format="%Y%m%d").dt.date,
            "adj_factor": pd.to_numeric(frame["adj_factor"], errors="coerce"),
        }
    ).sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_trade_cal(frame: pd.DataFrame, open_only: bool = True) -> pd.DataFrame:
    _require_columns(frame, ["cal_date", "is_open"], "tushare trade_cal")
    source = frame.copy()
    if open_only:
        source = source[source["is_open"].astype(int) == 1]
    mapped = pd.DataFrame(
        {
            "exchange": source.get("exchange", "SSE"),
            "date": pd.to_datetime(source["cal_date"], format="%Y%m%d").dt.date,
            "is_open": source["is_open"].astype(int),
        }
    )
    return mapped.sort_values(["date"]).reset_index(drop=True)


def map_tushare_stock_basic(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["ts_code", "symbol", "name", "exchange", "list_status"]
    _require_columns(frame, required, "tushare stock_basic")
    exchange = frame["exchange"].map({"SSE": "XSHG", "SZSE": "XSHE"}).fillna(frame["exchange"])
    return pd.DataFrame(
        {
            "asset_id": "CN_" + exchange + "_" + frame["symbol"],
            "symbol": frame["ts_code"],
            "market": "CN",
            "exchange": exchange,
            "asset_type": "stock",
            "currency": "CNY",
            "timezone": "Asia/Shanghai",
            "calendar": exchange,
            "name": frame["name"],
            "is_active": frame["list_status"] == "L",
        }
    ).sort_values(["asset_id"]).reset_index(drop=True)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} data is missing columns: {', '.join(missing)}")
