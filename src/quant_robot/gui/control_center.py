from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
GUI_AUDIT_PACKET_PATH = Path("data/reports/gui_control_center_audit/gui_control_center_audit.json")


def build_control_center_snapshot(repo_root: str | Path | None = None, active_goal: str | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    branch = _git_branch(root)
    artifacts = _artifact_status(root)
    backtest = _default_backtest()
    workflows = _workflow_commands(backtest)
    verification_gates = _verification_gates()
    readiness_matrix = _readiness_matrix(workflows, verification_gates, artifacts)
    audit_packets = _audit_packets(root)
    audit_packet_source = _load_gui_audit_packet(root)
    latest_gui_audit = audit_packet_source.get("packet") if audit_packet_source.get("status") == "packet_present" else None
    audit_scorecard = _audit_scorecard(verification_gates, readiness_matrix, artifacts, audit_packets, latest_gui_audit)
    audit_feedback = _audit_feedback(audit_packet_source, audit_packets)
    release_readiness = _release_readiness(verification_gates, audit_packets, readiness_matrix)

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
        "run_queue": _run_queue(workflows),
        "verification_gates": verification_gates,
        "operator_checklist": _operator_checklist(verification_gates, artifacts),
        "execution_plan": _execution_plan(workflows, verification_gates),
        "readiness_matrix": readiness_matrix,
        "release_readiness": release_readiness,
        "audit_scorecard": audit_scorecard,
        "operator_timeline": _operator_timeline(workflows, verification_gates, readiness_matrix, audit_scorecard),
        "run_history": _run_history_spec(),
        "execution_receipts": _execution_receipts_spec(),
        "audit_packets": audit_packets,
        "audit_feedback": audit_feedback,
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
) -> dict[str, Any]:
    required_gate_count = sum(1 for gate in verification_gates if str(gate.get("status", "")).startswith("required"))
    browser_gate_count = sum(1 for gate in verification_gates if "browser" in str(gate.get("gate_id", "")))
    missing_artifact_count = sum(1 for artifact in artifacts if artifact["status"] != "present")
    live_ready = bool(readiness_matrix.get("summary", {}).get("live_ready"))
    audit_packet_summary = (audit_packets or {}).get("summary", {})
    independent_audit_complete = bool(audit_packet_summary.get("independent_audit_complete"))
    required_missing_packets = int(audit_packet_summary.get("required_missing", 0) or 0)
    independent_audit_actions = _audit_packet_next_actions(latest_gui_audit) if latest_gui_audit else []
    categories = [
        {
            "category_id": "work_visibility",
            "label": "Work visibility",
            "score": 16,
            "max_score": 18,
            "status": "good",
            "evidence": "Run queue, operator checklist, execution plan, and readiness matrix are visible.",
        },
        {
            "category_id": "backtest_transparency",
            "label": "Backtest transparency",
            "score": 17,
            "max_score": 18,
            "status": "good",
            "evidence": "Control center exposes data source, market, factor, windows, TopN, cost, lag, and method steps.",
        },
        {
            "category_id": "paper_live_boundary",
            "label": "Paper/live boundary",
            "score": 20 if not live_ready else 0,
            "max_score": 20,
            "status": "blocked_live",
            "evidence": SAFETY_NOTICE,
        },
        {
            "category_id": "runtime_observability",
            "label": "Runtime observability",
            "score": 15,
            "max_score": 16,
            "status": "good",
            "evidence": "Current work, local workflow commands, and browser-persisted run history are visible.",
        },
        {
            "category_id": "verification_coverage",
            "label": "Verification coverage",
            "score": 14,
            "max_score": 16,
            "status": "good",
            "evidence": f"{required_gate_count} required gates tracked, including {browser_gate_count} browser smoke gates.",
        },
        {
            "category_id": "frontend_usability",
            "label": "Frontend usability",
            "score": 10 if missing_artifact_count == 0 else 8,
            "max_score": 12,
            "status": "good" if missing_artifact_count == 0 else "needs_artifacts",
            "evidence": f"{missing_artifact_count} tracked local artifact links are missing.",
        },
    ]
    total_score = sum(item["score"] for item in categories)
    max_score = sum(item["max_score"] for item in categories)
    repair_queue = []
    if latest_gui_audit:
        actionable_audit_actions = [
            action for action in independent_audit_actions if action.get("action") != "Run independent 5h GUI audit"
        ]
        first_action = actionable_audit_actions[0] if actionable_audit_actions else {}
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
    repair_queue.extend(
        [
            {
                "priority": "P1",
                "action": "Attach audit findings to next optimization round",
                "reason": "The GUI should turn each 5h scorecard into visible fixes and acceptance gates.",
            },
            {
                "priority": "P2",
                "action": "Generate missing audit packets" if required_missing_packets else "Review linked audit packets during next audit",
                "reason": (
                    f"{required_missing_packets} required audit packet links are missing."
                    if required_missing_packets
                    else "Audit packet links are visible; use them as the evidence spine for the next independent review."
                ),
            },
        ]
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
        if not next_actions:
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
                "verdict": packet.get("verdict", ""),
                "generated_at": packet.get("generated_at", ""),
                "next_action_count": len(next_actions),
                "required_missing_audit_packets": required_missing,
            },
            "next_actions": next_actions[:6],
            "evidence": "Latest independent GUI audit packet is feeding the next optimization round.",
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
