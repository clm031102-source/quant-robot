from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_14_paper_ops_guardrail"
DEFAULT_MIN_LIVE_READINESS_RUNS = 20
DEFAULT_PROVIDER_GAP_WARNING_THRESHOLD = 0


def build_paper_ops_guardrail_pack(
    paper_observation_history_pack: dict[str, Any],
    *,
    min_live_readiness_runs: int = DEFAULT_MIN_LIVE_READINESS_RUNS,
    provider_gap_warning_threshold: int = DEFAULT_PROVIDER_GAP_WARNING_THRESHOLD,
) -> dict[str, Any]:
    summary = _dict(paper_observation_history_pack.get("summary"))
    history_decision = _dict(paper_observation_history_pack.get("decision"))
    run_count = _int(summary.get("run_count"), 0)
    ready_runs = _int(summary.get("paper_observation_ready_runs"), 0)
    provider_missing = _int(summary.get("latest_provider_missing_date_rows"), 0)
    live_violations = _int(summary.get("live_boundary_violations"), 0)
    history_clear = bool(history_decision.get("history_clear_for_continued_paper_observation", False))
    history_blockers = _as_list(history_decision.get("blockers"))

    blockers = _blockers(history_clear, history_blockers, live_violations)
    warnings = _warnings(
        run_count=run_count,
        ready_runs=ready_runs,
        provider_missing=provider_missing,
        min_live_readiness_runs=min_live_readiness_runs,
        provider_gap_warning_threshold=provider_gap_warning_threshold,
    )
    continued_paper_allowed = not blockers and history_clear
    live_readiness_candidate = continued_paper_allowed and not warnings and ready_runs >= min_live_readiness_runs
    status = _status(blockers, warnings)
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source_stage": paper_observation_history_pack.get("stage"),
        "summary": {
            "history_run_count": run_count,
            "paper_observation_ready_runs": ready_runs,
            "min_live_readiness_runs": min_live_readiness_runs,
            "ready_run_deficit_for_live_readiness": max(0, min_live_readiness_runs - ready_runs),
            "latest_status": summary.get("latest_status"),
            "latest_required_assets": summary.get("latest_required_assets", []),
            "latest_final_fills": summary.get("latest_final_fills"),
            "latest_required_fills": summary.get("latest_required_fills"),
            "latest_provider_missing_date_rows": provider_missing,
            "provider_gap_warning_threshold": provider_gap_warning_threshold,
            "live_boundary_violations": live_violations,
        },
        "decision": {
            "continued_paper_observation_allowed": continued_paper_allowed,
            "live_readiness_candidate": live_readiness_candidate,
            "blockers": blockers,
            "warnings": warnings,
        },
        "checks": _checks(
            history_clear=history_clear,
            live_violations=live_violations,
            ready_runs=ready_runs,
            min_live_readiness_runs=min_live_readiness_runs,
            provider_missing=provider_missing,
            provider_gap_warning_threshold=provider_gap_warning_threshold,
        ),
        "next_actions": _next_actions(status, blockers, warnings),
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["markdown"] = render_paper_ops_guardrail_markdown(pack)
    return _sanitize(pack)


