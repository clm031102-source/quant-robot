from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def build_evidence_refresh_plan(
    review_packet: dict[str, Any],
    data_gap_resolution: dict[str, Any] | None = None,
    provider_evidence: dict[str, Any] | None = None,
    duplicate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checklist = _checklist_by_id(review_packet)
    candidate = review_packet.get("selected_candidate") if isinstance(review_packet.get("selected_candidate"), dict) else None
    selected_market = str(candidate.get("market")) if isinstance(candidate, dict) and candidate.get("market") else None
    tracks = [
        _data_quality_track(review_packet, checklist, data_gap_resolution),
        _provider_readiness_track(review_packet, checklist, provider_evidence, selected_market),
        _paper_observation_track(review_packet, checklist),
        _duplicate_resolution_track(review_packet, checklist, duplicate_registry),
        _manual_review_gate_track(review_packet, data_gap_resolution, provider_evidence, selected_market),
    ]
    actions = _ordered_actions(tracks)
    plan = {
        "stage": "phase_3_0_evidence_refresh",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": review_packet.get("stage"),
        "safety": review_packet.get("safety", _research_only_safety()),
        "refresh_status": _refresh_status(candidate, tracks),
        "selected_candidate": candidate,
        "tracks": tracks,
        "ordered_actions": actions,
        "evidence": review_packet.get("evidence", {}),
        "manual_review_gate": review_packet.get("manual_review_gate", {}),
        "review_status": review_packet.get("review_status"),
    }
    plan["markdown"] = render_evidence_refresh_markdown(plan)
    return plan


def write_evidence_refresh_plan(output_dir: str | Path, plan: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "evidence_refresh_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    (output_path / "evidence_refresh_plan.md").write_text(str(plan.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(plan.get("ordered_actions", [])).to_csv(output_path / "evidence_refresh_actions.csv", index=False)


def render_evidence_refresh_markdown(plan: dict[str, Any]) -> str:
    candidate = plan.get("selected_candidate") if isinstance(plan.get("selected_candidate"), dict) else {}
    lines = [
        "# Evidence Refresh Plan",
        "",
        f"- Status: {plan.get('refresh_status', 'unknown')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Market: {candidate.get('market', 'unknown')}",
        f"- Safety: {plan.get('safety', _research_only_safety())}",
        "",
        "## Tracks",
        "",
        "| Track | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for track in plan.get("tracks", []):
        if isinstance(track, dict):
            lines.append(f"| {track.get('label', track.get('track_id', 'unknown'))} | {track.get('status', 'unknown')} | {_table_text(track.get('evidence', ''))} |")
    lines.extend(["", "## Ordered Actions", ""])
    for action in plan.get("ordered_actions", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not plan.get("ordered_actions"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _data_quality_track(
    review_packet: dict[str, Any],
    checklist: dict[str, dict[str, Any]],
    data_gap_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check = checklist.get("data_quality", {})
    evidence = review_packet.get("evidence", {}) if isinstance(review_packet.get("evidence"), dict) else {}
    missing = _int(evidence.get("missing_date_rows"), 0)
    duplicate_bars = _int(evidence.get("duplicate_bars"), 0)
    zero_volume = _int(evidence.get("zero_volume_rows"), 0)
    resolved_missing = _gap_resolution_clears_missing_dates(data_gap_resolution, missing)
    effective_missing = 0 if resolved_missing else missing
    status = "action_required" if check.get("status") == "block" and (effective_missing > 0 or duplicate_bars > 0 or zero_volume > 0) else "clear"
    actions = []
    if status == "action_required":
        actions = [
            _action("data_quality", "List exact missing ETF dates before importing more local files.", "python scripts\\run_data_quality_audit.py --data-root data\\processed\\etf_csv --market CN_ETF --output-dir data\\reports\\data_quality_gap_audit"),
            _action("data_quality", "Refresh local ETF CSV coverage after the missing-date audit identifies gaps.", "python scripts\\batch_import_etf_csv.py --input-dir data\\raw\\tradingview_etf_csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\processed\\etf_csv"),
            _action("data_quality", "Rebuild promotion operations after local quality evidence changes.", "python scripts\\run_promotion_ops.py --output-dir data\\reports\\promotion_ops"),
            _action("data_quality", "Regenerate the review packet after evidence refresh.", "python scripts\\run_promotion_review.py --output-dir data\\reports\\promotion_review"),
        ]
    return _track(
        "data_quality",
        "Data quality refresh",
        status,
        (
            f"missing_date_rows={missing}, duplicate_bars={duplicate_bars}, zero_volume_rows={zero_volume}"
            f"{', gap_resolution=non_blocking' if resolved_missing and missing > 0 else ''}"
        ),
        actions,
    )


def _provider_readiness_track(
    review_packet: dict[str, Any],
    checklist: dict[str, dict[str, Any]],
    provider_evidence: dict[str, Any] | None = None,
    selected_market: str | None = None,
) -> dict[str, Any]:
    check = checklist.get("provider_readiness", {})
    evidence = review_packet.get("evidence", {}) if isinstance(review_packet.get("evidence"), dict) else {}
    current_market = _market_provider_readiness(provider_evidence, selected_market)
    status = "action_required" if check.get("status") == "block" else "clear"
    if current_market is not None:
        status = "clear" if current_market["ready"] else "action_required"
    actions = []
    if status == "action_required":
        actions = [
            _action("provider_readiness", "Build a provider readiness evidence pack for review gating.", "python scripts\\run_provider_evidence.py --output-dir data\\reports\\provider_evidence"),
            _action("provider_readiness", "Check optional package and token readiness locally.", "python scripts\\check_readiness.py"),
            _action("provider_readiness", "Record provider readiness evidence for the next review packet.", "python scripts\\show_provider_status.py"),
        ]
    return _track("provider_readiness", "Provider readiness", status, _provider_evidence(check, evidence, current_market), actions)


def _provider_evidence(check: dict[str, Any], evidence: dict[str, Any], current_market: dict[str, Any] | None = None) -> str:
    if current_market is not None:
        return (
            f"market={current_market['market']}, ready_market_providers={current_market['ready_count']}/{current_market['provider_count']}, "
            f"parquet_ready={current_market['parquet_ready']}"
        )
    check_evidence = check.get("evidence")
    if check_evidence:
        return str(check_evidence)
    if evidence.get("candidate_market_provider_ready") is not None:
        ready = evidence.get("candidate_market_ready_providers")
        total = evidence.get("candidate_market_providers")
        if ready is not None and total is not None:
            return f"candidate market providers ready={ready}/{total}"
        return f"candidate_market_provider_ready={evidence.get('candidate_market_provider_ready')}"
    return f"providers_ready={evidence.get('providers_ready')}"


def _paper_observation_track(review_packet: dict[str, Any], checklist: dict[str, dict[str, Any]]) -> dict[str, Any]:
    check = checklist.get("paper_observation", {})
    candidate = review_packet.get("selected_candidate") if isinstance(review_packet.get("selected_candidate"), dict) else {}
    evidence = review_packet.get("evidence", {}) if isinstance(review_packet.get("evidence"), dict) else {}
    observation_complete = bool(evidence.get("paper_observation_complete"))
    paper_ready = candidate.get("promotion_status") == "paper_ready"
    status = "clear" if observation_complete else "continue" if paper_ready or check.get("status") == "pass" else "action_required"
    actions = []
    if status != "clear":
        actions = [
            _action("paper_observation", "Extend local per-candidate paper evidence with the current candidate search config.", "python scripts\\run_paper_batch.py --config configs\\paper_batch_cn_etf_candidate_search.json"),
            _action("paper_observation", "Summarize paper observation windows, guard events, and risk-profile trends.", "python scripts\\run_paper_observation.py --paper-batch-summary data\\reports\\paper_batch_cn_etf_candidate_search\\paper_batch_summary.json --output-dir data\\reports\\paper_observation"),
            _action("paper_observation", "Rebuild promotion report from refreshed paper evidence.", "python scripts\\run_promotion_report.py --config configs\\promotion_gate_cn_etf_candidate_search.json"),
        ]
    return _track("paper_observation", "Paper observation", status, _paper_evidence(check, evidence), actions)


def _paper_evidence(check: dict[str, Any], evidence: dict[str, Any]) -> str:
    observed = evidence.get("paper_observed_candidates")
    completed = evidence.get("paper_completed_candidates")
    if evidence.get("paper_observation_complete") and observed is not None and completed is not None:
        return f"observed_candidates={observed}, completed_candidates={completed}"
    return str(check.get("evidence", "paper evidence missing"))


def _duplicate_resolution_track(
    review_packet: dict[str, Any],
    checklist: dict[str, dict[str, Any]],
    duplicate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check = checklist.get("duplicate_cluster", {})
    duplicate_clusters = review_packet.get("duplicate_clusters", [])
    registered = _duplicate_registry_present(duplicate_registry)
    has_duplicates = (bool(duplicate_clusters) or check.get("status") in {"warn", "block"}) and not registered
    status = "action_required" if has_duplicates else "clear"
    actions = []
    if status == "action_required":
        actions = [
            _action("duplicate_resolution", "Treat duplicate signal clusters as one canonical edge during evidence review.", "python scripts\\run_promotion_report.py --config configs\\promotion_gate_cn_etf_candidate_search.json"),
            _action("duplicate_resolution", "Build a stable duplicate canonical registry for review and GUI evidence.", "python scripts\\run_duplicate_registry.py --promotion-report data\\reports\\promotion_gate_cn_etf_candidate_search\\promotion_report.json --output-dir data\\reports\\duplicate_registry"),
            _action("duplicate_resolution", "Regenerate operations summary so duplicate clusters remain visible.", "python scripts\\run_promotion_ops.py --output-dir data\\reports\\promotion_ops"),
        ]
    return _track("duplicate_resolution", "Duplicate resolution", status, _duplicate_evidence(check, duplicate_registry), actions)


def _manual_review_gate_track(
    review_packet: dict[str, Any],
    data_gap_resolution: dict[str, Any] | None = None,
    provider_evidence: dict[str, Any] | None = None,
    selected_market: str | None = None,
) -> dict[str, Any]:
    gate = review_packet.get("manual_review_gate", {}) if isinstance(review_packet.get("manual_review_gate"), dict) else {}
    reasons = _effective_manual_gate_reasons(gate.get("reasons", []), data_gap_resolution, provider_evidence, selected_market)
    status = "clear" if gate.get("allowed") or not reasons else "blocked"
    actions = []
    if status == "blocked":
        actions = [
            _action("manual_review_gate", "Rehearse the manual review gate as a local dry run before any API boundary work.", "python scripts\\run_manual_review_rehearsal.py --output-dir data\\reports\\manual_review_rehearsal"),
            _action("manual_review_gate", "Keep manual live review disabled until data quality, provider readiness, and duplicate review are clean.", "python scripts\\run_evidence_refresh.py --output-dir data\\reports\\evidence_refresh"),
        ]
    return _track("manual_review_gate", "Manual review gate", status, ", ".join(reasons) or "allowed", actions)


def _refresh_status(candidate: dict[str, Any] | None, tracks: list[dict[str, Any]]) -> str:
    if candidate is None:
        return "blocked"
    if any(track.get("status") in {"action_required", "blocked", "continue"} for track in tracks):
        return "action_required"
    return "clear"


def _ordered_actions(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for track in tracks:
        if track.get("status") == "clear":
            continue
        ordered.extend(action for action in track.get("actions", []) if isinstance(action, dict))
    return [{**action, "priority": index + 1} for index, action in enumerate(ordered)]


def _checklist_by_id(review_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("check_id")): item
        for item in review_packet.get("checklist", [])
        if isinstance(item, dict)
    }


def _gap_resolution_clears_missing_dates(data_gap_resolution: dict[str, Any] | None, missing_date_rows: int) -> bool:
    if missing_date_rows <= 0 or not isinstance(data_gap_resolution, dict):
        return missing_date_rows == 0
    summary = data_gap_resolution.get("summary", {})
    if not isinstance(summary, dict):
        return False
    gap_rows = _int(summary.get("gap_rows"), 0)
    blocking = _int(summary.get("blocking_gap_rows"), 0)
    blocks_boundary = bool(summary.get("blocks_api_boundary", blocking > 0))
    return gap_rows >= missing_date_rows and blocking == 0 and not blocks_boundary


def _market_provider_readiness(provider_evidence: dict[str, Any] | None, selected_market: str | None) -> dict[str, Any] | None:
    if not selected_market or not isinstance(provider_evidence, dict):
        return None
    summary = provider_evidence.get("summary", {}) if isinstance(provider_evidence.get("summary"), dict) else {}
    parquet_ready = bool(summary.get("parquet_ready"))
    market_rows = [
        row
        for row in provider_evidence.get("market_matrix", [])
        if isinstance(row, dict)
        and str(row.get("market")) == selected_market
        and str(row.get("coverage_status", "")).startswith("implemented")
    ]
    if not market_rows:
        return None
    ready_count = sum(1 for row in market_rows if bool(row.get("ready")) or row.get("coverage_status") == "implemented_ready")
    return {
        "market": selected_market,
        "ready": ready_count > 0 and parquet_ready,
        "ready_count": ready_count,
        "provider_count": len(market_rows),
        "parquet_ready": parquet_ready,
    }


def _duplicate_registry_present(duplicate_registry: dict[str, Any] | None) -> bool:
    if not isinstance(duplicate_registry, dict):
        return False
    summary = duplicate_registry.get("summary", {})
    registry = duplicate_registry.get("canonical_registry", [])
    return isinstance(summary, dict) and (bool(registry) or any(key in summary for key in ("canonical_candidates", "duplicate_members", "clusters")))


def _duplicate_evidence(check: dict[str, Any], duplicate_registry: dict[str, Any] | None) -> str:
    if _duplicate_registry_present(duplicate_registry):
        summary = duplicate_registry.get("summary", {}) if isinstance(duplicate_registry, dict) else {}
        members = _int(summary.get("duplicate_members"), 0) if isinstance(summary, dict) else 0
        clusters = _int(summary.get("clusters"), 0) if isinstance(summary, dict) else 0
        return f"duplicate_members={members}, clusters={clusters}, registry=present"
    return str(check.get("evidence", "no duplicate cluster"))


def _effective_manual_gate_reasons(
    reasons: object,
    data_gap_resolution: dict[str, Any] | None,
    provider_evidence: dict[str, Any] | None,
    selected_market: str | None,
) -> list[str]:
    if not isinstance(reasons, list):
        return []
    clears_missing = _gap_resolution_clears_missing_dates(data_gap_resolution, 1)
    current_market = _market_provider_readiness(provider_evidence, selected_market)
    clears_provider = bool(current_market and current_market.get("ready"))
    rows = []
    for reason in reasons:
        text = str(reason)
        if clears_missing and text in {"missing_dates_present", "data_quality_clean_blocked"}:
            continue
        if clears_provider and text == "providers_not_ready_for_live_review":
            continue
        rows.append(text)
    return rows


def _track(track_id: str, label: str, status: str, evidence: str, actions: list[dict[str, str]]) -> dict[str, Any]:
    return {"track_id": track_id, "label": label, "status": status, "evidence": evidence, "actions": actions}


def _action(track_id: str, reason: str, command: str) -> dict[str, str]:
    return {"track_id": track_id, "reason": reason, "command": command}


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
