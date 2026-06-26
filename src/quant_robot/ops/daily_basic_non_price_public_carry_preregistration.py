from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable


STAGE = "daily_basic_non_price_public_carry_preregistration"
ROUND130_SOURCE_AUDIT = "docs/research/cn_stock_alpha101_rank_pv_reversal_residual_prescreen_round130_2026-06-22.md"
ROUND132_NEXT_DIRECTION = "round132_daily_basic_non_price_public_carry_prescreen"
SOURCE_EVIDENCE_STATUS = "daily_basic_public_carry_preregistered_not_empirical_alpha"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

KNOWN_DAILY_BASIC_FIELDS = (
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
    "volume_ratio",
)

FORBIDDEN_TERMS = (
    "low_turnover",
    "turnover_rate",
    "turnover_rate_f",
    "alpha101",
    "pv_",
    "moneyflow",
    "adj_close",
    "close",
    "open",
    "high",
    "low",
    "amount",
)


@dataclass(frozen=True)
class DailyBasicNonPricePublicCarryCandidateSpec:
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


def default_daily_basic_non_price_public_carry_specs() -> list[DailyBasicNonPricePublicCarryCandidateSpec]:
    return [
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_dividend_value_stability_carry_20",
            family="dividend_value_carry",
            formula_template=(
                "0.35*cs_z(dv_ttm)+0.25*cs_z(dv_ratio)+0.20*cs_z(inv_pb)+"
                "0.20*cs_z(inv_pe_ttm_stable_20)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("dv_ttm", "dv_ratio", "pb", "pe_ttm"),
            economic_rationale=(
                "Dividend yield and inexpensive valuation are public carry/value ideas; stability is added "
                "before measurement so the candidate is not a raw cheap-stock sweep."
            ),
            public_reference_tags=("dividend_yield", "fama_french_value", "alphalens"),
            expected_failure_modes=("value_trap", "dividend_data_sparse", "portfolio_translation_gap"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_value_yield_size_neutral_20",
            family="dividend_value_carry",
            formula_template=(
                "0.45*cs_z(resid_value_yield_vs_log_circ_mv_20)+0.30*cs_z(dv_ttm)+"
                "0.25*cs_z(inv_ps_ttm)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("pe_ttm", "pb", "ps_ttm", "dv_ttm", "circ_mv"),
            economic_rationale=(
                "Value/yield must prove it is not only a size proxy, so the preregistered signal starts from "
                "a size-neutral carry template."
            ),
            public_reference_tags=("fama_french_value", "quality_value", "alphalens"),
            expected_failure_modes=("size_exposure_disguise", "weak_icir", "sector_concentration"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_valuation_reversion_quality_60",
            family="valuation_stability",
            formula_template="0.45*cs_z(-pb_z_60)+0.30*cs_z(-ps_ttm_z_60)+0.25*cs_z(dv_ttm)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("pb", "ps_ttm", "dv_ttm"),
            economic_rationale=(
                "Rolling valuation mean reversion is a slow public value hypothesis that should not depend on "
                "same-family price-volume reversal."
            ),
            public_reference_tags=("value_reversion", "fama_french_value", "alphalens"),
            expected_failure_modes=("slow_decay", "accounting_regime_shift", "weak_monotonicity"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_valuation_dispersion_compression_60",
            family="valuation_stability",
            formula_template=(
                "0.40*cs_z(-abs_pb_z_60)+0.35*cs_z(-abs_pe_ttm_z_60)+0.25*cs_z(dv_ratio)"
            ),
            direction="higher_is_better",
            windows=(60,),
            required_fields=("pb", "pe_ttm", "dv_ratio"),
            economic_rationale=(
                "This tests whether valuation normalization, not price momentum, carries cross-sectional "
                "information after extreme valuation outliers are avoided."
            ),
            public_reference_tags=("value_reversion", "robust_value", "alphalens"),
            expected_failure_modes=("outlier_dependency", "insufficient_spread", "yearly_instability"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_free_float_supply_quality_20",
            family="share_structure_quality",
            formula_template=(
                "0.45*cs_z(free_share_to_total_share)+0.30*cs_z(float_share_to_total_share)+"
                "0.25*cs_z(inv_pb)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("free_share", "float_share", "total_share", "pb"),
            economic_rationale=(
                "Share-structure quality is a supply-side public hypothesis; combining it with value avoids a "
                "standalone float-structure artifact."
            ),
            public_reference_tags=("share_structure", "quality_value", "alphalens"),
            expected_failure_modes=("supply_proxy_weakness", "corporate_action_noise", "capacity_tail"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_float_structure_value_blend_20",
            family="share_structure_quality",
            formula_template=(
                "0.35*cs_z(free_share_to_float_share)+0.35*cs_z(inv_pb)+0.30*cs_z(dv_ttm)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("free_share", "float_share", "pb", "dv_ttm"),
            economic_rationale=(
                "The candidate checks whether float availability plus value/yield creates a cleaner "
                "implementation path than low-liquidity tails."
            ),
            public_reference_tags=("share_structure", "dividend_yield", "pyfolio"),
            expected_failure_modes=("data_revision", "low_cross_section_coverage", "weak_oos"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_volume_ratio_crowding_reversal_20",
            family="crowding_balance",
            formula_template="0.45*cs_z(-volume_ratio_z_20)+0.30*cs_z(inv_pb)+0.25*cs_z(dv_ttm)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("volume_ratio", "pb", "dv_ttm"),
            economic_rationale=(
                "Volume-ratio crowding is a daily-basic field, not raw low-turnover. It is tested as a "
                "valuation-backed anti-crowding hypothesis."
            ),
            public_reference_tags=("crowding", "contrarian_value", "alphalens"),
            expected_failure_modes=("hidden_liquidity_tail", "event_day_artifact", "turnover_cost"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_crowding_value_yield_balance_20",
            family="crowding_balance",
            formula_template=(
                "0.35*cs_z(-abs_volume_ratio_z_20)+0.35*cs_z(inv_ps_ttm)+0.30*cs_z(dv_ratio)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("volume_ratio", "ps_ttm", "dv_ratio"),
            economic_rationale=(
                "This candidate avoids extreme crowding while keeping value/yield exposure fixed before "
                "measurement."
            ),
            public_reference_tags=("crowding", "robust_value", "alphalens"),
            expected_failure_modes=("crowding_proxy_noise", "weak_quantile_spread", "capacity_filter_failure"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_midcap_value_yield_capacity_20",
            family="capacity_aware_value",
            formula_template=(
                "0.30*cs_z(dv_ttm)+0.30*cs_z(inv_pb)+0.20*cs_z(inv_ps_ttm)+"
                "0.20*cs_z(mid_circ_mv_score)"
            ),
            direction="higher_is_better",
            windows=(20,),
            required_fields=("dv_ttm", "pb", "ps_ttm", "circ_mv"),
            economic_rationale=(
                "A mid-cap value/yield template tests a capacity-aware value thesis without falling back to "
                "binary large-market-cap repair."
            ),
            public_reference_tags=("fama_french_value", "capacity_aware_value", "pyfolio"),
            expected_failure_modes=("midcap_beta", "relative_return_failure", "drawdown_tail"),
        ),
        DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_size_quality_value_stability_60",
            family="capacity_aware_value",
            formula_template=(
                "0.35*cs_z(inv_pb)+0.25*cs_z(dv_ttm)+0.20*cs_z(mid_total_mv_score)+"
                "0.20*cs_z(-valuation_instability_60)"
            ),
            direction="higher_is_better",
            windows=(60,),
            required_fields=("pb", "dv_ttm", "total_mv", "pe_ttm"),
            economic_rationale=(
                "Capacity-aware value needs stable valuation and sufficient implementability before any "
                "portfolio conversion."
            ),
            public_reference_tags=("quality_value", "robust_value", "pyfolio"),
            expected_failure_modes=("stability_overfiltering", "valuation_trap", "weak_icir"),
        ),
    ]


def build_daily_basic_non_price_public_carry_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 4,
    candidate_specs: Iterable[DailyBasicNonPricePublicCarryCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_daily_basic_non_price_public_carry_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
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
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": ROUND132_NEXT_DIRECTION,
            "next_direction": ROUND132_NEXT_DIRECTION,
        },
        "family_rotation_context": {
            "source_audit": ROUND130_SOURCE_AUDIT,
            "source_round": "round130_alpha101_rank_pv_reversal_residual_prescreen",
            "hibernated_families": [
                "alpha101_rank_pv_reversal",
                "pv_reversal_cluster",
                "low_turnover_repair",
                "raw_moneyflow_only",
            ],
            "rotation_reason": (
                "Round130 showed negative residual IC after public price-volume reference de-duplication. "
                "Round122-126 also showed that high raw low-liquidity return cannot bypass capacity, "
                "overlap, extreme-trade, and drawdown gates."
            ),
            "next_direction": ROUND132_NEXT_DIRECTION,
        },
        "public_reference_review": {
            "projects_reviewed": [
                "alphalens",
                "pyfolio",
                "qlib",
                "public_value_yield_research",
                "fama_french_value_templates",
            ],
            "method": (
                "Use public value/carry/quality ideas as fixed hypotheses only. Daily-basic candidates are "
                "pre-registered before measurement and counted in multiple-testing accounting."
            ),
        },
        "data_policy": {
            "known_daily_basic_fields": list(KNOWN_DAILY_BASIC_FIELDS),
            "forbidden_terms": list(FORBIDDEN_TERMS),
            "coverage_preflight_required": True,
            "reason": (
                "The local daily-basic factor input schema is available, but empirical use must first prove "
                "date coverage, cross-section size, and same-date/next-bar alignment."
            ),
        },
        "evaluation_gate": {
            "next_required_gate": ROUND132_NEXT_DIRECTION,
            "required_metrics": [
                "daily_basic_coverage_preflight",
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "ic_positive_rate",
                "quantile_spread",
                "quantile_monotonicity",
                "factor_turnover",
                "capacity_participation",
                "field_coverage_by_date",
                "family_redundancy_correlation",
                "multiple_testing_accounting",
            ],
            "portfolio_backtest_allowed_after": "daily_basic_prescreen_lead_and_capacity_cleanliness",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_extreme_trade_diagnostic": True,
            "next_allowed_action": (
                "Build Round132 daily-basic-only factor matrices, run coverage preflight, and then perform "
                "IC/quantile/turnover/capacity prescreen. No portfolio grid before prescreen evidence."
            ),
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_daily_basic_non_price_public_carry_markdown(result)
    return result


def write_daily_basic_non_price_public_carry_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_non_price_public_carry_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_non_price_public_carry_preregistration.md").write_text(
        render_daily_basic_non_price_public_carry_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "daily_basic_non_price_public_carry_candidates.csv", _candidate_csv_rows(result))


def render_daily_basic_non_price_public_carry_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("family_rotation_context", {})
    lines = [
        "# Daily-Basic Non-Price Public Carry Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', ROUND130_SOURCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', ROUND132_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Rotation Context",
        "",
        f"- Hibernated families: {', '.join(rotation.get('hibernated_families', []))}",
        f"- Rotation reason: {rotation.get('rotation_reason', '')}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Windows | Required fields | Public refs | Failure modes |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {factor} | {family} | {windows} | {fields} | {refs} | {failure_modes} |".format(
                factor=candidate["factor_name"],
                family=candidate["family"],
                windows="/".join(str(item) for item in candidate["windows"]),
                fields=", ".join(candidate["required_fields"]),
                refs=", ".join(candidate["public_reference_tags"]),
                failure_modes=", ".join(candidate["expected_failure_modes"]),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is preregistration only and creates no profitability claim.",
            "- Round132 must start with daily-basic coverage preflight and must count all candidates in multiple-testing accounting.",
            "- No candidate may enter a portfolio grid before IC, quantile, turnover, field-coverage, and capacity evidence exists.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: DailyBasicNonPricePublicCarryCandidateSpec) -> dict[str, Any]:
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "source_evidence_status": spec.source_evidence_status,
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
        "market": "CN",
        "asset_type": "stock",
        "next_required_gate": ROUND132_NEXT_DIRECTION,
    }


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers: list[str] = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if any(candidate["portfolio_backtest_allowed"] for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate["promotion_allowed"] for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    if any(_has_forbidden_term(candidate) for candidate in candidates):
        blockers.append("forbidden_low_turnover_or_price_volume_term")
    if any(not set(candidate["required_fields"]).issubset(set(KNOWN_DAILY_BASIC_FIELDS)) for candidate in candidates):
        blockers.append("unknown_or_forbidden_required_fields")
    if any(not candidate["economic_rationale"] for candidate in candidates):
        blockers.append("missing_economic_rationale")
    if any(not candidate["public_reference_tags"] for candidate in candidates):
        blockers.append("missing_public_reference_tags")
    if any(not candidate["expected_failure_modes"] for candidate in candidates):
        blockers.append("missing_expected_failure_modes")
    return _dedupe(blockers)


def _has_forbidden_term(candidate: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(candidate.get("factor_name", "")),
            str(candidate.get("family", "")),
            str(candidate.get("formula_template", "")),
            " ".join(str(item) for item in candidate.get("required_fields", [])),
        ]
    ).lower()
    return any(term in text for term in FORBIDDEN_TERMS)


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "family": candidate["family"],
                "direction": candidate["direction"],
                "windows": "|".join(str(item) for item in candidate["windows"]),
                "required_fields": "|".join(candidate["required_fields"]),
                "public_reference_tags": "|".join(candidate["public_reference_tags"]),
                "expected_failure_modes": "|".join(candidate["expected_failure_modes"]),
                "source_evidence_status": candidate["source_evidence_status"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
                "next_required_gate": candidate["next_required_gate"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "factor_name",
        "family",
        "direction",
        "windows",
        "required_fields",
        "public_reference_tags",
        "expected_failure_modes",
        "source_evidence_status",
        "portfolio_backtest_allowed",
        "promotion_allowed",
        "next_required_gate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    return value