def write_paper_ops_guardrail_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "paper_ops_guardrail_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "paper_ops_guardrail_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("checks", [])).to_csv(output_path / "paper_ops_guardrail_checks.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "paper_ops_guardrail_next_actions.csv", index=False)


def render_paper_ops_guardrail_markdown(pack: dict[str, Any]) -> str:
    summary = _dict(pack.get("summary"))
    decision = _dict(pack.get("decision"))
    lines = [
        "# Phase 5.14 Paper Ops Guardrail",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status')}",
        f"- Continued paper observation allowed: {decision.get('continued_paper_observation_allowed', False)}",
        f"- Live readiness candidate: {decision.get('live_readiness_candidate', False)}",
        f"- Ready runs: {summary.get('paper_observation_ready_runs')} / {summary.get('min_live_readiness_runs')}",
        f"- Provider missing date rows: {summary.get('latest_provider_missing_date_rows')}",
        f"- Live boundary violations: {summary.get('live_boundary_violations')}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Checks",
        "",
        "| Check | Status | Observed | Threshold | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("checks", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('check_id', '')} | "
                f"{row.get('status', '')} | "
                f"{row.get('observed_value', '')} | "
                f"{row.get('threshold', '')} | "
                f"{row.get('reason', '')} |"
            )
    lines.extend(["", "## Next Actions", ""])
    actions = pack.get("next_actions", [])
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _blockers(history_clear: bool, history_blockers: list[str], live_violations: int) -> list[str]:
    if live_violations > 0:
        return ["live_boundary_violation"]
    if history_clear:
        return []
    blockers = ["history_not_clear"]
    for item in history_blockers:
        if item not in blockers:
            blockers.append(item)
    return blockers


def _warnings(
    *,
    run_count: int,
    ready_runs: int,
    provider_missing: int,
    min_live_readiness_runs: int,
    provider_gap_warning_threshold: int,
) -> list[str]:
    warnings = []
    if run_count < min_live_readiness_runs or ready_runs < min_live_readiness_runs:
        warnings.append("short_paper_history")
    if provider_missing > provider_gap_warning_threshold:
        warnings.append("provider_missing_date_rows")
    return warnings


def _checks(
    *,
    history_clear: bool,
    live_violations: int,
    ready_runs: int,
    min_live_readiness_runs: int,
    provider_missing: int,
    provider_gap_warning_threshold: int,
) -> list[dict[str, Any]]:
    return [
        _check(
            "history_clear",
            "pass" if history_clear else "block",
            history_clear,
            True,
            "Latest paper observation history must be clear before paper operations continue.",
        ),
        _check(
            "live_boundary_disabled",
            "pass" if live_violations == 0 else "block",
            live_violations,
            0,
            "Any live-boundary violation freezes paper operations review.",
        ),
        _check(
            "paper_history_depth",
            "pass" if ready_runs >= min_live_readiness_runs else "warn",
            ready_runs,
            min_live_readiness_runs,
            "Live-readiness discussion needs many consecutive paper-ready observations.",
        ),
        _check(
            "provider_missing_date_rows",
            "pass" if provider_missing <= provider_gap_warning_threshold else "warn",
            provider_missing,
            provider_gap_warning_threshold,
            "Provider-level data gaps should be reduced before expanding automation.",
        ),
    ]


def _check(check_id: str, status: str, observed_value: Any, threshold: Any, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "observed_value": observed_value,
        "threshold": threshold,
        "reason": reason,
    }


def _status(blockers: list[str], warnings: list[str]) -> str:
    if blockers:
        return "paper_ops_blocked"
    if warnings:
        return "paper_ops_watch"
    return "paper_ops_ready"


def _next_actions(status: str, blockers: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    if status == "paper_ops_blocked":
        return [
            {
                "action": "inspect_paper_ops_blockers",
                "local_only": True,
                "reason": f"Paper operations guardrail is blocked by: {' / '.join(blockers)}.",
            }
        ]
    if "short_paper_history" in warnings:
        return [
            {
                "action": "continue_accumulating_paper_observation_history",
                "local_only": True,
                "reason": "More paper-ready observations are required before any live-readiness discussion.",
            }
        ]
    if "provider_missing_date_rows" in warnings:
        return [
            {
                "action": "reduce_provider_data_gaps",
                "local_only": True,
                "reason": "Provider-level missing date rows remain above the warning threshold.",
            }
        ]
    return [
        {
            "action": "prepare_manual_live_readiness_review",
            "local_only": True,
            "reason": "Paper operations guardrail is clear; prepare a manual review packet before any live-boundary design.",
        }
    ]


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
