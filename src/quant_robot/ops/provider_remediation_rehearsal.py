from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.provider_remediation import build_provider_remediation_matrix


STAGE = "phase_4_11_provider_remediation_review_rehearsal"
DEFAULT_OUT_OF_SCOPE_PROVIDERS = {"akshare", "ccxt", "yfinance"}


def build_provider_remediation_rehearsal(
    provider_evidence: dict[str, Any],
    out_of_scope_providers: set[str] | None = None,
    baseline_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = baseline_matrix if isinstance(baseline_matrix, dict) else build_provider_remediation_matrix(provider_evidence)
    sample_rows = _sample_review_rows(
        baseline.get("remediation_items", []),
        out_of_scope_providers or DEFAULT_OUT_OF_SCOPE_PROVIDERS,
    )
    rehearsed = baseline if not sample_rows else build_provider_remediation_matrix(provider_evidence, review_rows=sample_rows)
    source_summary = baseline.get("summary", {}) if isinstance(baseline.get("summary"), dict) else {}
    rehearsed_summary = rehearsed.get("summary", {}) if isinstance(rehearsed.get("summary"), dict) else {}
    source_blocking = _int(source_summary.get("blocking_remediation_items"), 0)
    rehearsed_blocking = _int(rehearsed_summary.get("blocking_remediation_items"), 0)
    rehearsal = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": provider_evidence.get("stage"),
        "safety": _research_only_safety(),
        "summary": {
            "source_remediation_items": _int(source_summary.get("remediation_items"), 0),
            "sample_review_rows": len(sample_rows),
            "source_blocking_remediation_items": source_blocking,
            "rehearsed_blocking_remediation_items": rehearsed_blocking,
            "blocker_delta": source_blocking - rehearsed_blocking,
            "blocks_api_boundary_after_rehearsal": bool(rehearsed_summary.get("blocks_api_boundary", False)),
        },
        "sample_review_rows": sample_rows,
        "rehearsed_remediation_summary": rehearsed_summary,
        "rehearsed_remediation_items": rehearsed.get("remediation_items", []),
        "readiness_projection": _readiness_projection(rehearsed_summary),
    }
    rehearsal["markdown"] = render_provider_remediation_rehearsal_markdown(rehearsal)
    return rehearsal


def write_provider_remediation_rehearsal(output_dir: str | Path, rehearsal: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "provider_remediation_rehearsal.json").write_text(
        json.dumps(rehearsal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "provider_remediation_rehearsal.md").write_text(str(rehearsal.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(rehearsal.get("sample_review_rows", [])).to_csv(output_path / "sample_provider_remediation_reviews.csv", index=False)
    pd.DataFrame(rehearsal.get("rehearsed_remediation_items", [])).to_csv(output_path / "rehearsed_provider_remediation_items.csv", index=False)
    pd.DataFrame([rehearsal.get("summary", {})]).to_csv(output_path / "provider_remediation_rehearsal_summary.csv", index=False)


def render_provider_remediation_rehearsal_markdown(rehearsal: dict[str, Any]) -> str:
    summary = rehearsal.get("summary", {}) if isinstance(rehearsal.get("summary"), dict) else {}
    projection = rehearsal.get("readiness_projection", {}) if isinstance(rehearsal.get("readiness_projection"), dict) else {}
    lines = [
        "# Provider Remediation Review Rehearsal",
        "",
        f"- Stage: {rehearsal.get('stage', STAGE)}",
        f"- Safety: {rehearsal.get('safety', _research_only_safety())}",
        f"- Before blocking remediation items: {summary.get('source_blocking_remediation_items', 0)}",
        f"- After rehearsal blocking remediation items: {summary.get('rehearsed_blocking_remediation_items', 0)}",
        f"- Blocker delta: {summary.get('blocker_delta', 0)}",
        f"- Projected readiness status: {projection.get('status', 'unknown')}",
        "",
        "## Sample Review Rows",
        "",
        "| Remediation ID | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rehearsal.get("sample_review_rows", []):
        if isinstance(row, dict):
            lines.append(f"| {row.get('remediation_id', '')} | {row.get('review_status', '')} | {_table_text(row.get('evidence_note', ''))} |")
    if not rehearsal.get("sample_review_rows"):
        lines.append("| none | none | none |")
    return "\n".join(lines) + "\n"


def _sample_review_rows(remediation_items: list[Any], out_of_scope_providers: set[str]) -> list[dict[str, Any]]:
    rows = []
    for item in remediation_items:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider", ""))
        if provider not in out_of_scope_providers:
            continue
        if item.get("blocks_provider_readiness") is False or item.get("review_status") == "accepted_out_of_scope":
            continue
        rows.append(
            {
                "remediation_id": item.get("remediation_id", ""),
                "review_status": "accepted_out_of_scope",
                "evidence_note": "Rehearsal only: placeholder local scope decision; replace with real review evidence before use.",
                "reviewed_by": "rehearsal",
                "reviewed_at": datetime.now(timezone.utc).date().isoformat(),
            }
        )
    return rows


def _readiness_projection(summary: dict[str, Any]) -> dict[str, Any]:
    blocking = _int(summary.get("blocking_remediation_items"), 0)
    return {
        "track_id": "provider_remediation",
        "status": "block" if blocking > 0 else "pass",
        "evidence": (
            f"remediation_items={summary.get('remediation_items', 0)}, "
            f"blocking_remediation_items={blocking}, needs_review={summary.get('needs_review', 0)}"
        ),
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
