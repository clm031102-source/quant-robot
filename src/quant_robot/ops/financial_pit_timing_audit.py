from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize


STAGE = "financial_pit_timing_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_FINANCIAL_COLUMNS = ("asset_id", "symbol", "market", "source", "ann_date", "end_date")
EXACT_KEY_COLUMNS = ("asset_id", "end_date", "ann_date", "source")


def build_financial_pit_timing_audit(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    max_timing_rows: int = 5000,
    max_signal_lag_calendar_days: int = 30,
) -> dict[str, Any]:
    financial_path = Path(financial_root)
    bars_paths = [Path(root) for root in bars_roots]
    financial = _normalise_financial(_load_fina_indicator_inputs(financial_path))
    missing_columns = [column for column in REQUIRED_FINANCIAL_COLUMNS if column not in financial.columns]
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial.columns else []
    bars = _load_bars(bars_paths, assets)

    quality = _financial_quality(financial, missing_columns)
    revision = _revision_summary(financial, missing_columns)
    timing = _timing_summary(
        financial,
        bars,
        missing_columns,
        max_signal_lag_calendar_days=max_signal_lag_calendar_days,
    )
    blockers = _dedupe(
        quality["blockers"]
        + revision["blockers"]
        + timing["blockers"]
    )
    timing_rows = timing["timing_rows"][: max(0, int(max_timing_rows))]
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(financial_path),
        "bars_roots": [str(root) for root in bars_paths],
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "financial_rows": int(len(financial)),
            "financial_assets": int(financial["asset_id"].nunique(dropna=True)) if "asset_id" in financial.columns else 0,
            "bar_rows": int(len(bars)),
            "bar_assets": int(bars["asset_id"].nunique(dropna=True)) if not bars.empty else 0,
            "missing_required_financial_columns": missing_columns,
            **quality["summary"],
            **revision["summary"],
            **timing["summary"],
            "timing_rows_written": len(timing_rows),
            "timing_rows_available": len(timing["timing_rows"]),
        },
        "availability_policy": {
            "ann_date_required": True,
            "report_period_only_availability_allowed": False,
            "signal_date_rule": "first_trade_date_strictly_after_ann_date",
            "same_day_announcement_trading_allowed": False,
            "available_date_output_required_for_factor_matrix": True,
            "available_date_column_present": "available_date" in financial.columns,
        },
        "revision_policy": {
            "revision_handling_status": revision["revision_handling_status"],
            "distinct_revision_ann_dates_required": True,
            "exact_duplicate_revision_keys_allowed": False,
            "same_report_period_multiple_ann_dates_allowed": True,
        },
        "promotion_policy": {
            "portfolio_backtest_allowed": False,
            "promotion_allowed": False,
            "profitability_claim_allowed": False,
            "next_allowed_action": "Use this audit as financial PIT timing evidence before any financial factor matrix or portfolio grid.",
        },
        "timing_rows": timing_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_timing_audit_markdown(result)
    return result


def write_financial_pit_timing_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_pit_timing_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_timing_audit.md").write_text(
        render_financial_pit_timing_audit_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "financial_pit_timing_audit_timing_rows.csv", result.get("timing_rows", []) or [])


def render_financial_pit_timing_audit_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    availability = result.get("availability_policy", {}) or {}
    revision = result.get("revision_policy", {}) or {}
    promotion = result.get("promotion_policy", {}) or {}
    lines = [
        "# Financial PIT Timing Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Financial rows: {summary.get('financial_rows', 0)}",
        f"- Financial assets: {summary.get('financial_assets', 0)}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Missing required columns: {', '.join(summary.get('missing_required_financial_columns', []) or []) or 'none'}",
        f"- Missing PIT rows: {summary.get('missing_pit_date_rows', 0)}",
        f"- Announcement before report period rows: {summary.get('ann_date_before_report_period_rows', 0)}",
        f"- Exact duplicate key rows: {summary.get('exact_duplicate_key_rows', 0)}",
        f"- Revision groups: {summary.get('revision_group_count', 0)}",
        f"- Revision rows: {summary.get('revision_row_count', 0)}",
        f"- Signal mapped rows: {summary.get('signal_mapped_rows', 0)}",
        f"- Signal unmapped rows: {summary.get('signal_unmapped_rows', 0)}",
        f"- Signal alignment violations: {summary.get('signal_alignment_violation_rows', 0)}",
        f"- Stale signal lag rows: {summary.get('stale_signal_lag_rows', 0)}",
        f"- Max signal lag allowed: {summary.get('max_signal_lag_calendar_days_allowed', 0)} calendar days",
        f"- Revision handling status: `{revision.get('revision_handling_status', '')}`",
        f"- Signal date rule: `{availability.get('signal_date_rule', '')}`",
        f"- Same-day announcement trading allowed: {availability.get('same_day_announcement_trading_allowed', False)}",
        f"- Profitability claim allowed: {promotion.get('profitability_claim_allowed', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
        "- This audit checks financial input timing only; it is not IC, Sharpe, total return, win-rate, or promotion evidence.",
        "- Distinct later `ann_date` rows for the same `asset_id` and `end_date` are treated as revision-aware rows.",
        "- Exact duplicate keys are blocked because they make revision ordering ambiguous.",
    ]
    return "\n".join(lines) + "\n"


