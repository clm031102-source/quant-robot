from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.factors.cn_stock_champion import (
    CN_STOCK_CHAMPION_FACTOR_NAMES,
    compute_cn_stock_champion_factors,
)
from quant_robot.factors.daily_basic_public_quality_value_momentum import (
    DAILY_BASIC_PUBLIC_QVM_FACTOR_NAMES,
    compute_daily_basic_public_quality_value_momentum_factors,
)
from quant_robot.factors.daily_basic_residual_composite import (
    DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES,
    compute_daily_basic_residual_composite_factors,
)
from quant_robot.factors.daily_basic_technical_combo import (
    DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES,
    compute_daily_basic_technical_combo_factors,
)
from quant_robot.factors.daily_basic_value_yield_risk_repair import (
    DAILY_BASIC_VALUE_YIELD_RISK_REPAIR_FACTOR_NAMES,
    compute_daily_basic_value_yield_risk_repair_factors,
)
from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES, compute_daily_basic_factors
from quant_robot.ops.clean_technical_portfolio_diagnostic import (
    SAFETY,
    apply_data_quality_quarantine,
    apply_market_regime_filter,
    backtest_price_bars,
    case_row,
    data_window_from_counts,
    filter_rebalance_dates,
    forward_trade_frame,
    market_regime_allowed_dates,
    run_fast_factor_backtest,
    sanitize,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    compute_daily_basic_non_price_public_carry_factors,
    default_daily_basic_non_price_public_carry_specs,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.schema.factors import FACTOR_COLUMNS


STAGE = "daily_basic_clean_portfolio_diagnostic"


DEFAULT_DAILY_BASIC_CARRY_NAMES = (
    "daily_basic_dividend_value_stability_carry_20",
    "daily_basic_value_yield_size_neutral_20",
    "daily_basic_midcap_value_yield_capacity_20",
    "daily_basic_volume_ratio_crowding_reversal_20",
)
DEFAULT_CANDIDATES = (
    *DAILY_BASIC_PUBLIC_QVM_FACTOR_NAMES,
    *DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES,
    *CN_STOCK_CHAMPION_FACTOR_NAMES,
    *DEFAULT_DAILY_BASIC_CARRY_NAMES,
)


def run_daily_basic_clean_portfolio_diagnostic(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
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
    market_regime_lookback: int | None = None,
    min_market_momentum: float = 0.0,
    max_market_drawdown: float | None = None,
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
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        tuple(Path(path) for path in daily_basic_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    daily_basic = filter_daily_basic_to_bars(daily_basic, bars)
    factor_bars = factor_price_bars(bars, factor_price_column)
    backtest_bars = backtest_price_bars(bars, backtest_price_column)
    forward_trades = forward_trade_frame(
        backtest_bars,
        execution_lag=execution_lag,
        holding_period=holding_period,
    )
    allowed_regime_dates: set[pd.Timestamp] | None = None
    regime_report: dict[str, Any] = {"enabled": False}
    if market_regime_lookback is not None:
        allowed_regime_dates, regime_report = market_regime_allowed_dates(
            backtest_bars,
            price_column="adj_close",
            lookback=int(market_regime_lookback),
            min_market_momentum=min_market_momentum,
            max_market_drawdown=max_market_drawdown,
        )

    leaderboard: list[dict[str, Any]] = []
    factor_rows = 0
    factor_assets: set[str] = set()
    non_empty_factor_names: list[str] = []
    factors_by_name = build_daily_basic_factor_frames(
        factor_bars,
        daily_basic,
        candidate_factor_names=candidate_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )
    for factor_name in candidate_factor_names:
        factor_slice = factors_by_name.get(str(factor_name), empty_factor_frame()).reset_index(drop=True)
        factor_slice = apply_market_regime_filter(factor_slice, allowed_regime_dates)
        factor_rows += int(len(factor_slice))
        if not factor_slice.empty:
            factor_assets.update(factor_slice["asset_id"].astype(str).unique())
            non_empty_factor_names.append(str(factor_name))
        if factor_slice.empty:
            leaderboard.append(
                empty_daily_basic_case_row(
                    factor_name=str(factor_name),
                    reason="no_factor_rows_after_daily_basic_coverage_clean_universe_and_liquidity_filter",
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
            "purpose": "costed clean-universe portfolio diagnostic for public daily-basic value/quality/liquidity candidates",
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
            "market_regime_lookback": None if market_regime_lookback is None else int(market_regime_lookback),
            "min_market_momentum": float(min_market_momentum),
            "max_market_drawdown": None if max_market_drawdown is None else float(max_market_drawdown),
        },
        "data_quality_quarantine": quarantine,
        "market_regime_filter": regime_report,
        "daily_basic_window": {
            "rows": int(len(daily_basic)),
            "assets": int(daily_basic["asset_id"].nunique()) if "asset_id" in daily_basic else 0,
            "min_date": _min_date(daily_basic, "date"),
            "max_date": _max_date(daily_basic, "date"),
        },
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
    write_daily_basic_clean_portfolio_diagnostic(output_dir, result)
    return result


def build_daily_basic_factor_frames(
    bars: pd.DataFrame,
    daily_basic: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    min_signal_date_amount: float,
) -> dict[str, pd.DataFrame]:
    requested = [str(name) for name in candidate_factor_names]
    pieces: list[pd.DataFrame] = []
    qvm_names = tuple(name for name in requested if name in DAILY_BASIC_PUBLIC_QVM_FACTOR_NAMES)
    if qvm_names:
        pieces.append(compute_daily_basic_public_quality_value_momentum_factors(bars, daily_basic, factor_names=qvm_names))
    residual_names = tuple(name for name in requested if name in DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES)
    if residual_names:
        pieces.append(compute_daily_basic_residual_composite_factors(bars, daily_basic, factor_names=residual_names))
    champion_names = tuple(name for name in requested if name in CN_STOCK_CHAMPION_FACTOR_NAMES)
    if champion_names:
        pieces.append(compute_cn_stock_champion_factors(bars, daily_basic, factor_names=champion_names))
    risk_repair_names = tuple(name for name in requested if name in DAILY_BASIC_VALUE_YIELD_RISK_REPAIR_FACTOR_NAMES)
    if risk_repair_names:
        pieces.append(compute_daily_basic_value_yield_risk_repair_factors(bars, daily_basic, factor_names=risk_repair_names))
    technical_combo_names = tuple(name for name in requested if name in DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES)
    if technical_combo_names:
        pieces.append(compute_daily_basic_technical_combo_factors(bars, daily_basic, factor_names=technical_combo_names))
    raw_daily_basic_names = tuple(name for name in requested if name in DAILY_BASIC_FACTOR_NAMES)
    if raw_daily_basic_names:
        raw = compute_daily_basic_factors(daily_basic)
        pieces.append(raw[raw["factor_name"].isin(raw_daily_basic_names)].reset_index(drop=True))
    carry_names = (
        set(requested)
        - set(qvm_names)
        - set(residual_names)
        - set(champion_names)
        - set(risk_repair_names)
        - set(technical_combo_names)
        - set(raw_daily_basic_names)
    )
    if carry_names:
        specs = [spec for spec in default_daily_basic_non_price_public_carry_specs() if spec.factor_name in carry_names]
        missing = sorted(carry_names - {spec.factor_name for spec in specs})
        if missing:
            raise ValueError(f"Unsupported daily-basic clean diagnostic factor names: {', '.join(missing)}")
        pieces.append(compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=specs))
    if not pieces:
        return {}
    factor_frame = pd.concat([piece for piece in pieces if not piece.empty], ignore_index=True)
    if factor_frame.empty:
        return {}
    factor_frame = ensure_lookback_window(factor_frame)
    factor_frame = attach_capacity_fields(factor_frame, bars)
    factor_frame = factor_frame[
        (pd.to_numeric(factor_frame["amount"], errors="coerce") >= float(min_signal_date_amount))
        & (pd.to_numeric(factor_frame["adv20_amount"], errors="coerce") >= float(min_signal_date_amount))
    ].dropna(subset=["factor_value"])
    return {
        str(factor_name): group[[*FACTOR_COLUMNS, "amount", "adv20_amount"]].sort_values(["asset_id", "date"]).reset_index(drop=True)
        for factor_name, group in factor_frame.groupby("factor_name", sort=False)
    }


def ensure_lookback_window(factor_frame: pd.DataFrame) -> pd.DataFrame:
    frame = factor_frame.copy()
    if "lookback_window" not in frame:
        frame["lookback_window"] = frame["factor_name"].astype(str).map(_window_from_factor_name).fillna(20).astype(int)
        return frame
    frame["lookback_window"] = pd.to_numeric(frame["lookback_window"], errors="coerce")
    missing = frame["lookback_window"].isna()
    if missing.any():
        frame.loc[missing, "lookback_window"] = frame.loc[missing, "factor_name"].astype(str).map(_window_from_factor_name)
    frame["lookback_window"] = frame["lookback_window"].fillna(20).astype(int)
    return frame


def _window_from_factor_name(factor_name: str) -> int | None:
    _, separator, suffix = str(factor_name).rpartition("_")
    if separator and suffix.isdigit():
        return int(suffix)
    return None


def attach_capacity_fields(factor_frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty:
        return factor_frame.copy()
    capacity = capacity_frame(bars)
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.merge(capacity, on=["date", "asset_id", "market"], how="left", validate="many_to_one")


def capacity_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars[["date", "asset_id", "market", "amount"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    pieces = []
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        item = group.copy()
        item["adv20_amount"] = item["amount"].rolling(20, min_periods=5).mean()
        pieces.append(item)
    if not pieces:
        return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount"])
    return pd.concat(pieces, ignore_index=True)


def filter_daily_basic_to_bars(daily_basic: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if daily_basic.empty or bars.empty:
        return daily_basic.copy()
    assets = set(bars["asset_id"].astype(str).unique())
    min_date = pd.Timestamp(bars["date"].min())
    max_date = pd.Timestamp(bars["date"].max())
    frame = daily_basic.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    return frame[
        frame["asset_id"].isin(assets)
        & (frame["date"] >= min_date)
        & (frame["date"] <= max_date)
    ].reset_index(drop=True)


def factor_price_bars(bars: pd.DataFrame, price_column: str) -> pd.DataFrame:
    column = str(price_column)
    if column == "adj_close":
        return bars
    if column not in bars:
        raise ValueError(f"factor price column is missing from bars: {column}")
    output = bars.copy()
    output["adj_close"] = pd.to_numeric(output[column], errors="coerce")
    return output


def empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=[*FACTOR_COLUMNS, "amount", "adv20_amount"])


def empty_daily_basic_case_row(*, factor_name: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": f"{factor_name}_empty",
        "factor_name": factor_name,
        "top_n": 0,
        "holding_period": 0,
        "rebalance_interval": 0,
        "cost_bps": 0.0,
        "portfolio_value": 0.0,
        "total_return": 0.0,
        "annualized_return": 0.0,
        "sharpe": 0.0,
        "overlap_autocorr_adjusted_sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "turnover": 0.0,
        "average_holdings": 0.0,
        "avg_participation_rate": 0.0,
        "max_participation_rate": 0.0,
        "capacity_limited_trades": 0,
        "max_abs_trade_gross_return": 0.0,
        "extreme_trade_return_count": 0,
        "extreme_trade_return_rate": 0.0,
        "extreme_excluded_total_return": 0.0,
        "extreme_excluded_annualized_return": 0.0,
        "extreme_excluded_sharpe": 0.0,
        "extreme_excluded_max_drawdown": 0.0,
        "extreme_excluded_win_rate": 0.0,
        "yearly_positive_rate": 0.0,
        "losing_year_count": 0,
        "worst_year_total_return": 0.0,
        "diagnostic_pass": False,
        "blockers": [reason],
    }


def write_daily_basic_clean_portfolio_diagnostic(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "daily_basic_clean_portfolio_diagnostic.json").write_text(
        json.dumps(sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(
        output / "daily_basic_clean_portfolio_diagnostic_leaderboard.csv",
        index=False,
    )


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()
