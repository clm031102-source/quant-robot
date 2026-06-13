from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.data_gap_resolution import VALID_STATUSES, resolution_status_options


STAGE = "phase_4_14_residual_data_gap_review_pack"
DEFAULT_TEMPLATE_PATH = "data\\reports\\residual_data_gap_review\\residual_gap_review_template.csv"


def build_residual_data_gap_review_pack(
    data_gap_rehearsal: dict[str, Any],
    residual_focus_pack: dict[str, Any] | None = None,
    data_gap_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = data_gap_ledger if isinstance(data_gap_ledger, dict) else data_gap_rehearsal
    source_rows = source.get("ledger_rows", source.get("rehearsed_ledger_rows", []))
    residual_rows = _residual_rows(source_rows)
    template_rows = _review_template_rows(residual_rows)
    focus_item = _data_gap_focus_item(residual_focus_pack)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": source.get("stage"),
        "focus_stage": residual_focus_pack.get("stage") if isinstance(residual_focus_pack, dict) else None,
        "safety": _research_only_safety(),
        "summary": _summary(data_gap_rehearsal, residual_rows, focus_item, data_gap_ledger=data_gap_ledger),
        "focus_item": focus_item,
        "residual_rows": residual_rows,
        "review_template_rows": template_rows,
        "action_queue": _action_queue(residual_rows),
        "status_options": resolution_status_options(),
    }
    pack["markdown"] = render_residual_data_gap_review_markdown(pack)
    return pack


def write_residual_data_gap_review_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "residual_data_gap_review_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "residual_data_gap_review_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("residual_rows", [])).to_csv(output_path / "residual_data_gap_rows.csv", index=False)
    pd.DataFrame(pack.get("review_template_rows", [])).to_csv(output_path / "residual_gap_review_template.csv", index=False)
    pd.DataFrame(pack.get("action_queue", [])).to_csv(output_path / "residual_gap_action_queue.csv", index=False)
    pd.DataFrame(pack.get("status_options", [])).to_csv(output_path / "residual_gap_status_options.csv", index=False)


