from __future__ import annotations

import fnmatch
import json
import os
import subprocess
from pathlib import Path
from typing import Any


SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
GUI_AUDIT_PACKET_PATH = Path("data/reports/gui_control_center_audit/gui_control_center_audit.json")
RESOLVED_AUDIT_LOOP_ACTIONS = {
    "Attach audit findings to next optimization round",
    "Review linked audit packets during next audit",
}


def build_control_center_snapshot(repo_root: str | Path | None = None, active_goal: str | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    branch = _git_branch(root)
    workspace_sync = _workspace_sync(root, branch)
    artifacts = _artifact_status(root)
    backtest = _default_backtest()
    workflows = _workflow_commands(backtest)
    run_queue = _run_queue(workflows)
    verification_gates = _verification_gates()
    readiness_matrix = _readiness_matrix(workflows, verification_gates, artifacts)
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
    )
    audit_feedback = _audit_feedback(audit_packet_source, audit_packets)
    audit_iteration_plan = _audit_iteration_plan(audit_feedback, audit_scorecard, verification_gates, readiness_matrix)
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
        "workspace_sync": workspace_sync,
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
        "audit_iteration_plan": audit_iteration_plan,
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
            "cadence": "Every 5 hours",
            "name": "GUI control center audit",
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


def _workflow_commands(backtest: dict[str, Any]) -> list[dict[str, Any]]:
    query = (
        f"source={backtest['source']}&data_root={backtest['data_root']}&market={backtest['market']}"
        f"&factor={backtest['factor']}&factor_windows={backtest['factor_windows']}&top_n={backtest['top_n']}"
        f"&cost_bps={backtest['cost_bps']}&start_date={backtest['start_date']}&end_date={backtest['end_date']}"
        f"&rebalance_interval={backtest['rebalance_interval']}&benchmark_asset_id={backtest['benchmark_asset_id']}"
        f"&cash_annual_return={backtest['cash_annual_return']}&regime_filter=true&regime_lookback={backtest['regime_lookback']}"
        f"&max_drawdown_limit={backtest['max_drawdown_limit']}"
    )
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
            "command": f"GET /api/research?{query}",
            "endpoint": f"/api/research?{query}",
            "mode": "local",
            "safety": "research calculation only",
        },
        {
            "workflow_id": "signal_snapshot",
            "label": "Generate advisory signal snapshot",
            "command": (
                f"GET /api/signals?source={backtest['source']}&data_root={backtest['data_root']}"
                f"&market={backtest['market']}&factor={backtest['factor']}&top_n={backtest['top_n']}"
                "&max_asset_weight=0.4&min_cash_weight=0.1"
            ),
            "endpoint": "/api/signals",
            "mode": "local",
            "safety": "advisory targets only, executable=false",
        },
        {
            "workflow_id": "paper_simulation",
            "label": "Run local paper simulation",
            "command": (
                f"GET /api/paper?source={backtest['source']}&data_root={backtest['data_root']}"
                f"&market={backtest['market']}&factor={backtest['factor']}&top_n={backtest['top_n']}"
                f"&start_date={backtest['start_date']}&end_date={backtest['end_date']}"
                "&initial_cash=100000&commission_bps=5&slippage_bps=5&max_asset_weight=0.4&min_cash_weight=0.1"
            ),
            "endpoint": "/api/paper",
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


def _workflow_by_id(workflows: list[dict[str, Any]], workflow_id: str) -> dict[str, Any] | None:
    for workflow in workflows:
        if workflow.get("workflow_id") == workflow_id:
            return workflow
    return None


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
            "score": 14 if result_evidence_ready else 13,
            "max_score": 14,
            "status": "good" if result_evidence_ready else "needs_result_evidence",
            "evidence": (
                "Startup health, result evidence, current work, local workflow commands, and browser-persisted run history are visible."
                if result_evidence_ready
                else "Runtime view needs result evidence that maps metrics to workflow receipts and next commands."
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
    repair_queue = _dedupe_audit_actions(repair_queue)
    return {
        "stage": "gui_audit_scorecard",
        "summary": {
            "local_self_check_score": total_score,
            "max_score": max_score,
            "cadence_hours": 5,
            "automation_id": "gui-5h",
            "independent_audit_complete": independent_audit_complete,
            "score_source": "independent_gui_audit_packet" if latest_gui_audit else "local_self_check_not_independent_audit",
            "independent_audit_score": latest_gui_audit.get("score") if latest_gui_audit else None,
            "independent_audit_verdict": latest_gui_audit.get("verdict") if latest_gui_audit else "",
            "required_gate_count": required_gate_count,
            "missing_artifact_count": missing_artifact_count,
            "required_missing_audit_packets": required_missing_packets,
        },
        "categories": categories,
        "repair_queue": repair_queue,
        "next_audit": {
            "cadence": "Every 5 hours",
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
            label="Independent 5h GUI audit",
            path=Path("data/reports/gui_control_center_audit/gui_control_center_audit.json"),
            markdown_path=Path("data/reports/gui_control_center_audit/gui_control_center_audit.md"),
            command="python scripts\\run_gui_control_center_audit.py --output-dir data\\reports\\gui_control_center_audit",
            required=True,
            role="Independent GUI control center auditor",
            cadence="Every 5 hours",
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
            "detail": f"{repair_count} repair actions queued from the local scorecard and 5h audit protocol.",
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
