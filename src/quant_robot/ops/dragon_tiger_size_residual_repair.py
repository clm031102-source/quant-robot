from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.dragon_tiger_pit_ic_prescreen import (
    DRAGON_TIGER_DEFAULT_HORIZONS,
    compute_dragon_tiger_factor_frame,
    load_dragon_tiger_stock_day,
    load_stock_basic,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import summarize_event_factor_pit_ic_prescreen
from quant_robot.ops.event_factor_preregistration import SAFETY
from quant_robot.research.labels import make_forward_returns


STAGE = "dragon_tiger_size_residual_repair_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round234_dragon_tiger_repaired_lead_dedup_before_portfolio_grid_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure"
SOURCE_TO_REPAIR_NAME = {
    "dragon_tiger_net_buy_continuation_1d": "dragon_tiger_net_buy_continuation_size_residual_1d",
    "dragon_tiger_institutional_net_buy_pressure_1d": "dragon_tiger_institutional_net_buy_pressure_size_residual_1d",
}
REPAIR_FACTOR_NAMES = tuple(SOURCE_TO_REPAIR_NAME.values())
RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "industry_neutral_retention_ratio",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "size_neutral_retention_ratio",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "research_lead",
    "promotion_allowed",
    "blockers",
]


def build_dragon_tiger_size_residual_repair_prescreen(
    *,
    stock_day: pd.DataFrame | None = None,
    processed_root: str | Path | None = None,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    stock_basic: pd.DataFrame | None = None,
    stock_basic_path: str | Path | None = None,
    market: str = "CN",
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DRAGON_TIGER_DEFAULT_HORIZONS,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    alpha: float = 0.05,
) -> dict[str, Any]:
    if bars is None:
        if bars_roots is None:
            raise ValueError("Either bars or bars_roots must be provided")
        bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    else:
        bars = _normalise_bars(bars)
    if stock_day is None:
        if processed_root is None:
            raise ValueError("Either stock_day or processed_root must be provided")
        stock_day = load_dragon_tiger_stock_day(
            processed_root,
            market=market,
            start_year=pd.Timestamp(analysis_start_date).year,
            end_year=pd.Timestamp(analysis_end_date).year,
        )
    if stock_basic is None:
        stock_basic = load_stock_basic(stock_basic_path)
    source_specs = [{"factor_name": name} for name in SOURCE_TO_REPAIR_NAME]
    source_frame = compute_dragon_tiger_factor_frame(
        stock_day,
        bars,
        candidate_specs=source_specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    factor_frame = compute_dragon_tiger_size_residual_factor_frame(source_frame)
    factor_frame = _filter_date_window(
        factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    specs = _repair_candidate_specs()
    result = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=tuple(horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
    )
    _specialize_result(
        result,
        bars=bars,
        source_frame=source_frame,
        factor_frame=factor_frame,
        labels=labels,
        processed_root=processed_root,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    return result


def compute_dragon_tiger_size_residual_factor_frame(factor_frame: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty:
        return _empty_factor_frame()
    frame = factor_frame[factor_frame["factor_name"].isin(SOURCE_TO_REPAIR_NAME)].copy()
    if frame.empty:
        return _empty_factor_frame()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    frame["log_adv20"] = pd.to_numeric(frame["log_adv20"], errors="coerce")
    rows: list[pd.DataFrame] = []
    for (source_name, signal_date), group in frame.groupby(["factor_name", "date"], sort=False):
        valid = group.dropna(subset=["factor_value", "log_adv20"]).copy()
        if len(valid) < 3 or valid["log_adv20"].nunique(dropna=True) < 2:
            continue
        valid["factor_value"] = _simple_residual(
            valid["factor_value"].rank(method="average"),
            valid["log_adv20"].rank(method="average"),
        )
        valid["source_factor_name"] = str(source_name)
        valid["factor_name"] = SOURCE_TO_REPAIR_NAME[str(source_name)]
        rows.append(valid)
    if not rows:
        return _empty_factor_frame()
    output = pd.concat(rows, ignore_index=True)
    return (
        output[
            [
                "date",
                "event_date",
                "asset_id",
                "market",
                "factor_name",
                "factor_value",
                "amount",
                "adv20_amount",
                "log_adv20",
                "pit_lag_trade_days",
                "source_event_count",
                "source_factor_name",
            ]
        ]
        .dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_dragon_tiger_size_residual_repair_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "dragon_tiger_size_residual_repair_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "dragon_tiger_size_residual_repair_prescreen.md").write_text(
        render_dragon_tiger_size_residual_repair_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "dragon_tiger_size_residual_repair_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "dragon_tiger_size_residual_repair_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "dragon_tiger_size_residual_repair_neutral_observations.csv",
        result.get("neutral_observations", []),
        ["factor_name", "horizon", "date", "industry_neutral_rank_ic", "size_neutral_rank_ic", "cross_section", "industry_count"],
    )


def render_dragon_tiger_size_residual_repair_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Dragon-Tiger Size Residual Repair Prescreen Round233",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {size:.4f} | {lead} |".format(
                factor_name=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage residualizes Dragon-Tiger net-buy pressure against daily `log_adv20` exposure before retesting PIT IC.",
            "- It is still not a portfolio backtest.",
            "- Promotion remains blocked until lead de-dup, walk-forward, cost/capacity, regime, strict statistics, and final holdout gates clear.",
        ]
    )
    return "\n".join(lines) + "\n"


def _specialize_result(
    result: dict[str, Any],
    *,
    bars: pd.DataFrame,
    source_frame: pd.DataFrame,
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    processed_root: str | Path | None,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
    execution_lag: int,
    pit_lag_trade_days: int,
) -> None:
    result["stage"] = STAGE
    summary = result.get("summary", {})
    summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS if summary.get("research_lead_count", 0) else NEXT_DIRECTION_WITHOUT_LEADS
    result["data_window"] = {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "source_factor_rows": int(len(source_frame)),
        "factor_rows": int(len(factor_frame)),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_walk_forward_oos_clearance",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "event_signal_date_rule": "tushare_dragon_tiger_available_date_strictly_after_trade_date",
        "execution_lag": int(execution_lag),
        "same_day_event_trading_allowed": False,
    }
    result["residual_repair_policy"] = {
        "source_factor_names": list(SOURCE_TO_REPAIR_NAME),
        "repair_factor_names": list(REPAIR_FACTOR_NAMES),
        "daily_residual_exposure": "log_adv20_rank",
        "method": "daily_cross_sectional_rank_residualization_before_pit_ic",
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "dragon_tiger_repaired_lead_dedup_before_portfolio_grid_preflight",
        "reason": "This is a size residual repair IC prescreen. Portfolio grids remain blocked until lead de-dup, walk-forward, cost/capacity, regime, strict statistics, and final holdout gates clear.",
    }
    result["processed_root"] = str(Path(processed_root)) if processed_root else None
    result["generated_at"] = date.today().isoformat()
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_dragon_tiger_size_residual_repair_markdown(result)


def _repair_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": name,
            "family": "dragon_tiger_attention_reversal_event_size_residual_repair",
            "formula_template": "daily_rank_residual(source_factor, log_adv20)",
            "direction": "higher_is_better",
            "required_endpoints": ["processed/dragon_tiger_stock_day", "processed/bars"],
            "required_fields": ["available_date", "factor_value", "log_adv20"],
            "event_date_fields": ["date", "available_date"],
            "windows": [1],
            "economic_rationale": "Retest the strongest Dragon-Tiger net-buy pressure signals after removing the observed size/liquidity exposure.",
            "public_reference_tags": ["alphalens", "factor_neutralization", "event_study"],
            "expected_failure_modes": ["raw_signal_was_size_beta", "residual_ic_collapses", "event_sparse_coverage"],
            "portfolio_backtest_allowed": False,
            "promotion_allowed": False,
        }
        for name in REPAIR_FACTOR_NAMES
    ]


def _simple_residual(y: pd.Series, x: pd.Series) -> pd.Series:
    frame = pd.DataFrame({"y": pd.to_numeric(y, errors="coerce"), "x": pd.to_numeric(x, errors="coerce")}).dropna()
    output = pd.Series(index=y.index, dtype=float)
    if len(frame) < 3 or frame["x"].nunique() < 2:
        output.loc[frame.index] = frame["y"] - frame["y"].mean()
        return output
    x_centered = frame["x"] - frame["x"].mean()
    denominator = float((x_centered * x_centered).sum())
    if denominator == 0.0:
        output.loc[frame.index] = frame["y"] - frame["y"].mean()
        return output
    beta = float(((frame["y"] - frame["y"].mean()) * x_centered).sum() / denominator)
    alpha = float(frame["y"].mean() - beta * frame["x"].mean())
    output.loc[frame.index] = frame["y"] - (alpha + beta * frame["x"])
    return output


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date", "asset_id", "market", "adj_close", "amount"]).reset_index(drop=True)


def _filter_date_window(frame: pd.DataFrame, *, start_date: str, end_date: str, include_final_holdout: bool) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "event_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "pit_lag_trade_days",
            "source_event_count",
            "source_factor_name",
        ]
    )


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
