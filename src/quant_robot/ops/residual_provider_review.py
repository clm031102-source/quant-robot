from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.provider_remediation import VALID_REMEDIATION_STATUSES, remediation_status_options


STAGE = "phase_4_15_residual_provider_review_pack"
DEFAULT_TEMPLATE_PATH = "data\\reports\\residual_provider_review\\residual_provider_review_template.csv"


def build_residual_provider_review_pack(
    provider_remediation_rehearsal: dict[str, Any],
    residual_focus_pack: dict[str, Any] | None = None,
    provider_remediation_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = provider_remediation_matrix if isinstance(provider_remediation_matrix, dict) else provider_remediation_rehearsal
    source_items = source.get("remediation_items", source.get("rehearsed_remediation_items", []))
    residual_items = _residual_items(source_items)
    template_rows = _review_template_rows(residual_items)
    focus_item = _provider_focus_item(residual_focus_pack)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": source.get("stage"),
        "focus_stage": residual_focus_pack.get("stage") if isinstance(residual_focus_pack, dict) else None,
        "safety": _research_only_safety(),
        "summary": _summary(
            provider_remediation_rehearsal,
            residual_items,
            focus_item,
            provider_remediation_matrix=provider_remediation_matrix,
        ),
        "focus_item": focus_item,
        "residual_items": residual_items,
        "review_template_rows": template_rows,
        "action_queue": _action_queue(residual_items),
        "status_options": remediation_status_options(),
    }
    pack["markdown"] = render_residual_provider_review_markdown(pack)
    return pack


def write_residual_provider_review_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "residual_provider_review_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "residual_provider_review_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("residual_items", [])).to_csv(output_path / "residual_provider_remediation_items.csv", index=False)
    pd.DataFrame(pack.get("review_template_rows", [])).to_csv(output_path / "residual_provider_review_template.csv", index=False)
    pd.DataFrame(pack.get("action_queue", [])).to_csv(output_path / "residual_provider_action_queue.csv", index=False)
    pd.DataFrame(pack.get("status_options", [])).to_csv(output_path / "residual_provider_status_options.csv", index=False)


