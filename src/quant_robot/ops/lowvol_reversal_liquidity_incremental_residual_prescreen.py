from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    SAFETY,
    default_capacity_safe_price_volume_candidate_specs,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    RESULT_COLUMNS,
    _data_window,
    _sanitize,
    _write_csv,
    compute_capacity_safe_price_volume_factors,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.lowvol_reversal_liquidity_incremental_residual_preregistration import (
    EXPOSURE_CONTROLS,
    REFERENCE_CLUSTER_MEMBERS,
    ROUND118_SOURCE_AUDIT,
    default_lowvol_reversal_liquidity_incremental_residual_specs,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import _correlation_row, _filter_dates, _sample_dates
from quant_robot.ops.market_residual_risk_premia_preregistration import (
    default_market_residual_risk_premia_candidate_specs,
)
from quant_robot.ops.public_alpha101_capacity_safe_preregistration import default_public_alpha101_candidate_specs
from quant_robot.ops.public_alpha101_capacity_safe_prescreen import (
    compute_public_alpha101_capacity_safe_factors,
    load_public_alpha101_bars,
)
from quant_robot.ops.public_alpha101_reference_exposure_dedup import _exposure_frame_from_bars
from quant_robot.research.labels import make_forward_returns


STAGE = "lowvol_reversal_liquidity_incremental_residual_prescreen"
NEXT_REVIEW_DIRECTION = "round121_round118_120_three_round_review_before_next_action"
POST_REVIEW_BRIDGE_DIRECTION = "round121_incremental_residual_dedup_walk_forward_bridge_after_review"
POST_REVIEW_ROTATE_DIRECTION = "round121_family_rotation_after_incremental_residual_prescreen_review"
NEXT_REQUIRED_GATE = "round121_three_round_review_and_incremental_residual_dedup_before_portfolio_grid"

REFERENCE_CORRELATION_COLUMNS = [
    "candidate_factor_name",
    "factor_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "redundancy_class",
    "blockers",
]
EXPOSURE_CORRELATION_COLUMNS = [
    "candidate_factor_name",
    "exposure_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "exposure_class",
    "blockers",
]

BASE_REFERENCE_NAMES = (
    "amount_stability_reversal_5_20",
    "range_contraction_lowvol_reversal_20",
    "pv_lowvol_reversal_blend_20",
    "bollinger_reversal_lowvol_liquid_20",
    "donchian_pullback_lowvol_liquid_20",
    "rsi_reversal_lowvol_liquid_14_20",
)
PUBLIC_Q_FACTOR_NAME = "qlib_alpha158_return_std_position_blend_20"


def build_lowvol_reversal_liquidity_incremental_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 10, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    sample_every_n_dates: int = 5,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_lowvol_reversal_liquidity_incremental_residual_specs())
    bars = load_public_alpha101_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_lowvol_reversal_liquidity_incremental_residual_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
        min_residual_cross_section=min_cross_section,
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
    reference_frame = _build_reference_frame(bars, min_signal_date_amount=min_signal_date_amount)
    reference_correlations = candidate_reference_correlations(
        factor_frame,
        reference_frame,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
    )
    exposure_correlations = candidate_exposure_correlations(
        factor_frame,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
    )
    residual_leads = _incremental_research_lead_names(
        result.get("results", []),
        reference_correlations=reference_correlations,
        exposure_correlations=exposure_correlations,
    )
    gate_blockers = _gate_blockers(result, reference_correlations, exposure_correlations, residual_leads)
    result["stage"] = STAGE
    result["summary"]["next_direction"] = NEXT_REVIEW_DIRECTION
    result["summary"]["promotion_allowed_candidates"] = 0
    result["summary"]["incremental_research_lead_count"] = len(residual_leads)
    result["summary"]["reference_highly_redundant_rows"] = int(
        sum(1 for row in reference_correlations if row["redundancy_class"] == "highly_redundant")
    )
    result["summary"]["exposure_high_rows"] = int(
        sum(1 for row in exposure_correlations if row["exposure_class"] == "high_exposure")
    )
    result["data_window"] = _data_window(bars, factor_frame, labels) | {
        "factor_rows": int(len(factor_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "label_rows": int(len(labels)),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["incremental_residual_context"] = {
        "source_audit": ROUND118_SOURCE_AUDIT,
        "source_preregistration": (
            "docs/research/cn_stock_lowvol_reversal_liquidity_incremental_residual_preregistration_round119_2026-06-22.md"
        ),
        "reference_cluster_members": list(REFERENCE_CLUSTER_MEMBERS),
        "exposure_controls": list(EXPOSURE_CONTROLS),
        "residualization": "per_signal_date_cross_sectional_ols_no_full_period_fit",
        "sample_every_n_dates_for_correlations": sample_every_n_dates,
        "no_portfolio_grid": True,
    }
    result["gate"] = {
        "blockers": gate_blockers,
        "required_before": [
            "round121_round118_120_three_round_review_before_next_action",
            "incremental_residual_reference_exposure_dedup_before_portfolio_grid",
            "long_cycle_walk_forward_cost_capacity_regime_gate_before_paper_ready",
        ],
        "drawdown_policy": "A higher drawdown tolerance does not waive incremental IC, redundancy, exposure, or cost gates.",
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_grid_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_REQUIRED_GATE,
        "reason": "Round120 is an incremental-residual prescreen only; it cannot promote factors to paper-ready use.",
    }
    result["recommended_post_review_direction"] = (
        POST_REVIEW_BRIDGE_DIRECTION if residual_leads and not gate_blockers else POST_REVIEW_ROTATE_DIRECTION
    )
    result["reference_correlations"] = reference_correlations
    result["exposure_correlations"] = exposure_correlations
    result["incremental_research_leads"] = residual_leads
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_lowvol_reversal_liquidity_incremental_residual_prescreen_markdown(result)
    return result


def compute_lowvol_reversal_liquidity_incremental_residual_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = 10_000_000,
    min_residual_cross_section: int = 30,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_lowvol_reversal_liquidity_incremental_residual_specs())
    allowed_names = {spec.factor_name for spec in specs}
    wide = _wide_source_frame(bars, min_signal_date_amount=min_signal_date_amount)
    if wide.empty:
        return _empty_factor_frame()
    recipes = _residual_recipes()
    frames: list[pd.DataFrame] = []
    for factor_name in allowed_names:
        recipe = recipes.get(factor_name)
        if recipe is None:
            continue
        target = _target_series(wide, recipe["target"])
        residual_frame = _residualize_by_date(
            wide,
            target=target,
            controls=recipe["controls"],
            min_cross_section=min_residual_cross_section,
        )
        if residual_frame.empty:
            continue
        residual_frame["factor_name"] = factor_name
        frames.append(residual_frame)
    if not frames:
        return _empty_factor_frame()
    return pd.concat(frames, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def candidate_reference_correlations(
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
) -> list[dict[str, Any]]:
    if factor_frame.empty or reference_frame.empty:
        return []
    candidates = _sample_dates(_normalise_factor_frame(factor_frame), sample_every_n_dates=sample_every_n_dates)
    references = _filter_dates(_normalise_factor_frame(reference_frame), candidates["date"].unique())
    rows: list[dict[str, Any]] = []
    for candidate_name, candidate in candidates.groupby("factor_name", sort=True):
        lead = candidate[["date", "asset_id", "market", "factor_value"]].rename(columns={"factor_value": "lead_value"})
        for reference_name, reference in references.groupby("factor_name", sort=True):
            merged = reference[["date", "asset_id", "market", "factor_value"]].merge(
                lead,
                on=["date", "asset_id", "market"],
                how="inner",
            )
            row = _correlation_row(
                name_key="factor_name",
                name=str(reference_name),
                group=merged,
                value_column="factor_value",
                lead_column="lead_value",
                min_cross_section=min_cross_section,
                high_corr_threshold=0.85,
                high_mean_abs_corr_threshold=0.70,
                moderate_corr_threshold=0.70,
                moderate_mean_abs_corr_threshold=0.50,
                high_class="highly_redundant",
                moderate_class="moderately_redundant",
                unique_class="unique",
                high_blocker="high_reference_correlation_with_incremental_residual",
                moderate_blocker="moderate_reference_correlation_with_incremental_residual",
                insufficient_blocker="insufficient_reference_overlap_with_incremental_residual",
            )
            row["candidate_factor_name"] = str(candidate_name)
            rows.append(row)
    return sorted(rows, key=lambda row: (row["candidate_factor_name"], -row["max_abs_correlation"], row["factor_name"]))


def candidate_exposure_correlations(
    factor_frame: pd.DataFrame,
    *,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
) -> list[dict[str, Any]]:
    if factor_frame.empty:
        return []
    candidates = _sample_dates(_normalise_factor_frame(factor_frame), sample_every_n_dates=sample_every_n_dates)
    if "adv20_amount" in candidates:
        candidates["log_adv20_amount"] = np.log(
            pd.to_numeric(candidates["adv20_amount"], errors="coerce").where(candidates["adv20_amount"] > 0)
        )
    rows: list[dict[str, Any]] = []
    for candidate_name, candidate in candidates.groupby("factor_name", sort=True):
        for exposure_name in EXPOSURE_CONTROLS:
            if exposure_name not in candidate:
                continue
            group = candidate[["date", "asset_id", "market", "factor_value", exposure_name]].rename(
                columns={exposure_name: "exposure_value"}
            )
            row = _correlation_row(
                name_key="exposure_name",
                name=exposure_name,
                group=group,
                value_column="exposure_value",
                lead_column="factor_value",
                min_cross_section=min_cross_section,
                high_corr_threshold=0.85,
                high_mean_abs_corr_threshold=0.60,
                moderate_corr_threshold=0.70,
                moderate_mean_abs_corr_threshold=0.40,
                high_class="high_exposure",
                moderate_class="moderate_exposure",
                unique_class="low_exposure",
                high_blocker="high_incremental_residual_exposure_correlation",
                moderate_blocker="moderate_incremental_residual_exposure_correlation",
                insufficient_blocker="insufficient_exposure_overlap_with_incremental_residual",
            )
            row["candidate_factor_name"] = str(candidate_name)
            rows.append(row)
    return sorted(rows, key=lambda row: (row["candidate_factor_name"], -row["max_abs_correlation"], row["exposure_name"]))


def write_lowvol_reversal_liquidity_incremental_residual_prescreen(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "lowvol_reversal_liquidity_incremental_residual_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lowvol_reversal_liquidity_incremental_residual_prescreen.md").write_text(
        render_lowvol_reversal_liquidity_incremental_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lowvol_reversal_liquidity_incremental_residual_prescreen_results.csv",
        result.get("results", []),
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "lowvol_reversal_liquidity_incremental_residual_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "lowvol_reversal_liquidity_incremental_residual_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "lowvol_reversal_liquidity_incremental_residual_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )


def render_lowvol_reversal_liquidity_incremental_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("incremental_residual_context", {})
    lines = [
        "# Low-Vol Reversal Liquidity Incremental Residual Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Incremental research leads: {summary.get('incremental_research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Highly redundant correlation rows: {summary.get('reference_highly_redundant_rows', 0)}",
        f"- High exposure rows: {summary.get('exposure_high_rows', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{summary.get('next_direction', NEXT_REVIEW_DIRECTION)}`",
        f"- Recommended post-review direction: `{result.get('recommended_post_review_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        "",
        "## Incremental Residual Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND118_SOURCE_AUDIT)}",
        f"- Source preregistration: {context.get('source_preregistration', '')}",
        "- Reference cluster members: " + ", ".join(context.get("reference_cluster_members", []) or []),
        "- Exposure controls: " + ", ".join(context.get("exposure_controls", []) or []),
        f"- Residualization: {context.get('residualization', '')}",
        f"- Portfolio grid blocked: {context.get('no_portfolio_grid', True)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC+ | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:30]:
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
            "## Gate",
            "",
            f"- Blockers: {', '.join(result.get('gate', {}).get('blockers', [])) or 'none'}",
            f"- Drawdown policy: {result.get('gate', {}).get('drawdown_policy', '')}",
            f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
            f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
            f"- Safety: {result.get('safety', SAFETY)}",
        ]
    )
    return "\n".join(lines) + "\n"


def _wide_source_frame(bars: pd.DataFrame, *, min_signal_date_amount: float) -> pd.DataFrame:
    reference_frame = _build_reference_frame(bars, min_signal_date_amount=min_signal_date_amount)
    if reference_frame.empty:
        return pd.DataFrame()
    wide = _wide_factor_values(reference_frame)
    public_specs = [spec for spec in default_public_alpha101_candidate_specs() if spec.factor_name == PUBLIC_Q_FACTOR_NAME]
    q_frame = compute_public_alpha101_capacity_safe_factors(
        bars,
        candidate_specs=public_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    if not q_frame.empty:
        q_values = q_frame[["date", "asset_id", "market", "factor_value"]].rename(
            columns={"factor_value": PUBLIC_Q_FACTOR_NAME}
        )
        wide = wide.merge(q_values, on=["date", "asset_id", "market"], how="left", validate="one_to_one")
    exposure_frame = _exposure_frame_from_bars(bars, min_signal_date_amount=min_signal_date_amount)
    exposure_columns = [
        "date",
        "asset_id",
        "market",
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
    ]
    if not exposure_frame.empty:
        wide = wide.merge(
            exposure_frame[[column for column in exposure_columns if column in exposure_frame.columns]],
            on=["date", "asset_id", "market"],
            how="left",
            validate="one_to_one",
        )
    wide["log_adv20_amount"] = np.log(pd.to_numeric(wide["adv20_amount"], errors="coerce").where(wide["adv20_amount"] > 0))
    return wide.replace([np.inf, -np.inf], np.nan)


def _build_reference_frame(bars: pd.DataFrame, *, min_signal_date_amount: float) -> pd.DataFrame:
    allowed = set(BASE_REFERENCE_NAMES)
    specs = [spec for spec in default_capacity_safe_price_volume_candidate_specs() if spec.factor_name in allowed]
    return compute_capacity_safe_price_volume_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )


def _wide_factor_values(frame: pd.DataFrame) -> pd.DataFrame:
    normalised = _normalise_factor_frame(frame)
    index_columns = ["date", "asset_id", "market"]
    value_wide = (
        normalised.pivot_table(
            index=index_columns,
            columns="factor_name",
            values="factor_value",
            aggfunc="last",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    meta = (
        normalised.sort_values(index_columns)
        .groupby(index_columns, as_index=False)[["amount", "adv20_amount"]]
        .last()
    )
    return meta.merge(value_wide, on=index_columns, how="inner", validate="one_to_one")


def _residual_recipes() -> dict[str, dict[str, Any]]:
    cluster = list(REFERENCE_CLUSTER_MEMBERS)
    return {
        "qlib_blend_residual_vs_lowvol_cluster_5": {
            "target": PUBLIC_Q_FACTOR_NAME,
            "controls": cluster,
        },
        "qlib_blend_cluster_exposure_neutral_residual_5": {
            "target": PUBLIC_Q_FACTOR_NAME,
            "controls": cluster + list(EXPOSURE_CONTROLS),
        },
        "amount_stability_incremental_residual_5_20": {
            "target": "amount_stability_reversal_5_20",
            "controls": [
                "range_contraction_lowvol_reversal_20",
                "pv_lowvol_reversal_blend_20",
                "bollinger_reversal_lowvol_liquid_20",
                "log_adv20_amount",
            ],
        },
        "range_contraction_incremental_residual_20": {
            "target": "range_contraction_lowvol_reversal_20",
            "controls": [
                "amount_stability_reversal_5_20",
                "pv_lowvol_reversal_blend_20",
                "bollinger_reversal_lowvol_liquid_20",
                "beta_120",
            ],
        },
        "bollinger_reversal_incremental_residual_20": {
            "target": "bollinger_reversal_lowvol_liquid_20",
            "controls": [
                "amount_stability_reversal_5_20",
                "range_contraction_lowvol_reversal_20",
                "pv_lowvol_reversal_blend_20",
                "market_corr_60",
            ],
        },
        "donchian_pullback_incremental_residual_20": {
            "target": "donchian_pullback_lowvol_liquid_20",
            "controls": cluster + ["log_adv20_amount"],
        },
        "rsi_reversal_incremental_residual_14_20": {
            "target": "rsi_reversal_lowvol_liquid_14_20",
            "controls": cluster + ["downside_beta_120"],
        },
        "pv_lowvol_cluster_residual_spread_20": {
            "target": ("spread", "pv_lowvol_reversal_blend_20", "bollinger_reversal_lowvol_liquid_20"),
            "controls": [
                "amount_stability_reversal_5_20",
                "range_contraction_lowvol_reversal_20",
                "log_adv20_amount",
                "market_corr_60",
            ],
        },
    }


def _target_series(frame: pd.DataFrame, target: str | tuple[str, str, str]) -> pd.Series:
    if isinstance(target, tuple):
        _, left, right = target
        return pd.to_numeric(frame[left], errors="coerce") - pd.to_numeric(frame[right], errors="coerce")
    return pd.to_numeric(frame[target], errors="coerce")


def _residualize_by_date(
    frame: pd.DataFrame,
    *,
    target: pd.Series,
    controls: Sequence[str],
    min_cross_section: int,
) -> pd.DataFrame:
    missing = [column for column in controls if column not in frame.columns]
    if missing:
        return _empty_factor_frame()
    working = frame.copy()
    working["_target"] = target
    rows: list[pd.DataFrame] = []
    output_columns = [
        "date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
    ]
    for _, group in working.groupby("date", sort=True):
        group = group.dropna(subset=["_target", *controls])
        if len(group) < max(min_cross_section, len(controls) + 3):
            continue
        y = group["_target"].astype(float).to_numpy()
        x = group[list(controls)].astype(float).to_numpy()
        x = np.column_stack([np.ones(len(x)), x])
        try:
            beta, *_ = np.linalg.lstsq(x, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        residual = y - x @ beta
        piece = group[[column for column in output_columns if column in group.columns]].copy()
        piece["factor_value"] = _standardize_residual(residual)
        rows.append(piece)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True)


def _standardize_residual(residual: np.ndarray) -> np.ndarray:
    residual = residual.astype(float)
    std = float(np.nanstd(residual))
    if not np.isfinite(std) or std <= 1e-12:
        return residual
    return (residual - float(np.nanmean(residual))) / std


def _incremental_research_lead_names(
    results: Sequence[dict[str, Any]],
    *,
    reference_correlations: Sequence[dict[str, Any]],
    exposure_correlations: Sequence[dict[str, Any]],
) -> list[str]:
    research_leads = {row["factor_name"] for row in results if row.get("research_lead", False)}
    blocked = {
        row["candidate_factor_name"]
        for row in reference_correlations
        if row.get("redundancy_class") == "highly_redundant"
    }
    blocked.update(
        row["candidate_factor_name"]
        for row in exposure_correlations
        if row.get("exposure_class") == "high_exposure"
    )
    return sorted(research_leads - blocked)


def _gate_blockers(
    result: dict[str, Any],
    reference_correlations: Sequence[dict[str, Any]],
    exposure_correlations: Sequence[dict[str, Any]],
    residual_leads: Sequence[str],
) -> list[str]:
    blockers = []
    if int(result.get("summary", {}).get("factor_rows", 0)) == 0:
        blockers.append("incremental_residual_factor_frame_empty")
    if not residual_leads:
        blockers.append("no_incremental_residual_research_lead_after_redundancy_exposure_gate")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("some_incremental_residuals_still_highly_redundant_with_reference_cluster")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("some_incremental_residuals_still_highly_exposed_to_market_or_liquidity_proxy")
    blockers.append("promotion_requires_round121_review_walk_forward_cost_capacity_regime_gates")
    return blockers


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_factor_frame()
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in [
        "amount",
        "adv20_amount",
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
        "log_adv20_amount",
    ]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    return normalised.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


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
            "beta_120",
            "downside_beta_120",
            "market_corr_60",
            "residual_vol_60",
        ]
    )


def _spec_payload(spec: Any) -> dict[str, Any]:
    payload = asdict(spec) if hasattr(spec, "__dataclass_fields__") else dict(spec)
    for key in ("windows", "required_fields", "public_reference_tags"):
        if key in payload:
            payload[key] = list(payload[key])
    return payload
