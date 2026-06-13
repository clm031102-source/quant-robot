from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_3_5_manual_review_gate_rehearsal"


def build_manual_review_rehearsal(
    review_packet: dict[str, Any],
    data_quality: dict[str, Any] | None = None,
    data_gap_resolution: dict[str, Any] | None = None,
    provider_evidence: dict[str, Any] | None = None,
    paper_observation: dict[str, Any] | None = None,
    duplicate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requirements = [
        _research_boundary_requirement(review_packet),
        _manual_gate_requirement(review_packet, data_gap_resolution),
        _data_quality_requirement(data_quality, data_gap_resolution),
        _provider_requirement(provider_evidence, _selected_market(review_packet)),
        _paper_observation_requirement(paper_observation),
        _duplicate_registry_requirement(duplicate_registry),
        _dry_run_boundary_requirement(),
    ]
    blockers = _blockers(review_packet, requirements, data_gap_resolution)
    gate_status = "blocked" if blockers else "ready_for_manual_review_rehearsal"
    rehearsal = {
        "stage": STAGE,
        "safety": _research_only_safety(),
        "gate_status": gate_status,
        "selected_candidate": review_packet.get("selected_candidate"),
        "blockers": blockers,
        "requirements": requirements,
        "dry_run": _dry_run(),
        "summary": _summary(requirements, blockers),
    }
    rehearsal["markdown"] = render_manual_review_rehearsal_markdown(rehearsal)
    return rehearsal


def write_manual_review_rehearsal(output_dir: str | Path, rehearsal: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "manual_review_rehearsal.json").write_text(
        json.dumps(rehearsal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "manual_review_rehearsal.md").write_text(str(rehearsal.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(rehearsal.get("requirements", [])).to_csv(output_path / "manual_review_requirements.csv", index=False)


def render_manual_review_rehearsal_markdown(rehearsal: dict[str, Any]) -> str:
    candidate = rehearsal.get("selected_candidate") if isinstance(rehearsal.get("selected_candidate"), dict) else {}
    dry_run = rehearsal.get("dry_run", {}) if isinstance(rehearsal.get("dry_run"), dict) else {}
    lines = [
        "# Manual Review Gate Rehearsal",
        "",
        f"- Stage: {rehearsal.get('stage', STAGE)}",
        f"- Status: {rehearsal.get('gate_status', 'unknown')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Safety: {rehearsal.get('safety', _research_only_safety())}",
        f"- Broker connection: {dry_run.get('broker_connection', 'disabled')}",
        f"- Account reads: {dry_run.get('account_reads', 'disabled')}",
        f"- Order placement: {dry_run.get('order_placement', 'disabled')}",
        "",
        "## Requirements",
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in rehearsal.get("requirements", []):
        if isinstance(item, dict):
            lines.append(f"| {item.get('label', item.get('requirement_id', 'unknown'))} | {item.get('status', 'unknown')} | {_table_text(item.get('evidence', ''))} |")
    lines.extend(["", "## Blockers", ""])
    for blocker in rehearsal.get("blockers", []):
        lines.append(f"- {blocker}")
    if not rehearsal.get("blockers"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _research_boundary_requirement(review_packet: dict[str, Any]) -> dict[str, str]:
    safety = str(review_packet.get("safety", ""))
    lower = safety.lower()
    ok = "no broker" in lower and "no account" in lower and "no order" in lower
    return _requirement("research_boundary", "Research boundary", "pass" if ok else "block", safety or _research_only_safety())


def _manual_gate_requirement(review_packet: dict[str, Any], data_gap_resolution: dict[str, Any] | None = None) -> dict[str, str]:
    gate = review_packet.get("manual_review_gate", {}) if isinstance(review_packet.get("manual_review_gate"), dict) else {}
    allowed = bool(gate.get("allowed"))
    reasons = _effective_manual_gate_reasons(gate.get("reasons", []), data_gap_resolution)
    return _requirement(
        "manual_live_review_enabled",
        "Manual live review enabled",
        "pass" if allowed else "block",
        "allowed" if allowed else ", ".join(str(reason) for reason in reasons) or "manual_live_review_not_enabled",
    )


def _data_quality_requirement(data_quality: dict[str, Any] | None, data_gap_resolution: dict[str, Any] | None = None) -> dict[str, str]:
    summary = data_quality.get("summary", data_quality) if isinstance(data_quality, dict) else {}
    missing = _int(summary.get("missing_date_rows"), 0) if isinstance(summary, dict) else 0
    duplicate_bars = _int(summary.get("duplicate_bars"), 0) if isinstance(summary, dict) else 0
    zero_volume = _int(summary.get("zero_volume_rows"), 0) if isinstance(summary, dict) else 0
    resolved_missing = _gap_resolution_clears_missing_dates(data_gap_resolution, missing)
    effective_missing = 0 if resolved_missing else missing
    clean = effective_missing == 0 and duplicate_bars == 0 and zero_volume == 0
    resolution_note = ", gap_resolution=non_blocking" if resolved_missing and missing > 0 else ""
    return _requirement(
        "data_quality_clean",
        "Data quality clean",
        "pass" if clean else "block",
        f"missing_date_rows={missing}, duplicate_bars={duplicate_bars}, zero_volume_rows={zero_volume}{resolution_note}",
    )


def _provider_requirement(provider_evidence: dict[str, Any] | None, selected_market: str | None = None) -> dict[str, str]:
    summary = provider_evidence.get("summary", {}) if isinstance(provider_evidence, dict) else {}
    providers = _int(summary.get("providers"), 0) if isinstance(summary, dict) else 0
    ready = _int(summary.get("ready_providers"), 0) if isinstance(summary, dict) else 0
    parquet_ready = bool(summary.get("parquet_ready")) if isinstance(summary, dict) else False
    if selected_market and isinstance(provider_evidence, dict):
        market_rows = [
            row
            for row in provider_evidence.get("market_matrix", [])
            if isinstance(row, dict)
            and str(row.get("market")) == selected_market
            and str(row.get("coverage_status", "")).startswith("implemented")
        ]
        if market_rows:
            market_ready = sum(1 for row in market_rows if bool(row.get("ready")) or row.get("coverage_status") == "implemented_ready")
            ok = market_ready > 0 and parquet_ready
            return _requirement(
                "provider_readiness",
                "Provider readiness",
                "pass" if ok else "block",
                f"market={selected_market}, ready_market_providers={market_ready}/{len(market_rows)}, parquet_ready={parquet_ready}",
            )
    ok = providers > 0 and ready == providers and parquet_ready
    return _requirement(
        "provider_readiness",
        "Provider readiness",
        "pass" if ok else "block",
        f"ready_providers={ready}/{providers}, parquet_ready={parquet_ready}",
    )


def _paper_observation_requirement(paper_observation: dict[str, Any] | None) -> dict[str, str]:
    summary = paper_observation.get("summary", {}) if isinstance(paper_observation, dict) else {}
    observed = _int(summary.get("observed_candidates"), 0) if isinstance(summary, dict) else 0
    completed = _int(summary.get("completed_candidates"), 0) if isinstance(summary, dict) else 0
    return _requirement(
        "paper_observation",
        "Paper observation",
        "pass" if observed > 0 else "warn",
        f"observed_candidates={observed}, completed_candidates={completed}",
    )


def _duplicate_registry_requirement(duplicate_registry: dict[str, Any] | None) -> dict[str, str]:
    summary = duplicate_registry.get("summary", {}) if isinstance(duplicate_registry, dict) else {}
    members = _int(summary.get("duplicate_members"), 0) if isinstance(summary, dict) else 0
    clusters = _int(summary.get("clusters"), 0) if isinstance(summary, dict) else 0
    return _requirement(
        "duplicate_registry_review",
        "Duplicate registry review",
        "pass" if members == 0 else "warn",
        f"duplicate_members={members}, clusters={clusters}",
    )


def _dry_run_boundary_requirement() -> dict[str, str]:
    return _requirement(
        "dry_run_live_boundary",
        "Dry-run live boundary",
        "pass",
        "No broker connection, no account reads, no order placement, no live trading.",
    )


def _blockers(
    review_packet: dict[str, Any],
    requirements: list[dict[str, str]],
    data_gap_resolution: dict[str, Any] | None = None,
) -> list[str]:
    gate = review_packet.get("manual_review_gate", {}) if isinstance(review_packet.get("manual_review_gate"), dict) else {}
    blockers = _effective_manual_gate_reasons(gate.get("reasons", []), data_gap_resolution)
    blockers.extend(f"{item['requirement_id']}_blocked" for item in requirements if item.get("status") == "block")
    return list(dict.fromkeys(blockers))


def _summary(requirements: list[dict[str, str]], blockers: list[str]) -> dict[str, int]:
    return {
        "requirements": len(requirements),
        "passed": sum(1 for item in requirements if item.get("status") == "pass"),
        "warnings": sum(1 for item in requirements if item.get("status") == "warn"),
        "blocked": sum(1 for item in requirements if item.get("status") == "block"),
        "blockers": len(blockers),
    }


def _dry_run() -> dict[str, Any]:
    return {
        "would_cross_live_boundary": False,
        "broker_connection": "disabled",
        "account_reads": "disabled",
        "order_placement": "disabled",
        "live_trading": "disabled",
        "executable": False,
    }


def _requirement(requirement_id: str, label: str, status: str, evidence: str) -> dict[str, str]:
    return {"requirement_id": requirement_id, "label": label, "status": status, "evidence": evidence}


def _selected_market(review_packet: dict[str, Any]) -> str | None:
    candidate = review_packet.get("selected_candidate", {}) if isinstance(review_packet.get("selected_candidate"), dict) else {}
    market = candidate.get("market")
    return str(market) if market else None


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


def _effective_manual_gate_reasons(reasons: object, data_gap_resolution: dict[str, Any] | None) -> list[str]:
    if not isinstance(reasons, list):
        return []
    clears_missing = _gap_resolution_clears_missing_dates(data_gap_resolution, 1)
    rows = []
    for reason in reasons:
        text = str(reason)
        if clears_missing and text in {"missing_dates_present", "data_quality_clean_blocked"}:
            continue
        rows.append(text)
    return rows


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
