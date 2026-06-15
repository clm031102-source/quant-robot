from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_8_post_refresh_replay"


def build_post_refresh_replay_pack(
    recent_data_refresh: dict[str, Any],
    *,
    daily_ops: dict[str, Any] | None = None,
    profile_observation: dict[str, Any] | None = None,
    daily_ops_output_dir: str | Path | None = None,
    profile_observation_output_dir: str | Path | None = None,
    replay_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recent_decision = recent_data_refresh.get("decision", {}) if isinstance(recent_data_refresh.get("decision"), dict) else {}
    daily_decision = daily_ops.get("decision", {}) if isinstance(daily_ops, dict) and isinstance(daily_ops.get("decision"), dict) else {}
    observation_decision = (
        profile_observation.get("decision", {})
        if isinstance(profile_observation, dict) and isinstance(profile_observation.get("decision"), dict)
        else {}
    )
    recent_ready = _recent_refresh_ready(recent_data_refresh)
    daily_allowed = bool(daily_decision.get("paper_trading_allowed", False))
    observation_allowed = bool(observation_decision.get("paper_observation_allowed", False))
    blockers = _blockers(recent_decision, daily_decision, observation_decision, recent_ready, daily_allowed, observation_allowed, replay_error)

    if replay_error:
        status = "replay_failed"
    elif not recent_ready:
        status = "blocked"
    elif daily_allowed and observation_allowed:
        status = "completed"
    else:
        status = "replay_blocked"

    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "recent_data_refresh": _recent_summary(recent_data_refresh),
        "daily_ops": _daily_summary(daily_ops or {}),
        "profile_observation": _observation_summary(profile_observation or {}),
        "daily_ops_output_dir": str(daily_ops_output_dir) if daily_ops_output_dir is not None else None,
        "profile_observation_output_dir": str(profile_observation_output_dir) if profile_observation_output_dir is not None else None,
        "replay_error": replay_error or {},
        "decision": {
            "recent_data_ready": recent_ready,
            "daily_ops_paper_allowed": daily_allowed,
            "profile_observation_allowed": observation_allowed,
            "post_refresh_replay_allowed": status == "completed",
            "blockers": blockers,
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_post_refresh_replay_markdown(pack)
    return _sanitize(pack)


def write_post_refresh_replay_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "post_refresh_replay_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "post_refresh_replay_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "post_refresh_replay_next_actions.csv", index=False)


def render_post_refresh_replay_markdown(pack: dict[str, Any]) -> str:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    recent = pack.get("recent_data_refresh", {}) if isinstance(pack.get("recent_data_refresh"), dict) else {}
    daily = pack.get("daily_ops", {}) if isinstance(pack.get("daily_ops"), dict) else {}
    observation = pack.get("profile_observation", {}) if isinstance(pack.get("profile_observation"), dict) else {}
    lines = [
        "# Phase 5.8 Post-Refresh Replay",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Recent refresh status: {recent.get('status')}",
        f"- Recent source: {recent.get('source')}",
        f"- Daily Ops status: {daily.get('status')}",
        f"- Observation status: {observation.get('observation_status')}",
        f"- Post-refresh replay allowed: {decision.get('post_refresh_replay_allowed', False)}",
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


def _recent_refresh_ready(pack: dict[str, Any]) -> bool:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return bool(decision.get("recent_data_ready", False) and decision.get("signal_data_stale_cleared", False))


def _recent_summary(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": pack.get("stage"),
        "status": pack.get("status"),
        "mode": pack.get("mode"),
        "source": pack.get("source"),
        "market": pack.get("market"),
        "output_dir": pack.get("output_dir"),
        "target_window": pack.get("target_window", {}) if isinstance(pack.get("target_window"), dict) else {},
        "coverage": pack.get("coverage", {}) if isinstance(pack.get("coverage"), dict) else {},
        "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
    }


def _daily_summary(pack: dict[str, Any]) -> dict[str, Any]:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return {
        "stage": pack.get("stage"),
        "run_date": pack.get("run_date"),
        "status": decision.get("status"),
        "paper_trading_allowed": bool(decision.get("paper_trading_allowed", False)),
        "blocking_reasons": decision.get("blocking_reasons", []) if isinstance(decision.get("blocking_reasons"), list) else [],
        "candidate": pack.get("candidate", {}) if isinstance(pack.get("candidate"), dict) else {},
        "risk": pack.get("risk", {}) if isinstance(pack.get("risk"), dict) else {},
    }


def _observation_summary(pack: dict[str, Any]) -> dict[str, Any]:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return {
        "stage": pack.get("stage"),
        "run_date": pack.get("run_date"),
        "observation_status": decision.get("observation_status"),
        "paper_observation_allowed": bool(decision.get("paper_observation_allowed", False)),
        "stop_reasons": decision.get("stop_reasons", []) if isinstance(decision.get("stop_reasons"), list) else [],
        "summary": pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {},
    }


def _blockers(
    recent_decision: dict[str, Any],
    daily_decision: dict[str, Any],
    observation_decision: dict[str, Any],
    recent_ready: bool,
    daily_allowed: bool,
    observation_allowed: bool,
    replay_error: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    if not recent_ready:
        blockers.extend(_as_list(recent_decision.get("blockers")) or ["recent_data_refresh_not_ready"])
    if replay_error:
        stage = replay_error.get("stage", "post_refresh_replay")
        message = replay_error.get("error", "unknown error")
        blockers.append(f"{stage}_failed: {message}")
    if recent_ready and daily_decision and not daily_allowed:
        blockers.extend(_as_list(daily_decision.get("blocking_reasons")) or ["daily_ops_not_paper_ready"])
    if recent_ready and observation_decision and not observation_allowed:
        blockers.extend(_as_list(observation_decision.get("stop_reasons")) or ["profile_observation_not_allowed"])
    return _unique(blockers)


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    blockers = _as_list(decision.get("blockers"))
    actions: list[dict[str, Any]] = []
    if any("TUSHARE_TOKEN" in blocker for blocker in blockers):
        actions.append(
            {
                "action": "set_tushare_token_env",
                "command": "setx TUSHARE_TOKEN <your-token>",
                "local_only": True,
                "reason": "Set the token locally, open a new shell, then execute the recent data refresh.",
            }
        )
    if not decision.get("recent_data_ready", False) and not actions:
        actions.append(
            {
                "action": "execute_recent_data_refresh",
                "command": "python scripts\\run_recent_data_refresh.py --execute",
                "local_only": True,
                "reason": "Recent data is not ready, so replay is blocked until refresh completes.",
            }
        )
    if pack.get("status") == "replay_failed":
        actions.append(
            {
                "action": "inspect_post_refresh_replay_error",
                "local_only": True,
                "reason": "A downstream paper workflow failed during replay.",
            }
        )
    if pack.get("status") == "replay_blocked":
        actions.append(
            {
                "action": "inspect_post_refresh_daily_ops_or_observation",
                "local_only": True,
                "reason": "Recent data replay ran, but Daily Ops or Observation still blocked paper continuation.",
            }
        )
    if pack.get("status") == "completed":
        actions.append(
            {
                "action": "continue_paper_observation_on_refreshed_data",
                "local_only": True,
                "reason": "Recent data, Daily Ops, and profile observation all cleared the paper-only replay gate.",
            }
        )
    return actions


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


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
