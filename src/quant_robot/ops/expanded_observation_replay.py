from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_10_expanded_observation_replay"


def build_expanded_observation_replay_pack(
    observation_sufficiency_pack: dict[str, Any],
    *,
    recent_data_refresh: dict[str, Any] | None = None,
    post_refresh_replay: dict[str, Any] | None = None,
    final_observation_sufficiency: dict[str, Any] | None = None,
    replay_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_decision = _dict(observation_sufficiency_pack.get("decision"))
    source_recommendation = _dict(observation_sufficiency_pack.get("recommendation"))
    can_extend = _can_extend(observation_sufficiency_pack)
    final_decision = _dict((final_observation_sufficiency or {}).get("decision"))
    final_cleared = bool(final_decision.get("observation_sufficiency_cleared", False))

    if replay_error:
        status = "replay_failed"
    elif not can_extend:
        status = "blocked"
    elif final_cleared:
        status = "completed"
    else:
        status = "expanded_replay_blocked"

    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source_observation_sufficiency": _sufficiency_summary(observation_sufficiency_pack),
        "recent_data_refresh": _recent_summary(recent_data_refresh or {}),
        "post_refresh_replay": _post_refresh_summary(post_refresh_replay or {}),
        "final_observation_sufficiency": _sufficiency_summary(final_observation_sufficiency or {}),
        "replay_error": replay_error or {},
        "decision": {
            "can_extend_observation_window": can_extend,
            "expanded_observation_cleared": status == "completed",
            "blockers": _blockers(status, source_decision, final_decision, replay_error),
        },
        "window": {
            "start_date": source_recommendation.get("suggested_start_date"),
            "end_date": source_recommendation.get("suggested_end_date"),
            "estimated_total_observation_days": source_recommendation.get("estimated_total_observation_days"),
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_expanded_observation_replay_markdown(pack)
    return _sanitize(pack)


def write_expanded_observation_replay_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "expanded_observation_replay_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "expanded_observation_replay_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "expanded_observation_replay_next_actions.csv", index=False)


def render_expanded_observation_replay_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    window = _dict(pack.get("window"))
    source = _dict(pack.get("source_observation_sufficiency"))
    final = _dict(pack.get("final_observation_sufficiency"))
    lines = [
        "# Phase 5.10 Expanded Observation Replay",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Source sufficiency status: {source.get('status')}",
        f"- Final sufficiency status: {final.get('status')}",
        f"- Window: {window.get('start_date')} to {window.get('end_date')}",
        f"- Expanded observation cleared: {decision.get('expanded_observation_cleared', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Blockers",
        "",
    ]
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
    source_decision: dict[str, Any],
    final_decision: dict[str, Any],
    replay_error: dict[str, Any] | None,
) -> list[str]:
    if status == "completed":
        return []
    if replay_error:
        stage = replay_error.get("stage", "expanded_observation_replay")
        return [f"{stage}_failed: {replay_error.get('error', 'unknown error')}"]
    if status == "blocked":
        return _as_list(source_decision.get("blockers")) or ["observation_sufficiency_not_extendable"]
    return _as_list(final_decision.get("blockers")) or ["expanded_observation_still_insufficient"]


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    if pack.get("status") == "completed":
        return [
            {
                "action": "continue_paper_observation_on_expanded_window",
                "local_only": True,
                "reason": "Expanded observation window cleared sample sufficiency under the current policy.",
            }
        ]
    if pack.get("status") == "blocked":
        return [
            {
                "action": "resolve_observation_sufficiency_gate",
                "command": "python scripts\\run_observation_sufficiency.py",
                "local_only": True,
                "reason": "Expanded replay requires a sufficiency artifact that recommends extending the data window.",
            }
        ]
    if pack.get("status") == "replay_failed":
        return [
            {
                "action": "inspect_expanded_observation_replay_error",
                "local_only": True,
                "reason": "The expanded replay chain raised an execution error.",
            }
        ]
    return [
        {
            "action": "review_expanded_observation_blockers",
            "local_only": True,
            "reason": "Expanded replay ran but sample sufficiency or downstream paper gates still blocked continuation.",
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


def _recent_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "source": pack.get("source"),
        "output_dir": pack.get("output_dir"),
        "coverage": pack.get("coverage", {}) if isinstance(pack.get("coverage"), dict) else {},
        "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
    }


def _post_refresh_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
        "profile_observation_output_dir": pack.get("profile_observation_output_dir"),
    }


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
