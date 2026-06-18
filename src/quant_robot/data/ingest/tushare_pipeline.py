from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.data.quality_report import build_quality_report
from quant_robot.storage.dataset_store import DatasetStore


class TushareDailyAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...


def run_tushare_daily_ingest(
    adapter: TushareDailyAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    resume: bool = True,
    market: str = "CN",
) -> dict[str, object]:
    market = market.upper()
    if market not in {"CN", "CN_ETF"}:
        raise ValueError(f"Unsupported Tushare ingest market: {market}")
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    downloaded: list[str] = []
    skipped: list[str] = []
    raw_frames_by_date: dict[str, pd.DataFrame] = {}
    downloaded_rows_by_date: dict[str, int] = {}

    trade_dates = _trade_dates(adapter, start_date, end_date)
    for trade_date in trade_dates:
        key = _manifest_key(market, trade_date)
        if resume and manifest.is_completed(key) and _raw_partition_has_rows(store, _raw_dataset(market), trade_date):
            skipped.append(trade_date)
            continue
        raw = _fetch_daily(adapter, trade_date, market)
        if raw.empty:
            _mark_empty_raw_response(manifest, key, trade_date)
        store.write_frame(raw, _raw_dataset(market), {"trade_date": trade_date})
        downloaded.append(trade_date)
        downloaded_rows_by_date[trade_date] = len(raw)
        raw_frames_by_date[trade_date] = raw

    try:
        raw_for_processing = _load_raw_frames(store, trade_dates, raw_frames_by_date, market)
        raw_for_processing, adjusted, adjustment_report = _attach_adjusted_close(
            adapter,
            raw_for_processing,
            start_date,
            end_date,
            market,
        )
        processed = _normalize_tushare_daily(raw_for_processing, market)
        if not processed.empty:
            validate_market_data(processed)
            _write_processed_by_year(store, processed, market)
        expected_dates = [pd.to_datetime(date, format="%Y%m%d").date() for date in trade_dates]
        report = build_quality_report(processed, expected_dates=expected_dates) if not processed.empty else _empty_report()
    except Exception as exc:
        for trade_date in downloaded:
            manifest.mark_failed(_manifest_key(market, trade_date), reason=str(exc))
        manifest.save()
        raise
    for trade_date in downloaded:
        manifest.mark_completed(_manifest_key(market, trade_date), rows=downloaded_rows_by_date[trade_date])
    manifest.save()
    (output_path / "quality_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "source": "tushare",
        "market": market,
        "downloaded_trade_dates": downloaded,
        "skipped_trade_dates": skipped,
        "processed_rows": int(len(processed)),
        "adjusted": adjusted,
        "adjustment_report": adjustment_report,
        "quality_report": report,
    }


def _trade_dates(adapter: TushareDailyAdapter, start_date: str, end_date: str) -> list[str]:
    calendar = adapter.fetch_trade_calendar(start_date, end_date)
    dates = pd.to_datetime(calendar["date"]).dt.strftime("%Y%m%d")
    return list(dates)


def _fetch_daily(adapter: TushareDailyAdapter, trade_date: str, market: str) -> pd.DataFrame:
    if market == "CN_ETF":
        if not hasattr(adapter, "fetch_etf_daily_by_trade_date"):
            raise ValueError("Tushare adapter does not implement CN_ETF fund daily fetching")
        return adapter.fetch_etf_daily_by_trade_date(trade_date)  # type: ignore[attr-defined]
    return adapter.fetch_daily_by_trade_date(trade_date)


def _manifest_key(market: str, trade_date: str) -> str:
    return f"daily:{trade_date}" if market == "CN" else f"{market}:daily:{trade_date}"


def _raw_dataset(market: str) -> str:
    return "raw/tushare/fund_daily" if market == "CN_ETF" else "raw/tushare/daily"


def _raw_partition_has_rows(store: DatasetStore, dataset: str, trade_date: str) -> bool:
    partitions = {"trade_date": trade_date}
    if not store.exists(dataset, partitions):
        return False
    try:
        return len(store.read_frame(dataset, partitions)) > 0
    except FileNotFoundError:
        return False


