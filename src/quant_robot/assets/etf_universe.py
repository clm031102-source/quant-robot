from __future__ import annotations

from typing import Any

import pandas as pd

from quant_robot.assets.models import Asset


DEFAULT_CN_ETFS: tuple[tuple[str, str], ...] = (
    ("510300.SH", "沪深300 ETF"),
    ("510500.SH", "中证500 ETF"),
    ("159915.SZ", "创业板 ETF"),
    ("588000.SH", "科创50 ETF"),
    ("512100.SH", "中证1000 ETF"),
    ("512880.SH", "证券 ETF"),
    ("512690.SH", "酒 ETF"),
    ("515790.SH", "光伏 ETF"),
    ("516160.SH", "新能源 ETF"),
    ("159819.SZ", "人工智能 ETF"),
    ("511880.SH", "货币 ETF"),
)


def default_cn_etf_assets() -> list[Asset]:
    return [cn_etf_asset(symbol, name) for symbol, name in DEFAULT_CN_ETFS]


def cn_etf_assets_from_tushare_fund_basic(frame: pd.DataFrame, as_of: str | None = None) -> list[Asset]:
    filtered = filter_tushare_cn_etf_fund_basic(frame, as_of=as_of)
    assets = [cn_etf_asset(str(row["symbol"]), str(row.get("name", ""))) for _, row in filtered.iterrows()]
    return sorted(assets, key=lambda asset: asset.asset_id)


def filter_tushare_cn_etf_fund_basic(frame: pd.DataFrame, as_of: str | None = None) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    required = ["symbol", "name", "market", "status"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Tushare fund_basic universe is missing columns: {', '.join(missing)}")
    source = frame.copy()
    symbol = source["symbol"].astype(str).str.upper()
    market = source["market"].astype(str).str.upper()
    etf_mask = source["is_etf"] if "is_etf" in source.columns else _contains_etf(source)
    exchange_mask = symbol.str.endswith((".SH", ".SZ"))
    base_mask = market.eq("E") & etf_mask.astype(bool) & exchange_mask
    if as_of:
        active_mask = _listed_on_date(source, as_of)
    elif "is_active" in source.columns:
        active_mask = source["is_active"].astype(bool)
    else:
        active_mask = source["status"].astype(str).str.upper().eq("L")
    filtered = source[base_mask & active_mask].copy()
    filtered["symbol"] = symbol[filtered.index]
    return filtered.sort_values(["symbol"]).reset_index(drop=True)


def resolve_cn_etf_asset(symbol: str) -> Asset:
    normalized = _normalize_symbol(symbol)
    names = {_normalize_symbol(item_symbol): name for item_symbol, name in DEFAULT_CN_ETFS}
    return cn_etf_asset(normalized, names.get(normalized, "A股ETF"))


def cn_etf_asset(symbol: str, name: str = "") -> Asset:
    normalized = _normalize_symbol(symbol)
    exchange = _exchange_for_symbol(normalized)
    return Asset(
        asset_id=f"CN_ETF_{exchange}_{normalized.split('.', 1)[0]}",
        symbol=normalized,
        market="CN_ETF",
        exchange=exchange,
        asset_type="etf",
        currency="CNY",
        timezone="Asia/Shanghai",
        calendar=exchange,
        name=name,
        lot_size=100.0,
        tick_size=0.001,
    )


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if "." not in value:
        if value.startswith(("15", "16")):
            return f"{value}.SZ"
        return f"{value}.SH"
    return value


def _exchange_for_symbol(symbol: str) -> str:
    suffix = symbol.rsplit(".", 1)[-1]
    if suffix == "SH":
        return "XSHG"
    if suffix == "SZ":
        return "XSHE"
    raise ValueError(f"Unsupported CN ETF symbol suffix: {symbol}")


def _contains_etf(frame: pd.DataFrame) -> pd.Series:
    columns = [column for column in ["name", "fund_type", "invest_type", "type"] if column in frame.columns]
    if not columns:
        return pd.Series([False] * len(frame), index=frame.index)
    haystack = frame[columns].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
    return haystack.str.contains("ETF", regex=False)


def _listed_on_date(frame: pd.DataFrame, as_of: str) -> pd.Series:
    as_of_date = pd.to_datetime(as_of).date()
    list_dates = _date_series(frame.get("list_date"), frame.index)
    delist_dates = _date_series(frame.get("delist_date"), frame.index)
    return list_dates.notna() & (list_dates <= as_of_date) & (delist_dates.isna() | (delist_dates > as_of_date))


def _date_series(values: Any, index: pd.Index) -> pd.Series:
    if values is None:
        return pd.Series([None] * len(index), index=index)
    parsed = pd.to_datetime(pd.Series(list(values), index=index), errors="coerce")
    return parsed.map(lambda value: value.date() if pd.notna(value) else None)
