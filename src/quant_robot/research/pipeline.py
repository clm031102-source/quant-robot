from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.etf_moneyflow_basket import (
    aggregate_etf_moneyflow_basket_inputs,
    compute_etf_moneyflow_basket_factors,
)
from quant_robot.factors.etf_share_size import compute_etf_share_size_factors
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_inputs import compute_daily_basic_factors
from quant_robot.factors.moneyflow_technical import compute_moneyflow_technical_combo_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
from quant_robot.reports.plots import write_line_svg
from quant_robot.research.decision import (
    build_benchmark_curve,
    compare_strategy_to_benchmark,
    decision_summary,
    regime_allowed_dates,
)
from quant_robot.research.groups import quantile_group_returns
from quant_robot.research.ic import compute_ic
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.long_short import long_short_returns
from quant_robot.storage.etf_moneyflow_baskets import load_etf_moneyflow_baskets
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs
from quant_robot.storage.cn_etf_rotation_membership import filter_signals_to_cn_etf_rotation_membership
from quant_robot.storage.factor_inputs import load_factor_inputs
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs


MIN_IC_OBSERVATIONS_FOR_SIGNIFICANCE = 3
ZERO_VARIANCE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class ResearchPipelineConfig:
    factor_name: str = "momentum_2"
    factor_source: str = "technical"
    factor_windows: tuple[int, ...] = (2, 3)
    factor_input_root: Path | None = None
    factor_input_required: bool = False
    moneyflow_input_root: Path | None = None
    market: str = "ALL"
    rotation_membership_root: Path | None = None
    rotation_membership_required: bool = False
    start_date: str | None = None
    end_date: str | None = None
    forward_horizon: int = 1
    execution_lag: int = 1
    rebalance_interval: int = 1
    quantiles: int = 2
    top_n: int = 2
    cost_bps: float = 5.0
    portfolio_scope: str | None = None
    periods_per_year: float | None = None
    benchmark_asset_id: str | None = None
    cash_annual_return: float = 0.0
    regime_filter: bool = False
    regime_lookback: int = 20
    target_gross_exposure: float = 1.0
    commission_bps: float | None = None
    slippage_bps: float | None = None
    market_impact_bps: float = 0.0
    max_participation_rate: float | None = None
    portfolio_value: float = 1_000_000.0
    min_relative_return: float | None = None
    max_drawdown_limit: float | None = None
    signal_start_date: str | None = None
    signal_end_date: str | None = None
    output_dir: Path | None = None


