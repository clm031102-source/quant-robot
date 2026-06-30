from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_0_daily_ops"
PROFILE_DAILY_OPS_STAGE = "phase_5_5_profile_daily_ops_activation"
MANUAL_ONLY_BLOCKERS = {"manual_live_review_not_enabled", "manual_live_review_enabled_blocked"}
PROMOTABLE_PROMOTION_STATUSES = {"paper_ready", "manual_live_review"}
DEFAULT_MAX_DRAWDOWN_LIMIT = -0.2
DEFAULT_MAX_SIGNAL_AGE_DAYS = 7
TICKET_COLUMNS = [
    "ticket_id",
    "ticket_type",
    "asset_id",
    "market",
    "side",
    "estimated_quantity_delta",
    "target_weight",
    "delta_value",
    "live_order_allowed",
]


def build_daily_ops_pack(
    promotion_review: dict[str, Any],
    readiness_board: dict[str, Any],
    signal_snapshot: dict[str, Any],
    paper_simulation: dict[str, Any],
    paper_profile: dict[str, Any] | None = None,
    run_date: str | None = None,
    max_drawdown_limit: float = DEFAULT_MAX_DRAWDOWN_LIMIT,
    max_signal_age_days: int = DEFAULT_MAX_SIGNAL_AGE_DAYS,
) -> dict[str, Any]:
    run_day = run_date or date.today().isoformat()
    candidate = _candidate(promotion_review, readiness_board)
    drawdown_limit = _normalized_drawdown_limit(max_drawdown_limit)
    risk_policy = _risk_policy(paper_simulation, drawdown_limit)
    signal_freshness = _signal_freshness(signal_snapshot, run_day, max_signal_age_days)
    profile_summary = _paper_profile_summary(paper_profile or {})
    blockers = _merge_unique(
        _blocker_ids(readiness_board),
        _promotion_status_blockers(candidate) + risk_policy["risk_blockers"] + signal_freshness["blocking_reasons"],
    )
    non_manual_blockers = [blocker for blocker in blockers if blocker not in MANUAL_ONLY_BLOCKERS]
    status = "blocked" if non_manual_blockers else "paper_ready"
    tickets = [] if status == "blocked" else _advisory_tickets(signal_snapshot)
    pack = {
        "stage": PROFILE_DAILY_OPS_STAGE if profile_summary else STAGE,
        "run_date": run_day,
        "safety": _safety(),
        "candidate": candidate,
        "decision": {
            "status": status,
            "live_boundary_allowed": False,
            "paper_trading_allowed": status == "paper_ready",
            "blocking_reasons": blockers,
            "non_manual_blocking_reasons": non_manual_blockers,
            "signal_freshness": signal_freshness,
        },
        "signal": _signal_summary(signal_snapshot, signal_freshness),
        "risk": _risk_summary(paper_simulation),
        "risk_policy": risk_policy,
        "paper_profile": profile_summary,
        "advisory_tickets": tickets,
        "simulation": _simulation_summary(paper_simulation),
        "readiness": _readiness_summary(readiness_board),
    }
    pack["markdown"] = render_daily_ops_markdown(pack)
    return _sanitize(pack)


