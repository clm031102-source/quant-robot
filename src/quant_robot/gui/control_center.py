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
        "backtest": {
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
        },
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
