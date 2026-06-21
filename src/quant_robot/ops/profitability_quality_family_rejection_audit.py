from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


STAGE = "profitability_quality_family_rejection_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
POST_SYNC_RESEARCH_DIRECTION = "capacity_safe_price_volume_lowvol_reversal_composite_preregistration"
ROUND100_SYNC_DIRECTION = "round100_lightweight_stage_report_and_github_safe_sync"
ROBUSTNESS_DIRECTION = "profitability_quality_lead_robustness_and_portfolio_translation_audit"


def build_profitability_quality_family_rejection_audit(
    *,
    controlled_ic_screen: dict[str, Any],
    source_report: str | Path | None = None,
    rounds: Iterable[int] = (97, 98, 99),
) -> dict[str, Any]:
    summary = _dict(controlled_ic_screen.get("summary"))
    promotion = _dict(controlled_ic_screen.get("promotion_policy"))
    multiple_testing = _dict(controlled_ic_screen.get("multiple_testing"))
    round_list = [int(round_id) for round_id in rounds]
    requirements = _requirements(summary, promotion, multiple_testing, round_list)
    reject_reasons = _reject_reasons(summary, promotion)
    reject_family = not _blockers(requirements) and bool(reject_reasons)
    has_lead = _int(summary.get("research_lead_count")) > 0 or _int(summary.get("fdr_significant")) > 0
    if has_lead and not reject_family:
        status = "family_not_rejected_needs_robustness"
        immediate_next = ROBUSTNESS_DIRECTION
        post_sync = "not_applicable_until_robustness_review"
        family_hibernated = False
        continue_same_family = True
    elif reject_family:
        status = "family_rejected_rotate_after_sync"
        immediate_next = ROUND100_SYNC_DIRECTION
        post_sync = POST_SYNC_RESEARCH_DIRECTION
        family_hibernated = True
        continue_same_family = False
    else:
        status = "audit_blocked"
        immediate_next = "repair_profitability_quality_audit_inputs"
        post_sync = "blocked"
        family_hibernated = False
        continue_same_family = False
    payload: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source_report": str(source_report) if source_report else "",
        "rounds": round_list,
        "summary": {
            "family": "financial_profitability_quality",
            "candidate_count": _int(summary.get("candidate_count")),
            "test_count": _int(summary.get("test_count")),
            "ic_observation_count": _int(summary.get("ic_observation_count")),
            "aligned_rows": _int(summary.get("aligned_rows")),
            "bonferroni_significant": _int(summary.get("bonferroni_significant")),
            "fdr_significant": _int(summary.get("fdr_significant")),
            "research_lead_count": _int(summary.get("research_lead_count")),
            "requirements": len(requirements),
            "passed_requirements": sum(1 for row in requirements if row["status"] == "pass"),
            "blocked_requirements": sum(1 for row in requirements if row["status"] == "block"),
        },
        "requirements": requirements,
        "decision": {
            "family_hibernated": family_hibernated,
            "continue_same_family": continue_same_family,
            "reject_reasons": reject_reasons,
            "immediate_next_direction": immediate_next,
            "post_sync_research_direction": post_sync,
            "round100_sync_due": status == "family_rejected_rotate_after_sync",
        },
        "public_reference_review": _public_reference_review(),
        "next_protocol": _next_protocol(),
        "promotion_policy": {
            "promotion_allowed": False,
            "paper_ready_allowed": False,
            "portfolio_backtest_allowed": bool(has_lead and not reject_family),
            "parameter_tuning_allowed": False,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    payload["markdown"] = render_profitability_quality_family_rejection_audit_markdown(payload)
    return payload


def write_profitability_quality_family_rejection_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_quality_family_rejection_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_quality_family_rejection_audit.md").write_text(
        render_profitability_quality_family_rejection_audit_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("requirements", []) or []).to_csv(
        output_path / "profitability_quality_family_rejection_requirements.csv",
        index=False,
    )


