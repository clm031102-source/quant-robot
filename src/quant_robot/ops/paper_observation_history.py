from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_13_paper_observation_history"


def build_paper_observation_history_pack(activation_gate_packs: list[dict[str, Any]]) -> dict[str, Any]:
    ledger = [_ledger_row(pack) for pack in activation_gate_packs if isinstance(pack, dict)]
    latest = ledger[-1] if ledger else {}
    live_violations = sum(1 for row in ledger if bool(row.get("live_boundary_allowed", False)))
    latest_blockers = _split_blockers(str(latest.get("blockers", ""))) if latest else []
    blockers = ["live_boundary_violation"] if live_violations else latest_blockers
    latest_clear = bool(
        latest
        and latest.get("status") == "paper_observation_ready"
        and latest.get("paper_continuation_allowed")
        and not latest_blockers
    )
    history_clear = latest_clear and live_violations == 0
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "run_count": len(ledger),
            "paper_observation_ready_runs": sum(1 for row in ledger if row.get("status") == "paper_observation_ready"),
            "blocked_runs": sum(1 for row in ledger if row.get("status") != "paper_observation_ready"),
            "live_boundary_violations": live_violations,
            "latest_status": latest.get("status"),
            "latest_required_assets": latest.get("required_asset_ids", []),
            "latest_final_fills": latest.get("final_fills"),
            "latest_required_fills": latest.get("required_fills"),
            "latest_provider_missing_date_rows": latest.get("provider_missing_date_rows"),
        },
        "decision": {
            "history_clear_for_continued_paper_observation": history_clear,
            "blockers": blockers,
            "next_paper_observation_allowed": history_clear,
        },
        "ledger": ledger,
        "next_actions": _next_actions(history_clear, blockers, bool(ledger)),
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["markdown"] = render_paper_observation_history_markdown(pack)
    return _sanitize(pack)


def write_paper_observation_history_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "paper_observation_history_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "paper_observation_history_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("ledger", [])).to_csv(output_path / "paper_observation_history_ledger.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "paper_observation_history_next_actions.csv", index=False)


def render_paper_observation_history_markdown(pack: dict[str, Any]) -> str:
    summary = _dict(pack.get("summary"))
    decision = _dict(pack.get("decision"))
    lines = [
        "# Phase 5.13 Paper Observation History",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Run count: {summary.get('run_count', 0)}",
        f"- Latest status: {summary.get('latest_status')}",
        f"- Latest fills: {summary.get('latest_final_fills')} / {summary.get('latest_required_fills')}",
        f"- Latest required assets: {', '.join(summary.get('latest_required_assets', []) or [])}",
        f"- Provider missing date rows: {summary.get('latest_provider_missing_date_rows')}",
        f"- History clear: {decision.get('history_clear_for_continued_paper_observation', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Ledger",
        "",
        "| Date | Status | Required assets | Fills | Blockers |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("ledger", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('generated_at', '')} | "
                f"{row.get('status', '')} | "
                f"{', '.join(row.get('required_asset_ids', []) or [])} | "
                f"{row.get('final_fills')} / {row.get('required_fills')} | "
                f"{row.get('blockers', '')} |"
            )
    lines.extend(["", "## Next Actions", ""])
    actions = pack.get("next_actions", [])
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _ledger_row(pack: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(pack.get("decision"))
    coverage = _dict(_dict(pack.get("recent_data_refresh")).get("coverage"))
    fills = _dict(_dict(pack.get("final_observation_sufficiency")).get("fills"))
    iterative = _dict(pack.get("iterative_observation_expansion"))
    blockers = _as_list(decision.get("blockers"))
    return {
        "generated_at": pack.get("generated_at"),
        "stage": pack.get("stage"),
        "source": pack.get("source"),
        "mode": pack.get("mode"),
        "status": pack.get("status"),
        "recent_data_ready": bool(decision.get("recent_data_ready", False)),
        "activation_chain_allowed": bool(decision.get("activation_chain_allowed", False)),
        "paper_continuation_allowed": bool(decision.get("paper_continuation_allowed", False)),
        "coverage_scope": coverage.get("coverage_scope"),
        "required_asset_ids": _as_list(coverage.get("required_asset_ids")),
        "expected_trade_dates_count": _int_or_none(coverage.get("expected_trade_dates_count")),
        "required_asset_missing_date_rows": _int(coverage.get("required_asset_missing_date_rows"), 0),
        "provider_missing_date_rows": _int(coverage.get("provider_missing_date_rows"), 0),
        "final_fills": _int_or_none(fills.get("observed_fills")),
        "required_fills": _int_or_none(fills.get("required_fills")),
        "iterative_rounds": _int(iterative.get("round_count"), 0),
        "blockers": " / ".join(blockers),
        "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
    }


def _next_actions(history_clear: bool, blockers: list[str], has_runs: bool) -> list[dict[str, Any]]:
    if not has_runs:
        return [
            {
                "action": "run_tushare_activation_gate",
                "local_only": True,
                "command": "python scripts\\run_tushare_activation_gate.py --machine highspec_desktop --report-dir data\\reports\\tushare_activation_gate --execute",
                "reason": "No paper observation gate runs are available for the history ledger.",
            }
        ]
    if "live_boundary_violation" in blockers:
        return [
            {
                "action": "freeze_and_inspect_live_boundary",
                "local_only": True,
                "reason": "A paper observation artifact reported live boundary access and must be inspected before continuing.",
            }
        ]
    if history_clear:
        return [
            {
                "action": "continue_paper_observation_history",
                "local_only": True,
                "reason": "Latest paper observation gate is clear; continue accumulating paper-only evidence.",
            }
        ]
    return [
        {
            "action": "inspect_latest_paper_observation_blockers",
            "local_only": True,
            "reason": "Latest paper observation gate is not clear; inspect blockers before continuing.",
        }
    ]


def _split_blockers(value: str) -> list[str]:
    return [item.strip() for item in value.split("/") if item.strip()]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


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
