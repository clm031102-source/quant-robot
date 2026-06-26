from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable


STAGE = "turnover_continuous_capacity_repair_preregistration"
NEXT_REQUIRED_GATE = "capacity_repair_ic_quantile_turnover_prescreen"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
SOURCE_AUDIT = "docs/research/cn_stock_aggressive_turnover_capacity_audit_round122_2026-06-22.md"
SOURCE_LEADS = ("turnover_rate_low", "turnover_rate_f_low")
DEFAULT_CAPACITY_POLICY: dict[str, Any] = {
    "exclude_st": True,
    "exclude_suspended": True,
    "exclude_limit_up_down_if_untradable": True,
    "min_listing_days": 120,
    "min_signal_date_amount": 10_000_000,
    "max_position_adv_participation": 0.01,
    "require_calendar_holding_gate": True,
    "require_extreme_trade_diagnostic": True,
}


@dataclass(frozen=True)
class TurnoverCapacityRepairCandidateSpec:
    factor_name: str
    raw_factor_name: str
    formula_template: str
    repair_type: str
    required_fields: tuple[str, ...]
    economic_rationale: str
    capacity_repair_rationale: str
    windows: tuple[int, ...] = (20,)
    public_reference_tags: tuple[str, ...] = ("alphalens", "pyfolio", "vectorbt")
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_turnover_continuous_capacity_repair_specs() -> list[TurnoverCapacityRepairCandidateSpec]:
    specs: list[TurnoverCapacityRepairCandidateSpec] = []
    for raw_name, raw_field in (
        ("turnover_rate_low", "turnover_rate"),
        ("turnover_rate_f_low", "turnover_rate_f"),
    ):
        specs.extend(
            [
                TurnoverCapacityRepairCandidateSpec(
                    factor_name=f"{raw_name}_adv_soft_rank_20",
                    raw_factor_name=raw_name,
                    formula_template=(
                        f"cs_z(-{raw_field}) * clip(cs_rank(log_adv20), 0.35, 1.00) + "
                        "0.20*cs_z(log_circ_mv)"
                    ),
                    repair_type="continuous_capacity_weight",
                    required_fields=(raw_field, "amount", "circ_mv"),
                    economic_rationale=(
                        "Keeps the low-turnover behavioral anomaly but makes the liquidity term continuous, "
                        "so the signal is not a hard large-cap substitution."
                    ),
                    capacity_repair_rationale=(
                        "Use ADV rank as a soft multiplier to reduce participation risk while preserving "
                        "some raw low-turnover ranking information."
                    ),
                ),
                TurnoverCapacityRepairCandidateSpec(
                    factor_name=f"{raw_name}_adv_mv_soft_blend_20",
                    raw_factor_name=raw_name,
                    formula_template=(
                        f"0.60*cs_z(-{raw_field}) + 0.25*cs_z(log_adv20) + 0.15*cs_z(log_circ_mv)"
                    ),
                    repair_type="continuous_capacity_weight",
                    required_fields=(raw_field, "amount", "circ_mv"),
                    economic_rationale=(
                        "Tests whether the raw low-turnover edge survives a mild liquidity and free-float "
                        "capacity blend without the destructive binary large-mv gate."
                    ),
                    capacity_repair_rationale=(
                        "Blend liquidity and market-cap continuously to avoid selecting names that exceed "
                        "the participation budget."
                    ),
                ),
                TurnoverCapacityRepairCandidateSpec(
                    factor_name=f"{raw_name}_participation_budget_100k_20",
                    raw_factor_name=raw_name,
                    formula_template=(
                        f"cs_z(-{raw_field}) * clip(0.01 / estimated_participation_100k_top100_adv20, 0.00, 1.00)"
                    ),
                    repair_type="continuous_capacity_weight",
                    required_fields=(raw_field, "amount", "circ_mv"),
                    economic_rationale=(
                        "The raw factor may be valuable only at small capital. This candidate explicitly "
                        "tests a 100k portfolio participation budget instead of pretending it scales."
                    ),
                    capacity_repair_rationale=(
                        "Participation-budget weighting directly penalizes trades that would breach 1% ADV."
                    ),
                ),
            ]
        )
    return specs


