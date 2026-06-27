from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."


def build_control_center_snapshot(repo_root: str | Path | None = None, active_goal: str | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    branch = _git_branch(root)
    artifacts = _artifact_status(root)
    backtest = _default_backtest()

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
        "workflows": _workflow_commands(backtest),
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
        "report_links": _report_links(root, artifacts),
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


def _report_links(root: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = [
        {"kind": "logs", "label": "GUI logs page", "path": "#page-logs", "status": "available"},
        {"kind": "reports", "label": "Local report directory", "path": "data/reports", "status": "present" if (root / "data/reports").exists() else "missing"},
    ]
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