def run_research_pipeline(
    bars: pd.DataFrame,
    config: ResearchPipelineConfig,
    *,
    precomputed_factors: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if config.rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    filtered = _filter_bars(bars, config)
    validate_market_data(filtered)
    factor_inputs = pd.DataFrame() if precomputed_factors is not None else _load_factor_input_frame(config)
    factors = (
        _filter_precomputed_factors(precomputed_factors, config)
        if precomputed_factors is not None
        else _compute_factor_source(filtered, factor_inputs, config)
    )
    labels = make_forward_returns(filtered, horizons=(config.forward_horizon,), execution_lag=config.execution_lag)
    selected = factors[factors["factor_name"] == config.factor_name].dropna(subset=["factor_value"]).reset_index(drop=True)
    selected = _filter_signals(selected, config)
    selected = filter_signals_to_cn_etf_rotation_membership(
        selected,
        root=config.rotation_membership_root,
        market=config.market,
        required=config.rotation_membership_required,
    )
    regime = _regime_summary(filtered, selected, config)
    if config.regime_filter:
        selected = _apply_regime_filter(selected, regime["allowed_dates"])
    ic = compute_ic(selected, labels)
    groups = quantile_group_returns(selected, labels, quantiles=config.quantiles)
    long_short = long_short_returns(selected, labels, quantiles=config.quantiles)
    portfolio_scope = _resolve_portfolio_scope(config)
    periods_per_year = _resolve_periods_per_year(config)
    backtest = run_factor_backtest(
        selected,
        filtered,
        top_n=config.top_n,
        cost_bps=config.cost_bps,
        portfolio_scope=portfolio_scope,
        execution_lag=config.execution_lag,
        holding_period=config.forward_horizon,
        rebalance_interval=config.rebalance_interval,
        target_gross_exposure=config.target_gross_exposure,
        periods_per_year=periods_per_year,
        commission_bps=config.commission_bps,
        slippage_bps=config.slippage_bps,
        market_impact_bps=config.market_impact_bps,
        max_participation_rate=config.max_participation_rate,
        portfolio_value=config.portfolio_value,
    )
    tail_ic = compute_ic(backtest.positions, labels)
    drawdown = _drawdown_curve(backtest.equity_curve)
    benchmark_curve = build_benchmark_curve(_comparison_bars(filtered, config), benchmark_asset_id=config.benchmark_asset_id)
    benchmark_metrics = compare_strategy_to_benchmark(
        backtest.equity_curve,
        benchmark_curve,
        cash_annual_return=config.cash_annual_return,
        periods_per_year=periods_per_year,
    )
    decision = decision_summary(
        backtest.metrics,
        benchmark_metrics,
        min_relative_return=config.min_relative_return,
        max_drawdown_limit=config.max_drawdown_limit,
    )
    summary = {**_factor_summary(ic), **_tail_factor_summary(tail_ic)}
    result = _sanitize(
        {
            "data_mode": "fixture" if set(filtered["source"].astype(str)) == {"fixture"} else "research",
            "request": _config_dict(config, portfolio_scope, periods_per_year),
            "metrics": backtest.metrics,
            "benchmark_metrics": benchmark_metrics,
            "decision": decision,
            "regime": {key: value for key, value in regime.items() if key not in {"allowed_dates", "rows"}},
            "factor_summary": summary,
            "artifact_rows": {
                "bars": len(filtered),
                "factor_inputs": len(factor_inputs),
                "factors": len(selected),
                "labels": len(labels),
                "ic": len(ic),
                "tail_ic": len(tail_ic),
                "group_returns": len(groups),
                "long_short": len(long_short),
                "trades": len(backtest.trades),
                "holdings": len(backtest.positions),
                "benchmark": len(benchmark_curve),
                "regime": len(regime["rows"]),
            },
            "equity_curve": _records(backtest.equity_curve),
            "benchmark_curve": _records(benchmark_curve),
            "drawdown_curve": _records(drawdown),
            "regime_curve": _records(regime["rows"]),
            "ic": _records(ic),
            "tail_ic": _records(tail_ic),
            "group_returns": _records(groups),
            "long_short": _records(long_short),
            "trades": _records(backtest.trades),
            "holdings": _records(backtest.positions),
        }
    )
    if config.output_dir is not None:
        _write_artifacts(
            config.output_dir,
            result,
            backtest.equity_curve,
            benchmark_curve,
            drawdown,
            regime["rows"],
            ic,
            tail_ic,
            groups,
            long_short,
            backtest.trades,
            backtest.positions,
        )
    return result


def _filter_bars(bars: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _load_factor_input_frame(config: ResearchPipelineConfig) -> pd.DataFrame:
    factor_source = config.factor_source
    if factor_source not in {
        "technical",
        "tushare_daily_basic",
        "tushare_moneyflow",
        "moneyflow_technical_combo",
        "etf_share_size",
        "etf_moneyflow_basket",
        "combined",
    }:
        raise ValueError(f"Unsupported factor_source: {factor_source}")
    if factor_source == "technical":
        if config.factor_input_required and config.factor_input_root is None:
            raise ValueError("factor_input_root is required when factor_input_required is true")
        return pd.DataFrame()
    if factor_source == "etf_share_size":
        return _load_etf_share_size_inputs(config)
    if factor_source == "etf_moneyflow_basket":
        return _load_etf_moneyflow_basket_inputs(config)
    if factor_source in {"tushare_moneyflow", "moneyflow_technical_combo"}:
        return _load_tushare_moneyflow_inputs(config)
    return _load_tushare_daily_basic_inputs(config)


def _load_tushare_daily_basic_inputs(config: ResearchPipelineConfig) -> pd.DataFrame:
    factor_source = config.factor_source
    if config.execution_lag < 1:
        raise ValueError("execution_lag must be at least 1 for Tushare daily-basic factors")
    if config.factor_input_root is None:
        if factor_source == "tushare_daily_basic" or config.factor_input_required:
            raise ValueError("factor_input_root is required for Tushare daily-basic factor sources")
        return pd.DataFrame()
    market = config.market.upper()
    if market == "ALL":
        raise ValueError("Tushare daily-basic factor inputs require a specific CN market")
    frame = load_factor_inputs(config.factor_input_root, market)
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _load_tushare_moneyflow_inputs(config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.execution_lag < 1:
        raise ValueError("execution_lag must be at least 1 for Tushare moneyflow factors")
    if config.moneyflow_input_root is None:
        raise ValueError("moneyflow_input_root is required for Tushare moneyflow factor sources")
    market = config.market.upper()
    if market == "ALL":
        raise ValueError("Tushare moneyflow inputs require a specific CN market")
    frame = load_moneyflow_inputs(config.moneyflow_input_root, market)
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _load_etf_share_size_inputs(config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.execution_lag < 1:
        raise ValueError("execution_lag must be at least 1 for ETF share-size factors")
    if config.factor_input_root is None:
        raise ValueError("factor_input_root is required for ETF share-size factor sources")
    market = config.market.upper()
    if market == "ALL":
        raise ValueError("ETF share-size inputs require a specific CN_ETF market")
    if market != "CN_ETF":
        raise ValueError("ETF share-size factor source requires market=CN_ETF")
    frame = load_etf_share_size_inputs(config.factor_input_root, market)
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _load_etf_moneyflow_basket_inputs(config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.execution_lag < 1:
        raise ValueError("execution_lag must be at least 1 for ETF moneyflow basket factors")
    if config.factor_input_root is None:
        raise ValueError("factor_input_root is required for ETF moneyflow basket mappings")
    if config.moneyflow_input_root is None:
        raise ValueError("moneyflow_input_root is required for ETF moneyflow basket factors")
    market = config.market.upper()
    if market == "ALL":
        raise ValueError("ETF moneyflow basket inputs require a specific CN_ETF market")
    if market != "CN_ETF":
        raise ValueError("ETF moneyflow basket factor source requires market=CN_ETF")
    moneyflow = load_moneyflow_inputs(config.moneyflow_input_root, "CN")
    if config.start_date:
        moneyflow = moneyflow[pd.to_datetime(moneyflow["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        moneyflow = moneyflow[pd.to_datetime(moneyflow["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    baskets = load_etf_moneyflow_baskets(config.factor_input_root, market)
    return aggregate_etf_moneyflow_basket_inputs(moneyflow, baskets)


def _compute_factor_source(bars: pd.DataFrame, factor_inputs: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.factor_source == "technical":
        return compute_basic_factors(bars, windows=config.factor_windows)
    if config.factor_source == "etf_share_size":
        return compute_etf_share_size_factors(factor_inputs)
    if config.factor_source == "etf_moneyflow_basket":
        return compute_etf_moneyflow_basket_factors(factor_inputs)
    if config.factor_source == "tushare_moneyflow":
        return compute_moneyflow_factors(factor_inputs)
    if config.factor_source == "moneyflow_technical_combo":
        return compute_moneyflow_technical_combo_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    daily_basic = compute_daily_basic_factors(factor_inputs)
    if config.factor_source == "tushare_daily_basic":
        return daily_basic
    technical = compute_basic_factors(bars, windows=config.factor_windows)
    return pd.concat([technical, daily_basic], ignore_index=True).sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _filter_precomputed_factors(factors: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    frame = factors.copy()
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.reset_index(drop=True)


def _filter_signals(factors: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    frame = factors.copy()
    if config.signal_start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.signal_start_date).date()]
    if config.signal_end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.signal_end_date).date()]
    if config.rebalance_interval > 1 and not frame.empty:
        signal_dates = sorted(pd.to_datetime(frame["date"]).dt.date.unique())
        keep_dates = set(signal_dates[:: config.rebalance_interval])
        frame = frame[pd.to_datetime(frame["date"]).dt.date.isin(keep_dates)]
    return frame.reset_index(drop=True)


def _comparison_bars(bars: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    frame = bars.copy()
    if config.signal_start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.signal_start_date).date()]
    if config.signal_end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.signal_end_date).date()]
    return frame.reset_index(drop=True)


def _regime_summary(bars: pd.DataFrame, selected: pd.DataFrame, config: ResearchPipelineConfig) -> dict[str, Any]:
    if not config.regime_filter:
        return {
            "enabled": False,
            "lookback": config.regime_lookback,
            "blocked_signal_dates": 0,
            "allowed_dates": None,
            "rows": pd.DataFrame(columns=["date", "regime_momentum", "regime_allowed"]),
        }
    rows = regime_allowed_dates(bars, benchmark_asset_id=config.benchmark_asset_id, lookback=config.regime_lookback)
    allowed_dates = set(rows.loc[rows["regime_allowed"], "date"])
    signal_dates = set(pd.to_datetime(selected["date"]).dt.date.unique()) if not selected.empty else set()
    return {
        "enabled": True,
        "lookback": config.regime_lookback,
        "blocked_signal_dates": len(signal_dates - allowed_dates),
        "allowed_dates": allowed_dates,
        "rows": rows,
    }


def _apply_regime_filter(factors: pd.DataFrame, allowed_dates: set[Any] | None) -> pd.DataFrame:
    if factors.empty or not allowed_dates:
        return factors.iloc[0:0].copy()
    dates = pd.to_datetime(factors["date"]).dt.date
    return factors[dates.isin(allowed_dates)].reset_index(drop=True)


def _resolve_portfolio_scope(config: ResearchPipelineConfig) -> str:
    if config.portfolio_scope is not None:
        return config.portfolio_scope
    return "global" if config.market.upper() == "ALL" else "market"


def _resolve_periods_per_year(config: ResearchPipelineConfig) -> float:
    if config.periods_per_year is not None:
        return config.periods_per_year
    base_periods = 365 if config.market.upper() == "CRYPTO" else 252
    return base_periods / float(max(config.rebalance_interval, 1))


def _factor_summary(ic: pd.DataFrame) -> dict[str, float | int | str]:
    if ic.empty:
        return {
            "mean_ic": 0.0,
            "mean_rank_ic": 0.0,
            "icir": 0.0,
            "ic_observations": 0,
            "positive_ic_rate": 0.0,
            "ic_t_stat": 0.0,
            "ic_p_value": 1.0,
            "rank_ic_t_stat": 0.0,
            "rank_ic_p_value": 1.0,
            "significance_status": "insufficient_data",
        }
    clean_ic = pd.to_numeric(ic["ic"], errors="coerce").dropna()
    clean_rank = pd.to_numeric(ic["rank_ic"], errors="coerce").dropna()
    mean_ic = float(clean_ic.mean()) if not clean_ic.empty else 0.0
    std_ic = float(clean_ic.std(ddof=0)) if not clean_ic.empty else 0.0
    ic_t_stat, ic_p_value = _guarded_series_t_test(clean_ic)
    rank_t_stat, rank_p_value = _guarded_series_t_test(clean_rank)
    return {
        "mean_ic": mean_ic,
        "mean_rank_ic": float(clean_rank.mean()) if not clean_rank.empty else 0.0,
        "icir": 0.0 if std_ic == 0.0 else float(mean_ic / std_ic),
        "ic_observations": int(len(clean_ic)),
        "positive_ic_rate": float((clean_ic > 0).mean()) if not clean_ic.empty else 0.0,
        "ic_t_stat": ic_t_stat,
        "ic_p_value": ic_p_value,
        "rank_ic_t_stat": rank_t_stat,
        "rank_ic_p_value": rank_p_value,
        "significance_status": _significance_status(mean_ic, ic_p_value, len(clean_ic), std_ic),
    }


def _tail_factor_summary(ic: pd.DataFrame) -> dict[str, float | int | str]:
    return {f"tail_{key}": value for key, value in _factor_summary(ic).items()}


def _guarded_series_t_test(values: pd.Series) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < MIN_IC_OBSERVATIONS_FOR_SIGNIFICANCE:
        return 0.0, 1.0
    if _is_zero_variance(float(clean.std(ddof=0))):
        return 0.0, 1.0
    return _series_t_test(clean)


def _series_t_test(values: pd.Series) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    observations = len(clean)
    if observations < MIN_IC_OBSERVATIONS_FOR_SIGNIFICANCE:
        return 0.0, 1.0
    mean = float(clean.mean())
    std = float(clean.std(ddof=1))
    if _is_zero_variance(std):
        return 0.0, 1.0
    t_stat = mean / (std / math.sqrt(observations))
    p_value = math.erfc(abs(t_stat) / math.sqrt(2.0))
    return t_stat, max(min(p_value, 1.0), 0.0)


def _significance_status(mean_ic: float, p_value: float, observations: int, std_ic: float) -> str:
    if observations < MIN_IC_OBSERVATIONS_FOR_SIGNIFICANCE or _is_zero_variance(std_ic):
        return "insufficient_data"
    if p_value <= 0.05 and mean_ic > 0.0:
        return "significant_positive"
    if p_value <= 0.05 and mean_ic < 0.0:
        return "significant_negative"
    return "not_significant"


def _is_zero_variance(value: float) -> bool:
    return math.isclose(value, 0.0, abs_tol=ZERO_VARIANCE_TOLERANCE)


def _drawdown_curve(equity_curve: pd.DataFrame) -> pd.DataFrame:
    if equity_curve.empty:
        return pd.DataFrame(columns=["date", "drawdown"])
    frame = equity_curve[["date", "equity"]].copy()
    frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1.0
    return frame[["date", "drawdown"]]


def _write_artifacts(
    output_dir: Path,
    result: dict[str, Any],
    equity_curve: pd.DataFrame,
    benchmark_curve: pd.DataFrame,
    drawdown: pd.DataFrame,
    regime: pd.DataFrame,
    ic: pd.DataFrame,
    tail_ic: pd.DataFrame,
    groups: pd.DataFrame,
    long_short: pd.DataFrame,
    trades: pd.DataFrame,
    holdings: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps({"data_mode": result["data_mode"], **result["metrics"]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "benchmark_metrics.json").write_text(json.dumps(result["benchmark_metrics"], indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "decision.json").write_text(json.dumps(result["decision"], indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "factor_summary.json").write_text(json.dumps(result["factor_summary"], indent=2, sort_keys=True), encoding="utf-8")
    equity_curve.to_csv(output_dir / "equity_curve.csv", index=False)
    benchmark_curve.to_csv(output_dir / "benchmark_curve.csv", index=False)
    drawdown.to_csv(output_dir / "drawdown_curve.csv", index=False)
    regime.to_csv(output_dir / "regime_curve.csv", index=False)
    ic.to_csv(output_dir / "ic.csv", index=False)
    tail_ic.to_csv(output_dir / "tail_ic.csv", index=False)
    groups.to_csv(output_dir / "group_returns.csv", index=False)
    long_short.to_csv(output_dir / "long_short.csv", index=False)
    trades.to_csv(output_dir / "trades.csv", index=False)
    holdings.to_csv(output_dir / "holdings.csv", index=False)
    write_line_svg(equity_curve, "date", "equity", output_dir / "equity_curve.svg", "Research Pipeline Equity")
    write_line_svg(drawdown, "date", "drawdown", output_dir / "drawdown_curve.svg", "Research Pipeline Drawdown")
    write_line_svg(ic, "date", "ic", output_dir / "ic.svg", "Research Pipeline IC")


def _config_dict(config: ResearchPipelineConfig, portfolio_scope: str, periods_per_year: float) -> dict[str, Any]:
    data = asdict(config)
    data["factor_windows"] = list(config.factor_windows)
    data["factor_input_root"] = str(config.factor_input_root) if config.factor_input_root is not None else None
    data["moneyflow_input_root"] = str(config.moneyflow_input_root) if config.moneyflow_input_root is not None else None
    data["rotation_membership_root"] = (
        str(config.rotation_membership_root) if config.rotation_membership_root is not None else None
    )
    data["portfolio_scope"] = portfolio_scope
    data["periods_per_year"] = periods_per_year
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    return data


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
