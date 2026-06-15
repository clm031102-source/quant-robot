from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_9_observation_sufficiency"
DEFAULT_MIN_RELAXATION_FILLS = 10
DEFAULT_FALLBACK_OBSERVATION_DAYS = 252


def build_observation_sufficiency_pack(
    post_refresh_replay_pack: dict[str, Any],
    *,
    profile_observation_pack: dict[str, Any] | None = None,
    minimum_relaxation_fills: int = DEFAULT_MIN_RELAXATION_FILLS,
    fallback_observation_days: int = DEFAULT_FALLBACK_OBSERVATION_DAYS,
) -> dict[str, Any]:
    observation = profile_observation_pack or {}
    min_rule = _minimum_fills_rule(observation)
    observed_fills = _int(min_rule.get("observed_value"), _ledger_fills(observation))
    required_fills = _int(min_rule.get("threshold"), 20)
    fill_deficit = max(0, required_fills - observed_fills)
    window = _observation_window(observation, post_refresh_replay_pack)
    observation_days = _calendar_days(window.get("start_date"), window.get("end_date"))
    fill_rate = observed_fills / observation_days if observation_days and observed_fills > 0 else 0.0
    estimated_total_days = _estimated_total_days(required_fills, fill_rate, fallback_observation_days)
    additional_days = max(0, estimated_total_days - observation_days) if observation_days else estimated_total_days
    suggested_end = _date_str(window.get("end_date")) or _target_end(post_refresh_replay_pack)
    suggested_start = _shift_start(suggested_end, estimated_total_days)
    stop_reasons = _stop_reasons(observation, post_refresh_replay_pack)
    min_fills_blocked = "minimum_fills_observed" in stop_reasons or min_rule.get("status") == "stop"
    missing_observation = not bool(observation)
    paper_allowed = bool(_dict(observation.get("decision")).get("paper_observation_allowed", False))

    if missing_observation:
        status = "blocked_missing_observation"
    elif min_fills_blocked:
        status = "needs_more_observation_data"
    elif paper_allowed:
        status = "sufficient"
    else:
        status = "blocked_by_other_observation_rules"

    threshold_relaxation_allowed = _threshold_relaxation_allowed(
        observed_fills,
        minimum_relaxation_fills,
        stop_reasons,
        min_fills_blocked,
    )
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source_stage": post_refresh_replay_pack.get("stage"),
        "post_refresh_status": post_refresh_replay_pack.get("status"),
        "fills": {
            "observed_fills": observed_fills,
            "required_fills": required_fills,
            "fill_deficit": fill_deficit,
            "observation_days": observation_days,
            "fill_rate_per_day": _round(fill_rate),
        },
        "recommendation": {
            "priority": _priority(status),
            "estimated_total_observation_days": estimated_total_days,
            "additional_observation_days": additional_days,
            "suggested_start_date": suggested_start,
            "suggested_end_date": suggested_end,
            "threshold_relaxation_allowed": threshold_relaxation_allowed,
            "threshold_policy": "extend_window_before_relaxing_min_fills",
            "minimum_relaxation_fills": minimum_relaxation_fills,
        },
        "decision": {
            "observation_sufficiency_cleared": status == "sufficient",
            "minimum_fills_blocked": min_fills_blocked,
            "missing_observation": missing_observation,
            "blockers": _blockers(status, stop_reasons),
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack, post_refresh_replay_pack)
    pack["markdown"] = render_observation_sufficiency_markdown(pack)
    return _sanitize(pack)


def write_observation_sufficiency_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "observation_sufficiency_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "observation_sufficiency_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "observation_sufficiency_next_actions.csv", index=False)


def render_observation_sufficiency_markdown(pack: dict[str, Any]) -> str:
    fills = _dict(pack.get("fills"))
    recommendation = _dict(pack.get("recommendation"))
    decision = _dict(pack.get("decision"))
    lines = [
        "# Phase 5.9 Observation Sufficiency",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Observed fills: {fills.get('observed_fills')}",
        f"- Required fills: {fills.get('required_fills')}",
        f"- Fill deficit: {fills.get('fill_deficit')}",
        f"- Estimated total observation days: {recommendation.get('estimated_total_observation_days')}",
        f"- Suggested start date: {recommendation.get('suggested_start_date')}",
        f"- Suggested end date: {recommendation.get('suggested_end_date')}",
        f"- Threshold relaxation allowed: {recommendation.get('threshold_relaxation_allowed', False)}",
        f"- Observation sufficiency cleared: {decision.get('observation_sufficiency_cleared', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Next Actions",
        "",
    ]
    actions = pack.get("next_actions", [])
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _minimum_fills_rule(observation: dict[str, Any]) -> dict[str, Any]:
    rules = observation.get("stop_rules", []) if isinstance(observation.get("stop_rules"), list) else []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("rule_id") == "minimum_fills_observed":
            return rule
    return {}


