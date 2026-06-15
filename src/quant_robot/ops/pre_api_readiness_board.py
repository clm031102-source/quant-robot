from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_0_pre_api_readiness_board"


def build_pre_api_readiness_board(
    review_packet: dict[str, Any],
    data_quality: dict[str, Any] | None = None,
    data_gap_resolution: dict[str, Any] | None = None,
    provider_evidence: dict[str, Any] | None = None,
    provider_remediation: dict[str, Any] | None = None,
    paper_observation: dict[str, Any] | None = None,
    duplicate_registry: dict[str, Any] | None = None,
    manual_rehearsal: dict[str, Any] | None = None,
    evidence_refresh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = [
        _data_quality_item(data_quality, data_gap_resolution),
    ]
    if data_gap_resolution is not None:
        items.append(_data_gap_resolution_item(data_gap_resolution))
    items.extend(
        [
            _provider_item(provider_evidence, _selected_market(review_packet)),
            *([_provider_remediation_item(provider_remediation)] if provider_remediation is not None else []),
            _paper_item(paper_observation),
            _duplicate_item(duplicate_registry),
            _manual_gate_item(review_packet, manual_rehearsal, data_gap_resolution),
            _evidence_refresh_item(evidence_refresh),
            _boundary_item(review_packet, manual_rehearsal),
        ]
    )
    blockers = _blocker_register(items, review_packet, manual_rehearsal, data_gap_resolution)
    actions = _next_actions(evidence_refresh, blockers)
    board = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": _research_only_safety(),
        "overall_status": _overall_status(items, blockers),
        "selected_candidate": review_packet.get("selected_candidate"),
        "summary": _summary(items, blockers, actions),
        "boundary": _boundary(review_packet, manual_rehearsal),
        "readiness_items": items,
        "blocker_register": blockers,
        "next_local_actions": actions,
    }
    board["markdown"] = render_pre_api_readiness_board_markdown(board)
    return board


