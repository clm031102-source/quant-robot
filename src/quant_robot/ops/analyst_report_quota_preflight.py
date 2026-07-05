from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


STAGE = "analyst_report_quota_preflight"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
DEFAULT_MAX_DAILY_REQUESTS = 2
COUNTED_WINDOW_STATUSES = {"ok", "cap_warning", "failed"}
QUOTA_SCOPE = "local_report_roots_only"
QUOTA_SCOPE_WARNING = "local_report_roots_only"
QUOTA_TARGET_DATE_MISMATCH_WARNING = "quota_target_date_differs_from_generated_at"
MISSING_REQUIRED_QUOTA_PACK_MACHINES_BLOCKER = "missing_required_quota_pack_machines"
QUOTA_PACK_MANIFEST = "analyst_report_quota_pack_manifest.json"


def build_analyst_report_quota_preflight(
    *,
    report_roots: Iterable[str | Path],
    target_date: str | None = None,
    max_daily_requests: int = DEFAULT_MAX_DAILY_REQUESTS,
    required_quota_pack_machines: Iterable[str] | None = None,
    quota_pack_machine_notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    generated_at = date.today().isoformat()
    target = target_date or generated_at
    target_date_matches_generated_at = target == generated_at
    warnings = [QUOTA_SCOPE_WARNING]
    if not target_date_matches_generated_at:
        warnings.append(QUOTA_TARGET_DATE_MISMATCH_WARNING)
    report_root_paths = [Path(root) for root in report_roots]
    report_root_labels = [str(root) for root in report_root_paths]
    quota_pack_provenance = _quota_pack_provenance(report_root_paths)
    required_machines = _unique_nonempty(required_quota_pack_machines or [])
    present_machines = _present_quota_pack_machines(quota_pack_provenance)
    missing_required_machines = [machine for machine in required_machines if machine not in set(present_machines)]
    machine_notes = _quota_pack_machine_note_rows(quota_pack_machine_notes or {})
    scan = _scan_cache_reports(report_roots=report_root_paths, target_date=target)
    rows = scan["rows"]
    counted = [row for row in rows if row["counts_against_quota"]]
    rate_limited = [row for row in rows if row.get("provider_rate_limit")]
    next_retry_values = [
        int(row["retry_after_seconds"])
        for row in rate_limited
        if row.get("retry_after_seconds") is not None
    ]
    blockers: list[str] = []
    if rate_limited:
        blockers.append("provider_rate_limit_observed")
    if len(counted) >= int(max_daily_requests):
        blockers.append("daily_provider_request_budget_exhausted")
    if missing_required_machines:
        blockers.append(MISSING_REQUIRED_QUOTA_PACK_MACHINES_BLOCKER)

    packet = {
        "stage": STAGE,
        "generated_at": generated_at,
        "target_date": target,
        "max_daily_requests": int(max_daily_requests),
        "quota_scope": QUOTA_SCOPE,
        "warnings": warnings,
        "summary": {
            "report_root_count": len(report_root_labels),
            "report_roots": report_root_labels,
            "target_date_matches_generated_at": target_date_matches_generated_at,
            "cache_report_count": len({row["report_path"] for row in rows}),
            "quota_pack_root_count": len(quota_pack_provenance),
            "required_quota_pack_machines": required_machines,
            "present_quota_pack_machines": present_machines,
            "missing_required_quota_pack_machines": missing_required_machines,
            "quota_pack_machine_notes": machine_notes,
            "same_day_window_rows": len(rows),
            "duplicate_evidence_rows": scan["duplicate_evidence_rows"],
            "counted_provider_request_windows": len(counted),
            "rate_limited_windows": len(rate_limited),
            "remaining_request_windows": max(0, int(max_daily_requests) - len(counted)),
            "next_retry_after_seconds": max(next_retry_values) if next_retry_values else None,
        },
        "window_rows": rows,
        "duplicate_window_rows": scan["duplicate_window_rows"],
        "quota_pack_provenance": quota_pack_provenance,
        "decision": {
            "request_allowed": not blockers,
            "blockers": blockers,
            "next_action": _next_action(blockers),
        },
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_analyst_report_quota_preflight_markdown(packet)
    return packet


def write_analyst_report_quota_preflight(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(packet)
    (output_path / "analyst_report_quota_preflight.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "analyst_report_quota_preflight.md").write_text(
        render_analyst_report_quota_preflight_markdown(clean),
        encoding="utf-8",
    )


def render_analyst_report_quota_preflight_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    blockers = _list(decision.get("blockers"))
    warnings = _list(packet.get("warnings"))
    report_roots = _list(summary.get("report_roots"))
    lines = [
        "# Analyst Report Quota Preflight",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Target date: {packet.get('target_date', '')}",
        f"- Max daily requests: {packet.get('max_daily_requests', DEFAULT_MAX_DAILY_REQUESTS)}",
        f"- Quota scope: {packet.get('quota_scope', QUOTA_SCOPE)}",
        f"- Counted provider request windows: {summary.get('counted_provider_request_windows', 0)}",
        f"- Duplicate evidence rows skipped: {summary.get('duplicate_evidence_rows', 0)}",
        f"- Rate-limited windows: {summary.get('rate_limited_windows', 0)}",
        f"- Remaining request windows: {summary.get('remaining_request_windows', 0)}",
        f"- Request allowed: {decision.get('request_allowed', False)}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Warnings",
        "",
    ]
    lines.extend(f"- {warning}" for warning in warnings) if warnings else lines.append("- none")
    lines.extend(
        [
            "",
            "## Report Roots",
            "",
        ]
    )
    lines.extend(f"- {root}" for root in report_roots) if report_roots else lines.append("- none")
    lines.extend(
        [
            "",
            "## Quota Pack Provenance",
            "",
        ]
    )
    pack_provenance = _list_of_dicts(packet.get("quota_pack_provenance"))
    if pack_provenance:
        lines.extend(
            [
                "| Pack Root | Machine | Task | Branch |",
                "|---|---|---|---|",
            ]
        )
        for item in pack_provenance:
            lines.append(
                "| {root} | {machine} | {task} | {branch} |".format(
                    root=item.get("quota_pack_root", ""),
                    machine=item.get("machine", ""),
                    task=item.get("task", ""),
                    branch=item.get("branch", ""),
                )
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Required Quota Pack Machines",
            "",
            f"- Required: {', '.join(_list(summary.get('required_quota_pack_machines'))) or 'none'}",
            f"- Present: {', '.join(_list(summary.get('present_quota_pack_machines'))) or 'none'}",
            f"- Missing: {', '.join(_list(summary.get('missing_required_quota_pack_machines'))) or 'none'}",
            "",
            "## Quota Pack Machine Notes",
            "",
            "This note context is audit-only and does not satisfy required pack evidence.",
        ]
    )
    machine_notes = _list_of_dicts(summary.get("quota_pack_machine_notes"))
    if machine_notes:
        lines.extend(["", "| Machine | Note |", "|---|---|"])
        for item in machine_notes:
            lines.append(f"| {item.get('machine', '')} | {item.get('note', '')} |")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Duplicate Evidence Rows",
            "",
        ]
    )
    duplicates = _list_of_dicts(packet.get("duplicate_window_rows"))
    if duplicates:
        lines.extend(
            [
                "| Kept Report | Duplicate Report | Window | Status |",
                "|---|---|---|---|",
            ]
        )
        for row in duplicates:
            lines.append(
                "| {kept} | {duplicate} | {start}..{end} | {status} |".format(
                    kept=row.get("kept_report_path", ""),
                    duplicate=row.get("duplicate_report_path", ""),
                    start=row.get("window_start", ""),
                    end=row.get("window_end", ""),
                    status=row.get("status", ""),
                )
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Counted Windows",
            "",
            "| Report | Window | Status | Counts | Rate Limit |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in _list_of_dicts(packet.get("window_rows")):
        if not row.get("counts_against_quota") and not row.get("provider_rate_limit"):
            continue
        lines.append(
            "| {path} | {start}..{end} | {status} | {counts} | {limit} |".format(
                path=row.get("report_path", ""),
                start=row.get("window_start", ""),
                end=row.get("window_end", ""),
                status=row.get("status", ""),
                counts=row.get("counts_against_quota", False),
                limit=row.get("provider_rate_limit", "") or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _scan_cache_reports(*, report_roots: Iterable[str | Path], target_date: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in _cache_report_paths(report_roots):
        packet = _load_json(path)
        if packet.get("stage") != "tushare_analyst_report_cache":
            continue
        if packet.get("source") != "tushare_report_rc":
            continue
        if packet.get("generated_at") != target_date:
            continue
        for item in _list_of_dicts(packet.get("rows_by_window")):
            status = str(item.get("status", ""))
            rate_limit = item.get("provider_rate_limit")
            rows.append(
                {
                    "report_path": str(path),
                    "quota_evidence_fingerprint": _row_evidence_fingerprint(path, packet, item),
                    "generated_at": str(packet.get("generated_at", "")),
                    "window_start": str(item.get("window_start", "")),
                    "window_end": str(item.get("window_end", "")),
                    "status": status,
                    "counts_against_quota": status in COUNTED_WINDOW_STATUSES,
                    "provider_rate_limit": str(rate_limit) if rate_limit else "",
                    "retry_after_seconds": item.get("retry_after_seconds"),
                }
            )
    unique_rows: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    duplicate_rows: list[dict[str, Any]] = []
    for row in rows:
        fingerprint = str(row.get("quota_evidence_fingerprint", ""))
        if fingerprint in seen:
            duplicate_rows.append(_duplicate_row(row, seen[fingerprint]))
            continue
        seen[fingerprint] = row
        unique_rows.append(row)
    return {
        "rows": unique_rows,
        "duplicate_evidence_rows": len(rows) - len(unique_rows),
        "duplicate_window_rows": duplicate_rows,
    }


def _quota_pack_provenance(report_roots: Iterable[Path]) -> list[dict[str, Any]]:
    provenance: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for root in report_roots:
        root_path = Path(root)
        if not _is_quota_pack_root(root_path):
            continue
        resolved = root_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        manifest = _load_json(root_path / QUOTA_PACK_MANIFEST)
        source = _dict(manifest.get("provenance"))
        summary = _dict(manifest.get("summary"))
        provenance.append(
            {
                "quota_pack_root": str(root_path),
                "machine": str(source.get("machine", "")),
                "task": str(source.get("task", "")),
                "branch": str(source.get("branch", "")),
                "generated_at": str(manifest.get("generated_at", "")),
                "exported_report_count": int(summary.get("exported_report_count", 0) or 0),
            }
        )
    return provenance


def _present_quota_pack_machines(quota_pack_provenance: Iterable[dict[str, Any]]) -> list[str]:
    return _unique_nonempty(str(item.get("machine", "")) for item in quota_pack_provenance)


def parse_quota_pack_machine_notes(values: Iterable[str] | None) -> dict[str, str]:
    notes: dict[str, str] = {}
    for value in values or []:
        machine, separator, note = str(value).partition("=")
        cleaned_machine = machine.strip()
        cleaned_note = note.strip()
        if not separator or not cleaned_machine or not cleaned_note:
            raise ValueError("--quota-pack-machine-note expects MACHINE=NOTE")
        notes[cleaned_machine] = cleaned_note
    return notes


def _quota_pack_machine_note_rows(notes: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for machine, note in notes.items():
        cleaned_machine = str(machine).strip()
        cleaned_note = str(note).strip()
        if not cleaned_machine or not cleaned_note:
            continue
        rows.append({"machine": cleaned_machine, "note": cleaned_note})
    return rows


def _unique_nonempty(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _next_action(blockers: list[str]) -> str:
    if not blockers:
        return "run_cache_once"
    if MISSING_REQUIRED_QUOTA_PACK_MACHINES_BLOCKER in blockers:
        return "collect_required_quota_pack_evidence"
    return "wait_or_review_provider_quota"


def _duplicate_row(duplicate: dict[str, Any], kept: dict[str, Any]) -> dict[str, Any]:
    return {
        "quota_evidence_fingerprint": str(duplicate.get("quota_evidence_fingerprint", "")),
        "kept_report_path": str(kept.get("report_path", "")),
        "duplicate_report_path": str(duplicate.get("report_path", "")),
        "generated_at": str(duplicate.get("generated_at", "")),
        "window_start": str(duplicate.get("window_start", "")),
        "window_end": str(duplicate.get("window_end", "")),
        "status": str(duplicate.get("status", "")),
        "counts_against_quota": bool(duplicate.get("counts_against_quota", False)),
        "provider_rate_limit": str(duplicate.get("provider_rate_limit", "")),
        "retry_after_seconds": duplicate.get("retry_after_seconds"),
    }


def _row_evidence_fingerprint(path: Path, packet: dict[str, Any], row: dict[str, Any]) -> str:
    report_identity = f"analyst_report_source:{_report_source_fingerprint(path, packet)}"
    evidence = {
        "report_identity": report_identity,
        "generated_at": str(packet.get("generated_at", "")),
        "window_start": str(row.get("window_start", "")),
        "window_end": str(row.get("window_end", "")),
        "status": str(row.get("status", "")),
        "provider_rate_limit": str(row.get("provider_rate_limit", "") or ""),
        "retry_after_seconds": row.get("retry_after_seconds"),
    }
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def _report_source_fingerprint(path: Path, packet: dict[str, Any]) -> str:
    existing = str(packet.get("quota_pack_source_fingerprint", "")).strip()
    if existing:
        return existing
    evidence = {
        "source_path": str(path.resolve()),
        "payload": packet,
    }
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def _cache_report_paths(report_roots: Iterable[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for root in report_roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.name == "tushare_analyst_report_cache.json":
            paths.append(root_path)
        elif root_path.exists():
            include_quota_pack_contents = _is_quota_pack_root(root_path)
            paths.extend(
                path
                for path in root_path.rglob("tushare_analyst_report_cache.json")
                if include_quota_pack_contents or not _is_inside_quota_pack(path)
            )
    return sorted(set(paths))


def _is_quota_pack_root(path: Path) -> bool:
    return path.is_dir() and (path / QUOTA_PACK_MANIFEST).exists()


def _is_inside_quota_pack(path: Path) -> bool:
    return any((parent / QUOTA_PACK_MANIFEST).exists() for parent in path.parents)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