def _mark_empty_raw_response(manifest: IngestManifest, key: str, trade_date: str) -> None:
    reason = f"empty raw response for open trade date {trade_date}"
    manifest.mark_failed(key, reason=reason)
    manifest.save()
    raise RuntimeError(reason)


def _load_raw_frames(store: DatasetStore, trade_dates: list[str], raw_frames_by_date: dict[str, pd.DataFrame], market: str) -> pd.DataFrame:
    frames = []
    for trade_date in trade_dates:
        if trade_date in raw_frames_by_date:
            frames.append(raw_frames_by_date[trade_date])
        elif store.exists(_raw_dataset(market), {"trade_date": trade_date}):
            frames.append(store.read_frame(_raw_dataset(market), {"trade_date": trade_date}))
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "amount"])
    return pd.concat(frames, ignore_index=True)


def _write_processed_by_year(store: DatasetStore, processed: pd.DataFrame, market: str) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["date"]).dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(year)}
        merged = group
        if store.exists("processed/bars", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/bars", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "timestamp", "frequency", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "timestamp"]).reset_index(drop=True)
        validate_market_data(merged)
        store.write_frame(merged, "processed/bars", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    if "timestamp" in coerced.columns:
        coerced["timestamp"] = pd.to_datetime(coerced["timestamp"], utc=True)
    if "date" in coerced.columns:
        coerced["date"] = pd.to_datetime(coerced["date"]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _normalize_tushare_daily(raw: pd.DataFrame, market: str = "CN") -> pd.DataFrame:
    pieces = []
    for symbol, group in raw.groupby("symbol", sort=True):
        asset = _asset_from_tushare_symbol(symbol, market=market)
        pieces.append(normalize_ohlcv(group, asset, source="tushare", frequency="1d"))
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).sort_values(["asset_id", "timestamp"]).reset_index(drop=True)


def _attach_adjusted_close(
    adapter: TushareDailyAdapter,
    raw: pd.DataFrame,
    start_date: str,
    end_date: str,
    market: str = "CN",
) -> tuple[pd.DataFrame, bool, dict[str, object]]:
    audit = _adjustment_report_template(market, len(raw))
    if market != "CN":
        audit["status"] = "not_applicable_market"
        return raw, False, audit
    if raw.empty or not hasattr(adapter, "fetch_adj_factor"):
        audit["status"] = "raw_empty" if raw.empty else "adapter_missing_fetch_adj_factor"
        return raw, False, audit
    adj_factor = adapter.fetch_adj_factor("", start_date, end_date)  # type: ignore[attr-defined]
    audit["range_factor_rows"] = int(len(adj_factor))
    audit["factor_rows"] = int(len(adj_factor))
    source = raw.copy()
    source["date"] = pd.to_datetime(source["date"]).dt.date
    if adj_factor.empty:
        audit["status"] = "empty_adj_factor"
        if hasattr(adapter, "fetch_adj_factor_by_trade_date"):
            fallback = _fetch_adj_factor_for_source_dates(adapter, source, audit)
            if not fallback.empty:
                adjusted, audit = _try_attach_adj_factor(source, fallback, audit)
                if adjusted is not None:
                    return adjusted, True, audit
        return raw, False, audit
    adjusted, audit = _try_attach_adj_factor(source, adj_factor, audit)
    if adjusted is not None:
        return adjusted, True, audit
    if audit["status"] == "partial_adj_factor_coverage" and hasattr(adapter, "fetch_adj_factor_by_trade_date"):
        fallback = _fetch_adj_factor_for_source_dates(adapter, source, audit)
        if not fallback.empty:
            adjusted, audit = _try_attach_adj_factor(source, fallback, audit)
            if adjusted is not None:
                return adjusted, True, audit
    return raw, False, audit


def _fetch_adj_factor_for_source_dates(
    adapter: TushareDailyAdapter,
    source: pd.DataFrame,
    audit: dict[str, object],
) -> pd.DataFrame:
    trade_dates = sorted(source["date"].unique())
    fallback = _fetch_adj_factor_by_trade_dates(adapter, trade_dates)
    audit["fallback_used"] = True
    audit["fallback_trade_dates"] = [date.strftime("%Y%m%d") for date in trade_dates]
    audit["fallback_factor_rows"] = int(len(fallback))
    return fallback


def _fetch_adj_factor_by_trade_dates(
    adapter: TushareDailyAdapter,
    trade_dates: list[object],
    empty_response_retries: int = 3,
) -> pd.DataFrame:
    frames = []
    for trade_date in trade_dates:
        date_text = pd.to_datetime(trade_date).strftime("%Y%m%d")
        frame = pd.DataFrame()
        for _ in range(max(1, empty_response_retries)):
            frame = adapter.fetch_adj_factor_by_trade_date(date_text)  # type: ignore[attr-defined]
            if not frame.empty:
                break
        frames.append(frame)
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "adj_factor"])
    return pd.concat(frames, ignore_index=True)


