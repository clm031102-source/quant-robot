from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.research.overlap import overlap_aware_return_stats
from quant_robot.schema.factors import FACTOR_COLUMNS


STAGE = "clean_technical_portfolio_diagnostic"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


COMPOSITE_SPECS: dict[str, tuple[str, ...]] = {
    "trend_resilience": ("momentum", "drawdown_resilience", "liquidity_resilience"),
    "defensive_reversal": ("reversal", "low_downside_volatility", "liquidity_resilience"),
    "liquidity_confirmed_breakout": ("momentum", "amount_stability", "liquidity_resilience"),
}


def run_clean_technical_portfolio_diagnostic(
    *,
    bars_roots: Iterable[str | Path],
    output_dir: str | Path,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    candidate_factor_names: Sequence[str],
    factor_price_column: str = "close",
    backtest_price_column: str = "close",
    top_n_values: Sequence[int] = (50, 100),
    cost_bps_values: Sequence[float] = (5.0, 10.0),
    holding_period: int = 20,
    rebalance_intervals: Sequence[int] = (5, 10),
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
    candidate_specs = [_split_candidate_window(name) for name in candidate_factor_names]
    features = base_feature_frame(
        bars,
        windows=sorted({window for _, window in candidate_specs}),
        price_column=factor_price_column,
    )

    leaderboard: list[dict[str, Any]] = []
    backtest_bars = backtest_price_bars(bars, backtest_price_column)
    forward_trades = forward_trade_frame(
        backtest_bars,
        execution_lag=execution_lag,
        holding_period=holding_period,
    )
    factor_rows = 0
    factor_assets: set[str] = set()
    non_empty_factor_names: list[str] = []
    for factor_name, (prefix, window) in zip(candidate_factor_names, candidate_specs):
        factor_slice = clean_factor_slice_from_features(
            features,
            factor_name=factor_name,
            prefix=prefix,
            window=window,
            min_signal_date_amount=min_signal_date_amount,
        )
        factor_rows += int(len(factor_slice))
        if not factor_slice.empty:
            factor_assets.update(factor_slice["asset_id"].astype(str).unique())
            non_empty_factor_names.append(str(factor_name))
        if factor_slice.empty:
            leaderboard.append(
                empty_case_row(
                    factor_name=factor_name,
                    reason="no_factor_rows_after_clean_universe_and_liquidity_filter",
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
                            factor_name=factor_name,
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
            "purpose": "costed clean-universe baseline for public technical factors before further mining",
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
        "summary": {
            "candidates": int(len(candidate_factor_names)),
            "factor_rows": int(factor_rows),
            "cases": int(len(leaderboard)),
            "diagnostic_pass_cases": int(sum(bool(row.get("diagnostic_pass")) for row in leaderboard)),
            "best_case_id": leaderboard[0]["case_id"] if leaderboard else None,
            "portfolio_grid_is_diagnostic_only": True,
        },
        "data_window": data_window_from_counts(
            bars,
            factor_rows=factor_rows,
            factor_assets=len(factor_assets),
            factor_names=non_empty_factor_names,
        ),
        "leaderboard": leaderboard,
    }
    write_clean_technical_portfolio_diagnostic(output_dir, result)
    return result


def build_clean_technical_factor_frame(
    bars: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    price_column: str = "close",
    min_signal_date_amount: float = 10_000_000.0,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", price_column, "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for clean technical factors: {', '.join(missing)}")
    candidate_specs = [_split_candidate_window(name) for name in candidate_factor_names]
    windows = sorted({window for _, window in candidate_specs})
    features = base_feature_frame(bars, windows=windows, price_column=price_column)
    if features.empty:
        return pd.DataFrame(columns=[*FACTOR_COLUMNS, "amount", "adv20_amount"])

    rows: list[pd.DataFrame] = []
    for factor_name, (prefix, window) in zip(candidate_factor_names, candidate_specs):
        rows.append(
            clean_factor_slice_from_features(
                features,
                factor_name=factor_name,
                prefix=prefix,
                window=window,
                min_signal_date_amount=min_signal_date_amount,
            )
        )
    if not rows:
        return pd.DataFrame(columns=[*FACTOR_COLUMNS, "amount", "adv20_amount"])
    factors = pd.concat(rows, ignore_index=True)
    factors = factors[
        (pd.to_numeric(factors["amount"], errors="coerce") >= float(min_signal_date_amount))
        & (pd.to_numeric(factors["adv20_amount"], errors="coerce") >= float(min_signal_date_amount))
    ]
    return factors[[*FACTOR_COLUMNS, "amount", "adv20_amount"]].sort_values(
        ["factor_name", "asset_id", "date"]
    ).reset_index(drop=True)


def clean_factor_slice_from_features(
    features: pd.DataFrame,
    *,
    factor_name: str,
    prefix: str,
    window: int,
    min_signal_date_amount: float,
) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=[*FACTOR_COLUMNS, "amount", "adv20_amount"])
    values = candidate_values(features, prefix, window)
    output = features[["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    output["factor_name"] = factor_name
    output["factor_value"] = values.replace([np.inf, -np.inf], np.nan)
    output["lookback_window"] = int(window)
    output = output.dropna(subset=["factor_value"])
    output = output[
        (pd.to_numeric(output["amount"], errors="coerce") >= float(min_signal_date_amount))
        & (pd.to_numeric(output["adv20_amount"], errors="coerce") >= float(min_signal_date_amount))
    ]
    return output[[*FACTOR_COLUMNS, "amount", "adv20_amount"]].reset_index(drop=True)


def base_feature_frame(bars: pd.DataFrame, *, windows: Sequence[int], price_column: str) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame[price_column] = pd.to_numeric(frame[price_column], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame[(frame[price_column] > 0.0) & (frame["amount"] > 0.0)].sort_values(["asset_id", "date"])
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        price = group[price_column]
        returns = price.pct_change()
        amount = group["amount"]
        output = group[["date", "asset_id", "market", "amount"]].copy()
        output["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        for window in windows:
            window = int(window)
            momentum = price / price.shift(window) - 1.0
            volatility = returns.rolling(window).std(ddof=0)
            downside_volatility = returns.clip(upper=0.0).rolling(window).std(ddof=0)
            drawdown = price / price.rolling(window).max() - 1.0
            amount_change = amount.replace(0.0, np.nan).pct_change()
            short_window = max(2, window // 3)
            output[f"momentum_{window}"] = momentum
            output[f"risk_adjusted_momentum_{window}"] = (momentum / volatility.replace(0.0, np.nan)).replace(
                [np.inf, -np.inf], np.nan
            )
            output[f"reversal_{window}"] = -momentum
            output[f"low_volatility_{window}"] = -volatility
            output[f"low_downside_volatility_{window}"] = -downside_volatility
            output[f"drawdown_resilience_{window}"] = drawdown.replace([np.inf, -np.inf], np.nan)
            output[f"liquidity_resilience_{window}"] = -(returns.abs() / amount.replace(0.0, np.nan)).replace(
                [np.inf, -np.inf], np.nan
            )
            output[f"amount_stability_{window}"] = -amount_change.rolling(window).std(ddof=0)
            output[f"average_amount_{window}"] = np.log1p(amount.where(amount > 0.0).rolling(window).mean())
            output[f"crash_recovery_{window}"] = (
                (price / price.shift(short_window) - 1.0) * (-drawdown.clip(upper=0.0))
            ).replace([np.inf, -np.inf], np.nan)
            output[f"recovery_quality_{window}"] = (
                (price / price.shift(short_window) - 1.0) / downside_volatility.replace(0.0, np.nan) + drawdown
            ).replace([np.inf, -np.inf], np.nan)
        pieces.append(output)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def candidate_values(features: pd.DataFrame, prefix: str, window: int) -> pd.Series:
    column = f"{prefix}_{window}"
    if column in features.columns:
        return pd.to_numeric(features[column], errors="coerce")
    if prefix == "market_relative_strength":
        momentum = pd.to_numeric(features[f"momentum_{window}"], errors="coerce")
        return momentum - momentum.groupby([features["date"], features["market"]]).transform("median")
    if prefix in COMPOSITE_SPECS:
        component_columns = [f"{component}_{window}" for component in COMPOSITE_SPECS[prefix]]
        missing = [component for component in component_columns if component not in features.columns]
        if missing:
            raise ValueError(f"Missing component columns for {prefix}_{window}: {', '.join(missing)}")
        ranked = features.groupby(["date", "market"], group_keys=False)[component_columns].rank(
            method="average",
            pct=True,
        )
        return ranked.mean(axis=1, skipna=False)
    raise ValueError(f"Unsupported clean technical factor: {prefix}_{window}")


def apply_data_quality_quarantine(
    bars: pd.DataFrame,
    *,
    exclude_asset_prefixes: Sequence[str],
    max_abs_daily_return_quarantine: float | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = bars.copy()
    excluded_by_prefix: set[str] = set()
    for prefix in exclude_asset_prefixes:
        prefix = str(prefix)
        if prefix:
            excluded_by_prefix.update(frame.loc[frame["asset_id"].astype(str).str.startswith(prefix), "asset_id"].astype(str))
    excluded_by_return: set[str] = set()
    if max_abs_daily_return_quarantine is not None:
        threshold = float(max_abs_daily_return_quarantine)
        for column in ("close", "adj_close"):
            if column not in frame:
                continue
            returns = frame.sort_values(["asset_id", "date"]).groupby("asset_id")[column].pct_change()
            excluded_by_return.update(frame.loc[returns.abs() > threshold, "asset_id"].astype(str))
    excluded = excluded_by_prefix | excluded_by_return
    if excluded:
        frame = frame[~frame["asset_id"].astype(str).isin(excluded)].reset_index(drop=True)
    return frame, {
        "excluded_assets": int(len(excluded)),
        "excluded_by_prefix_assets": int(len(excluded_by_prefix)),
        "excluded_by_extreme_daily_return_assets": int(len(excluded_by_return)),
        "remaining_assets": int(frame["asset_id"].nunique()) if "asset_id" in frame else 0,
        "remaining_rows": int(len(frame)),
    }


def backtest_price_bars(bars: pd.DataFrame, price_column: str) -> pd.DataFrame:
    column = str(price_column)
    if column == "adj_close":
        return bars
    if column not in bars:
        raise ValueError(f"backtest price column is missing from bars: {column}")
    output = bars.copy()
    output["adj_close"] = pd.to_numeric(output[column], errors="coerce")
    return output


def filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if factors.empty or rebalance_interval <= 1:
        return factors.copy()
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    dates = pd.Index(sorted(frame["date"].dropna().unique()))
    keep = set(dates[:: int(rebalance_interval)])
    return frame[frame["date"].isin(keep)].reset_index(drop=True)


def market_regime_allowed_dates(
    bars: pd.DataFrame,
    *,
    price_column: str = "adj_close",
    lookback: int = 120,
    min_market_momentum: float = 0.0,
    max_market_drawdown: float | None = None,
) -> tuple[set[pd.Timestamp], dict[str, Any]]:
    if lookback < 2:
        raise ValueError("market regime lookback must be at least 2")
    if price_column not in bars:
        raise ValueError(f"market regime price column is missing from bars: {price_column}")
    frame = bars[["date", "asset_id", price_column]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame[price_column] = pd.to_numeric(frame[price_column], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"])
    frame["return_1d"] = frame.groupby("asset_id", sort=False)[price_column].pct_change()
    market_return = frame.groupby("date", sort=True)["return_1d"].median().dropna()
    if market_return.empty:
        return set(), {
            "enabled": True,
            "lookback": int(lookback),
            "allowed_dates": 0,
            "total_dates": 0,
            "allowed_ratio": 0.0,
        }
    market_equity = (1.0 + market_return).cumprod()
    momentum = market_equity / market_equity.shift(int(lookback)) - 1.0
    drawdown = market_equity / market_equity.rolling(int(lookback), min_periods=int(lookback)).max() - 1.0
    allowed = momentum >= float(min_market_momentum)
    if max_market_drawdown is not None:
        allowed &= drawdown >= float(max_market_drawdown)
    allowed_dates = set(pd.to_datetime(momentum.index[allowed.fillna(False)]))
    total_dates = int(momentum.notna().sum())
    return allowed_dates, {
        "enabled": True,
        "price_column": price_column,
        "lookback": int(lookback),
        "min_market_momentum": float(min_market_momentum),
        "max_market_drawdown": None if max_market_drawdown is None else float(max_market_drawdown),
        "allowed_dates": int(len(allowed_dates)),
        "total_dates": total_dates,
        "allowed_ratio": float(len(allowed_dates) / total_dates) if total_dates else 0.0,
        "min_allowed_date": min_date(pd.DataFrame({"date": list(allowed_dates)}), "date") if allowed_dates else None,
        "max_allowed_date": max_date(pd.DataFrame({"date": list(allowed_dates)}), "date") if allowed_dates else None,
    }


def apply_market_regime_filter(factors: pd.DataFrame, allowed_dates: set[pd.Timestamp] | None) -> pd.DataFrame:
    if not allowed_dates:
        return factors
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame[frame["date"].isin(allowed_dates)].reset_index(drop=True)


def forward_trade_frame(
    bars: pd.DataFrame,
    *,
    execution_lag: int,
    holding_period: int,
) -> pd.DataFrame:
    if execution_lag < 1:
        raise ValueError("execution_lag must be at least 1")
    if holding_period < 1:
        raise ValueError("holding_period must be at least 1")
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for forward trade frame: {', '.join(missing)}")
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    grouped = frame.groupby("asset_id", sort=False)
    entry_shift = int(execution_lag)
    exit_shift = int(execution_lag + holding_period)
    frame["entry_date"] = grouped["date"].shift(-entry_shift)
    frame["exit_date"] = grouped["date"].shift(-exit_shift)
    frame["entry_price"] = grouped["adj_close"].shift(-entry_shift)
    frame["exit_price"] = grouped["adj_close"].shift(-exit_shift)
    frame["entry_amount"] = grouped["amount"].shift(-entry_shift)
    frame["gross_return"] = frame["exit_price"] / frame["entry_price"] - 1.0
    return frame[
        [
            "date",
            "asset_id",
            "market",
            "entry_date",
            "exit_date",
            "entry_amount",
            "gross_return",
        ]
    ].dropna(subset=["entry_date", "exit_date", "gross_return"]).reset_index(drop=True)


def run_fast_factor_backtest(
    factors: pd.DataFrame,
    forward_trades: pd.DataFrame,
    *,
    top_n: int,
    cost_bps: float,
    holding_period: int,
    rebalance_interval: int,
    target_gross_exposure: float,
    periods_per_year: float,
    market_impact_bps: float,
    max_participation_rate: float,
    portfolio_value: float,
) -> tuple[dict[str, float], pd.DataFrame]:
    if factors.empty:
        metrics = summarize_returns(pd.Series(dtype=float), periods_per_year=periods_per_year)
        metrics.update(empty_overlap_metrics())
        metrics.update(empty_trade_metrics())
        return metrics, empty_trades()
    frame = factors.dropna(subset=["factor_value"]).copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    merged = frame.merge(
        forward_trades,
        on=["date", "asset_id", "market"],
        how="inner",
    )
    if merged.empty:
        metrics = summarize_returns(pd.Series(dtype=float), periods_per_year=periods_per_year)
        metrics.update(empty_overlap_metrics())
        metrics.update(empty_trade_metrics())
        return metrics, empty_trades()
    selected = (
        merged.sort_values(["date", "market", "factor_name", "factor_value"], ascending=[True, True, True, False])
        .groupby(["date", "market", "factor_name"], as_index=False, group_keys=False)
        .head(int(top_n))
        .copy()
    )
    sleeve_scale = 1.0 if holding_period <= 1 else min(float(rebalance_interval) / float(holding_period), 1.0)
    selected_count = selected.groupby(["date", "market", "factor_name"])["asset_id"].transform("count").replace(0, np.nan)
    selected["target_weight"] = float(target_gross_exposure) * sleeve_scale / selected_count
    selected["target_notional"] = selected["target_weight"].abs() * float(portfolio_value)
    selected["participation_rate"] = selected["target_notional"] / selected["entry_amount"].where(selected["entry_amount"] > 0.0)
    selected["participation_rate"] = selected["participation_rate"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    selected["capacity_limited"] = selected["participation_rate"] > float(max_participation_rate)
    selected["cost_rate"] = vectorized_cost_rate(
        selected["participation_rate"],
        cost_bps=float(cost_bps),
        market_impact_bps=float(market_impact_bps),
        max_participation_rate=float(max_participation_rate),
    )
    selected["net_return"] = selected["gross_return"] - selected["cost_rate"]
    selected["weighted_return"] = selected["target_weight"] * selected["net_return"]
    trades = selected[
        [
            "date",
            "entry_date",
            "exit_date",
            "asset_id",
            "market",
            "factor_name",
            "target_weight",
            "target_notional",
            "entry_amount",
            "participation_rate",
            "capacity_limited",
            "cost_rate",
            "gross_return",
            "net_return",
            "weighted_return",
        ]
    ].rename(columns={"date": "signal_date"})
    returns = (
        trades.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"))
        .sort_values("exit_date")["period_return"]
    )
    metrics = summarize_returns(returns, periods_per_year=periods_per_year)
    metrics.update(overlap_metrics(returns, periods_per_year=periods_per_year, holding_period=holding_period))
    metrics["turnover"] = float(trades.groupby("signal_date")["target_weight"].sum().mean()) if not trades.empty else 0.0
    metrics["average_holdings"] = float(trades.groupby("signal_date")["asset_id"].nunique().mean()) if not trades.empty else 0.0
    metrics["avg_cost_rate"] = float(trades["cost_rate"].mean()) if not trades.empty else 0.0
    metrics["max_cost_rate"] = float(trades["cost_rate"].max()) if not trades.empty else 0.0
    metrics["avg_participation_rate"] = float(trades["participation_rate"].mean()) if not trades.empty else 0.0
    metrics["max_participation_rate"] = float(trades["participation_rate"].max()) if not trades.empty else 0.0
    metrics["capacity_limited_trades"] = int(trades["capacity_limited"].sum()) if not trades.empty else 0
    return metrics, trades.reset_index(drop=True)


def vectorized_cost_rate(
    participation_rate: pd.Series,
    *,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float,
) -> pd.Series:
    impact = pd.Series(0.0, index=participation_rate.index)
    if market_impact_bps > 0.0:
        denominator = max(float(max_participation_rate), 1e-12)
        impact = float(market_impact_bps) * (participation_rate / denominator).clip(lower=0.0, upper=1.0)
    return 2.0 * (float(cost_bps) + impact) / 10000.0


def overlap_metrics(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, float]:
    stats = overlap_aware_return_stats(
        returns,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    return {
        key if key.startswith("overlap_") else f"overlap_{key}": value
        for key, value in stats.items()
    }


def empty_overlap_metrics() -> dict[str, float]:
    return {
        "overlap_autocorr_adjusted_sharpe": 0.0,
        "overlap_autocorrelation": 0.0,
        "overlap_effective_sample_size": 0.0,
    }


def empty_trade_metrics() -> dict[str, float]:
    return {
        "turnover": 0.0,
        "average_holdings": 0.0,
        "avg_cost_rate": 0.0,
        "max_cost_rate": 0.0,
        "avg_participation_rate": 0.0,
        "max_participation_rate": 0.0,
        "capacity_limited_trades": 0.0,
    }


def empty_trades() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "signal_date",
            "entry_date",
            "exit_date",
            "asset_id",
            "market",
            "factor_name",
            "target_weight",
            "target_notional",
            "entry_amount",
            "participation_rate",
            "capacity_limited",
            "cost_rate",
            "gross_return",
            "net_return",
            "weighted_return",
        ]
    )


def case_row(
    metrics: dict[str, Any],
    trades: pd.DataFrame,
    *,
    factor_name: str,
    top_n: int,
    cost_bps: float,
    holding_period: int,
    rebalance_interval: int,
    portfolio_value: float,
    max_participation_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
    extreme_trade_abs_return: float,
    periods_per_year: float,
) -> dict[str, Any]:
    max_abs_trade = float(trades["gross_return"].abs().max()) if not trades.empty else 0.0
    extreme_count = int((trades["gross_return"].abs() > extreme_trade_abs_return).sum()) if not trades.empty else 0
    trade_count = int(len(trades))
    extreme_rate = float(extreme_count / trade_count) if trade_count else 0.0
    stress = extreme_excluded_metrics(
        trades,
        extreme_trade_abs_return=extreme_trade_abs_return,
        periods_per_year=periods_per_year,
    )
    yearly = yearly_return_summary(trades, periods_per_year=periods_per_year)
    yearly_returns = [float(row["total_return"]) for row in yearly]
    losing_years = int(sum(value <= 0.0 for value in yearly_returns))
    yearly_positive_rate = float(sum(value > 0.0 for value in yearly_returns) / len(yearly_returns)) if yearly_returns else 0.0
    worst_year = float(min(yearly_returns)) if yearly_returns else 0.0

    blockers = []
    if metric(metrics, "total_return") <= 0.0:
        blockers.append("non_positive_total_return")
    if metric(metrics, "annualized_return") <= 0.0:
        blockers.append("non_positive_annualized_return")
    if metric(metrics, "overlap_autocorr_adjusted_sharpe") < min_overlap_adjusted_sharpe:
        blockers.append("overlap_adjusted_sharpe_below_threshold")
    if metric(metrics, "max_drawdown") < max_drawdown_floor:
        blockers.append("drawdown_below_user_tolerance_floor")
    if int(metric(metrics, "capacity_limited_trades")) > 0:
        blockers.append("capacity_limited_trades_present")
    if extreme_rate > 0.01:
        blockers.append("extreme_trade_rate_above_one_percent")
    if stress["total_return"] <= 0.0:
        blockers.append("extreme_excluded_total_return_non_positive")
    if stress["annualized_return"] <= 0.0:
        blockers.append("extreme_excluded_annualized_return_non_positive")
    if stress["max_drawdown"] < max_drawdown_floor:
        blockers.append("extreme_excluded_drawdown_below_user_tolerance_floor")
    if yearly_returns and yearly_positive_rate < 0.50:
        blockers.append("yearly_positive_rate_below_half")
    return {
        "case_id": f"{factor_name}_top{top_n}_hold{holding_period}_reb{rebalance_interval}_cost{cost_bps:g}_cap{portfolio_value:g}",
        "factor_name": factor_name,
        "top_n": int(top_n),
        "holding_period": int(holding_period),
        "rebalance_interval": int(rebalance_interval),
        "cost_bps": float(cost_bps),
        "portfolio_value": float(portfolio_value),
        "total_return": metric(metrics, "total_return"),
        "annualized_return": metric(metrics, "annualized_return"),
        "sharpe": metric(metrics, "sharpe"),
        "overlap_autocorr_adjusted_sharpe": metric(metrics, "overlap_autocorr_adjusted_sharpe"),
        "max_drawdown": metric(metrics, "max_drawdown"),
        "win_rate": metric(metrics, "win_rate"),
        "turnover": metric(metrics, "turnover"),
        "average_holdings": metric(metrics, "average_holdings"),
        "avg_participation_rate": metric(metrics, "avg_participation_rate"),
        "max_participation_rate": metric(metrics, "max_participation_rate"),
        "capacity_limited_trades": int(metric(metrics, "capacity_limited_trades")),
        "max_abs_trade_gross_return": max_abs_trade,
        "extreme_trade_return_count": extreme_count,
        "extreme_trade_return_rate": extreme_rate,
        "extreme_excluded_total_return": stress["total_return"],
        "extreme_excluded_annualized_return": stress["annualized_return"],
        "extreme_excluded_sharpe": stress["sharpe"],
        "extreme_excluded_max_drawdown": stress["max_drawdown"],
        "extreme_excluded_win_rate": stress["win_rate"],
        "yearly_positive_rate": yearly_positive_rate,
        "losing_year_count": losing_years,
        "worst_year_total_return": worst_year,
        "diagnostic_pass": not blockers,
        "blockers": blockers,
    }


def empty_case_row(*, factor_name: str, reason: str) -> dict[str, Any]:
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


def extreme_excluded_metrics(
    trades: pd.DataFrame,
    *,
    extreme_trade_abs_return: float,
    periods_per_year: float,
) -> dict[str, float]:
    if trades.empty:
        return empty_return_metrics()
    clean = trades[trades["gross_return"].abs() <= extreme_trade_abs_return].copy()
    if clean.empty:
        return empty_return_metrics()
    returns = (
        clean.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"))
        .sort_values("exit_date")["period_return"]
    )
    return summarize_returns(returns, periods_per_year=periods_per_year)


def yearly_return_summary(trades: pd.DataFrame, *, periods_per_year: float) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    returns = (
        trades.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"))
        .sort_values("exit_date")
        .reset_index(drop=True)
    )
    returns["year"] = pd.to_datetime(returns["exit_date"]).dt.year
    rows: list[dict[str, Any]] = []
    for year, group in returns.groupby("year", sort=True):
        stats = summarize_returns(group["period_return"], periods_per_year=periods_per_year)
        rows.append(
            {
                "year": int(year),
                "period_count": int(len(group)),
                "total_return": float(stats["total_return"]),
                "sharpe": float(stats["sharpe"]),
                "max_drawdown": float(stats["max_drawdown"]),
                "win_rate": float(stats["win_rate"]),
            }
        )
    return rows


def empty_return_metrics() -> dict[str, float]:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
    }


def metric(metrics: dict[str, Any], name: str) -> float:
    try:
        return float(metrics.get(name, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def data_window(bars: pd.DataFrame, factors: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": min_date(bars, "date"),
        "max_bar_date": max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "factor_rows": int(len(factors)),
        "factor_assets": int(factors["asset_id"].nunique()) if "asset_id" in factors else 0,
        "factor_names": sorted(factors["factor_name"].dropna().astype(str).unique()) if "factor_name" in factors else [],
    }


def data_window_from_counts(
    bars: pd.DataFrame,
    *,
    factor_rows: int,
    factor_assets: int,
    factor_names: Sequence[str],
) -> dict[str, Any]:
    return {
        "min_bar_date": min_date(bars, "date"),
        "max_bar_date": max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "factor_rows": int(factor_rows),
        "factor_assets": int(factor_assets),
        "factor_names": sorted(set(str(name) for name in factor_names)),
    }


def min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def write_clean_technical_portfolio_diagnostic(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "clean_technical_portfolio_diagnostic.json").write_text(
        json.dumps(sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(
        output / "clean_technical_portfolio_diagnostic_leaderboard.csv",
        index=False,
    )


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (str, bytes, list, tuple, dict)) else False:
        return None
    return value


def _split_candidate_window(factor_name: str) -> tuple[str, int]:
    name = str(factor_name)
    prefix, separator, suffix = name.rpartition("_")
    if not separator or not suffix.isdigit():
        raise ValueError(f"Clean technical factor names must end with an integer window: {factor_name}")
    return prefix, int(suffix)
