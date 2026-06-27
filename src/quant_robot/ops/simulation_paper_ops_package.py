from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "simulation_paper_ops_package"
SAFETY = "research-to-paper only; no broker, account, order, or live-trading access"


def build_simulation_paper_ops_package(
    *,
    config: dict[str, Any],
    paper_handoff: dict[str, Any],
    capacity_stress: dict[str, Any] | None = None,
    extreme_trade_profile: dict[str, Any] | None = None,
    blend_audit: dict[str, Any] | None = None,
    max_user_drawdown: float = -0.30,
) -> dict[str, Any]:
    cfg = _dict(config)
    handoff = _dict(paper_handoff)
    round457 = _dict(cfg.get("round457_range_q20_paper_readiness_hardening"))
    capacity = _dict(capacity_stress) or _dict(round457.get("capacity_stress"))
    extreme = _dict(extreme_trade_profile) or _dict(round457.get("extreme_trade_profile"))
    blend = _dict(blend_audit)
    user_drawdown = -abs(_number(max_user_drawdown, -0.30))

    candidates = [_dict(row) for row in _list(handoff.get("candidates"))]
    summary = _dict(handoff.get("summary"))
    default_id = str(summary.get("default_candidate_id") or _choose_default_candidate(candidates) or "")
    high_return_id = str(
        summary.get("primary_high_return_candidate_id")
        or round457.get("primary_high_return_paper_candidate_id")
        or _choose_high_return_candidate(candidates)
        or ""
    )
    default_candidate = _candidate_by_id(candidates, default_id)
    high_candidate = _candidate_by_id(candidates, high_return_id)
    high_config_candidate = _handoff_candidate_by_id(cfg, high_return_id)
    worst_cost_drawdown = _candidate_worst_cost_drawdown(high_config_candidate)
    if worst_cost_drawdown is None:
        worst_cost_drawdown = _worst_cost_drawdown(round457)

    blockers = _blockers(default_id, high_return_id, default_candidate, high_candidate, handoff)
    warnings = _warnings(
        config=cfg,
        default_candidate=default_candidate,
        high_candidate=high_candidate,
        capacity=capacity,
        extreme=extreme,
        blend=blend,
        max_user_drawdown=user_drawdown,
        worst_cost_drawdown=worst_cost_drawdown,
    )
    lanes = [
        _lane_row("baseline_comparison", default_candidate, max_user_drawdown=user_drawdown),
        _lane_row("primary_high_return_observation", high_candidate, max_user_drawdown=user_drawdown),
    ]
    lanes = [row for row in lanes if row]
    paper_allowed = not blockers
    status = "paper_ops_package_ready" if paper_allowed else "paper_ops_package_blocked"
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "safety": SAFETY,
        "live_boundary_allowed": False,
        "summary": {
            "default_candidate_id": default_id or None,
            "primary_high_return_candidate_id": high_return_id or None,
            "paper_lane_count": len(lanes),
            "ready_lane_count": sum(row.get("handoff_status") == "ready_for_paper_simulation" for row in lanes),
            "blocked_lane_count": sum(row.get("handoff_status") != "ready_for_paper_simulation" for row in lanes),
            "final_holdout_status": _final_holdout_status(cfg),
            "high_return_annualized_return": _metric(high_candidate, "computed_annualized_return", "evidence_annualized_return"),
            "high_return_total_return": _metric(high_candidate, "computed_total_return"),
            "high_return_max_drawdown": _metric(high_candidate, "computed_max_drawdown", "evidence_max_drawdown"),
        },
        "decision": {
            "paper_observation_allowed": paper_allowed,
            "default_lane_required": default_candidate is not None,
            "high_return_lane_required": high_candidate is not None,
            "live_cycle_allowed": False,
            "blockers": blockers,
            "warnings": warnings,
            "decision_text": _decision_text(paper_allowed, blockers),
        },
        "blockers": blockers,
        "warnings": warnings,
        "paper_lanes": lanes,
        "risk_controls": _risk_controls(
            capacity=capacity,
            extreme=extreme,
            max_user_drawdown=user_drawdown,
            worst_cost_drawdown=worst_cost_drawdown,
        ),
        "command_queue": _command_queue(paper_allowed),
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Paper-operations packaging only; final holdout remains sealed and no live boundary is crossed.",
        },
    }
    pack["markdown"] = render_simulation_paper_ops_package_markdown(pack)
    return _sanitize(pack)


