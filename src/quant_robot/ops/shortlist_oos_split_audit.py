from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import (
    load_candidate_period_returns,
    summarize_return_blocks,
)


STAGE = "shortlist_oos_split_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_shortlist_oos_split_audit(
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    *,
    train_years: Sequence[int] = (2, 3, 4, 5),
    test_years: int = 1,
    step_years: int = 1,
    return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    strict_min_annualized_return: float = 0.0,
    strict_min_overlap_sharpe: float = 0.0,
    strict_max_drawdown: float = -0.20,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for candidate_name, source in return_sources.items():
        source_path, source_return_column, source_date_column = _normalise_source_spec(
            source,
            default_return_column=return_column,
            default_date_column=date_column,
        )
        returns, resolved_column = load_candidate_period_returns(
            source_path,
            return_column=source_return_column,
            date_column=source_date_column,
        )
        candidate_folds = _candidate_oos_folds(
            returns,
            candidate_name=str(candidate_name),
            return_column=resolved_column,
            train_years=tuple(int(year) for year in train_years),
            test_years=int(test_years),
            step_years=int(step_years),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            strict_min_annualized_return=strict_min_annualized_return,
            strict_min_overlap_sharpe=strict_min_overlap_sharpe,
            strict_max_drawdown=strict_max_drawdown,
        )
        folds.extend(candidate_folds)
        rows.append(_candidate_summary(str(candidate_name), resolved_column, candidate_folds))
    rows = sorted(
        rows,
        key=lambda row: (
            -float(row["strict_pass_rate"]),
            -float(row["mean_oos_overlap_sharpe"]),
            -float(row["mean_oos_annualized_return"]),
        ),
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "train_years": [int(year) for year in train_years],
                "test_years": int(test_years),
                "step_years": int(step_years),
                "return_column": return_column or "auto",
                "date_column": date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "strict_min_annualized_return": float(strict_min_annualized_return),
                "strict_min_overlap_sharpe": float(strict_min_overlap_sharpe),
                "strict_max_drawdown": float(strict_max_drawdown),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "fold_count": int(len(folds)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "rows": rows,
            "folds": folds,
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "OOS split audits are pre-simulation robustness checks only; final holdout remains sealed.",
            },
        }
    )


def write_shortlist_oos_split_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(audit)
    (output / "shortlist_oos_split_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "shortlist_oos_split_summary.csv", index=False)
    pd.DataFrame(sanitized.get("folds", [])).to_csv(output / "shortlist_oos_split_folds.csv", index=False)


def _candidate_oos_folds(
    period_returns: pd.DataFrame,
    *,
    candidate_name: str,
    return_column: str,
    train_years: Sequence[int],
    test_years: int,
    step_years: int,
    periods_per_year: float,
    holding_period: int,
    strict_min_annualized_return: float,
    strict_min_overlap_sharpe: float,
    strict_max_drawdown: float,
) -> list[dict[str, Any]]:
    if period_returns.empty:
        return []
    frame = period_returns.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date")
    if frame.empty:
        return []
    min_year = int(frame["date"].dt.year.min())
    max_year = int(frame["date"].dt.year.max())
    rows = []
    for train_span in train_years:
        first_start = min_year
        last_start = max_year - int(train_span) - int(test_years) + 1
        if last_start < first_start:
            continue
        for train_start in range(first_start, last_start + 1, max(int(step_years), 1)):
            train_end = train_start + int(train_span) - 1
            test_start = train_end + 1
            test_end = test_start + int(test_years) - 1
            test_frame = frame[(frame["date"].dt.year >= test_start) & (frame["date"].dt.year <= test_end)]
            if test_frame.empty:
                continue
            metrics = summarize_return_blocks(
                test_frame[["date", "period_return"]],
                candidate_name=candidate_name,
                return_column="period_return",
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            ann = _number(metrics.get("annualized_return"))
            overlap = _number(metrics.get("overlap_autocorr_adjusted_sharpe"))
            drawdown = _number(metrics.get("max_drawdown"))
            loose_pass = ann > 0.0
            strict_pass = (
                ann > float(strict_min_annualized_return)
                and overlap > float(strict_min_overlap_sharpe)
                and drawdown >= float(strict_max_drawdown)
            )
            rows.append(
                {
                    "candidate_name": candidate_name,
                    "return_column": return_column,
                    "split_id": f"train{train_span}_{train_start}_{train_end}_test{test_start}_{test_end}",
                    "train_years": int(train_span),
                    "train_start_year": int(train_start),
                    "train_end_year": int(train_end),
                    "test_start_year": int(test_start),
                    "test_end_year": int(test_end),
                    "period_count": int(metrics.get("period_count", 0)),
                    "annualized_return": ann,
                    "overlap_autocorr_adjusted_sharpe": overlap,
                    "max_drawdown": drawdown,
                    "sharpe": _number(metrics.get("sharpe")),
                    "win_rate": _number(metrics.get("win_rate")),
                    "loose_pass": bool(loose_pass),
                    "strict_pass": bool(strict_pass),
                }
            )
    return rows


def _candidate_summary(candidate_name: str, return_column: str, folds: list[dict[str, Any]]) -> dict[str, Any]:
    if not folds:
        return {
            "candidate_name": candidate_name,
            "return_column": return_column,
            "split_count": 0,
            "mean_oos_annualized_return": 0.0,
            "min_oos_annualized_return": 0.0,
            "mean_oos_overlap_sharpe": 0.0,
            "min_oos_overlap_sharpe": 0.0,
            "worst_oos_drawdown": 0.0,
            "positive_oos_rate": 0.0,
            "loose_pass_rate": 0.0,
            "strict_pass_rate": 0.0,
        }
    frame = pd.DataFrame(folds)
    return {
        "candidate_name": candidate_name,
        "return_column": return_column,
        "split_count": int(len(frame)),
        "mean_oos_annualized_return": _number(frame["annualized_return"].mean()),
        "min_oos_annualized_return": _number(frame["annualized_return"].min()),
        "mean_oos_overlap_sharpe": _number(frame["overlap_autocorr_adjusted_sharpe"].mean()),
        "min_oos_overlap_sharpe": _number(frame["overlap_autocorr_adjusted_sharpe"].min()),
        "worst_oos_drawdown": _number(frame["max_drawdown"].min()),
        "positive_oos_rate": _rate(frame["annualized_return"] > 0.0),
        "loose_pass_rate": _rate(frame["loose_pass"]),
        "strict_pass_rate": _rate(frame["strict_pass"]),
    }


def _normalise_source_spec(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    default_return_column: str | None,
    default_date_column: str,
) -> tuple[str | Path | pd.DataFrame, str | None, str]:
    if isinstance(source, Mapping) and not isinstance(source, pd.DataFrame):
        path = source.get("path")
        if path is None:
            raise ValueError("source spec missing path")
        return (
            path,
            str(source.get("return_column")) if source.get("return_column") else default_return_column,
            str(source.get("date_column") or default_date_column),
        )
    return source, default_return_column, default_date_column


def _rate(values: Any) -> float:
    series = pd.Series(values)
    if series.empty:
        return 0.0
    return float(series.fillna(False).astype(bool).mean())


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
