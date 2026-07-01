from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LEDGER_PATH = Path("data/reports/gui_operation_ledger/gui_operation_ledger.json")
MAX_LEDGER_ENTRIES = 50
SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
PAPER_REQUEST_SIGNATURE_KEYS = (
    "source",
    "market",
    "factor_name",
    "factor_windows",
    "top_n",
    "rebalance_interval",
    "initial_cash",
    "commission_bps",
    "slippage_bps",
    "max_asset_weight",
    "max_market_weight",
    "max_gross_exposure",
    "min_cash_weight",
    "max_drawdown_guard",
    "guard_cooldown_periods",
    "as_of_date",
    "run_date",
    "same_parameter_lock_id",
    "same_parameter_request_id",
    "case_id",
    "risk_profile_id",
)
SMALL_CAPITAL_OBSERVATION_LIMITS = {
    "max_initial_capital": 10000.0,
    "max_single_order_notional": 1000.0,
    "max_daily_loss": 200.0,
}
PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS = 3
PAPER_PERFORMANCE_AVG_RETURN_FLOOR = 0.0
PAPER_PERFORMANCE_MAX_DRAWDOWN = -(
    SMALL_CAPITAL_OBSERVATION_LIMITS["max_daily_loss"]
    / SMALL_CAPITAL_OBSERVATION_LIMITS["max_initial_capital"]
)


