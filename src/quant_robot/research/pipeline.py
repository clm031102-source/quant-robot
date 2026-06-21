from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.daily_basic_technical_combo import (
    DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES,
    compute_daily_basic_technical_combo_factors,
)
from quant_robot.factors.daily_basic_residual_composite import (
    DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES,
    compute_daily_basic_residual_composite_factors,
)
from quant_robot.factors.daily_basic_smart_money_quality import (
    DAILY_BASIC_SMART_MONEY_QUALITY_FACTOR_NAMES,
    compute_daily_basic_smart_money_quality_factors,
)
from quant_robot.factors.daily_basic_public_risk_filter_bridge import (
    DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES,
    compute_daily_basic_public_risk_filter_bridge_factors,
)
from quant_robot.factors.daily_basic_value_liquidity_tail import (
    DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES,
    compute_daily_basic_value_liquidity_tail_factors,
)
from quant_robot.factors.etf_moneyflow_basket import (
    ETF_MONEYFLOW_BASKET_FACTOR_NAMES,
    aggregate_etf_moneyflow_basket_inputs,
    compute_etf_moneyflow_basket_factors,
)
from quant_robot.factors.etf_share_size import ETF_SHARE_SIZE_FACTOR_NAMES, compute_etf_share_size_factors
from quant_robot.factors.etf_theme_breadth import compute_etf_theme_breadth_factors, etf_theme_breadth_factor_names
from quant_robot.factors.public_technical_liquidity import (
    PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES,
    compute_public_technical_liquidity_factors,
)
from quant_robot.factors.public_technical_tail_guard import (
    PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES,
    compute_public_technical_tail_guard_factors,
)
from quant_robot.factors.public_formula_price_volume import (
    PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES,
    compute_public_formula_price_volume_factors,
)
from quant_robot.factors.public_rsrs import PUBLIC_RSRS_FACTOR_NAMES, compute_public_rsrs_factors
from quant_robot.factors.public_trend_volume import (
    PUBLIC_TREND_VOLUME_FACTOR_NAMES,
    compute_public_trend_volume_factors,
)
from quant_robot.factors.public_technical import PUBLIC_TECHNICAL_FACTOR_NAMES, compute_public_technical_factors
from quant_robot.factors.technical import compute_basic_factors, technical_factor_names
from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES, compute_daily_basic_factors
from quant_robot.factors.moneyflow_technical import (
    MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES,
    compute_moneyflow_technical_combo_factors,
)
from quant_robot.factors.tushare_moneyflow import MONEYFLOW_FACTOR_NAMES, compute_moneyflow_factors
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
from quant_robot.storage.cn_etf_theme_map import load_cn_etf_theme_map
from quant_robot.storage.etf_moneyflow_baskets import load_etf_moneyflow_baskets
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs
from quant_robot.schema.factors import FACTOR_COLUMNS
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
    start_date: str | None = None
    end_date: str | None = None
    forward_horizon: int = 1
    execution_lag: int = 1
    rebalance_interval: int = 1
    quantiles: int = 2
    top_n: int = 2
    cost_bps: float = 5.0
    portfolio_scope: str | None = None
    selection_method: str = "top_n"
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
    min_total_return: float | None = None
    min_relative_return: float | None = None
    max_drawdown_limit: float | None = None
    signal_start_date: str | None = None
    signal_end_date: str | None = None
    output_dir: Path | None = None


@dataclass(frozen=True)
class ResearchPipelinePreparedInputs:
    input_fingerprint: str
    data_mode: str
    filtered: pd.DataFrame
    factor_inputs: pd.DataFrame
    selected: pd.DataFrame
    labels: pd.DataFrame
    regime: dict[str, Any]
    ic: pd.DataFrame
    groups: pd.DataFrame
    long_short: pd.DataFrame
    portfolio_scope: str
    periods_per_year: float
    benchmark_curve: pd.DataFrame


