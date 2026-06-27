from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_simulation_shortlist_config(config: dict[str, Any], *, repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root)
    blockers: list[str] = []

    holdout = _dict(config.get("final_holdout_2026"))
    if str(holdout.get("status") or "").lower() != "sealed":
        blockers.append("final_holdout_2026_not_sealed")
    if holdout.get("read_once_required") is not True:
        blockers.append("final_holdout_2026_read_once_not_required")

    raw_generation_policy = _dict(config.get("raw_generation_policy"))
    if (
        raw_generation_policy.get("parity_gate_required") is not True
        or raw_generation_policy.get("simulation_event_source_policy")
        != "use_frozen_validated_event_sources_until_raw_generation_parity_passes"
    ):
        blockers.append("raw_generation_policy_missing_or_invalid")
    blocked_generated_sources = {
        _normalize_path(str(_dict(item).get("path") or ""))
        for item in _list(raw_generation_policy.get("blocked_generated_event_sources"))
        if str(_dict(item).get("path") or "")
    }

    candidates = _list(config.get("simulation_candidates"))
    for candidate in candidates:
        candidate_id = str(_dict(candidate).get("id") or "<unknown>")
        row = _dict(candidate)
        if not row.get("formula"):
            blockers.append(f"candidate_missing_formula:{candidate_id}")
        if not isinstance(row.get("evidence"), dict) or not row.get("evidence"):
            blockers.append(f"candidate_missing_evidence:{candidate_id}")
        event_source = _dict(row.get("event_return_source"))
        event_source_path = _normalize_path(str(event_source.get("path") or ""))
        if event_source_path and event_source_path in blocked_generated_sources:
            blockers.append(f"candidate_uses_blocked_generated_event_source:{candidate_id}")

    source_docs = [str(item) for item in _list(config.get("source_docs"))]
    superseded_paths = {str(_dict(item).get("path") or "") for item in _list(config.get("superseded_outputs"))}
    superseded_paths.discard("")
    for source_doc in source_docs:
        if source_doc in superseded_paths:
            blockers.append(f"source_docs_include_superseded_output:{source_doc}")
        if not (root / source_doc).exists():
            blockers.append(f"source_doc_missing:{source_doc}")

    return {
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
        "summary": {
            "candidate_count": len(candidates),
            "source_doc_count": len(source_docs),
            "superseded_output_count": len(superseded_paths),
            "blocked_generated_event_source_count": len(blocked_generated_sources),
            "final_holdout_status": str(holdout.get("status") or ""),
        },
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip()
