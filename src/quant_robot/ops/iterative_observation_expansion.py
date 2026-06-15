from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_11_iterative_observation_expansion"


def build_iterative_observation_expansion_pack(
    initial_observation_sufficiency: dict[str, Any],
    *,
    rounds: list[dict[str, Any]] | None = None,
    max_rounds: int = 3,
    expansion_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    round_rows = rounds or []
    final_round = round_rows[-1] if round_rows else {}
    final_expanded = _dict(final_round.get("expanded_observation_replay"))
    final_sufficiency = _dict(final_expanded.get("final_observation_sufficiency"))
    final_decision = _dict(final_sufficiency.get("decision"))
    cleared = bool(final_decision.get("observation_sufficiency_cleared", False))
    initial_extendable = _can_extend(initial_observation_sufficiency)

    if expansion_error:
        status = "expansion_failed"
    elif not initial_extendable:
        status = "blocked"
    elif cleared:
        status = "completed"
    elif len(round_rows) >= max_rounds:
        status = "max_rounds_reached"
    else:
        status = "needs_more_rounds"

    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "max_rounds": max_rounds,
        "round_count": len(round_rows),
        "initial_observation_sufficiency": _sufficiency_summary(initial_observation_sufficiency),
        "rounds": round_rows,
        "final_observation_sufficiency": _sufficiency_summary(final_sufficiency),
        "expansion_error": expansion_error or {},
        "decision": {
            "initial_extendable": initial_extendable,
            "iterative_observation_cleared": status == "completed",
            "blockers": _blockers(status, initial_observation_sufficiency, final_sufficiency, expansion_error),
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_iterative_observation_expansion_markdown(pack)
    return _sanitize(pack)


def write_iterative_observation_expansion_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "iterative_observation_expansion_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "iterative_observation_expansion_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "iterative_observation_expansion_next_actions.csv", index=False)
    pd.DataFrame(_round_csv_rows(pack.get("rounds", []))).to_csv(output_path / "iterative_observation_expansion_rounds.csv", index=False)


def render_iterative_observation_expansion_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    final = _dict(pack.get("final_observation_sufficiency"))
    fills = _dict(final.get("fills"))
    lines = [
        "# Phase 5.11 Iterative Observation Expansion",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Round count: {pack.get('round_count', 0)} / {pack.get('max_rounds', 0)}",
        f"- Final fills: {fills.get('observed_fills')} / {fills.get('required_fills')}",
        f"- Iterative observation cleared: {decision.get('iterative_observation_cleared', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Rounds",
        "",
    ]
    rounds = pack.get("rounds", [])
    if rounds:
        for row in rounds:
            if isinstance(row, dict):
                expanded = _dict(row.get("expanded_observation_replay"))
                window = _dict(expanded.get("window"))
                final_sufficiency = _dict(expanded.get("final_observation_sufficiency"))
                final_fills = _dict(final_sufficiency.get("fills"))
                lines.append(
                    "- "
                    f"round {row.get('round')}: {expanded.get('status')} "
                    f"{window.get('start_date')} to {window.get('end_date')} "
                    f"fills {final_fills.get('observed_fills')}/{final_fills.get('required_fills')}"
                )
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = decision.get("blockers", [])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    actions = pack.get("next_actions", [])
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _can_extend(pack: dict[str, Any]) -> bool:
    recommendation = _dict(pack.get("recommendation"))
    return (
        pack.get("status") == "needs_more_observation_data"
        and recommendation.get("priority") == "extend_recent_data_window"
        and bool(recommendation.get("suggested_start_date"))
        and bool(recommendation.get("suggested_end_date"))
    )


def _blockers(
    status: str,
    initial_sufficiency: dict[str, Any],
    final_sufficiency: dict[str, Any],
    expansion_error: dict[str, Any] | None,
) -> list[str]:
    if status == "completed":
        return []
    if expansion_error:
        stage = expansion_error.get("stage", "iterative_observation_expansion")
        return [f"{stage}_failed: {expansion_error.get('error', 'unknown error')}"]
    if status == "blocked":
        return _as_list(_dict(initial_sufficiency.get("decision")).get("blockers")) or ["observation_sufficiency_not_extendable"]
    final_blockers = _as_list(_dict(final_sufficiency.get("decision")).get("blockers"))
    return final_blockers or [status]


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    if pack.get("status") == "completed":
        return [
            {
                "action": "continue_paper_observation_on_iterative_window",
                "local_only": True,
                "reason": "Iterative expansion cleared observation sample sufficiency under the current policy.",
            }
        ]
    if pack.get("status") == "blocked":
        return [
            {
                "action": "resolve_observation_sufficiency_gate",
                "command": "python scripts\\run_observation_sufficiency.py",
                "local_only": True,
                "reason": "Iterative expansion requires an extendable observation sufficiency artifact.",
            }
        ]
    if pack.get("status") == "max_rounds_reached":
        return [
            {
                "action": "review_min_fills_policy_or_expand_max_rounds",
                "local_only": True,
                "reason": "Expansion reached the configured round limit before clearing the sample gate.",
            }
        ]
    return [
        {
            "action": "inspect_iterative_expansion_error",
            "local_only": True,
            "reason": "The iterative expansion chain failed or still needs another round.",
        }
    ]


def _sufficiency_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "fills": pack.get("fills", {}) if isinstance(pack.get("fills"), dict) else {},
        "recommendation": pack.get("recommendation", {}) if isinstance(pack.get("recommendation"), dict) else {},
        "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
    }


def _round_csv_rows(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in rounds:
        expanded = _dict(row.get("expanded_observation_replay")) if isinstance(row, dict) else {}
        window = _dict(expanded.get("window"))
        final = _dict(expanded.get("final_observation_sufficiency"))
        fills = _dict(final.get("fills"))
        rows.append(
            {
                "round": row.get("round") if isinstance(row, dict) else None,
                "status": expanded.get("status"),
                "start_date": window.get("start_date"),
                "end_date": window.get("end_date"),
                "observed_fills": fills.get("observed_fills"),
                "required_fills": fills.get("required_fills"),
                "fill_deficit": fills.get("fill_deficit"),
            }
        )
    return rows


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


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