def run_research_pipeline(
    bars: pd.DataFrame,
    config: ResearchPipelineConfig,
    *,
    precomputed_factors: pd.DataFrame | None = None,
    prepared_inputs: ResearchPipelinePreparedInputs | None = None,
) -> dict[str, Any]:
    _validate_pipeline_config(config)
    if prepared_inputs is None:
        prepared_inputs = prepare_research_pipeline_inputs(
            bars,
            config,
            precomputed_factors=precomputed_factors,
        )
    else:
        _require_matching_prepared_inputs(prepared_inputs, config)
    return _run_research_pipeline_from_inputs(prepared_inputs, config)


def prepare_research_pipeline_inputs(
    bars: pd.DataFrame,
    config: ResearchPipelineConfig,
    *,
    precomputed_factors: pd.DataFrame | None = None,
) -> ResearchPipelinePreparedInputs:
    _validate_pipeline_config(config)
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
    regime = _regime_summary(filtered, selected, config)
    if config.regime_filter:
        selected = _apply_regime_filter(selected, regime["allowed_dates"])
    ic = compute_ic(selected, labels)
    groups = quantile_group_returns(selected, labels, quantiles=config.quantiles)
    long_short = long_short_returns(selected, labels, quantiles=config.quantiles)
    portfolio_scope = _resolve_portfolio_scope(config)
    periods_per_year = _resolve_periods_per_year(config)
    benchmark_curve = build_benchmark_curve(_comparison_bars(filtered, config), benchmark_asset_id=config.benchmark_asset_id)
    return ResearchPipelinePreparedInputs(
        input_fingerprint=research_input_fingerprint(config),
        data_mode="fixture" if set(filtered["source"].astype(str)) == {"fixture"} else "research",
        filtered=filtered,
        factor_inputs=factor_inputs,
        selected=selected,
        labels=labels,
        regime=regime,
        ic=ic,
        groups=groups,
        long_short=long_short,
        portfolio_scope=portfolio_scope,
        periods_per_year=periods_per_year,
        benchmark_curve=benchmark_curve,
    )


def _run_research_pipeline_from_inputs(
    prepared: ResearchPipelinePreparedInputs,
    config: ResearchPipelineConfig,
) -> dict[str, Any]:
    backtest = run_factor_backtest(
        prepared.selected,
        prepared.filtered,
        top_n=config.top_n,
        cost_bps=config.cost_bps,
        portfolio_scope=prepared.portfolio_scope,
        execution_lag=config.execution_lag,
        holding_period=config.forward_horizon,
        rebalance_interval=config.rebalance_interval,
        target_gross_exposure=config.target_gross_exposure,
        periods_per_year=prepared.periods_per_year,
        commission_bps=config.commission_bps,
        slippage_bps=config.slippage_bps,
        market_impact_bps=config.market_impact_bps,
        max_participation_rate=config.max_participation_rate,
        portfolio_value=config.portfolio_value,
        selection_method=config.selection_method,
    )
    tail_ic = compute_ic(backtest.positions, prepared.labels)
    drawdown = _drawdown_curve(backtest.equity_curve)
    benchmark_metrics = compare_strategy_to_benchmark(
        backtest.equity_curve,
        prepared.benchmark_curve,
        cash_annual_return=config.cash_annual_return,
        periods_per_year=prepared.periods_per_year,
    )
    decision = decision_summary(
        backtest.metrics,
        benchmark_metrics,
        min_total_return=config.min_total_return,
        min_relative_return=config.min_relative_return,
        max_drawdown_limit=config.max_drawdown_limit,
    )
    summary = {**_factor_summary(prepared.ic), **_tail_factor_summary(tail_ic)}
    result = _sanitize(
        {
            "data_mode": prepared.data_mode,
            "request": _config_dict(config, prepared.portfolio_scope, prepared.periods_per_year),
            "metrics": backtest.metrics,
            "benchmark_metrics": benchmark_metrics,
            "decision": decision,
            "regime": {key: value for key, value in prepared.regime.items() if key not in {"allowed_dates", "rows"}},
            "factor_summary": summary,
            "artifact_rows": {
                "bars": len(prepared.filtered),
                "factor_inputs": len(prepared.factor_inputs),
                "factors": len(prepared.selected),
                "labels": len(prepared.labels),
                "ic": len(prepared.ic),
                "tail_ic": len(tail_ic),
                "group_returns": len(prepared.groups),
                "long_short": len(prepared.long_short),
                "trades": len(backtest.trades),
                "holdings": len(backtest.positions),
                "benchmark": len(prepared.benchmark_curve),
                "regime": len(prepared.regime["rows"]),
            },
            "equity_curve": _records(backtest.equity_curve),
            "benchmark_curve": _records(prepared.benchmark_curve),
            "drawdown_curve": _records(drawdown),
            "regime_curve": _records(prepared.regime["rows"]),
            "ic": _records(prepared.ic),
            "tail_ic": _records(tail_ic),
            "group_returns": _records(prepared.groups),
            "long_short": _records(prepared.long_short),
            "trades": _records(backtest.trades),
            "holdings": _records(backtest.positions),
        }
    )
    if config.output_dir is not None:
        _write_artifacts(
            config.output_dir,
            result,
            backtest.equity_curve,
            prepared.benchmark_curve,
            drawdown,
            prepared.regime["rows"],
            prepared.ic,
            tail_ic,
            prepared.groups,
            prepared.long_short,
            backtest.trades,
            backtest.positions,
        )
    return result


