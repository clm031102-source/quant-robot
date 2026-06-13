from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_1_blocker_resolution_worklist"


def build_blocker_worklist(readiness_board: dict[str, Any]) -> dict[str, Any]:
    blockers = [row for row in readiness_board.get("blocker_register", []) if isinstance(row, dict)]
    actions = _action_queue(readiness_board.get("next_local_actions", []))
    work_items = [_work_item(index + 1, blocker, actions) for index, blocker in enumerate(blockers)]
    worklist = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": readiness_board.get("stage"),
        "source_status": readiness_board.get("overall_status"),
        "safety": _research_only_safety(),
        "selected_candidate": readiness_board.get("selected_candidate"),
        "boundary": _boundary(readiness_board),
        "summary": _summary(work_items, actions),
        "work_items": work_items,
        "action_queue": actions,
    }
    worklist["markdown"] = render_blocker_worklist_markdown(worklist)
    return worklist


def write_blocker_worklist(output_dir: str | Path, worklist: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "blocker_resolution_worklist.json").write_text(
        json.dumps(worklist, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "blocker_resolution_worklist.md").write_text(str(worklist.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(worklist.get("work_items", [])).to_csv(output_path / "blocker_work_items.csv", index=False)
    pd.DataFrame(worklist.get("action_queue", [])).to_csv(output_path / "blocker_action_queue.csv", index=False)


def render_blocker_worklist_markdown(worklist: dict[str, Any]) -> str:
    summary = worklist.get("summary", {}) if isinstance(worklist.get("summary"), dict) else {}
    boundary = worklist.get("boundary", {}) if isinstance(worklist.get("boundary"), dict) else {}
    lines = [
        "# Blocker Resolution Worklist",
        "",
        f"- Stage: {worklist.get('stage', STAGE)}",
        f"- Source status: {worklist.get('source_status', 'unknown')}",
        f"- Open work items: {summary.get('open_work_items', 0)}",
        f"- Safety: {worklist.get('safety', _research_only_safety())}",
        f"- Live boundary crossed: {boundary.get('would_cross_live_boundary', False)}",
        "",
        "## Work Items",
        "",
        "| ID | Track | Blocker | Status | Primary Command |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in worklist.get("work_items", []):
        if isinstance(item, dict):
            lines.append(
                "| "
                f"{item.get('work_item_id', '')} | "
                f"{item.get('track_id', 'unknown')} | "
                f"{item.get('blocker_id', 'unknown')} | "
                f"{item.get('work_status', 'unknown')} | "
                f"`{item.get('primary_command', '')}` |"
            )
    lines.extend(["", "## Action Queue", ""])
    for action in worklist.get("action_queue", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not worklist.get("action_queue"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _work_item(index: int, blocker: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    track_id = str(blocker.get("track_id", "unknown"))
    command = _primary_command(track_id, blocker, actions)
    return {
        "work_item_id": f"WI-{index:03d}",
        "work_status": "open",
        "track_id": track_id,
        "blocker_id": str(blocker.get("blocker_id", "unknown")),
        "severity": blocker.get("severity", "block"),
        "evidence": blocker.get("evidence", ""),
        "primary_command": command,
        "local_only": True,
    }


def _action_queue(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = []
    seen = set()
    for index, action in enumerate(value, start=1):
        if not isinstance(action, dict):
            continue
        command = str(action.get("command", ""))
        if not command or command in seen:
            continue
        seen.add(command)
        rows.append(
            {
                "priority": _int(action.get("priority"), index),
                "track_id": action.get("track_id"),
                "command": command,
                "reason": action.get("reason", ""),
                "local_only": True,
            }
        )
    return sorted(rows, key=lambda row: _int(row.get("priority"), 999999))


def _primary_command(track_id: str, blocker: dict[str, Any], actions: list[dict[str, Any]]) -> str:
    for action in actions:
        if str(action.get("track_id")) == track_id and action.get("command"):
            return str(action["command"])
    if blocker.get("recommended_command"):
        return str(blocker["recommended_command"])
    return "python scripts\\run_checks.py --execute"


def _summary(work_items: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "work_items": len(work_items),
        "open_work_items": sum(1 for item in work_items if item.get("work_status") == "open"),
        "action_queue": len(actions),
    }


def _boundary(readiness_board: dict[str, Any]) -> dict[str, Any]:
    boundary = readiness_board.get("boundary", {}) if isinstance(readiness_board.get("boundary"), dict) else {}
    return {
        "would_cross_live_boundary": bool(boundary.get("would_cross_live_boundary", False)),
        "broker_connection": boundary.get("broker_connection", "disabled"),
        "account_reads": boundary.get("account_reads", "disabled"),
        "order_placement": boundary.get("order_placement", "disabled"),
        "live_trading": boundary.get("live_trading", "disabled"),
    }


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
