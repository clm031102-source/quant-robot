from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (
    RESULT_COLUMNS as PUBLIC_REFERENCE_RESULT_COLUMNS,
    _apply_multiple_testing,
    _is_research_lead,
    _nonzero,
    _result_blockers,
    _safe_log,
    _sanitize,
    _spec_payload,
    _streaming_data_window,
    _summarize_factor_horizon,
    _write_csv,
    load_public_reference_multi_family_bars,
)
from quant_robot.ops.public_technical_failure_reversal_preregistration import (
    NEXT_REQUIRED_GATE as PREREG_NEXT_REQUIRED_GATE,
    SAFETY,
    STAGE as PREREG_STAGE,
    default_public_technical_failure_reversal_specs,
)


STAGE = "public_technical_failure_reversal_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round156_public_technical_failure_reversal_neutral_dedup_before_portfolio_grid"
NEXT_DIRECTION_WITHOUT_LEADS = "round156_rotate_after_public_technical_failure_reversal_prescreen_failure"
RESULT_COLUMNS = [
    "factor_name",
    "family",
    "source_failed_positive_factor",
    *[column for column in PUBLIC_REFERENCE_RESULT_COLUMNS if column not in {"factor_name", "family"}],
]


def build_public_technical_failure_reversal_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    moneyflow_input_root: str | Path,
    preregistration_json: str | Path | None = None,
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    alpha: float = 0.05,
) -> dict[str, Any]:
    specs = _load_candidate_specs(preregistration_json, candidate_specs)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    features = _technical_feature_frame(bars, horizons=tuple(horizons), execution_lag=execution_lag)
    result = summarize_public_technical_failure_reversal_prescreen_from_features(
        features,
        candidate_specs=specs,
        horizons=tuple(horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        alpha=alpha,
    )
    result.update(
        {
            "bars_roots": [str(Path(root)) for root in bars_roots],
            "factor_input_root": str(Path(factor_input_root)),
            "moneyflow_input_root": str(Path(moneyflow_input_root)),
            "preregistration_json": str(Path(preregistration_json)) if preregistration_json else None,
            "data_window": _streaming_data_window(
                bars,
                features,
                horizons=tuple(horizons),
                min_signal_date_amount=min_signal_date_amount,
            ),
            "holdout_policy": {
                "final_holdout_included": include_final_holdout,
                "analysis_start_date": analysis_start_date,
                "analysis_end_date": analysis_end_date,
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "read_once_after_neutral_dedup_walk_forward_clearance_only",
            },
            "source_context": {
                "preregistration_stage": PREREG_STAGE,
                "preregistration_next_required_gate": PREREG_NEXT_REQUIRED_GATE,
                "public_negative_evidence_is_hypothesis_source_only": True,
                "portfolio_grid_blocked_before_neutral_dedup": True,
            },
            "capacity_policy": {
                "min_signal_date_amount": min_signal_date_amount,
                "adv20_amount_filter_enabled": True,
                "liquidity_term_kept_positive_in_inverse_formulas": True,
                "portfolio_backtest_allowed_before_prescreen_lead": False,
            },
        }
    )
    result["markdown"] = render_public_technical_failure_reversal_prescreen_markdown(result)
    return result


def summarize_public_technical_failure_reversal_prescreen_from_features(
    features: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any],
    horizons: tuple[int, ...],
    min_cross_section: int,
    min_ic_observations: int,
    min_signal_date_amount: float,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    max_top_quantile_turnover: float = 0.90,
) -> dict[str, Any]:
    requested_horizons = tuple(int(horizon) for horizon in horizons)
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    candidate_values = _candidate_value_series(features)
    results: list[dict[str, Any]] = []
    ic_rows: list[dict[str, Any]] = []
    aligned_rows = 0
    factor_rows = 0
    factor_names_with_rows: set[str] = set()
    families_with_rows: set[str] = set()
    unique_assets: set[str] = set()
    for spec in candidate_specs:
        name = _field(spec, "factor_name")
        family = _field(spec, "family")
        source_failed = _field(spec, "source_failed_positive_factor")
        values = candidate_values.get(name)
        if values is None:
            factor_frame = _empty_factor_frame()
        else:
            factor_frame = features.loc[
                capacity_mask,
                ["date", "asset_id", "market", "amount", "adv20_amount"],
            ].copy()
            factor_frame["family"] = family
            factor_frame["source_failed_positive_factor"] = source_failed
            factor_frame["factor_name"] = name
            factor_frame["factor_value"] = values.loc[capacity_mask]
            factor_frame = factor_frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        factor_rows += len(factor_frame)
        if not factor_frame.empty:
            factor_names_with_rows.add(name)
            families_with_rows.add(family)
            unique_assets.update(factor_frame["asset_id"].astype(str).unique().tolist())
        for horizon in requested_horizons:
            forward_column = f"forward_return_{horizon}"
            if factor_frame.empty or forward_column not in features:
                group = pd.DataFrame(columns=list(factor_frame.columns) + ["forward_return"])
            else:
                group = factor_frame.copy()
                group["forward_return"] = features.loc[group.index, forward_column]
                group = group.dropna(subset=["forward_return"])
            aligned_rows += len(group)
            summary, observations = _summarize_factor_horizon(
                factor_name=name,
                horizon=int(horizon),
                group=group,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
            )
            summary["family"] = family
            summary["source_failed_positive_factor"] = source_failed
            results.append(summary)
            ic_rows.extend(observations)
    _apply_multiple_testing(results, alpha=alpha)
    for row in results:
        row["research_lead"] = _is_research_lead(
            row,
            min_abs_ic=min_abs_ic,
            min_abs_icir=min_abs_icir,
            min_positive_ic_rate=min_positive_ic_rate,
            max_top_quantile_turnover=max_top_quantile_turnover,
        )
        row["promotion_allowed"] = False
        row["blockers"] = _dedupe(
            list(row.get("blockers", []) or [])
            + _result_blockers(row)
            + ["promotion_requires_neutral_dedup_walk_forward_cost_capacity_regime_gates"]
        )
    summary = {
        "passes": True,
        "candidate_count": len(candidate_specs),
        "family_count": len({_field(spec, "family") for spec in candidate_specs}),
        "factor_names_with_rows": len(factor_names_with_rows),
        "families_with_rows": len(families_with_rows),
        "test_count": len(results),
        "research_lead_count": sum(1 for row in results if row["research_lead"]),
        "multiple_testing_lead_count": sum(1 for row in results if row["fdr_significant"]),
        "promotion_allowed_candidates": 0,
        "portfolio_backtest_allowed_candidates": 0,
        "factor_rows": int(factor_rows),
        "label_rows": int(
            sum(
                features[f"forward_return_{horizon}"].notna().sum()
                for horizon in requested_horizons
                if f"forward_return_{horizon}" in features
            )
        ),
        "aligned_rows": int(aligned_rows),
        "horizons": sorted(requested_horizons),
        "min_cross_section": min_cross_section,
        "min_ic_observations": min_ic_observations,
        "streaming_factor_evaluation": True,
        "unique_assets": len(unique_assets),
    }
    summary["next_direction"] = (
        NEXT_DIRECTION_WITH_LEADS if summary["research_lead_count"] else NEXT_DIRECTION_WITHOUT_LEADS
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": summary,
        "candidate_specs": [_spec_payload(spec) for spec in candidate_specs],
        "multiple_testing_policy": {
            "alpha": alpha,
            "method": "Bonferroni and Benjamini-Hochberg FDR across Round154 public technical failure-reversal factor x horizon tests",
            "counts_all_round154_candidates": True,
            "round154_candidate_count": len(candidate_specs),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_next_gate": "neutral_reference_dedup_before_portfolio_grid",
            "reason": "Round155 is a long-cycle IC/quantile/turnover prescreen only.",
        },
        "results": sorted(results, key=lambda row: (not row["research_lead"], row["family"], -abs(row["mean_spearman_ic"]))),
        "ic_observations": ic_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_technical_failure_reversal_prescreen_markdown(result)
    return result


def write_public_technical_failure_reversal_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "public_technical_failure_reversal_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_technical_failure_reversal_prescreen.md").write_text(
        render_public_technical_failure_reversal_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_technical_failure_reversal_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "public_technical_failure_reversal_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_public_technical_failure_reversal_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Public Technical Failure-Reversal Prescreen Round155",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Portfolio backtest allowed candidates: {summary.get('portfolio_backtest_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Family | H | IC | ICIR | t | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:30]:
        lines.append(
            "| {factor_name} | {family} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                family=row.get("family", ""),
                horizon=int(row["horizon"]),
                ic=float(row["mean_spearman_ic"]),
                icir=float(row["icir"]),
                t=float(row["ic_t_stat"]),
                pos=float(row["ic_positive_rate"]),
                spread=float(row["quantile_spread"]),
                mono=float(row["quantile_monotonicity"]),
                turnover=float(row["avg_top_quantile_turnover"]),
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor or launch a portfolio grid.",
            "- All Round154 candidates are counted in multiple-testing accounting.",
            "- Any lead must next pass neutralization, reference de-duplication, walk-forward, costs, capacity, and regime gates.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_value_series(features: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "inverse_donchian_breakout_failure_liquid_20": (
            -0.45 * features["z_donchian_position_20"] - 0.30 * features["z_return_efficiency_20"] + 0.25 * features["z_log_adv20"]
        ),
        "inverse_price_efficiency_failure_liquid_20": (
            -0.50 * features["z_return_efficiency_20"] - 0.25 * features["z_return_20"] + 0.25 * features["z_log_adv20"]
        ),
        "inverse_volume_price_resonance_failure_20_60": (
            -0.40 * features["z_return_20"]
            - 0.30 * features["z_amount_trend_20_60"]
            - 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "inverse_supertrend_breakout_failure_10_20": (
            -0.35 * features["z_supertrend_state_10_3"]
            - 0.35 * features["z_price_breakout_20"]
            - 0.20 * features["z_return_efficiency_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "supertrend_extension_continuation_repair_10_3": (
            -0.45 * features["z_supertrend_distance_reversal_10_3"]
            + 0.30 * features["z_neg_atr_ratio_10"]
            + 0.25 * features["z_log_adv20"]
        ),
        "inverse_rsrs_slope_failure_liquid_18_60": (
            -0.45 * features["z_rsrs_slope_18"]
            - 0.30 * features["z_rsrs_slope_delta_60"]
            + 0.15 * features["z_neg_realized_vol_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "rsrs_residual_extreme_reversal_repair_18": (
            -0.55 * features["z_rsrs_residual_z_18"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "inverse_kbar_momentum_failure_lowvol_20": (
            -0.40 * features["z_kbar_close_position_20"]
            - 0.35 * features["z_skip5_momentum_20"]
            + 0.25 * features["z_neg_realized_vol_20"]
        ),
    }


def _technical_feature_frame(
    bars: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "high", "low", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy()
        close = group["adj_close"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        returns = close.pct_change()
        rolling_high20 = high.rolling(20, min_periods=5).max()
        rolling_low20 = low.rolling(20, min_periods=5).min()
        range_width = _nonzero(rolling_high20 - rolling_low20)
        ma10 = close.rolling(10, min_periods=5).mean()
        atr10 = _average_true_range(high, low, close, 10)
        rsrs_slope = high.rolling(18, min_periods=10).cov(low) / _nonzero(low.rolling(18, min_periods=10).var())
        rsrs_residual = high - rsrs_slope * low
        piece = group[["date", "asset_id", "market", "adj_close", "amount"]].copy()
        piece["return_1d"] = returns
        piece["return_20"] = close.pct_change(20)
        piece["skip5_momentum_20"] = close.shift(5).pct_change(20)
        piece["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(
            amount.rolling(60, min_periods=20).mean()
        ) - 1.0
        piece["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        piece["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        piece["hl_range_20"] = ((high / low) - 1.0).rolling(20, min_periods=5).mean()
        piece["donchian_position_20"] = (close - rolling_low20) / range_width
        piece["price_breakout_20"] = close / _nonzero(rolling_high20) - 1.0
        piece["return_efficiency_20"] = piece["return_20"] / _nonzero(returns.abs().rolling(20, min_periods=5).sum())
        intraday_range = _nonzero(high - low)
        piece["kbar_close_position_20"] = ((close - low) / intraday_range).rolling(20, min_periods=5).mean()
        piece["atr_ratio_10"] = atr10 / _nonzero(close)
        piece["supertrend_distance_reversal_10_3"] = -((close - ma10) / _nonzero(3.0 * atr10))
        piece["supertrend_state_10_3"] = (close > ma10).astype(float) * 2.0 - 1.0
        piece["rsrs_slope_18"] = rsrs_slope
        piece["rsrs_slope_delta_60"] = rsrs_slope - rsrs_slope.rolling(60, min_periods=20).mean()
        piece["rsrs_residual_z_18"] = (
            rsrs_residual - rsrs_residual.rolling(18, min_periods=10).mean()
        ) / _nonzero(rsrs_residual.rolling(18, min_periods=10).std(ddof=0))
        for horizon in horizons:
            entry = close.shift(-execution_lag)
            exit_ = close.shift(-(execution_lag + int(horizon)))
            piece[f"forward_return_{int(horizon)}"] = exit_ / entry - 1.0
        pieces.append(piece)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = _safe_log(features["adv20_amount"])
    z_inputs = {
        "z_donchian_position_20": features["donchian_position_20"],
        "z_return_efficiency_20": features["return_efficiency_20"],
        "z_log_adv20": features["log_adv20"],
        "z_return_20": features["return_20"],
        "z_amount_trend_20_60": features["amount_trend_20_60"],
        "z_supertrend_state_10_3": features["supertrend_state_10_3"],
        "z_price_breakout_20": features["price_breakout_20"],
        "z_supertrend_distance_reversal_10_3": features["supertrend_distance_reversal_10_3"],
        "z_neg_atr_ratio_10": -features["atr_ratio_10"],
        "z_rsrs_slope_18": features["rsrs_slope_18"],
        "z_rsrs_slope_delta_60": features["rsrs_slope_delta_60"],
        "z_neg_realized_vol_20": -features["realized_vol_20"],
        "z_rsrs_residual_z_18": features["rsrs_residual_z_18"],
        "z_kbar_close_position_20": features["kbar_close_position_20"],
        "z_skip5_momentum_20": features["skip5_momentum_20"],
    }
    for column, values in z_inputs.items():
        features[column] = _cs_zscore(features, values)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window, min_periods=max(5, window // 2)).mean()


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / _nonzero(std)


def _load_candidate_specs(preregistration_json: str | Path | None, candidate_specs: Sequence[Any] | None) -> list[Any]:
    if candidate_specs is not None:
        return list(candidate_specs)
    if preregistration_json is None:
        return default_public_technical_failure_reversal_specs()
    packet = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [candidate for candidate in packet.get("candidates", []) or [] if isinstance(candidate, dict)]
    return candidates or default_public_technical_failure_reversal_specs()


def _field(spec: Any, name: str) -> Any:
    if isinstance(spec, dict):
        return spec.get(name)
    return getattr(spec, name)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "amount",
            "adv20_amount",
            "family",
            "source_failed_positive_factor",
            "factor_name",
            "factor_value",
        ]
    )


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
