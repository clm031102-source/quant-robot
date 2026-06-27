from __future__ import annotations

import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.clean_technical_portfolio_diagnostic import overlap_metrics
from quant_robot.ops.shortlist_return_block_audit import load_candidate_period_returns


STAGE = "simulation_shortlist_blend_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_simulation_shortlist_blend_audit(
    *,
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    weight_step: float = 0.25,
    max_components: int = 3,
    max_drawdown_floor: float = -0.30,
    duplicate_correlation: float = 0.98,
) -> dict[str, Any]:
    series_by_name = {
        str(name): _load_return_series(source, return_column=return_column, date_column=date_column)
        for name, source in return_sources.items()
    }
    series_by_name = {name: series for name, series in series_by_name.items() if not series.empty}
    if not series_by_name:
        return _empty_audit(
            return_column=return_column,
            date_column=date_column,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            weight_step=weight_step,
            max_components=max_components,
            max_drawdown_floor=max_drawdown_floor,
            duplicate_correlation=duplicate_correlation,
        )

    single_metrics = {
        name: _metric_pack(series, periods_per_year=periods_per_year, holding_period=holding_period)
        for name, series in series_by_name.items()
    }
    correlations = _pairwise_correlations(series_by_name)
    correlation_lookup = {
        frozenset((str(row["left"]), str(row["right"]))): _number(row["correlation"]) for row in correlations
    }
    rows: list[dict[str, Any]] = []
    best_return_stream: pd.DataFrame | None = None

    for components, weights in _candidate_weight_specs(
        tuple(series_by_name),
        weight_step=weight_step,
        max_components=max_components,
    ):
        aligned = pd.concat([series_by_name[name].rename(name) for name in components], axis=1, join="inner").dropna()
        blended = aligned.mul(list(weights), axis=1).sum(axis=1) if not aligned.empty else pd.Series(dtype=float)
        metrics = _metric_pack(blended, periods_per_year=periods_per_year, holding_period=holding_period)
        row = _blend_row(
            components=components,
            weights=weights,
            metrics=metrics,
            single_metrics=single_metrics,
            aligned_count=len(aligned),
            source_date_counts={name: int(len(series_by_name[name])) for name in components},
            max_drawdown_floor=max_drawdown_floor,
            correlation_lookup=correlation_lookup,
            duplicate_correlation=duplicate_correlation,
        )
        rows.append(row)
        if row["selection_status"] != "blocked":
            if best_return_stream is None or _score(row) > _score(rows[0]):
                best_return_stream = _series_to_frame(blended)

    rows = sorted(rows, key=lambda row: (row["selection_status"] == "blocked", -_score(row), row["case_id"]))
    pass_rows = [row for row in rows if row["selection_status"] != "blocked"]
    if pass_rows:
        best_components = pass_rows[0]["components"]
        best_weights = pass_rows[0]["weights"]
        aligned = pd.concat([series_by_name[name].rename(name) for name in best_components], axis=1, join="inner").dropna()
        best_return_stream = _series_to_frame(aligned.mul(best_weights, axis=1).sum(axis=1))

    return _sanitize(
        {
            "stage": STAGE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "safety": SAFETY,
            "thresholds": {
                "return_column": return_column or "auto",
                "date_column": date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "weight_step": float(weight_step),
                "max_components": int(max_components),
                "max_drawdown_floor": float(max_drawdown_floor),
                "duplicate_correlation": float(duplicate_correlation),
            },
            "summary": {
                "source_count": int(len(series_by_name)),
                "case_count": int(len(rows)),
                "pass_case_count": int(len(pass_rows)),
                "blocked_case_count": int(len(rows) - len(pass_rows)),
                "best_case_id": pass_rows[0]["case_id"] if pass_rows else None,
            },
            "rows": rows,
            "correlations": correlations,
            "best_blend_period_returns": [] if best_return_stream is None else best_return_stream.to_dict("records"),
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Blend audit is a simulation-preparation layer only; it does not read final holdout or create live signals.",
            },
        }
    )