def write_pre_api_readiness_board(output_dir: str | Path, board: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "pre_api_readiness_board.json").write_text(
        json.dumps(board, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "pre_api_readiness_board.md").write_text(str(board.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(board.get("readiness_items", [])).to_csv(output_path / "pre_api_readiness_items.csv", index=False)
    pd.DataFrame(board.get("blocker_register", [])).to_csv(output_path / "pre_api_blockers.csv", index=False)
    pd.DataFrame(board.get("next_local_actions", [])).to_csv(output_path / "pre_api_next_actions.csv", index=False)


def render_pre_api_readiness_board_markdown(board: dict[str, Any]) -> str:
    candidate = board.get("selected_candidate") if isinstance(board.get("selected_candidate"), dict) else {}
    summary = board.get("summary", {}) if isinstance(board.get("summary"), dict) else {}
    boundary = board.get("boundary", {}) if isinstance(board.get("boundary"), dict) else {}
    lines = [
        "# Pre-API Readiness Board",
        "",
        f"- Stage: {board.get('stage', STAGE)}",
        f"- Status: {board.get('overall_status', 'unknown')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Safety: {board.get('safety', _research_only_safety())}",
        f"- Blockers: {summary.get('blockers', 0)}",
        f"- No broker boundary: {boundary.get('broker_connection', 'disabled')}",
        f"- No account boundary: {boundary.get('account_reads', 'disabled')}",
        f"- No order boundary: {boundary.get('order_placement', 'disabled')}",
        "",
        "## Readiness Items",
        "",
        "| Track | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for item in board.get("readiness_items", []):
        if isinstance(item, dict):
            lines.append(f"| {item.get('label', item.get('track_id', 'unknown'))} | {item.get('status', 'unknown')} | {_table_text(item.get('evidence', ''))} |")
    lines.extend(["", "## Blockers", ""])
    for blocker in board.get("blocker_register", []):
        if isinstance(blocker, dict):
            lines.append(f"- `{blocker.get('blocker_id')}` ({blocker.get('severity')}): {blocker.get('evidence')}")
    if not board.get("blocker_register"):
        lines.append("- none")
    lines.extend(["", "## Next Local Actions", ""])
    for action in board.get("next_local_actions", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not board.get("next_local_actions"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _data_quality_item(data_quality: dict[str, Any] | None, data_gap_resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = data_quality.get("summary", data_quality) if isinstance(data_quality, dict) else {}
    missing = _int(summary.get("missing_date_rows"), 0) if isinstance(summary, dict) else 0
    duplicate_bars = _int(summary.get("duplicate_bars"), 0) if isinstance(summary, dict) else 0
    zero_volume = _int(summary.get("zero_volume_rows"), 0) if isinstance(summary, dict) else 0
    resolved_missing = _gap_resolution_clears_missing_dates(data_gap_resolution, missing)
    effective_missing = 0 if resolved_missing else missing
    status = "pass" if effective_missing == 0 and duplicate_bars == 0 and zero_volume == 0 else "block"
    resolution_note = ", gap_resolution=non_blocking" if resolved_missing and missing > 0 else ""
    return _item(
        "data_quality",
        "Data quality",
        status,
        f"missing_date_rows={missing}, duplicate_bars={duplicate_bars}, zero_volume_rows={zero_volume}{resolution_note}",
    )


def _data_gap_resolution_item(data_gap_resolution: dict[str, Any] | None) -> dict[str, Any]:
    summary = data_gap_resolution.get("summary", {}) if isinstance(data_gap_resolution, dict) else {}
    gap_rows = _int(summary.get("gap_rows"), 0) if isinstance(summary, dict) else 0
    blocking = _int(summary.get("blocking_gap_rows"), 0) if isinstance(summary, dict) else 0
    needs_review = _int(summary.get("needs_review"), 0) if isinstance(summary, dict) else 0
    blocks_boundary = bool(summary.get("blocks_api_boundary")) if isinstance(summary, dict) else blocking > 0
    status = "block" if blocks_boundary or blocking > 0 else "pass"
    return _item(
        "data_gap_resolution",
        "Data gap resolution",
        status,
        f"gap_rows={gap_rows}, blocking_gap_rows={blocking}, needs_review={needs_review}",
    )


def _provider_item(provider_evidence: dict[str, Any] | None, selected_market: str | None = None) -> dict[str, Any]:
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
            status = "pass" if market_ready > 0 and parquet_ready else "block"
            return _item(
                "provider_readiness",
                "Provider readiness",
                status,
                f"market={selected_market}, ready_market_providers={market_ready}/{len(market_rows)}, parquet_ready={parquet_ready}",
            )
    status = "pass" if providers > 0 and ready == providers and parquet_ready else "block"
    return _item("provider_readiness", "Provider readiness", status, f"ready_providers={ready}/{providers}, parquet_ready={parquet_ready}")


def _provider_remediation_item(provider_remediation: dict[str, Any] | None) -> dict[str, Any]:
    summary = provider_remediation.get("summary", {}) if isinstance(provider_remediation, dict) else {}
    remediation_items = _int(summary.get("remediation_items"), 0) if isinstance(summary, dict) else 0
    blocking_items = _int(summary.get("blocking_remediation_items"), remediation_items) if isinstance(summary, dict) else remediation_items
    dependency_items = _int(summary.get("dependency_items"), 0) if isinstance(summary, dict) else 0
    credential_items = _int(summary.get("credential_items"), 0) if isinstance(summary, dict) else 0
    adapter_items = _int(summary.get("adapter_items"), 0) if isinstance(summary, dict) else 0
    storage_items = _int(summary.get("storage_items"), 0) if isinstance(summary, dict) else 0
    blocks_boundary = bool(summary.get("blocks_api_boundary")) if isinstance(summary, dict) else blocking_items > 0
    status = "block" if blocks_boundary or blocking_items > 0 else "pass"
    return _item(
        "provider_remediation",
        "Provider remediation",
        status,
        (
            f"remediation_items={remediation_items}, blocking_remediation_items={blocking_items}, dependency_items={dependency_items}, "
            f"credential_items={credential_items}, adapter_items={adapter_items}, storage_items={storage_items}"
        ),
    )


def _paper_item(paper_observation: dict[str, Any] | None) -> dict[str, Any]:
    summary = paper_observation.get("summary", {}) if isinstance(paper_observation, dict) else {}
    observed = _int(summary.get("observed_candidates"), 0) if isinstance(summary, dict) else 0
    completed = _int(summary.get("completed_candidates"), 0) if isinstance(summary, dict) else 0
    guard_events = _int(summary.get("total_guard_events"), 0) if isinstance(summary, dict) else 0
    status = "pass" if observed > 0 else "warn"
    return _item("paper_observation", "Paper observation", status, f"observed_candidates={observed}, completed_candidates={completed}, guard_events={guard_events}")


def _duplicate_item(duplicate_registry: dict[str, Any] | None) -> dict[str, Any]:
    summary = duplicate_registry.get("summary", {}) if isinstance(duplicate_registry, dict) else {}
    members = _int(summary.get("duplicate_members"), 0) if isinstance(summary, dict) else 0
    clusters = _int(summary.get("clusters"), 0) if isinstance(summary, dict) else 0
    status = "pass" if members == 0 else "warn"
    return _item("duplicate_registry", "Duplicate registry", status, f"duplicate_members={members}, clusters={clusters}")


def _manual_gate_item(
    review_packet: dict[str, Any],
    manual_rehearsal: dict[str, Any] | None,
    data_gap_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = review_packet.get("manual_review_gate", {}) if isinstance(review_packet.get("manual_review_gate"), dict) else {}
    reasons = _effective_manual_gate_reasons(gate.get("reasons", []), data_gap_resolution)
    rehearsal_blockers = _effective_manual_gate_reasons(manual_rehearsal.get("blockers", []) if isinstance(manual_rehearsal, dict) else [], data_gap_resolution)
    rehearsal_status = str(manual_rehearsal.get("gate_status")) if isinstance(manual_rehearsal, dict) else "missing"
    blocked_rehearsal = rehearsal_status == "blocked" and bool(rehearsal_blockers)
    allowed = bool(gate.get("allowed")) or (not reasons and not blocked_rehearsal)
    status = "pass" if allowed and not blocked_rehearsal else "block"
    reason_text = ", ".join(str(reason) for reason in reasons)
    return _item("manual_review_gate", "Manual review gate", status, reason_text or f"rehearsal_status={rehearsal_status}")


def _evidence_refresh_item(evidence_refresh: dict[str, Any] | None) -> dict[str, Any]:
    status = str(evidence_refresh.get("refresh_status")) if isinstance(evidence_refresh, dict) else "missing"
    normalized = "pass" if status == "clear" else "warn"
    actions = evidence_refresh.get("ordered_actions", []) if isinstance(evidence_refresh, dict) else []
    return _item("evidence_refresh", "Evidence refresh", normalized, f"refresh_status={status}, ordered_actions={len(actions) if isinstance(actions, list) else 0}")


def _boundary_item(review_packet: dict[str, Any], manual_rehearsal: dict[str, Any] | None) -> dict[str, Any]:
    boundary = _boundary(review_packet, manual_rehearsal)
    status = "pass" if not boundary["would_cross_live_boundary"] else "block"
    evidence = f"broker_connection={boundary['broker_connection']}, account_reads={boundary['account_reads']}, order_placement={boundary['order_placement']}"
    return _item("research_boundary", "Research boundary", status, evidence)


def _blocker_register(
    items: list[dict[str, Any]],
    review_packet: dict[str, Any],
    manual_rehearsal: dict[str, Any] | None,
    data_gap_resolution: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    blockers = []
    gate = review_packet.get("manual_review_gate", {}) if isinstance(review_packet.get("manual_review_gate"), dict) else {}
    manual_reasons = _consolidated_manual_gate_reasons(
        gate.get("reasons", []),
        manual_rehearsal.get("blockers", []) if isinstance(manual_rehearsal, dict) else [],
        data_gap_resolution,
    )
    for item in items:
        if item.get("status") != "block":
            continue
        if item.get("track_id") == "manual_review_gate" and manual_reasons:
            continue
        blockers.append(_blocker_for_item(item))
    for reason in manual_reasons:
        blockers.append(
            {
                "blocker_id": str(reason),
                "track_id": "manual_review_gate",
                "severity": "block",
                "evidence": str(reason),
                "recommended_command": "python scripts\\run_manual_review_rehearsal.py --output-dir data\\reports\\manual_review_rehearsal",
            }
        )
    return _dedupe_blockers(blockers)


def _blocker_for_item(item: dict[str, Any]) -> dict[str, Any]:
    track_id = str(item.get("track_id"))
    blocker_id = {
        "data_quality": "data_quality_missing_dates",
        "data_gap_resolution": "data_gap_resolution_blocking_gaps",
        "provider_readiness": "provider_readiness_not_ready",
        "provider_remediation": "provider_remediation_items_open",
        "manual_review_gate": "manual_review_gate_blocked",
        "research_boundary": "research_boundary_violation",
    }.get(track_id, f"{track_id}_blocked")
    return {
        "blocker_id": blocker_id,
        "track_id": track_id,
        "severity": "block",
        "evidence": str(item.get("evidence", "")),
        "recommended_command": _recommended_command(track_id),
    }


def _next_actions(evidence_refresh: dict[str, Any] | None, blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = evidence_refresh.get("ordered_actions", []) if isinstance(evidence_refresh, dict) else []
    rows = []
    if isinstance(actions, list) and actions:
        for index, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                continue
            rows.append(
                {
                    "priority": _int(action.get("priority"), index),
                    "track_id": action.get("track_id"),
                    "command": action.get("command"),
                    "reason": action.get("reason"),
                }
            )
        rows = sorted(rows, key=lambda row: _int(row.get("priority"), 999999))
    seen = {str(row.get("command")) for row in rows if row.get("command")}
    next_priority = max((_int(row.get("priority"), 0) for row in rows), default=0) + 1
    for index, blocker in enumerate(blockers, start=1):
        if blocker.get("track_id") == "data_gap_resolution":
            evidence_command = "python scripts\\run_data_gap_evidence.py --output-dir data\\reports\\data_gap_evidence"
            if evidence_command not in seen:
                seen.add(evidence_command)
                rows.append(
                    {
                        "priority": next_priority if actions else index,
                        "track_id": "data_gap_evidence",
                        "command": evidence_command,
                        "reason": "Attach raw CSV and peer-trading evidence before changing data-gap statuses.",
                    }
                )
                next_priority += 1
        command = blocker.get("recommended_command")
        if not command or str(command) in seen:
            continue
        seen.add(str(command))
        rows.append(
            {
                "priority": next_priority if actions else index,
                "track_id": blocker.get("track_id"),
                "command": command,
                "reason": blocker.get("evidence"),
            }
        )
        next_priority += 1
    return rows


def _summary(items: list[dict[str, Any]], blockers: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "readiness_items": len(items),
        "passed": sum(1 for item in items if item.get("status") == "pass"),
        "warnings": sum(1 for item in items if item.get("status") == "warn"),
        "blocked": sum(1 for item in items if item.get("status") == "block"),
        "blockers": len(blockers),
        "next_local_actions": len(actions),
    }


def _overall_status(items: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    if blockers or any(item.get("status") == "block" for item in items):
        return "blocked"
    if any(item.get("status") == "warn" for item in items):
        return "needs_review"
    return "ready_for_api_boundary_planning"


def _boundary(review_packet: dict[str, Any], manual_rehearsal: dict[str, Any] | None) -> dict[str, Any]:
    dry_run = manual_rehearsal.get("dry_run", {}) if isinstance(manual_rehearsal, dict) else {}
    safety = str(review_packet.get("safety", _research_only_safety()))
    would_cross = bool(dry_run.get("would_cross_live_boundary", False))
    if "No broker" not in safety:
        would_cross = True
    return {
        "would_cross_live_boundary": would_cross,
        "broker_connection": dry_run.get("broker_connection", "disabled"),
        "account_reads": dry_run.get("account_reads", "disabled"),
        "order_placement": dry_run.get("order_placement", "disabled"),
        "live_trading": dry_run.get("live_trading", "disabled"),
    }


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


def _consolidated_manual_gate_reasons(
    gate_reasons: object,
    rehearsal_reasons: object,
    data_gap_resolution: dict[str, Any] | None,
) -> list[str]:
    combined = []
    for reason in _effective_manual_gate_reasons(gate_reasons, data_gap_resolution):
        if reason not in combined:
            combined.append(reason)
    for reason in _effective_manual_gate_reasons(rehearsal_reasons, data_gap_resolution):
        if reason not in combined:
            combined.append(reason)
    if "manual_live_review_not_enabled" in combined and "manual_live_review_enabled_blocked" in combined:
        combined = [reason for reason in combined if reason != "manual_live_review_enabled_blocked"]
    return combined


def _item(track_id: str, label: str, status: str, evidence: str) -> dict[str, Any]:
    return {"track_id": track_id, "label": label, "status": status, "evidence": evidence}


def _recommended_command(track_id: str) -> str:
    return {
        "data_quality": "python scripts\\run_data_quality_audit.py --data-root data\\processed\\etf_csv --market CN_ETF --output-dir data\\reports\\data_quality_gap_audit",
        "data_gap_resolution": "python scripts\\run_data_gap_resolution.py --output-dir data\\reports\\data_gap_resolution",
        "provider_readiness": "python scripts\\run_provider_evidence.py --output-dir data\\reports\\provider_evidence",
        "provider_remediation": "python scripts\\run_provider_remediation.py --output-dir data\\reports\\provider_remediation",
        "manual_review_gate": "python scripts\\run_manual_review_rehearsal.py --output-dir data\\reports\\manual_review_rehearsal",
        "research_boundary": "python scripts\\run_project_audit.py --json",
    }.get(track_id, "python scripts\\run_checks.py --execute")


def _dedupe_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    rows = []
    for blocker in blockers:
        key = str(blocker.get("blocker_id"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(blocker)
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
