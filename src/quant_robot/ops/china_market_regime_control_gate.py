from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any


STAGE = "china_market_regime_control_gate"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_CONTROL_IDS = (
    "policy_liquidity_regime",
    "credit_cycle_proxy",
    "northbound_margin_turnover_temperature",
    "index_location_state",
)


def build_china_market_regime_control_gate(config: dict[str, Any]) -> dict[str, Any]:
    controls = _control_rows(config)
    blockers = _blockers(controls)
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "scope_id": str(config.get("scope_id", "cn_stock_china_market_regime_controls")),
            "total_controls": len(controls),
            "implemented_controls": sum(1 for row in controls if row["implemented"]),
            "blocked_alpha_claim_controls": sum(1 for row in controls if row["standalone_alpha_claim_allowed"]),
            "blocked_fields_count": sum(len(row["blocked_fields"]) for row in controls),
        },
        "control_rows": controls,
        "promotion_policy": {
            "regime_controls_allowed_for_stratification": not blockers,
            "standalone_regime_alpha_claim_allowed": False,
            "portfolio_grid_allowed_from_regime_gate_alone": False,
            "next_required_gate": "candidate_family_specific_pit_ic_and_residual_audit",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_china_market_regime_control_gate_markdown(result)
    return result


def write_china_market_regime_control_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "china_market_regime_control_gate.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "china_market_regime_control_gate.md").write_text(
        render_china_market_regime_control_gate_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "control_rows.csv", result.get("control_rows", []))


def render_china_market_regime_control_gate_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    policy = result.get("promotion_policy", {}) or {}
    lines = [
        "# China Market Regime Control Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Total controls: {summary.get('total_controls', 0)}",
        f"- Implemented controls: {summary.get('implemented_controls', 0)}",
        f"- Blocked alpha-claim controls: {summary.get('blocked_alpha_claim_controls', 0)}",
        f"- Blocked fields count: {summary.get('blocked_fields_count', 0)}",
        f"- Regime controls allowed for stratification: {policy.get('regime_controls_allowed_for_stratification', False)}",
        f"- Standalone regime alpha claim allowed: {policy.get('standalone_regime_alpha_claim_allowed', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Controls",
        "",
    ]
    for row in result.get("control_rows", []):
        lines.append(
            "- {control}: datasets={datasets}; usable={usable}; blocked={blocked}; pit={pit}; alpha_claim={alpha}".format(
                control=row.get("control_id"),
                datasets=", ".join(row.get("dataset_refs", [])),
                usable=", ".join(row.get("usable_fields", [])),
                blocked=", ".join(row.get("blocked_fields", [])) or "none",
                pit=row.get("pit_join_required"),
                alpha=row.get("standalone_alpha_claim_allowed"),
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
        usable_fields = _list(raw.get("usable_fields"))
        blocked_fields = _list(raw.get("blocked_fields"))
        available_date_required = bool(raw.get("available_date_required", False))
        pit_join_required = bool(raw.get("pit_join_required", False))
        standalone_alpha_claim_allowed = bool(raw.get("standalone_alpha_claim_allowed", False))
        rows.append(
            {
                "control_id": control_id,
                "dataset_refs": dataset_refs,
                "usable_fields": usable_fields,
                "blocked_fields": blocked_fields,
                "available_date_required": available_date_required,
                "pit_join_required": pit_join_required,
                "standalone_alpha_claim_allowed": standalone_alpha_claim_allowed,
                "implemented": bool(dataset_refs and usable_fields and available_date_required and pit_join_required and not standalone_alpha_claim_allowed),
            }
        )
    return rows


def _blockers(rows: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in rows:
        control_id = row["control_id"]
        if not row["dataset_refs"]:
            blockers.append(f"missing_dataset_refs:{control_id}")
        if not row["usable_fields"]:
            blockers.append(f"missing_usable_fields:{control_id}")
        if not row["available_date_required"]:
            blockers.append(f"missing_available_date_required:{control_id}")
        if not row["pit_join_required"]:
            blockers.append(f"missing_pit_join_required:{control_id}")
        if row["standalone_alpha_claim_allowed"]:
            blockers.append(f"standalone_alpha_claim_allowed:{control_id}")
    return blockers


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "control_id",
        "dataset_refs",
        "usable_fields",
        "blocked_fields",
        "available_date_required",
        "pit_join_required",
        "standalone_alpha_claim_allowed",
        "implemented",
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


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
