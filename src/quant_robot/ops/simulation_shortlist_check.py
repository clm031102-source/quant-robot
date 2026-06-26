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

    candidates = _list(config.get("simulation_candidates"))
    for candidate in candidates:
        candidate_id = str(_dict(candidate).get("id") or "<unknown>")
        row = _dict(candidate)
        if not row.get("formula"):
            blockers.append(f"candidate_missing_formula:{candidate_id}")
        if not isinstance(row.get("evidence"), dict) or not row.get("evidence"):
            blockers.append(f"candidate_missing_evidence:{candidate_id}")

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
            "final_holdout_status": str(holdout.get("status") or ""),
        },
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
