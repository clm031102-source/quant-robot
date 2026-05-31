from __future__ import annotations

import math
from typing import Any

import pandas as pd

from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness
from quant_robot.gui.fixtures import mock_data
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation
from quant_robot.portfolio.rebalance import build_rebalance_plan
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot


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
            ],
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
    bars = _filtered_bars(market, start_date, end_date)
    result = run_research_pipeline(
        bars,
        ResearchPipelineConfig(
            factor_name=factor_name,
            factor_windows=(2, 3),
            market=market,
            start_date=start_date,
            end_date=end_date,
            top_n=top_n,
            cost_bps=cost_bps,
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
            "data_mode": mock_data.DATA_MODE,
            "notice": mock_data.DEMO_NOTICE,
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
    snapshot = generate_signal_snapshot(
        mock_data.demo_bars(),
        SignalPipelineConfig(
            factor_name=factor_name,
            factor_windows=(2, 3),
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
            "data_mode": mock_data.DATA_MODE,
            "notice": mock_data.DEMO_NOTICE,
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
    result = run_paper_simulation(
        mock_data.demo_bars(),
        PaperSimulationConfig(
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
        ),
    )
    equity_curve = pd.DataFrame(result["equity_curve"])
    result["data_mode"] = mock_data.DATA_MODE
    result["notice"] = mock_data.DEMO_NOTICE
    result["risk"] = _risk_from_paper(result["metrics"], equity_curve)
    return _sanitize(result)


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