def write_simulation_paper_ops_package(output_dir: str | Path, package: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(package)
    (output / "simulation_paper_ops_package.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "simulation_paper_ops_package.md").write_text(
        str(sanitized.get("markdown", "")),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("paper_lanes", [])).to_csv(
        output / "simulation_paper_ops_lanes.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("command_queue", [])).to_csv(
        output / "simulation_paper_ops_commands.csv",
        index=False,
    )


def render_simulation_paper_ops_package_markdown(package: dict[str, Any]) -> str:
    summary = _dict(package.get("summary"))
    decision = _dict(package.get("decision"))
    risk = _dict(package.get("risk_controls"))
    lines = [
        "# Simulation Paper Ops Package",
        "",
        f"- Stage: `{package.get('stage', STAGE)}`",
        f"- Status: `{package.get('status')}`",
        f"- Paper observation allowed: `{decision.get('paper_observation_allowed', False)}`",
        f"- Default candidate: `{summary.get('default_candidate_id')}`",
        f"- Primary high-return candidate: `{summary.get('primary_high_return_candidate_id')}`",
        f"- Final holdout status: `{summary.get('final_holdout_status')}`",
        f"- Live boundary allowed: `{package.get('live_boundary_allowed', False)}`",
        f"- Safety: {package.get('safety', SAFETY)}",
        "",
        "## Paper Lanes",
        "",
        "| Lane | Candidate | Status | Ann | Total | MaxDD | OOS pass | Flags |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in _list(package.get("paper_lanes")):
        item = _dict(row)
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} | {} | {} | {} |".format(
                item.get("lane_role"),
                item.get("candidate_id"),
                item.get("handoff_status"),
                _pct(item.get("annualized_return")),
                _pct(item.get("total_return")),
                _pct(item.get("max_drawdown")),
                _pct(item.get("oos_strict_pass_rate")),
                ", ".join(_list(item.get("monitoring_flags"))) or "-",
            )
        )
    lines.extend(
        [
            "",
            "## Risk Controls",
            "",
            f"- Max user drawdown: `{_pct(risk.get('max_user_drawdown'))}`",
            f"- Capacity safe through AUM multiplier: `{risk.get('capacity_safe_through_aum_multiplier')}`",
            f"- Capacity unsafe from AUM multiplier: `{risk.get('capacity_unsafe_from_aum_multiplier')}`",
            f"- Extreme contribution share: `{_pct(risk.get('extreme_contribution_share'))}`",
            f"- Worst cost-stress drawdown: `{_pct(risk.get('worst_cost_stress_drawdown'))}`",
            "",
            "## Warnings",
            "",
        ]
    )
    warnings = _list(package.get("warnings"))
    lines.extend([f"- {warning}" for warning in warnings] if warnings else ["- none"])
    lines.extend(["", "## Blockers", ""])
    blockers = _list(package.get("blockers"))
    lines.extend([f"- {blocker}" for blocker in blockers] if blockers else ["- none"])
    return "\n".join(lines) + "\n"


