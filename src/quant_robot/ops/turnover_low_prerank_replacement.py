from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.clean_technical_portfolio_diagnostic import (
    SAFETY,
    apply_data_quality_quarantine,
    backtest_price_bars,
    filter_rebalance_dates,
    forward_trade_frame,
    run_fast_factor_backtest,
    sanitize,
)
from quant_robot.ops.daily_basic_clean_portfolio_diagnostic import (
    build_daily_basic_factor_frames,
    filter_daily_basic_to_bars,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.turnover_low_tradeability_exposure_diagnostic import (
    attach_tradeability_and_exposures,
    load_stock_metadata,
    load_tradeability_masks,
    period_return_records_from_trades,
    return_metric_pack,
    returns_by_exit_date,
)


STAGE = "turnover_low_prerank_replacement"
DEFAULT_VARIANTS = (
    {
        "variant": "turnover_low_top50_entry_cash_after",
        "drop_turnover_f_bottom_quantile": None,
        "allowed_stock_markets": None,
    },
    {
        "variant": "replace_drop_turnover_f_low10_entry_cash_after",
        "drop_turnover_f_bottom_quantile": 0.10,
        "allowed_stock_markets": None,
    },
    {
        "variant": "replace_drop_turnover_f_low10_mainboard_prerank",
        "drop_turnover_f_bottom_quantile": 0.10,
        "allowed_stock_markets": ("主板",),
    },
)


def run_turnover_low_prerank_replacement(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    tradeability_mask_roots: Iterable[str | Path],
    metadata_roots: Iterable[str | Path],
    output_dir: str | Path,
    variants: Sequence[dict[str, Any]] = DEFAULT_VARIANTS,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    factor_name: str = "turnover_rate_low",
    factor_price_column: str = "close",
    backtest_price_column: str = "close",
    top_n: int = 50,
    cost_bps: float = 5.0,
    holding_period: int = 20,
    rebalance_interval: int = 5,
    execution_lag: int = 1,
    min_signal_date_amount: float = 10_000_000.0,
    portfolio_value: float = 1_000_000.0,
    max_participation_rate: float = 0.05,
    market_impact_bps: float = 0.0,
    exclude_asset_prefixes: Sequence[str] = (),
    max_abs_daily_return_quarantine: float | None = None,
) -> dict[str, Any]:
    periods_per_year = 252.0 / float(max(int(rebalance_interval), 1))
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
    factor_bars = _factor_price_bars(bars, factor_price_column)
    factors = build_daily_basic_factor_frames(
        factor_bars,
        daily_basic,
        candidate_factor_names=(factor_name,),
        min_signal_date_amount=min_signal_date_amount,
    ).get(factor_name, pd.DataFrame())
    factors = filter_rebalance_dates(factors, int(rebalance_interval))
    factors = attach_signal_daily_basic_columns(factors, daily_basic, columns=("turnover_rate_f",))
    metadata = load_stock_metadata(metadata_roots)
    factors = attach_signal_metadata(factors, metadata, columns=("stock_market",))
    forward_trades = forward_trade_frame(
        backtest_price_bars(bars, backtest_price_column),
        execution_lag=execution_lag,
        holding_period=holding_period,
    )
    masks = load_tradeability_masks(tradeability_mask_roots)

    rows = []
    variant_outputs: dict[str, dict[str, Any]] = {}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for spec in variants:
        variant_name = str(spec["variant"])
        variant_factors = apply_prerank_variant_filters(factors, spec)
        base_metrics, trades = run_fast_factor_backtest(
            variant_factors,
            forward_trades,
            top_n=int(top_n),
            cost_bps=float(cost_bps),
            holding_period=int(holding_period),
            rebalance_interval=int(rebalance_interval),
            target_gross_exposure=1.0,
            periods_per_year=periods_per_year,
            market_impact_bps=float(market_impact_bps),
            max_participation_rate=float(max_participation_rate),
            portfolio_value=float(portfolio_value),
        )
        exposure = attach_tradeability_and_exposures(
            trades,
            daily_basic=daily_basic,
            metadata=metadata,
            tradeability_masks=masks,
        )
        raw_returns = returns_by_exit_date(exposure, "weighted_return")
        entry_cash_returns = returns_by_exit_date(exposure, "entry_cash_proxy_weighted_return")
        roundtrip_returns = returns_by_exit_date(exposure, "roundtrip_cash_proxy_weighted_return")
        variant_row = {
            "variant": variant_name,
            "candidate_rows_before_filter": int(len(factors)),
            "candidate_rows_after_filter": int(len(variant_factors)),
            "selected_trade_rows": int(len(exposure)),
            "entry_allowed_trade_rows": int(exposure["entry_allowed"].sum()) if "entry_allowed" in exposure else 0,
            "entry_allowed_trade_rate": _rate(exposure.get("entry_allowed", pd.Series(dtype=bool))),
            "raw": return_metric_pack(raw_returns, periods_per_year=periods_per_year, holding_period=holding_period),
            "entry_cash": return_metric_pack(
                entry_cash_returns,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            ),
            "roundtrip_cash": return_metric_pack(
                roundtrip_returns,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            ),
            "base_metrics": sanitize(base_metrics),
            "filters": _variant_filter_record(spec),
        }
        rows.append(_flat_row(variant_row))
        variant_outputs[variant_name] = sanitize(variant_row)
        pd.DataFrame(period_return_records_from_trades(exposure)).to_csv(
            output / f"{variant_name}_period_returns.csv",
            index=False,
        )
        exposure.to_parquet(output / f"{variant_name}_trades_with_tradeability.parquet", index=False)

    result = {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "factor_name": factor_name,
            "factor_price_column": factor_price_column,
            "backtest_price_column": backtest_price_column,
            "top_n": int(top_n),
            "cost_bps": float(cost_bps),
            "holding_period": int(holding_period),
            "rebalance_interval": int(rebalance_interval),
            "execution_lag": int(execution_lag),
            "min_signal_date_amount": float(min_signal_date_amount),
            "portfolio_value": float(portfolio_value),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "exclude_asset_prefixes": list(exclude_asset_prefixes),
            "max_abs_daily_return_quarantine": (
                None if max_abs_daily_return_quarantine is None else float(max_abs_daily_return_quarantine)
            ),
        },
        "data_quality_quarantine": quarantine,
        "summary": {
            "variant_count": int(len(rows)),
            "best_entry_cash_annualized_variant": _best_variant(rows, "entry_cash_annualized_return"),
            "best_entry_cash_overlap_variant": _best_variant(rows, "entry_cash_overlap_autocorr_adjusted_sharpe"),
            "best_entry_cash_drawdown_variant": _best_variant(rows, "entry_cash_max_drawdown", largest=True),
        },
        "rows": rows,
        "variant_outputs": variant_outputs,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Pre-rank replacement is a research check; final holdout remains sealed.",
        },
    }
    write_turnover_low_prerank_replacement(output, result)
    return sanitize(result)


