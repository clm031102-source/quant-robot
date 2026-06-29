from __future__ import annotations

import csv
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness
from quant_robot.gui.fixtures import mock_data
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation
from quant_robot.portfolio.rebalance import build_rebalance_plan
from quant_robot.ops.evidence_refresh import build_evidence_refresh_plan
from quant_robot.ops.promotion_console import build_promotion_operations_console
from quant_robot.ops.review_packet import build_promotion_review_packet
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_GUI_PROCESSED_ROOT = Path("data/processed/etf_csv")
DEFAULT_GUI_PROCESSED_MARKETS = ("CN_ETF",)
DEFAULT_READINESS_BOARD = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_DATA_GAP_EVIDENCE = Path("data/reports/data_gap_evidence/data_gap_evidence_pack.json")
DEFAULT_DATA_GAP_RESOLUTION = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_PROVIDER_REMEDIATION = Path("data/reports/provider_remediation/provider_remediation_matrix.json")
DEFAULT_DUPLICATE_REGISTRY = Path("data/reports/duplicate_registry/duplicate_canonical_registry.json")
DEFAULT_RESIDUAL_FOCUS = Path("data/reports/residual_blocker_focus/residual_blocker_focus_pack.json")
DEFAULT_DAILY_OPS_PACK = Path("data/reports/daily_ops/daily_ops_pack.json")
DEFAULT_RISK_CANDIDATE_PACK = Path("data/reports/risk_candidate_selector/risk_candidate_pack.json")
DEFAULT_CONSTRAINED_RISK_CANDIDATE_PACK = Path("data/reports/risk_candidate_selector_risk_constrained/risk_candidate_pack.json")
DEFAULT_CONSTRAINED_SEARCH_PACK = Path("data/reports/constrained_candidate_search/constrained_candidate_search_pack.json")
DEFAULT_PAPER_PROFILE_PACK = Path("data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json")
DEFAULT_PROFILE_OBSERVATION_PACK = Path("data/reports/profile_observation/profile_observation_pack.json")
DEFAULT_RECENT_DATA_REFRESH_PACK = Path("data/reports/recent_data_refresh/recent_data_refresh_pack.json")
DEFAULT_POST_REFRESH_REPLAY_PACK = Path("data/reports/post_refresh_replay/post_refresh_replay_pack.json")
DEFAULT_OBSERVATION_SUFFICIENCY_PACK = Path("data/reports/observation_sufficiency/observation_sufficiency_pack.json")
DEFAULT_EXPANDED_OBSERVATION_REPLAY_PACK = Path("data/reports/expanded_observation_replay/expanded_observation_replay_pack.json")
DEFAULT_ITERATIVE_OBSERVATION_EXPANSION_PACK = Path("data/reports/iterative_observation_expansion/iterative_observation_expansion_pack.json")
DEFAULT_TUSHARE_ACTIVATION_GATE_PACK = Path("data/reports/tushare_activation_gate/tushare_activation_gate_pack.json")
DEFAULT_FACTOR_LEADERBOARD_REPORTS_ROOT = Path("data/reports")
DEFAULT_FACTOR_LEADERBOARD_CONFIGS_ROOT = Path("configs")
DEFAULT_FACTOR_LEADERBOARD_CACHE = Path("data/reports/gui_factor_leaderboard_cache/gui_factor_leaderboard_cache.json")
FACTOR_LEADERBOARD_CACHE_VERSION = 2
PRIMARY_FACTOR_MARKET = "CN_ETF"
FACTOR_LEADERBOARD_GROUPS = {
    "primary_cn_etf": {
        "label": "CN_ETF 主线榜",
        "description": "只展示 A 股 ETF 轮动主线候选，默认先看这张榜。",
    },
    "cn_stock_research": {
        "label": "CN 个股辅助研究榜",
        "description": "只展示 A 股个股研究候选，不能直接当 ETF 轮动信号。",
    },
    "all_history": {
        "label": "全部历史榜",
        "description": "展示所有市场历史候选，用来盘点资产，不作为默认推广依据。",
    },
}
FACTOR_LEADERBOARD_FILE_KEYWORDS = (
    "leaderboard",
    "candidate",
    "factor",
    "prescreen",
    "walk_forward",
    "portfolio",
    "paper",
    "promotion",
    "optimizer",
    "results",
    "summary",
)
FACTOR_LEADERBOARD_SCORE_PRIORITY = (
    "paper_sharpe",
    "walk_forward_sharpe",
    "oos_sharpe",
    "test_sharpe",
    "sharpe",
    "sharpe_ratio",
    "rank_ic",
    "mean_rank_ic",
    "mean_ic",
    "score",
    "total_return",
)
FACTOR_LEADERBOARD_METRIC_ALIASES = {
    "total_return": ("total_return", "paper_total_return", "strategy_total_return", "net_total_return", "return_total"),
    "annualized_return": ("annualized_return", "annual_return", "paper_annualized_return", "cagr"),
    "sharpe": ("sharpe", "sharpe_ratio", "paper_sharpe", "walk_forward_sharpe", "oos_sharpe", "test_sharpe"),
    "max_drawdown": ("max_drawdown", "max_equity_drawdown", "paper_max_drawdown", "max_dd"),
    "win_rate": ("win_rate", "hit_rate", "positive_rate", "pct_profitable_periods"),
    "rank_ic": ("rank_ic", "mean_rank_ic", "avg_rank_ic"),
    "mean_ic": ("mean_ic", "ic_mean", "ic"),
    "trade_count": ("trade_count", "trades", "n_trades", "num_trades", "fill_count", "fills"),
    "sample_count": ("sample_count", "observations", "n_obs", "ic_observations", "periods", "fold_count"),
}
FACTOR_LEADERBOARD_PARAM_KEYS = (
    "top_n",
    "topN",
    "cost_bps",
    "commission_bps",
    "slippage_bps",
    "rebalance_interval",
    "holding_period",
    "lookback",
    "factor_window",
    "factor_windows",
    "execution_lag",
    "forward_horizon",
    "market",
    "portfolio_scope",
    "max_asset_weight",
    "max_market_weight",
    "max_gross_exposure",
    "max_drawdown_guard",
    "risk_tier",
    "profile_id",
    "portfolio_value",
)
FACTOR_LEADERBOARD_IDENTITY_KEYS = {
    "case_id",
    "candidate_id",
    "factor_name",
    "factor",
    "public_factor_name",
    "lead_factor_name",
    "source_factor_name",
    "profile_id",
    "strategy_id",
}
FACTOR_LEADERBOARD_METRIC_KEYS = set(FACTOR_LEADERBOARD_SCORE_PRIORITY) | {
    alias for aliases in FACTOR_LEADERBOARD_METRIC_ALIASES.values() for alias in aliases
}


def build_gui_snapshot() -> dict[str, Any]:
    strategies = mock_data.demo_strategies()
    markets = mock_data.market_statuses()
    logs = mock_data.task_logs()
    return _sanitize(
        {
            "data_mode": mock_data.DATA_MODE,
            "notice": mock_data.DEMO_NOTICE,
            "dashboard": {
                "strategy_count": len(strategies),
                "data_source_count": len(markets),
                "latest_report": "Demo multi-market research report",
                "backtest_count": 1,
                "risk_notice": "Research only. No broker, no orders, no live trading.",
            },
            "strategies": strategies,
            "markets": markets,
            "assets": mock_data.serialized_assets(),
            "risk": mock_data.risk_snapshot(),
            "logs": logs,
            "reports": mock_data.report_entries(),
            "readiness": {
                "tushare": check_tushare_readiness(),
                "parquet": check_parquet_readiness(),
            },
            "available_factors": [
                "momentum_2",
                "reversal_2",
                "volatility_2",
                "volume_change_2",
                "liquidity_2",
                "momentum_3",
                "reversal_3",
                "volatility_3",
                "volume_change_3",
                "liquidity_3",
                "momentum_5",
                "risk_adjusted_momentum_5",
                "reversal_5",
                "volatility_5",
                "volume_change_5",
                "liquidity_5",
                "momentum_10",
                "risk_adjusted_momentum_10",
                "reversal_10",
                "volatility_10",
                "volume_change_10",
                "liquidity_10",
                "momentum_20",
                "risk_adjusted_momentum_20",
                "reversal_20",
                "volatility_20",
                "volume_change_20",
                "liquidity_20",
                "momentum_60",
                "risk_adjusted_momentum_60",
                "reversal_60",
                "volatility_60",
                "volume_change_60",
                "liquidity_60",
                "momentum_120",
                "risk_adjusted_momentum_120",
                "reversal_120",
                "volatility_120",
                "volume_change_120",
                "liquidity_120",
            ],
        }
    )


