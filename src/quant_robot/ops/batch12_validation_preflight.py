from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "cn_stock_batch12_validation_preflight"
EXPECTED_NEXT_DIRECTION = "factor_validation_required_for_daily_champion_oos_candidates"
EXPECTED_VALIDATION_WINDOW = {"start": "2025-01-01", "end": "2025-12-31"}
VALIDATION_BRANCH_PREFIX = "codex/factor-validation-cn-stock-"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_CONTROLS = [
    "twenty_twenty_five_oos_only",
    "overlap_aware_return_statistics",
    "daily_vs_every2_every3_controls",
    "cost_capacity_turnover_stress",
    "cumulative_multiple_testing_accounting",
    "no_parameter_tuning_during_oos",
    "final_holdout_only_after_oos_clearance",
]
REQUIRED_OVERLAP_STATISTICS = [
    "naive_sharpe",
    "autocorr_adjusted_sharpe",
    "newey_west_standard_error_mean",
    "newey_west_t_stat_mean",
    "variance_inflation",
    "effective_sample_size",
    "autocorrelations",
    "overlap_risk_flag",
]


def build_batch12_validation_preflight(
    *,
    handoff: dict[str, Any],
    startup_gate: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    blockers = _blockers(handoff, startup_gate, request)
    final_holdout = _dict(handoff.get("final_holdout_window"))
    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "cleared" if not blockers else "blocked",
        "summary": {
            "machine": request.get("machine"),
            "task": request.get("task"),
            "branch": request.get("branch"),
            "current_branch": request.get("current_branch"),
            "market": request.get("market"),
            "asset_type": request.get("asset_type"),
            "source_discovery_report": handoff.get("source_discovery_report"),
            "prior_related_hypotheses": handoff.get("prior_related_hypotheses"),
        },
        "validation_window": _dict(handoff.get("validation_window")),
        "final_holdout_window": final_holdout,
        "final_holdout_allowed": bool(final_holdout.get("allowed_next", False)),
        "frozen_candidates": _list_of_dicts(handoff.get("frozen_candidates")),
        "required_controls": _list(handoff.get("required_controls")),
        "required_overlap_statistics": _list(handoff.get("required_overlap_statistics")),
        "decision": {
            "validation_preflight_cleared": not blockers,
            "blockers": blockers,
        },
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_batch12_validation_preflight_markdown(packet)
    return packet


def write_batch12_validation_preflight(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_packet = {key: value for key, value in packet.items() if key != "markdown"}
    (output_path / "batch12_validation_preflight.json").write_text(
        json.dumps(json_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "batch12_validation_preflight.md").write_text(
        str(packet.get("markdown", "")),
        encoding="utf-8",
    )


def validate_batch12_validation_preflight_packet(
    packet_path: str | Path | None,
    *,
    require_generated_today: bool = True,
    context: str = "CN stock Batch 12 validation",
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a validation preflight packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a validation preflight packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} preflight packet must be generated today: {path}")
    decision = _dict(packet.get("decision"))
    if packet.get("status") != "cleared" or decision.get("validation_preflight_cleared") is not True:
        raise ValueError(f"{context} preflight is not cleared: {path}")
    if _dict(packet.get("validation_window")) != EXPECTED_VALIDATION_WINDOW:
        raise ValueError(f"{context} preflight validation window mismatch: {path}")
    if packet.get("final_holdout_allowed") is not False:
        raise ValueError(f"{context} preflight allows final holdout too early: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} preflight violates live boundary: {path}")
    if len(_list_of_dicts(packet.get("frozen_candidates"))) != 2:
        raise ValueError(f"{context} preflight must freeze exactly two Batch 12 candidates: {path}")
    return packet


def render_batch12_validation_preflight_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# CN Stock Batch 12 Validation Preflight",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Machine: {summary.get('machine')}",
        f"- Task: {summary.get('task')}",
        f"- Branch: {summary.get('branch')}",
        f"- Current branch: {summary.get('current_branch')}",
        f"- Market: {summary.get('market')}",
        f"- Asset type: {summary.get('asset_type')}",
        f"- Validation window: {_dict(packet.get('validation_window')).get('start')} to {_dict(packet.get('validation_window')).get('end')}",
        f"- Final holdout allowed: {packet.get('final_holdout_allowed', False)}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        "",
        "## Frozen Candidates",
        "",
    ]
    for candidate in _list_of_dicts(packet.get("frozen_candidates")):
        lines.append(f"- {candidate.get('case_id')} cost_bps={candidate.get('cost_bps')}")
    lines.extend(["", "## Required Controls", ""])
    lines.extend(f"- {item}" for item in _list(packet.get("required_controls")))
    lines.extend(["", "## Required Overlap Statistics", ""])
    lines.extend(f"- {item}" for item in _list(packet.get("required_overlap_statistics")))
    lines.extend(["", "## Blockers", ""])
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(["", f"Safety: {packet.get('safety', SAFETY_TEXT)}", ""])
    return "\n".join(lines)


def _blockers(handoff: dict[str, Any], startup_gate: dict[str, Any], request: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    task = str(request.get("task", ""))
    branch = str(request.get("branch", ""))
    current_branch = str(request.get("current_branch", ""))

    if task != "factor_validation":
        blockers.append("task_not_factor_validation")
    if not branch.startswith(VALIDATION_BRANCH_PREFIX):
        blockers.append("branch_not_factor_validation")
    if current_branch and branch and current_branch != branch:
        blockers.append("current_branch_mismatch")
    if str(request.get("market", "")).upper() != "CN":
        blockers.append("market_scope_mismatch")
    if str(request.get("asset_type", "")).lower() != "stock":
        blockers.append("asset_type_scope_mismatch")
    if request.get("final_holdout_touched") is True:
        blockers.append("final_holdout_touched")

    if str(handoff.get("market", "")).upper() != "CN" or str(handoff.get("asset_type", "")).lower() != "stock":
        blockers.append("handoff_scope_mismatch")
    if _dict(handoff.get("validation_window")) != EXPECTED_VALIDATION_WINDOW:
        blockers.append("validation_window_not_2025_only")
    if _dict(handoff.get("final_holdout_window")).get("allowed_next") is not False:
        blockers.append("final_holdout_not_locked")
    if len(_list_of_dicts(handoff.get("frozen_candidates"))) != 2:
        blockers.append("frozen_candidate_count_mismatch")
    controls = set(_list(handoff.get("required_controls")))
    for control in REQUIRED_CONTROLS:
        if control not in controls:
            blockers.append(f"missing_required_control:{control}")
    overlap_statistics = set(_list(handoff.get("required_overlap_statistics")))
    for statistic in REQUIRED_OVERLAP_STATISTICS:
        if statistic not in overlap_statistics:
            blockers.append(f"missing_required_overlap_statistic:{statistic}")

    if startup_gate.get("status") != "cleared" or _dict(startup_gate.get("decision")).get("startup_gate_cleared") is not True:
        blockers.append("startup_gate_not_cleared")
    protocol = _dict(startup_gate.get("repeatable_mining_protocol"))
    if protocol.get("next_direction") != EXPECTED_NEXT_DIRECTION:
        blockers.append("startup_gate_next_direction_mismatch")
    if "batch12_validation_handoff_read" not in set(_list(protocol.get("confirm_before_each_run"))):
        blockers.append("startup_gate_missing_handoff_confirmation")
    if startup_gate.get("live_boundary_allowed") is not False:
        blockers.append("startup_gate_live_boundary_violation")
    return blockers


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
