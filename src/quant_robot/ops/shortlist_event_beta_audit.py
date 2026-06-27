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


STAGE = "shortlist_event_beta_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_shortlist_event_beta_audit(
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    *,
    benchmark_source: str | Path | pd.DataFrame,
    benchmarks: Sequence[str] | None = None,
    return_column: str | None = None,
    date_column: str = "date",
    benchmark_column: str = "benchmark",
    benchmark_return_column: str = "period_return_benchmark",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
) -> dict[str, Any]:
    benchmark_returns = _load_benchmark_returns(
        benchmark_source,
        date_column=date_column,
        benchmark_column=benchmark_column,
        benchmark_return_column=benchmark_return_column,
    )
    if benchmarks:
        keep = {str(item) for item in benchmarks}
        benchmark_returns = benchmark_returns[benchmark_returns["benchmark"].isin(keep)].copy()
    rows: list[dict[str, Any]] = []
    hedged_frames: list[pd.DataFrame] = []
    for candidate_name, source in return_sources.items():
        source_path, source_return_column, source_date_column = _normalise_source_spec(
            source,
            default_return_column=return_column,
            default_date_column=date_column,
        )
        strategy_returns, resolved_column = load_candidate_period_returns(
            source_path,
            return_column=source_return_column,
            date_column=source_date_column,
        )
        for benchmark_name, benchmark_frame in benchmark_returns.groupby("benchmark", sort=True):
            row, hedged = _audit_pair(
                str(candidate_name),
                strategy_returns,
                str(benchmark_name),
                benchmark_frame,
                source_return_column=resolved_column,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            rows.append(row)
            hedged_frames.append(hedged)
    rows = sorted(
        rows,
        key=lambda row: (
            str(row["benchmark"]),
            -float(row["hedged_annualized_return"]),
            -float(row["hedged_overlap_sharpe"]),
        ),
    )
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "return_column": return_column or "auto",
            "date_column": date_column,
            "benchmark_column": benchmark_column,
            "benchmark_return_column": benchmark_return_column,
            "periods_per_year": float(periods_per_year),
            "holding_period": int(holding_period),
            "benchmarks": list(benchmarks) if benchmarks else "all",
        },
        "summary": {
            "candidate_count": int(len(return_sources)),
            "benchmark_count": int(benchmark_returns["benchmark"].nunique()) if not benchmark_returns.empty else 0,
            "row_count": int(len(rows)),
        },
        "rows": _sanitize(rows),
        "hedged_returns": pd.concat(hedged_frames, ignore_index=True) if hedged_frames else pd.DataFrame(),
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Event beta audits are diagnostic only; final holdout remains sealed.",
        },
    }