def attach_signal_daily_basic_columns(
    factors: pd.DataFrame,
    daily_basic: pd.DataFrame,
    *,
    columns: Iterable[str],
) -> pd.DataFrame:
    if factors.empty:
        return factors.copy()
    keep = [column for column in columns if column in daily_basic]
    if not keep:
        return factors.copy()
    daily = daily_basic[["date", "asset_id", "market", *keep]].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["asset_id"] = daily["asset_id"].astype(str)
    daily["market"] = daily["market"].astype(str)
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    return frame.merge(daily, on=["date", "asset_id", "market"], how="left")


def attach_signal_metadata(
    factors: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    columns: Iterable[str],
) -> pd.DataFrame:
    if factors.empty or metadata.empty:
        return factors.copy()
    keep = [column for column in columns if column in metadata]
    if not keep or "asset_id" not in metadata:
        return factors.copy()
    meta = metadata[["asset_id", *keep]].copy()
    meta["asset_id"] = meta["asset_id"].astype(str)
    frame = factors.copy()
    frame["asset_id"] = frame["asset_id"].astype(str)
    return frame.merge(meta.drop_duplicates("asset_id"), on="asset_id", how="left")


def apply_prerank_variant_filters(factors: pd.DataFrame, spec: dict[str, Any]) -> pd.DataFrame:
    frame = factors.copy()
    quantile = spec.get("drop_turnover_f_bottom_quantile")
    if quantile is not None:
        frame = drop_bottom_quantile_by_date(frame, "turnover_rate_f", float(quantile))
    allowed_stock_markets = spec.get("allowed_stock_markets")
    if allowed_stock_markets:
        frame = filter_allowed_stock_markets(frame, allowed_stock_markets=tuple(allowed_stock_markets))
    return frame.reset_index(drop=True)