def render_residual_data_gap_review_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Residual Data Gap Review Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Residual gap rows: {summary.get('residual_gap_rows', 0)}",
        f"- Residual assets: {summary.get('residual_assets', 0)}",
        f"- Sample cleared gap rows: {summary.get('sample_cleared_gap_rows', 0)}",
        f"- Blocks API boundary after review: {summary.get('blocks_api_boundary_after_review', False)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        "",
        "## Residual Gaps",
        "",
        "| Gap ID | Asset | Symbol | Missing Date | Status | Command |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("residual_rows", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('gap_id', '')} | "
                f"{row.get('asset_id', '')} | "
                f"{row.get('symbol', '')} | "
                f"{row.get('missing_date', '')} | "
                f"{row.get('resolution_status', '')} | "
                f"`{_table_text(row.get('recommended_command', ''))}` |"
            )
    if not pack.get("residual_rows"):
        lines.append("| none | none | none | none | none | none |")
    lines.extend(["", "## Action Queue", ""])
    for action in pack.get("action_queue", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not pack.get("action_queue"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _residual_rows(value: Any) -> list[dict[str, Any]]:
    rows = []
    if not isinstance(value, list):
        return rows
    for row in value:
        if not isinstance(row, dict) or not bool(row.get("blocks_api_boundary", False)):
            continue
        rows.append(
            {
                "gap_id": str(row.get("gap_id", "")),
                "asset_id": str(row.get("asset_id", "")),
                "symbol": str(row.get("symbol", "")),
                "missing_date": str(row.get("missing_date", "")),
                "resolution_status": str(row.get("resolution_status", "needs_review")),
                "evidence_note": str(row.get("evidence_note", "")),
                "recommended_command": str(row.get("recommended_command", "")),
                "blocks_api_boundary": True,
                "local_only": True,
            }
        )
    return rows


def _review_template_rows(residual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed_statuses = ";".join(sorted(VALID_STATUSES))
    rows = []
    for row in residual_rows:
        rows.append(
            {
                "gap_id": row.get("gap_id", ""),
                "asset_id": row.get("asset_id", ""),
                "symbol": row.get("symbol", ""),
                "missing_date": row.get("missing_date", ""),
                "resolution_status": row.get("resolution_status", "needs_review"),
                "evidence_note": row.get("evidence_note", ""),
                "reviewed_by": "",
                "reviewed_at": "",
                "allowed_statuses": allowed_statuses,
                "review_guidance": "Fill local evidence, then rerun data-gap resolution with this template as --resolution-file.",
            }
        )
    return rows


def _action_queue(residual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not residual_rows:
        return [
            {
                "priority": 1,
                "track_id": "data_gap_resolution",
                "command": "python scripts\\run_readiness_projection.py --output-dir data\\reports\\readiness_projection",
                "reason": "Refresh projection after confirming no residual data gaps remain.",
                "local_only": True,
            }
        ]
    return [
        {
            "priority": 1,
            "track_id": "data_quality",
            "command": "python scripts\\run_data_quality_audit.py --data-root data\\processed\\etf_csv --market CN_ETF --output-dir data\\reports\\data_quality_gap_audit",
            "reason": "Regenerate exact missing-date rows before reviewing residual gaps.",
            "local_only": True,
        },
        {
            "priority": 2,
            "track_id": "data_quality",
            "command": "python scripts\\batch_import_etf_csv.py --input-dir data\\raw\\tradingview_etf_csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\processed\\etf_csv",
            "reason": "Refresh local ETF CSV coverage if residual gaps are true data holes.",
            "local_only": True,
        },
        {
            "priority": 3,
            "track_id": "data_gap_evidence",
            "command": "python scripts\\run_data_gap_evidence.py --gap-rows data\\reports\\residual_data_gap_review\\residual_data_gap_rows.csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\reports\\data_gap_evidence",
            "reason": "Attach local raw CSV and peer-trading evidence before changing residual gap statuses.",
            "local_only": True,
        },
        {
            "priority": 4,
            "track_id": "data_gap_resolution",
            "command": f"python scripts\\run_data_gap_resolution.py --resolution-file {DEFAULT_TEMPLATE_PATH} --output-dir data\\reports\\data_gap_resolution",
            "reason": "Apply reviewed residual gap statuses back into the local data-gap ledger.",
            "local_only": True,
        },
        {
            "priority": 5,
            "track_id": "data_gap_resolution",
            "command": "python scripts\\run_data_gap_rehearsal.py --output-dir data\\reports\\data_gap_rehearsal",
            "reason": "Refresh rehearsal evidence after residual gap review changes.",
            "local_only": True,
        },
        {
            "priority": 6,
            "track_id": "readiness_projection",
            "command": "python scripts\\run_readiness_projection.py --output-dir data\\reports\\readiness_projection",
            "reason": "Refresh projected blockers after residual data-gap evidence changes.",
            "local_only": True,
        },
        {
            "priority": 7,
            "track_id": "residual_blocker_focus",
            "command": "python scripts\\run_residual_blocker_focus.py --output-dir data\\reports\\residual_blocker_focus",
            "reason": "Refresh root blocker focus after data-gap residuals change.",
            "local_only": True,
        },
    ]


def _summary(
    data_gap_rehearsal: dict[str, Any],
    residual_rows: list[dict[str, Any]],
    focus_item: dict[str, Any] | None,
    data_gap_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rehearsal_summary = data_gap_rehearsal.get("summary", {}) if isinstance(data_gap_rehearsal.get("summary"), dict) else {}
    source_summary = data_gap_ledger.get("summary", {}) if isinstance(data_gap_ledger, dict) and isinstance(data_gap_ledger.get("summary"), dict) else rehearsal_summary
    residual_assets = {row.get("asset_id") for row in residual_rows if row.get("asset_id")}
    source_rows = data_gap_ledger.get("ledger_rows", []) if isinstance(data_gap_ledger, dict) else data_gap_rehearsal.get("rehearsed_ledger_rows", [])
    return {
        "source_gap_rows": _int(source_summary.get("gap_rows", source_summary.get("source_gap_rows")), len(source_rows)),
        "source_blocking_gap_rows": _int(source_summary.get("blocking_gap_rows", source_summary.get("source_blocking_gap_rows")), 0),
        "sample_cleared_gap_rows": _int(rehearsal_summary.get("sample_resolution_rows"), 0),
        "rehearsed_blocking_gap_rows": _int(rehearsal_summary.get("rehearsed_blocking_gap_rows"), len(residual_rows)),
        "residual_gap_rows": len(residual_rows),
        "residual_assets": len(residual_assets),
        "blocks_api_boundary_after_review": len(residual_rows) > 0,
        "focus_priority_rank": _int(focus_item.get("priority_rank"), 0) if isinstance(focus_item, dict) else None,
    }


def _data_gap_focus_item(focus_pack: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(focus_pack, dict):
        return None
    rows = focus_pack.get("focus_items", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("track_id") == "data_gap_resolution":
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
    return "Research only. Residual data-gap review artifacts only; No broker connection, no account reads, no order placement, no live trading."
