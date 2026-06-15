from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.data_gap_resolution import build_data_gap_resolution_ledger


STAGE = "phase_4_6_data_gap_resolution_rehearsal"


def build_data_gap_rehearsal(
    data_quality_audit: dict[str, Any],
    sample_size: int = 2,
    baseline_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_ledger if isinstance(baseline_ledger, dict) else build_data_gap_resolution_ledger(data_quality_audit)
    sample_rows = _sample_resolution_rows(baseline.get("ledger_rows", []), sample_size)
    rehearsed = baseline if not sample_rows else build_data_gap_resolution_ledger(data_quality_audit, resolution_rows=sample_rows)
    source_summary = baseline.get("summary", {}) if isinstance(baseline.get("summary"), dict) else {}
    rehearsed_summary = rehearsed.get("summary", {}) if isinstance(rehearsed.get("summary"), dict) else {}
    source_blocking = _int(source_summary.get("blocking_gap_rows"), 0)
    rehearsed_blocking = _int(rehearsed_summary.get("blocking_gap_rows"), 0)
    rehearsal = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": data_quality_audit.get("stage"),
        "safety": _research_only_safety(),
        "summary": {
            "source_gap_rows": _int(source_summary.get("gap_rows"), 0),
            "sample_resolution_rows": len(sample_rows),
            "source_blocking_gap_rows": source_blocking,
            "rehearsed_blocking_gap_rows": rehearsed_blocking,
            "blocker_delta": source_blocking - rehearsed_blocking,
            "blocks_api_boundary_after_rehearsal": bool(rehearsed_summary.get("blocks_api_boundary", False)),
        },
        "sample_resolution_rows": sample_rows,
        "rehearsed_ledger_summary": rehearsed_summary,
        "rehearsed_ledger_rows": rehearsed.get("ledger_rows", []),
        "readiness_projection": _readiness_projection(rehearsed_summary),
    }
    rehearsal["markdown"] = render_data_gap_rehearsal_markdown(rehearsal)
    return rehearsal


def write_data_gap_rehearsal(output_dir: str | Path, rehearsal: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "data_gap_rehearsal.json").write_text(
        json.dumps(rehearsal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "data_gap_rehearsal.md").write_text(str(rehearsal.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(rehearsal.get("sample_resolution_rows", [])).to_csv(output_path / "sample_gap_resolutions.csv", index=False)
    pd.DataFrame(rehearsal.get("rehearsed_ledger_rows", [])).to_csv(output_path / "rehearsed_data_gap_rows.csv", index=False)
    pd.DataFrame([rehearsal.get("summary", {})]).to_csv(output_path / "data_gap_rehearsal_summary.csv", index=False)


def render_data_gap_rehearsal_markdown(rehearsal: dict[str, Any]) -> str:
    summary = rehearsal.get("summary", {}) if isinstance(rehearsal.get("summary"), dict) else {}
    projection = rehearsal.get("readiness_projection", {}) if isinstance(rehearsal.get("readiness_projection"), dict) else {}
    lines = [
        "# Data Gap Resolution Rehearsal",
        "",
        f"- Stage: {rehearsal.get('stage', STAGE)}",
        f"- Safety: {rehearsal.get('safety', _research_only_safety())}",
        f"- Before blocking gaps: {summary.get('source_blocking_gap_rows', 0)}",
        f"- After rehearsal blocking gaps: {summary.get('rehearsed_blocking_gap_rows', 0)}",
        f"- Blocker delta: {summary.get('blocker_delta', 0)}",
        f"- Projected readiness status: {projection.get('status', 'unknown')}",
        "",
        "## Sample Resolution Rows",
        "",
        "| Gap ID | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rehearsal.get("sample_resolution_rows", []):
        if isinstance(row, dict):
            lines.append(f"| {row.get('gap_id', '')} | {row.get('resolution_status', '')} | {_table_text(row.get('evidence_note', ''))} |")
    if not rehearsal.get("sample_resolution_rows"):
        lines.append("| none | none | none |")
    return "\n".join(lines) + "\n"


def _sample_resolution_rows(ledger_rows: list[Any], sample_size: int) -> list[dict[str, Any]]:
    rows = []
    count = max(0, int(sample_size))
    for row in ledger_rows:
        if not isinstance(row, dict):
            continue
        if row.get("blocks_api_boundary") is False and row.get("resolution_status") not in {"needs_review", "backfill_required"}:
            continue
        rows.append(
            {
                "gap_id": row.get("gap_id", ""),
                "resolution_status": "accepted_non_trading_day",
                "evidence_note": "Rehearsal only: placeholder local evidence; replace with real local evidence before review.",
                "reviewed_by": "rehearsal",
                "reviewed_at": datetime.now(timezone.utc).date().isoformat(),
            }
        )
        if len(rows) >= count:
            break
    return rows


def _readiness_projection(summary: dict[str, Any]) -> dict[str, Any]:
    blocking = _int(summary.get("blocking_gap_rows"), 0)
    return {
        "track_id": "data_gap_resolution",
        "status": "block" if blocking > 0 else "pass",
        "evidence": f"gap_rows={summary.get('gap_rows', 0)}, blocking_gap_rows={blocking}, needs_review={summary.get('needs_review', 0)}",
    }


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Rehearsal artifacts only; No broker connection, no account reads, no order placement, no live trading."
