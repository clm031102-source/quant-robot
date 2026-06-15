from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.risk_policy_tiers import (
    PHASE_5_4_STAGE,
    assign_risk_tier,
    normalize_risk_tiers,
    paper_calmar,
    risk_tier_counts,
    tier_label,
)


STAGE = "phase_5_1_risk_candidate_selector"
DEFAULT_MAX_DRAWDOWN_LIMIT = -0.2
DEFAULT_MIN_WALK_FORWARD_SHARPE = 0.3
DEFAULT_MIN_RELATIVE_RETURN = 0.0
DEFAULT_MIN_PAPER_SHARPE = 0.5
DEFAULT_MIN_TRADES = 20


def build_risk_candidate_pack(
    promotion_report: dict[str, Any],
    daily_ops_pack: dict[str, Any] | None = None,
    max_drawdown_limit: float = DEFAULT_MAX_DRAWDOWN_LIMIT,
    min_walk_forward_sharpe: float = DEFAULT_MIN_WALK_FORWARD_SHARPE,
    min_relative_return: float = DEFAULT_MIN_RELATIVE_RETURN,
    min_paper_sharpe: float = DEFAULT_MIN_PAPER_SHARPE,
    min_trades: int = DEFAULT_MIN_TRADES,
    risk_tiers: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    primary_risk_tier: str | None = None,
) -> dict[str, Any]:
    daily = daily_ops_pack or {}
    policy = _policy(max_drawdown_limit, min_walk_forward_sharpe, min_relative_return, min_paper_sharpe, min_trades)
    tiers, primary = normalize_risk_tiers(risk_tiers, policy, primary_risk_tier)
    if tiers:
        policy["primary_risk_tier"] = primary
        policy["risk_tiers"] = tiers
    current_daily_case = _current_daily_case(daily)
    candidates = [
        _candidate_row(index + 1, row, policy, daily, current_daily_case, tiers)
        for index, row in enumerate(_list(promotion_report.get("candidates", [])))
        if isinstance(row, dict)
    ]
    eligible = [row for row in candidates if row.get("risk_status") == "risk_eligible"]
    tier_eligible = [row for row in candidates if row.get("tier_status") == "tier_eligible"]
    selected_source = tier_eligible if tiers else eligible
    selected = _selected_candidate(selected_source, tiers=tiers)
    selection_status = _selection_status(selected, bool(tiers), primary)
    pack = {
        "stage": PHASE_5_4_STAGE if tiers else STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_stage": promotion_report.get("stage"),
        "safety": _safety(),
        "live_boundary_allowed": False,
        "paper_trading_allowed": bool(selected),
        "selection_status": selection_status,
        "policy": policy,
        "daily_ops_context": _daily_context(daily),
        "summary": _summary(candidates),
        "selected_candidate": selected,
        "candidates": candidates,
        "next_actions": _next_actions(selection_status, policy),
    }
    pack["markdown"] = render_risk_candidate_markdown(pack)
    return _sanitize(pack)


def write_risk_candidate_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "risk_candidate_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "risk_candidate_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("candidates", [])).to_csv(output_path / "risk_candidate_candidates.csv", index=False)
    pd.DataFrame([pack.get("summary", {})]).to_csv(output_path / "risk_candidate_summary.csv", index=False)


