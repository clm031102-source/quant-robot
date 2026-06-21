from __future__ import annotations

import pandas as pd


MONEYFLOW_COLUMNS = [
    "symbol",
    "date",
    "buy_sm_vol",
    "buy_sm_amount",
    "sell_sm_vol",
    "sell_sm_amount",
    "buy_md_vol",
    "buy_md_amount",
    "sell_md_vol",
    "sell_md_amount",
    "buy_lg_vol",
    "buy_lg_amount",
    "sell_lg_vol",
    "sell_lg_amount",
    "buy_elg_vol",
    "buy_elg_amount",
    "sell_elg_vol",
    "sell_elg_amount",
    "net_mf_vol",
    "net_mf_amount",
]

DAILY_BASIC_COLUMNS = [
    "symbol",
    "date",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
]

FUND_BASIC_COLUMNS = [
    "symbol",
    "name",
    "market",
    "status",
    "fund_type",
    "type",
    "invest_type",
    "is_etf",
    "list_date",
    "delist_date",
    "found_date",
]

STOCK_BASIC_COLUMNS = [
    "asset_id",
    "symbol",
    "market",
    "exchange",
    "asset_type",
    "currency",
    "timezone",
    "calendar",
    "name",
    "is_active",
    "area",
    "industry",
    "stock_market",
    "list_date",
    "delist_date",
    "is_hs",
]

_MONEYFLOW_NUMERIC_COLUMNS = [column for column in MONEYFLOW_COLUMNS if column not in {"symbol", "date"}]
_DAILY_BASIC_NUMERIC_COLUMNS = [column for column in DAILY_BASIC_COLUMNS if column not in {"symbol", "date"}]


def map_tushare_daily(frame: pd.DataFrame) -> pd.DataFrame:
    output_columns = ["symbol", "date", "open", "high", "low", "close", "volume", "amount"]
    if frame.empty:
        return pd.DataFrame(columns=output_columns)
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
    return mapped[output_columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_daily_basic(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=DAILY_BASIC_COLUMNS)
    _require_columns(frame, ["ts_code", "trade_date"], "tushare daily_basic")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "date": pd.to_datetime(source["trade_date"], format="%Y%m%d").dt.date,
        }
    )
    for column in _DAILY_BASIC_NUMERIC_COLUMNS:
        mapped[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    return mapped[DAILY_BASIC_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_fund_basic(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=FUND_BASIC_COLUMNS)
    _require_columns(frame, ["ts_code", "name"], "tushare fund_basic")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "name": _optional_text(source, "name"),
            "market": _optional_text(source, "market"),
            "status": _optional_text(source, "status"),
            "fund_type": _optional_text(source, "fund_type"),
            "type": _optional_text(source, "type"),
            "invest_type": _optional_text(source, "invest_type"),
            "list_date": _optional_date(source, "list_date"),
            "delist_date": _optional_date(source, "delist_date"),
            "found_date": _optional_date(source, "found_date"),
        }
    )
    mapped["is_etf"] = _fund_basic_is_etf(mapped)
    return mapped[FUND_BASIC_COLUMNS].sort_values(["symbol"]).reset_index(drop=True)


def map_tushare_moneyflow(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=MONEYFLOW_COLUMNS)
    _require_columns(frame, ["ts_code", "trade_date"], "tushare moneyflow")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "date": pd.to_datetime(source["trade_date"], format="%Y%m%d").dt.date,
        }
    )
    for column in _MONEYFLOW_NUMERIC_COLUMNS:
        mapped[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    return mapped[MONEYFLOW_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_adj_factor(frame: pd.DataFrame) -> pd.DataFrame:
    output_columns = ["symbol", "date", "adj_factor"]
    if frame.empty:
        return pd.DataFrame(columns=output_columns)
    _require_columns(frame, ["ts_code", "trade_date", "adj_factor"], "tushare adj_factor")
    return pd.DataFrame(
        {
            "symbol": frame["ts_code"],
            "date": pd.to_datetime(frame["trade_date"], format="%Y%m%d").dt.date,
            "adj_factor": pd.to_numeric(frame["adj_factor"], errors="coerce"),
        }
    )[output_columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def map_tushare_trade_cal(frame: pd.DataFrame, open_only: bool = True) -> pd.DataFrame:
    output_columns = ["exchange", "date", "is_open"]
    if frame.empty:
        return pd.DataFrame(columns=output_columns)
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
    return mapped[output_columns].sort_values(["date"]).reset_index(drop=True)


def map_tushare_stock_basic(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=STOCK_BASIC_COLUMNS)
    required = ["ts_code", "symbol", "name", "exchange", "list_status"]
    _require_columns(frame, required, "tushare stock_basic")
    exchange = frame["exchange"].map({"SSE": "XSHG", "SZSE": "XSHE", "BSE": "XBEI"}).fillna(frame["exchange"])
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
            "area": _optional_text(frame, "area"),
            "industry": _optional_text(frame, "industry"),
            "stock_market": _optional_text(frame, "market"),
            "list_date": _optional_date(frame, "list_date"),
            "delist_date": _optional_date(frame, "delist_date"),
            "is_hs": _optional_text(frame, "is_hs"),
        }
    )[STOCK_BASIC_COLUMNS].sort_values(["asset_id"]).reset_index(drop=True)


def _optional_text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str)


def _optional_date(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([pd.NaT] * len(frame), index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").dt.date


def _fund_basic_is_etf(frame: pd.DataFrame) -> pd.Series:
    columns = ["name", "fund_type", "type", "invest_type"]
    haystack = frame[columns].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
    return haystack.str.contains("ETF", regex=False)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} data is missing columns: {', '.join(missing)}")