_RESEARCH_INPUT_RUNTIME_CONFIG_KEYS = {
    "top_n",
    "cost_bps",
    "cash_annual_return",
    "target_gross_exposure",
    "selection_method",
    "commission_bps",
    "slippage_bps",
    "market_impact_bps",
    "max_participation_rate",
    "portfolio_value",
    "min_total_return",
    "min_relative_return",
    "max_drawdown_limit",
    "output_dir",
}


def research_input_fingerprint(config: ResearchPipelineConfig) -> str:
    data = _config_dict(
        config,
        _resolve_portfolio_scope(config),
        _resolve_periods_per_year(config),
    )
    for key in _RESEARCH_INPUT_RUNTIME_CONFIG_KEYS:
        data.pop(key, None)
    return json.dumps(_sanitize(data), sort_keys=True, separators=(",", ":"))


def _validate_pipeline_config(config: ResearchPipelineConfig) -> None:
    if config.rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    if config.selection_method not in {"top_n", "industry_neutral_top_n"}:
        raise ValueError("selection_method must be 'top_n' or 'industry_neutral_top_n'")


def _require_matching_prepared_inputs(prepared: ResearchPipelinePreparedInputs, config: ResearchPipelineConfig) -> None:
    expected = research_input_fingerprint(config)
    if prepared.input_fingerprint != expected:
        raise ValueError("prepared research inputs do not match the research pipeline configuration")


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
        "daily_basic_technical_combo",
        "daily_basic_residual_composite",
        "daily_basic_smart_money_quality",
        "daily_basic_public_risk_filter_bridge",
        "daily_basic_value_liquidity_tail",
        "tushare_moneyflow",
        "moneyflow_technical_combo",
        "etf_share_size",
        "etf_moneyflow_basket",
        "etf_theme_breadth",
        "public_technical",
        "public_technical_liquidity",
        "public_technical_tail_guard",
        "public_formula_price_volume",
        "public_rsrs",
        "public_trend_volume",
        "combined",
    }:
        raise ValueError(f"Unsupported factor_source: {factor_source}")
    if factor_source in {
        "technical",
        "public_technical",
        "public_technical_liquidity",
        "public_technical_tail_guard",
        "public_formula_price_volume",
        "public_rsrs",
        "public_trend_volume",
    }:
        if config.factor_input_required and config.factor_input_root is None:
            raise ValueError("factor_input_root is required when factor_input_required is true")
        return pd.DataFrame()
    if factor_source == "etf_share_size":
        return _load_etf_share_size_inputs(config)
    if factor_source == "etf_moneyflow_basket":
        return _load_etf_moneyflow_basket_inputs(config)
    if factor_source == "etf_theme_breadth":
        return _load_etf_theme_map_inputs(config)
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