def append_operation_ledger_entry(
    *,
    repo_root: str | Path,
    workflow_id: str,
    label: str,
    status: str,
    command: str = "",
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    entry = _build_entry(
        workflow_id=workflow_id,
        label=label,
        status=status,
        command=command,
        request=request or {},
        result=result or {},
    )
    packet = _read_packet(root)
    rows = [entry, *packet.get("rows", [])][:MAX_LEDGER_ENTRIES]
    packet = _packet(rows)
    _write_packet(root, packet)
    return entry


def build_operation_ledger_snapshot(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    packet = _read_packet(root)
    rows = packet.get("rows", [])
    return _packet(rows)


def build_daily_closure_ledger_snapshot(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    packet = _read_packet(root)
    grouped: dict[str, dict[str, Any]] = {}
    for entry in packet.get("rows", []):
        if not isinstance(entry, dict):
            continue
        workflow_id = str(entry.get("workflow_id") or "")
        if workflow_id not in {"daily_trade_advisory", "paper_simulation", "post_close_journal"}:
            continue
        date_key = _closure_date_key(entry)
        if not date_key:
            continue
        row = grouped.setdefault(date_key, _empty_closure_row(date_key))
        _apply_closure_entry(row, entry)

    rows = [_finalize_closure_row(row) for row in grouped.values()]
    rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    rows = rows[:5]
    closed = sum(1 for row in rows if row.get("completed_loop"))
    blocked = sum(
        1
        for row in rows
        if row.get("manual_execution_blocked") or row.get("manual_execution_missing_review")
    )
    clean = sum(1 for row in rows if row.get("manual_execution_clean"))
    matched_paper = sum(1 for row in rows if row.get("paper_request_match_status") == "matched")
    legacy_unverified = sum(1 for row in rows if row.get("paper_request_match_status") == "legacy_unverified")
    paper_returns = [
        float(row["paper_total_return"])
        for row in rows
        if isinstance(row.get("paper_total_return"), (int, float))
    ]
    paper_drawdowns = [
        float(row["paper_max_drawdown"])
        for row in rows
        if isinstance(row.get("paper_max_drawdown"), (int, float))
    ]
    paper_positive_days = sum(1 for value in paper_returns if value > 0)
    paper_quality_days = sum(1 for row in rows if row.get("paper_performance_quality_status") == "pass")
    paper_average_total_return = _average(paper_returns)
    paper_worst_drawdown = min(paper_drawdowns) if paper_drawdowns else None
    paper_performance_quality_passed = (
        len(rows) >= 5
        and matched_paper >= 5
        and paper_positive_days >= PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS
        and paper_average_total_return is not None
        and paper_average_total_return > PAPER_PERFORMANCE_AVG_RETURN_FLOOR
        and paper_worst_drawdown is not None
        and paper_worst_drawdown >= PAPER_PERFORMANCE_MAX_DRAWDOWN
    )
    paper_performance_quality_status = (
        "pass"
        if paper_performance_quality_passed
        else "missing"
        if not paper_returns
        else "blocked"
    )
    status = (
        "server_closure_ready"
        if len(rows) >= 5 and closed >= 5 and matched_paper >= 5 and blocked == 0 and paper_performance_quality_passed
        else "blocked_by_manual_execution"
        if blocked
        else "needs_same_parameter_paper_evidence"
        if len(rows) >= 5 and closed >= 5 and matched_paper < 5
        else "needs_paper_performance_quality"
        if len(rows) >= 5 and closed >= 5 and matched_paper >= 5 and not paper_performance_quality_passed
        else "needs_more_closure_receipts"
    )
    return {
        "stage": "gui_daily_closure_ledger",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "status": status,
            "server_observed_days": len(rows),
            "closed_loop_days": closed,
            "clean_execution_days": clean,
            "blocked_execution_days": blocked,
            "matched_paper_days": matched_paper,
            "legacy_unverified_paper_days": legacy_unverified,
            "paper_positive_days": paper_positive_days,
            "paper_quality_days": paper_quality_days,
            "paper_quality_required_days": PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS,
            "paper_average_total_return": paper_average_total_return,
            "paper_worst_drawdown": paper_worst_drawdown,
            "paper_performance_max_drawdown": PAPER_PERFORMANCE_MAX_DRAWDOWN,
            "paper_performance_quality_status": paper_performance_quality_status,
            "paper_performance_quality_passed": paper_performance_quality_passed,
            "lookback_days": 5,
            "source": LEDGER_PATH.as_posix(),
            "next_action": _closure_next_action(rows),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "rows": rows,
        "safety": _safety(),
    }


def build_server_capital_observation_gate(daily_closure_ledger: dict[str, Any]) -> dict[str, Any]:
    summary = daily_closure_ledger.get("summary", {}) if isinstance(daily_closure_ledger, dict) else {}
    rows = daily_closure_ledger.get("rows", []) if isinstance(daily_closure_ledger, dict) else []
    closed = _int(summary.get("closed_loop_days"))
    clean = _int(summary.get("clean_execution_days"))
    blocked = _int(summary.get("blocked_execution_days"))
    observed = _int(summary.get("server_observed_days"))
    matched_paper = _int(summary.get("matched_paper_days"))
    legacy_unverified = _int(summary.get("legacy_unverified_paper_days"))
    paper_positive_days = _int(summary.get("paper_positive_days"))
    paper_quality_days = _int(summary.get("paper_quality_days"))
    paper_average_total_return = _optional_num(summary.get("paper_average_total_return"))
    paper_worst_drawdown = _optional_num(summary.get("paper_worst_drawdown"))
    paper_performance_quality_passed = bool(summary.get("paper_performance_quality_passed"))
    streak_ready = (
        observed >= 5
        and closed >= 5
        and clean >= 5
        and matched_paper >= 5
        and blocked == 0
        and paper_performance_quality_passed
    )
    if streak_ready:
        status = "manual_small_capital_observation_candidate"
        next_action = "Prepare a manual small-capital observation packet; keep broker connection and order placement outside this system."
    elif blocked > 0:
        status = "blocked_by_manual_execution_audit"
        next_action = "Review blocked manual execution days before any capital observation discussion."
    elif observed >= 5 and closed >= 5 and matched_paper < 5:
        status = "blocked_need_same_parameter_paper_evidence"
        next_action = "Rerun same-parameter paper simulation from the displayed daily advisory request before any capital observation discussion."
    elif observed >= 5 and closed >= 5 and clean >= 5 and matched_paper >= 5 and not paper_performance_quality_passed:
        status = "blocked_need_paper_performance_quality"
        next_action = "Keep running same-parameter paper observation until recent paper returns and drawdown clear the quality gate."
    else:
        status = "blocked_need_clean_server_closure_days"
        next_action = "Collect five clean server-side closure days before small-capital observation."
    gate_rows = [
        _capital_gate_row(
            "server_closure_streak",
            "Server closure streak",
            "pass" if streak_ready else "blocked",
            f"closed={closed}/5, observed={observed}/5",
        ),
        _capital_gate_row(
            "manual_execution_quality",
            "Manual execution quality",
            "pass" if clean >= 5 and blocked == 0 else "blocked",
            f"clean={clean}/5, blocked={blocked}",
        ),
        _capital_gate_row(
            "same_parameter_paper_evidence",
            "Same-parameter paper evidence",
            "pass" if matched_paper >= 5 else "blocked",
            f"matched={matched_paper}/5, legacy_unverified={legacy_unverified}",
        ),
        _capital_gate_row(
            "paper_performance_quality",
            "Paper performance quality",
            "pass" if paper_performance_quality_passed else "blocked",
            (
                f"positive={paper_positive_days}/{PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS}, "
                f"quality={paper_quality_days}/5, "
                f"avg_return={_format_optional_float(paper_average_total_return)}, "
                f"worst_drawdown={_format_optional_float(paper_worst_drawdown)}, "
                f"drawdown_floor={PAPER_PERFORMANCE_MAX_DRAWDOWN:.4f}"
            ),
        ),
        _capital_gate_row(
            "capital_scope",
            "Capital scope",
            "review",
            "candidate only; external human review must set budget and skip conditions",
        ),
        _capital_gate_row(
            "live_boundary",
            "Live boundary",
            "blocked_expected",
            "no broker connection, no account read, no order placement, no automated live trading",
        ),
    ]
    scorecard = _capital_observation_evidence_scorecard(
        closed=closed,
        clean=clean,
        blocked=blocked,
        matched_paper=matched_paper,
        paper_performance_quality_passed=paper_performance_quality_passed,
        paper_positive_days=paper_positive_days,
        paper_quality_days=paper_quality_days,
        paper_average_total_return=paper_average_total_return,
        paper_worst_drawdown=paper_worst_drawdown,
    )
    manual_observation_packet = _manual_small_capital_observation_packet(
        ready=streak_ready,
        status=status,
        next_action=next_action,
        closed=closed,
        observed=observed,
        clean=clean,
        blocked=blocked,
        matched_paper=matched_paper,
        legacy_unverified=legacy_unverified,
        paper_performance_quality_passed=paper_performance_quality_passed,
        paper_positive_days=paper_positive_days,
        paper_quality_days=paper_quality_days,
        paper_average_total_return=paper_average_total_return,
        paper_worst_drawdown=paper_worst_drawdown,
        scorecard=scorecard,
        recent_rows=rows[:5] if isinstance(rows, list) else [],
    )
    return {
        "stage": "gui_server_capital_observation_gate",
        "summary": {
            "status": status,
            "manual_small_capital_observation_candidate": streak_ready,
            "server_closed_loop_days": closed,
            "server_observed_days": observed,
            "clean_execution_days": clean,
            "blocked_execution_days": blocked,
            "matched_paper_days": matched_paper,
            "legacy_unverified_paper_days": legacy_unverified,
            "paper_positive_days": paper_positive_days,
            "paper_quality_days": paper_quality_days,
            "paper_quality_required_days": PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS,
            "paper_average_total_return": paper_average_total_return,
            "paper_worst_drawdown": paper_worst_drawdown,
            "paper_performance_max_drawdown": PAPER_PERFORMANCE_MAX_DRAWDOWN,
            "paper_performance_quality_passed": paper_performance_quality_passed,
            "next_action": next_action,
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "rows": gate_rows,
        "evidence_scorecard": scorecard,
        "manual_observation_packet": manual_observation_packet,
        "recent_closure_rows": rows[:5] if isinstance(rows, list) else [],
        "safety": _safety(),
    }


def _manual_small_capital_observation_packet(
    *,
    ready: bool,
    status: str,
    next_action: str,
    closed: int,
    observed: int,
    clean: int,
    blocked: int,
    matched_paper: int,
    legacy_unverified: int,
    paper_performance_quality_passed: bool,
    paper_positive_days: int,
    paper_quality_days: int,
    paper_average_total_return: float | None,
    paper_worst_drawdown: float | None,
    scorecard: dict[str, Any],
    recent_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    score_summary = scorecard.get("summary", {}) if isinstance(scorecard, dict) else {}
    next_missing = str(score_summary.get("next_missing_gate_id") or "")
    material_ready = bool(ready and score_summary.get("manual_observation_material_ready"))
    packet_status = (
        "ready_for_external_manual_observation_review"
        if material_ready
        else "blocked_need_more_evidence"
    )
    plain_answer = (
        "服务端闭环证据已够，可以准备小资金人工观察材料；软件仍不能连接券商、读取账户或下单。"
        if material_ready
        else "小资金人工观察材料未齐；先补完缺失的同参数模拟盘、盘后复盘或人工执行审计。"
    )
    return {
        "stage": "gui_manual_small_capital_observation_packet",
        "summary": {
            "status": packet_status,
            "source_gate_status": status,
            "ordinary_question": "现在能不能开始小资金实盘观察？",
            "plain_answer": plain_answer,
            "manual_observation_material_ready": material_ready,
            "next_missing_gate_id": next_missing,
            "next_action": next_action,
            "server_closed_loop_days": closed,
            "server_observed_days": observed,
            "clean_execution_days": clean,
            "blocked_execution_days": blocked,
            "matched_paper_days": matched_paper,
            "legacy_unverified_paper_days": legacy_unverified,
            "paper_positive_days": paper_positive_days,
            "paper_quality_days": paper_quality_days,
            "paper_quality_required_days": PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS,
            "paper_average_total_return": paper_average_total_return,
            "paper_worst_drawdown": paper_worst_drawdown,
            "paper_performance_max_drawdown": PAPER_PERFORMANCE_MAX_DRAWDOWN,
            "paper_performance_quality_passed": paper_performance_quality_passed,
            "max_initial_capital": SMALL_CAPITAL_OBSERVATION_LIMITS["max_initial_capital"],
            "max_single_order_notional": SMALL_CAPITAL_OBSERVATION_LIMITS["max_single_order_notional"],
            "max_daily_loss": SMALL_CAPITAL_OBSERVATION_LIMITS["max_daily_loss"],
            "external_manual_only": True,
            "software_order_submission_allowed": False,
            "paper_only": True,
            "real_money_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "risk_limits": [
            _small_capital_limit_row(
                "max_initial_capital",
                "Maximum initial observation capital",
                SMALL_CAPITAL_OBSERVATION_LIMITS["max_initial_capital"],
                "Total external cash allocated to the first manual observation period must not exceed this value.",
            ),
            _small_capital_limit_row(
                "max_single_order_notional",
                "Maximum single order notional",
                SMALL_CAPITAL_OBSERVATION_LIMITS["max_single_order_notional"],
                "Each external manual ticket must stay below this notional value after broker-side price recheck.",
            ),
            _small_capital_limit_row(
                "max_daily_loss",
                "Maximum daily loss",
                SMALL_CAPITAL_OBSERVATION_LIMITS["max_daily_loss"],
                "If external manual observation loses this much in one day, stop and record a post-close risk review.",
            ),
        ],
        "operator_steps": _small_capital_operator_steps(material_ready),
        "required_inputs": _small_capital_required_inputs(material_ready),
        "forbidden_actions": _small_capital_forbidden_actions(),
        "recent_closure_dates": [
            str(row.get("date") or "")
            for row in recent_rows
            if isinstance(row, dict) and row.get("date")
        ],
        "evidence_scorecard_summary": score_summary,
        "safety": {
            **_safety(),
            "real_money_allowed": False,
            "auto_order_allowed": False,
        },
    }


def _small_capital_limit_row(limit_id: str, label: str, value: float, plain_rule: str) -> dict[str, Any]:
    return {
        "limit_id": limit_id,
        "label": label,
        "value": value,
        "plain_rule": plain_rule,
        "external_manual_only": True,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _small_capital_operator_steps(material_ready: bool) -> list[dict[str, Any]]:
    return [
        _small_capital_step(
            "read_small_capital_limits",
            "Read the small-capital limits",
            "required" if material_ready else "locked",
            "control-server-capital-observation-gate",
            "Confirm max initial capital, max single order notional, and max daily loss before opening any external broker app.",
        ),
        _small_capital_step(
            "review_today_final_operation_packet",
            "Review today's final operation packet",
            "required" if material_ready else "locked",
            "daily-beginner-execution-answer-final-packet",
            "Use only the latest final packet, manual price/cash recheck, and skip rules; Top3 names alone are not orders.",
        ),
        _small_capital_step(
            "external_manual_decision_only",
            "External manual decision only",
            "manual_only" if material_ready else "locked",
            "beginner-live-handoff-board",
            "If the human proceeds, the action happens outside this software; the software still cannot place orders.",
        ),
        _small_capital_step(
            "record_post_close_observation",
            "Record the post-close observation",
            "required" if material_ready else "locked",
            "beginner-post-close-journal-board",
            "Record execution, skip reason, slippage, risk state, and whether the observation stayed inside limits.",
        ),
    ]


def _small_capital_step(
    step_id: str,
    label: str,
    status: str,
    target_id: str,
    plain_action: str,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "label": label,
        "status": status,
        "target_id": target_id,
        "plain_action": plain_action,
        "manual_required": True,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _small_capital_required_inputs(material_ready: bool) -> list[dict[str, Any]]:
    status = "required" if material_ready else "locked"
    return [
        _small_capital_input("external_cash_budget", status, "Write the exact external cash budget before observation starts."),
        _small_capital_input("per_order_notional_check", status, "Confirm every external manual ticket stays below the packet limit."),
        _small_capital_input("daily_loss_stop_acknowledgement", status, "Confirm the daily loss stop and what to do after it triggers."),
        _small_capital_input("post_close_review_plan", status, "Confirm how today's manual observation will be recorded after close."),
    ]


def _small_capital_input(input_id: str, status: str, plain_requirement: str) -> dict[str, Any]:
    return {
        "input_id": input_id,
        "status": status,
        "plain_requirement": plain_requirement,
        "external_manual_only": True,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _small_capital_forbidden_actions() -> list[dict[str, Any]]:
    return [
        {
            "action_id": "do_not_scale_above_packet_limits",
            "plain_rule": "Do not exceed the packet's capital, single-order, or daily-loss limits.",
            "order_placement_allowed": False,
        },
        {
            "action_id": "do_not_treat_top3_as_orders",
            "plain_rule": "Do not treat Top3 factor names or target rows as broker orders.",
            "order_placement_allowed": False,
        },
        {
            "action_id": "do_not_skip_same_day_price_cash_recheck",
            "plain_rule": "Do not skip external realtime price, available cash, and board-lot recalculation.",
            "order_placement_allowed": False,
        },
        {
            "action_id": "do_not_skip_post_close_closure",
            "plain_rule": "Do not skip post-close review; missing closure quarantines future reuse evidence.",
            "order_placement_allowed": False,
        },
    ]


def _capital_observation_evidence_scorecard(
    *,
    closed: int,
    clean: int,
    blocked: int,
    matched_paper: int,
    paper_performance_quality_passed: bool,
    paper_positive_days: int,
    paper_quality_days: int,
    paper_average_total_return: float | None,
    paper_worst_drawdown: float | None,
) -> dict[str, Any]:
    score_rows = [
        _capital_evidence_row(
            gate_id="server_closed_loop_days",
            label="Server closed-loop days",
            status="pass" if closed >= 5 else "blocked",
            current_value=closed,
            required_value=5,
            comparator=">=",
            plain_requirement="Collect at least five server-side closure days with Top3 advisory, same-parameter paper evidence, and post-close journal.",
            target_id="control-daily-closure-ledger",
            workflow_id="daily_trade_advisory" if closed < 5 else "",
        ),
        _capital_evidence_row(
            gate_id="same_parameter_paper_days",
            label="Same-parameter paper days",
            status="pass" if matched_paper >= 5 else "blocked",
            current_value=matched_paper,
            required_value=5,
            comparator=">=",
            plain_requirement="Collect at least five paper receipts whose parameters match the daily Top3 advisory request.",
            target_id="paper-metrics",
            workflow_id="paper_simulation" if matched_paper < 5 else "",
        ),
        _capital_evidence_row(
            gate_id="paper_performance_quality",
            label="Paper performance quality",
            status="pass" if paper_performance_quality_passed else "blocked",
            current_value=paper_quality_days,
            required_value=PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS,
            comparator=">=",
            plain_requirement=(
                "Recent same-parameter paper evidence must show at least three positive/quality days, "
                "positive average return, and no drawdown beyond the small-capital daily loss floor."
            ),
            target_id="paper-metrics",
            workflow_id="paper_simulation" if not paper_performance_quality_passed else "",
        ),
        _capital_evidence_row(
            gate_id="clean_manual_execution_days",
            label="Clean manual execution days",
            status="pass" if clean >= 5 else "blocked",
            current_value=clean,
            required_value=5,
            comparator=">=",
            plain_requirement="Collect at least five post-close manual execution audits with no missing review or breach.",
            target_id="control-daily-closure-ledger",
            workflow_id="post_close_journal" if clean < 5 else "",
        ),
        _capital_evidence_row(
            gate_id="blocked_manual_execution_days",
            label="Blocked manual execution days",
            status="pass" if blocked == 0 else "blocked",
            current_value=blocked,
            required_value=0,
            comparator="=",
            plain_requirement="Chasing, overslippage, quantity mismatch, and missing execution review must stay at zero.",
            target_id="beginner-post-close-journal-board",
            workflow_id="post_close_journal" if blocked else "",
        ),
        _capital_evidence_row(
            gate_id="research_only_live_boundary",
            label="Research-only live boundary",
            status="pass",
            current_value=0,
            required_value=0,
            comparator="=",
            plain_requirement="The software does not connect to brokers, read accounts, place orders, or run automated live trading.",
            target_id="control-safety-boundary",
            workflow_id="",
        ),
    ]
    passed = sum(1 for row in score_rows if row.get("status") == "pass")
    next_missing = next((str(row.get("gate_id") or "") for row in score_rows if row.get("status") != "pass"), "")
    ready = passed == len(score_rows)
    return {
        "stage": "gui_small_capital_observation_evidence_scorecard",
        "summary": {
            "status": "ready_for_manual_small_capital_packet" if ready else "blocked_need_more_evidence",
            "passed_gate_count": passed,
            "required_gate_count": len(score_rows),
            "readiness_score_pct": int(round(passed / max(len(score_rows), 1) * 100)),
            "next_missing_gate_id": next_missing,
            "paper_positive_days": paper_positive_days,
            "paper_quality_days": paper_quality_days,
            "paper_quality_required_days": PAPER_PERFORMANCE_REQUIRED_POSITIVE_DAYS,
            "paper_average_total_return": paper_average_total_return,
            "paper_worst_drawdown": paper_worst_drawdown,
            "paper_performance_max_drawdown": PAPER_PERFORMANCE_MAX_DRAWDOWN,
            "paper_performance_quality_passed": paper_performance_quality_passed,
            "manual_observation_material_ready": ready,
            "paper_only": True,
            "real_money_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "rows": score_rows,
        "safety": _safety(),
    }


def _capital_evidence_row(
    *,
    gate_id: str,
    label: str,
    status: str,
    current_value: int,
    required_value: int,
    comparator: str,
    plain_requirement: str,
    target_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "current_value": current_value,
        "required_value": required_value,
        "comparator": comparator,
        "plain_requirement": plain_requirement,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "paper_only": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "auto_order_allowed": False,
    }


def _build_entry(
    *,
    workflow_id: str,
    label: str,
    status: str,
    command: str,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
    return {
        "operation_id": f"{workflow_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}",
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "workflow_id": workflow_id,
        "label": label,
        "status": status,
        "command": command,
        "request": _json_safe(request),
        "metrics": _json_safe(metrics),
        "request_summary": _request_summary(request),
        "metric_summary": _metric_summary(metrics, result),
        "stage": result.get("stage", ""),
        "safety": _safety(),
    }


def _packet(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = rows[0] if rows else {}
    return {
        "stage": "gui_operation_ledger",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "entry_count": len(rows),
            "max_entries": MAX_LEDGER_ENTRIES,
            "latest_workflow_id": latest.get("workflow_id", ""),
            "latest_status": latest.get("status", ""),
            "path": LEDGER_PATH.as_posix(),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": rows,
        "safety": _safety(),
    }


def _read_packet(root: Path) -> dict[str, Any]:
    path = root / LEDGER_PATH
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _packet([])
    rows = packet.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    return _packet([row for row in rows if isinstance(row, dict)][:MAX_LEDGER_ENTRIES])


def _write_packet(root: Path, packet: dict[str, Any]) -> None:
    path = root / LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")


def _request_summary(request: dict[str, Any]) -> str:
    keys = [
        "market",
        "factor_name",
        "factor",
        "top_n",
        "cost_bps",
        "as_of_date",
        "run_date",
        "start_date",
        "end_date",
        "initial_cash",
        "gate_id",
    ]
    parts = [f"{key}={request[key]}" for key in keys if request.get(key) not in {None, ""}]
    return " / ".join(parts)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _metric_summary(metrics: dict[str, Any], result: dict[str, Any]) -> str:
    metric_keys = [
        "total_return",
        "annualized_return",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "ending_equity",
        "target_count",
        "signal_count",
        "manual_ticket_count",
        "manual_execution_decision",
        "manual_execution_missing_review_count",
        "manual_execution_guardrail_breach_count",
        "manual_execution_slippage_breach_count",
        "returncode",
    ]
    values: list[str] = []
    for key in metric_keys:
        value = metrics.get(key, result.get(key))
        if value not in {None, ""}:
            values.append(f"{key}={_format_metric(value)}")
    return " / ".join(values) or str(result.get("status", ""))


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _safety() -> dict[str, Any]:
    return {
        "notice": SAFETY_NOTICE,
        "paper_only": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _closure_date_key(entry: dict[str, Any]) -> str:
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    candidates = [
        request.get("as_of_date"),
        request.get("run_date"),
        request.get("end_date"),
        entry.get("recorded_at"),
    ]
    for value in candidates:
        key = _normalize_date_key(value)
        if key:
            return key
    return ""


def _normalize_date_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _empty_closure_row(date_key: str) -> dict[str, Any]:
    return {
        "date": date_key,
        "top3_signal_ready": False,
        "same_parameter_paper_ready": False,
        "post_close_journal_ready": False,
        "manual_execution_clean": False,
        "manual_execution_blocked": False,
        "manual_execution_missing_review": False,
        "paper_receipt_completed": False,
        "expected_paper_request_signature": {},
        "expected_same_parameter_paper_requests": [],
        "expected_same_parameter_paper_request_ids": [],
        "matched_same_parameter_paper_request_ids": [],
        "missing_same_parameter_paper_request_ids": [],
        "same_parameter_paper_required_count": 0,
        "same_parameter_paper_matched_count": 0,
        "latest_paper_request_signature": {},
        "paper_request_signatures": [],
        "paper_request_match_status": "missing",
        "paper_request_mismatch_keys": [],
        "paper_total_return": None,
        "paper_sharpe": None,
        "paper_max_drawdown": None,
        "paper_win_rate": None,
        "paper_performance_quality_status": "missing",
        "latest_daily_trade_receipt": "",
        "latest_paper_receipt": "",
        "latest_post_close_receipt": "",
        "missing_steps": [],
        "completed_loop": False,
    }


def _apply_closure_entry(row: dict[str, Any], entry: dict[str, Any]) -> None:
    workflow_id = str(entry.get("workflow_id") or "")
    status = str(entry.get("status") or "")
    if status not in {"completed", "passed"}:
        return
    metrics = entry.get("metrics", {}) if isinstance(entry.get("metrics"), dict) else {}
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    recorded_at = str(entry.get("recorded_at") or "")
    if workflow_id == "daily_trade_advisory":
        signal_count = _num(metrics.get("signal_count"), _num(request.get("signal_count"), 0.0))
        selected_count = _num(metrics.get("selected_factor_count"), _num(request.get("selected_factor_count"), 0.0))
        if signal_count > 0 or selected_count > 0:
            row["top3_signal_ready"] = True
            row["latest_daily_trade_receipt"] = recorded_at
            expected_top3 = _daily_expected_same_parameter_requests(entry)
            if expected_top3:
                row["expected_same_parameter_paper_requests"] = expected_top3
                row["expected_same_parameter_paper_request_ids"] = [
                    _same_parameter_request_id(item, index)
                    for index, item in enumerate(expected_top3, start=1)
                ]
            row["expected_paper_request_signature"] = _daily_expected_paper_signature(entry)
    elif workflow_id == "paper_simulation":
        row["paper_receipt_completed"] = True
        signature = _request_signature(request)
        row["latest_paper_request_signature"] = signature
        paper_signatures = row.get("paper_request_signatures")
        if not isinstance(paper_signatures, list):
            paper_signatures = []
        paper_signatures.append(signature)
        row["paper_request_signatures"] = paper_signatures
        row["latest_paper_receipt"] = recorded_at
        row["paper_total_return"] = _paper_total_return(metrics, request)
        row["paper_sharpe"] = _optional_num(metrics.get("sharpe"))
        row["paper_max_drawdown"] = _optional_num(
            metrics.get("max_drawdown", metrics.get("max_equity_drawdown"))
        )
        row["paper_win_rate"] = _optional_num(metrics.get("win_rate"))
    elif workflow_id == "post_close_journal":
        row["post_close_journal_ready"] = bool(metrics.get("manual_review_recorded", True))
        row["latest_post_close_receipt"] = recorded_at
        status_text = str(metrics.get("manual_execution_decision") or "")
        missing = _num(metrics.get("manual_execution_missing_review_count"), 0.0)
        blocked = (
            _num(metrics.get("manual_execution_guardrail_breach_count"), 0.0)
            + _num(metrics.get("manual_execution_slippage_breach_count"), 0.0)
            + _num(metrics.get("manual_execution_blocked_count"), 0.0)
        )
        if status_text == "manual_execution_evidence_ready" and missing <= 0 and blocked <= 0:
            row["manual_execution_clean"] = True
        elif status_text == "manual_execution_review_incomplete" or missing > 0:
            row["manual_execution_missing_review"] = True
        elif status_text == "guardrail_breach_review_required" or blocked > 0:
            row["manual_execution_blocked"] = True


def _finalize_closure_row(row: dict[str, Any]) -> dict[str, Any]:
    row = _finalize_same_parameter_paper(row)
    row = _finalize_paper_performance(row)
    missing = []
    if not row.get("top3_signal_ready"):
        missing.append("daily_trade_advisory")
    if not row.get("same_parameter_paper_ready"):
        missing.append("paper_simulation")
    if not row.get("post_close_journal_ready"):
        missing.append("post_close_journal")
    if not row.get("manual_execution_clean"):
        missing.append("manual_execution_clean")
    completed = not missing and not row.get("manual_execution_blocked") and not row.get("manual_execution_missing_review")
    return {
        **row,
        "missing_steps": missing,
        "completed_loop": completed,
        "live_trading_allowed": False,
        "order_placement_allowed": False,
    }


def _finalize_same_parameter_paper(row: dict[str, Any]) -> dict[str, Any]:
    paper_done = bool(row.get("paper_receipt_completed"))
    expected_top3 = (
        row.get("expected_same_parameter_paper_requests")
        if isinstance(row.get("expected_same_parameter_paper_requests"), list)
        else []
    )
    if expected_top3:
        actual_signatures = [
            item
            for item in (row.get("paper_request_signatures") if isinstance(row.get("paper_request_signatures"), list) else [])
            if isinstance(item, dict)
        ]
        matched_ids: list[str] = []
        missing_ids: list[str] = []
        mismatch_keys: list[str] = []
        for index, expected_request in enumerate(expected_top3, start=1):
            if not isinstance(expected_request, dict):
                continue
            request_id = _same_parameter_request_id(expected_request, index)
            expected_signature = _request_signature(expected_request)
            matched = False
            request_mismatch_keys: list[str] = []
            for actual_signature in actual_signatures:
                candidate_mismatches = _signature_mismatch_keys(actual_signature, expected_signature)
                if not candidate_mismatches:
                    matched = True
                    break
                request_mismatch_keys = request_mismatch_keys or candidate_mismatches
            if matched:
                matched_ids.append(request_id)
            else:
                missing_ids.append(request_id)
                mismatch_keys.extend(request_mismatch_keys or ["missing_same_parameter_paper_receipt"])
        row["same_parameter_paper_required_count"] = len(expected_top3)
        row["same_parameter_paper_matched_count"] = len(matched_ids)
        row["matched_same_parameter_paper_request_ids"] = matched_ids
        row["missing_same_parameter_paper_request_ids"] = missing_ids
        row["same_parameter_paper_ready"] = bool(expected_top3) and not missing_ids
        if not paper_done or not matched_ids:
            row["paper_request_match_status"] = "missing"
        else:
            row["paper_request_match_status"] = "matched" if not missing_ids else "partial"
        row["paper_request_mismatch_keys"] = sorted(set(mismatch_keys))
        return row

    expected = row.get("expected_paper_request_signature") if isinstance(row.get("expected_paper_request_signature"), dict) else {}
    latest = row.get("latest_paper_request_signature") if isinstance(row.get("latest_paper_request_signature"), dict) else {}
    if not paper_done:
        row["same_parameter_paper_ready"] = False
        row["paper_request_match_status"] = "missing"
        row["paper_request_mismatch_keys"] = []
        return row
    if expected:
        mismatches = _signature_mismatch_keys(latest, expected)
        row["same_parameter_paper_ready"] = not mismatches
        row["paper_request_match_status"] = "matched" if not mismatches else "mismatched"
        row["paper_request_mismatch_keys"] = mismatches
        return row
    row["same_parameter_paper_ready"] = True
    row["paper_request_match_status"] = "legacy_unverified"
    row["paper_request_mismatch_keys"] = []
    return row


def _finalize_paper_performance(row: dict[str, Any]) -> dict[str, Any]:
    total_return = _optional_num(row.get("paper_total_return"))
    max_drawdown = _optional_num(row.get("paper_max_drawdown"))
    if not row.get("same_parameter_paper_ready"):
        row["paper_performance_quality_status"] = "missing"
        return row
    if total_return is None or max_drawdown is None:
        row["paper_performance_quality_status"] = "missing"
        return row
    row["paper_total_return"] = total_return
    row["paper_max_drawdown"] = max_drawdown
    row["paper_performance_quality_status"] = (
        "pass"
        if total_return > PAPER_PERFORMANCE_AVG_RETURN_FLOOR
        and max_drawdown >= PAPER_PERFORMANCE_MAX_DRAWDOWN
        else "blocked"
    )
    return row


def _paper_total_return(metrics: dict[str, Any], request: dict[str, Any]) -> float | None:
    explicit = _optional_num(metrics.get("total_return", metrics.get("return")))
    if explicit is not None:
        return explicit
    ending_equity = _optional_num(metrics.get("ending_equity"))
    initial_cash = _optional_num(
        metrics.get("initial_cash", request.get("initial_cash"))
    )
    if ending_equity is None or initial_cash is None or initial_cash <= 0:
        return None
    return (ending_equity / initial_cash) - 1.0


def _daily_expected_paper_signature(entry: dict[str, Any]) -> dict[str, Any]:
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    for key in ("paper_request_signature", "same_parameter_paper_request", "paper_simulation_request"):
        value = request.get(key)
        if isinstance(value, dict):
            return _request_signature(value)
    return {}


def _daily_expected_same_parameter_requests(entry: dict[str, Any]) -> list[dict[str, Any]]:
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    for key in ("same_parameter_top3_paper_requests", "same_parameter_paper_requests"):
        value = request.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _same_parameter_request_id(request: dict[str, Any], index: int) -> str:
    for key in ("same_parameter_request_id", "request_id", "case_id", "factor_name", "factor"):
        value = str(request.get(key) or "").strip()
        if value:
            return value
    return f"top3-paper-{index:03d}"


def _request_signature(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {}
    source: dict[str, Any] = dict(request)
    if not source.get("factor_name") and source.get("factor") not in {None, ""}:
        source["factor_name"] = source.get("factor")
    signature: dict[str, Any] = {}
    for key in PAPER_REQUEST_SIGNATURE_KEYS:
        value = source.get(key)
        if value is None or value == "":
            continue
        signature[key] = _canonical_signature_value(key, value)
    return signature


def _signature_mismatch_keys(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            mismatches.append(key)
    return mismatches


def _canonical_signature_value(key: str, value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 10)
    text = str(value).strip()
    if key == "market":
        return text.upper()
    if key == "factor_windows":
        if isinstance(value, (list, tuple)):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return text.replace(" ", "")
    if key in {
        "top_n",
        "rebalance_interval",
        "initial_cash",
        "commission_bps",
        "slippage_bps",
        "max_asset_weight",
        "max_market_weight",
        "max_gross_exposure",
        "min_cash_weight",
        "max_drawdown_guard",
        "guard_cooldown_periods",
    }:
        try:
            return round(float(text), 10)
        except ValueError:
            return text
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True, ensure_ascii=False)
    return text


def _closure_next_action(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Run daily trade advisory, paper simulation, and post-close review to start the server-side closure ledger."
    latest = rows[0]
    if latest.get("completed_loop"):
        if latest.get("paper_performance_quality_status") != "pass":
            return "Keep running same-parameter paper performance observation before any small-capital review."
        return "Continue collecting five clean server-side closure days before any small-capital observation."
    missing = latest.get("missing_steps") if isinstance(latest.get("missing_steps"), list) else []
    return "Refresh missing closure step: " + (" / ".join(str(item) for item in missing) or "manual review")


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "missing"
    return f"{value:.4f}"


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _capital_gate_row(gate_id: str, label: str, status: str, evidence: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "live_trading_allowed": False,
        "order_placement_allowed": False,
    }