def render_profitability_quality_family_rejection_audit_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    decision = _dict(audit.get("decision"))
    lines = [
        "# Profitability Quality Family Rejection Audit",
        "",
        "## Family Rejection",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Status: {audit.get('status', 'unknown')}",
        f"- Family: {summary.get('family', 'financial_profitability_quality')}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- IC observations: {summary.get('ic_observation_count', 0)}",
        f"- Bonferroni significant: {summary.get('bonferroni_significant', 0)}",
        f"- FDR significant: {summary.get('fdr_significant', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Family hibernated: {decision.get('family_hibernated', False)}",
        f"- Continue same family: {decision.get('continue_same_family', False)}",
        f"- Immediate next direction: {decision.get('immediate_next_direction', '')}",
        f"- Post-sync research direction: {decision.get('post_sync_research_direction', '')}",
        f"- Live boundary allowed: {audit.get('live_boundary_allowed', False)}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Requirements",
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in audit.get("requirements", []) or []:
        lines.append(
            f"| {row.get('label', row.get('requirement_id', 'unknown'))} | {row.get('status', 'unknown')} | {_table_text(row.get('evidence', ''))} |"
        )
    lines.extend(["", "## Reject Reasons", ""])
    reasons = decision.get("reject_reasons", []) or []
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- none")
    lines.extend(["", "## Public Reference Review", ""])
    for item in audit.get("public_reference_review", {}).get("notes", []) or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _requirements(
    summary: dict[str, Any],
    promotion: dict[str, Any],
    multiple_testing: dict[str, Any],
    rounds: list[int],
) -> list[dict[str, Any]]:
    blockers = _as_list(summary.get("blockers"))
    return [
        _requirement(
            "controlled_ic_screen_passed",
            "Controlled IC screen passed",
            not blockers and _bool(summary.get("passes"), True),
            f"blockers={len(blockers)}",
            blockers,
        ),
        _requirement(
            "minimum_test_count",
            "Minimum test count",
            _int(summary.get("test_count")) > 0,
            f"test_count={_int(summary.get('test_count'))}",
            ["missing_ic_tests"] if _int(summary.get("test_count")) <= 0 else [],
        ),
        _requirement(
            "multiple_testing_recorded",
            "Multiple testing recorded",
            _int(multiple_testing.get("test_count")) > 0 and multiple_testing.get("bonferroni_alpha") is not None,
            f"test_count={_int(multiple_testing.get('test_count'))}, bonferroni_alpha={multiple_testing.get('bonferroni_alpha')}",
            ["missing_multiple_testing_record"] if _int(multiple_testing.get("test_count")) <= 0 else [],
        ),
        _requirement(
            "zero_multiple_testing_leads",
            "Zero multiple-testing leads",
            _int(summary.get("bonferroni_significant")) == 0 and _int(summary.get("fdr_significant")) == 0,
            f"bonferroni={_int(summary.get('bonferroni_significant'))}, fdr={_int(summary.get('fdr_significant'))}",
            [],
        ),
        _requirement(
            "portfolio_promotion_blocked",
            "Portfolio promotion blocked",
            not _bool(promotion.get("promotion_allowed")) and not _bool(promotion.get("portfolio_backtest_allowed")),
            f"promotion_allowed={_bool(promotion.get('promotion_allowed'))}, portfolio_backtest_allowed={_bool(promotion.get('portfolio_backtest_allowed'))}",
            ["portfolio_promotion_not_blocked"]
            if _bool(promotion.get("promotion_allowed")) or _bool(promotion.get("portfolio_backtest_allowed"))
            else [],
        ),
        _requirement(
            "three_round_review_due",
            "Three-round review due",
            len(rounds) == 3 and max(rounds) - min(rounds) == 2,
            f"rounds={','.join(str(round_id) for round_id in rounds)}",
            ["invalid_three_round_review_window"] if not (len(rounds) == 3 and max(rounds) - min(rounds) == 2) else [],
        ),
    ]


def _reject_reasons(summary: dict[str, Any], promotion: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _int(summary.get("research_lead_count")) == 0 and _int(summary.get("fdr_significant")) == 0:
        reasons.append("zero_multiple_testing_leads")
    if _int(summary.get("bonferroni_significant")) == 0:
        reasons.append("zero_bonferroni_significant_results")
    if not _bool(promotion.get("portfolio_backtest_allowed")):
        reasons.append("portfolio_backtest_not_allowed_after_ic_failure")
    return reasons


def _public_reference_review() -> dict[str, Any]:
    references = ["qlib", "alphalens", "vectorbt", "pyfolio", "worldquant_101_alphas"]
    notes = [
        "qlib-style workflow: keep data, factor generation, IC analysis, and portfolio simulation separated.",
        "alphalens-style workflow: require IC, quantile spread, turnover, and decay evidence before portfolio expansion.",
        "vectorbt-style workflow: only run fast portfolio grids after a signal survives pre-registered statistical screens.",
        "pyfolio-style workflow: reserve risk attribution for candidates with real portfolio evidence.",
        "worldquant_101_alphas-style workflow: rotate to simple price-volume transforms with explicit economic intuition instead of tuning a failed family.",
    ]
    return {
        "references": references,
        "notes": notes,
        "implication": POST_SYNC_RESEARCH_DIRECTION,
    }


def _next_protocol() -> dict[str, Any]:
    return {
        "forbidden_directions": [
            "profitability_quality_more_parameter_tuning_after_zero_ic_leads",
            "profitability_quality_portfolio_backtest_after_failed_controlled_ic_screen",
            "profitability_quality_full_universe_expansion_before_shard_ic_signal",
        ],
        "required_before_next_mining": [
            "round100_lightweight_stage_report",
            "github_safe_sync_after_validation",
            "capacity_safe_price_volume_candidate_preregistration",
            "alphalens_style_ic_quantile_turnover_prescreen",
            "no_portfolio_grid_before_statistical_lead",
        ],
    }


def _requirement(
    requirement_id: str,
    label: str,
    ok: bool,
    evidence: str,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "status": "pass" if ok else "block",
        "evidence": evidence,
        "blockers": blockers or ([] if ok else [requirement_id]),
    }


def _blockers(requirements: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in requirements:
        if row.get("status") == "block":
            blockers.extend(_as_list(row.get("blockers")) or [str(row.get("requirement_id"))])
    return list(dict.fromkeys(blocker for blocker in blockers if blocker))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
