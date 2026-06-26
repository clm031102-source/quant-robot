from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
    CapacitySafePriceVolumeCandidateSpec,
    build_capacity_safe_price_volume_preregistration,
)


STAGE = "lowvol_reversal_liquidity_incremental_residual_preregistration"
ROUND118_SOURCE_AUDIT = "docs/research/cn_stock_soft_capacity_low_turnover_early_stop_round118_2026-06-22.md"
ROUND120_NEXT_DIRECTION = "round120_lowvol_reversal_liquidity_incremental_residual_prescreen"
SOURCE_EVIDENCE_STATUS = "incremental_residual_preregistered_not_empirical_alpha"
REFERENCE_CLUSTER_MEMBERS = (
    "amount_stability_reversal_5_20",
    "range_contraction_lowvol_reversal_20",
    "pv_lowvol_reversal_blend_20",
    "bollinger_reversal_lowvol_liquid_20",
)
EXPOSURE_CONTROLS = (
    "log_adv20_amount",
    "beta_120",
    "downside_beta_120",
    "market_corr_60",
)


def default_lowvol_reversal_liquidity_incremental_residual_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        _spec(
            factor_name="qlib_blend_residual_vs_lowvol_cluster_5",
            family="qlib_incremental_residual",
            formula_template=(
                "cs_resid(qlib_alpha158_return_std_position_blend_20 ~ "
                "amount_stability_reversal_5_20 + range_contraction_lowvol_reversal_20 + "
                "pv_lowvol_reversal_blend_20 + bollinger_reversal_lowvol_liquid_20)"
            ),
            windows=(5, 20),
            required_fields=("adj_close", "high", "low", "amount", "reference_factor_matrix"),
            rationale=(
                "Round115 found this Qlib-style blend useful, but Round116 showed it was redundant with the "
                "low-vol/reversal/liquidity cluster. This candidate only keeps the cross-sectional residual."
            ),
        ),
        _spec(
            factor_name="qlib_blend_cluster_exposure_neutral_residual_5",
            family="qlib_incremental_exposure_neutral",
            formula_template=(
                "cs_resid(qlib_alpha158_return_std_position_blend_20 ~ "
                "amount_stability_reversal_5_20 + range_contraction_lowvol_reversal_20 + "
                "pv_lowvol_reversal_blend_20 + bollinger_reversal_lowvol_liquid_20 + "
                "log_adv20_amount + beta_120 + downside_beta_120 + market_corr_60)"
            ),
            windows=(5, 20, 120),
            required_fields=("adj_close", "high", "low", "amount", "reference_factor_matrix"),
            rationale=(
                "If the Qlib blend still has edge after removing cluster, liquidity, beta, downside beta, and "
                "market-correlation exposures, it is a cleaner incremental hypothesis."
            ),
        ),
        _spec(
            factor_name="amount_stability_incremental_residual_5_20",
            family="liquidity_capacity_incremental",
            formula_template=(
                "cs_resid(amount_stability_reversal_5_20 ~ range_contraction_lowvol_reversal_20 + "
                "pv_lowvol_reversal_blend_20 + bollinger_reversal_lowvol_liquid_20 + log_adv20_amount)"
            ),
            windows=(5, 20),
            required_fields=("adj_close", "amount", "reference_factor_matrix"),
            rationale=(
                "Tests whether amount stability contains information beyond the broader low-vol/reversal "
                "cluster and the direct liquidity proxy."
            ),
        ),
        _spec(
            factor_name="range_contraction_incremental_residual_20",
            family="range_incremental_residual",
            formula_template=(
                "cs_resid(range_contraction_lowvol_reversal_20 ~ amount_stability_reversal_5_20 + "
                "pv_lowvol_reversal_blend_20 + bollinger_reversal_lowvol_liquid_20 + beta_120)"
            ),
            windows=(20, 120),
            required_fields=("adj_close", "high", "low", "amount", "reference_factor_matrix"),
            rationale=(
                "Range contraction was repeatedly correlated with other reversal/low-vol factors. This "
                "registers only the part orthogonal to the cluster and market beta."
            ),
        ),
        _spec(
            factor_name="bollinger_reversal_incremental_residual_20",
            family="public_technical_incremental_residual",
            formula_template=(
                "cs_resid(bollinger_reversal_lowvol_liquid_20 ~ amount_stability_reversal_5_20 + "
                "range_contraction_lowvol_reversal_20 + pv_lowvol_reversal_blend_20 + market_corr_60)"
            ),
            windows=(20, 60),
            required_fields=("adj_close", "amount", "reference_factor_matrix"),
            rationale=(
                "Keeps the Bollinger public-indicator intuition only if it adds information beyond the "
                "known cluster and market-correlation exposure."
            ),
        ),
        _spec(
            factor_name="donchian_pullback_incremental_residual_20",
            family="public_channel_incremental_residual",
            formula_template=(
                "orthogonalize(donchian_pullback_lowvol_liquid_20, "
                "[amount_stability_reversal_5_20, range_contraction_lowvol_reversal_20, "
                "pv_lowvol_reversal_blend_20, bollinger_reversal_lowvol_liquid_20, log_adv20_amount])"
            ),
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount", "reference_factor_matrix"),
            rationale=(
                "Donchian pullback had overlap with the blocked cluster; this candidate tests whether the "
                "channel component adds anything after orthogonalization."
            ),
        ),
        _spec(
            factor_name="rsi_reversal_incremental_residual_14_20",
            family="public_oscillator_incremental_residual",
            formula_template=(
                "orthogonalize(rsi_reversal_lowvol_liquid_14_20, "
                "[amount_stability_reversal_5_20, range_contraction_lowvol_reversal_20, "
                "pv_lowvol_reversal_blend_20, bollinger_reversal_lowvol_liquid_20, downside_beta_120])"
            ),
            windows=(14, 20, 120),
            required_fields=("adj_close", "amount", "reference_factor_matrix"),
            rationale=(
                "RSI reversal is public and plausible, but it is only worth measuring as residual information "
                "after the stronger reversal/low-vol cluster and downside beta exposure."
            ),
        ),
        _spec(
            factor_name="pv_lowvol_cluster_residual_spread_20",
            family="price_volume_incremental_residual",
            formula_template=(
                "cs_resid(pv_lowvol_reversal_blend_20 - bollinger_reversal_lowvol_liquid_20 ~ "
                "amount_stability_reversal_5_20 + range_contraction_lowvol_reversal_20 + "
                "log_adv20_amount + market_corr_60)"
            ),
            windows=(20, 60),
            required_fields=("adj_close", "high", "low", "amount", "reference_factor_matrix"),
            rationale=(
                "Tests whether the disagreement between price-volume reversal and Bollinger reversal has "
                "incremental value after removing common cluster and liquidity/market-correlation exposure."
            ),
        ),
    ]


