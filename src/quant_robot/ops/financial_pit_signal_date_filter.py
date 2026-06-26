from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.financial_pit_timing_audit import (
    EXACT_KEY_COLUMNS,
    REQUIRED_FINANCIAL_COLUMNS,
    _load_bars,
    _normalise_financial,
    _signal_dates_strictly_after_ann_date,
)
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "financial_pit_signal_date_filter"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_financial_pit_signal_date_filter(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    max_signal_lag_calendar_days: int = 30,
) -> dict[str, Any]:
    financial_path = Path(financial_root)
    bars_paths = [Path(root) for root in bars_roots]
    financial = _normalise_financial(_load_fina_indicator_inputs(financial_path))
    missing_columns = [column for column in REQUIRED_FINANCIAL_COLUMNS if column not in financial.columns]
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial.columns else []
    bars = _load_bars(bars_paths, assets)
    blockers = []
    if financial.empty:
        blockers.append("missing_financial_rows")
    if missing_columns:
        blockers.append("missing_required_financial_columns")
    filtered = pd.DataFrame()
    dropped_unmapped = 0
    dropped_stale = 0
    missing_pit_rows = 0
    ann_before_report = 0
    duplicate_rows = 0
    if not financial.empty and not missing_columns:
        ann_dates = pd.to_datetime(financial["ann_date"], errors="coerce")
        end_dates = pd.to_datetime(financial["end_date"], errors="coerce")
        missing_pit_rows = int((ann_dates.isna() | end_dates.isna()).sum())
        ann_before_report = int((ann_dates < end_dates).sum())
        duplicate_rows = int(financial.duplicated(list(EXACT_KEY_COLUMNS)).sum())
        if missing_pit_rows:
            blockers.append("missing_pit_date_rows")
        if ann_before_report:
            blockers.append("ann_date_before_report_period")
        if duplicate_rows:
            blockers.append("exact_duplicate_financial_keys")
        signals = _signal_dates_strictly_after_ann_date(financial, bars)
        lag_days = (signals - ann_dates).dt.days
        unmapped_mask = signals.isna()
        stale_mask = lag_days > int(max_signal_lag_calendar_days)
        dropped_unmapped = int(unmapped_mask.sum())
        dropped_stale = int(stale_mask.sum())
        keep_mask = ~(unmapped_mask | stale_mask)
        if not any(blocker in blockers for blocker in ["missing_pit_date_rows", "ann_date_before_report_period", "exact_duplicate_financial_keys"]):
            filtered = financial.loc[keep_mask].copy()
            filtered["available_date"] = signals.loc[keep_mask].values
            filtered["signal_date"] = signals.loc[keep_mask].values
            filtered["signal_lag_calendar_days"] = lag_days.loc[keep_mask].astype("int64").values
    if filtered.empty:
        blockers.append("no_filtered_financial_rows")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(financial_path),
        "bars_roots": [str(root) for root in bars_paths],
        "summary": {
            "passes": not blockers,
            "blockers": _dedupe(blockers),
            "input_rows": int(len(financial)),
            "filtered_rows": int(len(filtered)),
            "bar_rows": int(len(bars)),
            "missing_required_financial_columns": missing_columns,
            "missing_pit_date_rows": missing_pit_rows,
            "ann_date_before_report_period_rows": ann_before_report,
            "exact_duplicate_key_rows": duplicate_rows,
            "dropped_unmapped_signal_rows": dropped_unmapped,
            "dropped_stale_signal_lag_rows": dropped_stale,
            "max_signal_lag_calendar_days_allowed": int(max_signal_lag_calendar_days),
        },
        "filtered_sample_rows": _sample_rows(filtered),
        "filtered_frame": filtered,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_signal_date_filter_markdown(result)
    return result


def write_financial_pit_signal_date_filter(output_root: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)
    frame = result.get("filtered_frame")
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        DatasetStore(output_path).write_frame(
            frame,
            "processed/fina_indicator_inputs",
            {"frequency": "1q", "market": str(result.get("market", "CN")), "year": "pit_signal"},
        )
    (output_path / "financial_pit_signal_date_filter.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_signal_date_filter.md").write_text(
        render_financial_pit_signal_date_filter_markdown(result),
        encoding="utf-8",
    )


def render_financial_pit_signal_date_filter_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Signal-Date Filter",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Input rows: {summary.get('input_rows', 0)}",
        f"- Filtered rows: {summary.get('filtered_rows', 0)}",
        f"- Dropped unmapped signal rows: {summary.get('dropped_unmapped_signal_rows', 0)}",
        f"- Dropped stale signal-lag rows: {summary.get('dropped_stale_signal_lag_rows', 0)}",
        f"- Max signal lag allowed: {summary.get('max_signal_lag_calendar_days_allowed', 0)} calendar days",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
        "- This creates PIT-clean financial inputs with `available_date`, `signal_date`, and `signal_lag_calendar_days`.",
        "- It drops stale/unmapped timing rows, but exact duplicate financial keys remain hard blockers.",
        "- It is data-readiness evidence only, not factor profitability evidence.",
    ]
    return "\n".join(lines) + "\n"


def _sample_rows(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    sample = frame.head(limit).copy()
    for column in ("date", "ann_date", "end_date", "available_date", "signal_date"):
        if column in sample.columns:
            sample[column] = pd.to_datetime(sample[column], errors="coerce").dt.date.astype(str)
    return sample.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if key not in {"markdown", "filtered_frame"}
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
