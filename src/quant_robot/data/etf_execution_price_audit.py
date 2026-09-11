"""Bounded, read-only reconciliation of ETF bars to retained provider records.

This checks local lineage, not provider authenticity or corporate-action completeness.
Only price/schema columns are projected; factors and return labels are never loaded.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact
from quant_robot.storage.fingerprints import sha256_file

PRICE_COLUMNS = ("open", "high", "low", "close", "volume", "amount")
RAW_COLUMNS = ("symbol", "date", *PRICE_COLUMNS)
BAR_COLUMNS = (*RAW_COLUMNS, "asset_id", "market", "frequency", "source", "adjusted", "adj_close")
FINAL_HOLDOUT_START = date(2026, 1, 1)


def audit_price_frames(bars: pd.DataFrame, raw: pd.DataFrame, *, expected_dates: list[str]) -> dict[str, Any]:
    """Reconcile keys, schema, calendar and values without computing price returns."""
    for name, frame, columns in (("processed", bars, BAR_COLUMNS), ("raw", raw, RAW_COLUMNS)):
        missing = sorted(set(columns) - set(frame.columns))
        if missing:
            raise ValueError(f"{name} prices missing columns: {missing}")
    bars, raw = bars.copy(), raw.copy()
    for frame in (bars, raw):
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    keys = ["symbol", "date"]
    blockers: list[str] = []
    processed_duplicates = int(bars.duplicated(keys).sum())
    raw_duplicates = int(raw.duplicated(keys).sum())
    if processed_duplicates or raw_duplicates:
        blockers.append("duplicate_authority_keys")
    null_keys = int(bars[keys + ["asset_id"]].isna().any(axis=1).sum() + raw[keys].isna().any(axis=1).sum())
    if null_keys:
        blockers.append("null_authority_keys")
    expected_assets = bars["symbol"].astype(str).map(_asset_id)
    bad_identity = int((expected_assets.isna() | bars.asset_id.ne(expected_assets)
                        | bars.market.ne("CN_ETF") | bars.frequency.ne("1d") | bars.source.ne("tushare")).sum())
    if bad_identity:
        blockers.append("processed_identity_or_source_mismatch")
    adjusted_boolean = bars.adjusted.map(lambda value: isinstance(value, (bool, np.bool_)))
    if not adjusted_boolean.all():
        blockers.append("invalid_adjusted_boolean")
    invalid = {"processed": _invalid_price_rows(bars), "raw": _invalid_price_rows(raw)}
    adjusted_prices = pd.to_numeric(bars.adj_close, errors="coerce")
    invalid_adjusted = int((~np.isfinite(adjusted_prices) | adjusted_prices.le(0)).sum())
    if any(invalid.values()) or invalid_adjusted:
        blockers.append("invalid_price_or_amount")
    observed_dates = set(bars.date.dropna())
    expected = set(expected_dates)
    missing_sessions = sorted(expected - observed_dates)
    unexpected_sessions = sorted((observed_dates | set(raw.date.dropna())) - expected)
    if missing_sessions or unexpected_sessions:
        blockers.append("calendar_session_mismatch")
    if bars.empty or raw.empty:
        blockers.append("empty_price_source")
    # Duplicate keys already fail; deduplication here bounds diagnostic join size.
    comparison = bars.drop_duplicates(keys).merge(raw.drop_duplicates(keys), on=keys, how="outer",
        suffixes=("_processed", "_raw"), indicator=True, validate="one_to_one")
    missing_raw = int(comparison._merge.eq("left_only").sum())
    missing_processed = int(comparison._merge.eq("right_only").sum())
    if missing_raw or missing_processed:
        blockers.append("raw_processed_key_coverage_mismatch")
    matched = comparison.loc[comparison._merge.eq("both")]
    mismatches = {}
    for column in PRICE_COLUMNS:
        left = pd.to_numeric(matched[column + "_processed"], errors="coerce")
        right = pd.to_numeric(matched[column + "_raw"], errors="coerce")
        mismatches[column] = int((~np.isclose(left, right, rtol=1e-10, atol=1e-10)).sum())
    if any(mismatches.values()):
        blockers.append("raw_processed_value_mismatch")
    equal_adjusted = np.isclose(adjusted_prices, pd.to_numeric(bars.close, errors="coerce"), rtol=1e-10, atol=1e-10)
    years = []
    for year, group in bars.groupby(bars.date.str[:4]):
        years.append({"year": year, "rows": len(group), "assets": int(group.asset_id.nunique()),
                      "sessions": int(group.date.nunique()), "start": group.date.min(), "end": group.date.max()})
    return {
        "stage": "cn_etf_execution_price_source_audit", "schema_version": 1,
        "local_raw_reconciliation_passed": not blockers, "blockers": blockers,
        "execution_accounting_source_verified": False,
        "remaining_requirements": ["provider_authenticity_not_independently_audited",
            "corporate_action_history_not_audited", "research_adjustment_source_not_audited",
            "etf_instrument_classification_not_audited", "asset_session_absences_need_lifecycle_or_suspension_evidence"],
        "summary": {"processed_rows": len(bars), "raw_rows": len(raw), "assets": int(bars.asset_id.nunique()),
            "observed_sessions": len(observed_dates), "expected_sessions": len(expected),
            "processed_duplicate_keys": processed_duplicates, "raw_duplicate_keys": raw_duplicates,
            "null_key_rows": null_keys, "bad_identity_rows": bad_identity,
            "invalid_price_rows": invalid, "invalid_adjusted_price_rows": invalid_adjusted,
            "missing_sessions": missing_sessions, "unexpected_sessions": unexpected_sessions,
            "processed_keys_without_raw": missing_raw, "raw_keys_without_processed": missing_processed,
            "value_mismatch_rows": mismatches,
            "adjusted_true_rows": int((bars.adjusted.eq(True) & adjusted_boolean).sum()),
            "adjusted_false_rows": int((bars.adjusted.eq(False) & adjusted_boolean).sum()),
            "adj_close_equals_close_rows": int(equal_adjusted.sum()),
            "adj_close_differs_from_close_rows": int((~equal_adjusted).sum()), "by_year": years},
        "boundaries": {"source_mutated": False, "provider_requested": False, "factor_generated": False,
            "forward_return_read": False, "final_holdout_read": False, "promotion_allowed": False,
            "broker_connection_allowed": False, "order_placement_allowed": False},
    }


def run_execution_price_audit(*, data_root: str | Path, start_date: str, end_date: str,
        calendar_path: str | Path, calendar_manifest_path: str | Path,
        progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if start > end or end >= FINAL_HOLDOUT_START:
        raise ValueError("price audit requires an ordered window before the final holdout")
    root = Path(data_root)
    inventory: dict[str, dict[str, Any]] = {}
    calendar_path, calendar_manifest_path = Path(calendar_path), Path(calendar_manifest_path)
    for path in (calendar_path, calendar_manifest_path, root / "manifest.json"):
        _inventory(path, inventory)
    calendar_manifest = validate_cn_trading_calendar_artifact(calendar_path, calendar_manifest_path)
    requested = calendar_manifest.get("requested_range", {})
    if (not requested.get("start") or not requested.get("end")
            or date.fromisoformat(requested["start"]) > start or date.fromisoformat(requested["end"]) < end):
        raise ValueError("validated calendar does not cover the audit window")
    calendar = pd.read_csv(calendar_path, usecols=["date"])
    all_dates = pd.to_datetime(calendar.date).dt.date
    sessions = [value.isoformat() for value in all_dates if start <= value <= end]
    if not sessions:
        raise ValueError("price audit window has no validated trading sessions")
    ingest_manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
    bar_frames, raw_frames, missing_partitions, manifest_mismatches = [], [], [], []
    base = root / "processed/bars/frequency=1d/market=CN_ETF"
    for year in range(start.year, end.year + 1):
        partition = base / f"year={year}"
        if not partition.is_dir():
            missing_partitions.append(str(partition))
            continue
        bar_frames.extend(_read_partition(partition, BAR_COLUMNS, start, end, inventory, partition_year=year))
    raw_base = root / "raw/tushare/fund_daily"
    # Include unexpected local sessions inside the requested window in the reconciliation.
    raw_partitions = {}
    for partition in raw_base.glob("trade_date=*"):
        value = partition.name.partition("=")[2]
        try:
            session = datetime.strptime(value, "%Y%m%d").date()
        except ValueError:
            continue
        if start <= session <= end:
            raw_partitions[session.isoformat()] = partition
    for index, session in enumerate(sorted(set(sessions) | set(raw_partitions))):
        partition = raw_partitions.get(session)
        if partition is None:
            missing_partitions.append(str(raw_base / ("trade_date=" + session.replace("-", ""))))
            continue
        frames = _read_partition(partition, RAW_COLUMNS, date.fromisoformat(session), date.fromisoformat(session),
                                 inventory, partition_date=date.fromisoformat(session))
        raw_frames.extend(frames)
        row_count = sum(len(frame) for frame in frames)
        item = ingest_manifest.get("completed", {}).get("CN_ETF:daily:" + session.replace("-", ""), {})
        if type(item.get("rows")) is not int or item["rows"] != row_count:
            manifest_mismatches.append(session)
        if progress and (index + 1) % 200 == 0:
            progress(f"Reconciled source files for {index + 1} sessions")
    bars = pd.concat(bar_frames, ignore_index=True) if bar_frames else pd.DataFrame(columns=BAR_COLUMNS)
    raw = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame(columns=RAW_COLUMNS)
    report = audit_price_frames(bars, raw, expected_dates=sessions)
    report["missing_partitions"] = missing_partitions
    report["manifest_row_count_mismatch_dates"] = manifest_mismatches
    if missing_partitions:
        report["blockers"].append("missing_source_partitions")
    if manifest_mismatches:
        report["blockers"].append("ingest_manifest_row_count_mismatch")
    changed = [item["path"] for item in inventory.values() if sha256_file(item["path"]) != item["sha256"]]
    if changed:
        report["blockers"].append("source_changed_during_audit")
    report["changed_during_audit"] = changed
    report["local_raw_reconciliation_passed"] = not report["blockers"]
    report["input_files"] = list(inventory.values())
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["window"] = {"start": start.isoformat(), "end": end.isoformat()}
    report["data_root"] = str(root)
    report["audit_implementation_sha256"] = sha256_file(Path(__file__))
    return report


def _inventory(path: Path, inventory: dict[str, dict[str, Any]]) -> None:
    key = str(path.resolve())
    inventory.setdefault(key, {"path": key, "sha256": sha256_file(path), "bytes": path.stat().st_size})


def _read_partition(path: Path, columns: tuple[str, ...], start: date, end: date,
                    inventory: dict[str, dict[str, Any]], *, partition_date: date | None = None,
                    partition_year: int | None = None) -> list[pd.DataFrame]:
    marker = path / "_format.json"
    if marker.is_file():
        _inventory(marker, inventory)
        payload = json.loads(marker.read_text(encoding="utf-8"))
        kind, name = payload.get("format"), payload.get("file")
        if kind not in {"parquet", "csv"} or not isinstance(name, str) or Path(name).name != name:
            raise ValueError(f"invalid source format marker: {marker}")
        files = [path / name]
        if files[0].suffix != "." + kind:
            raise ValueError(f"source marker extension mismatch: {marker}")
    else:
        parquet, csv = sorted(path.glob("*.parquet")), sorted(path.glob("*.csv"))
        if parquet and csv:
            raise ValueError(f"ambiguous source formats: {path}")
        files = parquet or csv
    if not files:
        raise ValueError(f"empty price source partition: {path}")
    frames = []
    for file in files:
        _inventory(file, inventory)
        if file.suffix == ".parquet":
            import pyarrow.parquet as pq
            reader = pq.ParquetFile(file)
            dates = reader.read(columns=["date"]).to_pandas()["date"]
        else:
            dates = pd.read_csv(file, usecols=["date"])["date"]
        dates = pd.to_datetime(dates, errors="raise").dt.date
        # Check dates alone before reading any values, including mislabelled year partitions.
        if dates.isna().any() or any(value >= FINAL_HOLDOUT_START for value in dates):
            raise ValueError(f"invalid or final holdout dates in source partition: {file}")
        if ((partition_date is not None and dates.ne(partition_date).any())
                or (partition_year is not None and any(value.year != partition_year for value in dates))):
            raise ValueError(f"source partition label and row dates disagree: {file}")
        if file.suffix == ".parquet":
            import pyarrow as pa
            import pyarrow.dataset as ds
            field = ds.field("date").cast(pa.date32())
            frame = ds.dataset([file], format="parquet").to_table(columns=list(columns),
                filter=(field >= start) & (field <= end)).to_pandas()
        else:
            if (dates.lt(start) | dates.gt(end)).any():
                raise ValueError("CSV cannot project a partial window before reading values; use a bounded source partition")
            frame = pd.read_csv(file, usecols=list(columns))
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        frames.append(frame)
    return frames


def _asset_id(symbol: str) -> str | None:
    parts = symbol.split(".")
    if len(parts) != 2 or len(parts[0]) != 6 or not parts[0].isdigit() or parts[1] not in {"SH", "SZ"}:
        return None
    return "CN_ETF_" + ("XSHG" if parts[1] == "SH" else "XSHE") + "_" + parts[0]


def _invalid_price_rows(frame: pd.DataFrame) -> int:
    values = frame[list(PRICE_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    invalid = ~np.isfinite(values).all(axis=1)
    invalid |= values[["open", "high", "low", "close"]].le(0).any(axis=1)
    invalid |= values[["volume", "amount"]].lt(0).any(axis=1)
    invalid |= values.low.gt(values[["open", "close"]].min(axis=1)) | values.high.lt(values[["open", "close"]].max(axis=1))
    return int(invalid.sum())
