from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.sources.tushare_mapping import FUND_PORTFOLIO_COLUMNS
from quant_robot.storage.dataset_store import DatasetStore


ETF_MONEYFLOW_BASKET_COLUMNS = [
    "etf_asset_id",
    "etf_symbol",
    "stock_asset_id",
    "stock_symbol",
    "weight",
    "known_date",
    "end_date",
    "source",
    "portfolio_period_end_date",
    "holding_mkv",
    "holding_amount",
    "stk_mkv_ratio",
    "stk_float_ratio",
]


class TushareFundPortfolioAdapter(Protocol):
    def fetch_fund_portfolio(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        ...


def run_tushare_fund_portfolio_basket_ingest(
    adapter: TushareFundPortfolioAdapter,
    etf_symbols: list[str] | tuple[str, ...],
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    resume: bool = True,
    market: str = "CN_ETF",
) -> dict[str, object]:
    market = market.upper()
    if market != "CN_ETF":
        raise ValueError(f"Unsupported Tushare fund_portfolio basket market: {market}")
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    symbols = sorted({str(symbol).upper() for symbol in etf_symbols})
    downloaded: list[str] = []
    skipped: list[str] = []
    reused_raw: list[str] = []
    raw_frames_by_symbol: dict[str, pd.DataFrame] = {}
    downloaded_rows_by_symbol: dict[str, int] = {}
    raw_dataset = _raw_dataset()

    for symbol in symbols:
        key = _manifest_key(symbol, start_date, end_date)
        if resume and manifest.is_completed(key):
            skipped.append(symbol)
            continue
        if resume and store.exists(raw_dataset, {"ts_code": symbol, "start_date": start_date, "end_date": end_date}):
            skipped.append(symbol)
            reused_raw.append(symbol)
            continue
        raw = adapter.fetch_fund_portfolio(symbol, start_date=start_date, end_date=end_date)
        store.write_frame(raw, raw_dataset, {"ts_code": symbol, "start_date": start_date, "end_date": end_date})
        downloaded.append(symbol)
        downloaded_rows_by_symbol[symbol] = len(raw)
        raw_frames_by_symbol[symbol] = raw

    try:
        raw_for_processing = _load_raw_frames(store, symbols, start_date, end_date, raw_frames_by_symbol)
        baskets = build_etf_moneyflow_baskets_from_fund_portfolio(raw_for_processing, eligible_etf_symbols=symbols)
        if not baskets.empty:
            _validate_baskets(baskets)
            store.write_frame(baskets, "metadata/etf_moneyflow_baskets", {"market": market})
        report = _quality_report(raw_for_processing, baskets, market)
    except Exception as exc:
        for symbol in downloaded + reused_raw:
            manifest.mark_failed(_manifest_key(symbol, start_date, end_date), reason=str(exc))
        manifest.save()
        raise

    for symbol in reused_raw:
        downloaded_rows_by_symbol[symbol] = len(
            store.read_frame(raw_dataset, {"ts_code": symbol, "start_date": start_date, "end_date": end_date})
        )
    for symbol in downloaded:
        manifest.mark_completed(_manifest_key(symbol, start_date, end_date), rows=downloaded_rows_by_symbol[symbol])
    for symbol in reused_raw:
        manifest.mark_completed(_manifest_key(symbol, start_date, end_date), rows=downloaded_rows_by_symbol[symbol])
    manifest.save()
    (output_path / "fund_portfolio_basket_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "source": "tushare",
        "dataset": "fund_portfolio_baskets",
        "market": market,
        "downloaded_symbols": downloaded,
        "skipped_symbols": skipped,
        "reused_raw_symbols": reused_raw,
        "raw_rows": int(len(raw_for_processing)),
        "processed_rows": int(len(baskets)),
        "quality_report": report,
    }


def build_etf_moneyflow_baskets_from_fund_portfolio(
    portfolio: pd.DataFrame,
    eligible_etf_symbols: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    if portfolio.empty:
        return pd.DataFrame(columns=ETF_MONEYFLOW_BASKET_COLUMNS)
    _require_columns(portfolio, ["fund_symbol", "known_date", "stock_symbol"], "Tushare fund_portfolio")
    source = portfolio.copy()
    source["fund_symbol"] = source["fund_symbol"].astype(str).str.upper()
    source["stock_symbol"] = source["stock_symbol"].astype(str).str.upper()
    source["known_date"] = pd.to_datetime(source["known_date"], errors="coerce").dt.date
    source["period_end_date"] = (
        pd.to_datetime(source["period_end_date"], errors="coerce").dt.date
        if "period_end_date" in source.columns
        else pd.NaT
    )
    if source["known_date"].isna().any():
        raise ValueError("Tushare fund_portfolio contains missing known_date values")
    if eligible_etf_symbols is not None:
        eligible = {str(symbol).upper() for symbol in eligible_etf_symbols}
        source = source[source["fund_symbol"].isin(eligible)].copy()
    if source.empty:
        return pd.DataFrame(columns=ETF_MONEYFLOW_BASKET_COLUMNS)
    for column in ["mkv", "amount", "stk_mkv_ratio", "stk_float_ratio"]:
        source[column] = pd.to_numeric(source[column], errors="coerce") if column in source.columns else pd.NA
    source["weight_basis"] = source["mkv"].where(source["mkv"] > 0, source["stk_mkv_ratio"])
    source = source[pd.to_numeric(source["weight_basis"], errors="coerce") > 0].copy()
    if source.empty:
        return pd.DataFrame(columns=ETF_MONEYFLOW_BASKET_COLUMNS)
    source["group_weight_sum"] = source.groupby(["fund_symbol", "known_date"], sort=False)["weight_basis"].transform("sum")
    source["weight"] = source["weight_basis"] / source["group_weight_sum"].where(source["group_weight_sum"] > 0)
    next_known = _next_known_date_by_fund(source)
    source["end_date"] = [
        _end_date_before(next_known.get((fund_symbol, known_date)))
        for fund_symbol, known_date in zip(source["fund_symbol"], source["known_date"], strict=True)
    ]
    rows = pd.DataFrame(
        {
            "etf_asset_id": source["fund_symbol"].map(lambda value: _asset_id_from_tushare_symbol(value, "CN_ETF")),
            "etf_symbol": source["fund_symbol"],
            "stock_asset_id": source["stock_symbol"].map(lambda value: _asset_id_from_tushare_symbol(value, "CN")),
            "stock_symbol": source["stock_symbol"],
            "weight": source["weight"],
            "known_date": source["known_date"],
            "end_date": source["end_date"],
            "source": "tushare_fund_portfolio",
            "portfolio_period_end_date": source["period_end_date"],
            "holding_mkv": source["mkv"],
            "holding_amount": source["amount"],
            "stk_mkv_ratio": source["stk_mkv_ratio"],
            "stk_float_ratio": source["stk_float_ratio"],
        }
    )
    rows = rows.dropna(subset=["weight"])
    return rows[ETF_MONEYFLOW_BASKET_COLUMNS].sort_values(
        ["etf_asset_id", "known_date", "stock_asset_id"]
    ).reset_index(drop=True)


def _load_raw_frames(
    store: DatasetStore,
    symbols: list[str],
    start_date: str,
    end_date: str,
    raw_frames_by_symbol: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    frames = []
    for symbol in symbols:
        if symbol in raw_frames_by_symbol:
            frames.append(raw_frames_by_symbol[symbol])
        elif store.exists(_raw_dataset(), {"ts_code": symbol, "start_date": start_date, "end_date": end_date}):
            frames.append(store.read_frame(_raw_dataset(), {"ts_code": symbol, "start_date": start_date, "end_date": end_date}))
    if not frames:
        return pd.DataFrame(columns=FUND_PORTFOLIO_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _next_known_date_by_fund(frame: pd.DataFrame) -> dict[tuple[str, object], object]:
    mapping: dict[tuple[str, object], object] = {}
    for fund_symbol, group in frame[["fund_symbol", "known_date"]].drop_duplicates().groupby("fund_symbol", sort=True):
        known_dates = sorted(group["known_date"].tolist())
        for index, known_date in enumerate(known_dates):
            mapping[(fund_symbol, known_date)] = known_dates[index + 1] if index + 1 < len(known_dates) else None
    return mapping


def _end_date_before(next_known: object | None) -> object:
    if next_known is None or pd.isna(next_known):
        return pd.NaT
    return pd.to_datetime(next_known).date() - pd.Timedelta(days=1)


def _asset_id_from_tushare_symbol(symbol: str, market: str) -> str:
    parts = str(symbol).upper().split(".")
    if len(parts) != 2:
        raise ValueError(f"Unsupported Tushare symbol: {symbol}")
    code, suffix = parts
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare symbol suffix: {symbol}") from exc
    return f"{market}_{exchange}_{code}"


def _validate_baskets(frame: pd.DataFrame) -> None:
    _require_columns(frame, ETF_MONEYFLOW_BASKET_COLUMNS, "ETF moneyflow baskets")
    if frame["known_date"].isna().any():
        raise ValueError("ETF moneyflow baskets contain missing known_date values")
    if frame["weight"].isna().any():
        raise ValueError("ETF moneyflow baskets contain missing weights")
    if (pd.to_numeric(frame["weight"], errors="coerce") <= 0).any():
        raise ValueError("ETF moneyflow baskets contain non-positive weights")


def _quality_report(raw: pd.DataFrame, baskets: pd.DataFrame, market: str) -> dict[str, object]:
    if baskets.empty:
        return {
            "raw_rows": int(len(raw)),
            "rows": 0,
            "market": market,
            "etfs": 0,
            "stocks": 0,
            "start_known_date": None,
            "end_known_date": None,
            "missing_known_date_rows": int(raw["known_date"].isna().sum()) if "known_date" in raw.columns else 0,
            "duplicate_rows": 0,
        }
    known_dates = pd.to_datetime(baskets["known_date"])
    return {
        "raw_rows": int(len(raw)),
        "rows": int(len(baskets)),
        "market": market,
        "etfs": int(baskets["etf_asset_id"].nunique()),
        "stocks": int(baskets["stock_asset_id"].nunique()),
        "start_known_date": known_dates.min().date().isoformat(),
        "end_known_date": known_dates.max().date().isoformat(),
        "missing_known_date_rows": int(raw["known_date"].isna().sum()) if "known_date" in raw.columns else 0,
        "duplicate_rows": int(baskets.duplicated(["etf_asset_id", "stock_asset_id", "known_date", "source"]).sum()),
    }


def _manifest_key(symbol: str, start_date: str, end_date: str) -> str:
    return f"fund_portfolio:{symbol}:{start_date}:{end_date}"


def _raw_dataset() -> str:
    return "raw/tushare/fund_portfolio"


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} inputs are missing columns: {', '.join(missing)}")