def render_risk_candidate_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    policy = pack.get("policy", {}) if isinstance(pack.get("policy"), dict) else {}
    selected = pack.get("selected_candidate") if isinstance(pack.get("selected_candidate"), dict) else None
    lines = [
        "# Phase 5.1 Risk Candidate Selector",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Selection: {pack.get('selection_status', 'unknown')}",
        f"- Risk eligible candidates: {summary.get('risk_eligible_candidates', 0)}",
        f"- Tier eligible candidates: {summary.get('tier_eligible_candidates', 0)}",
        f"- Max drawdown limit: {policy.get('max_drawdown_limit', DEFAULT_MAX_DRAWDOWN_LIMIT)}",
        f"- Primary risk tier: {policy.get('primary_risk_tier', 'legacy_policy')}",
        f"- Paper trading allowed: {pack.get('paper_trading_allowed', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Selected Candidate",
        "",
    ]
    if selected:
        lines.extend(
            [
                f"- Case: {selected.get('case_id')}",
                f"- Market: {selected.get('market')}",
                f"- Factor: {selected.get('factor_name')}",
                f"- Risk tier: {selected.get('risk_tier')}",
                f"- Walk-forward drawdown: {selected.get('walk_forward_max_drawdown')}",
                f"- Paper drawdown: {selected.get('paper_max_drawdown')}",
                f"- Paper Calmar: {selected.get('paper_calmar')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Candidate Screening",
            "",
            "| Rank | Case | Status | Tier | WF Sharpe | WF Drawdown | Paper Sharpe | Paper Drawdown | Paper Calmar | Rejections |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("candidates", [])[:20]:
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('screen_rank', '')} | "
                f"{row.get('case_id', '')} | "
                f"{row.get('risk_status', '')} | "
                f"{row.get('risk_tier', '')} | "
                f"{_round(row.get('walk_forward_sharpe'))} | "
                f"{_round(row.get('walk_forward_max_drawdown'))} | "
                f"{_round(row.get('paper_sharpe'))} | "
                f"{_round(row.get('paper_max_drawdown'))} | "
                f"{_round(row.get('paper_calmar'))} | "
                f"{', '.join(row.get('rejection_reasons', [])) if isinstance(row.get('rejection_reasons'), list) else ''} |"
            )
    return "\n".join(lines) + "\n"


