from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import DEFAULT_CAPACITY_FILTERS, SAFETY
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    _cs_zscore,
    _data_window,
    _normalise_bars,
    _sanitize,
    _write_csv,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "high_52week_quality_prescreen"
DEFAULT_CANDIDATE_PLAN = Path("configs/factor_mining_candidate_plan_round207_52week_high_quality_20260624.json")
NEXT_REQUIRED_GATE = "industry_style_residual_audit_before_portfolio_conversion"


def build_high_52week_quality_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_plan_json: str | Path = DEFAULT_CANDIDATE_PLAN,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    candidate_plan = _load_candidate_plan(candidate_plan_json)
    specs = _candidate_specs(candidate_plan)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_high_52week_quality_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["stage"] = STAGE
    result["candidate_plan_json"] = str(Path(candidate_plan_json))
    result["family_rotation_policy"] = candidate_plan.get("family_rotation_policy", {})
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_residual_prescreen_walk_forward_cost_capacity_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_REQUIRED_GATE,
        "reason": (
            "This is an IC, quantile, turnover, and multiple-testing prescreen for a newly "
            "pre-registered 52-week high anchor family; it is not portfolio evidence."
        ),
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_high_52week_quality_prescreen_markdown(result)
    return result


def compute_high_52week_quality_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = list(candidate_specs or _candidate_specs(_load_candidate_plan(DEFAULT_CANDIDATE_PLAN)))
    features = _feature_frame(bars)
    if features.empty:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "high_52w_proximity_liquid_quality_252_20": (
            0.45 * features["z_high_52w_proximity"]
            + 0.25 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
            + 0.10 * features["z_neg_realized_vol_20"]
        ),
        "high_52w_pullback_resilience_252_20": (
            0.40 * features["z_high_52w_proximity"]
            + 0.30 * features["z_neg_drawdown_from_20d_high"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "high_52w_breakout_amount_confirmation_252_20": (
            0.40 * features["z_high_52w_proximity"]
            + 0.30 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "high_52w_low_drawdown_residual_anchor_252_60": (
            0.45 * features["z_high_52w_proximity"]
            + 0.25 * features["z_neg_max_drawdown_60"]
            + 0.20 * features["z_neg_realized_vol_60"]
            + 0.10 * features["z_log_adv20"]
        ),
        "avoid_high_52w_proximity_overextension_252_20": (
            -0.45 * features["z_high_52w_proximity"]
            + 0.25 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
            + 0.10 * features["z_neg_realized_vol_20"]
        ),
        "avoid_high_52w_breakout_amount_exhaustion_252_20": (
            -0.40 * features["z_high_52w_proximity"]
            - 0.30 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "avoid_high_52w_pullback_failure_252_20": (
            -0.40 * features["z_high_52w_proximity"]
            - 0.30 * features["z_neg_drawdown_from_20d_high"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "avoid_high_52w_low_drawdown_crowding_252_60": (
            -0.45 * features["z_high_52w_proximity"]
            - 0.25 * features["z_neg_max_drawdown_60"]
            - 0.20 * features["z_neg_realized_vol_60"]
            + 0.10 * features["z_log_adv20"]
        ),
    }
    allowed_names = {_factor_name(spec) for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def write_high_52week_quality_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "high_52week_quality_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "high_52week_quality_prescreen.md").write_text(
        render_high_52week_quality_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "high_52week_quality_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "high_52week_quality_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_high_52week_quality_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# High 52-Week Quality Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor to paper-ready or live use.",
            "- Any lead must next pass industry/style residualization before portfolio conversion.",
            "- If no lead survives within three rounds, the family rotation gate blocks same-family continuation.",
        ]
    )
    return "\n".join(lines) + "\n"


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    bars = _normalise_bars(bars)
    pieces: list[pd.DataFrame] = []
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        high = group["high"]
        amount = group["amount"]
        returns = close.pct_change()
        rolling_high_252 = close.rolling(252, min_periods=120).max()
        rolling_high_20 = high.rolling(20, min_periods=5).max()
        rolling_high_60 = close.rolling(60, min_periods=20).max()
        adv20 = amount.rolling(20, min_periods=5).mean()
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["adv20_amount"] = adv20
        frame["high_52w_proximity"] = close / rolling_high_252 - 1.0
        frame["momentum_20"] = close.pct_change(20)
        frame["return_efficiency_20"] = frame["momentum_20"] / returns.abs().rolling(20, min_periods=5).sum()
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        frame["realized_vol_60"] = returns.rolling(60, min_periods=20).std(ddof=0)
        frame["drawdown_from_20d_high"] = 1.0 - close / rolling_high_20
        frame["max_drawdown_60"] = 1.0 - close / rolling_high_60
        frame["amount_trend_20_60"] = (
            amount.rolling(20, min_periods=10).mean() / amount.rolling(60, min_periods=20).mean() - 1.0
        )
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = features["adv20_amount"].where(features["adv20_amount"] > 0).apply(math.log)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_high_52w_proximity": frame["high_52w_proximity"],
        "z_return_efficiency_20": frame["return_efficiency_20"],
        "z_log_adv20": frame["log_adv20"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_neg_drawdown_from_20d_high": -frame["drawdown_from_20d_high"],
        "z_amount_trend_20_60": frame["amount_trend_20_60"],
        "z_neg_max_drawdown_60": -frame["max_drawdown_60"],
        "z_neg_realized_vol_60": -frame["realized_vol_60"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _load_candidate_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate_specs(candidate_plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(candidate) for candidate in candidate_plan.get("candidates", []) if isinstance(candidate, dict)]


def _factor_name(spec: dict[str, Any]) -> str:
    return str(spec.get("factor_name", "")).strip()
