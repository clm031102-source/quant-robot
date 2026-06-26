from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any


STAGE = "event_factor_control_gate"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_CONTROL_IDS = (
    "earnings_forecast_events",
    "dividend_ex_right_events",
    "buyback_holder_change_unlock_events",
)
ALLOWED_CONTROL_ACTIONS = {"hibernate", "controlled_retest_only", "coverage_blocked"}


def build_event_factor_control_gate(config: dict[str, Any]) -> dict[str, Any]:
    rows = _control_rows(config)
    blockers = _blockers(rows)
    passes = not blockers
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": passes,
            "blockers": blockers,
            "scope_id": str(config.get("scope_id", "cn_stock_event_factor_controls")),
            "total_controls": len(rows),
            "closed_controls": sum(1 for row in rows if row["closed"]),
            "hibernated_controls": sum(1 for row in rows if row["control_action"] == "hibernate"),
            "coverage_blocked_controls": sum(1 for row in rows if row["control_action"] == "coverage_blocked"),
            "controlled_retest_only_controls": sum(
                1 for row in rows if row["control_action"] == "controlled_retest_only"
            ),
            "blocked_endpoint_count": sum(len(row["blocked_endpoints"]) for row in rows),
        },
        "control_rows": rows,
        "promotion_policy": {
            "event_controls_closed": passes,
            "non_event_direct_factor_generation_allowed": passes,
            "event_factor_generation_allowed": False,
            "event_factor_portfolio_grid_allowed": False,
            "standalone_event_alpha_claim_allowed": False,
            "next_required_gate": "candidate_family_specific_preregistration_and_pit_residual_ic_audit",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_event_factor_control_gate_markdown(result)
    return result


def write_event_factor_control_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_factor_control_gate.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_factor_control_gate.md").write_text(
        render_event_factor_control_gate_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "event_control_rows.csv", result.get("control_rows", []))


def render_event_factor_control_gate_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    policy = _dict(result.get("promotion_policy"))
    lines = [
        "# Event Factor Control Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Total controls: {summary.get('total_controls', 0)}",
        f"- Closed controls: {summary.get('closed_controls', 0)}",
        f"- Hibernated controls: {summary.get('hibernated_controls', 0)}",
        f"- Coverage-blocked controls: {summary.get('coverage_blocked_controls', 0)}",
        f"- Controlled-retest-only controls: {summary.get('controlled_retest_only_controls', 0)}",
        f"- Blocked endpoint count: {summary.get('blocked_endpoint_count', 0)}",
        f"- Non-event direct factor generation allowed: {policy.get('non_event_direct_factor_generation_allowed', False)}",
        f"- Event factor generation allowed: {policy.get('event_factor_generation_allowed', False)}",
        f"- Event factor portfolio grid allowed: {policy.get('event_factor_portfolio_grid_allowed', False)}",
        f"- Standalone event alpha claim allowed: {policy.get('standalone_event_alpha_claim_allowed', False)}",
        f"- Blockers: {', '.join(_list(summary.get('blockers'))) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Controls",
        "",
    ]
    for row in _list_of_dicts(result.get("control_rows")):
        lines.append(
            "- {control}: action={action}; family_mining={family}; usable={usable}; blocked={blocked}; pit={pit}; neutral={neutral}".format(
                control=row.get("control_id"),
                action=row.get("control_action"),
                family=row.get("family_mining_allowed"),
                usable=", ".join(_list(row.get("usable_endpoints"))) or "none",
                blocked=", ".join(_list(row.get("blocked_endpoints"))) or "none",
                pit=row.get("pit_signal_date_audit_required"),
                neutral=row.get("neutralized_ic_audit_required"),
            )
        )
    return "\n".join(lines) + "\n"


def _control_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    configured = [row for row in config.get("controls", []) if isinstance(row, dict)]
    by_id = {str(row.get("control_id", "")): row for row in configured}
    rows = []
    for control_id in REQUIRED_CONTROL_IDS:
        raw = by_id.get(control_id, {})
        dataset_refs = _list(raw.get("dataset_refs"))
        usable_endpoints = _list(raw.get("usable_endpoints"))
        blocked_endpoints = _list(raw.get("blocked_endpoints"))
        control_action = str(raw.get("control_action", "")).strip()
        family_mining_allowed = bool(raw.get("family_mining_allowed", False))
        pit_signal_date_audit_required = bool(raw.get("pit_signal_date_audit_required", False))
        neutralized_ic_audit_required = bool(raw.get("neutralized_ic_audit_required", False))
        standalone_alpha_claim_allowed = bool(raw.get("standalone_alpha_claim_allowed", False))
        evidence = str(raw.get("evidence", "")).strip()
        next_action = str(raw.get("next_action", "")).strip()
        rows.append(
            {
                "control_id": control_id,
                "dataset_refs": dataset_refs,
                "usable_endpoints": usable_endpoints,
                "blocked_endpoints": blocked_endpoints,
                "control_action": control_action,
                "family_mining_allowed": family_mining_allowed,
                "pit_signal_date_audit_required": pit_signal_date_audit_required,
                "neutralized_ic_audit_required": neutralized_ic_audit_required,
                "standalone_alpha_claim_allowed": standalone_alpha_claim_allowed,
                "evidence": evidence,
                "next_action": next_action,
                "closed": bool(
                    dataset_refs
                    and control_action in ALLOWED_CONTROL_ACTIONS
                    and pit_signal_date_audit_required
                    and neutralized_ic_audit_required
                    and not standalone_alpha_claim_allowed
                    and evidence
                    and next_action
                    and not family_mining_allowed
                ),
            }
        )
    return rows


def _blockers(rows: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in rows:
        control_id = row["control_id"]
        if not row["dataset_refs"]:
            blockers.append(f"missing_dataset_refs:{control_id}")
        if row["control_action"] not in ALLOWED_CONTROL_ACTIONS:
            blockers.append(f"invalid_control_action:{control_id}:{row['control_action']}")
        if not row["pit_signal_date_audit_required"]:
            blockers.append(f"missing_pit_signal_date_audit:{control_id}")
        if not row["neutralized_ic_audit_required"]:
            blockers.append(f"missing_neutralized_ic_audit:{control_id}")
        if row["standalone_alpha_claim_allowed"]:
            blockers.append(f"standalone_event_alpha_claim_allowed:{control_id}")
        if row["family_mining_allowed"]:
            blockers.append(f"event_family_mining_still_allowed:{control_id}")
        if row["blocked_endpoints"] and row["family_mining_allowed"]:
            blockers.append(f"blocked_endpoints_must_block_family:{control_id}")
        if not row["evidence"]:
            blockers.append(f"missing_control_evidence:{control_id}")
        if not row["next_action"]:
            blockers.append(f"missing_next_action:{control_id}")
    return blockers


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "control_id",
        "dataset_refs",
        "usable_endpoints",
        "blocked_endpoints",
        "control_action",
        "family_mining_allowed",
        "pit_signal_date_audit_required",
        "neutralized_ic_audit_required",
        "standalone_alpha_claim_allowed",
        "evidence",
        "next_action",
        "closed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: "|".join(row[key]) if isinstance(row.get(key), list) else row.get(key)
                    for key in fieldnames
                }
            )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
