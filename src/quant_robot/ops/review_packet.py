from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def build_promotion_review_packet(console: dict[str, Any], candidate_id: str | None = None) -> dict[str, Any]:
    selected = _select_candidate(console, candidate_id)
    checklist = _checklist(console, selected)
    manual_gate = _manual_review_gate(console)
    review_status = _review_status(selected, checklist, manual_gate)
    packet = {
        "stage": "phase_2_9_promotion_review_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": console.get("stage"),
        "source_report": console.get("source_report"),
        "safety": console.get("safety", _research_only_safety()),
        "review_status": review_status,
        "selected_candidate": selected,
        "manual_review_gate": manual_gate,
        "checklist": checklist,
        "live_review_blockers": list(console.get("live_review_blockers", [])),
        "next_actions": list(console.get("next_actions", [])),
        "duplicate_clusters": _candidate_duplicate_clusters(console, selected),
        "duplicate_registry_summary": console.get("duplicate_registry_summary", {}),
        "evidence": console.get("evidence", {}),
        "summary": console.get("summary", {}),
    }
    packet["markdown"] = render_promotion_review_markdown(packet)
    return packet


def write_promotion_review_packet(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "promotion_review_packet.json").write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    (output_path / "promotion_review_packet.md").write_text(str(packet.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(packet.get("checklist", [])).to_csv(output_path / "promotion_review_checklist.csv", index=False)


def render_promotion_review_markdown(packet: dict[str, Any]) -> str:
    candidate = packet.get("selected_candidate") if isinstance(packet.get("selected_candidate"), dict) else {}
    lines = [
        "# Promotion Review Packet",
        "",
        f"- Status: {packet.get('review_status', 'unknown')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Market: {candidate.get('market', 'unknown')}",
        f"- Factor: {candidate.get('factor_name', 'unknown')}",
        f"- Risk profile: {candidate.get('risk_profile_id', 'unknown')}",
        f"- Safety: {packet.get('safety', _research_only_safety())}",
        "",
        "## Candidate Evidence",
        "",
        f"- Promotion status: {candidate.get('promotion_status', 'unknown')}",
        f"- Score: {candidate.get('score', 'unknown')}",
        f"- OOS Sharpe: {candidate.get('test_sharpe', 'unknown')}",
        f"- OOS relative return: {candidate.get('test_relative_return', 'unknown')}",
        f"- OOS trades: {candidate.get('test_trades', 'unknown')}",
        f"- Paper matched: {candidate.get('paper_matched', 'unknown')}",
        f"- Paper Sharpe: {candidate.get('paper_sharpe', 'unknown')}",
        f"- Paper max drawdown: {candidate.get('paper_max_drawdown', 'unknown')}",
        "",
        "## Checklist",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in packet.get("checklist", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"| {item.get('label', item.get('check_id', 'unknown'))} | {item.get('status', 'unknown')} | {_table_text(item.get('evidence', ''))} |")
    lines.extend(["", "## Live Review Gate", ""])
    gate = packet.get("manual_review_gate") if isinstance(packet.get("manual_review_gate"), dict) else {}
    lines.append(f"- Status: {gate.get('status', 'unknown')}")
    reasons = gate.get("reasons", [])
    if reasons:
        lines.append(f"- Reasons: {', '.join(str(reason) for reason in reasons)}")
    duplicate_summary = packet.get("duplicate_registry_summary") if isinstance(packet.get("duplicate_registry_summary"), dict) else {}
    if duplicate_summary:
        lines.extend(["", "## Duplicate Registry", ""])
        lines.append(f"- Canonical candidates: {duplicate_summary.get('canonical_candidates', 0)}")
        lines.append(f"- Duplicate members: {duplicate_summary.get('duplicate_members', 0)}")
        lines.append(f"- Clusters: {duplicate_summary.get('clusters', 0)}")
    lines.extend(["", "## Next Actions", ""])
    for item in packet.get("next_actions", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('action', 'unknown')}: {item.get('reason', '')}")
    if not packet.get("next_actions"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _select_candidate(console: dict[str, Any], candidate_id: str | None) -> dict[str, Any] | None:
    candidates = []
    top = console.get("top_candidate")
    if isinstance(top, dict):
        candidates.append(top)
    candidates.extend(candidate for candidate in console.get("candidates", []) if isinstance(candidate, dict))
    if candidate_id is None:
        return dict(candidates[0]) if candidates else None
    for candidate in candidates:
        if str(candidate.get("case_id")) == candidate_id:
            return dict(candidate)
    return None


def _checklist(console: dict[str, Any], candidate: dict[str, Any] | None) -> list[dict[str, Any]]:
    blockers = set(str(value) for value in console.get("live_review_blockers", []))
    evidence = console.get("evidence", {}) if isinstance(console.get("evidence"), dict) else {}
    return [
        _check(
            "research_boundary",
            "Research boundary",
            "pass" if "No broker" in str(console.get("safety", "")) else "block",
            console.get("safety", _research_only_safety()),
        ),
        _check(
            "provider_readiness",
            "Provider readiness",
            "pass" if _provider_ready(evidence) else "block",
            _provider_evidence(evidence, blockers),
        ),
        _check(
            "data_quality",
            "Data quality",
            "block" if blockers.intersection({"quality_report_missing", "missing_dates_present", "duplicate_bars_present", "zero_volume_rows_present"}) else "pass",
            _quality_evidence(evidence, blockers),
        ),
        _check(
            "walk_forward_evidence",
            "Walk-forward evidence",
            "pass" if candidate and _has_number(candidate.get("test_sharpe")) and int(candidate.get("test_trades") or 0) > 0 else "warn",
            _walk_forward_evidence(candidate),
        ),
        _check(
            "paper_observation",
            "Paper observation",
            "pass" if candidate and candidate.get("paper_matched") else "warn",
            _paper_evidence(candidate),
        ),
        _check(
            "duplicate_cluster",
            "Duplicate cluster",
            _duplicate_status(console, candidate),
            _duplicate_evidence(console, candidate),
        ),
    ]


def _manual_review_gate(console: dict[str, Any]) -> dict[str, Any]:
    blockers = list(console.get("live_review_blockers", []))
    allowed = bool(console.get("live_review_allowed")) and not blockers
    return {"status": "allowed" if allowed else "blocked", "allowed": allowed, "reasons": blockers}


def _review_status(candidate: dict[str, Any] | None, checklist: list[dict[str, Any]], manual_gate: dict[str, Any]) -> str:
    if candidate is None:
        return "missing_candidate"
    if manual_gate.get("allowed"):
        return "ready_for_manual_review"
    if any(item.get("status") == "block" for item in checklist):
        return "blocked"
    if candidate.get("promotion_status") == "paper_ready":
        return "paper_observation"
    return str(candidate.get("promotion_status", "review_required"))


def _candidate_duplicate_clusters(console: dict[str, Any], candidate: dict[str, Any] | None) -> list[dict[str, Any]]:
    if candidate is None:
        return []
    case_id = str(candidate.get("case_id"))
    return [
        cluster
        for cluster in console.get("duplicate_clusters", [])
        if isinstance(cluster, dict) and str(cluster.get("canonical_case_id")) == case_id
    ]


def _duplicate_status(console: dict[str, Any], candidate: dict[str, Any] | None) -> str:
    if candidate is None:
        return "warn"
    if candidate.get("duplicate_of"):
        return "block"
    return "warn" if _candidate_duplicate_clusters(console, candidate) else "pass"


def _duplicate_evidence(console: dict[str, Any], candidate: dict[str, Any] | None) -> str:
    if candidate is None:
        return "no candidate selected"
    if candidate.get("duplicate_of"):
        return f"candidate duplicates {candidate.get('duplicate_of')}"
    clusters = _candidate_duplicate_clusters(console, candidate)
    if not clusters:
        return "no duplicate cluster"
    return "; ".join(f"{cluster.get('duplicate_count', 0)} duplicates" for cluster in clusters)


def _check(check_id: str, label: str, status: str, evidence: object) -> dict[str, str]:
    return {"check_id": check_id, "label": label, "status": status, "evidence": str(evidence)}


def _quality_evidence(evidence: dict[str, Any], blockers: set[str]) -> str:
    parts = [
        f"missing_date_rows={evidence.get('missing_date_rows')}",
        f"duplicate_bars={evidence.get('duplicate_bars')}",
        f"zero_volume_rows={evidence.get('zero_volume_rows')}",
    ]
    data_blockers = sorted(reason for reason in blockers if reason in {"quality_report_missing", "missing_dates_present", "duplicate_bars_present", "zero_volume_rows_present"})
    if data_blockers:
        parts.append(f"blockers={','.join(data_blockers)}")
    return ", ".join(parts)


def _provider_ready(evidence: dict[str, Any]) -> bool:
    return bool(evidence.get("candidate_market_provider_ready") or evidence.get("providers_ready"))


def _provider_evidence(evidence: dict[str, Any], blockers: set[str]) -> str:
    if evidence.get("candidate_market_provider_ready"):
        return (
            "candidate market providers ready="
            f"{evidence.get('candidate_market_ready_providers')}/{evidence.get('candidate_market_providers')}"
        )
    if evidence.get("providers_ready"):
        return "providers ready"
    return ", ".join(sorted(reason for reason in blockers if "provider" in reason)) or "provider readiness is not confirmed"


def _walk_forward_evidence(candidate: dict[str, Any] | None) -> str:
    if candidate is None:
        return "no candidate selected"
    return f"test_sharpe={candidate.get('test_sharpe')}, relative_return={candidate.get('test_relative_return')}, trades={candidate.get('test_trades')}"


def _paper_evidence(candidate: dict[str, Any] | None) -> str:
    if candidate is None:
        return "no candidate selected"
    return f"matched={candidate.get('paper_matched')}, sharpe={candidate.get('paper_sharpe')}, max_drawdown={candidate.get('paper_max_drawdown')}"


def _has_number(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