def _ledger_fills(observation: dict[str, Any]) -> int:
    ledger = observation.get("ledger", []) if isinstance(observation.get("ledger"), list) else []
    if ledger and isinstance(ledger[0], dict):
        return _int(ledger[0].get("fills"), 0)
    return 0


def _observation_window(observation: dict[str, Any], post_refresh: dict[str, Any]) -> dict[str, Any]:
    window = observation.get("observation_window", {}) if isinstance(observation.get("observation_window"), dict) else {}
    if window:
        return window
    recent = _dict(post_refresh.get("recent_data_refresh"))
    target = _dict(recent.get("target_window"))
    return {"start_date": target.get("start_date"), "end_date": target.get("end_date")}


def _stop_reasons(observation: dict[str, Any], post_refresh: dict[str, Any]) -> list[str]:
    observation_decision = _dict(observation.get("decision"))
    reasons = _as_list(observation_decision.get("stop_reasons"))
    if reasons:
        return reasons
    post_decision = _dict(post_refresh.get("decision"))
    return _as_list(post_decision.get("blockers"))


def _threshold_relaxation_allowed(
    observed_fills: int,
    minimum_relaxation_fills: int,
    stop_reasons: list[str],
    min_fills_blocked: bool,
) -> bool:
    other_stops = [reason for reason in stop_reasons if reason != "minimum_fills_observed"]
    return min_fills_blocked and observed_fills >= minimum_relaxation_fills and not other_stops


def _priority(status: str) -> str:
    if status == "needs_more_observation_data":
        return "extend_recent_data_window"
    if status == "sufficient":
        return "continue_paper_observation"
    if status == "blocked_missing_observation":
        return "rerun_post_refresh_replay"
    return "inspect_other_observation_rules"


def _blockers(status: str, stop_reasons: list[str]) -> list[str]:
    if status == "sufficient":
        return []
    if status == "blocked_missing_observation":
        return ["profile_observation_artifact_missing"]
    return stop_reasons or [status]


def _next_actions(pack: dict[str, Any], post_refresh: dict[str, Any]) -> list[dict[str, Any]]:
    recommendation = _dict(pack.get("recommendation"))
    if pack.get("status") == "needs_more_observation_data":
        start = recommendation.get("suggested_start_date")
        end = recommendation.get("suggested_end_date")
        actions = [
            {
                "action": "extend_recent_refresh_window",
                "command": f"python scripts\\run_recent_data_refresh.py --start-date {start} --end-date {end} --execute",
                "local_only": True,
                "reason": "Increase the paper observation sample before considering any threshold relaxation.",
            },
            {
                "action": "rerun_post_refresh_replay",
                "command": "python scripts\\run_post_refresh_replay.py",
                "local_only": True,
                "reason": "Replay Daily Ops and Profile Observation after the extended refresh completes.",
            },
        ]
        if recommendation.get("threshold_relaxation_allowed"):
            actions.append(
                {
                    "action": "review_min_fills_policy",
                    "local_only": True,
                    "reason": "Observed fills are near the threshold; manual policy review may be reasonable after window expansion.",
                }
            )
        return actions
    if pack.get("status") == "sufficient":
        return [
            {
                "action": "continue_paper_observation",
                "local_only": True,
                "reason": "Observation sample is sufficient under the current min-fills policy.",
            }
        ]
    return [
        {
            "action": "rerun_post_refresh_replay",
            "command": "python scripts\\run_post_refresh_replay.py",
            "local_only": True,
            "reason": "A complete post-refresh replay artifact is required before sample sufficiency can be planned.",
        }
    ]


def _estimated_total_days(required_fills: int, fill_rate: float, fallback_days: int) -> int:
    if fill_rate <= 0:
        return fallback_days
    return max(1, int(math.ceil(required_fills / fill_rate)))


def _shift_start(end_date: str | None, total_days: int) -> str | None:
    if not end_date:
        return None
    try:
        return (date.fromisoformat(end_date[:10]) - timedelta(days=max(0, total_days - 1))).isoformat()
    except ValueError:
        return None


def _target_end(post_refresh: dict[str, Any]) -> str | None:
    recent = _dict(post_refresh.get("recent_data_refresh"))
    target = _dict(recent.get("target_window"))
    return _date_str(target.get("end_date"))


def _calendar_days(start: Any, end: Any) -> int:
    start_date = _date_str(start)
    end_date = _date_str(end)
    if not start_date or not end_date:
        return 0
    try:
        return (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
    except ValueError:
        return 0


def _date_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


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


def _round(value: float) -> float:
    return round(float(value), 6)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
