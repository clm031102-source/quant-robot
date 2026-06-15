from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.execution.boundary import build_execution_boundary_status, build_manual_approval_packet


STAGE = "phase_6_1_small_capital_review_gate"


@dataclass(frozen=True)
class SmallCapitalReviewPolicy:
    max_initial_capital: float = 10000.0
    max_single_order_notional: float = 1000.0
    max_daily_loss: float = 200.0
    max_paper_drawdown: float = 0.10
    min_paper_fills: int = 30
    min_observation_days: int = 20
    min_observed_candidates: int = 1
    min_completed_candidates: int = 1
    max_guard_events: int = 0
    max_execution_events: int = 0
    min_market_regimes: int = 2


def build_small_capital_review_gate(
    review_packet: dict[str, Any],
    *,
    manual_rehearsal: dict[str, Any] | None = None,
    paper_observation: dict[str, Any] | None = None,
    pre_api_readiness: dict[str, Any] | None = None,
    observation_sufficiency: dict[str, Any] | None = None,
    market_regime_coverage: dict[str, Any] | None = None,
    policy: SmallCapitalReviewPolicy | dict[str, Any] | None = None,
    reviewer: str | None = None,
) -> dict[str, Any]:
    active_policy = _policy(policy)
    candidate = _dict(review_packet.get("selected_candidate"))
    boundary = build_execution_boundary_status()
    requirements = [
        _candidate_requirement(candidate),
        _manual_gate_requirement(review_packet, candidate),
        _manual_rehearsal_requirement(manual_rehearsal),
        _pre_api_readiness_requirement(pre_api_readiness),
        _paper_observation_requirement(candidate, paper_observation, active_policy),
        _observation_sufficiency_requirement(observation_sufficiency),
        _market_regime_coverage_requirement(market_regime_coverage, active_policy),
        _execution_boundary_requirement(boundary),
    ]
    blockers = _blockers(requirements)
    ready = not blockers
    gate = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "ready_for_manual_small_capital_review" if ready else "blocked",
        "safety": _safety(),
        "selected_candidate": candidate,
        "risk_limits": asdict(active_policy),
        "requirements": requirements,
        "summary": _summary(requirements, blockers),
        "decision": {
            "manual_small_capital_review_ready": ready,
            "live_boundary_allowed": False,
            "executable": False,
            "blockers": blockers,
        },
        "boundary": boundary,
        "manual_approval_packet": build_manual_approval_packet(candidate, reviewer=reviewer),
    }
    gate["markdown"] = render_small_capital_review_gate_markdown(gate)
    return gate


