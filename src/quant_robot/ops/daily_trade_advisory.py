from __future__ import annotations

import csv
import io
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

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
SAFETY_NOTICE = "仅研究到模拟盘：不连接券商、不读取账户、不生成实盘委托、不自动下单。"
BOARD_LOT_SIZE = 100
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

    metadata_keys = {
        "status",
        "decision",
        "promotion_status",
        "gate_status",
        "selection_status",
        "review_status",
        "promotion_label",
        "ranking_quality",
        "has_oos_evidence",
        "score_metric",
    }
    if not (metadata_keys & set(row)):
        return (True, "legacy_runnable_candidate")
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
) -> dict[str, Any]:
    signal_cards = [_signal_card(candidate, _matching_signal(candidate, signal_snapshots)) for candidate in candidates]
    selected_profile = _risk_profile_by_id(risk_profile_id)
    applied_max_gross_exposure = _applied_max_gross_exposure(max_gross_exposure, selected_profile)
    combined_targets = _combined_targets(
        signal_cards,
        portfolio_value=portfolio_value,
        max_gross_exposure=applied_max_gross_exposure,
    )
    fallback_signal_only = _fallback_signal_only(candidates)
    manual_plan_blocked_reason = "fallback_baseline_not_tradeable" if fallback_signal_only else ""
    position_validation = _current_position_validation(current_positions, combined_targets)
    position_rows = position_validation["rows"] if position_validation["status"] != "error" else []
    manual_plan = (
        []
        if position_validation["status"] == "error" or manual_plan_blocked_reason
        else _manual_trade_plan(
            combined_targets,
            current_positions=position_rows,
            portfolio_value=portfolio_value,
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
        "markdown": "",
    }
    pack["pretrade_readiness"] = _build_pretrade_readiness(pack)
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
    pack["daily_trade_decision_sheet"] = build_daily_trade_decision_sheet(pack)
    pack["trading_system_blueprint"] = build_daily_trading_system_blueprint(pack)
    pack["daily_signal_execution_bridge"] = build_daily_signal_execution_bridge(pack)
    pack["real_world_manual_handoff_gate"] = build_real_world_manual_handoff_gate(pack)
    pack["daily_deployment_readiness"] = build_daily_deployment_readiness_pack(pack)
    pack["live_profitability_readiness"] = build_live_profitability_readiness_scorecard(pack)
    pack["summary"]["live_transition_status"] = pack["live_transition_plan"]["summary"]["status"]
    pack["summary"]["trading_system_status"] = pack["trading_system_blueprint"]["summary"]["status"]
    pack["summary"]["execution_bridge_status"] = pack["daily_signal_execution_bridge"]["summary"]["status"]
    pack["summary"]["real_world_handoff_status"] = pack["real_world_manual_handoff_gate"]["summary"]["decision"]
    pack["summary"]["deployment_readiness_status"] = pack["daily_deployment_readiness"]["summary"]["decision"]
    pack["summary"]["live_profitability_readiness_status"] = pack["live_profitability_readiness"]["summary"]["decision"]
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

    if validation.get("status") == "error":
        decision = "fix_current_positions_first"
        primary_action = "先修正当前持仓输入；不要看买卖票据，也不要在券商端操作。"
        primary_reason = validation.get("plain_summary") or "当前持仓输入存在错误。"
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
    positions_ok = validation.get("status") != "error"
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
            "blocked" if position_status == "error" else ("pass" if position_status == "ok" else "waiting"),
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
    if signal_count <= 0 or target_count <= 0 or (manual_count <= 0 and not summary.get("fallback_signal_only")):
        blockers.append("signal_not_ready")
    if signal_errors:
        blockers.append("signal_errors")
    if invalid_sizing_tickets:
        blockers.append("price_or_sizing_missing")
    if position_validation.get("status") == "error":
        blockers.append("current_position_input_invalid")
    if signal_count > 0 and not freshness["fresh_for_run_date"]:
        blockers.append("stale_signal_date")

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
            "status": "blocked" if position_validation.get("status") == "error" else ("pass" if position_validation.get("status") == "ok" else "waiting"),
            "text": (
                f"当前持仓输入状态={position_validation.get('status') or 'not_provided'}；"
                f"已接收={position_validation.get('accepted_count', 0)}；问题={position_validation.get('issue_count', 0)}。"
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
    if summary.get("fallback_signal_only"):
        warnings.append("当前只有内置基线演示信号，没有合格推广候选；只能观察和跑模拟盘，不能生成手工交易票据。")
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
            "summary": {
                "selected_factor_count": selected_count,
                "signal_count": signal_count,
                "target_count": target_count,
                "manual_ticket_count": manual_count,
                "manual_trade_plan_blocked": bool(summary.get("manual_trade_plan_blocked")),
                "manual_trade_plan_blocked_reason": summary.get("manual_trade_plan_blocked_reason"),
                "current_position_count": position_validation.get("accepted_count", 0),
                "current_position_issue_count": position_validation.get("issue_count", 0),
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
    blocking_reasons = [str(item) for item in readiness.get("blockers", []) if str(item).strip()]
    can_show_tickets = bool(readiness.get("manual_action_candidate"))
    copyable_tickets = [
        _broker_handoff_ticket(index, row)
        for index, row in enumerate(manual_plan, start=1)
        if can_show_tickets
    ]
    rounded_value = sum(_float(row.get("rounded_value"), 0.0) for row in manual_plan)
    cash_delta = sum(_float(row.get("cash_delta_after_rounding"), 0.0) for row in manual_plan)
    target_value = sum(_float(row.get("target_value"), 0.0) for row in manual_plan)
    if copyable_tickets:
        status = "review_only"
    elif "stale_signal_date" in blocking_reasons:
        status = "blocked_by_freshness"
    elif blocking_reasons:
        status = "blocked_by_readiness"
    else:
        status = "waiting_for_tickets"
    if copyable_tickets:
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
            "blocking_reasons": blocking_reasons,
            "summary": {
                "ticket_count": len(copyable_tickets),
                "target_value": target_value,
                "rounded_value": rounded_value,
                "cash_delta_after_rounding": cash_delta,
                "traffic_light": readiness.get("traffic_light"),
                "manual_action_candidate": bool(readiness.get("manual_action_candidate")),
            },
            "confirmation_checklist": [
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


def _broker_handoff_ticket(index: int, row: dict[str, Any]) -> dict[str, Any]:
    asset_id = str(row.get("asset_id") or "")
    side = str(row.get("side") or "buy_or_adjust")
    latest_price = _float_or_none(row.get("latest_price"))
    rounded_quantity = _int(row.get("rounded_quantity"), 0)
    rounded_value = _float(row.get("rounded_value"), 0.0)
    cash_delta = _float(row.get("cash_delta_after_rounding"), 0.0)
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
        "source_factors": row.get("source_factors"),
        "copy_text": copy_text,
        "do_not_submit_until_checked": True,
        "live_order_allowed": False,
        "order_placement_allowed": False,
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
            "today_actions": today_actions,
            "missing_evidence": missing_evidence,
            "operator_script": operator_script,
            "trade_system_state": trade_system_state,
            "trade_package_checklist": trade_package_checklist,
            "safety": SAFETY_NOTICE,
        }
    )


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
    ticket_source = copyable_tickets or manual_plan
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

    ticket_source = copyable_tickets or manual_plan
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


def build_live_profitability_readiness_scorecard(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    readiness = pack.get("pretrade_readiness") if isinstance(pack.get("pretrade_readiness"), dict) else {}
    validation = pack.get("current_position_validation") if isinstance(pack.get("current_position_validation"), dict) else {}
    deployment = pack.get("daily_deployment_readiness") if isinstance(pack.get("daily_deployment_readiness"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
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
    else:
        decision = "not_ready_for_real_money"
        plain_answer = "今天只能进入同参数模拟盘和人工复核；还不能宣称稳定盈利，也不能直接投入真实资金。"
        next_label = "先跑同参数模拟盘"
        next_target = "paper-metrics"
        next_workflow = "paper_simulation"

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
            "required",
            "候选因子必须有 walk-forward、OOS、长周期和不同市场状态证据，不能只看短期总收益。",
            "control-backtest-gate",
            evidence_kind="walk_forward_oos_report",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "lookahead_bias_audit",
            "未来函数审计",
            "required",
            "信号使用收盘数据时至少下一交易日执行；负向 shift、全样本归一化、报告期错位必须审计。",
            "daily-trading-system-blueprint",
            evidence_kind="lookahead_bias_audit",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "multiple_testing_control",
            "多重检验控制",
            "required",
            "需要记录总实验数、去重参数组合和显著性修正，避免只挑最好看的回测。",
            "factor-leaderboard-table",
            evidence_kind="multiple_testing_log",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "transaction_cost_capacity",
            "成本 / 滑点 / 容量",
            "required",
            "必须扣除手续费、滑点、冲击成本，检查 ETF 成交额、换手率和单票容量。",
            "daily-pretrade-readiness-verdict",
            evidence_kind="cost_capacity_report",
            required_before="small_capital_observation",
        ),
        _live_profitability_gate(
            "matched_paper_receipts",
            "同参数模拟盘回执",
            "required",
            "至少积累 5 次同参数模拟盘回执，再讨论小资金人工观察。",
            "paper-metrics",
            "paper_simulation" if paper_rehearsal_allowed else "",
            evidence_kind="paper_simulation_receipts",
            required_before="small_capital_observation",
            minimum_required_observations=5,
        ),
        _live_profitability_gate(
            "post_close_journals",
            "盘后复盘样本",
            "required",
            "至少积累 5 次盘后复盘，记录执行、跳过、滑点、未成交、回撤和异常。",
            "beginner-post-close-journal-board",
            "post_close_journal" if has_signal_targets else "",
            evidence_kind="post_close_journal_receipts",
            required_before="small_capital_observation",
            minimum_required_observations=5,
        ),
        _live_profitability_gate(
            "production_sample_size",
            "生产观察样本",
            "required",
            "至少 20 次 paper-ready 观察样本通过后，才允许讨论人工生产化；不能靠一两天收益升级。",
            "beginner-live-handoff-board",
            evidence_kind="paper_ready_observation_history",
            required_before="production_manual_review",
            minimum_required_observations=20,
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
            "hard_gates": hard_gates,
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
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "evidence_kind": evidence_kind,
        "required_before": required_before,
        "minimum_required_observations": minimum_required_observations,
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
) -> dict[str, Any]:
    blocked = decision.startswith("blocked") or blocker_count > 0 or position_status == "error"
    has_candidate_pool = market == "CN_ETF" and selected_factor_count > 0
    has_today_signal = signal_count > 0 and target_count > 0
    has_manual_ticket = ticket_count > 0
    if position_status == "error":
        mode = "blocked_fix_current_positions"
    elif blocked:
        mode = "blocked_pretrade_red_light"
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
            "small_capital_observation_allowed": False,
            "live_trading_allowed": False,
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
        "source_factors",
        "review_status",
        "review_only",
        "paper_simulation_required",
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
        "source_factors": factor_text,
        "review_status": "manual_review_only",
        "review_only": True,
        "paper_simulation_required": True,
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
                "source_factors": sorted({str(item) for item in row.get("source_factors", []) if item}),
                "executable": False,
            }
        )
    return sorted(rows, key=lambda item: (-float(item["target_weight"]), str(item["asset_id"])))


def _manual_trade_plan(
    combined_targets: list[dict[str, Any]],
    current_positions: list[dict[str, Any]] | None = None,
    portfolio_value: float = 100000.0,
) -> list[dict[str, Any]]:
    positions = current_positions or []
    if positions:
        return _manual_rebalance_plan(combined_targets, positions, portfolio_value=portfolio_value)
    rows = []
    for index, target in enumerate(combined_targets, start=1):
        sizing = _manual_ticket_sizing(target, board_lot_size=BOARD_LOT_SIZE)
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
) -> list[dict[str, Any]]:
    target_frame = pd.DataFrame(combined_targets)
    if target_frame.empty:
        target_frame = pd.DataFrame(columns=["asset_id", "market", "target_weight", "latest_price"])
    position_frame = pd.DataFrame(current_positions)
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
    rows = []
    for index, item in enumerate(rebalance.to_dict(orient="records"), start=1):
        rows.append(_manual_rebalance_ticket(index, item, market_lookup))
    return rows


def _manual_rebalance_ticket(index: int, row: dict[str, Any], market_lookup: dict[str, str]) -> dict[str, Any]:
    asset_id = str(row.get("asset_id") or "")
    latest_price = _float_or_none(row.get("latest_price"))
    estimated_quantity_delta = _float(row.get("estimated_quantity_delta"), 0.0)
    side = _manual_side(row.get("action"), estimated_quantity_delta)
    rounded_quantity = _rounded_trade_quantity(estimated_quantity_delta, BOARD_LOT_SIZE)
    rounded_value = None if latest_price is None else rounded_quantity * latest_price
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
        "estimated_target_quantity": target_quantity,
        "estimated_quantity": abs(estimated_quantity_delta),
        "estimated_quantity_delta": estimated_quantity_delta,
        "rounded_quantity": rounded_quantity,
        "rounded_quantity_delta": rounded_quantity if side == "buy" else -rounded_quantity if side == "sell" else 0,
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": cash_delta,
        "quantity_note": f"按 {BOARD_LOT_SIZE} 份一手对净买卖差额向下取整；仅供人工复核，系统不会下单。",
        "source_factors": "",
        "executable": False,
        "live_order_allowed": False,
        "manual_instruction": manual_instruction,
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
            "market": item.get("market") or "CN_ETF",
        }
        if latest_price is not None:
            row["latest_price"] = latest_price
        rows.append(row)
    if issues:
        status = "error"
    elif rows:
        status = "ok"
    else:
        status = "not_provided"
    return _sanitize(
        {
            "status": status,
            "accepted_count": len(rows) if status != "error" else 0,
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
    return "未填写当前持仓，将按目标仓位估算买入金额；进入实盘前建议先手填当前持仓。"


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
