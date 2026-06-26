from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    PUBLIC_REFERENCE_PROJECTS,
    SAFETY,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    _data_window,
    _normalise_bars,
    _sanitize,
    _write_csv,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.market_residual_risk_premia_preregistration import (
    ROUND107_109_SOURCE_AUDIT,
    default_market_residual_risk_premia_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "market_residual_risk_premia_prescreen"
NEXT_DEDUP_DIRECTION = "round112_market_residual_lead_exposure_dedup"
NEXT_ROTATE_DIRECTION = "round112_family_rotation_after_market_residual_prescreen_failure"
NEXT_REQUIRED_GATE = "market_exposure_diagnostic_for_round111_leads"


def build_market_residual_risk_premia_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_market_residual_risk_premia_candidate_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_market_residual_risk_premia_factors(
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
    result = summarize_market_residual_risk_premia_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["markdown"] = render_market_residual_risk_premia_prescreen_markdown(result)
    return result


def build_equal_weight_market_proxy(
    bars: pd.DataFrame,
    *,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    frame = _normalise_bars(bars).sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["asset_return_1d"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change()
    eligible = frame[
        frame["asset_return_1d"].replace([np.inf, -np.inf], np.nan).notna()
        & (frame["amount"] >= min_signal_date_amount)
    ]
    proxy = (
        eligible.groupby(["date", "market"], as_index=False)["asset_return_1d"]
        .mean()
        .rename(columns={"asset_return_1d": "market_equal_weight_return"})
    )
    return proxy.sort_values(["market", "date"]).reset_index(drop=True)


def compute_market_residual_risk_premia_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_market_residual_risk_premia_candidate_specs())
    features = _feature_frame(bars, min_signal_date_amount=min_signal_date_amount)
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "low_beta_120": -1.00 * features["z_beta_120"] + 0.20 * features["z_log_adv20"],
        "downside_beta_low_120": (
            -0.80 * features["z_downside_beta_120"]
            - 0.20 * features["z_downside_residual_vol_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "idio_vol_low_60": (
            -0.75 * features["z_residual_vol_60"]
            - 0.15 * features["z_abs_residual_return_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "residual_reversal_5_60": (
            0.70 * features["z_neg_residual_return_5"]
            + 0.20 * features["z_neg_residual_vol_60"]
            + 0.10 * features["z_log_adv20"]
        ),
        "residual_momentum_quality_20_120": (
            0.55 * features["z_residual_momentum_120_skip20"]
            + 0.25 * features["z_residual_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "low_market_corr_60": (
            -0.70 * features["z_market_corr_60"]
            - 0.20 * features["z_residual_vol_60"]
            + 0.10 * features["z_log_adv20"]
        ),
        "crash_resilience_60": (
            -0.50 * features["z_co_crash_days_60"]
            - 0.30 * features["z_downside_residual_vol_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "beta_adjusted_range_contraction_60": (
            -0.45 * features["z_beta_adjusted_hl_range_60"]
            - 0.35 * features["z_residual_vol_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "downside_residual_vol_low_60": (
            -0.80 * features["z_downside_residual_vol_60"] + 0.20 * features["z_log_adv20"]
        ),
        "positive_residual_skew_60": (
            0.70 * features["z_residual_skew_60"]
            - 0.20 * features["z_residual_vol_60"]
            + 0.10 * features["z_log_adv20"]
        ),
    }
    allowed_names = {spec.factor_name for spec in specs}
    base_columns = [
        "date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "market_equal_weight_return",
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
    ]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
        & features["market_equal_weight_return"].notna()
    )
    rows: list[pd.DataFrame] = []
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_market_residual_risk_premia_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[Any] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    alpha: float = 0.05,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_market_residual_risk_premia_candidate_specs())
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=expected_candidate_count if expected_candidate_count is not None else len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        alpha=alpha,
    )
    result["stage"] = STAGE
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["market_residual_context"] = {
        "source_audit": ROUND107_109_SOURCE_AUDIT,
        "market_proxy": "same_date_equal_weight_cn_stock_return",
        "residualization": "rolling_beta_signal_date_only",
        "no_full_period_normalization": True,
        "no_topn_portfolio_grid": True,
        "final_holdout_touched": False,
    }
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS) + ["factor_model_construction"],
        "method": "Factor-model residualization plus Alphalens-style IC, quantile, turnover, and FDR prescreen.",
    }
    lead_count = int(result["summary"].get("research_lead_count", 0))
    result["summary"]["next_direction"] = NEXT_DEDUP_DIRECTION if lead_count else NEXT_ROTATE_DIRECTION
    result["summary"]["promotion_allowed_candidates"] = 0
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_REQUIRED_GATE,
        "next_allowed_action": (
            "market_exposure_and_correlation_dedup_if_research_leads_survive"
            if lead_count
            else "rotate_family_after_zero_market_residual_prescreen_leads"
        ),
        "reason": "Round111 is a statistical prescreen; portfolio promotion requires later exposure, cost, capacity, regime, and walk-forward gates.",
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_market_residual_risk_premia_prescreen_markdown(result)
    return result


def write_market_residual_risk_premia_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "market_residual_risk_premia_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "market_residual_risk_premia_prescreen.md").write_text(
        render_market_residual_risk_premia_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "market_residual_risk_premia_candidates.csv", _candidate_csv_rows(result), _candidate_columns())
    _write_csv(output_path / "market_residual_risk_premia_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "market_residual_risk_premia_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_market_residual_risk_premia_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("market_residual_context", {})
    lines = [
        "# Market Residual Risk Premia Prescreen",
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
        f"- Next direction: {summary.get('next_direction', '')}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        "",
        "## Market Residual Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND107_109_SOURCE_AUDIT)}",
        f"- Market proxy: {context.get('market_proxy', '')}",
        f"- Residualization: {context.get('residualization', '')}",
        f"- No full-period normalization: {context.get('no_full_period_normalization', False)}",
        f"- Top-N portfolio grid blocked: {context.get('no_topn_portfolio_grid', True)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC+ | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
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
            "## Promotion Policy",
            "",
            f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
            f"- Requires next gate: {result.get('promotion_policy', {}).get('requires_next_gate', NEXT_REQUIRED_GATE)}",
            f"- Reason: {result.get('promotion_policy', {}).get('reason', '')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _feature_frame(bars: pd.DataFrame, *, min_signal_date_amount: float) -> pd.DataFrame:
    bars = _normalise_bars(bars).sort_values(["asset_id", "date"]).reset_index(drop=True)
    proxy = build_equal_weight_market_proxy(bars, min_signal_date_amount=min_signal_date_amount)
    bars = bars.merge(proxy, on=["date", "market"], how="left", validate="many_to_one")
    pieces: list[pd.DataFrame] = []
    for _, group in bars.groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        returns = close.pct_change()
        market_returns = group["market_equal_weight_return"]
        adv20 = amount.rolling(20, min_periods=5).mean()
        beta_120 = _rolling_beta(returns, market_returns, window=120, min_periods=40)
        downside_beta_120 = _rolling_beta(
            returns.where(market_returns < 0),
            market_returns.where(market_returns < 0),
            window=120,
            min_periods=20,
        )
        residual = returns - beta_120 * market_returns
        residual_return_20 = residual.rolling(20, min_periods=10).sum()
        residual_abs_path_20 = residual.abs().rolling(20, min_periods=10).sum()
        hl_range_60 = ((high / low) - 1.0).rolling(60, min_periods=20).mean()
        frame = group[["date", "asset_id", "market", "amount", "market_equal_weight_return"]].copy()
        frame["return_1d"] = returns
        frame["adv20_amount"] = adv20
        frame["beta_120"] = beta_120
        frame["downside_beta_120"] = downside_beta_120
        frame["market_corr_60"] = returns.rolling(60, min_periods=20).corr(market_returns)
        frame["residual_return_5"] = residual.rolling(5, min_periods=3).sum()
        frame["residual_return_20"] = residual_return_20
        frame["residual_momentum_120_skip20"] = residual.shift(20).rolling(120, min_periods=40).sum()
        frame["residual_return_efficiency_20"] = residual_return_20 / residual_abs_path_20.where(
            residual_abs_path_20.abs() > 1e-12
        )
        frame["residual_vol_60"] = residual.rolling(60, min_periods=20).std(ddof=0)
        frame["downside_residual_vol_60"] = residual.clip(upper=0).rolling(60, min_periods=20).std(ddof=0)
        frame["co_crash_days_60"] = ((returns < 0) & (market_returns < 0)).astype(float).rolling(60, min_periods=20).sum()
        frame["residual_skew_60"] = residual.rolling(60, min_periods=20).skew()
        frame["beta_adjusted_hl_range_60"] = hl_range_60 / (1.0 + beta_120.abs())
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = np.log(features["adv20_amount"].where(features["adv20_amount"] > 0))
    return features.replace([np.inf, -np.inf], pd.NA)


def _rolling_beta(left: pd.Series, right: pd.Series, *, window: int, min_periods: int) -> pd.Series:
    covariance = left.rolling(window, min_periods=min_periods).cov(right)
    variance = right.rolling(window, min_periods=min_periods).var()
    return covariance / variance.where(variance.abs() > 1e-12)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_beta_120": frame["beta_120"],
        "z_downside_beta_120": frame["downside_beta_120"],
        "z_market_corr_60": frame["market_corr_60"],
        "z_residual_vol_60": frame["residual_vol_60"],
        "z_neg_residual_vol_60": -frame["residual_vol_60"],
        "z_downside_residual_vol_60": frame["downside_residual_vol_60"],
        "z_neg_residual_return_5": -frame["residual_return_5"],
        "z_abs_residual_return_20": frame["residual_return_20"].abs(),
        "z_residual_momentum_120_skip20": frame["residual_momentum_120_skip20"],
        "z_residual_return_efficiency_20": frame["residual_return_efficiency_20"],
        "z_co_crash_days_60": frame["co_crash_days_60"],
        "z_beta_adjusted_hl_range_60": frame["beta_adjusted_hl_range_60"],
        "z_residual_skew_60": frame["residual_skew_60"],
        "z_log_adv20": frame["log_adv20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.where(std.abs() > 1e-12)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "market_equal_weight_return",
            "beta_120",
            "downside_beta_120",
            "market_corr_60",
            "residual_vol_60",
        ]
    )


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for spec in result.get("candidate_specs", []):
        rows.append(
            {
                "factor_name": spec.get("factor_name", ""),
                "family": spec.get("family", ""),
                "formula_template": spec.get("formula_template", ""),
                "windows": ",".join(str(window) for window in spec.get("windows", []) or []),
                "required_fields": ",".join(spec.get("required_fields", []) or []),
                "public_reference_tags": ",".join(spec.get("public_reference_tags", []) or []),
                "promotion_allowed": spec.get("promotion_allowed", False),
            }
        )
    return rows


def _candidate_columns() -> list[str]:
    return [
        "factor_name",
        "family",
        "formula_template",
        "windows",
        "required_fields",
        "public_reference_tags",
        "promotion_allowed",
    ]


def _spec_payload(spec: Any) -> dict[str, Any]:
    payload = asdict(spec) if hasattr(spec, "__dataclass_fields__") else dict(spec)
    for key in ("windows", "required_fields", "public_reference_tags"):
        if key in payload:
            payload[key] = list(payload[key])
    return payload

