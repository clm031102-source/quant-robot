from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from quant_robot.gui.operation_ledger import build_operation_ledger_snapshot


SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
GUI_AUDIT_PACKET_PATH = Path("data/reports/gui_control_center_audit/gui_control_center_audit.json")
GUI_AUDIT_AUTOMATION_ID = "gui-5h"
GUI_AUDIT_CADENCE_ROUNDS = 5
RESOLVED_AUDIT_LOOP_ACTIONS = {
    "Attach audit findings to next optimization round",
    "Review linked audit packets during next audit",
}
VERIFICATION_RUNNER_GATE_IDS = ("gui_compile", "project_audit", "sync_audit")
VERIFICATION_RUNNER_TIMEOUT_SECONDS = {
    "gui_compile": 120,
    "project_audit": 180,
    "sync_audit": 180,
}


def build_control_center_snapshot(repo_root: str | Path | None = None, active_goal: str | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    branch = _git_branch(root)
    workspace_sync = _workspace_sync(root, branch)
    process_monitor = _process_monitor(root)
    active_operation = _active_operation_spec()
    operation_ledger = build_operation_ledger_snapshot(root)
    artifacts = _artifact_status(root)
    backtest = _default_backtest()
    form_defaults = _form_defaults(backtest)
    workflows = _workflow_commands(form_defaults)
    parameter_authority = _parameter_authority(form_defaults, workflows)
    run_queue = _run_queue(workflows)
    trade_mode_control = _trade_mode_control(workflows)
    verification_gates = _verification_gates()
    verification_runner = build_verification_runner_snapshot(verification_gates)
    ledger_evidence = _ledger_evidence(workflows, operation_ledger, verification_runner)
    readiness_matrix = _readiness_matrix(workflows, verification_gates, artifacts)
    workflow_preflight = _workflow_preflight(
        workflows,
        parameter_authority,
        ledger_evidence,
        readiness_matrix,
        verification_runner,
    )
    audit_packets = _audit_packets(root)
    startup_health = _startup_health(workflows, verification_gates, audit_packets)
    backtest_provenance = _backtest_provenance(backtest, workflows)
    execution_receipts = _execution_receipts_spec()
    result_evidence = _result_evidence(workflows, execution_receipts)
    backtest_gate = _backtest_gate(workflows, execution_receipts)
    audit_packet_source = _load_gui_audit_packet(root)
    latest_gui_audit = audit_packet_source.get("packet") if audit_packet_source.get("status") == "packet_present" else None
    audit_scorecard = _audit_scorecard(
        verification_gates,
        readiness_matrix,
        artifacts,
        audit_packets,
        latest_gui_audit,
        backtest_provenance,
        result_evidence,
        ledger_evidence,
        process_monitor,
    )
    audit_feedback = _audit_feedback(audit_packet_source, audit_packets)
    audit_iteration_plan = _audit_iteration_plan(audit_feedback, audit_scorecard, verification_gates, readiness_matrix)
    action_center = _action_center(ledger_evidence, audit_iteration_plan, verification_runner)
    audit_scheduler = _audit_scheduler(root, audit_packet_source, operation_ledger)
    round_checkpoint_report = _round_checkpoint_report(
        latest_gui_audit,
        operation_ledger,
        audit_scheduler,
        audit_scorecard,
        audit_iteration_plan,
        verification_gates,
    )
    release_readiness = _release_readiness(verification_gates, audit_packets, readiness_matrix)
    workflow_trace = _workflow_trace(
        workflows,
        run_queue,
        startup_health,
        result_evidence,
        release_readiness,
        execution_receipts,
    )

    return {
        "stage": "gui_control_center",
        "status": "ready",
        "work": {
            "machine": os.environ.get("QUANT_ROBOT_MACHINE", "office_desktop"),
            "task": os.environ.get("QUANT_ROBOT_TASK", "factor_review"),
            "branch": branch,
            "goal": active_goal
            or "Build and continuously improve the Quant Robot GUI control center MVP.",
            "branch_policy": "Use a codex/ task branch for GUI work; keep main stable.",
        },
        "backtest": backtest,
        "form_defaults": form_defaults,
        "parameter_authority": parameter_authority,
        "workflow_preflight": workflow_preflight,
        "workspace_sync": workspace_sync,
        "process_monitor": process_monitor,
        "active_operation": active_operation,
        "operation_ledger": operation_ledger,
        "trade_mode_control": trade_mode_control,
        "action_center": action_center,
        "method": {
            "title": "Backtest path",
            "steps": [
                {"step": 1, "name": "Load local bars", "detail": "Use local processed CN_ETF bars or demo fixtures."},
                {"step": 2, "name": "Build factor", "detail": "Compute the selected factor and configured windows."},
                {"step": 3, "name": "Create labels", "detail": "Use forward returns aligned with the configured horizon."},
                {"step": 4, "name": "Delay execution", "detail": "Apply execution_lag before simulated entry."},
                {"step": 5, "name": "Rank portfolio", "detail": "Select top_n assets within the requested portfolio scope."},
                {"step": 6, "name": "Apply costs", "detail": "Deduct cost_bps and paper slippage assumptions."},
                {"step": 7, "name": "Compute metrics", "detail": "Report return, Sharpe, drawdown, win rate, trades, and benchmark comparison."},
                {"step": 8, "name": "Record artifacts", "detail": "Expose local reports and logs without committing generated data."},
            ],
        },
        "workflows": workflows,
        "run_queue": run_queue,
        "verification_gates": verification_gates,
        "verification_runner": verification_runner,
        "operator_checklist": _operator_checklist(verification_gates, artifacts),
        "execution_plan": _execution_plan(workflows, verification_gates),
        "startup_health": startup_health,
        "backtest_provenance": backtest_provenance,
        "backtest_gate": backtest_gate,
        "workflow_trace": workflow_trace,
        "readiness_matrix": readiness_matrix,
        "release_readiness": release_readiness,
        "audit_scorecard": audit_scorecard,
        "operator_timeline": _operator_timeline(workflows, verification_gates, readiness_matrix, audit_scorecard),
        "run_history": _run_history_spec(),
        "execution_receipts": execution_receipts,
        "audit_packets": audit_packets,
        "audit_feedback": audit_feedback,
        "round_checkpoint_report": round_checkpoint_report,
        "audit_iteration_plan": audit_iteration_plan,
        "audit_scheduler": audit_scheduler,
        "results": {
            "source": "Run research or paper workflow to populate live result values in the browser.",
            "metrics": [
                {"key": "total_return", "label": "Total return"},
                {"key": "annualized_return", "label": "Annualized return"},
                {"key": "sharpe", "label": "Sharpe"},
                {"key": "max_drawdown", "label": "Max drawdown"},
                {"key": "win_rate", "label": "Win rate"},
                {"key": "trade_count", "label": "Trade count"},
                {"key": "benchmark_relative_return", "label": "Benchmark relative return"},
                {"key": "paper_ending_equity", "label": "Paper ending equity"},
            ],
        },
        "result_evidence": result_evidence,
        "ledger_evidence": ledger_evidence,
        "artifacts": artifacts,
        "report_links": _report_links(root, artifacts, audit_packets),
        "safety": {
            "notice": SAFETY_NOTICE,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "automation": {
            "cadence": audit_scheduler["summary"].get(
                "cadence",
                f"Every {GUI_AUDIT_CADENCE_ROUNDS} GUI rounds; fallback every 5 hours",
            ),
            "name": audit_scheduler["summary"].get("name", "GUI control center audit"),
            "status": audit_scheduler["summary"].get("status", "unknown"),
            "expected_output": "Score, required fixes, and next optimization list.",
        },
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_backtest() -> dict[str, Any]:
    return {
        "source": "processed-bars",
        "data_root": "data/processed/etf_csv",
        "market": "CN_ETF",
        "factor": "momentum_2",
        "factor_windows": "5,10,20,60,120",
        "top_n": 2,
        "cost_bps": 5.0,
        "rebalance_interval": 5,
        "execution_lag": 1,
        "forward_horizon": 1,
        "start_date": "2026-01-01",
        "end_date": "2026-05-21",
        "benchmark_asset_id": "CN_ETF_XSHG_510300",
        "cash_annual_return": 0.015,
        "regime_filter": True,
        "regime_lookback": 3,
        "max_drawdown_limit": 0.25,
    }


def _form_defaults(backtest: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "gui_form_defaults",
        "summary": {
            "status": "ready",
            "source": backtest["source"],
            "market": backtest["market"],
            "factor": backtest["factor"],
            "paper_only": True,
            "live_trading_allowed": False,
            "next_action": "Apply these defaults to GUI form controls before running workflow buttons.",
        },
        "research": {
            "source": backtest["source"],
            "data_root": backtest["data_root"],
            "market": backtest["market"],
            "factor": backtest["factor"],
            "factor_windows": backtest["factor_windows"],
            "top_n": backtest["top_n"],
            "cost_bps": backtest["cost_bps"],
            "execution_lag": backtest["execution_lag"],
            "forward_horizon": backtest["forward_horizon"],
            "rebalance_interval": backtest["rebalance_interval"],
            "benchmark_asset_id": backtest["benchmark_asset_id"],
            "cash_annual_return": backtest["cash_annual_return"],
            "regime_filter": backtest["regime_filter"],
            "regime_lookback": backtest["regime_lookback"],
            "min_relative_return": "",
            "max_drawdown_limit": backtest["max_drawdown_limit"],
            "start_date": backtest["start_date"],
            "end_date": backtest["end_date"],
        },
        "signal": {
            "source": backtest["source"],
            "data_root": backtest["data_root"],
            "market": backtest["market"],
            "factor": backtest["factor"],
            "factor_windows": backtest["factor_windows"],
            "top_n": backtest["top_n"],
            "as_of_date": backtest["end_date"],
            "max_asset_weight": 0.4,
            "max_market_weight": 1,
            "max_gross_exposure": 1,
            "min_cash_weight": 0.1,
        },
        "paper": {
            "source": backtest["source"],
            "data_root": backtest["data_root"],
            "market": backtest["market"],
            "factor": backtest["factor"],
            "factor_windows": backtest["factor_windows"],
            "top_n": backtest["top_n"],
            "rebalance_interval": backtest["rebalance_interval"],
            "start_date": backtest["start_date"],
            "end_date": backtest["end_date"],
            "initial_cash": 100000,
            "commission_bps": 5,
            "slippage_bps": 5,
            "max_asset_weight": 0.4,
            "max_market_weight": 1,
            "max_gross_exposure": 1,
            "min_cash_weight": 0.1,
            "max_drawdown_guard": "",
            "guard_cooldown_periods": 0,
        },
        "safety": _verification_runner_safety(),
    }


def _workflow_commands(form_defaults: dict[str, Any]) -> list[dict[str, Any]]:
    specs = _workflow_request_specs(form_defaults)
    research = specs["research_backtest"]
    signal = specs["signal_snapshot"]
    paper = specs["paper_simulation"]
    return [
        {
            "workflow_id": "gui_start",
            "label": "Start local GUI",
            "command": "python scripts\\run_gui.py --host 127.0.0.1 --port 8765",
            "endpoint": "/",
            "mode": "local",
            "safety": "no broker, no account reads, no orders",
        },
        {
            "workflow_id": "research_backtest",
            "label": "Run research backtest",
            "command": f"GET {research['endpoint']}",
            "endpoint": research["endpoint"],
            "request": research["request"],
            "query": research["query"],
            "mode": "local",
            "safety": "research calculation only",
        },
        {
            "workflow_id": "signal_snapshot",
            "label": "Generate advisory signal snapshot",
            "command": f"GET {signal['endpoint']}",
            "endpoint": signal["endpoint"],
            "request": signal["request"],
            "query": signal["query"],
            "mode": "local",
            "safety": "advisory targets only, executable=false",
        },
        {
            "workflow_id": "paper_simulation",
            "label": "Run local paper simulation",
            "command": f"GET {paper['endpoint']}",
            "endpoint": paper["endpoint"],
            "request": paper["request"],
            "query": paper["query"],
            "mode": "local",
            "safety": "simulated fills only",
        },
        {
            "workflow_id": "project_audit",
            "label": "Run project audit",
            "command": "python scripts\\run_project_audit.py --json",
            "endpoint": "",
            "mode": "local",
            "safety": "code and config audit only",
        },
    ]


def _workflow_request_specs(form_defaults: dict[str, Any]) -> dict[str, dict[str, Any]]:
    research = form_defaults["research"]
    signal = form_defaults["signal"]
    paper = form_defaults["paper"]
    research_query = {
        "market": research["market"],
        "factor": research["factor"],
        "factor_windows": research["factor_windows"],
        "top_n": research["top_n"],
        "cost_bps": research["cost_bps"],
        "start_date": research["start_date"],
        "end_date": research["end_date"],
        "forward_horizon": research["forward_horizon"],
        "execution_lag": research["execution_lag"],
        "rebalance_interval": research["rebalance_interval"],
        "benchmark_asset_id": research["benchmark_asset_id"],
        "cash_annual_return": research["cash_annual_return"],
        "regime_filter": research["regime_filter"],
        "regime_lookback": research["regime_lookback"],
        "min_relative_return": research["min_relative_return"],
        "max_drawdown_limit": research["max_drawdown_limit"],
        "source": research["source"],
        "data_root": research["data_root"],
    }
    signal_query = {
        "market": signal["market"],
        "factor": signal["factor"],
        "factor_windows": signal["factor_windows"],
        "top_n": signal["top_n"],
        "as_of_date": signal["as_of_date"],
        "max_asset_weight": signal["max_asset_weight"],
        "max_market_weight": signal["max_market_weight"],
        "max_gross_exposure": signal["max_gross_exposure"],
        "min_cash_weight": signal["min_cash_weight"],
        "source": signal["source"],
        "data_root": signal["data_root"],
    }
    paper_query = {
        "market": paper["market"],
        "factor": paper["factor"],
        "factor_windows": paper["factor_windows"],
        "top_n": paper["top_n"],
        "rebalance_interval": paper["rebalance_interval"],
        "start_date": paper["start_date"],
        "end_date": paper["end_date"],
        "initial_cash": paper["initial_cash"],
        "commission_bps": paper["commission_bps"],
        "slippage_bps": paper["slippage_bps"],
        "max_asset_weight": paper["max_asset_weight"],
        "max_market_weight": paper["max_market_weight"],
        "max_gross_exposure": paper["max_gross_exposure"],
        "min_cash_weight": paper["min_cash_weight"],
        "max_drawdown_guard": paper["max_drawdown_guard"],
        "guard_cooldown_periods": paper["guard_cooldown_periods"],
        "source": paper["source"],
        "data_root": paper["data_root"],
    }
    return {
        "research_backtest": {
            "endpoint": _workflow_endpoint_from_query("/api/research", research_query),
            "query": research_query,
            "request": {
                "market": research["market"],
                "factor_name": research["factor"],
                "factor_windows": _factor_windows_list(research["factor_windows"]),
                "top_n": research["top_n"],
                "cost_bps": research["cost_bps"],
                "start_date": research["start_date"],
                "end_date": research["end_date"],
                "forward_horizon": research["forward_horizon"],
                "execution_lag": research["execution_lag"],
                "rebalance_interval": research["rebalance_interval"],
                "benchmark_asset_id": research["benchmark_asset_id"],
                "cash_annual_return": research["cash_annual_return"],
                "regime_filter": research["regime_filter"],
                "regime_lookback": research["regime_lookback"],
                "min_relative_return": _optional_number(research["min_relative_return"]),
                "max_drawdown_limit": research["max_drawdown_limit"],
            },
        },
        "signal_snapshot": {
            "endpoint": _workflow_endpoint_from_query("/api/signals", signal_query),
            "query": signal_query,
            "request": {
                "market": signal["market"],
                "factor_name": signal["factor"],
                "factor_windows": _factor_windows_list(signal["factor_windows"]),
                "top_n": signal["top_n"],
                "as_of_date": signal["as_of_date"],
                "max_asset_weight": signal["max_asset_weight"],
                "max_market_weight": signal["max_market_weight"],
                "max_gross_exposure": signal["max_gross_exposure"],
                "min_cash_weight": signal["min_cash_weight"],
            },
        },
        "paper_simulation": {
            "endpoint": _workflow_endpoint_from_query("/api/paper", paper_query),
            "query": paper_query,
            "request": {
                "market": paper["market"],
                "factor_name": paper["factor"],
                "factor_windows": _factor_windows_list(paper["factor_windows"]),
                "top_n": paper["top_n"],
                "rebalance_interval": paper["rebalance_interval"],
                "start_date": paper["start_date"],
                "end_date": paper["end_date"],
                "initial_cash": paper["initial_cash"],
                "commission_bps": paper["commission_bps"],
                "slippage_bps": paper["slippage_bps"],
                "max_asset_weight": paper["max_asset_weight"],
                "max_market_weight": paper["max_market_weight"],
                "max_gross_exposure": paper["max_gross_exposure"],
                "min_cash_weight": paper["min_cash_weight"],
                "max_drawdown_guard": _optional_number(paper["max_drawdown_guard"]),
                "guard_cooldown_periods": paper["guard_cooldown_periods"],
            },
        },
    }


def _parameter_authority(form_defaults: dict[str, Any], workflows: list[dict[str, Any]]) -> dict[str, Any]:
    specs = {
        "research_backtest": {
            "label": "Research backtest",
            "defaults_key": "research",
            "comparison_keys": [
                "market",
                "factor_name",
                "factor_windows",
                "top_n",
                "cost_bps",
                "start_date",
                "end_date",
                "execution_lag",
                "forward_horizon",
                "rebalance_interval",
                "benchmark_asset_id",
                "cash_annual_return",
                "regime_filter",
                "regime_lookback",
                "max_drawdown_limit",
            ],
        },
        "signal_snapshot": {
            "label": "Signal snapshot",
            "defaults_key": "signal",
            "comparison_keys": [
                "market",
                "factor_name",
                "factor_windows",
                "top_n",
                "as_of_date",
                "max_asset_weight",
                "max_market_weight",
                "max_gross_exposure",
                "min_cash_weight",
            ],
        },
        "paper_simulation": {
            "label": "Paper simulation",
            "defaults_key": "paper",
            "comparison_keys": [
                "market",
                "factor_name",
                "factor_windows",
                "top_n",
                "rebalance_interval",
                "start_date",
                "end_date",
                "initial_cash",
                "commission_bps",
                "slippage_bps",
                "max_asset_weight",
                "max_market_weight",
                "max_gross_exposure",
                "min_cash_weight",
            ],
        },
    }
    rows: list[dict[str, Any]] = []
    for workflow_id, spec in specs.items():
        workflow = _workflow_by_id(workflows, workflow_id) or {}
        canonical_request = workflow.get("request", {}) if isinstance(workflow.get("request"), dict) else {}
        defaults = form_defaults.get(str(spec["defaults_key"]), {})
        rows.append(
            {
                "workflow_id": workflow_id,
                "label": spec["label"],
                "status": "canonical",
                "defaults_key": spec["defaults_key"],
                "authority_source": "form_defaults -> workflow.request -> frontend parameter consistency",
                "comparison_keys": spec["comparison_keys"],
                "canonical_request": canonical_request,
                "canonical_summary": _request_brief(canonical_request),
                "form_default_summary": _request_brief(_defaults_request_view(defaults)),
                "endpoint": str(workflow.get("endpoint") or ""),
                "command": str(workflow.get("command") or ""),
                "paper_only": True,
                "live_trading_allowed": False,
                "safety": SAFETY_NOTICE,
            }
        )
    return {
        "stage": "gui_parameter_authority",
        "summary": {
            "status": "ready",
            "authority_source": "form_defaults",
            "workflow_count": len(rows),
            "frontend_checker": "renderParameterConsistency",
            "next_action": "Keep current form parameters aligned with these canonical workflow requests before running actions.",
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": rows,
        "safety": _verification_runner_safety(),
    }


def _defaults_request_view(defaults: dict[str, Any]) -> dict[str, Any]:
    result = dict(defaults)
    if "factor" in result and "factor_name" not in result:
        result["factor_name"] = result["factor"]
    return result


def _request_brief(request: dict[str, Any]) -> str:
    return " / ".join(
        part
        for part in [
            str(request.get("market") or ""),
            str(request.get("factor_name") or request.get("factor") or ""),
            f"top_n={request.get('top_n')}" if request.get("top_n") not in {None, ""} else "",
            f"cost={request.get('cost_bps')}bps" if request.get("cost_bps") not in {None, ""} else "",
            f"cash={request.get('initial_cash')}" if request.get("initial_cash") not in {None, ""} else "",
            str(request.get("start_date") or request.get("as_of_date") or ""),
            str(request.get("end_date") or ""),
        ]
        if part
    ) or "--"


def _workflow_preflight(
    workflows: list[dict[str, Any]],
    parameter_authority: dict[str, Any],
    ledger_evidence: dict[str, Any],
    readiness_matrix: dict[str, Any],
    verification_runner: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        _preflight_workflow_row(
            workflows,
            parameter_authority,
            ledger_evidence,
            readiness_matrix,
            "research_backtest",
            "Research backtest",
            "research",
            "Run",
        ),
        _preflight_workflow_row(
            workflows,
            parameter_authority,
            ledger_evidence,
            readiness_matrix,
            "signal_snapshot",
            "Signal snapshot",
            "advisory_signal",
            "Run",
        ),
        _preflight_workflow_row(
            workflows,
            parameter_authority,
            ledger_evidence,
            readiness_matrix,
            "paper_simulation",
            "Paper simulation",
            "paper_simulation",
            "Run",
        ),
        _preflight_verification_row(verification_runner, ledger_evidence),
        _preflight_live_row(),
    ]
    runnable_count = sum(1 for row in rows if row["runnable"])
    blocked_count = sum(1 for row in rows if row["status"] == "blocked")
    review_count = sum(1 for row in rows if _preflight_row_needs_review(row))
    next_runnable = next((row for row in rows if row["runnable"]), {})
    return {
        "stage": "gui_workflow_preflight",
        "summary": {
            "status": "review" if review_count else "ready",
            "runnable_count": runnable_count,
            "blocked_count": blocked_count,
            "review_count": review_count,
            "tracked_workflows": len(rows),
            "next_action": (
                f"Run {next_runnable.get('label', 'workflow')} after preflight review."
                if next_runnable
                else "Review preflight blockers."
            ),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": rows,
        "safety": _verification_runner_safety(),
    }


def _preflight_workflow_row(
    workflows: list[dict[str, Any]],
    parameter_authority: dict[str, Any],
    ledger_evidence: dict[str, Any],
    readiness_matrix: dict[str, Any],
    workflow_id: str,
    label: str,
    mode: str,
    button_label: str,
) -> dict[str, Any]:
    workflow = _workflow_by_id(workflows, workflow_id) or {}
    authority = _parameter_authority_row(parameter_authority, workflow_id)
    ledger = _ledger_evidence_by_id(ledger_evidence, workflow_id)
    readiness = _readiness_row_by_id(readiness_matrix, workflow_id)
    readiness_status = str(readiness.get("status") or "ready")
    status = "gate_controlled" if workflow_id == "paper_simulation" and readiness_status != "ready" else "ready_to_run"
    checks = [
        _preflight_check(
            "parameter_authority",
            "Parameter authority",
            "passed" if authority else "missing",
            authority.get("canonical_summary", "") if authority else "No canonical workflow request found.",
        ),
        _preflight_check(
            "execution_boundary",
            "Execution boundary",
            "passed",
            "Local research, advisory signal, or paper simulation only; no broker/account/order side effects.",
        ),
        _preflight_check(
            "readiness",
            "Mode readiness",
            readiness_status if readiness_status else "ready",
            readiness.get("evidence") or readiness.get("guardrail") or "Readiness matrix row is available.",
        ),
        _preflight_check(
            "server_receipt",
            "Server receipt",
            "current" if ledger.get("freshness") == "current" else "refresh_after_run",
            ledger.get("next_action") or "Run this workflow to refresh server-side evidence.",
        ),
    ]
    return {
        "workflow_id": workflow_id,
        "label": label,
        "mode": mode,
        "status": status,
        "runnable": bool(workflow.get("endpoint")),
        "endpoint": str(workflow.get("endpoint") or ""),
        "command": str(workflow.get("command") or ""),
        "button_label": button_label,
        "reason": readiness.get("guardrail") or SAFETY_NOTICE,
        "checks": checks,
        "permissions": _preflight_permissions(
            research_api=workflow_id in {"research_backtest", "signal_snapshot"},
            paper_simulation=workflow_id == "paper_simulation",
        ),
        "paper_only": True,
        "live_trading_allowed": False,
        "safety": SAFETY_NOTICE,
    }


def _preflight_verification_row(verification_runner: dict[str, Any], ledger_evidence: dict[str, Any]) -> dict[str, Any]:
    endpoint = _verification_preflight_endpoint(verification_runner, "gui_compile")
    ledger = _ledger_evidence_by_id(ledger_evidence, "verification_runner")
    allowed = "gui_compile" in verification_runner.get("summary", {}).get("allowed_gate_ids", [])
    return {
        "workflow_id": "verification_runner",
        "label": "Verification runner",
        "mode": "local_verification",
        "status": "ready_to_run" if allowed else "blocked",
        "runnable": bool(endpoint and allowed),
        "endpoint": endpoint,
        "command": f"GET {endpoint}" if endpoint else "",
        "button_label": "Run",
        "reason": "Allowlisted local verification gates only.",
        "checks": [
            _preflight_check(
                "allowlist",
                "Gate allowlist",
                "passed" if allowed else "blocked",
                "gui_compile is allowlisted for browser-triggered local verification."
                if allowed
                else "gui_compile is not in the verification runner allowlist.",
            ),
            _preflight_check(
                "execution_boundary",
                "Execution boundary",
                "passed",
                "Local compile/project/sync audit commands only; no broker/account/order side effects.",
            ),
            _preflight_check(
                "server_receipt",
                "Server receipt",
                "current" if ledger.get("freshness") == "current" else "refresh_after_run",
                ledger.get("next_action") or "Run gui_compile to refresh verification evidence.",
            ),
        ],
        "permissions": _preflight_permissions(research_api=False, paper_simulation=False),
        "paper_only": True,
        "live_trading_allowed": False,
        "safety": SAFETY_NOTICE,
    }


def _preflight_live_row() -> dict[str, Any]:
    return {
        "workflow_id": "live_trading",
        "label": "Live trading",
        "mode": "live_trading",
        "status": "blocked",
        "runnable": False,
        "endpoint": "",
        "command": "blocked by research-to-paper boundary",
        "button_label": "",
        "reason": SAFETY_NOTICE,
        "checks": [
            _preflight_check("live_boundary", "Live boundary", "blocked", SAFETY_NOTICE),
            _preflight_check("broker_connection", "Broker connection", "blocked", "No broker connection is allowed."),
            _preflight_check("order_placement", "Order placement", "blocked", "No order placement is allowed."),
        ],
        "permissions": _preflight_permissions(research_api=False, paper_simulation=False),
        "paper_only": True,
        "live_trading_allowed": False,
        "safety": SAFETY_NOTICE,
    }


def _preflight_check(check_id: str, label: str, status: str, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "evidence": evidence,
    }


def _preflight_row_needs_review(row: dict[str, Any]) -> bool:
    if row.get("workflow_id") == "live_trading":
        return False
    if row.get("status") in {"gate_controlled", "blocked"}:
        return True
    clean_statuses = {"passed", "current", "ready"}
    return any(
        isinstance(check, dict) and check.get("status") not in clean_statuses
        for check in row.get("checks", [])
    )


def _verification_preflight_endpoint(verification_runner: dict[str, Any], gate_id: str) -> str:
    command_or_endpoint = _verification_endpoint(verification_runner, gate_id)
    if command_or_endpoint.startswith("GET "):
        return command_or_endpoint.removeprefix("GET ").strip()
    return command_or_endpoint if command_or_endpoint.startswith("/api/") else ""


def _preflight_permissions(*, research_api: bool, paper_simulation: bool) -> dict[str, Any]:
    return {
        "research_api_allowed": research_api,
        "paper_simulation_allowed": paper_simulation,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _parameter_authority_row(parameter_authority: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    for row in parameter_authority.get("rows", []) if isinstance(parameter_authority, dict) else []:
        if isinstance(row, dict) and row.get("workflow_id") == workflow_id:
            return row
    return {}


def _ledger_evidence_by_id(ledger_evidence: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    for row in ledger_evidence.get("rows", []) if isinstance(ledger_evidence, dict) else []:
        if isinstance(row, dict) and row.get("workflow_id") == workflow_id:
            return row
    return {}


def _readiness_row_by_id(readiness_matrix: dict[str, Any], mode_id: str) -> dict[str, Any]:
    for row in readiness_matrix.get("rows", []) if isinstance(readiness_matrix, dict) else []:
        if isinstance(row, dict) and row.get("mode_id") == mode_id:
            return row
    return {}


def _workflow_endpoint_from_query(path: str, query: dict[str, Any]) -> str:
    return f"{path}?{urlencode([(key, _query_value(value)) for key, value in query.items()])}"


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_query_value(item) for item in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if value is None:
        return ""
    return str(value)


def _factor_windows_list(value: Any) -> list[int]:
    if isinstance(value, (list, tuple)):
        return [int(item) for item in value]
    return [int(part.strip()) for part in str(value or "").split(",") if part.strip()]


def _optional_number(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _run_queue(workflows: list[dict[str, Any]]) -> dict[str, Any]:
    active = _workflow_by_id(workflows, "research_backtest")
    pending = [
        _workflow_by_id(workflows, "signal_snapshot"),
        _workflow_by_id(workflows, "paper_simulation"),
        _workflow_by_id(workflows, "project_audit"),
    ]
    pending = [item for item in pending if item]
    blocked = [
        {
            "workflow_id": "live_trading",
            "label": "Live trading handoff",
            "status": "blocked",
            "reason": "Research-to-paper boundary is active; broker/account/order actions are disabled.",
        }
    ]
    return {
        "stage": "gui_run_queue",
        "active": {
            "workflow_id": active["workflow_id"] if active else "none",
            "label": active["label"] if active else "No active workflow",
            "status": "ready_to_run",
            "mode": active["mode"] if active else "local",
            "command": active["command"] if active else "",
            "safety": active["safety"] if active else SAFETY_NOTICE,
        },
        "summary": {
            "active": 1 if active else 0,
            "pending": len(pending),
            "blocked": len(blocked),
            "completed": 0,
        },
        "pending": [
            {
                "workflow_id": item["workflow_id"],
                "label": item["label"],
                "status": "queued",
                "mode": item["mode"],
                "command": item["command"],
                "safety": item["safety"],
            }
            for item in pending
        ],
        "blocked": blocked,
    }


def _active_operation_spec() -> dict[str, Any]:
    supported_workflows = [
        "research_backtest",
        "signal_snapshot",
        "paper_simulation",
        "verification_runner",
    ]
    return {
        "stage": "gui_active_operation",
        "summary": {
            "status": "browser_managed",
            "active": False,
            "supported_workflow_ids": supported_workflows,
            "state_source": "browser_runtime",
            "receipt_source": "browser localStorage + API receipts",
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "next_action": "The browser marks an operation running before calling a workflow API and keeps the latest receipt visible after completion.",
        },
        "rows": [
            {
                "check_id": "current_browser_operation",
                "label": "Current browser operation",
                "status": "waiting",
                "source": "state.activeOperation",
                "evidence": "Updated immediately when the operator starts research, signal, paper, or verification work from the GUI.",
            },
            {
                "check_id": "last_browser_receipt",
                "label": "Last browser receipt",
                "status": "waiting",
                "source": "run_history/execution_receipts/verification_result",
                "evidence": "Completed operations stay visible with status, timing, request parameters, metrics, or verification return code.",
            },
            {
                "check_id": "safe_boundary",
                "label": "Safe boundary",
                "status": "blocked_live",
                "source": "safety",
                "evidence": SAFETY_NOTICE,
            },
        ],
    }


def _workflow_by_id(workflows: list[dict[str, Any]], workflow_id: str) -> dict[str, Any] | None:
    for workflow in workflows:
        if workflow.get("workflow_id") == workflow_id:
            return workflow
    return None


def _trade_mode_control(workflows: list[dict[str, Any]]) -> dict[str, Any]:
    research = _workflow_by_id(workflows, "research_backtest") or {}
    paper = _workflow_by_id(workflows, "paper_simulation") or {}

    def permissions(*, research_api: bool = False, paper_simulation: bool = False) -> dict[str, Any]:
        return {
            "research_api_allowed": research_api,
            "paper_simulation_allowed": paper_simulation,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        }

    rows = [
        {
            "mode_id": "research",
            "label": "Research backtest",
            "status": "ready",
            "entrypoint": research.get("command", "GET /api/research"),
            "scope": "Local factor and portfolio research on configured data.",
            "permissions": permissions(research_api=True),
            "guardrail": "Computes metrics only; no broker, account, or order side effects.",
            "next_action": research.get("command", ""),
        },
        {
            "mode_id": "paper_simulation",
            "label": "Paper simulation",
            "status": "gate_controlled",
            "entrypoint": paper.get("command", "GET /api/paper"),
            "scope": "Local simulated fills, positions, equity, and guard events.",
            "permissions": permissions(research_api=True, paper_simulation=True),
            "guardrail": "Simulation output is local evidence; promotion gates still decide operator use.",
            "next_action": paper.get("command", ""),
        },
        {
            "mode_id": "live_trading",
            "label": "Live trading",
            "status": "blocked",
            "entrypoint": "blocked by research-to-paper boundary",
            "scope": "Broker/account/order side effects.",
            "permissions": permissions(),
            "guardrail": SAFETY_NOTICE,
            "next_action": "Manual architecture and safety work required before any live capability exists.",
        },
    ]
    return {
        "stage": "gui_trade_mode_control",
        "summary": {
            "default_mode": "research",
            "mode_count": len(rows),
            "research_available": True,
            "paper_simulation_available": True,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "next_action": "Use research or paper simulation endpoints; live trading remains blocked.",
        },
        "rows": rows,
        "safety": {
            "notice": SAFETY_NOTICE,
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
    }


def _verification_gates() -> list[dict[str, Any]]:
    return [
        {
            "gate_id": "gui_unit_tests",
            "label": "GUI unit tests",
            "command": "python -m unittest -v tests.unit.test_gui",
            "status": "required_before_push",
            "mode": "local",
            "evidence": "The GUI unit test suite should pass before publishing GUI changes.",
        },
        {
            "gate_id": "project_audit",
            "label": "Project audit",
            "command": "python scripts\\run_project_audit.py --json",
            "status": "required_before_push",
            "mode": "local",
            "evidence": "Audit must report safety.passes=true and no forbidden token/data/broker hits.",
        },
        {
            "gate_id": "gui_compile",
            "label": "GUI compile check",
            "command": "python -m compileall -q src\\quant_robot\\gui",
            "status": "required_before_push",
            "mode": "local",
            "evidence": "Python GUI modules compile without syntax errors.",
        },
        {
            "gate_id": "sync_audit",
            "label": "Safe sync audit",
            "command": "python scripts\\sync_project.py --machine office_desktop --task factor_review",
            "status": "required_before_push",
            "mode": "local",
            "evidence": "Changed paths must be syncable with no branch discovery or safety blockers.",
        },
        {
            "gate_id": "local_startup_smoke",
            "label": "Local startup smoke",
            "command": "python scripts\\run_gui.py --host 127.0.0.1 --port 8765",
            "status": "required_for_operator_use",
            "mode": "local",
            "evidence": "Local /api/control/status returns stage=gui_control_center.",
        },
        {
            "gate_id": "browser_desktop_smoke",
            "label": "Desktop browser smoke",
            "command": "Browser check http://127.0.0.1:8765/",
            "status": "required_for_ui_change",
            "mode": "local",
            "evidence": "Run queue and verification gates render with no horizontal overflow or console errors.",
        },
        {
            "gate_id": "browser_mobile_smoke",
            "label": "Mobile browser smoke",
            "command": "Browser check 390x844 http://127.0.0.1:8765/",
            "status": "required_for_ui_change",
            "mode": "local",
            "evidence": "Critical control center blocks remain visible and responsive on mobile.",
        },
    ]


def build_verification_runner_snapshot(verification_gates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    gates = verification_gates if verification_gates is not None else _verification_gates()
    gate_by_id = {str(gate.get("gate_id", "")): gate for gate in gates}
    rows: list[dict[str, Any]] = []
    for gate_id in VERIFICATION_RUNNER_GATE_IDS:
        gate = gate_by_id.get(gate_id)
        if not gate:
            continue
        rows.append(
            {
                "gate_id": gate_id,
                "label": gate.get("label", gate_id),
                "command": gate.get("command", ""),
                "endpoint": f"/api/control/verification?gate_id={gate_id}",
                "mode": "local",
                "status": "ready_to_run",
                "allowed": True,
                "timeout_seconds": VERIFICATION_RUNNER_TIMEOUT_SECONDS.get(gate_id, 120),
                "safety": "allowlisted local verification only; no broker, account, order, or live-trading side effects",
            }
        )
    return {
        "stage": "gui_verification_runner",
        "summary": {
            "allowed": len(rows),
            "allowed_gate_ids": [row["gate_id"] for row in rows],
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "next_action": "Run allowlisted verification gates locally and inspect the returned receipt before publishing.",
        },
        "rows": rows,
    }


def run_verification_gate(
    gate_id: str,
    repo_root: str | Path | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    runner = build_verification_runner_snapshot()
    row_by_id = {str(row.get("gate_id", "")): row for row in runner.get("rows", [])}
    row = row_by_id.get(gate_id)
    command_args = _verification_runner_command_args(gate_id)
    safety = _verification_runner_safety()
    if row is None or command_args is None:
        return {
            "stage": "gui_verification_result",
            "gate_id": gate_id,
            "status": "blocked",
            "returncode": None,
            "command": "",
            "duration_seconds": 0.0,
            "stdout_tail": "",
            "stderr_tail": "Gate is not registered in the GUI allowlist.",
            "started_at": "",
            "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "safety": safety,
        }

    timeout_seconds = timeout if timeout is not None else int(row.get("timeout_seconds", 120))
    timeout_seconds = max(1, min(int(timeout_seconds), 300))
    started = datetime.now(UTC)
    try:
        completed = subprocess.run(
            command_args,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        finished = datetime.now(UTC)
        return {
            "stage": "gui_verification_result",
            "gate_id": gate_id,
            "status": "timeout",
            "returncode": None,
            "command": row.get("command", ""),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "stdout_tail": _tail_text(exc.stdout),
            "stderr_tail": _tail_text(exc.stderr) or f"Timed out after {timeout_seconds} seconds.",
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "safety": safety,
        }
    except OSError as exc:
        finished = datetime.now(UTC)
        return {
            "stage": "gui_verification_result",
            "gate_id": gate_id,
            "status": "failed",
            "returncode": None,
            "command": row.get("command", ""),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "stdout_tail": "",
            "stderr_tail": _tail_text(str(exc)),
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "safety": safety,
        }

    finished = datetime.now(UTC)
    return {
        "stage": "gui_verification_result",
        "gate_id": gate_id,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "command": row.get("command", ""),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "stdout_tail": _tail_text(completed.stdout),
        "stderr_tail": _tail_text(completed.stderr),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "safety": safety,
    }


def _verification_runner_command_args(gate_id: str) -> list[str] | None:
    commands = {
        "gui_compile": [sys.executable, "-m", "compileall", "-q", "src\\quant_robot\\gui"],
        "project_audit": [sys.executable, "scripts\\run_project_audit.py", "--json"],
        "sync_audit": [
            sys.executable,
            "scripts\\sync_project.py",
            "--machine",
            "office_desktop",
            "--task",
            "factor_review",
        ],
    }
    return commands.get(gate_id)


def _verification_runner_safety() -> dict[str, Any]:
    return {
        "notice": SAFETY_NOTICE,
        "paper_only": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _tail_text(value: Any, max_chars: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    return text[-max_chars:]


def _operator_checklist(verification_gates: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    required_gate_count = sum(1 for gate in verification_gates if str(gate.get("status", "")).startswith("required"))
    missing_artifacts = [item for item in artifacts if item["status"] != "present"]
    items = [
        {
            "check_id": "research_context",
            "label": "CN_ETF research context",
            "status": "ready",
            "detail": "Current control-center defaults target CN_ETF local processed bars.",
        },
        {
            "check_id": "verification_pack",
            "label": "Verification pack before push",
            "status": "required",
            "detail": f"{required_gate_count} local verification gates must be rerun before publishing GUI changes.",
        },
        {
            "check_id": "artifact_visibility",
            "label": "Local artifact visibility",
            "status": "ready" if not missing_artifacts else "required",
            "detail": "Tracked GUI artifact links are present." if not missing_artifacts else f"{len(missing_artifacts)} local artifact links are missing.",
        },
        {
            "check_id": "paper_boundary",
            "label": "Paper simulation boundary",
            "status": "required",
            "detail": "Paper workflows are local simulations only; promotion gates must pass before operator use.",
        },
        {
            "check_id": "startup_smoke",
            "label": "Local startup smoke",
            "status": "required",
            "detail": "The local GUI server and /api/control/status must respond before operator use.",
        },
        {
            "check_id": "live_boundary",
            "label": "Live trading boundary",
            "status": "blocked",
            "detail": "Broker connection, account reads, order placement, and live trading remain disabled.",
        },
        {
            "check_id": "audit_cadence",
            "label": "5h GUI audit cadence",
            "status": "ready",
            "detail": "A recurring GUI audit should score the console and feed the next optimization round.",
        },
    ]
    return {
        "stage": "operator_checklist",
        "summary": {
            "research_ready": True,
            "paper_ready": False,
            "live_ready": False,
            "ready": sum(1 for item in items if item["status"] == "ready"),
            "required": sum(1 for item in items if item["status"] == "required"),
            "blocked": sum(1 for item in items if item["status"] == "blocked"),
        },
        "items": items,
    }


def _execution_plan(workflows: list[dict[str, Any]], verification_gates: list[dict[str, Any]]) -> dict[str, Any]:
    verification_command = verification_gates[0]["command"] if verification_gates else "python -m unittest -v tests.unit.test_gui"
    steps = [
        {
            "step_id": "context_gate",
            "label": "Confirm workstation and branch context",
            "status": "done",
            "detail": "office_desktop / factor_review / codex GUI task branch.",
            "command": "python scripts\\sync_project.py --machine office_desktop --task factor_review",
        },
        {
            "step_id": "research_backtest",
            "label": "Run CN_ETF research backtest",
            "status": "active",
            "detail": "Use local processed-bars defaults and current factor settings.",
            "command": _workflow_command(workflows, "research_backtest"),
        },
        {
            "step_id": "signal_snapshot",
            "label": "Generate advisory signal snapshot",
            "status": "queued",
            "detail": "Create targets and rebalance plan with executable=false.",
            "command": _workflow_command(workflows, "signal_snapshot"),
        },
        {
            "step_id": "paper_simulation",
            "label": "Run local paper simulation",
            "status": "queued",
            "detail": "Simulated fills only; no broker, account, or order side effects.",
            "command": _workflow_command(workflows, "paper_simulation"),
        },
        {
            "step_id": "verification_pack",
            "label": "Run verification pack",
            "status": "queued",
            "detail": "GUI tests, project audit, compile check, sync audit, and browser smoke checks.",
            "command": verification_command,
        },
        {
            "step_id": "publish_branch",
            "label": "Commit and push GUI branch",
            "status": "queued",
            "detail": "Only source, tests, docs, and lightweight summaries are syncable.",
            "command": "git push origin codex/gui-control-center-mvp-20260627",
        },
        {
            "step_id": "live_handoff",
            "label": "Live trading handoff",
            "status": "blocked",
            "detail": SAFETY_NOTICE,
            "command": "blocked by research-to-paper boundary",
        },
    ]
    return {
        "stage": "execution_plan",
        "summary": {
            "active_step": "research_backtest",
            "queued": sum(1 for item in steps if item["status"] == "queued"),
            "blocked": sum(1 for item in steps if item["status"] == "blocked"),
            "done": sum(1 for item in steps if item["status"] == "done"),
        },
        "steps": steps,
    }


def _readiness_matrix(
    workflows: list[dict[str, Any]],
    verification_gates: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    required_gates = [gate for gate in verification_gates if str(gate.get("status", "")).startswith("required")]
    missing_artifacts = [artifact for artifact in artifacts if artifact["status"] != "present"]
    rows = [
        {
            "mode_id": "research_backtest",
            "label": "Research backtest",
            "status": "ready",
            "scope": "CN_ETF local research",
            "guardrail": "Local processed bars or demo fixtures; no broker/account/order access.",
            "next_action": _workflow_command(workflows, "research_backtest"),
            "evidence": "Backtest method, parameters, result slots, and verification pack are visible in Mission Control.",
        },
        {
            "mode_id": "signal_snapshot",
            "label": "Advisory signal snapshot",
            "status": "ready",
            "scope": "Advisory targets only",
            "guardrail": "Rebalance plans stay executable=false and do not route orders.",
            "next_action": _workflow_command(workflows, "signal_snapshot"),
            "evidence": "Signal workflow produces target weights and rebalance intent for operator review.",
        },
        {
            "mode_id": "paper_simulation",
            "label": "Paper simulation",
            "status": "requires_gates",
            "scope": "Local simulated fills",
            "guardrail": "Run promotion/readiness gates before operator use; generated data stays out of Git.",
            "next_action": _workflow_command(workflows, "paper_simulation"),
            "evidence": (
                f"{len(required_gates)} required gates tracked; "
                f"{len(missing_artifacts)} local artifact links currently missing."
            ),
        },
        {
            "mode_id": "live_trading",
            "label": "Live trading",
            "status": "blocked",
            "scope": "Broker/account/order side effects",
            "guardrail": SAFETY_NOTICE,
            "next_action": "Blocked by research-to-paper boundary",
            "evidence": "No broker connection, account reads, order placement, or live trading.",
        },
    ]
    return {
        "stage": "readiness_matrix",
        "summary": {
            "ready": sum(1 for row in rows if row["status"] == "ready"),
            "requires_gates": sum(1 for row in rows if row["status"] == "requires_gates"),
            "blocked": sum(1 for row in rows if row["status"] == "blocked"),
            "paper_ready": False,
            "live_ready": False,
            "required_gate_count": len(required_gates),
            "missing_artifact_count": len(missing_artifacts),
        },
        "rows": rows,
    }


def _startup_health(
    workflows: list[dict[str, Any]],
    verification_gates: list[dict[str, Any]],
    audit_packets: dict[str, Any],
) -> dict[str, Any]:
    gate_by_id = {gate.get("gate_id"): gate for gate in verification_gates}
    packet_by_id = {row.get("packet_id"): row for row in audit_packets.get("rows", [])}
    browser_packet = packet_by_id.get("browser_smoke", {})
    browser_smoke_ready = browser_packet.get("status") == "present"
    local_startup_ready = browser_smoke_ready

    def gate_row(gate_id: str, *, ready: bool | None = None) -> dict[str, Any]:
        gate = gate_by_id.get(gate_id, {})
        row_ready = browser_smoke_ready if ready is None else ready
        return {
            "check_id": gate_id,
            "label": gate.get("label", gate_id),
            "status": "ready" if row_ready else "manual_required",
            "command": gate.get("command", ""),
            "evidence": gate.get("evidence", "Run the local startup verification gate."),
        }

    packet_present = browser_packet.get("status") == "present"
    rows = [
        gate_row("local_startup_smoke", ready=local_startup_ready),
        {
            "check_id": "control_status_api",
            "label": "Control status API",
            "status": "ready" if local_startup_ready else "manual_required",
            "command": "GET /api/control/status",
            "evidence": "Control API must return stage=gui_control_center.",
        },
        gate_row("browser_desktop_smoke"),
        gate_row("browser_mobile_smoke"),
        {
            "check_id": "browser_smoke_packet",
            "label": browser_packet.get("label", "GUI browser smoke evidence"),
            "status": "ready" if packet_present else "missing_required",
            "command": browser_packet.get(
                "command",
                "python scripts\\run_gui_browser_smoke.py --base-url http://127.0.0.1:8765 --output-dir data\\reports\\gui_browser_smoke",
            ),
            "evidence": (
                f"Evidence packet present at {browser_packet.get('markdown_path') or browser_packet.get('path', '')}."
                if packet_present
                else browser_packet.get("evidence", "GUI browser smoke evidence packet is missing.")
            ),
        },
    ]
    ready_count = sum(1 for row in rows if row["status"] == "ready")
    manual_required = sum(1 for row in rows if row["status"] == "manual_required")
    missing_required = sum(1 for row in rows if row["status"] == "missing_required")
    return {
        "stage": "gui_startup_health",
        "summary": {
            "status": "ready" if local_startup_ready and browser_smoke_ready and missing_required == 0 else "needs_evidence",
            "local_startup_ready": local_startup_ready,
            "browser_smoke_ready": browser_smoke_ready,
            "control_status_endpoint": "/api/control/status",
            "ready": ready_count,
            "manual_required": manual_required,
            "missing_required": missing_required,
            "next_action": (
                "Browser smoke evidence is current"
                if local_startup_ready and browser_smoke_ready and missing_required == 0
                else _workflow_command(workflows, "gui_start")
            ),
        },
        "rows": rows,
    }


def _backtest_provenance(backtest: dict[str, Any], workflows: list[dict[str, Any]]) -> dict[str, Any]:
    research_endpoint = _workflow_command(workflows, "research_backtest")
    paper_endpoint = _workflow_command(workflows, "paper_simulation")
    rows = [
        {
            "check_id": "data_scope",
            "label": "Data scope",
            "status": "ready",
            "detail": (
                f"{backtest['source']} reads {backtest['data_root']} for {backtest['market']} "
                f"from {backtest['start_date']} to {backtest['end_date']}."
            ),
        },
        {
            "check_id": "factor_inputs",
            "label": "Factor inputs",
            "status": "ready",
            "detail": (
                f"{backtest['factor']} with windows {backtest['factor_windows']} ranks top "
                f"{backtest['top_n']} assets against {backtest['benchmark_asset_id']}."
            ),
        },
        {
            "check_id": "execution_model",
            "label": "Execution model",
            "status": "ready",
            "detail": (
                f"Rebalance every {backtest['rebalance_interval']} bars with lag "
                f"{backtest['execution_lag']} and forward horizon {backtest['forward_horizon']}."
            ),
        },
        {
            "check_id": "cost_model",
            "label": "Cost and risk model",
            "status": "ready",
            "detail": (
                f"Cost {backtest['cost_bps']} bps, cash annual return {backtest['cash_annual_return']}, "
                f"regime filter={backtest['regime_filter']} lookback={backtest['regime_lookback']}, "
                f"max drawdown limit={backtest['max_drawdown_limit']}."
            ),
        },
        {
            "check_id": "output_metrics",
            "label": "Output metrics",
            "status": "ready",
            "detail": "Reports total return, annualized return, Sharpe, max drawdown, win rate, trades, benchmark relative return, and paper equity.",
        },
        {
            "check_id": "paper_live_boundary",
            "label": "Paper/live boundary",
            "status": "blocked_live",
            "detail": SAFETY_NOTICE,
        },
    ]
    return {
        "stage": "backtest_provenance",
        "summary": {
            "status": "ready",
            "market": backtest["market"],
            "factor": backtest["factor"],
            "data_root": backtest["data_root"],
            "research_endpoint": research_endpoint,
            "paper_endpoint": paper_endpoint,
            "paper_only": True,
            "live_trading_allowed": False,
            "row_count": len(rows),
        },
        "rows": rows,
    }


def _result_evidence(workflows: list[dict[str, Any]], execution_receipts: dict[str, Any]) -> dict[str, Any]:
    research_endpoint = _workflow_command(workflows, "research_backtest")
    signal_endpoint = _workflow_command(workflows, "signal_snapshot")
    paper_endpoint = _workflow_command(workflows, "paper_simulation")
    receipt_storage_key = execution_receipts.get("storage_key", "quant_robot.gui.execution_receipts.v1")
    rows = [
        {
            "check_id": "research_metrics",
            "label": "Research result metrics",
            "status": "awaiting_run",
            "source_workflow": "research_backtest",
            "command": research_endpoint,
            "metric_keys": ["total_return", "annualized_return", "sharpe", "max_drawdown", "win_rate", "trade_count"],
            "detail": "Run the research backtest to populate total return, annualized return, Sharpe, drawdown, win rate, and trade count.",
        },
        {
            "check_id": "benchmark_metrics",
            "label": "Benchmark comparison",
            "status": "awaiting_run",
            "source_workflow": "research_backtest",
            "command": research_endpoint,
            "metric_keys": ["benchmark_relative_return"],
            "detail": "Research results should include benchmark relative return against the configured CN_ETF benchmark.",
        },
        {
            "check_id": "signal_metrics",
            "label": "Signal snapshot metrics",
            "status": "awaiting_run",
            "source_workflow": "signal_snapshot",
            "command": signal_endpoint,
            "metric_keys": ["target_count", "target_gross_exposure", "rebalance_count"],
            "detail": "Run advisory signals to record target count, gross exposure, and non-executable rebalance intent.",
        },
        {
            "check_id": "paper_metrics",
            "label": "Paper simulation metrics",
            "status": "awaiting_run",
            "source_workflow": "paper_simulation",
            "command": paper_endpoint,
            "metric_keys": ["paper_ending_equity", "fill_count", "guard_event_count"],
            "detail": "Run local paper simulation to populate ending equity, simulated fills, and guard events.",
        },
        {
            "check_id": "execution_receipts",
            "label": "Execution receipts",
            "status": "browser_local",
            "source_workflow": "browser_receipts",
            "command": f"browser localStorage {receipt_storage_key}",
            "metric_keys": ["stored_receipts"],
            "detail": "The browser stores structured receipts for research, signal, and paper workflow runs.",
        },
        {
            "check_id": "live_boundary",
            "label": "Live result boundary",
            "status": "blocked_live",
            "source_workflow": "live_trading",
            "command": "blocked by research-to-paper boundary",
            "metric_keys": ["live_trading_allowed", "order_placement_allowed"],
            "detail": SAFETY_NOTICE,
        },
    ]
    return {
        "stage": "gui_result_evidence",
        "summary": {
            "status": "awaiting_workflow_run",
            "receipt_storage_key": receipt_storage_key,
            "research_endpoint": research_endpoint,
            "signal_endpoint": signal_endpoint,
            "paper_endpoint": paper_endpoint,
            "paper_only": True,
            "live_trading_allowed": False,
            "metric_groups": len(rows),
            "next_action": research_endpoint,
        },
        "rows": rows,
    }


def _ledger_evidence(
    workflows: list[dict[str, Any]],
    operation_ledger: dict[str, Any],
    verification_runner: dict[str, Any],
) -> dict[str, Any]:
    expected = [
        {
            "workflow_id": "research_backtest",
            "label": "Run research backtest",
            "current_command": _workflow_command(workflows, "research_backtest"),
            "current_request": _workflow_request(workflows, "research_backtest"),
        },
        {
            "workflow_id": "signal_snapshot",
            "label": "Generate advisory signal snapshot",
            "current_command": _workflow_command(workflows, "signal_snapshot"),
            "current_request": _workflow_request(workflows, "signal_snapshot"),
        },
        {
            "workflow_id": "paper_simulation",
            "label": "Run local paper simulation",
            "current_command": _workflow_command(workflows, "paper_simulation"),
            "current_request": _workflow_request(workflows, "paper_simulation"),
        },
        {
            "workflow_id": "verification_runner",
            "label": "Run verification gate gui_compile",
            "current_command": _verification_endpoint(verification_runner, "gui_compile"),
            "current_request": {"gate_id": "gui_compile"},
        },
    ]
    rows = [
        _ledger_evidence_row(item, operation_ledger)
        for item in expected
    ]
    current_receipts = sum(1 for row in rows if row["freshness"] == "current")
    missing_or_stale = sum(1 for row in rows if row["freshness"] in {"missing", "stale", "failed_current"})
    status = "current" if current_receipts == len(rows) else "partial" if current_receipts else "needs_current_receipts"
    next_row = next((row for row in rows if row["freshness"] != "current"), rows[0] if rows else {})
    return {
        "stage": "gui_ledger_evidence",
        "summary": {
            "status": status,
            "current_receipts": current_receipts,
            "missing_or_stale": missing_or_stale,
            "tracked_workflows": len(rows),
            "source": operation_ledger.get("summary", {}).get("path", "data/reports/gui_operation_ledger/gui_operation_ledger.json")
            if isinstance(operation_ledger, dict)
            else "data/reports/gui_operation_ledger/gui_operation_ledger.json",
            "next_action": next_row.get("next_action", "Run current GUI workflows to refresh server-side receipts."),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": rows,
        "safety": _verification_runner_safety(),
    }


def _ledger_evidence_row(expected: dict[str, Any], operation_ledger: dict[str, Any]) -> dict[str, Any]:
    workflow_id = expected["workflow_id"]
    rows = operation_ledger.get("rows", []) if isinstance(operation_ledger, dict) else []
    latest = next(
        (row for row in rows if isinstance(row, dict) and row.get("workflow_id") == workflow_id),
        None,
    )
    current_command = expected.get("current_command", "")
    current_request = expected.get("current_request", {})
    latest_command = str(latest.get("command") or "") if latest else ""
    latest_request = latest.get("request", {}) if latest and isinstance(latest.get("request"), dict) else {}
    matches_current_request = bool(latest_request) and _request_matches(latest_request, current_request)
    legacy_command_match = bool(latest) and _normalize_command(latest_command) == _normalize_command(current_command)
    matches_current_command = bool(latest) and (matches_current_request or (not latest_request and legacy_command_match))
    latest_status = str(latest.get("status") or "") if latest else ""
    if not latest:
        freshness = "missing"
        status = "awaiting_run"
    elif not matches_current_command:
        freshness = "stale"
        status = latest_status or "stale"
    elif latest_status in {"completed", "passed"}:
        freshness = "current"
        status = latest_status
    else:
        freshness = "failed_current"
        status = latest_status or "failed"
    return {
        "workflow_id": workflow_id,
        "label": expected.get("label", workflow_id),
        "freshness": freshness,
        "status": status,
        "matches_current_command": matches_current_command,
        "matches_current_request": matches_current_request,
        "current_command": current_command,
        "current_request": current_request,
        "latest_command": latest_command,
        "latest_request": latest_request,
        "latest_recorded_at": str(latest.get("recorded_at") or "") if latest else "",
        "latest_request_summary": str(latest.get("request_summary") or "") if latest else "",
        "latest_metric_summary": str(latest.get("metric_summary") or "") if latest else "",
        "source": "server_operation_ledger",
        "next_action": (
            "Covered by the latest server-side receipt."
            if freshness == "current"
            else f"{expected.get('label', workflow_id)} with the displayed current command."
        ),
    }


def _request_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not isinstance(actual, dict) or not isinstance(expected, dict) or not expected:
        return False
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value is None and key == "factor_name":
            actual_value = actual.get("factor")
        if _normalize_request_value(actual_value) != _normalize_request_value(expected_value):
            return False
    return True


def _normalize_request_value(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_normalize_request_value(item) for item in value)
    text = str(value).strip()
    if "," in text:
        return ",".join(_normalize_request_value(item) for item in text.split(","))
    lower = text.lower()
    if lower in {"true", "false"}:
        return lower
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:g}"


def _action_center(
    ledger_evidence: dict[str, Any],
    audit_iteration_plan: dict[str, Any],
    verification_runner: dict[str, Any],
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for row in ledger_evidence.get("rows", []) if isinstance(ledger_evidence, dict) else []:
        if not isinstance(row, dict) or row.get("freshness") == "current":
            continue
        action = _ledger_action(row)
        if action:
            actions.append(action)

    for row in audit_iteration_plan.get("rows", []) if isinstance(audit_iteration_plan, dict) else []:
        if not isinstance(row, dict) or row.get("status") == "blocked_expected":
            continue
        actions.append(
            {
                "action_id": f"audit_{row.get('action_id') or _slug(row.get('action') or 'review')}",
                "priority": str(row.get("priority") or "P2"),
                "label": str(row.get("action") or row.get("action_id") or "Review audit action"),
                "status": str(row.get("status") or "review"),
                "workflow_id": "audit_review",
                "runnable": False,
                "command": str(row.get("verification_command") or ""),
                "endpoint": "",
                "button_label": "",
                "reason": str(row.get("acceptance_evidence") or row.get("next_review") or ""),
                "source": "audit_iteration_plan",
                "safety": SAFETY_NOTICE,
            }
        )

    if not actions:
        actions.append(_verification_action(verification_runner, "gui_compile", priority="P2"))

    deduped = _dedupe_actions(actions)
    deduped.sort(key=lambda item: (_priority_rank(item.get("priority", "P3")), item.get("action_id", "")))
    runnable_count = sum(1 for item in deduped if item.get("runnable"))
    blocked_count = sum(1 for item in deduped if not item.get("runnable"))
    first = deduped[0] if deduped else {}
    return {
        "stage": "gui_action_center",
        "summary": {
            "status": "ready" if runnable_count else "review" if deduped else "blocked",
            "action_count": len(deduped),
            "runnable_actions": runnable_count,
            "blocked_actions": blocked_count,
            "next_action": first.get("label", "Review control center state."),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": deduped[:8],
        "safety": _verification_runner_safety(),
    }


def _ledger_action(row: dict[str, Any]) -> dict[str, Any] | None:
    workflow_id = str(row.get("workflow_id") or "")
    priority_by_workflow = {
        "research_backtest": "P1",
        "signal_snapshot": "P2",
        "paper_simulation": "P2",
        "verification_runner": "P2",
    }
    if workflow_id not in priority_by_workflow:
        return None
    command = str(row.get("current_command") or "")
    action_id = "run_verification_gui_compile" if workflow_id == "verification_runner" else f"refresh_{workflow_id}"
    return {
        "action_id": action_id,
        "priority": priority_by_workflow[workflow_id],
        "label": str(row.get("label") or workflow_id),
        "status": "ready_to_run",
        "workflow_id": workflow_id,
        "verification_gate": "gui_compile" if workflow_id == "verification_runner" else "",
        "runnable": True,
        "command": command,
        "endpoint": _command_endpoint(command),
        "button_label": "Run",
        "reason": f"Server receipt is {row.get('freshness', 'missing')}; refresh the current command before trusting metrics.",
        "source": "ledger_evidence",
        "safety": SAFETY_NOTICE,
    }


def _verification_action(verification_runner: dict[str, Any], gate_id: str, *, priority: str) -> dict[str, Any]:
    command = _verification_endpoint(verification_runner, gate_id)
    return {
        "action_id": f"run_verification_{gate_id}",
        "priority": priority,
        "label": f"Run verification gate {gate_id}",
        "status": "ready_to_run",
        "workflow_id": "verification_runner",
        "verification_gate": gate_id,
        "runnable": True,
        "command": command,
        "endpoint": _command_endpoint(command),
        "button_label": "Run",
        "reason": "Keep the local GUI verification evidence fresh before publishing.",
        "source": "verification_runner",
        "safety": "allowlisted local verification only; no broker, account, order, or live-trading side effects",
    }


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for action in actions:
        action_id = str(action.get("action_id") or "")
        if action_id in seen:
            continue
        seen.add(action_id)
        deduped.append(action)
    return deduped


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(str(priority), 9)


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "action"


def _command_endpoint(command: str) -> str:
    text = str(command or "").strip()
    if text.startswith("GET "):
        return text[4:]
    return ""


def _verification_endpoint(verification_runner: dict[str, Any], gate_id: str) -> str:
    rows = verification_runner.get("rows", []) if isinstance(verification_runner, dict) else []
    for row in rows:
        if isinstance(row, dict) and row.get("gate_id") == gate_id:
            endpoint = str(row.get("endpoint") or "")
            return f"GET {endpoint}" if endpoint else str(row.get("command") or "")
    return f"GET /api/control/verification?gate_id={gate_id}"


def _normalize_command(command: str) -> str:
    return str(command or "").strip().replace("\\", "/")


def _backtest_gate(workflows: list[dict[str, Any]], execution_receipts: dict[str, Any]) -> dict[str, Any]:
    research_command = _workflow_command(workflows, "research_backtest")
    paper_command = _workflow_command(workflows, "paper_simulation")
    receipt_storage_key = execution_receipts.get("storage_key", "quant_robot.gui.execution_receipts.v1")
    rows = [
        _gate_row(
            gate_id="sharpe",
            label="Sharpe",
            metric_key="sharpe",
            source="research_metrics",
            comparator=">=",
            threshold=1.0,
            value_type="decimal",
            command=research_command,
            evidence="Require Sharpe >= 1.0 before paper-observation consideration.",
        ),
        _gate_row(
            gate_id="total_return",
            label="Total return",
            metric_key="total_return",
            source="research_metrics",
            comparator=">=",
            threshold=0.0,
            value_type="percent",
            command=research_command,
            evidence="Require non-negative total return before paper-observation consideration.",
        ),
        _gate_row(
            gate_id="annualized_return",
            label="Annualized return",
            metric_key="annualized_return",
            source="research_metrics",
            comparator=">=",
            threshold=0.05,
            value_type="percent",
            command=research_command,
            evidence="Require annualized return >= 5% before paper-observation consideration.",
        ),
        _gate_row(
            gate_id="max_drawdown",
            label="Max drawdown",
            metric_key="max_drawdown",
            source="research_metrics",
            comparator=">=",
            threshold=-0.30,
            value_type="percent",
            command=research_command,
            evidence="Repo drawdown metrics are negative; require max_drawdown >= -30% before paper-observation consideration.",
        ),
        _gate_row(
            gate_id="win_rate",
            label="Win rate",
            metric_key="win_rate",
            source="research_metrics",
            comparator=">=",
            threshold=0.50,
            value_type="percent",
            command=research_command,
            evidence="Require win rate >= 50% before paper-observation consideration.",
        ),
        _gate_row(
            gate_id="trade_count",
            label="Trade count",
            metric_key="trade_count",
            source="research_metrics",
            comparator=">=",
            threshold=5,
            value_type="number",
            command=research_command,
            evidence="Require at least five simulated trades so one-off outcomes are not overread.",
        ),
        _gate_row(
            gate_id="benchmark_relative_return",
            label="Benchmark relative return",
            metric_key="benchmark_relative_return",
            source="benchmark_metrics",
            comparator=">=",
            threshold=0.0,
            value_type="percent",
            command=research_command,
            evidence="Require non-negative relative return versus the configured CN_ETF benchmark.",
        ),
        _gate_row(
            gate_id="paper_ending_equity",
            label="Paper ending equity",
            metric_key="paper_ending_equity",
            source="paper_metrics",
            comparator=">=",
            threshold=100000.0,
            value_type="currency",
            command=paper_command,
            evidence="Paper simulation should not finish below initial cash before observation handoff.",
            threshold_source="paper_request.initial_cash",
        ),
        _gate_row(
            gate_id="execution_receipts",
            label="Execution receipts",
            metric_key="stored_receipts",
            source="browser_receipts",
            comparator=">=",
            threshold=2,
            value_type="number",
            command=f"browser localStorage {receipt_storage_key}",
            evidence="Require current research and paper receipts that match the displayed workflow requests.",
            receipt_workflow_ids=["research_backtest", "paper_simulation"],
            requires_current_request=True,
        ),
        {
            "gate_id": "live_boundary",
            "label": "Live trading boundary",
            "metric_key": "live_trading_allowed",
            "source": "safety",
            "comparator": "==",
            "threshold": False,
            "value_type": "boolean",
            "severity": "hard_block",
            "status": "blocked_expected",
            "command": "blocked by research-to-paper boundary",
            "evidence": SAFETY_NOTICE,
        },
    ]
    return {
        "stage": "gui_backtest_gate",
        "summary": {
            "status": "awaiting_research_result",
            "paper_candidate_allowed": False,
            "live_trading_allowed": False,
            "risk_profile": "paper_observation_candidate",
            "receipt_storage_key": receipt_storage_key,
            "next_action": research_command,
            "threshold_count": len(rows),
            "max_drawdown_threshold": -0.30,
        },
        "rows": rows,
    }


def _gate_row(
    *,
    gate_id: str,
    label: str,
    metric_key: str,
    source: str,
    comparator: str,
    threshold: float,
    value_type: str,
    command: str,
    evidence: str,
    **extra: Any,
) -> dict[str, Any]:
    row = {
        "gate_id": gate_id,
        "label": label,
        "metric_key": metric_key,
        "source": source,
        "comparator": comparator,
        "threshold": threshold,
        "value_type": value_type,
        "severity": "paper_required",
        "status": "awaiting_metric",
        "command": command,
        "evidence": evidence,
    }
    row.update(extra)
    return row


def _workflow_trace(
    workflows: list[dict[str, Any]],
    run_queue: dict[str, Any],
    startup_health: dict[str, Any],
    result_evidence: dict[str, Any],
    release_readiness: dict[str, Any],
    execution_receipts: dict[str, Any],
) -> dict[str, Any]:
    active = run_queue.get("active", {}) if isinstance(run_queue.get("active"), dict) else {}
    active_workflow = str(active.get("workflow_id") or "research_backtest")
    active_status = str(active.get("status") or "ready_to_run")
    research_command = _workflow_command(workflows, "research_backtest")
    signal_command = _workflow_command(workflows, "signal_snapshot")
    paper_command = _workflow_command(workflows, "paper_simulation")
    receipt_storage_key = str(execution_receipts.get("storage_key") or "quant_robot.gui.execution_receipts.v1")
    startup_status = str(startup_health.get("summary", {}).get("status") or "needs_evidence")
    result_summary = result_evidence.get("summary", {}) if isinstance(result_evidence.get("summary"), dict) else {}
    release_rows = release_readiness.get("rows", []) if isinstance(release_readiness.get("rows"), list) else []
    verification_command = _release_row_command(
        release_rows,
        "gui_unit_tests",
        "python -m unittest -v tests.unit.test_gui",
    )
    audit_command = _release_row_command(
        release_rows,
        "independent_gui_audit_packet",
        "python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
    )
    rows = [
        {
            "trace_id": "startup_health",
            "label": "Confirm local GUI startup health",
            "status": "ready" if startup_status == "ready" else "required",
            "source_workflow": "gui_start",
            "command": "GET /api/control/status",
            "endpoint": "/api/control/status",
            "evidence": str(startup_health.get("summary", {}).get("next_action") or "Control status and browser smoke evidence gate operator use."),
            "next_action": "Use this health check before running research workflows.",
        },
        {
            "trace_id": "research_backtest",
            "label": "Run CN_ETF research backtest",
            "status": "active",
            "source_workflow": "research_backtest",
            "command": research_command,
            "endpoint": _workflow_endpoint(workflows, "research_backtest"),
            "evidence": "Research metrics populate total return, annualized return, Sharpe, drawdown, win rate, trade count, and benchmark comparison.",
            "next_action": "Run research before advisory signals and paper simulation.",
        },
        {
            "trace_id": "result_evidence",
            "label": "Record result evidence",
            "status": str(result_summary.get("status") or "awaiting_workflow_run"),
            "source_workflow": "browser_receipts",
            "command": f"browser localStorage {receipt_storage_key}",
            "endpoint": "localStorage",
            "evidence": "Structured receipts connect displayed metrics to the workflow that produced them.",
            "next_action": str(result_summary.get("next_action") or research_command),
        },
        {
            "trace_id": "signal_snapshot",
            "label": "Generate advisory signal snapshot",
            "status": "queued",
            "source_workflow": "signal_snapshot",
            "command": signal_command,
            "endpoint": _workflow_endpoint(workflows, "signal_snapshot"),
            "evidence": "Targets and rebalance intent stay advisory with executable=false.",
            "next_action": "Run after research metrics are refreshed.",
        },
        {
            "trace_id": "paper_simulation",
            "label": "Run local paper simulation",
            "status": "queued",
            "source_workflow": "paper_simulation",
            "command": paper_command,
            "endpoint": _workflow_endpoint(workflows, "paper_simulation"),
            "evidence": "Paper fills are local simulations only and do not touch broker, account, or order systems.",
            "next_action": "Run after research and advisory signal checks.",
        },
        {
            "trace_id": "verification_pack",
            "label": "Run verification pack",
            "status": "required",
            "source_workflow": "verification",
            "command": verification_command,
            "endpoint": "local command",
            "evidence": "GUI tests, compile checks, project audit, browser smoke, and sync audit must pass before publishing.",
            "next_action": "Run before committing or pushing GUI changes.",
        },
        {
            "trace_id": "audit_packet",
            "label": "Run independent GUI audit",
            "status": "packet_required",
            "source_workflow": "independent_gui_audit",
            "command": audit_command,
            "endpoint": "data/reports/gui_control_center_audit",
            "evidence": "The 5h GUI audit scores the console and feeds the next optimization round.",
            "next_action": "Re-run after each substantial GUI improvement.",
        },
        {
            "trace_id": "publish_branch",
            "label": "Publish syncable GUI branch",
            "status": "publish_ready",
            "source_workflow": "git_sync",
            "command": "python scripts\\sync_project.py --machine office_desktop --task factor_review --execute --push",
            "endpoint": "GitHub task branch",
            "evidence": "Only source, tests, docs, configs, and lightweight summaries are syncable.",
            "next_action": "Push after verification and sync audit are clean.",
        },
        {
            "trace_id": "live_boundary",
            "label": "Keep live trading blocked",
            "status": "blocked",
            "source_workflow": "live_trading",
            "command": "blocked by research-to-paper boundary",
            "endpoint": "none",
            "evidence": SAFETY_NOTICE,
            "next_action": "Do not connect broker, read accounts, place orders, or enable live trading from this GUI.",
        },
    ]
    return {
        "stage": "gui_workflow_trace",
        "summary": {
            "current_workflow": active_workflow,
            "current_status": active_status,
            "next_endpoint": _workflow_endpoint(workflows, active_workflow) or research_command,
            "evidence_storage_key": receipt_storage_key,
            "paper_only": bool(result_summary.get("paper_only", True)),
            "live_trading_allowed": False,
            "steps": len(rows),
            "queued": sum(1 for row in rows if row["status"] == "queued"),
            "required": sum(1 for row in rows if row["status"] in {"required", "packet_required"}),
            "blocked": sum(1 for row in rows if row["status"] == "blocked"),
        },
        "rows": rows,
    }


def _release_row_command(rows: list[dict[str, Any]], check_id: str, fallback: str) -> str:
    for row in rows:
        if row.get("check_id") == check_id and row.get("command"):
            return str(row["command"])
    return fallback


def _workflow_endpoint(workflows: list[dict[str, Any]], workflow_id: str) -> str:
    workflow = _workflow_by_id(workflows, workflow_id)
    return str(workflow.get("endpoint", "")) if workflow else ""


def _release_readiness(
    verification_gates: list[dict[str, Any]],
    audit_packets: dict[str, Any],
    readiness_matrix: dict[str, Any],
) -> dict[str, Any]:
    gate_by_id = {gate.get("gate_id"): gate for gate in verification_gates}
    packet_by_id = {row.get("packet_id"): row for row in audit_packets.get("rows", [])}

    def gate_row(gate_id: str, status: str = "manual_required") -> dict[str, Any]:
        gate = gate_by_id.get(gate_id, {})
        return {
            "check_id": gate_id,
            "label": gate.get("label", gate_id),
            "status": status,
            "command": gate.get("command", ""),
            "evidence": gate.get("evidence", "Run this local verification command before publishing GUI changes."),
        }

    def packet_row(packet_id: str, check_id: str) -> dict[str, Any]:
        packet = packet_by_id.get(packet_id, {})
        present = packet.get("status") == "present"
        return {
            "check_id": check_id,
            "label": packet.get("label", packet_id),
            "status": "passed_evidence" if present else "missing_required",
            "command": packet.get("command", ""),
            "evidence": (
                f"Evidence packet present at {packet.get('markdown_path') or packet.get('path', '')}."
                if present
                else packet.get("evidence", "Required evidence packet is missing.")
            ),
        }

    live_row = next(
        (row for row in readiness_matrix.get("rows", []) if row.get("mode_id") == "live_trading"),
        {},
    )
    paper_row = next(
        (row for row in readiness_matrix.get("rows", []) if row.get("mode_id") == "paper_simulation"),
        {},
    )
    rows = [
        gate_row("gui_unit_tests"),
        gate_row("gui_compile"),
        gate_row("sync_audit"),
        packet_row("project_audit", "project_audit_packet"),
        packet_row("browser_smoke", "browser_smoke_packet"),
        packet_row("independent_gui_audit", "independent_gui_audit_packet"),
        {
            "check_id": "paper_boundary",
            "label": paper_row.get("label", "Paper simulation"),
            "status": paper_row.get("status", "requires_gates"),
            "command": paper_row.get("next_action", ""),
            "evidence": paper_row.get("guardrail", "Paper workflow requires local readiness gates."),
        },
        {
            "check_id": "live_boundary",
            "label": live_row.get("label", "Live trading"),
            "status": "blocked_expected",
            "command": "blocked by research-to-paper boundary",
            "evidence": live_row.get("guardrail", SAFETY_NOTICE),
        },
    ]
    manual_required = sum(1 for row in rows if row["status"] == "manual_required")
    missing_required = sum(1 for row in rows if row["status"] == "missing_required")
    passed_evidence = sum(1 for row in rows if row["status"] == "passed_evidence")
    blocked_expected = sum(1 for row in rows if row["status"] == "blocked_expected")
    return {
        "stage": "gui_release_readiness",
        "summary": {
            "evidence_ready": missing_required == 0,
            "push_ready": manual_required == 0 and missing_required == 0,
            "paper_ready": bool(readiness_matrix.get("summary", {}).get("paper_ready")),
            "live_ready": False,
            "manual_required": manual_required,
            "missing_required": missing_required,
            "passed_evidence": passed_evidence,
            "blocked_expected": blocked_expected,
            "next_action": "Run manual verification pack" if manual_required else "Review release evidence",
        },
        "rows": rows,
    }


def _audit_scorecard(
    verification_gates: list[dict[str, Any]],
    readiness_matrix: dict[str, Any],
    artifacts: list[dict[str, Any]],
    audit_packets: dict[str, Any] | None = None,
    latest_gui_audit: dict[str, Any] | None = None,
    backtest_provenance: dict[str, Any] | None = None,
    result_evidence: dict[str, Any] | None = None,
    ledger_evidence: dict[str, Any] | None = None,
    process_monitor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required_gate_count = sum(1 for gate in verification_gates if str(gate.get("status", "")).startswith("required"))
    browser_gate_count = sum(1 for gate in verification_gates if "browser" in str(gate.get("gate_id", "")))
    missing_artifact_count = sum(1 for artifact in artifacts if artifact["status"] != "present")
    live_ready = bool(readiness_matrix.get("summary", {}).get("live_ready"))
    audit_packet_summary = (audit_packets or {}).get("summary", {})
    startup_health_ready = any(
        row.get("packet_id") == "browser_smoke" and row.get("status") == "present"
        for row in (audit_packets or {}).get("rows", [])
    )
    independent_audit_complete = bool(audit_packet_summary.get("independent_audit_complete"))
    required_missing_packets = int(audit_packet_summary.get("required_missing", 0) or 0)
    audit_feedback_loop_ready = independent_audit_complete and required_missing_packets == 0
    backtest_provenance_ready = (
        (backtest_provenance or {}).get("stage") == "backtest_provenance"
        and bool((backtest_provenance or {}).get("rows"))
    )
    result_evidence_ready = (
        (result_evidence or {}).get("stage") == "gui_result_evidence"
        and bool((result_evidence or {}).get("rows"))
    )
    ledger_evidence_ready = (
        (ledger_evidence or {}).get("stage") == "gui_ledger_evidence"
        and bool((ledger_evidence or {}).get("rows"))
    )
    ledger_evidence_summary = (
        (ledger_evidence or {}).get("summary", {})
        if isinstance((ledger_evidence or {}).get("summary"), dict)
        else {}
    )
    ledger_current_receipts = int(ledger_evidence_summary.get("current_receipts", 0) or 0)
    process_monitor_ready = (
        (process_monitor or {}).get("stage") == "gui_process_monitor"
        and bool((process_monitor or {}).get("rows"))
    )
    independent_audit_actions = _audit_packet_next_actions(latest_gui_audit) if latest_gui_audit else []
    categories = [
        {
            "category_id": "work_visibility",
            "label": "Work visibility",
            "score": 16,
            "max_score": 16,
            "status": "good",
            "evidence": "Run queue, operator checklist, execution plan, startup health, and readiness matrix are visible.",
        },
        {
            "category_id": "backtest_transparency",
            "label": "Backtest transparency",
            "score": 16 if backtest_provenance_ready else 15,
            "max_score": 16,
            "status": "good" if backtest_provenance_ready else "needs_provenance",
            "evidence": (
                "Control center exposes data source, market, factor, windows, TopN, cost, lag, method steps, and backtest provenance."
                if backtest_provenance_ready
                else "Control center needs a backtest provenance panel with source, endpoint, output, and boundary evidence."
            ),
        },
        {
            "category_id": "paper_live_boundary",
            "label": "Paper/live boundary",
            "score": 18 if not live_ready else 0,
            "max_score": 18,
            "status": "blocked_live",
            "evidence": SAFETY_NOTICE,
        },
        {
            "category_id": "runtime_observability",
            "label": "Runtime observability",
            "score": 10 if result_evidence_ready and process_monitor_ready else 9,
            "max_score": 10,
            "status": "good" if result_evidence_ready and process_monitor_ready else "needs_runtime_evidence",
            "evidence": (
                "Startup health, process monitor, result evidence, current work, local workflow commands, and browser-persisted run history are visible."
                if result_evidence_ready and process_monitor_ready
                else "Runtime view needs both local process monitor evidence and result evidence that maps metrics to workflow receipts."
            ),
        },
        {
            "category_id": "server_ledger_evidence",
            "label": "Server ledger evidence",
            "score": 4 if ledger_evidence_ready else 0,
            "max_score": 4,
            "status": "good" if ledger_evidence_ready else "missing_server_receipts",
            "evidence": (
                f"Server operation ledger checks current workflow receipts; current={ledger_current_receipts}."
                if ledger_evidence_ready
                else "Control center must expose server-side ledger freshness for research, signal, paper, and verification workflows."
            ),
        },
        {
            "category_id": "verification_coverage",
            "label": "Verification coverage",
            "score": 14 if startup_health_ready else 13,
            "max_score": 14,
            "status": "good" if startup_health_ready else "needs_browser_smoke",
            "evidence": (
                f"{required_gate_count} required gates tracked, including {browser_gate_count} browser smoke gates; "
                f"startup browser evidence is {'present' if startup_health_ready else 'missing'}."
            ),
        },
        {
            "category_id": "frontend_usability",
            "label": "Frontend usability",
            "score": 10 if missing_artifact_count == 0 else 8,
            "max_score": 10,
            "status": "good" if missing_artifact_count == 0 else "needs_artifacts",
            "evidence": f"{missing_artifact_count} tracked local artifact links are missing.",
        },
        {
            "category_id": "audit_feedback_loop",
            "label": "Audit feedback loop",
            "score": 12 if audit_feedback_loop_ready else 6 if independent_audit_complete else 0,
            "max_score": 12,
            "status": "good" if audit_feedback_loop_ready else "needs_audit_packets",
            "evidence": (
                "Independent audit, project audit, browser smoke evidence, and audit iteration plan are connected."
                if audit_feedback_loop_ready
                else f"{required_missing_packets} required audit evidence packets are missing from the feedback loop."
            ),
        },
    ]
    total_score = sum(item["score"] for item in categories)
    max_score = sum(item["max_score"] for item in categories)
    repair_queue = []
    if latest_gui_audit:
        actionable_audit_actions = [
            action
            for action in independent_audit_actions
            if action.get("action") != "Run independent 5h GUI audit"
            and not (
                audit_feedback_loop_ready
                and action.get("action") in RESOLVED_AUDIT_LOOP_ACTIONS
            )
        ]
        if actionable_audit_actions:
            first_action = actionable_audit_actions[0]
            repair_queue.append(
                {
                    "priority": first_action.get("priority", "P1"),
                    "action": first_action.get("action", "Apply independent GUI audit next actions"),
                    "reason": first_action.get("reason", "The latest independent audit packet is now the next optimization input."),
                }
            )
    else:
        repair_queue.append(
            {
                "priority": "P0",
                "action": "Run independent 5h GUI audit",
                "reason": "The visible score is a local self-check; the separate audit agent must still issue a scored review.",
            }
        )
    if not audit_feedback_loop_ready:
        repair_queue.append(
            {
                "priority": "P1",
                "action": "Attach audit findings to next optimization round",
                "reason": "The GUI should turn each 5h scorecard into visible fixes and acceptance gates.",
            }
        )
    if required_missing_packets:
        repair_queue.append(
            {
                "priority": "P2",
                "action": "Generate missing audit packets",
                "reason": f"{required_missing_packets} required audit packet links are missing.",
            }
        )
    if not ledger_evidence_ready:
        repair_queue.append(
            {
                "priority": "P1",
                "action": "Expose server ledger freshness",
                "reason": "The GUI must show whether server-side receipts match the current workflow commands.",
            }
        )
    repair_queue = _dedupe_audit_actions(repair_queue)
    return {
        "stage": "gui_audit_scorecard",
        "summary": {
            "local_self_check_score": total_score,
            "max_score": max_score,
            "cadence_hours": 5,
            "cadence_rounds": GUI_AUDIT_CADENCE_ROUNDS,
            "automation_id": "gui-5h",
            "independent_audit_complete": independent_audit_complete,
            "score_source": "independent_gui_audit_packet" if latest_gui_audit else "local_self_check_not_independent_audit",
            "independent_audit_score": latest_gui_audit.get("score") if latest_gui_audit else None,
            "independent_audit_verdict": latest_gui_audit.get("verdict") if latest_gui_audit else "",
            "required_gate_count": required_gate_count,
            "missing_artifact_count": missing_artifact_count,
            "required_missing_audit_packets": required_missing_packets,
            "ledger_current_receipts": ledger_current_receipts,
        },
        "categories": categories,
        "repair_queue": repair_queue,
        "next_audit": {
            "cadence": f"Every {GUI_AUDIT_CADENCE_ROUNDS} GUI rounds; fallback every 5 hours",
            "expected_output": "0-100 score, category scores, required fixes, and next optimization list.",
            "agent_role": "Independent GUI control center auditor",
        },
    }


def _load_gui_audit_packet(root: Path) -> dict[str, Any]:
    target = root / GUI_AUDIT_PACKET_PATH
    if not target.exists():
        return {
            "status": "packet_missing",
            "path": str(GUI_AUDIT_PACKET_PATH),
            "packet": None,
            "error": "",
        }
    try:
        packet = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "packet_invalid",
            "path": str(GUI_AUDIT_PACKET_PATH),
            "packet": None,
            "error": str(exc),
        }
    if not isinstance(packet, dict):
        return {
            "status": "packet_invalid",
            "path": str(GUI_AUDIT_PACKET_PATH),
            "packet": None,
            "error": "The GUI audit packet must be a JSON object.",
        }
    return {
        "status": "packet_present",
        "path": str(GUI_AUDIT_PACKET_PATH),
        "packet": packet,
        "error": "",
    }


def _audit_scheduler(root: Path, packet_source: dict[str, Any], operation_ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    automation = _load_automation_config(GUI_AUDIT_AUTOMATION_ID)
    automation_config = automation.get("config") if automation.get("status") == "present" else {}
    automation_status = str(automation_config.get("status") or automation.get("status") or "unknown").lower()
    cadence_hours = _rrule_cadence_hours(str(automation_config.get("rrule") or "")) or 5
    cadence_rounds = GUI_AUDIT_CADENCE_ROUNDS
    current_round = _current_gui_round(operation_ledger or {})
    rounds_until_next_audit = _rounds_until_next_audit(current_round, cadence_rounds)
    next_round_audit_due_status = (
        "due_now" if current_round > 0 and rounds_until_next_audit == 0 else "collecting_rounds"
    )
    round_report_required = next_round_audit_due_status == "due_now"
    packet = packet_source.get("packet") if packet_source.get("status") == "packet_present" else None
    generated_at = _audit_packet_generated_at(packet, root / GUI_AUDIT_PACKET_PATH)
    now = datetime.now(UTC)
    last_audit_age_hours = _age_hours(generated_at, now)
    next_due_at = generated_at + timedelta(hours=cadence_hours) if generated_at else None
    next_due_status = _next_due_status(
        automation_status,
        last_audit_age_hours,
        cadence_hours,
        packet_source.get("status") == "packet_present",
    )
    config_status = "ready" if automation_status == "active" else "missing" if automation_status == "missing" else "warn"
    packet_status = "ready" if packet_source.get("status") == "packet_present" else "missing"
    rows = [
        {
            "check_id": "automation_config",
            "label": "GUI audit heartbeat",
            "status": config_status,
            "value": (
                f"{str(automation_config.get('status', automation.get('status', 'unknown'))).upper()} / "
                f"{automation_config.get('kind', '--')} / {automation_config.get('rrule', '--')}"
            ),
            "evidence": str(automation.get("path") or "No local gui-5h automation.toml found."),
        },
        {
            "check_id": "round_cadence",
            "label": "Round audit cadence",
            "status": "required" if round_report_required else "ready",
            "value": (
                f"round {current_round} / every {cadence_rounds} rounds / "
                f"{rounds_until_next_audit} rounds until audit"
            ),
            "evidence": "Every five completed GUI rounds require an audit report and next flow plan before the next optimization cycle.",
        },
        {
            "check_id": "last_audit_packet",
            "label": "Latest independent audit",
            "status": packet_status,
            "value": _audit_packet_value(packet, generated_at),
            "evidence": str(packet_source.get("path") or GUI_AUDIT_PACKET_PATH),
        },
        {
            "check_id": "next_due",
            "label": "Next audit due",
            "status": "ready" if next_due_status == "on_schedule" else "required" if next_due_status == "due_now" else "warn",
            "value": _iso_text(next_due_at) if next_due_at else "--",
            "evidence": f"cadence={cadence_hours}h / age={_format_hours(last_audit_age_hours)} / status={next_due_status}",
        },
        {
            "check_id": "next_flow_plan",
            "label": "Audit report + next flow plan",
            "status": "required" if round_report_required else "ready",
            "value": (
                "audit report + next flow plan required"
                if round_report_required
                else "continue current plan until the next 5-round checkpoint"
            ),
            "evidence": "The checkpoint must summarize completed GUI work, audit score, issues, and the next process plan.",
        },
        {
            "check_id": "safety_boundary",
            "label": "Audit safety boundary",
            "status": "blocked_expected",
            "value": SAFETY_NOTICE,
            "evidence": "The audit may score and recommend fixes; it must not connect brokers, read accounts, place orders, or enable live trading.",
        },
    ]
    return {
        "stage": "gui_audit_scheduler",
        "summary": {
            "automation_id": GUI_AUDIT_AUTOMATION_ID,
            "status": automation_status if automation_status in {"active", "paused", "missing"} else "unknown",
            "automation_kind": str(automation_config.get("kind") or ""),
            "name": str(automation_config.get("name") or "GUI control center audit"),
            "rrule": str(automation_config.get("rrule") or ""),
            "cadence": f"Every {cadence_rounds} GUI rounds; fallback every {cadence_hours} hours",
            "cadence_hours": cadence_hours,
            "cadence_rounds": cadence_rounds,
            "current_round": current_round,
            "rounds_until_next_audit": rounds_until_next_audit,
            "next_round_audit_due_status": next_round_audit_due_status,
            "next_report_required": round_report_required,
            "next_flow_plan_required": round_report_required,
            "last_audit_generated_at": _iso_text(generated_at),
            "last_audit_age_hours": last_audit_age_hours,
            "last_audit_score": packet.get("score") if isinstance(packet, dict) else None,
            "last_audit_verdict": packet.get("verdict", "") if isinstance(packet, dict) else "",
            "next_due_at": _iso_text(next_due_at),
            "next_due_status": next_due_status,
            "config_status": automation.get("status", "unknown"),
            "target_thread_id": str(automation_config.get("target_thread_id") or ""),
            "live_trading_allowed": False,
            "next_action": (
                "Write the five-round audit report and next flow plan before continuing GUI optimization."
                if round_report_required
                else _audit_scheduler_next_action(automation_status, next_due_status)
            ),
        },
        "rows": rows,
    }


def _current_gui_round(operation_ledger: dict[str, Any]) -> int:
    summary = operation_ledger.get("summary", {}) if isinstance(operation_ledger, dict) else {}
    try:
        return max(0, int(summary.get("entry_count") or 0))
    except (TypeError, ValueError):
        return 0


def _rounds_until_next_audit(current_round: int, cadence_rounds: int) -> int:
    if cadence_rounds <= 0:
        return 0
    if current_round <= 0:
        return cadence_rounds
    remainder = current_round % cadence_rounds
    return 0 if remainder == 0 else cadence_rounds - remainder


def _load_automation_config(automation_id: str) -> dict[str, Any]:
    target = _codex_home() / "automations" / automation_id / "automation.toml"
    if not target.exists():
        return {"status": "missing", "path": str(target), "config": {}, "error": ""}
    try:
        config = tomllib.loads(target.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        return {"status": "invalid", "path": str(target), "config": {}, "error": str(exc)}
    return {"status": "present", "path": str(target), "config": config, "error": ""}


def _codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured) if configured else Path.home() / ".codex"


def _rrule_cadence_hours(rrule: str) -> int:
    parts = {
        item.split("=", 1)[0].upper(): item.split("=", 1)[1]
        for item in rrule.split(";")
        if "=" in item
    }
    interval = _int_or_none(parts.get("INTERVAL")) or 1
    freq = str(parts.get("FREQ", "")).upper()
    if freq == "HOURLY":
        return interval
    if freq == "DAILY":
        return interval * 24
    return 0


def _audit_packet_generated_at(packet: Any, path: Path) -> datetime | None:
    if isinstance(packet, dict):
        parsed = _parse_datetime(str(packet.get("generated_at") or ""))
        if parsed:
            return parsed
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_hours(started_at: datetime | None, now: datetime) -> float | None:
    if started_at is None:
        return None
    return round(max(0.0, (now - started_at).total_seconds() / 3600.0), 2)


def _next_due_status(
    automation_status: str,
    last_audit_age_hours: float | None,
    cadence_hours: int,
    packet_present: bool,
) -> str:
    if automation_status == "missing":
        return "automation_missing"
    if automation_status == "paused":
        return "paused"
    if not packet_present or last_audit_age_hours is None:
        return "audit_packet_missing"
    if cadence_hours <= 0:
        return "unknown_cadence"
    return "due_now" if last_audit_age_hours >= cadence_hours else "on_schedule"


def _audit_packet_value(packet: Any, generated_at: datetime | None) -> str:
    if not isinstance(packet, dict):
        return "No parseable GUI audit packet."
    return (
        f"{packet.get('score', '--')} / {packet.get('max_score', '--')} / "
        f"{packet.get('verdict', '--')} / {_iso_text(generated_at)}"
    )


def _audit_scheduler_next_action(automation_status: str, next_due_status: str) -> str:
    if automation_status == "missing":
        return "Create or restore the gui-5h heartbeat automation."
    if automation_status == "paused":
        return "Continue the 5-round audit cadence; resume gui-5h only as a time-based fallback."
    if next_due_status == "due_now":
        return "Run the independent GUI audit now and feed findings into the next optimization round."
    if next_due_status == "audit_packet_missing":
        return "Generate the independent GUI audit packet."
    return "Keep iterating; the 5h GUI audit cadence is visible."


def _iso_text(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _format_hours(value: float | None) -> str:
    return "--" if value is None else f"{value:.2f}h"


def _audit_feedback(packet_source: dict[str, Any], audit_packets: dict[str, Any]) -> dict[str, Any]:
    status = str(packet_source.get("status", "packet_missing"))
    packet = packet_source.get("packet") if status == "packet_present" else None
    required_missing = int((audit_packets.get("summary") or {}).get("required_missing", 0) or 0)
    source_path = str(packet_source.get("path") or GUI_AUDIT_PACKET_PATH)
    if isinstance(packet, dict):
        next_actions = _dedupe_audit_actions([
            action for action in _audit_packet_next_actions(packet) if action.get("action") != "Run independent 5h GUI audit"
        ])
        verdict = str(packet.get("verdict", ""))
        if not next_actions and verdict != "clear":
            next_actions = [
                {
                    "priority": "P2",
                    "action": "Review independent audit packet",
                    "reason": "The packet has no explicit next_actions; operator review should decide the next GUI improvement.",
                }
            ]
        return {
            "stage": "gui_audit_feedback",
            "status": "packet_present",
            "summary": {
                "source_path": source_path,
                "score": packet.get("score"),
                "max_score": packet.get("max_score"),
                "verdict": verdict,
                "generated_at": packet.get("generated_at", ""),
                "next_action_count": len(next_actions),
                "required_missing_audit_packets": required_missing,
            },
            "next_actions": next_actions[:6],
            "evidence": (
                "Latest independent GUI audit packet is clear; no repair actions are queued."
                if not next_actions and verdict == "clear"
                else "Latest independent GUI audit packet is feeding the next optimization round."
            ),
        }
    if status == "packet_invalid":
        next_actions = [
            {
                "priority": "P0",
                "action": "Regenerate independent 5h GUI audit",
                "reason": packet_source.get("error", "The current audit packet cannot be parsed."),
            }
        ]
    else:
        next_actions = [
            {
                "priority": "P0",
                "action": "Run independent 5h GUI audit",
                "reason": "No parseable independent audit packet is available for the feedback loop.",
                "command": "python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
            }
        ]
    return {
        "stage": "gui_audit_feedback",
        "status": status,
        "summary": {
            "source_path": source_path,
            "score": None,
            "max_score": None,
            "verdict": "",
            "generated_at": "",
            "next_action_count": len(next_actions),
            "required_missing_audit_packets": required_missing,
        },
        "next_actions": next_actions,
        "evidence": "Create a valid independent GUI audit packet before using audit feedback as optimization input.",
    }


def _audit_iteration_plan(
    audit_feedback: dict[str, Any],
    audit_scorecard: dict[str, Any],
    verification_gates: list[dict[str, Any]],
    readiness_matrix: dict[str, Any],
) -> dict[str, Any]:
    score_summary = audit_scorecard.get("summary", {})
    source = str(score_summary.get("score_source") or "local_self_check_not_independent_audit")
    feedback_status = str(audit_feedback.get("status") or "packet_missing")
    next_actions = [
        item for item in audit_feedback.get("next_actions", []) if isinstance(item, dict)
    ]
    rows: list[dict[str, Any]] = []
    for index, action in enumerate(next_actions[:6]):
        action_label = str(action.get("action") or "Review audit finding")
        reason = str(action.get("reason") or "The next GUI audit should confirm this finding has an operator-visible fix.")
        rows.append(
            {
                "action_id": _audit_action_id(action_label, index),
                "priority": str(action.get("priority") or ("P1" if index == 0 else "P2")),
                "action": action_label,
                "status": "queued" if feedback_status == "packet_present" else "blocked_missing_audit",
                "source": source,
                "acceptance_evidence": reason,
                "verification_command": _audit_iteration_verification_command(action_label, verification_gates),
                "next_review": "Re-run the independent 5h GUI audit after this action is implemented.",
            }
        )

    live_row = next(
        (row for row in readiness_matrix.get("rows", []) if row.get("mode_id") == "live_trading"),
        {},
    )
    rows.append(
        {
            "action_id": "live_boundary_guard",
            "priority": "P0",
            "action": "Keep live trading boundary blocked",
            "status": "blocked_expected",
            "source": "project_safety_policy",
            "acceptance_evidence": str(live_row.get("evidence") or live_row.get("guardrail") or SAFETY_NOTICE),
            "verification_command": _gate_command(verification_gates, "project_audit"),
            "next_review": "Every GUI audit must keep broker/account/order/live trading disabled.",
        }
    )
    active_actions = sum(1 for row in rows if row["status"] == "queued")
    blocked_expected = sum(1 for row in rows if row["status"] == "blocked_expected")
    return {
        "stage": "gui_audit_iteration_plan",
        "summary": {
            "source": source,
            "audit_score": score_summary.get("independent_audit_score")
            if source == "independent_gui_audit_packet"
            else score_summary.get("local_self_check_score"),
            "max_score": score_summary.get("max_score"),
            "verdict": score_summary.get("independent_audit_verdict", ""),
            "cadence_hours": score_summary.get("cadence_hours", 5),
            "active_actions": active_actions,
            "blocked_expected": blocked_expected,
            "next_action": rows[0]["action"] if rows else "Run independent 5h GUI audit",
        },
        "rows": rows,
    }


def _audit_action_id(action: str, index: int) -> str:
    lowered = action.strip().lower()
    chars = [char if char.isalnum() else "_" for char in lowered]
    slug = "_".join(part for part in "".join(chars).split("_") if part)
    return slug[:48] or f"audit_action_{index + 1}"


def _audit_iteration_verification_command(action: str, verification_gates: list[dict[str, Any]]) -> str:
    lowered = action.lower()
    if "packet" in lowered or "audit" in lowered:
        return "python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit"
    if "browser" in lowered or "visible" in lowered or "render" in lowered:
        return "Browser check http://127.0.0.1:8765/ and 390x844"
    return _gate_command(verification_gates, "gui_unit_tests")


def _gate_command(verification_gates: list[dict[str, Any]], gate_id: str) -> str:
    gate = next((item for item in verification_gates if item.get("gate_id") == gate_id), {})
    return str(gate.get("command") or "python -m unittest -v tests.unit.test_gui")


def _audit_packet_next_actions(packet: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not packet:
        return []
    rows = packet.get("next_actions", [])
    if not isinstance(rows, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(rows):
        default_priority = "P1" if index == 0 else "P2"
        if isinstance(item, dict):
            action = item.get("action") or item.get("name") or item.get("title") or "Review audit finding"
            reason = item.get("reason") or item.get("detail") or item.get("evidence") or ""
            normalized.append(
                {
                    "priority": str(item.get("priority") or default_priority),
                    "action": str(action),
                    "reason": str(reason),
                }
            )
        else:
            normalized.append(
                {
                    "priority": default_priority,
                    "action": str(item),
                    "reason": "Imported from the independent GUI audit packet.",
                }
            )
    return normalized


def _round_checkpoint_report(
    latest_gui_audit: dict[str, Any] | None,
    operation_ledger: dict[str, Any],
    audit_scheduler: dict[str, Any],
    audit_scorecard: dict[str, Any],
    audit_iteration_plan: dict[str, Any],
    verification_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    packet_report = latest_gui_audit.get("round_checkpoint_report") if isinstance(latest_gui_audit, dict) else None
    if isinstance(packet_report, dict) and packet_report.get("stage") == "gui_round_checkpoint_report":
        return _normalize_round_checkpoint_report(packet_report, audit_scheduler, verification_gates)
    return _live_round_checkpoint_report(operation_ledger, audit_scheduler, audit_scorecard, audit_iteration_plan, verification_gates)


def _normalize_round_checkpoint_report(
    report: dict[str, Any],
    audit_scheduler: dict[str, Any],
    verification_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(report)
    summary = dict(normalized.get("summary", {}))
    scheduler_summary = audit_scheduler.get("summary", {}) if isinstance(audit_scheduler, dict) else {}
    summary.setdefault("cadence_rounds", scheduler_summary.get("cadence_rounds", GUI_AUDIT_CADENCE_ROUNDS))
    summary.setdefault("current_round", scheduler_summary.get("current_round", 0))
    summary.setdefault("next_review_trigger", f"Every {summary.get('cadence_rounds', GUI_AUDIT_CADENCE_ROUNDS)} completed GUI rounds; fallback every 5 hours.")
    summary.setdefault("live_trading_allowed", False)
    normalized["summary"] = summary
    normalized["recent_work"] = [
        row for row in normalized.get("recent_work", []) if isinstance(row, dict)
    ][:5]
    flow_plan = dict(normalized.get("flow_plan", {}))
    flow_plan.setdefault("status", "ready")
    flow_plan.setdefault("next_steps", _default_round_next_steps())
    flow_plan.setdefault("verification_plan", _verification_plan_rows(verification_gates))
    flow_plan.setdefault("safety", SAFETY_NOTICE)
    normalized["flow_plan"] = flow_plan
    normalized.setdefault("safety", _verification_runner_safety())
    return normalized


def _live_round_checkpoint_report(
    operation_ledger: dict[str, Any],
    audit_scheduler: dict[str, Any],
    audit_scorecard: dict[str, Any],
    audit_iteration_plan: dict[str, Any],
    verification_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    ledger_summary = operation_ledger.get("summary", {}) if isinstance(operation_ledger, dict) else {}
    scheduler_summary = audit_scheduler.get("summary", {}) if isinstance(audit_scheduler, dict) else {}
    score_summary = audit_scorecard.get("summary", {}) if isinstance(audit_scorecard, dict) else {}
    recent_work = [
        _round_work_item(row)
        for row in (operation_ledger.get("rows", []) if isinstance(operation_ledger, dict) else [])[:5]
        if isinstance(row, dict)
    ]
    next_steps = _round_next_steps_from_iteration_plan(audit_iteration_plan) or _default_round_next_steps()
    cadence_rounds = int(scheduler_summary.get("cadence_rounds") or GUI_AUDIT_CADENCE_ROUNDS)
    current_round = int(scheduler_summary.get("current_round") or ledger_summary.get("entry_count") or 0)
    return {
        "stage": "gui_round_checkpoint_report",
        "summary": {
            "status": "live_preview",
            "current_round": current_round,
            "completed_rounds": len(recent_work),
            "cadence_rounds": cadence_rounds,
            "rounds_until_next_audit": scheduler_summary.get("rounds_until_next_audit"),
            "next_review_trigger": f"Every {cadence_rounds} completed GUI rounds; fallback every 5 hours.",
            "audit_score": score_summary.get("independent_audit_score") or score_summary.get("local_self_check_score"),
            "max_score": score_summary.get("max_score"),
            "verdict": score_summary.get("independent_audit_verdict", ""),
            "repair_action_count": len(audit_scorecard.get("repair_queue", [])) if isinstance(audit_scorecard, dict) else 0,
            "live_trading_allowed": False,
        },
        "recent_work": recent_work,
        "flow_plan": {
            "status": "ready",
            "next_steps": next_steps,
            "verification_plan": _verification_plan_rows(verification_gates),
            "safety": SAFETY_NOTICE,
        },
        "safety": _verification_runner_safety(),
    }


def _round_work_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": str(row.get("operation_id") or ""),
        "recorded_at": str(row.get("recorded_at") or ""),
        "workflow_id": str(row.get("workflow_id") or ""),
        "label": str(row.get("label") or row.get("workflow_id") or ""),
        "status": str(row.get("status") or ""),
        "request_summary": str(row.get("request_summary") or ""),
        "metric_summary": str(row.get("metric_summary") or ""),
        "command": str(row.get("command") or ""),
    }


def _round_next_steps_from_iteration_plan(audit_iteration_plan: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(audit_iteration_plan, dict):
        return []
    rows = [row for row in audit_iteration_plan.get("rows", []) if isinstance(row, dict)]
    active_rows = [row for row in rows if row.get("status") not in {"blocked_expected"}]
    return [
        {
            "priority": str(row.get("priority") or "P2"),
            "action": str(row.get("action") or row.get("action_id") or "Review audit action"),
            "reason": str(row.get("acceptance_evidence") or row.get("next_review") or ""),
            "verification": str(row.get("verification_command") or "python -m unittest -v tests.unit.test_gui"),
        }
        for row in active_rows[:5]
    ]


def _default_round_next_steps() -> list[dict[str, Any]]:
    return [
        {
            "priority": "P1",
            "action": "Continue the next GUI optimization round from the largest remaining operator blind spot.",
            "reason": "The latest audit has no active repair queue; keep improving workflow visibility and safety clarity.",
            "verification": "python -m unittest -v tests.unit.test_gui",
        },
        {
            "priority": "P2",
            "action": "Generate the next five-round checkpoint report after five more completed GUI rounds.",
            "reason": "The active goal requires an audit report and next flow plan every five rounds.",
            "verification": "python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
        },
    ]


def _verification_plan_rows(verification_gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "gate_id": str(item.get("gate_id") or ""),
            "label": str(item.get("label") or ""),
            "command": str(item.get("command") or ""),
        }
        for item in verification_gates[:5]
        if isinstance(item, dict)
    ]


def _dedupe_audit_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for row in rows:
        action = str(row.get("action", ""))
        if action in seen_actions:
            continue
        seen_actions.add(action)
        deduped.append(row)
    return deduped


def _audit_packets(root: Path) -> dict[str, Any]:
    rows = [
        _audit_packet_row(
            root,
            packet_id="independent_gui_audit",
            label="Independent five-round GUI audit",
            path=Path("data/reports/gui_control_center_audit/gui_control_center_audit.json"),
            markdown_path=Path("data/reports/gui_control_center_audit/gui_control_center_audit.md"),
            command="python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
            required=True,
            role="Independent GUI control center auditor",
            cadence=f"Every {GUI_AUDIT_CADENCE_ROUNDS} GUI rounds; fallback every 5 hours",
        ),
        _audit_packet_row(
            root,
            packet_id="project_audit",
            label="Project safety audit",
            path=Path("data/reports/project_audit/project_audit.json"),
            markdown_path=Path("data/reports/project_audit/project_audit.md"),
            command="python scripts\\run_project_audit.py --json",
            required=True,
            role="Repository safety gate",
            cadence="Before each GUI push",
        ),
        _audit_packet_row(
            root,
            packet_id="promotion_review_packet",
            label="Promotion review packet",
            path=Path("data/reports/promotion_review/promotion_review_packet.json"),
            markdown_path=Path("data/reports/promotion_review/promotion_review_packet.md"),
            command="python scripts\\run_promotion_review.py --output-dir data\\reports\\promotion_review",
            required=False,
            role="Paper-readiness evidence",
            cadence="When promotion evidence changes",
        ),
        _audit_packet_row(
            root,
            packet_id="browser_smoke",
            label="GUI browser smoke evidence",
            path=Path("data/reports/gui_browser_smoke/gui_browser_smoke.json"),
            markdown_path=Path("data/reports/gui_browser_smoke/gui_browser_smoke.md"),
            command=(
                "python scripts\\run_gui_browser_smoke.py --base-url http://127.0.0.1:8765 "
                "--output-dir data\\reports\\gui_browser_smoke"
            ),
            required=True,
            role="Frontend operator usability gate",
            cadence="Before each GUI push",
        ),
    ]
    required_missing = [row for row in rows if row["required"] and row["status"] != "present"]
    present_rows = [row for row in rows if row["status"] == "present"]
    return {
        "stage": "gui_audit_packets",
        "summary": {
            "tracked_packets": len(rows),
            "present": len(present_rows),
            "missing": sum(1 for row in rows if row["status"] != "present"),
            "required_missing": len(required_missing),
            "independent_audit_complete": any(
                row["packet_id"] == "independent_gui_audit" and row["status"] == "present" for row in rows
            ),
            "latest_packet": _latest_packet_label(present_rows),
        },
        "rows": rows,
    }


def _audit_packet_row(
    root: Path,
    *,
    packet_id: str,
    label: str,
    path: Path,
    markdown_path: Path,
    command: str,
    required: bool,
    role: str,
    cadence: str,
) -> dict[str, Any]:
    json_target = root / path
    markdown_target = root / markdown_path
    present_target = json_target if json_target.exists() else markdown_target if markdown_target.exists() else None
    return {
        "packet_id": packet_id,
        "label": label,
        "status": "present" if present_target else "missing",
        "required": required,
        "path": str(path),
        "markdown_path": str(markdown_path),
        "command": command,
        "role": role,
        "cadence": cadence,
        "updated_at": _mtime_text(present_target) if present_target else "",
        "evidence": "Local audit packet is available." if present_target else "Generate or attach this audit evidence before relying on the console score.",
    }


def _latest_packet_label(rows: list[dict[str, Any]]) -> str:
    dated = [row for row in rows if row.get("updated_at")]
    if not dated:
        return ""
    return max(dated, key=lambda row: str(row.get("updated_at", ""))).get("label", "")


def _mtime_text(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.stat().st_mtime_ns)
    except OSError:
        return ""


def _run_history_spec() -> dict[str, Any]:
    return {
        "stage": "gui_run_history",
        "storage_key": "quant_robot.gui.run_history.v1",
        "max_entries": 20,
        "empty_state": "No local workflow runs recorded in this browser yet.",
        "capture_events": [
            {"workflow_id": "startup_workflows", "label": "Run startup workflows"},
            {"workflow_id": "research_backtest", "label": "Run research backtest"},
            {"workflow_id": "signal_snapshot", "label": "Generate advisory signal snapshot"},
            {"workflow_id": "paper_simulation", "label": "Run local paper simulation"},
            {"workflow_id": "daily_ops", "label": "Refresh Daily Ops"},
            {"workflow_id": "promotion_ops", "label": "Refresh Promotion Ops"},
        ],
    }


def _execution_receipts_spec() -> dict[str, Any]:
    return {
        "stage": "gui_execution_receipts",
        "storage_key": "quant_robot.gui.execution_receipts.v1",
        "max_entries": 20,
        "empty_state": "No structured workflow receipts recorded in this browser yet.",
        "capture_events": [
            {"workflow_id": "research_backtest", "label": "Research backtest receipt"},
            {"workflow_id": "signal_snapshot", "label": "Advisory signal receipt"},
            {"workflow_id": "paper_simulation", "label": "Paper simulation receipt"},
        ],
        "fields": [
            "workflow_id",
            "time",
            "request",
            "metrics",
            "decision",
            "safety",
        ],
    }


def _operator_timeline(
    workflows: list[dict[str, Any]],
    verification_gates: list[dict[str, Any]],
    readiness_matrix: dict[str, Any],
    audit_scorecard: dict[str, Any],
) -> dict[str, Any]:
    repair_queue = audit_scorecard.get("repair_queue", [])
    required_gate_count = len([gate for gate in verification_gates if str(gate.get("status", "")).startswith("required")])
    repair_count = len(repair_queue)
    events = [
        {
            "event_id": "context_gate",
            "label": "Context gate",
            "status": "done",
            "detail": "office_desktop / factor_review / codex GUI task branch.",
            "command": "python scripts\\sync_project.py --machine office_desktop --task factor_review",
        },
        {
            "event_id": "research_backtest",
            "label": "CN_ETF research backtest",
            "status": "active",
            "detail": "Current primary workflow: run local processed-bars research with visible method and parameters.",
            "command": _workflow_command(workflows, "research_backtest"),
        },
        {
            "event_id": "signal_snapshot",
            "label": "Advisory signal snapshot",
            "status": "queued",
            "detail": "Generate target weights with executable=false after research refresh.",
            "command": _workflow_command(workflows, "signal_snapshot"),
        },
        {
            "event_id": "paper_simulation",
            "label": "Paper simulation gate",
            "status": "requires_gates",
            "detail": "Local simulated fills only; promotion and readiness gates must remain visible before operator use.",
            "command": _workflow_command(workflows, "paper_simulation"),
        },
        {
            "event_id": "verification_pack",
            "label": "Verification pack",
            "status": "required",
            "detail": f"{required_gate_count} required GUI, audit, compile, sync, and browser gates before push.",
            "command": verification_gates[0]["command"] if verification_gates else "python -m unittest -v tests.unit.test_gui",
        },
        {
            "event_id": "audit_repair_queue",
            "label": "Audit repair queue",
            "status": "required",
            "detail": f"{repair_count} repair actions queued from the local scorecard and five-round audit protocol.",
            "command": repair_queue[0]["action"] if repair_queue else "No audit repair actions queued",
        },
        {
            "event_id": "live_handoff",
            "label": "Live trading handoff",
            "status": "blocked",
            "detail": readiness_matrix.get("rows", [])[-1].get("guardrail", SAFETY_NOTICE)
            if readiness_matrix.get("rows")
            else SAFETY_NOTICE,
            "command": "blocked by research-to-paper boundary",
        },
    ]
    return {
        "stage": "operator_timeline",
        "summary": {
            "current_event": "research_backtest",
            "events": len(events),
            "active": sum(1 for item in events if item["status"] == "active"),
            "queued": sum(1 for item in events if item["status"] == "queued"),
            "required": sum(1 for item in events if item["status"] in {"required", "requires_gates"}),
            "blocked": sum(1 for item in events if item["status"] == "blocked"),
            "repair_count": repair_count,
        },
        "events": events,
    }


def _workflow_command(workflows: list[dict[str, Any]], workflow_id: str) -> str:
    workflow = _workflow_by_id(workflows, workflow_id)
    return workflow["command"] if workflow else ""


def _workflow_request(workflows: list[dict[str, Any]], workflow_id: str) -> dict[str, Any]:
    workflow = _workflow_by_id(workflows, workflow_id)
    request = workflow.get("request", {}) if workflow else {}
    return request if isinstance(request, dict) else {}


def _report_links(root: Path, artifacts: list[dict[str, Any]], audit_packets: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    links = [
        {"kind": "logs", "label": "GUI logs page", "path": "#page-logs", "status": "available"},
        {"kind": "reports", "label": "Local report directory", "path": "data/reports", "status": "present" if (root / "data/reports").exists() else "missing"},
    ]
    for packet in (audit_packets or {}).get("rows", []):
        links.append(
            {
                "kind": "audit_packet",
                "label": packet.get("label", packet.get("packet_id", "")),
                "path": packet.get("markdown_path") or packet.get("path", ""),
                "status": packet.get("status", "missing"),
            }
        )
    links.extend(
        {
            "kind": "artifact",
            "label": artifact["artifact_id"],
            "path": artifact["path"],
            "status": artifact["status"],
        }
        for artifact in artifacts
    )
    return links


def _process_monitor(root: Path) -> dict[str, Any]:
    current_pid = os.getpid()
    queried_rows = _normalize_process_rows(_query_related_processes(root), current_pid=current_pid)
    rows = _dedupe_process_rows([_current_process_row(current_pid), *queried_rows])
    gui_detected = any(row.get("role") == "gui_server" for row in rows)
    active_job_roles = {"browser_smoke", "gui_audit", "project_audit", "factor_job", "verification_job"}
    running_jobs = sum(1 for row in rows if row.get("role") in active_job_roles)
    status = "observing" if rows else "unknown"
    return {
        "stage": "gui_process_monitor",
        "summary": {
            "status": status,
            "current_pid": current_pid,
            "related_processes": len(rows),
            "running_jobs": running_jobs,
            "gui_server_detected": gui_detected,
            "paper_only": True,
            "live_trading_allowed": False,
            "poll_command": "GET /api/control/status",
            "next_action": (
                "Review active local research, smoke, and audit processes before launching more work."
                if running_jobs
                else "No extra GUI worker jobs detected; launch research, paper, or verification workflows from the console."
            ),
        },
        "rows": rows,
    }


def _current_process_row(current_pid: int) -> dict[str, Any]:
    command = " ".join([Path(sys.executable).name, *sys.argv])
    rows = _normalize_process_rows(
        [
            {
                "process_id": current_pid,
                "name": Path(sys.executable).name,
                "command_line": command,
                "created_at": "",
            }
        ],
        current_pid=current_pid,
    )
    row = rows[0] if rows else {}
    row["check_id"] = "current_process"
    row["label"] = "Current API process"
    return row


def _query_related_processes(root: Path) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    script = rf"""
$ErrorActionPreference = 'Stop'
Get-CimInstance Win32_Process |
  Where-Object {{
    $_.CommandLine -and
    $_.CommandLine -notmatch "Get-CimInstance Win32_Process" -and
    $_.Name -match "python|py|powershell" -and (
      $_.CommandLine -match "quant_robot|run_gui|run_project_audit|run_gui_browser_smoke|run_gui_control_center_audit|sync_project|scripts[\\/]+run_|unittest|pytest|compileall"
    )
  }} |
  Select-Object ProcessId,Name,CommandLine,CreationDate |
  ConvertTo-Json -Depth 3
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _normalize_process_rows(rows: Any, current_pid: int | None = None) -> list[dict[str, Any]]:
    if isinstance(rows, dict):
        source_rows = [rows]
    elif isinstance(rows, list):
        source_rows = [row for row in rows if isinstance(row, dict)]
    else:
        source_rows = []
    normalized: list[dict[str, Any]] = []
    for item in source_rows:
        process_id = _int_or_none(item.get("ProcessId", item.get("process_id", item.get("pid"))))
        if process_id is None:
            continue
        command = _redact_command_line(str(item.get("CommandLine", item.get("command_line", item.get("command", ""))) or ""))
        name = str(item.get("Name", item.get("name", "process")) or "process")
        role = _process_role(command, process_id=process_id, current_pid=current_pid)
        normalized.append(
            {
                "check_id": "current_process" if current_pid is not None and process_id == current_pid else f"process_{process_id}",
                "label": _process_label(role),
                "process_id": process_id,
                "name": name,
                "role": role,
                "status": "running",
                "started_at": str(item.get("CreationDate", item.get("created_at", "")) or ""),
                "command": command or name,
                "paper_only": True,
                "live_trading_allowed": False,
                "evidence": "Local process observation only; no broker, account, order, or live-trading side effects.",
            }
        )
    return normalized


def _process_role(command: str, *, process_id: int, current_pid: int | None = None) -> str:
    lowered = command.lower()
    if "run_gui.py" in lowered or "quant_robot.gui" in lowered:
        return "gui_server"
    if "run_gui_browser_smoke.py" in lowered:
        return "browser_smoke"
    if "run_gui_control_center_audit.py" in lowered:
        return "gui_audit"
    if "run_project_audit.py" in lowered or "sync_project.py" in lowered:
        return "project_audit"
    if "unittest" in lowered or "pytest" in lowered or "compileall" in lowered:
        return "verification_job"
    if "factor" in lowered or "backtest" in lowered or "research" in lowered:
        return "factor_job"
    if current_pid is not None and process_id == current_pid:
        return "current_snapshot"
    return "related_python"


def _process_label(role: str) -> str:
    labels = {
        "gui_server": "GUI server",
        "browser_smoke": "Browser smoke",
        "gui_audit": "GUI audit",
        "project_audit": "Project audit",
        "verification_job": "Verification job",
        "factor_job": "Factor or backtest job",
        "current_snapshot": "Current API process",
        "related_python": "Related process",
    }
    return labels.get(role, "Related process")


def _dedupe_process_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        process_id = row.get("process_id")
        if not isinstance(process_id, int) or process_id in seen:
            continue
        seen.add(process_id)
        deduped.append(row)
    return deduped


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _redact_command_line(command: str) -> str:
    redacted = re.sub(r"(?i)(tushare[_-]?token|token|api[_-]?key)=([^\s&]+)", r"\1=<redacted>", command)
    redacted = re.sub(r"(?i)(--(?:tushare[_-]?token|token|api[_-]?key))\s+\S+", r"\1 <redacted>", redacted)
    if len(redacted) > 360:
        return f"{redacted[:340]} ... <truncated>"
    return redacted


def _workspace_sync(root: Path, branch: str) -> dict[str, Any]:
    changed_paths = _git_changed_paths(root)
    upstream_sync = _git_text(root, ["rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
    head = _git_text(root, ["log", "-1", "--format=%h %s"])
    classification = _classify_workspace_paths(root, changed_paths)
    behind, ahead = _parse_upstream_sync(upstream_sync)
    blocked_count = len(classification["blocked"])
    syncable_count = len(classification["syncable"])
    ignored_count = len(classification["ignored"])
    is_unknown = branch == "unknown" or head == "unknown"
    status = "unknown" if is_unknown else "dirty" if changed_paths else "clean"
    next_action = (
        "Inspect repository manually; git metadata is unavailable."
        if status == "unknown"
        else "Remove or ignore forbidden paths before syncing."
        if blocked_count
        else "Run verification and safe sync before push."
        if changed_paths
        else "Workspace is clean; continue GUI iteration or pull latest main when integrating."
    )
    rows = [
        {
            "check_id": "current_branch",
            "label": "Current branch",
            "status": "ready" if branch.startswith("codex/") else "warn" if branch not in {"", "unknown"} else "unknown",
            "value": branch,
            "evidence": "Task branches should use the codex/ prefix; keep main stable.",
        },
        {
            "check_id": "head_commit",
            "label": "HEAD",
            "status": "ready" if head != "unknown" else "unknown",
            "value": head,
            "evidence": "Latest local commit visible to the operator.",
        },
        {
            "check_id": "worktree",
            "label": "Worktree",
            "status": "clean" if not changed_paths and not is_unknown else "dirty" if changed_paths else "unknown",
            "value": f"{len(changed_paths)} changed path(s)",
            "evidence": _path_preview(changed_paths),
        },
        {
            "check_id": "upstream_sync",
            "label": "Upstream sync",
            "status": "ready" if behind == 0 else "behind" if behind > 0 else "unknown",
            "value": upstream_sync,
            "evidence": f"behind={behind if behind >= 0 else '--'} / ahead={ahead if ahead >= 0 else '--'}",
        },
        {
            "check_id": "safe_sync_policy",
            "label": "Safe sync policy",
            "status": "blocked" if blocked_count else "ready",
            "value": f"syncable={syncable_count} / blocked={blocked_count} / ignored={ignored_count}",
            "evidence": "Only source, tests, configs, docs, and lightweight summaries are syncable.",
        },
        {
            "check_id": "publish_command",
            "label": "Publish command",
            "status": "required",
            "value": "python scripts\\sync_project.py --machine office_desktop --task factor_review --execute --push",
            "evidence": "Run after tests, compile checks, project audit, browser smoke, and sync audit pass.",
        },
    ]
    return {
        "stage": "gui_workspace_sync",
        "summary": {
            "status": status,
            "current_branch": branch,
            "head": head,
            "upstream_sync": upstream_sync,
            "behind": behind,
            "ahead": ahead,
            "changed_paths": len(changed_paths),
            "syncable_paths": syncable_count,
            "blocked_paths": blocked_count,
            "ignored_paths": ignored_count,
            "next_action": next_action,
        },
        "classification": classification,
        "rows": rows,
    }


def _git_text(root: Path, args: list[str], timeout: int = 3) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _git_changed_paths(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return _parse_git_status_paths(completed.stdout.rstrip("\n"))


def _parse_git_status_paths(status: str) -> list[str]:
    paths: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:].strip().strip('"')
        if " -> " in raw_path:
            paths.extend(part.strip().strip('"') for part in raw_path.split(" -> ", 1))
        else:
            paths.append(raw_path)
    return [path for path in paths if path]


def _classify_workspace_paths(root: Path, paths: list[str]) -> dict[str, list[str]]:
    config = _load_workstation_config(root)
    sync_policy = config.get("sync_policy", {}) if isinstance(config.get("sync_policy"), dict) else {}
    data_policy = config.get("data_policy", {}) if isinstance(config.get("data_policy"), dict) else {}
    allowed_patterns = [str(item) for item in sync_policy.get("allowed_paths", [])]
    forbidden_patterns = [str(item) for item in sync_policy.get("forbidden_paths", [])]
    forbidden_patterns.extend(str(item) for item in data_policy.get("ignored_paths", []))
    syncable: list[str] = []
    blocked: list[str] = []
    ignored: list[str] = []
    for path in paths:
        normalized = _normalize_repo_path(path)
        if _matches_repo_path(normalized, forbidden_patterns) and normalized != ".env.example":
            blocked.append(normalized)
        elif _matches_repo_path(normalized, allowed_patterns):
            syncable.append(normalized)
        else:
            ignored.append(normalized)
    return {
        "syncable": syncable,
        "blocked": blocked,
        "ignored": ignored,
    }


def _load_workstation_config(root: Path) -> dict[str, Any]:
    path = root / "configs" / "workstations.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _normalize_repo_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _matches_repo_path(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        normalized = _normalize_repo_path(pattern)
        if normalized.endswith("/"):
            prefix = normalized[:-1]
            if path == prefix or path.startswith(normalized):
                return True
        elif path == normalized or fnmatch.fnmatch(path, normalized):
            return True
    return False


def _parse_upstream_sync(value: str) -> tuple[int, int]:
    parts = value.replace("\t", " ").split()
    if len(parts) < 2:
        return -1, -1
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return -1, -1


def _path_preview(paths: list[str]) -> str:
    if not paths:
        return "No changed paths."
    preview = ", ".join(paths[:3])
    suffix = "" if len(paths) <= 3 else f", +{len(paths) - 3} more"
    return f"Changed: {preview}{suffix}"


def _git_branch(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    branch = completed.stdout.strip()
    return branch or "unknown"


def _artifact_status(root: Path) -> list[dict[str, Any]]:
    paths = [
        ("readiness_board", Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")),
        ("daily_ops", Path("data/reports/daily_ops/daily_ops_pack.json")),
        ("risk_candidates", Path("data/reports/risk_candidate_selector/risk_candidate_pack.json")),
        ("paper_profiles", Path("data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json")),
        ("promotion_report", Path("data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json")),
        ("quality_report", Path("data/processed/etf_csv/quality_report_cn_etf.json")),
    ]
    return [
        {
            "artifact_id": artifact_id,
            "path": str(path),
            "status": "present" if (root / path).exists() else "missing",
        }
        for artifact_id, path in paths
    ]
