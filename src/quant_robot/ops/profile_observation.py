from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_6_profile_observation_ledger"
DEFAULT_MAX_SIGNAL_AGE_DAYS = 7
DEFAULT_MIN_FILLS = 20
DEFAULT_GUARD_EVENT_WARNING_RATIO = 0.5


def build_profile_observation_pack(
    daily_ops_pack: dict[str, Any],
    *,
    simulation_manifest: dict[str, Any] | None = None,
    equity_curve: list[dict[str, Any]] | None = None,
    guard_events: list[dict[str, Any]] | None = None,
    execution_events: list[dict[str, Any]] | None = None,
    run_date: str | None = None,
    max_signal_age_days: int = DEFAULT_MAX_SIGNAL_AGE_DAYS,
    min_fills: int = DEFAULT_MIN_FILLS,
    guard_event_warning_ratio: float = DEFAULT_GUARD_EVENT_WARNING_RATIO,
) -> dict[str, Any]:
    run_day = run_date or str(daily_ops_pack.get("run_date") or date.today().isoformat())
    profile = _dict(daily_ops_pack.get("paper_profile"))
    decision = _dict(daily_ops_pack.get("decision"))
    risk = _dict(daily_ops_pack.get("risk"))
    risk_policy = _dict(daily_ops_pack.get("risk_policy"))
    signal = _dict(daily_ops_pack.get("signal"))
    simulation = _dict(daily_ops_pack.get("simulation"))
    manifest = simulation_manifest or {}
    equity_rows = _records(equity_curve)
    guard_rows = _records(guard_events)
    execution_rows = _records(execution_events)
    observation_window = _observation_window(equity_rows)
    signal_date = str(signal.get("signal_date") or signal.get("as_of_date") or "")
    signal_age_days = _calendar_gap(signal_date, run_day) if signal_date else None
    fills = _int(simulation.get("fills"), 0)
    guard_count = len(guard_rows) if guard_rows else _int(simulation.get("guard_events"), 0)
    execution_count = len(execution_rows) if execution_rows else _int(simulation.get("execution_events"), 0)
    equity_points = _int(observation_window.get("equity_points"), 0)
    guard_ratio = guard_count / equity_points if equity_points else 0.0

    context = {
        "run_date": run_day,
        "decision": decision,
        "risk": risk,
        "risk_policy": risk_policy,
        "signal_date": signal_date,
        "signal_age_days": signal_age_days,
        "max_signal_age_days": max_signal_age_days,
        "fills": fills,
        "min_fills": min_fills,
        "guard_events": guard_count,
        "guard_event_ratio": guard_ratio,
        "guard_event_warning_ratio": guard_event_warning_ratio,
        "execution_events": execution_count,
        "profile": profile,
        "simulation_manifest": manifest,
    }
    stop_rules = _stop_rules(context)
    stop_reasons = [row["rule_id"] for row in stop_rules if row.get("status") == "stop"]
    warning_reasons = [row["rule_id"] for row in stop_rules if row.get("status") == "warn"]
    observation_status = "stopped" if stop_reasons else "observe"
    ledger_row = _ledger_row(
        daily_ops_pack,
        profile,
        risk,
        signal,
        observation_window,
        run_day,
        signal_age_days,
        fills,
        guard_count,
        guard_ratio,
        execution_count,
        observation_status,
        stop_reasons,
    )
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "run_date": run_day,
        "safety": _safety(),
        "live_boundary_allowed": False,
        "decision": {
            "observation_status": observation_status,
            "paper_observation_allowed": not stop_reasons,
            "stop_reasons": stop_reasons,
            "warning_reasons": warning_reasons,
            "stop_count": len(stop_reasons),
            "warning_count": len(warning_reasons),
        },
        "summary": {
            "ledger_rows": 1,
            "stop_rules": len(stop_rules),
            "stop_count": len(stop_reasons),
            "warning_count": len(warning_reasons),
            "pass_count": sum(1 for row in stop_rules if row.get("status") == "pass"),
            "signal_age_days": signal_age_days,
            "max_signal_age_days": max_signal_age_days,
            "guard_event_ratio": _round_float(guard_ratio),
        },
        "candidate": _dict(daily_ops_pack.get("candidate")),
        "paper_profile": profile,
        "observation_window": observation_window,
        "stop_rules": stop_rules,
        "ledger": [ledger_row],
        "next_actions": _next_actions(stop_reasons, warning_reasons, signal_date, run_day),
    }
    pack["markdown"] = render_profile_observation_markdown(pack)
    return _sanitize(pack)