def write_shortlist_event_beta_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize({key: value for key, value in audit.items() if key != "hedged_returns"})
    (output / "shortlist_event_beta_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "shortlist_event_beta_audit_rows.csv", index=False)
    hedged_returns = audit.get("hedged_returns")
    if isinstance(hedged_returns, pd.DataFrame) and not hedged_returns.empty:
        hedged_returns.to_csv(output / "shortlist_event_beta_hedged_returns.csv", index=False)


def _audit_pair(
    candidate_name: str,
    strategy_returns: pd.DataFrame,
    benchmark_name: str,
    benchmark_returns: pd.DataFrame,
    *,
    source_return_column: str,
    periods_per_year: float,
    holding_period: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    strategy = strategy_returns[["date", "period_return"]].rename(columns={"period_return": "strategy_return"})
    benchmark = benchmark_returns[["date", "benchmark_return"]]
    frame = strategy.merge(benchmark, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if frame.empty:
        return _empty_row(candidate_name, benchmark_name, source_return_column), pd.DataFrame()
    y = frame["strategy_return"].astype(float).to_numpy()
    x = frame["benchmark_return"].astype(float).to_numpy()
    x_var = float(np.var(x))
    beta = float(np.cov(x, y, ddof=0)[0, 1] / x_var) if x_var > 0.0 else 0.0
    correlation = float(np.corrcoef(x, y)[0, 1]) if len(frame) > 1 and np.std(x) > 0 and np.std(y) > 0 else 0.0
    r_squared = correlation * correlation
    hedged_return = y - beta * x
    alpha_t_stat = _mean_t_stat(hedged_return)
    hedged_frame = pd.DataFrame(
        {
            "date": frame["date"],
            "candidate": candidate_name,
            "benchmark": benchmark_name,
            "strategy_return": y,
            "benchmark_return": x,
            "beta": beta,
            "hedged_return": hedged_return,
            "period_return": hedged_return,
        }
    )
    strategy_metrics = summarize_return_blocks(
        frame[["date", "strategy_return"]].rename(columns={"strategy_return": "period_return"}),
        candidate_name=candidate_name,
        return_column=source_return_column,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    benchmark_metrics = summarize_return_blocks(
        frame[["date", "benchmark_return"]].rename(columns={"benchmark_return": "period_return"}),
        candidate_name=benchmark_name,
        return_column="benchmark_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    hedged_metrics = summarize_return_blocks(
        hedged_frame[["date", "period_return"]],
        candidate_name=f"{candidate_name}_{benchmark_name}_hedged",
        return_column="hedged_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    row = {
        "candidate": candidate_name,
        "benchmark": benchmark_name,
        "source_return_column": source_return_column,
        "observations": int(len(frame)),
        "beta": beta,
        "r_squared": r_squared,
        "alpha_annualized": _number(float(np.mean(hedged_return)) * float(periods_per_year)),
        "alpha_t_stat": alpha_t_stat,
        "strategy_total_return": strategy_metrics["total_return"],
        "strategy_annualized_return": strategy_metrics["annualized_return"],
        "strategy_max_drawdown": strategy_metrics["max_drawdown"],
        "benchmark_total_return": benchmark_metrics["total_return"],
        "hedged_total_return": hedged_metrics["total_return"],
        "hedged_annualized_return": hedged_metrics["annualized_return"],
        "hedged_overlap_sharpe": hedged_metrics["overlap_autocorr_adjusted_sharpe"],
        "hedged_max_drawdown": hedged_metrics["max_drawdown"],
    }
    return _sanitize(row), hedged_frame


def _load_benchmark_returns(
    source: str | Path | pd.DataFrame,
    *,
    date_column: str,
    benchmark_column: str,
    benchmark_return_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(Path(source))
    missing = [column for column in (date_column, benchmark_column, benchmark_return_column) if column not in frame]
    if missing:
        raise ValueError(f"benchmark source missing columns: {', '.join(missing)}")
    working = frame[[date_column, benchmark_column, benchmark_return_column]].copy()
    working["date"] = pd.to_datetime(working[date_column], errors="coerce")
    working["benchmark"] = working[benchmark_column].astype(str)
    working["benchmark_return"] = pd.to_numeric(working[benchmark_return_column], errors="coerce").fillna(0.0)
    working = working.dropna(subset=["date"])
    if working.empty:
        return pd.DataFrame(columns=["date", "benchmark", "benchmark_return"])
    return (
        working.groupby(["date", "benchmark"], as_index=False)["benchmark_return"]
        .mean()
        .sort_values(["benchmark", "date"])
        .reset_index(drop=True)
    )


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


def _empty_row(candidate_name: str, benchmark_name: str, source_return_column: str) -> dict[str, Any]:
    return {
        "candidate": candidate_name,
        "benchmark": benchmark_name,
        "source_return_column": source_return_column,
        "observations": 0,
        "beta": 0.0,
        "r_squared": 0.0,
        "alpha_annualized": 0.0,
        "alpha_t_stat": 0.0,
        "strategy_total_return": 0.0,
        "strategy_annualized_return": 0.0,
        "strategy_max_drawdown": 0.0,
        "benchmark_total_return": 0.0,
        "hedged_total_return": 0.0,
        "hedged_annualized_return": 0.0,
        "hedged_overlap_sharpe": 0.0,
        "hedged_max_drawdown": 0.0,
    }


def _mean_t_stat(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    std = float(np.std(values, ddof=1))
    if std <= 0.0:
        return 0.0
    return _number(float(np.mean(values)) / (std / math.sqrt(len(values))))


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