def _try_attach_adj_factor(
    source: pd.DataFrame,
    adj_factor: pd.DataFrame,
    audit: dict[str, object],
) -> tuple[pd.DataFrame | None, dict[str, object]]:
    factors = adj_factor.copy()
    factors["date"] = pd.to_datetime(factors["date"]).dt.date
    audit["factor_rows"] = int(len(factors))
    duplicate_factor_keys = int(factors.duplicated(["symbol", "date"]).sum())
    audit["duplicate_factor_keys"] = duplicate_factor_keys
    if duplicate_factor_keys:
        audit["status"] = "duplicate_adj_factor_keys"
        return None, audit
    merged = source.merge(factors, on=["symbol", "date"], how="left")
    missing_rows = int(merged["adj_factor"].isna().sum())
    audit["matched_rows"] = int(len(merged) - missing_rows)
    audit["missing_rows"] = missing_rows
    audit["coverage"] = float(audit["matched_rows"] / len(source)) if len(source) else 0.0
    if missing_rows:
        audit["status"] = "partial_adj_factor_coverage"
        return None, audit
    merged["adj_close"] = merged["close"] * merged["adj_factor"]
    audit["status"] = "applied"
    return merged.drop(columns=["adj_factor"]), audit


def _adjustment_report_template(market: str, raw_rows: int) -> dict[str, object]:
    return {
        "market": market,
        "raw_rows": int(raw_rows),
        "factor_rows": 0,
        "range_factor_rows": 0,
        "fallback_used": False,
        "fallback_factor_rows": 0,
        "fallback_trade_dates": [],
        "matched_rows": 0,
        "missing_rows": int(raw_rows),
        "duplicate_factor_keys": 0,
        "coverage": 0.0,
        "status": "not_checked",
    }


def _asset_from_tushare_symbol(symbol: str, market: str = "CN") -> Asset:
    code, suffix = symbol.split(".")
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare symbol suffix: {symbol}") from exc
    market = market.upper()
    if market == "CN_ETF":
        return Asset(
            asset_id=f"CN_ETF_{exchange}_{code}",
            symbol=symbol,
            market="CN_ETF",
            exchange=exchange,
            asset_type="etf",
            currency="CNY",
            timezone="Asia/Shanghai",
            calendar=exchange,
        )
    return Asset(
        asset_id=f"CN_{exchange}_{code}",
        symbol=symbol,
        market="CN",
        exchange=exchange,
        asset_type="stock",
        currency="CNY",
        timezone="Asia/Shanghai",
        calendar=exchange,
    )


def _empty_report() -> dict[str, object]:
    return {
        "rows": 0,
        "assets": 0,
        "markets": [],
        "start_date": None,
        "end_date": None,
        "duplicate_bars": 0,
        "zero_volume_rows": 0,
        "missing_date_rows": 0,
        "coverage_by_asset": [],
    }
