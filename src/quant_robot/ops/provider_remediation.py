from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_7_provider_remediation_matrix"
VALID_REMEDIATION_STATUSES = {
    "needs_review",
    "blocked_external_change",
    "adapter_work_required",
    "resolved_locally",
    "accepted_out_of_scope",
}
BLOCKING_REMEDIATION_STATUSES = {"needs_review", "blocked_external_change", "adapter_work_required"}
VALIDATION_COLUMNS = ["row_number", "remediation_id", "review_status", "issue_type", "message", "local_only"]


def build_provider_remediation_matrix(
    provider_evidence: dict[str, Any],
    review_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = []
    for provider in provider_evidence.get("providers", []):
        if isinstance(provider, dict):
            items.extend(_provider_items(provider))
    parquet = provider_evidence.get("parquet", {}) if isinstance(provider_evidence.get("parquet"), dict) else {}
    if not bool(parquet.get("ready", False)):
        items.extend(_parquet_items(parquet))
    known_ids = {str(item.get("remediation_id", "")) for item in items}
    reviews, validation = _validated_review_index(review_rows or [], known_ids)
    items = [_apply_review(item, reviews.get(str(item.get("remediation_id", "")))) for item in items]
    matrix = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": provider_evidence.get("stage"),
        "safety": _research_only_safety(),
        "summary": _summary(items, provider_evidence),
        "review_validation": validation,
        "remediation_items": items,
    }
    matrix["markdown"] = render_provider_remediation_markdown(matrix)
    return matrix