def _blockers(
    default_id: str,
    high_return_id: str,
    default_candidate: dict[str, Any] | None,
    high_candidate: dict[str, Any] | None,
    handoff: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if bool(handoff.get("live_boundary_allowed", False)):
        blockers.append("live_boundary_violation")
    if not default_id or default_candidate is None:
        blockers.append("default_candidate_missing")
    elif str(default_candidate.get("handoff_status")) != "ready_for_paper_simulation":
        blockers.append("default_candidate_not_ready")
    if not high_return_id or high_candidate is None:
        blockers.append("primary_high_return_candidate_missing")
    elif str(high_candidate.get("handoff_status")) != "ready_for_paper_simulation":
        blockers.append("primary_high_return_candidate_not_ready")
    return sorted(set(blockers))


def _warnings(
    *,
    config: dict[str, Any],
    default_candidate: dict[str, Any] | None,
    high_candidate: dict[str, Any] | None,
    capacity: dict[str, Any],
    extreme: dict[str, Any],
    blend: dict[str, Any],
    max_user_drawdown: float,
    worst_cost_drawdown: float | None,
) -> list[str]:
    warnings: list[str] = []
    if _final_holdout_status(config) == "sealed":
        warnings.append("final_holdout_sealed_promotion_blocked")
    if high_candidate is not None and str(high_candidate.get("role")) == "diagnostic":
        warnings.append("high_return_lane_is_diagnostic_role")
    high_drawdown = _metric(high_candidate, "computed_max_drawdown", "evidence_max_drawdown")
    if high_drawdown is not None and high_drawdown <= max_user_drawdown + 0.02:
        warnings.append("high_return_drawdown_near_user_limit")
    if worst_cost_drawdown is not None and worst_cost_drawdown < max_user_drawdown:
        warnings.append("high_return_cost_stress_drawdown_below_user_limit")
    if _capacity_unsafe_from(capacity) is not None:
        warnings.append("capacity_not_clean_at_large_aum")
    if _extreme_contribution_share(extreme) >= 0.25:
        warnings.append("high_return_tail_contribution_concentrated")
    if _dict(blend.get("summary")).get("blocked_case_count"):
        warnings.append("shortlist_streams_highly_correlated")
    if high_candidate is not None and _metric(
        high_candidate,
        "csi500_beta_hedged_annualized_return",
    ) is None:
        warnings.append("high_return_beta_hedged_metrics_missing")
    if default_candidate is not None and high_candidate is not None:
        default_ann = _metric(default_candidate, "computed_annualized_return", "evidence_annualized_return")
        high_ann = _metric(high_candidate, "computed_annualized_return", "evidence_annualized_return")
        if default_ann is not None and high_ann is not None and high_ann > default_ann:
            warnings.append("default_lane_kept_for_baseline_not_return_maximization")
    return sorted(set(warnings))


def _lane_row(
    lane_role: str,
    candidate: dict[str, Any] | None,
    *,
    max_user_drawdown: float,
) -> dict[str, Any] | None:
    if candidate is None:
        return None
    drawdown = _metric(candidate, "computed_max_drawdown", "evidence_max_drawdown")
    flags = []
    if str(candidate.get("role")) == "diagnostic":
        flags.append("diagnostic_role")
    if drawdown is not None and drawdown <= max_user_drawdown + 0.02:
        flags.append("drawdown_near_user_limit")
    if str(candidate.get("handoff_status")) != "ready_for_paper_simulation":
        flags.append("not_ready")
    if _metric(candidate, "csi500_beta_hedged_annualized_return") is None:
        flags.append("beta_hedge_missing")
    return {
        "lane_role": lane_role,
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_role": str(candidate.get("role") or ""),
        "handoff_status": str(candidate.get("handoff_status") or ""),
        "annualized_return": _metric(candidate, "computed_annualized_return", "evidence_annualized_return"),
        "total_return": _metric(candidate, "computed_total_return"),
        "overlap_sharpe": _metric(candidate, "computed_overlap_sharpe"),
        "sharpe": _metric(candidate, "computed_sharpe"),
        "max_drawdown": drawdown,
        "win_rate": _metric(candidate, "computed_win_rate"),
        "oos_strict_pass_rate": _metric(candidate, "oos_strict_pass_rate"),
        "cost_rate": _metric(candidate, "cost_rate"),
        "period_count": _metric(candidate, "period_count"),
        "date_start": candidate.get("date_start"),
        "date_end": candidate.get("date_end"),
        "source_path": candidate.get("source_path"),
        "return_column": candidate.get("return_column"),
        "monitoring_flags": flags,
        "blockers": _list(candidate.get("blockers")),
    }


def _risk_controls(
    *,
    capacity: dict[str, Any],
    extreme: dict[str, Any],
    max_user_drawdown: float,
    worst_cost_drawdown: float | None,
) -> dict[str, Any]:
    return {
        "max_user_drawdown": max_user_drawdown,
        "capacity_safe_through_aum_multiplier": _capacity_safe_through(capacity),
        "capacity_unsafe_from_aum_multiplier": _capacity_unsafe_from(capacity),
        "extreme_contribution_share": _extreme_contribution_share(extreme),
        "extreme_trade_count": _int(_first_present(extreme, "extreme_trade_count"), 0),
        "worst_cost_stress_drawdown": worst_cost_drawdown,
        "paper_only_controls": [
            "Monitor default and high-return lanes side by side.",
            "Do not promote or open live-boundary work while final holdout is sealed.",
            "Treat a drawdown breach of the user limit as a review trigger, not an automatic order.",
            "Keep capacity at or below the safe AUM multiplier until a fresh capacity audit says otherwise.",
        ],
    }


def _command_queue(paper_allowed: bool) -> list[dict[str, Any]]:
    if not paper_allowed:
        return [
            _command(
                1,
                "inspect_paper_ops_package_blockers",
                "python scripts\\run_simulation_paper_ops_package.py --config configs\\cn_stock_profit_sprint_simulation_shortlist_20260627.json",
                "Paper package is blocked; inspect blockers before starting paper observation.",
            )
        ]
    return [
        _command(
            1,
            "refresh_simulation_shortlist_replay",
            "python scripts\\run_simulation_shortlist_replay.py --config configs\\cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root . --output-dir data\\reports\\paper_ops_replay",
            "Verify packaged event streams still replay to the expected metrics.",
        ),
        _command(
            2,
            "refresh_simulation_paper_handoff",
            "python scripts\\run_simulation_shortlist_paper_handoff.py --config configs\\cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root . --output-dir data\\reports\\paper_ops_handoff --max-user-drawdown -0.30 --min-oos-strict-pass-rate 0.75",
            "Refresh default and primary high-return paper lanes under the agreed drawdown tolerance.",
        ),
        _command(
            3,
            "review_capacity_and_tail_risk",
            "python scripts\\run_simulation_paper_ops_package.py --config configs\\cn_stock_profit_sprint_simulation_shortlist_20260627.json --paper-handoff data\\reports\\paper_ops_handoff\\simulation_paper_handoff.json",
            "Rebuild the consolidated paper-ops package before a paper observation cycle.",
        ),
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


def _decision_text(paper_allowed: bool, blockers: list[str]) -> str:
    if paper_allowed:
        return "Paper observation can proceed with the conservative default lane and the primary high-return lane."
    return "Paper observation is blocked by: " + " / ".join(blockers)


def _candidate_by_id(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any] | None:
    return next((row for row in candidates if str(row.get("candidate_id")) == candidate_id), None)


def _handoff_candidate_by_id(config: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    for row in _list(config.get("paper_simulation_handoff_candidates")):
        item = _dict(row)
        row_id = str(item.get("id") or item.get("candidate_id") or "")
        if row_id == candidate_id:
            return item
    return None


def _choose_default_candidate(candidates: list[dict[str, Any]]) -> str | None:
    for row in candidates:
        if str(row.get("role")) == "default_10bps":
            return str(row.get("candidate_id"))
    ready = [row for row in candidates if str(row.get("handoff_status")) == "ready_for_paper_simulation"]
    return str(ready[0].get("candidate_id")) if ready else None


def _choose_high_return_candidate(candidates: list[dict[str, Any]]) -> str | None:
    ready = [row for row in candidates if str(row.get("handoff_status")) == "ready_for_paper_simulation"]
    if not ready:
        return None
    return str(max(ready, key=lambda row: _metric(row, "computed_annualized_return", "evidence_annualized_return") or -math.inf).get("candidate_id"))


def _final_holdout_status(config: dict[str, Any]) -> str | None:
    final = _dict(config.get("final_holdout_2026"))
    value = final.get("status")
    return str(value) if value is not None else None


def _capacity_safe_through(capacity: dict[str, Any]) -> float | None:
    if "safe_through_aum_multiplier" in capacity:
        return _metric(capacity, "safe_through_aum_multiplier")
    rows = [_dict(row) for row in _list(capacity.get("rows"))]
    safe = [_metric(row, "aum_multiplier") for row in rows if bool(row.get("capacity_safe"))]
    safe = [value for value in safe if value is not None]
    return max(safe) if safe else None


def _capacity_unsafe_from(capacity: dict[str, Any]) -> float | None:
    if "unsafe_from_aum_multiplier" in capacity:
        return _metric(capacity, "unsafe_from_aum_multiplier")
    rows = [_dict(row) for row in _list(capacity.get("rows"))]
    unsafe = [_metric(row, "aum_multiplier") for row in rows if not bool(row.get("capacity_safe", True))]
    unsafe = [value for value in unsafe if value is not None]
    return min(unsafe) if unsafe else None


def _extreme_contribution_share(extreme: dict[str, Any]) -> float:
    value = _first_present(extreme, "extreme_contribution_share")
    if value is not None:
        return _number(value, 0.0)
    summary = _dict(extreme.get("summary"))
    if "extreme_contribution_share" in summary:
        return _number(summary.get("extreme_contribution_share"), 0.0)
    total = _number(_first_present(extreme, "total_contribution_sum"), 0.0)
    extreme_sum = _number(_first_present(extreme, "extreme_contribution_sum"), 0.0)
    if abs(total) <= 1e-12:
        return 0.0
    return extreme_sum / total


def _worst_cost_drawdown(round457: dict[str, Any]) -> float | None:
    cost = _dict(round457.get("cost_stress"))
    drawdowns = [
        _number(value, math.nan)
        for key, value in cost.items()
        if "drawdown" in str(key).lower() and math.isfinite(_number(value, math.nan))
    ]
    return min(drawdowns) if drawdowns else None


def _candidate_worst_cost_drawdown(candidate: dict[str, Any] | None) -> float | None:
    if candidate is None:
        return None
    drawdowns: list[float] = []
    for source in (candidate, _dict(candidate.get("evidence")), _dict(candidate.get("cost_stress"))):
        for key, value in source.items():
            text = str(key).lower()
            if "cost" not in text or "drawdown" not in text:
                continue
            number = _number(value, math.nan)
            if math.isfinite(number):
                drawdowns.append(number)
    return min(drawdowns) if drawdowns else None


def _metric(row: dict[str, Any] | None, *keys: str) -> float | None:
    if row is None:
        return None
    for key in keys:
        if key in row and row.get(key) is not None:
            number = _number(row.get(key), math.nan)
            if math.isfinite(number):
                return number
    return None


def _first_present(row: dict[str, Any], key: str) -> Any:
    if key in row:
        return row.get(key)
    summary = _dict(row.get("summary"))
    if key in summary:
        return summary.get(key)
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _number(value: Any, default: float = 0.0) -> float:
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


def _pct(value: Any) -> str:
    number = _number(value, math.nan)
    if not math.isfinite(number):
        return ""
    return f"{number * 100:.2f}%"


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