def _normalise_financial(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    for column in ("date", "ann_date", "end_date", "available_date"):
        if column in output.columns:
            output[column] = pd.to_datetime(output[column], errors="coerce")
    for column in ("asset_id", "symbol", "market", "source"):
        if column in output.columns:
            output[column] = output[column].astype(str)
    sort_columns = [column for column in ("asset_id", "end_date", "ann_date", "source") if column in output.columns]
    return output.sort_values(sort_columns).reset_index(drop=True) if sort_columns else output.reset_index(drop=True)


def _financial_quality(financial: pd.DataFrame, missing_columns: list[str]) -> dict[str, Any]:
    blockers: list[str] = []
    if financial.empty:
        blockers.append("missing_financial_rows")
    if missing_columns:
        blockers.append("missing_required_financial_columns")
    if financial.empty or missing_columns:
        return {
            "blockers": blockers,
            "summary": {
                "missing_ann_date_rows": 0,
                "missing_end_date_rows": 0,
                "missing_pit_date_rows": 0,
                "ann_date_before_report_period_rows": 0,
                "ann_date_start": None,
                "ann_date_end": None,
                "report_period_start": None,
                "report_period_end": None,
            },
        }

    ann_dates = pd.to_datetime(financial["ann_date"], errors="coerce")
    end_dates = pd.to_datetime(financial["end_date"], errors="coerce")
    missing_ann = int(ann_dates.isna().sum())
    missing_end = int(end_dates.isna().sum())
    ann_before_report = int((ann_dates < end_dates).sum())
    if missing_ann or missing_end:
        blockers.append("missing_pit_date_rows")
    if ann_before_report:
        blockers.append("ann_date_before_report_period")
    return {
        "blockers": blockers,
        "summary": {
            "missing_ann_date_rows": missing_ann,
            "missing_end_date_rows": missing_end,
            "missing_pit_date_rows": missing_ann + missing_end,
            "ann_date_before_report_period_rows": ann_before_report,
            "ann_date_start": _iso_date(ann_dates.min()),
            "ann_date_end": _iso_date(ann_dates.max()),
            "report_period_start": _iso_date(end_dates.min()),
            "report_period_end": _iso_date(end_dates.max()),
        },
    }


def _revision_summary(financial: pd.DataFrame, missing_columns: list[str]) -> dict[str, Any]:
    if financial.empty or any(column in missing_columns for column in EXACT_KEY_COLUMNS):
        return {
            "blockers": [],
            "revision_handling_status": "not_auditable_missing_keys",
            "summary": {
                "exact_duplicate_key_rows": 0,
                "revision_group_count": 0,
                "revision_row_count": 0,
            },
        }
    duplicate_rows = int(financial.duplicated(list(EXACT_KEY_COLUMNS)).sum())
    grouped = financial.dropna(subset=["asset_id", "end_date", "ann_date"]).groupby(["asset_id", "end_date"], dropna=False)
    ann_counts = grouped["ann_date"].nunique()
    revision_keys = ann_counts[ann_counts > 1].index
    revision_group_count = int(len(revision_keys))
    revision_row_count = int(
        sum(len(grouped.get_group(key)) for key in revision_keys)
    )
    blockers = ["exact_duplicate_financial_keys"] if duplicate_rows else []
    if duplicate_rows:
        status = "blocked_duplicate_revision_keys"
    elif revision_group_count:
        status = "revision_aware_distinct_ann_dates"
    else:
        status = "no_revision_groups_observed"
    return {
        "blockers": blockers,
        "revision_handling_status": status,
        "summary": {
            "exact_duplicate_key_rows": duplicate_rows,
            "revision_group_count": revision_group_count,
            "revision_row_count": revision_row_count,
        },
    }


def _timing_summary(
    financial: pd.DataFrame,
    bars: pd.DataFrame,
    missing_columns: list[str],
    *,
    max_signal_lag_calendar_days: int,
) -> dict[str, Any]:
    if financial.empty or missing_columns:
        return {
            "blockers": [],
            "timing_rows": [],
            "summary": {
                "signal_mapped_rows": 0,
                "signal_unmapped_rows": 0,
                "signal_alignment_violation_rows": 0,
                "stale_signal_lag_rows": 0,
                "max_signal_lag_calendar_days": None,
                "max_signal_lag_calendar_days_allowed": int(max_signal_lag_calendar_days),
            },
        }
    signals = _signal_dates_strictly_after_ann_date(financial, bars)
    ann_dates = pd.to_datetime(financial["ann_date"], errors="coerce")
    mapped_mask = signals.notna()
    alignment_violations = int(((signals <= ann_dates) & mapped_mask).sum())
    signal_unmapped = int((~mapped_mask).sum())
    lag_days = (signals[mapped_mask] - ann_dates[mapped_mask]).dt.days if mapped_mask.any() else pd.Series(dtype="float64")
    stale_signal_lag_rows = int((lag_days > int(max_signal_lag_calendar_days)).sum()) if not lag_days.empty else 0
    blockers: list[str] = []
    if bars.empty:
        blockers.append("missing_bars")
    if signal_unmapped:
        blockers.append("signal_date_unmapped_rows")
    if alignment_violations:
        blockers.append("signal_alignment_violation_rows")
    if stale_signal_lag_rows:
        blockers.append("signal_lag_exceeds_max_calendar_days")
    timing_rows = _timing_rows(financial, signals)
    return {
        "blockers": blockers,
        "timing_rows": timing_rows,
        "summary": {
            "signal_mapped_rows": int(mapped_mask.sum()),
            "signal_unmapped_rows": signal_unmapped,
            "signal_alignment_violation_rows": alignment_violations,
            "stale_signal_lag_rows": stale_signal_lag_rows,
            "max_signal_lag_calendar_days": int(lag_days.max()) if not lag_days.empty else None,
            "max_signal_lag_calendar_days_allowed": int(max_signal_lag_calendar_days),
        },
    }


def _signal_dates_strictly_after_ann_date(financial: pd.DataFrame, bars: pd.DataFrame) -> pd.Series:
    if bars.empty:
        return pd.Series([pd.NaT] * len(financial), index=financial.index)
    bar_dates = {
        asset_id: pd.DatetimeIndex(group["date"].sort_values().dropna().unique())
        for asset_id, group in bars.groupby("asset_id")
    }
    signal_dates = []
    for row in financial.itertuples(index=False):
        asset_id = str(getattr(row, "asset_id"))
        ann_date = pd.Timestamp(getattr(row, "ann_date"))
        dates = bar_dates.get(asset_id)
        if dates is None or pd.isna(ann_date):
            signal_dates.append(pd.NaT)
            continue
        position = dates.searchsorted(ann_date, side="right")
        signal_dates.append(dates[position] if position < len(dates) else pd.NaT)
    return pd.Series(signal_dates, index=financial.index)


def _timing_rows(financial: pd.DataFrame, signals: pd.Series) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in financial.reset_index(drop=True).iterrows():
        signal_date = signals.iloc[index] if index < len(signals) else pd.NaT
        rows.append(
            {
                "asset_id": str(row.get("asset_id", "")),
                "symbol": str(row.get("symbol", "")),
                "source": str(row.get("source", "")),
                "end_date": _iso_date(row.get("end_date")),
                "ann_date": _iso_date(row.get("ann_date")),
                "signal_date": _iso_date(signal_date),
                "signal_lag_calendar_days": _lag_days(row.get("ann_date"), signal_date),
            }
        )
    return rows


def _load_bars(roots: list[Path], assets: list[str]) -> pd.DataFrame:
    frames = []
    columns = ["date", "asset_id", "market", "adj_close"]
    asset_set = set(assets)
    for root in roots:
        dataset_root = root / "processed" / "bars" / "frequency=1d" / "market=CN"
        if not dataset_root.exists():
            dataset_root = root
        for path in _dataset_files(dataset_root):
            frame = _read_frame(path)
            missing = [column for column in columns if column not in frame.columns]
            if missing:
                continue
            if asset_set:
                frame = frame[frame["asset_id"].astype(str).isin(asset_set)]
            if not frame.empty:
                frames.append(frame[columns])
    if not frames:
        return pd.DataFrame(columns=columns)
    output = pd.concat(frames, ignore_index=True)
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["adj_close"] = pd.to_numeric(output["adj_close"], errors="coerce")
    return (
        output[(output["market"] == "CN") & (output["adj_close"] > 0)]
        .dropna(subset=columns)
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _dataset_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() in {".parquet", ".csv"}:
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".parquet", ".csv"})


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else [
        "asset_id",
        "symbol",
        "source",
        "end_date",
        "ann_date",
        "signal_date",
        "signal_lag_calendar_days",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _iso_date(value: Any) -> str | None:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    return timestamp.date().isoformat()


def _lag_days(ann_date: Any, signal_date: Any) -> int | None:
    ann = pd.Timestamp(ann_date)
    signal = pd.Timestamp(signal_date)
    if pd.isna(ann) or pd.isna(signal):
        return None
    return int((signal - ann).days)


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
