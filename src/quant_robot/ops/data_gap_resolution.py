from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_2_data_gap_resolution_ledger"
VALID_STATUSES = {
    "needs_review",
    "backfill_required",
    "accepted_non_trading_day",
    "accepted_suspension_or_no_trade",
    "resolved_with_backfill",
}
BLOCKING_STATUSES = {"needs_review", "backfill_required"}
VALIDATION_COLUMNS = ["row_number", "gap_id", "resolution_status", "issue_type", "message", "local_only"]


def build_data_gap_resolution_ledger(
    data_quality_audit: dict[str, Any],
    resolution_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    missing_dates = [row for row in data_quality_audit.get("missing_dates", []) if isinstance(row, dict)]
    known_gap_ids = {stable_gap_id(row.get("asset_id", ""), row.get("missing_date", "")) for row in missing_dates}
    resolutions, validation = _validated_resolution_index(resolution_rows or [], known_gap_ids)
    rows = [_ledger_row(row, data_quality_audit, resolutions) for row in missing_dates]
    actions = _action_queue(data_quality_audit, rows)
    ledger = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": data_quality_audit.get("stage"),
        "source_root": data_quality_audit.get("source_root"),
        "safety": _research_only_safety(),
        "summary": _summary(rows, validation["summary"]["applied_resolution_rows"]),
        "resolution_validation": validation,
        "ledger_rows": rows,
        "action_queue": actions,
    }
    ledger["markdown"] = render_data_gap_resolution_markdown(ledger)
    return ledger