def _load_etf_theme_map_inputs(config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.execution_lag < 1:
        raise ValueError("execution_lag must be at least 1 for ETF theme breadth factors")
    if config.factor_input_root is None:
        raise ValueError("factor_input_root is required for ETF theme breadth factors")
    market = config.market.upper()
    if market == "ALL":
        raise ValueError("ETF theme breadth inputs require a specific CN_ETF market")
    if market != "CN_ETF":
        raise ValueError("ETF theme breadth factor source requires market=CN_ETF")
    return load_cn_etf_theme_map(config.factor_input_root, market)


def _compute_factor_source(bars: pd.DataFrame, factor_inputs: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    if config.factor_source == "technical":
        if config.factor_name not in technical_factor_names(config.factor_windows):
            return _empty_factor_frame()
        return compute_basic_factors(bars, windows=config.factor_windows, factor_names=(config.factor_name,))
    if config.factor_source == "public_technical":
        if config.factor_name not in PUBLIC_TECHNICAL_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_technical_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "public_technical_liquidity":
        if config.factor_name not in PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_technical_liquidity_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "public_technical_tail_guard":
        if config.factor_name not in PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_technical_tail_guard_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "public_formula_price_volume":
        if config.factor_name not in PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_formula_price_volume_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "public_rsrs":
        if config.factor_name not in PUBLIC_RSRS_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_rsrs_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "public_trend_volume":
        if config.factor_name not in PUBLIC_TREND_VOLUME_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_public_trend_volume_factors(bars, factor_names=(config.factor_name,))
    if config.factor_source == "etf_share_size":
        if config.factor_name not in ETF_SHARE_SIZE_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_etf_share_size_factors(factor_inputs)
    if config.factor_source == "etf_moneyflow_basket":
        if config.factor_name not in ETF_MONEYFLOW_BASKET_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_etf_moneyflow_basket_factors(factor_inputs)
    if config.factor_source == "etf_theme_breadth":
        if config.factor_name not in etf_theme_breadth_factor_names(config.factor_windows):
            return _empty_factor_frame()
        return compute_etf_theme_breadth_factors(bars, factor_inputs, windows=config.factor_windows)
    if config.factor_source == "tushare_moneyflow":
        if config.factor_name not in MONEYFLOW_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_moneyflow_factors(factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "moneyflow_technical_combo":
        if config.factor_name not in MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_moneyflow_technical_combo_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "tushare_daily_basic":
        if config.factor_name not in DAILY_BASIC_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_factors(factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "daily_basic_technical_combo":
        if config.factor_name not in DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_technical_combo_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "daily_basic_residual_composite":
        if config.factor_name not in DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_residual_composite_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "daily_basic_smart_money_quality":
        if config.factor_name not in DAILY_BASIC_SMART_MONEY_QUALITY_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_smart_money_quality_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    if config.factor_source == "daily_basic_public_risk_filter_bridge":
        if config.factor_name not in DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_public_risk_filter_bridge_factors(
            bars,
            factor_inputs,
            factor_names=(config.factor_name,),
        )
    if config.factor_source == "daily_basic_value_liquidity_tail":
        if config.factor_name not in DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES:
            return _empty_factor_frame()
        return compute_daily_basic_value_liquidity_tail_factors(bars, factor_inputs, factor_names=(config.factor_name,))
    pieces = []
    if config.factor_name in technical_factor_names(config.factor_windows):
        pieces.append(compute_basic_factors(bars, windows=config.factor_windows, factor_names=(config.factor_name,)))
    if config.factor_name in DAILY_BASIC_FACTOR_NAMES:
        pieces.append(compute_daily_basic_factors(factor_inputs, factor_names=(config.factor_name,)))
    if not pieces:
        return _empty_factor_frame()
    if len(pieces) == 1:
        return pieces[0]
    technical, daily_basic = pieces
    return pd.concat([technical, daily_basic], ignore_index=True).sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=FACTOR_COLUMNS)


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
