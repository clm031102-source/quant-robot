from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.clean_technical_portfolio_diagnostic import overlap_metrics
from quant_robot.ops.factor_statistical_reality_check import build_purged_cpcv_splits
from quant_robot.ops.shortlist_return_block_audit import load_candidate_period_returns


STAGE = "shortlist_incremental_return_robustness"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)


def build_shortlist_incremental_return_robustness(
    *,
    base_return_source: str | Path | pd.DataFrame | Mapping[str, Any],
    candidate_return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    base_return_column: str | None = None,
    candidate_return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    cpcv_groups: int = 10,
    cpcv_test_group_count: int = 3,
    purge_observations: int = 0,
    embargo_observations: int = 0,
    bootstrap_iterations: int = 1000,
    bootstrap_period: str = "Q",
    random_seed: int = 42,
    max_drawdown_floor: float = -0.30,
    min_cpcv_annualized_win_rate: float = 0.50,
    min_bootstrap_annualized_win_rate: float = 0.50,
) -> dict[str, Any]:
    base_returns, resolved_base_column = _load_return_series(
        base_return_source,
        return_column=base_return_column,
        date_column=date_column,
    )
    rows: list[dict[str, Any]] = []
    cpcv_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    yearly_rows: list[dict[str, Any]] = []

    for offset, (candidate_name, source) in enumerate(candidate_return_sources.items()):
        candidate_returns, resolved_candidate_column = _load_return_series(
            source,
            return_column=candidate_return_column,
            date_column=date_column,
        )
        aligned, alignment = _align_returns(base_returns, candidate_returns)
        row_cpcv = _build_cpcv_rows(
            candidate_name,
            aligned,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            cpcv_groups=cpcv_groups,
            cpcv_test_group_count=cpcv_test_group_count,
            purge_observations=purge_observations,
            embargo_observations=embargo_observations,
            max_drawdown_floor=max_drawdown_floor,
        )
        row_bootstrap = _build_bootstrap_rows(
            candidate_name,
            aligned,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            bootstrap_iterations=bootstrap_iterations,
            bootstrap_period=bootstrap_period,
            random_seed=int(random_seed) + offset,
            max_drawdown_floor=max_drawdown_floor,
        )
        row_yearly = _build_yearly_delta_rows(candidate_name, aligned)

        base_metrics = _metric_pack(
            aligned["base"] if not aligned.empty else pd.Series(dtype=float),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        candidate_metrics = _metric_pack(
            aligned["candidate"] if not aligned.empty else pd.Series(dtype=float),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        deltas = _metric_deltas(candidate_metrics, base_metrics)
        summary = {
            "candidate_name": str(candidate_name),
            "base_return_column": resolved_base_column,
            "candidate_return_column": resolved_candidate_column,
            **alignment,
            **_flatten_metrics("base", base_metrics),
            **_flatten_metrics("candidate", candidate_metrics),
            **_flatten_metrics("delta", deltas),
            **_rate_summary("cpcv", row_cpcv),
            **_rate_summary("bootstrap", row_bootstrap),
            "year_count": int(len(row_yearly)),
            "year_win_rate": _positive_rate(row["delta_return"] for row in row_yearly),
        }
        summary["blockers"] = _blockers(
            summary,
            max_drawdown_floor=max_drawdown_floor,
            min_cpcv_annualized_win_rate=min_cpcv_annualized_win_rate,
            min_bootstrap_annualized_win_rate=min_bootstrap_annualized_win_rate,
        )
        rows.append(summary)
        cpcv_rows.extend(row_cpcv)
        bootstrap_rows.extend(row_bootstrap)
        yearly_rows.extend(row_yearly)

    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["delta_annualized_return"]),
            -float(row["delta_overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "date_column": date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "cpcv_groups": int(cpcv_groups),
                "cpcv_test_group_count": int(cpcv_test_group_count),
                "purge_observations": int(purge_observations),
                "embargo_observations": int(embargo_observations),
                "bootstrap_iterations": int(bootstrap_iterations),
                "bootstrap_period": str(bootstrap_period),
                "random_seed": int(random_seed),
                "max_drawdown_floor": float(max_drawdown_floor),
                "min_cpcv_annualized_win_rate": float(min_cpcv_annualized_win_rate),
                "min_bootstrap_annualized_win_rate": float(min_bootstrap_annualized_win_rate),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "pass_candidate_count": int(sum(not row["blockers"] for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "rows": rows,
            "cpcv_splits": cpcv_rows,
            "block_bootstrap": bootstrap_rows,
            "yearly_delta": yearly_rows,
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Incremental return robustness is an audit layer only; final holdout remains sealed.",
            },
        }
    )


def write_shortlist_incremental_return_robustness(
    output_dir: str | Path,
    audit: Mapping[str, Any],
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    (output / "shortlist_incremental_return_robustness.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "shortlist_incremental_return_summary.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("cpcv_splits", [])).to_csv(
        output / "shortlist_incremental_return_cpcv_splits.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("block_bootstrap", [])).to_csv(
        output / "shortlist_incremental_return_block_bootstrap.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("yearly_delta", [])).to_csv(
        output / "shortlist_incremental_return_yearly_delta.csv",
        index=False,
    )


def _load_return_series(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    return_column: str | None,
    date_column: str,
) -> tuple[pd.Series, str]:
    resolved_source, resolved_return_column, resolved_date_column = _normalise_source_spec(
        source,
        default_return_column=return_column,
        default_date_column=date_column,
    )
    frame, column = load_candidate_period_returns(
        resolved_source,
        return_column=resolved_return_column,
        date_column=resolved_date_column,
    )
    if frame.empty:
        return pd.Series(dtype=float), column
    series = pd.Series(
        pd.to_numeric(frame["period_return"], errors="coerce").fillna(0.0).to_numpy(dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(frame["date"], errors="coerce")),
    )
    series = series[~series.index.isna()].sort_index()
    return series, column


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


def _align_returns(base: pd.Series, candidate: pd.Series) -> tuple[pd.DataFrame, dict[str, int]]:
    base_dates = set(pd.DatetimeIndex(base.index))
    candidate_dates = set(pd.DatetimeIndex(candidate.index))
    aligned = pd.concat(
        [base.rename("base"), candidate.rename("candidate")],
        axis=1,
        join="inner",
    ).dropna()
    return aligned, {
        "base_date_count": int(len(base_dates)),
        "candidate_date_count": int(len(candidate_dates)),
        "alignment_date_count": int(len(aligned)),
        "base_only_date_count": int(len(base_dates - candidate_dates)),
        "candidate_only_date_count": int(len(candidate_dates - base_dates)),
    }


def _metric_pack(
    returns: pd.Series,
    *,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, float]:
    if returns.empty:
        return {key: 0.0 for key in METRIC_KEYS}
    metrics = summarize_returns(returns.reset_index(drop=True), periods_per_year=periods_per_year)
    metrics.update(
        overlap_metrics(
            returns.reset_index(drop=True),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
    )
    return {key: _number(metrics.get(key)) for key in METRIC_KEYS}


def _metric_deltas(candidate_metrics: Mapping[str, Any], base_metrics: Mapping[str, Any]) -> dict[str, float]:
    return {key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key)) for key in METRIC_KEYS}


def _flatten_metrics(prefix: str, metrics: Mapping[str, Any]) -> dict[str, float]:
    return {f"{prefix}_{key}": _number(value) for key, value in metrics.items()}


def _build_cpcv_rows(
    candidate_name: str,
    aligned: pd.DataFrame,
    *,
    periods_per_year: float,
    holding_period: int,
    cpcv_groups: int,
    cpcv_test_group_count: int,
    purge_observations: int,
    embargo_observations: int,
    max_drawdown_floor: float,
) -> list[dict[str, Any]]:
    if aligned.empty or len(aligned) < cpcv_groups:
        return []
    splits = build_purged_cpcv_splits(
        aligned.index,
        n_groups=int(cpcv_groups),
        test_group_count=int(cpcv_test_group_count),
        purge_observations=int(purge_observations),
        embargo_observations=int(embargo_observations),
    )
    rows = []
    for split in splits:
        selected = _select_iso_dates(aligned, set(split["test_dates"]))
        rows.append(
            _incremental_row(
                candidate_name,
                selected,
                row_type="cpcv",
                row_id=int(split["split_id"]),
                periods_per_year=periods_per_year,
                holding_period=holding_period,
                max_drawdown_floor=max_drawdown_floor,
                extra={
                    "test_groups": ",".join(str(value) for value in split["test_groups"]),
                    "test_start": split["test_start"],
                    "test_end": split["test_end"],
                    "test_observations": int(split["test_observations"]),
                    "train_observations": int(split["train_observations"]),
                    "purged_observations": int(split["purged_observations"]),
                },
            )
        )
    return rows


def _build_bootstrap_rows(
    candidate_name: str,
    aligned: pd.DataFrame,
    *,
    periods_per_year: float,
    holding_period: int,
    bootstrap_iterations: int,
    bootstrap_period: str,
    random_seed: int,
    max_drawdown_floor: float,
) -> list[dict[str, Any]]:
    if aligned.empty or bootstrap_iterations <= 0:
        return []
    grouped = {
        str(period): group.copy()
        for period, group in aligned.groupby(pd.DatetimeIndex(aligned.index).to_period(str(bootstrap_period)))
    }
    labels = sorted(grouped)
    if not labels:
        return []
    rng = np.random.default_rng(int(random_seed))
    rows = []
    for iteration in range(1, int(bootstrap_iterations) + 1):
        sampled_labels = list(rng.choice(labels, size=len(labels), replace=True))
        sampled = pd.concat([grouped[label] for label in sampled_labels], axis=0)
        rows.append(
            _incremental_row(
                candidate_name,
                sampled,
                row_type="bootstrap",
                row_id=iteration,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
                max_drawdown_floor=max_drawdown_floor,
                extra={
                    "sampled_block_count": int(len(sampled_labels)),
                    "sampled_blocks": ",".join(sampled_labels),
                },
            )
        )
    return rows


def _build_yearly_delta_rows(candidate_name: str, aligned: pd.DataFrame) -> list[dict[str, Any]]:
    if aligned.empty:
        return []
    rows = []
    years = pd.DatetimeIndex(aligned.index).year
    for year in sorted(set(years)):
        chunk = aligned[years == int(year)]
        base_return = float((1.0 + chunk["base"]).prod() - 1.0)
        candidate_return = float((1.0 + chunk["candidate"]).prod() - 1.0)
        rows.append(
            {
                "candidate_name": candidate_name,
                "year": int(year),
                "base_return": _number(base_return),
                "candidate_return": _number(candidate_return),
                "delta_return": _number(candidate_return - base_return),
                "observation_count": int(len(chunk)),
            }
        )
    return rows


def _incremental_row(
    candidate_name: str,
    returns: pd.DataFrame,
    *,
    row_type: str,
    row_id: int,
    periods_per_year: float,
    holding_period: int,
    max_drawdown_floor: float,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    base_metrics = _metric_pack(
        returns["base"] if not returns.empty else pd.Series(dtype=float),
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    candidate_metrics = _metric_pack(
        returns["candidate"] if not returns.empty else pd.Series(dtype=float),
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    deltas = _metric_deltas(candidate_metrics, base_metrics)
    return {
        "candidate_name": candidate_name,
        "row_type": row_type,
        "row_id": int(row_id),
        "observation_count": int(len(returns)),
        **_flatten_metrics("base", base_metrics),
        **_flatten_metrics("candidate", candidate_metrics),
        **_flatten_metrics("delta", deltas),
        "annualized_win": bool(deltas["annualized_return"] > 0.0),
        "overlap_win": bool(deltas["overlap_autocorr_adjusted_sharpe"] > 0.0),
        "drawdown_win": bool(deltas["max_drawdown"] > 0.0),
        "candidate_max_drawdown_floor_pass": bool(candidate_metrics["max_drawdown"] >= max_drawdown_floor),
        "strict_pass": bool(
            deltas["annualized_return"] > 0.0
            and deltas["overlap_autocorr_adjusted_sharpe"] > 0.0
            and candidate_metrics["max_drawdown"] >= max_drawdown_floor
        ),
        **dict(extra),
    }


def _select_iso_dates(frame: pd.DataFrame, iso_dates: set[str]) -> pd.DataFrame:
    if frame.empty:
        return frame
    date_strings = pd.DatetimeIndex(frame.index).date.astype(str)
    return frame[pd.Series(date_strings, index=frame.index).isin(iso_dates)]


def _rate_summary(prefix: str, rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        f"{prefix}_split_count" if prefix == "cpcv" else f"{prefix}_iteration_count": int(len(rows)),
        f"{prefix}_annualized_win_rate": _positive_rate(row["annualized_win"] for row in rows),
        f"{prefix}_overlap_win_rate": _positive_rate(row["overlap_win"] for row in rows),
        f"{prefix}_drawdown_win_rate": _positive_rate(row["drawdown_win"] for row in rows),
        f"{prefix}_max_drawdown_floor_pass_rate": _positive_rate(
            row["candidate_max_drawdown_floor_pass"] for row in rows
        ),
        f"{prefix}_strict_pass_rate": _positive_rate(row["strict_pass"] for row in rows),
    }


def _positive_rate(values: Any) -> float:
    clean = [bool(value) if isinstance(value, (bool, np.bool_)) else _number(value) > 0.0 for value in values]
    return float(sum(clean) / len(clean)) if clean else 0.0


def _blockers(
    row: Mapping[str, Any],
    *,
    max_drawdown_floor: float,
    min_cpcv_annualized_win_rate: float,
    min_bootstrap_annualized_win_rate: float,
) -> list[str]:
    blockers = []
    if int(row.get("alignment_date_count", 0)) <= 0:
        blockers.append("no_aligned_returns")
    if int(row.get("base_only_date_count", 0)) > 0 or int(row.get("candidate_only_date_count", 0)) > 0:
        blockers.append("date_alignment_loss")
    if _number(row.get("delta_annualized_return")) <= 0.0:
        blockers.append("non_positive_delta_annualized_return")
    if _number(row.get("candidate_max_drawdown")) < float(max_drawdown_floor):
        blockers.append("candidate_max_drawdown_below_floor")
    if _number(row.get("cpcv_annualized_win_rate")) < float(min_cpcv_annualized_win_rate):
        blockers.append("weak_cpcv_annualized_win_rate")
    if _number(row.get("bootstrap_annualized_win_rate")) < float(min_bootstrap_annualized_win_rate):
        blockers.append("weak_bootstrap_annualized_win_rate")
    return blockers


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
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, float):
        return _number(value)
    return value
