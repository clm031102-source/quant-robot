from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "factor_batch_readiness_gate"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_factor_batch_readiness_gate(
    *,
    source_queue_packet: dict[str, Any],
    candidate_plan_gate_packet: dict[str, Any],
    candidate_plan_path: str | Path,
    source_queue_output_dir: str | Path,
    candidate_plan_gate_output_dir: str | Path,
    provider_quota_preflight_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_decision = _dict(source_queue_packet.get("decision"))
    candidate_decision = _dict(candidate_plan_gate_packet.get("decision"))
    quota_packet = _dict(provider_quota_preflight_packet)
    quota_decision = _dict(quota_packet.get("decision"))
    source_status = str(source_decision.get("status", source_queue_packet.get("status", "unknown")))
    candidate_status = str(candidate_plan_gate_packet.get("status", "unknown"))
    blockers = _blockers(
        source_decision=source_decision,
        candidate_decision=candidate_decision,
        provider_quota_decision=quota_decision,
        provider_quota_provided=bool(quota_packet),
    )
    source_next_action = str(source_decision.get("next_action", ""))
    source_local_prescreen_next_action = str(source_decision.get("local_prescreen_next_action", ""))
    ready = not blockers
    next_action = _next_action(
        ready=ready,
        provider_quota_decision=quota_decision,
        provider_quota_provided=bool(quota_packet),
        source_next_action=source_next_action,
        source_local_prescreen_next_action=source_local_prescreen_next_action,
    )
    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "ready" if ready else "blocked",
        "candidate_plan_path": str(candidate_plan_path),
        "source_queue_output_dir": str(source_queue_output_dir),
        "candidate_plan_gate_output_dir": str(candidate_plan_gate_output_dir),
        "summary": {
            "source_queue_status": source_status,
            "candidate_plan_gate_status": candidate_status,
            "provider_quota_preflight_status": _provider_quota_preflight_status(
                quota_decision,
                provided=bool(quota_packet),
            ),
            "source_queue_active_source_count": _int(
                _dict(source_queue_packet.get("summary")).get("active_source_count")
            ),
            "source_queue_source_count": _int(_dict(source_queue_packet.get("summary")).get("source_count")),
            "source_queue_no_provider_ready_source_count": _int(
                _dict(source_queue_packet.get("summary")).get("no_provider_ready_source_count")
            ),
            "source_queue_hibernated_or_closed_source_count": _int(
                _dict(source_queue_packet.get("summary")).get("hibernated_or_closed_source_count")
            ),
            "candidate_count": _int(_dict(candidate_plan_gate_packet.get("summary")).get("candidate_count")),
        },
        "decision": {
            "factor_batch_ready": ready,
            "research_screen_allowed": ready and candidate_decision.get("research_screen_allowed") is True,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "next_action": next_action,
            "blockers": blockers,
        },
        "source_queue_decision": source_decision,
        "candidate_plan_gate_decision": candidate_decision,
        "provider_quota_preflight_decision": quota_decision,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    packet["markdown"] = render_factor_batch_readiness_gate_markdown(packet)
    return packet


def write_factor_batch_readiness_gate(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(packet)
    (output_path / "factor_batch_readiness_gate.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_batch_readiness_gate.md").write_text(
        render_factor_batch_readiness_gate_markdown(clean),
        encoding="utf-8",
    )


def validate_factor_batch_readiness_gate_packet(
    packet_path: str | Path | None,
    *,
    require_generated_today: bool = True,
    context: str = "CN stock factor batch",
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a factor batch readiness gate packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a factor batch readiness gate packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} factor batch readiness gate must be generated today: {path}")
    decision = _dict(packet.get("decision"))
    if packet.get("status") != "ready" or decision.get("factor_batch_ready") is not True:
        raise ValueError(f"{context} factor batch readiness gate is not ready: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} factor batch readiness gate violates live boundary: {path}")
    return packet


def render_factor_batch_readiness_gate_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# Factor Batch Readiness Gate",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Candidate plan: `{packet.get('candidate_plan_path', '')}`",
        f"- Source queue status: {summary.get('source_queue_status', 'unknown')}",
        f"- Candidate plan gate status: {summary.get('candidate_plan_gate_status', 'unknown')}",
        f"- Provider quota preflight status: {summary.get('provider_quota_preflight_status', 'not_provided')}",
        f"- Factor batch ready: {decision.get('factor_batch_ready', False)}",
        f"- Research screen allowed: {decision.get('research_screen_allowed', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next action: `{decision.get('next_action', '')}`",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    return "\n".join(lines) + "\n"


def _blockers(
    *,
    source_decision: dict[str, Any],
    candidate_decision: dict[str, Any],
    provider_quota_decision: dict[str, Any],
    provider_quota_provided: bool,
) -> list[str]:
    blockers: list[str] = []
    if provider_quota_provided and provider_quota_decision.get("request_allowed") is not True:
        quota_blockers = _list(provider_quota_decision.get("blockers"))
        if quota_blockers:
            blockers.extend(f"provider_quota_preflight_blocked:{blocker}" for blocker in quota_blockers)
        else:
            blockers.append("provider_quota_preflight_blocked")
    if source_decision.get("status") != "cleared":
        source_blockers = _list(source_decision.get("blockers"))
        if source_blockers:
            blockers.extend(f"source_queue_blocked:{blocker}" for blocker in source_blockers)
        else:
            blockers.append("source_queue_not_cleared")
    if candidate_decision.get("candidate_plan_gate_cleared") is not True:
        candidate_blockers = _list(candidate_decision.get("blockers"))
        if candidate_blockers:
            blockers.extend(f"candidate_plan_gate_blocked:{blocker}" for blocker in candidate_blockers)
        else:
            blockers.append("candidate_plan_gate_not_cleared")
    return _unique_preserving_order(blockers)


def _provider_quota_preflight_status(decision: dict[str, Any], *, provided: bool) -> str:
    if not provided:
        return "not_provided"
    return "allowed" if decision.get("request_allowed") is True else "blocked"


def _next_action(
    *,
    ready: bool,
    provider_quota_decision: dict[str, Any],
    provider_quota_provided: bool,
    source_next_action: str,
    source_local_prescreen_next_action: str = "",
) -> str:
    if ready:
        return "run_frozen_candidate_prescreen"
    if provider_quota_provided and provider_quota_decision.get("request_allowed") is not True:
        quota_blockers = _list(provider_quota_decision.get("blockers"))
        if (
            "daily_provider_request_budget_exhausted" in quota_blockers
            and source_local_prescreen_next_action.startswith("local_prescreen_current_")
        ):
            return source_local_prescreen_next_action
        quota_next_action = str(provider_quota_decision.get("next_action", "")).strip()
        if quota_next_action:
            return quota_next_action
    return source_next_action or "review_factor_batch_readiness_blockers"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


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
