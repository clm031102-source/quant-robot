from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.public_reference_multi_family_preregistration import DEFAULT_CAPACITY_FILTERS


STAGE = "price_volume_shock_reversal_preregistration"
SOURCE_AUDIT = "docs/research/cn_stock_round154_156_three_round_review_2026-06-23.md"
NEGATIVE_EVIDENCE_AUDIT = "docs/research/cn_stock_public_technical_failure_reversal_neutral_dedup_round156_2026-06-23.md"
NEXT_REQUIRED_GATE = "round158_price_volume_shock_reversal_neutral_prescreen"
SOURCE_EVIDENCE_STATUS = "public_non_rsrs_price_volume_shock_hypothesis_after_round154_156_rotation"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
PUBLIC_REFERENCE_PROJECTS = (
    "amihud_illiquidity",
    "volume_climax",
    "close_location_value",
    "vwap_proxy",
    "gap_reversal",
    "range_expansion",
    "alphalens",
    "vectorbt",
)


@dataclass(frozen=True)
class PriceVolumeShockReversalCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_price_volume_shock_reversal_specs() -> list[PriceVolumeShockReversalCandidateSpec]:
    return [
        PriceVolumeShockReversalCandidateSpec(
            factor_name="amihud_shock_reversal_liquid_20_60",
            family="liquidity_stress_reversal",
            formula_template="0.45*cs_z(amihud_shock_20_60)+0.30*cs_z(-return_5)+0.25*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 20, 60),
            required_fields=("adj_close", "amount", "vol"),
            economic_rationale="Tests whether short-horizon liquidity stress plus price damage mean supply exhaustion, while keeping liquid names positive instead of buying untradeable tails.",
            public_reference_tags=("amihud_illiquidity", "liquidity_reversal", "alphalens"),
            expected_failure_modes=("illiquidity_tail", "cost_capacity_drag", "bear_regime_continuation"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="volume_climax_reversal_close_location_20",
            family="volume_climax_exhaustion",
            formula_template="0.40*cs_z(volume_ratio_5_20)+0.35*cs_z(1-close_location_20)+0.25*cs_z(-return_5)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low", "amount", "vol"),
            economic_rationale="Public volume-climax ideas expect heavy turnover with weak close location to reflect panic or forced selling rather than continuation.",
            public_reference_tags=("volume_climax", "close_location_value", "alphalens"),
            expected_failure_modes=("one_day_event_contamination", "limit_down_tradeability", "short_reversal_decay"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="range_expansion_exhaustion_reversal_20",
            family="range_expansion_exhaustion",
            formula_template="0.45*cs_z(true_range_ratio_5_20)+0.30*cs_z(-return_5)+0.25*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Range expansion after price damage is treated as capitulation only if the name remains tradable; this avoids repeating low-turnover capacity failures.",
            public_reference_tags=("range_expansion", "atr_exhaustion", "vectorbt"),
            expected_failure_modes=("trend_crash_continuation", "range_data_quality", "capacity_tail"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="downside_volume_absorption_reversal_10_60",
            family="downside_volume_absorption",
            formula_template="0.40*cs_z(down_day_volume_share_10)+0.30*cs_z(-return_10)+0.20*cs_z(-realized_vol_20)+0.10*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(10, 20, 60),
            required_fields=("adj_close", "amount", "vol"),
            economic_rationale="High volume concentrated on down days may indicate supply absorption, but only after volatility control and liquidity checks.",
            public_reference_tags=("volume_absorption", "downside_volume", "alphalens"),
            expected_failure_modes=("value_trap_after_bad_news", "event_contamination", "weak_industry_neutral_ic"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="gap_range_failure_reversal_5_20",
            family="gap_range_failure_reversal",
            formula_template="0.35*cs_z(abs(open_gap_1))+0.35*cs_z(intraday_failure_reversal_5)+0.30*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(1, 5, 20),
            required_fields=("open", "adj_close", "high", "low", "amount"),
            economic_rationale="Reframes gap signals as failed continuation plus range context, not the pure overnight-gap line that previously produced zero usable leads.",
            public_reference_tags=("gap_reversal", "range_failure", "vectorbt"),
            expected_failure_modes=("same_day_open_close_alignment", "limit_price_nontradeable", "pure_gap_redundancy"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="vwap_proxy_reclaim_reversal_20",
            family="vwap_proxy_reclaim",
            formula_template="0.35*cs_z(close_over_vwap_proxy_5)+0.30*cs_z(-return_20)+0.20*cs_z(volume_ratio_5_20)+0.15*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount", "vol"),
            economic_rationale="Uses daily amount/volume as a coarse VWAP proxy to test reclaim after selling pressure; the next screen must audit unit consistency before promotion.",
            public_reference_tags=("vwap_proxy", "volume_reclaim", "alphalens"),
            expected_failure_modes=("amount_volume_unit_mismatch", "intraday_proxy_noise", "weak_portfolio_translation"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="low_liquidity_stress_normalization_20_60",
            family="liquidity_stress_reversal",
            formula_template="0.45*cs_z(amihud_shock_20_60)+0.35*cs_z(-liquidity_stress_persistence_20)+0.20*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount", "vol"),
            economic_rationale="Separates temporary stress from persistent illiquidity so the family does not accidentally become another capacity-blind microcap bet.",
            public_reference_tags=("amihud_illiquidity", "liquidity_normalization", "alphalens"),
            expected_failure_modes=("persistent_illiquidity_misclassified", "style_exposure", "cost_capacity_drag"),
        ),
        PriceVolumeShockReversalCandidateSpec(
            factor_name="volatility_compression_after_shock_reversal_20_60",
            family="post_shock_volatility_compression",
            formula_template="0.35*cs_z(shock_return_abs_5_20)+0.35*cs_z(-realized_vol_ratio_10_60)+0.30*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 10, 20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Tests whether a shock followed by volatility compression indicates stabilization; dedup must compare it against old low-vol reversal clusters.",
            public_reference_tags=("volatility_compression", "range_expansion", "vectorbt"),
            expected_failure_modes=("lowvol_reversal_redundancy", "late_signal_decay", "regime_dependency"),
        ),
    ]


def build_price_volume_shock_reversal_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 4,
    candidate_specs: Iterable[PriceVolumeShockReversalCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_price_volume_shock_reversal_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    rsrs_count = sum(1 for candidate in candidates if _candidate_mentions(candidate, "rsrs"))
    blockers = _blockers(candidates, min_candidates=min_candidates, min_families=min_families)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "min_candidates": int(min_candidates),
            "family_count": len({candidate["family"] for candidate in candidates}),
            "min_families": int(min_families),
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "rsrs_candidate_count": rsrs_count,
            "portfolio_backtest_allowed_candidates": sum(1 for candidate in candidates if candidate["portfolio_backtest_allowed"]),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "rotation_context": {
            "source_audit": SOURCE_AUDIT,
            "negative_evidence_audit": NEGATIVE_EVIDENCE_AUDIT,
            "source_round": "round154_156_public_technical_failure_reversal_neutral_dedup",
            "rotation_reason": "Round156 left no portfolio preflight candidates and showed high RSRS reference redundancy; Round157 rotates to a different public price-volume shock mechanism.",
            "hibernated_families": [
                "public_rsrs_inverse_failure_reversal",
                "public_technical_failure_reversal_rsrs_cluster",
                "moneyflow_only_selection",
            ],
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": "Use public technical indicators only as hypothesis sources. Every candidate is pre-registered, non-RSRS, and must pass neutral residual IC before any portfolio grid.",
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "liquidity_kept_positive": True,
            "reason": "Shock-reversal ideas often drift into illiquid tails, so liquidity remains a positive component and capacity gates are mandatory later.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "ic_positive_rate",
                "industry_neutral_ic",
                "size_liquidity_vol_residual_ic",
                "quantile_spread",
                "quantile_monotonicity",
                "factor_turnover",
                "reference_correlation_dedup",
                "fdr_multiple_testing",
                "cost_capacity_walk_forward_later_gate",
            ],
            "portfolio_backtest_allowed_after": "neutral_prescreen_and_reference_dedup_only",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_neutral_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_reference_dedup": True,
            "requires_event_contamination_audit": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_price_volume_shock_reversal_preregistration_markdown(result)
    return result


def write_price_volume_shock_reversal_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "price_volume_shock_reversal_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "price_volume_shock_reversal_preregistration.md").write_text(
        render_price_volume_shock_reversal_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "price_volume_shock_reversal_candidates.csv", _candidate_csv_rows(result))


def render_price_volume_shock_reversal_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("rotation_context", {})
    lines = [
        "# Price-Volume Shock Reversal Preregistration Round157",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- RSRS candidates: {summary.get('rsrs_candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', SOURCE_AUDIT)}",
        f"- Negative evidence audit: {rotation.get('negative_evidence_audit', NEGATIVE_EVIDENCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio before neutral prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_neutral_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Windows | Public refs | Failure modes |",
        "|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {factor} | {family} | {windows} | {refs} | {failure_modes} |".format(
                factor=candidate["factor_name"],
                family=candidate["family"],
                windows="/".join(str(item) for item in candidate["windows"]),
                refs=", ".join(candidate["public_reference_tags"]),
                failure_modes=", ".join(candidate["expected_failure_modes"]),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is preregistration only; it creates no IC, return, Sharpe, win-rate, or promotion claim.",
            "- The family is intentionally non-RSRS after Round156 redundancy failure.",
            "- Round158 must run long-cycle industry/style neutral prescreen before any TopN or walk-forward portfolio grid.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: PriceVolumeShockReversalCandidateSpec) -> dict[str, Any]:
    payload = asdict(spec)
    for key in ["windows", "required_fields", "public_reference_tags", "expected_failure_modes"]:
        payload[key] = list(payload[key])
    payload.update(
        {
            "capacity_filters": dict(DEFAULT_CAPACITY_FILTERS),
            "market": "CN",
            "asset_type": "stock",
            "round": "round157",
            "next_required_gate": NEXT_REQUIRED_GATE,
            "neutral_prescreen_required_before_portfolio_grid": True,
        }
    )
    return payload


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if any(candidate["portfolio_backtest_allowed"] for candidate in candidates):
        blockers.append("portfolio_backtest_permission_not_allowed_at_preregistration")
    if any(candidate["promotion_allowed"] for candidate in candidates):
        blockers.append("promotion_permission_not_allowed_at_preregistration")
    if any(_candidate_mentions(candidate, "rsrs") for candidate in candidates):
        blockers.append("rsrs_family_reentry_blocked")
    return blockers


def _candidate_mentions(candidate: dict[str, Any], needle: str) -> bool:
    searchable = " ".join(
        [
            str(candidate.get("factor_name", "")),
            str(candidate.get("family", "")),
            str(candidate.get("formula_template", "")),
            " ".join(str(item) for item in candidate.get("public_reference_tags", []) or []),
        ]
    ).lower()
    return needle.lower() in searchable


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": candidate.get("factor_name"),
            "family": candidate.get("family"),
            "windows": "|".join(str(item) for item in candidate.get("windows", [])),
            "required_fields": "|".join(candidate.get("required_fields", [])),
            "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed"),
            "promotion_allowed": candidate.get("promotion_allowed"),
            "next_required_gate": candidate.get("next_required_gate"),
            "neutral_prescreen_required_before_portfolio_grid": candidate.get("neutral_prescreen_required_before_portfolio_grid"),
        }
        for candidate in result.get("candidates", []) or []
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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