def build_factor_leaderboard_snapshot(
    reports_root: str | Path | None = None,
    configs_root: str | Path | None = None,
    limit: int = 20,
    max_files: int = 400,
    max_file_bytes: int = 8_000_000,
    max_csv_rows_per_file: int = 500,
) -> dict[str, Any]:
    report_root = Path(reports_root) if reports_root else DEFAULT_FACTOR_LEADERBOARD_REPORTS_ROOT
    config_root = Path(configs_root) if configs_root else DEFAULT_FACTOR_LEADERBOARD_CONFIGS_ROOT
    safe_limit = max(1, min(int(limit or 20), 100))
    cached = _read_factor_leaderboard_cache(report_root, config_root, safe_limit)
    if cached is not None:
        return cached
    runtime_factors = build_gui_snapshot().get("available_factors", [])
    config_inventory = _collect_config_factor_inventory(config_root)
    report_inventory = _collect_report_candidate_inventory(
        report_root,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
        max_csv_rows_per_file=max_csv_rows_per_file,
    )
    candidate_rows = report_inventory["rows"]
    deduped_rows = _dedupe_leaderboard_rows(candidate_rows)
    ranked_rows = _sort_leaderboard_rows(deduped_rows)
    leaderboards = _build_factor_leaderboards(ranked_rows, safe_limit)
    top_rows = leaderboards["all_history"]["rows"]

    runtime_names = sorted({str(name) for name in runtime_factors if str(name).strip()})
    config_names = sorted(config_inventory["factor_names"])
    report_names = sorted(
        {
            str(row.get("factor_name"))
            for row in candidate_rows
            if row.get("factor_name") and str(row.get("factor_name")).strip()
        }
    )
    all_names = sorted(set(runtime_names) | set(config_names) | set(report_names))
    candidate_rows_by_market = _count_rows_by_market(candidate_rows)
    deduped_rows_by_market = _count_rows_by_market(deduped_rows)
    unique_factor_names_by_market = _count_factor_names_by_market(candidate_rows)

    snapshot = _sanitize(
        {
            "stage": "gui_factor_leaderboard",
            "cache_version": FACTOR_LEADERBOARD_CACHE_VERSION,
            "reports_root": str(report_root),
            "configs_root": str(config_root),
            "summary": {
                "primary_market": PRIMARY_FACTOR_MARKET,
                "runtime_dropdown_factor_names": len(runtime_names),
                "config_factor_names": len(config_names),
                "report_factor_names": len(report_names),
                "unique_factor_names": len(all_names),
                "candidate_rows": report_inventory["candidate_rows"],
                "deduped_candidate_rows": len(deduped_rows),
                "candidate_rows_by_market": candidate_rows_by_market,
                "deduped_candidate_rows_by_market": deduped_rows_by_market,
                "unique_factor_names_by_market": unique_factor_names_by_market,
                "primary_market_candidate_rows": candidate_rows_by_market.get(PRIMARY_FACTOR_MARKET, 0),
                "primary_market_deduped_candidate_rows": deduped_rows_by_market.get(PRIMARY_FACTOR_MARKET, 0),
                "primary_market_unique_factor_names": unique_factor_names_by_market.get(PRIMARY_FACTOR_MARKET, 0),
                "cn_stock_candidate_rows": candidate_rows_by_market.get("CN", 0),
                "cn_stock_unique_factor_names": unique_factor_names_by_market.get("CN", 0),
                "report_files_scanned": report_inventory["files_scanned"],
                "report_files_with_candidates": report_inventory["files_with_candidates"],
                "report_files_skipped": report_inventory["files_skipped"],
                "scan_file_cap": max_files,
                "scan_mode": "fast_gui_candidate_summary_scan",
                "config_files_scanned": config_inventory["files_scanned"],
                "top_n": safe_limit,
                "ranking_basis": "qualified rows first, then first available score among paper/walk-forward/oos/test sharpe, sharpe, rank IC, mean IC, score, total return",
                "note": "The factor dropdown is only the runnable preset list; this ledger aggregates config factor names and historical report candidate rows.",
            },
            "factor_names": {
                "from_runtime_dropdown": runtime_names,
                "from_configs": config_names,
                "from_reports": report_names,
                "all_unique": all_names,
            },
            "leaderboards": leaderboards,
            "top20": top_rows,
            "warnings": report_inventory["warnings"],
        }
    )
    _write_factor_leaderboard_cache(report_root, config_root, snapshot)
    return snapshot


def build_project_status_snapshot(
    readiness_board: str | Path | None = None,
    data_gap_evidence: str | Path | None = None,
    provider_remediation: str | Path | None = None,
    residual_focus: str | Path | None = None,
) -> dict[str, Any]:
    board = _read_optional_json(Path(readiness_board) if readiness_board else DEFAULT_READINESS_BOARD)
    gap_pack = _read_optional_json(Path(data_gap_evidence) if data_gap_evidence else DEFAULT_DATA_GAP_EVIDENCE)
    provider_pack = _read_optional_json(Path(provider_remediation) if provider_remediation else DEFAULT_PROVIDER_REMEDIATION)
    focus_pack = _read_optional_json(Path(residual_focus) if residual_focus else DEFAULT_RESIDUAL_FOCUS)

    actions = sorted(
        board.get("next_local_actions", []),
        key=lambda item: int(item.get("priority", 999)),
    )
    provider_items = provider_pack.get("remediation_items", [])
    tushare_items = [item for item in provider_items if str(item.get("provider", "")).lower() == "tushare"]
    blocking_tushare = [
        item
        for item in tushare_items
        if item.get("blocks_provider_readiness") is True
        or item.get("review_status") in {"needs_review", "blocked_external_change", "adapter_work_required"}
    ]
    local_gap_actions_remaining = any(
        "data_gap" in str(item.get("track_id", "")) or "akshare" in str(item.get("command", "")).lower()
        for item in actions
    )
    gap_summary = gap_pack.get("summary", {})
    provider_summary = provider_pack.get("summary", {})
    focus_summary = focus_pack.get("summary", {})
    blocker_register = board.get("blocker_register", [])
    selected_candidate = board.get("selected_candidate") or {}
    primary_tushare = blocking_tushare[0] if blocking_tushare else (tushare_items[0] if tushare_items else {})

    return _sanitize(
        {
            "stage": "gui_project_status",
            "safety": board.get("safety", "Research only. No broker connection, no account reads, no order placement, no live trading."),
            "overall_status": board.get("overall_status", "unknown" if not board else "clear"),
            "generated_at": board.get("generated_at"),
            "selected_candidate": selected_candidate,
            "readiness_items": board.get("readiness_items", []),
            "blockers": blocker_register,
            "blocker_count": len(blocker_register),
            "next_actions": actions[:12],
            "boundary": board.get("boundary", {}),
            "data_gaps": {
                "gap_rows": int(gap_summary.get("gap_rows", 0) or 0),
                "target_raw_rows_found": int(gap_summary.get("target_raw_rows_found", 0) or 0),
                "gaps_with_peer_trading": int(gap_summary.get("gaps_with_peer_trading", 0) or 0),
                "blocks_api_boundary": bool(gap_summary.get("blocks_api_boundary", False)),
                "sample_rows": gap_pack.get("evidence_rows", [])[:8],
            },
            "provider_remediation": {
                "remediation_items": int(provider_summary.get("remediation_items", 0) or 0),
                "blocking_remediation_items": int(provider_summary.get("blocking_remediation_items", 0) or 0),
                "blocks_api_boundary": bool(provider_summary.get("blocks_api_boundary", False)),
                "items": provider_items[:8],
            },
            "residual_focus": {
                "root_focus_items": int(focus_summary.get("root_focus_items", 0) or 0),
                "residual_blockers": int(focus_summary.get("residual_blockers", 0) or 0),
                "highest_priority_track": focus_summary.get("highest_priority_track"),
                "items": focus_pack.get("focus_items", [])[:6],
            },
            "tushare": {
                "status": primary_tushare.get("review_status", "clear" if not blocking_tushare else "blocked"),
                "blocker": primary_tushare.get("blocker"),
                "required_now": bool(blocking_tushare and not local_gap_actions_remaining),
                "reason": primary_tushare.get("evidence_note")
                or ("Local data-gap actions still remain before asking for Tushare." if blocking_tushare else "Tushare is not blocking the current local push."),
            },
        }
    )