def render_residual_provider_review_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Residual Provider Review Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Residual remediation items: {summary.get('residual_remediation_items', 0)}",
        f"- Residual providers: {summary.get('residual_providers', 0)}",
        f"- Sample cleared remediation items: {summary.get('sample_cleared_remediation_items', 0)}",
        f"- Blocks API boundary after review: {summary.get('blocks_api_boundary_after_review', False)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        "",
        "## Residual Provider Items",
        "",
        "| Remediation ID | Provider | Type | Status | Verification |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in pack.get("residual_items", []):
        if isinstance(item, dict):
            lines.append(
                "| "
                f"{item.get('remediation_id', '')} | "
                f"{item.get('provider', '')} | "
                f"{item.get('blocker_type', '')} | "
                f"{item.get('review_status', '')} | "
                f"`{_table_text(item.get('verification_command', ''))}` |"
            )
    if not pack.get("residual_items"):
        lines.append("| none | none | none | none | none |")
    lines.extend(["", "## Action Queue", ""])
    for action in pack.get("action_queue", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not pack.get("action_queue"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _residual_items(value: Any) -> list[dict[str, Any]]:
    rows = []
    if not isinstance(value, list):
        return rows
    for item in value:
        if not isinstance(item, dict) or not bool(item.get("blocks_provider_readiness", False)):
            continue
        rows.append(
            {
                "remediation_id": str(item.get("remediation_id", "")),
                "provider": str(item.get("provider", "")),
                "blocker_type": str(item.get("blocker_type", "")),
                "blocker": str(item.get("blocker", "")),
                "review_status": str(item.get("review_status", "needs_review")),
                "evidence_note": str(item.get("evidence_note", "")),
                "verification_command": str(item.get("verification_command", "")),
                "resolution_hint": str(item.get("resolution_hint", "")),
                "blocks_provider_readiness": True,
                "local_only": True,
            }
        )
    return rows


def _review_template_rows(residual_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed_statuses = ";".join(sorted(VALID_REMEDIATION_STATUSES))
    rows = []
    for item in residual_items:
        rows.append(
            {
                "remediation_id": item.get("remediation_id", ""),
                "provider": item.get("provider", ""),
                "blocker_type": item.get("blocker_type", ""),
                "blocker": item.get("blocker", ""),
                "review_status": item.get("review_status", "needs_review"),
                "evidence_note": item.get("evidence_note", ""),
                "reviewed_by": "",
                "reviewed_at": "",
                "verification_command": item.get("verification_command", ""),
                "resolution_hint": item.get("resolution_hint", ""),
                "allowed_statuses": allowed_statuses,
                "review_guidance": "Fill controlled local evidence, then rerun provider remediation with this template as --review-file.",
                "local_only": True,
            }
        )
    return rows


def _action_queue(residual_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not residual_items:
        return [
            {
                "priority": 1,
                "track_id": "provider_remediation",
                "command": "python scripts\\run_readiness_projection.py --output-dir data\\reports\\readiness_projection",
                "reason": "Refresh projection after confirming no residual provider-remediation blockers remain.",
                "local_only": True,
            }
        ]
    return [
        {
            "priority": 1,
            "track_id": "provider_readiness",
            "command": "python scripts\\check_readiness.py",
            "reason": "Recheck optional dependency and token readiness locally before reviewing residual provider blockers.",
            "local_only": True,
        },
        {
            "priority": 2,
            "track_id": "provider_readiness",
            "command": "python scripts\\show_provider_status.py",
            "reason": "Record current provider readiness evidence after local environment review.",
            "local_only": True,
        },
        {
            "priority": 3,
            "track_id": "provider_remediation",
            "command": f"python scripts\\run_provider_remediation.py --review-file {DEFAULT_TEMPLATE_PATH} --output-dir data\\reports\\provider_remediation",
            "reason": "Apply reviewed residual provider statuses back into the local provider-remediation matrix.",
            "local_only": True,
        },
        {
            "priority": 4,
            "track_id": "provider_remediation",
            "command": "python scripts\\run_provider_remediation_rehearsal.py --output-dir data\\reports\\provider_remediation_rehearsal",
            "reason": "Refresh provider-remediation rehearsal evidence after residual provider review changes.",
            "local_only": True,
        },
        {
            "priority": 5,
            "track_id": "readiness_projection",
            "command": "python scripts\\run_readiness_projection.py --output-dir data\\reports\\readiness_projection",
            "reason": "Refresh projected blockers after residual provider evidence changes.",
            "local_only": True,
        },
        {
            "priority": 6,
            "track_id": "residual_blocker_focus",
            "command": "python scripts\\run_residual_blocker_focus.py --output-dir data\\reports\\residual_blocker_focus",
            "reason": "Refresh root blocker focus after provider residuals change.",
            "local_only": True,
        },
    ]


def _summary(
    provider_remediation_rehearsal: dict[str, Any],
    residual_items: list[dict[str, Any]],
    focus_item: dict[str, Any] | None,
    provider_remediation_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rehearsal_summary = (
        provider_remediation_rehearsal.get("summary", {})
        if isinstance(provider_remediation_rehearsal.get("summary"), dict)
        else {}
    )
    source_summary = (
        provider_remediation_matrix.get("summary", {})
        if isinstance(provider_remediation_matrix, dict) and isinstance(provider_remediation_matrix.get("summary"), dict)
        else rehearsal_summary
    )
    source_items = provider_remediation_matrix.get("remediation_items", []) if isinstance(provider_remediation_matrix, dict) else provider_remediation_rehearsal.get("rehearsed_remediation_items", [])
    residual_providers = {row.get("provider") for row in residual_items if row.get("provider")}
    return {
        "source_remediation_items": _int(source_summary.get("remediation_items", source_summary.get("source_remediation_items")), len(source_items)),
        "source_blocking_remediation_items": _int(source_summary.get("blocking_remediation_items", source_summary.get("source_blocking_remediation_items")), 0),
        "sample_cleared_remediation_items": _int(rehearsal_summary.get("sample_review_rows"), 0),
        "rehearsed_blocking_remediation_items": _int(rehearsal_summary.get("rehearsed_blocking_remediation_items"), len(residual_items)),
        "residual_remediation_items": len(residual_items),
        "residual_providers": len(residual_providers),
        "blocks_api_boundary_after_review": len(residual_items) > 0,
        "focus_priority_rank": _int(focus_item.get("priority_rank"), 0) if isinstance(focus_item, dict) else None,
    }


def _provider_focus_item(focus_pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(focus_pack, dict):
        return None
    rows = focus_pack.get("focus_items", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("track_id") == "provider_remediation":
            return row
    return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Residual provider review artifacts only; No broker connection, no account reads, no order placement, no live trading."
