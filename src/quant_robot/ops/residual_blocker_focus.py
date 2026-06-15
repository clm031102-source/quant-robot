from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_13_residual_blocker_focus_pack"

_RELATED_TRACKS = {
    "data_gap_resolution": ["data_gap_resolution", "data_quality"],
    "provider_remediation": ["provider_remediation", "provider_readiness"],
}

_DOWNSTREAM_KEYWORDS = {
    "data_gap_resolution": ("data_gap", "data_quality", "missing_date", "missing_dates"),
    "provider_remediation": ("provider", "providers_not_ready", "provider_readiness"),
}


def build_residual_blocker_focus_pack(
    readiness_projection: dict[str, Any],
    blocker_worklist: dict[str, Any],
) -> dict[str, Any]:
    residual_rows = _open_residual_rows(readiness_projection.get("residual_rows", []))
    projection_items = _projection_items_by_track(readiness_projection.get("projection_items", []))
    work_items = _list_of_dicts(blocker_worklist.get("work_items", []))
    action_queue = _list_of_dicts(blocker_worklist.get("action_queue", []))
    focus_items = _focus_items(residual_rows, projection_items, work_items)
    focus_actions = _focus_actions(focus_items, action_queue)
    downstream_waits = _downstream_waits(focus_items, work_items, projection_items)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": readiness_projection.get("stage"),
        "worklist_stage": blocker_worklist.get("stage"),
        "safety": _research_only_safety(),
        "boundary": _boundary(readiness_projection, blocker_worklist),
        "summary": _summary(focus_items, focus_actions, downstream_waits),
        "focus_items": focus_items,
        "downstream_waits": downstream_waits,
        "action_queue": focus_actions,
    }
    pack["markdown"] = render_residual_blocker_focus_markdown(pack)
    return pack


def write_residual_blocker_focus_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "residual_blocker_focus_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "residual_blocker_focus_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("focus_items", [])).to_csv(output_path / "residual_focus_items.csv", index=False)
    pd.DataFrame(pack.get("downstream_waits", [])).to_csv(output_path / "residual_downstream_waits.csv", index=False)
    pd.DataFrame(pack.get("action_queue", [])).to_csv(output_path / "residual_focus_actions.csv", index=False)


