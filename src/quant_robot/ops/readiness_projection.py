from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_12_pre_api_readiness_projection_pack"


def build_readiness_projection_pack(
    readiness_board: dict[str, Any],
    data_gap_rehearsal: dict[str, Any] | None = None,
    provider_remediation_rehearsal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delta_rows = _delta_rows(data_gap_rehearsal, provider_remediation_rehearsal)
    residual_rows = _residual_rows(delta_rows)
    projections = _projection_by_track(data_gap_rehearsal, provider_remediation_rehearsal)
    items = _projection_items(readiness_board, projections)
    summary = _summary(readiness_board, items, delta_rows)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": readiness_board.get("stage"),
        "safety": _research_only_safety(),
        "summary": summary,
        "boundary": _boundary(readiness_board),
        "projection_items": items,
        "delta_rows": delta_rows,
        "residual_rows": residual_rows,
    }
    pack["markdown"] = render_readiness_projection_markdown(pack)
    return pack


def write_readiness_projection_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "readiness_projection_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "readiness_projection_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("projection_items", [])).to_csv(output_path / "readiness_projection_items.csv", index=False)
    pd.DataFrame(pack.get("delta_rows", [])).to_csv(output_path / "readiness_projection_deltas.csv", index=False)
    pd.DataFrame(pack.get("residual_rows", [])).to_csv(output_path / "readiness_projection_residuals.csv", index=False)


def render_readiness_projection_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Pre-API Readiness Projection Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        f"- Current blockers: {summary.get('current_blockers', 0)}",
        f"- Projected blocked items: {summary.get('projected_blocked_items', 0)}",
        f"- total rehearsal delta: {summary.get('total_rehearsal_delta', 0)}",
        "",
        "## Projection Items",
        "",
        "| Track | Current | Projected | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for item in pack.get("projection_items", []):
        if isinstance(item, dict):
            lines.append(
                "| "
                f"{item.get('track_id', '')} | "
                f"{item.get('current_status', '')} | "
                f"{item.get('projected_status', '')} | "
                f"{_table_text(item.get('projected_evidence', ''))} |"
            )
    lines.extend(["", "## Rehearsal Deltas", ""])
    for row in pack.get("delta_rows", []):
        if isinstance(row, dict):
            lines.append(f"- `{row.get('track_id')}`: {row.get('before_blockers')} -> {row.get('after_blockers')} ({row.get('blocker_delta')})")
    if not pack.get("delta_rows"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _projection_items(readiness_board: dict[str, Any], projections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in readiness_board.get("readiness_items", []):
        if not isinstance(item, dict):
            continue
        track_id = str(item.get("track_id", ""))
        projection = projections.get(track_id, {})
        projected_status = str(projection.get("status", item.get("status", "unknown")))
        projected_evidence = str(projection.get("evidence", item.get("evidence", "")))
        rows.append(
            {
                "track_id": track_id,
                "label": item.get("label", track_id),
                "current_status": item.get("status", "unknown"),
                "projected_status": projected_status,
                "current_evidence": item.get("evidence", ""),
                "projected_evidence": projected_evidence,
                "projection_source": projection.get("source_stage", "current_board"),
                "status_changed": item.get("status") != projected_status,
                "local_only": True,
            }
        )
    return rows


def _projection_by_track(
    data_gap_rehearsal: dict[str, Any] | None,
    provider_remediation_rehearsal: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    projections = {}
    for source in [data_gap_rehearsal, provider_remediation_rehearsal]:
        if not isinstance(source, dict):
            continue
        projection = source.get("readiness_projection", {})
        if not isinstance(projection, dict) or not projection.get("track_id"):
            continue
        row = dict(projection)
        row["source_stage"] = source.get("stage")
        projections[str(projection["track_id"])] = row
    return projections


def _delta_rows(
    data_gap_rehearsal: dict[str, Any] | None,
    provider_remediation_rehearsal: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows = []
    data_gap_summary = data_gap_rehearsal.get("summary", {}) if isinstance(data_gap_rehearsal, dict) else {}
    if data_gap_summary:
        rows.append(
            {
                "track_id": "data_gap_resolution",
                "source_stage": data_gap_rehearsal.get("stage") if isinstance(data_gap_rehearsal, dict) else "",
                "before_blockers": _int(data_gap_summary.get("source_blocking_gap_rows"), 0),
                "after_blockers": _int(data_gap_summary.get("rehearsed_blocking_gap_rows"), 0),
                "blocker_delta": _int(data_gap_summary.get("blocker_delta"), 0),
                "local_only": True,
            }
        )
    provider_summary = provider_remediation_rehearsal.get("summary", {}) if isinstance(provider_remediation_rehearsal, dict) else {}
    if provider_summary:
        rows.append(
            {
                "track_id": "provider_remediation",
                "source_stage": provider_remediation_rehearsal.get("stage") if isinstance(provider_remediation_rehearsal, dict) else "",
                "before_blockers": _int(provider_summary.get("source_blocking_remediation_items"), 0),
                "after_blockers": _int(provider_summary.get("rehearsed_blocking_remediation_items"), 0),
                "blocker_delta": _int(provider_summary.get("blocker_delta"), 0),
                "local_only": True,
            }
        )
    return rows


def _residual_rows(delta_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in delta_rows:
        remaining = _int(row.get("after_blockers"), 0)
        rows.append(
            {
                "track_id": row.get("track_id", ""),
                "remaining_blockers": remaining,
                "projected_status": "block" if remaining > 0 else "pass",
                "source_stage": row.get("source_stage", ""),
                "local_only": True,
            }
        )
    return rows


def _summary(readiness_board: dict[str, Any], projection_items: list[dict[str, Any]], delta_rows: list[dict[str, Any]]) -> dict[str, Any]:
    board_summary = readiness_board.get("summary", {}) if isinstance(readiness_board.get("summary"), dict) else {}
    return {
        "current_blockers": _int(board_summary.get("blockers"), 0),
        "current_blocked_items": _int(board_summary.get("blocked"), 0),
        "projected_blocked_items": sum(1 for item in projection_items if item.get("projected_status") == "block"),
        "projected_warning_items": sum(1 for item in projection_items if item.get("projected_status") == "warn"),
        "total_rehearsal_delta": sum(_int(row.get("blocker_delta"), 0) for row in delta_rows),
        "projection_tracks": len(delta_rows),
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


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Projection artifacts only; No broker connection, no account reads, no order placement, no live trading."