def write_daily_ops_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_ops_pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True), encoding="utf-8")
    (output_path / "daily_ops_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("advisory_tickets", []), columns=TICKET_COLUMNS).to_csv(output_path / "daily_ops_tickets.csv", index=False)
    pd.DataFrame([_summary_row(pack)]).to_csv(output_path / "daily_ops_summary.csv", index=False)


def render_daily_ops_markdown(pack: dict[str, Any]) -> str:
    candidate = pack.get("candidate", {}) if isinstance(pack.get("candidate"), dict) else {}
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    signal = pack.get("signal", {}) if isinstance(pack.get("signal"), dict) else {}
    risk = pack.get("risk", {}) if isinstance(pack.get("risk"), dict) else {}
    lines = [
        "# Daily Ops Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Run date: {pack.get('run_date', '')}",
        f"- Candidate: {candidate.get('case_id', 'none')}",
        f"- Market: {candidate.get('market', 'unknown')}",
        f"- Decision: {decision.get('status', 'unknown')}",
        f"- Paper trading allowed: {decision.get('paper_trading_allowed', False)}",
        f"- Live boundary allowed: {decision.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Signal",
        "",
        f"- As of: {signal.get('as_of_date', 'unknown')}",
        f"- Signal date: {signal.get('signal_date', 'unknown')}",
        f"- Signal age days: {signal.get('signal_age_days', 'unknown')}",
        f"- Targets: {signal.get('target_count', 0)}",
        f"- Advisory tickets: {len(pack.get('advisory_tickets', []))}",
        "",
        "## Risk",
        "",
        f"- Total return: {risk.get('total_return', 0.0)}",
        f"- Max equity drawdown: {risk.get('max_equity_drawdown', 0.0)}",
        f"- Guard events: {risk.get('guard_events', 0)}",
        f"- Execution blocks: {risk.get('execution_blocks', 0)}",
        f"- Max drawdown limit: {pack.get('risk_policy', {}).get('max_drawdown_limit', DEFAULT_MAX_DRAWDOWN_LIMIT)}",
        "",
        "## Paper Profile",
        "",
        f"- Profile: {pack.get('paper_profile', {}).get('profile_id', 'none')}",
        f"- Risk tier: {pack.get('paper_profile', {}).get('risk_tier', 'none')}",
        "",
        "## Blockers",
        "",
    ]
    blockers = decision.get("blocking_reasons", [])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _candidate(promotion_review: dict[str, Any], readiness_board: dict[str, Any]) -> dict[str, Any]:
    candidate = promotion_review.get("selected_candidate")
    if not isinstance(candidate, dict):
        candidate = readiness_board.get("selected_candidate")
    if not isinstance(candidate, dict):
        return {}
    return {
        "case_id": candidate.get("case_id"),
        "market": candidate.get("market"),
        "factor_name": candidate.get("factor_name"),
        "rank": candidate.get("rank"),
        "promotion_status": candidate.get("promotion_status"),
    }


def _blocker_ids(readiness_board: dict[str, Any]) -> list[str]:
    blockers = []
    for row in readiness_board.get("blocker_register", []):
        if isinstance(row, dict) and row.get("blocker_id"):
            text = str(row.get("blocker_id"))
            if text not in blockers:
                blockers.append(text)
    return blockers


def _promotion_status_blockers(candidate: dict[str, Any]) -> list[str]:
    if str(candidate.get("promotion_status") or "") in PROMOTABLE_PROMOTION_STATUSES:
        return []
    return ["promotion_status_not_paper_ready"]


def _risk_policy(paper_simulation: dict[str, Any], max_drawdown_limit: float) -> dict[str, Any]:
    metrics = paper_simulation.get("metrics", {}) if isinstance(paper_simulation.get("metrics"), dict) else {}
    max_drawdown = _float(metrics.get("max_equity_drawdown"), 0.0)
    breached = max_drawdown < max_drawdown_limit
    return {
        "max_drawdown_limit": max_drawdown_limit,
        "max_drawdown_breached": breached,
        "risk_blockers": ["risk_max_drawdown_breach"] if breached else [],
    }


def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    values = []
    for item in [*first, *second]:
        if item not in values:
            values.append(item)
    return values


def _advisory_tickets(signal_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(signal_snapshot.get("rebalance_plan", []), start=1):
        if not isinstance(row, dict):
            continue
        quantity = _float(row.get("estimated_quantity_delta"), 0.0)
        side = "hold"
        if quantity > 0.0:
            side = "buy"
        elif quantity < 0.0:
            side = "sell"
        rows.append(
            {
                "ticket_id": f"daily-{index:03d}",
                "ticket_type": "advisory_rebalance",
                "asset_id": row.get("asset_id"),
                "market": row.get("market"),
                "side": side,
                "estimated_quantity_delta": quantity,
                "target_weight": _float(row.get("target_weight"), 0.0),
                "delta_value": _float(row.get("delta_value"), 0.0),
                "live_order_allowed": False,
            }
        )
    return rows


def _signal_summary(signal_snapshot: dict[str, Any], freshness: dict[str, Any] | None = None) -> dict[str, Any]:
    targets = signal_snapshot.get("targets", [])
    signal_freshness = freshness or {}
    return {
        "as_of_date": signal_snapshot.get("as_of_date"),
        "signal_date": signal_snapshot.get("signal_date"),
        "run_date": signal_freshness.get("run_date"),
        "signal_age_days": signal_freshness.get("signal_age_days"),
        "max_signal_age_days": signal_freshness.get("max_signal_age_days"),
        "freshness_status": signal_freshness.get("status"),
        "target_count": len(targets) if isinstance(targets, list) else 0,
        "target_gross_exposure": signal_snapshot.get("target_gross_exposure"),
        "cash_weight": signal_snapshot.get("cash_weight"),
    }


def _risk_summary(paper_simulation: dict[str, Any]) -> dict[str, Any]:
    metrics = paper_simulation.get("metrics", {}) if isinstance(paper_simulation.get("metrics"), dict) else {}
    return {
        "total_return": _float(metrics.get("total_return"), 0.0),
        "max_equity_drawdown": _float(metrics.get("max_equity_drawdown"), 0.0),
        "ending_equity": _float(metrics.get("ending_equity"), 0.0),
        "guard_events": len(paper_simulation.get("guard_events", []) if isinstance(paper_simulation.get("guard_events"), list) else []),
        "execution_blocks": len(paper_simulation.get("execution_events", []) if isinstance(paper_simulation.get("execution_events"), list) else []),
    }


def _paper_profile_summary(paper_profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(paper_profile, dict) or not paper_profile:
        return {}
    return {
        "profile_id": paper_profile.get("profile_id"),
        "case_id": paper_profile.get("case_id"),
        "risk_tier": paper_profile.get("risk_tier"),
        "risk_tier_label": paper_profile.get("risk_tier_label"),
        "max_asset_weight": _float(paper_profile.get("max_asset_weight"), 1.0),
        "max_gross_exposure": _float(paper_profile.get("max_gross_exposure"), 1.0),
        "min_cash_weight": _float(paper_profile.get("min_cash_weight"), 0.0),
        "max_drawdown_guard": _float(paper_profile.get("max_drawdown_guard"), 0.0),
        "guard_cooldown_periods": int(_float(paper_profile.get("guard_cooldown_periods"), 0.0)),
    }


def _simulation_summary(paper_simulation: dict[str, Any]) -> dict[str, Any]:
    return {
        "fills": len(paper_simulation.get("fills", []) if isinstance(paper_simulation.get("fills"), list) else []),
        "guard_events": len(paper_simulation.get("guard_events", []) if isinstance(paper_simulation.get("guard_events"), list) else []),
        "execution_events": len(paper_simulation.get("execution_events", []) if isinstance(paper_simulation.get("execution_events"), list) else []),
    }


def _readiness_summary(readiness_board: dict[str, Any]) -> dict[str, Any]:
    items = readiness_board.get("readiness_items", [])
    return {
        "overall_status": readiness_board.get("overall_status"),
        "blocked_items": sum(1 for item in items if isinstance(item, dict) and item.get("status") == "block") if isinstance(items, list) else 0,
        "warning_items": sum(1 for item in items if isinstance(item, dict) and item.get("status") == "warn") if isinstance(items, list) else 0,
        "blockers": len(_blocker_ids(readiness_board)),
    }


def _summary_row(pack: dict[str, Any]) -> dict[str, Any]:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    candidate = pack.get("candidate", {}) if isinstance(pack.get("candidate"), dict) else {}
    risk = pack.get("risk", {}) if isinstance(pack.get("risk"), dict) else {}
    risk_policy = pack.get("risk_policy", {}) if isinstance(pack.get("risk_policy"), dict) else {}
    return {
        "stage": pack.get("stage"),
        "run_date": pack.get("run_date"),
        "case_id": candidate.get("case_id"),
        "market": candidate.get("market"),
        "decision_status": decision.get("status"),
        "paper_trading_allowed": decision.get("paper_trading_allowed"),
        "live_boundary_allowed": decision.get("live_boundary_allowed"),
        "blockers": len(decision.get("blocking_reasons", [])) if isinstance(decision.get("blocking_reasons"), list) else 0,
        "advisory_tickets": len(pack.get("advisory_tickets", [])),
        "total_return": risk.get("total_return"),
        "max_equity_drawdown": risk.get("max_equity_drawdown"),
        "max_drawdown_limit": risk_policy.get("max_drawdown_limit"),
        "max_drawdown_breached": risk_policy.get("max_drawdown_breached"),
        "risk_blockers": len(risk_policy.get("risk_blockers", [])) if isinstance(risk_policy.get("risk_blockers"), list) else 0,
        "signal_age_days": pack.get("signal", {}).get("signal_age_days") if isinstance(pack.get("signal"), dict) else None,
        "max_signal_age_days": pack.get("signal", {}).get("max_signal_age_days") if isinstance(pack.get("signal"), dict) else None,
        "profile_id": pack.get("paper_profile", {}).get("profile_id") if isinstance(pack.get("paper_profile"), dict) else None,
        "risk_tier": pack.get("paper_profile", {}).get("risk_tier") if isinstance(pack.get("paper_profile"), dict) else None,
    }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalized_drawdown_limit(value: float) -> float:
    return -abs(_float(value, DEFAULT_MAX_DRAWDOWN_LIMIT))


def _signal_freshness(signal_snapshot: dict[str, Any], run_date: str, max_signal_age_days: int) -> dict[str, Any]:
    signal_date = str(signal_snapshot.get("signal_date") or signal_snapshot.get("as_of_date") or "").strip()
    age_days = _calendar_gap(signal_date, run_date) if signal_date else None
    blockers: list[str] = []
    status = "unknown"
    if age_days is not None:
        if age_days < 0:
            blockers.append("signal_date_after_run_date")
            status = "blocked_future_signal"
        elif age_days > max_signal_age_days:
            blockers.append("signal_data_stale")
            status = "blocked_stale_signal"
        else:
            status = "fresh"
    return {
        "run_date": run_date,
        "signal_date": signal_date or None,
        "signal_age_days": age_days,
        "max_signal_age_days": int(max_signal_age_days),
        "status": status,
        "blocking_reasons": blockers,
    }


def _calendar_gap(start_date: str, end_date: str) -> int | None:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return None
    return (end - start).days


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
