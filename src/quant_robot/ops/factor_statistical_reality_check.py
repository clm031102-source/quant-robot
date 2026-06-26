from __future__ import annotations

from datetime import date
import itertools
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable

import pandas as pd


STAGE = "factor_statistical_reality_check"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

DEFAULT_METRIC_COLUMNS = (
    "test_overlap_autocorr_adjusted_sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "mean_test_overlap_autocorr_adjusted_sharpe",
    "mean_test_sharpe",
    "test_sharpe",
    "sharpe",
)
DEFAULT_OBSERVATION_COLUMNS = (
    "test_overlap_effective_sample_size",
    "overlap_effective_sample_size",
    "test_overlap_observations",
    "overlap_observations",
    "test_long_short_observations",
    "long_short_observations",
    "total_test_trades",
    "test_trades",
    "trades",
)
DEFAULT_P_VALUE_COLUMNS = (
    "test_ic_p_value",
    "test_rank_ic_p_value",
    "ic_p_value",
    "rank_ic_p_value",
    "p_value",
)

_NORMAL = NormalDist()
_EULER_GAMMA = 0.5772156649015329


def probabilistic_sharpe_probability(
    *,
    observed_sharpe: float,
    benchmark_sharpe: float = 0.0,
    observations: int | float,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Approximate the probability that observed Sharpe exceeds a benchmark Sharpe."""

    standard_error = _sharpe_standard_error(
        observed_sharpe=observed_sharpe,
        observations=observations,
        skew=skew,
        kurtosis=kurtosis,
    )
    if not math.isfinite(standard_error) or standard_error <= 0.0:
        return 0.5 if observed_sharpe == benchmark_sharpe else float(observed_sharpe > benchmark_sharpe)
    z_score = (float(observed_sharpe) - float(benchmark_sharpe)) / standard_error
    return _clip_probability(_NORMAL.cdf(z_score))


def deflated_sharpe_probability(
    *,
    observed_sharpe: float,
    observations: int | float,
    trial_count: int,
    benchmark_sharpe: float = 0.0,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Approximate Deflated Sharpe probability after accounting for repeated trials.

    This uses the Bailey-Lopez de Prado expected maximum Sharpe intuition with a
    normal approximation. It is intentionally conservative and dependency-free;
    it should be treated as a promotion blocker, not as standalone proof of alpha.
    """

    standard_error = _sharpe_standard_error(
        observed_sharpe=observed_sharpe,
        observations=observations,
        skew=skew,
        kurtosis=kurtosis,
    )
    hurdle = float(benchmark_sharpe)
    if int(trial_count) > 1 and math.isfinite(standard_error) and standard_error > 0.0:
        hurdle += _expected_max_null_sharpe(standard_error=standard_error, trial_count=int(trial_count))
    return probabilistic_sharpe_probability(
        observed_sharpe=observed_sharpe,
        benchmark_sharpe=hurdle,
        observations=observations,
        skew=skew,
        kurtosis=kurtosis,
    )


def benjamini_hochberg(p_values: Iterable[Any], *, alpha: float = 0.05) -> list[dict[str, Any]]:
    values = [_clean_probability(value, default=1.0) for value in p_values]
    if not values:
        return []
    n_tests = len(values)
    indexed = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    max_significant_rank = 0
    ranked: dict[int, dict[str, Any]] = {}
    for rank, (index, p_value) in enumerate(indexed, start=1):
        critical = (rank / n_tests) * float(alpha)
        if p_value <= critical:
            max_significant_rank = rank
        ranked[index] = {
            "index": index,
            "p_value": p_value,
            "rank": rank,
            "critical_value": critical,
            "significant": False,
            "adjusted_p_value": 1.0,
        }

    running_min = 1.0
    for rank, (index, p_value) in reversed(list(enumerate(indexed, start=1))):
        running_min = min(running_min, p_value * n_tests / rank)
        ranked[index]["adjusted_p_value"] = min(running_min, 1.0)
        ranked[index]["significant"] = rank <= max_significant_rank

    return [ranked[index] for index in range(n_tests)]


def build_purged_cpcv_splits(
    dates: Iterable[Any],
    *,
    n_groups: int,
    test_group_count: int,
    purge_observations: int = 0,
    embargo_observations: int = 0,
) -> list[dict[str, Any]]:
    unique_dates = _unique_sorted_dates(dates)
    if not unique_dates:
        return []
    if n_groups < 2:
        raise ValueError("n_groups must be at least 2")
    if n_groups > len(unique_dates):
        raise ValueError("n_groups cannot exceed the number of unique dates")
    if test_group_count < 1 or test_group_count >= n_groups:
        raise ValueError("test_group_count must be between 1 and n_groups - 1")

    groups = _balanced_date_groups(len(unique_dates), n_groups)
    splits: list[dict[str, Any]] = []
    all_positions = set(range(len(unique_dates)))
    for split_id, test_groups in enumerate(itertools.combinations(range(n_groups), test_group_count), start=1):
        test_positions = set(
            position
            for group_id in test_groups
            for position in groups[group_id]
        )
        protected_positions = set(test_positions)
        for position in test_positions:
            start = max(0, position - int(purge_observations))
            end = min(len(unique_dates) - 1, position + int(embargo_observations))
            protected_positions.update(range(start, end + 1))
        purged_positions = protected_positions - test_positions
        train_positions = sorted(all_positions - protected_positions)
        test_positions_sorted = sorted(test_positions)
        splits.append(
            {
                "split_id": split_id,
                "test_groups": list(test_groups),
                "n_groups": n_groups,
                "test_group_count": test_group_count,
                "purge_observations_requested": int(purge_observations),
                "embargo_observations_requested": int(embargo_observations),
                "train_observations": len(train_positions),
                "test_observations": len(test_positions_sorted),
                "purged_observations": len(purged_positions),
                "train_start": _date_at(unique_dates, train_positions, first=True),
                "train_end": _date_at(unique_dates, train_positions, first=False),
                "test_start": _date_at(unique_dates, test_positions_sorted, first=True),
                "test_end": _date_at(unique_dates, test_positions_sorted, first=False),
                "train_dates": [unique_dates[position] for position in train_positions],
                "test_dates": [unique_dates[position] for position in test_positions_sorted],
                "purged_dates": [unique_dates[position] for position in sorted(purged_positions)],
            }
        )
    return splits


def build_parameter_sensitivity_heatmap(
    experiments: pd.DataFrame,
    *,
    x_param: str,
    y_param: str,
    metric: str,
    neighbor_min_fraction: float = 0.75,
    min_neighbor_count: int = 2,
) -> dict[str, Any]:
    missing = [column for column in (x_param, y_param, metric) if column not in experiments.columns]
    if missing or experiments.empty:
        return {
            "x_param": x_param,
            "y_param": y_param,
            "metric": metric,
            "status": "missing_columns" if missing else "empty",
            "missing_columns": missing,
            "cells": [],
            "best_cell": None,
        }

    clean = experiments[[x_param, y_param, metric]].dropna(subset=[x_param, y_param, metric]).copy()
    if clean.empty:
        return {
            "x_param": x_param,
            "y_param": y_param,
            "metric": metric,
            "status": "empty_after_dropna",
            "missing_columns": [],
            "cells": [],
            "best_cell": None,
        }

    grouped = clean.groupby([x_param, y_param], dropna=False)[metric].agg(["mean", "count"]).reset_index()
    cells = [
        {
            "x": _scalar(row[x_param]),
            "y": _scalar(row[y_param]),
            "metric_mean": float(row["mean"]),
            "metric_count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]
    x_values = sorted({_hashable(cell["x"]) for cell in cells}, key=_sort_key)
    y_values = sorted({_hashable(cell["y"]) for cell in cells}, key=_sort_key)
    x_rank = {value: index for index, value in enumerate(x_values)}
    y_rank = {value: index for index, value in enumerate(y_values)}
    best = max(cells, key=lambda cell: (cell["metric_mean"], -_sort_key(cell["x"])[0]))
    best_x_rank = x_rank[_hashable(best["x"])]
    best_y_rank = y_rank[_hashable(best["y"])]
    neighbor_cells = [
        cell
        for cell in cells
        if not (cell["x"] == best["x"] and cell["y"] == best["y"])
        and abs(x_rank[_hashable(cell["x"])] - best_x_rank) <= 1
        and abs(y_rank[_hashable(cell["y"])] - best_y_rank) <= 1
    ]
    metric_threshold = best["metric_mean"] * float(neighbor_min_fraction) if best["metric_mean"] > 0.0 else best["metric_mean"]
    neighbor_pass_count = sum(1 for cell in neighbor_cells if cell["metric_mean"] >= metric_threshold)
    neighbor_count = len(neighbor_cells)
    best_cell = {
        **best,
        "neighbor_metric_threshold": metric_threshold,
        "neighbor_count": neighbor_count,
        "neighbor_pass_count": neighbor_pass_count,
        "neighbor_pass_rate": neighbor_pass_count / neighbor_count if neighbor_count else 0.0,
        "stable_peak": bool(neighbor_pass_count >= int(min_neighbor_count)),
    }
    return {
        "x_param": x_param,
        "y_param": y_param,
        "metric": metric,
        "status": "ok",
        "missing_columns": [],
        "neighbor_min_fraction": float(neighbor_min_fraction),
        "min_neighbor_count": int(min_neighbor_count),
        "cells": sorted(cells, key=lambda cell: (_sort_key(cell["x"]), _sort_key(cell["y"]))),
        "best_cell": best_cell,
    }


def build_factor_statistical_reality_check(
    experiments: pd.DataFrame,
    *,
    metric_column: str | None = None,
    observations_column: str | None = None,
    p_value_column: str | None = None,
    case_column: str = "case_id",
    date_column: str | None = None,
    x_param: str | None = None,
    y_param: str | None = None,
    sensitivity_metric: str | None = None,
    alpha: float = 0.05,
    min_deflated_sharpe_probability: float = 0.95,
    cpcv_groups: int = 6,
    cpcv_test_group_count: int = 2,
    purge_observations: int = 0,
    embargo_observations: int = 0,
) -> dict[str, Any]:
    experiments = experiments.copy() if isinstance(experiments, pd.DataFrame) else pd.DataFrame(experiments)
    metric_name = metric_column or _first_existing_column(experiments, DEFAULT_METRIC_COLUMNS)
    observation_name = observations_column or _first_existing_column(experiments, DEFAULT_OBSERVATION_COLUMNS)
    p_value_name = p_value_column or _first_existing_column(experiments, DEFAULT_P_VALUE_COLUMNS)
    blockers: list[str] = []
    if experiments.empty:
        blockers.append("missing_experiment_rows")
    if metric_name is None:
        blockers.append("missing_sharpe_metric_column")

    hypothesis_count = _hypothesis_count(experiments, case_column=case_column)
    scored_rows = _scored_rows(
        experiments,
        metric_column=metric_name,
        observations_column=observation_name,
        p_value_column=p_value_name,
        case_column=case_column,
        hypothesis_count=hypothesis_count,
        min_deflated_sharpe_probability=min_deflated_sharpe_probability,
    )
    bh_rows = benjamini_hochberg([row["p_value"] for row in scored_rows], alpha=alpha)
    for row, bh in zip(scored_rows, bh_rows):
        row["fdr_rank"] = bh["rank"]
        row["fdr_critical_value"] = bh["critical_value"]
        row["fdr_adjusted_p_value"] = bh["adjusted_p_value"]
        row["fdr_significant"] = bh["significant"]
        row["statistical_candidate"] = bool(row["deflated_sharpe_pass"] and row["fdr_significant"])

    cpcv_splits: list[dict[str, Any]] = []
    if date_column:
        if date_column not in experiments.columns:
            blockers.append("missing_cpcv_date_column")
        else:
            cpcv_splits = build_purged_cpcv_splits(
                experiments[date_column].dropna(),
                n_groups=cpcv_groups,
                test_group_count=cpcv_test_group_count,
                purge_observations=purge_observations,
                embargo_observations=embargo_observations,
            )

    sensitivity = None
    if x_param and y_param:
        sensitivity = build_parameter_sensitivity_heatmap(
            experiments,
            x_param=x_param,
            y_param=y_param,
            metric=sensitivity_metric or metric_name or "",
        )
    elif x_param or y_param:
        blockers.append("incomplete_parameter_sensitivity_axes")

    ranked_rows = sorted(
        scored_rows,
        key=lambda row: (
            not row.get("statistical_candidate", False),
            -float(row.get("deflated_sharpe_probability", 0.0)),
            -float(row.get("observed_sharpe", 0.0)),
            str(row.get("case_id", "")),
        ),
    )
    for rank, row in enumerate(ranked_rows, start=1):
        row["statistical_rank"] = rank

    summary = _summary(
        ranked_rows,
        blockers=blockers,
        hypothesis_count=hypothesis_count,
        metric_column=metric_name,
        observations_column=observation_name,
        p_value_column=p_value_name,
        cpcv_splits=cpcv_splits,
        sensitivity=sensitivity,
    )
    report = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": summary,
        "rows": ranked_rows,
        "cpcv_splits": cpcv_splits,
        "sensitivity": sensitivity,
        "promotion_policy": {
            "promotion_allowed": False,
            "paper_ready_allowed": False,
            "portfolio_backtest_allowed": summary["statistical_candidate_count"] > 0,
            "next_allowed_action": (
                "Candidates may proceed only to long-cycle replay, tradeability, portfolio construction, "
                "regime, event, and capacity audits."
            ),
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    report["markdown"] = render_markdown(report)
    return _sanitize(report)


def write_factor_statistical_reality_check(output_dir: str | Path, report: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_report = _sanitize(report)
    (output_path / "factor_statistical_reality_check.json").write_text(
        json.dumps(clean_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_statistical_reality_check.md").write_text(
        render_markdown(clean_report),
        encoding="utf-8",
    )
    pd.DataFrame(clean_report.get("rows", []) or []).to_csv(
        output_path / "factor_statistical_reality_check_rows.csv",
        index=False,
    )
    pd.DataFrame(clean_report.get("cpcv_splits", []) or []).drop(
        columns=["train_dates", "test_dates", "purged_dates"],
        errors="ignore",
    ).to_csv(output_path / "factor_statistical_reality_check_cpcv_splits.csv", index=False)
    sensitivity = clean_report.get("sensitivity") or {}
    pd.DataFrame(sensitivity.get("cells", []) or []).to_csv(
        output_path / "factor_statistical_reality_check_sensitivity.csv",
        index=False,
    )


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {}) or {}
    lines = [
        "# Factor Statistical Reality Check",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Hypotheses: {summary.get('hypothesis_count', 0)}",
        f"- Metric: {summary.get('metric_column')}",
        f"- Observations: {summary.get('observations_column')}",
        f"- p-value: {summary.get('p_value_column')}",
        f"- Deflated Sharpe pass: {summary.get('deflated_sharpe_pass_count', 0)}",
        f"- FDR significant: {summary.get('fdr_significant_count', 0)}",
        f"- Statistical candidates: {summary.get('statistical_candidate_count', 0)}",
        f"- CPCV splits: {summary.get('cpcv_split_count', 0)}",
        f"- Sensitivity stable peak: {summary.get('sensitivity_stable_peak', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {report.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {report.get('live_boundary_allowed', False)}",
        f"- Safety: {report.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
        "| Rank | Case | Factor | Sharpe | DSR Prob | p-value | FDR q | Candidate |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for row in (report.get("rows", []) or [])[:20]:
        lines.append(
            "| {rank} | {case} | {factor} | {sharpe:.3f} | {dsr:.3f} | {p:.4g} | {q:.4g} | {cand} |".format(
                rank=row.get("statistical_rank", ""),
                case=row.get("case_id", ""),
                factor=row.get("factor_name", ""),
                sharpe=float(row.get("observed_sharpe") or 0.0),
                dsr=float(row.get("deflated_sharpe_probability") or 0.0),
                p=float(row.get("p_value") or 1.0),
                q=float(row.get("fdr_adjusted_p_value") or 1.0),
                cand=row.get("statistical_candidate", False),
            )
        )
    return "\n".join(lines) + "\n"


def _scored_rows(
    experiments: pd.DataFrame,
    *,
    metric_column: str | None,
    observations_column: str | None,
    p_value_column: str | None,
    case_column: str,
    hypothesis_count: int,
    min_deflated_sharpe_probability: float,
) -> list[dict[str, Any]]:
    if metric_column is None or experiments.empty:
        return []
    rows: list[dict[str, Any]] = []
    for index, row in experiments.reset_index(drop=True).iterrows():
        observed_sharpe = _float(row.get(metric_column), 0.0)
        observations = max(_float(row.get(observations_column), 0.0) if observations_column else 0.0, 2.0)
        skew = _float(row.get("skew"), 0.0)
        kurtosis = _float(row.get("kurtosis"), 3.0)
        psr = probabilistic_sharpe_probability(
            observed_sharpe=observed_sharpe,
            benchmark_sharpe=0.0,
            observations=observations,
            skew=skew,
            kurtosis=kurtosis,
        )
        dsr = deflated_sharpe_probability(
            observed_sharpe=observed_sharpe,
            observations=observations,
            trial_count=max(hypothesis_count, 1),
            benchmark_sharpe=0.0,
            skew=skew,
            kurtosis=kurtosis,
        )
        derived_p_value = _two_sided_sharpe_p_value(
            observed_sharpe=observed_sharpe,
            observations=observations,
            skew=skew,
            kurtosis=kurtosis,
        )
        p_value = _clean_probability(row.get(p_value_column), default=derived_p_value) if p_value_column else derived_p_value
        rows.append(
            {
                "source_row": int(index),
                "case_id": str(row.get(case_column, index)) if case_column in experiments.columns else str(index),
                "factor_name": str(row.get("factor_name", "")),
                "metric_column": metric_column,
                "observed_sharpe": observed_sharpe,
                "observations": observations,
                "probabilistic_sharpe_probability": psr,
                "deflated_sharpe_probability": dsr,
                "deflated_sharpe_pass": bool(dsr >= float(min_deflated_sharpe_probability)),
                "p_value": p_value,
                "derived_sharpe_p_value": derived_p_value,
                "hypothesis_count": int(max(hypothesis_count, 1)),
                "min_deflated_sharpe_probability": float(min_deflated_sharpe_probability),
            }
        )
    return rows


def _summary(
    rows: list[dict[str, Any]],
    *,
    blockers: list[str],
    hypothesis_count: int,
    metric_column: str | None,
    observations_column: str | None,
    p_value_column: str | None,
    cpcv_splits: list[dict[str, Any]],
    sensitivity: dict[str, Any] | None,
) -> dict[str, Any]:
    best = rows[0] if rows else {}
    best_cell = (sensitivity or {}).get("best_cell") if sensitivity else None
    return {
        "rows": len(rows),
        "hypothesis_count": int(hypothesis_count),
        "metric_column": metric_column,
        "observations_column": observations_column,
        "p_value_column": p_value_column or "derived_from_sharpe",
        "best_case_id": best.get("case_id"),
        "best_observed_sharpe": best.get("observed_sharpe"),
        "max_deflated_sharpe_probability": max(
            (float(row.get("deflated_sharpe_probability", 0.0)) for row in rows),
            default=0.0,
        ),
        "deflated_sharpe_pass_count": sum(1 for row in rows if row.get("deflated_sharpe_pass")),
        "fdr_significant_count": sum(1 for row in rows if row.get("fdr_significant")),
        "statistical_candidate_count": sum(1 for row in rows if row.get("statistical_candidate")),
        "cpcv_split_count": len(cpcv_splits),
        "sensitivity_status": (sensitivity or {}).get("status") if sensitivity else "not_requested",
        "sensitivity_stable_peak": bool(best_cell and best_cell.get("stable_peak")),
        "blockers": blockers,
        "passes": bool(rows) and not blockers,
    }


def _sharpe_standard_error(
    *,
    observed_sharpe: float,
    observations: int | float,
    skew: float,
    kurtosis: float,
) -> float:
    n_obs = float(observations)
    if not math.isfinite(n_obs) or n_obs <= 1.0:
        return math.inf
    sharpe = float(observed_sharpe)
    numerator = 1.0 - float(skew) * sharpe + ((float(kurtosis) - 1.0) / 4.0) * sharpe * sharpe
    numerator = max(numerator, 1e-12)
    return math.sqrt(numerator / (n_obs - 1.0))


def _expected_max_null_sharpe(*, standard_error: float, trial_count: int) -> float:
    if trial_count <= 1:
        return 0.0
    # Clip quantiles away from one to avoid infinities in very large grids.
    first = _NORMAL.inv_cdf(min(1.0 - 1e-12, 1.0 - 1.0 / trial_count))
    second = _NORMAL.inv_cdf(min(1.0 - 1e-12, 1.0 - 1.0 / (trial_count * math.e)))
    return float(standard_error) * ((1.0 - _EULER_GAMMA) * first + _EULER_GAMMA * second)


def _two_sided_sharpe_p_value(
    *,
    observed_sharpe: float,
    observations: int | float,
    skew: float,
    kurtosis: float,
) -> float:
    standard_error = _sharpe_standard_error(
        observed_sharpe=observed_sharpe,
        observations=observations,
        skew=skew,
        kurtosis=kurtosis,
    )
    if not math.isfinite(standard_error) or standard_error <= 0.0:
        return 1.0
    z_score = float(observed_sharpe) / standard_error
    return _clip_probability(math.erfc(abs(z_score) / math.sqrt(2.0)))


def _hypothesis_count(experiments: pd.DataFrame, *, case_column: str) -> int:
    if experiments.empty:
        return 0
    if case_column in experiments.columns:
        return int(experiments[case_column].astype(str).nunique())
    return int(len(experiments))


def _first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    columns = set(frame.columns)
    for column in candidates:
        if column in columns:
            return column
    return None


def _balanced_date_groups(date_count: int, n_groups: int) -> list[list[int]]:
    base_size, remainder = divmod(date_count, n_groups)
    groups = []
    start = 0
    for group_id in range(n_groups):
        size = base_size + (1 if group_id < remainder else 0)
        end = start + size
        groups.append(list(range(start, end)))
        start = end
    return groups


def _unique_sorted_dates(dates: Iterable[Any]) -> list[str]:
    values = []
    for value in dates:
        if pd.isna(value):
            continue
        values.append(pd.to_datetime(value).date().isoformat())
    return sorted(set(values))


def _date_at(dates: list[str], positions: list[int], *, first: bool) -> str | None:
    if not positions:
        return None
    return dates[positions[0 if first else -1]]


def _clean_probability(value: Any, *, default: float) -> float:
    number = _float(value, default)
    if not math.isfinite(number):
        return _clip_probability(default)
    return _clip_probability(number)


def _clip_probability(value: float) -> float:
    if not math.isfinite(float(value)):
        return 0.0
    return max(0.0, min(float(value), 1.0))


def _float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _scalar(value: Any) -> Any:
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def _hashable(value: Any) -> Any:
    return _scalar(value)


def _sort_key(value: Any) -> tuple[int, Any]:
    scalar = _scalar(value)
    try:
        return (0, float(scalar))
    except (TypeError, ValueError):
        return (1, str(scalar))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return _sanitize(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