def build_turnover_continuous_capacity_repair_preregistration(
    *,
    min_candidates: int = 6,
    candidate_specs: Iterable[TurnoverCapacityRepairCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_turnover_continuous_capacity_repair_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_evidence": {
            "source_audit": SOURCE_AUDIT,
            "raw_research_leads": list(SOURCE_LEADS),
            "audit_tags": [
                "round122_aggressive_turnover_capacity_audit",
                "raw_high_return_capacity_blocked",
                "binary_large_mv_repair_failed",
            ],
            "decision": "Run one disciplined continuous-capacity repair preregistration before hibernating low-turnover.",
        },
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "min_candidates": min_candidates,
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "source_research_leads": len({candidate["raw_factor_name"] for candidate in candidates}),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
        },
        "capacity_policy": {
            "policy": DEFAULT_CAPACITY_POLICY,
            "reason": (
                "User drawdown tolerance does not waive capacity. Raw low-turnover can advance only through "
                "capacity-clean, extreme-trade-clean, costed evidence."
            ),
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "mean_spearman_rank_ic",
                "icir",
                "rank_ic_t_stat",
                "q5_q1_spread",
                "quantile_monotonicity",
                "top_quantile_turnover",
                "capacity_limited_trade_count",
                "max_participation_rate",
                "extreme_trade_return_count",
                "raw_factor_correlation",
            ],
            "portfolio_backtest_allowed_after": "capacity_clean_ic_quantile_turnover_prescreen_lead",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_extreme_trade_diagnostic": True,
            "requires_regime_coverage": True,
            "next_allowed_action": "Build candidate factor matrices and run capacity-repair IC/quantile/turnover prescreen.",
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_turnover_continuous_capacity_repair_markdown(result)
    return result


def write_turnover_continuous_capacity_repair_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "turnover_continuous_capacity_repair_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "turnover_continuous_capacity_repair_preregistration.md").write_text(
        render_turnover_continuous_capacity_repair_markdown(result),
        encoding="utf-8",
    )
    rows = _candidate_csv_rows(result)
    with (output_path / "turnover_continuous_capacity_repair_candidates.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["factor_name"])
        writer.writeheader()
        writer.writerows(rows)


def render_turnover_continuous_capacity_repair_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    source = result.get("source_evidence", {})
    lines = [
        "# Turnover Continuous Capacity Repair Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Source research leads: {summary.get('source_research_leads', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Source Evidence",
        "",
        f"- Source audit: `{source.get('source_audit', SOURCE_AUDIT)}`",
        "- Raw research leads: " + ", ".join(source.get("raw_research_leads", []) or []),
        "- Audit tags: " + ", ".join(source.get("audit_tags", []) or []),
        "",
        "## Capacity Policy",
        "",
        f"- Policy: `{json.dumps(result.get('capacity_policy', {}).get('policy', {}), sort_keys=True)}`",
        f"- Reason: {result.get('capacity_policy', {}).get('reason', '')}",
        "",
        "## Candidates",
        "",
        "| Factor | Raw factor | Repair | Formula | Required fields |",
        "|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {name} | {raw} | {repair} | `{formula}` | {fields} |".format(
                name=candidate["factor_name"],
                raw=candidate["raw_factor_name"],
                repair=candidate["repair_type"],
                formula=candidate["formula_template"],
                fields=", ".join(candidate.get("required_fields", []) or []),
            )
        )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: TurnoverCapacityRepairCandidateSpec) -> dict[str, Any]:
    return {
        "factor_name": spec.factor_name,
        "raw_factor_name": spec.raw_factor_name,
        "market": "CN",
        "asset_type": "stock",
        "family": "daily_basic_low_turnover_capacity_repair",
        "formula_template": spec.formula_template,
        "repair_type": spec.repair_type,
        "direction": "higher_is_better",
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "economic_rationale": spec.economic_rationale,
        "capacity_repair_rationale": spec.capacity_repair_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "capacity_policy": dict(DEFAULT_CAPACITY_POLICY),
        "source_evidence_status": "round122_raw_lead_capacity_blocked_preregistered_repair",
        "registration_status": "pre_registered",
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "lookahead_policy": "Signal uses only same-date daily-basic and trailing ADV fields; execution must lag to next tradable bar.",
    }


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int) -> list[str]:
    blockers: list[str] = []
    names = [candidate["factor_name"] for candidate in candidates]
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len(names) != len(set(names)):
        blockers.append("duplicate_candidate_names")
    if any(candidate.get("raw_factor_name") not in SOURCE_LEADS for candidate in candidates):
        blockers.append("unknown_raw_turnover_source")
    if any("large_mv" in candidate.get("factor_name", "") for candidate in candidates):
        blockers.append("binary_large_mv_repair_reused")
    if any("binary_large_mv" in candidate.get("formula_template", "") for candidate in candidates):
        blockers.append("binary_large_mv_repair_reused")
    if any(candidate.get("repair_type") != "continuous_capacity_weight" for candidate in candidates):
        blockers.append("non_continuous_repair_type")
    if any(not set(("amount", "circ_mv")).issubset(set(candidate.get("required_fields", []))) for candidate in candidates):
        blockers.append("missing_capacity_required_fields")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    return _dedupe(blockers)


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "raw_factor_name": candidate["raw_factor_name"],
                "repair_type": candidate["repair_type"],
                "windows": ",".join(str(window) for window in candidate.get("windows", []) or []),
                "required_fields": ",".join(candidate.get("required_fields", []) or []),
                "registration_status": candidate["registration_status"],
                "next_required_gate": candidate["next_required_gate"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
                "max_position_adv_participation": candidate["capacity_policy"]["max_position_adv_participation"],
                "formula_template": candidate["formula_template"],
            }
        )
    return rows


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
        return value.isoformat()
    return value
