from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.cn_calendar_seasonality_preregistration import SAFETY, default_cn_calendar_seasonality_specs
from quant_robot.ops.cn_calendar_seasonality_residual_prescreen import (
    build_cn_calendar_seasonality_exposure_frame,
    build_cn_calendar_seasonality_factor_frame,
    build_cn_calendar_seasonality_feature_frame,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (
    DEFAULT_RESIDUAL_EXPOSURES,
    _load_stock_basic,
    _merge_lead_exposures,
    industry_neutralize_technical_lead,
    residualize_technical_lead,
)


STAGE = "cn_calendar_pre_holiday_cost_capacity_preflight"
DEFAULT_FACTOR_NAME = "pre_holiday_liquidity_avoidance_5_3"
DEFAULT_COST_BPS_VALUES = (5.0, 10.0, 20.0)
DEFAULT_PORTFOLIO_VALUES = (100_000.0, 500_000.0, 1_000_000.0, 5_000_000.0)
DEFAULT_TOP_N = 100
DEFAULT_HOLDING_PERIOD = 5
DEFAULT_REBALANCE_INTERVAL = 1
DEFAULT_EXECUTION_LAG = 1
DEFAULT_MARKET_IMPACT_BPS = 10.0
DEFAULT_MIN_SIGNAL_AMOUNT = 10_000_000.0
DEFAULT_MAX_PARTICIPATION_RATE = 0.01
DEFAULT_MAX_CALENDAR_HOLDING_DAYS = 20
DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE = 0.50
DEFAULT_MAX_DRAWDOWN_FLOOR = -0.40
DEFAULT_PERIODS_PER_YEAR = 21.0
NEXT_WALK_FORWARD = "round166_pre_holiday_liquidity_avoidance_walk_forward_validation"
NEXT_HIBERNATE = "round166_calendar_seasonality_hibernation_after_cost_capacity_failure"

LEADERBOARD_COLUMNS = [
    "case_id",
    "factor_name",
    "market",
    "top_n",
    "holding_period",
    "rebalance_interval",
    "execution_lag",
    "cost_bps",
    "market_impact_bps",
    "portfolio_value",
    "trades",
    "signals_before_tradeability_filter",
    "signals_filtered_min_signal_amount",
    "calendar_limited_trades",
    "total_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "overlap_newey_west_t_stat_mean",
    "overlap_effective_sample_size",
    "max_drawdown",
    "win_rate",
    "turnover",
    "average_holdings",
    "avg_cost_rate",
    "max_cost_rate",
    "avg_participation_rate",
    "max_participation_rate",
    "capacity_limited_trades",
    "max_abs_trade_gross_return",
    "p99_abs_trade_gross_return",
    "hard_blocked",
    "walk_forward_candidate",
    "blockers",
]


def build_cn_calendar_pre_holiday_cost_capacity_preflight(
    *,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    stock_basic: str | Path | pd.DataFrame | None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    factor_name: str = DEFAULT_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION_RATE,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    raw_bars = _load_or_filter_bars(
        bars=bars,
        bars_roots=bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    features = build_cn_calendar_seasonality_feature_frame(
        raw_bars,
        horizons=(int(holding_period),),
        execution_lag=execution_lag,
    )
    residual_factors = build_pre_holiday_residual_factor_frame(
        features,
        stock_basic=stock_basic_frame,
        factor_name=factor_name,
        min_signal_date_amount=min_signal_date_amount,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    result = summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
        residual_factors,
        raw_bars,
        factor_name=factor_name,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        min_signal_amount=min_signal_amount,
        max_participation_rate=max_participation_rate,
        market_impact_bps=market_impact_bps,
        max_calendar_holding_days=max_calendar_holding_days,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
        periods_per_year=periods_per_year,
    )
    result["data_window"] = _data_window(raw_bars, residual_factors)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_walk_forward_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round164_calendar_seasonality_residual_prescreen",
        "source_report": "docs/research/cn_stock_cn_calendar_seasonality_residual_prescreen_round164_2026-06-23.md",
        "scope": "single frozen pre-holiday residual lead; no calendar parameter expansion",
    }
    result["markdown"] = render_cn_calendar_pre_holiday_cost_capacity_preflight_markdown(result)
    return result


def build_pre_holiday_residual_factor_frame(
    features: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    factor_name: str = DEFAULT_FACTOR_NAME,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> pd.DataFrame:
    spec = _lead_spec(factor_name)
    raw = build_cn_calendar_seasonality_factor_frame(
        features,
        candidate_specs=[spec],
        min_signal_date_amount=min_signal_date_amount,
    )
    exposure = build_cn_calendar_seasonality_exposure_frame(features, stock_basic)
    lead_with_exposures = _merge_lead_exposures(raw, exposure)
    industry = industry_neutralize_technical_lead(
        lead_with_exposures,
        industry_factor_name=f"{factor_name}_industry_neutral",
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    residual = residualize_technical_lead(
        industry,
        exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
        residual_factor_name=f"{factor_name}_industry_size_liquidity_vol_residual",
        min_cross_section=min_cross_section,
    )
    if residual.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    frame = residual[["date", "asset_id", "market", "factor_value"]].copy()
    frame["factor_name"] = factor_name
    return frame[["date", "asset_id", "market", "factor_name", "factor_value"]].dropna(subset=["factor_value"])


def summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    factor_name: str = DEFAULT_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION_RATE,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
) -> dict[str, Any]:
    _validate_inputs(top_n=top_n, holding_period=holding_period, rebalance_interval=rebalance_interval)
    prepared_factors = _filter_rebalance_dates(_prepare_factors(factor_frame, factor_name), rebalance_interval)
    prepared_bars = _prepare_bars(bars)
    leaderboard: list[dict[str, Any]] = []
    for cost_bps in cost_bps_values:
        for portfolio_value in portfolio_values:
            backtest = run_factor_backtest(
                prepared_factors,
                prepared_bars,
                top_n=top_n,
                cost_bps=float(cost_bps),
                portfolio_scope="market",
                execution_lag=execution_lag,
                holding_period=holding_period,
                rebalance_interval=1,
                target_gross_exposure=1.0,
                periods_per_year=float(periods_per_year),
                market_impact_bps=market_impact_bps,
                max_participation_rate=max_participation_rate,
                min_signal_amount=min_signal_amount,
                max_calendar_holding_days=max_calendar_holding_days,
                portfolio_value=float(portfolio_value),
            )
            leaderboard.append(
                _case_row(
                    backtest.metrics,
                    backtest.trades,
                    factor_name=factor_name,
                    top_n=top_n,
                    holding_period=holding_period,
                    rebalance_interval=rebalance_interval,
                    execution_lag=execution_lag,
                    cost_bps=float(cost_bps),
                    market_impact_bps=market_impact_bps,
                    portfolio_value=float(portfolio_value),
                    min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
                    max_drawdown_floor=max_drawdown_floor,
                )
            )
    walk_forward_candidates = [row for row in leaderboard if row["walk_forward_candidate"]]
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "thresholds": {
            "factor_name": factor_name,
            "cost_bps_values": [float(value) for value in cost_bps_values],
            "portfolio_values": [float(value) for value in portfolio_values],
            "top_n": int(top_n),
            "holding_period": int(holding_period),
            "rebalance_interval": int(rebalance_interval),
            "execution_lag": int(execution_lag),
            "periods_per_year": float(periods_per_year),
            "min_signal_amount": float(min_signal_amount),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "max_calendar_holding_days": int(max_calendar_holding_days or 0),
            "min_overlap_adjusted_sharpe": float(min_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
        },
        "summary": _summary(prepared_factors, leaderboard),
        "portfolio_preflight_policy": {
            "walk_forward_allowed_candidates": len(walk_forward_candidates),
            "allowed_case_ids": [row["case_id"] for row in walk_forward_candidates],
            "scope": "single frozen pre-holiday residual lead only; no holiday-window parameter expansion",
            "next_direction": NEXT_WALK_FORWARD if walk_forward_candidates else NEXT_HIBERNATE,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "cost_capacity_preflight_is_not_walk_forward",
                "regime_coverage_not_yet_verified",
                "final_holdout_not_read",
            ],
        },
        "leaderboard": leaderboard,
        "next_direction": NEXT_WALK_FORWARD if walk_forward_candidates else NEXT_HIBERNATE,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_calendar_pre_holiday_cost_capacity_preflight_markdown(result)
    return result


def write_cn_calendar_pre_holiday_cost_capacity_preflight(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "cn_calendar_pre_holiday_cost_capacity_preflight.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_calendar_pre_holiday_cost_capacity_preflight.md").write_text(
        render_cn_calendar_pre_holiday_cost_capacity_preflight_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", []), columns=LEADERBOARD_COLUMNS).to_csv(
        output_path / "cn_calendar_pre_holiday_cost_capacity_preflight_leaderboard.csv",
        index=False,
    )


def render_cn_calendar_pre_holiday_cost_capacity_preflight_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    policy = result.get("portfolio_preflight_policy", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# CN Calendar Pre-Holiday Cost Capacity Preflight Round165",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Factor: {thresholds.get('factor_name', DEFAULT_FACTOR_NAME)}",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Signal rows: {summary.get('signal_rows', 0)}",
        f"- Signal dates: {summary.get('signal_dates', 0)}",
        f"- Walk-forward allowed candidates: {policy.get('walk_forward_allowed_candidates', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: {result.get('next_direction', NEXT_HIBERNATE)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Frozen Parameters",
        "",
        f"- TopN: {thresholds.get('top_n')}",
        f"- Holding period: {thresholds.get('holding_period')}",
        f"- Rebalance interval over signal dates: {thresholds.get('rebalance_interval')}",
        f"- Periods per year: {thresholds.get('periods_per_year')}",
        f"- Cost bps values: {thresholds.get('cost_bps_values')}",
        f"- Portfolio values: {thresholds.get('portfolio_values')}",
        "",
        "## Leaderboard",
        "",
        "| Case | Cost | Capital | Total | Ann | Sharpe | Overlap Sharpe | MaxDD | Win | Trades | CapLimited | Candidate | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "| {case} | {cost:.1f} | {capital:.0f} | {total:.2%} | {ann:.2%} | {sharpe:.3f} | {overlap:.3f} | {dd:.2%} | {win:.1%} | {trades} | {cap} | {cand} | {blockers} |".format(
                case=row.get("case_id", ""),
                cost=_number(row.get("cost_bps")),
                capital=_number(row.get("portfolio_value")),
                total=_number(row.get("total_return")),
                ann=_number(row.get("annualized_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                win=_number(row.get("win_rate")),
                trades=int(_number(row.get("trades"))),
                cap=int(_number(row.get("capacity_limited_trades"))),
                cand="yes" if row.get("walk_forward_candidate") else "no",
                blockers=row.get("blockers", "") or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can only allow walk-forward validation; it cannot promote a factor.",
            "- A single residual lead is not permission to tune holiday windows or broaden the calendar family.",
        ]
    )
    return "\n".join(lines) + "\n"


def _case_row(
    metrics: dict[str, Any],
    trades: pd.DataFrame,
    *,
    factor_name: str,
    top_n: int,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    cost_bps: float,
    market_impact_bps: float,
    portfolio_value: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
) -> dict[str, Any]:
    blockers = _blockers(
        metrics,
        trades=trades,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
    )
    hard_blocked = bool(blockers)
    walk_forward_candidate = bool(not hard_blocked and cost_bps > 0.0)
    case_id = (
        f"CN_{factor_name}_top{top_n}_hold{holding_period}_reb{rebalance_interval}_"
        f"lag{execution_lag}_cost{_case_number(cost_bps)}_cap{_case_number(portfolio_value)}"
    )
    return _sanitize(
        {
            "case_id": case_id,
            "factor_name": factor_name,
            "market": "CN",
            "top_n": int(top_n),
            "holding_period": int(holding_period),
            "rebalance_interval": int(rebalance_interval),
            "execution_lag": int(execution_lag),
            "cost_bps": float(cost_bps),
            "market_impact_bps": float(market_impact_bps),
            "portfolio_value": float(portfolio_value),
            "trades": int(len(trades)),
            "signals_before_tradeability_filter": int(_metric(metrics, "signals_before_tradeability_filter")),
            "signals_filtered_min_signal_amount": int(_metric(metrics, "signals_filtered_min_signal_amount")),
            "calendar_limited_trades": int(_metric(metrics, "calendar_limited_trades")),
            "total_return": _metric(metrics, "total_return"),
            "annualized_return": _metric(metrics, "annualized_return"),
            "annualized_volatility": _metric(metrics, "annualized_volatility"),
            "sharpe": _metric(metrics, "sharpe"),
            "overlap_autocorr_adjusted_sharpe": _metric(metrics, "overlap_autocorr_adjusted_sharpe"),
            "overlap_newey_west_t_stat_mean": _metric(metrics, "overlap_newey_west_t_stat_mean"),
            "overlap_effective_sample_size": _metric(metrics, "overlap_effective_sample_size"),
            "max_drawdown": _metric(metrics, "max_drawdown"),
            "win_rate": _metric(metrics, "win_rate"),
            "turnover": _metric(metrics, "turnover"),
            "average_holdings": _metric(metrics, "average_holdings"),
            "avg_cost_rate": _metric(metrics, "avg_cost_rate"),
            "max_cost_rate": _metric(metrics, "max_cost_rate"),
            "avg_participation_rate": _metric(metrics, "avg_participation_rate"),
            "max_participation_rate": _metric(metrics, "max_participation_rate"),
            "capacity_limited_trades": int(_metric(metrics, "capacity_limited_trades")),
            "max_abs_trade_gross_return": _metric(metrics, "max_abs_trade_gross_return"),
            "p99_abs_trade_gross_return": _metric(metrics, "p99_abs_trade_gross_return"),
            "hard_blocked": hard_blocked,
            "walk_forward_candidate": walk_forward_candidate,
            "blockers": ";".join(blockers),
        }
    )


def _blockers(
    metrics: dict[str, Any],
    *,
    trades: pd.DataFrame,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
) -> list[str]:
    blockers = []
    if trades.empty:
        blockers.append("no_trades")
    if _metric(metrics, "total_return") <= 0.0:
        blockers.append("non_positive_total_return_after_cost")
    if _metric(metrics, "annualized_return") <= 0.0:
        blockers.append("non_positive_annualized_return_after_cost")
    if _metric(metrics, "overlap_autocorr_adjusted_sharpe") < min_overlap_adjusted_sharpe:
        blockers.append("overlap_adjusted_sharpe_below_min")
    if _metric(metrics, "capacity_limited_trades") > 0:
        blockers.append("capacity_limited_trades_present")
    if _metric(metrics, "calendar_limited_trades") > 0:
        blockers.append("calendar_holding_gate_filtered_trades")
    if _metric(metrics, "max_drawdown") < max_drawdown_floor:
        blockers.append("max_drawdown_below_user_floor")
    return _dedupe(blockers)


def _prepare_factors(frame: pd.DataFrame, factor_name: str) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(frame, required, "factor_frame")
    output = frame[required].copy()
    output["date"] = pd.to_datetime(output["date"]).dt.date
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output[(output["market"] == "CN") & (output["factor_name"] == factor_name)].dropna(subset=["factor_value"])


def _prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    _require_columns(frame, required, "bars")
    columns = required + (["amount"] if "amount" in frame.columns else [])
    output = frame[columns].copy()
    output["date"] = pd.to_datetime(output["date"]).dt.date
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["adj_close"] = pd.to_numeric(output["adj_close"], errors="coerce")
    if "amount" in output:
        output["amount"] = pd.to_numeric(output["amount"], errors="coerce")
    return output[(output["market"] == "CN") & (output["adj_close"] > 0)].drop_duplicates(["asset_id", "market", "date"], keep="last")


def _filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if rebalance_interval <= 1 or factors.empty:
        return factors.reset_index(drop=True)
    rows = []
    for _, group in factors.groupby(["market", "factor_name"], sort=True):
        signal_dates = sorted(pd.to_datetime(group["date"]).dt.date.unique())
        keep_dates = set(signal_dates[::rebalance_interval])
        rows.append(group[pd.to_datetime(group["date"]).dt.date.isin(keep_dates)])
    return pd.concat(rows, ignore_index=True).reset_index(drop=True) if rows else factors.iloc[0:0].copy()


def _load_or_filter_bars(
    *,
    bars: pd.DataFrame | None,
    bars_roots: Iterable[str | Path] | None,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if bars is None:
        roots = list(bars_roots or [])
        if not roots:
            raise ValueError("bars or bars_roots is required")
        return load_public_reference_multi_family_bars(
            roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp("2026-12-31") if include_final_holdout else pd.Timestamp(analysis_end_date)
    return frame[(frame["date"] >= start) & (frame["date"] <= end)].reset_index(drop=True)


def _stock_basic_frame(value: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return _load_stock_basic(value) if value is not None else pd.DataFrame()


def _lead_spec(factor_name: str) -> Any:
    specs = [spec for spec in default_cn_calendar_seasonality_specs() if spec.factor_name == factor_name]
    if not specs:
        raise ValueError(f"Unknown calendar factor: {factor_name}")
    return specs[0]


def _validate_inputs(*, top_n: int, holding_period: int, rebalance_interval: int) -> None:
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if holding_period < 1:
        raise ValueError("holding_period must be positive")
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be positive")


def _summary(factors: pd.DataFrame, leaderboard: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "factor_names": sorted(factors["factor_name"].dropna().astype(str).unique().tolist()) if not factors.empty else [],
        "signal_rows": int(len(factors)),
        "signal_dates": int(factors["date"].nunique()) if not factors.empty else 0,
        "case_count": int(len(leaderboard)),
        "hard_blocked_cases": int(sum(1 for row in leaderboard if row.get("hard_blocked"))),
        "walk_forward_allowed_candidates": int(sum(1 for row in leaderboard if row.get("walk_forward_candidate"))),
        "best_total_return": _best_metric(leaderboard, "total_return"),
        "best_overlap_adjusted_sharpe": _best_metric(leaderboard, "overlap_autocorr_adjusted_sharpe"),
        "min_max_drawdown": _min_metric(leaderboard, "max_drawdown"),
        "max_capacity_limited_trades": int(max((_number(row.get("capacity_limited_trades")) for row in leaderboard), default=0)),
    }


def _data_window(bars: pd.DataFrame, factors: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _date_min(bars, "date"),
        "max_bar_date": _date_max(bars, "date"),
        "bar_rows": int(len(bars)),
        "min_signal_date": _date_min(factors, "date"),
        "max_signal_date": _date_max(factors, "date"),
        "factor_rows": int(len(factors)),
        "unique_assets": int(factors["asset_id"].nunique()) if "asset_id" in factors else 0,
    }


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _metric(metrics: dict[str, Any], key: str) -> float:
    return _number(metrics.get(key, 0.0))


def _best_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


def _min_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(min((_number(row.get(key)) for row in rows), default=0.0))


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _case_number(value: float) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", "p")


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value) if math.isfinite(value) else 0.0
    return value
