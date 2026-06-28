from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.gui.control_center import SAFETY_NOTICE, build_control_center_snapshot


DEFAULT_OUTPUT_DIR = Path("data/reports/gui_control_center_audit")


def run_gui_control_center_audit(
    repo_root: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    snapshot = build_control_center_snapshot(repo_root=repo_root)
    scorecard = snapshot.get("audit_scorecard", {})
    summary = scorecard.get("summary", {})
    next_actions = _next_actions(scorecard, snapshot.get("audit_packets", {}))
    score = int(summary.get("local_self_check_score", 0) or 0)
    max_score = int(summary.get("max_score", 0) or 0)
    verdict = _verdict(scorecard)
    audit_iteration_plan = _audit_iteration_plan_for_packet(
        snapshot.get("audit_iteration_plan", {}),
        next_actions,
        score=score,
        max_score=max_score,
        verdict=verdict,
    )
    round_checkpoint_report = _round_checkpoint_report(
        snapshot,
        score=score,
        max_score=max_score,
        verdict=verdict,
        next_actions=next_actions,
        audit_iteration_plan=audit_iteration_plan,
    )
    packet = {
        "stage": "gui_control_center_independent_audit",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "score": score,
        "max_score": max_score,
        "verdict": verdict,
        "scorecard": {
            "summary": summary,
            "categories": scorecard.get("categories", []),
            "repair_queue": scorecard.get("repair_queue", []),
        },
        "audit_packets": snapshot.get("audit_packets", {}),
        "audit_iteration_plan": audit_iteration_plan,
        "round_checkpoint_report": round_checkpoint_report,
        "verification_gates": snapshot.get("verification_gates", []),
        "next_actions": next_actions,
        "safety": snapshot.get("safety", {"notice": SAFETY_NOTICE, "live_trading_allowed": False}),
    }
    _write_packet(Path(output_dir), packet)
    return packet


def _verdict(scorecard: dict[str, Any]) -> str:
    summary = scorecard.get("summary", {})
    if not summary.get("independent_audit_complete"):
        return "independent_audit_recorded_but_prior_packet_missing"
    if scorecard.get("repair_queue"):
        return "needs_repair"
    return "clear"


def _next_actions(scorecard: dict[str, Any], audit_packets: dict[str, Any]) -> list[dict[str, Any]]:
    actions = [
        {
            "priority": item.get("priority", "P2"),
            "action": item.get("action", ""),
            "reason": item.get("reason", ""),
        }
        for item in scorecard.get("repair_queue", [])
    ]
    missing_packets = [
        row for row in audit_packets.get("rows", []) if row.get("required") and row.get("status") != "present"
    ]
    actions.extend(
        {
            "priority": "P1",
            "action": f"Generate {row.get('label', row.get('packet_id', 'audit packet'))}",
            "reason": row.get("command", ""),
        }
        for row in missing_packets
    )
    return actions


def _audit_iteration_plan_for_packet(
    audit_iteration_plan: dict[str, Any],
    next_actions: list[dict[str, Any]],
    *,
    score: int,
    max_score: int,
    verdict: str,
) -> dict[str, Any]:
    if next_actions or not isinstance(audit_iteration_plan, dict):
        normalized = dict(audit_iteration_plan)
        summary = dict(normalized.get("summary", {}))
        summary.update({"audit_score": score, "max_score": max_score, "verdict": verdict})
        normalized["summary"] = summary
        return normalized
    rows = [
        row
        for row in audit_iteration_plan.get("rows", [])
        if isinstance(row, dict) and row.get("status") == "blocked_expected"
    ]
    summary = dict(audit_iteration_plan.get("summary", {}))
    summary.update(
        {
            "active_actions": 0,
            "audit_score": score,
            "max_score": max_score,
            "verdict": verdict,
            "blocked_expected": len(rows),
            "next_action": rows[0].get("action", "No audit repair actions queued") if rows else "No audit repair actions queued",
        }
    )
    normalized = dict(audit_iteration_plan)
    normalized["summary"] = summary
    normalized["rows"] = rows
    return normalized


def _round_checkpoint_report(
    snapshot: dict[str, Any],
    *,
    score: int,
    max_score: int,
    verdict: str,
    next_actions: list[dict[str, Any]],
    audit_iteration_plan: dict[str, Any],
) -> dict[str, Any]:
    operation_ledger = snapshot.get("operation_ledger", {})
    ledger_summary = operation_ledger.get("summary", {}) if isinstance(operation_ledger, dict) else {}
    scheduler_summary = (snapshot.get("audit_scheduler", {}) or {}).get("summary", {})
    recent_work = [
        _round_work_item(row)
        for row in (operation_ledger.get("rows", []) if isinstance(operation_ledger, dict) else [])[:5]
        if isinstance(row, dict)
    ]
    cadence_rounds = int(scheduler_summary.get("cadence_rounds") or 5)
    current_round = int(scheduler_summary.get("current_round") or ledger_summary.get("entry_count") or 0)
    flow_plan = _round_flow_plan(
        next_actions,
        audit_iteration_plan,
        snapshot.get("verification_gates", []),
    )
    return {
        "stage": "gui_round_checkpoint_report",
        "summary": {
            "status": "ready",
            "current_round": current_round,
            "completed_rounds": len(recent_work),
            "cadence_rounds": cadence_rounds,
            "rounds_until_next_audit": scheduler_summary.get("rounds_until_next_audit"),
            "next_review_trigger": f"Every {cadence_rounds} completed GUI rounds; fallback every 5 hours.",
            "audit_score": score,
            "max_score": max_score,
            "verdict": verdict,
            "repair_action_count": len(next_actions),
            "live_trading_allowed": False,
        },
        "recent_work": recent_work,
        "flow_plan": flow_plan,
        "safety": snapshot.get("safety", {"notice": SAFETY_NOTICE, "live_trading_allowed": False}),
    }


def _round_work_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": str(row.get("operation_id") or ""),
        "recorded_at": str(row.get("recorded_at") or ""),
        "workflow_id": str(row.get("workflow_id") or ""),
        "label": str(row.get("label") or row.get("workflow_id") or ""),
        "status": str(row.get("status") or ""),
        "request_summary": str(row.get("request_summary") or ""),
        "metric_summary": str(row.get("metric_summary") or ""),
        "command": str(row.get("command") or ""),
    }


