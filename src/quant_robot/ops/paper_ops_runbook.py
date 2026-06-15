from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_15_paper_ops_runbook"


def build_paper_ops_runbook_pack(paper_ops_guardrail_pack: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(paper_ops_guardrail_pack.get("decision"))
    guardrail_summary = _dict(paper_ops_guardrail_pack.get("summary"))
    guardrail_blockers = _as_list(decision.get("blockers"))
    guardrail_warnings = _as_list(decision.get("warnings"))
    continued_allowed = bool(decision.get("continued_paper_observation_allowed", False))
    live_candidate = bool(decision.get("live_readiness_candidate", False))
    live_boundary_violation = bool(paper_ops_guardrail_pack.get("live_boundary_allowed", False))
    blockers = _blockers(continued_allowed, guardrail_blockers, live_boundary_violation)
    paper_cycle_allowed = continued_allowed and not blockers
    command_queue = _paper_cycle_commands() if paper_cycle_allowed else _blocked_commands(blockers)
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "paper_cycle_ready" if paper_cycle_allowed else "paper_cycle_blocked",
        "source_stage": paper_ops_guardrail_pack.get("stage"),
        "summary": {
            "guardrail_status": paper_ops_guardrail_pack.get("status"),
            "history_run_count": guardrail_summary.get("history_run_count"),
            "paper_observation_ready_runs": guardrail_summary.get("paper_observation_ready_runs"),
            "ready_run_deficit_for_live_readiness": guardrail_summary.get("ready_run_deficit_for_live_readiness"),
            "latest_required_assets": guardrail_summary.get("latest_required_assets", []),
            "latest_provider_missing_date_rows": guardrail_summary.get("latest_provider_missing_date_rows"),
            "guardrail_warnings": guardrail_warnings,
            "command_count": len(command_queue),
        },
        "decision": {
            "paper_cycle_allowed": paper_cycle_allowed,
            "live_cycle_allowed": False,
            "live_readiness_candidate": live_candidate,
            "blockers": blockers,
            "warnings": guardrail_warnings,
        },
        "command_queue": command_queue,
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["markdown"] = render_paper_ops_runbook_markdown(pack)
    return _sanitize(pack)


def write_paper_ops_runbook_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "paper_ops_runbook_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "paper_ops_runbook_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("command_queue", [])).to_csv(output_path / "paper_ops_runbook_commands.csv", index=False)


def render_paper_ops_runbook_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    summary = _dict(pack.get("summary"))
    lines = [
        "# Phase 5.15 Paper Ops Runbook",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status')}",
        f"- Paper cycle allowed: {decision.get('paper_cycle_allowed', False)}",
        f"- Live cycle allowed: {decision.get('live_cycle_allowed', False)}",
        f"- Guardrail status: {summary.get('guardrail_status')}",
        f"- Command count: {summary.get('command_count', 0)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Command Queue",
        "",
        "| Order | Action | Command | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for row in pack.get("command_queue", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('order', '')} | "
                f"{row.get('action', '')} | "
                f"`{row.get('command', '')}` | "
                f"{row.get('reason', '')} |"
            )
    return "\n".join(lines) + "\n"


def _paper_cycle_commands() -> list[dict[str, Any]]:
    return [
        _command(
            1,
            "check_tushare_readiness",
            "python scripts\\check_readiness.py",
            "Confirm optional data-provider readiness before starting a paper-only cycle.",
        ),
        _command(
            2,
            "run_tushare_activation_gate",
            "python scripts\\run_tushare_activation_gate.py --report-dir data\\reports\\tushare_activation_gate --execute",
            "Refresh required recent data and rerun the paper activation chain.",
        ),
        _command(
            3,
            "update_paper_observation_history",
            "python scripts\\run_paper_observation_history.py --activation-gate-pack data\\reports\\tushare_activation_gate\\tushare_activation_gate_pack.json --output-dir data\\reports\\paper_observation_history",
            "Append the latest paper activation evidence into the paper observation history artifact.",
        ),
        _command(
            4,
            "update_paper_ops_guardrail",
            "python scripts\\run_paper_ops_guardrail.py --paper-observation-history data\\reports\\paper_observation_history\\paper_observation_history_pack.json --output-dir data\\reports\\paper_ops_guardrail",
            "Recompute the paper operations guardrail from the updated history.",
        ),
    ]


def _blocked_commands(blockers: list[str]) -> list[dict[str, Any]]:
    return [
        _command(
            1,
            "inspect_paper_ops_guardrail_blockers",
            "python scripts\\run_paper_ops_guardrail.py",
            f"Paper cycle is blocked by: {' / '.join(blockers) if blockers else 'unknown'}; inspect guardrail before running a paper cycle.",
        )
    ]


def _command(order: int, action: str, command: str, reason: str) -> dict[str, Any]:
    return {
        "order": order,
        "action": action,
        "command": command,
        "reason": reason,
        "local_only": True,
        "requires_manual_start": True,
        "live_boundary_allowed": False,
    }


def _blockers(continued_allowed: bool, guardrail_blockers: list[str], live_boundary_violation: bool) -> list[str]:
    if live_boundary_violation:
        return ["live_boundary_violation"]
    if continued_allowed:
        return []
    return guardrail_blockers or ["paper_ops_guardrail_not_clear"]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