def drop_bottom_quantile_by_date(frame: pd.DataFrame, value_column: str, quantile: float) -> pd.DataFrame:
    if value_column not in frame:
        raise ValueError(f"frame missing value column: {value_column}")
    if quantile <= 0.0:
        return frame.copy()
    if quantile >= 1.0:
        raise ValueError("quantile must be below 1")
    working = frame.copy()
    working["date"] = pd.to_datetime(working["date"])
    values = pd.to_numeric(working[value_column], errors="coerce")
    thresholds = values.groupby(working["date"]).transform(lambda series: series.quantile(float(quantile)))
    return working[values.notna() & (values > thresholds)].reset_index(drop=True)


def filter_allowed_stock_markets(
    frame: pd.DataFrame,
    *,
    allowed_stock_markets: Sequence[str],
) -> pd.DataFrame:
    if "stock_market" not in frame:
        raise ValueError("frame missing stock_market column")
    allowed = {str(value) for value in allowed_stock_markets}
    values = frame["stock_market"].fillna("UNKNOWN").astype(str)
    return frame[values.isin(allowed)].reset_index(drop=True)


def write_turnover_low_prerank_replacement(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize(result)
    (output / "turnover_low_prerank_replacement.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "turnover_low_prerank_replacement_rows.csv", index=False)


def _factor_price_bars(bars: pd.DataFrame, price_column: str) -> pd.DataFrame:
    column = str(price_column)
    if column == "close":
        return bars
    if column not in bars:
        raise ValueError(f"factor price column is missing from bars: {column}")
    output = bars.copy()
    output["close"] = pd.to_numeric(output[column], errors="coerce")
    return output


def _flat_row(row: dict[str, Any]) -> dict[str, Any]:
    output = {
        "variant": row["variant"],
        "candidate_rows_before_filter": row["candidate_rows_before_filter"],
        "candidate_rows_after_filter": row["candidate_rows_after_filter"],
        "selected_trade_rows": row["selected_trade_rows"],
        "entry_allowed_trade_rows": row["entry_allowed_trade_rows"],
        "entry_allowed_trade_rate": row["entry_allowed_trade_rate"],
    }
    for namespace in ("raw", "entry_cash", "roundtrip_cash"):
        for key, value in row[namespace].items():
            if isinstance(value, (int, float, np.integer, np.floating)):
                output[f"{namespace}_{key}"] = float(value)
    for key, value in row["filters"].items():
        output[f"filter_{key}"] = value
    return sanitize(output)


def _variant_filter_record(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "drop_turnover_f_bottom_quantile": spec.get("drop_turnover_f_bottom_quantile"),
        "allowed_stock_markets": list(spec.get("allowed_stock_markets") or []),
    }


def _best_variant(rows: list[dict[str, Any]], key: str, *, largest: bool = True) -> str | None:
    values = [row for row in rows if key in row]
    if not values:
        return None
    chosen = max(values, key=lambda row: float(row[key])) if largest else min(values, key=lambda row: float(row[key]))
    return str(chosen["variant"])


def _rate(values: pd.Series) -> float:
    if values is None or len(values) == 0:
        return 0.0
    return float(pd.Series(values).fillna(False).astype(bool).mean())
