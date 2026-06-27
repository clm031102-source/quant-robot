from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks


STAGE = "shortlist_event_calendar_parity"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)


def build_event_calendar_parity_audit(
    reference_source: str | Path | pd.DataFrame,
    generated_source: str | Path | pd.DataFrame,
    *,
    reference_return_column: str = "period_return",
    generated_return_column: str = "period_return",
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    metric_tolerance: float = 0.005,
    date_return_tolerance: float = 0.0001,
) -> dict[str, Any]:
    reference = _load_returns(
        reference_source,
        return_column=reference_return_column,
        date_column=date_column,
        output_column="reference_return",
    )
    generated = _load_returns(
        generated_source,
        return_column=generated_return_column,
        date_column=date_column,
        output_column="generated_return",
    )
    merged = reference.merge(generated, on="date", how="outer")
    merged["reference_return"] = pd.to_numeric(merged["reference_return"], errors="coerce").fillna(0.0)
    merged["generated_return"] = pd.to_numeric(merged["generated_return"], errors="coerce").fillna(0.0)
    reference_dates = set(pd.to_datetime(reference["date"]))
    generated_dates = set(pd.to_datetime(generated["date"]))
    merged["in_reference"] = merged["date"].isin(reference_dates)
    merged["in_generated"] = merged["date"].isin(generated_dates)
    merged["diff"] = merged["generated_return"] - merged["reference_return"]
    merged["abs_diff"] = merged["diff"].abs()
    merged = merged.sort_values("date").reset_index(drop=True)

    reference_metrics = _metrics(
        reference[["date", "reference_return"]].rename(columns={"reference_return": "period_return"}),
        candidate_name="reference",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    generated_metrics = _metrics(
        generated[["date", "generated_return"]].rename(columns={"generated_return": "period_return"}),
        candidate_name="generated",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    metric_diffs = {
        key: _number(generated_metrics.get(key)) - _number(reference_metrics.get(key))
        for key in METRIC_KEYS
    }
    blockers = _blockers(
        merged,
        metric_diffs=metric_diffs,
        metric_tolerance=metric_tolerance,
        date_return_tolerance=date_return_tolerance,
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "reference_return_column": reference_return_column,
                "generated_return_column": generated_return_column,
                "date_column": date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "metric_tolerance": float(metric_tolerance),
                "date_return_tolerance": float(date_return_tolerance),
            },
            "summary": {
                "reference_dates": int(len(reference_dates)),
                "generated_dates": int(len(generated_dates)),
                "union_dates": int(len(merged)),
                "overlap_dates": int(len(reference_dates & generated_dates)),
                "missing_generated_dates": int((~merged["in_generated"] & merged["in_reference"]).sum()),
                "extra_generated_dates": int((merged["in_generated"] & ~merged["in_reference"]).sum()),
                "date_return_drift_count": int((merged["abs_diff"] > float(date_return_tolerance)).sum()),
                "max_abs_date_return_diff": _number(merged["abs_diff"].max()),
                "blocked": bool(blockers),
            },
            "reference_metrics": reference_metrics,
            "generated_metrics": generated_metrics,
            "metric_diffs": metric_diffs,
            "rows": _rows(merged),
            "blockers": blockers,
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Calendar parity is a generation audit; it is not profitability evidence.",
            },
        }
    )


def write_event_calendar_parity_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(audit)
    (output / "event_calendar_parity_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "event_calendar_parity_rows.csv", index=False)
    pd.DataFrame(
        [
            {"metric": key, "diff": value}
            for key, value in sanitized.get("metric_diffs", {}).items()
        ]
    ).to_csv(output / "event_calendar_parity_metric_diffs.csv", index=False)


def _load_returns(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    date_column: str,
    output_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    missing = [column for column in (date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"return source missing columns: {', '.join(missing)}")
    working = frame[[date_column, return_column]].copy()
    working["date"] = pd.to_datetime(working[date_column], errors="coerce")
    working[output_column] = pd.to_numeric(working[return_column], errors="coerce").fillna(0.0)
    working = working.dropna(subset=["date"])
    return (
        working.groupby("date", as_index=False)[output_column]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )


def _metrics(
    frame: pd.DataFrame,
    *,
    candidate_name: str,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    row = summarize_return_blocks(
        frame,
        candidate_name=candidate_name,
        return_column="period_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    return {key: row.get(key) for key in ("candidate_name", "period_count", *METRIC_KEYS)}


def _blockers(
    merged: pd.DataFrame,
    *,
    metric_diffs: dict[str, float],
    metric_tolerance: float,
    date_return_tolerance: float,
) -> list[str]:
    blockers = []
    if int((~merged["in_generated"] & merged["in_reference"]).sum()):
        blockers.append("missing_generated_dates")
    if int((merged["in_generated"] & ~merged["in_reference"]).sum()):
        blockers.append("extra_generated_dates")
    if int((merged["abs_diff"] > float(date_return_tolerance)).sum()):
        blockers.append("date_return_drift")
    for key, diff in metric_diffs.items():
        if abs(float(diff)) > float(metric_tolerance):
            blockers.append(f"metric_drift:{key}")
    return blockers


def _rows(merged: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in merged.sort_values("abs_diff", ascending=False).itertuples(index=False):
        rows.append(
            {
                "date": pd.Timestamp(row.date).date().isoformat(),
                "reference_return": _number(row.reference_return),
                "generated_return": _number(row.generated_return),
                "diff": _number(row.diff),
                "abs_diff": _number(row.abs_diff),
                "in_reference": bool(row.in_reference),
                "in_generated": bool(row.in_generated),
            }
        )
    return rows


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported return source file type: {path.suffix}")


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _number(value)
    if isinstance(value, float):
        return _number(value)
    return value