def write_small_capital_review_gate(output_dir: str | Path, gate: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "small_capital_review_gate.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "small_capital_review_gate.md").write_text(str(gate.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(gate.get("requirements", [])).to_csv(output_path / "small_capital_review_requirements.csv", index=False)


def render_small_capital_review_gate_markdown(gate: dict[str, Any]) -> str:
    candidate = _dict(gate.get("selected_candidate"))
    decision = _dict(gate.get("decision"))
    boundary = _dict(gate.get("boundary"))
    limits = _dict(gate.get("risk_limits"))
    lines = [
        "# Small Capital Review Gate",
        "",
        f"- Stage: {gate.get('stage', STAGE)}",
        f"- Status: {gate.get('status', 'unknown')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Manual review ready: {decision.get('manual_small_capital_review_ready', False)}",
        f"- Live boundary allowed: {decision.get('live_boundary_allowed', False)}",
        f"- Executable: {decision.get('executable', False)}",
        f"- Max initial capital: {limits.get('max_initial_capital')}",
        f"- Max single order notional: {limits.get('max_single_order_notional')}",
        f"- Max daily loss: {limits.get('max_daily_loss')}",
        f"- Broker connection: {boundary.get('broker_connection', 'disabled')}",
        f"- Account reads: {boundary.get('account_reads', 'disabled')}",
        f"- Order placement: {boundary.get('order_placement', 'disabled')}",
        f"- Safety: {gate.get('safety', _safety())}",
        "",
        "## Requirements",
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in gate.get("requirements", []):
        if isinstance(row, dict):
            lines.append(
                f"| {row.get('label', row.get('requirement_id', 'unknown'))} | {row.get('status', 'unknown')} | {_table_text(row.get('evidence', ''))} |"
            )
    lines.extend(["", "## Blockers", ""])
    blockers = _as_list(decision.get("blockers"))
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _candidate_requirement(candidate: dict[str, Any]) -> dict[str, Any]:
    case_id = str(candidate.get("case_id", ""))
    status = str(candidate.get("promotion_status", ""))
    ok = bool(case_id) and status == "manual_live_review"
    if not case_id:
        blockers = ["selected_candidate_missing"]
    elif status != "manual_live_review":
        blockers = ["promotion_status_not_manual_live_review"]
    else:
        blockers = []
    return _requirement("selected_candidate", "Selected candidate", "pass" if ok else "block", f"case_id={case_id or 'none'}, promotion_status={status or 'none'}", blockers)


def _manual_gate_requirement(review_packet: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    gate = _dict(review_packet.get("manual_review_gate"))
    allowed = bool(gate.get("allowed"))
    reasons = _as_list(gate.get("reasons"))
    blockers = [] if allowed else reasons or ["manual_live_review_not_enabled"]
    if not allowed and str(candidate.get("promotion_status")) != "manual_live_review" and "promotion_status_not_manual_live_review" not in blockers:
        blockers.append("promotion_status_not_manual_live_review")
    return _requirement("manual_review_gate", "Manual review gate", "pass" if allowed else "block", "allowed" if allowed else ", ".join(blockers), blockers)


def _manual_rehearsal_requirement(manual_rehearsal: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(manual_rehearsal, dict):
        return _requirement("manual_review_rehearsal", "Manual review rehearsal", "block", "missing", ["manual_review_rehearsal_missing"])
    dry_run = _dict(manual_rehearsal.get("dry_run"))
    blockers = _as_list(manual_rehearsal.get("blockers"))
    if str(manual_rehearsal.get("gate_status")) != "ready_for_manual_review_rehearsal":
        blockers.append("manual_review_rehearsal_not_ready")
    if bool(dry_run.get("would_cross_live_boundary", False)):
        blockers.append("manual_rehearsal_crosses_live_boundary")
    if str(dry_run.get("broker_connection", "disabled")) != "disabled":
        blockers.append("manual_rehearsal_broker_connection_enabled")
    if str(dry_run.get("account_reads", "disabled")) != "disabled":
        blockers.append("manual_rehearsal_account_reads_enabled")
    if str(dry_run.get("order_placement", "disabled")) != "disabled":
        blockers.append("manual_rehearsal_order_placement_enabled")
    if bool(dry_run.get("executable", False)):
        blockers.append("manual_rehearsal_executable")
    blockers = _dedupe(blockers)
    evidence = f"gate_status={manual_rehearsal.get('gate_status', 'missing')}, blockers={len(blockers)}"
    return _requirement("manual_review_rehearsal", "Manual review rehearsal", "pass" if not blockers else "block", evidence, blockers)


def _pre_api_readiness_requirement(pre_api_readiness: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(pre_api_readiness, dict):
        return _requirement("pre_api_readiness", "Pre-API readiness", "block", "missing", ["pre_api_readiness_missing"])
    blockers = [str(row.get("blocker_id")) for row in pre_api_readiness.get("blocker_register", []) if isinstance(row, dict) and row.get("blocker_id")]
    status = str(pre_api_readiness.get("overall_status", "missing"))
    if status != "ready_for_api_boundary_planning":
        blockers.append("pre_api_readiness_not_clear")
    boundary = _dict(pre_api_readiness.get("boundary"))
    if bool(boundary.get("would_cross_live_boundary", False)):
        blockers.append("pre_api_boundary_crosses_live_boundary")
    blockers = _dedupe(blockers)
    evidence = f"overall_status={status}, blockers={len(blockers)}"
    return _requirement("pre_api_readiness", "Pre-API readiness", "pass" if not blockers else "block", evidence, blockers)


def _paper_observation_requirement(
    candidate: dict[str, Any],
    paper_observation: dict[str, Any] | None,
    policy: SmallCapitalReviewPolicy,
) -> dict[str, Any]:
    if not isinstance(paper_observation, dict):
        return _requirement("paper_observation", "Paper observation", "block", "missing", ["paper_observation_missing"])
    summary = _dict(paper_observation.get("summary"))
    row = _candidate_paper_row(candidate, paper_observation)
    observed = _int(summary.get("observed_candidates"), 0)
    completed = _int(summary.get("completed_candidates"), 0)
    fills = _int(row.get("fills"), 0)
    drawdown = abs(_float(row.get("max_equity_drawdown"), 0.0))
    observation_days = _observation_days(_dict(row.get("observation_window")))
    guard_events = max(_int(summary.get("total_guard_events"), 0), _int(_dict(row.get("guard_summary")).get("guard_events"), 0))
    execution_events = max(_int(summary.get("total_execution_events"), 0), _int(_dict(row.get("execution_summary")).get("execution_events"), 0))
    blockers: list[str] = []
    if observed < policy.min_observed_candidates:
        blockers.append("paper_observed_candidates_below_minimum")
    if completed < policy.min_completed_candidates:
        blockers.append("paper_completed_candidates_below_minimum")
    if not row:
        blockers.append("paper_candidate_observation_missing")
    if fills < policy.min_paper_fills:
        blockers.append("paper_fills_below_minimum")
    if observation_days < policy.min_observation_days:
        blockers.append("paper_observation_window_too_short")
    if drawdown > policy.max_paper_drawdown:
        blockers.append("paper_drawdown_above_limit")
    if guard_events > policy.max_guard_events:
        blockers.append("paper_guard_events_above_limit")
    if execution_events > policy.max_execution_events:
        blockers.append("paper_execution_events_above_limit")
    evidence = (
        f"observed_candidates={observed}, completed_candidates={completed}, fills={fills}, "
        f"observation_days={observation_days}, max_drawdown={drawdown:.6f}, guard_events={guard_events}, execution_events={execution_events}"
    )
    return _requirement("paper_observation", "Paper observation", "pass" if not blockers else "block", evidence, blockers)


def _observation_sufficiency_requirement(observation_sufficiency: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(observation_sufficiency, dict):
        return _requirement("observation_sufficiency", "Observation sufficiency", "block", "missing", ["observation_sufficiency_missing"])
    decision = _dict(observation_sufficiency.get("decision"))
    clear = str(observation_sufficiency.get("status")) == "sufficient" and bool(decision.get("observation_sufficiency_cleared", False))
    blockers = [] if clear else _as_list(decision.get("blockers")) or ["observation_sufficiency_not_clear"]
    evidence = f"status={observation_sufficiency.get('status', 'missing')}, blockers={len(blockers)}"
    return _requirement("observation_sufficiency", "Observation sufficiency", "pass" if clear else "block", evidence, blockers)


def _market_regime_coverage_requirement(market_regime_coverage: dict[str, Any] | None, policy: SmallCapitalReviewPolicy) -> dict[str, Any]:
    if not isinstance(market_regime_coverage, dict):
        return _requirement("market_regime_coverage", "Market regime coverage", "block", "missing", ["market_regime_coverage_missing"])
    summary = _dict(market_regime_coverage.get("summary"))
    decision = _dict(market_regime_coverage.get("decision"))
    covered = _int(summary.get("covered_regimes"), 0)
    regimes = _as_list(summary.get("regimes"))
    cleared = bool(decision.get("market_regime_coverage_cleared", False)) or str(market_regime_coverage.get("status")) == "sufficient"
    blockers = _as_list(decision.get("blockers"))
    if covered < policy.min_market_regimes:
        blockers.append("market_regimes_below_minimum")
    if not cleared:
        blockers.append("market_regime_coverage_not_clear")
    blockers = _dedupe(blockers)
    evidence = f"covered_regimes={covered}, min_market_regimes={policy.min_market_regimes}, regimes={','.join(regimes)}"
    return _requirement("market_regime_coverage", "Market regime coverage", "pass" if not blockers else "block", evidence, blockers)


def _execution_boundary_requirement(boundary: dict[str, Any]) -> dict[str, Any]:
    disabled_order_field = "live_" + "order_allowed"
    blockers: list[str] = []
    if bool(boundary.get(disabled_order_field, True)):
        blockers.append("disabled_order_boundary_enabled")
    if str(boundary.get("broker_connection", "")) != "disabled":
        blockers.append("broker_connection_enabled")
    if str(boundary.get("account_reads", "")) != "disabled":
        blockers.append("account_reads_enabled")
    if str(boundary.get("order_placement", "")) != "disabled":
        blockers.append("order_placement_enabled")
    if not bool(boundary.get("kill_switch_enabled", False)):
        blockers.append("kill_switch_disabled")
    evidence = (
        f"broker_connection={boundary.get('broker_connection')}, account_reads={boundary.get('account_reads')}, "
        f"order_placement={boundary.get('order_placement')}, disabled_order_boundary={boundary.get(disabled_order_field)}"
    )
    return _requirement("execution_boundary", "Execution boundary", "pass" if not blockers else "block", evidence, blockers)


def _candidate_paper_row(candidate: dict[str, Any], paper_observation: dict[str, Any]) -> dict[str, Any]:
    case_id = str(candidate.get("case_id", ""))
    rows = [row for row in paper_observation.get("candidates", []) if isinstance(row, dict)]
    for row in rows:
        if case_id and str(row.get("case_id")) == case_id:
            return row
    for row in rows:
        if row.get("status") == "completed" and row.get("observation_status") == "observed":
            return row
    return {}


def _observation_days(window: dict[str, Any]) -> int:
    start = _date(window.get("start_date"))
    end = _date(window.get("end_date"))
    if start is None or end is None:
        return 0
    return max(0, (end - start).days + 1)


def _date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _summary(requirements: list[dict[str, Any]], blockers: list[str]) -> dict[str, int]:
    return {
        "requirements": len(requirements),
        "passed": sum(1 for row in requirements if row.get("status") == "pass"),
        "warnings": sum(1 for row in requirements if row.get("status") == "warn"),
        "blocked": sum(1 for row in requirements if row.get("status") == "block"),
        "blockers": len(blockers),
    }


def _blockers(requirements: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in requirements:
        blockers.extend(_as_list(row.get("blockers")))
    return _dedupe(blockers)


def _requirement(requirement_id: str, label: str, status: str, evidence: str, blockers: list[str] | None = None) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "blockers": blockers or [],
    }


def _policy(value: SmallCapitalReviewPolicy | dict[str, Any] | None) -> SmallCapitalReviewPolicy:
    if isinstance(value, SmallCapitalReviewPolicy):
        return value
    if isinstance(value, dict):
        allowed = {field for field in SmallCapitalReviewPolicy.__dataclass_fields__}
        return SmallCapitalReviewPolicy(**{key: item for key, item in value.items() if key in allowed})
    return SmallCapitalReviewPolicy()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _safety() -> str:
    return "Research-to-paper-to-review only. No broker connection, no account reads, no order placement, no live trading."
