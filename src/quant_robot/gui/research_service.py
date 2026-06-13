from __future__ import annotations

import json
import math
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
DEFAULT_CONSTRAINED_SEARCH_PACK = Path("data/reports/constrained_candidate_search/constrained_candidate_search_pack.json")
DEFAULT_PAPER_PROFILE_PACK = Path("data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json")


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
    pack_path = Path(risk_candidate_pack) if risk_candidate_pack else DEFAULT_RISK_CANDIDATE_PACK
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