def render_residual_blocker_focus_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    boundary = pack.get("boundary", {}) if isinstance(pack.get("boundary"), dict) else {}
    lines = [
        "# Residual Blocker Focus Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Root focus items: {summary.get('root_focus_items', 0)}",
        f"- Residual blockers: {summary.get('residual_blockers', 0)}",
        f"- Downstream waits: {summary.get('downstream_waits', 0)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        f"- Live boundary crossed: {boundary.get('would_cross_live_boundary', False)}",
        "",
        "## Focus Items",
        "",
        "| Priority | Track | Remaining | Evidence | Commands |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in pack.get("focus_items", []):
        if isinstance(item, dict):
            lines.append(
                "| "
                f"{item.get('priority_rank', '')} | "
                f"{item.get('track_id', '')} | "
                f"{item.get('remaining_blockers', 0)} | "
                f"{_table_text(item.get('projected_evidence', ''))} | "
                f"{_table_text('; '.join(item.get('primary_commands', [])))} |"
            )
    lines.extend(["", "## Downstream Waits", ""])
    if pack.get("downstream_waits"):
        for wait in pack.get("downstream_waits", []):
            if isinstance(wait, dict):
                tracks = ", ".join(wait.get("blocked_by_tracks", []))
                blockers = ", ".join(wait.get("blocker_ids", []))
                lines.append(f"- `{wait.get('track_id')}` waits on {tracks}: {blockers}")
    else:
        lines.append("- none")
    lines.extend(["", "## Focus Action Queue", ""])
    if pack.get("action_queue"):
        for action in pack.get("action_queue", []):
            if isinstance(action, dict):
                lines.append(f"{action.get('priority')}. `{action.get('command')}`")
                lines.append(f"   - {action.get('reason', '')}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _focus_items(
    residual_rows: list[dict[str, Any]],
    projection_items: dict[str, dict[str, Any]],
    work_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    indexed = list(enumerate(residual_rows))
    ordered = sorted(indexed, key=lambda row: (-_int(row[1].get("remaining_blockers"), 0), row[0]))
    rows = []
    for rank, (_, residual) in enumerate(ordered, start=1):
        track_id = str(residual.get("track_id", "unknown"))
        projection = projection_items.get(track_id, {})
        related_tracks = _related_tracks(track_id)
        linked_items = [item for item in work_items if str(item.get("track_id")) in related_tracks]
        downstream_blocker_ids = _downstream_blocker_ids(track_id, work_items)
        rows.append(
            {
                "focus_id": f"FB-{rank:03d}",
                "priority_rank": rank,
                "track_id": track_id,
                "label": projection.get("label", track_id),
                "remaining_blockers": _int(residual.get("remaining_blockers"), 0),
                "projected_status": residual.get("projected_status", projection.get("projected_status", "unknown")),
                "projected_evidence": projection.get("projected_evidence", ""),
                "current_status": projection.get("current_status", "unknown"),
                "current_evidence": projection.get("current_evidence", ""),
                "source_stage": residual.get("source_stage", ""),
                "related_tracks": related_tracks,
                "linked_work_item_ids": _unique_str(item.get("work_item_id") for item in linked_items),
                "blocker_ids": _unique_str(item.get("blocker_id") for item in linked_items),
                "primary_commands": _unique_str(item.get("primary_command") for item in linked_items if item.get("primary_command")),
                "downstream_blocker_ids": downstream_blocker_ids,
                "local_only": True,
            }
        )
    return rows


def _focus_actions(focus_items: list[dict[str, Any]], action_queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for focus in focus_items:
        focus_track = str(focus.get("track_id", ""))
        related_tracks = set(focus.get("related_tracks", [focus_track]))
        for action in sorted(action_queue, key=lambda row: _int(row.get("priority"), 999999)):
            command = str(action.get("command", ""))
            if not command or command in seen:
                continue
            if str(action.get("track_id")) not in related_tracks:
                continue
            seen.add(command)
            rows.append(
                {
                    "priority": len(rows) + 1,
                    "source_priority": _int(action.get("priority"), len(rows) + 1),
                    "track_id": action.get("track_id", ""),
                    "focus_track_id": focus_track,
                    "command": command,
                    "reason": action.get("reason", ""),
                    "local_only": True,
                }
            )
    return rows


def _downstream_waits(
    focus_items: list[dict[str, Any]],
    work_items: list[dict[str, Any]],
    projection_items: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    manual_blockers_by_track: dict[str, list[str]] = {}
    for focus in focus_items:
        track_id = str(focus.get("track_id", ""))
        blocker_ids = _downstream_blocker_ids(track_id, work_items)
        if blocker_ids:
            manual_blockers_by_track[track_id] = blocker_ids
    if not manual_blockers_by_track:
        return []
    manual_projection = projection_items.get("manual_review_gate", {})
    all_blockers = []
    for blocker_ids in manual_blockers_by_track.values():
        all_blockers.extend(blocker_ids)
    return [
        {
            "track_id": "manual_review_gate",
            "blocked_by_tracks": list(manual_blockers_by_track.keys()),
            "blocker_ids": _unique_str(all_blockers),
            "evidence": manual_projection.get("projected_evidence", manual_projection.get("current_evidence", "")),
            "local_only": True,
        }
    ]


def _downstream_blocker_ids(track_id: str, work_items: list[dict[str, Any]]) -> list[str]:
    keywords = _DOWNSTREAM_KEYWORDS.get(track_id, ())
    if not keywords:
        return []
    rows = []
    for item in work_items:
        if str(item.get("track_id")) != "manual_review_gate":
            continue
        text = f"{item.get('blocker_id', '')} {item.get('evidence', '')}".lower()
        if any(keyword in text for keyword in keywords):
            rows.append(str(item.get("blocker_id", "")))
    return _unique_str(rows)


def _open_residual_rows(value: Any) -> list[dict[str, Any]]:
    rows = []
    for row in _list_of_dicts(value):
        remaining = _int(row.get("remaining_blockers"), 0)
        if remaining <= 0:
            continue
        copied = dict(row)
        copied["remaining_blockers"] = remaining
        rows.append(copied)
    return rows


def _projection_items_by_track(value: Any) -> dict[str, dict[str, Any]]:
    return {str(row.get("track_id", "")): row for row in _list_of_dicts(value) if row.get("track_id")}


def _related_tracks(track_id: str) -> list[str]:
    return list(_RELATED_TRACKS.get(track_id, [track_id]))


def _summary(
    focus_items: list[dict[str, Any]],
    focus_actions: list[dict[str, Any]],
    downstream_waits: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "root_focus_items": len(focus_items),
        "residual_blockers": sum(_int(item.get("remaining_blockers"), 0) for item in focus_items),
        "downstream_waits": len(downstream_waits),
        "action_queue": len(focus_actions),
        "highest_priority_track": focus_items[0].get("track_id") if focus_items else None,
    }


def _boundary(readiness_projection: dict[str, Any], blocker_worklist: dict[str, Any]) -> dict[str, Any]:
    source = readiness_projection.get("boundary") if isinstance(readiness_projection.get("boundary"), dict) else {}
    fallback = blocker_worklist.get("boundary") if isinstance(blocker_worklist.get("boundary"), dict) else {}
    return {
        "would_cross_live_boundary": bool(source.get("would_cross_live_boundary", fallback.get("would_cross_live_boundary", False))),
        "broker_connection": source.get("broker_connection", fallback.get("broker_connection", "disabled")),
        "account_reads": source.get("account_reads", fallback.get("account_reads", "disabled")),
        "order_placement": source.get("order_placement", fallback.get("order_placement", "disabled")),
        "live_trading": source.get("live_trading", fallback.get("live_trading", "disabled")),
    }


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _unique_str(values: Any) -> list[str]:
    rows = []
    seen = set()
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Focus artifacts only; No broker connection, no account reads, no order placement, no live trading."