def write_profile_observation_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profile_observation_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profile_observation_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("ledger", [])).to_csv(output_path / "profile_observation_ledger.csv", index=False)
    pd.DataFrame(pack.get("stop_rules", [])).to_csv(output_path / "profile_observation_stop_rules.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "profile_observation_next_actions.csv", index=False)


def render_profile_observation_markdown(pack: dict[str, Any]) -> str:
    decision = _dict(pack.get("decision"))
    profile = _dict(pack.get("paper_profile"))
    summary = _dict(pack.get("summary"))
    lines = [
        "# Phase 5.6 Profile Observation Ledger",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Run date: {pack.get('run_date', '')}",
        f"- Observation status: {decision.get('observation_status', 'unknown')}",
        f"- Paper observation allowed: {decision.get('paper_observation_allowed', False)}",
        f"- Profile: {profile.get('profile_id', 'none')}",
        f"- Risk tier: {profile.get('risk_tier', 'none')}",
        f"- Signal age days: {summary.get('signal_age_days', 'unknown')}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Stop Rules",
        "",
        "| Rule | Status | Observed | Threshold | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("stop_rules", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('rule_id', '')} | "
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


def _stop_rules(context: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(context.get("decision"))
    risk = _dict(context.get("risk"))
    risk_policy = _dict(context.get("risk_policy"))
    profile = _dict(context.get("profile"))
    manifest = _dict(context.get("simulation_manifest"))
    request = _dict(manifest.get("request"))
    max_drawdown = _float(risk.get("max_equity_drawdown"), 0.0)
    drawdown_limit = _float(risk_policy.get("max_drawdown_limit"), -0.2)
    signal_age = context.get("signal_age_days")
    max_signal_age = _int(context.get("max_signal_age_days"), DEFAULT_MAX_SIGNAL_AGE_DAYS)
    fills = _int(context.get("fills"), 0)
    min_fills = _int(context.get("min_fills"), DEFAULT_MIN_FILLS)
    execution_events = _int(context.get("execution_events"), 0)
    guard_ratio = _float(context.get("guard_event_ratio"), 0.0)
    guard_threshold = _float(context.get("guard_event_warning_ratio"), DEFAULT_GUARD_EVENT_WARNING_RATIO)
    drift = _profile_drift(profile, request)
    return [
        _rule(
            "daily_ops_paper_ready",
            "stop",
            decision.get("status"),
            "paper_ready",
            decision.get("status") == "paper_ready" and bool(decision.get("paper_trading_allowed")),
            "Daily Ops must be paper-ready before observation continues.",
        ),
        _rule(
            "live_boundary_disabled",
            "stop",
            bool(decision.get("live_boundary_allowed", False)),
            False,
            not bool(decision.get("live_boundary_allowed", False)),
            "Live trading boundary must remain disabled.",
        ),
        _rule(
            "signal_data_stale",
            "stop",
            signal_age if signal_age is not None else "missing",
            max_signal_age,
            signal_age is not None and signal_age <= max_signal_age,
            "Signal date is too old for active paper observation.",
        ),
        _rule(
            "drawdown_policy_breach",
            "stop",
            _round_float(max_drawdown),
            _round_float(drawdown_limit),
            max_drawdown >= drawdown_limit,
            "Paper drawdown must remain within the active risk tier limit.",
        ),
        _rule(
            "execution_blocks_absent",
            "stop",
            execution_events,
            0,
            execution_events == 0,
            "Execution block events require manual inspection.",
        ),
        _rule(
            "minimum_fills_observed",
            "stop",
            fills,
            min_fills,
            fills >= min_fills,
            "Observation needs enough fills to avoid tiny-sample decisions.",
        ),
        _rule(
            "profile_parameter_drift",
            "stop",
            ", ".join(drift) if drift else "none",
            "none",
            not drift,
            "Daily Ops simulation parameters must match the activated profile.",
        ),
        _rule(
            "guard_event_ratio_high",
            "warn",
            _round_float(guard_ratio),
            _round_float(guard_threshold),
            guard_ratio <= guard_threshold,
            "Drawdown guard is firing frequently; profile may be unstable.",
        ),
    ]


def _rule(
    rule_id: str,
    severity: str,
    observed_value: Any,
    threshold: Any,
    passed: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "status": "pass" if passed else severity,
        "observed_value": observed_value,
        "threshold": threshold,
        "reason": reason,
    }


def _profile_drift(profile: dict[str, Any], request: dict[str, Any]) -> list[str]:
    if not profile or not request:
        return []
    checks = [
        "max_asset_weight",
        "max_gross_exposure",
        "min_cash_weight",
        "max_drawdown_guard",
        "guard_cooldown_periods",
    ]
    drift = []
    for key in checks:
        if key in profile and key in request and not _close_enough(profile.get(key), request.get(key)):
            drift.append(key)
    return drift


def _ledger_row(
    daily_ops_pack: dict[str, Any],
    profile: dict[str, Any],
    risk: dict[str, Any],
    signal: dict[str, Any],
    observation_window: dict[str, Any],
    run_date: str,
    signal_age_days: int | None,
    fills: int,
    guard_events: int,
    guard_event_ratio: float,
    execution_events: int,
    observation_status: str,
    stop_reasons: list[str],
) -> dict[str, Any]:
    candidate = _dict(daily_ops_pack.get("candidate"))
    return {
        "run_date": run_date,
        "case_id": candidate.get("case_id"),
        "market": candidate.get("market"),
        "factor_name": candidate.get("factor_name"),
        "profile_id": profile.get("profile_id"),
        "risk_tier": profile.get("risk_tier"),
        "observation_status": observation_status,
        "signal_date": signal.get("signal_date") or signal.get("as_of_date"),
        "signal_age_days": signal_age_days,
        "observation_start": observation_window.get("start_date"),
        "observation_end": observation_window.get("end_date"),
        "equity_points": observation_window.get("equity_points", 0),
        "ending_equity": _round_float(observation_window.get("ending_equity", risk.get("ending_equity", 0.0))),
        "current_drawdown": _round_float(observation_window.get("current_drawdown", 0.0)),
        "total_return": _round_float(risk.get("total_return", 0.0)),
        "max_equity_drawdown": _round_float(risk.get("max_equity_drawdown", 0.0)),
        "fills": fills,
        "guard_events": guard_events,
        "guard_event_ratio": _round_float(guard_event_ratio),
        "execution_events": execution_events,
        "paper_observation_allowed": not stop_reasons,
        "stop_reasons": stop_reasons,
    }


def _next_actions(stop_reasons: list[str], warning_reasons: list[str], signal_date: str, run_date: str) -> list[dict[str, Any]]:
    actions = []
    if "signal_data_stale" in stop_reasons:
        actions.append(
            {
                "action": "refresh_tushare_recent_data",
                "local_only": True,
                "command": "python scripts\\ingest_data.py --source tushare --market CN_ETF --start-date "
                f"{_next_day(signal_date) or signal_date} --end-date {run_date} --output-dir data\\processed\\tushare_etf_recent",
                "reason": "Activated profile uses stale signal data; refresh recent CN ETF bars before continuing observation.",
            }
        )
    if "profile_parameter_drift" in stop_reasons:
        actions.append(
            {
                "action": "rerun_daily_ops_with_selected_profile",
                "local_only": True,
                "command": "python scripts\\run_daily_ops.py --paper-profile-pack data\\reports\\paper_profile_optimizer\\paper_profile_optimizer_pack.json --output-dir data\\reports\\daily_ops",
                "reason": "Daily Ops simulation parameters no longer match the activated paper profile.",
            }
        )
    if "drawdown_policy_breach" in stop_reasons:
        actions.append(
            {
                "action": "freeze_profile_and_manual_review",
                "local_only": True,
                "reason": "Active paper drawdown breached the risk tier limit.",
            }
        )
    if "guard_event_ratio_high" in warning_reasons:
        actions.append(
            {
                "action": "inspect_guard_frequency",
                "local_only": True,
                "reason": "Drawdown guard events are frequent enough to question profile stability.",
            }
        )
    if not actions:
        actions.append(
            {
                "action": "continue_daily_paper_observation",
                "local_only": True,
                "reason": "No hard stop rule fired; keep observing before any live-boundary discussion.",
            }
        )
    return actions


def _observation_window(equity_curve: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in equity_curve if row.get("date")]
    if not rows:
        return {
            "start_date": None,
            "end_date": None,
            "equity_points": 0,
            "ending_equity": 0.0,
            "current_drawdown": 0.0,
        }
    rows = sorted(rows, key=lambda row: str(row.get("date")))
    equities = [_float(row.get("equity"), 0.0) for row in rows]
    peak = max(equities) if equities else 0.0
    ending = equities[-1] if equities else 0.0
    current_drawdown = ending / peak - 1.0 if peak > 0.0 else 0.0
    return {
        "start_date": str(rows[0].get("date")),
        "end_date": str(rows[-1].get("date")),
        "equity_points": len(rows),
        "ending_equity": ending,
        "current_drawdown": current_drawdown,
    }


def _calendar_gap(start: str, end: str) -> int:
    try:
        return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days
    except ValueError:
        return 0


def _next_day(value: str) -> str | None:
    try:
        return (date.fromisoformat(value[:10]) + timedelta(days=1)).isoformat()
    except (ValueError, TypeError):
        return None


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _round_float(value: Any) -> float:
    return round(_float(value), 6)


def _close_enough(left: Any, right: Any) -> bool:
    return abs(_float(left) - _float(right)) <= 1e-9


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
