from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_3_4_duplicate_canonical_registry"


def build_duplicate_registry(promotion_report: dict[str, Any]) -> dict[str, Any]:
    candidates = _sorted_candidates(promotion_report.get("candidates", []))
    duplicate_members = [_duplicate_member(row) for row in candidates if row.get("duplicate_of")]
    by_canonical: dict[str, list[dict[str, Any]]] = {}
    for member in duplicate_members:
        by_canonical.setdefault(str(member["canonical_case_id"]), []).append(member)
    canonical_registry = _canonical_rows(candidates, by_canonical)
    registry = {
        "stage": STAGE,
        "safety": _research_only_safety(),
        "summary": _summary(candidates, canonical_registry, duplicate_members),
        "canonical_registry": canonical_registry,
        "duplicate_members": duplicate_members,
    }
    registry["markdown"] = render_duplicate_registry_markdown(registry)
    return registry


def write_duplicate_registry(output_dir: str | Path, registry: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "duplicate_canonical_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "duplicate_canonical_registry.md").write_text(str(registry.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(registry.get("canonical_registry", [])).to_csv(output_path / "canonical_candidates.csv", index=False)
    pd.DataFrame(registry.get("duplicate_members", [])).to_csv(output_path / "duplicate_members.csv", index=False)


def render_duplicate_registry_markdown(registry: dict[str, Any]) -> str:
    summary = registry.get("summary", {}) if isinstance(registry.get("summary"), dict) else {}
    lines = [
        "# Duplicate Canonical Registry",
        "",
        f"- Stage: {registry.get('stage', STAGE)}",
        f"- Safety: {registry.get('safety', _research_only_safety())}",
        f"- Canonical candidates: {summary.get('canonical_candidates', 0)}",
        f"- Duplicate members: {summary.get('duplicate_members', 0)}",
        f"- Clusters: {summary.get('clusters', 0)}",
        "",
        "## Canonical Candidates",
        "",
        "| Canonical | Status | Score | Duplicates | Members |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in registry.get("canonical_registry", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('canonical_case_id', 'unknown')} | "
                f"{row.get('promotion_status', 'unknown')} | "
                f"{row.get('score', 0.0)} | "
                f"{row.get('duplicate_count', 0)} | "
                f"{_join(row.get('duplicate_members', []))} |"
            )
    lines.extend(
        [
            "",
            "## Duplicate Members",
            "",
            "| Duplicate | Canonical | Similarity | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in registry.get("duplicate_members", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('duplicate_case_id', 'unknown')} | "
                f"{row.get('canonical_case_id', 'unknown')} | "
                f"{row.get('duplicate_similarity', 0.0)} | "
                f"{row.get('suppression_reason', 'unknown')} |"
            )
    return "\n".join(lines) + "\n"


def _canonical_rows(candidates: list[dict[str, Any]], by_canonical: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    canonical_ids = set()
    for candidate in candidates:
        if candidate.get("duplicate_of"):
            continue
        case_id = str(candidate.get("case_id", "unknown"))
        canonical_ids.add(case_id)
        members = sorted(by_canonical.get(case_id, []), key=lambda row: (_int(row.get("duplicate_rank"), 999999), str(row.get("duplicate_case_id"))))
        rows.append(
            {
                "canonical_case_id": case_id,
                "canonical_rank": _int(candidate.get("promotion_rank"), 999999),
                "market": candidate.get("market"),
                "factor_name": candidate.get("factor_name"),
                "promotion_status": candidate.get("promotion_status"),
                "score": _float(candidate.get("score")),
                "duplicate_count": len(members),
                "duplicate_members": [str(member.get("duplicate_case_id")) for member in members],
                "canonical_reason": "non_duplicate_candidate",
            }
        )
    missing_canonicals = sorted(set(by_canonical) - canonical_ids)
    for case_id in missing_canonicals:
        members = by_canonical[case_id]
        rows.append(
            {
                "canonical_case_id": case_id,
                "canonical_rank": None,
                "market": members[0].get("market") if members else None,
                "factor_name": None,
                "promotion_status": "missing_canonical",
                "score": 0.0,
                "duplicate_count": len(members),
                "duplicate_members": [str(member.get("duplicate_case_id")) for member in members],
                "canonical_reason": "referenced_by_duplicate_only",
            }
        )
    return sorted(rows, key=lambda row: (_int(row.get("canonical_rank"), 999999), str(row.get("canonical_case_id"))))


def _duplicate_member(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "duplicate_case_id": str(candidate.get("case_id", "unknown")),
        "canonical_case_id": str(candidate.get("duplicate_of")),
        "duplicate_rank": _int(candidate.get("promotion_rank"), 999999),
        "market": candidate.get("market"),
        "factor_name": candidate.get("factor_name"),
        "promotion_status": candidate.get("promotion_status"),
        "duplicate_similarity": _float(candidate.get("duplicate_similarity")),
        "suppression_reason": _suppression_reason(candidate),
        "blocking_reasons": list(candidate.get("blocking_reasons", [])) if isinstance(candidate.get("blocking_reasons"), list) else [],
        "warnings": list(candidate.get("warnings", [])) if isinstance(candidate.get("warnings"), list) else [],
    }


def _summary(
    candidates: list[dict[str, Any]],
    canonical_registry: list[dict[str, Any]],
    duplicate_members: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "candidates": len(candidates),
        "canonical_candidates": len(canonical_registry),
        "duplicate_members": len(duplicate_members),
        "clusters": sum(1 for row in canonical_registry if _int(row.get("duplicate_count"), 0) > 0),
        "suppressed_duplicates": sum(1 for row in duplicate_members if row.get("suppression_reason")),
    }


def _suppression_reason(candidate: dict[str, Any]) -> str:
    blocking = candidate.get("blocking_reasons", [])
    if isinstance(blocking, list):
        for reason in blocking:
            if "duplicate" in str(reason):
                return str(reason)
    warnings = candidate.get("warnings", [])
    if isinstance(warnings, list):
        for warning in warnings:
            if "duplicate" in str(warning):
                return str(warning)
    return f"duplicate_of:{candidate.get('duplicate_of')}"


def _sorted_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = [row for row in value if isinstance(row, dict)]
    return sorted(rows, key=lambda row: (_int(row.get("promotion_rank"), 999999), str(row.get("case_id"))))


def _join(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return ", ".join(str(value) for value in values)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
