from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.clean_technical_portfolio_diagnostic import (
    SAFETY,
    apply_data_quality_quarantine,
    backtest_price_bars,
    filter_rebalance_dates,
    forward_trade_frame,
    overlap_metrics,
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


STAGE = "turnover_low_tradeability_exposure_diagnostic"
DEFAULT_EXPOSURE_COLUMNS = (
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe_ttm",
    "pb",
    "ps_ttm",
    "dv_ttm",
    "total_mv",
    "circ_mv",
)
DEFAULT_METADATA_COLUMNS = (
    "asset_id",
    "exchange",
    "industry",
    "stock_market",
    "list_date",
    "delist_date",
    "is_active",
    "is_hs",
)


def run_turnover_low_tradeability_exposure_diagnostic(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    tradeability_mask_roots: Iterable[str | Path],
    metadata_roots: Iterable[str | Path],
    output_dir: str | Path,
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
    extreme_trade_abs_return: float = 0.50,
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
    forward_trades = forward_trade_frame(
        backtest_price_bars(bars, backtest_price_column),
        execution_lag=execution_lag,
        holding_period=holding_period,
    )
    base_metrics, trades = run_fast_factor_backtest(
        factors,
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
    metadata = load_stock_metadata(metadata_roots)
    masks = load_tradeability_masks(tradeability_mask_roots)
    exposure = attach_tradeability_and_exposures(
        trades,
        daily_basic=daily_basic,
        metadata=metadata,
        tradeability_masks=masks,
    )
    result = summarize_turnover_low_tradeability_exposure(
        exposure,
        base_metrics=base_metrics,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        extreme_trade_abs_return=extreme_trade_abs_return,
    )
    result.update(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "source_context": {
                "purpose": "diagnose whether low-turnover profits survive real A-share tradeability and exposure stress",
                "not_paper_ready": True,
                "promotion_allowed": False,
            },
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
                "extreme_trade_abs_return": float(extreme_trade_abs_return),
            },
            "data_quality_quarantine": quarantine,
            "data_window": {
                "bar_rows": int(len(bars)),
                "bar_assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
                "daily_basic_rows": int(len(daily_basic)),
                "factor_rows_after_rebalance_filter": int(len(factors)),
                "trade_rows": int(len(trades)),
                "metadata_rows": int(len(metadata)),
                "tradeability_mask_rows": int(len(masks)),
            },
        }
    )
    write_turnover_low_tradeability_exposure_diagnostic(output_dir, result)
    return result


def attach_tradeability_and_exposures(
    trades: pd.DataFrame,
    *,
    daily_basic: pd.DataFrame,
    metadata: pd.DataFrame,
    tradeability_masks: pd.DataFrame,
) -> pd.DataFrame:
    frame = trades.copy()
    if frame.empty:
        return _empty_trade_exposure_frame()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame["entry_date"] = pd.to_datetime(frame["entry_date"])
    frame["exit_date"] = pd.to_datetime(frame["exit_date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)

    daily = daily_basic.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["asset_id"] = daily["asset_id"].astype(str)
    daily["market"] = daily["market"].astype(str)
    exposure_columns = [column for column in DEFAULT_EXPOSURE_COLUMNS if column in daily.columns]
    frame = frame.merge(
        daily[["date", "asset_id", "market", *exposure_columns]].rename(columns={"date": "signal_date"}),
        on=["signal_date", "asset_id", "market"],
        how="left",
    )

    if not metadata.empty:
        meta = metadata.copy()
        meta["asset_id"] = meta["asset_id"].astype(str)
        columns = [column for column in DEFAULT_METADATA_COLUMNS if column in meta.columns]
        frame = frame.merge(meta[columns].drop_duplicates("asset_id"), on="asset_id", how="left")

    if not tradeability_masks.empty:
        masks = tradeability_masks.copy()
        masks["date"] = pd.to_datetime(masks["date"])
        masks["asset_id"] = masks["asset_id"].astype(str)
        entry_columns = [
            column
            for column in ("date", "asset_id", "entry_tradeable", "can_buy", "blocked_reasons")
            if column in masks.columns
        ]
        exit_columns = [
            column
            for column in ("date", "asset_id", "exit_tradeable", "can_sell", "blocked_reasons")
            if column in masks.columns
        ]
        frame = frame.merge(
            masks[entry_columns].rename(
                columns={"date": "entry_date", "blocked_reasons": "entry_blocked_reasons"}
            ),
            on=["entry_date", "asset_id"],
            how="left",
        )
        frame = frame.merge(
            masks[exit_columns].rename(columns={"date": "exit_date", "blocked_reasons": "exit_blocked_reasons"}),
            on=["exit_date", "asset_id"],
            how="left",
        )

    for column in ("entry_tradeable", "exit_tradeable", "can_buy", "can_sell"):
        if column not in frame:
            frame[column] = True
        frame[f"{column}_missing"] = frame[column].isna()
        frame[column] = frame[column].fillna(True).astype(bool)
    for column in ("entry_blocked_reasons", "exit_blocked_reasons"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    frame["entry_allowed"] = frame["entry_tradeable"] & frame["can_buy"]
    frame["exit_allowed"] = frame["exit_tradeable"] & frame["can_sell"]
    frame["fully_tradeable_roundtrip"] = frame["entry_allowed"] & frame["exit_allowed"]
    frame["entry_cash_proxy_weighted_return"] = np.where(frame["entry_allowed"], frame["weighted_return"], 0.0)
    frame["roundtrip_cash_proxy_weighted_return"] = np.where(
        frame["fully_tradeable_roundtrip"],
        frame["weighted_return"],
        0.0,
    )
    return frame


def summarize_turnover_low_tradeability_exposure(
    trades: pd.DataFrame,
    *,
    base_metrics: dict[str, Any],
    periods_per_year: float,
    extreme_trade_abs_return: float,
    holding_period: int = 20,
) -> dict[str, Any]:
    if trades.empty:
        return {
            "summary": {"trade_rows": 0},
            "base_metrics": sanitize(base_metrics),
            "tradeability_metrics": {},
            "drawdown": {},
            "worst_years": [],
            "worst_months": [],
            "bucket_summaries": {},
            "industry_contribution": {"worst": [], "best": []},
            "worst_trades": [],
        }
    output = trades.copy()
    output["exit_date"] = pd.to_datetime(output["exit_date"])
    period_returns = returns_by_exit_date(output, "weighted_return")
    entry_cash_returns = returns_by_exit_date(output, "entry_cash_proxy_weighted_return")
    roundtrip_cash_returns = returns_by_exit_date(output, "roundtrip_cash_proxy_weighted_return")
    summary = {
        "trade_rows": int(len(output)),
        "period_rows": int(len(period_returns)),
        "entry_blocked_trade_rows": int((~output["entry_allowed"]).sum()),
        "entry_blocked_trade_rate": _rate(~output["entry_allowed"]),
        "exit_blocked_trade_rows": int((~output["exit_allowed"]).sum()),
        "exit_blocked_trade_rate": _rate(~output["exit_allowed"]),
        "roundtrip_blocked_trade_rows": int((~output["fully_tradeable_roundtrip"]).sum()),
        "roundtrip_blocked_trade_rate": _rate(~output["fully_tradeable_roundtrip"]),
        "roundtrip_blocked_weighted_return_sum": _sum(output.loc[~output["fully_tradeable_roundtrip"], "weighted_return"]),
        "roundtrip_allowed_weighted_return_sum": _sum(output.loc[output["fully_tradeable_roundtrip"], "weighted_return"]),
        "extreme_trade_return_count": int((output["gross_return"].abs() > float(extreme_trade_abs_return)).sum()),
        "extreme_trade_return_rate": _rate(output["gross_return"].abs() > float(extreme_trade_abs_return)),
    }
    return {
        "summary": summary,
        "base_metrics": sanitize(base_metrics),
        "tradeability_metrics": {
            "entry_cash_proxy": return_metric_pack(
                entry_cash_returns,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            ),
            "roundtrip_cash_proxy": return_metric_pack(
                roundtrip_cash_returns,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            ),
        },
        "drawdown": drawdown_summary(period_returns),
        "period_returns": period_return_records_from_trades(output),
        "worst_years": worst_periods(period_returns, "Y", limit=8),
        "worst_months": worst_periods(period_returns, "M", limit=15),
        "blocked_reasons_top": blocked_reason_counts(output, limit=20),
        "bucket_summaries": bucket_summaries(output),
        "industry_contribution": industry_contribution(output),
        "worst_trades": worst_trades(output, limit=50),
    }


def load_stock_metadata(roots: Iterable[str | Path]) -> pd.DataFrame:
    paths = _parquet_paths(roots)
    if not paths:
        return pd.DataFrame(columns=DEFAULT_METADATA_COLUMNS)
    frames = [pd.read_parquet(path) for path in paths]
    if not frames:
        return pd.DataFrame(columns=DEFAULT_METADATA_COLUMNS)
    frame = pd.concat(frames, ignore_index=True)
    if "asset_id" in frame:
        frame = frame.drop_duplicates("asset_id")
    return frame


def load_tradeability_masks(roots: Iterable[str | Path]) -> pd.DataFrame:
    paths = _parquet_paths(roots)
    if not paths:
        return pd.DataFrame()
    columns = [
        "date",
        "asset_id",
        "entry_tradeable",
        "exit_tradeable",
        "can_buy",
        "can_sell",
        "blocked_reasons",
    ]
    frames = []
    for path in paths:
        frame = pd.read_parquet(path)
        frames.append(frame[[column for column in columns if column in frame.columns]])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def write_turnover_low_tradeability_exposure_diagnostic(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "turnover_low_tradeability_exposure_diagnostic.json").write_text(
        json.dumps(sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_csv(output / "turnover_low_bucket_summary.csv", _flatten_bucket_summaries(result.get("bucket_summaries", {})))
    _write_csv(output / "turnover_low_industry_worst.csv", result.get("industry_contribution", {}).get("worst", []))
    _write_csv(output / "turnover_low_industry_best.csv", result.get("industry_contribution", {}).get("best", []))
    _write_csv(output / "turnover_low_worst_trades.csv", result.get("worst_trades", []))
    _write_csv(output / "turnover_low_period_returns.csv", result.get("period_returns", []))


def returns_by_exit_date(trades: pd.DataFrame, column: str) -> pd.Series:
    if trades.empty or column not in trades:
        return pd.Series(dtype=float)
    returns = (
        trades.groupby("exit_date", as_index=False)
        .agg(period_return=(column, "sum"))
        .sort_values("exit_date")
    )
    return pd.Series(returns["period_return"].to_numpy(dtype=float), index=pd.to_datetime(returns["exit_date"]))


def period_return_records(
    raw_returns: pd.Series,
    entry_cash_returns: pd.Series,
    roundtrip_cash_returns: pd.Series,
) -> list[dict[str, Any]]:
    dates = raw_returns.index.union(entry_cash_returns.index).union(roundtrip_cash_returns.index).sort_values()
    rows = []
    for date in dates:
        rows.append(
            {
                "date": pd.Timestamp(date).date().isoformat(),
                "raw_return": float(raw_returns.get(date, 0.0)),
                "entry_cash_proxy_return": float(entry_cash_returns.get(date, 0.0)),
                "roundtrip_cash_proxy_return": float(roundtrip_cash_returns.get(date, 0.0)),
            }
        )
    return rows


def period_return_records_from_trades(trades: pd.DataFrame) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    frame = trades.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame["entry_date"] = pd.to_datetime(frame["entry_date"])
    frame["exit_date"] = pd.to_datetime(frame["exit_date"])
    rows = []
    for exit_date, group in frame.groupby("exit_date", sort=True):
        signal_dates = sorted(pd.to_datetime(group["signal_date"]).dropna().unique())
        entry_dates = sorted(pd.to_datetime(group["entry_date"]).dropna().unique())
        rows.append(
            {
                "date": pd.Timestamp(exit_date).date().isoformat(),
                "signal_date": _first_date(signal_dates),
                "entry_date": _first_date(entry_dates),
                "signal_date_count": int(len(signal_dates)),
                "entry_date_count": int(len(entry_dates)),
                "raw_return": _sum(group["weighted_return"]),
                "entry_cash_proxy_return": _sum(group["entry_cash_proxy_weighted_return"]),
                "roundtrip_cash_proxy_return": _sum(group["roundtrip_cash_proxy_weighted_return"]),
            }
        )
    return rows


def return_metric_pack(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, Any]:
    metrics = summarize_returns(returns.reset_index(drop=True), periods_per_year=periods_per_year)
    metrics.update(
        overlap_metrics(
            returns.reset_index(drop=True),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
    )
    return sanitize(metrics)


def drawdown_summary(returns: pd.Series) -> dict[str, Any]:
    if returns.empty:
        return {}
    equity = (1.0 + returns).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    trough_idx = drawdown.idxmin()
    peak_idx = equity.loc[:trough_idx].idxmax()
    return {
        "max_drawdown": float(drawdown.loc[trough_idx]),
        "peak_date": pd.Timestamp(peak_idx).date().isoformat(),
        "trough_date": pd.Timestamp(trough_idx).date().isoformat(),
        "peak_equity": float(equity.loc[peak_idx]),
        "trough_equity": float(equity.loc[trough_idx]),
    }


def worst_periods(returns: pd.Series, period: str, *, limit: int) -> list[dict[str, Any]]:
    if returns.empty:
        return []
    frame = pd.DataFrame({"date": pd.to_datetime(returns.index), "period_return": returns.to_numpy(dtype=float)})
    frame["period"] = frame["date"].dt.to_period(period).astype(str)
    grouped = (
        frame.groupby("period", as_index=False)["period_return"]
        .apply(lambda series: float((1.0 + series).prod() - 1.0))
        .rename(columns={"period_return": "total_return"})
        .sort_values("total_return")
        .head(int(limit))
    )
    return grouped.to_dict("records")


def blocked_reason_counts(trades: pd.DataFrame, *, limit: int) -> dict[str, int]:
    blocked = trades[~trades["fully_tradeable_roundtrip"]]
    if blocked.empty:
        return {}
    reasons = (
        blocked["entry_blocked_reasons"].fillna("").astype(str)
        + ";"
        + blocked["exit_blocked_reasons"].fillna("").astype(str)
    )
    counts: dict[str, int] = {}
    for text in reasons:
        for part in str(text).split(";"):
            reason = part.strip()
            if not reason:
                continue
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: int(limit)])


def bucket_summaries(trades: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    summaries: dict[str, list[dict[str, Any]]] = {}
    for column in DEFAULT_EXPOSURE_COLUMNS:
        if column not in trades:
            continue
        numeric = pd.to_numeric(trades[column], errors="coerce")
        valid = trades[numeric.notna()].copy()
        if valid.empty:
            continue
        try:
            valid["bucket"] = pd.qcut(numeric[numeric.notna()].rank(method="first"), 5, labels=False, duplicates="drop")
        except ValueError:
            continue
        grouped = (
            valid.groupby("bucket")
            .agg(
                trades=("weighted_return", "size"),
                weighted_return_sum=("weighted_return", "sum"),
                avg_gross_return=("gross_return", "mean"),
                blocked_rate=("fully_tradeable_roundtrip", lambda series: float((~series).mean())),
                avg_value=(column, "mean"),
            )
            .reset_index()
        )
        summaries[column] = _records(grouped)
    return summaries


def industry_contribution(trades: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    if "industry" not in trades:
        return {"worst": [], "best": []}
    frame = trades.copy()
    frame["industry"] = frame["industry"].fillna("__missing__").astype(str)
    grouped = (
        frame.groupby("industry")
        .agg(
            trades=("weighted_return", "size"),
            weighted_return_sum=("weighted_return", "sum"),
            avg_gross_return=("gross_return", "mean"),
            blocked_rate=("fully_tradeable_roundtrip", lambda series: float((~series).mean())),
        )
        .reset_index()
        .sort_values("weighted_return_sum")
    )
    return {
        "worst": _records(grouped.head(20)),
        "best": _records(grouped.tail(20).sort_values("weighted_return_sum", ascending=False)),
    }


def worst_trades(trades: pd.DataFrame, *, limit: int) -> list[dict[str, Any]]:
    columns = [
        "signal_date",
        "entry_date",
        "exit_date",
        "asset_id",
        "industry",
        "stock_market",
        "gross_return",
        "weighted_return",
        "turnover_rate",
        "circ_mv",
        "entry_allowed",
        "exit_allowed",
        "entry_blocked_reasons",
        "exit_blocked_reasons",
    ]
    available = [column for column in columns if column in trades]
    frame = trades.sort_values("weighted_return").head(int(limit))[available].copy()
    for column in ("signal_date", "entry_date", "exit_date"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column]).dt.date.astype(str)
    return _records(frame)


def _factor_price_bars(bars: pd.DataFrame, price_column: str) -> pd.DataFrame:
    column = str(price_column)
    if column == "adj_close":
        return bars
    if column not in bars:
        raise ValueError(f"factor price column is missing from bars: {column}")
    output = bars.copy()
    output["adj_close"] = pd.to_numeric(output[column], errors="coerce")
    return output


def _parquet_paths(roots: Iterable[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        path = Path(root)
        if path.is_file() and path.suffix == ".parquet":
            paths.append(path)
        elif path.exists():
            paths.extend(sorted(path.rglob("*.parquet")))
    return paths


def _empty_trade_exposure_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "signal_date",
            "entry_date",
            "exit_date",
            "asset_id",
            "market",
            "weighted_return",
            "entry_allowed",
            "exit_allowed",
            "fully_tradeable_roundtrip",
        ]
    )


def _flatten_bucket_summaries(summaries: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for name, items in summaries.items():
        for item in items:
            row = dict(item)
            row["exposure"] = name
            rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [sanitize(record) for record in frame.to_dict("records")]


def _rate(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else 0.0


def _sum(values: pd.Series) -> float:
    return float(pd.to_numeric(values, errors="coerce").fillna(0.0).sum())


def _first_date(values: Sequence[Any]) -> str | None:
    if not values:
        return None
    return pd.Timestamp(values[0]).date().isoformat()