def write_data_gap_resolution_ledger(output_dir: str | Path, ledger: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "data_gap_resolution_ledger.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "data_gap_resolution_ledger.md").write_text(str(ledger.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(ledger.get("ledger_rows", [])).to_csv(output_path / "data_gap_resolution_rows.csv", index=False)
    pd.DataFrame(ledger.get("action_queue", [])).to_csv(output_path / "data_gap_resolution_action_queue.csv", index=False)
    pd.DataFrame(build_resolution_template_rows(ledger)).to_csv(output_path / "gap_resolutions_template.csv", index=False)
    pd.DataFrame(resolution_status_options()).to_csv(output_path / "data_gap_resolution_status_options.csv", index=False)
    pd.DataFrame(
        ledger.get("resolution_validation", {}).get("rows", []),
        columns=VALIDATION_COLUMNS,
    ).to_csv(output_path / "data_gap_resolution_validation.csv", index=False)


def render_data_gap_resolution_markdown(ledger: dict[str, Any]) -> str:
    summary = ledger.get("summary", {}) if isinstance(ledger.get("summary"), dict) else {}
    lines = [
        "# Data Gap Resolution Ledger",
        "",
        f"- Stage: {ledger.get('stage', STAGE)}",
        f"- Gap rows: {summary.get('gap_rows', 0)}",
        f"- Blocking gap rows: {summary.get('blocking_gap_rows', 0)}",
        f"- Blocks API boundary: {summary.get('blocks_api_boundary', False)}",
        f"- Safety: {ledger.get('safety', _research_only_safety())}",
        "",
        "## Ledger Rows",
        "",
        "| Gap ID | Asset | Symbol | Missing date | Status | Blocks API boundary | Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in ledger.get("ledger_rows", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            f"{row.get('gap_id', '')} | "
            f"{row.get('asset_id', '')} | "
            f"{row.get('symbol', '')} | "
            f"{row.get('missing_date', '')} | "
            f"{row.get('resolution_status', '')} | "
            f"{row.get('blocks_api_boundary', False)} | "
            f"{_table_text(row.get('evidence_note', ''))} |"
        )
    if not ledger.get("ledger_rows"):
        lines.append("| none | none | none | none | none | False | none |")
    lines.extend(["", "## Action Queue", ""])
    for action in ledger.get("action_queue", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not ledger.get("action_queue"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def stable_gap_id(asset_id: object, missing_date: object) -> str:
    asset = re.sub(r"[^A-Za-z0-9_]+", "_", str(asset_id)).strip("_") or "unknown_asset"
    date = re.sub(r"[^0-9]+", "", str(missing_date)) or "unknown_date"
    return f"DG-{asset}-{date}"


def build_resolution_template_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    allowed_statuses = ";".join(sorted(VALID_STATUSES))
    for row in ledger.get("ledger_rows", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "gap_id": row.get("gap_id", ""),
                "asset_id": row.get("asset_id", ""),
                "symbol": row.get("symbol", ""),
                "missing_date": row.get("missing_date", ""),
                "resolution_status": "needs_review",
                "evidence_note": "",
                "reviewed_by": "",
                "reviewed_at": "",
                "allowed_statuses": allowed_statuses,
                "review_guidance": "Record local evidence before marking this gap accepted or resolved.",
            }
        )
    return rows


def resolution_status_options() -> list[dict[str, Any]]:
    descriptions = {
        "needs_review": "No local evidence has been recorded yet.",
        "backfill_required": "Local evidence indicates the missing row still needs a data refresh.",
        "accepted_non_trading_day": "Local evidence supports treating the date as a non-trading day for this asset.",
        "accepted_suspension_or_no_trade": "Local evidence supports treating the date as suspension or no-trade.",
        "resolved_with_backfill": "A local data refresh restored or otherwise resolved the missing row.",
    }
    return [
        {
            "resolution_status": status,
            "blocks_api_boundary": status in BLOCKING_STATUSES,
            "description": descriptions[status],
        }
        for status in sorted(VALID_STATUSES)
    ]


def _ledger_row(
    missing_row: dict[str, Any],
    data_quality_audit: dict[str, Any],
    resolutions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    asset_id = str(missing_row.get("asset_id", ""))
    missing_date = str(missing_row.get("missing_date", ""))
    gap_id = stable_gap_id(asset_id, missing_date)
    resolution = resolutions.get(gap_id, {})
    status = _status(resolution.get("resolution_status", "needs_review"))
    evidence_note = str(resolution.get("evidence_note") or "No local resolution recorded yet.")
    return {
        "gap_id": gap_id,
        "asset_id": asset_id,
        "symbol": str(missing_row.get("symbol", "")),
        "missing_date": missing_date,
        "resolution_status": status,
        "evidence_note": evidence_note,
        "reviewed_by": str(resolution.get("reviewed_by", "")),
        "reviewed_at": str(resolution.get("reviewed_at", "")),
        "recommended_command": _recommended_command(status, data_quality_audit),
        "blocks_api_boundary": status in BLOCKING_STATUSES,
        "local_only": True,
    }


def _resolution_by_gap_id(resolution_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    resolutions: dict[str, dict[str, Any]] = {}
    for row in resolution_rows:
        if not isinstance(row, dict):
            continue
        gap_id = str(row.get("gap_id", "")).strip()
        if not gap_id and row.get("asset_id") and row.get("missing_date"):
            gap_id = stable_gap_id(row.get("asset_id"), row.get("missing_date"))
        if gap_id:
            resolutions[gap_id] = row
    return resolutions


def _validated_resolution_index(
    resolution_rows: list[dict[str, Any]],
    known_gap_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    resolutions: dict[str, dict[str, Any]] = {}
    validation_rows = []
    duplicate_count = 0
    invalid_count = 0
    unknown_count = 0
    for row_number, row in enumerate(resolution_rows, start=1):
        if not isinstance(row, dict):
            continue
        gap_id = str(row.get("gap_id", "")).strip()
        if not gap_id and row.get("asset_id") and row.get("missing_date"):
            gap_id = stable_gap_id(row.get("asset_id"), row.get("missing_date"))
        status = str(row.get("resolution_status", "needs_review") or "needs_review").strip()
        if gap_id not in known_gap_ids:
            unknown_count += 1
            validation_rows.append(
                _validation_row(row_number, gap_id, status, "unknown_gap_id", "Resolution row does not match a current gap_id.")
            )
            continue
        if status not in VALID_STATUSES:
            invalid_count += 1
            validation_rows.append(
                _validation_row(row_number, gap_id, status, "invalid_status", "Resolution status is not supported.")
            )
            continue
        if gap_id in resolutions:
            duplicate_count += 1
            validation_rows.append(
                _validation_row(row_number, gap_id, status, "duplicate_gap_id", "Duplicate resolution row ignored; first valid row is kept.")
            )
            continue
        resolutions[gap_id] = row
    validation_errors = duplicate_count + invalid_count + unknown_count
    return resolutions, {
        "summary": {
            "resolution_rows": len(resolution_rows),
            "applied_resolution_rows": len(resolutions),
            "duplicate_gap_id_rows": duplicate_count,
            "invalid_status_rows": invalid_count,
            "unknown_gap_id_rows": unknown_count,
            "validation_errors": validation_errors,
        },
        "rows": validation_rows,
    }


def _validation_row(row_number: int, gap_id: str, status: str, issue_type: str, message: str) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "gap_id": gap_id,
        "resolution_status": status,
        "issue_type": issue_type,
        "message": message,
        "local_only": True,
    }


def _summary(rows: list[dict[str, Any]], resolution_overrides: int) -> dict[str, Any]:
    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    for row in rows:
        status = str(row.get("resolution_status", "needs_review"))
        counts[status] = counts.get(status, 0) + 1
    blocking = sum(1 for row in rows if row.get("blocks_api_boundary"))
    summary: dict[str, Any] = {
        "gap_rows": len(rows),
        "assets_with_gaps": len({row.get("asset_id") for row in rows}),
        "blocking_gap_rows": blocking,
        "blocks_api_boundary": blocking > 0,
        "resolution_overrides": resolution_overrides,
    }
    summary.update(counts)
    return summary


def _action_queue(data_quality_audit: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = [
        {
            "priority": 1,
            "track_id": "data_quality",
            "command": _audit_command(data_quality_audit),
            "reason": "Regenerate exact missing-date rows after local data changes.",
            "local_only": True,
        },
        {
            "priority": 2,
            "track_id": "data_gap_resolution",
            "command": "python scripts\\run_data_gap_resolution.py --data-quality-audit data\\reports\\data_quality_gap_audit\\data_quality_gap_audit.json --output-dir data\\reports\\data_gap_resolution",
            "reason": "Refresh this ledger after resolution notes or data imports.",
            "local_only": True,
        },
    ]
    if any(row.get("resolution_status") == "backfill_required" for row in rows):
        actions.append(
            {
                "priority": 3,
                "track_id": "data_gap_backfill",
                "command": "python scripts\\run_akshare_gap_backfill.py --gap-rows data\\reports\\data_gap_evidence\\data_gap_evidence_rows.csv --processed-root data\\processed\\etf_csv --output-dir data\\reports\\akshare_gap_backfill",
                "reason": "Attempt public AKShare ETF backfill before escalating to paid provider data.",
                "local_only": True,
            }
        )
    if any(row.get("resolution_status") == "backfill_required" or row.get("resolution_status") == "needs_review" for row in rows):
        actions.append(
            {
                "priority": 4,
                "track_id": "data_quality",
                "command": _backfill_command(data_quality_audit),
                "reason": "Refresh local ETF CSV coverage after unresolved gaps are inspected.",
                "local_only": True,
            }
        )
    actions.append(
        {
            "priority": 5,
            "track_id": "pre_api_readiness",
            "command": "python scripts\\run_pre_api_readiness_board.py --output-dir data\\reports\\pre_api_readiness_board",
            "reason": "Rebuild readiness status after gap-resolution state changes.",
            "local_only": True,
        }
    )
    return actions


def _recommended_command(status: str, data_quality_audit: dict[str, Any]) -> str:
    if status == "backfill_required":
        return _backfill_command(data_quality_audit)
    if status in {"accepted_non_trading_day", "accepted_suspension_or_no_trade", "resolved_with_backfill"}:
        return "python scripts\\run_data_gap_resolution.py --output-dir data\\reports\\data_gap_resolution"
    return _audit_command(data_quality_audit)


def _audit_command(data_quality_audit: dict[str, Any]) -> str:
    return _repair_command(
        data_quality_audit,
        "inspect_missing_dates",
        "python scripts\\run_data_quality_audit.py --data-root data\\processed\\etf_csv --market CN_ETF --output-dir data\\reports\\data_quality_gap_audit",
    )


def _backfill_command(data_quality_audit: dict[str, Any]) -> str:
    return _repair_command(
        data_quality_audit,
        "refresh_etf_csv",
        "python scripts\\batch_import_etf_csv.py --input-dir data\\raw\\tradingview_etf_csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\processed\\etf_csv",
    )


def _repair_command(data_quality_audit: dict[str, Any], action_name: str, default: str) -> str:
    actions = data_quality_audit.get("repair_actions", [])
    if not isinstance(actions, list):
        return default
    for action in actions:
        if isinstance(action, dict) and action.get("action") == action_name and action.get("command"):
            return str(action["command"])
    return default


def _status(value: object) -> str:
    status = str(value or "needs_review").strip()
    return status if status in VALID_STATUSES else "needs_review"


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Local data-gap resolution only; no broker connection, no account reads, no order placement, no live trading."
