from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


STAGE = "phase_6_0_daily_trade_advisory"
PRETRADE_WORKFLOW_STAGE = "phase_6_1_daily_pretrade_workflow"
PRETRADE_READINESS_STAGE = "phase_6_2_manual_pretrade_readiness"
MANUAL_BROKER_HANDOFF_STAGE = "phase_6_3_manual_broker_handoff"
TRADE_SYSTEM_STAGE = "phase_6_4_manual_trade_system_protocol"
SAFETY_NOTICE = "仅研究到模拟盘：不连接券商、不读取账户、不生成实盘委托、不自动下单。"
BOARD_LOT_SIZE = 100


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
            }
        )
        if len(selected) >= max(1, int(limit)):
            break
    return selected


def build_daily_trade_advisory_pack(
    candidates: list[dict[str, Any]],
    signal_snapshots: list[dict[str, Any]],
    run_date: str | None = None,
    portfolio_value: float = 100000.0,
    max_gross_exposure: float = 1.0,
) -> dict[str, Any]:
    signal_cards = [_signal_card(candidate, _matching_signal(candidate, signal_snapshots)) for candidate in candidates]
    combined_targets = _combined_targets(signal_cards, portfolio_value=portfolio_value, max_gross_exposure=max_gross_exposure)
    manual_plan = _manual_trade_plan(combined_targets)
    pack = {
        "stage": STAGE,
        "run_date": run_date or date.today().isoformat(),
        "safety": SAFETY_NOTICE,
        "summary": {
            "selected_factor_count": len(candidates),
            "signal_count": sum(1 for card in signal_cards if card["status"] == "signal_ready"),
            "combined_target_count": len(combined_targets),
            "manual_ticket_count": len(manual_plan),
            "manual_execution_required": True,
            "paper_simulation_recommended": True,
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


def _build_pretrade_readiness(pack: dict[str, Any]) -> dict[str, Any]:
    summary = pack.get("summary") if isinstance(pack.get("summary"), dict) else {}
    factors = [row for row in pack.get("factors", []) if isinstance(row, dict)]
    signal_cards = [row for row in pack.get("signal_cards", []) if isinstance(row, dict)]
    targets = [row for row in pack.get("combined_targets", []) if isinstance(row, dict)]
    manual_plan = [row for row in pack.get("manual_trade_plan", []) if isinstance(row, dict)]
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
    if signal_count <= 0 or target_count <= 0 or manual_count <= 0:
        blockers.append("signal_not_ready")
    if signal_errors:
        blockers.append("signal_errors")
    if invalid_sizing_tickets:
        blockers.append("price_or_sizing_missing")
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
            "latest_price": row.get("latest_price"),
            "rounded_quantity": row.get("rounded_quantity"),
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
    reference_price = "--" if latest_price is None else f"{latest_price:.4f}"
    copy_text = (
        f"{index}. ETF {asset_id}；方向={side}；参考价={reference_price}；"
        f"按 {BOARD_LOT_SIZE} 份一手取整数量={rounded_quantity}；"
        f"参考金额={rounded_value:.2f}；取整后剩余现金约={cash_delta:.2f}。"
        "请在券商端核对实时价格、代码、现金和风险；系统不会下单。"
    )
    return {
        "step_number": index,
        "ticket_id": row.get("ticket_id"),
        "asset_id": asset_id,
        "side": side,
        "reference_price": latest_price,
        "rounded_quantity": rounded_quantity,
        "rounded_value": rounded_value,
        "cash_delta_after_rounding": cash_delta,
        "source_factors": row.get("source_factors"),
        "copy_text": copy_text,
        "do_not_submit_until_checked": True,
        "live_order_allowed": False,
        "order_placement_allowed": False,
    }


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


def _manual_trade_plan(combined_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