def build_lowvol_reversal_liquidity_incremental_residual_preregistration(
    *,
    min_candidates: int = 8,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_lowvol_reversal_liquidity_incremental_residual_specs())
    result = build_capacity_safe_price_volume_preregistration(
        min_candidates=min_candidates,
        candidate_specs=specs,
    )
    result["stage"] = STAGE
    result["summary"]["next_required_gate"] = ROUND120_NEXT_DIRECTION
    result["summary"]["next_direction"] = ROUND120_NEXT_DIRECTION
    for candidate in result.get("candidates", []) or []:
        candidate["next_required_gate"] = ROUND120_NEXT_DIRECTION
        candidate["source_evidence_status"] = SOURCE_EVIDENCE_STATUS
    result["incremental_residual_context"] = {
        "source_audit": ROUND118_SOURCE_AUDIT,
        "reference_cluster_members": list(REFERENCE_CLUSTER_MEMBERS),
        "exposure_controls": list(EXPOSURE_CONTROLS),
        "previous_blockers": [
            "round116_lead_highly_redundant_with_reference_factor",
            "round116_lead_high_exposure_to_market_or_liquidity_proxy",
            "round118_soft_capacity_low_turnover_zero_positive_relative_oos_rows",
        ],
        "method": (
            "Pre-register residual and orthogonalized variants before measurement. Round120 must test "
            "incremental IC, quantile spread, turnover, capacity, and exposure diagnostics against the "
            "reference cluster; no portfolio grid is allowed from preregistration alone."
        ),
    }
    result["evaluation_gate"]["next_required_gate"] = ROUND120_NEXT_DIRECTION
    result["evaluation_gate"]["required_metrics"] = list(result["evaluation_gate"]["required_metrics"]) + [
        "incremental_ic_over_reference_cluster",
        "residual_factor_reference_correlation",
        "post_neutralization_exposure_correlation",
    ]
    result["promotion_policy"]["next_allowed_action"] = (
        "Run Round120 incremental-residual IC/quantile/turnover/exposure prescreen; portfolio grids remain blocked."
    )
    result["markdown"] = render_lowvol_reversal_liquidity_incremental_residual_preregistration_markdown(result)
    return result


def write_lowvol_reversal_liquidity_incremental_residual_preregistration(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "lowvol_reversal_liquidity_incremental_residual_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lowvol_reversal_liquidity_incremental_residual_preregistration.md").write_text(
        render_lowvol_reversal_liquidity_incremental_residual_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lowvol_reversal_liquidity_incremental_residual_candidates.csv",
        _candidate_csv_rows(result),
    )


def render_lowvol_reversal_liquidity_incremental_residual_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("incremental_residual_context", {})
    lines = [
        "# Low-Vol Reversal Liquidity Incremental Residual Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {context.get('source_audit', ROUND118_SOURCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', ROUND120_NEXT_DIRECTION)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Incremental Residual Context",
        "",
        "- Reference cluster members: " + ", ".join(context.get("reference_cluster_members", []) or []),
        "- Exposure controls: " + ", ".join(context.get("exposure_controls", []) or []),
        "- Previous blockers: " + ", ".join(context.get("previous_blockers", []) or []),
        f"- Method: {context.get('method', '')}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Direction | Windows | Required fields |",
        "|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {name} | {family} | {direction} | {windows} | {fields} |".format(
                name=candidate["factor_name"],
                family=candidate["family"],
                direction=candidate["direction"],
                windows=", ".join(str(window) for window in candidate.get("windows", []) or []),
                fields=", ".join(candidate.get("required_fields", []) or []),
            )
        )
    return "\n".join(lines) + "\n"


def _spec(
    *,
    factor_name: str,
    family: str,
    formula_template: str,
    windows: tuple[int, ...],
    required_fields: tuple[str, ...],
    rationale: str,
) -> CapacitySafePriceVolumeCandidateSpec:
    return CapacitySafePriceVolumeCandidateSpec(
        factor_name=factor_name,
        family=family,
        formula_template=formula_template,
        direction="higher_is_better",
        windows=windows,
        required_fields=required_fields,
        economic_rationale=rationale,
        public_reference_tags=("qlib", "alphalens", "worldquant_101_alphas"),
        source_evidence_status=SOURCE_EVIDENCE_STATUS,
    )


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "family": candidate["family"],
                "windows": ",".join(str(window) for window in candidate.get("windows", []) or []),
                "required_fields": ",".join(candidate.get("required_fields", []) or []),
                "source_evidence_status": candidate["source_evidence_status"],
                "next_required_gate": candidate["next_required_gate"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
