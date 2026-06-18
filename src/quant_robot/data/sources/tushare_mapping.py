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
    "management",
    "custodian",
    "fund_type",
    "found_date",
    "due_date",
    "list_date",
    "issue_date",
    "delist_date",
    "status",
    "invest_type",
    "type",
    "market",
    "is_active",
    "is_exchange_traded",
    "is_etf",
]

FUND_PORTFOLIO_COLUMNS = [
    "fund_symbol",
    "known_date",
    "period_end_date",
    "stock_symbol",
    "mkv",
    "amount",
    "stk_mkv_ratio",
    "stk_float_ratio",
]

ETF_SHARE_SIZE_COLUMNS = [
    "symbol",
    "date",
    "name",
    "total_share",
    "total_size",
    "nav",
    "close",
    "exchange",
]

_MONEYFLOW_NUMERIC_COLUMNS = [column for column in MONEYFLOW_COLUMNS if column not in {"symbol", "date"}]
_DAILY_BASIC_NUMERIC_COLUMNS = [column for column in DAILY_BASIC_COLUMNS if column not in {"symbol", "date"}]
_FUND_PORTFOLIO_NUMERIC_COLUMNS = ["mkv", "amount", "stk_mkv_ratio", "stk_float_ratio"]
_ETF_SHARE_SIZE_NUMERIC_COLUMNS = ["total_share", "total_size", "nav", "close"]


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


def map_tushare_fund_basic(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=FUND_BASIC_COLUMNS)
    _require_columns(frame, ["ts_code", "name", "status", "market"], "tushare fund_basic")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "name": source["name"],
            "management": _optional_text(source, "management"),
            "custodian": _optional_text(source, "custodian"),
            "fund_type": _optional_text(source, "fund_type"),
            "found_date": _optional_date(source, "found_date"),
            "due_date": _optional_date(source, "due_date"),
            "list_date": _optional_date(source, "list_date"),
            "issue_date": _optional_date(source, "issue_date"),
            "delist_date": _optional_date(source, "delist_date"),
            "status": _optional_text(source, "status"),
            "invest_type": _optional_text(source, "invest_type"),
            "type": _optional_text(source, "type"),
            "market": _optional_text(source, "market"),
        }
    )
    mapped["is_active"] = mapped["status"].astype(str).str.upper().eq("L")
    mapped["is_exchange_traded"] = mapped["market"].astype(str).str.upper().eq("E")
    mapped["is_etf"] = _fund_basic_etf_mask(mapped)
    return mapped[FUND_BASIC_COLUMNS].sort_values(["symbol"]).reset_index(drop=True)


def map_tushare_fund_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=FUND_PORTFOLIO_COLUMNS)
    _require_columns(frame, ["ts_code", "ann_date", "end_date", "symbol"], "tushare fund_portfolio")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "fund_symbol": source["ts_code"],
            "known_date": pd.to_datetime(source["ann_date"], format="%Y%m%d", errors="coerce").dt.date,
            "period_end_date": pd.to_datetime(source["end_date"], format="%Y%m%d", errors="coerce").dt.date,
            "stock_symbol": source["symbol"],
        }
    )
    for column in _FUND_PORTFOLIO_NUMERIC_COLUMNS:
        mapped[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    return mapped[FUND_PORTFOLIO_COLUMNS].sort_values(
        ["fund_symbol", "known_date", "period_end_date", "stock_symbol"]
    ).reset_index(drop=True)


def map_tushare_etf_share_size(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=ETF_SHARE_SIZE_COLUMNS)
    _require_columns(frame, ["ts_code", "trade_date"], "tushare etf_share_size")
    source = frame.copy()
    mapped = pd.DataFrame(
        {
            "symbol": source["ts_code"],
            "date": pd.to_datetime(source["trade_date"], format="%Y%m%d").dt.date,
            "name": _optional_text(source, "etf_name"),
            "exchange": _optional_text(source, "exchange"),
        }
    )
    for column in _ETF_SHARE_SIZE_NUMERIC_COLUMNS:
        mapped[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    mapped["total_share"] = mapped["total_share"] * 10000.0
    mapped["total_size"] = mapped["total_size"] * 10000.0
    return mapped[ETF_SHARE_SIZE_COLUMNS].sort_values(["date", "symbol"]).reset_index(drop=True)


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
        }
    ).sort_values(["asset_id"]).reset_index(drop=True)


def _optional_text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _optional_date(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _optional_text(frame, column).astype("string").replace({"": pd.NA, "nan": pd.NA, "NaT": pd.NA})
    return pd.to_datetime(values, format="%Y%m%d", errors="coerce").dt.date


def _fund_basic_etf_mask(frame: pd.DataFrame) -> pd.Series:
    text_columns = [column for column in ["name", "fund_type", "invest_type", "type"] if column in frame.columns]
    haystack = frame[text_columns].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
    return haystack.str.contains("ETF", regex=False)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} data is missing columns: {', '.join(missing)}")