def _round_flow_plan(
    next_actions: list[dict[str, Any]],
    audit_iteration_plan: dict[str, Any],
    verification_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    if next_actions:
        next_steps = [
            {
                "priority": str(item.get("priority") or "P2"),
                "action": str(item.get("action") or "Review audit action"),
                "reason": str(item.get("reason") or ""),
                "verification": _verification_for_action(item, audit_iteration_plan, verification_gates),
            }
            for item in next_actions[:5]
            if isinstance(item, dict)
        ]
    else:
        next_steps = [
            {
                "priority": "P1",
                "action": "Continue the next GUI optimization round from the largest remaining operator blind spot.",
                "reason": "The latest audit is clear; keep improving observability, safety gates, and workflow clarity.",
                "verification": "python -m unittest -v tests.unit.test_gui",
            },
            {
                "priority": "P2",
                "action": "Generate the next five-round checkpoint report after five more completed GUI rounds.",
                "reason": "The objective requires an audit report and next flow plan every five rounds.",
                "verification": "python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
            },
        ]
    return {
        "status": "ready",
        "next_steps": next_steps,
        "verification_plan": [
            {
                "gate_id": str(item.get("gate_id") or ""),
                "label": str(item.get("label") or ""),
                "command": str(item.get("command") or ""),
            }
            for item in verification_gates[:5]
            if isinstance(item, dict)
        ],
        "safety": SAFETY_NOTICE,
    }


def _verification_for_action(
    action: dict[str, Any],
    audit_iteration_plan: dict[str, Any],
    verification_gates: list[dict[str, Any]],
) -> str:
    action_name = str(action.get("action") or "")
    rows = audit_iteration_plan.get("rows", []) if isinstance(audit_iteration_plan, dict) else []
    for row in rows:
        if isinstance(row, dict) and str(row.get("action") or "") == action_name:
            return str(row.get("verification_command") or "")
    for gate in verification_gates:
        if isinstance(gate, dict) and gate.get("gate_id") == "gui_unit_tests":
            return str(gate.get("command") or "python -m unittest -v tests.unit.test_gui")
    return "python -m unittest -v tests.unit.test_gui"


def _write_packet(output_dir: Path, packet: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gui_control_center_audit.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "gui_control_center_audit.md").write_text(_render_markdown(packet), encoding="utf-8")


def _render_markdown(packet: dict[str, Any]) -> str:
    safety = packet.get("safety", {})
    rows = [
        "# GUI Control Center Independent Audit",
        "",
        f"- Generated at: {packet.get('generated_at', '')}",
        f"- Score: {packet.get('score', 0)} / {packet.get('max_score', 0)}",
        f"- Verdict: {packet.get('verdict', '')}",
        f"- Safety: {safety.get('notice', SAFETY_NOTICE)}",
        "",
        "## Category Scores",
    ]
    for category in packet.get("scorecard", {}).get("categories", []):
        rows.append(
            f"- {category.get('label', category.get('category_id', 'category'))}: "
            f"{category.get('score', 0)} / {category.get('max_score', 0)} "
            f"({category.get('status', '')})"
        )
    iteration_plan = packet.get("audit_iteration_plan", {})
    iteration_summary = iteration_plan.get("summary", {}) if isinstance(iteration_plan, dict) else {}
    rows.extend(
        [
            "",
            "## Audit Iteration Plan",
            f"- Source: {iteration_summary.get('source', '')}",
            f"- Active actions: {iteration_summary.get('active_actions', 0)}",
            f"- Blocked expected: {iteration_summary.get('blocked_expected', 0)}",
        ]
    )
    iteration_rows = iteration_plan.get("rows", []) if isinstance(iteration_plan, dict) else []
    for item in iteration_rows:
        rows.append(
            f"- [{item.get('priority', 'P2')}] {item.get('action', '')}: "
            f"{item.get('status', '')}; verify with {item.get('verification_command', '')}"
        )
    checkpoint = packet.get("round_checkpoint_report", {})
    checkpoint_summary = checkpoint.get("summary", {}) if isinstance(checkpoint, dict) else {}
    rows.extend(
        [
            "",
            "## Five-Round Checkpoint Report",
            f"- Current round: {checkpoint_summary.get('current_round', 0)}",
            f"- Completed rounds summarized: {checkpoint_summary.get('completed_rounds', 0)}",
            f"- Cadence: every {checkpoint_summary.get('cadence_rounds', 5)} GUI rounds",
            f"- Verdict: {checkpoint_summary.get('verdict', '')}",
            "",
            "### Recent GUI Work",
        ]
    )
    for item in checkpoint.get("recent_work", [])[:5] if isinstance(checkpoint, dict) else []:
        rows.append(
            f"- {item.get('recorded_at', '')} / {item.get('workflow_id', '')} / "
            f"{item.get('status', '')}: {item.get('request_summary', '') or item.get('metric_summary', '')}"
        )
    flow_plan = checkpoint.get("flow_plan", {}) if isinstance(checkpoint, dict) else {}
    rows.extend(["", "### Next Flow Plan"])
    for item in flow_plan.get("next_steps", []):
        rows.append(
            f"- [{item.get('priority', 'P2')}] {item.get('action', '')}: "
            f"{item.get('reason', '')}; verify with {item.get('verification', '')}"
        )
    rows.extend(["", "## Next Actions"])
    actions = packet.get("next_actions", [])
    if not actions:
        rows.append("- No repair actions recorded.")
    for action in actions:
        rows.append(f"- [{action.get('priority', 'P2')}] {action.get('action', '')}: {action.get('reason', '')}")
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local GUI control center audit packet.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    packet = run_gui_control_center_audit(repo_root=args.repo_root, output_dir=args.output_dir)
    print(json.dumps(packet, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
