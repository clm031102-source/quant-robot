from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import pandas as pd

from quant_robot.portfolio.rebalance import FORBIDDEN_REAL_ACCOUNT_COLUMNS, build_rebalance_plan


STAGE = "phase_6_0_daily_trade_advisory"
PRETRADE_WORKFLOW_STAGE = "phase_6_1_daily_pretrade_workflow"
PRETRADE_READINESS_STAGE = "phase_6_2_manual_pretrade_readiness"
MANUAL_BROKER_HANDOFF_STAGE = "phase_6_3_manual_broker_handoff"
TRADE_SYSTEM_STAGE = "phase_6_4_manual_trade_system_protocol"
DAILY_REHEARSAL_STAGE = "phase_6_5_daily_rehearsal_daybook"
POST_CLOSE_JOURNAL_STAGE = "phase_6_6_post_close_journal_template"
LIVE_TRANSITION_STAGE = "phase_6_7_live_transition_plan"
BEGINNER_ACTION_SUMMARY_STAGE = "phase_6_8_beginner_action_summary"
LIVE_READINESS_GATE_STAGE = "phase_6_9_daily_live_readiness_gate"
BEGINNER_TRADE_ACTION_CARD_STAGE = "phase_6_10_beginner_trade_action_card"
DAILY_LIVE_PILOT_BRIEF_STAGE = "phase_6_11_daily_live_pilot_brief"
SMALL_CAPITAL_OBSERVATION_GATE_STAGE = "phase_6_12_small_capital_observation_gate"
MANUAL_TICKET_EXPORT_STAGE = "phase_6_13_manual_ticket_export"
DAILY_TRADE_DECISION_SHEET_STAGE = "phase_6_14_daily_trade_decision_sheet"
DAILY_TRADING_SYSTEM_BLUEPRINT_STAGE = "phase_6_15_daily_trading_system_blueprint"
DAILY_SIGNAL_EXECUTION_BRIDGE_STAGE = "phase_6_16_daily_signal_execution_bridge"
REAL_WORLD_MANUAL_HANDOFF_GATE_STAGE = "phase_6_17_real_world_manual_handoff_gate"
DAILY_DEPLOYMENT_READINESS_STAGE = "phase_6_18_daily_deployment_readiness_pack"
LIVE_PROFITABILITY_READINESS_STAGE = "phase_6_19_live_profitability_readiness_scorecard"
DAILY_FACTOR_HEALTH_MONITOR_STAGE = "phase_6_20_daily_factor_health_monitor"
DAILY_REAL_MONEY_TRANSITION_GATE_STAGE = "phase_6_21_daily_real_money_transition_gate"
DAILY_CANDIDATE_POOL_TOP20_STAGE = "phase_6_22_daily_candidate_pool_top20"
MANUAL_EXECUTION_AUDIT_STAGE = "phase_6_23_manual_execution_audit"
DAILY_MANUAL_TRADING_SESSION_STAGE = "phase_6_24_daily_manual_trading_session"
DAILY_PAPER_ALLOCATION_PLAYBOOK_STAGE = "phase_6_25_daily_paper_allocation_playbook"
DAILY_PRE_EXECUTION_GUARD_STAGE = "phase_6_26_daily_pre_execution_guard"
DAILY_SAME_PARAMETER_PAPER_REHEARSAL_STAGE = "phase_6_27_daily_same_parameter_paper_rehearsal"
DAILY_BEGINNER_EXECUTION_ANSWER_STAGE = "phase_6_28_daily_beginner_execution_answer"
DAILY_EXECUTION_RISK_CIRCUIT_BREAKER_STAGE = "phase_6_29_daily_execution_risk_circuit_breaker"
DAILY_OPERATOR_MISSION_CONTROL_STAGE = "phase_6_30_daily_operator_mission_control"
DAILY_LIVE_TRADING_SYSTEM_STATUS_STAGE = "phase_6_31_daily_live_trading_system_status"
DAILY_MANUAL_OBSERVATION_PACKET_STAGE = "phase_6_32_daily_manual_observation_packet"
CANDIDATE_EVIDENCE_REPAIR_PLAN_STAGE = "phase_6_33_candidate_evidence_repair_plan"
SAFETY_NOTICE = "仅研究到模拟盘：不连接券商、不读取账户、不生成实盘委托、不自动下单。"
BOARD_LOT_SIZE = 100
SMALL_CAPITAL_OBSERVATION_MAX_INITIAL_CAPITAL = 10000.0
SMALL_CAPITAL_OBSERVATION_MAX_SINGLE_TICKET_NOTIONAL = 1000.0
SMALL_CAPITAL_OBSERVATION_MAX_DAILY_LOSS = 200.0
MANUAL_PRICE_DEVIATION_GUARD_PCT = 0.005
MANUAL_MAX_SLIPPAGE_BPS = 10
MANUAL_ESTIMATED_COMMISSION_BPS = 5.0
MANUAL_MAX_PARTICIPATION_RATE = 0.01
MANUAL_MAX_CONSECUTIVE_LOSS_DAYS = 3
RECENT_OBSERVATION_MIN_COUNT = 3
RECENT_OBSERVATION_MAX_LOSS_PCT = 0.02
RECENT_OBSERVATION_MIN_WIN_RATE = 0.40
PAPER_FLAT_POSITION_ASSET_IDS = {"PAPER_FLAT_CASH", "CN_ETF_PAPER_FLAT"}
DAILY_CANDIDATE_MIN_TRADE_COUNT = 30
DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS = (
    "sharpe",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "trade_count",
)
LIQUIDITY_REFERENCE_FIELDS = (
    "liquidity_reference_value",
    "avg_daily_turnover_value",
    "avg_daily_amount",
    "avg_daily_value",
    "avg_daily_turnover",
    "turnover_amount",
    "daily_amount",
    "amount",
)
DEFAULT_RISK_PROFILE_ID = "balanced_20dd"
RISK_PROFILE_SPECS = [
    {
        "profile_id": "conservative_10dd",
        "label": "保守观察",
        "max_gross_exposure": 0.30,
        "max_single_etf_weight": 0.15,
        "min_cash_weight": 0.70,
        "max_acceptable_drawdown": 0.10,
        "daily_loss_stop": 0.01,
        "plain_use": "适合刚进模拟盘或小资金观察第一阶段，宁可少赚也先验证流程。",
    },
    {
        "profile_id": DEFAULT_RISK_PROFILE_ID,
        "label": "标准观察",
        "max_gross_exposure": 0.60,
        "max_single_etf_weight": 0.30,
        "min_cash_weight": 0.40,
        "max_acceptable_drawdown": 0.20,
        "daily_loss_stop": 0.02,
        "plain_use": "适合模拟盘稳定后，但仍需要严格看回撤、成交和异常价格。",
    },
    {
        "profile_id": "aggressive_30dd",
        "label": "进取观察",
        "max_gross_exposure": 1.00,
        "max_single_etf_weight": 0.40,
        "min_cash_weight": 0.00,
        "max_acceptable_drawdown": 0.30,
        "daily_loss_stop": 0.03,
        "plain_use": "只有你明确接受约 30% 回撤，且模拟盘/小资金闸门持续通过时才考虑。",
    },
]


def select_daily_top_factor_candidates(
    leaderboard: dict[str, Any],
    runnable_factor_names: Iterable[str] | None = None,
    limit: int = 3,
    primary_market: str = "CN_ETF",
) -> list[dict[str, Any]]:
    runnable = {str(name) for name in (runnable_factor_names or []) if str(name).strip()}
    source_rows = _leaderboard_rows(leaderboard)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        market = str(row.get("market") or "").upper()
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        if market != primary_market or not factor_name:
            continue
        if runnable and factor_name not in runnable:
            continue
        eligible, eligibility_reason = _daily_advisory_candidate_eligibility(row)
        if not eligible:
            continue
        key = factor_name
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            {
                "rank": _int(row.get("rank"), len(selected) + 1),
                "case_id": str(row.get("case_id") or factor_name),
                "factor_name": factor_name,
                "market": market,
                "family": row.get("family"),
                "sharpe": _float_or_none(row.get("sharpe")),
                "annualized_return": _float_or_none(row.get("annualized_return")),
                "total_return": _float_or_none(row.get("total_return")),
                "max_drawdown": _float_or_none(row.get("max_drawdown")),
                "win_rate": _float_or_none(row.get("win_rate")),
                "rank_ic": _float_or_none(row.get("rank_ic")),
                "trade_count": _float_or_none(row.get("trade_count")),
                "score_metric": row.get("score_metric"),
                "promotion_label": row.get("promotion_label"),
                "plain_conclusion": row.get("plain_conclusion"),
                "params": row.get("params") if isinstance(row.get("params"), dict) else {},
                "signalable": True,
                "advisory_eligible": True,
                "advisory_eligibility_reason": eligibility_reason,
            }
        )
        if len(selected) >= max(1, int(limit)):
            break
    return selected


def build_daily_candidate_pool_top20(
    leaderboard: dict[str, Any],
    selected_candidates: list[dict[str, Any]] | None = None,
    runnable_factor_names: Iterable[str] | None = None,
    limit: int = 20,
    primary_market: str = "CN_ETF",
) -> dict[str, Any]:
    runnable = {str(name) for name in (runnable_factor_names or []) if str(name).strip()}
    selected = [row for row in (selected_candidates or []) if isinstance(row, dict)]
    selected_case_ids = {str(row.get("case_id") or "") for row in selected if str(row.get("case_id") or "").strip()}
    selected_factor_to_case: dict[str, str] = {}
    for row in selected:
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        case_id = str(row.get("case_id") or factor_name).strip()
        if factor_name and factor_name not in selected_factor_to_case:
            selected_factor_to_case[factor_name] = case_id

    rows: list[dict[str, Any]] = []
    for source_index, source in enumerate(_leaderboard_rows(leaderboard), start=1):
        market = str(source.get("market") or "").upper()
        factor_name = str(source.get("factor_name") or source.get("factor") or "").strip()
        if market != primary_market or not factor_name:
            continue
        case_id = str(source.get("case_id") or factor_name).strip()
        eligible, eligibility_reason = _daily_advisory_candidate_eligibility(source)
        runnable_today = not runnable or factor_name in runnable
        if case_id in selected_case_ids:
            selection_status = "selected_top3"
            selection_reason = "selected_for_today_top3_signal"
        elif factor_name in selected_factor_to_case:
            selection_status = "duplicate_factor_name_not_selected"
            selection_reason = f"same_factor_already_selected:{selected_factor_to_case[factor_name]}"
        elif not runnable_today:
            selection_status = "not_runnable"
            selection_reason = "factor_not_registered_in_runtime"
        elif not eligible:
            selection_status = "blocked"
            selection_reason = eligibility_reason
        else:
            selection_status = "eligible_not_selected"
            selection_reason = "outside_today_top3_limit"

        rows.append(
            {
                "rank": _int(source.get("rank"), source_index),
                "case_id": case_id,
                "factor_name": factor_name,
                "market": market,
                "family": source.get("family"),
                "selection_status": selection_status,
                "selection_reason": selection_reason,
                "advisory_eligible": bool(eligible),
                "advisory_eligibility_reason": eligibility_reason,
                "runnable_today": bool(runnable_today),
                "direct_buy_allowed": False,
                "sharpe": _float_or_none(source.get("sharpe")),
                "annualized_return": _float_or_none(source.get("annualized_return")),
                "total_return": _float_or_none(source.get("total_return")),
                "max_drawdown": _float_or_none(source.get("max_drawdown")),
                "win_rate": _float_or_none(source.get("win_rate")),
                "rank_ic": _float_or_none(source.get("rank_ic")),
                "trade_count": _float_or_none(source.get("trade_count")),
                "score_metric": source.get("score_metric"),
                "promotion_label": source.get("promotion_label"),
                "ranking_quality": source.get("ranking_quality"),
                "ranking_reasons": source.get("ranking_reasons") if isinstance(source.get("ranking_reasons"), list) else [],
                "plain_conclusion": source.get("plain_conclusion"),
                "params": source.get("params") if isinstance(source.get("params"), dict) else {},
                "source_file": source.get("source_file") or source.get("source_path"),
            }
        )
        if len(rows) >= max(1, int(limit or 20)):
            break

    selected_count = sum(1 for row in rows if row["selection_status"] == "selected_top3")
    blocked_count = sum(1 for row in rows if row["selection_status"] in {"blocked", "not_runnable"})
    return _sanitize(
        {
            "stage": DAILY_CANDIDATE_POOL_TOP20_STAGE,
            "primary_market": primary_market,
            "summary": {
                "primary_market": primary_market,
                "pool_limit": max(1, int(limit or 20)),
                "row_count": len(rows),
                "selected_top3_count": selected_count,
                "runnable_row_count": sum(1 for row in rows if row["runnable_today"]),
                "blocked_row_count": blocked_count,
                "direct_buy_from_leaderboard_allowed": False,
                "plain_rule": (
                    "Top20 is an audit pool; selected_top3 rows can feed today's signal snapshot, "
                    "but no row is a direct order."
                ),
            },
            "rows": rows,
        }
    )


def _daily_candidate_pool_from_candidates(
    candidates: list[dict[str, Any]],
    primary_market: str = "CN_ETF",
) -> dict[str, Any]:
    rows = []
    for index, row in enumerate([item for item in candidates if isinstance(item, dict)], start=1):
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        market = str(row.get("market") or primary_market).upper()
        rows.append(
            {
                "rank": _int(row.get("rank"), index),
                "case_id": str(row.get("case_id") or factor_name),
                "factor_name": factor_name,
                "market": market,
                "family": row.get("family"),
                "selection_status": "selected_top3" if market == primary_market else "outside_primary_market",
                "selection_reason": "pack_selected_candidate",
                "advisory_eligible": bool(row.get("advisory_eligible", True)),
                "advisory_eligibility_reason": row.get("advisory_eligibility_reason") or "pack_selected_candidate",
                "runnable_today": True,
                "direct_buy_allowed": False,
                "sharpe": _float_or_none(row.get("sharpe")),
                "annualized_return": _float_or_none(row.get("annualized_return")),
                "total_return": _float_or_none(row.get("total_return")),
                "max_drawdown": _float_or_none(row.get("max_drawdown")),
                "win_rate": _float_or_none(row.get("win_rate")),
                "rank_ic": _float_or_none(row.get("rank_ic")),
                "trade_count": _float_or_none(row.get("trade_count")),
                "score_metric": row.get("score_metric"),
                "promotion_label": row.get("promotion_label"),
                "ranking_quality": row.get("ranking_quality"),
                "ranking_reasons": row.get("ranking_reasons") if isinstance(row.get("ranking_reasons"), list) else [],
                "plain_conclusion": row.get("plain_conclusion"),
                "params": row.get("params") if isinstance(row.get("params"), dict) else {},
            }
        )
    selected_count = sum(1 for row in rows if row["selection_status"] == "selected_top3")
    return _sanitize(
        {
            "stage": DAILY_CANDIDATE_POOL_TOP20_STAGE,
            "primary_market": primary_market,
            "summary": {
                "primary_market": primary_market,
                "pool_limit": 20,
                "row_count": len(rows),
                "selected_top3_count": selected_count,
                "runnable_row_count": len(rows),
                "blocked_row_count": 0,
                "direct_buy_from_leaderboard_allowed": False,
                "plain_rule": "Fallback pool built from selected candidates; it is still review-only and never an order list.",
            },
            "rows": rows[:20],
        }
    )


def _daily_advisory_candidate_eligibility(row: dict[str, Any]) -> tuple[bool, str]:
    if "daily_signal_eligible" in row:
        reason = str(row.get("daily_signal_eligibility_reason") or "daily_signal_eligible")
        return (bool(row.get("daily_signal_eligible")), reason)

    status_text = " ".join(
        str(row.get(key) or "")
        for key in (
            "status",
            "decision",
            "promotion_status",
            "gate_status",
            "selection_status",
            "review_status",
            "promotion_label",
        )
    ).lower()
    if any(token in status_text for token in ("blocked", "rejected", "research_only", "not_paper_ready", "duplicate")):
        return (False, "blocked_or_research_only_candidate")

    quality = str(row.get("ranking_quality") or "").strip().lower()
    if quality and quality != "qualified":
        return (False, f"ranking_quality_{quality}")

    if any(token in status_text for token in ("paper_ready", "manual_live_review", "manual_review", "accepted", "watchlist")):
        return (True, "explicit_advisory_candidate_status")

    score_metric = str(row.get("score_metric") or "").lower()
    if row.get("has_oos_evidence") is True and score_metric.startswith(("paper", "walk_forward", "oos", "test")):
        return (True, "oos_or_paper_evidence")

    return (False, "missing_paper_ready_or_oos_gate")


def _fallback_signal_only(candidates: list[dict[str, Any]]) -> bool:
    return bool(candidates) and all(bool(row.get("fallback_baseline")) for row in candidates)


def build_daily_trade_advisory_pack(
    candidates: list[dict[str, Any]],
    signal_snapshots: list[dict[str, Any]],
    run_date: str | None = None,
    portfolio_value: float = 100000.0,
    max_gross_exposure: float = 1.0,
    risk_profile_id: str | None = None,
    current_positions: list[dict[str, Any]] | None = None,
    evidence_snapshot: dict[str, Any] | None = None,
    candidate_pool_top20: dict[str, Any] | None = None,
    manual_available_cash: float | None = None,
) -> dict[str, Any]:
    signal_cards = [_signal_card(candidate, _matching_signal(candidate, signal_snapshots)) for candidate in candidates]
    selected_profile = _risk_profile_by_id(risk_profile_id)
    applied_max_gross_exposure = _applied_max_gross_exposure(max_gross_exposure, selected_profile)
    manual_cash_value = _float_or_none(manual_available_cash)
    combined_targets = _combined_targets(
        signal_cards,
        portfolio_value=portfolio_value,
        max_gross_exposure=applied_max_gross_exposure,
    )
    fallback_signal_only = _fallback_signal_only(candidates)
    position_validation = _current_position_validation(current_positions, combined_targets)
    manual_plan_blocked_reason = ""
    if fallback_signal_only:
        manual_plan_blocked_reason = "fallback_baseline_not_tradeable"
    elif position_validation["status"] == "not_provided" and combined_targets:
        manual_plan_blocked_reason = "current_positions_not_provided"
    position_rows = position_validation["rows"] if position_validation["status"] != "error" else []
    manual_plan = (
        []
        if position_validation["status"] == "error" or manual_plan_blocked_reason
        else _manual_trade_plan(
            combined_targets,
            current_positions=position_rows,
            portfolio_value=portfolio_value,
            risk_profile=selected_profile,
        )
    )
    pack = {
        "stage": STAGE,
        "run_date": run_date or date.today().isoformat(),
        "safety": SAFETY_NOTICE,
        "summary": {
            "selected_factor_count": len(candidates),
            "signal_count": sum(1 for card in signal_cards if card["status"] == "signal_ready"),
            "combined_target_count": len(combined_targets),
            "manual_ticket_count": len(manual_plan),
            "current_position_count": len(position_rows),
            "current_position_issue_count": position_validation["issue_count"],
            "current_position_status": position_validation["status"],
            "fallback_signal_only": fallback_signal_only,
            "manual_trade_plan_blocked": bool(manual_plan_blocked_reason),
            "manual_trade_plan_blocked_reason": manual_plan_blocked_reason,
            "manual_execution_required": True,
            "paper_simulation_recommended": True,
            "risk_profile_id": selected_profile.get("profile_id") if selected_profile else "custom_current_parameters",
            "risk_profile_label": selected_profile.get("label") if selected_profile else "自定义参数",
            "requested_max_gross_exposure": max_gross_exposure,
            "applied_max_gross_exposure": applied_max_gross_exposure,
            "portfolio_value": portfolio_value,
            "manual_available_cash": manual_cash_value,
            "manual_available_cash_source": "manual_input_only" if manual_cash_value is not None else "not_provided",
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "next_action": "先复核今日前三因子和目标仓位，再查看模拟盘表现；若要实盘，只能由人手工在券商端决定是否交易。",
        },
        "factors": candidates,
        "signal_cards": signal_cards,
        "combined_target_count": len(combined_targets),
        "combined_targets": combined_targets,
        "current_positions": position_rows,
        "current_position_validation": position_validation,
        "manual_trade_plan": manual_plan,
        "operator_checklist": _operator_checklist(),
        "live_profitability_evidence_snapshot": _live_profitability_evidence_snapshot(evidence_snapshot),
        "candidate_pool_top20": (
            candidate_pool_top20
            if isinstance(candidate_pool_top20, dict)
            else _daily_candidate_pool_from_candidates(candidates)
        ),
        "markdown": "",
    }
    pack["pretrade_readiness"] = _build_pretrade_readiness(pack)
    pack["candidate_evidence_repair_plan"] = build_candidate_evidence_repair_plan(pack)
    pack["manual_broker_handoff"] = _build_manual_broker_handoff(pack)
    pack["operator_next_actions"] = _operator_next_actions(
        pack,
        pack["pretrade_readiness"],
        pack["manual_broker_handoff"],
    )
    pack["pretrade_workflow"] = build_daily_pretrade_workflow(pack)
    pack["trade_system"] = build_manual_trade_system_protocol(pack)
    pack["daily_rehearsal_daybook"] = build_daily_rehearsal_daybook(pack)
    pack["post_close_journal_template"] = build_post_close_journal_template(pack)
    pack["live_transition_plan"] = build_live_transition_plan(pack)
    pack["beginner_action_summary"] = build_beginner_action_summary(pack)
    pack["daily_live_readiness_gate"] = build_daily_live_readiness_gate(pack)
    pack["beginner_trade_action_card"] = build_beginner_trade_action_card(pack)
    pack["small_capital_observation_gate"] = build_small_capital_observation_gate(pack)
    pack["daily_live_pilot_brief"] = build_daily_live_pilot_brief(pack)
    pack["manual_ticket_export"] = build_manual_ticket_export(pack)
    pack["manual_execution_audit"] = build_manual_execution_audit(pack, [])
    pack["daily_trade_decision_sheet"] = build_daily_trade_decision_sheet(pack)
    pack["trading_system_blueprint"] = build_daily_trading_system_blueprint(pack)
    pack["daily_signal_execution_bridge"] = build_daily_signal_execution_bridge(pack)
    pack["real_world_manual_handoff_gate"] = build_real_world_manual_handoff_gate(pack)
    pack["daily_deployment_readiness"] = build_daily_deployment_readiness_pack(pack)
    pack["live_profitability_readiness"] = build_live_profitability_readiness_scorecard(pack)
    pack["daily_factor_health_monitor"] = build_daily_factor_health_monitor(pack)
    pack["daily_execution_risk_circuit_breaker"] = build_daily_execution_risk_circuit_breaker(pack)
    pack["daily_real_money_transition_gate"] = build_daily_real_money_transition_gate(pack)
    pack["daily_manual_trading_session"] = build_daily_manual_trading_session(pack)
    pack["daily_paper_allocation_playbook"] = build_daily_paper_allocation_playbook(pack)
    pack["daily_pre_execution_guard"] = build_daily_pre_execution_guard(pack)
    pack["daily_same_parameter_paper_rehearsal"] = build_daily_same_parameter_paper_rehearsal(pack)
    pack["daily_beginner_execution_answer"] = build_daily_beginner_execution_answer(pack)
    pack["daily_live_trading_system_status"] = build_daily_live_trading_system_status(pack)
    pack["daily_manual_observation_packet"] = build_daily_manual_observation_packet(pack)
    pack["daily_operator_mission_control"] = build_daily_operator_mission_control(pack)
    pack["summary"]["live_transition_status"] = pack["live_transition_plan"]["summary"]["status"]
    pack["summary"]["trading_system_status"] = pack["trading_system_blueprint"]["summary"]["status"]
    pack["summary"]["execution_bridge_status"] = pack["daily_signal_execution_bridge"]["summary"]["status"]
    pack["summary"]["real_world_handoff_status"] = pack["real_world_manual_handoff_gate"]["summary"]["decision"]
    pack["summary"]["deployment_readiness_status"] = pack["daily_deployment_readiness"]["summary"]["decision"]
    pack["summary"]["live_profitability_readiness_status"] = pack["live_profitability_readiness"]["summary"]["decision"]
    pack["summary"]["factor_health_status"] = pack["daily_factor_health_monitor"]["summary"]["decision"]
    pack["summary"]["real_money_transition_status"] = pack["daily_real_money_transition_gate"]["summary"]["decision"]
    pack["summary"]["manual_trading_session_status"] = pack["daily_manual_trading_session"]["summary"]["session_status"]
    pack["summary"]["execution_risk_circuit_status"] = pack["daily_execution_risk_circuit_breaker"]["summary"][
        "decision"
    ]
    pack["summary"]["paper_allocation_playbook_status"] = pack["daily_paper_allocation_playbook"]["summary"][
        "allocation_status"
    ]
    pack["summary"]["pre_execution_guard_status"] = pack["daily_pre_execution_guard"]["summary"]["guard_status"]
    pack["summary"]["same_parameter_paper_rehearsal_status"] = pack["daily_same_parameter_paper_rehearsal"]["summary"][
        "rehearsal_status"
    ]
    pack["summary"]["beginner_execution_answer_status"] = pack["daily_beginner_execution_answer"]["summary"][
        "allowed_mode"
    ]
    pack["summary"]["operator_mission_status"] = pack["daily_operator_mission_control"]["summary"]["mission_status"]
    pack["summary"]["live_trading_system_status"] = pack["daily_live_trading_system_status"]["summary"][
        "go_live_state"
    ]
    pack["summary"]["manual_observation_packet_status"] = pack["daily_manual_observation_packet"]["summary"][
        "packet_status"
    ]
    pack["markdown"] = render_daily_trade_advisory_markdown(pack)
    return _sanitize(pack)


def build_daily_pretrade_workflow(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    signal_count = _int(summary.get("signal_count"), 0)
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    target_count = _int(summary.get("combined_target_count"), len(targets))
    manual_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    signal_errors = [row for row in signal_cards if row.get("status") == "signal_error"]
    signal_ready = signal_count > 0 and target_count > 0 and not signal_errors
    scope_ready = market == "CN_ETF"
    readiness_status = "manual_review_required" if scope_ready and signal_ready else "waiting_for_signals"
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else _build_pretrade_readiness(pack)
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else _build_manual_broker_handoff(pack)
    operator_next_actions = (
        pack.get("operator_next_actions")
        if isinstance(pack.get("operator_next_actions"), list)
        else _operator_next_actions(pack, readiness, handoff)
    )
    primary_action = operator_next_actions[0] if operator_next_actions else {}
    steps = [
        {
            "step_number": 1,
            "step_id": "scope_and_data",
            "title": "确认研究对象和数据",
            "status": "ready" if scope_ready else "blocked",
            "plain_action": f"确认今天只看 {market} 主线，数据来自本地清洗行情，不把 CN 个股择股结果直接当 ETF 轮动信号。",
            "evidence": f"市场={market}；入选因子={selected_count}；运行日期={pack.get('run_date', '')}",
            "automation_allowed": False,
        },
        {
            "step_number": 2,
            "step_id": "factor_signal_review",
            "title": "复核前三因子和今日信号",
            "status": "ready" if signal_ready else "blocked",
            "plain_action": "先看前三因子、信号数量、目标 ETF 和过拟合标签；信号不足时不要进入下一步。",
            "evidence": f"信号={signal_count}/{selected_count}；目标ETF={target_count}",
            "automation_allowed": False,
        },
        {
            "step_number": 3,
            "step_id": "paper_simulation_review",
            "title": "查看模拟盘表现",
            "status": "required" if signal_ready else "waiting",
            "plain_action": "把今天的建议和对应参数放进本地模拟盘，先看净值、回撤、成交、保护事件，再决定是否继续。",
            "evidence": "需要模拟盘回放或最近 paper 回执；单日信号不能直接等同可实盘盈利。",
            "automation_allowed": False,
        },
        {
            "step_number": 4,
            "step_id": "risk_and_cash_review",
            "title": "人工核对风险和现金",
            "status": "required" if signal_ready else "waiting",
            "plain_action": "核对目标仓位、单 ETF 上限、总仓位、现金余量、流动性、涨跌停和是否能承受回撤。",
            "evidence": f"手工工单={manual_count}；系统建议仍需人工风险复核。",
            "automation_allowed": False,
        },
        {
            "step_number": 5,
            "step_id": "manual_broker_execution",
            "title": "只允许人工券商端操作",
            "status": "manual_only",
            "plain_action": "系统不会下单；如果你决定实盘，只能由你本人打开券商软件，逐项核对 ETF 代码、价格、金额和风险后手工操作。",
            "evidence": "live_order_allowed=false；broker_connection_allowed=false；order_placement_allowed=false。",
            "automation_allowed": False,
        },
    ]
    workflow = {
        "stage": PRETRADE_WORKFLOW_STAGE,
        "run_date": pack.get("run_date", date.today().isoformat()),
        "summary": {
            "readiness_status": readiness_status,
            "step_count": len(steps),
            "signal_ready": signal_ready,
            "manual_review_required": True,
            "paper_simulation_required": True,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
            "primary_next_action_id": primary_action.get("action_id"),
            "primary_next_action_title": primary_action.get("title"),
            "primary_next_step": "先完成模拟盘和风险复核，再决定是否人工操作。" if signal_ready else "先生成完整今日信号。",
        },
        "steps": steps,
        "pretrade_readiness": readiness,
        "manual_broker_handoff": handoff,
        "operator_next_actions": operator_next_actions,
        "beginner_cards": [
            {
                "card_id": "first_read",
                "title": "第一眼先看什么",
                "text": "先看前三因子是否有信号，再看目标 ETF 数量和是否出现错误。",
            },
            {
                "card_id": "risk_read",
                "title": "第二眼看风险",
                "text": "收益和年化不是唯一标准，还要看回撤、模拟盘、流动性和仓位是否能承受。",
            },
            {
                "card_id": "manual_boundary",
                "title": "最后只做人工决定",
                "text": "软件只给建议和复核清单，不连接券商、不读取账户、不自动下单。",
            },
        ],
    }
    return _sanitize(workflow)


def build_manual_trade_system_protocol(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    workflow = pack.get("pretrade_workflow") if isinstance(pack.get("pretrade_workflow"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    ticket_count = _int(summary.get("manual_ticket_count"), 0)
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    traffic_light = str(readiness.get("traffic_light") or "red")
    manual_review_candidate = bool(readiness.get("manual_action_candidate"))
    risk_profile_id = str(summary.get("risk_profile_id") or "custom_current_parameters")
    return _sanitize(
        {
            "stage": TRADE_SYSTEM_STAGE,
            "primary_market": market,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "daily_selection_rule": {
                "rule_id": "cn_etf_top3_runnable_factor_signals",
                "candidate_limit": 3,
                "source": "factor_leaderboard_runtime_candidates",
                "selection_scope": "CN_ETF only",
                "required_metrics": [
                    "sharpe",
                    "annualized_return",
                    "max_drawdown",
                    "win_rate",
                    "rank_ic",
                    "trade_count",
                ],
                "anti_overfit_notes": [
                    "Do not choose factors by one-day signal or headline total return only.",
                    "Require current signal date, cost-aware paper review, and manual risk/cash review before any human action.",
                ],
            },
            "operator_workflow": {
                "workflow_id": "daily_pretrade_checkup",
                "button_label": "开盘前一键体检",
                "paper_simulation_required": True,
                "manual_review_required": True,
                "evidence_chain": [
                    "daily_ops",
                    "daily_trade_advisory",
                    "pretrade_readiness",
                    "paper_simulation_receipt",
                    "manual_broker_handoff",
                ],
                "current_step_count": workflow.get("summary", {}).get("step_count"),
            },
            "portfolio_policy": {
                "portfolio_value": summary.get("target_value"),
                "combined_target_count": summary.get("combined_target_count"),
                "manual_ticket_count": ticket_count,
                "board_lot_size": BOARD_LOT_SIZE,
                "risk_profile_id": risk_profile_id,
                "risk_profile_label": summary.get("risk_profile_label"),
                "applied_max_gross_exposure": summary.get("applied_max_gross_exposure"),
                "cash_and_position_review_required": True,
                "single_etf_limit_review_required": True,
                "liquidity_and_capacity_review_required": True,
            },
            "execution_boundary": {
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "manual_ticket_export_only": True,
                "safety": SAFETY_NOTICE,
            },
            "go_live_decision": {
                "status": "manual_review_only",
                "traffic_light": traffic_light,
                "manual_review_candidate": manual_review_candidate,
                "blockers": blockers,
                "operator_summary": handoff.get("operator_summary") or readiness.get("operator_verdict"),
                "next_action": (
                    "Run paper simulation and manually review broker tickets."
                    if manual_review_candidate
                    else "Fix red-light blockers before considering any manual broker review."
                ),
            },
        }
    )


def build_daily_rehearsal_daybook(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    run_date = str(pack.get("run_date") or date.today().isoformat())
    signal_fresh = freshness.get("fresh_for_run_date") is True
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    manual_candidate = bool(readiness.get("manual_action_candidate"))
    scope_done = market == "CN_ETF"
    signal_done = scope_done and signal_fresh and selected_count > 0 and signal_count > 0 and target_count > 0
    paper_status = "required" if signal_done else "waiting"
    risk_status = "required" if manual_candidate else ("blocked" if blockers else "waiting")
    manual_status = "manual_only" if tickets else ("blocked" if blockers else "waiting")
    post_close_status = "required" if signal_count > 0 else "waiting"
    phases = [
        {
            "phase_number": 1,
            "phase_id": "scope_and_data",
            "title": "确认主线和数据日期",
            "status": "done" if scope_done and signal_fresh else ("blocked" if not scope_done or blockers else "waiting"),
            "plain_action": f"只看 {market} 主线；确认运行日期和信号日期一致，不能拿 CN 个股择股结果直接当 ETF 轮动依据。",
            "evidence": f"market={market}; run_date={run_date}; latest_signal_date={freshness.get('latest_signal_date') or '无'}",
            "gui_target": "recent-data-refresh-status",
            "automation_allowed": False,
        },
        {
            "phase_number": 2,
            "phase_id": "top3_signal_generation",
            "title": "生成前三因子和今日信号",
            "status": "done" if signal_done else ("blocked" if blockers else "waiting"),
            "plain_action": "从 CN_ETF 可运行候选里取前三因子，生成当天 ETF 权重和目标仓位。",
            "evidence": f"factors={selected_count}; signals={signal_count}; targets={target_count}",
            "gui_target": "daily-trade-factor-table",
            "automation_allowed": False,
        },
        {
            "phase_number": 3,
            "phase_id": "paper_simulation_review",
            "title": "本地模拟盘复核",
            "status": paper_status,
            "plain_action": "先跑本地模拟盘，看收益、最大回撤、成交和保护事件；单日信号不能直接当盈利结论。",
            "evidence": "需要浏览器本地 paper_simulation 回执作为当天人工复核前证据。",
            "gui_target": "paper-metrics",
            "automation_allowed": False,
        },
        {
            "phase_number": 4,
            "phase_id": "risk_cash_review",
            "title": "人工核对风险和现金",
            "status": risk_status,
            "plain_action": "人工核对单 ETF 上限、总仓位、现金余量、流动性和自己能承受的最大回撤。",
            "evidence": f"traffic_light={readiness.get('traffic_light') or 'unknown'}; blockers={', '.join(blockers) or '无'}",
            "gui_target": "daily-pretrade-readiness-verdict",
            "automation_allowed": False,
        },
        {
            "phase_number": 5,
            "phase_id": "manual_broker_review",
            "title": "人工券商端核对",
            "status": manual_status,
            "plain_action": "如果你本人决定继续，只能打开券商软件逐项人工核对 ETF、价格、数量、现金和风险；系统不自动下单。",
            "evidence": f"copyable_tickets={len(tickets)}; handoff_status={handoff.get('status') or 'unknown'}",
            "gui_target": "daily-manual-broker-handoff-ticket-table",
            "automation_allowed": False,
        },
        {
            "phase_number": 6,
            "phase_id": "post_close_journal",
            "title": "收盘后复盘记录",
            "status": post_close_status,
            "plain_action": "收盘后记录当天信号、模拟盘、人工决策、错过/执行原因和次日要复核的风险，不把一次结果当成长期有效。",
            "evidence": "形成日终复盘记录后，下一轮因子审计才有真实演练反馈。",
            "gui_target": "control-operation-ledger",
            "automation_allowed": False,
        },
    ]
    current_phase = next((phase for phase in phases if phase["status"] in {"blocked", "required", "waiting"}), phases[-1])
    done_count = sum(1 for phase in phases if phase["status"] == "done")
    blocked_count = sum(1 for phase in phases if phase["status"] == "blocked")
    return _sanitize(
        {
            "stage": DAILY_REHEARSAL_STAGE,
            "run_date": run_date,
            "safety": SAFETY_NOTICE,
            "summary": {
                "primary_market": market,
                "phase_count": len(phases),
                "done_count": done_count,
                "blocked_count": blocked_count,
                "current_phase_id": current_phase["phase_id"],
                "current_phase_title": current_phase["title"],
                "paper_simulation_required": True,
                "post_close_review_required": True,
                "manual_review_required": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "operator_summary": (
                    "红灯阻断仍在，先补齐数据或信号。"
                    if blocked_count
                    else f"当前来到：{current_phase['title']}。继续按演练清单做，不自动下单。"
                ),
            },
            "phases": phases,
        }
    )


def build_post_close_journal_template(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), 0)
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    run_date = str(pack.get("run_date") or date.today().isoformat())
    signal_fresh = freshness.get("fresh_for_run_date") is True
    items = [
        {
            "item_id": "signal_evidence",
            "title": "今日信号证据",
            "status": "done" if signal_fresh and signal_count > 0 else "needs_review",
            "prompt": "确认今天的前三因子、信号日期、目标 ETF 和阻断项是否一致。",
            "evidence": f"signals={signal_count}; targets={target_count}; latest_signal_date={freshness.get('latest_signal_date') or '无'}",
            "gui_target": "daily-trade-factor-table",
            "automation_allowed": False,
        },
        {
            "item_id": "paper_simulation",
            "title": "模拟盘表现",
            "status": "required",
            "prompt": "记录模拟盘收益、最大回撤、成交笔数和保护事件；没有模拟盘回执就不要写成可实盘结论。",
            "evidence": "读取浏览器本地 paper_simulation 回执。",
            "gui_target": "paper-metrics",
            "automation_allowed": False,
        },
        {
            "item_id": "manual_decision",
            "title": "人工决策",
            "status": "required",
            "prompt": "今天是否人工执行、跳过或减仓？写下原因，尤其是风险、流动性、价格偏差和个人承受度。",
            "evidence": "人工填写，不读取账户，不连接券商。",
            "gui_target": "daily-manual-broker-handoff-ticket-table",
            "automation_allowed": False,
        },
        {
            "item_id": "risk_observation",
            "title": "风险观察",
            "status": "required",
            "prompt": "记录今天暴露出的回撤、集中度、现金、流动性或异常价格问题。",
            "evidence": f"traffic_light={readiness.get('traffic_light') or 'unknown'}; blockers={', '.join(readiness.get('blockers', [])) or '无'}",
            "gui_target": "daily-pretrade-readiness-verdict",
            "automation_allowed": False,
        },
        {
            "item_id": "next_day_follow_up",
            "title": "次日跟进",
            "status": "required",
            "prompt": "写下次日要复核的数据、因子、信号、新风险或参数，不把今天一次表现当成长期有效。",
            "evidence": "作为下一轮因子审计和模拟盘观察输入。",
            "gui_target": "control-operation-ledger",
            "automation_allowed": False,
        },
    ]
    return _sanitize(
        {
            "stage": POST_CLOSE_JOURNAL_STAGE,
            "run_date": run_date,
            "safety": SAFETY_NOTICE,
            "summary": {
                "primary_market": market,
                "question_count": len(items),
                "manual_decision_required": True,
                "paper_receipt_required": True,
                "post_close_review_required": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "operator_summary": "收盘后把信号、模拟盘、人工判断和次日风险写成回执；这是研究反馈，不是下单记录。",
            },
            "items": items,
        }
    )


def build_live_transition_plan(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    tickets = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(tickets))
    risk_profile_id = str(summary.get("risk_profile_id") or "custom_current_parameters")
    signal_ready = signal_count > 0 and target_count > 0 and ticket_count > 0
    manual_candidate = bool(readiness.get("manual_action_candidate"))
    if blockers:
        status = "blocked_before_manual_review"
    elif signal_ready:
        status = "paper_first_manual_pilot_candidate"
    else:
        status = "waiting_for_daily_top3_signal"

    def loop_step(
        index: int,
        step_id: str,
        title: str,
        status_value: str,
        plain_action: str,
        evidence: str,
        gui_target: str,
    ) -> dict[str, Any]:
        return {
            "step_number": index,
            "step_id": step_id,
            "title": title,
            "status": status_value,
            "plain_action": plain_action,
            "evidence": evidence,
            "gui_target": gui_target,
            "automation_allowed": False,
            "live_order_allowed": False,
            "order_placement_allowed": False,
        }

    operating_loop = [
        loop_step(
            1,
            "fresh_data",
            "确认今天数据和信号日期",
            "done" if freshness.get("fresh_for_run_date") else ("blocked" if blockers else "waiting"),
            "先确认运行日期、最新信号日期和 CN_ETF 主线一致；旧信号不能进人工交易复核。",
            f"run_date={freshness.get('run_date') or pack.get('run_date')}; latest_signal_date={freshness.get('latest_signal_date') or '无'}",
            "recent-data-refresh-status",
        ),
        loop_step(
            2,
            "top3_factor_signal",
            "生成前三因子和今日信号",
            "done" if signal_ready else ("blocked" if blockers else "waiting"),
            "每天只从 CN_ETF 可运行候选中取前三因子，再生成当天目标 ETF；不是直接按历史排行榜买。",
            f"factors={selected_count}; signals={signal_count}; targets={target_count}",
            "daily-trade-factor-table",
        ),
        loop_step(
            3,
            "portfolio_sizing",
            "折算目标仓位和一手份额",
            "done" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            f"按目标仓位、参考价和 {BOARD_LOT_SIZE} 份一手向下取整，得到人工核对数量和金额。",
            f"manual_tickets={ticket_count}; rounded_value={readiness.get('summary', {}).get('rounded_value', 0)}",
            "daily-trade-manual-table",
        ),
        loop_step(
            4,
            "paper_simulation",
            "先跑模拟盘复核",
            "required" if signal_ready and not blockers else ("blocked" if blockers else "waiting"),
            "用同一组因子、TopN、成本和仓位参数跑本地模拟盘，先看收益、最大回撤、成交和保护事件。",
            "需要当天信号对应的 paper_simulation 回执；没有回执不能写成实盘结论。",
            "paper-metrics",
        ),
        loop_step(
            5,
            "manual_risk_review",
            "人工复核风险预算",
            "required" if manual_candidate else ("blocked" if blockers else "waiting"),
            "人工选择风险档位，核对最大可承受回撤、单 ETF 上限、总仓位、现金、流动性和价格偏差。",
            f"traffic_light={readiness.get('traffic_light') or 'unknown'}; blockers={', '.join(blockers) or '无'}",
            "daily-pretrade-readiness-verdict",
        ),
        loop_step(
            6,
            "small_capital_review_gate",
            "小资金人工观察闸门",
            "waiting",
            "只有候选通过推广、模拟盘观察、样本充足、市场状态覆盖和小资金风控闸门，才进入小资金人工观察准备。",
            "对应 scripts\\run_small_capital_review_gate.py；输出仍然不是自动订单。",
            "beginner-live-handoff-board",
        ),
        loop_step(
            7,
            "post_close_feedback",
            "收盘后复盘反馈",
            "required" if signal_count > 0 else "waiting",
            "记录今天信号、模拟盘、人工决策、跳过原因、价格偏差和次日风险，把实盘前演练反馈回因子审计。",
            "形成 post_close_journal 回执后再优化明天流程。",
            "control-operation-ledger",
        ),
    ]

    risk_profiles = _risk_profiles(risk_profile_id)
    evidence_gates = [
        {
            "gate_id": "walk_forward_and_oos",
            "label": "长周期和样本外验证",
            "required": True,
            "plain_requirement": "不能只看短样本或单日信号，必须有长周期、滚动和 OOS 证据。",
        },
        {
            "gate_id": "cost_capacity_tradeability",
            "label": "成本、容量和可交易性",
            "required": True,
            "plain_requirement": "要扣交易成本，检查流动性、成交额、一手份额、涨跌停和价格偏差。",
        },
        {
            "gate_id": "paper_observation_and_journal",
            "label": "模拟盘观察和日终复盘",
            "required": True,
            "plain_requirement": "需要足够模拟成交、回撤、保护事件和每日复盘记录。",
        },
        {
            "gate_id": "small_capital_review_gate",
            "label": "小资金人工观察闸门",
            "required": True,
            "plain_requirement": "通过 small_capital_review_gate 后也只生成人工审批包，不自动下单。",
        },
    ]
    return _sanitize(
        {
            "stage": LIVE_TRANSITION_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "status": status,
                "primary_market": market,
                "daily_top_factor_limit": 3,
                "selected_factor_count": selected_count,
                "today_signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "selected_risk_profile_id": risk_profile_id,
                "selected_risk_profile_label": summary.get("risk_profile_label"),
                "requested_max_gross_exposure": summary.get("requested_max_gross_exposure"),
                "applied_max_gross_exposure": summary.get("applied_max_gross_exposure"),
                "paper_simulation_required": True,
                "small_capital_review_required": True,
                "manual_review_required": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "operator_summary": (
                    "今天可以进入模拟盘优先的人工复核候选；仍不是自动实盘。"
                    if status == "paper_first_manual_pilot_candidate"
                    else "先处理红灯阻断或生成完整今日信号，不能进入人工实盘观察。"
                ),
            },
            "daily_top3_signal_rule": {
                "rule_id": "daily_cn_etf_top3_factor_signal_to_manual_review",
                "candidate_limit": 3,
                "selection_scope": "CN_ETF",
                "source": "leaderboard_runtime_candidates_then_signal_snapshot",
                "ranking_inputs": [
                    "Sharpe",
                    "annualized_return",
                    "max_drawdown",
                    "win_rate",
                    "RankIC",
                    "trade_count",
                    "OOS/paper evidence",
                ],
                "plain_warning": "可以每天看前三因子和今日信号，但不能只按今日排行榜直接下单；必须经过模拟盘、风险和小资金人工观察闸门。",
            },
            "execution_rules": {
                "board_lot_size": BOARD_LOT_SIZE,
                "price_source": "本地参考价只用于估算，券商端实时价格必须人工核对。",
                "settlement_note": "股票 ETF 通常按 T+1 处理；部分债券、黄金、跨境和货币 ETF 可能支持 T+0，实操前必须按 ETF 品种和券商规则人工确认。",
                "order_style": "只输出人工核对清单；不生成可提交订单、不连接券商、不读取账户。",
            },
            "risk_profiles": risk_profiles,
            "evidence_gates": evidence_gates,
            "operating_loop": operating_loop,
        }
    )


def build_beginner_action_summary(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    buy_tickets = [row for row in manual_plan if str(row.get("side") or "").lower() in {"buy", "buy_or_adjust", "increase"}]
    sell_tickets = [row for row in manual_plan if str(row.get("side") or "").lower() in {"sell", "decrease"}]
    hold_tickets = [row for row in manual_plan if str(row.get("side") or "").lower() == "hold"]
    ticket_summary = {
        "ticket_count": len(manual_plan),
        "buy_ticket_count": len(buy_tickets),
        "sell_ticket_count": len(sell_tickets),
        "hold_ticket_count": len(hold_tickets),
        "gross_review_value": sum(_float(row.get("rounded_value"), 0.0) for row in manual_plan),
        "copyable_ticket_count": len(handoff.get("copyable_tickets", [])) if isinstance(handoff.get("copyable_tickets"), list) else 0,
    }

    if validation.get("status") in {"error", "not_provided"}:
        decision = "fix_current_positions_first"
        primary_action = "先修正当前持仓输入；不要看买卖票据，也不要在券商端操作。"
        primary_reason = validation.get("plain_summary") or "当前持仓输入未通过盘前检查。"
        steps = [
            _beginner_action_step(
                1,
                "fix_current_positions",
                "修正当前持仓",
                "blocked_until_done",
                primary_reason,
                "daily-current-positions",
            ),
            _beginner_action_step(
                2,
                "rerun_daily_trade_advisory",
                "重新生成今日建议",
                "waiting",
                "修正后重新生成，确认红灯阻断消失。",
                "run-daily-trade-advisory",
            ),
        ]
    elif blockers:
        decision = "resolve_blockers_first"
        primary_action = "先处理红灯阻断项；现在不能进入人工交易复核。"
        primary_reason = "阻断项：" + ", ".join(blockers)
        steps = [
            _beginner_action_step(
                1,
                "inspect_pretrade_blockers",
                "查看盘前红灯",
                "blocked_until_done",
                primary_reason,
                "daily-pretrade-readiness-verdict",
            ),
            _beginner_action_step(
                2,
                "regenerate_or_refresh_data",
                "刷新数据或重新生成信号",
                "waiting",
                "旧信号、缺信号或价格缺失时，先回到数据和信号步骤。",
                "daily-pretrade-next-actions",
            ),
        ]
    elif manual_plan:
        decision = "manual_review_only"
        primary_action = "先跑模拟盘，再人工核对净买卖票据；系统不会下单。"
        primary_reason = f"今日有 {len(manual_plan)} 张人工复核票据；买入 {len(buy_tickets)}，卖出 {len(sell_tickets)}，保持 {len(hold_tickets)}。"
        steps = [
            _beginner_action_step(
                1,
                "run_paper_simulation_first",
                "先跑模拟盘",
                "required_before_manual_review",
                "先看本地模拟盘收益、回撤、成交和保护事件。",
                "paper-metrics",
            ),
            _beginner_action_step(
                2,
                "review_net_rebalance_tickets",
                "核对净买卖票据",
                "manual_review_only",
                primary_reason,
                "daily-trade-manual-table",
            ),
            _beginner_action_step(
                3,
                "post_close_journal",
                "收盘后写回执",
                "required_after_decision",
                "记录今天执行、跳过或减仓的原因，供下一轮审计。",
                "beginner-post-close-journal-board",
            ),
        ]
    else:
        decision = "waiting_for_daily_signal"
        primary_action = "先生成今日前三因子信号；没有票据就不要操作。"
        primary_reason = f"信号={summary.get('signal_count', 0)}，目标={summary.get('combined_target_count', 0)}，票据={summary.get('manual_ticket_count', 0)}。"
        steps = [
            _beginner_action_step(
                1,
                "generate_daily_trade_advisory",
                "生成今日前三建议",
                "waiting",
                primary_reason,
                "run-daily-trade-advisory",
            )
        ]

    return _sanitize(
        {
            "stage": BEGINNER_ACTION_SUMMARY_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "decision": decision,
                "primary_action": primary_action,
                "primary_reason": primary_reason,
                "manual_review_required": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "ticket_summary": ticket_summary,
            "position_validation": validation,
            "steps": steps,
            "safety": SAFETY_NOTICE,
        }
    )


def build_daily_live_readiness_gate(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), 0)
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    positions_ok = validation.get("status") == "ok"
    fresh_for_run_date = bool(freshness.get("fresh_for_run_date"))
    has_today_signal = signal_count > 0 and target_count > 0
    has_manual_tickets = ticket_count > 0 and bool(manual_plan)

    if not positions_ok:
        decision = "blocked_fix_current_positions"
        primary_action = "先修正当前持仓输入；实盘前准备、模拟盘和人工票据都先暂停。"
        primary_reason = validation.get("plain_summary") or "当前持仓输入存在危险字段或格式错误。"
        cta_label = "修正当前持仓"
        cta_target = "daily-current-positions"
        action_workflow = None
    elif blockers:
        decision = "blocked_pretrade_red_light"
        primary_action = "先处理盘前红灯阻断项；不能进入模拟盘交接或人工交易复核。"
        primary_reason = "阻断项：" + ", ".join(blockers)
        cta_label = "查看盘前红灯"
        cta_target = "daily-pretrade-readiness-verdict"
        action_workflow = None
    elif has_manual_tickets:
        decision = "paper_rehearsal_required"
        primary_action = "先跑本地模拟盘并人工复核票据；今天仍然不是自动实盘。"
        primary_reason = f"今日有 {ticket_count} 张人工复核票据，必须先完成模拟盘和风险复核。"
        cta_label = "运行模拟盘复核"
        cta_target = "paper-metrics"
        action_workflow = "paper_simulation"
    elif has_today_signal:
        decision = "waiting_for_trade_ticket"
        primary_action = "已有今日信号但没有可复核票据；先检查价格、仓位和一手取整。"
        primary_reason = f"信号={signal_count}，目标={target_count}，票据={ticket_count}。"
        cta_label = "检查仓位和票据"
        cta_target = "daily-trade-target-table"
        action_workflow = "daily_trade_advisory"
    else:
        decision = "waiting_for_daily_signal"
        primary_action = "先生成今日前三 CN_ETF 因子信号；没有当天信号就不要操作。"
        primary_reason = f"信号={signal_count}，目标={target_count}，票据={ticket_count}。"
        cta_label = "生成今日建议"
        cta_target = "run-daily-trade-advisory"
        action_workflow = "daily_trade_advisory"

    def gate_row(gate_id: str, label: str, status: str, plain_check: str, evidence: str, gui_target: str) -> dict[str, Any]:
        return {
            "gate_id": gate_id,
            "label": label,
            "status": status,
            "plain_check": plain_check,
            "evidence": evidence,
            "gui_target": gui_target,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
        }

    blocked_by_position = not positions_ok
    blocked_by_pretrade = bool(blockers)
    gate_rows = [
        gate_row(
            "current_positions",
            "当前持仓输入",
            "blocked" if blocked_by_position else "ready",
            "只允许资产、数量、参考价等纸面字段；不能输入账户、券商、真实委托字段。",
            validation.get("plain_summary") or f"accepted={validation.get('accepted_count', 0)}; issues={validation.get('issue_count', 0)}",
            "daily-current-positions",
        ),
        gate_row(
            "signal_freshness",
            "信号日期",
            "ready" if fresh_for_run_date else ("blocked" if "stale_signal_date" in blockers else "waiting"),
            "当天信号必须和运行日期一致；旧信号不能当作今日操作依据。",
            f"run_date={freshness.get('run_date') or pack.get('run_date')}; latest_signal_date={freshness.get('latest_signal_date') or '无'}",
            "daily-pretrade-readiness-verdict",
        ),
        gate_row(
            "today_signal",
            "前三因子今日信号",
            "ready" if has_today_signal and not blocked_by_pretrade else ("blocked" if blocked_by_pretrade else "waiting"),
            "只从 CN_ETF 可运行候选中取前三信号，不把 CN 个股或历史榜单直接当 ETF 交易信号。",
            f"market={market}; signals={signal_count}; targets={target_count}",
            "daily-trade-factor-table",
        ),
        gate_row(
            "paper_rehearsal",
            "模拟盘复核",
            "required" if has_manual_tickets and not blocked_by_pretrade else ("blocked" if blocked_by_pretrade else "waiting"),
            "有票据也必须先跑本地模拟盘，看收益、回撤、胜率、成交和保护事件。",
            f"manual_tickets={ticket_count}; paper_simulation_required=True",
            "paper-metrics",
        ),
        gate_row(
            "manual_review",
            "人工复核票据",
            "waiting_for_paper" if has_manual_tickets and not blocked_by_pretrade else ("blocked" if blocked_by_pretrade else "waiting"),
            "票据只能作为人工核对清单；券商端是否操作必须由人单独决定。",
            f"manual_review_required=True; rounded_value={readiness.get('summary', {}).get('rounded_value', 0)}",
            "daily-trade-manual-table",
        ),
        gate_row(
            "live_boundary",
            "实盘交易边界",
            "locked",
            "当前软件不连接券商、不读取账户、不生成真实委托、不自动下单。",
            SAFETY_NOTICE,
            "control-safety-boundary",
        ),
    ]

    def ladder(mode_id: str, label: str, status: str, plain_state: str, gui_target: str) -> dict[str, Any]:
        return {
            "mode_id": mode_id,
            "label": label,
            "status": status,
            "plain_state": plain_state,
            "gui_target": gui_target,
            "live_order_allowed": False,
            "order_placement_allowed": False,
        }

    blocked = blocked_by_position or blocked_by_pretrade
    mode_ladder = [
        ladder(
            "research_signal",
            "研究信号",
            "ready" if has_today_signal and not blocked else ("blocked" if blocked else "waiting"),
            "生成并复核今日前三 CN_ETF 信号。",
            "daily-trade-factor-table",
        ),
        ladder(
            "paper_simulation",
            "模拟盘",
            "required" if has_manual_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "先用相同参数做本地模拟盘回放。",
            "paper-metrics",
        ),
        ladder(
            "manual_review",
            "人工复核",
            "locked_until_paper_rehearsal" if has_manual_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "模拟盘和风险检查后，人工核对票据。",
            "daily-trade-manual-table",
        ),
        ladder(
            "small_capital_observation",
            "小资金人工观察",
            "locked_until_gate",
            "需要推广闸门、模拟盘观察、盘后复盘和小资金风控全部通过。",
            "beginner-live-handoff-board",
        ),
        ladder(
            "live_trading",
            "实盘交易",
            "locked",
            "本项目当前不提供自动实盘交易；只能输出研究和人工复核材料。",
            "control-safety-boundary",
        ),
    ]

    forbidden_shortcuts = [
        {
            "shortcut_id": "daily_top3_direct_buy",
            "plain_warning": "不要把今日前三因子直接等同于买入指令。",
        },
        {
            "shortcut_id": "stale_signal_reuse",
            "plain_warning": "不要用旧日期信号补今天的交易判断。",
        },
        {
            "shortcut_id": "cn_stock_to_etf_direct_transfer",
            "plain_warning": "不要把 CN 个股资金流择股结果直接当 CN_ETF 轮动信号。",
        },
        {
            "shortcut_id": "skip_paper_and_journal",
            "plain_warning": "不要跳过模拟盘和盘后复盘直接进入小资金观察。",
        },
    ]

    return _sanitize(
        {
            "stage": LIVE_READINESS_GATE_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "decision": decision,
                "primary_action": primary_action,
                "primary_reason": primary_reason,
                "cta_label": cta_label,
                "cta_target": cta_target,
                "action_workflow": action_workflow,
                "primary_market": market,
                "paper_simulation_required": True,
                "manual_review_required": True,
                "small_capital_review_required": True,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "gate_rows": gate_rows,
            "mode_ladder": mode_ladder,
            "forbidden_shortcuts": forbidden_shortcuts,
            "safety": SAFETY_NOTICE,
        }
    )


def build_beginner_trade_action_card(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    live_gate = pack.get("daily_live_readiness_gate") if isinstance(pack.get("daily_live_readiness_gate"), dict) else {}
    gate_summary = live_gate.get("summary") if isinstance(live_gate.get("summary"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    decision = str(gate_summary.get("decision") or "waiting_for_daily_signal")
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), 0)
    ticket_count = _int(summary.get("manual_ticket_count"), 0)
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    position_status = str(validation.get("status") or "not_provided")

    if decision == "blocked_fix_current_positions":
        answer_code = "no"
        recommended_mode = "fix_inputs_first"
        can_manual_review_today = False
        plain_answer = "不能操作。当前持仓输入里有账户、券商或订单等危险字段，先修正输入。"
        why = validation.get("plain_summary") or "当前持仓输入没有通过安全检查。"
        next_action = {
            "action_id": "fix_current_positions",
            "workflow_id": None,
            "target_id": "daily-current-positions",
            "button_label": "修正当前持仓",
            "plain_action": "删除账户、券商、订单等真实交易字段，只保留资产、数量和参考价。",
        }
    elif decision == "blocked_pretrade_red_light" or blockers:
        answer_code = "no"
        recommended_mode = "resolve_red_light_first"
        can_manual_review_today = False
        plain_answer = "不能操作。盘前闸门是红灯，先处理阻断项。"
        why = gate_summary.get("primary_reason") or ("阻断项：" + ", ".join(blockers))
        next_action = {
            "action_id": "resolve_pretrade_blockers",
            "workflow_id": gate_summary.get("action_workflow"),
            "target_id": gate_summary.get("cta_target") or "daily-pretrade-readiness-verdict",
            "button_label": gate_summary.get("cta_label") or "查看盘前红灯",
            "plain_action": gate_summary.get("primary_action") or "先看盘前总判定和阻断原因。",
        }
    elif decision == "paper_rehearsal_required":
        answer_code = "not_yet"
        recommended_mode = "paper_first_manual_review"
        can_manual_review_today = ticket_count > 0
        plain_answer = "还不能直接买。先用同一组参数跑模拟盘，再人工复核票据。"
        why = gate_summary.get("primary_reason") or f"已有 {ticket_count} 张人工复核票据，但模拟盘复核仍是必需步骤。"
        next_action = {
            "action_id": "run_paper_simulation",
            "workflow_id": gate_summary.get("action_workflow") or "paper_simulation",
            "target_id": gate_summary.get("cta_target") or "paper-metrics",
            "button_label": gate_summary.get("cta_label") or "运行模拟盘复核",
            "plain_action": gate_summary.get("primary_action") or "先跑本地模拟盘，查看收益、回撤、胜率和成交。",
        }
    elif decision == "waiting_for_trade_ticket":
        answer_code = "not_yet"
        recommended_mode = "build_manual_ticket_first"
        can_manual_review_today = False
        plain_answer = "还不能操作。已有信号但没有可核对的人工票据。"
        why = gate_summary.get("primary_reason") or f"信号={signal_count}，目标={target_count}，票据={ticket_count}。"
        next_action = {
            "action_id": "build_manual_tickets",
            "workflow_id": gate_summary.get("action_workflow") or "daily_trade_advisory",
            "target_id": gate_summary.get("cta_target") or "daily-trade-target-table",
            "button_label": gate_summary.get("cta_label") or "检查仓位和票据",
            "plain_action": gate_summary.get("primary_action") or "先补齐价格、仓位和一手取整后的人工复核票据。",
        }
    else:
        answer_code = "not_yet"
        recommended_mode = "generate_signal_first"
        can_manual_review_today = False
        plain_answer = "还没有今日可用信号。先生成今日前三 CN_ETF 因子建议。"
        why = gate_summary.get("primary_reason") or f"信号={signal_count}，目标={target_count}，票据={ticket_count}。"
        next_action = {
            "action_id": "generate_daily_trade_advisory",
            "workflow_id": gate_summary.get("action_workflow") or "daily_trade_advisory",
            "target_id": gate_summary.get("cta_target") or "run-daily-trade-advisory",
            "button_label": gate_summary.get("cta_label") or "生成今日建议",
            "plain_action": gate_summary.get("primary_action") or "先生成今日前三 CN_ETF 因子信号。",
        }

    def checklist_row(check_id: str, label: str, status: str, plain_check: str, target_id: str) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "label": label,
            "status": status,
            "plain_check": plain_check,
            "target_id": target_id,
            "automation_allowed": False,
            "live_order_allowed": False,
            "order_placement_allowed": False,
        }

    plain_checklist = [
        checklist_row(
            "cn_etf_scope",
            "主线市场",
            "pass" if market == "CN_ETF" else "blocked",
            f"今天只允许把 CN_ETF 信号当主线；当前 market={market}。",
            "active-market-label",
        ),
        checklist_row(
            "current_positions",
            "当前持仓输入",
            "pass" if position_status == "ok" else "blocked",
            f"状态={position_status}；不能输入账户、券商、订单等真实交易字段。",
            "daily-current-positions",
        ),
        checklist_row(
            "today_signal",
            "今日信号",
            "pass" if signal_count > 0 and target_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            f"前置因子={selected_count}；信号={signal_count}；目标 ETF={target_count}。",
            "daily-trade-factor-table",
        ),
        checklist_row(
            "paper_simulation",
            "模拟盘复核",
            "required" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            "有票据也必须先跑模拟盘，看收益、回撤、胜率、成交和保护事件。",
            "paper-metrics",
        ),
        checklist_row(
            "manual_ticket",
            "人工票据",
            "ready" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            f"当前可核对票据={ticket_count}；票据只供人工复核，不是下单指令。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        checklist_row(
            "live_boundary",
            "实盘边界",
            "locked",
            "软件不连接券商、不读取账户、不自动下单；真正交易只能由人另行决定。",
            "control-safety-boundary",
        ),
    ]

    return _sanitize(
        {
            "stage": BEGINNER_TRADE_ACTION_CARD_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "decision": decision,
                "answer_code": answer_code,
                "plain_answer": plain_answer,
                "why": why,
                "recommended_mode": recommended_mode,
                "can_manual_review_today": can_manual_review_today,
                "manual_review_required": True,
                "paper_simulation_required": True,
                "auto_order_allowed": False,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "next_action": next_action,
            "evidence": {
                "primary_market": market,
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "traffic_light": readiness.get("traffic_light") or "unknown",
                "blockers": blockers,
                "freshness": freshness,
                "current_position_status": position_status,
                "current_position_issue_count": validation.get("issue_count", 0),
                "handoff_status": handoff.get("status"),
            },
            "plain_checklist": plain_checklist,
            "safety": SAFETY_NOTICE,
        }
    )


def build_small_capital_observation_gate(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    risk_profile_id = str(summary.get("risk_profile_id") or "custom_current_parameters")
    selected_profile = _risk_profile_by_id(risk_profile_id) or {}
    max_drawdown = _float(
        selected_profile.get("max_acceptable_drawdown"),
        0.30 if risk_profile_id == "aggressive_30dd" else 0.20,
    )
    has_daily_material = selected_count > 0 and signal_count > 0 and ticket_count > 0
    if blockers:
        decision = "blocked_by_pretrade_red_light"
        plain_answer = "小资金观察不能打开：盘前红灯阻断还没有处理。"
        primary_action = "先处理红灯阻断，再重新生成今日建议。"
    elif not has_daily_material:
        decision = "waiting_for_daily_material"
        plain_answer = "小资金观察不能打开：还缺今日前三信号或人工票据。"
        primary_action = "先生成今日前三 CN_ETF 因子信号和人工复核票据。"
        next_workflow_id = "daily_trade_advisory"
        next_gui_target = "daily-trade-factor-table"
        next_button_label = "生成今日建议"
    else:
        decision = "evidence_required"
        plain_answer = "小资金观察还不能打开：必须先积累模拟盘、盘后复盘和风险证据。"
        primary_action = "先连续完成模拟盘、盘后复盘、回撤和保护事件检查。"
        next_workflow_id = "paper_simulation"
        next_gui_target = "paper-metrics"
        next_button_label = "先跑模拟盘"
    if blockers:
        next_workflow_id = ""
        next_gui_target = "daily-pretrade-readiness-verdict"
        next_button_label = "查看红灯"

    def row(
        gate_id: str,
        label: str,
        requirement_type: str,
        required_value: float | int | bool,
        comparator: str,
        plain_requirement: str,
        gui_target: str,
        workflow_id: str = "",
        status: str = "evidence_required",
    ) -> dict[str, Any]:
        return {
            "gate_id": gate_id,
            "label": label,
            "status": status,
            "requirement_type": requirement_type,
            "required_value": required_value,
            "comparator": comparator,
            "plain_requirement": plain_requirement,
            "gui_target": gui_target,
            "workflow_id": workflow_id,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        }

    gate_rows = [
        row(
            "paper_simulation_receipts",
            "模拟盘观察次数",
            "local_execution_receipt_count",
            5,
            ">=",
            "至少 5 次模拟盘回执，避免把单日表现当成规律。",
            "paper-metrics",
            "paper_simulation",
        ),
        row(
            "post_close_journal_receipts",
            "盘后复盘次数",
            "local_execution_receipt_count",
            5,
            ">=",
            "至少 5 次盘后复盘回执，记录执行、跳过、偏差和次日要验证的风险。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        row(
            "latest_paper_drawdown",
            "最大回撤预算",
            "latest_paper_metric",
            max_drawdown,
            "<=",
            "最新模拟盘最大回撤必须低于当前风险档位；收益高也不能绕过回撤预算。",
            "paper-metrics",
        ),
        row(
            "latest_paper_guard_events",
            "保护事件",
            "latest_paper_metric",
            0,
            "=",
            "最新模拟盘不能触发风控保护事件；触发过就先复盘原因。",
            "paper-metrics",
        ),
        row(
            "latest_paper_fills",
            "成交样本",
            "latest_paper_metric",
            1,
            ">=",
            "最新模拟盘至少产生一次成交；空跑不能作为小资金观察证据。",
            "paper-metrics",
        ),
        row(
            "manual_ticket_and_red_light",
            "人工票据和红灯",
            "daily_pretrade_gate",
            1,
            ">=",
            "今日必须有人工票据，且盘前红灯阻断为 0。",
            "daily-manual-broker-handoff-ticket-table",
            status="ready" if ticket_count > 0 and not blockers else "blocked" if blockers else "waiting",
        ),
        row(
            "research_only_safety_boundary",
            "权限边界",
            "safety_boundary",
            False,
            "=",
            "系统必须保持无券商、无账户、无下单权限；真实买卖只能人工决定。",
            "control-safety-boundary",
            status="locked",
        ),
    ]
    return _sanitize(
        {
            "stage": SMALL_CAPITAL_OBSERVATION_GATE_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "primary_action": primary_action,
                "minimum_paper_simulation_receipts": 5,
                "minimum_post_close_journal_receipts": 5,
                "max_acceptable_drawdown": max_drawdown,
                "requires_zero_guard_events": True,
                "requires_filled_paper_trade": True,
                "manual_ticket_count": ticket_count,
                "handoff_status": handoff.get("status"),
                "traffic_light": readiness.get("traffic_light") or "unknown",
                "blockers": blockers,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "decision_card": {
                "title": "今天能不能小资金观察",
                "answer_code": "not_ready",
                "plain_answer": f"还不能小资金观察：{primary_action}",
                "next_step_label": next_button_label,
                "next_workflow_id": next_workflow_id,
                "next_gui_target": next_gui_target,
                "manual_only_boundary": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "gate_rows": gate_rows,
            "safety": SAFETY_NOTICE,
        }
    )


def build_daily_live_pilot_brief(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    live_gate = pack.get("daily_live_readiness_gate") if isinstance(pack.get("daily_live_readiness_gate"), dict) else {}
    small_capital_gate = (
        pack.get("small_capital_observation_gate")
        if isinstance(pack.get("small_capital_observation_gate"), dict)
        else build_small_capital_observation_gate(pack)
    )
    gate_summary = live_gate.get("summary") if isinstance(live_gate.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    target_count = _int(summary.get("combined_target_count"), 0)
    if blockers:
        status = "blocked_before_manual_review"
        plain_answer = "今天不能照着操作：盘前闸门仍有红灯阻断。"
        primary_action = gate_summary.get("primary_action") or "先处理红灯阻断项。"
    elif ticket_count > 0 and signal_count > 0:
        status = "manual_review_candidate"
        plain_answer = "今天可以进入人工复核，但不能把它当成自动买入指令。"
        primary_action = "先跑模拟盘复核，再看人工票据。"
    elif signal_count > 0:
        status = "waiting_for_manual_ticket"
        plain_answer = "已有今日信号，但还没有完整人工票据。"
        primary_action = "补齐价格、仓位和一手取整后的人工票据。"
    else:
        status = "waiting_for_daily_signal"
        plain_answer = "还没有今日前三因子信号。"
        primary_action = "先生成今日前三 CN_ETF 因子建议。"

    def step(
        step_number: int,
        step_id: str,
        title: str,
        status_value: str,
        plain_action: str,
        gui_target: str,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        return {
            "step_number": step_number,
            "step_id": step_id,
            "title": title,
            "status": status_value,
            "plain_action": plain_action,
            "gui_target": gui_target,
            "workflow_id": workflow_id,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
        }

    manual_operation_steps = [
        step(
            1,
            "run_pretrade_checkup",
            "开盘前一键体检",
            "required",
            "先把 daily_ops、今日前三建议、盘前红黄灯和人工票据合成一张本地回执。",
            "beginner-trade-system-board",
            "daily_pretrade_checkup",
        ),
        step(
            2,
            "review_top3_signal",
            "查看前三因子和今日信号",
            "done" if signal_count > 0 else "waiting",
            "只确认候选、信号日期、目标 ETF 和权重；不能把前三因子直接当买入指令。",
            "daily-trade-factor-table",
            "daily_trade_advisory" if signal_count <= 0 else "",
        ),
        step(
            3,
            "run_paper_simulation",
            "运行本地模拟盘复核",
            "required" if signal_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            "用同一组信号先看收益、最大回撤、胜率、成交和保护事件。",
            "paper-metrics",
            "paper_simulation" if signal_count > 0 and not blockers else "",
        ),
        step(
            4,
            "review_manual_ticket",
            "核对人工票据",
            "manual_only" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            "核对 ETF 代码、方向、参考价、目标权重、取整份额、金额、现金余量和来源因子。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        step(
            5,
            "human_broker_decision",
            "券商端由人手工决定",
            "manual_only" if ticket_count > 0 and not blockers else "locked",
            "软件不会连接券商或提交订单；是否在券商端操作必须由本人另行判断。",
            "control-safety-boundary",
        ),
        step(
            6,
            "post_close_journal",
            "收盘后写复盘回执",
            "required" if signal_count > 0 else "waiting",
            "记录今天信号、模拟盘、人工决定、跳过原因和次日要复核的风险。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]

    def ticket_preview(index: int, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "step_number": index,
            "ticket_id": row.get("ticket_id") or f"daily-top3-{index:03d}",
            "asset_id": row.get("asset_id"),
            "market": row.get("market") or "CN_ETF",
            "side": row.get("side") or "buy_or_adjust",
            "target_weight": row.get("target_weight"),
            "latest_price": row.get("latest_price"),
            "rounded_quantity": row.get("rounded_quantity"),
            "rounded_value": row.get("rounded_value"),
            "source_factors": row.get("source_factors"),
            "plain_instruction": "仅供人工核对，不是订单；券商端价格、现金和风险需本人再确认。",
            "executable": False,
            "automation_allowed": False,
            "live_order_allowed": False,
            "order_placement_allowed": False,
        }

    risk_profile_id = str(summary.get("risk_profile_id") or "custom_current_parameters")
    selected_profile = _risk_profile_by_id(risk_profile_id) or {}
    return _sanitize(
        {
            "stage": DAILY_LIVE_PILOT_BRIEF_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "status": status,
                "plain_answer": plain_answer,
                "primary_action": primary_action,
                "primary_market": market,
                "daily_top_factor_limit": 3,
                "selected_factor_count": selected_count,
                "today_signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "traffic_light": readiness.get("traffic_light") or "unknown",
                "blocker_count": len(blockers),
                "paper_simulation_required": True,
                "manual_review_required": True,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "today_signal_rule": {
                "rule_id": "daily_top3_candidates_not_direct_orders",
                "selection_scope": "CN_ETF",
                "candidate_limit": 3,
                "source": "daily_trade_advisory factors + same-day signal snapshots",
                "plain_warning": "不能把前三因子直接当买入指令；必须经过日期、模拟盘、成本、风险和人工票据复核。",
            },
            "manual_operation_steps": manual_operation_steps,
            "manual_ticket_preview": [ticket_preview(index, row) for index, row in enumerate(manual_plan, start=1)],
            "risk_budget": {
                "risk_profile_id": risk_profile_id,
                "risk_profile_label": summary.get("risk_profile_label") or selected_profile.get("label"),
                "applied_max_gross_exposure": summary.get("applied_max_gross_exposure"),
                "max_single_etf_weight": selected_profile.get("max_single_etf_weight"),
                "max_acceptable_drawdown": selected_profile.get("max_acceptable_drawdown"),
                "daily_loss_stop": selected_profile.get("daily_loss_stop"),
                "board_lot_size": BOARD_LOT_SIZE,
                "plain_review": "收益和年化高也不能跳过回撤、单 ETF 上限、现金、流动性和价格偏差核对。",
            },
            "execution_boundary": {
                "plain_boundary": "券商端由人手工决定；软件只生成研究、模拟盘和人工复核材料。",
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "manual_ticket_export_only": True,
            },
            "small_capital_observation_gate": small_capital_gate,
            "blockers": blockers,
            "safety": SAFETY_NOTICE,
        }
    )


def _beginner_action_step(
    step_number: int,
    step_id: str,
    title: str,
    status: str,
    plain_action: str,
    gui_target: str,
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "title": title,
        "status": status,
        "plain_action": plain_action,
        "gui_target": gui_target,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "order_placement_allowed": False,
    }


def _manual_cash_feasibility(manual_plan: list[dict[str, Any]], manual_available_cash: Any) -> dict[str, Any]:
    estimated_buy_cash_required = round(
        sum(_float(row.get("estimated_buy_cash_required"), 0.0) for row in manual_plan),
        6,
    )
    estimated_sell_cash_released = round(
        sum(_float(row.get("estimated_sell_cash_released"), 0.0) for row in manual_plan),
        6,
    )
    estimated_cash_impact_after_costs = round(
        sum(_float(row.get("estimated_cash_impact_after_costs"), 0.0) for row in manual_plan),
        6,
    )
    manual_cash_value = _float_or_none(manual_available_cash)
    if not manual_plan or estimated_buy_cash_required <= 0:
        status = "not_required"
        shortfall = 0.0
    elif manual_cash_value is None:
        status = "not_provided"
        shortfall = None
    else:
        shortfall = round(max(0.0, estimated_buy_cash_required - manual_cash_value), 6)
        status = "blocked" if shortfall > 1e-9 else "pass"
    return _sanitize(
        {
            "status": status,
            "cash_source": "manual_input_only" if manual_cash_value is not None else "not_provided",
            "manual_available_cash": manual_cash_value,
            "estimated_buy_cash_required": estimated_buy_cash_required,
            "estimated_sell_cash_released": estimated_sell_cash_released,
            "estimated_cash_impact_after_costs": estimated_cash_impact_after_costs,
            "estimated_cash_shortfall": shortfall,
            "conservative_rule": "available_cash_must_cover_buy_cash_before_same_day_sell_credit",
            "same_day_sell_credit_treated_as_manual_review_only": estimated_sell_cash_released > 0,
            "manual_input_required_before_broker_review": status in {"not_provided", "blocked"},
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
    )


def _build_pretrade_readiness(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    position_validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    position_issues = [row for row in position_validation.get("issues", []) if isinstance(row, dict)]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    manual_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    signal_errors = [row for row in signal_cards if row.get("status") == "signal_error"]
    freshness = _pretrade_signal_freshness(pack, signal_cards)
    candidate_trade_evidence = _candidate_trade_evidence_audit(factors)
    candidate_evidence_status = str(candidate_trade_evidence.get("status") or "waiting")
    cash_feasibility = _manual_cash_feasibility(manual_plan, summary.get("manual_available_cash"))
    invalid_sizing_tickets = [
        str(row.get("ticket_id") or row.get("asset_id") or "")
        for row in manual_plan
        if _float_or_none(row.get("latest_price")) is None or row.get("rounded_quantity") is None
    ]
    zero_lot_tickets = [
        str(row.get("ticket_id") or row.get("asset_id") or "")
        for row in manual_plan
        if _float(row.get("target_value"), 0.0) > 0 and _float(row.get("rounded_quantity"), 0.0) <= 0
    ]

    blockers: list[str] = []
    if market != "CN_ETF":
        blockers.append("non_cn_etf_scope")
    if bool(summary.get("fallback_signal_only")):
        blockers.append("fallback_baseline_not_tradeable")
    manual_blocked_reason = str(summary.get("manual_trade_plan_blocked_reason") or "")
    if signal_count <= 0 or target_count <= 0:
        blockers.append("signal_not_ready")
    elif manual_count <= 0 and not summary.get("fallback_signal_only") and not manual_blocked_reason:
        blockers.append("signal_not_ready")
    if manual_blocked_reason == "current_positions_not_provided":
        blockers.append("current_position_not_provided")
    if signal_errors:
        blockers.append("signal_errors")
    if selected_count > 0 and candidate_evidence_status == "blocked":
        blockers.append("candidate_trade_evidence_incomplete")
    if invalid_sizing_tickets:
        blockers.append("price_or_sizing_missing")
    if position_validation.get("status") == "error":
        blockers.append("current_position_input_invalid")
    if signal_count > 0 and not freshness["fresh_for_run_date"]:
        blockers.append("stale_signal_date")
    if manual_count > 0 and cash_feasibility.get("status") == "not_provided":
        blockers.append("manual_cash_not_provided")
    if cash_feasibility.get("status") == "blocked":
        blockers.append("manual_cash_shortfall")

    manual_action_candidate = not blockers and manual_count > 0
    traffic_light = "yellow" if manual_action_candidate else "red"
    operator_verdict = (
        "可进入人工复核：先核对模拟盘、价格、现金和风险，再由本人决定是否在券商端手工操作；系统不会下单。"
        if manual_action_candidate
        else "不可进入人工操作：今日信号、价格或研究范围仍有阻断项，先处理红灯问题。"
    )

    required_confirmations = [
        {
            "check_id": "cn_etf_scope",
            "status": "pass" if market == "CN_ETF" else "blocked",
            "text": f"研究主线必须是 CN_ETF；当前 market={market}。",
        },
        {
            "check_id": "signal_ready",
            "status": "pass" if signal_count > 0 and target_count > 0 and not signal_errors else "blocked",
            "text": f"今日信号={signal_count}/{selected_count}，目标ETF={target_count}。",
        },
        {
            "check_id": "candidate_trade_evidence",
            "status": (
                "pass"
                if candidate_evidence_status == "pass"
                else "waiting"
                if candidate_evidence_status == "waiting"
                else "blocked"
            ),
            "text": (
                f"top3 evidence status={candidate_evidence_status}; "
                f"blocked={candidate_trade_evidence.get('blocked_count', 0)}; "
                f"required={','.join(DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS)}; "
                f"min_trade_count={DAILY_CANDIDATE_MIN_TRADE_COUNT}."
            ),
        },
        {
            "check_id": "signal_freshness",
            "status": "pass" if freshness["fresh_for_run_date"] else ("waiting" if not freshness["latest_signal_date"] else "blocked"),
            "text": f"运行日期={freshness['run_date']}；最新信号日期={freshness['latest_signal_date'] or '无'}。",
        },
        {
            "check_id": "price_and_board_lot",
            "status": "pass" if manual_count > 0 and not invalid_sizing_tickets else ("waiting" if manual_count == 0 else "blocked"),
            "text": f"手工票据={manual_count}；按 {BOARD_LOT_SIZE} 份一手向下取整。",
        },
        {
            "check_id": "current_position_input",
            "status": "pass" if position_validation.get("status") == "ok" else "blocked",
            "text": (
                f"当前持仓输入状态={position_validation.get('status') or 'not_provided'}；"
                f"已接收={position_validation.get('accepted_count', 0)}；问题={position_validation.get('issue_count', 0)}。"
            ),
        },
        {
            "check_id": "manual_available_cash",
            "status": (
                "pass"
                if cash_feasibility.get("status") in {"pass", "not_required"}
                else "blocked"
                if cash_feasibility.get("status") == "blocked"
                or (manual_count > 0 and cash_feasibility.get("status") == "not_provided")
                else "waiting"
            ),
            "text": (
                f"手填券商可用现金={cash_feasibility.get('manual_available_cash') if cash_feasibility.get('manual_available_cash') is not None else '未填写'}；"
                f"预计买入所需现金={cash_feasibility.get('estimated_buy_cash_required')}；"
                f"缺口={cash_feasibility.get('estimated_cash_shortfall') if cash_feasibility.get('estimated_cash_shortfall') is not None else '待人工确认'}。"
            ),
        },
        {
            "check_id": "paper_and_risk_review",
            "status": "required" if manual_action_candidate else "waiting",
            "text": "必须先看模拟盘、最大回撤、流动性、仓位上限和现金余量。",
        },
        {
            "check_id": "manual_only_boundary",
            "status": "required",
            "text": "系统不连接券商、不读取账户、不生成实盘委托、不自动下单。",
        },
    ]

    action_sequence = [
        {
            "step_number": index,
            "ticket_id": row.get("ticket_id"),
            "asset_id": row.get("asset_id"),
            "side": row.get("side"),
            "current_quantity": row.get("current_quantity"),
            "current_value": row.get("current_value"),
            "target_value": row.get("target_value"),
            "delta_value": row.get("delta_value"),
            "latest_price": row.get("latest_price"),
            "rounded_quantity": row.get("rounded_quantity"),
            "rounded_quantity_delta": row.get("rounded_quantity_delta"),
            "rounded_value": row.get("rounded_value"),
            "cash_delta_after_rounding": row.get("cash_delta_after_rounding"),
            "source_factors": row.get("source_factors"),
            "live_order_allowed": False,
            "manual_instruction": row.get("manual_instruction"),
        }
        for index, row in enumerate(manual_plan, start=1)
    ]

    warnings = ["即使黄灯，也只代表可以进入人工复核，不代表策略已被证明能稳定盈利。"]
    if zero_lot_tickets:
        warnings.append(f"以下票据按一手取整后为 0，不能直接买入：{', '.join(zero_lot_tickets)}。")
    if signal_errors:
        warnings.append("有入选因子没有生成同日信号，不能当作可操作建议。")
    if candidate_evidence_status == "blocked":
        warnings.append("Top3 candidate trade evidence is incomplete: required metrics must be present and trade_count must be at least 30 before manual action review.")
    if cash_feasibility.get("status") == "blocked":
        warnings.append("手填券商可用现金不足以覆盖今日买入票据，不能进入人工买入复核。")
    elif cash_feasibility.get("status") == "not_provided" and manual_count > 0:
        warnings.append("尚未手填券商可用现金；不能进入人工券商复核，先补现金检查。")
    if summary.get("fallback_signal_only"):
        warnings.append("当前只有内置基线演示信号，没有合格推广候选；只能观察和跑模拟盘，不能生成手工交易票据。")
    if position_validation.get("status") == "not_provided" and target_count > 0:
        warnings.append("未填写当前持仓；只能查看目标仓位，不能生成可复制人工票据。")
    if position_issues:
        warnings.append("当前持仓输入有问题：" + "；".join(str(item.get("message") or item.get("issue_id")) for item in position_issues[:3]))

    return _sanitize(
        {
            "stage": PRETRADE_READINESS_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "traffic_light": traffic_light,
            "operator_verdict": operator_verdict,
            "manual_action_candidate": manual_action_candidate,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
            "blockers": blockers,
            "warnings": warnings,
            "freshness": freshness,
            "candidate_trade_evidence": candidate_trade_evidence,
            "cash_feasibility": cash_feasibility,
            "summary": {
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": manual_count,
                "candidate_trade_evidence_status": candidate_evidence_status,
                "candidate_trade_evidence_blocked_count": candidate_trade_evidence.get("blocked_count", 0),
                "candidate_trade_evidence_min_trade_count": DAILY_CANDIDATE_MIN_TRADE_COUNT,
                "manual_trade_plan_blocked": bool(summary.get("manual_trade_plan_blocked")),
                "manual_trade_plan_blocked_reason": summary.get("manual_trade_plan_blocked_reason"),
                "current_position_count": position_validation.get("accepted_count", 0),
                "current_position_issue_count": position_validation.get("issue_count", 0),
                "manual_available_cash": cash_feasibility.get("manual_available_cash"),
                "manual_available_cash_source": cash_feasibility.get("cash_source"),
                "manual_cash_feasibility_status": cash_feasibility.get("status"),
                "manual_cash_shortfall": cash_feasibility.get("estimated_cash_shortfall"),
                "estimated_buy_cash_required": cash_feasibility.get("estimated_buy_cash_required"),
                "estimated_sell_cash_released": cash_feasibility.get("estimated_sell_cash_released"),
                "estimated_cash_impact_after_costs": cash_feasibility.get("estimated_cash_impact_after_costs"),
                "target_value": sum(_float(row.get("target_value"), 0.0) for row in manual_plan),
                "rounded_value": sum(_float(row.get("rounded_value"), 0.0) for row in manual_plan),
                "cash_delta_after_rounding": sum(_float(row.get("cash_delta_after_rounding"), 0.0) for row in manual_plan),
                "board_lot_size": BOARD_LOT_SIZE,
            },
            "required_confirmations": required_confirmations,
            "action_sequence": action_sequence,
            "safety": SAFETY_NOTICE,
        }
    )


def _candidate_trade_evidence_audit(factors: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(factors, start=1):
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        case_id = str(row.get("case_id") or factor_name or f"candidate_{index}").strip()
        evidence_required = _candidate_trade_evidence_required(row)
        missing_metrics = [
            metric
            for metric in DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS
            if evidence_required and _float_or_none(row.get(metric)) is None
        ]
        trade_count = _float_or_none(row.get("trade_count"))
        annualized_return = _float_or_none(row.get("annualized_return"))
        violations: list[str] = []
        if evidence_required and trade_count is not None and trade_count < DAILY_CANDIDATE_MIN_TRADE_COUNT:
            violations.append("trade_count_below_minimum")
        if evidence_required and annualized_return is not None and annualized_return <= 0:
            violations.append("annualized_return_not_positive")
        status = "pass" if not missing_metrics and not violations else "blocked"
        rows.append(
            {
                "candidate_index": index,
                "case_id": case_id,
                "factor_name": factor_name,
                "status": status,
                "evidence_required": evidence_required,
                "missing_metrics": missing_metrics,
                "violations": violations,
                "trade_count": trade_count,
                "min_trade_count": DAILY_CANDIDATE_MIN_TRADE_COUNT,
                "annualized_return": annualized_return,
                "required_metrics": list(DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS),
                "manual_action_allowed": status == "pass",
                "order_placement_allowed": False,
            }
        )
    blocked_count = sum(1 for row in rows if row["status"] != "pass")
    status = "waiting" if not rows else "blocked" if blocked_count else "pass"
    return {
        "status": status,
        "candidate_count": len(rows),
        "blocked_count": blocked_count,
        "passed_count": len(rows) - blocked_count,
        "required_metrics": list(DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS),
        "min_trade_count": DAILY_CANDIDATE_MIN_TRADE_COUNT,
        "rows": rows,
        "manual_action_allowed": status == "pass",
        "order_placement_allowed": False,
    }


def build_candidate_evidence_repair_plan(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    candidate_evidence = (
        readiness.get("candidate_trade_evidence")
        if isinstance(readiness.get("candidate_trade_evidence"), dict)
        else _candidate_trade_evidence_audit(factors)
    )
    evidence_rows = [row for row in candidate_evidence.get("rows", []) if isinstance(row, dict)]
    blocked_rows = [row for row in evidence_rows if row.get("status") != "pass"]
    fallback_only = bool(summary.get("fallback_signal_only")) or "fallback_baseline_not_tradeable" in blockers
    evidence_blocked = bool(blocked_rows) or "candidate_trade_evidence_incomplete" in blockers
    has_candidates = bool(factors)

    if not has_candidates:
        status = "waiting_for_cn_etf_candidate_pool"
        next_step_id = "refresh_primary_cn_etf_candidates"
    elif fallback_only or evidence_blocked or market != "CN_ETF":
        status = "blocked_missing_tradable_candidate_evidence"
        next_step_id = "repair_candidate_trade_evidence"
    else:
        status = "candidate_trade_evidence_ready_for_paper"
        next_step_id = "run_same_parameter_paper_rehearsal"

    manual_ticket_release_allowed = (
        status == "candidate_trade_evidence_ready_for_paper"
        and not blockers
        and bool(readiness.get("manual_action_candidate"))
    )
    blocking_reasons = sorted(
        {
            *blockers,
            *(["fallback_baseline_not_tradeable"] if fallback_only else []),
            *(["candidate_trade_evidence_incomplete"] if evidence_blocked else []),
            *(["non_cn_etf_scope"] if market != "CN_ETF" else []),
        }
    )

    repair_rows = []
    audit_by_case = {
        str(row.get("case_id") or row.get("factor_name") or ""): row
        for row in evidence_rows
        if str(row.get("case_id") or row.get("factor_name") or "").strip()
    }
    for index, row in enumerate(factors[:20], start=1):
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        case_id = str(row.get("case_id") or factor_name or f"candidate_{index}").strip()
        audit = audit_by_case.get(case_id) or audit_by_case.get(factor_name) or {}
        missing_metrics = [str(item) for item in audit.get("missing_metrics", []) if str(item).strip()]
        violations = [str(item) for item in audit.get("violations", []) if str(item).strip()]
        if bool(row.get("fallback_baseline")):
            violations.append("fallback_baseline_observation_only")
        repair_rows.append(
            {
                "rank": _int(row.get("rank"), index),
                "case_id": case_id,
                "factor_name": factor_name,
                "market": str(row.get("market") or market).upper(),
                "candidate_status": row.get("status") or row.get("promotion_status") or row.get("promotion_label"),
                "evidence_status": audit.get("status") or ("blocked" if row.get("fallback_baseline") else "waiting"),
                "missing_metrics": missing_metrics,
                "violations": sorted(set(violations)),
                "required_metrics": list(DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS),
                "min_trade_count": DAILY_CANDIDATE_MIN_TRADE_COUNT,
                "manual_ticket_release_allowed": False,
                "order_placement_allowed": False,
            }
        )

    def action(action_id: str, label: str, target_id: str, workflow_id: str, status_value: str, why: str) -> dict[str, Any]:
        return {
            "action_id": action_id,
            "label": label,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "status": status_value,
            "why": why,
            "manual_ticket_release_allowed": False,
            "order_placement_allowed": False,
        }

    next_actions = [
        action(
            "review_primary_cn_etf_leaderboard",
            "Review primary CN_ETF leaderboard and remove fallback-only rows",
            "daily-trade-decision-candidate-pool",
            "",
            "required" if fallback_only or not has_candidates else "review",
            "Top3 must come from qualified CN_ETF candidates, not runtime fallback baselines.",
        ),
        action(
            "run_long_sample_walk_forward",
            "Run long-sample walk-forward evidence refresh",
            "factor-leaderboard-table",
            "research_backtest",
            "required" if evidence_blocked or fallback_only else "done",
            "Required metrics must include Sharpe, annualized return, drawdown, win rate, and trade count.",
        ),
        action(
            "run_promotion_gate_review",
            "Run promotion gate review",
            "promotion-review-status",
            "promotion_ops",
            "required" if evidence_blocked or fallback_only else "review",
            "Promotion gates prevent a high backtest row from becoming an operator signal without OOS evidence.",
        ),
        action(
            "run_same_parameter_paper_rehearsal",
            "Run same-parameter paper rehearsal after candidate evidence passes",
            "daily-same-parameter-paper-requests",
            "paper_simulation",
            "locked" if status != "candidate_trade_evidence_ready_for_paper" else "required",
            "Paper rehearsal must use the same Top3 parameters and lock id before any manual ticket review.",
        ),
        action(
            "rerun_daily_trade_advisory",
            "Regenerate today's advisory after evidence repair",
            "daily-trade-decision-sheet",
            "daily_trade_advisory",
            "required",
            "The daily signal, target table, cash check, and manual tickets must be rebuilt from repaired evidence.",
        ),
    ]

    return _sanitize(
        {
            "stage": CANDIDATE_EVIDENCE_REPAIR_PLAN_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "status": status,
                "next_step_id": next_step_id,
                "primary_market": market,
                "candidate_count": len(factors),
                "blocked_candidate_count": len(blocked_rows)
                + sum(1 for row in factors if bool(row.get("fallback_baseline"))),
                "fallback_signal_only": fallback_only,
                "candidate_trade_evidence_status": candidate_evidence.get("status") or "waiting",
                "blockers": blocking_reasons,
                "manual_ticket_release_allowed": manual_ticket_release_allowed,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "required_metrics": list(DAILY_CANDIDATE_REQUIRED_TRADE_EVIDENCE_METRICS),
            "min_trade_count": DAILY_CANDIDATE_MIN_TRADE_COUNT,
            "candidate_rows": repair_rows,
            "release_rules": [
                {
                    "rule_id": "primary_market_cn_etf",
                    "status": "pass" if market == "CN_ETF" else "blocked",
                    "text": "Candidate scope must be CN_ETF.",
                },
                {
                    "rule_id": "no_fallback_baseline",
                    "status": "blocked" if fallback_only else "pass",
                    "text": "Runtime fallback baselines are observation-only and cannot release manual tickets.",
                },
                {
                    "rule_id": "required_trade_metrics_present",
                    "status": "pass" if not evidence_blocked else "blocked",
                    "text": "Sharpe, annualized return, max drawdown, win rate, and trade count must be present.",
                },
                {
                    "rule_id": "minimum_trade_count",
                    "status": "pass"
                    if all(
                        _float_or_none(row.get("trade_count")) is not None
                        and _float(row.get("trade_count")) >= DAILY_CANDIDATE_MIN_TRADE_COUNT
                        for row in evidence_rows
                    )
                    else "blocked"
                    if evidence_rows
                    else "waiting",
                    "text": f"Trade count must be at least {DAILY_CANDIDATE_MIN_TRADE_COUNT}.",
                },
                {
                    "rule_id": "same_parameter_paper_before_manual_ticket",
                    "status": "required",
                    "text": "Even after candidate evidence passes, same-parameter paper rehearsal remains required.",
                },
            ],
            "next_actions": next_actions,
            "safety": SAFETY_NOTICE,
        }
    )


def _candidate_trade_evidence_required(row: dict[str, Any]) -> bool:
    if row.get("daily_signal_eligible") is not None or row.get("advisory_eligible") is not None:
        return True
    if row.get("has_oos_evidence") is not None:
        return True
    for key in (
        "status",
        "decision",
        "promotion_status",
        "gate_status",
        "selection_status",
        "review_status",
        "promotion_label",
        "ranking_quality",
        "score_metric",
    ):
        if str(row.get(key) or "").strip():
            return True
    return False


def _pretrade_signal_freshness(pack: dict[str, Any], signal_cards: list[dict[str, Any]]) -> dict[str, Any]:
    run_date = str(pack.get("run_date") or date.today().isoformat())
    signal_dates = sorted(
        {
            str(row.get("signal_date") or row.get("as_of_date") or "").strip()
            for row in signal_cards
            if isinstance(row, dict) and str(row.get("signal_date") or row.get("as_of_date") or "").strip()
        }
    )
    latest_signal_date = signal_dates[-1] if signal_dates else None
    stale_signal_dates = [item for item in signal_dates if item != run_date]
    return {
        "run_date": run_date,
        "latest_signal_date": latest_signal_date,
        "signal_dates": signal_dates,
        "stale_signal_dates": stale_signal_dates,
        "fresh_for_run_date": bool(latest_signal_date) and not stale_signal_dates and latest_signal_date == run_date,
    }


def _build_manual_broker_handoff(pack: dict[str, Any]) -> dict[str, Any]:
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else _build_pretrade_readiness(pack)
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    blocking_reasons = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    can_show_tickets = bool(readiness.get("manual_action_candidate"))
    cash_feasibility = (
        readiness.get("cash_feasibility")
        if isinstance(readiness.get("cash_feasibility"), dict)
        else _manual_cash_feasibility(manual_plan, summary.get("manual_available_cash"))
    )
    raw_copyable_tickets = [
        _broker_handoff_ticket(index, row, summary)
        for index, row in enumerate(manual_plan, start=1)
        if can_show_tickets
    ]
    evidence = _live_profitability_evidence_snapshot(pack.get("live_profitability_evidence_snapshot"))
    evidence_counts = evidence.get("counts") if isinstance(evidence.get("counts"), dict) else {}
    selected_count = _int(summary.get("selected_factor_count"), 0)
    same_parameter_required_count = _int(
        evidence_counts.get("same_parameter_top3_required_requests"),
        selected_count if selected_count > 0 else len(raw_copyable_tickets),
    )
    if same_parameter_required_count <= 0 and raw_copyable_tickets:
        same_parameter_required_count = len(raw_copyable_tickets)
    same_parameter_matched_count = _int(evidence_counts.get("same_parameter_top3_matched_requests"), 0)
    same_parameter_paper_required = bool(raw_copyable_tickets)
    same_parameter_paper_ready = (
        not same_parameter_paper_required
        or (
            same_parameter_required_count > 0
            and same_parameter_matched_count >= same_parameter_required_count
        )
    )
    masked_until_same_parameter = same_parameter_paper_required and not same_parameter_paper_ready
    copyable_tickets = [] if masked_until_same_parameter else raw_copyable_tickets
    rounded_value = sum(_float(row.get("rounded_value"), 0.0) for row in manual_plan)
    cash_delta = sum(_float(row.get("cash_delta_after_rounding"), 0.0) for row in manual_plan)
    target_value = sum(_float(row.get("target_value"), 0.0) for row in manual_plan)
    estimated_buy_cash_required = sum(_float(row.get("estimated_buy_cash_required"), 0.0) for row in manual_plan)
    estimated_sell_cash_released = sum(_float(row.get("estimated_sell_cash_released"), 0.0) for row in manual_plan)
    estimated_cash_impact_after_costs = sum(
        _float(row.get("estimated_cash_impact_after_costs"), 0.0) for row in manual_plan
    )
    if masked_until_same_parameter:
        status = "blocked_same_parameter_paper_required"
    elif copyable_tickets:
        status = "review_only"
    elif "stale_signal_date" in blocking_reasons:
        status = "blocked_by_freshness"
    elif blocking_reasons:
        status = "blocked_by_readiness"
    else:
        status = "waiting_for_tickets"
    if masked_until_same_parameter:
        operator_summary = "先完成 Top3 同参数模拟盘并匹配全部回执，才显示人工券商复核票据；信号不是可直接照抄的实盘指令。"
    elif copyable_tickets:
        operator_summary = "这些内容只是给你在券商软件里逐项人工核对，不能被系统自动提交；价格以券商端实时行情为准。"
    elif status == "blocked_by_freshness":
        operator_summary = "信号日期不是运行日期当天，不能进入人工券商核对；先刷新数据或选择正确的信号日期。"
    elif blocking_reasons:
        operator_summary = "盘前判定仍有阻断项，不能进入人工券商核对。"
    else:
        operator_summary = "还没有可核对票据；先生成今日信号和盘前判定。"
    return _sanitize(
        {
            "stage": MANUAL_BROKER_HANDOFF_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "status": status,
            "operator_summary": operator_summary,
            "ready_for_auto_order": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "paper_simulation_required": True,
            "same_parameter_paper_required": same_parameter_paper_required,
            "same_parameter_paper_ready": same_parameter_paper_ready,
            "copyable_tickets_masked_until_same_parameter_paper": masked_until_same_parameter,
            "manual_ticket_mask_reason": (
                "same_parameter_paper_required_before_manual_tickets"
                if masked_until_same_parameter
                else ""
            ),
            "blocking_reasons": blocking_reasons,
            "summary": {
                "ticket_count": len(copyable_tickets),
                "blocked_copyable_ticket_count": len(raw_copyable_tickets) if masked_until_same_parameter else 0,
                "target_value": target_value,
                "rounded_value": rounded_value,
                "cash_delta_after_rounding": cash_delta,
                "estimated_buy_cash_required": round(estimated_buy_cash_required, 6),
                "estimated_sell_cash_released": round(estimated_sell_cash_released, 6),
                "estimated_cash_impact_after_costs": round(estimated_cash_impact_after_costs, 6),
                "manual_available_cash": cash_feasibility.get("manual_available_cash"),
                "manual_cash_feasibility_status": cash_feasibility.get("status"),
                "manual_cash_shortfall": cash_feasibility.get("estimated_cash_shortfall"),
                "manual_available_cash_source": cash_feasibility.get("cash_source"),
                "traffic_light": readiness.get("traffic_light"),
                "manual_action_candidate": bool(readiness.get("manual_action_candidate")),
                "same_parameter_paper_required_count": same_parameter_required_count,
                "same_parameter_paper_matched_count": same_parameter_matched_count,
                "same_parameter_paper_ready": same_parameter_paper_ready,
            },
            "cash_feasibility": cash_feasibility,
            "confirmation_checklist": [
                {
                    "check_id": "same_parameter_paper_required_before_manual_tickets",
                    "status": "pass" if same_parameter_paper_ready else "required",
                    "text": "Top3 同参数模拟盘必须全部匹配后，才允许查看人工复核票据。",
                },
                {
                    "check_id": "paper_simulation_required",
                    "status": "required",
                    "text": "先查看本地模拟盘、回撤、成交和保护事件；不要把单日信号直接当盈利保证。",
                },
                {
                    "check_id": "verify_broker_realtime_price",
                    "status": "required",
                    "text": "券商端实时价格如果和本地参考价明显不同，必须重新估算份额和现金。",
                },
                {
                    "check_id": "verify_cash_and_position_limit",
                    "status": "required",
                    "text": "核对账户现金、单 ETF 上限、总仓位上限和你能承受的回撤。",
                },
                {
                    "check_id": "manual_only_boundary",
                    "status": "blocked_for_automation",
                    "text": "系统不连接券商、不读取账户、不生成实盘委托、不自动下单。",
                },
            ],
            "copyable_tickets": copyable_tickets,
            "safety": SAFETY_NOTICE,
        }
    )


def _operator_next_actions(
    pack: dict[str, Any],
    readiness: dict[str, Any],
    handoff: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    blocker_set = set(blockers)
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    run_date = str(readiness.get("run_date") or pack.get("run_date") or date.today().isoformat())
    latest_signal_date = freshness.get("latest_signal_date") or "无"
    workflow_by_action = {
        "regenerate_daily_top3_signal": "daily_trade_advisory",
        "run_paper_simulation": "paper_simulation",
    }
    label_by_action = {
        "refresh_cn_etf_data": "查看刷新面板",
        "regenerate_daily_top3_signal": "重新生成建议",
        "run_paper_simulation": "运行模拟盘复核",
        "inspect_factor_runtime_gap": "查看运行缺口",
        "review_risk_and_cash": "查看风险判定",
        "manual_broker_review": "查看人工票据",
    }

    def action(
        action_id: str,
        status: str,
        title: str,
        plain_action: str,
        why: str,
        expected_result: str,
        gui_target: str,
    ) -> dict[str, Any]:
        return {
            "action_id": action_id,
            "status": status,
            "title": title,
            "plain_action": plain_action,
            "why": why,
            "expected_result": expected_result,
            "gui_target": gui_target,
            "cta_label": label_by_action.get(action_id, "查看位置"),
            "cta_target": gui_target,
            "cta_type": "run" if workflow_by_action.get(action_id) else "jump",
            "action_workflow": workflow_by_action.get(action_id),
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
        }

    if "non_cn_etf_scope" in blocker_set:
        return [
            action(
                "return_to_cn_etf_scope",
                "blocked_until_done",
                "先切回 CN_ETF 主线",
                "当前不是 CN_ETF 轮动主线，不能把其他市场或个股信号当作 ETF 实盘依据。",
                "non_cn_etf_scope",
                "每日交易建议只保留 CN_ETF 候选和 CN_ETF 信号。",
                "daily-trade-advisory-status",
            )
        ]

    if "stale_signal_date" in blocker_set:
        return [
            action(
                "refresh_cn_etf_data",
                "blocked_until_done",
                "先刷新 CN_ETF 今日数据",
                "最新信号日期不是运行当天，先刷新本地 CN_ETF 行情和因子输入，再重新生成今日建议。",
                f"stale_signal_date: run_date={run_date}, latest_signal_date={latest_signal_date}",
                "最新信号日期等于运行日期，红灯阻断项消失。",
                "recent-data-refresh-status",
            ),
            action(
                "regenerate_daily_top3_signal",
                "waiting",
                "重新生成今日前三交易建议",
                "数据刷新后再生成前三因子信号，不沿用旧信号。",
                "需要用刷新后的数据重新计算目标 ETF。",
                "生成 run_date 当天的 signal_cards 和手工复核票据。",
                "daily-trade-advisory-status",
            ),
            action(
                "run_paper_simulation",
                "waiting",
                "再跑模拟盘复核",
                "只有当天信号生成后，才进入模拟盘和风险复核。",
                "旧信号不能直接进入模拟盘或人工券商核对。",
                "得到当天信号对应的纸面表现和风险摘要。",
                "paper-metrics",
            ),
        ]

    if "signal_not_ready" in blocker_set or "signal_errors" in blocker_set:
        return [
            action(
                "regenerate_daily_top3_signal",
                "blocked_until_done",
                "先生成完整今日信号",
                "前三因子还没有形成可操作的今日目标仓位，不能进入人工复核。",
                "signal_not_ready/signal_errors",
                "signal_count、target_count、manual_ticket_count 都大于 0。",
                "daily-trade-advisory-status",
            ),
            action(
                "inspect_factor_runtime_gap",
                "waiting",
                "查看为什么信号没生成",
                "如果生成失败，检查因子是否在运行列表、数据日期和参数窗口是否匹配。",
                f"signal_count={summary.get('signal_count', 0)}, target_count={summary.get('target_count', 0)}",
                "找到缺失因子或缺失数据，不再盲目点击执行。",
                "factor-runtime-gap-list",
            ),
        ]

    if "price_or_sizing_missing" in blocker_set:
        return [
            action(
                "verify_price_and_board_lot",
                "blocked_until_done",
                "先补齐价格和一手取整",
                "有票据缺少可用价格或份额取整结果，不能给人工券商核对。",
                "price_or_sizing_missing",
                "每张票据都有参考价、取整份额、取整金额和剩余现金。",
                "daily-pretrade-readiness-action-table",
            )
        ]

    if readiness.get("manual_action_candidate"):
        actions = [
            action(
                "run_paper_simulation",
                "required_before_manual_ticket",
                "先跑模拟盘复核",
                "黄灯只表示可以进入人工复核，不代表可以直接买；先看模拟盘、回撤和成交。",
                "manual_action_candidate=true, paper_simulation_required=true",
                "确认当天信号在模拟盘里没有触发不可接受的回撤、成交或保护事件。",
                "paper-metrics",
            ),
            action(
                "review_risk_and_cash",
                "required_before_manual_ticket",
                "再人工核对风险和现金",
                "核对单 ETF 上限、总仓位、现金余量、流动性和你能承受的最大回撤。",
                "manual review required before any broker-side action",
                "确认风险预算允许今天继续人工复核。",
                "daily-pretrade-readiness-verdict",
            ),
        ]
        if handoff.get("status") == "review_only":
            actions.append(
                action(
                    "manual_broker_review",
                    "manual_only",
                    "最后才看人工券商票据",
                    "只把票据当成核对清单；是否在券商端操作必须由你本人决定。",
                    "system never submits orders",
                    "在券商端逐项人工核对代码、价格、份额、金额和风险。",
                    "daily-manual-broker-handoff-ticket-table",
                )
            )
        return actions

    return [
        action(
            "inspect_red_light_blockers",
            "blocked_until_done",
            "先处理红灯阻断项",
            "当前状态不能进入人工操作，先看阻断项和确认清单。",
            "/".join(blockers) or "unknown_blocker",
            "红灯阻断项消失后，再进入模拟盘和人工复核。",
            "daily-pretrade-readiness-status",
        )
    ]


def _broker_handoff_ticket(index: int, row: dict[str, Any], summary: dict[str, Any] | None = None) -> dict[str, Any]:
    asset_id = str(row.get("asset_id") or "")
    side = str(row.get("side") or "buy_or_adjust")
    latest_price = _float_or_none(row.get("latest_price"))
    rounded_quantity = _int(row.get("rounded_quantity"), 0)
    rounded_value = _float(row.get("rounded_value"), 0.0)
    cash_delta = _float(row.get("cash_delta_after_rounding"), 0.0)
    estimated_commission_bps = _float(row.get("estimated_commission_bps"), MANUAL_ESTIMATED_COMMISSION_BPS)
    estimated_commission_cost = _float(row.get("estimated_commission_cost"), 0.0)
    estimated_buy_cash_required = _float(row.get("estimated_buy_cash_required"), 0.0)
    estimated_sell_cash_released = _float(row.get("estimated_sell_cash_released"), 0.0)
    estimated_cash_impact_after_costs = _float(row.get("estimated_cash_impact_after_costs"), 0.0)
    current_quantity = _float(row.get("current_quantity"), 0.0)
    delta_value = _float(row.get("delta_value"), _float(row.get("target_value"), 0.0))
    reference_price = "--" if latest_price is None else f"{latest_price:.4f}"
    copy_text = (
        f"{index}. ETF {asset_id}；方向={side}；参考价={reference_price}；"
        f"当前持仓={current_quantity:.2f}；净差额金额={delta_value:.2f}；"
        f"按 {BOARD_LOT_SIZE} 份一手取整数量={rounded_quantity}；"
        f"参考金额={rounded_value:.2f}；取整误差约={cash_delta:.2f}。"
        "请在券商端核对实时价格、代码、现金和风险；系统不会下单。"
    )
    copy_text += (
        f" estimated_buy_cash_required={estimated_buy_cash_required:.2f};"
        f" estimated_sell_cash_released={estimated_sell_cash_released:.2f};"
        f" estimated_cash_impact_after_costs={estimated_cash_impact_after_costs:.2f};"
        f" estimated_commission_bps={estimated_commission_bps:.2f};"
        f" estimated_commission_cost={estimated_commission_cost:.2f}."
    )
    risk_budget = _manual_ticket_risk_budget(
        row,
        portfolio_value=_float((summary or {}).get("portfolio_value"), 100000.0),
        risk_profile=_risk_profile_by_id(str((summary or {}).get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID)),
    )
    execution_guardrails = _manual_ticket_execution_guardrails(
        {**row, "reference_price": latest_price, "rounded_value": rounded_value}
    )
    enriched_row = {**row, "risk_budget": risk_budget, "execution_guardrails": execution_guardrails}
    return {
        "step_number": index,
        "ticket_id": row.get("ticket_id"),
        "asset_id": asset_id,
        "side": side,
        "reference_price": latest_price,
        "current_quantity": row.get("current_quantity"),
        "current_value": row.get("current_value"),
        "target_weight": row.get("target_weight"),
        "target_value": row.get("target_value"),
        "delta_value": row.get("delta_value"),
        "rounded_quantity": rounded_quantity,
        "rounded_quantity_delta": row.get("rounded_quantity_delta"),
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": cash_delta,
        "estimated_commission_bps": estimated_commission_bps,
        "estimated_commission_cost": estimated_commission_cost,
        "estimated_buy_cash_required": estimated_buy_cash_required,
        "estimated_sell_cash_released": estimated_sell_cash_released,
        "estimated_cash_impact_after_costs": estimated_cash_impact_after_costs,
        "source_factors": row.get("source_factors"),
        "copy_text": copy_text,
        "do_not_submit_until_checked": True,
        "risk_budget": risk_budget,
        "execution_guardrails": execution_guardrails,
        "manual_skip_conditions": _manual_ticket_skip_conditions(enriched_row),
        "review_checklist": _broker_ticket_review_checklist(enriched_row),
        "red_flags": _broker_ticket_red_flags(),
        "live_order_allowed": False,
        "order_placement_allowed": False,
    }


def _manual_ticket_execution_guardrails(row: dict[str, Any]) -> dict[str, Any]:
    reference_price = _float_or_none(row.get("reference_price") or row.get("latest_price"))
    rounded_value = max(0.0, _float(row.get("rounded_value"), 0.0))
    lower_bound = None
    upper_bound = None
    if reference_price is not None and reference_price > 0:
        lower_bound = round(reference_price * (1 - MANUAL_PRICE_DEVIATION_GUARD_PCT), 6)
        upper_bound = round(reference_price * (1 + MANUAL_PRICE_DEVIATION_GUARD_PCT), 6)
    return {
        "guardrail_id": "manual_pretrade_price_slippage_guard",
        "reference_price": reference_price,
        "max_reference_price_deviation_pct": MANUAL_PRICE_DEVIATION_GUARD_PCT,
        "lower_price_bound": lower_bound,
        "upper_price_bound": upper_bound,
        "max_slippage_bps": MANUAL_MAX_SLIPPAGE_BPS,
        "max_estimated_slippage_cost": round(rounded_value * MANUAL_MAX_SLIPPAGE_BPS / 10000, 6),
        "manual_input_fields": [
            "broker_realtime_price",
            "actual_fill_price",
            "fill_quantity",
            "execute_or_skip_reason",
        ],
        "plain_rule": "券商实时价必须落在参考价护栏内；预估滑点或实际价格明显超出时，跳过或重新生成今日建议。",
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _manual_ticket_risk_budget(
    row: dict[str, Any],
    *,
    portfolio_value: float,
    risk_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = risk_profile or _risk_profile_by_id(DEFAULT_RISK_PROFILE_ID) or {}
    profile_id = str(profile.get("profile_id") or DEFAULT_RISK_PROFILE_ID)
    profile_label = profile.get("label") or profile_id
    portfolio = max(0.0, _float(portfolio_value, 100000.0))
    rounded_value = max(0.0, _float(row.get("rounded_value"), 0.0))
    target_weight = max(0.0, _float(row.get("target_weight"), 0.0))
    max_single = max(0.0, _float(profile.get("max_single_etf_weight"), 0.30))
    max_gross = max(0.0, _float(profile.get("max_gross_exposure"), 0.60))
    min_cash = max(0.0, _float(profile.get("min_cash_weight"), 0.40))
    max_drawdown = max(0.0, _float(profile.get("max_acceptable_drawdown"), 0.20))
    daily_loss_stop = max(0.0, _float(profile.get("daily_loss_stop"), 0.02))
    portfolio_daily_loss_budget = portfolio * daily_loss_stop
    ticket_adverse_move_loss = rounded_value * daily_loss_stop
    max_single_value = portfolio * max_single
    max_drawdown_budget_value = portfolio * max_drawdown
    return {
        "risk_profile_id": profile_id,
        "risk_profile_label": profile_label,
        "portfolio_value": portfolio,
        "target_weight": target_weight,
        "rounded_value": rounded_value,
        "max_single_etf_weight": max_single,
        "max_single_etf_value": max_single_value,
        "max_gross_exposure": max_gross,
        "min_cash_weight": min_cash,
        "max_acceptable_drawdown": max_drawdown,
        "max_drawdown_budget_value": max_drawdown_budget_value,
        "daily_loss_stop": daily_loss_stop,
        "portfolio_daily_loss_budget": portfolio_daily_loss_budget,
        "ticket_adverse_move_loss": ticket_adverse_move_loss,
        "ticket_loss_budget_share": (
            ticket_adverse_move_loss / portfolio_daily_loss_budget
            if portfolio_daily_loss_budget > 0
            else 0.0
        ),
        "single_etf_limit_breached": bool(max_single and target_weight > max_single + 1e-12),
        "rounded_value_limit_breached": bool(max_single_value and rounded_value > max_single_value + 1e-9),
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _manual_ticket_skip_conditions(row: dict[str, Any]) -> list[dict[str, Any]]:
    budget = row.get("risk_budget") if isinstance(row.get("risk_budget"), dict) else {}
    guardrails = row.get("execution_guardrails") if isinstance(row.get("execution_guardrails"), dict) else {}
    rounded_quantity = _int(row.get("rounded_quantity"), 0)
    rounded_value = _float(row.get("rounded_value"), 0.0)
    reference_price = _float_or_none(row.get("reference_price") or row.get("latest_price"))

    def condition(condition_id: str, status: str, plain_condition: str) -> dict[str, Any]:
        return {
            "condition_id": condition_id,
            "status": status,
            "plain_condition": plain_condition,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }

    return [
        condition(
            "single_etf_limit_breached",
            "blocked" if budget.get("single_etf_limit_breached") or budget.get("rounded_value_limit_breached") else "pass",
            "单 ETF 权重或金额超过风险档位上限时，跳过这张票据。",
        ),
        condition(
            "zero_or_missing_quantity",
            "blocked" if rounded_quantity <= 0 or rounded_value <= 0 else "pass",
            "数量为 0、金额为 0 或无法按 100 份取整时，不进入券商端操作。",
        ),
        condition(
            "broker_price_changed_from_reference",
            "required",
            f"券商端实时价必须人工核对；本地参考价={reference_price if reference_price is not None else '--'}，偏离明显就重新估算或跳过。",
        ),
        condition(
            "broker_price_outside_guardrail",
            "required",
            (
                "券商实时价必须在人工价格护栏内；"
                f"下限={guardrails.get('lower_price_bound', '--')}，"
                f"上限={guardrails.get('upper_price_bound', '--')}，"
                f"最大滑点={guardrails.get('max_slippage_bps', '--')}bps；超出就跳过或重算。"
            ),
        ),
        condition(
            "paper_receipt_missing",
            "required",
            "没有同参数模拟盘回执和盘后复盘样本时，不要把票据升级为真实资金动作。",
        ),
        condition(
            "manual_discomfort_or_unclear_reason",
            "required",
            "如果本人无法解释为什么买、能承受多少回撤、触发什么熔断，就跳过。",
        ),
    ]


def _broker_ticket_review_checklist(row: dict[str, Any]) -> list[dict[str, Any]]:
    asset_id = str(row.get("asset_id") or "")
    side = str(row.get("side") or "review")
    rounded_quantity = _int(row.get("rounded_quantity"), 0)
    rounded_value = _float_or_none(row.get("rounded_value"))
    reference_price = _float_or_none(row.get("reference_price") or row.get("latest_price"))
    risk_budget = row.get("risk_budget") if isinstance(row.get("risk_budget"), dict) else {}
    guardrails = row.get("execution_guardrails") if isinstance(row.get("execution_guardrails"), dict) else {}
    checks = [
        (
            "asset_code_match",
            "核对 ETF 代码",
            f"券商端搜索并确认 ETF={asset_id or '--'}；不认识、停牌、退市或不是 CN_ETF 就跳过。",
        ),
        (
            "broker_realtime_price",
            "核对实时价格",
            f"本地参考价={reference_price if reference_price is not None else '--'}；券商端实时价偏离明显时重新估算金额和数量。",
        ),
        (
            "price_guardrail",
            "价格/滑点护栏",
            (
                f"实时价必须在 {guardrails.get('lower_price_bound', '--')} - "
                f"{guardrails.get('upper_price_bound', '--')} 之间；"
                f"最大滑点={guardrails.get('max_slippage_bps', '--')}bps，"
                f"预估滑点成本上限={guardrails.get('max_estimated_slippage_cost', '--')}。"
            ),
        ),
        (
            "quantity_and_lot_size",
            "核对方向和数量",
            f"方向={side}，数量={rounded_quantity}；数量为 0、不是整手或方向看不懂就不要操作。",
        ),
        (
            "cash_and_weight_limit",
            "核对现金和仓位上限",
            f"票据金额={rounded_value if rounded_value is not None else '--'}；人工确认现金、单 ETF 权重、总仓位和回撤预算没有超限。",
        ),
        (
            "risk_budget_gate",
            "核对风险预算",
            f"风险档位={risk_budget.get('risk_profile_id', '--')}；当日亏损预算={risk_budget.get('portfolio_daily_loss_budget', '--')}；这张票据不利波动估算={risk_budget.get('ticket_adverse_move_loss', '--')}；超限就跳过。",
        ),
        (
            "final_human_decision",
            "最终本人确认",
            "离开本系统后只在券商端人工决定；这张票据不是订单，也不能自动提交。",
        ),
    ]
    return [
        {
            "check_id": check_id,
            "label": label,
            "status": "required",
            "plain_check": plain_check,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
        for check_id, label, plain_check in checks
    ]


def _broker_ticket_red_flags() -> list[dict[str, Any]]:
    return [
        _broker_ticket_red_flag(
            "price_changed_from_reference",
            "券商端实时价明显偏离本地参考价，必须重新估算金额、数量和滑点。",
        ),
        _broker_ticket_red_flag(
            "cash_or_position_limit_breach",
            "现金不足、单 ETF 权重超限、总仓位超限或回撤预算超限时，跳过这张票据。",
        ),
        _broker_ticket_red_flag(
            "asset_not_tradeable",
            "停牌、涨跌停、无法成交、代码不匹配或不是目标 ETF 时，跳过这张票据。",
        ),
        _broker_ticket_red_flag(
            "manual_discomfort",
            "本人无法解释这笔交易、情绪不稳定或不愿承担回撤时，跳过而不是硬做。",
        ),
    ]


def _broker_ticket_red_flag(flag_id: str, plain_flag: str) -> dict[str, Any]:
    return {
        "flag_id": flag_id,
        "status": "block_if_seen",
        "plain_flag": plain_flag,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def build_daily_trade_decision_sheet(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    live_gate = pack.get("daily_live_readiness_gate") if isinstance(pack.get("daily_live_readiness_gate"), dict) else {}
    action_card = pack.get("beginner_trade_action_card") if isinstance(pack.get("beginner_trade_action_card"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    combined_targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    candidate_pool_top20 = (
        pack.get("candidate_pool_top20")
        if isinstance(pack.get("candidate_pool_top20"), dict)
        else _daily_candidate_pool_from_candidates(factors, primary_market=market)
    )
    candidate_repair_plan = (
        pack.get("candidate_evidence_repair_plan")
        if isinstance(pack.get("candidate_evidence_repair_plan"), dict)
        else build_candidate_evidence_repair_plan(pack)
    )
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(combined_targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    position_status = str(validation.get("status") or "not_provided")
    live_summary = live_gate.get("summary") if isinstance(live_gate.get("summary"), dict) else {}
    action_summary = action_card.get("summary") if isinstance(action_card.get("summary"), dict) else {}
    action_next = action_card.get("next_action") if isinstance(action_card.get("next_action"), dict) else {}

    if position_status == "error":
        decision = "blocked_fix_current_positions"
        answer_code = "no"
        plain_answer = "不能操作。当前持仓输入含有账户、券商、订单或格式风险，先修正输入。"
        target_id = "daily-current-positions"
        button_label = "修正当前持仓"
        workflow_id = ""
    elif blockers:
        decision = "blocked_pretrade_red_light"
        answer_code = "no"
        plain_answer = "不能操作。盘前红灯没有清理前，不进入模拟盘或人工券商复核。"
        target_id = "daily-pretrade-readiness-verdict"
        button_label = "查看盘前红灯"
        workflow_id = ""
    elif ticket_count > 0:
        decision = "paper_first_manual_review"
        answer_code = "not_yet"
        plain_answer = "还不能直接买。先跑同参数模拟盘，再人工核对票据、现金、价格和风险。"
        target_id = "paper-metrics"
        button_label = "运行模拟盘复核"
        workflow_id = "paper_simulation"
    elif signal_count > 0 and target_count > 0:
        decision = "waiting_for_manual_tickets"
        answer_code = "not_yet"
        plain_answer = "已有今日信号，但还没有完整人工复核票据。先检查价格、仓位和一手取整。"
        target_id = "daily-trade-target-table"
        button_label = "检查目标仓位"
        workflow_id = "daily_trade_advisory"
    else:
        decision = "waiting_for_daily_signal"
        answer_code = "not_yet"
        plain_answer = "还没有今日可用信号。先生成今日前三 CN_ETF 因子建议。"
        target_id = "run-daily-trade-advisory"
        button_label = "生成今日建议"
        workflow_id = "daily_trade_advisory"

    if action_next.get("target_id"):
        target_id = str(action_next.get("target_id"))
        button_label = str(action_next.get("button_label") or button_label)
        workflow_id = str(action_next.get("workflow_id") or workflow_id)
    if action_summary.get("plain_answer"):
        plain_answer = str(action_summary.get("plain_answer"))
    if live_summary.get("decision") in {"blocked_fix_current_positions", "blocked_pretrade_red_light"}:
        decision = str(live_summary.get("decision"))

    signal_by_factor = {
        str(row.get("factor_name") or ""): row
        for row in signal_cards
        if str(row.get("factor_name") or "").strip()
    }
    daily_top3 = []
    for index, factor in enumerate(factors[:3], start=1):
        factor_name = str(factor.get("factor_name") or factor.get("factor") or "")
        signal = signal_by_factor.get(factor_name, {})
        daily_top3.append(
            {
                "rank": _int(factor.get("rank"), index),
                "factor_name": factor_name,
                "case_id": factor.get("case_id"),
                "market": str(factor.get("market") or market).upper(),
                "signal_status": signal.get("status") or "missing",
                "signal_date": signal.get("signal_date") or signal.get("as_of_date"),
                "target_count": _int(signal.get("target_count"), 0),
                "sharpe": _float_or_none(factor.get("sharpe")),
                "annualized_return": _float_or_none(factor.get("annualized_return")),
                "total_return": _float_or_none(factor.get("total_return")),
                "max_drawdown": _float_or_none(factor.get("max_drawdown")),
                "win_rate": _float_or_none(factor.get("win_rate")),
                "rank_ic": _float_or_none(factor.get("rank_ic")),
                "promotion_label": factor.get("promotion_label"),
                "plain_conclusion": factor.get("plain_conclusion"),
                "params": factor.get("params") if isinstance(factor.get("params"), dict) else {},
                "direct_order_allowed": False,
            }
        )

    ticket_source = copyable_tickets if copyable_tickets else ([] if blockers or position_status == "error" else manual_plan)
    today_actions = [_decision_sheet_action(index, row) for index, row in enumerate(ticket_source, start=1)]
    missing_evidence = _decision_sheet_missing_evidence(
        decision=decision,
        blockers=blockers,
        ticket_count=ticket_count,
        position_status=position_status,
    )
    operator_script = _decision_sheet_operator_script(decision, ticket_count)
    trade_system_state = _build_daily_trade_system_state(
        decision=decision,
        market=market,
        selected_factor_count=_int(summary.get("selected_factor_count"), len(factors)),
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        blocker_count=len(blockers),
        position_status=position_status,
        pre_live_master_gate=pack.get("live_profitability_evidence_snapshot", {}).get("pre_live_master_gate", {}),
    )
    trade_package_checklist = _decision_sheet_trade_package_checklist(
        daily_top3=daily_top3,
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        blockers=blockers,
        position_status=position_status,
        decision=decision,
    )
    beginner_operation_recipe = _decision_sheet_beginner_operation_recipe(
        decision=decision,
        plain_answer=plain_answer,
        button_label=button_label,
        target_id=target_id,
        workflow_id=workflow_id,
        daily_top3=daily_top3,
        today_actions=today_actions,
        missing_evidence=missing_evidence,
        trade_package_checklist=trade_package_checklist,
        blockers=blockers,
        position_status=position_status,
    )

    return _sanitize(
        {
            "stage": DAILY_TRADE_DECISION_SHEET_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "decision": decision,
                "answer_code": answer_code,
                "plain_answer": plain_answer,
                "primary_market": market,
                "selected_factor_count": _int(summary.get("selected_factor_count"), len(factors)),
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "blocker_count": len(blockers),
                "manual_review_required": True,
                "paper_simulation_required": True,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "what_to_do_now": {
                "button_label": button_label,
                "target_id": target_id,
                "workflow_id": workflow_id,
                "plain_action": live_summary.get("primary_action") or action_next.get("plain_action") or plain_answer,
                "manual_only_boundary": True,
                "order_placement_allowed": False,
            },
            "daily_top3": daily_top3,
            "candidate_pool_top20": candidate_pool_top20,
            "candidate_evidence_repair_plan": candidate_repair_plan,
            "today_actions": today_actions,
            "missing_evidence": missing_evidence,
            "operator_script": operator_script,
            "trade_system_state": trade_system_state,
            "trade_package_checklist": trade_package_checklist,
            "beginner_operation_recipe": beginner_operation_recipe,
            "safety": SAFETY_NOTICE,
        }
    )


def build_daily_live_trading_system_status(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    decision_sheet = (
        pack.get("daily_trade_decision_sheet")
        if isinstance(pack.get("daily_trade_decision_sheet"), dict)
        else build_daily_trade_decision_sheet(pack)
    )
    pre_execution = (
        pack.get("daily_pre_execution_guard")
        if isinstance(pack.get("daily_pre_execution_guard"), dict)
        else build_daily_pre_execution_guard(pack)
    )
    same_paper = (
        pack.get("daily_same_parameter_paper_rehearsal")
        if isinstance(pack.get("daily_same_parameter_paper_rehearsal"), dict)
        else build_daily_same_parameter_paper_rehearsal(pack)
    )
    profitability = (
        pack.get("live_profitability_readiness")
        if isinstance(pack.get("live_profitability_readiness"), dict)
        else build_live_profitability_readiness_scorecard(pack)
    )
    pre_summary = pre_execution.get("summary") if isinstance(pre_execution.get("summary"), dict) else {}
    paper_summary = same_paper.get("summary") if isinstance(same_paper.get("summary"), dict) else {}
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(pack.get("factors", [])) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), 0)
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), 0)
    ticket_count = _int(summary.get("manual_ticket_count"), 0)
    guard_status = str(pre_summary.get("guard_status") or "waiting")
    paper_status = str(paper_summary.get("rehearsal_status") or "waiting")
    paper_allowed = bool(paper_summary.get("paper_rehearsal_allowed")) or bool(
        pre_summary.get("paper_rehearsal_allowed")
    )
    manual_review_allowed = bool(pre_summary.get("manual_broker_review_allowed")) or bool(
        paper_summary.get("manual_broker_review_allowed")
    )
    small_capital_candidate = bool(profitability_summary.get("small_capital_observation_candidate"))
    production_candidate = bool(profitability_summary.get("production_manual_review_candidate"))
    manual_clean_count = _int(profitability_summary.get("manual_execution_clean_receipts"), 0)
    manual_blocked_count = _int(profitability_summary.get("manual_execution_blocked_receipts"), 0)
    manual_missing_review_count = _int(
        profitability_summary.get("manual_execution_missing_review_receipts"), 0
    )
    manual_execution_feedback_status = _operator_execution_feedback_status(
        manual_blocked_count=manual_blocked_count,
        manual_missing_review_count=manual_missing_review_count,
        manual_clean_count=manual_clean_count,
    )

    if market != "CN_ETF":
        go_live_state = "blocked_wrong_market"
        next_step_id = "confirm_cn_etf_scope"
    elif manual_execution_feedback_status == "blocked_manual_execution_audit":
        go_live_state = "blocked_manual_execution_feedback"
        next_step_id = "review_manual_execution_feedback"
    elif blockers:
        go_live_state = "blocked_pretrade_gates"
        next_step_id = "clear_pretrade_blockers"
    elif selected_count <= 0:
        go_live_state = "waiting_for_top3_candidates"
        next_step_id = "select_top3_candidates"
    elif signal_count <= 0 or target_count <= 0:
        go_live_state = "waiting_for_today_signals"
        next_step_id = "generate_today_signals"
    elif ticket_count <= 0:
        go_live_state = "manual_ticket_required"
        next_step_id = "build_manual_tickets"
    elif not paper_allowed:
        go_live_state = "same_parameter_paper_locked"
        next_step_id = "clear_pre_execution_guard"
    elif not manual_review_allowed:
        go_live_state = "same_parameter_paper_required"
        next_step_id = "run_same_parameter_paper"
    elif small_capital_candidate or production_candidate:
        go_live_state = "manual_small_capital_review_candidate"
        next_step_id = "manual_broker_review"
    else:
        go_live_state = "manual_review_material_ready"
        next_step_id = "manual_broker_review"

    def step(
        step_number: int,
        step_id: str,
        label: str,
        status: str,
        target_id: str,
        workflow_id: str = "",
        evidence: str = "",
    ) -> dict[str, Any]:
        return {
            "step_number": step_number,
            "step_id": step_id,
            "label": label,
            "status": status,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "evidence": evidence,
            "manual_required": True,
            "automation_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }

    signal_ready = signal_count > 0 and target_count > 0
    operating_ladder = [
        step(
            1,
            "select_top3_candidates",
            "每日先选 CN_ETF Top3 候选因子",
            "done" if selected_count else "required",
            "daily-trade-decision-top3",
            "daily_trade_advisory" if not selected_count else "",
            f"selected={selected_count}; direct_buy=false",
        ),
        step(
            2,
            "generate_today_signals",
            "生成当日信号和目标 ETF",
            "done" if signal_ready else ("blocked" if blockers else "required"),
            "daily-trade-target-table",
            "daily_trade_advisory" if not signal_ready else "",
            f"signals={signal_count}; targets={target_count}",
        ),
        step(
            3,
            "build_manual_tickets",
            "折算为人工复核票据",
            "done" if ticket_count else ("blocked" if blockers else "required"),
            "daily-manual-broker-handoff-ticket-table",
            "",
            f"tickets={ticket_count}; board_lot={BOARD_LOT_SIZE}",
        ),
        step(
            4,
            "run_same_parameter_paper",
            "同参数模拟盘复核",
            "done" if manual_review_allowed else ("required" if paper_allowed else "locked"),
            "paper-metrics",
            "paper_simulation" if paper_allowed and not manual_review_allowed else "",
            f"rehearsal_status={paper_status}",
        ),
        step(
            5,
            "pre_execution_guard",
            "盘前价格、容量、风控护栏",
            "done" if manual_review_allowed else ("blocked" if guard_status.startswith("blocked") else "required"),
            "daily-pre-execution-guard",
            "",
            f"guard_status={guard_status}",
        ),
        step(
            6,
            "manual_broker_review",
            "本人离开系统后在券商端人工复核",
            "manual_required" if manual_review_allowed else "locked",
            "daily-manual-broker-handoff-ticket-table",
            "",
            "software_order=false; broker_connection=false",
        ),
        step(
            7,
            "post_close_journal",
            "收盘后复盘并记录反馈",
            "required" if selected_count else "waiting",
            "beginner-post-close-journal-board",
            "post_close_journal" if selected_count else "",
            "required for next-session reuse and factor health",
        ),
        step(
            8,
            "review_manual_execution_feedback",
            "复核上一轮人工执行反馈",
            "blocked"
            if manual_execution_feedback_status == "blocked_manual_execution_audit"
            else "done"
            if manual_execution_feedback_status == "clean_feedback_ready"
            else "required",
            "beginner-post-close-journal-board",
            "post_close_journal"
            if manual_execution_feedback_status == "blocked_manual_execution_audit"
            else "",
            (
                f"feedback={manual_execution_feedback_status}; clean={manual_clean_count}; "
                f"blocked={manual_blocked_count}; missing_review={manual_missing_review_count}"
            ),
        ),
    ]
    next_step = next((row for row in operating_ladder if row["step_id"] == next_step_id), operating_ladder[0])
    runtime_contract = _daily_trading_runtime_contract(
        market=market,
        selected_count=selected_count,
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        blockers=blockers,
        guard_status=guard_status,
        paper_status=paper_status,
        paper_allowed=paper_allowed,
        manual_review_allowed=manual_review_allowed,
        small_capital_candidate=small_capital_candidate,
        production_candidate=production_candidate,
        manual_execution_feedback_status=manual_execution_feedback_status,
        profitability=profitability,
    )
    return _sanitize(
        {
            "stage": DAILY_LIVE_TRADING_SYSTEM_STATUS_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "go_live_state": go_live_state,
                "primary_market": market,
                "daily_top3_policy": "top3_candidates_not_orders",
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "pre_execution_guard_status": guard_status,
                "same_parameter_paper_status": paper_status,
                "profitability_decision": profitability_summary.get("decision"),
                "small_capital_observation_candidate": small_capital_candidate,
                "production_manual_review_candidate": production_candidate,
                "manual_execution_feedback_status": manual_execution_feedback_status,
                "manual_execution_clean_receipts": manual_clean_count,
                "manual_execution_blocked_receipts": manual_blocked_count,
                "manual_execution_missing_review_receipts": manual_missing_review_count,
                "runtime_contract_status": runtime_contract["summary"]["contract_status"],
                "runtime_contract_passed_layer_count": runtime_contract["summary"]["passed_layer_count"],
                "runtime_contract_blocked_layer_count": runtime_contract["summary"]["blocked_layer_count"],
                "runtime_contract_required_layer_count": runtime_contract["summary"]["required_layer_count"],
                "next_step_id": next_step.get("step_id"),
                "next_label": next_step.get("label"),
                "next_target_id": next_step.get("target_id"),
                "next_workflow_id": next_step.get("workflow_id"),
                "direct_buy_top3_allowed": False,
                "manual_review_required": True,
                "paper_simulation_required": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "live_trading_allowed": False,
            },
            "operating_ladder": operating_ladder,
            "top3_selection_policy": {
                "primary_market": "CN_ETF",
                "top_factor_limit": 3,
                "rank_source": "factor leaderboard plus promotion/paper/oos evidence",
                "direct_buy_from_leaderboard_allowed": False,
                "same_day_signal_required": True,
            },
            "deployment_boundary": {
                "allowed_stage": "research_to_paper_to_manual_review",
                "forbidden": [
                    "auto_broker_connection",
                    "account_read",
                    "order_routing",
                    "copy_top3_as_order",
                    "reuse_stale_signal",
                ],
                "manual_small_capital_review_can_only_start_after": [
                    "fresh_cn_etf_signal",
                    "manual_ticket_pack",
                    "same_parameter_paper_receipt",
                    "pre_execution_guard",
                    "post_close_journal",
                    "profitability_evidence_review",
                ],
            },
            "trading_runtime_contract": runtime_contract,
            "safety": SAFETY_NOTICE,
        }
    )


def _daily_trading_runtime_contract(
    *,
    market: str,
    selected_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    blockers: list[str],
    guard_status: str,
    paper_status: str,
    paper_allowed: bool,
    manual_review_allowed: bool,
    small_capital_candidate: bool,
    production_candidate: bool,
    manual_execution_feedback_status: str,
    profitability: dict[str, Any],
) -> dict[str, Any]:
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    hard_gates = [row for row in profitability.get("hard_gates", []) if isinstance(row, dict)]
    gate_by_id = {str(row.get("gate_id") or ""): row for row in hard_gates}
    signal_ready = signal_count > 0 and target_count > 0
    ticket_ready = ticket_count > 0 and not blockers
    risk_guard_ready = manual_review_allowed or (
        ticket_ready and not str(guard_status or "").startswith("blocked") and bool(paper_allowed)
    )
    feedback_clean = manual_execution_feedback_status == "clean_feedback_ready"
    feedback_blocked = manual_execution_feedback_status == "blocked_manual_execution_audit"

    layers = [
        _runtime_contract_layer(
            "approved_factor_pool",
            "准入因子池",
            "pass" if market == "CN_ETF" and selected_count > 0 else "blocked" if market != "CN_ETF" else "required",
            f"market={market}; selected_top3={selected_count}; direct_buy=false",
            "daily-trade-decision-top3",
            "daily_trade_advisory" if selected_count <= 0 else "",
        ),
        _runtime_contract_layer(
            "same_day_signal",
            "当日信号",
            "pass" if signal_ready and not blockers else "blocked" if blockers else "required",
            f"signals={signal_count}; targets={target_count}; blockers={len(blockers)}",
            "daily-trade-target-table",
            "daily_trade_advisory" if not signal_ready else "",
        ),
        _runtime_contract_layer(
            "portfolio_rebalance_plan",
            "组合调仓",
            "pass" if ticket_ready else "blocked" if blockers else "required",
            f"manual_tickets={ticket_count}; current_positions_required=true; board_lot={BOARD_LOT_SIZE}",
            "daily-manual-broker-handoff-ticket-table",
            "daily_trade_advisory" if ticket_count <= 0 and not blockers else "",
        ),
        _runtime_contract_layer(
            "risk_cost_capacity_guard",
            "风控成本",
            "pass" if risk_guard_ready else "blocked" if str(guard_status or "").startswith("blocked") else "required",
            f"guard_status={guard_status}; paper_status={paper_status}; paper_allowed={paper_allowed}",
            "daily-pre-execution-guard",
            "paper_simulation" if paper_allowed and not manual_review_allowed else "",
        ),
        _runtime_contract_layer(
            "post_close_feedback_loop",
            "盘后反馈",
            "pass" if feedback_clean else "blocked" if feedback_blocked else "required",
            f"execution_feedback={manual_execution_feedback_status}; next_session_quarantine={profitability_summary.get('decision')}",
            "beginner-post-close-journal-board",
            "post_close_journal" if not feedback_clean else "",
        ),
    ]
    passed = sum(1 for row in layers if row["status"] == "pass")
    blocked = sum(1 for row in layers if row["status"] == "blocked")
    required = sum(1 for row in layers if row["status"] == "required")
    if blocked:
        contract_status = "blocked_trading_system_contract"
    elif passed == len(layers) and (small_capital_candidate or production_candidate):
        contract_status = "manual_observation_candidate"
    elif passed == len(layers):
        contract_status = "manual_review_material_ready"
    else:
        contract_status = "evidence_incomplete"

    return _sanitize(
        {
            "summary": {
                "contract_status": contract_status,
                "layer_count": len(layers),
                "passed_layer_count": passed,
                "blocked_layer_count": blocked,
                "required_layer_count": required,
                "primary_market": market,
                "daily_top3_direct_order_allowed": False,
                "manual_review_required": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "top3_signal_policy": {
                "policy_id": "daily_top3_candidates_not_orders",
                "plain_rule": (
                    "Select Top3 only from the pre-approved CN_ETF candidate pool; "
                    "the Top3 list is the signal router, not the buy command."
                ),
                "requires_same_day_signal": True,
                "requires_current_positions": True,
                "requires_same_parameter_paper": True,
                "requires_post_close_feedback": True,
                "direct_buy_allowed": False,
            },
            "layers": layers,
            "profitability_controls": [
                _runtime_profitability_control("walk_forward_oos", gate_by_id.get("walk_forward_oos")),
                _runtime_profitability_control("lookahead_bias_audit", gate_by_id.get("lookahead_bias_audit")),
                _runtime_profitability_control("multiple_testing_control", gate_by_id.get("multiple_testing_control")),
                _runtime_profitability_control(
                    "transaction_cost_capacity",
                    gate_by_id.get("transaction_cost_capacity"),
                ),
                {
                    "control_id": "execution_feedback",
                    "status": "pass" if feedback_clean else "blocked" if feedback_blocked else "required",
                    "evidence": manual_execution_feedback_status,
                    "order_placement_allowed": False,
                },
            ],
            "operator_rule": {
                "plain_answer": (
                    "盈利系统不是每天追排行榜前三，而是每天只复用已准入的 CN_ETF 因子，"
                    "生成当日目标、扣除成本容量、完成同参数模拟盘和盘后反馈后，"
                    "才允许进入人工观察材料阶段。"
                ),
                "can_buy_today": False,
                "external_human_manual_only": True,
                "broker_connection_allowed": False,
                "order_placement_allowed": False,
            },
        }
    )


def _runtime_contract_layer(
    layer_id: str,
    label: str,
    status: str,
    evidence: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "required_before_manual_observation": True,
        "manual_required": True,
        "automation_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _runtime_profitability_control(control_id: str, gate: dict[str, Any] | None) -> dict[str, Any]:
    gate = gate if isinstance(gate, dict) else {}
    return {
        "control_id": control_id,
        "status": str(gate.get("status") or "required"),
        "evidence": gate.get("evidence") or gate.get("plain_check") or gate.get("reason") or "",
        "observed_count": gate.get("observed_count"),
        "minimum_required_observations": gate.get("minimum_required_observations"),
        "order_placement_allowed": False,
    }


def build_daily_manual_observation_packet(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    pre_execution = (
        pack.get("daily_pre_execution_guard")
        if isinstance(pack.get("daily_pre_execution_guard"), dict)
        else build_daily_pre_execution_guard(pack)
    )
    same_paper = (
        pack.get("daily_same_parameter_paper_rehearsal")
        if isinstance(pack.get("daily_same_parameter_paper_rehearsal"), dict)
        else build_daily_same_parameter_paper_rehearsal(pack)
    )
    profitability = (
        pack.get("live_profitability_readiness")
        if isinstance(pack.get("live_profitability_readiness"), dict)
        else build_live_profitability_readiness_scorecard(pack)
    )
    live_system = (
        pack.get("daily_live_trading_system_status")
        if isinstance(pack.get("daily_live_trading_system_status"), dict)
        else build_daily_live_trading_system_status(pack)
    )
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    combined_targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    pre_summary = pre_execution.get("summary") if isinstance(pre_execution.get("summary"), dict) else {}
    paper_summary = same_paper.get("summary") if isinstance(same_paper.get("summary"), dict) else {}
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    live_summary = live_system.get("summary") if isinstance(live_system.get("summary"), dict) else {}
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(combined_targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    paper_allowed = bool(paper_summary.get("paper_rehearsal_allowed")) or bool(pre_summary.get("paper_rehearsal_allowed"))
    manual_review_allowed = bool(paper_summary.get("manual_broker_review_allowed")) or bool(
        pre_summary.get("manual_broker_review_allowed")
    )
    small_capital_ready = bool(profitability_summary.get("small_capital_observation_candidate")) or bool(
        profitability_summary.get("production_manual_review_candidate")
    )

    if market != "CN_ETF":
        packet_status = "blocked_wrong_market"
    elif blockers:
        packet_status = "blocked_pretrade_red_light"
    elif selected_count <= 0 or signal_count <= 0 or target_count <= 0:
        packet_status = "waiting_for_today_signal"
    elif ticket_count <= 0:
        packet_status = "waiting_for_manual_tickets"
    elif not paper_allowed or not manual_review_allowed:
        packet_status = "paper_rehearsal_required"
    else:
        packet_status = "manual_observation_material_ready"

    next_step_id = str(live_summary.get("next_step_id") or _manual_observation_next_step(packet_status))
    next_target_id = str(live_summary.get("next_target_id") or _manual_observation_next_target(packet_status))
    next_workflow_id = str(live_summary.get("next_workflow_id") or _manual_observation_next_workflow(packet_status))

    def evidence_row(
        gate_id: str,
        label: str,
        status: str,
        evidence: str,
        target_id: str,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        return {
            "gate_id": gate_id,
            "label": label,
            "status": status,
            "evidence": evidence,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "required_before_manual_observation": status != "locked",
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }

    evidence_rows = [
        evidence_row(
            "cn_etf_scope",
            "CN_ETF primary scope",
            "pass" if market == "CN_ETF" else "blocked",
            f"market={market}",
            "factor-leaderboard-table",
        ),
        evidence_row(
            "today_top3_signal",
            "Today Top3 signal",
            "pass" if signal_count > 0 and target_count > 0 else "blocked",
            f"selected={selected_count}; signals={signal_count}; targets={target_count}",
            "daily-trade-decision-top3",
            "daily_trade_advisory" if signal_count <= 0 else "",
        ),
        evidence_row(
            "pretrade_red_light",
            "Pretrade red-light gate",
            "pass" if not blockers else "blocked",
            "blockers=" + (",".join(blockers) if blockers else "0"),
            "daily-pretrade-readiness-verdict",
        ),
        evidence_row(
            "manual_ticket_pack",
            "Manual ticket packet",
            "pass" if ticket_count > 0 else "blocked",
            f"manual_tickets={ticket_count}",
            "daily-manual-broker-handoff-ticket-table",
        ),
        evidence_row(
            "same_parameter_paper",
            "Same-parameter paper rehearsal",
            "pass" if manual_review_allowed else "required" if paper_allowed else "blocked",
            f"rehearsal_status={paper_summary.get('rehearsal_status') or 'waiting'}",
            "paper-metrics",
            "paper_simulation" if paper_allowed and not manual_review_allowed else "",
        ),
        evidence_row(
            "profitability_evidence",
            "Profitability evidence",
            "pass" if small_capital_ready else "required",
            f"decision={profitability_summary.get('decision') or 'waiting'}",
            "daily-live-profitability-readiness",
        ),
        evidence_row(
            "research_only_boundary",
            "Research-only boundary",
            "locked",
            "broker_connection=false; account_read=false; order_placement=false; auto_order=false",
            "control-safety-boundary",
        ),
    ]
    passed_rows = sum(1 for row in evidence_rows if row.get("status") in {"pass", "locked"})
    required_rows = len(evidence_rows)
    ticket_source = handoff.get("copyable_tickets") if isinstance(handoff.get("copyable_tickets"), list) else manual_plan
    return _sanitize(
        {
            "stage": DAILY_MANUAL_OBSERVATION_PACKET_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "summary": {
                "packet_status": packet_status,
                "primary_market": market,
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "same_parameter_paper_status": paper_summary.get("rehearsal_status"),
                "pre_execution_guard_status": pre_summary.get("guard_status"),
                "profitability_decision": profitability_summary.get("decision"),
                "evidence_score_pct": int(round(passed_rows / max(required_rows, 1) * 100)),
                "passed_evidence_count": passed_rows,
                "required_evidence_count": required_rows,
                "manual_observation_material_ready": packet_status == "manual_observation_material_ready",
                "small_capital_observation_candidate": small_capital_ready,
                "next_step_id": next_step_id,
                "next_target_id": next_target_id,
                "next_workflow_id": next_workflow_id,
                "can_buy_today": False,
                "direct_buy_top3_allowed": False,
                "manual_review_required": True,
                "paper_simulation_required": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "live_trading_allowed": False,
            },
            "top3_factor_snapshot": [_manual_observation_factor_snapshot(row, index) for index, row in enumerate(factors[:3], 1)],
            "same_parameter_paper_requests": [
                _manual_observation_paper_request(row, index)
                for index, row in enumerate(same_paper.get("recommended_requests", [])[:3], 1)
                if isinstance(row, dict)
            ],
            "manual_ticket_preview": [
                _manual_observation_ticket_preview(row, index)
                for index, row in enumerate(ticket_source[:10], 1)
                if isinstance(row, dict)
            ],
            "evidence_rows": evidence_rows,
            "operator_steps": [
                _manual_observation_step(
                    1,
                    "review_top3_signal",
                    "Review today's Top3 CN_ETF signal",
                    "done" if signal_count > 0 else "required",
                    "daily-trade-decision-top3",
                    "daily_trade_advisory" if signal_count <= 0 else "",
                ),
                _manual_observation_step(
                    2,
                    "run_same_parameter_paper",
                    "Run the locked same-parameter paper rehearsal",
                    "required" if paper_allowed and not manual_review_allowed else "done" if manual_review_allowed else "locked",
                    "paper-metrics",
                    "paper_simulation" if paper_allowed and not manual_review_allowed else "",
                ),
                _manual_observation_step(
                    3,
                    "review_manual_tickets",
                    "Review manual tickets and risk budget",
                    "manual_review_only" if ticket_count > 0 and not blockers else "blocked",
                    "daily-manual-broker-handoff-ticket-table",
                ),
                _manual_observation_step(
                    4,
                    "human_external_broker_decision",
                    "Human may decide outside this system; software cannot place orders",
                    "manual_locked",
                    "control-safety-boundary",
                ),
                _manual_observation_step(
                    5,
                    "post_close_journal",
                    "Record post-close journal and execution feedback",
                    "required",
                    "beginner-post-close-journal-board",
                    "post_close_journal",
                ),
            ],
            "forbidden_actions": [
                "direct_buy_top3",
                "auto_broker_connection",
                "account_read",
                "order_routing",
                "reuse_stale_signal",
                "skip_same_parameter_paper",
            ],
            "source_status": {
                "live_trading_system_state": live_summary.get("go_live_state"),
                "pretrade_blockers": blockers,
                "manual_handoff_status": handoff.get("status"),
            },
            "safety": SAFETY_NOTICE,
        }
    )


def _manual_observation_next_step(packet_status: str) -> str:
    return {
        "blocked_wrong_market": "confirm_cn_etf_scope",
        "blocked_pretrade_red_light": "clear_pretrade_blockers",
        "waiting_for_today_signal": "generate_today_signals",
        "waiting_for_manual_tickets": "build_manual_tickets",
        "paper_rehearsal_required": "run_same_parameter_paper",
        "manual_observation_material_ready": "manual_broker_review",
    }.get(packet_status, "review_manual_observation_packet")


def _manual_observation_next_target(packet_status: str) -> str:
    return {
        "blocked_wrong_market": "factor-leaderboard-table",
        "blocked_pretrade_red_light": "daily-pretrade-readiness-verdict",
        "waiting_for_today_signal": "daily-trade-decision-top3",
        "waiting_for_manual_tickets": "daily-manual-broker-handoff-ticket-table",
        "paper_rehearsal_required": "paper-metrics",
        "manual_observation_material_ready": "daily-manual-broker-handoff-ticket-table",
    }.get(packet_status, "daily-manual-observation-packet")


def _manual_observation_next_workflow(packet_status: str) -> str:
    return {
        "waiting_for_today_signal": "daily_trade_advisory",
        "paper_rehearsal_required": "paper_simulation",
    }.get(packet_status, "")


def _manual_observation_factor_snapshot(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "rank": _int(row.get("rank"), index),
        "case_id": str(row.get("case_id") or ""),
        "factor_name": str(row.get("factor_name") or ""),
        "market": str(row.get("market") or "CN_ETF"),
        "promotion_label": str(row.get("promotion_label") or ""),
        "advisory_eligible": bool(row.get("advisory_eligible")),
        "fallback_baseline": bool(row.get("fallback_baseline")),
        "direct_buy_allowed": False,
        "order_placement_allowed": False,
    }


def _manual_observation_paper_request(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "rank": index,
        "request_id": str(row.get("request_id") or row.get("same_parameter_request_id") or ""),
        "same_parameter_request_id": str(row.get("same_parameter_request_id") or row.get("request_id") or ""),
        "same_parameter_lock_id": str(row.get("same_parameter_lock_id") or ""),
        "factor": str(row.get("factor") or row.get("factor_name") or ""),
        "top_n": _int(row.get("top_n"), 0),
        "request_url": str(row.get("request_url") or ""),
        "status": "paper_rehearsal_request",
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _manual_observation_ticket_preview(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "step_number": _int(row.get("step_number"), index),
        "ticket_id": str(row.get("ticket_id") or ""),
        "asset_id": str(row.get("asset_id") or ""),
        "market": str(row.get("market") or "CN_ETF"),
        "side": str(row.get("side") or "review"),
        "target_weight": _float_or_none(row.get("target_weight")),
        "reference_price": _float_or_none(row.get("reference_price")),
        "rounded_quantity": _int(row.get("rounded_quantity"), 0),
        "rounded_value": _float_or_none(row.get("rounded_value")),
        "source_factors": row.get("source_factors") if isinstance(row.get("source_factors"), list) else [],
        "review_only": True,
        "order_placement_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
    }


def _manual_observation_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "manual_required": True,
        "automation_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def build_daily_operator_mission_control(pack: dict[str, Any]) -> dict[str, Any]:
    decision_sheet = (
        pack.get("daily_trade_decision_sheet")
        if isinstance(pack.get("daily_trade_decision_sheet"), dict)
        else build_daily_trade_decision_sheet(pack)
    )
    sheet_summary = decision_sheet.get("summary") if isinstance(decision_sheet.get("summary"), dict) else {}
    recipe = (
        decision_sheet.get("beginner_operation_recipe")
        if isinstance(decision_sheet.get("beginner_operation_recipe"), dict)
        else {}
    )
    recipe_summary = recipe.get("summary") if isinstance(recipe.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    pre_execution_guard = (
        pack.get("daily_pre_execution_guard")
        if isinstance(pack.get("daily_pre_execution_guard"), dict)
        else build_daily_pre_execution_guard(pack)
    )
    pre_execution_summary = (
        pre_execution_guard.get("summary") if isinstance(pre_execution_guard.get("summary"), dict) else {}
    )
    pre_execution_rows = [
        row for row in pre_execution_guard.get("row_guardrails", []) if isinstance(row, dict)
    ]
    pre_execution_by_asset = {
        str(row.get("asset_id") or ""): row
        for row in pre_execution_rows
        if str(row.get("asset_id") or "").strip()
    }
    factor_health = (
        pack.get("daily_factor_health_monitor")
        if isinstance(pack.get("daily_factor_health_monitor"), dict)
        else build_daily_factor_health_monitor(pack)
    )
    health_summary = factor_health.get("summary") if isinstance(factor_health.get("summary"), dict) else {}
    profitability = (
        pack.get("live_profitability_readiness")
        if isinstance(pack.get("live_profitability_readiness"), dict)
        else build_live_profitability_readiness_scorecard(pack)
    )
    profitability_summary = (
        profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    )
    live_system = (
        pack.get("daily_live_trading_system_status")
        if isinstance(pack.get("daily_live_trading_system_status"), dict)
        else build_daily_live_trading_system_status(pack)
    )
    live_system_summary = live_system.get("summary") if isinstance(live_system.get("summary"), dict) else {}
    profitability_hard_gates = [
        row for row in profitability.get("hard_gates", []) if isinstance(row, dict)
    ]
    profitability_blocked_gate_count = sum(
        1 for row in profitability_hard_gates if str(row.get("status") or "") == "blocked"
    )
    profitability_required_gate_count = sum(
        1 for row in profitability_hard_gates if str(row.get("status") or "") == "required"
    )
    profitability_partial_gate_count = sum(
        1 for row in profitability_hard_gates if str(row.get("status") or "") == "partial"
    )
    daybook = (
        pack.get("daily_rehearsal_daybook")
        if isinstance(pack.get("daily_rehearsal_daybook"), dict)
        else build_daily_rehearsal_daybook(pack)
    )
    daybook_summary = daybook.get("summary") if isinstance(daybook.get("summary"), dict) else {}
    daybook_phases = [row for row in daybook.get("phases", []) if isinstance(row, dict)]
    current_phase_id = str(daybook_summary.get("current_phase_id") or "")
    current_phase = next(
        (row for row in daybook_phases if str(row.get("phase_id") or "") == current_phase_id),
        next((row for row in daybook_phases if str(row.get("status") or "") != "done"), {}),
    )
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    missing_evidence = [row for row in decision_sheet.get("missing_evidence", []) if isinstance(row, dict)]
    operator_inputs = [row for row in recipe.get("operator_inputs_required", []) if isinstance(row, dict)]
    tickets = [row for row in recipe.get("ticket_preview", []) if isinstance(row, dict)]
    top3_count = _int(recipe_summary.get("top3_count"), _int(sheet_summary.get("selected_factor_count"), 0))
    signal_count = _int(sheet_summary.get("signal_count"), 0)
    target_count = _int(sheet_summary.get("target_count"), 0)
    ticket_count = _int(recipe_summary.get("ticket_preview_count"), _int(sheet_summary.get("manual_ticket_count"), len(tickets)))
    missing_count = _int(recipe_summary.get("missing_evidence_count"), len(missing_evidence))
    input_ready_count = _int(recipe_summary.get("operator_input_ready_count"), _count_status(operator_inputs, "ready"))
    input_manual_count = _int(recipe_summary.get("operator_input_manual_count"), _count_status(operator_inputs, "manual_required"))
    input_missing_count = _int(recipe_summary.get("operator_input_missing_count"), _count_status(operator_inputs, "missing"))
    input_blocked_count = _count_status(operator_inputs, "blocked")
    capacity_blocked_count = sum(1 for row in pre_execution_rows if bool(row.get("capacity_blocked")))
    liquidity_evidence_missing_count = sum(1 for row in pre_execution_rows if bool(row.get("liquidity_evidence_missing")))
    manual_clean_count = _int(health_summary.get("manual_execution_clean_receipts"), 0)
    manual_blocked_count = _int(health_summary.get("manual_execution_blocked_receipts"), 0)
    manual_missing_review_count = _int(health_summary.get("manual_execution_missing_review_receipts"), 0)
    next_session_quarantine_required = bool(health_summary.get("next_session_quarantine_required"))
    next_session_reuse_status = str(health_summary.get("next_session_reuse_status") or "waiting_for_top3_candidates")
    execution_feedback_status = _operator_execution_feedback_status(
        manual_blocked_count=manual_blocked_count,
        manual_missing_review_count=manual_missing_review_count,
        manual_clean_count=manual_clean_count,
    )
    primary_next_step_id = str(recipe_summary.get("primary_next_step_id") or _operator_primary_step(sheet_summary))
    mission_status = _operator_mission_status(
        decision=str(sheet_summary.get("decision") or ""),
        primary_next_step_id=primary_next_step_id,
        blockers=blockers,
        ticket_count=ticket_count,
        input_missing_count=input_missing_count,
        input_blocked_count=input_blocked_count,
        execution_feedback_status=execution_feedback_status,
    )
    next_actions = _operator_mission_next_actions(
        recipe_summary=recipe_summary,
        primary_next_step_id=primary_next_step_id,
        input_manual_count=input_manual_count,
        input_missing_count=input_missing_count,
        ticket_count=ticket_count,
        execution_feedback_status=execution_feedback_status,
        next_session_quarantine_required=next_session_quarantine_required,
    )
    cards = _operator_mission_cards(
        top3_count=top3_count,
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        missing_evidence=missing_evidence,
        input_manual_count=input_manual_count,
        input_missing_count=input_missing_count,
        input_blocked_count=input_blocked_count,
        blockers=blockers,
        pre_execution_summary=pre_execution_summary,
        capacity_blocked_count=capacity_blocked_count,
        liquidity_evidence_missing_count=liquidity_evidence_missing_count,
        execution_feedback_status=execution_feedback_status,
        next_session_quarantine_required=next_session_quarantine_required,
        next_session_reuse_status=next_session_reuse_status,
        manual_clean_count=manual_clean_count,
        manual_blocked_count=manual_blocked_count,
        manual_missing_review_count=manual_missing_review_count,
        current_phase=current_phase,
        phase_done_count=_int(daybook_summary.get("done_count"), 0),
        phase_blocked_count=_int(daybook_summary.get("blocked_count"), 0),
        phase_count=_int(daybook_summary.get("phase_count"), len(daybook_phases)),
        profitability_decision=str(profitability_summary.get("decision") or ""),
        profitability_score_pct=_int(profitability_summary.get("readiness_score_pct"), 0),
        profitability_next_target_id=str(
            profitability_summary.get("next_target_id") or "beginner-live-handoff-board"
        ),
        profitability_next_workflow_id=str(
            profitability_summary.get("next_workflow_id") or ""
        ),
        profitability_blocked_gate_count=profitability_blocked_gate_count,
        profitability_required_gate_count=profitability_required_gate_count,
        profitability_partial_gate_count=profitability_partial_gate_count,
        small_capital_observation_candidate=bool(
            profitability_summary.get("small_capital_observation_candidate")
        ),
        production_manual_review_candidate=bool(
            profitability_summary.get("production_manual_review_candidate")
        ),
    )
    cards.insert(2, _operator_live_system_card(live_system))
    return _sanitize(
        {
            "stage": DAILY_OPERATOR_MISSION_CONTROL_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "summary": {
                "mission_status": mission_status,
                "decision": sheet_summary.get("decision"),
                "primary_next_step_id": primary_next_step_id,
                "primary_next_label": recipe_summary.get("next_label") or sheet_summary.get("plain_answer"),
                "current_phase_id": current_phase.get("phase_id") or current_phase_id,
                "current_phase_title": current_phase.get("title") or daybook_summary.get("current_phase_title"),
                "current_phase_status": current_phase.get("status") or "waiting",
                "current_phase_target_id": current_phase.get("gui_target") or "",
                "phase_done_count": _int(daybook_summary.get("done_count"), 0),
                "phase_blocked_count": _int(daybook_summary.get("blocked_count"), 0),
                "phase_count": _int(daybook_summary.get("phase_count"), len(daybook_phases)),
                "top3_count": top3_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "missing_evidence_count": missing_count,
                "operator_input_count": len(operator_inputs),
                "operator_input_ready_count": input_ready_count,
                "operator_input_manual_count": input_manual_count,
                "operator_input_missing_count": input_missing_count,
                "operator_input_blocked_count": input_blocked_count,
                "blocker_count": len(blockers),
                "pre_execution_guard_status": pre_execution_summary.get("guard_status"),
                "capacity_blocked_count": capacity_blocked_count,
                "liquidity_evidence_missing_count": liquidity_evidence_missing_count,
                "max_participation_rate": pre_execution_summary.get("max_participation_rate"),
                "paper_rehearsal_allowed": bool(pre_execution_summary.get("paper_rehearsal_allowed")),
                "manual_broker_review_allowed": bool(pre_execution_summary.get("manual_broker_review_allowed")),
                "execution_feedback_status": execution_feedback_status,
                "next_session_quarantine_required": next_session_quarantine_required,
                "next_session_reuse_status": next_session_reuse_status,
                "manual_execution_clean_receipts": manual_clean_count,
                "manual_execution_blocked_receipts": manual_blocked_count,
                "manual_execution_missing_review_receipts": manual_missing_review_count,
                "profitability_readiness_decision": profitability_summary.get("decision"),
                "profitability_readiness_score_pct": _int(
                    profitability_summary.get("readiness_score_pct"), 0
                ),
                "profitability_next_target_id": profitability_summary.get("next_target_id"),
                "profitability_next_workflow_id": profitability_summary.get("next_workflow_id"),
                "profitability_passed_gate_count": _int(
                    profitability_summary.get("passed_gate_count"), 0
                ),
                "profitability_total_gate_count": _int(
                    profitability_summary.get("total_gate_count"), len(profitability_hard_gates)
                ),
                "profitability_blocked_gate_count": profitability_blocked_gate_count,
                "profitability_required_gate_count": profitability_required_gate_count,
                "profitability_partial_gate_count": profitability_partial_gate_count,
                "small_capital_observation_candidate": bool(
                    profitability_summary.get("small_capital_observation_candidate")
                ),
                "production_manual_review_candidate": bool(
                    profitability_summary.get("production_manual_review_candidate")
                ),
                "go_live_state": live_system_summary.get("go_live_state"),
                "daily_top3_policy": live_system_summary.get("daily_top3_policy"),
                "paper_simulation_required": True,
                "manual_review_required": True,
                "real_money_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "cards": cards,
            "live_trading_system_status": live_system,
            "next_actions": next_actions,
            "visible_ticket_summary": [
                _operator_mission_ticket_summary(
                    index,
                    ticket,
                    pre_execution_by_asset.get(str(ticket.get("asset_id") or "")),
                )
                for index, ticket in enumerate(tickets[:5], start=1)
            ],
            "blockers": blockers,
            "missing_evidence": missing_evidence,
            "safety": SAFETY_NOTICE,
        }
    )


def _operator_primary_step(sheet_summary: dict[str, Any]) -> str:
    decision = str(sheet_summary.get("decision") or "")
    if decision.startswith("blocked"):
        return "fix_blockers"
    if decision == "paper_first_manual_review":
        return "run_same_parameter_paper"
    if decision == "waiting_for_manual_tickets":
        return "build_manual_tickets"
    return "generate_today_signal"


def _operator_mission_status(
    *,
    decision: str,
    primary_next_step_id: str,
    blockers: list[str],
    ticket_count: int,
    input_missing_count: int,
    input_blocked_count: int,
    execution_feedback_status: str,
) -> str:
    if execution_feedback_status == "blocked_manual_execution_audit":
        return "blocked_execution_feedback"
    if decision.startswith("blocked") or blockers or input_blocked_count:
        return "blocked_pretrade_review_required"
    if primary_next_step_id == "run_same_parameter_paper":
        return "paper_rehearsal_required"
    if input_missing_count:
        return "operator_inputs_missing"
    if ticket_count > 0:
        return "manual_review_material_ready"
    return "waiting_for_today_signal"


def _operator_execution_feedback_status(
    *,
    manual_blocked_count: int,
    manual_missing_review_count: int,
    manual_clean_count: int,
) -> str:
    if manual_blocked_count > 0 or manual_missing_review_count > 0:
        return "blocked_manual_execution_audit"
    if manual_clean_count >= 5:
        return "clean_feedback_ready"
    return "waiting_for_execution_feedback"


def _operator_live_system_card(live_system: dict[str, Any]) -> dict[str, Any]:
    summary = live_system.get("summary") if isinstance(live_system.get("summary"), dict) else {}
    go_live_state = str(summary.get("go_live_state") or "waiting_for_top3_candidates")
    if go_live_state.startswith("blocked"):
        status = "blocked"
    elif "candidate" in go_live_state or "manual_review_material_ready" in go_live_state:
        status = "manual_required"
    elif "required" in go_live_state or "waiting" in go_live_state:
        status = "required"
    else:
        status = "waiting"
    return {
        "card_id": "live_trading_system_status",
        "label": "实盘落地总控",
        "status": status,
        "detail": (
            f"state={go_live_state}; top3_policy={summary.get('daily_top3_policy')}; "
            f"next={summary.get('next_step_id')}; order=false"
        ),
        "target_id": summary.get("next_target_id") or "daily-trade-decision-sheet",
        "workflow_id": summary.get("next_workflow_id") or "",
        "order_placement_allowed": False,
    }


def _operator_mission_cards(
    *,
    top3_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    missing_evidence: list[dict[str, Any]],
    input_manual_count: int,
    input_missing_count: int,
    input_blocked_count: int,
    blockers: list[str],
    pre_execution_summary: dict[str, Any],
    capacity_blocked_count: int,
    liquidity_evidence_missing_count: int,
    execution_feedback_status: str,
    next_session_quarantine_required: bool,
    next_session_reuse_status: str,
    manual_clean_count: int,
    manual_blocked_count: int,
    manual_missing_review_count: int,
    current_phase: dict[str, Any],
    phase_done_count: int,
    phase_blocked_count: int,
    phase_count: int,
    profitability_decision: str,
    profitability_score_pct: int,
    profitability_next_target_id: str,
    profitability_next_workflow_id: str,
    profitability_blocked_gate_count: int,
    profitability_required_gate_count: int,
    profitability_partial_gate_count: int,
    small_capital_observation_candidate: bool,
    production_manual_review_candidate: bool,
) -> list[dict[str, Any]]:
    missing_ids = {str(row.get("check_id") or "") for row in missing_evidence}
    red_blocked = bool(blockers) or input_blocked_count > 0
    current_phase = current_phase if isinstance(current_phase, dict) else {}
    current_phase_status = str(current_phase.get("status") or "waiting")
    current_phase_title = str(current_phase.get("title") or current_phase.get("phase_id") or "今日流程")
    current_phase_target = str(current_phase.get("gui_target") or "beginner-daily-rehearsal-board")
    profitability_status = (
        "blocked"
        if profitability_blocked_gate_count
        else "ready"
        if small_capital_observation_candidate or production_manual_review_candidate
        else "missing"
        if profitability_required_gate_count or profitability_partial_gate_count
        else "waiting"
    )

    def card(
        card_id: str,
        label: str,
        status: str,
        detail: str,
        target_id: str,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        return {
            "card_id": card_id,
            "label": label,
            "status": "blocked" if red_blocked and status not in {"ready", "locked"} else status,
            "detail": detail,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "order_placement_allowed": False,
        }

    return [
        card(
            "daily_phase_progress",
            "今日流程阶段",
            current_phase_status,
            (
                f"current={current_phase_title}; done={phase_done_count}; "
                f"blocked={phase_blocked_count}; total={phase_count}"
            ),
            current_phase_target,
        ),
        card(
            "profitability_evidence",
            "盈利证据",
            profitability_status,
            (
                f"decision={profitability_decision or '--'}; score={profitability_score_pct}; "
                f"blocked={profitability_blocked_gate_count}; "
                f"required={profitability_required_gate_count}; "
                f"partial={profitability_partial_gate_count}; "
                f"small_capital_candidate={small_capital_observation_candidate}; "
                f"production_candidate={production_manual_review_candidate}"
            ),
            profitability_next_target_id or "beginner-live-handoff-board",
            profitability_next_workflow_id,
        ),
        card(
            "today_top3_signal",
            "今日 Top3 信号",
            "ready" if top3_count > 0 and signal_count > 0 and target_count > 0 else "waiting",
            f"top3={top3_count}; signals={signal_count}; targets={target_count}",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not signal_count else "",
        ),
        card(
            "same_parameter_paper",
            "同参数模拟盘",
            "missing" if "paper_simulation_receipt" in missing_ids and ticket_count > 0 else "ready",
            "必须先用完全相同参数跑本地模拟盘，再看是否进入人工复核。",
            "paper-metrics",
            "paper_simulation" if ticket_count > 0 else "",
        ),
        card(
            "manual_broker_inputs",
            "人工输入",
            "blocked" if input_blocked_count else ("manual_required" if input_manual_count else "missing" if input_missing_count else "ready"),
            f"ready={input_manual_count == 0 and input_missing_count == 0}; manual={input_manual_count}; missing={input_missing_count}",
            "daily-beginner-operation-recipe-inputs",
        ),
        card(
            "manual_ticket_review",
            "人工票据",
            "manual_required" if ticket_count > 0 else "waiting",
            f"tickets={ticket_count}; review_only=true",
            "daily-manual-broker-handoff-ticket-table",
        ),
        card(
            "cost_capacity_guard",
            "成本容量闸门",
            "blocked" if capacity_blocked_count else ("missing" if liquidity_evidence_missing_count else "ready"),
            (
                f"guard={pre_execution_summary.get('guard_status') or '--'}; "
                f"capacity_blocked={capacity_blocked_count}; liquidity_missing={liquidity_evidence_missing_count}; "
                f"max_participation={pre_execution_summary.get('max_participation_rate')}"
            ),
            "daily-pre-execution-guard",
        ),
        card(
            "execution_feedback",
            "成交反馈",
            "blocked"
            if execution_feedback_status == "blocked_manual_execution_audit"
            else "missing"
            if next_session_quarantine_required
            else "ready"
            if execution_feedback_status == "clean_feedback_ready"
            else "waiting",
            (
                f"status={execution_feedback_status}; clean={manual_clean_count}; "
                f"blocked={manual_blocked_count}; missing_review={manual_missing_review_count}; "
                f"next_session={next_session_reuse_status}"
            ),
            "daily-factor-health-monitor",
            "post_close_journal" if execution_feedback_status == "blocked_manual_execution_audit" else "",
        ),
        card(
            "post_close_journal",
            "盘后复盘",
            "missing" if "post_close_journal_plan" in missing_ids else "waiting",
            "无论执行或跳过，都要记录结果和明日复核点。",
            "beginner-post-close-journal-board",
            "post_close_journal" if ticket_count > 0 else "",
        ),
        card(
            "live_safety_boundary",
            "实盘边界",
            "locked",
            "软件不连接券商、不读取账户、不自动下单；只能给人工复核材料。",
            "control-safety-boundary",
        ),
    ]


def _operator_mission_next_actions(
    *,
    recipe_summary: dict[str, Any],
    primary_next_step_id: str,
    input_manual_count: int,
    input_missing_count: int,
    ticket_count: int,
    execution_feedback_status: str,
    next_session_quarantine_required: bool,
) -> list[dict[str, Any]]:
    rows = [
        {
            "action_id": primary_next_step_id,
            "label": recipe_summary.get("next_label") or primary_next_step_id,
            "status": "next",
            "plain_action": recipe_summary.get("plain_answer") or "先完成这一步，再进入下一道人工复核闸门。",
            "target_id": recipe_summary.get("next_target_id") or "daily-trade-decision-sheet",
            "workflow_id": recipe_summary.get("next_workflow_id") or "",
            "order_placement_allowed": False,
        }
    ]
    if execution_feedback_status == "blocked_manual_execution_audit":
        rows.insert(
            0,
            {
                "action_id": "review_execution_feedback",
                "label": "先复核成交反馈",
                "status": "blocked",
                "plain_action": "上一轮人工成交、滑点或缺回执没有清理前，不要把 Top3 直接复用于下一次人工复核。",
                "target_id": "daily-factor-health-monitor",
                "workflow_id": "post_close_journal",
                "order_placement_allowed": False,
            },
        )
    if input_manual_count or input_missing_count:
        rows.append(
            {
                "action_id": "complete_operator_inputs",
                "label": "补齐人工输入",
                "status": "manual_required",
                "plain_action": "人工核对券商实时价格、现金、脱敏持仓和模拟盘/复盘回执。",
                "target_id": "daily-beginner-operation-recipe-inputs",
                "workflow_id": "",
                "order_placement_allowed": False,
            }
        )
    if ticket_count:
        rows.append(
            {
                "action_id": "review_manual_tickets",
                "label": "复核人工票据",
                "status": "manual_required",
                "plain_action": "只把票据当作复核材料，不把软件输出直接复制成订单。",
                "target_id": "daily-manual-broker-handoff-ticket-table",
                "workflow_id": "",
                "order_placement_allowed": False,
            }
        )
    return rows


def _operator_mission_ticket_summary(
    index: int,
    ticket: dict[str, Any],
    guardrail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guardrail = guardrail if isinstance(guardrail, dict) else {}
    return {
        "step_number": _int(ticket.get("step_number"), index),
        "ticket_id": str(ticket.get("ticket_id") or f"daily-ticket-{index:03d}"),
        "asset_id": str(ticket.get("asset_id") or ""),
        "market": str(ticket.get("market") or "CN_ETF"),
        "side": str(ticket.get("side") or "review"),
        "target_weight": _float_or_none(ticket.get("target_weight")),
        "reference_price": _float_or_none(ticket.get("reference_price") or ticket.get("latest_price")),
        "rounded_quantity": _int(ticket.get("rounded_quantity"), 0),
        "rounded_quantity_delta": _int(ticket.get("rounded_quantity_delta"), _int(ticket.get("rounded_quantity"), 0)),
        "liquidity_reference_value": _float_or_none(guardrail.get("liquidity_reference_value")),
        "liquidity_reference_field": guardrail.get("liquidity_reference_field"),
        "liquidity_evidence_missing": bool(guardrail.get("liquidity_evidence_missing")),
        "participation_rate": _float_or_none(guardrail.get("participation_rate")),
        "max_participation_rate": _float_or_none(guardrail.get("max_participation_rate")),
        "capacity_blocked": bool(guardrail.get("capacity_blocked")),
        "max_slippage_bps": _int(guardrail.get("max_slippage_bps"), MANUAL_MAX_SLIPPAGE_BPS),
        "max_estimated_slippage_cost": _float_or_none(guardrail.get("max_estimated_slippage_cost")),
        "copy_to_broker_allowed": False,
        "review_only": True,
        "order_placement_allowed": False,
    }


def build_daily_trading_system_blueprint(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    live_plan = pack.get("live_transition_plan") if isinstance(pack.get("live_transition_plan"), dict) else {}
    decision_sheet = pack.get("daily_trade_decision_sheet") if isinstance(pack.get("daily_trade_decision_sheet"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    tickets = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(tickets))
    signal_errors = [row for row in signal_cards if row.get("status") == "signal_error"]
    signal_ready = signal_count > 0 and target_count > 0 and not signal_errors
    manual_ticket_ready = ticket_count > 0 and not blockers
    if blockers:
        status = "blocked_red_light"
    elif manual_ticket_ready:
        status = "paper_first_manual_review"
    elif signal_ready:
        status = "build_manual_tickets"
    else:
        status = "waiting_for_today_signal"

    evidence_chain = [
        _trading_system_evidence(
            "startup_gate",
            "CN_ETF 主线闸门",
            "ready" if market == "CN_ETF" else "blocked",
            f"primary_market={market}",
            "control-startup-health",
        ),
        _trading_system_evidence(
            "factor_leaderboard_top3",
            "每日前三候选因子",
            "ready" if selected_count > 0 else "waiting",
            f"selected_factors={selected_count}; direct_buy_from_leaderboard=false",
            "daily-trade-factor-table",
        ),
        _trading_system_evidence(
            "today_signal_snapshot",
            "当日信号和目标仓位",
            "ready" if signal_ready else ("blocked" if blockers else "waiting"),
            f"signals={signal_count}; targets={target_count}; signal_errors={len(signal_errors)}",
            "daily-trade-target-table",
        ),
        _trading_system_evidence(
            "manual_ticket_pack",
            "人工复核票据",
            "ready" if manual_ticket_ready else ("blocked" if blockers else "waiting"),
            f"manual_tickets={ticket_count}; board_lot_size={BOARD_LOT_SIZE}",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _trading_system_evidence(
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            "required",
            "browser_local_receipt_required=true; no live conclusion without paper review",
            "paper-metrics",
            "paper_simulation",
        ),
        _trading_system_evidence(
            "post_close_journal",
            "盘后复盘反馈",
            "required",
            "record execute/skip reason, slippage, drawdown, and next-day review items",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        _trading_system_evidence(
            "small_capital_observation_gate",
            "小资金人工观察闸门",
            "locked",
            "requires promotion, observation sufficiency, paper evidence, and manual review",
            "beginner-live-handoff-board",
        ),
    ]
    operator_buy_process = [
        _trading_system_operator_step(
            1,
            "open_daily_command",
            "生成今日前三建议",
            "ready" if selected_count > 0 else "waiting",
            "先从 CN_ETF 可运行候选里取前三因子，不允许从历史排行榜直接买。",
            "run-daily-trade-advisory",
            "daily_trade_advisory",
        ),
        _trading_system_operator_step(
            2,
            "review_today_signal",
            "复核当日信号",
            "ready" if signal_ready else ("blocked" if blockers else "waiting"),
            "确认信号日期、目标 ETF、目标权重、参数和过拟合标签；无同日信号就停止。",
            "daily-trade-decision-top3",
        ),
        _trading_system_operator_step(
            3,
            "run_paper_simulation",
            "先跑同参数模拟盘",
            "required" if manual_ticket_ready else ("blocked" if blockers else "waiting"),
            "用相同因子、TopN、成本和仓位参数跑本地模拟盘，查看收益、回撤、成交和保护事件。",
            "paper-metrics",
            "paper_simulation",
        ),
        _trading_system_operator_step(
            4,
            "review_manual_tickets",
            "核对人工票据",
            "ready" if manual_ticket_ready else ("blocked" if blockers else "waiting"),
            "逐项核对 ETF、方向、参考价、目标金额、100 份取整、现金差额和来源因子。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _trading_system_operator_step(
            5,
            "manual_broker_review",
            "券商端只做人工复核",
            "manual_only",
            "如果你本人决定继续，只能另行打开券商端人工核对代码、实时价格、份额、现金和风险；系统不连接、不读取、不下单。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _trading_system_operator_step(
            6,
            "post_close_journal",
            "收盘后写回执",
            "required",
            "记录执行或跳过的原因，把真实演练反馈回到下一轮因子审计和流程优化。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]
    system_layers = [
        _trading_system_layer("research_layer", "因子研究层", "用长期样本、OOS、成本和闸门筛候选，不把短期排行榜当结论。"),
        _trading_system_layer("signal_layer", "每日信号层", "每天只把可运行 CN_ETF 候选转换成当日 ETF 目标仓位。"),
        _trading_system_layer("portfolio_layer", "组合约束层", "叠加总仓位、单 ETF 上限、现金下限、100 份取整和红灯阻断。"),
        _trading_system_layer("paper_layer", "模拟盘层", "同参数本地模拟盘先观察收益、回撤、成交和保护事件。"),
        _trading_system_layer("manual_review_layer", "人工复核层", "只输出人工复核票据，不接券商、不读账户、不自动下单。"),
        _trading_system_layer("feedback_layer", "盘后反馈层", "把执行、跳过、滑点和风险问题写回下一轮审计。"),
    ]
    return _sanitize(
        {
            "stage": DAILY_TRADING_SYSTEM_BLUEPRINT_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "status": status,
                "primary_market": market,
                "system_type": "daily_cn_etf_paper_first_manual_review_system",
                "daily_top3_signal_supported": market == "CN_ETF",
                "direct_live_trading_supported": False,
                "manual_execution_required": True,
                "paper_simulation_required": True,
                "post_close_journal_required": True,
                "selected_factor_count": selected_count,
                "today_signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "blocker_count": len(blockers),
                "live_transition_status": (live_plan.get("summary") or {}).get("status"),
                "decision_sheet_status": (decision_sheet.get("summary") or {}).get("decision"),
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "operator_summary": _trading_system_operator_summary(status),
            },
            "candidate_pool_policy": {
                "selection_scope": "CN_ETF",
                "top_factor_limit": 3,
                "source": "qualified_factor_leaderboard_then_signal_snapshot",
                "direct_buy_from_leaderboard_allowed": False,
                "cn_stock_moneyflow_primary_allowed": False,
                "required_metrics": [
                    "Sharpe",
                    "annualized_return",
                    "max_drawdown",
                    "win_rate",
                    "RankIC",
                    "trade_count",
                    "OOS/paper evidence",
                ],
                "anti_overfit_policy": "排行榜只能选候选，必须经过当日信号、模拟盘回执、风险和人工复核。",
            },
            "system_layers": system_layers,
            "evidence_chain": evidence_chain,
            "operator_buy_process": operator_buy_process,
            "risk_controls": [
                "只允许 CN_ETF 主线信号进入每日交易建议。",
                "没有同日信号、同参数模拟盘或人工票据时不进入人工券商复核。",
                "总收益和年化不能覆盖过拟合、回撤、容量、流动性和交易成本风险。",
                "真实交易只能由人离开系统后在券商端逐项人工决定。",
            ],
            "missing_for_manual_observation": [
                item["evidence_id"]
                for item in evidence_chain
                if item["status"] in {"blocked", "waiting", "required", "locked"}
            ],
        }
    )


def build_daily_signal_execution_bridge(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    decision_sheet = pack.get("daily_trade_decision_sheet") if isinstance(pack.get("daily_trade_decision_sheet"), dict) else {}
    decision_summary = decision_sheet.get("summary") if isinstance(decision_sheet.get("summary"), dict) else {}
    what_to_do_now = decision_sheet.get("what_to_do_now") if isinstance(decision_sheet.get("what_to_do_now"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    position_status = str(validation.get("status") or "not_provided")
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    has_top3 = market == "CN_ETF" and selected_count > 0
    has_signal_targets = signal_count > 0 and target_count > 0
    has_manual_tickets = ticket_count > 0 or bool(copyable_tickets)
    blocked = bool(blockers) or position_status == "error" or str(decision_summary.get("decision") or "").startswith("blocked")

    if position_status == "error":
        status = "blocked_current_position_input"
        next_label = "先修正当前持仓输入"
        next_target = "daily-current-positions"
        next_workflow = ""
    elif blockers:
        status = "blocked_pretrade_red_light"
        next_label = "先清理盘前红灯"
        next_target = "daily-pretrade-readiness-verdict"
        next_workflow = ""
    elif has_manual_tickets:
        status = "paper_first_manual_review_ready"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    elif has_signal_targets:
        status = "build_manual_ticket_pack"
        next_label = "先补齐人工票据"
        next_target = "daily-trade-target-table"
        next_workflow = "daily_trade_advisory"
    elif has_top3:
        status = "generate_today_signal"
        next_label = "生成今日前三信号"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"
    else:
        status = "waiting_for_candidate_pool"
        next_label = "先看 CN_ETF 候选榜"
        next_target = "factor-leaderboard-table"
        next_workflow = ""

    if what_to_do_now.get("button_label"):
        next_label = str(what_to_do_now.get("button_label"))
        next_target = str(what_to_do_now.get("target_id") or next_target)
        next_workflow = str(what_to_do_now.get("workflow_id") or next_workflow)

    signal_status = "blocked" if blocked else ("done" if has_signal_targets else ("required" if has_top3 else "waiting"))
    target_status = signal_status if not has_signal_targets else "done"
    ticket_status = "blocked" if blocked else ("done" if has_manual_tickets else ("required" if has_signal_targets else "waiting"))
    paper_status = "blocked" if blocked else ("required" if has_manual_tickets else "waiting")
    journal_status = "blocked" if blocked else ("required" if has_manual_tickets else "waiting")
    manual_status = "manual_only" if has_manual_tickets and not blocked else "manual_locked"

    daily_steps = [
        _signal_execution_step(
            1,
            "select_top3_candidates",
            "选择每日前三候选",
            "done" if has_top3 else ("blocked" if market != "CN_ETF" else "required"),
            "只从通过闸门的 CN_ETF 主线候选里取前三，不能从历史收益榜直接买。",
            f"market={market}; selected_factors={selected_count}",
            "factor-leaderboard-table",
        ),
        _signal_execution_step(
            2,
            "generate_today_signal",
            "生成当日信号",
            signal_status,
            "前三候选必须转成同日 ETF 目标仓位，旧信号、无目标或信号错误都停止。",
            f"signals={signal_count}; targets={target_count}; blockers={len(blockers)}",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets and not blocked else "",
        ),
        _signal_execution_step(
            3,
            "portfolio_sizing",
            "组合仓位约束",
            target_status,
            "套用风险档位、总仓位上限、单 ETF 上限、现金下限和 100 份取整。",
            f"risk_profile={summary.get('risk_profile_id')}; target_count={target_count}",
            "daily-trade-target-table",
        ),
        _signal_execution_step(
            4,
            "manual_ticket_pack",
            "生成人工复核票据",
            ticket_status,
            "把目标仓位和当前持仓差额转成可人工核对的买卖票据；票据不是订单。",
            f"manual_tickets={ticket_count}; copyable_tickets={len(copyable_tickets)}",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _signal_execution_step(
            5,
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            paper_status,
            "用同一组因子、TopN、成本、调仓和风控参数先跑本地模拟盘。",
            "paper_receipt_required=true",
            "paper-metrics",
            "paper_simulation" if has_manual_tickets and not blocked else "",
        ),
        _signal_execution_step(
            6,
            "manual_broker_review",
            "人工券商端复核",
            manual_status,
            "如果本人决定继续，只能另行打开券商端人工核对代码、实时价格、份额、现金和风险。",
            "system_order_permission=false",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _signal_execution_step(
            7,
            "post_close_journal",
            "收盘后写回执",
            journal_status,
            "记录执行或跳过、滑点、未成交、回撤和次日要复核的问题，反馈到下一轮审计。",
            "post_close_journal_required=true",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_manual_tickets and not blocked else "",
        ),
    ]

    deployment_gates = [
        _signal_execution_gate(
            "long_sample_oos_cost_gate",
            "长样本/OOS/成本闸门",
            "required",
            "候选因子必须长期样本、OOS、成本和参数敏感性不过拟合；高年化不能替代这道门。",
            "control-backtest-gate",
        ),
        _signal_execution_gate(
            "same_day_signal_gate",
            "同日信号闸门",
            "done" if has_signal_targets else ("blocked" if blocked else "required"),
            "只有同日 CN_ETF 信号和目标仓位才允许进入人工复核。",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets and not blocked else "",
        ),
        _signal_execution_gate(
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            "required" if has_manual_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "先看本地模拟盘收益、回撤、成交和保护事件，再谈人工复核。",
            "paper-metrics",
            "paper_simulation" if has_manual_tickets and not blocked else "",
        ),
        _signal_execution_gate(
            "risk_cash_review",
            "风险和现金复核",
            "required" if has_manual_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "确认总仓位、单 ETF 权重、现金余量、最大可承受回撤和实时流动性。",
            "daily-pretrade-readiness-verdict",
        ),
        _signal_execution_gate(
            "manual_broker_review",
            "人工券商端复核",
            "manual_locked",
            "系统不接券商、不读账户、不下单；真实操作只能由本人在券商端另行决定。",
            "daily-manual-broker-handoff-ticket-table",
        ),
    ]
    paper_simulation_handoff = _build_signal_execution_paper_handoff(
        factors=factors,
        market=market,
        portfolio_value=_float(summary.get("requested_portfolio_value"), _float(summary.get("portfolio_value"), 100000.0)),
        summary=summary,
    )

    return _sanitize(
        {
            "stage": DAILY_SIGNAL_EXECUTION_BRIDGE_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "status": status,
                "primary_market": market,
                "daily_top3_signal_supported": market == "CN_ETF",
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "blocker_count": len(blockers),
                "current_position_status": position_status,
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "live_deployment_mode": "paper_then_manual_small_capital_observation",
                "direct_buy_from_top3_allowed": False,
                "direct_live_trading_supported": False,
                "manual_execution_required": True,
                "paper_simulation_required": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "live_trading_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "candidate_to_signal_rules": [
                _signal_execution_rule("top3_is_candidate_pool", "前三因子只是候选池入口，不是买入指令。"),
                _signal_execution_rule("same_day_signal_required", "必须生成当日 CN_ETF 信号和目标仓位，旧信号不能用。"),
                _signal_execution_rule("oos_cost_capacity_required", "长样本/OOS/成本/容量不过关时，只能继续研究，不能推进人工复核。"),
                _signal_execution_rule("risk_profile_applied", "必须套用风险档位、仓位上限、现金下限和 100 份取整。"),
            ],
            "manual_order_rules": [
                _signal_execution_rule("target_minus_current", "人工票据来自目标仓位减当前持仓；没有当前持仓时只能按目标仓位估算。"),
                _signal_execution_rule("reference_price_not_order_price", "参考价不是券商端实时成交价，最终价格必须人工核对。"),
                _signal_execution_rule("copy_text_not_order", "可复制文本只是复核材料，不是委托单。"),
                _signal_execution_rule("post_close_feedback_required", "无论执行或跳过，都要写盘后回执反馈到下一轮审计。"),
            ],
            "paper_simulation_handoff": paper_simulation_handoff,
            "deployment_gates": deployment_gates,
            "daily_operating_steps": daily_steps,
        }
    )


def build_real_world_manual_handoff_gate(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    decision_sheet = pack.get("daily_trade_decision_sheet") if isinstance(pack.get("daily_trade_decision_sheet"), dict) else {}
    bridge = pack.get("daily_signal_execution_bridge") if isinstance(pack.get("daily_signal_execution_bridge"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    position_status = str(validation.get("status") or "not_provided")
    risk_profile_id = str(summary.get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID)
    risk_profile = _risk_profile_by_id(risk_profile_id) or _risk_profile_by_id(DEFAULT_RISK_PROFILE_ID) or {}
    paper_handoff = bridge.get("paper_simulation_handoff") if isinstance(bridge.get("paper_simulation_handoff"), dict) else {}
    paper_request = paper_handoff.get("recommended_request") if isinstance(paper_handoff.get("recommended_request"), dict) else {}

    if position_status == "error":
        decision = "blocked_current_position_input"
        plain_answer = "不能进入人工观察：当前持仓输入有危险字段或格式错误。"
        next_label = "先修正当前持仓"
        next_target = "daily-current-positions"
        next_workflow = ""
    elif blockers:
        decision = "blocked_pretrade_red_light"
        plain_answer = "不能进入人工观察：盘前红灯还没清掉。"
        next_label = "查看盘前红灯"
        next_target = "daily-pretrade-readiness-verdict"
        next_workflow = ""
    elif ticket_count > 0:
        decision = "paper_first_manual_review_candidate"
        plain_answer = "可以准备人工观察材料：先跑同参数模拟盘，再逐项核对票据。"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    elif signal_count > 0 and target_count > 0:
        decision = "build_manual_ticket_pack_first"
        plain_answer = "已有今日信号，但还没有人工票据；先补齐仓位和一手取整。"
        next_label = "补齐人工票据"
        next_target = "daily-trade-target-table"
        next_workflow = "daily_trade_advisory"
    elif selected_count > 0:
        decision = "generate_today_signal_first"
        plain_answer = "已有前三候选，但没有当日信号；先生成今日 CN_ETF 目标仓位。"
        next_label = "生成今日前三信号"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"
    else:
        decision = "waiting_for_cn_etf_candidate_pool"
        plain_answer = "还没有 CN_ETF 候选池；先回到因子排行榜和候选生成。"
        next_label = "查看候选榜"
        next_target = "factor-leaderboard-table"
        next_workflow = ""

    capital_ladder = _real_world_capital_deployment_ladder(
        selected_count=selected_count,
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        blockers=blockers,
    )
    ticket_source = [] if handoff.get("copyable_tickets_masked_until_same_parameter_paper") else copyable_tickets or manual_plan
    manual_ticket_preview = [_real_world_ticket_preview(row, index) for index, row in enumerate(ticket_source[:10], start=1)]
    runbook = [
        _real_world_runbook_step(
            1,
            "generate_daily_top3_signal",
            "生成每日前三因子和当日信号",
            "done" if signal_count > 0 and target_count > 0 else ("blocked" if blockers else "required"),
            "每天只从 CN_ETF 可运行候选里取前三，再生成当日目标 ETF 和权重；排行榜本身不能直接买。",
            f"selected={selected_count}; signals={signal_count}; targets={target_count}",
            "daily-trade-factor-table",
            "daily_trade_advisory" if signal_count == 0 and not blockers else "",
        ),
        _real_world_runbook_step(
            2,
            "run_pretrade_checkup",
            "开盘前一键体检",
            "blocked" if blockers else "required",
            "检查数据日期、红黄灯、当前持仓输入、今日信号、价格和人工票据是否完整。",
            f"traffic_light={readiness.get('traffic_light') or 'unknown'}; blockers={len(blockers)}",
            "daily-pretrade-readiness-verdict",
            "daily_pretrade_checkup" if not blockers else "",
        ),
        _real_world_runbook_step(
            3,
            "run_same_parameter_paper",
            "同参数模拟盘复核",
            "required" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            "用同一组因子、窗口、TopN、成本、调仓间隔和风险档位跑本地模拟盘。",
            _paper_request_summary(paper_request),
            "paper-metrics",
            "paper_simulation" if ticket_count > 0 and not blockers else "",
        ),
        _real_world_runbook_step(
            4,
            "review_manual_tickets",
            "核对人工票据",
            "manual_review_only" if ticket_count > 0 and not blockers else ("blocked" if blockers else "waiting"),
            "逐项核对 ETF 代码、方向、参考价、数量、金额、现金差额、来源因子和风险预算。",
            f"manual_tickets={ticket_count}; copyable_tickets={len(copyable_tickets)}",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _real_world_runbook_step(
            5,
            "human_broker_manual_decision",
            "本人券商端手工决定",
            "manual_locked",
            "如果本人仍决定真实操作，只能离开系统到券商端人工输入；软件不会下单，也不会读取账户。",
            "broker_connection=false; account_read=false; order_placement=false",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _real_world_runbook_step(
            6,
            "post_close_journal",
            "收盘后写复盘回执",
            "required" if signal_count > 0 else "waiting",
            "记录执行、跳过、滑点、未成交、回撤、保护事件和次日复核事项，反馈给下一轮因子审计。",
            "post_close_journal_required=true",
            "beginner-post-close-journal-board",
            "post_close_journal" if signal_count > 0 and not blockers else "",
        ),
    ]
    go_live_blockers = [
        _real_world_gate(
            "candidate_quality_gate",
            "候选因子质量闸门",
            "required",
            "前三因子必须有长样本、OOS、成本、容量、回撤和参数敏感性证据；不能只看总收益。",
            "daily-trading-system-blueprint",
        ),
        _real_world_gate(
            "same_day_signal_gate",
            "同日信号闸门",
            "pass" if signal_count > 0 and target_count > 0 and not blockers else "blocked",
            "必须有当天 CN_ETF 信号和目标仓位，旧信号或信号错误必须停止。",
            "daily-trade-factor-table",
            "daily_trade_advisory" if signal_count == 0 and not blockers else "",
        ),
        _real_world_gate(
            "manual_ticket_gate",
            "人工票据闸门",
            "pass" if ticket_count > 0 and not blockers else "blocked",
            "必须形成可人工核对票据，且票据只能用于复核，不能当委托单。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _real_world_gate(
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            "required" if ticket_count > 0 and not blockers else "waiting",
            "真实操作前先看同参数模拟盘收益、回撤、胜率、成交和保护事件。",
            "paper-metrics",
            "paper_simulation" if ticket_count > 0 and not blockers else "",
        ),
        _real_world_gate(
            "risk_cash_tradeability_review",
            "风险、现金和可交易性复核",
            "required" if ticket_count > 0 and not blockers else "waiting",
            "核对总仓位、单 ETF 上限、现金余量、实时价格、成交额、涨跌停和自己可承受回撤。",
            "daily-pretrade-readiness-verdict",
        ),
        _real_world_gate(
            "post_close_feedback_loop",
            "盘后反馈闭环",
            "required",
            "无论执行或跳过，都要写复盘回执，防止系统只会回测不会学习执行偏差。",
            "beginner-post-close-journal-board",
            "post_close_journal" if signal_count > 0 and not blockers else "",
        ),
    ]
    return _sanitize(
        {
            "stage": REAL_WORLD_MANUAL_HANDOFF_GATE_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "primary_market": market,
                "daily_top_factor_limit": 3,
                "selected_factor_count": selected_count,
                "today_signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "blocker_count": len(blockers),
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "manual_observation_candidate": decision == "paper_first_manual_review_candidate",
                "direct_buy_from_top3_allowed": False,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "daily_top3_signal_contract": {
                "contract_id": "top3_candidate_to_same_day_signal_not_order",
                "selection_scope": "CN_ETF",
                "candidate_limit": 3,
                "source": "qualified_factor_leaderboard_then_signal_snapshot",
                "required_daily_outputs": [
                    "top3_factor_candidates",
                    "same_day_signal_snapshot",
                    "combined_target_weights",
                    "manual_review_tickets",
                    "same_parameter_paper_request",
                ],
                "plain_warning": "前三因子只是候选入口；必须转成同日信号、目标仓位和人工票据后，才能进入模拟盘和人工复核。",
            },
            "risk_budget": {
                "risk_profile_id": risk_profile.get("profile_id") or risk_profile_id,
                "risk_profile_label": risk_profile.get("label") or summary.get("risk_profile_label"),
                "max_gross_exposure": summary.get("applied_max_gross_exposure"),
                "max_single_etf_weight": risk_profile.get("max_single_etf_weight"),
                "min_cash_weight": risk_profile.get("min_cash_weight"),
                "max_acceptable_drawdown": risk_profile.get("max_acceptable_drawdown"),
                "plain_budget": (
                    f"当前风险档位最多按约 {_format_percent_plain(risk_profile.get('max_acceptable_drawdown'))} 回撤承受度观察；"
                    "收益和年化不能替代回撤、现金、流动性和心理承受力复核。"
                ),
            },
            "manual_ticket_preview": manual_ticket_preview,
            "capital_deployment_ladder": capital_ladder,
            "paper_simulation_handoff": paper_handoff,
            "manual_operation_runbook": runbook,
            "go_live_blockers": go_live_blockers,
            "safety_boundaries": [
                _real_world_boundary(
                    "no_broker_connection",
                    "不连接券商",
                    "软件不能连接券商接口，也不能读取账户。",
                ),
                _real_world_boundary(
                    "no_account_read",
                    "不读取真实账户",
                    "当前持仓只能由用户手填或留空，不能从真实账户拉取。",
                ),
                _real_world_boundary(
                    "no_order_placement",
                    "不生成实盘委托",
                    "系统输出的是复核材料，不是可提交订单。",
                ),
                _real_world_boundary(
                    "manual_broker_manual_decision",
                    "券商端本人手工决定",
                    "如果进入真实交易，只能由本人离开系统后在券商端逐项人工确认。",
                ),
            ],
            "decision_sheet_summary": decision_sheet.get("summary") if isinstance(decision_sheet.get("summary"), dict) else {},
        }
    )


def build_daily_deployment_readiness_pack(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    bridge = pack.get("daily_signal_execution_bridge") if isinstance(pack.get("daily_signal_execution_bridge"), dict) else {}
    real_gate = pack.get("real_world_manual_handoff_gate") if isinstance(pack.get("real_world_manual_handoff_gate"), dict) else {}
    paper_handoff = bridge.get("paper_simulation_handoff") if isinstance(bridge.get("paper_simulation_handoff"), dict) else {}
    paper_request = paper_handoff.get("recommended_request") if isinstance(paper_handoff.get("recommended_request"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    position_status = str(validation.get("status") or "not_provided")
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    has_candidates = market == "CN_ETF" and selected_count > 0
    has_signal_targets = signal_count > 0 and target_count > 0
    has_manual_material = ticket_count > 0 or bool(copyable_tickets)
    position_blocked = position_status == "error"
    pretrade_blocked = bool(blockers)
    paper_rehearsal_allowed = has_signal_targets and not position_blocked and not pretrade_blocked
    manual_material_ready = has_manual_material and not position_blocked and not pretrade_blocked

    if position_blocked:
        decision = "blocked_current_position_input"
        plain_answer = "不能进入模拟盘或人工复核：当前持仓输入含账户、券商、订单字段或格式风险。"
        next_label = "先修正当前持仓"
        next_target = "daily-current-positions"
        next_workflow = ""
    elif pretrade_blocked:
        decision = "blocked_pretrade_red_light"
        plain_answer = "今天不能买：盘前红灯没有清理前，只能观察，不能进入人工券商复核。"
        next_label = "先看红灯阻断"
        next_target = "daily-pretrade-readiness-verdict"
        next_workflow = ""
    elif has_manual_material:
        decision = "paper_first_manual_review_candidate"
        plain_answer = "可以进入模拟盘复核和人工票据核对，但前三因子仍不是直接买入指令。"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    elif has_signal_targets:
        decision = "build_manual_ticket_pack_first"
        plain_answer = "已有同日信号和目标仓位，但还没有可复核的买卖票据；先补齐份额、金额和取整。"
        next_label = "补齐人工票据"
        next_target = "daily-trade-target-table"
        next_workflow = "daily_trade_advisory"
    elif has_candidates:
        decision = "generate_today_signal_first"
        plain_answer = "已有前三候选，但还没有同日目标 ETF 信号；先生成今日信号。"
        next_label = "生成今日信号"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"
    else:
        decision = "waiting_for_candidate_pool"
        plain_answer = "还没有合格 CN_ETF 候选池；先回到因子排行榜和推广闸门。"
        next_label = "查看 CN_ETF 排行榜"
        next_target = "factor-leaderboard-table"
        next_workflow = ""

    sequence = [
        _deployment_sequence_step(
            1,
            "qualified_top3_candidates",
            "选择每日前三候选",
            "done" if has_candidates else "required",
            "只从 CN_ETF 主线、可运行且未被推广闸门阻断的候选里选前三；不能从历史收益榜直接买。",
            f"market={market}; selected={selected_count}; fallback={bool(summary.get('fallback_signal_only'))}",
            "factor-leaderboard-table",
            "daily_trade_advisory" if not has_candidates else "",
        ),
        _deployment_sequence_step(
            2,
            "same_day_signal_snapshot",
            "生成同日信号和目标仓位",
            "done" if has_signal_targets else ("blocked" if pretrade_blocked else "required"),
            "前三候选必须转成运行日当天的 ETF、权重、参考价格和目标金额；旧信号不能复用。",
            f"signals={signal_count}; targets={target_count}; run_date={pack.get('run_date')}",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets and not pretrade_blocked else "",
        ),
        _deployment_sequence_step(
            3,
            "pretrade_red_light_gate",
            "盘前红灯闸门",
            "blocked" if position_blocked or pretrade_blocked else "done",
            "检查信号日期、兜底基线、当前持仓、价格、风险档位和安全边界；红灯未清理时不买。",
            ", ".join(blockers) if blockers else f"position_status={position_status}",
            "daily-pretrade-readiness-verdict",
        ),
        _deployment_sequence_step(
            4,
            "same_parameter_paper_rehearsal",
            "同参数模拟盘复核",
            "required" if manual_material_ready else ("blocked" if pretrade_blocked or position_blocked else "waiting"),
            "用同一组因子、TopN、成本、调仓间隔、资金规模和风险档位先跑本地模拟盘。",
            _paper_request_summary(paper_request),
            "paper-metrics",
            "paper_simulation" if manual_material_ready else "",
        ),
        _deployment_sequence_step(
            5,
            "manual_ticket_review",
            "人工买卖票据核对",
            "manual_review_only" if manual_material_ready else ("blocked" if pretrade_blocked or position_blocked else "waiting"),
            "只核对 ETF、方向、参考价、数量、金额、现金差额、来源因子和风险；票据不是订单。",
            f"manual_tickets={ticket_count}; copyable_tickets={len(copyable_tickets)}",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _deployment_sequence_step(
            6,
            "human_broker_decision",
            "本人券商端手工决定",
            "manual_locked",
            "如果本人仍决定真实操作，只能离开本系统在券商端逐项人工确认；系统不连接、不读取、不下单。",
            "broker_connection=false; account_read=false; order_placement=false",
            "control-safety-boundary",
        ),
        _deployment_sequence_step(
            7,
            "post_close_feedback",
            "收盘后反馈闭环",
            "required" if has_signal_targets else "waiting",
            "记录执行、跳过、滑点、未成交、回撤、保护事件和次日复核事项，反馈到下一轮因子审计。",
            "post_close_journal_required=true",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets and not position_blocked else "",
        ),
    ]

    readiness_gates = [
        _deployment_readiness_gate(
            "qualified_candidate_gate",
            "候选质量闸门",
            "pass" if has_candidates and not bool(summary.get("fallback_signal_only")) else "blocked",
            "前三候选必须来自合格 CN_ETF 候选池；兜底基线只能观察，不能出票。",
            "factor-leaderboard-table",
        ),
        _deployment_readiness_gate(
            "same_day_signal_gate",
            "同日信号闸门",
            "pass" if has_signal_targets and not pretrade_blocked else "blocked",
            "只有运行日当天的 CN_ETF 信号和目标仓位才允许进入下一步。",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets and not pretrade_blocked else "",
        ),
        _deployment_readiness_gate(
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            "required" if manual_material_ready else ("blocked" if pretrade_blocked or position_blocked else "waiting"),
            "真实买卖前先看同参数模拟盘收益、回撤、胜率、成交和保护事件。",
            "paper-metrics",
            "paper_simulation" if manual_material_ready else "",
        ),
        _deployment_readiness_gate(
            "manual_ticket_gate",
            "人工票据闸门",
            "pass" if manual_material_ready else ("blocked" if pretrade_blocked or position_blocked else "waiting"),
            "必须有可人工核对的买卖票据，且票据只能用于人工复核，不能作为委托单。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _deployment_readiness_gate(
            "small_capital_observation_history",
            "小资金人工观察样本",
            "required",
            "至少积累 5 次同参数模拟盘回执、5 次盘后复盘，且风险和红灯稳定后再讨论小资金人工观察。",
            "beginner-live-handoff-board",
        ),
        _deployment_readiness_gate(
            "research_only_safety_boundary",
            "系统权限边界",
            "pass",
            "系统保持无券商连接、无账户读取、无真实委托、无自动下单。",
            "control-safety-boundary",
        ),
    ]

    profitability_controls = [
        _deployment_profitability_control(
            "walk_forward_oos_gate",
            "长样本和样本外验证",
            "不能只看短期总收益；候选必须经过 walk-forward/OOS、成本后和稳定性复核。",
            "control-backtest-gate",
        ),
        _deployment_profitability_control(
            "lookahead_bias_audit",
            "未来函数审计",
            "信号使用收盘数据时，执行必须至少滞后一日；任何负向 shift、全样本归一化都要审计。",
            "daily-trading-system-blueprint",
        ),
        _deployment_profitability_control(
            "multiple_testing_control",
            "多重检验控制",
            "每天前三来自大量实验时，要按候选数、参数数和重复信号去重，不能只挑最好看的结果。",
            "factor-leaderboard-table",
        ),
        _deployment_profitability_control(
            "cost_capacity_model",
            "成本、滑点和容量",
            "买卖 ETF 前先看调仓频率、成交额、冲击成本、单 ETF 权重和现金约束。",
            "daily-pretrade-readiness-verdict",
        ),
        _deployment_profitability_control(
            "drawdown_budget",
            "回撤预算",
            f"当前风险档位最多按约 {_format_percent_plain(_risk_profile_by_id(str(summary.get('risk_profile_id') or DEFAULT_RISK_PROFILE_ID)).get('max_acceptable_drawdown') if _risk_profile_by_id(str(summary.get('risk_profile_id') or DEFAULT_RISK_PROFILE_ID)) else None)} 回撤承受度观察；年化高也不能绕过回撤。",
            "daily-live-readiness-gate",
        ),
        _deployment_profitability_control(
            "post_close_feedback_loop",
            "盘后执行反馈",
            "真实市场的滑点、未成交、情绪和跳过原因必须回写，否则系统只会回测，不会学习执行偏差。",
            "beginner-post-close-journal-board",
        ),
    ]

    ticket_source = [] if handoff.get("copyable_tickets_masked_until_same_parameter_paper") else copyable_tickets or manual_plan
    manual_preview = [_deployment_ticket_preview(row, index) for index, row in enumerate(ticket_source[:20], start=1)]

    return _sanitize(
        {
            "stage": DAILY_DEPLOYMENT_READINESS_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "primary_market": market,
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "blocker_count": len(blockers),
                "daily_top3_supported": market == "CN_ETF",
                "paper_rehearsal_allowed": paper_rehearsal_allowed,
                "manual_review_material_ready": manual_material_ready,
                "small_capital_observation_allowed": False,
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "direct_buy_from_top3_allowed": False,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "top3_rule": {
                "rule_id": "daily_top3_candidates_not_orders",
                "selection_scope": "CN_ETF",
                "candidate_limit": 3,
                "plain_rule": "可以每天选前三因子并生成当天信号；前三只是候选池入口，不是买入指令。",
                "ranking_inputs": [
                    "Sharpe",
                    "annualized_return",
                    "max_drawdown",
                    "win_rate",
                    "RankIC",
                    "trade_count",
                    "OOS/paper evidence",
                    "cost/capacity evidence",
                ],
                "direct_order_allowed": False,
            },
            "daily_operating_sequence": sequence,
            "readiness_gates": readiness_gates,
            "profitability_controls": profitability_controls,
            "manual_buy_sell_preview": manual_preview,
            "paper_simulation_request": paper_request,
            "real_world_gate_summary": real_gate.get("summary") if isinstance(real_gate.get("summary"), dict) else {},
        }
    )


def _live_profitability_capital_tier_summary(
    *,
    decision: str,
    hard_gates: list[dict[str, Any]],
    small_capital_observation_candidate: bool,
    production_manual_review_candidate: bool,
) -> dict[str, Any]:
    def missing(required_before: str) -> list[dict[str, Any]]:
        return [
            row
            for row in hard_gates
            if row.get("required_before") == required_before and str(row.get("status") or "") != "pass"
        ]

    small_missing = missing("small_capital_observation")
    production_missing = missing("production_manual_review")
    all_missing = [row for row in hard_gates if str(row.get("status") or "") != "pass"]

    if production_manual_review_candidate:
        capital_tier = "production_manual_review_candidate"
        next_capital_tier = "external_human_manual_review"
        missing_count = 0
        plain_answer = "已达到人工生产化复核候选；系统仍不分配真实资金、不连接券商、不读账户、不下单。"
    elif small_capital_observation_candidate:
        capital_tier = "small_capital_manual_observation_candidate"
        next_capital_tier = "production_manual_review"
        missing_count = len(production_missing)
        plain_answer = "已达到小资金人工观察候选；这里只生成复核材料，真实资金必须由本人离开系统后手工决定。"
    elif decision.startswith("blocked"):
        capital_tier = "blocked_or_research_only"
        next_capital_tier = "same_parameter_paper"
        missing_count = len(all_missing)
        plain_answer = "存在阻断项；只能先修复或继续研究，不能推进真实资金、券商连接或下单动作。"
    else:
        capital_tier = "paper_simulation_only"
        next_capital_tier = "small_capital_manual_observation"
        missing_count = len(small_missing)
        plain_answer = "当前只能做同参数模拟盘和人工复核；补齐缺失闸门后才进入小资金人工观察候选。"

    return {
        "capital_tier": capital_tier,
        "next_capital_tier": next_capital_tier,
        "capital_tier_missing_gate_count": missing_count,
        "capital_tier_real_money_limit": 0,
        "capital_tier_external_manual_only": True,
        "capital_tier_plain_answer": plain_answer,
        "next_capital_allowed": False,
        "real_money_capital_limit": 0,
        "capital_tier_order_placement_allowed": False,
        "capital_tier_broker_connection_allowed": False,
        "capital_tier_account_read_allowed": False,
        "capital_tier_auto_order_allowed": False,
    }


def build_live_profitability_readiness_scorecard(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    deployment = pack.get("daily_deployment_readiness") if isinstance(pack.get("daily_deployment_readiness"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    evidence = _live_profitability_evidence_snapshot(pack.get("live_profitability_evidence_snapshot"))
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    position_status = str(validation.get("status") or "not_provided")
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(manual_plan))
    fallback_signal_only = bool(summary.get("fallback_signal_only"))
    has_candidates = market == "CN_ETF" and selected_count > 0 and not fallback_signal_only
    has_signal_targets = signal_count > 0 and target_count > 0 and not fallback_signal_only
    position_blocked = position_status == "error"
    pretrade_clear = not blockers and not position_blocked
    has_manual_material = ticket_count > 0 and pretrade_clear
    paper_rehearsal_allowed = has_signal_targets and pretrade_clear
    manual_review_material_ready = has_manual_material
    evidence_counts = evidence.get("counts", {})
    evidence_flags = evidence.get("flags", {})
    matched_paper_count = _int(evidence_counts.get("matched_paper_receipts"), 0)
    post_close_count = _int(evidence_counts.get("post_close_journal_receipts"), 0)
    manual_execution_clean_count = _int(evidence_counts.get("manual_execution_clean_receipts"), 0)
    manual_execution_blocked_count = _int(evidence_counts.get("manual_execution_blocked_receipts"), 0)
    manual_execution_missing_count = _int(evidence_counts.get("manual_execution_missing_review_receipts"), 0)
    paper_ready_count = _int(evidence_counts.get("paper_ready_observations"), 0)
    matched_paper_ready = matched_paper_count >= 5
    post_close_ready = post_close_count >= 5
    manual_execution_dirty = manual_execution_blocked_count > 0 or manual_execution_missing_count > 0
    manual_execution_ready = manual_execution_clean_count >= 5 and not manual_execution_dirty
    production_sample_ready = paper_ready_count >= 20
    research_evidence_ready = all(
        bool(evidence_flags.get(key))
        for key in (
            "walk_forward_oos_passed",
            "lookahead_bias_audit_passed",
            "multiple_testing_control_passed",
            "transaction_cost_capacity_passed",
        )
    )
    small_capital_observation_candidate = (
        has_manual_material
        and research_evidence_ready
        and matched_paper_ready
        and post_close_ready
        and manual_execution_ready
    )
    production_manual_review_candidate = small_capital_observation_candidate and production_sample_ready

    if position_blocked:
        decision = "blocked_current_position_input"
        plain_answer = "当前持仓输入有安全或格式问题，不能进入模拟盘、人工复核或真实资金观察。"
        next_label = "先修正当前持仓"
        next_target = "daily-current-positions"
        next_workflow = ""
    elif blockers:
        decision = "blocked_pretrade_red_light"
        plain_answer = "盘前红灯没有清理，今天最多观察，不能把信号转成真实资金动作。"
        next_label = "先看盘前红灯"
        next_target = "daily-pretrade-readiness-verdict"
        next_workflow = ""
    elif not has_candidates:
        decision = "waiting_for_qualified_cn_etf_candidates"
        plain_answer = "还没有合格 CN_ETF 候选池；先回到因子排行榜和推广闸门。"
        next_label = "查看 CN_ETF 候选"
        next_target = "factor-leaderboard-table"
        next_workflow = ""
    elif not has_signal_targets:
        decision = "generate_same_day_signal_first"
        plain_answer = "已有候选但没有同日信号；先生成今天的 CN_ETF 目标仓位。"
        next_label = "生成今日信号"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"
    elif not has_manual_material:
        decision = "build_manual_ticket_pack_first"
        plain_answer = "已有同日信号但没有可复核票据；先补齐目标金额、数量和取整。"
        next_label = "补齐人工票据"
        next_target = "daily-trade-target-table"
        next_workflow = "daily_trade_advisory"
    elif manual_execution_dirty:
        decision = "blocked_manual_execution_audit"
        plain_answer = "盘后人工成交审计出现追价、滑点超限、数量不一致或缺失回执，先复盘并修正执行纪律，不能升级到小资金观察。"
        next_label = "复盘人工成交审计"
        next_target = "beginner-post-close-journal-board"
        next_workflow = "post_close_journal"
    else:
        decision = "not_ready_for_real_money"
        plain_answer = "今天只能进入同参数模拟盘和人工复核；还不能宣称稳定盈利，也不能直接投入真实资金。"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"

    if decision == "not_ready_for_real_money" and production_manual_review_candidate:
        decision = "production_manual_review_candidate"
        plain_answer = "证据已达到人工生产化复核候选；系统仍不连接券商、不读取账户、不下单。"
        next_label = "查看人工交接"
        next_target = "beginner-live-handoff-board"
        next_workflow = ""
    elif decision == "not_ready_for_real_money" and small_capital_observation_candidate:
        decision = "small_capital_manual_observation_candidate"
        plain_answer = "证据已达到小资金人工观察候选；这不是自动实盘许可。"
        next_label = "查看小资金观察"
        next_target = "beginner-live-handoff-board"
        next_workflow = ""

    hard_gates = [
        _live_profitability_gate(
            "cn_etf_scope",
            "CN_ETF 主线范围",
            "pass" if has_candidates else "blocked",
            "只允许从合格 CN_ETF 候选池出发；兜底基线和 CN 个股线不能直接变成 ETF 实盘动作。",
            "factor-leaderboard-table",
            "daily_trade_advisory" if not has_candidates and not blockers else "",
            evidence_kind="candidate_scope",
            required_before="paper_rehearsal",
        ),
        _live_profitability_gate(
            "same_day_signal",
            "同日信号",
            "pass" if has_signal_targets and pretrade_clear else "blocked",
            "必须有运行日当天的 ETF、权重、参考价格和目标金额；旧信号不能复用。",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets and not blockers else "",
            evidence_kind="same_day_signal_snapshot",
            required_before="paper_rehearsal",
        ),
        _live_profitability_gate(
            "pretrade_red_light",
            "盘前红灯",
            "pass" if pretrade_clear else "blocked",
            "任何数据日期、兜底基线、持仓输入、价格或安全边界红灯都必须先清理。",
            "daily-pretrade-readiness-verdict",
            evidence_kind="pretrade_blocker_audit",
            required_before="paper_rehearsal",
        ),
        _live_profitability_gate(
            "manual_ticket",
            "人工票据",
            "pass" if has_manual_material else "blocked",
            "必须有可人工核对的买卖票据；票据只是复核材料，不是委托单。",
            "daily-manual-broker-handoff-ticket-table",
            evidence_kind="manual_review_ticket",
            required_before="paper_rehearsal",
        ),
        _live_profitability_gate(
            "walk_forward_oos",
            "长样本 / 样本外",
            "pass" if evidence_flags.get("walk_forward_oos_passed") else "required",
            "候选因子必须有 walk-forward、OOS、长周期和不同市场状态证据，不能只看短期总收益。",
            "control-backtest-gate",
            evidence_kind="walk_forward_oos_report",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "lookahead_bias_audit",
            "未来函数审计",
            "pass" if evidence_flags.get("lookahead_bias_audit_passed") else "required",
            "信号使用收盘数据时至少下一交易日执行；负向 shift、全样本归一化、报告期错位必须审计。",
            "daily-trading-system-blueprint",
            evidence_kind="lookahead_bias_audit",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "multiple_testing_control",
            "多重检验控制",
            "pass" if evidence_flags.get("multiple_testing_control_passed") else "required",
            "需要记录总实验数、去重参数组合和显著性修正，避免只挑最好看的回测。",
            "factor-leaderboard-table",
            evidence_kind="multiple_testing_log",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "transaction_cost_capacity",
            "成本 / 滑点 / 容量",
            "pass" if evidence_flags.get("transaction_cost_capacity_passed") else "required",
            "必须扣除手续费、滑点、冲击成本，检查 ETF 成交额、换手率和单票容量。",
            "daily-pretrade-readiness-verdict",
            evidence_kind="cost_capacity_report",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "matched_paper_receipts",
            "同参数模拟盘回执",
            "pass" if matched_paper_ready else "partial" if matched_paper_count > 0 else "required",
            "至少积累 5 次同参数模拟盘回执，再讨论小资金人工观察。",
            "paper-metrics",
            "paper_simulation" if paper_rehearsal_allowed else "",
            evidence_kind="paper_simulation_receipts",
            required_before="small_capital_observation",
            minimum_required_observations=5,
            observed_count=matched_paper_count,
        ),
        _live_profitability_gate(
            "post_close_journals",
            "盘后复盘样本",
            "pass" if post_close_ready else "partial" if post_close_count > 0 else "required",
            "至少积累 5 次盘后复盘，记录执行、跳过、滑点、未成交、回撤和异常。",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets else "",
            evidence_kind="post_close_journal_receipts",
            required_before="small_capital_observation",
            minimum_required_observations=5,
            observed_count=post_close_count,
        ),
        _live_profitability_gate(
            "manual_execution_quality",
            "人工成交审计质量",
            (
                "blocked"
                if manual_execution_dirty
                else "pass"
                if manual_execution_ready
                else "partial"
                if manual_execution_clean_count > 0
                else "required"
            ),
            "至少 5 次盘后人工成交/跳过审计必须干净，且追价、滑点超限、数量不一致、缺回执均为 0；否则不能升级小资金观察。",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets else "",
            evidence_kind="manual_execution_audit_receipts",
            required_before="small_capital_observation",
            minimum_required_observations=5,
            observed_count=manual_execution_clean_count,
        ),
        _live_profitability_gate(
            "production_sample_size",
            "生产观察样本",
            "pass" if production_sample_ready else "partial" if paper_ready_count > 0 else "required",
            "至少 20 次 paper-ready 观察样本通过后，才允许讨论人工生产化；不能靠一两天收益升级。",
            "beginner-live-handoff-board",
            evidence_kind="paper_ready_observation_history",
            required_before="production_manual_review",
            minimum_required_observations=20,
            observed_count=paper_ready_count,
        ),
        _live_profitability_gate(
            "research_only_safety_boundary",
            "安全权限边界",
            "pass",
            "系统保持不连接券商、不读取账户、不真实下单、不自动交易；真实资金只能由本人离开系统后手工决定。",
            "control-safety-boundary",
            evidence_kind="permission_boundary",
            required_before="all_stages",
        ),
    ]
    passed_gates = sum(1 for row in hard_gates if row["status"] == "pass")
    readiness_score_pct = int(round(passed_gates / max(len(hard_gates), 1) * 100))
    capital_tier_summary = _live_profitability_capital_tier_summary(
        decision=decision,
        hard_gates=hard_gates,
        small_capital_observation_candidate=small_capital_observation_candidate,
        production_manual_review_candidate=production_manual_review_candidate,
    )

    return _sanitize(
        {
            "stage": LIVE_PROFITABILITY_READINESS_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "primary_market": market,
                "readiness_score_pct": readiness_score_pct,
                "passed_gate_count": passed_gates,
                "total_gate_count": len(hard_gates),
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "paper_rehearsal_allowed": paper_rehearsal_allowed,
                "manual_review_material_ready": manual_review_material_ready,
                "evidence_mode": evidence.get("mode"),
                "matched_paper_receipts": matched_paper_count,
                "post_close_journal_receipts": post_close_count,
                "manual_execution_clean_receipts": manual_execution_clean_count,
                "manual_execution_blocked_receipts": manual_execution_blocked_count,
                "manual_execution_missing_review_receipts": manual_execution_missing_count,
                "paper_ready_observations": paper_ready_count,
                "small_capital_observation_candidate": small_capital_observation_candidate,
                "production_manual_review_candidate": production_manual_review_candidate,
                **capital_tier_summary,
                "profitability_claim_allowed": False,
                "real_money_allowed": False,
                "small_capital_observation_allowed": False,
                "direct_buy_from_top3_allowed": False,
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "beginner_ladder": [
                _live_profitability_ladder_step(
                    1,
                    "qualified_signal",
                    "合格候选和同日信号",
                    "done" if has_signal_targets and pretrade_clear else "blocked",
                    "先证明今天的 CN_ETF 信号是同日、可解释、未被红灯阻断。",
                    "daily-trade-factor-table",
                    "daily_trade_advisory" if not has_signal_targets and not blockers else "",
                ),
                _live_profitability_ladder_step(
                    2,
                    "same_parameter_paper",
                    "同参数模拟盘",
                    "next" if paper_rehearsal_allowed else "blocked",
                    "用同一组因子、TopN、成本、风险档位和资金规模跑本地模拟盘。",
                    "paper-metrics",
                    "paper_simulation" if paper_rehearsal_allowed else "",
                ),
                _live_profitability_ladder_step(
                    3,
                    "manual_review_ticket",
                    "人工票据复核",
                    "waiting" if has_manual_material else "blocked",
                    "人工核对 ETF、方向、价格、数量、金额、现金和风险，仍然不是订单。",
                    "daily-manual-broker-handoff-ticket-table",
                ),
                _live_profitability_ladder_step(
                    4,
                    "small_capital_observation",
                    "小资金人工观察",
                    "locked",
                    "需要 5 次模拟盘回执、5 次盘后复盘和风险稳定后再讨论。",
                    "beginner-live-handoff-board",
                ),
                _live_profitability_ladder_step(
                    5,
                    "production_manual_review",
                    "生产化人工复核",
                    "locked",
                    "至少 20 次 paper-ready 观察样本通过后，才允许进入更高频的人工复核流程。",
                    "beginner-live-handoff-board",
                ),
            ],
            "capital_tier_summary": capital_tier_summary,
            "hard_gates": hard_gates,
            "evidence_snapshot": evidence,
            "today_allowed_actions": _live_profitability_today_actions(
                decision=decision,
                next_label=next_label,
                next_target=next_target,
                next_workflow=next_workflow,
                paper_rehearsal_allowed=paper_rehearsal_allowed,
                manual_review_material_ready=manual_review_material_ready,
                has_signal_targets=has_signal_targets,
            ),
            "forbidden_actions": [
                _live_profitability_action(
                    "direct_buy_top3",
                    "直接买前三因子",
                    "前三因子只是候选入口；没有同日信号、模拟盘和人工复核，不能买。",
                    "factor-leaderboard-table",
                    "forbidden",
                ),
                _live_profitability_action(
                    "auto_broker_order",
                    "自动连券商下单",
                    "当前项目边界禁止券商连接、账户读取、真实委托和自动交易。",
                    "control-safety-boundary",
                    "forbidden",
                ),
                _live_profitability_action(
                    "skip_paper_receipt",
                    "跳过模拟盘直接实盘",
                    "没有同参数模拟盘回执，就无法判断成本、回撤和成交风险。",
                    "paper-metrics",
                    "forbidden",
                ),
                _live_profitability_action(
                    "size_up_from_annual_return",
                    "只因为年化高就加仓",
                    "年化和总收益不能替代回撤、OOS、多重检验、容量和执行复盘。",
                    "control-backtest-gate",
                    "forbidden",
                ),
            ],
            "stability_controls": [
                _live_profitability_control(
                    "kill_switch_drawdown",
                    "回撤熔断",
                    "模拟盘或人工观察触发风险档位回撤、连续亏损或红灯事件时，停止升级并回到审计。",
                    "daily-live-readiness-gate",
                ),
                _live_profitability_control(
                    "parameter_sensitivity",
                    "参数敏感性",
                    "最优参数附近上下扰动仍要稳定；尖峰参数不能进入真实资金观察。",
                    "control-backtest-gate",
                ),
                _live_profitability_control(
                    "execution_slippage_journal",
                    "滑点和未成交复盘",
                    "每天记录真实可成交价格、滑点、未成交、跳过原因和人工情绪偏差。",
                    "beginner-post-close-journal-board",
                ),
                _live_profitability_control(
                    "factor_decay_monitor",
                    "因子衰减监控",
                    "连续 paper-ready 观察恶化时，自动降级为研究候选，不继续推实盘。",
                    "promotion-gate-panel",
                ),
                _live_profitability_control(
                    "retirement_loop",
                    "淘汰闭环",
                    "低 IC、低胜率、成本后失效、容量不足或 regime 单点依赖的因子要退役。",
                    "factor-leaderboard-table",
                ),
            ],
            "deployment_readiness_summary": deployment.get("summary") if isinstance(deployment.get("summary"), dict) else {},
        }
    )


def _daily_next_session_top3_quarantine(
    evidence: dict[str, Any],
    factor_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = evidence.get("counts") if isinstance(evidence.get("counts"), dict) else {}
    factor_count = len(factor_rows)
    requested_top3_count = _int(counts.get("same_parameter_top3_required_requests"), 0)
    required_top3_count = max(requested_top3_count, factor_count if factor_count else 0)
    matched_top3_count = min(
        _int(counts.get("same_parameter_top3_matched_requests"), 0),
        required_top3_count,
    ) if required_top3_count else 0
    post_close_count = _int(counts.get("post_close_journal_receipts"), 0)
    manual_clean_count = _int(counts.get("manual_execution_clean_receipts"), 0)
    manual_blocked_count = _int(counts.get("manual_execution_blocked_receipts"), 0)
    manual_missing_review_count = _int(counts.get("manual_execution_missing_review_receipts"), 0)
    journal_required_count = min(required_top3_count, matched_top3_count)
    same_parameter_blocked = required_top3_count > 0 and matched_top3_count < required_top3_count
    journal_blocked = journal_required_count > 0 and post_close_count < journal_required_count
    manual_exception_count = manual_blocked_count + manual_missing_review_count
    manual_blocked = manual_exception_count > 0
    blocked_reason_count = sum(
        1
        for value in (
            same_parameter_blocked,
            journal_blocked,
            manual_blocked,
        )
        if value
    )
    quarantine_required = factor_count > 0 and blocked_reason_count > 0
    if not factor_count:
        reuse_status = "waiting_for_top3_candidates"
        plain_answer = "还没有今日 Top3，先生成候选、信号和同参数模拟请求。"
        scope = "none"
    elif quarantine_required:
        reuse_status = "quarantine_pending_evidence"
        plain_answer = "这组 Top3 还没有形成同参数模拟、盘后复盘、人工执行审计的干净闭环；明天继续用之前必须先复核或降权。"
        scope = "top3_slate"
    else:
        reuse_status = "top3_slate_clear_for_next_session_review"
        plain_answer = "这组 Top3 已有同参数模拟和盘后复盘闭环；明天仍需人工复核后才能继续进入候选，不代表可以自动下单。"
        scope = "top3_slate"

    rules: list[dict[str, Any]] = []
    if factor_count:
        rules.append(
            {
                "rule_id": "same_parameter_top3_paper_incomplete",
                "label": "同参数 Top3 模拟闭环",
                "status": "blocked" if same_parameter_blocked else "pass",
                "plain_rule": "每天 Top3 的每个因子都要用同一组参数跑纸面/模拟回放；没跑齐，下一交易日不能无提示复用。",
                "target_id": "daily-same-parameter-paper-rehearsal",
                "workflow_id": "paper_simulation" if same_parameter_blocked else "",
                "required_observations": required_top3_count,
                "observed_count": matched_top3_count,
                "missing_count": max(0, required_top3_count - matched_top3_count),
                "quarantine_next_session": bool(same_parameter_blocked),
                "order_placement_allowed": False,
            }
        )
        rules.append(
            {
                "rule_id": "post_close_journal_after_matched_paper",
                "label": "盘后复盘闭环",
                "status": "blocked" if journal_blocked else "pass",
                "plain_rule": "只要今天已有同参数模拟回执，就要留下盘后复盘；否则无法知道信号、成交和跳过原因是否真实可执行。",
                "target_id": "beginner-post-close-journal-board",
                "workflow_id": "post_close_journal" if journal_blocked else "",
                "required_observations": journal_required_count,
                "observed_count": post_close_count,
                "missing_count": max(0, journal_required_count - post_close_count),
                "quarantine_next_session": bool(journal_blocked),
                "order_placement_allowed": False,
            }
        )
        rules.append(
            {
                "rule_id": "manual_execution_exception",
                "label": "人工执行异常审计",
                "status": "blocked" if manual_blocked else "pass",
                "plain_rule": "如果手工成交、跳过、价格滑点或复核记录出现异常，下一交易日必须先隔离这组信号，不能直接继承。",
                "target_id": "manual-execution-audit-board",
                "workflow_id": "post_close_journal" if manual_blocked else "",
                "required_observations": 0,
                "observed_count": manual_exception_count,
                "missing_count": 0,
                "manual_execution_blocked_receipts": manual_blocked_count,
                "manual_execution_missing_review_receipts": manual_missing_review_count,
                "quarantine_next_session": bool(manual_blocked),
                "order_placement_allowed": False,
            }
        )

    return _sanitize(
        {
            "summary": {
                "next_session_quarantine_required": quarantine_required,
                "next_session_reuse_status": reuse_status,
                "quarantine_scope": scope,
                "quarantine_reason_count": blocked_reason_count,
                "quarantine_plain_answer": plain_answer,
                "same_parameter_top3_required_requests": required_top3_count,
                "same_parameter_top3_matched_requests": matched_top3_count,
                "post_close_journal_receipts": post_close_count,
                "manual_execution_clean_receipts": manual_clean_count,
                "manual_execution_blocked_receipts": manual_blocked_count,
                "manual_execution_missing_review_receipts": manual_missing_review_count,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "rules": rules,
        }
    )


def _daily_recent_observation_degradation(evidence: dict[str, Any]) -> dict[str, Any]:
    risk_state = evidence.get("risk_state") if isinstance(evidence.get("risk_state"), dict) else {}
    recent_count = _int(risk_state.get("recent_observation_count"), 0)
    recent_return = _float_or_none(risk_state.get("recent_observation_return_pct"))
    recent_win_rate = _float_or_none(risk_state.get("recent_observation_win_rate"))
    observed = recent_count > 0 or recent_return is not None or recent_win_rate is not None
    enough_sample = recent_count >= RECENT_OBSERVATION_MIN_COUNT
    return_blocked = bool(enough_sample and recent_return is not None and recent_return <= -RECENT_OBSERVATION_MAX_LOSS_PCT)
    win_rate_blocked = bool(enough_sample and recent_win_rate is not None and recent_win_rate < RECENT_OBSERVATION_MIN_WIN_RATE)
    degraded = return_blocked or win_rate_blocked
    status = "degraded" if degraded else "observed_clear" if observed else "not_observed"
    if degraded:
        plain_answer = "近期纸面/人工观察收益或胜率已经退化；先复盘、降级或隔离，不能继续推进到人工资金观察。"
    elif observed:
        plain_answer = "近期观察暂未触发退化闸门；仍然只允许同参数模拟盘和人工复核。"
    else:
        plain_answer = "还没有近期观察收益和胜率证据；不能把长期回测分数当作实盘稳定性。"

    return _sanitize(
        {
            "summary": {
                "recent_observation_status": status,
                "recent_observation_degradation_required": degraded,
                "recent_observation_count": recent_count,
                "recent_observation_return_pct": recent_return,
                "recent_observation_win_rate": recent_win_rate,
                "recent_observation_min_count": RECENT_OBSERVATION_MIN_COUNT,
                "recent_observation_max_loss_pct": RECENT_OBSERVATION_MAX_LOSS_PCT,
                "recent_observation_min_win_rate": RECENT_OBSERVATION_MIN_WIN_RATE,
                "recent_observation_plain_answer": plain_answer,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "rules": [
                {
                    "rule_id": "recent_observation_degradation",
                    "label": "近期观察退化",
                    "status": "blocked" if degraded else "pass",
                    "plain_rule": (
                        f"至少 {RECENT_OBSERVATION_MIN_COUNT} 次近期纸面/人工观察后，"
                        f"若累计收益 <= -{RECENT_OBSERVATION_MAX_LOSS_PCT:.0%} "
                        f"或胜率 < {RECENT_OBSERVATION_MIN_WIN_RATE:.0%}，下一交易日必须隔离并复盘。"
                    ),
                    "target_id": "beginner-post-close-journal-board",
                    "workflow_id": "post_close_journal" if degraded else "",
                    "required_observations": RECENT_OBSERVATION_MIN_COUNT,
                    "observed_count": recent_count,
                    "missing_count": max(0, RECENT_OBSERVATION_MIN_COUNT - recent_count),
                    "recent_observation_return_pct": recent_return,
                    "recent_observation_win_rate": recent_win_rate,
                    "quarantine_next_session": degraded,
                    "order_placement_allowed": False,
                }
            ],
        }
    )


def build_daily_factor_health_monitor(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    evidence = _live_profitability_evidence_snapshot(pack.get("live_profitability_evidence_snapshot"))
    flags = evidence.get("flags", {}) if isinstance(evidence.get("flags"), dict) else {}
    research_evidence_ready = all(
        bool(flags.get(key))
        for key in (
            "walk_forward_oos_passed",
            "lookahead_bias_audit_passed",
            "multiple_testing_control_passed",
            "transaction_cost_capacity_passed",
        )
    )
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    factor_rows = [
        _daily_factor_health_row(row, research_evidence_ready=research_evidence_ready)
        for row in factors
    ]
    next_session_quarantine = _daily_next_session_top3_quarantine(evidence, factor_rows)
    recent_observation = _daily_recent_observation_degradation(evidence)
    recent_observation_summary = (
        recent_observation.get("summary")
        if isinstance(recent_observation.get("summary"), dict)
        else {}
    )
    recent_observation_degraded = bool(recent_observation_summary.get("recent_observation_degradation_required"))
    quarantine_summary = (
        next_session_quarantine.get("summary")
        if isinstance(next_session_quarantine.get("summary"), dict)
        else {}
    )
    next_session_reuse_status = str(
        quarantine_summary.get("next_session_reuse_status")
        or "waiting_for_top3_candidates"
    )
    next_session_quarantine_required = bool(quarantine_summary.get("next_session_quarantine_required")) or recent_observation_degraded
    if recent_observation_degraded:
        next_session_reuse_status = "quarantine_recent_observation_degradation"
    for row in factor_rows:
        row["next_session_reuse_status"] = (
            "quarantine_recent_observation_degradation"
            if recent_observation_degraded
            else "quarantine_pending_evidence"
            if next_session_quarantine_required
            else "reviewable_after_clean_closed_loop"
        )
        row["next_session_quarantine_required"] = next_session_quarantine_required
        row["next_session_quarantine_scope"] = quarantine_summary.get("quarantine_scope", "top3_slate")
        row["next_session_quarantine_reason"] = (
            recent_observation_summary.get("recent_observation_plain_answer")
            if recent_observation_degraded
            else quarantine_summary.get("quarantine_plain_answer", "")
        )
        row["recent_observation_status"] = recent_observation_summary.get("recent_observation_status", "not_observed")
        row["recent_observation_degradation_required"] = recent_observation_degraded
    healthy_count = sum(1 for row in factor_rows if row["health_status"] == "healthy_for_paper_observation")
    watch_count = sum(1 for row in factor_rows if row["health_status"] == "watch")
    retire_count = sum(1 for row in factor_rows if row["health_status"] == "retire_candidate")
    if not factor_rows:
        decision = "waiting_for_top3_candidates"
        plain_answer = "还没有今日 Top3 因子，先生成 CN_ETF 今日前三候选和同日信号。"
        next_label = "生成今日前三建议"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"
    elif recent_observation_degraded:
        decision = "quarantine_recent_observation_degradation"
        plain_answer = str(
            recent_observation_summary.get("recent_observation_plain_answer")
            or "近期观察退化，先复盘、降级或隔离，不能继续推进人工资金观察。"
        )
        next_label = "复盘近期观察退化"
        next_target = "beginner-post-close-journal-board"
        next_workflow = "post_close_journal"
    elif retire_count:
        decision = "retire_or_reduce_weight_required"
        plain_answer = "Top3 里有退役或降权候选，不能把排行榜前三直接推到实盘；先替换、降权或只做观察。"
        next_label = "先处理退役候选"
        next_target = "daily-factor-health-rows"
        next_workflow = ""
    elif watch_count:
        decision = "factor_health_watch_required"
        plain_answer = "Top3 暂无硬性退役项，但仍有证据或稳定性缺口；只允许同参数模拟盘观察。"
        next_label = "跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    else:
        decision = "factor_health_clear_for_paper"
        plain_answer = "Top3 因子健康门暂时通过，可以进入同参数模拟盘和人工复核；仍不允许直接买入。"
        next_label = "跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"

    return _sanitize(
        {
            "stage": DAILY_FACTOR_HEALTH_MONITOR_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "primary_market": market,
                "selected_factor_count": _int(summary.get("selected_factor_count"), len(factor_rows)),
                "healthy_count": healthy_count,
                "watch_count": watch_count,
                "retire_candidate_count": retire_count,
                "research_evidence_ready": research_evidence_ready,
                "retirement_required_before_live": retire_count > 0 or recent_observation_degraded,
                "paper_observation_allowed": bool(factor_rows) and retire_count == 0 and not recent_observation_degraded,
                **recent_observation_summary,
                "top3_auto_buy_allowed": False,
                "direct_buy_from_top3_allowed": False,
                "profitability_claim_allowed": False,
                "real_money_allowed": False,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "next_session_quarantine_required": next_session_quarantine_required,
                "next_session_reuse_status": next_session_reuse_status,
                "quarantine_scope": quarantine_summary.get("quarantine_scope", "none"),
                "quarantine_reason_count": _int(quarantine_summary.get("quarantine_reason_count"), 0)
                + (1 if recent_observation_degraded else 0),
                "quarantine_plain_answer": (
                    recent_observation_summary.get("recent_observation_plain_answer")
                    if recent_observation_degraded
                    else quarantine_summary.get("quarantine_plain_answer", "")
                ),
                "same_parameter_top3_required_requests": _int(
                    quarantine_summary.get("same_parameter_top3_required_requests"),
                    0,
                ),
                "same_parameter_top3_matched_requests": _int(
                    quarantine_summary.get("same_parameter_top3_matched_requests"),
                    0,
                ),
                "post_close_journal_receipts": _int(quarantine_summary.get("post_close_journal_receipts"), 0),
                "manual_execution_clean_receipts": _int(
                    quarantine_summary.get("manual_execution_clean_receipts"),
                    0,
                ),
                "manual_execution_blocked_receipts": _int(
                    quarantine_summary.get("manual_execution_blocked_receipts"),
                    0,
                ),
                "manual_execution_missing_review_receipts": _int(
                    quarantine_summary.get("manual_execution_missing_review_receipts"),
                    0,
                ),
            },
            "factor_rows": factor_rows,
            "recommended_actions": _daily_factor_health_actions(
                decision=decision,
                retire_count=retire_count,
                watch_count=watch_count,
                has_factors=bool(factor_rows),
                next_label=next_label,
                next_target=next_target,
                next_workflow=next_workflow,
                paper_observation_allowed=bool(factor_rows) and retire_count == 0 and not recent_observation_degraded,
                recent_observation_degradation_required=recent_observation_degraded,
            )
            + (
                [
                    _daily_factor_health_action(
                        "complete_top3_evidence_before_next_session",
                        "补齐明日复用证据",
                        "同参数 Top3 模拟、盘后复盘或人工执行审计没有形成干净闭环；明天复用这组因子前必须先处理。",
                        "daily-same-parameter-paper-rehearsal",
                        "required",
                        "paper_simulation",
                    )
                ]
                if next_session_quarantine_required
                else []
            ),
            "evidence_snapshot": evidence,
            "next_session_quarantine_rules": next_session_quarantine.get("rules", [])
            + recent_observation.get("rules", []),
            "health_rules": [
                {
                    "rule_id": "retire_candidate",
                    "plain_rule": "负 Sharpe、RankIC 为负、30% 级别回撤、样本少于 30 笔、胜率低于 48% 或兜底基线，都不能进入实盘推广。",
                    "order_placement_allowed": False,
                },
                {
                    "rule_id": "watch",
                    "plain_rule": "指标没有硬伤但证据不足、RankIC 太弱、胜率不够或样本偏薄时，只做同参数模拟盘观察。",
                    "order_placement_allowed": False,
                },
                {
                    "rule_id": "healthy_for_paper_observation",
                    "plain_rule": "健康只表示可以继续同参数模拟盘和人工复核，不表示可以自动下单或保证盈利。",
                    "order_placement_allowed": False,
                },
            ],
        }
    )


def build_daily_real_money_transition_gate(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    health = pack.get("daily_factor_health_monitor") if isinstance(pack.get("daily_factor_health_monitor"), dict) else {}
    profitability = pack.get("live_profitability_readiness") if isinstance(pack.get("live_profitability_readiness"), dict) else {}
    risk_circuit = (
        pack.get("daily_execution_risk_circuit_breaker")
        if isinstance(pack.get("daily_execution_risk_circuit_breaker"), dict)
        else build_daily_execution_risk_circuit_breaker(pack)
    )
    health_summary = health.get("summary") if isinstance(health.get("summary"), dict) else {}
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    risk_circuit_summary = risk_circuit.get("summary") if isinstance(risk_circuit.get("summary"), dict) else {}
    evidence = (
        profitability.get("evidence_snapshot")
        if isinstance(profitability.get("evidence_snapshot"), dict)
        else _live_profitability_evidence_snapshot(pack.get("live_profitability_evidence_snapshot"))
    )
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    ticket_source = (
        []
        if handoff.get("copyable_tickets_masked_until_same_parameter_paper")
        else copyable_tickets or [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
    )
    manual_preview = _real_money_transition_ticket_preview(ticket_source, summary)
    blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    gate_by_id = {
        str(row.get("gate_id")): row
        for row in profitability.get("hard_gates", [])
        if isinstance(row, dict) and row.get("gate_id")
    }
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    selected_count = _int(summary.get("selected_factor_count"), len(factors))
    signal_count = _int(summary.get("signal_count"), 0)
    target_count = _int(summary.get("combined_target_count"), len(targets))
    ticket_count = _int(summary.get("manual_ticket_count"), len(ticket_source))
    position_status = str(validation.get("status") or summary.get("current_position_status") or "not_provided")
    health_decision = str(health_summary.get("decision") or "waiting_for_top3_candidates")
    profitability_decision = str(profitability_summary.get("decision") or "not_ready_for_real_money")
    risk_circuit_decision = str(risk_circuit_summary.get("decision") or "risk_state_not_observed")
    risk_circuit_blocked = bool(risk_circuit_summary.get("risk_circuit_blocked"))
    recent_observation_degraded = bool(health_summary.get("recent_observation_degradation_required"))
    health_blocked = (
        bool(health_summary.get("retirement_required_before_live"))
        or "retire" in health_decision
        or recent_observation_degraded
    )
    next_session_quarantine_required = bool(health_summary.get("next_session_quarantine_required"))
    next_session_quarantine_required_count = _int(health_summary.get("same_parameter_top3_required_requests"), 0)
    next_session_quarantine_matched_count = _int(health_summary.get("same_parameter_top3_matched_requests"), 0)
    next_session_quarantine_missing_count = max(
        0,
        next_session_quarantine_required_count - next_session_quarantine_matched_count,
    )
    has_signal_targets = signal_count > 0 and target_count > 0
    has_manual_material = ticket_count > 0 and bool(manual_preview)
    risk_blocked = any(
        bool((row.get("risk_budget") or {}).get("single_etf_limit_breached"))
        or bool((row.get("risk_budget") or {}).get("rounded_value_limit_breached"))
        or any(item.get("status") == "blocked" for item in row.get("manual_skip_conditions", []) if isinstance(item, dict))
        for row in manual_preview
    )
    research_evidence_status = _transition_research_evidence_status(gate_by_id)
    paper_receipt_status = _transition_gate_status(gate_by_id, "matched_paper_receipts")
    journal_status = _transition_gate_status(gate_by_id, "post_close_journals")
    manual_execution_status = _transition_gate_status(gate_by_id, "manual_execution_quality")
    production_sample_status = _transition_gate_status(gate_by_id, "production_sample_size")
    ticket_risk_status = (
        "blocked"
        if risk_blocked
        else "pass"
        if has_manual_material
        else "required"
    )

    if position_status == "error":
        decision = "blocked_current_position_input"
        plain_answer = "当前持仓输入含账户、券商、订单或格式风险，先修正输入，不能进入真实资金观察。"
        next_label = "修正当前持仓"
        next_target = "daily-current-positions"
        next_workflow = ""
    elif blockers:
        decision = "blocked_pretrade_red_light"
        plain_answer = "盘前红灯仍存在，今天只能观察或修复数据，不能把信号推进到人工资金动作。"
        next_label = "查看盘前红灯"
        next_target = "daily-pretrade-readiness-verdict"
        next_workflow = ""
    elif risk_circuit_blocked:
        decision = "blocked_risk_circuit_breaker"
        plain_answer = "当日亏损、回撤、连续亏损或冷却期风险熔断为红灯；今天只能纸面复盘，不能推进人工券商复核。"
        next_label = "记录风险事件"
        next_target = "beginner-post-close-journal-board"
        next_workflow = "post_close_journal"
    elif recent_observation_degraded:
        decision = "blocked_recent_observation_degradation"
        plain_answer = str(
            health_summary.get("recent_observation_plain_answer")
            or "近期纸面/人工观察收益或胜率退化；先复盘、降级或隔离，不能推进人工资金观察。"
        )
        next_label = "复盘近期观察退化"
        next_target = "beginner-post-close-journal-board"
        next_workflow = "post_close_journal"
    elif health_blocked:
        decision = "rotate_or_reduce_top3_first"
        plain_answer = "Top3 中存在退役或降权候选，先替换、降权或只观察，不能推进到真实资金。"
        next_label = "处理退役因子"
        next_target = "daily-factor-health-rows"
        next_workflow = ""
    elif next_session_quarantine_required:
        decision = "blocked_next_session_quarantine_required"
        plain_answer = (
            "Top3 same-parameter paper, post-close journal, or manual execution audit is incomplete; "
            "complete the next-session reuse evidence before any live/manual-money review."
        )
        next_label = "Complete next-session Top3 evidence"
        next_target = "daily-factor-health-rules"
        next_workflow = "paper_simulation" if has_signal_targets else "daily_trade_advisory"
    elif risk_blocked:
        decision = "blocked_ticket_risk_budget"
        plain_answer = "人工票据触发单 ETF、金额或数量风险预算阻断，先缩仓、改风险档位或跳过票据。"
        next_label = "查看票据风险"
        next_target = "daily-manual-broker-handoff-ticket-table"
        next_workflow = ""
    elif manual_execution_status == "blocked":
        decision = "blocked_manual_execution_audit"
        plain_answer = "盘后人工成交审计存在追价、滑点、数量或缺回执问题，先复盘执行纪律，不能进入真实资金观察。"
        next_label = "复盘人工成交审计"
        next_target = "beginner-post-close-journal-board"
        next_workflow = "post_close_journal"
    elif profitability_decision == "production_manual_review_candidate":
        decision = "production_manual_review_candidate"
        plain_answer = "证据已达到人工生产复核候选，但软件仍不连接券商、不读取账户、不自动下单。"
        next_label = "查看人工交接"
        next_target = "beginner-live-handoff-board"
        next_workflow = ""
    elif profitability_decision == "small_capital_manual_observation_candidate":
        decision = "small_capital_manual_observation_candidate"
        plain_answer = "证据已达到小资金人工观察候选，这只是人工观察资格，不是自动实盘许可。"
        next_label = "查看小资金观察"
        next_target = "beginner-live-handoff-board"
        next_workflow = ""
    elif has_manual_material and has_signal_targets:
        decision = "paper_rehearsal_required"
        plain_answer = "今天可以先跑同参数模拟盘并核对人工票据，但还不能宣称稳定盈利或投入真实资金。"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    elif has_signal_targets:
        decision = "build_manual_ticket_pack_first"
        plain_answer = "已有今日信号，但人工票据还不完整，先补齐数量、金额、取整和风险预算。"
        next_label = "补齐人工票据"
        next_target = "daily-trade-target-table"
        next_workflow = "daily_trade_advisory"
    else:
        decision = "generate_same_day_signal_first"
        plain_answer = "先生成今天的 CN_ETF Top3 信号，不能直接从排行榜进入买卖。"
        next_label = "生成今日信号"
        next_target = "run-daily-trade-advisory"
        next_workflow = "daily_trade_advisory"

    capital_mode = _real_money_transition_capital_mode(decision)
    preflight_rows = [
        _real_money_transition_gate_row(
            "cn_etf_scope",
            "CN_ETF 主线",
            "pass" if market == "CN_ETF" and selected_count > 0 else "blocked",
            f"market={market}; selected_factors={selected_count}",
            "factor-leaderboard-table",
            required_before="paper_rehearsal",
        ),
        _real_money_transition_gate_row(
            "factor_health",
            "Top3 因子健康",
            "blocked" if health_blocked else "pass" if health_summary.get("paper_observation_allowed") else "required",
            str(health_summary.get("plain_answer") or health_decision),
            "daily-factor-health-rows",
            required_before="paper_rehearsal",
        ),
        _real_money_transition_gate_row(
            "next_session_quarantine",
            "Next-session Top3 reuse quarantine",
            "blocked" if next_session_quarantine_required else "pass" if selected_count > 0 else "required",
            str(
                health_summary.get("quarantine_plain_answer")
                or "Top3 must complete same-parameter paper, post-close journal, and manual execution audit before reuse."
            ),
            "daily-factor-health-rules",
            "paper_simulation" if next_session_quarantine_required and has_signal_targets else "",
            required_before="manual_review",
            observed_count=next_session_quarantine_matched_count,
            required_count=next_session_quarantine_required_count,
            missing_count=next_session_quarantine_missing_count,
            reason_count=_int(health_summary.get("quarantine_reason_count"), 0),
        ),
        _real_money_transition_gate_row(
            "same_day_signal",
            "同日 ETF 信号",
            "pass" if has_signal_targets else "required",
            f"signals={signal_count}; targets={target_count}; run_date={pack.get('run_date')}",
            "daily-trade-factor-table",
            "daily_trade_advisory" if not has_signal_targets else "",
            required_before="paper_rehearsal",
        ),
        _real_money_transition_gate_row(
            "pretrade_red_light",
            "盘前红灯",
            "pass" if not blockers and position_status != "error" else "blocked",
            ", ".join(blockers) if blockers else f"position_status={position_status}",
            "daily-pretrade-readiness-verdict",
            required_before="paper_rehearsal",
        ),
        _real_money_transition_gate_row(
            "daily_risk_circuit_breaker",
            "当日风险熔断",
            "blocked" if risk_circuit_blocked else "pass",
            str(risk_circuit_summary.get("plain_answer") or risk_circuit_decision),
            "beginner-post-close-journal-board" if risk_circuit_blocked else "daily-pre-execution-guard",
            "post_close_journal" if risk_circuit_blocked else "",
            required_before="manual_review",
            observed_count=1 if bool(risk_circuit_summary.get("risk_state_observed")) else 0,
            required_count=1,
            missing_count=0 if bool(risk_circuit_summary.get("risk_state_observed")) else 1,
        ),
        _real_money_transition_gate_row(
            "research_evidence",
            "OOS / 未来函数 / 多重检验 / 成本容量",
            research_evidence_status,
            _transition_research_evidence_detail(gate_by_id),
            "control-backtest-gate",
            required_before="small_capital_observation",
        ),
        _real_money_transition_gate_row(
            "paper_receipts",
            "同参数模拟盘回执",
            paper_receipt_status,
            _transition_observation_detail(evidence, "matched_paper_receipts", required=5),
            "paper-metrics",
            "paper_simulation" if has_signal_targets else "",
            required_before="small_capital_observation",
        ),
        _real_money_transition_gate_row(
            "post_close_journals",
            "盘后复盘样本",
            journal_status,
            _transition_observation_detail(evidence, "post_close_journal_receipts", required=5),
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets else "",
            required_before="small_capital_observation",
        ),
        _real_money_transition_gate_row(
            "manual_execution_quality",
            "人工成交审计质量",
            manual_execution_status,
            _transition_observation_detail(evidence, "manual_execution_clean_receipts", required=5),
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets else "",
            required_before="small_capital_observation",
        ),
        _real_money_transition_gate_row(
            "production_sample_size",
            "生产观察样本",
            production_sample_status,
            _transition_observation_detail(evidence, "paper_ready_observations", required=20),
            "beginner-live-handoff-board",
            required_before="production_manual_review",
        ),
        _real_money_transition_gate_row(
            "manual_ticket_risk_budget",
            "人工票据风险预算",
            ticket_risk_status,
            f"manual_tickets={ticket_count}; risk_blocked={risk_blocked}",
            "daily-manual-broker-handoff-ticket-table",
            required_before="manual_review",
        ),
        _real_money_transition_gate_row(
            "research_only_safety_boundary",
            "系统权限边界",
            "pass",
            "软件不连接券商、不读取账户、不提交真实订单；真实资金只能由本人离开系统后手工决定。",
            "control-safety-boundary",
            required_before="all_stages",
        ),
    ]

    return _sanitize(
        {
            "stage": DAILY_REAL_MONEY_TRANSITION_GATE_STAGE,
            "run_date": pack.get("run_date", date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "plain_answer": plain_answer,
                "capital_mode": capital_mode,
                "primary_market": market,
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "factor_health_decision": health_decision,
                "live_profitability_decision": profitability_decision,
                "risk_circuit_decision": risk_circuit_decision,
                "risk_circuit_blocked": risk_circuit_blocked,
                "readiness_score_pct": _int(profitability_summary.get("readiness_score_pct"), 0),
                "matched_paper_receipts": _int(profitability_summary.get("matched_paper_receipts"), 0),
                "post_close_journal_receipts": _int(profitability_summary.get("post_close_journal_receipts"), 0),
                "manual_execution_clean_receipts": _int(
                    profitability_summary.get("manual_execution_clean_receipts"), 0
                ),
                "manual_execution_blocked_receipts": _int(
                    profitability_summary.get("manual_execution_blocked_receipts"), 0
                ),
                "manual_execution_missing_review_receipts": _int(
                    profitability_summary.get("manual_execution_missing_review_receipts"), 0
                ),
                "paper_ready_observations": _int(profitability_summary.get("paper_ready_observations"), 0),
                "next_session_quarantine_required": next_session_quarantine_required,
                "next_session_reuse_status": str(
                    health_summary.get("next_session_reuse_status") or "waiting_for_top3_candidates"
                ),
                "next_session_quarantine_missing_count": next_session_quarantine_missing_count,
                "small_capital_observation_candidate": bool(
                    profitability_summary.get("small_capital_observation_candidate")
                )
                and not health_blocked
                and not next_session_quarantine_required
                and not risk_blocked
                and not risk_circuit_blocked
                and manual_execution_status == "pass",
                "production_manual_review_candidate": bool(
                    profitability_summary.get("production_manual_review_candidate")
                )
                and not health_blocked
                and not next_session_quarantine_required
                and not risk_blocked
                and not risk_circuit_blocked
                and manual_execution_status == "pass",
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "real_money_allowed": False,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "human_broker_only": True,
            },
            "preflight_rows": preflight_rows,
            "today_signal_cards": _real_money_transition_signal_cards(factors, signal_cards, health),
            "manual_execution_preview": manual_preview,
            "operator_script": _real_money_transition_operator_script(
                decision=decision,
                next_target=next_target,
                next_workflow=next_workflow,
                paper_status=paper_receipt_status,
                journal_status=journal_status,
                ticket_risk_status=ticket_risk_status,
                has_manual_material=has_manual_material,
            ),
            "capital_mode_policy": {
                "capital_mode": capital_mode,
                "plain_policy": _real_money_transition_capital_policy_text(capital_mode),
                "max_system_stage": "manual_review_material",
                "external_human_decision_required": True,
                "software_submits_orders": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
            },
            "forbidden_actions": _real_money_transition_forbidden_actions(),
            "evidence_snapshot": evidence,
            "live_profitability_summary": profitability_summary,
            "factor_health_summary": health_summary,
            "risk_circuit_summary": risk_circuit_summary,
        }
    )


def build_daily_manual_trading_session(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    transition = (
        pack.get("daily_real_money_transition_gate")
        if isinstance(pack.get("daily_real_money_transition_gate"), dict)
        else {}
    )
    transition_summary = transition.get("summary") if isinstance(transition.get("summary"), dict) else {}
    profitability = (
        pack.get("live_profitability_readiness")
        if isinstance(pack.get("live_profitability_readiness"), dict)
        else {}
    )
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = (
        pack.get("current_position_validation")
        if isinstance(pack.get("current_position_validation"), dict)
        else {}
    )
    health = pack.get("daily_factor_health_monitor") if isinstance(pack.get("daily_factor_health_monitor"), dict) else {}
    health_summary = health.get("summary") if isinstance(health.get("summary"), dict) else {}
    risk_circuit = (
        pack.get("daily_execution_risk_circuit_breaker")
        if isinstance(pack.get("daily_execution_risk_circuit_breaker"), dict)
        else build_daily_execution_risk_circuit_breaker(pack)
    )
    risk_circuit_summary = risk_circuit.get("summary") if isinstance(risk_circuit.get("summary"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    preflight_rows = [row for row in transition.get("preflight_rows", []) if isinstance(row, dict)]
    gate_by_id = {str(row.get("gate_id")): row for row in preflight_rows if row.get("gate_id")}
    manual_preview_source = [
        row for row in transition.get("manual_execution_preview", []) if isinstance(row, dict)
    ]
    if not manual_preview_source:
        copyable_tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
        fallback_tickets = (
            []
            if handoff.get("copyable_tickets_masked_until_same_parameter_paper")
            else copyable_tickets or [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
        )
        manual_preview_source = _real_money_transition_ticket_preview(fallback_tickets, summary)
    manual_ticket_preview = [_daily_manual_session_ticket(row) for row in manual_preview_source]

    selected_count = _session_count(transition_summary.get("selected_factor_count"), summary.get("selected_factor_count"))
    signal_count = _session_count(transition_summary.get("signal_count"), summary.get("signal_count"))
    target_count = _session_count(transition_summary.get("target_count"), summary.get("combined_target_count"))
    ticket_count = len(manual_ticket_preview) or _session_count(
        transition_summary.get("manual_ticket_count"),
        summary.get("manual_ticket_count"),
    )
    matched_paper = _session_count(
        transition_summary.get("matched_paper_receipts"),
        profitability_summary.get("matched_paper_receipts"),
    )
    journal_count = _session_count(
        transition_summary.get("post_close_journal_receipts"),
        profitability_summary.get("post_close_journal_receipts"),
    )
    manual_clean = _session_count(
        transition_summary.get("manual_execution_clean_receipts"),
        profitability_summary.get("manual_execution_clean_receipts"),
    )
    manual_blocked = _session_count(
        transition_summary.get("manual_execution_blocked_receipts"),
        profitability_summary.get("manual_execution_blocked_receipts"),
    )
    manual_missing = _session_count(
        transition_summary.get("manual_execution_missing_review_receipts"),
        profitability_summary.get("manual_execution_missing_review_receipts"),
    )
    paper_ready_observations = _session_count(
        transition_summary.get("paper_ready_observations"),
        profitability_summary.get("paper_ready_observations"),
    )

    position_status = str(validation.get("status") or summary.get("current_position_status") or "unknown")
    readiness_blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    transition_decision = str(transition_summary.get("decision") or "")
    health_decision = str(health_summary.get("decision") or "")
    risk_circuit_decision = str(
        transition_summary.get("risk_circuit_decision")
        or risk_circuit_summary.get("decision")
        or "risk_state_not_observed"
    )
    risk_circuit_blocked = bool(
        transition_summary.get("risk_circuit_blocked")
        or risk_circuit_summary.get("risk_circuit_blocked")
        or transition_decision == "blocked_risk_circuit_breaker"
    )
    pretrade_blocked = (
        position_status == "error"
        or bool(readiness_blockers)
        or transition_decision in {"blocked_pretrade_red_light", "blocked_current_position_input"}
    )
    health_blocked = bool(health_summary.get("retirement_required_before_live")) or transition_decision == "rotate_or_reduce_top3_first"
    next_session_quarantine_required = bool(health_summary.get("next_session_quarantine_required")) or (
        transition_decision == "blocked_next_session_quarantine_required"
    )
    next_session_quarantine_missing_count = _session_count(
        transition_summary.get("next_session_quarantine_missing_count"),
        max(
            0,
            _int(health_summary.get("same_parameter_top3_required_requests"), 0)
            - _int(health_summary.get("same_parameter_top3_matched_requests"), 0),
        ),
    )
    has_same_day_signal = signal_count > 0 and target_count > 0
    has_manual_tickets = ticket_count > 0
    manual_execution_dirty = manual_blocked > 0 or manual_missing > 0
    production_candidate = bool(transition_summary.get("production_manual_review_candidate"))
    small_candidate = bool(transition_summary.get("small_capital_observation_candidate"))

    if pretrade_blocked:
        session_status = "blocked_pretrade_red_light"
    elif risk_circuit_blocked:
        session_status = "blocked_risk_circuit_breaker"
    elif health_blocked:
        session_status = "blocked_factor_health_rotation_required"
    elif not has_same_day_signal:
        session_status = "blocked_same_day_signal_required"
    elif not has_manual_tickets:
        session_status = "blocked_manual_ticket_required"
    elif matched_paper < 5:
        session_status = "blocked_same_parameter_paper_required"
    elif journal_count < 5:
        session_status = "blocked_post_close_journal_required"
    elif manual_execution_dirty:
        session_status = "blocked_manual_execution_audit"
    elif next_session_quarantine_required:
        session_status = "blocked_next_session_quarantine_required"
    elif production_candidate:
        session_status = "production_manual_review_candidate"
    elif small_candidate:
        session_status = "small_capital_manual_observation_candidate"
    else:
        session_status = "paper_rehearsal_required"

    blocked = session_status.startswith("blocked")
    traffic_light = "red" if blocked else "yellow"
    manual_broker_review_candidate = session_status in {
        "production_manual_review_candidate",
        "small_capital_manual_observation_candidate",
    }
    blocking_gates = _daily_manual_session_blocking_gates(
        selected_count=selected_count,
        signal_count=signal_count,
        target_count=target_count,
        ticket_count=ticket_count,
        matched_paper=matched_paper,
        journal_count=journal_count,
        manual_clean=manual_clean,
        manual_blocked=manual_blocked,
        manual_missing=manual_missing,
        pretrade_blocked=pretrade_blocked,
        risk_circuit_blocked=risk_circuit_blocked,
        risk_circuit_decision=risk_circuit_decision,
        health_blocked=health_blocked,
        next_session_quarantine_required=next_session_quarantine_required,
        next_session_quarantine_missing_count=next_session_quarantine_missing_count,
        research_evidence_status=str(gate_by_id.get("research_evidence", {}).get("status") or "required"),
    )
    next_gate = blocking_gates[0] if blocking_gates else {}
    return _sanitize(
        {
            "stage": DAILY_MANUAL_TRADING_SESSION_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "session_status": session_status,
                "traffic_light": traffic_light,
                "plain_answer": _daily_manual_session_plain_answer(session_status),
                "primary_market": str(transition_summary.get("primary_market") or "CN_ETF"),
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": ticket_count,
                "matched_paper_receipts": matched_paper,
                "post_close_journal_receipts": journal_count,
                "manual_execution_clean_receipts": manual_clean,
                "manual_execution_blocked_receipts": manual_blocked,
                "manual_execution_missing_review_receipts": manual_missing,
                "paper_ready_observations": paper_ready_observations,
                "readiness_score_pct": _session_count(transition_summary.get("readiness_score_pct")),
                "next_session_quarantine_required": next_session_quarantine_required,
                "next_session_quarantine_missing_count": next_session_quarantine_missing_count,
                "next_session_reuse_status": str(
                    health_summary.get("next_session_reuse_status")
                    or transition_summary.get("next_session_reuse_status")
                    or "waiting_for_top3_candidates"
                ),
                "risk_circuit_decision": risk_circuit_decision,
                "risk_circuit_blocked": risk_circuit_blocked,
                "manual_broker_review_candidate": manual_broker_review_candidate,
                "small_capital_observation_candidate": small_candidate and not blocked,
                "production_manual_review_candidate": production_candidate and not blocked,
                "real_money_allowed": False,
                "live_order_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "next_gate_id": next_gate.get("gate_id"),
                "next_label": next_gate.get("label") or transition_summary.get("next_label") or "Review today's manual session",
                "next_target_id": next_gate.get("target_id") or transition_summary.get("next_target_id") or "daily-manual-trading-session",
                "next_workflow_id": next_gate.get("workflow_id") or transition_summary.get("next_workflow_id") or "",
            },
            "session_phases": _daily_manual_session_phases(
                session_status=session_status,
                selected_count=selected_count,
                signal_count=signal_count,
                target_count=target_count,
                ticket_count=ticket_count,
                matched_paper=matched_paper,
                journal_count=journal_count,
                manual_clean=manual_clean,
                manual_blocked=manual_blocked,
                manual_missing=manual_missing,
            ),
            "blocking_gates": blocking_gates,
            "operator_checklist": _daily_manual_session_operator_checklist(
                session_status=session_status,
                selected_count=selected_count,
                signal_count=signal_count,
                ticket_count=ticket_count,
                matched_paper=matched_paper,
                journal_count=journal_count,
                manual_clean=manual_clean,
                manual_execution_dirty=manual_execution_dirty,
                manual_broker_review_candidate=manual_broker_review_candidate,
            ),
            "manual_ticket_preview": manual_ticket_preview,
            "transition_summary": transition_summary,
            "profitability_summary": profitability_summary,
            "risk_circuit_summary": risk_circuit_summary,
            "forbidden_actions": _real_money_transition_forbidden_actions(),
            "session_rules": [
                {
                    "rule_id": "no_direct_top3_buy",
                    "plain_rule": "Top3 factors are candidate inputs; they are never direct buy orders.",
                    "order_placement_allowed": False,
                },
                {
                    "rule_id": "same_parameter_paper_first",
                    "plain_rule": "A manual-money session needs matched same-parameter paper evidence before any human broker review.",
                    "order_placement_allowed": False,
                },
                {
                    "rule_id": "manual_external_broker_only",
                    "plain_rule": "If capital is ever used, the human must leave this software and decide manually in the broker app.",
                    "order_placement_allowed": False,
                },
            ],
        }
    )


def _daily_manual_session_ticket(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["order_placement_allowed"] = False
    item["auto_order_allowed"] = False
    item["broker_connection_allowed"] = False
    item["account_read_allowed"] = False
    item["manual_review_only"] = True
    return item


def _daily_manual_session_blocking_gates(
    *,
    selected_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    matched_paper: int,
    journal_count: int,
    manual_clean: int,
    manual_blocked: int,
    manual_missing: int,
    pretrade_blocked: bool,
    risk_circuit_blocked: bool,
    risk_circuit_decision: str,
    health_blocked: bool,
    next_session_quarantine_required: bool,
    next_session_quarantine_missing_count: int,
    research_evidence_status: str,
) -> list[dict[str, Any]]:
    candidates = [
        (
            "pretrade_red_light",
            "Pretrade red light",
            not pretrade_blocked,
            "daily-pretrade-readiness-verdict",
            "",
            "Fix current positions and pretrade blockers first.",
        ),
        (
            "daily_risk_circuit_breaker",
            "Daily risk circuit breaker",
            not risk_circuit_blocked,
            "beginner-post-close-journal-board" if risk_circuit_blocked else "daily-pre-execution-guard",
            "post_close_journal" if risk_circuit_blocked else "",
            f"risk_circuit_decision={risk_circuit_decision}.",
        ),
        (
            "factor_health",
            "Top3 factor health",
            not health_blocked and selected_count > 0,
            "daily-factor-health-rows",
            "",
            "Retire or reduce bad Top3 factors before manual review.",
        ),
        (
            "next_session_quarantine",
            "Next-session Top3 reuse quarantine",
            not next_session_quarantine_required,
            "daily-factor-health-rules",
            "paper_simulation",
            f"quarantine_required={next_session_quarantine_required}; missing={next_session_quarantine_missing_count}.",
        ),
        (
            "same_day_signal",
            "Same-day CN_ETF signal",
            signal_count > 0 and target_count > 0,
            "daily-trade-factor-table",
            "daily_trade_advisory",
            f"signals={signal_count}; targets={target_count}.",
        ),
        (
            "manual_ticket_pack",
            "Manual ticket pack",
            ticket_count > 0,
            "daily-manual-broker-handoff-ticket-table",
            "daily_trade_advisory",
            f"manual_tickets={ticket_count}.",
        ),
        (
            "research_evidence",
            "Research evidence gates",
            research_evidence_status == "pass",
            "control-backtest-gate",
            "",
            f"research_evidence_status={research_evidence_status}.",
        ),
        (
            "same_parameter_paper",
            "Same-parameter paper receipts",
            matched_paper >= 5,
            "paper-metrics",
            "paper_simulation",
            f"matched_paper_receipts={matched_paper}/5.",
        ),
        (
            "post_close_journal",
            "Post-close journals",
            journal_count >= 5,
            "beginner-post-close-journal-board",
            "post_close_journal",
            f"post_close_journals={journal_count}/5.",
        ),
        (
            "manual_execution_quality",
            "Manual execution quality",
            manual_clean >= 5 and manual_blocked == 0 and manual_missing == 0,
            "beginner-post-close-journal-board",
            "post_close_journal",
            f"clean={manual_clean}/5; blocked={manual_blocked}; missing={manual_missing}.",
        ),
    ]
    rows = []
    for gate_id, label, passed, target_id, workflow_id, evidence in candidates:
        if passed:
            continue
        rows.append(
            {
                "gate_id": gate_id,
                "label": label,
                "status": "blocked"
                if gate_id in {"pretrade_red_light", "daily_risk_circuit_breaker", "factor_health", "next_session_quarantine"}
                else "required",
                "evidence": evidence,
                "target_id": target_id,
                "workflow_id": workflow_id,
                "order_placement_allowed": False,
            }
        )
    return rows


def _daily_manual_session_phases(
    *,
    session_status: str,
    selected_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    matched_paper: int,
    journal_count: int,
    manual_clean: int,
    manual_blocked: int,
    manual_missing: int,
) -> list[dict[str, Any]]:
    blocked = session_status.startswith("blocked")
    return [
        _daily_manual_session_phase(
            1,
            "pre_open_check",
            "Pre-open check",
            "pass" if selected_count > 0 and signal_count > 0 and target_count > 0 else "required",
            f"selected={selected_count}; signals={signal_count}; targets={target_count}.",
            "daily-trade-factor-table",
            "daily_trade_advisory" if signal_count == 0 else "",
        ),
        _daily_manual_session_phase(
            2,
            "same_parameter_paper",
            "Same-parameter paper",
            "pass" if matched_paper >= 5 else "required",
            f"matched_paper_receipts={matched_paper}/5.",
            "paper-metrics",
            "paper_simulation",
        ),
        _daily_manual_session_phase(
            3,
            "manual_ticket_review",
            "Manual ticket review",
            "manual_review_only" if ticket_count > 0 and not blocked else "locked",
            f"manual_tickets={ticket_count}; broker automation disabled.",
            "daily-manual-broker-handoff-ticket-table",
            "",
        ),
        _daily_manual_session_phase(
            4,
            "post_close_journal",
            "Post-close journal",
            "pass" if journal_count >= 5 else "required",
            f"post_close_journals={journal_count}/5.",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        _daily_manual_session_phase(
            5,
            "manual_execution_audit",
            "Manual execution audit",
            "pass" if manual_clean >= 5 and manual_blocked == 0 and manual_missing == 0 else "blocked" if manual_blocked or manual_missing else "required",
            f"clean={manual_clean}/5; blocked={manual_blocked}; missing={manual_missing}.",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]


def _daily_manual_session_phase(
    order: int,
    phase_id: str,
    label: str,
    status: str,
    evidence: str,
    target_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    return {
        "order": order,
        "phase_id": phase_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "order_placement_allowed": False,
    }


def _daily_manual_session_operator_checklist(
    *,
    session_status: str,
    selected_count: int,
    signal_count: int,
    ticket_count: int,
    matched_paper: int,
    journal_count: int,
    manual_clean: int,
    manual_execution_dirty: bool,
    manual_broker_review_candidate: bool,
) -> list[dict[str, Any]]:
    return [
        _daily_manual_session_step(
            1,
            "refresh_top3_signal",
            "Refresh today's Top3 CN_ETF signal",
            "pass" if selected_count > 0 and signal_count > 0 else "required",
            f"selected={selected_count}; signals={signal_count}.",
            "daily-trade-factor-table",
            "daily_trade_advisory",
        ),
        _daily_manual_session_step(
            2,
            "run_same_parameter_paper",
            "Run same-parameter paper simulation",
            "pass" if matched_paper >= 5 else "required",
            f"matched_paper_receipts={matched_paper}/5.",
            "paper-metrics",
            "paper_simulation",
        ),
        _daily_manual_session_step(
            3,
            "review_manual_tickets",
            "Review manual ETF tickets",
            "pass" if ticket_count > 0 else "required",
            f"manual_tickets={ticket_count}.",
            "daily-manual-broker-handoff-ticket-table",
            "",
        ),
        _daily_manual_session_step(
            4,
            "open_external_broker_manually",
            "Only the human may open an external broker app",
            "manual_review_only" if manual_broker_review_candidate else "locked",
            f"session_status={session_status}; software_ordering=false.",
            "beginner-live-handoff-board",
            "",
        ),
        _daily_manual_session_step(
            5,
            "record_post_close_journal",
            "Record post-close journal and manual execution audit",
            "blocked" if manual_execution_dirty else "pass" if journal_count >= 5 and manual_clean >= 5 else "required",
            f"post_close_journals={journal_count}/5; manual_clean={manual_clean}/5.",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]


def _daily_manual_session_step(
    order: int,
    step_id: str,
    label: str,
    status: str,
    evidence: str,
    target_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    return {
        "order": order,
        "step_id": step_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "manual_required": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _daily_manual_session_plain_answer(session_status: str) -> str:
    answers = {
        "blocked_pretrade_red_light": "Pretrade blockers remain; do not move toward broker-side action.",
        "blocked_risk_circuit_breaker": "Daily loss, drawdown, or cooldown circuit breaker is red; stay in paper mode and record a risk review.",
        "blocked_factor_health_rotation_required": "A Top3 factor needs retirement or lower weight before manual review.",
        "blocked_next_session_quarantine_required": "Top3 reuse evidence is incomplete; finish same-parameter paper, post-close journal, and execution audit before manual review.",
        "blocked_same_day_signal_required": "Generate today's CN_ETF signal before any manual review.",
        "blocked_manual_ticket_required": "Build manual tickets before any broker-side human review.",
        "blocked_same_parameter_paper_required": "Run and match same-parameter paper receipts before any manual-money session.",
        "blocked_post_close_journal_required": "Collect post-close journals before promoting the session.",
        "blocked_manual_execution_audit": "Manual execution evidence is dirty or missing; review before continuing.",
        "production_manual_review_candidate": "Evidence is strong enough for manual production review material, but the software still cannot trade.",
        "small_capital_manual_observation_candidate": "Evidence is strong enough for small-capital manual observation material, not automatic trading.",
        "paper_rehearsal_required": "Keep this as paper rehearsal and manual ticket review until more evidence is collected.",
    }
    return answers.get(session_status, "Review today's signal, paper receipts, manual tickets, and journal before any human decision.")


def _session_count(*values: Any) -> int:
    for value in values:
        number = _float_or_none(value)
        if number is not None:
            return int(number)
    return 0


def _liquidity_reference_from_row(row: dict[str, Any]) -> tuple[float | None, str | None]:
    for field in LIQUIDITY_REFERENCE_FIELDS:
        value = _float_or_none(row.get(field))
        if value is not None and value > 0:
            return value, field
    volume = _float_or_none(row.get("avg_daily_volume") or row.get("volume_ma20") or row.get("vol_ma20"))
    reference_price = _float_or_none(row.get("reference_price") or row.get("latest_price"))
    if volume is not None and volume > 0 and reference_price is not None and reference_price > 0:
        return volume * reference_price, "avg_daily_volume_x_price"
    return None, None


def _tradeability_metadata(row: dict[str, Any]) -> dict[str, Any]:
    liquidity_value, liquidity_field = _liquidity_reference_from_row(row)
    result: dict[str, Any] = {}
    if liquidity_value is not None:
        result["liquidity_reference_value"] = liquidity_value
        result["liquidity_reference_field"] = liquidity_field
    return result


def build_daily_paper_allocation_playbook(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    session = (
        pack.get("daily_manual_trading_session")
        if isinstance(pack.get("daily_manual_trading_session"), dict)
        else {}
    )
    session_summary = session.get("summary") if isinstance(session.get("summary"), dict) else {}
    transition = (
        pack.get("daily_real_money_transition_gate")
        if isinstance(pack.get("daily_real_money_transition_gate"), dict)
        else {}
    )
    transition_summary = transition.get("summary") if isinstance(transition.get("summary"), dict) else {}
    profitability = (
        pack.get("live_profitability_readiness")
        if isinstance(pack.get("live_profitability_readiness"), dict)
        else {}
    )
    profitability_summary = profitability.get("summary") if isinstance(profitability.get("summary"), dict) else {}
    health = pack.get("daily_factor_health_monitor") if isinstance(pack.get("daily_factor_health_monitor"), dict) else {}
    health_summary = health.get("summary") if isinstance(health.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    manual_tickets = _paper_allocation_ticket_source(pack, session, transition)
    portfolio_value = _float(summary.get("portfolio_value"), 100000.0)
    risk_profile = _risk_profile_by_id(str(summary.get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID))
    session_status = str(session_summary.get("session_status") or "paper_rehearsal_required")
    next_session_required_count = _int(health_summary.get("same_parameter_top3_required_requests"), 0)
    next_session_matched_count = _int(health_summary.get("same_parameter_top3_matched_requests"), 0)
    next_session_missing_from_counts = max(0, next_session_required_count - next_session_matched_count)
    next_session_quarantine_required = (
        bool(health_summary.get("next_session_quarantine_required"))
        or bool(session_summary.get("next_session_quarantine_required"))
        or session_status == "blocked_next_session_quarantine_required"
    )
    next_session_quarantine_blocks_manual = session_status == "blocked_next_session_quarantine_required"
    next_session_quarantine_missing_count = _session_count(
        session_summary.get("next_session_quarantine_missing_count"),
        transition_summary.get("next_session_quarantine_missing_count"),
        health_summary.get("next_session_quarantine_missing_count"),
        next_session_missing_from_counts,
    )
    hard_blocked_statuses = {
        "blocked_pretrade_red_light",
        "blocked_factor_health_rotation_required",
        "blocked_same_day_signal_required",
        "blocked_next_session_quarantine_required",
    }
    readiness_blockers = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    manual_broker_review_candidate = bool(session_summary.get("manual_broker_review_candidate"))
    allocation_rows = [
        _paper_allocation_row(index, row, portfolio_value=portfolio_value, risk_profile=risk_profile)
        for index, row in enumerate(manual_tickets, start=1)
    ]
    paper_only_position_gap = bool(allocation_rows) and bool(readiness_blockers) and all(
        blocker == "current_position_not_provided" for blocker in readiness_blockers
    )
    pretrade_blocked = (bool(readiness_blockers) and not paper_only_position_gap) or (
        session_status in hard_blocked_statuses and not paper_only_position_gap
    )
    risk_blocked = any(bool(row.get("risk_blocked")) for row in allocation_rows)
    if not allocation_rows:
        allocation_status = "blocked_no_allocation_rows"
    elif pretrade_blocked:
        allocation_status = session_status if session_status in hard_blocked_statuses else "blocked_pretrade_red_light"
    elif next_session_quarantine_blocks_manual:
        allocation_status = "blocked_next_session_quarantine_required"
    elif risk_blocked:
        allocation_status = "blocked_risk_budget"
    elif manual_broker_review_candidate:
        allocation_status = "manual_review_candidate"
    else:
        allocation_status = "paper_rehearsal_required"

    blocked = allocation_status.startswith("blocked")
    traffic_light = "red" if blocked else "yellow"
    execution_mode = "manual_review_candidate_not_order" if manual_broker_review_candidate and not blocked else "paper_rehearsal_only"
    for row in allocation_rows:
        row["execution_mode"] = execution_mode
    allocated_value = round(sum(_float(row.get("paper_budget_value"), 0.0) for row in allocation_rows), 6)
    residual_cash = round(max(0.0, portfolio_value - allocated_value), 6)
    promotion_gates = _paper_allocation_promotion_gates(
        summary=summary,
        session_summary=session_summary,
        transition_summary=transition_summary,
        profitability_summary=profitability_summary,
        health_summary=health_summary,
        allocation_rows=allocation_rows,
        allocation_status=allocation_status,
    )
    next_gate = next((row for row in promotion_gates if row.get("status") != "pass"), {})
    return _sanitize(
        {
            "stage": DAILY_PAPER_ALLOCATION_PLAYBOOK_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "allocation_status": allocation_status,
                "traffic_light": traffic_light,
                "plain_answer": _paper_allocation_plain_answer(allocation_status),
                "primary_market": str(session_summary.get("primary_market") or "CN_ETF"),
                "portfolio_value": portfolio_value,
                "allocated_value": allocated_value,
                "residual_cash_value": residual_cash,
                "allocation_row_count": len(allocation_rows),
                "selected_factor_count": _session_count(
                    session_summary.get("selected_factor_count"),
                    summary.get("selected_factor_count"),
                ),
                "signal_count": _session_count(session_summary.get("signal_count"), summary.get("signal_count")),
                "manual_ticket_count": _session_count(
                    session_summary.get("manual_ticket_count"),
                    summary.get("manual_ticket_count"),
                ),
                "matched_paper_receipts": _session_count(
                    session_summary.get("matched_paper_receipts"),
                    profitability_summary.get("matched_paper_receipts"),
                ),
                "manual_broker_review_candidate": manual_broker_review_candidate and not blocked,
                "paper_rehearsal_required": allocation_status == "paper_rehearsal_required",
                "next_session_quarantine_required": next_session_quarantine_required,
                "next_session_quarantine_missing_count": next_session_quarantine_missing_count,
                "next_session_reuse_status": str(
                    health_summary.get("next_session_reuse_status")
                    or session_summary.get("next_session_reuse_status")
                    or "waiting_for_top3_candidates"
                ),
                "risk_blocked": risk_blocked,
                "next_gate_id": next_gate.get("gate_id"),
                "next_target_id": next_gate.get("target_id") or "daily-paper-allocation-playbook",
                "next_workflow_id": next_gate.get("workflow_id") or "",
                "real_money_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "allocation_rows": allocation_rows,
            "promotion_gates": promotion_gates,
            "operator_steps": _paper_allocation_operator_steps(
                allocation_status=allocation_status,
                manual_broker_review_candidate=manual_broker_review_candidate and not blocked,
                allocation_row_count=len(allocation_rows),
            ),
            "forbidden_actions": _paper_allocation_forbidden_actions(),
            "source_manual_session_summary": session_summary,
            "execution_boundary": {
                "plain_boundary": "This playbook is for paper rehearsal and human review only; it is not an order router.",
                "manual_review_only": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
        }
    )


def _paper_allocation_ticket_source(
    pack: dict[str, Any],
    session: dict[str, Any],
    transition: dict[str, Any],
) -> list[dict[str, Any]]:
    metadata_lookup = _tradeability_metadata_lookup(pack)
    for source in (
        session.get("manual_ticket_preview"),
        transition.get("manual_execution_preview"),
        pack.get("manual_trade_plan"),
    ):
        rows = [row for row in source if isinstance(row, dict)] if isinstance(source, list) else []
        if rows:
            return [
                {
                    **_fill_missing_tradeability_metadata(row, metadata_lookup),
                    "source_kind": str(row.get("source_kind") or "manual_ticket"),
                }
                for row in rows
            ]
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    handoff_rows = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    if handoff_rows:
        return [
            {
                **_fill_missing_tradeability_metadata(row, metadata_lookup),
                "source_kind": str(row.get("source_kind") or "manual_ticket"),
            }
            for row in handoff_rows
        ]
    return [
        {**_fill_missing_tradeability_metadata(row, metadata_lookup), "source_kind": "combined_target"}
        for row in pack.get("combined_targets", [])
        if isinstance(row, dict)
    ]


def _tradeability_metadata_lookup(pack: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for source_name in ("combined_targets", "manual_trade_plan"):
        source = pack.get(source_name)
        rows = [row for row in source if isinstance(row, dict)] if isinstance(source, list) else []
        for row in rows:
            asset_id = str(row.get("asset_id") or "").strip()
            if not asset_id:
                continue
            metadata = _tradeability_metadata(row)
            if row.get("source_factors"):
                metadata["source_factors"] = row.get("source_factors")
            if metadata:
                lookup.setdefault(asset_id, {}).update(metadata)
    return lookup


def _fill_missing_tradeability_metadata(
    row: dict[str, Any],
    metadata_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    asset_id = str(row.get("asset_id") or "").strip()
    result = dict(row)
    for key, value in metadata_lookup.get(asset_id, {}).items():
        if result.get(key) in (None, "") and value not in (None, ""):
            result[key] = value
    return result


def _paper_allocation_row(
    index: int,
    row: dict[str, Any],
    *,
    portfolio_value: float,
    risk_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    reference_price = _float_or_none(row.get("reference_price") or row.get("latest_price"))
    target_weight = _float(row.get("target_weight"), 0.0)
    target_value = _float(row.get("target_value"), target_weight * portfolio_value)
    paper_quantity = _int(row.get("rounded_quantity"), 0)
    paper_budget_value = _float(row.get("rounded_value"), 0.0)
    if paper_quantity <= 0 and reference_price and reference_price > 0:
        paper_quantity = int(target_value / reference_price / BOARD_LOT_SIZE) * BOARD_LOT_SIZE
    if paper_budget_value <= 0:
        paper_budget_value = paper_quantity * reference_price if reference_price else target_value
    liquidity_reference_value, liquidity_reference_field = _liquidity_reference_from_row(
        {**row, "reference_price": reference_price}
    )
    risk_budget = (
        row.get("risk_budget")
        if isinstance(row.get("risk_budget"), dict)
        else _manual_ticket_risk_budget(
            {**row, "rounded_value": paper_budget_value, "target_weight": target_weight},
            portfolio_value=portfolio_value,
            risk_profile=risk_profile,
        )
    )
    risk_blocked = bool(risk_budget.get("single_etf_limit_breached")) or bool(
        risk_budget.get("rounded_value_limit_breached")
    )
    return {
        "row_number": index,
        "ticket_id": row.get("ticket_id") or f"paper-allocation-{index:03d}",
        "asset_id": row.get("asset_id"),
        "market": row.get("market") or "CN_ETF",
        "side": row.get("side") or "buy_or_adjust",
        "target_weight": round(target_weight, 10),
        "target_value": round(target_value, 6),
        "reference_price": reference_price,
        "paper_quantity": paper_quantity,
        "paper_budget_value": round(paper_budget_value, 6),
        "residual_rounding_cash": round(max(0.0, target_value - paper_budget_value), 6),
        "liquidity_reference_value": (
            round(liquidity_reference_value, 6) if liquidity_reference_value is not None else None
        ),
        "liquidity_reference_field": liquidity_reference_field,
        "liquidity_evidence_missing": liquidity_reference_value is None,
        "max_participation_rate": MANUAL_MAX_PARTICIPATION_RATE,
        "source_factors": row.get("source_factors"),
        "source_kind": row.get("source_kind") or "manual_ticket",
        "risk_budget": risk_budget,
        "risk_blocked": risk_blocked,
        "plain_instruction": "Use this row in same-parameter paper rehearsal first; do not copy it as a broker order.",
        "execution_mode": "paper_rehearsal_only",
        "automation_allowed": False,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _paper_allocation_promotion_gates(
    *,
    summary: dict[str, Any],
    session_summary: dict[str, Any],
    transition_summary: dict[str, Any],
    profitability_summary: dict[str, Any],
    health_summary: dict[str, Any],
    allocation_rows: list[dict[str, Any]],
    allocation_status: str,
) -> list[dict[str, Any]]:
    selected = _session_count(session_summary.get("selected_factor_count"), summary.get("selected_factor_count"))
    signals = _session_count(session_summary.get("signal_count"), summary.get("signal_count"))
    tickets = len(allocation_rows)
    manual_ticket_count = _session_count(session_summary.get("manual_ticket_count"), summary.get("manual_ticket_count"))
    matched_paper = _session_count(
        session_summary.get("matched_paper_receipts"),
        transition_summary.get("matched_paper_receipts"),
        profitability_summary.get("matched_paper_receipts"),
    )
    journals = _session_count(
        session_summary.get("post_close_journal_receipts"),
        transition_summary.get("post_close_journal_receipts"),
        profitability_summary.get("post_close_journal_receipts"),
    )
    clean_manual = _session_count(
        session_summary.get("manual_execution_clean_receipts"),
        transition_summary.get("manual_execution_clean_receipts"),
        profitability_summary.get("manual_execution_clean_receipts"),
    )
    research_ready = all(
        bool(profitability_summary.get(key))
        for key in (
            "walk_forward_oos_passed",
            "lookahead_bias_audit_passed",
            "multiple_testing_control_passed",
            "transaction_cost_capacity_passed",
        )
    ) or str(transition_summary.get("research_evidence_status") or "") == "pass"
    factor_health_ok = not bool(health_summary.get("retirement_required_before_live"))
    next_session_required_count = _int(health_summary.get("same_parameter_top3_required_requests"), 0)
    next_session_matched_count = _int(health_summary.get("same_parameter_top3_matched_requests"), 0)
    next_session_missing_from_counts = max(0, next_session_required_count - next_session_matched_count)
    next_session_quarantine_required = bool(
        health_summary.get("next_session_quarantine_required")
        or session_summary.get("next_session_quarantine_required")
        or transition_summary.get("next_session_quarantine_required")
        or allocation_status == "blocked_next_session_quarantine_required"
    )
    next_session_quarantine_missing_count = _session_count(
        session_summary.get("next_session_quarantine_missing_count"),
        transition_summary.get("next_session_quarantine_missing_count"),
        health_summary.get("next_session_quarantine_missing_count"),
        next_session_missing_from_counts,
    )
    risk_ok = allocation_status != "blocked_risk_budget"

    def gate(
        gate_id: str,
        label: str,
        passed: bool,
        evidence: str,
        target_id: str,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        return {
            "gate_id": gate_id,
            "label": label,
            "status": "pass" if passed else "required",
            "evidence": evidence,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "order_placement_allowed": False,
        }

    return [
        gate(
            "top3_same_day_signal",
            "Top3 same-day signal",
            selected > 0 and signals > 0,
            f"selected={selected}; signals={signals}.",
            "daily-trade-factor-table",
            "daily_trade_advisory" if signals <= 0 else "",
        ),
        gate(
            "paper_allocation_rows",
            "Paper allocation rows",
            tickets > 0,
            f"allocation_rows={tickets}.",
            "daily-paper-allocation-playbook",
        ),
        gate(
            "manual_ticket_pack",
            "Manual ticket pack",
            manual_ticket_count > 0,
            f"manual_tickets={manual_ticket_count}; combined-target rows may still be rehearsed in paper mode.",
            "daily-manual-broker-handoff-ticket-table",
            "daily_trade_advisory" if manual_ticket_count <= 0 else "",
        ),
        gate(
            "risk_budget",
            "Risk budget and lot sizing",
            risk_ok,
            f"risk_blocked={not risk_ok}.",
            "daily-paper-allocation-playbook",
        ),
        gate(
            "factor_health",
            "Factor health",
            factor_health_ok,
            str(health_summary.get("decision") or "unknown"),
            "daily-factor-health-rows",
        ),
        gate(
            "next_session_quarantine",
            "Next-session Top3 reuse quarantine",
            not next_session_quarantine_required,
            f"quarantine_required={next_session_quarantine_required}; missing={next_session_quarantine_missing_count}.",
            "daily-factor-health-rows",
            "paper_simulation" if next_session_quarantine_required else "",
        ),
        gate(
            "research_evidence",
            "OOS, lookahead, multiple-test, cost-capacity evidence",
            research_ready,
            f"research_ready={research_ready}.",
            "control-backtest-gate",
        ),
        gate(
            "same_parameter_paper",
            "Same-parameter paper receipts",
            matched_paper >= 5,
            f"matched_paper_receipts={matched_paper}/5.",
            "paper-metrics",
            "paper_simulation",
        ),
        gate(
            "post_close_journal",
            "Post-close journal receipts",
            journals >= 5,
            f"post_close_journals={journals}/5.",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        gate(
            "manual_execution_audit",
            "Clean manual execution audit",
            clean_manual >= 5,
            f"clean_manual_execution_receipts={clean_manual}/5.",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]


def _paper_allocation_operator_steps(
    *,
    allocation_status: str,
    manual_broker_review_candidate: bool,
    allocation_row_count: int,
) -> list[dict[str, Any]]:
    def step(step_id: str, label: str, status: str, target_id: str, workflow_id: str = "") -> dict[str, Any]:
        return {
            "step_id": step_id,
            "label": label,
            "status": status,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "manual_required": True,
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }

    steps = [
        step(
            "review_allocation_rows",
            "Review paper allocation rows",
            "pass" if allocation_row_count > 0 else "required",
            "daily-paper-allocation-playbook",
        ),
        step(
            "run_same_parameter_paper",
            "Run same-parameter paper rehearsal",
            "required"
            if allocation_status in {"paper_rehearsal_required", "blocked_next_session_quarantine_required"}
            else "pass",
            "paper-metrics",
            "paper_simulation",
        ),
        step(
            "record_post_close_journal",
            "Record post-close result and skip/execute reason",
            "required",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]
    if manual_broker_review_candidate:
        steps.append(
            step(
                "open_external_broker_manually_if_human_chooses",
                "Human may open an external broker app after reviewing all gates",
                "manual_review_only",
                "daily-manual-trading-session",
            )
        )
    else:
        steps.append(
            step(
                "keep_inside_paper_mode",
                "Keep this playbook inside paper rehearsal",
                "required"
                if allocation_status == "blocked_next_session_quarantine_required"
                else "locked"
                if allocation_status.startswith("blocked")
                else "required",
                "paper-metrics",
                "paper_simulation",
            )
        )
    return steps


def _paper_allocation_forbidden_actions() -> list[dict[str, Any]]:
    rows = [
        ("do_not_copy_to_broker", "Do not copy paper rows into a broker ticket as-is."),
        ("skip_same_parameter_paper", "Do not skip the same-parameter paper rehearsal."),
        ("treat_allocation_as_order", "Do not treat allocation rows as executable orders."),
        ("ignore_risk_budget", "Do not ignore single ETF caps, lot sizing, cash, or slippage guardrails."),
    ]
    return [
        {
            "action_id": action_id,
            "plain_rule": plain_rule,
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }
        for action_id, plain_rule in rows
    ]


def _paper_allocation_plain_answer(allocation_status: str) -> str:
    answers = {
        "blocked_no_allocation_rows": "No allocation rows exist; generate today's Top3 signal and manual ticket pack first.",
        "blocked_pretrade_red_light": "Pretrade blockers remain; do not rehearse or review broker-side action yet.",
        "blocked_factor_health_rotation_required": "A Top3 factor needs retirement or lower weight before allocation rehearsal.",
        "blocked_same_day_signal_required": "Generate today's same-day CN_ETF signal before allocation rehearsal.",
        "blocked_next_session_quarantine_required": "Top3 reuse evidence is incomplete; keep the rows in same-parameter paper rehearsal and do not move them to broker review.",
        "blocked_manual_ticket_required": "Build manual ticket rows before allocation rehearsal.",
        "blocked_risk_budget": "Risk budget or lot sizing is breached; reduce exposure before rehearsal.",
        "manual_review_candidate": "Evidence is sufficient for human manual review material; the software still cannot submit orders.",
        "paper_rehearsal_required": "Use these rows for same-parameter paper rehearsal and collect receipts before any human broker review.",
    }
    return answers.get(allocation_status, "Review allocation rows in paper mode before any human decision.")


def build_daily_execution_risk_circuit_breaker(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    evidence = (
        pack.get("live_profitability_evidence_snapshot")
        if isinstance(pack.get("live_profitability_evidence_snapshot"), dict)
        else _live_profitability_evidence_snapshot(pack.get("live_profitability_evidence_snapshot"))
    )
    risk_state = evidence.get("risk_state") if isinstance(evidence.get("risk_state"), dict) else {}
    risk_profile = _risk_profile_by_id(str(summary.get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID)) or {}
    daily_loss_limit = max(0.0, _float(risk_profile.get("daily_loss_stop"), 0.02))
    max_drawdown_limit = max(0.0, _float(risk_profile.get("max_acceptable_drawdown"), 0.20))
    today_pnl_pct = _float_or_none(risk_state.get("today_pnl_pct"))
    today_loss_pct = _float_or_none(risk_state.get("today_loss_pct"))
    observed_loss_pct = 0.0
    if today_pnl_pct is not None and today_pnl_pct < 0:
        observed_loss_pct = abs(today_pnl_pct)
    if today_loss_pct is not None:
        observed_loss_pct = max(observed_loss_pct, abs(today_loss_pct))
    current_drawdown_pct = _float_or_none(risk_state.get("current_drawdown_pct"))
    observed_drawdown_pct = abs(current_drawdown_pct) if current_drawdown_pct is not None else 0.0
    consecutive_loss_days = _int(risk_state.get("consecutive_loss_days"), 0)
    cooldown_days_remaining = _int(risk_state.get("cooldown_days_remaining"), 0)
    risk_state_observed = any(
        value is not None
        for value in (
            today_pnl_pct,
            today_loss_pct,
            current_drawdown_pct,
            _float_or_none(risk_state.get("consecutive_loss_days")),
            _float_or_none(risk_state.get("cooldown_days_remaining")),
        )
    )
    daily_loss_blocked = risk_state_observed and observed_loss_pct >= daily_loss_limit - 1e-12 and daily_loss_limit > 0
    drawdown_blocked = risk_state_observed and observed_drawdown_pct >= max_drawdown_limit - 1e-12 and max_drawdown_limit > 0
    consecutive_loss_blocked = consecutive_loss_days >= MANUAL_MAX_CONSECUTIVE_LOSS_DAYS
    cooldown_blocked = cooldown_days_remaining > 0
    blocked = any(
        (
            daily_loss_blocked,
            drawdown_blocked,
            consecutive_loss_blocked,
            cooldown_blocked,
        )
    )
    decision = (
        "blocked_risk_circuit_breaker"
        if blocked
        else "risk_clear_for_manual_review"
        if risk_state_observed
        else "risk_state_not_observed"
    )
    rules = [
        _risk_circuit_rule(
            "daily_loss_stop",
            "blocked" if daily_loss_blocked else "pass",
            observed_loss_pct,
            daily_loss_limit,
            "Today's loss has reached the selected risk profile's daily stop.",
            "beginner-post-close-journal-board",
        ),
        _risk_circuit_rule(
            "max_drawdown_stop",
            "blocked" if drawdown_blocked else "pass",
            observed_drawdown_pct,
            max_drawdown_limit,
            "Current drawdown has reached the selected risk profile's drawdown budget.",
            "paper-metrics",
        ),
        _risk_circuit_rule(
            "consecutive_loss_days",
            "blocked" if consecutive_loss_blocked else "pass",
            consecutive_loss_days,
            MANUAL_MAX_CONSECUTIVE_LOSS_DAYS,
            "Too many consecutive loss days; pause manual review and audit the strategy.",
            "beginner-post-close-journal-board",
        ),
        _risk_circuit_rule(
            "cooldown_active",
            "blocked" if cooldown_blocked else "pass",
            cooldown_days_remaining,
            0,
            "A cooldown is active; do not promote today's signal to manual broker review.",
            "daily-pre-execution-guard",
        ),
    ]
    return _sanitize(
        {
            "stage": DAILY_EXECUTION_RISK_CIRCUIT_BREAKER_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "decision": decision,
                "traffic_light": "red" if blocked else "yellow",
                "plain_answer": _risk_circuit_plain_answer(decision),
                "risk_state_observed": risk_state_observed,
                "risk_profile_id": risk_profile.get("profile_id") or summary.get("risk_profile_id"),
                "today_pnl_pct": today_pnl_pct,
                "observed_loss_pct": observed_loss_pct,
                "daily_loss_stop": daily_loss_limit,
                "current_drawdown_pct": current_drawdown_pct,
                "observed_drawdown_pct": observed_drawdown_pct,
                "max_acceptable_drawdown": max_drawdown_limit,
                "consecutive_loss_days": consecutive_loss_days,
                "max_consecutive_loss_days": MANUAL_MAX_CONSECUTIVE_LOSS_DAYS,
                "cooldown_days_remaining": cooldown_days_remaining,
                "risk_circuit_blocked": blocked,
                "paper_rehearsal_allowed": True,
                "manual_broker_review_allowed": not blocked,
                "can_buy_today": False,
                "real_money_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "next_rule_id": next((row.get("rule_id") for row in rules if row.get("status") == "blocked"), None),
            },
            "rules": rules,
            "operator_steps": _risk_circuit_operator_steps(blocked),
            "source_risk_state": risk_state,
            "execution_boundary": {
                "plain_boundary": "This circuit breaker can only block or downgrade manual review; it never submits orders.",
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
        }
    )


def _risk_circuit_rule(
    rule_id: str,
    status: str,
    observed_value: float | int,
    limit_value: float | int,
    plain_rule: str,
    target_id: str,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "status": status,
        "observed_value": observed_value,
        "limit_value": limit_value,
        "plain_rule": plain_rule,
        "target_id": target_id,
        "workflow_id": "post_close_journal" if status == "blocked" else "",
        "manual_review_allowed": status != "blocked",
        "order_placement_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "auto_order_allowed": False,
    }


def _risk_circuit_plain_answer(decision: str) -> str:
    answers = {
        "blocked_risk_circuit_breaker": "Risk circuit breaker is red; keep today's rows in paper mode and do not enter broker review.",
        "risk_clear_for_manual_review": "Risk circuit breaker is clear for manual review material; the software still cannot place orders.",
        "risk_state_not_observed": "No daily risk state was provided; keep reviewing risk manually before any external broker action.",
    }
    return answers.get(decision, "Review daily loss, drawdown, consecutive losses, and cooldown state before any human decision.")


def _risk_circuit_operator_steps(blocked: bool) -> list[dict[str, Any]]:
    if blocked:
        rows = [
            ("stay_in_paper_mode", "Stay in paper mode and do not enter broker review", "required", "paper-metrics", "paper_simulation"),
            ("record_risk_event", "Record the loss, drawdown, or cooldown reason", "required", "beginner-post-close-journal-board", "post_close_journal"),
            ("audit_strategy_before_next_signal", "Audit factor, regime, and execution evidence before the next signal", "required", "daily-factor-health-rows", ""),
        ]
    else:
        rows = [
            ("review_daily_risk_state", "Review daily loss, drawdown, and cooldown state", "required", "daily-pre-execution-guard", ""),
            ("continue_manual_review_material_only", "Continue only as manual review material after all other guards pass", "manual_review_only", "daily-manual-trading-session", ""),
        ]
    return [
        {
            "step_id": step_id,
            "label": label,
            "status": status,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "manual_required": True,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
        for step_id, label, status, target_id, workflow_id in rows
    ]


def build_daily_pre_execution_guard(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    playbook = (
        pack.get("daily_paper_allocation_playbook")
        if isinstance(pack.get("daily_paper_allocation_playbook"), dict)
        else build_daily_paper_allocation_playbook(pack)
    )
    playbook_summary = playbook.get("summary") if isinstance(playbook.get("summary"), dict) else {}
    risk_circuit = (
        pack.get("daily_execution_risk_circuit_breaker")
        if isinstance(pack.get("daily_execution_risk_circuit_breaker"), dict)
        else build_daily_execution_risk_circuit_breaker(pack)
    )
    risk_circuit_summary = risk_circuit.get("summary") if isinstance(risk_circuit.get("summary"), dict) else {}
    allocation_rows = [row for row in playbook.get("allocation_rows", []) if isinstance(row, dict)]
    guardrails = [_pre_execution_row_guardrail(row) for row in allocation_rows]
    signal_fresh = freshness.get("fresh_for_run_date") is True
    manual_ticket_count = _session_count(
        playbook_summary.get("manual_ticket_count"),
        summary.get("manual_ticket_count"),
    )
    manual_candidate = bool(playbook_summary.get("manual_broker_review_candidate"))
    next_session_quarantine_required = (
        bool(playbook_summary.get("next_session_quarantine_required"))
        or str(playbook_summary.get("allocation_status") or "") == "blocked_next_session_quarantine_required"
    )
    next_session_quarantine_blocks_manual = (
        str(playbook_summary.get("allocation_status") or "") == "blocked_next_session_quarantine_required"
    )
    has_rows = bool(guardrails)
    risk_blocked = any(bool(row.get("risk_blocked")) for row in guardrails)
    capacity_blocked = any(bool(row.get("capacity_blocked")) for row in guardrails)
    risk_circuit_blocked = bool(risk_circuit_summary.get("risk_circuit_blocked"))
    liquidity_evidence_missing = any(bool(row.get("liquidity_evidence_missing")) for row in guardrails)
    price_missing = any(row.get("reference_price") is None or _int(row.get("paper_quantity"), 0) <= 0 for row in guardrails)

    if not signal_fresh:
        guard_status = "blocked_signal_freshness"
    elif not has_rows:
        guard_status = "blocked_no_allocation_rows"
    elif risk_blocked:
        guard_status = "blocked_risk_budget"
    elif risk_circuit_blocked:
        guard_status = "blocked_risk_circuit_breaker"
    elif capacity_blocked:
        guard_status = "blocked_liquidity_capacity"
    elif price_missing:
        guard_status = "blocked_price_reference"
    elif next_session_quarantine_blocks_manual:
        guard_status = "blocked_next_session_quarantine_required"
    elif manual_candidate:
        guard_status = "manual_review_candidate"
    else:
        guard_status = "paper_rehearsal_only"

    blocked = guard_status.startswith("blocked")
    traffic_light = "red" if blocked else "yellow"
    paper_rehearsal_allowed = guard_status in {
        "paper_rehearsal_only",
        "manual_review_candidate",
        "blocked_next_session_quarantine_required",
        "blocked_liquidity_capacity",
        "blocked_risk_circuit_breaker",
    }
    manual_broker_review_allowed = guard_status == "manual_review_candidate"
    skip_rules = _pre_execution_skip_rules(
        guard_status=guard_status,
        signal_fresh=signal_fresh,
        manual_ticket_count=manual_ticket_count,
        has_rows=has_rows,
        risk_blocked=risk_blocked,
        risk_circuit_blocked=risk_circuit_blocked,
        risk_circuit_decision=str(risk_circuit_summary.get("decision") or ""),
        capacity_blocked=capacity_blocked,
        price_missing=price_missing,
        next_session_quarantine_required=next_session_quarantine_required,
        next_session_quarantine_blocks_manual=next_session_quarantine_blocks_manual,
    )
    return _sanitize(
        {
            "stage": DAILY_PRE_EXECUTION_GUARD_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "guard_status": guard_status,
                "traffic_light": traffic_light,
                "plain_answer": _pre_execution_plain_answer(guard_status),
                "primary_market": str(playbook_summary.get("primary_market") or "CN_ETF"),
                "allocation_row_count": len(guardrails),
                "manual_ticket_count": manual_ticket_count,
                "signal_fresh": signal_fresh,
                "risk_circuit_decision": risk_circuit_summary.get("decision"),
                "risk_circuit_blocked": risk_circuit_blocked,
                "daily_loss_stop": risk_circuit_summary.get("daily_loss_stop"),
                "observed_loss_pct": risk_circuit_summary.get("observed_loss_pct"),
                "max_acceptable_drawdown": risk_circuit_summary.get("max_acceptable_drawdown"),
                "observed_drawdown_pct": risk_circuit_summary.get("observed_drawdown_pct"),
                "liquidity_evidence_missing": liquidity_evidence_missing,
                "capacity_blocked": capacity_blocked,
                "max_participation_rate": MANUAL_MAX_PARTICIPATION_RATE,
                "run_date": freshness.get("run_date") or pack.get("run_date"),
                "latest_signal_date": freshness.get("latest_signal_date"),
                "paper_rehearsal_allowed": paper_rehearsal_allowed,
                "manual_broker_review_allowed": manual_broker_review_allowed,
                "can_buy_today": False,
                "real_money_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
                "next_rule_id": next((row.get("rule_id") for row in skip_rules if row.get("status") != "pass"), None),
            },
            "row_guardrails": guardrails,
            "skip_rules": skip_rules,
            "operator_steps": _pre_execution_operator_steps(
                guard_status=guard_status,
                paper_rehearsal_allowed=paper_rehearsal_allowed,
                manual_broker_review_allowed=manual_broker_review_allowed,
            ),
            "source_playbook_summary": playbook_summary,
            "source_risk_circuit_summary": risk_circuit_summary,
            "execution_boundary": {
                "plain_boundary": "This guard only tells the human whether paper rehearsal or manual review is allowed; it never submits orders.",
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
        }
    )


def _pre_execution_row_guardrail(row: dict[str, Any]) -> dict[str, Any]:
    reference_price = _float_or_none(row.get("reference_price"))
    paper_value = max(0.0, _float(row.get("paper_budget_value"), 0.0))
    liquidity_reference_value, liquidity_reference_field = _liquidity_reference_from_row(row)
    participation_rate = (
        paper_value / liquidity_reference_value
        if liquidity_reference_value is not None and liquidity_reference_value > 0
        else None
    )
    capacity_blocked = bool(
        participation_rate is not None and participation_rate > MANUAL_MAX_PARTICIPATION_RATE + 1e-12
    )
    lower = round(reference_price * (1 - MANUAL_PRICE_DEVIATION_GUARD_PCT), 6) if reference_price else None
    upper = round(reference_price * (1 + MANUAL_PRICE_DEVIATION_GUARD_PCT), 6) if reference_price else None
    return {
        "row_number": _int(row.get("row_number"), 0),
        "asset_id": row.get("asset_id"),
        "market": row.get("market") or "CN_ETF",
        "side": row.get("side") or "buy_or_adjust",
        "execution_mode": row.get("execution_mode") or "paper_rehearsal_only",
        "source_kind": row.get("source_kind") or "manual_ticket",
        "target_weight": _float_or_none(row.get("target_weight")),
        "paper_budget_value": round(paper_value, 6),
        "paper_quantity": _int(row.get("paper_quantity"), 0),
        "reference_price": reference_price,
        "lower_price_bound": lower,
        "upper_price_bound": upper,
        "max_reference_price_deviation_pct": MANUAL_PRICE_DEVIATION_GUARD_PCT,
        "max_slippage_bps": MANUAL_MAX_SLIPPAGE_BPS,
        "max_estimated_slippage_cost": round(paper_value * MANUAL_MAX_SLIPPAGE_BPS / 10000, 6),
        "liquidity_reference_value": (
            round(liquidity_reference_value, 6) if liquidity_reference_value is not None else None
        ),
        "liquidity_reference_field": liquidity_reference_field,
        "liquidity_evidence_missing": liquidity_reference_value is None,
        "participation_rate": round(participation_rate, 10) if participation_rate is not None else None,
        "max_participation_rate": MANUAL_MAX_PARTICIPATION_RATE,
        "capacity_blocked": capacity_blocked,
        "risk_blocked": bool(row.get("risk_blocked")),
        "risk_budget": row.get("risk_budget") if isinstance(row.get("risk_budget"), dict) else {},
        "skip_if_price_outside_guardrail": True,
        "skip_if_quantity_zero": _int(row.get("paper_quantity"), 0) <= 0,
        "order_placement_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "auto_order_allowed": False,
    }


def _pre_execution_skip_rules(
    *,
    guard_status: str,
    signal_fresh: bool,
    manual_ticket_count: int,
    has_rows: bool,
    risk_blocked: bool,
    risk_circuit_blocked: bool,
    risk_circuit_decision: str,
    capacity_blocked: bool,
    price_missing: bool,
    next_session_quarantine_required: bool,
    next_session_quarantine_blocks_manual: bool,
) -> list[dict[str, Any]]:
    rows = [
        (
            "stale_signal_date",
            "pass" if signal_fresh else "blocked",
            "Skip today if the latest signal date does not match the run date.",
            "recent-data-refresh-status",
            "daily_trade_advisory" if not signal_fresh else "",
        ),
        (
            "paper_allocation_missing",
            "pass" if has_rows else "blocked",
            "Skip execution review when no paper allocation rows exist.",
            "daily-paper-allocation-playbook",
            "daily_trade_advisory" if not has_rows else "",
        ),
        (
            "manual_ticket_missing",
            "pass" if manual_ticket_count > 0 else "paper_only",
            "Without manual tickets, only same-parameter paper rehearsal is allowed.",
            "daily-manual-broker-handoff-ticket-table",
            "daily_trade_advisory" if manual_ticket_count <= 0 else "",
        ),
        (
            "risk_budget_breached",
            "blocked" if risk_blocked else "pass",
            "Skip rows whose single-ETF cap, lot sizing, or risk budget is breached.",
            "daily-paper-allocation-playbook",
            "",
        ),
        (
            "daily_risk_circuit_breaker",
            "blocked" if risk_circuit_blocked else "pass",
            "Skip manual broker review when daily loss, drawdown, consecutive loss, or cooldown circuit breaker is red.",
            "beginner-post-close-journal-board" if risk_circuit_blocked else "daily-pre-execution-guard",
            "post_close_journal" if risk_circuit_blocked else "",
        ),
        (
            "liquidity_capacity_breached",
            "blocked" if capacity_blocked else "pass",
            "Skip broker review when a paper row exceeds the maximum participation rate versus ETF turnover.",
            "daily-pre-execution-guard",
            "paper_simulation" if capacity_blocked else "",
        ),
        (
            "price_reference_missing",
            "blocked" if price_missing else "pass",
            "Skip rows without reference price or valid board-lot quantity.",
            "daily-paper-allocation-playbook",
            "",
        ),
        (
            "next_session_quarantine",
            "blocked"
            if next_session_quarantine_blocks_manual
            else "paper_only"
            if next_session_quarantine_required
            else "pass",
            "Finish same-parameter Top3 paper, post-close journal, and execution audit before manual broker review.",
            "daily-factor-health-rows",
            "paper_simulation" if next_session_quarantine_required else "",
        ),
        (
            "broker_price_outside_guardrail",
            "required" if guard_status == "manual_review_candidate" else "paper_only",
            "If the external broker price is outside the guardrail, skip or regenerate the plan.",
            "daily-pre-execution-guard",
            "",
        ),
        (
            "manual_discomfort",
            "required",
            "If the human cannot explain the reason, drawdown budget, and skip trigger, do not proceed.",
            "daily-pre-execution-guard",
            "",
        ),
    ]
    return [
        {
            "rule_id": rule_id,
            "status": status,
            "plain_rule": plain_rule,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }
        for rule_id, status, plain_rule, target_id, workflow_id in rows
    ]


def _pre_execution_operator_steps(
    *,
    guard_status: str,
    paper_rehearsal_allowed: bool,
    manual_broker_review_allowed: bool,
) -> list[dict[str, Any]]:
    def step(step_id: str, label: str, status: str, target_id: str, workflow_id: str = "") -> dict[str, Any]:
        return {
            "step_id": step_id,
            "label": label,
            "status": status,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "manual_required": True,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }

    if guard_status == "blocked_signal_freshness":
        return [
            step("refresh_cn_etf_data", "Refresh CN_ETF data and regenerate today's signal", "blocked", "recent-data-refresh-status", "daily_trade_advisory"),
            step("do_not_trade_stale_signal", "Do not rehearse or manually review stale signals", "forbidden", "daily-pre-execution-guard"),
            step("review_paper_allocation_rows", "Review ETF, weight, budget, quantity, and cash after fresh signals exist", "locked", "daily-paper-allocation-playbook"),
            step("verify_realtime_price_guardrail", "Compare external real-time price with the guardrail only after fresh signals exist", "locked", "daily-pre-execution-guard"),
            step("run_same_parameter_paper", "Run same-parameter paper rehearsal only after the freshness gate passes", "locked", "paper-metrics"),
            step("record_post_close_journal", "Record the skip reason and refresh result after the session", "required", "beginner-post-close-journal-board", "post_close_journal"),
        ]
    steps = [
        step("review_paper_allocation_rows", "Review ETF, weight, budget, quantity, and cash", "pass" if paper_rehearsal_allowed else "blocked", "daily-paper-allocation-playbook"),
        step("verify_realtime_price_guardrail", "Compare external real-time price with the guardrail before any human action", "required" if paper_rehearsal_allowed else "locked", "daily-pre-execution-guard"),
        step("run_same_parameter_paper", "Run same-parameter paper rehearsal", "required" if paper_rehearsal_allowed else "locked", "paper-metrics", "paper_simulation" if paper_rehearsal_allowed else ""),
        step("record_post_close_journal", "Record outcome, skip reason, and price/slippage observation", "required", "beginner-post-close-journal-board", "post_close_journal"),
    ]
    if manual_broker_review_allowed:
        steps.append(
            step(
                "open_external_broker_manually_if_human_chooses",
                "Only the human may open an external broker app after every guard passes",
                "manual_review_only",
                "daily-manual-trading-session",
            )
        )
    else:
        steps.append(step("stay_in_paper_mode", "Stay in paper mode until tickets and evidence are complete", "required", "paper-metrics", "paper_simulation"))
    return steps


def _pre_execution_plain_answer(guard_status: str) -> str:
    answers = {
        "blocked_signal_freshness": "Today's signal is stale; refresh CN_ETF data and regenerate the signal before any rehearsal or manual review.",
        "blocked_no_allocation_rows": "No allocation rows exist; generate today's Top3 CN_ETF signal first.",
        "blocked_risk_budget": "Risk budget is breached; reduce exposure or skip the row before rehearsal.",
        "blocked_risk_circuit_breaker": "Daily loss, drawdown, or cooldown circuit breaker is red; stay in paper mode and record a risk review.",
        "blocked_liquidity_capacity": "A row is too large versus ETF turnover; keep it in same-parameter paper rehearsal and reduce size before broker review.",
        "blocked_price_reference": "A row lacks reference price or valid quantity; skip or regenerate before review.",
        "blocked_next_session_quarantine_required": "Top3 reuse evidence is incomplete; only same-parameter paper rehearsal is allowed today.",
        "manual_review_candidate": "Manual review material is available, but buying remains an external human decision and the software cannot place orders.",
        "paper_rehearsal_only": "Only same-parameter paper rehearsal is allowed; do not copy rows into a broker ticket.",
    }
    return answers.get(guard_status, "Review freshness, allocation rows, price guardrails, and skip rules before any human decision.")


def build_daily_same_parameter_paper_rehearsal(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    combined_targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    playbook = (
        pack.get("daily_paper_allocation_playbook")
        if isinstance(pack.get("daily_paper_allocation_playbook"), dict)
        else build_daily_paper_allocation_playbook(pack)
    )
    pre_execution = (
        pack.get("daily_pre_execution_guard")
        if isinstance(pack.get("daily_pre_execution_guard"), dict)
        else build_daily_pre_execution_guard(pack)
    )
    pre_summary = pre_execution.get("summary") if isinstance(pre_execution.get("summary"), dict) else {}
    playbook_summary = playbook.get("summary") if isinstance(playbook.get("summary"), dict) else {}
    allocation_rows = [row for row in playbook.get("allocation_rows", []) if isinstance(row, dict)]
    market = str(pack.get("market") or _first_market(factors) or "CN_ETF").upper()
    portfolio_value = _float(summary.get("portfolio_value"), 100000.0)
    risk_profile_id = str(summary.get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID)
    risk_profile = _risk_profile_by_id(risk_profile_id)
    signal_as_of = _same_parameter_signal_as_of(pack, signal_cards, pre_summary)
    requests = [
        _same_parameter_paper_request(
            row,
            index=index,
            pack=pack,
            market=market,
            portfolio_value=portfolio_value,
            signal_as_of=signal_as_of,
            risk_profile_id=risk_profile_id,
            risk_profile=risk_profile,
            summary=summary,
        )
        for index, row in enumerate(factors[:3], start=1)
    ]
    combined_manifest = [_same_parameter_combined_manifest_row(index, row) for index, row in enumerate(combined_targets, 1)]
    allocation_manifest = [_same_parameter_allocation_manifest_row(row) for row in allocation_rows]
    guard_status = str(pre_summary.get("guard_status") or "blocked_no_allocation_rows")
    risk_blocked = bool(playbook_summary.get("risk_blocked")) or any(bool(row.get("risk_blocked")) for row in allocation_rows)
    price_missing = any(row.get("reference_price") is None or _int(row.get("paper_quantity"), 0) <= 0 for row in allocation_rows)
    if guard_status == "blocked_signal_freshness":
        rehearsal_status = "blocked_signal_freshness"
    elif not allocation_manifest:
        rehearsal_status = "blocked_no_allocation_rows"
    elif risk_blocked:
        rehearsal_status = "blocked_risk_budget"
    elif price_missing:
        rehearsal_status = "blocked_price_reference"
    elif guard_status == "manual_review_candidate":
        rehearsal_status = "manual_review_candidate"
    elif requests:
        rehearsal_status = "ready_for_same_parameter_paper"
    else:
        rehearsal_status = "waiting_for_top3_requests"
    paper_allowed = rehearsal_status in {"ready_for_same_parameter_paper", "manual_review_candidate"}
    manual_allowed = rehearsal_status == "manual_review_candidate" and bool(pre_summary.get("manual_broker_review_allowed"))
    lock_payload = {
        "run_date": pack.get("run_date"),
        "signal_as_of_date": signal_as_of,
        "market": market,
        "risk_profile_id": risk_profile_id,
        "requests": requests,
        "combined_target_manifest": combined_manifest,
        "allocation_manifest": allocation_manifest,
    }
    lock_id = _same_parameter_lock_id(lock_payload)
    locked_requests = [_same_parameter_request_with_lock(row, lock_id) for row in requests]
    return _sanitize(
        {
            "stage": DAILY_SAME_PARAMETER_PAPER_REHEARSAL_STAGE,
            "run_date": str(pack.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "rehearsal_status": rehearsal_status,
                "traffic_light": "red" if rehearsal_status.startswith("blocked") else "yellow",
                "plain_answer": _same_parameter_plain_answer(rehearsal_status),
                "workflow_id": "paper_simulation",
                "endpoint": "/api/paper",
                "primary_market": market,
                "selected_factor_count": len(factors[:3]),
                "request_count": len(requests),
                "combined_target_count": len(combined_manifest),
                "allocation_row_count": len(allocation_manifest),
                "signal_as_of_date": signal_as_of,
                "risk_profile_id": risk_profile_id,
                "portfolio_value": portfolio_value,
                "lock_id": lock_id,
                "paper_rehearsal_allowed": paper_allowed,
                "manual_broker_review_allowed": manual_allowed,
                "can_buy_today": False,
                "real_money_allowed": False,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "lock_id": lock_id,
            "recommended_requests": locked_requests,
            "combined_target_manifest": combined_manifest,
            "allocation_manifest": allocation_manifest,
            "lock_rules": _same_parameter_lock_rules(lock_id),
            "operator_steps": _same_parameter_operator_steps(rehearsal_status, paper_allowed, manual_allowed),
            "source_pre_execution_summary": pre_summary,
            "execution_boundary": {
                "plain_boundary": "These are locked paper-simulation requests and allocation evidence only; they are not broker orders.",
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
        }
    )


def build_daily_beginner_execution_answer(pack: dict[str, Any]) -> dict[str, Any]:
    guard = (
        pack.get("daily_pre_execution_guard")
        if isinstance(pack.get("daily_pre_execution_guard"), dict)
        else build_daily_pre_execution_guard(pack)
    )
    rehearsal = (
        pack.get("daily_same_parameter_paper_rehearsal")
        if isinstance(pack.get("daily_same_parameter_paper_rehearsal"), dict)
        else build_daily_same_parameter_paper_rehearsal(pack)
    )
    guard_summary = guard.get("summary") if isinstance(guard.get("summary"), dict) else {}
    rehearsal_summary = rehearsal.get("summary") if isinstance(rehearsal.get("summary"), dict) else {}
    guard_status = str(guard_summary.get("guard_status") or "blocked_no_allocation_rows")
    paper_allowed = bool(guard_summary.get("paper_rehearsal_allowed"))
    manual_allowed = bool(guard_summary.get("manual_broker_review_allowed"))

    if manual_allowed:
        ordinary_verdict = "manual_review_candidate"
        allowed_mode = "manual_review_material_only"
        headline = "证据可进入人工复核材料阶段，但软件仍不能买入或下单。"
        next_label = "核对执行前价格护栏"
        next_target = "daily-pre-execution-guard"
        next_workflow = ""
    elif paper_allowed:
        ordinary_verdict = "paper_only"
        allowed_mode = "same_parameter_paper_rehearsal_only"
        headline = "今天只做同参数模拟盘和盘后回执，不进入券商复核。"
        next_label = "运行同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"
    else:
        ordinary_verdict = "do_not_trade"
        allowed_mode = "blocked_no_action"
        headline = "今天不要买，也不要进入券商端；先处理红灯。"
        next_label = "查看执行前红灯"
        next_target = "daily-pre-execution-guard"
        next_workflow = ""

    reasons = _beginner_execution_reasons(guard)
    first_reason = next((row for row in reasons if row.get("status") == "blocked"), None) or next(
        (row for row in reasons if row.get("status") in {"required", "paper_only"}), None
    )
    if first_reason:
        next_target = str(first_reason.get("target_id") or next_target)
        next_workflow = str(first_reason.get("workflow_id") or next_workflow)
        next_label = _beginner_execution_next_label(str(first_reason.get("reason_id") or ""), next_label)

    review_rows = _beginner_execution_review_rows(
        guard.get("row_guardrails", []),
        manual_allowed=manual_allowed,
        paper_allowed=paper_allowed,
        guard_status=guard_status,
    )
    today_operation_card = _beginner_today_operation_card(
        ordinary_verdict=ordinary_verdict,
        allowed_mode=allowed_mode,
        headline=headline,
        guard_status=guard_status,
        paper_allowed=paper_allowed,
        manual_allowed=manual_allowed,
        next_label=next_label,
        next_target=next_target,
        next_workflow=next_workflow,
        review_rows=review_rows,
        reasons=reasons,
    )
    pre_market_packet = _beginner_pre_market_manual_execution_packet(
        pack=pack,
        manual_allowed=manual_allowed,
        paper_allowed=paper_allowed,
        today_operation_card=today_operation_card,
    )
    trade_system_gate = _beginner_trade_system_go_no_go_gate(
        guard_status=guard_status,
        manual_allowed=manual_allowed,
        paper_allowed=paper_allowed,
        today_operation_card=today_operation_card,
        pre_market_packet=pre_market_packet,
    )
    final_operation_packet = _beginner_final_operation_packet(
        pack=pack,
        today_operation_card=today_operation_card,
        pre_market_packet=pre_market_packet,
        trade_system_gate=trade_system_gate,
    )
    return _sanitize(
        {
            "stage": DAILY_BEGINNER_EXECUTION_ANSWER_STAGE,
            "run_date": str(pack.get("run_date") or guard.get("run_date") or date.today().isoformat()),
            "safety": SAFETY_NOTICE,
            "summary": {
                "ordinary_verdict": ordinary_verdict,
                "allowed_mode": allowed_mode,
                "today_action_code": today_operation_card["today_action_code"],
                "guard_status": guard_status,
                "rehearsal_status": str(rehearsal_summary.get("rehearsal_status") or ""),
                "headline": headline,
                "plain_answer": headline,
                "paper_rehearsal_allowed": paper_allowed,
                "manual_review_allowed": manual_allowed,
                "can_buy_today": False,
                "review_row_count": len(review_rows),
                "reason_count": len(reasons),
                "next_label": next_label,
                "next_target_id": next_target,
                "next_workflow_id": next_workflow,
                "manual_only_boundary": True,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "today_operation_card": today_operation_card,
            "trade_system_go_no_go_gate": trade_system_gate,
            "pre_market_manual_execution_packet": pre_market_packet,
            "beginner_final_operation_packet": final_operation_packet,
            "reasons": reasons,
            "review_rows": review_rows,
            "operator_next_steps": _beginner_execution_next_steps(
                guard.get("operator_steps", []),
                manual_allowed=manual_allowed,
                paper_allowed=paper_allowed,
            ),
            "forbidden_actions": [
                _beginner_execution_forbidden_action(
                    "direct_buy_top3",
                    "Do not buy directly from the Top3 factor list without same-day signal, paper evidence, risk checks, and human review.",
                ),
                _beginner_execution_forbidden_action(
                    "copy_rows_to_broker",
                    "Do not copy paper allocation rows into a broker app as orders.",
                ),
                _beginner_execution_forbidden_action(
                    "skip_post_close_journal",
                    "Do not skip the post-close journal; it is required evidence for the next session.",
                ),
            ],
            "source_pre_execution_summary": guard_summary,
            "execution_boundary": {
                "plain_boundary": "This card explains what a beginner should do next; it never connects to a broker or submits orders.",
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
        }
    )


def _beginner_final_operation_packet(
    *,
    pack: dict[str, Any],
    today_operation_card: dict[str, Any],
    pre_market_packet: dict[str, Any],
    trade_system_gate: dict[str, Any],
) -> dict[str, Any]:
    recheck = (
        pre_market_packet.get("broker_price_recheck_playbook")
        if isinstance(pre_market_packet.get("broker_price_recheck_playbook"), dict)
        else {}
    )
    recheck_rows = [row for row in recheck.get("rows", []) if isinstance(row, dict)]
    closure_gate = (
        today_operation_card.get("after_action_closure_gate")
        if isinstance(today_operation_card.get("after_action_closure_gate"), dict)
        else {}
    )
    final_action_status = str(trade_system_gate.get("decision") or "do_not_trade")
    traffic_light = str(trade_system_gate.get("traffic_light") or today_operation_card.get("traffic_light") or "red")
    manual_ticket_count = len(recheck_rows)
    post_close_required = bool(pre_market_packet.get("post_close_closure_required"))
    if final_action_status == "manual_review_only_not_order" and manual_ticket_count:
        plain_answer = (
            "今天最多查看人工复核票据；它们不是订单。先手工填券商实时价和可用现金，"
            "本地重算数量后，本人再决定跳过或离开系统手动处理。"
        )
    elif final_action_status == "paper_rehearsal_only":
        plain_answer = "今天只做同参数模拟盘，不进入券商端，不复制票据，不下单。"
    else:
        plain_answer = "今天不交易；先处理红灯、缺失证据或数据问题。"

    ticket_rows = []
    for index, row in enumerate(recheck_rows, start=1):
        small_capital_ticket = _small_capital_ticket_budget_overlay(row)
        ticket_rows.append(
            {
                "row_number": _int(row.get("row_number"), index),
                "ticket_id": str(row.get("ticket_id") or f"manual_review_{index}"),
                "asset_id": str(row.get("asset_id") or ""),
                "market": str(row.get("market") or "CN_ETF"),
                "suggested_side": str(row.get("side") or "review"),
                "reference_price": _float_or_none(row.get("reference_price")),
                "lower_price_bound": _float_or_none(row.get("lower_price_bound")),
                "upper_price_bound": _float_or_none(row.get("upper_price_bound")),
                "max_slippage_bps": _int(row.get("max_slippage_bps"), MANUAL_MAX_SLIPPAGE_BPS),
                "target_value_for_recalculation": _float_or_none(row.get("target_value_for_recalculation")),
                "estimated_quantity_at_reference": _int(row.get("estimated_quantity_at_reference"), 0),
                "board_lot_size": _int(row.get("board_lot_size"), BOARD_LOT_SIZE),
                "external_realtime_price_required": True,
                "external_cash_check_required": True,
                "human_final_decision_required": True,
                "final_quantity_rule": "recalculate_from_external_price_floor_to_board_lot",
                "skip_rule": str(row.get("skip_rule") or "skip_if_broker_price_outside_guardrail"),
                "cash_recheck_rule": str(row.get("cash_recheck_rule") or "skip_if_external_cash_below_recalculated_value"),
                "default_decision_if_missing_price": str(
                    row.get("default_decision_if_missing_price") or "skip_waiting_for_external_broker_price"
                ),
                **small_capital_ticket,
                "plain_instruction": str(
                    row.get("plain_instruction")
                    or "先在券商端手工核对实时价、现金和风险；看不懂或超护栏就跳过。"
                ),
                "copy_to_broker_allowed": False,
                "can_buy_by_software": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            }
        )

    small_capital_budget = _small_capital_budget_overlay(pack, ticket_rows)

    operator_steps = [
        {
            "step_id": "read_final_packet",
            "label": "先读最终操作包",
            "status": "required",
            "target_id": "daily-beginner-execution-answer-final-packet",
            "plain_action": "先确认今天是红灯、黄灯还是只允许模拟；不要直接照 Top3 下单。",
            "order_placement_allowed": False,
        },
        {
            "step_id": "fill_external_broker_price_and_cash",
            "label": "手工填写券商实时价和可用现金",
            "status": "required_external_input" if manual_ticket_count else "locked",
            "target_id": "daily-beginner-execution-answer-pre-market-packet",
            "plain_action": "逐票手工填实时价和现金，本地按一手取整重算数量。",
            "order_placement_allowed": False,
        },
        {
            "step_id": "human_choose_skip_or_manual_trade",
            "label": "本人决定跳过或离开系统手动处理",
            "status": "manual_only" if final_action_status == "manual_review_only_not_order" else "locked",
            "target_id": "beginner-live-handoff-board",
            "plain_action": "系统只给复核材料；最终是否在外部券商手动操作由人决定。",
            "order_placement_allowed": False,
        },
        {
            "step_id": "record_post_close_closure",
            "label": "收盘后补复盘和执行审计",
            "status": "required_after_action" if post_close_required else "locked",
            "target_id": "beginner-post-close-journal-board",
            "plain_action": "记录是否执行、成交价、数量、滑点、跳过原因和持仓更新。",
            "order_placement_allowed": False,
        },
    ]
    must_not_do = [
        {
            "action_id": "direct_buy_from_top3",
            "plain_rule": "不能因为某因子进入 Top3 就直接买入；Top3 只是候选入口。",
        },
        {
            "action_id": "copy_without_recheck",
            "plain_rule": "不能把参考数量复制成券商订单；必须用券商实时价、现金和护栏重新核对。",
        },
        {
            "action_id": "skip_post_close_closure",
            "plain_rule": "不能跳过盘后复盘和人工执行审计；缺闭环会隔离下一交易日 Top3。",
        },
    ]
    return _sanitize(
        {
            "packet_id": "beginner_final_operation_packet",
            "ordinary_question": "今天到底买什么、卖什么、跳过什么？",
            "final_action_status": final_action_status,
            "traffic_light": traffic_light,
            "plain_answer": plain_answer,
            "manual_ticket_count": manual_ticket_count,
            "external_manual_input_count": _int(trade_system_gate.get("external_manual_input_count"), 0),
            "post_close_closure_required": post_close_required,
            "next_session_quarantine_required_if_missing": bool(
                closure_gate.get("next_session_quarantine_required_if_missing")
            ),
            "next_session_rule": "quarantine_today_top3_if_missing_closure",
            "operator_steps": operator_steps,
            "ticket_rows": ticket_rows,
            "small_capital_budget": small_capital_budget,
            "must_not_do": must_not_do,
            "manual_only_boundary": True,
            "can_buy_by_software": False,
            "can_buy_today": False,
            "copy_to_broker_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
    )


def _small_capital_ticket_budget_overlay(row: dict[str, Any]) -> dict[str, Any]:
    max_single = SMALL_CAPITAL_OBSERVATION_MAX_SINGLE_TICKET_NOTIONAL
    reference_price = _float(row.get("reference_price"), 0.0)
    target_notional = abs(_float(row.get("target_value_for_recalculation"), 0.0))
    capped_notional = min(target_notional, max_single) if target_notional > 0 else 0.0
    board_lot = max(1, _int(row.get("board_lot_size"), BOARD_LOT_SIZE))
    capped_quantity = (
        int(math.floor(capped_notional / reference_price / board_lot) * board_lot)
        if reference_price > 0 and capped_notional > 0
        else 0
    )
    limit_breached = bool(target_notional > max_single + 1e-9)
    return {
        "small_capital_max_single_ticket_notional": max_single,
        "small_capital_requested_notional": target_notional,
        "small_capital_capped_notional": capped_notional,
        "small_capital_limit_breached": limit_breached,
        "small_capital_quantity_at_reference": capped_quantity,
        "small_capital_action": (
            "cap_or_skip_external_manual_review"
            if limit_breached
            else "within_small_capital_external_manual_review_budget"
        ),
        "small_capital_budget_note": (
            "Use the capped notional for small-capital observation review; skip if the external price/cash check fails."
        ),
    }


def _small_capital_budget_overlay(pack: dict[str, Any], ticket_rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    portfolio_value = _float(summary.get("portfolio_value"), SMALL_CAPITAL_OBSERVATION_MAX_INITIAL_CAPITAL)
    max_initial = min(
        SMALL_CAPITAL_OBSERVATION_MAX_INITIAL_CAPITAL,
        portfolio_value if portfolio_value > 0 else SMALL_CAPITAL_OBSERVATION_MAX_INITIAL_CAPITAL,
    )
    max_single = min(SMALL_CAPITAL_OBSERVATION_MAX_SINGLE_TICKET_NOTIONAL, max_initial)
    requested_total = sum(_float(row.get("small_capital_requested_notional"), 0.0) for row in ticket_rows)
    capped_total = sum(min(_float(row.get("small_capital_capped_notional"), 0.0), max_single) for row in ticket_rows)
    breach_count = sum(1 for row in ticket_rows if row.get("small_capital_limit_breached"))
    return {
        "budget_id": "small_capital_final_operation_budget",
        "max_initial_capital": max_initial,
        "max_single_ticket_notional": max_single,
        "max_daily_loss": min(SMALL_CAPITAL_OBSERVATION_MAX_DAILY_LOSS, max_initial),
        "ticket_count": len(ticket_rows),
        "ticket_limit_breach_count": breach_count,
        "total_requested_notional": requested_total,
        "total_capped_notional": capped_total,
        "capping_required": breach_count > 0,
        "external_manual_only": True,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _beginner_trade_system_go_no_go_gate(
    *,
    guard_status: str,
    manual_allowed: bool,
    paper_allowed: bool,
    today_operation_card: dict[str, Any],
    pre_market_packet: dict[str, Any],
) -> dict[str, Any]:
    packet_status = str(pre_market_packet.get("packet_status") or "blocked_no_manual_execution_packet")
    ticket_count = _int(pre_market_packet.get("ticket_count"), 0)
    recheck = (
        pre_market_packet.get("broker_price_recheck_playbook")
        if isinstance(pre_market_packet.get("broker_price_recheck_playbook"), dict)
        else {}
    )
    recheck_rows = recheck.get("rows") if isinstance(recheck.get("rows"), list) else []
    required_manual_inputs = (
        recheck.get("required_manual_inputs") if isinstance(recheck.get("required_manual_inputs"), list) else []
    )
    evidence_rows = (
        pre_market_packet.get("evidence_checklist")
        if isinstance(pre_market_packet.get("evidence_checklist"), list)
        else []
    )
    evidence_by_id = {
        str(row.get("check_id") or ""): row
        for row in evidence_rows
        if isinstance(row, dict)
    }

    if manual_allowed and packet_status == "manual_review_ready_not_order" and ticket_count > 0:
        decision = "manual_review_only_not_order"
        trade_mode = "external_manual_review_only"
        traffic_light = "yellow"
        plain_answer = "今天最多进入外部券商人工复核；软件只给证据、护栏和重算规则，不会买入或下单。"
        next_target_id = "daily-beginner-execution-answer-pre-market-packet"
        next_workflow_id = ""
        human_may_open_external_broker_app = True
    elif paper_allowed:
        decision = "paper_rehearsal_only"
        trade_mode = "same_parameter_paper_only"
        traffic_light = "yellow"
        plain_answer = "今天只能做同参数模拟盘和盘后记录；不要打开券商端照着买。"
        next_target_id = "daily-paper-allocation-playbook"
        next_workflow_id = "paper_simulation"
        human_may_open_external_broker_app = False
    else:
        decision = "do_not_trade"
        trade_mode = "blocked_no_action"
        traffic_light = "red"
        plain_answer = "今天不交易；先处理信号、数据、风险或闭环缺口。"
        next_target_id = str(today_operation_card.get("next_target_id") or "daily-pre-execution-guard")
        next_workflow_id = str(today_operation_card.get("next_workflow_id") or "")
        human_may_open_external_broker_app = False

    signal_status = str(evidence_by_id.get("signal_freshness", {}).get("status") or "required")
    same_parameter_status = str(evidence_by_id.get("same_parameter_top3_paper", {}).get("status") or "required")
    manual_ticket_status = str(evidence_by_id.get("manual_ticket_visibility", {}).get("status") or "required")
    pre_execution_status = "pass" if manual_allowed else "required" if paper_allowed else "blocked"
    recheck_status = "required_external_input" if recheck_rows else "locked"
    closure_status = "required_after_action" if bool(pre_market_packet.get("post_close_closure_required")) else "locked"
    gate_rows = [
        _trade_system_gate_row(
            "signal_freshness",
            signal_status,
            "今日信号必须是本次运行日期，不能拿旧信号交易。",
            evidence_by_id.get("signal_freshness", {}).get("evidence") or "",
            "daily-trade-advisory-status",
        ),
        _trade_system_gate_row(
            "same_parameter_top3_paper",
            same_parameter_status,
            "前三因子必须先完成同参数模拟盘证据。",
            evidence_by_id.get("same_parameter_top3_paper", {}).get("evidence") or "",
            "daily-same-parameter-paper-rehearsal",
        ),
        _trade_system_gate_row(
            "pre_execution_guard",
            pre_execution_status,
            "盘前风控、价格护栏、容量和跳过规则必须允许进入下一步。",
            guard_status,
            "daily-pre-execution-guard",
        ),
        _trade_system_gate_row(
            "manual_ticket_visibility",
            manual_ticket_status,
            "只有可见的人工复核票据才能进入券商端人工核对。",
            evidence_by_id.get("manual_ticket_visibility", {}).get("evidence") or f"tickets={ticket_count}",
            "daily-beginner-execution-answer-pre-market-packet",
        ),
        _trade_system_gate_row(
            "broker_realtime_price_recheck",
            recheck_status,
            "券商实时价、现金和最终跳过/执行决定必须由人手工填写。",
            f"rows={len(recheck_rows)}; required_inputs={len(required_manual_inputs)}",
            "daily-beginner-execution-answer-pre-market-packet",
        ),
        _trade_system_gate_row(
            "post_close_closure_plan",
            closure_status,
            "收盘后必须补盘后复盘、人工执行审计和持仓更新，否则明日隔离今日 Top3。",
            "after_action_closure_gate",
            "beginner-post-close-journal-board",
        ),
        _trade_system_gate_row(
            "automation_boundary",
            "protected",
            "系统不连接券商、不读取账户、不复制订单、不自动下单。",
            "broker_connection_allowed=false; order_placement_allowed=false",
            "beginner-live-handoff-board",
        ),
    ]

    blocked_statuses = {"blocked", "failed", "danger"}
    required_statuses = {"required", "required_external_input", "required_after_action"}
    return _sanitize(
        {
            "gate_id": "trade_system_go_no_go_gate",
            "decision": decision,
            "trade_mode": trade_mode,
            "traffic_light": traffic_light,
            "plain_answer": plain_answer,
            "guard_status": guard_status,
            "packet_status": packet_status,
            "ticket_count": ticket_count,
            "manual_review_allowed": bool(manual_allowed),
            "paper_rehearsal_allowed": bool(paper_allowed),
            "human_may_open_external_broker_app": bool(human_may_open_external_broker_app),
            "external_manual_input_count": len(required_manual_inputs),
            "ready_gate_count": sum(1 for row in gate_rows if row.get("status") in {"pass", "protected"}),
            "required_gate_count": sum(1 for row in gate_rows if row.get("status") in required_statuses),
            "blocked_gate_count": sum(1 for row in gate_rows if row.get("status") in blocked_statuses),
            "next_label": "查看盘前人工复核包" if decision == "manual_review_only_not_order" else str(today_operation_card.get("next_label") or ""),
            "next_target_id": next_target_id,
            "next_workflow_id": next_workflow_id,
            "gate_rows": gate_rows,
            "can_buy_by_software": False,
            "can_buy_today": False,
            "copy_to_broker_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
    )


def _trade_system_gate_row(
    gate_id: str,
    status: str,
    plain_rule: str,
    evidence: Any,
    target_id: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "status": status,
        "plain_rule": plain_rule,
        "evidence": str(evidence or ""),
        "target_id": target_id,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _beginner_today_operation_card(
    *,
    ordinary_verdict: str,
    allowed_mode: str,
    headline: str,
    guard_status: str,
    paper_allowed: bool,
    manual_allowed: bool,
    next_label: str,
    next_target: str,
    next_workflow: str,
    review_rows: list[dict[str, Any]],
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    if manual_allowed:
        today_action_code = "manual_review_only"
        traffic_light = "yellow"
        plain_answer = "今天只能把 Top3 信号生成的票据当作人工复核材料；先核对外部券商实时价格、现金、仓位和风险，不能由软件买入或复制下单。"
        primary_action = "人工复核票据，不自动买入"
    elif paper_allowed:
        today_action_code = "paper_rehearsal_only"
        traffic_light = "yellow"
        plain_answer = "今天只能运行同参数模拟盘和记录盘后复盘；不要打开券商端照着买。"
        primary_action = "先跑同参数模拟盘"
    else:
        today_action_code = "do_not_trade"
        traffic_light = "red"
        plain_answer = "今天不要买，也不要进入券商端；先处理红灯原因，再重新生成和复核信号。"
        primary_action = "先处理红灯，不交易"

    blocked_reasons = [row for row in reasons if str(row.get("status") or "") == "blocked"]
    required_reasons = [row for row in reasons if str(row.get("status") or "") in {"required", "paper_only"}]
    action_rows = []
    for index, row in enumerate(review_rows, start=1):
        action_rows.append(
            {
                "row_number": _int(row.get("row_number"), index),
                "asset_id": row.get("asset_id"),
                "market": row.get("market") or "CN_ETF",
                "side": row.get("side") or "review",
                "row_action_code": row.get("row_action_code") or today_action_code,
                "row_action_label": row.get("row_action_label") or primary_action,
                "plain_row_instruction": row.get("plain_row_instruction") or plain_answer,
                "row_blocker": row.get("row_blocker") or guard_status,
                "row_can_be_copied_to_broker": False,
                "target_weight": _float_or_none(row.get("target_weight")),
                "paper_budget_value": _float_or_none(row.get("paper_budget_value")),
                "paper_quantity": _int(row.get("paper_quantity"), 0),
                "reference_price": _float_or_none(row.get("reference_price")),
                "price_guardrail": {
                    "lower_price_bound": _float_or_none(row.get("lower_price_bound")),
                    "upper_price_bound": _float_or_none(row.get("upper_price_bound")),
                    "max_slippage_bps": _int(row.get("max_slippage_bps"), MANUAL_MAX_SLIPPAGE_BPS),
                },
                "manual_external_broker_check_required": bool(manual_allowed),
                "copy_to_broker_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            }
        )

    after_action_checklist = _beginner_after_action_checklist(
        manual_allowed=manual_allowed,
        paper_allowed=paper_allowed,
    )
    return {
        "card_id": "today_operation_verdict",
        "question": "今天到底怎么操作？",
        "today_action_code": today_action_code,
        "traffic_light": traffic_light,
        "ordinary_verdict": ordinary_verdict,
        "allowed_mode": allowed_mode,
        "guard_status": guard_status,
        "primary_action": primary_action,
        "plain_answer": plain_answer,
        "headline": headline,
        "ticket_count": len(review_rows),
        "blocked_reason_count": len(blocked_reasons),
        "required_reason_count": len(required_reasons),
        "paper_rehearsal_allowed": paper_allowed,
        "manual_review_allowed": manual_allowed,
        "manual_external_broker_check_required": bool(manual_allowed and review_rows),
        "next_label": next_label,
        "next_target_id": next_target,
        "next_workflow_id": next_workflow,
        "action_rows": action_rows,
        "after_action_checklist": after_action_checklist,
        "after_action_closure_gate": _beginner_after_action_closure_gate(after_action_checklist),
        "copy_to_broker_allowed": False,
        "can_buy_today": False,
        "manual_only_boundary": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _beginner_after_action_checklist(*, manual_allowed: bool, paper_allowed: bool) -> list[dict[str, Any]]:
    status = "required" if manual_allowed or paper_allowed else "locked"
    return [
        {
            "item_id": "record_post_close_journal",
            "label": "记录盘后复盘",
            "status": status,
            "plain_action": "无论人工复核后是否执行，都要记录今天为什么做、为什么跳过、纸面结果和风险状态。",
            "target_id": "beginner-post-close-journal-board",
            "workflow_id": "post_close_journal" if manual_allowed or paper_allowed else "",
            "failure_effect": "quarantine_next_session_top3",
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        {
            "item_id": "record_manual_execution_audit",
            "label": "记录人工成交审计",
            "status": status,
            "plain_action": "如果人在券商端执行或跳过票据，要记录成交价、数量、滑点、跳过原因和异常。",
            "target_id": "beginner-post-close-journal-board",
            "workflow_id": "post_close_journal" if manual_allowed or paper_allowed else "",
            "failure_effect": "quarantine_next_session_top3",
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        {
            "item_id": "update_current_positions_after_manual_trade",
            "label": "更新当前持仓",
            "status": status,
            "plain_action": "若今天有人工成交，明天生成信号前必须把脱敏后的 ETF、数量和价格更新到当前持仓。",
            "target_id": "daily-current-positions",
            "workflow_id": "",
            "failure_effect": "block_next_pretrade_readiness",
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        {
            "item_id": "quarantine_next_session_if_missing",
            "label": "缺闭环则隔离明日 Top3",
            "status": status,
            "plain_action": "盘后复盘、人工成交审计或当前持仓缺失时，下一交易日不能复用今天的 Top3 组合。",
            "target_id": "daily-factor-health-monitor",
            "workflow_id": "",
            "failure_effect": "quarantine_next_session_top3",
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
    ]


def _beginner_after_action_closure_gate(after_action_checklist: list[dict[str, Any]]) -> dict[str, Any]:
    required_statuses = {"required", "missing", "blocked", "paper_only"}
    required_items = [
        row
        for row in after_action_checklist
        if str(row.get("status") or "") in required_statuses
    ]
    missing_item_count = len(required_items)
    quarantine_required = missing_item_count > 0
    if quarantine_required:
        closure_status = "pending_after_action_closure"
        next_session_status = "quarantine_if_after_action_missing"
        plain_answer = (
            "收盘后复盘、人工成交审计和当前持仓没有闭环前，下一交易日不能复用今天的 Top3。"
        )
        next_target_id = "beginner-post-close-journal-board"
        next_workflow_id = "post_close_journal"
    else:
        closure_status = "locked_until_manual_or_paper_action"
        next_session_status = "no_today_top3_reuse_required"
        plain_answer = (
            "当前不允许人工复核或模拟盘演练，今天的 Top3 不应带入下一交易日。"
        )
        next_target_id = "daily-pre-execution-guard"
        next_workflow_id = ""

    return {
        "gate_id": "after_action_closure_gate",
        "closure_gate_status": closure_status,
        "plain_answer": plain_answer,
        "required_item_count": len(required_items),
        "missing_item_count": missing_item_count,
        "next_session_reuse_status": next_session_status,
        "next_session_quarantine_required_if_missing": quarantine_required,
        "next_target_id": next_target_id,
        "next_workflow_id": next_workflow_id,
        "copy_to_broker_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _beginner_pre_market_manual_execution_packet(
    *,
    pack: dict[str, Any],
    manual_allowed: bool,
    paper_allowed: bool,
    today_operation_card: dict[str, Any],
) -> dict[str, Any]:
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else {}
    freshness = readiness.get("freshness") if isinstance(readiness.get("freshness"), dict) else {}
    readiness_confirmations = [
        row for row in readiness.get("required_confirmations", []) if isinstance(row, dict)
    ]
    confirmation_by_id = {str(row.get("check_id") or ""): row for row in readiness_confirmations}
    handoff_summary = handoff.get("summary") if isinstance(handoff.get("summary"), dict) else {}
    tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    ticket_count = len(tickets)
    blocked_ticket_count = _int(handoff_summary.get("blocked_copyable_ticket_count"), 0)
    same_parameter_ready = bool(handoff_summary.get("same_parameter_paper_ready"))
    same_parameter_required = _int(handoff_summary.get("same_parameter_paper_required_count"), 0)
    same_parameter_matched = _int(handoff_summary.get("same_parameter_paper_matched_count"), 0)
    masked_until_paper = bool(handoff.get("copyable_tickets_masked_until_same_parameter_paper"))

    if manual_allowed and ticket_count > 0 and not masked_until_paper:
        packet_status = "manual_review_ready_not_order"
        next_human_action = "verify_external_broker_price_and_cash"
        plain_answer = "可以进入人工复核材料阶段：先核对券商实时价格、现金、持仓和风险，再由本人决定跳过或手动操作。"
    elif paper_allowed:
        packet_status = "paper_rehearsal_required_before_manual_review"
        next_human_action = "run_same_parameter_paper_before_broker_review"
        plain_answer = "今天还不能进入券商人工复核；先跑同参数模拟盘并补齐证据。"
    else:
        packet_status = "blocked_no_manual_execution_packet"
        next_human_action = "resolve_pretrade_blockers"
        plain_answer = "今天没有可用的人工执行包；先处理盘前红灯和缺失证据。"

    current_position_confirmation = confirmation_by_id.get("current_position_input", {})
    signal_freshness_status = "pass" if bool(freshness.get("fresh_for_run_date")) else "blocked"
    same_parameter_status = "pass" if same_parameter_ready else "required"
    manual_ticket_status = "pass" if ticket_count > 0 and not masked_until_paper else "required"
    current_position_status = str(current_position_confirmation.get("status") or "waiting")

    return _sanitize(
        {
            "packet_id": "pre_market_manual_execution_packet",
            "packet_status": packet_status,
            "run_date": str(pack.get("run_date") or readiness.get("run_date") or date.today().isoformat()),
            "manual_decision_mode": "external_broker_manual_review_only",
            "plain_answer": plain_answer,
            "next_human_action": next_human_action,
            "today_action_code": today_operation_card.get("today_action_code"),
            "traffic_light": today_operation_card.get("traffic_light"),
            "ticket_count": ticket_count,
            "blocked_ticket_count": blocked_ticket_count,
            "post_close_closure_required": bool(ticket_count or paper_allowed or manual_allowed),
            "broker_price_recheck_playbook": _broker_price_recheck_playbook(tickets),
            "evidence_checklist": [
                {
                    "check_id": "signal_freshness",
                    "status": signal_freshness_status,
                    "plain_check": "今日信号日期必须等于运行日期。",
                    "evidence": (
                        f"run_date={freshness.get('run_date') or readiness.get('run_date') or '--'}; "
                        f"latest_signal_date={freshness.get('latest_signal_date') or '--'}"
                    ),
                },
                {
                    "check_id": "same_parameter_top3_paper",
                    "status": same_parameter_status,
                    "plain_check": "Top3 同参数模拟盘必须全部匹配后，才允许查看人工复核票据。",
                    "evidence": f"matched={same_parameter_matched}/{same_parameter_required}",
                },
                {
                    "check_id": "manual_ticket_visibility",
                    "status": manual_ticket_status,
                    "plain_check": "只有盘前闸门通过且同参数模拟盘完成后，才显示人工复核票据。",
                    "evidence": f"visible={ticket_count}; blocked={blocked_ticket_count}; masked={masked_until_paper}",
                },
                {
                    "check_id": "current_position_input",
                    "status": current_position_status,
                    "plain_check": "必须用脱敏持仓输入计算目标差额，不能从券商账户自动读取。",
                    "evidence": current_position_confirmation.get("text") or "",
                },
                {
                    "check_id": "broker_manual_boundary",
                    "status": "blocked_for_automation",
                    "plain_check": "系统不连接券商、不读取账户、不复制订单、不自动下单。",
                    "evidence": "broker_connection_allowed=false; order_placement_allowed=false",
                },
                {
                    "check_id": "post_close_closure_required",
                    "status": "required" if ticket_count or paper_allowed or manual_allowed else "locked",
                    "plain_check": "收盘后必须记录复盘、人工执行审计和持仓更新，否则明天隔离今天 Top3。",
                    "evidence": "after_action_closure_gate",
                },
            ],
            "operator_sequence": [
                {
                    "step_id": "review_today_operation_card",
                    "label": "先看今日操作卡",
                    "status": "required",
                    "target_id": "daily-beginner-execution-answer-today-card",
                    "workflow_id": "",
                    "order_placement_allowed": False,
                    "auto_order_allowed": False,
                },
                {
                    "step_id": "verify_external_broker_price",
                    "label": "人工核对券商实时价格",
                    "status": "required" if packet_status == "manual_review_ready_not_order" else "locked",
                    "target_id": "manual-broker-price-check-summary",
                    "workflow_id": "",
                    "order_placement_allowed": False,
                    "auto_order_allowed": False,
                },
                {
                    "step_id": "check_cash_position_and_risk",
                    "label": "人工核对现金、持仓和回撤预算",
                    "status": "required" if packet_status == "manual_review_ready_not_order" else "locked",
                    "target_id": "daily-current-positions",
                    "workflow_id": "",
                    "order_placement_allowed": False,
                    "auto_order_allowed": False,
                },
                {
                    "step_id": "human_decides_skip_or_manual_trade",
                    "label": "本人决定跳过或离开系统手动操作",
                    "status": "manual_only" if packet_status == "manual_review_ready_not_order" else "locked",
                    "target_id": "beginner-live-handoff-board",
                    "workflow_id": "",
                    "order_placement_allowed": False,
                    "auto_order_allowed": False,
                },
                {
                    "step_id": "record_post_close_closure",
                    "label": "收盘后记录复盘和执行审计",
                    "status": "required" if ticket_count or paper_allowed or manual_allowed else "locked",
                    "target_id": "beginner-post-close-journal-board",
                    "workflow_id": "post_close_journal" if ticket_count or paper_allowed or manual_allowed else "",
                    "order_placement_allowed": False,
                    "auto_order_allowed": False,
                },
            ],
            "copy_to_broker_allowed": False,
            "can_buy_today": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
    )


def _broker_price_recheck_playbook(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_broker_price_recheck_row(index, ticket) for index, ticket in enumerate(tickets, start=1)]
    return _sanitize(
        {
            "playbook_id": "broker_price_recheck_playbook",
            "status": "waiting_for_external_broker_prices" if rows else "locked_no_visible_manual_tickets",
            "plain_answer": "券商端实时价必须人工填写并重算数量；价格超出护栏或滑点预算时跳过。",
            "ticket_count": len(rows),
            "session_decision_engine": "broker_price_recheck_session_verdict",
            "session_operator_rule": "all_visible_tickets_need_external_price_and_cash_before_manual_decision",
            "session_decision_statuses": [
                "locked_no_visible_manual_tickets",
                "waiting_for_all_external_inputs",
                "manual_review_all_rows_price_cash_ok",
                "manual_review_some_rows_skipped_or_blocked",
                "manual_review_all_rows_skipped",
            ],
            "required_manual_inputs": [
                "external_broker_realtime_price",
                "external_available_cash_after_manual_check",
                "human_final_skip_or_trade_decision",
            ],
            "recalculation_rule": "floor_to_board_lot_at_external_price",
            "skip_rule": "skip_if_broker_price_outside_guardrail",
            "rows": rows,
            "copy_to_broker_allowed": False,
            "can_buy_today": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
    )


def _broker_price_recheck_row(index: int, ticket: dict[str, Any]) -> dict[str, Any]:
    guardrails = (
        ticket.get("execution_guardrails")
        if isinstance(ticket.get("execution_guardrails"), dict)
        else _manual_ticket_execution_guardrails(ticket)
    )
    reference_price = _float_or_none(ticket.get("reference_price") or ticket.get("latest_price"))
    target_value = abs(_float(ticket.get("delta_value"), _float(ticket.get("target_value"), 0.0)))
    lower_bound = _float_or_none(guardrails.get("lower_price_bound"))
    upper_bound = _float_or_none(guardrails.get("upper_price_bound"))
    max_slippage_bps = _int(guardrails.get("max_slippage_bps"), MANUAL_MAX_SLIPPAGE_BPS)
    estimated_quantity_at_reference = _int(ticket.get("rounded_quantity_delta"), 0)
    if not estimated_quantity_at_reference:
        estimated_quantity_at_reference = _int(ticket.get("rounded_quantity"), 0)

    row = {
        "row_number": index,
        "ticket_id": str(ticket.get("ticket_id") or f"manual_review_{index}"),
        "asset_id": str(ticket.get("asset_id") or ""),
        "market": str(ticket.get("market") or "CN_ETF"),
        "side": str(ticket.get("side") or "review"),
        "manual_input_field": "external_broker_realtime_price",
        "local_decision_engine": "broker_price_recheck_local_calculator",
        "default_decision_if_missing_price": "skip_waiting_for_external_broker_price",
        "external_broker_realtime_price": None,
        "external_available_cash_after_manual_check": None,
        "reference_price": reference_price,
        "lower_price_bound": lower_bound,
        "upper_price_bound": upper_bound,
        "max_slippage_bps": max_slippage_bps,
        "target_value_for_recalculation": target_value,
        "board_lot_size": BOARD_LOT_SIZE,
        "estimated_quantity_at_reference": estimated_quantity_at_reference,
        "recalculation_rule": "floor_to_board_lot_at_external_price",
        "recalculated_quantity_at_external_price": None,
        "recalculated_value_at_external_price": None,
        "external_cash_shortfall": None,
        "skip_rule": "skip_if_broker_price_outside_guardrail",
        "cash_recheck_rule": "skip_if_external_cash_below_recalculated_value",
        "local_recheck_input_fields": [
            "external_broker_realtime_price",
            "external_available_cash_after_manual_check",
            "human_final_skip_or_trade_decision",
        ],
        "local_recalculation_output_fields": [
            "recalculated_quantity_at_external_price",
            "recalculated_value_at_external_price",
            "external_price_slippage_bps",
            "external_cash_shortfall",
            "local_recheck_decision",
        ],
        "local_decision_statuses": [
            "skip_waiting_for_external_broker_price",
            "skip_invalid_external_broker_price",
            "skip_invalid_external_available_cash",
            "skip_broker_price_outside_guardrail",
            "skip_slippage_budget_breached",
            "skip_quantity_zero_after_recalculation",
            "manual_review_price_ok_cash_pending",
            "skip_external_cash_below_recalculated_value",
            "manual_review_price_ok_quantity_recalculated",
        ],
        "skip_if_broker_price_below": lower_bound,
        "skip_if_broker_price_above": upper_bound,
        "cash_recheck_required": True,
        "human_final_decision_required": True,
        "plain_instruction": "在券商端看到实时价后，先确认价格在护栏内，再用实时价按一手取整重算数量；超护栏、现金不足或看不懂就跳过。",
        "copy_to_broker_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }
    small_capital_ticket = _small_capital_ticket_budget_overlay(row)
    capped_notional = _float(small_capital_ticket.get("small_capital_capped_notional"), target_value)
    effective_target = min(target_value, capped_notional) if capped_notional > 0 else target_value
    row.update(small_capital_ticket)
    row.update(
        {
            "effective_target_value_for_recalculation": effective_target,
            "small_capital_recheck_budget_applied": bool(effective_target < target_value - 1e-9),
        }
    )
    row["local_recalculation_output_fields"] = [
        *row["local_recalculation_output_fields"],
        "effective_target_value_for_recalculation",
        "small_capital_capped_notional",
        "small_capital_recheck_budget_applied",
    ]
    return row


def _beginner_execution_reasons(guard: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in guard.get("skip_rules", []):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status == "pass":
            continue
        rows.append(
            {
                "reason_id": item.get("rule_id"),
                "status": status,
                "plain_reason": item.get("plain_rule") or "",
                "target_id": item.get("target_id") or "daily-pre-execution-guard",
                "workflow_id": item.get("workflow_id") or "",
                "must_resolve_before_manual_review": status in {"blocked", "required"},
                "order_placement_allowed": False,
            }
        )
    return rows


def _beginner_execution_review_rows(
    rows: Any,
    *,
    manual_allowed: bool,
    paper_allowed: bool = False,
    guard_status: str = "",
) -> list[dict[str, Any]]:
    source_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    action = _beginner_execution_row_action(
        manual_allowed=manual_allowed,
        paper_allowed=paper_allowed,
        guard_status=guard_status,
    )
    execution_mode = str(action["execution_mode"])
    return [
        {
            "row_number": _int(row.get("row_number"), index),
            "asset_id": row.get("asset_id"),
            "market": row.get("market") or "CN_ETF",
            "side": row.get("side") or "buy_or_adjust",
            "execution_mode": execution_mode,
            "row_action_code": action["row_action_code"],
            "row_action_label": action["row_action_label"],
            "plain_row_instruction": action["plain_row_instruction"],
            "row_blocker": action["row_blocker"],
            "row_can_be_copied_to_broker": False,
            "target_weight": _float_or_none(row.get("target_weight")),
            "paper_budget_value": _float_or_none(row.get("paper_budget_value")),
            "paper_quantity": _int(row.get("paper_quantity"), 0),
            "reference_price": _float_or_none(row.get("reference_price")),
            "lower_price_bound": _float_or_none(row.get("lower_price_bound")),
            "upper_price_bound": _float_or_none(row.get("upper_price_bound")),
            "max_slippage_bps": _int(row.get("max_slippage_bps"), MANUAL_MAX_SLIPPAGE_BPS),
            "liquidity_reference_value": _float_or_none(row.get("liquidity_reference_value")),
            "liquidity_reference_field": row.get("liquidity_reference_field"),
            "liquidity_evidence_missing": bool(row.get("liquidity_evidence_missing")),
            "participation_rate": _float_or_none(row.get("participation_rate")),
            "max_participation_rate": _float_or_none(row.get("max_participation_rate")),
            "capacity_blocked": bool(row.get("capacity_blocked")),
            "risk_blocked": bool(row.get("risk_blocked")),
            "human_checklist": [
                "check_external_realtime_price",
                "check_liquidity_capacity",
                "check_cash_and_position",
                "check_quantity_board_lot",
                "check_drawdown_budget",
                "write_post_close_journal",
            ],
            "copy_to_broker_allowed": False,
            "manual_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
        for index, row in enumerate(source_rows, start=1)
    ]


def _beginner_execution_row_action(*, manual_allowed: bool, paper_allowed: bool, guard_status: str) -> dict[str, str]:
    blocker = str(guard_status or "").strip() or "pre_execution_guard_not_clear"
    if manual_allowed:
        return {
            "execution_mode": "manual_review_candidate_not_order",
            "row_action_code": "manual_review_only_not_order",
            "row_action_label": "人工复核材料，不是订单",
            "plain_row_instruction": "这一行只能作为人工复核材料；先核对券商实时价、现金、仓位和风险，软件不会买入或下单。",
            "row_blocker": "",
        }
    if paper_allowed:
        return {
            "execution_mode": "paper_rehearsal_only",
            "row_action_code": "paper_rehearsal_only",
            "row_action_label": "只做纸面演练",
            "plain_row_instruction": "这一行只能用于同参数纸面演练；不要打开券商端照着买，也不要复制成订单。",
            "row_blocker": blocker,
        }
    return {
        "execution_mode": "blocked_no_action",
        "row_action_code": "do_not_trade",
        "row_action_label": "今天不要买",
        "plain_row_instruction": f"今天不要买，也不要复制到券商；先处理红灯原因：{blocker}。",
        "row_blocker": blocker,
    }


def _beginner_execution_next_steps(rows: Any, *, manual_allowed: bool, paper_allowed: bool) -> list[dict[str, Any]]:
    source_rows = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if not source_rows:
        return [
            {
                "step_id": "review_pre_execution_guard",
                "label": "查看执行前守门",
                "status": "required",
                "target_id": "daily-pre-execution-guard",
                "workflow_id": "",
                "order_placement_allowed": False,
            }
        ]
    normalized = []
    for item in source_rows:
        step_id = str(item.get("step_id") or "")
        status = str(item.get("status") or "required")
        if step_id == "open_external_broker_manually_if_human_chooses" and not manual_allowed:
            status = "locked"
        if step_id == "run_same_parameter_paper" and paper_allowed:
            status = "required"
        normalized.append(
            {
                "step_id": step_id,
                "label": item.get("label") or step_id,
                "status": status,
                "target_id": item.get("target_id") or "",
                "workflow_id": item.get("workflow_id") or "",
                "manual_required": True,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            }
        )
    return normalized


def _beginner_execution_forbidden_action(action_id: str, plain_rule: str) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "plain_rule": plain_rule,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _beginner_execution_next_label(reason_id: str, fallback: str) -> str:
    labels = {
        "stale_signal_date": "刷新 CN_ETF 数据并重新生成信号",
        "paper_allocation_missing": "生成纸面分配清单",
        "manual_ticket_missing": "补齐人工复核票据",
        "risk_budget_breached": "降低仓位或跳过风险超限行",
        "daily_risk_circuit_breaker": "记录风险事件并保持纸面模式",
        "liquidity_capacity_breached": "降低金额或继续纸面演练",
        "price_reference_missing": "补齐参考价格和一手取整数量",
        "next_session_quarantine": "运行同参数模拟盘并补齐复用证据",
        "broker_price_outside_guardrail": "人工核对券商端实时价格护栏",
        "manual_discomfort": "暂停并写清楚风险原因",
    }
    return labels.get(reason_id, fallback)


def _same_parameter_signal_as_of(
    pack: dict[str, Any],
    signal_cards: list[dict[str, Any]],
    pre_summary: dict[str, Any],
) -> str:
    for value in (pre_summary.get("latest_signal_date"), pack.get("run_date")):
        text = str(value or "").strip()
        if text:
            return text
    dates = [
        str(row.get("signal_date") or row.get("as_of_date") or "").strip()
        for row in signal_cards
        if str(row.get("signal_date") or row.get("as_of_date") or "").strip()
    ]
    return sorted(dates)[-1] if dates else date.today().isoformat()


def _same_parameter_paper_request(
    candidate: dict[str, Any],
    *,
    index: int,
    pack: dict[str, Any],
    market: str,
    portfolio_value: float,
    signal_as_of: str,
    risk_profile_id: str,
    risk_profile: dict[str, Any] | None,
    summary: dict[str, Any],
) -> dict[str, Any]:
    params = candidate.get("params") if isinstance(candidate.get("params"), dict) else {}
    factor_name = str(candidate.get("factor_name") or candidate.get("factor") or "")
    cost_bps = _float(params.get("cost_bps"), _float(params.get("commission_bps"), 5.0))
    max_gross = _float(
        summary.get("applied_max_gross_exposure"),
        _float((risk_profile or {}).get("max_gross_exposure"), _float(summary.get("requested_max_gross_exposure"), 1.0)),
    )
    max_single = _float((risk_profile or {}).get("max_single_etf_weight"), _float(summary.get("max_asset_weight"), 0.4))
    min_cash = _float((risk_profile or {}).get("min_cash_weight"), max(0.0, 1.0 - max_gross))
    return {
        "request_id": f"top3-paper-{index:03d}",
        "rank": _int(candidate.get("rank"), index),
        "case_id": candidate.get("case_id"),
        "workflow_id": "paper_simulation",
        "endpoint": "/api/paper",
        "source": str(pack.get("source") or "processed-bars"),
        "market": market,
        "factor": factor_name,
        "factor_windows": _paper_factor_windows(params.get("factor_windows") or candidate.get("factor_windows"), factor_name),
        "top_n": _int(params.get("top_n") or params.get("topN"), 2),
        "rebalance_interval": _int(params.get("rebalance_interval") or params.get("holding_period"), 1),
        "start_date": params.get("start_date") or summary.get("start_date") or pack.get("start_date"),
        "end_date": params.get("end_date") or summary.get("end_date") or pack.get("end_date") or signal_as_of,
        "as_of_date": signal_as_of,
        "initial_cash": portfolio_value,
        "commission_bps": cost_bps,
        "slippage_bps": cost_bps,
        "max_asset_weight": max_single,
        "max_market_weight": _float(summary.get("max_market_weight"), 1.0),
        "max_gross_exposure": max_gross,
        "min_cash_weight": min_cash,
        "risk_profile_id": risk_profile_id,
        "order_placement_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "auto_order_allowed": False,
    }


def _same_parameter_request_with_lock(request: dict[str, Any], lock_id: str) -> dict[str, Any]:
    row = dict(request)
    row["same_parameter_lock_id"] = lock_id
    row["same_parameter_request_id"] = row.get("request_id")
    query_string = _same_parameter_paper_query(row)
    row["query_string"] = query_string
    row["request_url"] = f"{row.get('endpoint') or '/api/paper'}?{query_string}"
    return row


def _same_parameter_paper_query(request: dict[str, Any]) -> str:
    request_id = request.get("same_parameter_request_id") or request.get("request_id")
    pairs = [
        ("source", request.get("source")),
        ("market", request.get("market")),
        ("factor", request.get("factor") or request.get("factor_name")),
        ("factor_windows", request.get("factor_windows")),
        ("top_n", request.get("top_n")),
        ("rebalance_interval", request.get("rebalance_interval")),
        ("start_date", request.get("start_date")),
        ("end_date", request.get("end_date")),
        ("as_of_date", request.get("as_of_date")),
        ("run_date", request.get("as_of_date")),
        ("initial_cash", request.get("initial_cash")),
        ("commission_bps", request.get("commission_bps")),
        ("slippage_bps", request.get("slippage_bps")),
        ("max_asset_weight", request.get("max_asset_weight")),
        ("max_market_weight", request.get("max_market_weight")),
        ("max_gross_exposure", request.get("max_gross_exposure")),
        ("min_cash_weight", request.get("min_cash_weight")),
        ("risk_profile_id", request.get("risk_profile_id")),
        ("same_parameter_lock_id", request.get("same_parameter_lock_id")),
        ("same_parameter_request_id", request_id),
        ("case_id", request.get("case_id")),
    ]
    return urlencode([(key, str(value)) for key, value in pairs if value is not None and str(value) != ""])


def _same_parameter_combined_manifest_row(index: int, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_number": index,
        "asset_id": row.get("asset_id"),
        "market": row.get("market") or "CN_ETF",
        "target_weight": _float_or_none(row.get("target_weight")),
        "target_value": _float_or_none(row.get("target_value")),
        "latest_price": _float_or_none(row.get("latest_price")),
        "source_factors": row.get("source_factors"),
        "executable": False,
        "order_placement_allowed": False,
    }


def _same_parameter_allocation_manifest_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_number": _int(row.get("row_number"), 0),
        "ticket_id": row.get("ticket_id"),
        "asset_id": row.get("asset_id"),
        "market": row.get("market") or "CN_ETF",
        "side": row.get("side") or "buy_or_adjust",
        "target_weight": _float_or_none(row.get("target_weight")),
        "paper_budget_value": _float_or_none(row.get("paper_budget_value")),
        "paper_quantity": _int(row.get("paper_quantity"), 0),
        "reference_price": _float_or_none(row.get("reference_price")),
        "risk_blocked": bool(row.get("risk_blocked")),
        "source_kind": row.get("source_kind"),
        "execution_mode": row.get("execution_mode") or "paper_rehearsal_only",
        "order_placement_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "auto_order_allowed": False,
    }


def _same_parameter_lock_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(_sanitize(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _same_parameter_lock_rules(lock_id: str) -> list[dict[str, Any]]:
    rows = [
        ("do_not_change_parameters_after_signal", "Do not change factor, window, top_n, cost, date, or risk profile after the signal is generated."),
        ("run_all_top3_requests_before_review", "Run every Top3 paper request or explicitly record why a request was skipped."),
        ("match_receipt_lock_id", f"Paper receipts must reference lock_id={lock_id} before any manual review."),
        ("do_not_treat_paper_request_as_order", "Paper simulation requests are not broker orders and must not be copied into a broker app."),
    ]
    return [
        {
            "rule_id": rule_id,
            "plain_rule": plain_rule,
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }
        for rule_id, plain_rule in rows
    ]


def _same_parameter_operator_steps(
    rehearsal_status: str,
    paper_allowed: bool,
    manual_allowed: bool,
) -> list[dict[str, Any]]:
    def step(step_id: str, label: str, status: str, target_id: str, workflow_id: str = "") -> dict[str, Any]:
        return {
            "step_id": step_id,
            "label": label,
            "status": status,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "manual_required": True,
            "order_placement_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "auto_order_allowed": False,
        }

    locked = rehearsal_status.startswith("blocked")
    return [
        step(
            "confirm_same_parameter_lock",
            "Confirm the locked signal date, Top3 factor parameters, risk profile, and allocation manifest",
            "blocked" if locked else "required",
            "daily-same-parameter-paper-rehearsal",
        ),
        step(
            "run_each_top3_candidate_with_locked_params",
            "Run each Top3 paper request with the locked parameters",
            "locked" if not paper_allowed else "required",
            "paper-metrics",
            "paper_simulation" if paper_allowed else "",
        ),
        step(
            "compare_paper_receipts_to_lock_id",
            "Compare paper receipts against the lock id and allocation manifest",
            "locked" if not paper_allowed else "required",
            "control-result-evidence",
        ),
        step(
            "record_post_close_journal",
            "Record the paper rehearsal result and any skip reason after close",
            "required",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        step(
            "manual_review_only_after_clean_receipts",
            "Only the human may consider an external broker review after clean locked receipts exist",
            "manual_review_only" if manual_allowed else "locked",
            "daily-manual-trading-session",
        ),
    ]


def _same_parameter_plain_answer(rehearsal_status: str) -> str:
    answers = {
        "blocked_signal_freshness": "The signal is stale; refresh CN_ETF data before running paper rehearsal.",
        "blocked_no_allocation_rows": "No allocation manifest exists; generate today's Top3 signal first.",
        "blocked_risk_budget": "Risk budget is breached; reduce exposure before paper rehearsal.",
        "blocked_price_reference": "A row lacks price or board-lot quantity; regenerate before rehearsal.",
        "manual_review_candidate": "Locked paper requests and clean evidence are available; the software still cannot place orders.",
        "ready_for_same_parameter_paper": "Run every Top3 paper request with these locked parameters and compare receipts to the lock id.",
        "waiting_for_top3_requests": "Waiting for Top3 candidate requests before paper rehearsal.",
    }
    return answers.get(rehearsal_status, "Run locked same-parameter paper rehearsal before any human decision.")


def _transition_gate_status(gate_by_id: dict[str, dict[str, Any]], gate_id: str) -> str:
    row = gate_by_id.get(gate_id) if isinstance(gate_by_id.get(gate_id), dict) else {}
    return str(row.get("status") or "required")


def _transition_research_evidence_status(gate_by_id: dict[str, dict[str, Any]]) -> str:
    statuses = [
        _transition_gate_status(gate_by_id, gate_id)
        for gate_id in (
            "walk_forward_oos",
            "lookahead_bias_audit",
            "multiple_testing_control",
            "transaction_cost_capacity",
        )
    ]
    if all(status == "pass" for status in statuses):
        return "pass"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    return "required"


def _transition_research_evidence_detail(gate_by_id: dict[str, dict[str, Any]]) -> str:
    parts = []
    for gate_id in (
        "walk_forward_oos",
        "lookahead_bias_audit",
        "multiple_testing_control",
        "transaction_cost_capacity",
    ):
        parts.append(f"{gate_id}={_transition_gate_status(gate_by_id, gate_id)}")
    return "; ".join(parts)


def _transition_observation_detail(evidence: dict[str, Any], key: str, *, required: int) -> str:
    counts = evidence.get("counts", {}) if isinstance(evidence.get("counts"), dict) else {}
    observed = _int(counts.get(key), 0)
    return f"{key}={observed}/{required}"


def _real_money_transition_gate_row(
    gate_id: str,
    label: str,
    status: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str = "",
    *,
    required_before: str,
    observed_count: int | None = None,
    required_count: int | None = None,
    missing_count: int | None = None,
    reason_count: int | None = None,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "required_before": required_before,
        "observed_count": observed_count,
        "required_count": required_count,
        "missing_count": missing_count,
        "reason_count": reason_count,
        "automation_allowed": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_money_transition_ticket_preview(
    tickets: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    risk_profile = _risk_profile_by_id(str(summary.get("risk_profile_id") or DEFAULT_RISK_PROFILE_ID))
    portfolio_value = _float(summary.get("portfolio_value"), 100000.0)
    rows: list[dict[str, Any]] = []
    for index, ticket in enumerate(tickets[:20], start=1):
        risk_budget = (
            ticket.get("risk_budget")
            if isinstance(ticket.get("risk_budget"), dict)
            else _manual_ticket_risk_budget(
                ticket,
                portfolio_value=portfolio_value,
                risk_profile=risk_profile,
            )
        )
        execution_guardrails = (
            ticket.get("execution_guardrails")
            if isinstance(ticket.get("execution_guardrails"), dict)
            else _manual_ticket_execution_guardrails(ticket)
        )
        skip_conditions = (
            ticket.get("manual_skip_conditions")
            if isinstance(ticket.get("manual_skip_conditions"), list)
            else _manual_ticket_skip_conditions(
                {**ticket, "risk_budget": risk_budget, "execution_guardrails": execution_guardrails}
            )
        )
        rows.append(
            {
                "step_number": index,
                "ticket_id": str(ticket.get("ticket_id") or f"manual_review_{index}"),
                "asset_id": str(ticket.get("asset_id") or ""),
                "market": str(ticket.get("market") or "CN_ETF"),
                "side": str(ticket.get("side") or "review"),
                "target_weight": _float_or_none(ticket.get("target_weight")),
                "target_value": _float_or_none(ticket.get("target_value")),
                "delta_value": _float_or_none(ticket.get("delta_value")),
                "reference_price": _float_or_none(ticket.get("reference_price") or ticket.get("latest_price")),
                "rounded_quantity": _int(ticket.get("rounded_quantity"), 0),
                "rounded_quantity_delta": _int(
                    ticket.get("rounded_quantity_delta"),
                    _int(ticket.get("rounded_quantity"), 0),
                ),
                "rounded_value": _float_or_none(ticket.get("rounded_value")),
                "cash_delta_after_rounding": _float_or_none(ticket.get("cash_delta_after_rounding")),
                "source_factors": ticket.get("source_factors"),
                "risk_budget": risk_budget,
                "execution_guardrails": execution_guardrails,
                "manual_skip_conditions": skip_conditions,
                "plain_instruction": ticket.get("plain_instruction")
                or ticket.get("copy_text")
                or "仅供人工复核；不是订单，系统不会提交到券商。",
                "review_only": True,
                "executable": False,
                "live_order_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            }
        )
    return rows


def _real_money_transition_signal_cards(
    factors: list[dict[str, Any]],
    signal_cards: list[dict[str, Any]],
    health: dict[str, Any],
) -> list[dict[str, Any]]:
    health_rows = {
        str(row.get("factor_name")): row
        for row in health.get("factor_rows", [])
        if isinstance(row, dict) and row.get("factor_name")
    }
    signal_by_factor = {
        str(row.get("factor_name")): row
        for row in signal_cards
        if isinstance(row, dict) and row.get("factor_name")
    }
    rows: list[dict[str, Any]] = []
    for index, factor in enumerate(factors[:3], start=1):
        factor_name = str(factor.get("factor_name") or factor.get("factor") or "")
        health_row = health_rows.get(factor_name, {})
        signal_row = signal_by_factor.get(factor_name, {})
        rows.append(
            {
                "rank": _int(factor.get("rank"), index),
                "case_id": str(factor.get("case_id") or factor_name),
                "factor_name": factor_name,
                "market": str(factor.get("market") or "CN_ETF"),
                "signal_status": signal_row.get("status") or "waiting",
                "health_status": health_row.get("health_status") or "watch",
                "health_reason_codes": health_row.get("reason_codes") if isinstance(health_row.get("reason_codes"), list) else [],
                "metrics": health_row.get("metrics") if isinstance(health_row.get("metrics"), dict) else {},
                "order_placement_allowed": False,
            }
        )
    return rows


def _real_money_transition_operator_script(
    *,
    decision: str,
    next_target: str,
    next_workflow: str,
    paper_status: str,
    journal_status: str,
    ticket_risk_status: str,
    has_manual_material: bool,
) -> list[dict[str, Any]]:
    rows = [
        _real_money_transition_operator_step(
            1,
            "review_top3_factor_health",
            "复核今日 Top3 因子健康",
            "blocked" if decision == "rotate_or_reduce_top3_first" else "ready",
            "先看因子是否退役、降权或只观察，不能只按收益排行榜买。",
            "daily-factor-health-rows",
        ),
        _real_money_transition_operator_step(
            2,
            "run_same_parameter_paper",
            "运行同参数模拟盘",
            "pass" if paper_status == "pass" else "required",
            "用今天同一组因子、TopN、成本、风险档位和资金规模跑模拟盘回执。",
            "paper-metrics",
            "paper_simulation",
        ),
        _real_money_transition_operator_step(
            3,
            "review_manual_ticket_risk_budget",
            "核对人工票据风险预算",
            ticket_risk_status,
            "逐张看 ETF、方向、数量、金额、现金差额、单 ETF 上限和跳过条件。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        _real_money_transition_operator_step(
            4,
            "open_external_broker_manually",
            "如仍决定观察，只能本人离开系统手工打开券商端",
            "manual_locked" if has_manual_material else "waiting",
            "系统只提供复核材料，不连接券商、不读账户、不提交订单。",
            "control-safety-boundary",
        ),
        _real_money_transition_operator_step(
            5,
            "record_post_close_journal",
            "收盘后记录复盘",
            "pass" if journal_status == "pass" else "required",
            "无论执行、跳过还是只模拟，都记录原因、滑点、未成交、回撤和下一轮问题。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]
    if next_target and not any(row["target_id"] == next_target for row in rows):
        rows.insert(
            0,
            _real_money_transition_operator_step(
                0,
                "follow_primary_next_step",
                "先处理当前最缺的一步",
                "next",
                f"当前结论={decision}，先按主按钮补齐证据。",
                next_target,
                next_workflow,
            ),
        )
    return rows


def _real_money_transition_operator_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    plain_action: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_money_transition_capital_mode(decision: str) -> str:
    if decision == "production_manual_review_candidate":
        return "production_manual_review_only"
    if decision == "small_capital_manual_observation_candidate":
        return "small_capital_manual_observation_review_only"
    if decision == "paper_rehearsal_required":
        return "paper_simulation_only"
    if decision in {"build_manual_ticket_pack_first", "generate_same_day_signal_first"}:
        return "research_signal_only"
    return "blocked_or_research_only"


def _real_money_transition_capital_policy_text(capital_mode: str) -> str:
    policies = {
        "production_manual_review_only": "可以进入人工生产复核候选，但仍不允许软件下单。",
        "small_capital_manual_observation_review_only": "可以进入小资金人工观察候选，但必须本人外部手工决定。",
        "paper_simulation_only": "只能运行同参数模拟盘和人工票据复核，不能进入真实资金。",
        "research_signal_only": "只能生成研究信号和票据材料，还缺执行证据。",
        "blocked_or_research_only": "存在阻断项，只能研究或修复，不能推进资金动作。",
    }
    return policies.get(capital_mode, policies["blocked_or_research_only"])


def _real_money_transition_forbidden_actions() -> list[dict[str, Any]]:
    return [
        _live_profitability_action(
            "direct_buy_top3",
            "直接买 Top3 因子",
            "Top3 只是候选入口；没有信号、回执、复盘、风险预算和人工确认时不能买。",
            "factor-leaderboard-table",
            "forbidden",
        ),
        _live_profitability_action(
            "skip_paper_and_journal",
            "跳过模拟盘和盘后复盘",
            "没有同参数模拟回执和盘后记录，就无法判断滑点、回撤、成交和人为偏差。",
            "paper-metrics",
            "forbidden",
        ),
        _live_profitability_action(
            "auto_broker_order",
            "自动连接券商或下单",
            "当前项目边界禁止券商连接、账户读取、真实委托和自动交易。",
            "control-safety-boundary",
            "forbidden",
        ),
        _live_profitability_action(
            "ignore_ticket_risk_budget",
            "忽略票据风险预算",
            "单 ETF、总仓位、现金、价格偏离或本人无法解释时必须跳过。",
            "daily-manual-broker-handoff-ticket-table",
            "forbidden",
        ),
    ]


def _daily_factor_health_row(
    candidate: dict[str, Any],
    *,
    research_evidence_ready: bool,
) -> dict[str, Any]:
    factor_name = str(candidate.get("factor_name") or candidate.get("factor") or "").strip()
    market = str(candidate.get("market") or "CN_ETF").upper()
    sharpe = _daily_factor_health_metric(candidate, "sharpe", "oos_sharpe", "test_sharpe", "paper_sharpe")
    annualized_return = _daily_factor_health_metric(
        candidate,
        "annualized_return",
        "annual_return",
        "cagr",
        "paper_annualized_return",
    )
    total_return = _daily_factor_health_metric(candidate, "total_return", "return", "paper_total_return")
    max_drawdown = _daily_factor_health_metric(
        candidate,
        "max_drawdown",
        "max_dd",
        "max_equity_drawdown",
        "paper_max_drawdown",
    )
    win_rate = _daily_factor_health_metric(candidate, "win_rate", "monthly_win_rate", "paper_win_rate")
    rank_ic = _daily_factor_health_metric(candidate, "rank_ic", "RankIC", "mean_ic", "ic_mean")
    trade_count_value = _daily_factor_health_metric(candidate, "trade_count", "n_trades", "num_trades", "paper_trade_count")
    trade_count = _int(trade_count_value, 0) if trade_count_value is not None else 0
    drawdown_abs = abs(max_drawdown) if max_drawdown is not None else None
    reasons: list[str] = []

    if market != "CN_ETF":
        reasons.append("wrong_market")
    if bool(candidate.get("fallback_baseline")):
        reasons.append("fallback_baseline")
    if sharpe is None:
        reasons.append("missing_sharpe")
    elif sharpe < 0:
        reasons.append("negative_sharpe")
    elif sharpe < 0.5:
        reasons.append("low_sharpe")
    if drawdown_abs is None:
        reasons.append("missing_drawdown")
    elif drawdown_abs >= 0.30:
        reasons.append("high_drawdown")
    elif drawdown_abs >= 0.25:
        reasons.append("elevated_drawdown")
    if win_rate is None:
        reasons.append("missing_win_rate")
    elif win_rate < 0.48:
        reasons.append("low_win_rate")
    elif win_rate < 0.55:
        reasons.append("weak_win_rate")
    if rank_ic is None:
        reasons.append("missing_rank_ic")
    elif rank_ic < 0:
        reasons.append("negative_rank_ic")
    elif abs(rank_ic) < 0.02:
        reasons.append("weak_rank_ic")
    if trade_count <= 0:
        reasons.append("missing_trade_count")
    elif trade_count < 30:
        reasons.append("thin_trade_count")
    elif trade_count < 60:
        reasons.append("limited_trade_count")
    if not research_evidence_ready:
        reasons.append("missing_research_evidence")

    retire_reasons = {
        "wrong_market",
        "fallback_baseline",
        "negative_sharpe",
        "high_drawdown",
        "negative_rank_ic",
        "thin_trade_count",
        "low_win_rate",
    }
    if any(reason in retire_reasons for reason in reasons):
        health_status = "retire_candidate"
        decision = "exclude_or_reduce_before_paper"
        required_action = "先暂停、降权或替换这个因子；不要把它作为今日实盘候选。"
    elif reasons:
        health_status = "watch"
        decision = "paper_observe_only"
        required_action = "只做同参数模拟盘观察，盘后记录表现；不要扩大资金。"
    else:
        health_status = "healthy_for_paper_observation"
        decision = "paper_observation_allowed_not_order"
        required_action = "可以进入同参数模拟盘和人工复核，但仍不是买入指令。"

    return {
        "rank": _int(candidate.get("rank"), 0),
        "case_id": str(candidate.get("case_id") or factor_name),
        "factor_name": factor_name,
        "market": market,
        "family": candidate.get("family"),
        "health_status": health_status,
        "decision": decision,
        "required_action": required_action,
        "reason_codes": reasons,
        "plain_diagnosis": _daily_factor_health_reason_text(reasons),
        "metrics": {
            "sharpe": sharpe,
            "annualized_return": annualized_return,
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "rank_ic": rank_ic,
            "trade_count": trade_count,
        },
        "params": candidate.get("params") if isinstance(candidate.get("params"), dict) else {},
        "target_id": "daily-factor-health-rows",
        "workflow_id": "paper_simulation" if health_status != "retire_candidate" else "",
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _daily_factor_health_metric(candidate: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key not in candidate:
            continue
        value = _daily_factor_health_float(candidate.get(key))
        if value is not None:
            if key in {"win_rate", "monthly_win_rate", "paper_win_rate"} and value > 1:
                return value / 100.0
            return value
    return None


def _daily_factor_health_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    scale = 1.0
    if text.endswith("%"):
        text = text[:-1].strip()
        scale = 0.01
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    number *= scale
    return number if math.isfinite(number) else None


def _daily_factor_health_reason_text(reasons: list[str]) -> str:
    if not reasons:
        return "核心指标和研究证据暂时没有触发退役门；继续用模拟盘观察，不能宣称稳定盈利。"
    labels = {
        "wrong_market": "不是 CN_ETF 主线",
        "fallback_baseline": "兜底基线不能推广",
        "missing_sharpe": "缺少 Sharpe",
        "negative_sharpe": "Sharpe 为负",
        "low_sharpe": "Sharpe 偏低",
        "missing_drawdown": "缺少回撤",
        "high_drawdown": "回撤达到 30% 级别",
        "elevated_drawdown": "回撤偏高",
        "missing_win_rate": "缺少胜率",
        "low_win_rate": "胜率低于 48%",
        "weak_win_rate": "胜率未达到 55%",
        "missing_rank_ic": "缺少 RankIC",
        "negative_rank_ic": "RankIC 为负",
        "weak_rank_ic": "RankIC 太弱",
        "missing_trade_count": "缺少交易样本",
        "thin_trade_count": "交易样本少于 30 笔",
        "limited_trade_count": "交易样本少于 60 笔",
        "missing_research_evidence": "缺少 OOS/未来函数/多重检验/成本容量证据",
    }
    return "；".join(labels.get(reason, reason) for reason in reasons)


def _daily_factor_health_actions(
    *,
    decision: str,
    retire_count: int,
    watch_count: int,
    has_factors: bool,
    next_label: str,
    next_target: str,
    next_workflow: str,
    paper_observation_allowed: bool,
    recent_observation_degradation_required: bool = False,
) -> list[dict[str, Any]]:
    actions = [
        _daily_factor_health_action(
            "follow_factor_health_next_step",
            next_label,
            f"当前因子健康结论={decision}；先处理健康门，再看票据或模拟盘。",
            next_target,
            "next",
            next_workflow,
        )
    ]
    if retire_count:
        actions.append(
            _daily_factor_health_action(
                "retire_bad_factor",
                "退役或降权问题因子",
                f"有 {retire_count} 个 Top3 因子触发退役门，先从今日候选里剔除、降权或改为只观察。",
                "factor-leaderboard-table",
                "required",
            )
        )
    if recent_observation_degradation_required:
        actions.append(
            _daily_factor_health_action(
                "review_recent_observation_degradation",
                "复盘近期观察退化",
                "近期纸面/人工观察收益或胜率退化；先写盘后复盘、查成本/滑点/市场状态，再决定降级、隔离或替换。",
                "beginner-post-close-journal-board",
                "required",
                "post_close_journal",
            )
        )
    if paper_observation_allowed and (watch_count or has_factors):
        actions.append(
            _daily_factor_health_action(
                "run_same_parameter_paper",
                "同参数模拟盘观察",
                "健康门没有硬性退役项时，用同一组因子、TopN、成本和风险档位先跑模拟盘。",
                "paper-metrics",
                "allowed" if not retire_count else "waiting",
                "paper_simulation" if not retire_count else "",
            )
        )
    actions.append(
        _daily_factor_health_action(
            "block_direct_top3_buy",
            "禁止排行榜直买",
            "Top3 因子是候选入口，不是实盘指令；系统不连接券商、不读取账户、不自动下单。",
            "control-safety-boundary",
            "forbidden",
        )
    )
    return actions


def _daily_factor_health_action(
    action_id: str,
    label: str,
    plain_action: str,
    target_id: str,
    status: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _live_profitability_evidence_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    source = snapshot if isinstance(snapshot, dict) else {}
    raw_counts = source.get("counts") if isinstance(source.get("counts"), dict) else source
    raw_flags = source.get("flags") if isinstance(source.get("flags"), dict) else source
    raw_risk = (
        source.get("risk_state")
        if isinstance(source.get("risk_state"), dict)
        else source.get("risk")
        if isinstance(source.get("risk"), dict)
        else source
    )
    counts = {
        "matched_paper_receipts": _live_profitability_evidence_count(
            raw_counts.get("matched_paper_receipts", raw_counts.get("paper_simulation_receipts"))
        ),
        "post_close_journal_receipts": _live_profitability_evidence_count(
            raw_counts.get("post_close_journal_receipts", raw_counts.get("post_close_journals"))
        ),
        "manual_execution_clean_receipts": _live_profitability_evidence_count(
            raw_counts.get("manual_execution_clean_receipts", raw_counts.get("clean_manual_execution_receipts"))
        ),
        "manual_execution_blocked_receipts": _live_profitability_evidence_count(
            raw_counts.get("manual_execution_blocked_receipts", raw_counts.get("blocked_manual_execution_receipts"))
        ),
        "manual_execution_missing_review_receipts": _live_profitability_evidence_count(
            raw_counts.get(
                "manual_execution_missing_review_receipts",
                raw_counts.get("missing_manual_execution_review_receipts"),
            )
        ),
        "paper_ready_observations": _live_profitability_evidence_count(
            raw_counts.get("paper_ready_observations")
        ),
        "same_parameter_top3_required_requests": _live_profitability_evidence_count(
            raw_counts.get("same_parameter_top3_required_requests")
        ),
        "same_parameter_top3_matched_requests": _live_profitability_evidence_count(
            raw_counts.get("same_parameter_top3_matched_requests")
        ),
    }
    raw_pre_live = (
        source.get("pre_live_master_gate")
        if isinstance(source.get("pre_live_master_gate"), dict)
        else source.get("pre_live_gate")
        if isinstance(source.get("pre_live_gate"), dict)
        else source
    )
    pre_live_status = str(
        raw_pre_live.get("status")
        or raw_pre_live.get("pre_live_master_gate_status")
        or raw_pre_live.get("master_gate_status")
        or "not_checked"
    )
    pre_live_decision = str(
        raw_pre_live.get("decision")
        or raw_pre_live.get("pre_live_master_gate_decision")
        or raw_pre_live.get("master_gate_decision")
        or "continue_same_parameter_paper_and_closure"
    )
    pre_live_manual_allowed = (
        pre_live_status == "manual_small_capital_observation_ready"
        and pre_live_decision == "external_manual_small_capital_observation_only"
    )
    flags = {
        "walk_forward_oos_passed": _live_profitability_evidence_flag(raw_flags.get("walk_forward_oos_passed")),
        "lookahead_bias_audit_passed": _live_profitability_evidence_flag(raw_flags.get("lookahead_bias_audit_passed")),
        "multiple_testing_control_passed": _live_profitability_evidence_flag(raw_flags.get("multiple_testing_control_passed")),
        "transaction_cost_capacity_passed": _live_profitability_evidence_flag(raw_flags.get("transaction_cost_capacity_passed")),
    }
    risk_state = {
        "today_pnl_pct": _evidence_first_float(
            raw_risk,
            "today_pnl_pct",
            "today_return_pct",
            "current_day_pnl_pct",
            "current_session_pnl_pct",
        ),
        "today_loss_pct": _evidence_first_float(
            raw_risk,
            "today_loss_pct",
            "current_day_loss_pct",
            "session_loss_pct",
        ),
        "current_drawdown_pct": _evidence_first_float(
            raw_risk,
            "current_drawdown_pct",
            "portfolio_drawdown_pct",
            "latest_drawdown_pct",
            "max_drawdown",
        ),
        "consecutive_loss_days": _evidence_first_float(
            raw_risk,
            "consecutive_loss_days",
            "loss_streak_days",
            "red_day_streak",
        ),
        "cooldown_days_remaining": _evidence_first_float(
            raw_risk,
            "cooldown_days_remaining",
            "risk_cooldown_days_remaining",
            "cooldown_remaining",
        ),
        "recent_observation_count": _evidence_first_float(
            raw_risk,
            "recent_observation_count",
            "recent_paper_observation_count",
            "recent_observation_days",
            "recent_sample_count",
        ),
        "recent_observation_return_pct": _evidence_first_float(
            raw_risk,
            "recent_observation_return_pct",
            "recent_paper_return_pct",
            "recent_manual_observation_return_pct",
            "recent_cumulative_return_pct",
        ),
        "recent_observation_win_rate": _evidence_first_float(
            raw_risk,
            "recent_observation_win_rate",
            "recent_paper_win_rate",
            "recent_manual_observation_win_rate",
            "recent_win_rate",
        ),
    }
    return {
        "mode": str(source.get("mode") or ("snapshot" if source else "empty")),
        "counts": counts,
        "flags": flags,
        "risk_state": risk_state,
        "missing_counts": {
            "matched_paper_receipts": max(0, 5 - counts["matched_paper_receipts"]),
            "post_close_journal_receipts": max(0, 5 - counts["post_close_journal_receipts"]),
            "manual_execution_clean_receipts": max(0, 5 - counts["manual_execution_clean_receipts"]),
            "paper_ready_observations": max(0, 20 - counts["paper_ready_observations"]),
            "same_parameter_top3_requests": max(
                0,
                counts["same_parameter_top3_required_requests"]
                - counts["same_parameter_top3_matched_requests"],
            ),
        },
        "minimum_required_counts": {
            "matched_paper_receipts": 5,
            "post_close_journal_receipts": 5,
            "manual_execution_clean_receipts": 5,
            "paper_ready_observations": 20,
            "same_parameter_top3_required_requests": counts["same_parameter_top3_required_requests"],
        },
        "pre_live_master_gate": {
            "status": pre_live_status,
            "decision": pre_live_decision,
            "manual_small_capital_observation_allowed": pre_live_manual_allowed,
            "external_manual_only": True,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
    }


def _live_profitability_evidence_count(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    if isinstance(value, dict):
        items = value.get("items")
        if isinstance(items, list):
            return len(items)
        for key in ("count", "observed_count", "value", "total", "n"):
            if key in value:
                return _live_profitability_evidence_count(value.get(key), default)
        return default
    return max(0, _int(value, default))


def _evidence_first_float(source: dict[str, Any], *keys: str) -> float | None:
    if not isinstance(source, dict):
        return None
    for key in keys:
        if key in source:
            value = _float_or_none(source.get(key))
            if value is not None:
                return value
    return None


def _live_profitability_evidence_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        for key in ("passed", "pass", "ready", "clear", "ok", "completed"):
            if key in value:
                return _live_profitability_evidence_flag(value.get(key))
        value = value.get("status") or value.get("decision") or value.get("value")
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "pass", "passed", "ok", "ready", "clear", "clean", "completed"}


def _live_profitability_gate(
    gate_id: str,
    label: str,
    status: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str = "",
    *,
    evidence_kind: str,
    required_before: str,
    minimum_required_observations: int = 0,
    observed_count: int = 0,
) -> dict[str, Any]:
    minimum = max(0, _int(minimum_required_observations, 0))
    observed = max(0, _int(observed_count, 0))
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "evidence_kind": evidence_kind,
        "required_before": required_before,
        "minimum_required_observations": minimum,
        "observed_count": observed,
        "missing_count": max(0, minimum - observed) if minimum else 0,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _live_profitability_ladder_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    plain_state: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "plain_state": plain_state,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _live_profitability_today_actions(
    *,
    decision: str,
    next_label: str,
    next_target: str,
    next_workflow: str,
    paper_rehearsal_allowed: bool,
    manual_review_material_ready: bool,
    has_signal_targets: bool,
) -> list[dict[str, Any]]:
    actions = [
        _live_profitability_action(
            "follow_primary_next_step",
            next_label or "查看下一步",
            f"当前系统判断={decision}；先按主按钮补齐最缺的证据。",
            next_target or "daily-trade-advisory",
            "next",
            next_workflow,
        )
    ]
    if paper_rehearsal_allowed:
        actions.append(
            _live_profitability_action(
                "run_same_parameter_paper",
                "运行同参数模拟盘",
                "把今天的候选、TopN、成本、风险档位和资金规模用同一参数跑一遍本地模拟盘。",
                "paper-metrics",
                "allowed",
                "paper_simulation",
            )
        )
    if manual_review_material_ready:
        actions.append(
            _live_profitability_action(
                "review_manual_ticket_pack",
                "人工核对票据",
                "只核对 ETF、方向、数量、金额、现金和风险；这不是委托单。",
                "daily-manual-broker-handoff-ticket-table",
                "manual_review",
            )
        )
    if has_signal_targets:
        actions.append(
            _live_profitability_action(
                "write_post_close_journal",
                "收盘后写复盘",
                "无论执行、跳过还是只模拟，都要记录原因和异常，供下一轮审计使用。",
                "beginner-post-close-journal-board",
                "required",
                "post_close_journal",
            )
        )
    return actions


def _live_profitability_action(
    action_id: str,
    label: str,
    plain_action: str,
    target_id: str,
    status: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _live_profitability_control(
    control_id: str,
    label: str,
    plain_control: str,
    target_id: str,
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "label": label,
        "status": "required",
        "plain_control": plain_control,
        "target_id": target_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _deployment_sequence_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    plain_action: str,
    evidence: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _deployment_readiness_gate(
    gate_id: str,
    label: str,
    status: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _deployment_profitability_control(
    control_id: str,
    label: str,
    plain_control: str,
    target_id: str,
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "label": label,
        "status": "required",
        "plain_control": plain_control,
        "target_id": target_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _deployment_ticket_preview(ticket: dict[str, Any], step_number: int) -> dict[str, Any]:
    side = str(ticket.get("side") or ticket.get("action") or "review")
    operation = _deployment_operation_from_side(side)
    reference_price = _float_or_none(ticket.get("reference_price") or ticket.get("latest_price"))
    rounded_quantity = _int(ticket.get("rounded_quantity"), 0)
    rounded_value = _float_or_none(ticket.get("rounded_value"))
    return {
        "step_number": step_number,
        "ticket_id": str(ticket.get("ticket_id") or f"deployment_review_{step_number}"),
        "asset_id": str(ticket.get("asset_id") or ""),
        "market": str(ticket.get("market") or "CN_ETF"),
        "operation": operation,
        "side": side,
        "reference_price": reference_price,
        "current_quantity": _float_or_none(ticket.get("current_quantity")),
        "target_weight": _float_or_none(ticket.get("target_weight")),
        "target_value": _float_or_none(ticket.get("target_value")),
        "delta_value": _float_or_none(ticket.get("delta_value")),
        "rounded_quantity": rounded_quantity,
        "rounded_quantity_delta": _int(ticket.get("rounded_quantity_delta"), rounded_quantity),
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": _float_or_none(ticket.get("cash_delta_after_rounding")),
        "source_factors": ticket.get("source_factors"),
        "review_only": True,
        "executable": False,
        "warning_code": "manual_review_not_order",
        "plain_instruction": "这只是人工复核材料，不是订单；券商端价格、数量、现金和风险必须由本人再次确认。",
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _deployment_operation_from_side(side: str) -> str:
    normalized = str(side or "").lower()
    if normalized in {"buy", "increase", "buy_or_adjust"}:
        return "buy"
    if normalized in {"sell", "decrease"}:
        return "sell"
    if normalized == "hold":
        return "hold"
    return "review"


def _real_world_capital_deployment_ladder(
    *,
    selected_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    blockers: list[str],
) -> list[dict[str, Any]]:
    blocked = bool(blockers)
    has_candidates = selected_count > 0
    has_same_day_signal = signal_count > 0 and target_count > 0
    has_manual_tickets = ticket_count > 0

    return [
        _real_world_capital_stage(
            1,
            "research_signal",
            "研究信号层",
            "done" if has_candidates else "required",
            "0 元真实资金；只看 CN_ETF 候选、信号和证据。",
            "先把前三候选从长期、样本外、成本后证据里挑出来；不能按历史收益榜直接买。",
            "factor-leaderboard-table",
            "",
        ),
        _real_world_capital_stage(
            2,
            "same_parameter_paper",
            "同参数模拟盘层",
            "required" if has_manual_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "0 元真实资金；只跑本地模拟盘。",
            "用同参数模拟盘复核今日前三信号、TopN、成本、调仓和风险档位；没有回执不能进入人工观察。",
            "paper-metrics",
            "paper_simulation" if has_manual_tickets and not blocked else "",
        ),
        {
            **_real_world_capital_stage(
                3,
                "small_capital_manual_observation",
                "小资金人工观察层",
                "locked_until_evidence",
                "系统不读取账户、不建议具体实盘金额；只能由用户离开系统后人工决定。",
                "至少 5 次同参数模拟盘回执和 5 次收盘复盘都干净，且无盘前红灯，才允许讨论小资金人工观察。",
                "beginner-live-handoff-board",
                "",
            ),
            "minimum_matched_paper_receipts": 5,
            "minimum_post_close_journals": 5,
        },
        {
            **_real_world_capital_stage(
                4,
                "production_manual_review",
                "正式人工复核层",
                "locked_future_phase",
                "当前项目不开放；需要未来单独批准券商和账户边界。",
                "至少 20 次纸面观察合格、风控和成交偏差稳定、人工审计通过后，才进入未来正式人工复核方案。",
                "control-safety-boundary",
                "",
            ),
            "minimum_paper_ready_observations": 20,
        },
    ]


def _real_world_capital_stage(
    stage_number: int,
    stage_id: str,
    label: str,
    status: str,
    capital_mode: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    return {
        "stage_number": stage_number,
        "stage_id": stage_id,
        "label": label,
        "status": status,
        "capital_mode": capital_mode,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_world_runbook_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    plain_action: str,
    evidence: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_world_gate(
    gate_id: str,
    label: str,
    status: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_world_boundary(boundary_id: str, label: str, plain_boundary: str) -> dict[str, Any]:
    return {
        "boundary_id": boundary_id,
        "label": label,
        "plain_boundary": plain_boundary,
        "enforced": True,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _real_world_ticket_preview(ticket: dict[str, Any], step_number: int) -> dict[str, Any]:
    source_factors = ticket.get("source_factors")
    guardrails = (
        ticket.get("execution_guardrails")
        if isinstance(ticket.get("execution_guardrails"), dict)
        else _manual_ticket_execution_guardrails(ticket)
    )
    if isinstance(source_factors, list):
        factor_text = ", ".join(str(item) for item in source_factors)
    else:
        factor_text = str(source_factors or "")
    return {
        "step_number": step_number,
        "ticket_id": str(ticket.get("ticket_id") or f"manual_review_{step_number}"),
        "asset_id": str(ticket.get("asset_id") or ""),
        "market": str(ticket.get("market") or "CN_ETF"),
        "side": str(ticket.get("side") or "review"),
        "target_weight": _float_or_none(ticket.get("target_weight")),
        "target_value": _float_or_none(ticket.get("target_value")),
        "delta_value": _float_or_none(ticket.get("delta_value")),
        "reference_price": _float_or_none(ticket.get("reference_price") or ticket.get("latest_price")),
        "rounded_quantity": _int(ticket.get("rounded_quantity"), 0),
        "rounded_quantity_delta": _int(ticket.get("rounded_quantity_delta"), _int(ticket.get("rounded_quantity"), 0)),
        "rounded_value": _float_or_none(ticket.get("rounded_value")),
        "cash_delta_after_rounding": _float_or_none(ticket.get("cash_delta_after_rounding")),
        "lower_price_bound": _float_or_none(guardrails.get("lower_price_bound")),
        "upper_price_bound": _float_or_none(guardrails.get("upper_price_bound")),
        "max_reference_price_deviation_pct": _float_or_none(guardrails.get("max_reference_price_deviation_pct")),
        "max_slippage_bps": _int(guardrails.get("max_slippage_bps"), 0),
        "max_estimated_slippage_cost": _float_or_none(guardrails.get("max_estimated_slippage_cost")),
        "source_factors": factor_text,
        "executable": False,
        "review_only": True,
        "live_order_allowed": False,
        "order_placement_allowed": False,
        "plain_instruction": "软件不会下单；这只是人工核对材料，券商端实时价格、现金、数量和风险必须本人再确认。",
    }


def _paper_request_summary(request: dict[str, Any]) -> str:
    if not request:
        return "paper_request=waiting"
    return (
        f"factor={request.get('factor') or request.get('factor_name') or '--'}; "
        f"windows={request.get('factor_windows') or '--'}; "
        f"top_n={request.get('top_n') or '--'}; "
        f"cost={request.get('commission_bps') or '--'}bps"
    )


def _format_percent_plain(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return "--"
    return f"{number:.0%}"


def _build_signal_execution_paper_handoff(
    *,
    factors: list[dict[str, Any]],
    market: str,
    portfolio_value: float,
    summary: dict[str, Any],
) -> dict[str, Any]:
    primary = factors[0] if factors else {}
    params = primary.get("params") if isinstance(primary.get("params"), dict) else {}
    factor_name = str(primary.get("factor_name") or primary.get("factor") or "momentum_2")
    factor_windows = _paper_factor_windows(params.get("factor_windows") or primary.get("factor_windows"), factor_name)
    cost_bps = _float(params.get("cost_bps"), _float(params.get("commission_bps"), 5.0))
    top_n = _int(params.get("top_n") or params.get("topN"), 2)
    rebalance_interval = _int(params.get("rebalance_interval") or params.get("holding_period"), 1)
    max_asset_weight = _float(summary.get("max_asset_weight"), 0.4)
    max_market_weight = _float(summary.get("max_market_weight"), 1.0)
    max_gross_exposure = _float(summary.get("applied_max_gross_exposure"), _float(summary.get("requested_max_gross_exposure"), 1.0))
    min_cash_weight = _float(summary.get("min_cash_weight"), max(0.0, 1.0 - max_gross_exposure))
    request = {
        "source": "processed-bars",
        "market": market,
        "factor": factor_name,
        "factor_windows": factor_windows,
        "top_n": top_n,
        "rebalance_interval": rebalance_interval,
        "initial_cash": portfolio_value,
        "commission_bps": cost_bps,
        "slippage_bps": cost_bps,
        "max_asset_weight": max_asset_weight,
        "max_market_weight": max_market_weight,
        "max_gross_exposure": max_gross_exposure,
        "min_cash_weight": min_cash_weight,
    }
    return {
        "stage": "daily_signal_paper_simulation_handoff",
        "summary": {
            "status": "ready" if factors else "waiting_for_candidate",
            "default_factor_name": factor_name,
            "candidate_count": len(factors),
            "multi_factor_combo_supported": False,
            "uses_rank_1_candidate_by_default": True,
            "manual_review_required": True,
            "paper_simulation_required": True,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "recommended_request": request,
        "candidate_params": [
            {
                "rank": _int(row.get("rank"), index),
                "factor": str(row.get("factor_name") or row.get("factor") or ""),
                "case_id": row.get("case_id"),
                "factor_windows": _paper_factor_windows(
                    (row.get("params") if isinstance(row.get("params"), dict) else {}).get("factor_windows")
                    or row.get("factor_windows"),
                    str(row.get("factor_name") or row.get("factor") or ""),
                ),
                "top_n": _int((row.get("params") if isinstance(row.get("params"), dict) else {}).get("top_n"), top_n),
                "cost_bps": _float((row.get("params") if isinstance(row.get("params"), dict) else {}).get("cost_bps"), cost_bps),
            }
            for index, row in enumerate(factors[:3], start=1)
        ],
        "plain_warning": "当前模拟盘接口按单因子运行；默认把排名第一候选填入模拟盘表单，前三候选仍需分别复核，不代表三因子组合已经可实盘。",
    }


def _paper_factor_windows(value: Any, factor_name: str) -> str:
    if isinstance(value, (list, tuple, set)):
        windows = [_int(item, 0) for item in value]
    else:
        text = str(value or "").strip().replace("[", "").replace("]", "")
        windows = [_int(item.strip(), 0) for item in text.split(",") if item.strip()]
    cleaned = [item for item in windows if item > 0]
    if cleaned:
        return ",".join(str(item) for item in sorted(set(cleaned)))
    suffix = str(factor_name or "").rsplit("_", 1)[-1]
    fallback = _int(suffix, 20)
    return str(fallback if fallback > 0 else 20)


def _signal_execution_step(
    step_number: int,
    step_id: str,
    label: str,
    status: str,
    plain_action: str,
    evidence: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "label": label,
        "status": status,
        "plain_action": plain_action,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _signal_execution_gate(
    gate_id: str,
    label: str,
    status: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _signal_execution_rule(rule_id: str, plain_rule: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "plain_rule": plain_rule,
        "order_placement_allowed": False,
    }


def _trading_system_evidence(
    evidence_id: str,
    label: str,
    status: str,
    evidence: str,
    gui_target: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "gui_target": gui_target,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _trading_system_operator_step(
    step_number: int,
    step_id: str,
    title: str,
    status: str,
    plain_action: str,
    gui_target: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "step_id": step_id,
        "title": title,
        "status": status,
        "plain_action": plain_action,
        "gui_target": gui_target,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _trading_system_layer(layer_id: str, label: str, responsibility: str) -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "label": label,
        "responsibility": responsibility,
        "order_placement_allowed": False,
    }


def _trading_system_operator_summary(status: str) -> str:
    messages = {
        "blocked_red_light": "今天还不能进入人工操作，先处理信号、数据或风险红灯。",
        "paper_first_manual_review": "今天最多进入模拟盘优先的人工复核，仍不是自动实盘。",
        "build_manual_tickets": "已有当日信号，先补全人工票据和同参数模拟盘。",
        "waiting_for_today_signal": "先生成当日 CN_ETF 前三因子信号，再看后续证据。",
    }
    return messages.get(status, "按每日交易系统证据链逐步推进。")


def _build_daily_trade_system_state(
    *,
    decision: str,
    market: str,
    selected_factor_count: int,
    signal_count: int,
    target_count: int,
    ticket_count: int,
    blocker_count: int,
    position_status: str,
    pre_live_master_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocked = decision.startswith("blocked") or blocker_count > 0 or position_status == "error"
    has_candidate_pool = market == "CN_ETF" and selected_factor_count > 0
    has_today_signal = signal_count > 0 and target_count > 0
    has_manual_ticket = ticket_count > 0
    pre_live_summary = pre_live_master_gate if isinstance(pre_live_master_gate, dict) else {}
    pre_live_status = str(pre_live_summary.get("status") or "not_checked")
    pre_live_decision = str(pre_live_summary.get("decision") or "continue_same_parameter_paper_and_closure")
    pre_live_manual_allowed = (
        pre_live_status == "manual_small_capital_observation_ready"
        and pre_live_decision == "external_manual_small_capital_observation_only"
        and not blocked
        and has_manual_ticket
    )
    if position_status == "error":
        mode = "blocked_fix_current_positions"
    elif blocked:
        mode = "blocked_pretrade_red_light"
    elif pre_live_manual_allowed:
        mode = "manual_small_capital_observation_candidate"
    elif has_manual_ticket:
        mode = "paper_rehearsal_required"
    elif has_today_signal:
        mode = "manual_ticket_required"
    else:
        mode = "waiting_for_daily_signal"

    candidate_status = "done" if has_candidate_pool else ("blocked" if market != "CN_ETF" else "waiting")
    signal_status = "blocked" if blocked else ("done" if has_today_signal else "waiting")
    paper_status = "blocked" if blocked else ("required" if has_manual_ticket else "waiting")
    ticket_status = "blocked" if blocked else ("required" if has_manual_ticket else ("waiting" if has_today_signal else "waiting"))
    journal_status = "blocked" if blocked else ("required" if has_manual_ticket else "waiting")
    small_capital_status = (
        "blocked"
        if blocked
        else "external_manual_candidate"
        if pre_live_manual_allowed
        else "waiting"
    )
    stages = [
        _daily_trade_system_stage(
            "candidate_pool",
            "候选池",
            candidate_status,
            "只从 CN_ETF 主线可运行候选里选，不从全市场历史榜硬挑前三。",
            f"market={market}; selected_factors={selected_factor_count}",
            "factor-leaderboard-table",
        ),
        _daily_trade_system_stage(
            "today_signal",
            "今日信号",
            signal_status,
            "前三因子必须生成当天 ETF 目标，旧信号或无目标都不能进入交易复核。",
            f"signals={signal_count}; targets={target_count}",
            "daily-trade-factor-table",
        ),
        _daily_trade_system_stage(
            "paper_simulation",
            "模拟盘复核",
            paper_status,
            "用同参数先跑本地模拟盘，看收益、回撤、成交和保护事件。",
            "paper_receipt_required=true",
            "paper-metrics",
            "paper_simulation",
        ),
        _daily_trade_system_stage(
            "manual_ticket_review",
            "人工票据复核",
            ticket_status,
            "只生成可复核票据，人工核对价格、现金、仓位和 100 份取整。",
            f"manual_tickets={ticket_count}",
            "daily-trade-decision-actions",
        ),
        _daily_trade_system_stage(
            "post_close_journal",
            "盘后复盘",
            journal_status,
            "记录是否执行、为什么跳过、滑点、回撤和次日要验证的问题。",
            "post_close_journal_required=true",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
        _daily_trade_system_stage(
            "small_capital_observation",
            "小资金人工观察",
            small_capital_status,
            "预实盘总闸门通过后，也只允许外部人工小资金观察；软件仍不能连接券商或下单。",
            f"pre_live_status={pre_live_status}; decision={pre_live_decision}",
            "control-pre-live-master-gate",
        ),
        _daily_trade_system_stage(
            "human_broker_execution",
            "人工券商端操作",
            "manual_locked",
            "软件不连接券商、不读取账户、不自动下单；真要操作只能由本人另行打开券商端人工决定。",
            "system_order_permission=false",
            "daily-manual-broker-handoff-ticket-table",
        ),
    ]
    progress = {
        "completed_stage_count": sum(1 for row in stages if row["status"] == "done"),
        "required_stage_count": sum(1 for row in stages if row["status"] == "required"),
        "blocked_stage_count": sum(1 for row in stages if row["status"] == "blocked"),
        "locked_stage_count": sum(1 for row in stages if row["status"].endswith("locked")),
        "stage_count": len(stages),
    }
    next_gate = _daily_trade_system_next_gate(stages)
    return {
        "stage": "daily_trade_system_state",
        "mode": mode,
        "mode_label": _daily_trade_system_mode_label(mode),
        "progress": progress,
        "next_gate": next_gate,
        "candidate_pool_policy": {
            "selection_scope": "CN_ETF",
            "top_factor_limit": 3,
            "eligible_pool_required": True,
            "direct_buy_from_leaderboard_allowed": False,
            "cn_stock_moneyflow_primary_allowed": False,
        },
        "permissions": {
            "paper_simulation_allowed": not blocked and has_manual_ticket,
            "manual_ticket_review_allowed": not blocked and has_manual_ticket,
            "small_capital_observation_allowed": pre_live_manual_allowed,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "pre_live_master_gate": {
            "status": pre_live_status,
            "decision": pre_live_decision,
            "manual_small_capital_observation_allowed": pre_live_manual_allowed,
            "external_manual_only": True,
            "target_id": "control-pre-live-master-gate",
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "stages": stages,
    }


def _daily_trade_system_stage(
    stage_id: str,
    label: str,
    status: str,
    plain_check: str,
    evidence: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "label": label,
        "status": status,
        "plain_check": plain_check,
        "evidence": evidence,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "automation_allowed": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _daily_trade_system_next_gate(stages: list[dict[str, Any]]) -> dict[str, Any]:
    for status in ("blocked", "required", "waiting", "manual_locked"):
        for row in stages:
            if row.get("status") == status:
                return {
                    "stage_id": row.get("stage_id"),
                    "label": row.get("label"),
                    "status": row.get("status"),
                    "target_id": row.get("target_id"),
                    "workflow_id": row.get("workflow_id"),
                }
    return {}


def _daily_trade_system_mode_label(mode: str) -> str:
    labels = {
        "blocked_fix_current_positions": "先修正持仓输入",
        "blocked_pretrade_red_light": "盘前红灯阻断",
        "manual_small_capital_observation_candidate": "外部人工小资金观察候选",
        "paper_rehearsal_required": "先模拟盘复核",
        "manual_ticket_required": "先生成可复核票据",
        "waiting_for_daily_signal": "等待今日信号",
    }
    return labels.get(mode, mode)


def _decision_sheet_action(index: int, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_number": index,
        "action_type": "manual_review_ticket",
        "ticket_id": row.get("ticket_id") or f"daily-ticket-{index:03d}",
        "asset_id": row.get("asset_id"),
        "market": row.get("market") or "CN_ETF",
        "side": row.get("side") or "review",
        "target_weight": row.get("target_weight"),
        "reference_price": row.get("reference_price") or row.get("latest_price"),
        "current_quantity": row.get("current_quantity"),
        "current_value": row.get("current_value"),
        "target_value": row.get("target_value"),
        "delta_value": row.get("delta_value"),
        "rounded_quantity": row.get("rounded_quantity"),
        "rounded_quantity_delta": row.get("rounded_quantity_delta", row.get("rounded_quantity")),
        "rounded_value": row.get("rounded_value"),
        "cash_delta_after_rounding": row.get("cash_delta_after_rounding"),
        "source_factors": row.get("source_factors"),
        "plain_instruction": row.get("manual_instruction")
        or row.get("copy_text")
        or "仅供人工复核，不是订单。券商端价格、现金和风险必须本人再次确认。",
        "manual_only": True,
        "executable": False,
        "live_order_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _decision_sheet_missing_evidence(
    decision: str,
    blockers: list[str],
    ticket_count: int,
    position_status: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def row(check_id: str, status: str, label: str, why: str, target_id: str, workflow_id: str = "") -> None:
        rows.append(
            {
                "check_id": check_id,
                "status": status,
                "label": label,
                "why": why,
                "target_id": target_id,
                "workflow_id": workflow_id,
                "required_before_manual_money": True,
                "automation_allowed": False,
                "order_placement_allowed": False,
            }
        )

    if position_status == "error":
        row(
            "current_positions_fixed",
            "missing",
            "修正当前持仓输入",
            "当前持仓里出现账户、券商、订单或格式风险，必须先删掉危险字段。",
            "daily-current-positions",
        )
        return rows
    if blockers:
        row(
            "pretrade_blockers_resolved",
            "missing",
            "清理盘前红灯",
            "红灯阻断项仍存在：" + ", ".join(blockers),
            "daily-pretrade-readiness-verdict",
        )
        return rows
    if ticket_count <= 0 or decision == "waiting_for_daily_signal":
        row(
            "daily_top3_signal_ready",
            "missing",
            "生成今日前三信号",
            "还没有完整的今日 CN_ETF 信号和人工复核票据。",
            "daily-trade-factor-table",
            "daily_trade_advisory",
        )
        return rows

    row(
        "paper_simulation_receipt",
        "missing",
        "同参数模拟盘回执",
        "必须先用同一组参数跑本地模拟盘，检查收益、回撤、成交和保护事件。",
        "paper-metrics",
        "paper_simulation",
    )
    row(
        "risk_cash_review",
        "missing",
        "人工风险和现金复核",
        "核对单 ETF 上限、总仓位、现金余量、价格偏差、流动性和可承受回撤。",
        "daily-pretrade-readiness-verdict",
    )
    row(
        "manual_broker_price_check",
        "missing",
        "券商端实时价格核对",
        "本地参考价不等于券商端实时价格，最终数量和金额必须由人重新确认。",
        "daily-manual-broker-handoff-ticket-table",
    )
    row(
        "post_close_journal_plan",
        "missing",
        "收盘后复盘计划",
        "今天无论执行或跳过，都要记录信号、模拟盘、人工判断和次日风险。",
        "beginner-post-close-journal-board",
    )
    return rows


def _decision_sheet_operator_script(decision: str, ticket_count: int) -> list[dict[str, Any]]:
    steps = [
        (
            "daily_top3_signal_review",
            "复核今日前三因子",
            "查看因子、参数、Sharpe、年化、最大回撤、胜率、RankIC 和信号日期。",
            "daily-trade-factor-table",
            "",
        ),
        (
            "paper_simulation_first",
            "先跑本地模拟盘",
            "用同参数跑模拟盘，再看收益、回撤、成交、保护事件，不能跳过。",
            "paper-metrics",
            "paper_simulation",
        ),
        (
            "manual_ticket_review",
            "核对人工票据",
            "逐项看 ETF、方向、参考价、目标金额、取整份额、现金差额和来源因子。",
            "daily-manual-broker-handoff-ticket-table",
            "",
        ),
        (
            "human_decision_only",
            "人决定是否在券商端操作",
            "软件只给复核材料，不连接券商、不读取账户、不自动下单。",
            "control-safety-boundary",
            "",
        ),
        (
            "post_close_journal",
            "收盘后复盘",
            "记录今天执行或跳过的原因，把真实演练反馈带回下一轮审计。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]
    status_by_step = {
        "daily_top3_signal_review": "ready" if decision != "waiting_for_daily_signal" else "waiting",
        "paper_simulation_first": "required" if ticket_count > 0 and not decision.startswith("blocked") else "waiting",
        "manual_ticket_review": "manual_only" if ticket_count > 0 and not decision.startswith("blocked") else "waiting",
        "human_decision_only": "manual_only" if ticket_count > 0 and not decision.startswith("blocked") else "locked",
        "post_close_journal": "required" if decision != "waiting_for_daily_signal" else "waiting",
    }
    return [
        {
            "step_number": index,
            "step_id": step_id,
            "title": title,
            "status": status_by_step.get(step_id, "waiting"),
            "plain_action": plain_action,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "automation_allowed": False,
            "live_order_allowed": False,
            "broker_connection_allowed": False,
            "order_placement_allowed": False,
        }
        for index, (step_id, title, plain_action, target_id, workflow_id) in enumerate(steps, start=1)
    ]


def _decision_sheet_trade_package_checklist(
    *,
    daily_top3: list[dict[str, Any]],
    signal_count: int,
    target_count: int,
    ticket_count: int,
    blockers: list[str],
    position_status: str,
    decision: str,
) -> dict[str, Any]:
    blocked = bool(blockers) or position_status == "error" or decision.startswith("blocked")
    has_top3 = len(daily_top3) > 0
    has_targets = signal_count > 0 and target_count > 0
    has_tickets = ticket_count > 0

    def row(
        step_id: str,
        label: str,
        status: str,
        evidence: str,
        gui_target: str,
        plain_action: str,
    ) -> dict[str, Any]:
        return {
            "step_id": step_id,
            "label": label,
            "status": status,
            "evidence": evidence,
            "gui_target": gui_target,
            "plain_action": plain_action,
            "order_placement_allowed": False,
        }

    items = [
        row(
            "top_factor_pool",
            "前三 CN_ETF 因子",
            "done" if has_top3 else "required",
            f"top3={len(daily_top3)}",
            "daily-trade-decision-top3",
            "先生成今日前三 CN_ETF 候选。",
        ),
        row(
            "today_signal_targets",
            "今日信号和目标仓位",
            "done" if has_targets else ("blocked" if blocked else "required"),
            f"signals={signal_count}; targets={target_count}",
            "daily-trade-target-table",
            "确认今日信号、ETF 目标权重和数据日期。",
        ),
        row(
            "pretrade_red_light",
            "盘前红灯",
            "blocked" if blocked else "done",
            "blockers=" + ",".join(blockers) if blockers else f"position_status={position_status}",
            "daily-pretrade-readiness-verdict",
            "先清掉数据新鲜度、持仓输入和风险红灯。",
        ),
        row(
            "manual_ticket_review",
            "人工复核票据",
            "done" if has_tickets and not blocked else ("blocked" if blocked else "required"),
            f"manual_tickets={ticket_count}",
            "daily-manual-broker-handoff-ticket-table",
            "核对买卖方向、参考价、数量、金额、现金和风险。",
        ),
        row(
            "paper_simulation_receipt",
            "同参数模拟盘回执",
            "required" if has_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "local_browser_receipt_required=True",
            "paper-metrics",
            "先跑同参数模拟盘，确认收益、回撤和保护事件。",
        ),
        row(
            "post_close_journal",
            "收盘后复盘回执",
            "required" if has_tickets and not blocked else ("blocked" if blocked else "waiting"),
            "local_browser_receipt_required=True",
            "beginner-post-close-journal-board",
            "收盘后记录执行、跳过、偏差和下一轮改进。",
        ),
        row(
            "manual_safety_boundary",
            "自动下单边界",
            "manual_locked",
            "broker_connection_allowed=False; order_placement_allowed=False",
            "control-safety-boundary",
            "系统只给人工复核材料，不连接券商、不读取账户、不自动下单。",
        ),
    ]
    next_item = next((item for item in items if item["status"] in {"blocked", "required"}), None)
    blocked_count = sum(1 for item in items if item["status"] == "blocked")
    required_count = sum(1 for item in items if item["status"] == "required")
    done_count = sum(1 for item in items if item["status"] == "done")
    status = "blocked" if blocked_count else ("needs_manual_evidence" if required_count else "ready_for_manual_review")
    return {
        "stage": "daily_trade_package_checklist",
        "summary": {
            "status": status,
            "done_step_count": done_count,
            "required_step_count": required_count,
            "blocked_step_count": blocked_count,
            "locked_step_count": sum(1 for item in items if item["status"] == "manual_locked"),
            "next_step_id": next_item["step_id"] if next_item else "manual_ticket_review",
            "next_gui_target": next_item["gui_target"] if next_item else "daily-manual-broker-handoff-ticket-table",
            "manual_only_boundary": True,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "items": items,
    }


def _decision_sheet_beginner_operation_recipe(
    *,
    decision: str,
    plain_answer: str,
    button_label: str,
    target_id: str,
    workflow_id: str,
    daily_top3: list[dict[str, Any]],
    today_actions: list[dict[str, Any]],
    missing_evidence: list[dict[str, Any]],
    trade_package_checklist: dict[str, Any],
    blockers: list[str],
    position_status: str,
) -> dict[str, Any]:
    blocked = bool(blockers) or position_status == "error" or decision.startswith("blocked")
    has_top3 = bool(daily_top3)
    has_tickets = bool(today_actions)
    package_summary = (
        trade_package_checklist.get("summary")
        if isinstance(trade_package_checklist.get("summary"), dict)
        else {}
    )
    first_missing = missing_evidence[0] if missing_evidence else {}
    if blocked:
        primary_next_step_id = "clear_red_light"
        next_workflow_id = str(first_missing.get("workflow_id") or workflow_id or "")
        next_target_id = str(first_missing.get("target_id") or target_id or "daily-pretrade-readiness-verdict")
        next_label = str(first_missing.get("label") or button_label or "先处理阻断项")
        mode = "blocked_do_not_trade"
    elif has_tickets:
        primary_next_step_id = "run_same_parameter_paper"
        next_workflow_id = "paper_simulation"
        next_target_id = "paper-metrics"
        next_label = "先跑同参数模拟盘"
        mode = "paper_first_then_manual_review"
    elif has_top3:
        primary_next_step_id = "build_manual_ticket_pack"
        next_workflow_id = workflow_id or "daily_trade_advisory"
        next_target_id = target_id or "daily-trade-target-table"
        next_label = button_label or "补齐人工复核票据"
        mode = "complete_today_signal_pack"
    else:
        primary_next_step_id = "generate_today_top3_signal"
        next_workflow_id = workflow_id or "daily_trade_advisory"
        next_target_id = target_id or "run-daily-trade-advisory"
        next_label = button_label or "生成今日前三建议"
        mode = "waiting_for_today_top3"

    def step(
        step_number: int,
        step_id: str,
        label: str,
        status: str,
        plain_action: str,
        target: str,
        workflow: str = "",
    ) -> dict[str, Any]:
        return {
            "step_number": step_number,
            "step_id": step_id,
            "label": label,
            "status": status,
            "plain_action": plain_action,
            "target_id": target,
            "workflow_id": workflow,
            "manual_required": True,
            "automation_allowed": False,
            "copy_to_broker_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }

    steps = [
        step(
            1,
            "review_top3_signal",
            "看今日前三因子",
            "done" if has_top3 else ("blocked" if blocked else "required"),
            "先确认前三候选来自 CN_ETF 主线，并查看 Sharpe、年化、回撤、胜率、RankIC 和参数；这一步不是买入指令。",
            "daily-trade-decision-top3",
            "daily_trade_advisory" if not has_top3 and not blocked else "",
        ),
        step(
            2,
            "review_today_etf_targets",
            "看今日 ETF 目标",
            "done" if has_tickets else ("blocked" if blocked else "required"),
            "确认今天对应的 ETF、目标权重、参考价和数量；没有同日目标时不要进入人工复核。",
            "daily-trade-target-table",
            "daily_trade_advisory" if has_top3 and not has_tickets and not blocked else "",
        ),
        step(
            3,
            "run_same_parameter_paper",
            "先跑同参数模拟盘",
            "blocked" if blocked else ("required" if has_tickets else "waiting"),
            "用同一组因子、TopN、成本、风控参数先跑本地模拟盘，看收益、回撤、成交和保护事件。",
            "paper-metrics",
            "paper_simulation" if has_tickets and not blocked else "",
        ),
        step(
            4,
            "check_price_capacity_risk",
            "检查价格、容量和风险",
            "blocked" if blocked else ("required" if has_tickets else "waiting"),
            "逐项核对券商实时价是否在价格护栏内、参与率是否超容量、现金和最大回撤是否能承受。",
            "daily-pre-execution-guard",
        ),
        step(
            5,
            "manual_broker_review_if_human_chooses",
            "人工决定是否打开券商",
            "manual_locked",
            "软件不会连接券商、不会读取账户、不会自动下单；如果继续，只能由本人在券商端重新核对后手动决定。",
            "daily-manual-broker-handoff-ticket-table",
        ),
        step(
            6,
            "write_post_close_journal",
            "收盘后写复盘",
            "blocked" if blocked else ("required" if has_tickets else "waiting"),
            "记录执行或跳过原因、模拟盘结果、滑点、未成交、风险事件和下一日要复核的问题。",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_tickets and not blocked else "",
        ),
    ]

    skip_rules = [
        _beginner_operation_skip_rule(
            "direct_top3_buy_forbidden",
            "always_block",
            "不能看到前三因子就直接买，必须先有同日 ETF 信号、模拟盘、风险和人工复核。",
            "daily-trade-decision-top3",
        ),
        _beginner_operation_skip_rule(
            "stale_signal_date",
            "skip_if_seen",
            "信号日期不是今天或最新交易日时，跳过人工复核，先刷新数据并重新生成信号。",
            "daily-pre-execution-guard",
            "daily_trade_advisory",
        ),
        _beginner_operation_skip_rule(
            "broker_price_outside_guardrail",
            "skip_if_seen",
            "券商实时价超出价格护栏时，今天跳过该 ETF，不追价。",
            "daily-pre-execution-guard",
        ),
        _beginner_operation_skip_rule(
            "liquidity_capacity_breached",
            "skip_if_seen",
            "流动性证据缺失或参与率超限时，跳过或降低金额，只保留纸面演练。",
            "daily-pre-execution-guard",
        ),
        _beginner_operation_skip_rule(
            "risk_circuit_breaker",
            "skip_if_seen",
            "触发日亏损、连续亏损、冷静期或回撤阈值时，只能纸面观察，不能进入券商复核。",
            "daily-pre-execution-guard",
        ),
        _beginner_operation_skip_rule(
            "paper_receipt_missing",
            "skip_if_seen",
            "同参数模拟盘没有回执时，不进入人工券商复核。",
            "paper-metrics",
            "paper_simulation",
        ),
    ]

    ticket_preview = [
        {
            "ticket_id": row.get("ticket_id"),
            "asset_id": row.get("asset_id"),
            "market": row.get("market") or "CN_ETF",
            "side": row.get("side") or "review",
            "target_weight": _float_or_none(row.get("target_weight")),
            "reference_price": _float_or_none(row.get("reference_price")),
            "rounded_quantity": _int(row.get("rounded_quantity"), 0),
            "rounded_quantity_delta": _int(row.get("rounded_quantity_delta"), _int(row.get("rounded_quantity"), 0)),
            "plain_instruction": row.get("plain_instruction") or "只供人工复核，不是订单。",
            "copy_to_broker_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
        for row in today_actions[:5]
    ]
    operator_inputs = _beginner_operation_operator_inputs(
        position_status=position_status,
        has_tickets=has_tickets,
        blocked=blocked,
    )
    return {
        "stage": "daily_beginner_operation_recipe",
        "summary": {
            "decision": decision,
            "mode": mode,
            "plain_answer": plain_answer,
            "primary_next_step_id": primary_next_step_id,
            "next_label": next_label,
            "next_workflow_id": next_workflow_id,
            "next_target_id": next_target_id,
            "top3_count": len(daily_top3),
            "ticket_preview_count": len(ticket_preview),
            "missing_evidence_count": len(missing_evidence),
            "operator_input_count": len(operator_inputs),
            "operator_input_ready_count": _count_status(operator_inputs, "ready"),
            "operator_input_manual_count": _count_status(operator_inputs, "manual_required"),
            "operator_input_missing_count": _count_status(operator_inputs, "missing"),
            "package_status": package_summary.get("status"),
            "direct_buy_allowed": False,
            "manual_only_boundary": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "steps": steps,
        "skip_rules": skip_rules,
        "operator_inputs_required": operator_inputs,
        "ticket_preview": ticket_preview,
        "missing_evidence": missing_evidence,
    }


def _count_status(rows: list[dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if row.get("status") == status)


def _beginner_operation_operator_inputs(
    *,
    position_status: str,
    has_tickets: bool,
    blocked: bool,
) -> list[dict[str, Any]]:
    manual_status = "blocked" if blocked else ("manual_required" if has_tickets else "waiting")
    receipt_status = "blocked" if blocked else ("missing" if has_tickets else "waiting")
    position_input_status = "blocked" if position_status == "error" else (
        "missing" if position_status == "not_provided" else "ready"
    )
    rows = [
        (
            "broker_realtime_price",
            manual_status,
            "human_from_broker_app",
            "券商实时价格",
            "在券商软件里人工查看 ETF 实时价格，并确认没有超出价格护栏；系统不会连接券商读取价格。",
            "daily-pre-execution-guard",
            "",
        ),
        (
            "available_cash",
            manual_status,
            "human_from_broker_app",
            "可用现金",
            "人工确认券商端可用现金是否覆盖票据金额和滑点；不要把账户号或券商账号粘贴进系统。",
            "daily-manual-broker-handoff-ticket-table",
            "",
        ),
        (
            "current_positions_safe_csv",
            position_input_status,
            "human_sanitized_input",
            "当前持仓安全表",
            "只填写 asset_id, quantity, latest_price 等脱敏字段；禁止粘贴账户、券商、委托号或成交号。",
            "daily-current-positions",
            "",
        ),
        (
            "same_parameter_paper_receipt",
            receipt_status,
            "local_paper_simulation",
            "同参数模拟盘回执",
            "先用完全相同的因子、TopN、成本、调仓和风控参数跑本地模拟盘，再看回撤、成交和保护事件。",
            "paper-metrics",
            "paper_simulation",
        ),
        (
            "post_close_journal",
            receipt_status,
            "local_operator_journal",
            "收盘后复盘",
            "无论执行或跳过，都记录原因、模拟盘表现、滑点、未成交和下一日要复核的问题。",
            "beginner-post-close-journal-board",
            "post_close_journal",
        ),
    ]
    return [
        {
            "input_id": input_id,
            "status": status,
            "source": source,
            "label": label,
            "plain_instruction": plain_instruction,
            "target_id": target_id,
            "workflow_id": workflow_id,
            "required_before_manual_review": True,
            "manual_required": True,
            "sensitive_account_fields_allowed": False,
            "copy_to_broker_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        }
        for input_id, status, source, label, plain_instruction, target_id, workflow_id in rows
    ]


def _beginner_operation_skip_rule(
    rule_id: str,
    status: str,
    plain_rule: str,
    target_id: str,
    workflow_id: str = "",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "status": status,
        "plain_rule": plain_rule,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "manual_required": True,
        "copy_to_broker_allowed": False,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def build_manual_ticket_export(pack: dict[str, Any]) -> dict[str, Any]:
    handoff = pack.get("manual_broker_handoff") if isinstance(pack.get("manual_broker_handoff"), dict) else _build_manual_broker_handoff(pack)
    tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    run_date = str(pack.get("run_date") or handoff.get("run_date") or date.today().isoformat())
    export_status = str(handoff.get("status") or ("review_only" if tickets else "waiting_for_tickets"))
    columns = [
        "step_number",
        "ticket_id",
        "asset_id",
        "market",
        "side",
        "target_weight",
        "reference_price",
        "current_quantity",
        "current_value",
        "target_value",
        "delta_value",
        "rounded_quantity",
        "rounded_quantity_delta",
        "rounded_value",
        "cash_delta_after_rounding",
        "estimated_commission_bps",
        "estimated_commission_cost",
        "estimated_buy_cash_required",
        "estimated_sell_cash_released",
        "estimated_cash_impact_after_costs",
        "lower_price_bound",
        "upper_price_bound",
        "max_reference_price_deviation_pct",
        "max_slippage_bps",
        "max_estimated_slippage_cost",
        "source_factors",
        "review_status",
        "review_only",
        "paper_simulation_required",
        "manual_price_guardrail_note",
        "manual_check_note",
    ]
    rows = [_manual_ticket_export_row(ticket) for ticket in tickets]
    csv_text = _manual_ticket_export_csv(columns, rows)
    markdown_text = _manual_ticket_export_markdown(run_date, export_status, rows)
    return _sanitize(
        {
            "stage": MANUAL_TICKET_EXPORT_STAGE,
            "run_date": run_date,
            "summary": {
                "export_status": export_status,
                "ticket_count": len(rows),
                "download_filename": f"daily_manual_ticket_export_{run_date}.csv",
                "manual_review_required": True,
                "review_only": True,
                "paper_simulation_required": True,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "columns": columns,
            "rows": rows,
            "csv_text": csv_text,
            "markdown_text": markdown_text,
            "safety": SAFETY_NOTICE,
        }
    )


def _manual_ticket_export_row(ticket: dict[str, Any]) -> dict[str, Any]:
    source_factors = ticket.get("source_factors")
    guardrails = (
        ticket.get("execution_guardrails")
        if isinstance(ticket.get("execution_guardrails"), dict)
        else _manual_ticket_execution_guardrails(ticket)
    )
    if isinstance(source_factors, list):
        factor_text = "|".join(str(item) for item in source_factors)
    elif source_factors is None:
        factor_text = ""
    else:
        factor_text = str(source_factors)
    return {
        "step_number": _int(ticket.get("step_number"), 0),
        "ticket_id": str(ticket.get("ticket_id") or ""),
        "asset_id": str(ticket.get("asset_id") or ""),
        "market": str(ticket.get("market") or "CN_ETF"),
        "side": str(ticket.get("side") or "review"),
        "target_weight": _float_or_none(ticket.get("target_weight")),
        "reference_price": _float_or_none(ticket.get("reference_price")),
        "current_quantity": _float_or_none(ticket.get("current_quantity")),
        "current_value": _float_or_none(ticket.get("current_value")),
        "target_value": _float_or_none(ticket.get("target_value")),
        "delta_value": _float_or_none(ticket.get("delta_value")),
        "rounded_quantity": _int(ticket.get("rounded_quantity"), 0),
        "rounded_quantity_delta": _int(ticket.get("rounded_quantity_delta"), 0),
        "rounded_value": _float_or_none(ticket.get("rounded_value")),
        "cash_delta_after_rounding": _float_or_none(ticket.get("cash_delta_after_rounding")),
        "estimated_commission_bps": _float_or_none(ticket.get("estimated_commission_bps")),
        "estimated_commission_cost": _float_or_none(ticket.get("estimated_commission_cost")),
        "estimated_buy_cash_required": _float_or_none(ticket.get("estimated_buy_cash_required")),
        "estimated_sell_cash_released": _float_or_none(ticket.get("estimated_sell_cash_released")),
        "estimated_cash_impact_after_costs": _float_or_none(ticket.get("estimated_cash_impact_after_costs")),
        "lower_price_bound": _float_or_none(guardrails.get("lower_price_bound")),
        "upper_price_bound": _float_or_none(guardrails.get("upper_price_bound")),
        "max_reference_price_deviation_pct": _float_or_none(guardrails.get("max_reference_price_deviation_pct")),
        "max_slippage_bps": _int(guardrails.get("max_slippage_bps"), 0),
        "max_estimated_slippage_cost": _float_or_none(guardrails.get("max_estimated_slippage_cost")),
        "source_factors": factor_text,
        "review_status": "manual_review_only",
        "review_only": True,
        "paper_simulation_required": True,
        "manual_price_guardrail_note": str(guardrails.get("plain_rule") or ""),
        "manual_check_note": "仅供人工复核；先核对模拟盘、实时价格、现金、仓位上限和风险，再由人决定是否操作。",
    }


def _manual_ticket_export_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue()


def _manual_ticket_export_markdown(run_date: str, export_status: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        "# 今日人工复核票据",
        "",
        f"- 日期: {run_date}",
        f"- 状态: {export_status}",
        "- 边界: 仅供人工复核；系统不连接券商、不读取账户、不自动下单。",
        "",
    ]
    if not rows:
        lines.append("暂无可导出的人工复核票据。")
        return "\n".join(lines)
    for row in rows:
        lines.append(
            f"- {row.get('asset_id', '')}: {row.get('side', '')}, "
            f"数量 {row.get('rounded_quantity', 0)}, "
            f"参考金额 {row.get('rounded_value', '')}, "
            f"权重 {row.get('target_weight', '')}; manual_review_only"
        )
    return "\n".join(lines)


def build_manual_execution_audit(
    pack: dict[str, Any],
    execution_reviews: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    handoff = (
        pack.get("manual_broker_handoff")
        if isinstance(pack.get("manual_broker_handoff"), dict)
        else _build_manual_broker_handoff(pack)
    )
    tickets = [row for row in handoff.get("copyable_tickets", []) if isinstance(row, dict)]
    reviews = [row for row in (execution_reviews or []) if isinstance(row, dict)]
    reviews_by_key: dict[str, dict[str, Any]] = {}
    for review in reviews:
        ticket_id = str(review.get("ticket_id") or "").strip()
        asset_id = str(review.get("asset_id") or "").strip()
        if ticket_id:
            reviews_by_key[f"ticket:{ticket_id}"] = review
        if asset_id:
            reviews_by_key.setdefault(f"asset:{asset_id}", review)
    rows = [_manual_execution_audit_row(index, ticket, reviews_by_key) for index, ticket in enumerate(tickets, 1)]
    guardrail_breach_count = sum(1 for row in rows if "broker_price_outside_guardrail" in row.get("breach_reasons", []))
    slippage_breach_count = sum(1 for row in rows if "slippage_limit_breached" in row.get("breach_reasons", []))
    quantity_mismatch_count = sum(1 for row in rows if "quantity_mismatch" in row.get("breach_reasons", []))
    broker_recheck_session_missing_count = sum(
        1 for row in rows if "broker_recheck_session_missing" in row.get("breach_reasons", [])
    )
    broker_recheck_session_blocked_count = sum(
        1 for row in rows if "broker_recheck_session_not_ok" in row.get("breach_reasons", [])
    )
    small_capital_budget_breach_count = sum(
        1 for row in rows if "small_capital_budget_breached" in row.get("breach_reasons", [])
    )
    sensitive_field_count = sum(1 for row in rows if "sensitive_field_removed" in row.get("breach_reasons", []))
    missing_review_count = sum(1 for row in rows if row.get("review_status") == "missing_review")
    blocked_count = sum(1 for row in rows if row.get("review_status") == "blocked")
    executed_count = sum(1 for row in rows if row.get("manual_outcome") == "manual_trade_by_human")
    skipped_count = sum(
        1
        for row in rows
        if row.get("manual_outcome")
        in {"skipped_no_trade", "paper_only", "manual_review_no_trade", "blocked_by_risk"}
    )
    executed_notional = sum(_float(row.get("executed_notional"), 0.0) for row in rows)
    reference_notional = sum(_float(row.get("reference_notional"), 0.0) for row in rows)
    total_adverse_slippage_cost = sum(_float(row.get("adverse_slippage_cost"), 0.0) for row in rows)
    estimated_commission_cost = sum(_float(row.get("estimated_commission_cost"), 0.0) for row in rows)
    estimated_total_execution_cost = total_adverse_slippage_cost + estimated_commission_cost
    execution_cost_bps = (
        round(total_adverse_slippage_cost / reference_notional * 10000.0, 6)
        if reference_notional > 0
        else None
    )
    estimated_total_execution_cost_bps = (
        round(estimated_total_execution_cost / reference_notional * 10000.0, 6)
        if reference_notional > 0
        else None
    )
    if not rows:
        decision = "waiting_for_manual_tickets"
    elif (
        blocked_count
        or guardrail_breach_count
        or slippage_breach_count
        or small_capital_budget_breach_count
        or sensitive_field_count
    ):
        decision = "guardrail_breach_review_required"
    elif missing_review_count:
        decision = "manual_execution_review_incomplete"
    else:
        decision = "manual_execution_evidence_ready"
    return _sanitize(
        {
            "stage": MANUAL_EXECUTION_AUDIT_STAGE,
            "run_date": str(pack.get("run_date") or handoff.get("run_date") or date.today().isoformat()),
            "summary": {
                "decision": decision,
                "ticket_count": len(rows),
                "review_count": len(reviews),
                "executed_count": executed_count,
                "skipped_count": skipped_count,
                "guardrail_breach_count": guardrail_breach_count,
                "slippage_breach_count": slippage_breach_count,
                "quantity_mismatch_count": quantity_mismatch_count,
                "broker_recheck_session_missing_count": broker_recheck_session_missing_count,
                "broker_recheck_session_blocked_count": broker_recheck_session_blocked_count,
                "small_capital_budget_breach_count": small_capital_budget_breach_count,
                "small_capital_ticket_limit": SMALL_CAPITAL_OBSERVATION_MAX_SINGLE_TICKET_NOTIONAL,
                "sensitive_field_count": sensitive_field_count,
                "missing_review_count": missing_review_count,
                "blocked_count": blocked_count,
                "executed_notional": round(executed_notional, 6),
                "reference_notional": round(reference_notional, 6),
                "total_adverse_slippage_cost": round(total_adverse_slippage_cost, 6),
                "execution_cost_bps": execution_cost_bps,
                "estimated_commission_bps": MANUAL_ESTIMATED_COMMISSION_BPS,
                "estimated_commission_cost": round(estimated_commission_cost, 6),
                "estimated_total_execution_cost": round(estimated_total_execution_cost, 6),
                "estimated_total_execution_cost_bps": estimated_total_execution_cost_bps,
                "manual_execution_cost_impact": (
                    "measured_from_manual_fills"
                    if reference_notional > 0
                    else "waiting_for_manual_fill_details"
                ),
                "manual_review_required": True,
                "manual_execution_only": True,
                "live_trading_allowed": False,
                "broker_connection_allowed": False,
                "account_read_allowed": False,
                "order_placement_allowed": False,
                "auto_order_allowed": False,
            },
            "columns": [
                "ticket_id",
                "asset_id",
                "side",
                "manual_outcome",
                "reference_price",
                "actual_fill_price",
                "fill_quantity",
                "planned_quantity",
                "adverse_slippage_bps",
                "adverse_slippage_cost",
                "estimated_commission_bps",
                "estimated_commission_cost",
                "estimated_total_execution_cost",
                "executed_notional",
                "reference_notional",
                "price_within_guardrail",
                "slippage_within_limit",
                "slippage_cost_within_budget",
                "quantity_matches_ticket",
                "quantity_plan_basis",
                "small_capital_max_quantity_at_reference",
                "small_capital_quantity_match_allowed",
                "broker_price_recheck_session_decision",
                "broker_recheck_session_ok",
                "small_capital_max_single_ticket_notional",
                "small_capital_excess_notional",
                "small_capital_limit_breached",
                "review_status",
                "breach_reasons",
                "execute_or_skip_reason",
            ],
            "rows": rows,
            "safety": SAFETY_NOTICE,
        }
    )


def _manual_execution_audit_row(
    index: int,
    ticket: dict[str, Any],
    reviews_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ticket_id = str(ticket.get("ticket_id") or f"daily-top3-{index:03d}")
    asset_id = str(ticket.get("asset_id") or "")
    review = reviews_by_key.get(f"ticket:{ticket_id}") or reviews_by_key.get(f"asset:{asset_id}") or {}
    has_review = bool(review)
    sensitive_fields = sorted(FORBIDDEN_REAL_ACCOUNT_COLUMNS & set(review))
    guardrails = (
        ticket.get("execution_guardrails")
        if isinstance(ticket.get("execution_guardrails"), dict)
        else _manual_ticket_execution_guardrails(ticket)
    )
    side = str(ticket.get("side") or "buy_or_adjust")
    manual_outcome = str(review.get("manual_outcome") or ("missing_review" if not has_review else "skipped_no_trade"))
    broker_recheck_session_decision = str(
        review.get("broker_price_recheck_session_decision")
        or review.get("broker_recheck_session_decision")
        or ""
    ).strip()
    reference_price = _float_or_none(
        guardrails.get("reference_price") or ticket.get("reference_price") or ticket.get("latest_price")
    )
    actual_fill_price = _float_or_none(review.get("actual_fill_price") or review.get("fill_price"))
    fill_quantity_value = _float_or_none(review.get("fill_quantity") or review.get("quantity"))
    fill_quantity = int(fill_quantity_value) if fill_quantity_value is not None else None
    rounded_delta = _int(ticket.get("rounded_quantity_delta"), 0)
    rounded_quantity = _int(ticket.get("rounded_quantity"), 0)
    planned_quantity = abs(rounded_delta) if rounded_delta else abs(rounded_quantity)
    lower_bound = _float_or_none(guardrails.get("lower_price_bound"))
    upper_bound = _float_or_none(guardrails.get("upper_price_bound"))
    max_slippage_bps = _float(guardrails.get("max_slippage_bps"), float(MANUAL_MAX_SLIPPAGE_BPS))
    max_estimated_slippage_cost = _float_or_none(guardrails.get("max_estimated_slippage_cost"))
    breach_reasons: list[str] = []
    if sensitive_fields:
        breach_reasons.append("sensitive_field_removed")
    price_within_guardrail = None
    adverse_slippage_bps = None
    adverse_slippage_cost = None
    estimated_commission_cost = None
    estimated_total_execution_cost = None
    executed_notional = None
    reference_notional = None
    small_capital_limit = SMALL_CAPITAL_OBSERVATION_MAX_SINGLE_TICKET_NOTIONAL
    board_lot = max(1, _int(ticket.get("board_lot_size"), BOARD_LOT_SIZE))
    small_capital_max_quantity_at_reference = (
        int(math.floor(small_capital_limit / reference_price / board_lot) * board_lot)
        if reference_price is not None and reference_price > 0
        else 0
    )
    small_capital_limit_breached = False
    small_capital_excess_notional = 0.0
    small_capital_quantity_match_allowed = False
    quantity_plan_basis = "ticket_planned_quantity"
    standard_quantity_matches = None
    slippage_within_limit = None
    slippage_cost_within_budget = None
    quantity_matches_ticket = None
    if manual_outcome == "manual_trade_by_human":
        if not broker_recheck_session_decision:
            breach_reasons.append("broker_recheck_session_missing")
        elif broker_recheck_session_decision != "manual_review_all_rows_price_cash_ok":
            breach_reasons.append("broker_recheck_session_not_ok")
        if actual_fill_price is None or fill_quantity is None or fill_quantity <= 0:
            breach_reasons.append("missing_fill_detail")
        if actual_fill_price is not None and lower_bound is not None and upper_bound is not None:
            price_within_guardrail = lower_bound <= actual_fill_price <= upper_bound
            if not price_within_guardrail:
                breach_reasons.append("broker_price_outside_guardrail")
        if actual_fill_price is not None and reference_price is not None and reference_price > 0:
            if side.lower().startswith("sell"):
                adverse_slippage_bps = round((reference_price - actual_fill_price) / reference_price * 10000, 6)
            else:
                adverse_slippage_bps = round((actual_fill_price - reference_price) / reference_price * 10000, 6)
            slippage_within_limit = adverse_slippage_bps <= max_slippage_bps
            if not slippage_within_limit:
                breach_reasons.append("slippage_limit_breached")
        if fill_quantity is not None:
            standard_quantity_matches = planned_quantity <= 0 or abs(fill_quantity) == planned_quantity
            quantity_matches_ticket = standard_quantity_matches
        if (
            actual_fill_price is not None
            and reference_price is not None
            and fill_quantity is not None
            and fill_quantity > 0
        ):
            quantity = abs(fill_quantity)
            executed_notional = round(abs(actual_fill_price * quantity), 6)
            reference_notional = round(abs(reference_price * quantity), 6)
            small_capital_limit_breached = executed_notional > small_capital_limit + 1e-9
            if small_capital_limit_breached:
                small_capital_excess_notional = round(executed_notional - small_capital_limit, 6)
                breach_reasons.append("small_capital_budget_breached")
            if (
                standard_quantity_matches is False
                and not side.lower().startswith("sell")
                and small_capital_max_quantity_at_reference > 0
                and abs(fill_quantity) <= small_capital_max_quantity_at_reference
                and not small_capital_limit_breached
            ):
                small_capital_quantity_match_allowed = True
                quantity_matches_ticket = True
                quantity_plan_basis = "small_capital_manual_observation_budget"
            if side.lower().startswith("sell"):
                adverse_slippage_cost = round((reference_price - actual_fill_price) * quantity, 6)
            else:
                adverse_slippage_cost = round((actual_fill_price - reference_price) * quantity, 6)
            estimated_commission_cost = round(executed_notional * MANUAL_ESTIMATED_COMMISSION_BPS / 10000.0, 6)
            estimated_total_execution_cost = round(adverse_slippage_cost + estimated_commission_cost, 6)
            if max_estimated_slippage_cost is not None:
                slippage_cost_within_budget = adverse_slippage_cost <= max_estimated_slippage_cost
                if not slippage_cost_within_budget and "slippage_limit_breached" not in breach_reasons:
                    breach_reasons.append("slippage_cost_budget_breached")
        if standard_quantity_matches is False and not small_capital_quantity_match_allowed:
            breach_reasons.append("quantity_mismatch")
    if not has_review:
        review_status = "missing_review"
    elif breach_reasons:
        review_status = "blocked"
    elif manual_outcome == "manual_trade_by_human":
        review_status = "passed"
    else:
        review_status = "skipped"
    return {
        "step_number": index,
        "ticket_id": ticket_id,
        "asset_id": asset_id,
        "side": side,
        "manual_outcome": manual_outcome,
        "reference_price": reference_price,
        "actual_fill_price": actual_fill_price,
        "fill_quantity": fill_quantity,
        "planned_quantity": planned_quantity,
        "adverse_slippage_bps": adverse_slippage_bps,
        "adverse_slippage_cost": adverse_slippage_cost,
        "estimated_commission_bps": MANUAL_ESTIMATED_COMMISSION_BPS,
        "estimated_commission_cost": estimated_commission_cost,
        "estimated_total_execution_cost": estimated_total_execution_cost,
        "executed_notional": executed_notional,
        "reference_notional": reference_notional,
        "price_within_guardrail": price_within_guardrail,
        "slippage_within_limit": slippage_within_limit,
        "slippage_cost_within_budget": slippage_cost_within_budget,
        "quantity_matches_ticket": quantity_matches_ticket,
        "quantity_plan_basis": quantity_plan_basis,
        "small_capital_max_quantity_at_reference": small_capital_max_quantity_at_reference,
        "small_capital_quantity_match_allowed": small_capital_quantity_match_allowed,
        "broker_price_recheck_session_decision": broker_recheck_session_decision or None,
        "broker_recheck_session_ok": broker_recheck_session_decision == "manual_review_all_rows_price_cash_ok",
        "small_capital_max_single_ticket_notional": small_capital_limit,
        "small_capital_excess_notional": small_capital_excess_notional,
        "small_capital_limit_breached": small_capital_limit_breached,
        "lower_price_bound": lower_bound,
        "upper_price_bound": upper_bound,
        "max_slippage_bps": max_slippage_bps,
        "max_estimated_slippage_cost": max_estimated_slippage_cost,
        "review_status": review_status,
        "breach_reasons": breach_reasons,
        "execute_or_skip_reason": _manual_execution_safe_text(review.get("execute_or_skip_reason") or ""),
        "sensitive_fields_removed": sensitive_fields,
        "review_only": True,
        "manual_execution_only": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _manual_execution_safe_text(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = " ".join(text.split())[:300]
    for token in sorted(FORBIDDEN_REAL_ACCOUNT_COLUMNS):
        text = text.replace(str(token), "[removed_sensitive_field]")
    return text


def write_daily_trade_advisory_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_trade_advisory_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_path / "daily_trade_advisory_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("combined_targets", [])).to_csv(output_path / "daily_trade_advisory_targets.csv", index=False)
    pd.DataFrame(pack.get("manual_trade_plan", [])).to_csv(output_path / "daily_trade_advisory_manual_plan.csv", index=False)
    export = pack.get("manual_ticket_export") if isinstance(pack.get("manual_ticket_export"), dict) else build_manual_ticket_export(pack)
    (output_path / "daily_manual_ticket_export.csv").write_text(str(export.get("csv_text", "")), encoding="utf-8")
    (output_path / "daily_manual_ticket_export.md").write_text(str(export.get("markdown_text", "")), encoding="utf-8")



def render_daily_trade_advisory_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# 今日前三因子手工交易建议",
        "",
        f"- 阶段: {pack.get('stage', STAGE)}",
        f"- 运行日期: {pack.get('run_date', '')}",
        f"- 入选因子: {summary.get('selected_factor_count', 0)}",
        f"- 可用信号: {summary.get('signal_count', 0)}",
        f"- 允许实盘自动化: {summary.get('live_trading_allowed', False)}",
        f"- 允许自动下单: {summary.get('order_placement_allowed', False)}",
        f"- 安全边界: {pack.get('safety', SAFETY_NOTICE)}",
        "",
        "## 入选因子",
        "",
    ]
    for row in pack.get("factors", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- #{row.get('rank', '')} {row.get('factor_name', '')} / {row.get('case_id', '')} "
            f"Sharpe={row.get('sharpe', '')} MaxDD={row.get('max_drawdown', '')}"
        )
    lines.extend(["", "## 手工计划", ""])
    plan = pack.get("manual_trade_plan", [])
    if plan:
        for row in plan:
            if isinstance(row, dict):
                lines.append(f"- {row.get('side', 'hold')} {row.get('asset_id', '')}: target_weight={row.get('target_weight', 0)}")
    else:
        lines.append("- 无手工工单")
    daybook = pack.get("daily_rehearsal_daybook") if isinstance(pack.get("daily_rehearsal_daybook"), dict) else {}
    phases = [row for row in daybook.get("phases", []) if isinstance(row, dict)]
    if phases:
        lines.extend(["", "## 每日交易演练", ""])
        for phase in phases:
            lines.append(
                f"- {phase.get('phase_number', '')}. {phase.get('title', '')}: "
                f"{phase.get('status', '')} / {phase.get('plain_action', '')}"
            )
    journal = pack.get("post_close_journal_template") if isinstance(pack.get("post_close_journal_template"), dict) else {}
    journal_items = [row for row in journal.get("items", []) if isinstance(row, dict)]
    if journal_items:
        lines.extend(["", "## 收盘后复盘", ""])
        for item in journal_items:
            lines.append(f"- {item.get('title', '')}: {item.get('prompt', '')}")
    live_plan = pack.get("live_transition_plan") if isinstance(pack.get("live_transition_plan"), dict) else {}
    live_summary = live_plan.get("summary") if isinstance(live_plan.get("summary"), dict) else {}
    live_loop = [row for row in live_plan.get("operating_loop", []) if isinstance(row, dict)]
    if live_plan:
        lines.extend(["", "## 实盘落地路径", ""])
        lines.append(f"- 状态: {live_summary.get('status', '')}")
        lines.append(f"- 今日信号: {live_summary.get('today_signal_count', 0)}")
        lines.append(f"- 自动下单: {live_summary.get('order_placement_allowed', False)}")
        for step in live_loop:
            lines.append(f"- {step.get('step_number', '')}. {step.get('title', '')}: {step.get('status', '')}")
    real_world_gate = (
        pack.get("real_world_manual_handoff_gate")
        if isinstance(pack.get("real_world_manual_handoff_gate"), dict)
        else {}
    )
    real_world_summary = (
        real_world_gate.get("summary")
        if isinstance(real_world_gate.get("summary"), dict)
        else {}
    )
    real_world_runbook = [row for row in real_world_gate.get("manual_operation_runbook", []) if isinstance(row, dict)]
    if real_world_gate:
        lines.extend(["", "## 实盘前人工观察总闸门", ""])
        lines.append(f"- 结论: {real_world_summary.get('decision', '')}")
        lines.append(f"- 下一步: {real_world_summary.get('next_label', '')}")
        lines.append(f"- 排行榜直买: {real_world_summary.get('direct_buy_from_top3_allowed', False)}")
        lines.append(f"- 券商连接: {real_world_summary.get('broker_connection_allowed', False)}")
        for step in real_world_runbook:
            lines.append(f"- {step.get('step_number', '')}. {step.get('label', '')}: {step.get('status', '')}")
    return "\n".join(lines) + "\n"


def _leaderboard_rows(leaderboard: dict[str, Any]) -> list[dict[str, Any]]:
    boards = leaderboard.get("leaderboards") if isinstance(leaderboard.get("leaderboards"), dict) else {}
    primary = boards.get("primary_cn_etf") if isinstance(boards.get("primary_cn_etf"), dict) else {}
    rows = primary.get("rows") if isinstance(primary.get("rows"), list) else None
    if rows is not None:
        return [row for row in rows if isinstance(row, dict)]
    top20 = leaderboard.get("top20") if isinstance(leaderboard.get("top20"), list) else []
    return [row for row in top20 if isinstance(row, dict)]


def _matching_signal(candidate: dict[str, Any], signal_snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    factor_name = str(candidate.get("factor_name") or "")
    case_id = str(candidate.get("case_id") or "")
    for signal in signal_snapshots:
        if not isinstance(signal, dict):
            continue
        request = signal.get("request") if isinstance(signal.get("request"), dict) else {}
        signal_factor = str(signal.get("factor_name") or request.get("factor_name") or request.get("factor") or "")
        signal_case = str(signal.get("case_id") or "")
        if signal_case and signal_case == case_id:
            return signal
        if signal_factor and signal_factor == factor_name:
            return signal
    return None


def _signal_card(candidate: dict[str, Any], signal: dict[str, Any] | None) -> dict[str, Any]:
    if not signal:
        return {
            "case_id": candidate.get("case_id"),
            "factor_name": candidate.get("factor_name"),
            "status": "signal_missing",
            "signal_date": None,
            "target_count": 0,
            "targets": [],
            "rebalance_plan": [],
            "executable": False,
            "manual_note": "这个因子暂时没有生成信号快照。",
        }
    if signal.get("error"):
        return {
            "case_id": candidate.get("case_id"),
            "factor_name": candidate.get("factor_name"),
            "status": "signal_error",
            "signal_date": signal.get("signal_date"),
            "target_count": 0,
            "targets": [],
            "rebalance_plan": [],
            "executable": False,
            "error": signal.get("error"),
            "manual_note": "这个因子入选了，但信号引擎没有生成同日信号。",
        }
    targets = [row for row in signal.get("targets", []) if isinstance(row, dict)]
    rebalance = [row for row in signal.get("rebalance_plan", []) if isinstance(row, dict)]
    return {
        "case_id": candidate.get("case_id"),
        "factor_name": candidate.get("factor_name"),
        "status": "signal_ready",
        "as_of_date": signal.get("as_of_date"),
        "signal_date": signal.get("signal_date"),
        "target_count": len(targets),
        "target_gross_exposure": signal.get("target_gross_exposure"),
        "cash_weight": signal.get("cash_weight"),
        "targets": targets,
        "rebalance_plan": _force_non_executable(rebalance),
        "executable": False,
        "manual_note": "仅作为建议输入；任何手工交易前必须复核模拟盘和风险闸门。",
    }


def _force_non_executable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = dict(row)
        item["executable"] = False
        item.setdefault("safety_note", SAFETY_NOTICE)
        result.append(item)
    return result


def _combined_targets(
    signal_cards: list[dict[str, Any]],
    portfolio_value: float,
    max_gross_exposure: float,
) -> list[dict[str, Any]]:
    accum: dict[str, dict[str, Any]] = defaultdict(dict)
    ready_cards = [card for card in signal_cards if card.get("status") == "signal_ready"]
    if not ready_cards:
        return []
    divisor = float(len(ready_cards))
    for card in ready_cards:
        for target in card.get("targets", []):
            if not isinstance(target, dict):
                continue
            asset_id = str(target.get("asset_id") or "")
            if not asset_id:
                continue
            bucket = accum[asset_id]
            bucket.setdefault("asset_id", asset_id)
            bucket.setdefault("market", target.get("market") or "CN_ETF")
            bucket.setdefault("latest_price", _float_or_none(target.get("latest_price")))
            bucket.setdefault("source_factors", [])
            liquidity_value, liquidity_field = _liquidity_reference_from_row(target)
            if liquidity_value is not None:
                existing_liquidity = _float_or_none(bucket.get("liquidity_reference_value"))
                if existing_liquidity is None or liquidity_value < existing_liquidity:
                    bucket["liquidity_reference_value"] = liquidity_value
                    bucket["liquidity_reference_field"] = liquidity_field
            bucket["target_weight"] = float(bucket.get("target_weight") or 0.0) + _float(target.get("target_weight"), 0.0) / divisor
            bucket["source_factors"].append(card.get("factor_name"))
    total_weight = sum(float(row.get("target_weight") or 0.0) for row in accum.values())
    cap = max(0.0, min(float(max_gross_exposure), 1.0))
    scale = cap / total_weight if total_weight > cap and total_weight > 0.0 else 1.0
    rows = []
    for row in accum.values():
        weight = float(row.get("target_weight") or 0.0) * scale
        rows.append(
            {
                "asset_id": row["asset_id"],
                "market": row.get("market") or "CN_ETF",
                "target_weight": weight,
                "target_value": weight * float(portfolio_value),
                "latest_price": row.get("latest_price"),
                **_tradeability_metadata(row),
                "source_factors": sorted({str(item) for item in row.get("source_factors", []) if item}),
                "executable": False,
            }
        )
    return sorted(rows, key=lambda item: (-float(item["target_weight"]), str(item["asset_id"])))


def _manual_trade_plan(
    combined_targets: list[dict[str, Any]],
    current_positions: list[dict[str, Any]] | None = None,
    portfolio_value: float = 100000.0,
    risk_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    positions = current_positions or []
    if positions:
        return _manual_rebalance_plan(
            combined_targets,
            positions,
            portfolio_value=portfolio_value,
            risk_profile=risk_profile,
        )
    rows = []
    for index, target in enumerate(combined_targets, start=1):
        sizing = _manual_ticket_sizing(target, board_lot_size=BOARD_LOT_SIZE)
        cash_impact = _manual_ticket_cash_impact("buy_or_adjust", sizing.get("rounded_value"))
        rows.append(
            {
                "ticket_id": f"daily-top3-{index:03d}",
                "asset_id": target.get("asset_id"),
                "market": target.get("market"),
                "side": "buy_or_adjust",
                "target_weight": target.get("target_weight"),
                "target_value": target.get("target_value"),
                "latest_price": target.get("latest_price"),
                "board_lot_size": BOARD_LOT_SIZE,
                **sizing,
                **cash_impact,
                **_tradeability_metadata(target),
                "source_factors": ", ".join(target.get("source_factors", [])),
                "executable": False,
                "live_order_allowed": False,
                "manual_instruction": "如需手工实盘，请先核对 ETF 代码、价格、流动性、账户现金和风险闸门，再由你本人在券商端操作；系统不会下单。",
            }
        )
    return rows


def _manual_rebalance_plan(
    combined_targets: list[dict[str, Any]],
    current_positions: list[dict[str, Any]],
    portfolio_value: float,
    risk_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    target_frame = pd.DataFrame(combined_targets)
    if target_frame.empty:
        target_frame = pd.DataFrame(columns=["asset_id", "market", "target_weight", "latest_price"])
    position_frame = pd.DataFrame(current_positions)
    if position_frame.empty:
        position_frame = pd.DataFrame(columns=["asset_id", "quantity", "latest_price", "market"])
    latest_prices = _rebalance_latest_prices(combined_targets, current_positions)
    rebalance = build_rebalance_plan(
        target_frame[["asset_id", "market", "target_weight", "latest_price"]],
        position_frame,
        latest_prices,
        portfolio_value=portfolio_value,
    )
    market_lookup = {
        str(row.get("asset_id")): str(row.get("market") or "CN_ETF")
        for row in current_positions
        if str(row.get("asset_id") or "").strip()
    }
    target_metadata_lookup = {
        str(row.get("asset_id") or ""): {
            **_tradeability_metadata(row),
            "source_factors": ", ".join(row.get("source_factors", []))
            if isinstance(row.get("source_factors"), list)
            else row.get("source_factors"),
        }
        for row in combined_targets
        if isinstance(row, dict) and str(row.get("asset_id") or "").strip()
    }
    rows = []
    for index, item in enumerate(rebalance.to_dict(orient="records"), start=1):
        ticket = _manual_rebalance_ticket(index, item, market_lookup)
        ticket.update(target_metadata_lookup.get(str(ticket.get("asset_id") or ""), {}))
        rows.append(ticket)
    return rows


def _manual_rebalance_ticket(index: int, row: dict[str, Any], market_lookup: dict[str, str]) -> dict[str, Any]:
    asset_id = str(row.get("asset_id") or "")
    latest_price = _float_or_none(row.get("latest_price"))
    estimated_quantity_delta = _float(row.get("estimated_quantity_delta"), 0.0)
    side = _manual_side(row.get("action"), estimated_quantity_delta)
    rounded_quantity = _rounded_trade_quantity(estimated_quantity_delta, BOARD_LOT_SIZE)
    rounded_value = None if latest_price is None else rounded_quantity * latest_price
    cash_impact = _manual_ticket_cash_impact(side, rounded_value)
    delta_value = _float(row.get("delta_value"), 0.0)
    cash_delta = None if rounded_value is None else abs(delta_value) - rounded_value
    target_quantity = None if latest_price is None or latest_price <= 0 else _float(row.get("target_value"), 0.0) / latest_price
    manual_instruction = (
        "已按当前持仓计算净买卖差额；如需手工实盘，请先核对 ETF 代码、实时价格、"
        "当前持仓、目标仓位、现金和风险闸门。系统不会下单。"
    )
    return {
        "ticket_id": f"daily-top3-{index:03d}",
        "asset_id": asset_id,
        "market": row.get("market") or market_lookup.get(asset_id) or "CN_ETF",
        "side": side,
        "current_quantity": row.get("current_quantity"),
        "current_weight": row.get("current_weight"),
        "current_value": row.get("current_value"),
        "target_weight": row.get("target_weight"),
        "target_value": row.get("target_value"),
        "delta_value": delta_value,
        "latest_price": latest_price,
        "board_lot_size": BOARD_LOT_SIZE,
        "estimated_target_quantity": target_quantity,
        "estimated_quantity": abs(estimated_quantity_delta),
        "estimated_quantity_delta": estimated_quantity_delta,
        "rounded_quantity": rounded_quantity,
        "rounded_quantity_delta": rounded_quantity if side == "buy" else -rounded_quantity if side == "sell" else 0,
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": cash_delta,
        "quantity_note": f"按 {BOARD_LOT_SIZE} 份一手对净买卖差额向下取整；仅供人工复核，系统不会下单。",
        **cash_impact,
        "source_factors": "",
        "executable": False,
        "live_order_allowed": False,
        "manual_instruction": manual_instruction,
    }


def _manual_ticket_cash_impact(side: Any, rounded_value: Any) -> dict[str, Any]:
    value = max(0.0, _float(rounded_value, 0.0))
    commission_cost = round(value * MANUAL_ESTIMATED_COMMISSION_BPS / 10000.0, 6)
    normalized_side = str(side or "").lower()
    if normalized_side.startswith("sell") or normalized_side == "decrease":
        sell_cash_released = round(max(0.0, value - commission_cost), 6)
        buy_cash_required = 0.0
    elif normalized_side.startswith("buy") or normalized_side == "increase":
        buy_cash_required = round(value + commission_cost, 6)
        sell_cash_released = 0.0
    else:
        buy_cash_required = 0.0
        sell_cash_released = 0.0
    return {
        "estimated_commission_bps": MANUAL_ESTIMATED_COMMISSION_BPS,
        "estimated_commission_cost": commission_cost,
        "estimated_buy_cash_required": buy_cash_required,
        "estimated_sell_cash_released": sell_cash_released,
        "estimated_cash_impact_after_costs": round(sell_cash_released - buy_cash_required, 6),
    }


def _manual_ticket_sizing(target: dict[str, Any], board_lot_size: int = BOARD_LOT_SIZE) -> dict[str, Any]:
    target_value = _float_or_none(target.get("target_value"))
    latest_price = _float_or_none(target.get("latest_price"))
    if target_value is None or latest_price is None or latest_price <= 0:
        return {
            "estimated_quantity": None,
            "rounded_quantity": None,
            "rounded_value": None,
            "cash_delta_after_rounding": None,
            "quantity_note": "缺少可用价格，不能估算份额；必须人工核对行情。",
        }
    estimated_quantity = target_value / latest_price
    rounded_quantity = int(math.floor(estimated_quantity / board_lot_size) * board_lot_size)
    rounded_value = rounded_quantity * latest_price
    return {
        "estimated_quantity": estimated_quantity,
        "rounded_quantity": rounded_quantity,
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": target_value - rounded_value,
        "quantity_note": f"按 {board_lot_size} 份一手向下取整；仅供人工复核，系统不会下单。",
    }


def _current_position_validation(
    current_positions: list[dict[str, Any]] | None,
    combined_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    target_prices = {
        str(row.get("asset_id") or ""): _float_or_none(row.get("latest_price"))
        for row in combined_targets
        if isinstance(row, dict) and str(row.get("asset_id") or "").strip()
    }
    rows = []
    issues = []
    paper_flat_template_seen = False
    raw_rows = current_positions or []
    for index, item in enumerate(raw_rows, start=1):
        if not isinstance(item, dict):
            issues.append(_current_position_issue(index, "current_position_invalid_row", "持仓行不是可识别的表格行。"))
            continue
        if item.get("__parse_error"):
            issues.append(_current_position_issue(index, "current_position_parse_error", f"持仓输入格式无法解析：{item.get('__parse_error')}"))
            continue
        forbidden = sorted(FORBIDDEN_REAL_ACCOUNT_COLUMNS & set(item))
        if forbidden:
            issues.append(
                _current_position_issue(
                    index,
                    "current_position_forbidden_field",
                    "当前持仓不能包含账户、券商或订单字段：" + ", ".join(forbidden),
                )
            )
            continue
        asset_id = str(item.get("asset_id") or "").strip()
        quantity = _float_or_none(item.get("quantity"))
        if not asset_id:
            issues.append(_current_position_issue(index, "current_position_missing_asset_id", "当前持仓缺少 ETF 代码 asset_id。"))
            continue
        if quantity is None:
            issues.append(_current_position_issue(index, "current_position_missing_quantity", f"{asset_id} 缺少可用数量 quantity。"))
            continue
        if asset_id.upper() in PAPER_FLAT_POSITION_ASSET_IDS:
            if abs(float(quantity)) > 1e-12:
                issues.append(
                    _current_position_issue(
                        index,
                        "paper_flat_position_template_nonzero_quantity",
                        "纸面空仓模板只能使用 quantity=0；如果是真实持仓，请填写真实 ETF 代码。",
                    )
                )
                continue
            paper_flat_template_seen = True
            continue
        market = str(item.get("market") or "CN_ETF").strip().upper()
        if market != "CN_ETF":
            issues.append(
                _current_position_issue(
                    index,
                    "current_position_market_mismatch",
                    f"{asset_id} market={market} is outside the CN_ETF rotation line; fix the holdings input before manual ticket generation.",
                )
            )
            continue
        latest_price = _float_or_none(item.get("latest_price"))
        if latest_price is None and target_prices.get(asset_id) is None:
            issues.append(
                _current_position_issue(
                    index,
                    "current_position_missing_price",
                    f"{asset_id} 不在今日目标里，且没有 latest_price，无法估算卖出或保留金额。",
                )
            )
            continue
        row = {
            "asset_id": asset_id,
            "quantity": quantity,
            "market": market,
        }
        if latest_price is not None:
            row["latest_price"] = latest_price
        rows.append(row)
    if issues:
        status = "error"
    elif rows or paper_flat_template_seen:
        status = "ok"
    else:
        status = "not_provided"
    return _sanitize(
        {
            "status": status,
            "accepted_count": len(rows) if status != "error" else 0,
            "paper_flat_position_template": bool(paper_flat_template_seen and status != "error"),
            "issue_count": len(issues),
            "issues": issues,
            "rows": rows if status != "error" else [],
            "manual_rebalance_allowed": status != "error",
            "plain_summary": _current_position_validation_summary(status, len(rows), issues),
        }
    )


def _current_position_issue(row_number: int, issue_id: str, message: str) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "issue_id": issue_id,
        "severity": "error",
        "message": message,
        "manual_rebalance_allowed": False,
    }


def _current_position_validation_summary(status: str, accepted_count: int, issues: list[dict[str, Any]]) -> str:
    if status == "ok":
        return f"已接收 {accepted_count} 条当前持仓，将按净买卖差额生成手工复核票据。"
    if status == "error":
        return "当前持仓输入有问题，今天不能生成可人工核对的买卖票据；请先修正持仓表。"
    return "未填写当前持仓；只能查看目标仓位，不能生成可人工核对的买卖票据。"


def _rebalance_latest_prices(
    combined_targets: list[dict[str, Any]],
    current_positions: list[dict[str, Any]],
) -> pd.DataFrame:
    price_rows = [
        {"asset_id": row.get("asset_id"), "latest_price": row.get("latest_price")}
        for row in combined_targets
        if isinstance(row, dict) and row.get("asset_id")
    ]
    price_rows.extend(
        {"asset_id": row.get("asset_id"), "latest_price": row.get("latest_price")}
        for row in current_positions
        if isinstance(row, dict) and row.get("asset_id") and row.get("latest_price") is not None
    )
    return pd.DataFrame(price_rows, columns=["asset_id", "latest_price"])


def _manual_side(action: Any, estimated_quantity_delta: float) -> str:
    if str(action) == "increase" or estimated_quantity_delta > 0:
        return "buy"
    if str(action) == "decrease" or estimated_quantity_delta < 0:
        return "sell"
    return "hold"


def _rounded_trade_quantity(estimated_quantity_delta: float, board_lot_size: int) -> int:
    quantity = abs(float(estimated_quantity_delta))
    return int(math.floor(quantity / board_lot_size) * board_lot_size)


def _operator_checklist() -> list[dict[str, Any]]:
    return [
        {
            "check_id": "manual_review_required",
            "status": "required",
            "text": "人工复核今日前三因子、信号日期、目标仓位和风险闸门。",
        },
        {
            "check_id": "paper_simulation_first",
            "status": "required",
            "text": "先跑或查看本地模拟盘，不把单日信号直接等同于可实盘收益。",
        },
        {
            "check_id": "broker_side_only_by_human",
            "status": "blocked_for_automation",
            "text": "系统不连接券商、不读取账户、不自动下单；如实盘，只能由人手工在券商端操作。",
        },
    ]


def _risk_profile_by_id(risk_profile_id: str | None) -> dict[str, Any] | None:
    if not risk_profile_id:
        return None
    wanted = str(risk_profile_id).strip()
    for profile in RISK_PROFILE_SPECS:
        if profile["profile_id"] == wanted:
            return dict(profile)
    for profile in RISK_PROFILE_SPECS:
        if profile["profile_id"] == DEFAULT_RISK_PROFILE_ID:
            return dict(profile)
    return None


def _risk_profiles(selected_id: str | None) -> list[dict[str, Any]]:
    selected = str(selected_id or "").strip()
    return [{**profile, "selected": profile["profile_id"] == selected} for profile in RISK_PROFILE_SPECS]


def _applied_max_gross_exposure(requested: float, profile: dict[str, Any] | None) -> float:
    requested_value = max(0.0, min(_float(requested, 1.0), 1.0))
    if not profile:
        return requested_value
    profile_cap = max(0.0, min(_float(profile.get("max_gross_exposure"), requested_value), 1.0))
    return min(requested_value, profile_cap)


def _first_market(rows: list[dict[str, Any]]) -> str | None:
    for row in rows:
        market = str(row.get("market") or "").strip()
        if market:
            return market
    return None


def _float(value: Any, default: float = 0.0) -> float:
    number = _float_or_none(value)
    return default if number is None else number


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int(value: Any, default: int) -> int:
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


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