def build_daily_ops_snapshot(daily_ops_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(daily_ops_pack) if daily_ops_pack else DEFAULT_DAILY_OPS_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_daily_ops",
            "artifact_present": False,
            "source_path": str(pack_path),
            "run_date": None,
            "candidate": {},
            "decision": {
                "status": "missing",
                "paper_trading_allowed": False,
                "live_boundary_allowed": False,
                "blocking_reasons": ["daily_ops_artifact_missing"],
                "non_manual_blocking_reasons": ["daily_ops_artifact_missing"],
            },
            "blockers": ["daily_ops_artifact_missing"],
            "risk": {},
            "risk_policy": {},
            "paper_profile": {},
            "ticket_count": 0,
            "advisory_tickets": [],
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }

    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    blockers = decision.get("blocking_reasons", []) if isinstance(decision.get("blocking_reasons"), list) else []
    tickets = pack.get("advisory_tickets", []) if isinstance(pack.get("advisory_tickets"), list) else []
    return _sanitize(
        {
            "stage": "gui_daily_ops",
            "artifact_present": True,
            "source_path": str(pack_path),
            "run_date": pack.get("run_date"),
            "candidate": pack.get("candidate", {}) if isinstance(pack.get("candidate"), dict) else {},
            "decision": decision,
            "blockers": blockers,
            "risk": pack.get("risk", {}) if isinstance(pack.get("risk"), dict) else {},
            "risk_policy": pack.get("risk_policy", {}) if isinstance(pack.get("risk_policy"), dict) else {},
            "paper_profile": pack.get("paper_profile", {}) if isinstance(pack.get("paper_profile"), dict) else {},
            "ticket_count": len(tickets),
            "advisory_tickets": tickets[:80],
            "simulation": pack.get("simulation", {}) if isinstance(pack.get("simulation"), dict) else {},
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_risk_candidate_snapshot(risk_candidate_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(risk_candidate_pack) if risk_candidate_pack else _default_risk_candidate_pack_path()
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_risk_candidate_selector",
            "artifact_present": False,
            "source_path": str(pack_path),
            "selection_status": "missing",
            "paper_trading_allowed": False,
            "live_boundary_allowed": False,
            "summary": {"candidates": 0, "risk_eligible_candidates": 0, "paper_matched_candidates": 0},
            "selected_candidate": None,
            "next_actions": [{"action": "run_risk_candidate_selector", "reason": "risk candidate artifact is missing"}],
            "candidates": [],
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    candidates = pack.get("candidates", []) if isinstance(pack.get("candidates"), list) else []
    return _sanitize(
        {
            "stage": "gui_risk_candidate_selector",
            "artifact_present": True,
            "source_path": str(pack_path),
            "selection_status": pack.get("selection_status"),
            "paper_trading_allowed": bool(pack.get("paper_trading_allowed", False)),
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "summary": pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {},
            "policy": pack.get("policy", {}) if isinstance(pack.get("policy"), dict) else {},
            "selected_candidate": pack.get("selected_candidate") if isinstance(pack.get("selected_candidate"), dict) else None,
            "next_actions": pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [],
            "candidates": candidates[:30],
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def _default_risk_candidate_pack_path() -> Path:
    if DEFAULT_CONSTRAINED_RISK_CANDIDATE_PACK.exists():
        return DEFAULT_CONSTRAINED_RISK_CANDIDATE_PACK
    return DEFAULT_RISK_CANDIDATE_PACK


def build_constrained_search_snapshot(constrained_search_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(constrained_search_pack) if constrained_search_pack else DEFAULT_CONSTRAINED_SEARCH_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_constrained_candidate_search",
            "artifact_present": False,
            "source_path": str(pack_path),
            "selection_status": "missing",
            "summary": {"walk_forward_accepted": 0, "risk_eligible_candidates": 0, "frontier_candidates": 0},
            "selected_candidate": None,
            "frontier_candidates": [],
            "next_actions": [{"action": "run_constrained_candidate_search", "reason": "constrained search artifact is missing"}],
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_constrained_candidate_search",
            "artifact_present": True,
            "source_path": str(pack_path),
            "selection_status": pack.get("selection_status"),
            "summary": pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {},
            "selected_candidate": pack.get("selected_candidate") if isinstance(pack.get("selected_candidate"), dict) else None,
            "frontier_candidates": (pack.get("frontier_candidates", []) if isinstance(pack.get("frontier_candidates"), list) else [])[:20],
            "next_actions": pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [],
            "outputs": pack.get("outputs", {}) if isinstance(pack.get("outputs"), dict) else {},
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_paper_profile_snapshot(paper_profile_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(paper_profile_pack) if paper_profile_pack else DEFAULT_PAPER_PROFILE_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_paper_profile_optimizer",
            "artifact_present": False,
            "source_path": str(pack_path),
            "selection_status": "missing",
            "paper_trading_allowed": False,
            "live_boundary_allowed": False,
            "summary": {"profile_attempts": 0, "eligible_profiles": 0, "rejected_profiles": 0},
            "selected_profile": None,
            "attempts": [],
            "next_actions": [{"action": "run_paper_profile_optimizer", "reason": "paper profile optimizer artifact is missing"}],
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    attempts = pack.get("attempts", []) if isinstance(pack.get("attempts"), list) else []
    return _sanitize(
        {
            "stage": "gui_paper_profile_optimizer",
            "artifact_present": True,
            "source_path": str(pack_path),
            "selection_status": pack.get("selection_status"),
            "paper_trading_allowed": bool(pack.get("paper_trading_allowed", False)),
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "summary": pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {},
            "policy": pack.get("policy", {}) if isinstance(pack.get("policy"), dict) else {},
            "selected_profile": pack.get("selected_profile") if isinstance(pack.get("selected_profile"), dict) else None,
            "attempts": attempts[:30],
            "next_actions": pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [],
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_profile_observation_snapshot(profile_observation_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(profile_observation_pack) if profile_observation_pack else DEFAULT_PROFILE_OBSERVATION_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_profile_observation",
            "artifact_present": False,
            "source_path": str(pack_path),
            "decision": {
                "observation_status": "missing",
                "paper_observation_allowed": False,
                "stop_reasons": ["profile_observation_artifact_missing"],
            },
            "summary": {"stop_count": 0, "warning_count": 0},
            "paper_profile": {},
            "stop_rules": [],
            "ledger": [],
            "next_actions": [{"action": "run_profile_observation", "reason": "profile observation artifact is missing"}],
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_profile_observation",
            "artifact_present": True,
            "source_path": str(pack_path),
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "summary": pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {},
            "paper_profile": pack.get("paper_profile", {}) if isinstance(pack.get("paper_profile"), dict) else {},
            "stop_rules": (pack.get("stop_rules", []) if isinstance(pack.get("stop_rules"), list) else [])[:40],
            "ledger": (pack.get("ledger", []) if isinstance(pack.get("ledger"), list) else [])[:80],
            "next_actions": pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [],
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_recent_data_refresh_snapshot(recent_data_refresh_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(recent_data_refresh_pack) if recent_data_refresh_pack else DEFAULT_RECENT_DATA_REFRESH_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_recent_data_refresh",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "mode": None,
            "will_download": False,
            "target_window": {},
            "decision": {
                "signal_data_stale_cleared": False,
                "recent_data_ready": False,
                "blockers": ["recent_data_refresh_artifact_missing"],
                "next_daily_ops_allowed": False,
            },
            "coverage": {
                "coverage_status": "missing",
                "processed_rows": 0,
                "latest_data_date": None,
            },
            "readiness": {},
            "next_actions": [{"action": "run_recent_data_refresh", "reason": "recent data refresh artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    coverage = pack.get("coverage", {}) if isinstance(pack.get("coverage"), dict) else {}
    return _sanitize(
        {
            "stage": "gui_recent_data_refresh",
            "artifact_present": True,
            "source_path": str(pack_path),
            "source": pack.get("source"),
            "market": pack.get("market"),
            "status": pack.get("status"),
            "mode": pack.get("mode"),
            "will_download": bool(pack.get("will_download", False)),
            "target_window": pack.get("target_window", {}) if isinstance(pack.get("target_window"), dict) else {},
            "decision": decision,
            "coverage": coverage,
            "readiness": pack.get("readiness", {}) if isinstance(pack.get("readiness"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_post_refresh_replay_snapshot(post_refresh_replay_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(post_refresh_replay_pack) if post_refresh_replay_pack else DEFAULT_POST_REFRESH_REPLAY_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_post_refresh_replay",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "recent_data_refresh": {},
            "daily_ops": {},
            "profile_observation": {},
            "decision": {
                "recent_data_ready": False,
                "daily_ops_paper_allowed": False,
                "profile_observation_allowed": False,
                "post_refresh_replay_allowed": False,
                "blockers": ["post_refresh_replay_artifact_missing"],
            },
            "next_actions": [{"action": "run_post_refresh_replay", "reason": "post-refresh replay artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_post_refresh_replay",
            "artifact_present": True,
            "source_path": str(pack_path),
            "status": pack.get("status"),
            "recent_data_refresh": pack.get("recent_data_refresh", {}) if isinstance(pack.get("recent_data_refresh"), dict) else {},
            "daily_ops": pack.get("daily_ops", {}) if isinstance(pack.get("daily_ops"), dict) else {},
            "profile_observation": pack.get("profile_observation", {}) if isinstance(pack.get("profile_observation"), dict) else {},
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "replay_error": pack.get("replay_error", {}) if isinstance(pack.get("replay_error"), dict) else {},
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_observation_sufficiency_snapshot(observation_sufficiency_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(observation_sufficiency_pack) if observation_sufficiency_pack else DEFAULT_OBSERVATION_SUFFICIENCY_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_observation_sufficiency",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "fills": {"observed_fills": 0, "required_fills": 0, "fill_deficit": 0},
            "recommendation": {
                "priority": "run_observation_sufficiency",
                "threshold_relaxation_allowed": False,
            },
            "decision": {
                "observation_sufficiency_cleared": False,
                "blockers": ["observation_sufficiency_artifact_missing"],
            },
            "next_actions": [{"action": "run_observation_sufficiency", "reason": "observation sufficiency artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_observation_sufficiency",
            "artifact_present": True,
            "source_path": str(pack_path),
            "status": pack.get("status"),
            "fills": pack.get("fills", {}) if isinstance(pack.get("fills"), dict) else {},
            "recommendation": pack.get("recommendation", {}) if isinstance(pack.get("recommendation"), dict) else {},
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_expanded_observation_replay_snapshot(expanded_observation_replay_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(expanded_observation_replay_pack) if expanded_observation_replay_pack else DEFAULT_EXPANDED_OBSERVATION_REPLAY_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_expanded_observation_replay",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "window": {},
            "recent_data_refresh": {},
            "post_refresh_replay": {},
            "final_observation_sufficiency": {},
            "decision": {
                "can_extend_observation_window": False,
                "expanded_observation_cleared": False,
                "blockers": ["expanded_observation_replay_artifact_missing"],
            },
            "next_actions": [{"action": "run_expanded_observation_replay", "reason": "expanded observation replay artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_expanded_observation_replay",
            "artifact_present": True,
            "source_path": str(pack_path),
            "status": pack.get("status"),
            "window": pack.get("window", {}) if isinstance(pack.get("window"), dict) else {},
            "recent_data_refresh": pack.get("recent_data_refresh", {}) if isinstance(pack.get("recent_data_refresh"), dict) else {},
            "post_refresh_replay": pack.get("post_refresh_replay", {}) if isinstance(pack.get("post_refresh_replay"), dict) else {},
            "final_observation_sufficiency": (
                pack.get("final_observation_sufficiency", {}) if isinstance(pack.get("final_observation_sufficiency"), dict) else {}
            ),
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "replay_error": pack.get("replay_error", {}) if isinstance(pack.get("replay_error"), dict) else {},
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_iterative_observation_expansion_snapshot(iterative_observation_expansion_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = (
        Path(iterative_observation_expansion_pack)
        if iterative_observation_expansion_pack
        else DEFAULT_ITERATIVE_OBSERVATION_EXPANSION_PACK
    )
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_iterative_observation_expansion",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "round_count": 0,
            "max_rounds": 0,
            "rounds": [],
            "final_observation_sufficiency": {},
            "decision": {
                "initial_extendable": False,
                "iterative_observation_cleared": False,
                "blockers": ["iterative_observation_expansion_artifact_missing"],
            },
            "next_actions": [{"action": "run_iterative_observation_expansion", "reason": "iterative observation expansion artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_iterative_observation_expansion",
            "artifact_present": True,
            "source_path": str(pack_path),
            "status": pack.get("status"),
            "round_count": int(pack.get("round_count", 0) or 0),
            "max_rounds": int(pack.get("max_rounds", 0) or 0),
            "rounds": (pack.get("rounds", []) if isinstance(pack.get("rounds"), list) else [])[:20],
            "initial_observation_sufficiency": (
                pack.get("initial_observation_sufficiency", {}) if isinstance(pack.get("initial_observation_sufficiency"), dict) else {}
            ),
            "final_observation_sufficiency": (
                pack.get("final_observation_sufficiency", {}) if isinstance(pack.get("final_observation_sufficiency"), dict) else {}
            ),
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "expansion_error": pack.get("expansion_error", {}) if isinstance(pack.get("expansion_error"), dict) else {},
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def build_tushare_activation_gate_snapshot(tushare_activation_gate_pack: str | Path | None = None) -> dict[str, Any]:
    pack_path = Path(tushare_activation_gate_pack) if tushare_activation_gate_pack else DEFAULT_TUSHARE_ACTIVATION_GATE_PACK
    pack = _read_optional_json(pack_path)
    if not pack:
        return {
            "stage": "gui_tushare_activation_gate",
            "artifact_present": False,
            "source_path": str(pack_path),
            "status": "missing",
            "mode": "unknown",
            "source": "tushare",
            "readiness": {},
            "recent_data_refresh": {},
            "post_refresh_replay": {},
            "observation_sufficiency": {},
            "iterative_observation_expansion": {},
            "final_observation_sufficiency": {},
            "stage_ledger": [],
            "decision": {
                "activation_chain_allowed": False,
                "paper_continuation_allowed": False,
                "blockers": ["tushare_activation_gate_artifact_missing"],
            },
            "next_actions": [{"action": "run_tushare_activation_gate", "reason": "Tushare activation gate artifact is missing"}],
            "live_boundary_allowed": False,
            "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        }
    return _sanitize(
        {
            "stage": "gui_tushare_activation_gate",
            "artifact_present": True,
            "source_path": str(pack_path),
            "status": pack.get("status"),
            "mode": pack.get("mode"),
            "source": pack.get("source"),
            "market": pack.get("market"),
            "readiness": pack.get("readiness", {}) if isinstance(pack.get("readiness"), dict) else {},
            "recent_data_refresh": pack.get("recent_data_refresh", {}) if isinstance(pack.get("recent_data_refresh"), dict) else {},
            "post_refresh_replay": pack.get("post_refresh_replay", {}) if isinstance(pack.get("post_refresh_replay"), dict) else {},
            "observation_sufficiency": pack.get("observation_sufficiency", {}) if isinstance(pack.get("observation_sufficiency"), dict) else {},
            "iterative_observation_expansion": (
                pack.get("iterative_observation_expansion", {}) if isinstance(pack.get("iterative_observation_expansion"), dict) else {}
            ),
            "final_observation_sufficiency": (
                pack.get("final_observation_sufficiency", {}) if isinstance(pack.get("final_observation_sufficiency"), dict) else {}
            ),
            "stage_ledger": (pack.get("stage_ledger", []) if isinstance(pack.get("stage_ledger"), list) else [])[:20],
            "decision": pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {},
            "next_actions": (pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else [])[:40],
            "chain_error": pack.get("chain_error", {}) if isinstance(pack.get("chain_error"), dict) else {},
            "live_boundary_allowed": bool(pack.get("live_boundary_allowed", False)),
            "safety": pack.get(
                "safety",
                "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
            ),
        }
    )


def run_demo_research(
    market: str = "ALL",
    factor_name: str = "momentum_2",
    top_n: int = 2,
    cost_bps: float = 5.0,
    start_date: str | None = None,
    end_date: str | None = None,
    benchmark_asset_id: str | None = None,
    cash_annual_return: float = 0.0,
    regime_filter: bool = False,
    regime_lookback: int = 20,
    min_relative_return: float | None = None,
    max_drawdown_limit: float | None = None,
) -> dict[str, Any]:
    return run_gui_research(
        source="demo_fixture",
        market=market,
        factor_name=factor_name,
        factor_windows=(2, 3),
        top_n=top_n,
        cost_bps=cost_bps,
        start_date=start_date,
        end_date=end_date,
        benchmark_asset_id=benchmark_asset_id,
        cash_annual_return=cash_annual_return,
        regime_filter=regime_filter,
        regime_lookback=regime_lookback,
        min_relative_return=min_relative_return,
        max_drawdown_limit=max_drawdown_limit,
    )


def run_gui_research(
    source: str = "demo_fixture",
    data_root: str | Path | None = None,
    market: str = "ALL",
    factor_name: str = "momentum_2",
    factor_windows: tuple[int, ...] | None = None,
    top_n: int = 2,
    cost_bps: float = 5.0,
    start_date: str | None = None,
    end_date: str | None = None,
    forward_horizon: int = 1,
    execution_lag: int = 1,
    rebalance_interval: int = 1,
    portfolio_scope: str | None = None,
    periods_per_year: float | None = None,
    benchmark_asset_id: str | None = None,
    cash_annual_return: float = 0.0,
    regime_filter: bool = False,
    regime_lookback: int = 20,
    min_relative_return: float | None = None,
    max_drawdown_limit: float | None = None,
) -> dict[str, Any]:
    source_name = _normalize_gui_source(source)
    bars = _load_gui_bars(source_name, data_root, market)
    result = run_research_pipeline(
        bars,
        ResearchPipelineConfig(
            factor_name=factor_name,
            factor_windows=_resolve_factor_windows(factor_name, factor_windows),
            market=market,
            start_date=start_date,
            end_date=end_date,
            forward_horizon=forward_horizon,
            execution_lag=execution_lag,
            rebalance_interval=rebalance_interval,
            top_n=top_n,
            cost_bps=cost_bps,
            portfolio_scope=portfolio_scope,
            periods_per_year=periods_per_year,
            benchmark_asset_id=benchmark_asset_id,
            cash_annual_return=cash_annual_return,
            regime_filter=regime_filter,
            regime_lookback=regime_lookback,
            min_relative_return=min_relative_return,
            max_drawdown_limit=max_drawdown_limit,
        ),
    )
    risk = _risk_from_backtest(
        result["metrics"],
        pd.DataFrame(result["equity_curve"]),
        pd.DataFrame(result["trades"]),
    )
    return _sanitize(
        {
            "data_mode": mock_data.DATA_MODE if source_name == "demo_fixture" else result["data_mode"],
            "data_source": source_name,
            "notice": mock_data.DEMO_NOTICE if source_name == "demo_fixture" else "Processed bars research data. No broker account, no live trading, no order placement.",
            "request": result["request"],
            "metrics": result["metrics"],
            "benchmark_metrics": result["benchmark_metrics"],
            "decision": result["decision"],
            "regime": result["regime"],
            "factor_summary": result["factor_summary"],
            "risk": risk,
            "equity_curve": result["equity_curve"],
            "benchmark_curve": result["benchmark_curve"],
            "drawdown_curve": result["drawdown_curve"],
            "regime_curve": result["regime_curve"],
            "ic": result["ic"],
            "group_returns": result["group_returns"],
            "long_short": result["long_short"],
            "trades": result["trades"],
            "holdings": result["holdings"],
        }
    )


def run_demo_signal_snapshot(
    market: str = "ALL",
    factor_name: str = "momentum_2",
    top_n: int = 2,
    as_of_date: str | None = None,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    portfolio_value: float = 100000.0,
) -> dict[str, Any]:
    return run_gui_signal_snapshot(
        source="demo_fixture",
        market=market,
        factor_name=factor_name,
        factor_windows=(2, 3),
        top_n=top_n,
        as_of_date=as_of_date,
        max_asset_weight=max_asset_weight,
        max_market_weight=max_market_weight,
        max_gross_exposure=max_gross_exposure,
        min_cash_weight=min_cash_weight,
        portfolio_value=portfolio_value,
    )


def run_gui_signal_snapshot(
    source: str = "demo_fixture",
    data_root: str | Path | None = None,
    market: str = "ALL",
    factor_name: str = "momentum_2",
    factor_windows: tuple[int, ...] | None = None,
    top_n: int = 2,
    as_of_date: str | None = None,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    portfolio_value: float = 100000.0,
) -> dict[str, Any]:
    source_name = _normalize_gui_source(source)
    snapshot = generate_signal_snapshot(
        _load_gui_bars(source_name, data_root, market),
        SignalPipelineConfig(
            factor_name=factor_name,
            factor_windows=_resolve_factor_windows(factor_name, factor_windows),
            market=market,
            as_of_date=as_of_date,
            top_n=top_n,
            max_asset_weight=max_asset_weight,
            max_market_weight=max_market_weight,
            max_gross_exposure=max_gross_exposure,
            min_cash_weight=min_cash_weight,
        ),
    )
    targets = pd.DataFrame(snapshot["targets"])
    latest_prices = targets[["asset_id", "latest_price"]] if not targets.empty else pd.DataFrame(columns=["asset_id", "latest_price"])
    rebalance_plan = build_rebalance_plan(
        targets,
        pd.DataFrame(columns=["asset_id", "quantity"]),
        latest_prices,
        portfolio_value=portfolio_value,
    )
    return _sanitize(
        {
            **snapshot,
            "data_mode": mock_data.DATA_MODE if source_name == "demo_fixture" else snapshot["data_mode"],
            "data_source": source_name,
            "notice": mock_data.DEMO_NOTICE if source_name == "demo_fixture" else "Processed bars research data. No broker account, no live trading, no order placement.",
            "portfolio_value": portfolio_value,
            "rebalance_plan": _records(rebalance_plan),
        }
    )


def run_demo_paper_simulation(
    market: str = "ALL",
    factor_name: str = "momentum_2",
    top_n: int = 2,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_cash: float = 100000.0,
    commission_bps: float = 5.0,
    slippage_bps: float = 5.0,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    max_drawdown_guard: float | None = None,
    guard_cooldown_periods: int = 0,
) -> dict[str, Any]:
    return run_gui_paper_simulation(
        source="demo_fixture",
        market=market,
        factor_name=factor_name,
        factor_windows=(2, 3),
        top_n=top_n,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        max_asset_weight=max_asset_weight,
        max_market_weight=max_market_weight,
        max_gross_exposure=max_gross_exposure,
        min_cash_weight=min_cash_weight,
        max_drawdown_guard=max_drawdown_guard,
        guard_cooldown_periods=guard_cooldown_periods,
    )


def run_gui_paper_simulation(
    source: str = "demo_fixture",
    data_root: str | Path | None = None,
    market: str = "ALL",
    factor_name: str = "momentum_2",
    factor_windows: tuple[int, ...] | None = None,
    top_n: int = 2,
    rebalance_interval: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_cash: float = 100000.0,
    commission_bps: float = 5.0,
    slippage_bps: float = 5.0,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    periods_per_year: float | None = None,
    max_drawdown_guard: float | None = None,
    guard_cooldown_periods: int = 0,
) -> dict[str, Any]:
    source_name = _normalize_gui_source(source)
    result = run_paper_simulation(
        _load_gui_bars(source_name, data_root, market),
        PaperSimulationConfig(
            market=market,
            factor_name=factor_name,
            factor_windows=_resolve_factor_windows(factor_name, factor_windows),
            top_n=top_n,
            rebalance_interval=rebalance_interval,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            max_asset_weight=max_asset_weight,
            max_market_weight=max_market_weight,
            max_gross_exposure=max_gross_exposure,
            min_cash_weight=min_cash_weight,
            periods_per_year=periods_per_year,
            max_drawdown_guard=max_drawdown_guard,
            guard_cooldown_periods=guard_cooldown_periods,
        ),
    )
    equity_curve = pd.DataFrame(result["equity_curve"])
    result["data_mode"] = mock_data.DATA_MODE if source_name == "demo_fixture" else result["data_mode"]
    result["data_source"] = source_name
    result["notice"] = mock_data.DEMO_NOTICE if source_name == "demo_fixture" else "Processed bars research data. No broker account, no live trading, no order placement."
    result["risk"] = _risk_from_paper(result["metrics"], equity_curve)
    return _sanitize(result)


def build_promotion_ops_snapshot(
    promotion_report: str | Path | None = None,
    provider_status: str | Path | None = None,
    quality_report: str | Path | None = None,
) -> dict[str, Any]:
    report_path = Path(promotion_report) if promotion_report else _first_existing(
        [
            Path("data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json"),
            Path("data/reports/promotion_gate_cn_etf/promotion_report.json"),
        ]
    )
    if report_path is None:
        return {
            "stage": "phase_2_8_promotion_operations",
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
            "summary": {"candidates": 0, "blocked": 0, "research_only": 0, "paper_ready": 0, "manual_live_review": 0, "duplicates": 0},
            "live_review_allowed": False,
            "live_review_blockers": ["promotion_report_missing"],
            "top_candidate": None,
            "candidates": [],
            "duplicate_clusters": [],
            "evidence": {"provider_status_present": False, "quality_report_present": False, "providers_ready": False},
            "next_actions": [{"action": "rerun_promotion_gate", "reason": "promotion report is missing"}],
        }
    provider_path = Path(provider_status) if provider_status else Path("data/reports/provider_status/provider_status.json")
    quality_path = Path(quality_report) if quality_report else Path("data/processed/etf_csv/quality_report_cn_etf.json")
    return _sanitize(build_promotion_operations_console(report_path, provider_path, quality_path))


def build_promotion_review_snapshot(
    promotion_report: str | Path | None = None,
    provider_status: str | Path | None = None,
    quality_report: str | Path | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    console = build_promotion_ops_snapshot(
        promotion_report=promotion_report,
        provider_status=provider_status,
        quality_report=quality_report,
    )
    return _sanitize(build_promotion_review_packet(console, candidate_id=candidate_id))


def build_evidence_refresh_snapshot(
    promotion_report: str | Path | None = None,
    provider_status: str | Path | None = None,
    quality_report: str | Path | None = None,
    candidate_id: str | None = None,
    data_gap_resolution: str | Path | None = None,
    provider_evidence: str | Path | None = None,
    duplicate_registry: str | Path | None = None,
) -> dict[str, Any]:
    review = build_promotion_review_snapshot(
        promotion_report=promotion_report,
        provider_status=provider_status,
        quality_report=quality_report,
        candidate_id=candidate_id,
    )
    return _sanitize(
        build_evidence_refresh_plan(
            review,
            data_gap_resolution=_read_optional_json(Path(data_gap_resolution) if data_gap_resolution else DEFAULT_DATA_GAP_RESOLUTION),
            provider_evidence=_read_optional_json(Path(provider_evidence) if provider_evidence else DEFAULT_PROVIDER_EVIDENCE),
            duplicate_registry=_read_optional_json(Path(duplicate_registry) if duplicate_registry else DEFAULT_DUPLICATE_REGISTRY),
        )
    )


def _filtered_bars(market: str, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    bars = mock_data.demo_bars()
    market_upper = market.upper()
    if market_upper != "ALL":
        bars = bars[bars["market"] == market_upper]
    if start_date:
        start = pd.to_datetime(start_date).date()
        bars = bars[pd.to_datetime(bars["date"]).dt.date >= start]
    if end_date:
        end = pd.to_datetime(end_date).date()
        bars = bars[pd.to_datetime(bars["date"]).dt.date <= end]
    return bars.reset_index(drop=True)


def _normalize_gui_source(source: str) -> str:
    normalized = source.strip().lower().replace("_", "-")
    if normalized in {"demo", "demo-fixture", "fixture"}:
        return "demo_fixture"
    if normalized == "processed-bars":
        return "processed-bars"
    raise ValueError(f"Unsupported GUI data source: {source}")


def _load_gui_bars(source: str, data_root: str | Path | None, market: str) -> pd.DataFrame:
    if source == "demo_fixture":
        return mock_data.demo_bars()
    root = Path(data_root) if data_root is not None else DEFAULT_GUI_PROCESSED_ROOT
    market_upper = market.upper()
    if market_upper != "ALL":
        return load_processed_bars(root, market_upper)
    frames = []
    for item in DEFAULT_GUI_PROCESSED_MARKETS:
        try:
            frames.append(load_processed_bars(root, item))
        except FileNotFoundError:
            continue
    if not frames:
        raise FileNotFoundError(f"No processed bars found under {root}")
    return pd.concat(frames, ignore_index=True)


def _resolve_factor_windows(factor_name: str, explicit: tuple[int, ...] | None) -> tuple[int, ...]:
    if explicit:
        return explicit
    suffix = factor_name.rsplit("_", 1)[-1]
    if suffix.isdigit():
        return (int(suffix),)
    return (2, 3)


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_config_factor_inventory(config_root: Path) -> dict[str, Any]:
    names: set[str] = set()
    files_scanned = 0
    if not config_root.exists():
        return {"factor_names": names, "files_scanned": files_scanned}
    for path in sorted(config_root.rglob("*.json")):
        if not path.is_file():
            continue
        payload = _read_json_any(path)
        if payload is None:
            continue
        files_scanned += 1
        _collect_factor_names_from_config(payload, names)
    return {"factor_names": names, "files_scanned": files_scanned}


def _read_factor_leaderboard_cache(report_root: Path, config_root: Path, limit: int) -> dict[str, Any] | None:
    if report_root != DEFAULT_FACTOR_LEADERBOARD_REPORTS_ROOT or config_root != DEFAULT_FACTOR_LEADERBOARD_CONFIGS_ROOT:
        return None
    if not DEFAULT_FACTOR_LEADERBOARD_CACHE.exists():
        return None
    try:
        age_seconds = time.time() - DEFAULT_FACTOR_LEADERBOARD_CACHE.stat().st_mtime
    except OSError:
        return None
    if age_seconds > 1800:
        return None
    cached = _read_json_any(DEFAULT_FACTOR_LEADERBOARD_CACHE)
    if not isinstance(cached, dict) or cached.get("stage") != "gui_factor_leaderboard":
        return None
    if cached.get("cache_version") != FACTOR_LEADERBOARD_CACHE_VERSION:
        return None
    if isinstance(cached.get("leaderboards"), dict):
        for board in cached["leaderboards"].values():
            if isinstance(board, dict) and isinstance(board.get("rows"), list):
                board["rows"] = board["rows"][:limit]
    rows = cached.get("top20") if isinstance(cached.get("top20"), list) else []
    cached["top20"] = rows[:limit]
    if isinstance(cached.get("summary"), dict):
        cached["summary"]["top_n"] = limit
        cached["summary"]["cache_status"] = "hit"
        cached["summary"]["cache_age_seconds"] = int(age_seconds)
    return cached


def _write_factor_leaderboard_cache(report_root: Path, config_root: Path, snapshot: dict[str, Any]) -> None:
    if report_root != DEFAULT_FACTOR_LEADERBOARD_REPORTS_ROOT or config_root != DEFAULT_FACTOR_LEADERBOARD_CONFIGS_ROOT:
        return
    try:
        DEFAULT_FACTOR_LEADERBOARD_CACHE.parent.mkdir(parents=True, exist_ok=True)
        cache_payload = dict(snapshot)
        if isinstance(cache_payload.get("summary"), dict):
            cache_payload["summary"] = {**cache_payload["summary"], "cache_status": "miss_written"}
        DEFAULT_FACTOR_LEADERBOARD_CACHE.write_text(json.dumps(cache_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return


def _sort_leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            1 if row.get("ranking_quality") == "qualified" else 0,
            1 if row.get("is_primary_market") else 0,
            _numeric_sort_value(row.get("primary_score")),
            _numeric_sort_value(row.get("total_return")),
            _numeric_sort_value(row.get("annualized_return")),
        ),
        reverse=True,
    )


def _rank_leaderboard_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return [{**row, "rank": index} for index, row in enumerate(rows[:limit], start=1)]


def _build_factor_leaderboards(rows: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    primary_rows = [row for row in rows if row.get("market") == PRIMARY_FACTOR_MARKET]
    cn_rows = [row for row in rows if row.get("market") == "CN"]
    return {
        "primary_cn_etf": {
            **FACTOR_LEADERBOARD_GROUPS["primary_cn_etf"],
            "market": PRIMARY_FACTOR_MARKET,
            "rows": _rank_leaderboard_rows(primary_rows, limit),
            "row_count": len(primary_rows),
            "empty_message": "当前没有 CN_ETF 主线候选。先补 ETF 主线回测，再看全部历史榜。",
        },
        "cn_stock_research": {
            **FACTOR_LEADERBOARD_GROUPS["cn_stock_research"],
            "market": "CN",
            "rows": _rank_leaderboard_rows(cn_rows, limit),
            "row_count": len(cn_rows),
            "empty_message": "当前没有 CN 个股辅助研究候选。",
        },
        "all_history": {
            **FACTOR_LEADERBOARD_GROUPS["all_history"],
            "market": "ALL",
            "rows": _rank_leaderboard_rows(rows, limit),
            "row_count": len(rows),
            "empty_message": "当前没有可展示的历史候选。",
        },
    }


def _count_rows_by_market(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(row.get("market") or "UNKNOWN") for row in rows)
    return dict(sorted(counter.items()))


def _count_factor_names_by_market(rows: list[dict[str, Any]]) -> dict[str, int]:
    names_by_market: dict[str, set[str]] = {}
    for row in rows:
        market = str(row.get("market") or "UNKNOWN")
        factor_name = str(row.get("factor_name") or "").strip()
        if not factor_name:
            continue
        names_by_market.setdefault(market, set()).add(factor_name)
    return {market: len(names) for market, names in sorted(names_by_market.items())}


def _collect_factor_names_from_config(value: Any, names: set[str], parent_key: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"factor_name", "source_factor_name", "lead_factor_name", "public_factor_name"}:
                _add_factor_name(item, names)
            elif lowered in {"factor_names", "candidate_factor_names", "candidate_names"}:
                _add_factor_name(item, names)
            _collect_factor_names_from_config(item, names, lowered)
        return
    if isinstance(value, list):
        if parent_key in {"factor_names", "candidate_factor_names", "candidate_names"}:
            _add_factor_name(value, names)
        else:
            for item in value:
                _collect_factor_names_from_config(item, names, parent_key)


def _add_factor_name(value: Any, names: set[str]) -> None:
    if isinstance(value, str):
        text = value.strip()
        if _looks_like_factor_name(text):
            names.add(text)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _add_factor_name(item, names)


def _looks_like_factor_name(text: str) -> bool:
    if not text or len(text) > 180:
        return False
    lowered = text.lower()
    if any(separator in text for separator in ("/", "\\", ":", "\n", "\r")):
        return False
    if lowered.endswith((".json", ".csv", ".parquet", ".md", ".py", ".txt", ".log")):
        return False
    if lowered in {"cn", "cn_etf", "hk", "us", "crypto", "all", "market", "factor"}:
        return False
    return any(ch.isalpha() for ch in text)


def _collect_report_candidate_inventory(
    report_root: Path,
    *,
    max_files: int,
    max_file_bytes: int,
    max_csv_rows_per_file: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    files_scanned = 0
    files_with_candidates = 0
    files_skipped = 0
    warnings: list[str] = []
    if not report_root.exists():
        return {
            "rows": rows,
            "candidate_rows": 0,
            "files_scanned": files_scanned,
            "files_with_candidates": files_with_candidates,
            "files_skipped": files_skipped,
            "warnings": [f"missing reports root: {report_root}"],
        }

    candidate_files = _select_factor_report_files(list(_iter_factor_report_files(report_root)), max_files)
    for path in candidate_files:
        try:
            file_size = path.stat().st_size
        except OSError:
            files_skipped += 1
            continue
        if file_size > max_file_bytes:
            files_skipped += 1
            warnings.append(f"skipped large report file: {path}")
            continue
        before = len(rows)
        if path.suffix.lower() == ".json":
            payload = _read_json_any(path)
            if payload is not None:
                _collect_candidate_rows_from_json(payload, path, rows)
        elif path.suffix.lower() == ".csv":
            _collect_candidate_rows_from_csv(path, rows, max_rows=max_csv_rows_per_file)
        files_scanned += 1
        if len(rows) > before:
            files_with_candidates += 1

    return {
        "rows": rows,
        "candidate_rows": len(rows),
        "files_scanned": files_scanned,
        "files_with_candidates": files_with_candidates,
        "files_skipped": files_skipped,
        "warnings": warnings[:20],
    }


def _select_factor_report_files(files: list[Path], max_files: int) -> list[Path]:
    if len(files) <= max_files:
        return files
    primary_files = [path for path in files if _path_mentions_primary_market(path)]
    auxiliary_files = [path for path in files if not _path_mentions_primary_market(path)]
    primary_quota = min(len(primary_files), max(1, int(max_files * 0.7)))
    selected = primary_files[:primary_quota]
    selected.extend(auxiliary_files[: max_files - len(selected)])
    if len(selected) < max_files:
        selected.extend(primary_files[primary_quota : primary_quota + (max_files - len(selected))])
    return selected[:max_files]


def _path_mentions_primary_market(path: Path) -> bool:
    text = str(path).lower()
    return "cn_etf" in text or "etf" in text


def _iter_factor_report_files(report_root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    seed_file = report_root / "round303_24h_profit_sprint_candidate_metric_files.txt"
    if seed_file.exists():
        try:
            for line in seed_file.read_text(encoding="utf-8").splitlines():
                candidate = Path(line.strip())
                if not candidate.is_absolute():
                    candidate = Path.cwd() / candidate
                if _is_factor_report_file(candidate):
                    files[str(candidate)] = candidate
        except OSError:
            pass

    try:
        children = sorted(report_root.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return []

    for child in children:
        if child.is_file() and _is_factor_report_file(child):
            files[str(child)] = child
            continue
        if not child.is_dir() or not _should_scan_report_dir(child.name):
            continue
        scanned_in_dir = 0
        for path in child.rglob("*"):
            if scanned_in_dir >= 80:
                break
            if _is_factor_report_file(path):
                files[str(path)] = path
                scanned_in_dir += 1
    return sorted(files.values(), key=_factor_report_file_sort_key)


def _factor_report_file_sort_key(path: Path) -> tuple[int, int, str]:
    text = str(path).lower()
    name = path.name.lower()
    market_priority = 0 if ("cn_etf" in text or "etf" in text) else 1
    if "leaderboard" in name:
        file_priority = 0
    elif "candidate" in name:
        file_priority = 1
    elif "factor_summary" in name or "summary" in name:
        file_priority = 2
    elif "promotion" in name or "paper" in name or "portfolio" in name:
        file_priority = 3
    else:
        file_priority = 4
    return (market_priority, file_priority, text)


def _should_scan_report_dir(name: str) -> bool:
    lowered = name.lower()
    skip_markers = (
        "desktop_factor_mining_20260616_0800",
        "gui_browser_smoke",
        "gui_control_center_audit",
        "gui_factor_leaderboard_cache",
        "quant_pm_startup_gate",
        "automation",
        "data_manifest",
    )
    if any(marker in lowered for marker in skip_markers):
        return False
    return any(keyword in lowered for keyword in FACTOR_LEADERBOARD_FILE_KEYWORDS) or "round" in lowered


def _is_factor_report_file(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in {".json", ".csv"}:
        return False
    name = path.name.lower()
    path_text = str(path).lower()
    if name in {"quality_report_cn_etf.json", "gui_operation_ledger.json", "gui_factor_leaderboard_cache.json"}:
        return False
    if "gui_factor_leaderboard_cache" in path_text:
        return False
    detail_file_markers = (
        "diagnostics",
        "ic_observations",
        "monthly_ic",
        "yearly_ic",
        "daily_ic",
        "group_returns",
        "equity_curve",
        "drawdown",
        "holdings",
        "positions",
        "fills",
        "orders",
        "rebalance_plan",
        "trade_log",
        "raw_rows",
    )
    if any(marker in name for marker in detail_file_markers):
        return False
    detail_file_names = {
        "benchmark_metrics.json",
        "decision.json",
        "metrics.json",
        "ic.csv",
        "long_short.csv",
        "regime_curve.csv",
        "benchmark_curve.csv",
        "cn_etf_universe_selection.csv",
    }
    if name in detail_file_names:
        return False
    return any(keyword in name or keyword in path_text for keyword in FACTOR_LEADERBOARD_FILE_KEYWORDS)


def _collect_candidate_rows_from_json(value: Any, source_path: Path, rows: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if _mapping_may_be_factor_candidate(value):
            row = _candidate_row_from_mapping(value, source_path)
            if row is not None:
                rows.append(row)
        for item in value.values():
            _collect_candidate_rows_from_json(item, source_path, rows)
        return
    if isinstance(value, list):
        for item in value:
            _collect_candidate_rows_from_json(item, source_path, rows)


def _mapping_may_be_factor_candidate(mapping: dict[str, Any]) -> bool:
    keys = _collect_candidate_key_leaves(mapping, depth=2)
    return bool(keys & FACTOR_LEADERBOARD_IDENTITY_KEYS) and bool(keys & FACTOR_LEADERBOARD_METRIC_KEYS)


def _collect_candidate_key_leaves(value: Any, *, depth: int) -> set[str]:
    if not isinstance(value, dict):
        return set()
    keys: set[str] = set()
    for key, item in value.items():
        leaf = str(key).rsplit(".", 1)[-1].lower()
        keys.add(leaf)
        if depth > 0 and isinstance(item, dict):
            keys.update(_collect_candidate_key_leaves(item, depth=depth - 1))
    return keys


def _collect_candidate_rows_from_csv(path: Path, rows: list[dict[str, Any]], *, max_rows: int) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, raw_row in enumerate(reader):
                if index >= max_rows:
                    break
                row = _candidate_row_from_mapping(raw_row, path)
                if row is not None:
                    rows.append(row)
    except (OSError, csv.Error, UnicodeDecodeError):
        return


def _candidate_row_from_mapping(mapping: dict[str, Any], source_path: Path) -> dict[str, Any] | None:
    flat = _flatten_scalar_mapping(mapping)
    identity = _candidate_identity(flat)
    has_metric = any(_lookup_numeric_metric(flat, aliases) is not None for aliases in FACTOR_LEADERBOARD_METRIC_ALIASES.values())
    if not identity or not has_metric:
        return None
    factor_name = str(
        _first_present(
            flat,
            (
                "factor_name",
                "factor",
                "public_factor_name",
                "lead_factor_name",
                "source_factor_name",
                "candidate_factor_name",
            ),
        )
        or identity
        or ""
    )
    case_id = str(
        _first_present(flat, ("case_id", "candidate_id", "profile_id", "strategy_id", "id"))
        or identity
        or ""
    )
    if not factor_name and not case_id:
        return None

    normalized: dict[str, Any] = {
        "factor_name": factor_name,
        "case_id": case_id,
        "market": _first_present(flat, ("market", "universe", "asset_market")) or _infer_market_from_text(f"{case_id} {factor_name} {source_path}"),
        "family": _first_present(flat, ("family", "factor_family", "research_family", "source_family")) or _infer_family_from_text(f"{case_id} {factor_name}"),
        "status": _first_present(flat, ("status", "decision_status", "selection_status", "promotion_status", "gate_status")) or "",
        "decision": _first_present(flat, ("decision", "recommendation", "verdict", "promotion_decision")) or "",
        "source_path": str(source_path),
        "source_file": source_path.name,
        "params": _extract_candidate_params(flat),
        "all_data": {key: _coerce_scalar(value) for key, value in flat.items()},
    }
    for canonical, aliases in FACTOR_LEADERBOARD_METRIC_ALIASES.items():
        normalized[canonical] = _lookup_numeric_metric(flat, aliases)
    normalized["has_oos_evidence"] = (
        _lookup_numeric_metric(
            flat,
            (
                "oos_sharpe",
                "out_of_sample_sharpe",
                "walk_forward_sharpe",
                "validation_sharpe",
                "test_sharpe",
            ),
        )
        is not None
    )
    score_metric, score = _leaderboard_score(flat, normalized)
    normalized["score_metric"] = score_metric
    normalized["primary_score"] = score
    quality, quality_reasons = _leaderboard_quality(normalized)
    normalized["ranking_quality"] = quality
    normalized["ranking_reasons"] = quality_reasons
    _apply_factor_leaderboard_verdict(normalized)
    if normalized["primary_score"] is None and not has_metric:
        return None
    return normalized


def _flatten_scalar_mapping(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in mapping.items():
        text_key = str(key)
        dotted = f"{prefix}.{text_key}" if prefix else text_key
        if isinstance(value, dict):
            flat.update(_flatten_scalar_mapping(value, dotted))
        elif isinstance(value, (list, tuple)):
            scalar_items = [_coerce_scalar(item) for item in value if not isinstance(item, (dict, list, tuple))]
            if scalar_items and len(scalar_items) == len(value):
                flat[dotted] = ", ".join(str(item) for item in scalar_items[:20])
        else:
            flat[dotted] = _coerce_scalar(value)
    return flat


def _coerce_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isfinite(number):
            return value
        return None
    text = str(value).strip()
    if text == "":
        return ""
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return text
    if math.isfinite(number):
        return number
    return text


def _candidate_identity(flat: dict[str, Any]) -> str:
    value = _first_present(
        flat,
        (
            "case_id",
            "candidate_id",
            "factor_name",
            "factor",
            "public_factor_name",
            "lead_factor_name",
            "source_factor_name",
            "profile_id",
            "strategy_id",
        ),
    )
    return str(value).strip() if value is not None else ""


def _first_present(flat: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in flat and flat[key] not in {None, ""}:
            return flat[key]
    for key in keys:
        suffix = f".{key}"
        for flat_key, value in flat.items():
            if flat_key.endswith(suffix) and value not in {None, ""}:
                return value
    return None


def _lookup_numeric_metric(flat: dict[str, Any], aliases: tuple[str, ...]) -> float | None:
    for alias in aliases:
        value = flat.get(alias)
        number = _to_float(value)
        if number is not None:
            return number
    for alias in aliases:
        suffix = f".{alias}"
        for key, value in flat.items():
            if key.endswith(suffix):
                number = _to_float(value)
                if number is not None:
                    return number
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    if math.isfinite(number):
        return number
    return None


def _leaderboard_score(flat: dict[str, Any], normalized: dict[str, Any]) -> tuple[str, float | None]:
    for metric in FACTOR_LEADERBOARD_SCORE_PRIORITY:
        number = _lookup_numeric_metric(flat, (metric,))
        if number is not None:
            return metric, number
    for metric in ("sharpe", "rank_ic", "mean_ic", "score", "total_return"):
        number = _to_float(normalized.get(metric))
        if number is not None:
            return metric, number
    return "", None


def _extract_candidate_params(flat: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key, value in flat.items():
        leaf = key.rsplit(".", 1)[-1]
        if leaf in FACTOR_LEADERBOARD_PARAM_KEYS or key.startswith(("params.", "request.", "config.")):
            if value not in {None, ""} and len(params) < 24:
                params[leaf] = value
    return params


def _apply_factor_leaderboard_verdict(row: dict[str, Any]) -> None:
    market = str(row.get("market") or "").upper()
    is_primary = market == PRIMARY_FACTOR_MARKET
    market_role = _leaderboard_market_role(market)
    badges: list[str] = []
    quality = str(row.get("ranking_quality") or "")
    score = _to_float(row.get("primary_score"))
    sharpe = _to_float(row.get("sharpe"))
    drawdown = _to_float(row.get("max_drawdown"))
    has_oos = bool(row.get("has_oos_evidence"))

    row["market"] = market
    row["market_role"] = market_role
    row["is_primary_market"] = is_primary

    if not is_primary:
        badges.append("非ETF主线")
        if market == "CN":
            badges.append("CN个股辅助")
            row["promotion_label"] = "仅辅助研究"
            row["plain_conclusion"] = "这是 CN 个股辅助研究，不是 CN_ETF 主线，不能直接用于ETF轮动或模拟盘推广。"
        else:
            badges.append("非主线市场")
            row["promotion_label"] = "仅历史参考"
            row["plain_conclusion"] = "这条候选不属于 CN_ETF 主线，不能直接用于当前 ETF 轮动项目。"
    else:
        badges.append("CN_ETF主线")
        if quality != "qualified":
            badges.append("样本不足")
            row["promotion_label"] = "不可推广"
            row["plain_conclusion"] = "这是 CN_ETF 主线候选，但样本或交易证据不足，不能推广。"
        else:
            if not has_oos:
                badges.append("缺OOS")
            if (score is not None and score >= 3.0) or (sharpe is not None and sharpe >= 3.0):
                badges.append("疑似过拟合")
            if drawdown is not None and abs(drawdown) >= 0.30:
                badges.append("大回撤")
            if "疑似过拟合" in badges:
                row["promotion_label"] = "疑似过拟合"
                row["plain_conclusion"] = "这是 CN_ETF 主线候选，但收益或 Sharpe 异常高，必须做 OOS、滚动和参数敏感性审计。"
            elif has_oos and str(row.get("score_metric") or "").startswith(("paper", "walk_forward", "oos", "test")):
                row["promotion_label"] = "可进模拟盘观察"
                row["plain_conclusion"] = "这是 CN_ETF 主线候选，已有样本和 OOS/滚动证据，可进入模拟盘观察，但仍不能实盘自动交易。"
            elif has_oos:
                row["promotion_label"] = "可继续研究"
                row["plain_conclusion"] = "这是 CN_ETF 主线候选，已有部分验证证据，适合继续扩样本和审计。"
            else:
                row["promotion_label"] = "仅研究线索"
                row["plain_conclusion"] = "这是 CN_ETF 主线候选，但缺少 OOS/滚动证据，先当研究线索。"

    row["audit_badges"] = badges


def _leaderboard_market_role(market: str) -> str:
    if market == PRIMARY_FACTOR_MARKET:
        return "primary_cn_etf"
    if market == "CN":
        return "cn_stock_auxiliary"
    if market:
        return "other_market_auxiliary"
    return "unknown_market"


def _leaderboard_quality(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    trade_count = _to_float(row.get("trade_count"))
    sample_count = _to_float(row.get("sample_count"))
    source_path = str(row.get("source_path", "")).lower()
    if trade_count is None and sample_count is None:
        reasons.append("missing_sample_evidence")
    if trade_count is not None and trade_count < 30:
        reasons.append("trade_count_below_30")
    if sample_count is not None and sample_count < 30:
        reasons.append("sample_count_below_30")
    if "smoke" in source_path:
        reasons.append("smoke_artifact")
    if row.get("score_metric") == "total_return" and row.get("sharpe") is None and row.get("rank_ic") is None:
        reasons.append("return_only_metric")
    return ("thin_sample" if reasons else "qualified", reasons)


def _infer_market_from_text(text: str) -> str:
    upper = text.upper()
    for market in ("CN_ETF", "CRYPTO", "CN", "HK", "US"):
        if market in upper:
            return market
    return ""


def _infer_family_from_text(text: str) -> str:
    lowered = text.lower()
    family_markers = (
        "moneyflow",
        "turnover",
        "supertrend",
        "rsrs",
        "alpha101",
        "public",
        "daily_basic",
        "profitability",
        "accounting_quality",
        "event",
        "liquidity",
        "volatility",
        "momentum",
        "reversal",
        "smart_money",
    )
    for marker in family_markers:
        if marker in lowered:
            return marker
    return ""


def _dedupe_leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _leaderboard_row_key(row)
        current = best_by_key.get(key)
        if current is None or _numeric_sort_value(row.get("primary_score")) > _numeric_sort_value(current.get("primary_score")):
            best_by_key[key] = row
    return list(best_by_key.values())


def _leaderboard_row_key(row: dict[str, Any]) -> str:
    params = row.get("params") if isinstance(row.get("params"), dict) else {}
    if row.get("case_id"):
        key_payload = {
            "case_id": row.get("case_id"),
            "factor_name": row.get("factor_name"),
            "market": row.get("market"),
        }
        return json.dumps(key_payload, ensure_ascii=False, sort_keys=True, default=str)
    key_payload = {
        "case_id": row.get("case_id"),
        "factor_name": row.get("factor_name"),
        "market": row.get("market"),
        "top_n": params.get("top_n") or params.get("topN"),
        "cost_bps": params.get("cost_bps"),
        "rebalance_interval": params.get("rebalance_interval"),
        "holding_period": params.get("holding_period"),
    }
    return json.dumps(key_payload, ensure_ascii=False, sort_keys=True, default=str)


def _numeric_sort_value(value: Any) -> float:
    number = _to_float(value)
    if number is None:
        return float("-inf")
    return number


def _read_json_any(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _risk_from_backtest(metrics: dict[str, float], equity_curve: pd.DataFrame, trades: pd.DataFrame) -> dict[str, Any]:
    returns = equity_curve["period_return"] if "period_return" in equity_curve.columns else pd.Series(dtype=float)
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    var_95 = float(clean_returns.quantile(0.05)) if not clean_returns.empty else 0.0
    loss_streak = _max_loss_streak(clean_returns)
    exposure = _exposure_by_market(trades)
    return {
        "account_connected": False,
        "volatility": metrics.get("annualized_volatility", 0.0),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
        "var_95": var_95,
        "loss_streak": loss_streak,
        "exposure_by_market": exposure,
        "gross_exposure": sum(abs(value) for value in exposure.values()),
        "anomalies": mock_data.risk_snapshot()["anomalies"],
    }


def _risk_from_paper(metrics: dict[str, float], equity_curve: pd.DataFrame) -> dict[str, Any]:
    returns = equity_curve["period_return"] if "period_return" in equity_curve.columns else pd.Series(dtype=float)
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    var_95 = float(clean_returns.quantile(0.05)) if not clean_returns.empty else 0.0
    return {
        "account_connected": False,
        "volatility": metrics.get("annualized_volatility", 0.0),
        "max_drawdown": metrics.get("max_equity_drawdown", metrics.get("max_drawdown", 0.0)),
        "var_95": var_95,
        "loss_streak": _max_loss_streak(clean_returns),
        "gross_exposure": float(equity_curve["gross_exposure"].max()) if "gross_exposure" in equity_curve.columns and not equity_curve.empty else 0.0,
        "open_positions": metrics.get("open_positions", 0.0),
        "anomalies": [
            {"level": "info", "message": "Paper simulation uses local demo fixture bars only."},
            {"level": "warn", "message": "Simulated fills are not broker executions or live account records."},
        ],
    }


def _max_loss_streak(returns: pd.Series) -> int:
    streak = 0
    max_streak = 0
    for value in returns:
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _exposure_by_market(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty:
        return {}
    latest = trades.sort_values("signal_date").groupby(["signal_date", "market"], as_index=False)["target_weight"].sum()
    last_date = latest["signal_date"].max()
    last = latest[latest["signal_date"] == last_date]
    return {str(row.market): float(row.target_weight) for row in last.itertuples(index=False)}


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