def write_provider_remediation_matrix(output_dir: str | Path, matrix: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "provider_remediation_matrix.json").write_text(
        json.dumps(matrix, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "provider_remediation_matrix.md").write_text(str(matrix.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(matrix.get("remediation_items", [])).to_csv(output_path / "provider_remediation_items.csv", index=False)
    pd.DataFrame([matrix.get("summary", {})]).to_csv(output_path / "provider_remediation_summary.csv", index=False)
    pd.DataFrame(build_review_template_rows(matrix)).to_csv(
        output_path / "provider_remediation_review_template.csv",
        index=False,
    )
    pd.DataFrame(remediation_status_options()).to_csv(output_path / "provider_remediation_status_options.csv", index=False)
    pd.DataFrame(
        matrix.get("review_validation", {}).get("rows", []),
        columns=VALIDATION_COLUMNS,
    ).to_csv(output_path / "provider_remediation_validation.csv", index=False)


def render_provider_remediation_markdown(matrix: dict[str, Any]) -> str:
    summary = matrix.get("summary", {}) if isinstance(matrix.get("summary"), dict) else {}
    lines = [
        "# Provider Remediation Matrix",
        "",
        f"- Stage: {matrix.get('stage', STAGE)}",
        f"- Safety: {matrix.get('safety', _research_only_safety())}",
        f"- Remediation items: {summary.get('remediation_items', 0)}",
        f"- Blocks API boundary: {summary.get('blocks_api_boundary', False)}",
        "",
        "## Items",
        "",
        "| ID | Provider | Type | Blocker | Verification |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in matrix.get("remediation_items", []):
        if isinstance(item, dict):
            lines.append(
                "| "
                f"{item.get('remediation_id', '')} | "
                f"{item.get('provider', '')} | "
                f"{item.get('blocker_type', '')} | "
                f"{_table_text(item.get('blocker', ''))} | "
                f"`{item.get('verification_command', '')}` |"
            )
    if not matrix.get("remediation_items"):
        lines.append("| none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def build_review_template_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    allowed_statuses = ";".join(sorted(VALID_REMEDIATION_STATUSES))
    for item in matrix.get("remediation_items", []):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "remediation_id": item.get("remediation_id", ""),
                "provider": item.get("provider", ""),
                "blocker_type": item.get("blocker_type", ""),
                "blocker": item.get("blocker", ""),
                "review_status": item.get("review_status", "needs_review"),
                "evidence_note": item.get("evidence_note", ""),
                "reviewed_by": item.get("reviewed_by", ""),
                "reviewed_at": item.get("reviewed_at", ""),
                "verification_command": item.get("verification_command", ""),
                "resolution_hint": item.get("resolution_hint", ""),
                "allowed_statuses": allowed_statuses,
                "review_guidance": "Record controlled local evidence before marking this remediation resolved or out of scope.",
                "local_only": True,
            }
        )
    return rows


def _validated_review_index(
    review_rows: list[dict[str, Any]],
    known_remediation_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    reviews: dict[str, dict[str, Any]] = {}
    validation_rows = []
    duplicate_count = 0
    invalid_count = 0
    unknown_count = 0
    for row_number, row in enumerate(review_rows, start=1):
        if not isinstance(row, dict):
            continue
        remediation_id = str(row.get("remediation_id", "")).strip()
        status = str(row.get("review_status", "needs_review") or "needs_review").strip()
        if remediation_id not in known_remediation_ids:
            unknown_count += 1
            validation_rows.append(
                _validation_row(row_number, remediation_id, status, "unknown_remediation_id", "Review row does not match a current remediation_id.")
            )
            continue
        if status not in VALID_REMEDIATION_STATUSES:
            invalid_count += 1
            validation_rows.append(
                _validation_row(row_number, remediation_id, status, "invalid_status", "Review status is not supported.")
            )
            continue
        if remediation_id in reviews:
            duplicate_count += 1
            validation_rows.append(
                _validation_row(row_number, remediation_id, status, "duplicate_remediation_id", "Duplicate review row ignored; first valid row is kept.")
            )
            continue
        reviews[remediation_id] = row
    validation_errors = duplicate_count + invalid_count + unknown_count
    return reviews, {
        "summary": {
            "review_rows": len(review_rows),
            "applied_review_rows": len(reviews),
            "duplicate_remediation_id_rows": duplicate_count,
            "invalid_status_rows": invalid_count,
            "unknown_remediation_id_rows": unknown_count,
            "validation_errors": validation_errors,
        },
        "rows": validation_rows,
    }


def _validation_row(row_number: int, remediation_id: str, status: str, issue_type: str, message: str) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "remediation_id": remediation_id,
        "review_status": status,
        "issue_type": issue_type,
        "message": message,
        "local_only": True,
    }


def _apply_review(item: dict[str, Any], review: dict[str, Any] | None) -> dict[str, Any]:
    row = dict(item)
    status = _review_status(review.get("review_status") if isinstance(review, dict) else "needs_review")
    row.update(
        {
            "review_status": status,
            "evidence_note": str(review.get("evidence_note", "")) if isinstance(review, dict) else "",
            "reviewed_by": str(review.get("reviewed_by", "")) if isinstance(review, dict) else "",
            "reviewed_at": str(review.get("reviewed_at", "")) if isinstance(review, dict) else "",
            "blocks_provider_readiness": status in BLOCKING_REMEDIATION_STATUSES,
        }
    )
    return row


def remediation_status_options() -> list[dict[str, Any]]:
    descriptions = {
        "needs_review": "No local remediation evidence has been recorded yet.",
        "blocked_external_change": "The item still requires a controlled local environment or credential change.",
        "adapter_work_required": "Code-level adapter work is still required before this provider can be relied on.",
        "resolved_locally": "Local evidence shows the blocker has been resolved and verification was rerun.",
        "accepted_out_of_scope": "Local review accepts that this provider or storage path is not required for the current research scope.",
    }
    return [
        {
            "review_status": status,
            "blocks_provider_readiness": status in BLOCKING_REMEDIATION_STATUSES,
            "description": descriptions[status],
        }
        for status in sorted(VALID_REMEDIATION_STATUSES)
    ]


def _provider_items(provider: dict[str, Any]) -> list[dict[str, Any]]:
    if bool(provider.get("ready", False)):
        return []
    rows = []
    provider_name = str(provider.get("provider", "unknown"))
    package = str(provider.get("package") or provider_name)
    credential = str(provider.get("credential") or "")
    for missing in _list(provider.get("missing", [])):
        text = str(missing)
        lowered = text.lower()
        if "package" in lowered and "not installed" in lowered:
            rows.append(
                _item(
                    provider_name,
                    "dependency",
                    text,
                    f"Install optional package '{package}' in a controlled local environment, then rerun provider readiness checks.",
                    "python scripts\\check_readiness.py",
                    True,
                )
            )
        elif "token" in lowered or (credential and credential.lower() in lowered) or "credential" in lowered:
            rows.append(
                _item(
                    provider_name,
                    "credential",
                    text,
                    f"Set local environment variable {credential or 'provider credential'} before provider-enabled runs.",
                    "python scripts\\show_provider_status.py",
                    True,
                )
            )
        elif "adapter" in lowered and "planned" in lowered:
            rows.append(
                _item(
                    provider_name,
                    "adapter_implementation",
                    text,
                    f"Implement and test the {provider_name} adapter before relying on this provider.",
                    "python scripts\\show_provider_status.py",
                    True,
                )
            )
    return rows


def _parquet_items(parquet: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for missing in _list(parquet.get("missing", [])):
        text = str(missing)
        rows.append(
            _item(
                "parquet",
                "storage_dependency",
                text,
                "Install pyarrow or fastparquet in a controlled local environment, then rerun readiness checks.",
                "python scripts\\check_readiness.py",
                True,
            )
        )
    return rows


def _item(
    provider: str,
    blocker_type: str,
    blocker: str,
    resolution_hint: str,
    verification_command: str,
    blocks_provider_readiness: bool,
) -> dict[str, Any]:
    return {
        "remediation_id": f"PR-{provider}-{blocker_type}".replace(" ", "_"),
        "provider": provider,
        "blocker_type": blocker_type,
        "blocker": blocker,
        "resolution_hint": resolution_hint,
        "verification_command": verification_command,
        "blocks_provider_readiness": blocks_provider_readiness,
        "local_only": True,
    }


def _summary(items: list[dict[str, Any]], provider_evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_summary = provider_evidence.get("summary", {}) if isinstance(provider_evidence.get("summary"), dict) else {}
    blocking = sum(1 for item in items if item.get("blocks_provider_readiness"))
    summary: dict[str, Any] = {
        "providers": int(evidence_summary.get("providers", 0) or len(provider_evidence.get("providers", []))),
        "ready_providers": int(evidence_summary.get("ready_providers", 0) or 0),
        "blocked_providers": int(evidence_summary.get("blocked_providers", 0) or 0),
        "remediation_items": len(items),
        "blocking_remediation_items": blocking,
        "dependency_items": _count(items, "dependency"),
        "credential_items": _count(items, "credential"),
        "adapter_items": _count(items, "adapter_implementation"),
        "storage_items": _count(items, "storage_dependency"),
        "blocks_api_boundary": blocking > 0,
    }
    for status in sorted(VALID_REMEDIATION_STATUSES):
        summary[status] = sum(1 for item in items if item.get("review_status") == status)
    return summary


def _count(items: list[dict[str, Any]], blocker_type: str) -> int:
    return sum(1 for item in items if item.get("blocker_type") == blocker_type)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _review_status(value: object) -> str:
    status = str(value or "needs_review").strip()
    return status if status in VALID_REMEDIATION_STATUSES else "needs_review"


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
