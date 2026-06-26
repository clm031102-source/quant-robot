from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.factors.information_discreteness import (
    INFORMATION_DISCRETENESS_FACTOR_NAMES,
    compute_information_discreteness_factors,
)
from quant_robot.factors.liquidity_shock_recovery import (
    LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
    compute_liquidity_shock_recovery_factors,
)
from quant_robot.factors.public_trend_strength_state import (
    PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
    compute_public_trend_strength_state_factors,
)
from quant_robot.factors.public_trend_volume import (
    PUBLIC_TREND_VOLUME_FACTOR_NAMES,
    compute_public_trend_volume_factors,
)
from quant_robot.ops.clean_technical_portfolio_diagnostic import (
    SAFETY,
    apply_data_quality_quarantine,
    backtest_price_bars,
    case_row,
    data_window_from_counts,
    filter_rebalance_dates,
    forward_trade_frame,
    run_fast_factor_backtest,
    sanitize,
)
from quant_robot.ops.daily_basic_clean_portfolio_diagnostic import (
    attach_capacity_fields,
    empty_daily_basic_case_row,
    empty_factor_frame,
    factor_price_bars,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.schema.factors import FACTOR_COLUMNS


STAGE = "bar_factor_clean_portfolio_diagnostic"
DEFAULT_CANDIDATES = (
    "smart_money_trend_20",
    "anti_smart_money_trend_20",
    "supertrend_volume_capacity_strict_10_3_20",
    "obv_breakout_capacity_strict_20",
    "liquidity_recovery_quality_composite_20",
    "downside_liquidity_resilience_20",
    "fip_smooth_momentum_quality_60_20",
    "fip_discrete_jump_reversal_20_5",
    "fip_volume_confirmed_smooth_trend_20_60",
    "trend_strength_state_residual_composite_20",
    "williams_range_failure_reversal_14_20",
)


def run_bar_factor_clean_portfolio_diagnostic(
    *,
    bars_roots: Iterable[str | Path],
    output_dir: str | Path,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    candidate_factor_names: Sequence[str] = DEFAULT_CANDIDATES,
    factor_price_column: str = "close",
    backtest_price_column: str = "close",
    top_n_values: Sequence[int] = (100,),
    cost_bps_values: Sequence[float] = (10.0,),
    holding_period: int = 20,
    rebalance_intervals: Sequence[int] = (5,),
    execution_lag: int = 1,
    min_signal_date_amount: float = 10_000_000.0,
    portfolio_value: float = 1_000_000.0,
    max_participation_rate: float = 0.05,
    market_impact_bps: float = 0.0,
    exclude_asset_prefixes: Sequence[str] = (),
    max_abs_daily_return_quarantine: float | None = None,
    min_overlap_adjusted_sharpe: float = 0.50,
    max_drawdown_floor: float = -0.35,
    extreme_trade_abs_return: float = 0.50,
) -> dict[str, Any]:
    bars = load_public_reference_multi_family_bars(
        tuple(Path(path) for path in bars_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    bars, quarantine = apply_data_quality_quarantine(
        bars,
        exclude_asset_prefixes=exclude_asset_prefixes,
        max_abs_daily_return_quarantine=max_abs_daily_return_quarantine,
    )
    factor_bars = factor_price_bars(bars, factor_price_column)
    backtest_bars = backtest_price_bars(bars, backtest_price_column)
    forward_trades = forward_trade_frame(
        backtest_bars,
        execution_lag=execution_lag,
        holding_period=holding_period,
    )
    factors_by_name = build_bar_factor_frames(
        factor_bars,
        candidate_factor_names=candidate_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )

    leaderboard: list[dict[str, Any]] = []
    factor_rows = 0
    factor_assets: set[str] = set()
    non_empty_factor_names: list[str] = []
    for factor_name in candidate_factor_names:
        factor_slice = factors_by_name.get(str(factor_name), empty_factor_frame()).reset_index(drop=True)
        factor_rows += int(len(factor_slice))
        if not factor_slice.empty:
            factor_assets.update(factor_slice["asset_id"].astype(str).unique())
            non_empty_factor_names.append(str(factor_name))
        if factor_slice.empty:
            leaderboard.append(
                empty_daily_basic_case_row(
                    factor_name=str(factor_name),
                    reason="no_factor_rows_after_bar_factor_clean_universe_and_liquidity_filter",
                )
            )
            continue
        for rebalance_interval in rebalance_intervals:
            rebalanced = filter_rebalance_dates(factor_slice, int(rebalance_interval))
            periods_per_year = 252.0 / float(max(int(rebalance_interval), 1))
            for top_n in top_n_values:
                for cost_bps in cost_bps_values:
                    metrics, trades = run_fast_factor_backtest(
                        rebalanced,
                        forward_trades,
                        top_n=int(top_n),
                        cost_bps=float(cost_bps),
                        holding_period=holding_period,
                        rebalance_interval=int(rebalance_interval),
                        target_gross_exposure=1.0,
                        periods_per_year=periods_per_year,
                        market_impact_bps=market_impact_bps,
                        max_participation_rate=max_participation_rate,
                        portfolio_value=portfolio_value,
                    )
                    leaderboard.append(
                        case_row(
                            metrics,
                            trades,
                            factor_name=str(factor_name),
                            top_n=int(top_n),
                            cost_bps=float(cost_bps),
                            holding_period=holding_period,
                            rebalance_interval=int(rebalance_interval),
                            portfolio_value=portfolio_value,
                            max_participation_rate=max_participation_rate,
                            min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
                            max_drawdown_floor=max_drawdown_floor,
                            extreme_trade_abs_return=extreme_trade_abs_return,
                            periods_per_year=periods_per_year,
                        )
                    )

    leaderboard = sorted(
        leaderboard,
        key=lambda row: (
            not row["diagnostic_pass"],
            -float(row.get("overlap_autocorr_adjusted_sharpe", 0.0) or 0.0),
            -float(row.get("annualized_return", 0.0) or 0.0),
            float(row.get("max_drawdown", 0.0) or 0.0),
        ),
    )
    result = {
        "stage": STAGE,
        "safety": SAFETY,
        "source_context": {
            "purpose": "costed clean-universe portfolio diagnostic for public bar-based indicator families",
            "cn_stock_is_auxiliary_factor_source_for_project": True,
            "not_paper_ready": True,
            "promotion_allowed": False,
        },
        "thresholds": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "candidate_factor_names": list(candidate_factor_names),
            "factor_price_column": factor_price_column,
            "backtest_price_column": backtest_price_column,
            "top_n_values": [int(value) for value in top_n_values],
            "cost_bps_values": [float(value) for value in cost_bps_values],
            "holding_period": int(holding_period),
            "rebalance_intervals": [int(value) for value in rebalance_intervals],
            "execution_lag": int(execution_lag),
            "min_signal_date_amount": float(min_signal_date_amount),
            "portfolio_value": float(portfolio_value),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "exclude_asset_prefixes": list(exclude_asset_prefixes),
            "max_abs_daily_return_quarantine": (
                None if max_abs_daily_return_quarantine is None else float(max_abs_daily_return_quarantine)
            ),
            "min_overlap_adjusted_sharpe": float(min_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
            "extreme_trade_abs_return": float(extreme_trade_abs_return),
        },
        "data_quality_quarantine": quarantine,
        "data_window": data_window_from_counts(
            bars,
            factor_rows=factor_rows,
            factor_assets=len(factor_assets),
            factor_names=non_empty_factor_names,
        ),
        "summary": {
            "candidates": int(len(candidate_factor_names)),
            "factor_rows": int(factor_rows),
            "cases": int(len(leaderboard)),
            "diagnostic_pass_cases": int(sum(bool(row.get("diagnostic_pass")) for row in leaderboard)),
            "best_case_id": leaderboard[0]["case_id"] if leaderboard else None,
            "portfolio_grid_is_diagnostic_only": True,
        },
        "leaderboard": leaderboard,
    }
    write_bar_factor_clean_portfolio_diagnostic(output_dir, result)
    return result


def build_bar_factor_frames(
    bars: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    min_signal_date_amount: float,
) -> dict[str, pd.DataFrame]:
    requested = [str(name) for name in candidate_factor_names]
    pieces: list[pd.DataFrame] = []
    trend_volume = tuple(name for name in requested if name in PUBLIC_TREND_VOLUME_FACTOR_NAMES)
    if trend_volume:
        pieces.append(compute_public_trend_volume_factors(bars, factor_names=trend_volume))
    liquidity_recovery = tuple(name for name in requested if name in LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES)
    if liquidity_recovery:
        pieces.append(compute_liquidity_shock_recovery_factors(bars, factor_names=liquidity_recovery))
    information = tuple(name for name in requested if name in INFORMATION_DISCRETENESS_FACTOR_NAMES)
    if information:
        pieces.append(compute_information_discreteness_factors(bars, factor_names=information))
    trend_strength = tuple(name for name in requested if name in PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES)
    if trend_strength:
        pieces.append(compute_public_trend_strength_state_factors(bars, factor_names=trend_strength))
    known = set(trend_volume) | set(liquidity_recovery) | set(information) | set(trend_strength)
    missing = sorted(set(requested) - known)
    if missing:
        raise ValueError(f"Unsupported bar-factor clean diagnostic factor names: {', '.join(missing)}")
    if not pieces:
        return {}
    factor_frame = pd.concat([piece for piece in pieces if not piece.empty], ignore_index=True)
    if factor_frame.empty:
        return {}
    factor_frame = attach_capacity_fields(factor_frame, bars)
    factor_frame = factor_frame[
        (pd.to_numeric(factor_frame["amount"], errors="coerce") >= float(min_signal_date_amount))
        & (pd.to_numeric(factor_frame["adv20_amount"], errors="coerce") >= float(min_signal_date_amount))
    ].dropna(subset=["factor_value"])
    return {
        str(factor_name): group[[*FACTOR_COLUMNS, "amount", "adv20_amount"]].sort_values(["asset_id", "date"]).reset_index(drop=True)
        for factor_name, group in factor_frame.groupby("factor_name", sort=False)
    }


def write_bar_factor_clean_portfolio_diagnostic(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "bar_factor_clean_portfolio_diagnostic.json").write_text(
        json.dumps(sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(
        output / "bar_factor_clean_portfolio_diagnostic_leaderboard.csv",
        index=False,
    )