def _candidate_row(
    rank: int,
    row: dict[str, Any],
    policy: dict[str, Any],
    daily_ops_pack: dict[str, Any],
    current_daily_case: str | None,
    risk_tiers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    walk = row.get("walk_forward", {}) if isinstance(row.get("walk_forward"), dict) else {}
    paper = row.get("paper", {}) if isinstance(row.get("paper"), dict) else {}
    case_id = str(row.get("case_id", "unknown"))
    candidate = {
        "screen_rank": rank,
        "case_id": case_id,
        "market": row.get("market"),
        "factor_name": row.get("factor_name"),
        "promotion_rank": _int(row.get("promotion_rank"), rank),
        "promotion_status": row.get("promotion_status"),
        "score": _float(row.get("score")),
        "duplicate_of": row.get("duplicate_of"),
        "walk_forward_status": walk.get("validation_status"),
        "walk_forward_sharpe": _float(walk.get("test_sharpe")),
        "walk_forward_relative_return": _float(walk.get("test_relative_return")),
        "walk_forward_max_drawdown": _float(walk.get("test_max_drawdown")),
        "walk_forward_trades": _int(walk.get("test_trades")),
        "paper_matched": bool(paper.get("matched")),
        "paper_sharpe": _float(paper.get("sharpe")),
        "paper_max_drawdown": _float(paper.get("max_drawdown")),
        "paper_total_return": _float(paper.get("total_return")),
        "is_current_daily_candidate": case_id == current_daily_case,
    }
    candidate["paper_calmar"] = _round(paper_calmar(candidate["paper_total_return"], candidate["paper_max_drawdown"]))
    candidate["rejection_reasons"] = _rejection_reasons(candidate, policy, daily_ops_pack)
    candidate["risk_status"] = "risk_eligible" if not candidate["rejection_reasons"] else "rejected"
    if risk_tiers:
        tier_rejections = {
            str(tier.get("tier_id")): _rejection_reasons(candidate, tier, daily_ops_pack)
            for tier in risk_tiers
        }
        eligible_tiers, assigned_tier = assign_risk_tier(tier_rejections, risk_tiers)
        candidate["risk_tier_rejections"] = tier_rejections
        candidate["eligible_risk_tiers"] = eligible_tiers
        candidate["risk_tier"] = assigned_tier
        candidate["risk_tier_label"] = tier_label(risk_tiers, assigned_tier)
        candidate["tier_status"] = "tier_eligible" if assigned_tier else "tier_rejected"
    else:
        candidate["eligible_risk_tiers"] = []
        candidate["tier_status"] = "not_evaluated"
    return candidate


def _rejection_reasons(candidate: dict[str, Any], policy: dict[str, Any], daily_ops_pack: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if candidate.get("duplicate_of"):
        reasons.append("duplicate_candidate")
    if candidate.get("walk_forward_status") != "accepted":
        reasons.append("walk_forward_not_accepted")
    if _float(candidate.get("walk_forward_sharpe")) < _float(policy.get("min_walk_forward_sharpe")):
        reasons.append("walk_forward_sharpe_below_min")
    if _float(candidate.get("walk_forward_relative_return")) < _float(policy.get("min_relative_return")):
        reasons.append("relative_return_below_min")
    if _float(candidate.get("walk_forward_max_drawdown")) < _float(policy.get("max_drawdown_limit")):
        reasons.append("walk_forward_drawdown_breach")
    if _int(candidate.get("walk_forward_trades")) < _int(policy.get("min_trades")):
        reasons.append("walk_forward_trades_below_min")
    if not candidate.get("paper_matched"):
        reasons.append("paper_missing_or_unmatched")
    if _float(candidate.get("paper_sharpe")) < _float(policy.get("min_paper_sharpe")):
        reasons.append("paper_sharpe_below_min")
    if _float(candidate.get("paper_max_drawdown")) < _float(policy.get("max_drawdown_limit")):
        reasons.append("paper_drawdown_breach")
    if _float(candidate.get("paper_calmar")) < _float(policy.get("min_paper_calmar")):
        reasons.append("paper_calmar_below_min")
    if _float(candidate.get("paper_total_return")) < _float(policy.get("min_total_return")):
        reasons.append("paper_total_return_below_min")
    if candidate.get("is_current_daily_candidate") and _daily_status(daily_ops_pack) != "paper_ready":
        reasons.append("daily_ops_current_candidate_blocked")
    return reasons


def _selected_candidate(eligible: list[dict[str, Any]], tiers: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    if not eligible:
        return None
    if tiers:
        selected = sorted(
            eligible,
            key=lambda row: (
                -_float(row.get("paper_total_return")),
                -_float(row.get("paper_calmar")),
                -_float(row.get("paper_sharpe")),
                -_float(row.get("walk_forward_relative_return")),
                _int(row.get("promotion_rank"), 999999),
            ),
        )[0]
    else:
        selected = sorted(
            eligible,
            key=lambda row: (
                -_float(row.get("walk_forward_relative_return")),
                -_float(row.get("paper_sharpe")),
                _float(row.get("paper_max_drawdown")),
                _int(row.get("promotion_rank"), 999999),
            ),
        )[0]
    return {
        "case_id": selected.get("case_id"),
        "market": selected.get("market"),
        "factor_name": selected.get("factor_name"),
        "risk_tier": selected.get("risk_tier"),
        "risk_tier_label": selected.get("risk_tier_label"),
        "promotion_rank": selected.get("promotion_rank"),
        "score": selected.get("score"),
        "walk_forward_sharpe": selected.get("walk_forward_sharpe"),
        "walk_forward_relative_return": selected.get("walk_forward_relative_return"),
        "walk_forward_max_drawdown": selected.get("walk_forward_max_drawdown"),
        "paper_sharpe": selected.get("paper_sharpe"),
        "paper_max_drawdown": selected.get("paper_max_drawdown"),
        "paper_total_return": selected.get("paper_total_return"),
        "paper_calmar": selected.get("paper_calmar"),
        "live_order_allowed": False,
    }


def _summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    tier_rows = [row for row in candidates if row.get("tier_status") == "tier_eligible"]
    tier_ids = []
    for row in candidates:
        if row.get("risk_tier") and row.get("risk_tier") not in tier_ids:
            tier_ids.append(row.get("risk_tier"))
    tier_templates = [{"tier_id": tier_id} for tier_id in tier_ids]
    return {
        "candidates": len(candidates),
        "risk_eligible_candidates": sum(1 for row in candidates if row.get("risk_status") == "risk_eligible"),
        "tier_eligible_candidates": len(tier_rows),
        "risk_tier_counts": risk_tier_counts(tier_rows, tier_templates),
        "rejected_candidates": sum(1 for row in candidates if row.get("risk_status") == "rejected"),
        "duplicate_candidates": sum(1 for row in candidates if row.get("duplicate_of")),
        "paper_matched_candidates": sum(1 for row in candidates if row.get("paper_matched")),
    }


def _next_actions(selection_status: str, policy: dict[str, Any]) -> list[dict[str, Any]]:
    if selection_status == "risk_candidate_selected":
        return [
            {
                "action": "run_daily_ops_for_selected_candidate",
                "reason": "A risk-eligible paper candidate exists; generate a fresh signal and paper simulation before any observation.",
                "local_only": True,
            }
        ]
    return [
        {
            "action": "run_constrained_candidate_search",
            "reason": f"No candidate passed max_drawdown_limit={policy.get('max_drawdown_limit')}; search higher-return profiles within the configured risk tier if aggressive growth is enabled.",
            "local_only": True,
        },
        {
            "action": "expand_paper_sensitivity_grid",
            "reason": "Promotion report has insufficient candidates with matched paper evidence under the current risk policy.",
            "local_only": True,
        },
    ]


def _daily_context(daily_ops_pack: dict[str, Any]) -> dict[str, Any]:
    decision = daily_ops_pack.get("decision", {}) if isinstance(daily_ops_pack.get("decision"), dict) else {}
    candidate = daily_ops_pack.get("candidate", {}) if isinstance(daily_ops_pack.get("candidate"), dict) else {}
    return {
        "case_id": candidate.get("case_id"),
        "status": decision.get("status"),
        "paper_trading_allowed": bool(decision.get("paper_trading_allowed", False)),
        "non_manual_blocking_reasons": decision.get("non_manual_blocking_reasons", []),
    }


def _policy(
    max_drawdown_limit: float,
    min_walk_forward_sharpe: float,
    min_relative_return: float,
    min_paper_sharpe: float,
    min_trades: int,
) -> dict[str, Any]:
    return {
        "max_drawdown_limit": -abs(_float(max_drawdown_limit, DEFAULT_MAX_DRAWDOWN_LIMIT)),
        "min_walk_forward_sharpe": _float(min_walk_forward_sharpe, DEFAULT_MIN_WALK_FORWARD_SHARPE),
        "min_relative_return": _float(min_relative_return, DEFAULT_MIN_RELATIVE_RETURN),
        "min_paper_sharpe": _float(min_paper_sharpe, DEFAULT_MIN_PAPER_SHARPE),
        "min_trades": _int(min_trades, DEFAULT_MIN_TRADES),
        "min_paper_calmar": 0.0,
        "min_total_return": 0.0,
    }


def _selection_status(selected: dict[str, Any] | None, tier_mode: bool, primary_risk_tier: str | None) -> str:
    if not selected:
        return "no_risk_eligible_candidate"
    if not tier_mode:
        return "risk_candidate_selected"
    if selected.get("risk_tier") == primary_risk_tier:
        return "risk_candidate_selected"
    return "risk_tier_candidate_selected"


def _current_daily_case(daily_ops_pack: dict[str, Any]) -> str | None:
    candidate = daily_ops_pack.get("candidate", {}) if isinstance(daily_ops_pack.get("candidate"), dict) else {}
    case_id = candidate.get("case_id")
    return str(case_id) if case_id else None


def _daily_status(daily_ops_pack: dict[str, Any]) -> str:
    decision = daily_ops_pack.get("decision", {}) if isinstance(daily_ops_pack.get("decision"), dict) else {}
    return str(decision.get("status", "missing"))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _round(value: Any) -> str:
    return f"{_float(value):.4f}"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