def write_simulation_shortlist_blend_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    (output / "simulation_shortlist_blend_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "simulation_shortlist_blend_rows.csv", index=False)
    pd.DataFrame(sanitized.get("correlations", [])).to_csv(
        output / "simulation_shortlist_blend_correlations.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("best_blend_period_returns", [])).to_csv(
        output / "best_blend_period_returns.csv",
        index=False,
    )


def _load_return_series(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    return_column: str | None,
    date_column: str,
) -> pd.Series:
    source_path, source_return_column, source_date_column = _normalise_source_spec(
        source,
        default_return_column=return_column,
        default_date_column=date_column,
    )
    frame, _ = load_candidate_period_returns(
        source_path,
        return_column=source_return_column,
        date_column=source_date_column,
    )
    if frame.empty:
        return pd.Series(dtype=float)
    return pd.Series(
        pd.to_numeric(frame["period_return"], errors="coerce").fillna(0.0).to_numpy(dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(frame["date"], errors="coerce")),
    ).dropna().sort_index()


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


def _candidate_weight_specs(
    names: tuple[str, ...],
    *,
    weight_step: float,
    max_components: int,
) -> list[tuple[tuple[str, ...], tuple[float, ...]]]:
    if not 0.0 < float(weight_step) <= 1.0:
        raise ValueError("weight_step must be within (0, 1]")
    units = int(round(1.0 / float(weight_step)))
    if not math.isclose(units * float(weight_step), 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("weight_step must divide 1.0 exactly")
    output: list[tuple[tuple[str, ...], tuple[float, ...]]] = []
    max_size = min(max(int(max_components), 1), len(names))
    for size in range(1, max_size + 1):
        for components in itertools.combinations(sorted(names), size):
            for integer_weights in _positive_integer_compositions(units, size):
                weights = tuple(float(value) / float(units) for value in integer_weights)
                output.append((components, weights))
    return output


def _positive_integer_compositions(total: int, size: int) -> list[tuple[int, ...]]:
    if size == 1:
        return [(int(total),)]
    rows = []
    for first in range(1, int(total) - int(size) + 2):
        for tail in _positive_integer_compositions(int(total) - first, int(size) - 1):
            rows.append((first, *tail))
    return rows


def _metric_pack(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, float]:
    if returns.empty:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "overlap_autocorr_adjusted_sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
        }
    metrics = summarize_returns(returns.reset_index(drop=True), periods_per_year=periods_per_year)
    metrics.update(
        overlap_metrics(
            returns.reset_index(drop=True),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
    )
    return {
        "total_return": _number(metrics.get("total_return")),
        "annualized_return": _number(metrics.get("annualized_return")),
        "annualized_volatility": _number(metrics.get("annualized_volatility")),
        "sharpe": _number(metrics.get("sharpe")),
        "overlap_autocorr_adjusted_sharpe": _number(metrics.get("overlap_autocorr_adjusted_sharpe")),
        "max_drawdown": _number(metrics.get("max_drawdown")),
        "win_rate": _number(metrics.get("win_rate")),
    }


def _blend_row(
    *,
    components: tuple[str, ...],
    weights: tuple[float, ...],
    metrics: Mapping[str, Any],
    single_metrics: Mapping[str, Mapping[str, Any]],
    aligned_count: int,
    source_date_counts: Mapping[str, int],
    max_drawdown_floor: float,
    correlation_lookup: Mapping[frozenset[str], float],
    duplicate_correlation: float,
) -> dict[str, Any]:
    component_metric_rows = [single_metrics[name] for name in components]
    best_component = max(component_metric_rows, key=lambda row: _number(row.get("annualized_return")))
    best_component_overlap = max(component_metric_rows, key=lambda row: _number(row.get("overlap_autocorr_adjusted_sharpe")))
    best_component_drawdown = max(component_metric_rows, key=lambda row: _number(row.get("max_drawdown")))
    blockers = _blockers(
        metrics,
        aligned_count=aligned_count,
        max_drawdown_floor=max_drawdown_floor,
        source_date_counts=source_date_counts,
        component_count=len(components),
        max_pairwise_correlation=_max_pairwise_correlation(components, correlation_lookup),
        duplicate_correlation=duplicate_correlation,
    )
    return _sanitize(
        {
            "case_id": _case_id(components, weights),
            "components": list(components),
            "weights": [float(value) for value in weights],
            "component_count": int(len(components)),
            "aligned_period_count": int(aligned_count),
            "source_date_counts": dict(source_date_counts),
            "selection_status": "blocked" if blockers else "blend_candidate",
            "blockers": blockers,
            "score": _row_score(metrics),
            "total_return": _number(metrics.get("total_return")),
            "annualized_return": _number(metrics.get("annualized_return")),
            "annualized_volatility": _number(metrics.get("annualized_volatility")),
            "sharpe": _number(metrics.get("sharpe")),
            "overlap_autocorr_adjusted_sharpe": _number(metrics.get("overlap_autocorr_adjusted_sharpe")),
            "max_drawdown": _number(metrics.get("max_drawdown")),
            "win_rate": _number(metrics.get("win_rate")),
            "best_component_annualized_return": _number(best_component.get("annualized_return")),
            "best_component_overlap_sharpe": _number(best_component_overlap.get("overlap_autocorr_adjusted_sharpe")),
            "best_component_max_drawdown": _number(best_component_drawdown.get("max_drawdown")),
            "delta_vs_best_component_annualized_return": _number(metrics.get("annualized_return"))
            - _number(best_component.get("annualized_return")),
            "delta_vs_best_component_overlap_sharpe": _number(metrics.get("overlap_autocorr_adjusted_sharpe"))
            - _number(best_component_overlap.get("overlap_autocorr_adjusted_sharpe")),
            "delta_vs_best_component_max_drawdown": _number(metrics.get("max_drawdown"))
            - _number(best_component_drawdown.get("max_drawdown")),
        }
    )


def _blockers(
    metrics: Mapping[str, Any],
    *,
    aligned_count: int,
    max_drawdown_floor: float,
    source_date_counts: Mapping[str, int],
    component_count: int,
    max_pairwise_correlation: float | None,
    duplicate_correlation: float,
) -> list[str]:
    blockers = []
    if aligned_count <= 0:
        blockers.append("no_aligned_returns")
    if any(count != aligned_count for count in source_date_counts.values()):
        blockers.append("date_alignment_loss")
    if _number(metrics.get("total_return")) <= 0.0:
        blockers.append("non_positive_total_return")
    if _number(metrics.get("annualized_return")) <= 0.0:
        blockers.append("non_positive_annualized_return")
    if _number(metrics.get("max_drawdown")) < float(max_drawdown_floor):
        blockers.append("max_drawdown_below_floor")
    if component_count > 1 and max_pairwise_correlation is not None and max_pairwise_correlation >= duplicate_correlation:
        blockers.append("high_component_return_correlation")
    return blockers


def _case_id(components: tuple[str, ...], weights: tuple[float, ...]) -> str:
    pieces = []
    for name, weight in zip(components, weights):
        pieces.append(f"{name}_{int(round(float(weight) * 100.0)):02d}")
    return "__".join(pieces)


def _row_score(metrics: Mapping[str, Any]) -> float:
    return (
        _number(metrics.get("annualized_return")) * 100.0
        + _number(metrics.get("overlap_autocorr_adjusted_sharpe")) * 2.0
        + _number(metrics.get("sharpe")) * 0.5
        + _number(metrics.get("max_drawdown")) * 2.0
    )


def _score(row: Mapping[str, Any]) -> float:
    return _number(row.get("score"))


def _pairwise_correlations(series_by_name: Mapping[str, pd.Series]) -> list[dict[str, Any]]:
    rows = []
    names = sorted(series_by_name)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            joined = pd.concat([series_by_name[left].rename("left"), series_by_name[right].rename("right")], axis=1).dropna()
            if len(joined) < 3 or joined["left"].std() == 0.0 or joined["right"].std() == 0.0:
                continue
            rows.append({"left": left, "right": right, "correlation": _number(joined["left"].corr(joined["right"]))})
    return sorted(rows, key=lambda row: -abs(float(row["correlation"])))


def _max_pairwise_correlation(
    components: tuple[str, ...],
    correlation_lookup: Mapping[frozenset[str], float],
) -> float | None:
    values = []
    for left_index, left in enumerate(components):
        for right in components[left_index + 1 :]:
            key = frozenset((str(left), str(right)))
            if key in correlation_lookup:
                values.append(_number(correlation_lookup[key]))
    return max(values) if values else None


def _series_to_frame(series: pd.Series) -> pd.DataFrame:
    if series.empty:
        return pd.DataFrame(columns=["date", "period_return"])
    return pd.DataFrame(
        {
            "date": pd.DatetimeIndex(series.index).date.astype(str),
            "period_return": series.to_numpy(dtype=float),
        }
    )


def _empty_audit(**thresholds: Any) -> dict[str, Any]:
    return _sanitize(
        {
            "stage": STAGE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "safety": SAFETY,
            "thresholds": thresholds,
            "summary": {
                "source_count": 0,
                "case_count": 0,
                "pass_case_count": 0,
                "blocked_case_count": 0,
                "best_case_id": None,
            },
            "rows": [],
            "correlations": [],
            "best_blend_period_returns": [],
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Blend audit is a simulation-preparation layer only.",
            },
        }
    )


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
