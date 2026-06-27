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
    packet = {
        "stage": "gui_control_center_independent_audit",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "score": int(summary.get("local_self_check_score", 0) or 0),
        "max_score": int(summary.get("max_score", 0) or 0),
        "verdict": _verdict(scorecard),
        "scorecard": {
            "summary": summary,
            "categories": scorecard.get("categories", []),
            "repair_queue": scorecard.get("repair_queue", []),
        },
        "audit_packets": snapshot.get("audit_packets", {}),
        "verification_gates": snapshot.get("verification_gates", []),
        "next_actions": _next_actions(scorecard, snapshot.get("audit_packets", {})),
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
