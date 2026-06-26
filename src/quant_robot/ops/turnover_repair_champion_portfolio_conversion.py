from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.cn_stock_tradeability_gate import (
    CNStockTradeabilityPolicy,
    build_cn_stock_tradeability_frame,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (
    DEFAULT_MAX_PARTICIPATION,
    DEFAULT_PORTFOLIO_CAPITAL,
    DEFAULT_TOP_N,
    compute_turnover_continuous_capacity_repair_factors,
)
from quant_robot.ops.turnover_continuous_capacity_repair_preregistration import (
    SAFETY,
    TurnoverCapacityRepairCandidateSpec,
    default_turnover_continuous_capacity_repair_specs,
)
from quant_robot.storage.factor_inputs import load_factor_inputs


STAGE = "turnover_repair_champion_portfolio_conversion"
DEFAULT_CHAMPION_FACTOR_NAME = "turnover_rate_f_low_participation_budget_100k_20"
DEFAULT_COST_BPS_VALUES = (10.0, 20.0, 30.0)
DEFAULT_PORTFOLIO_VALUES = (100_000.0, 500_000.0, 1_000_000.0, 5_000_000.0)
DEFAULT_HOLDING_PERIOD = 20
DEFAULT_REBALANCE_INTERVAL = 20
DEFAULT_EXECUTION_LAG = 1
DEFAULT_MARKET_IMPACT_BPS = 10.0
DEFAULT_MIN_SIGNAL_AMOUNT = 10_000_000.0
DEFAULT_MAX_CALENDAR_HOLDING_DAYS = 45
DEFAULT_EXTREME_TRADE_ABS_RETURN = 0.50
DEFAULT_MAX_EXTREME_TRADE_RATE = 0.0
DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE = 0.50
DEFAULT_MAX_DRAWDOWN_FLOOR = -0.40
NEXT_WALK_FORWARD = "round127_turnover_repair_champion_walk_forward_cost_regime_validation"
NEXT_HIBERNATE = "round127_low_turnover_repair_hibernation_after_costed_conversion_failure"
TRADEABILITY_MASK_COLUMNS = [
    "entry_tradeable",
    "exit_tradeable",
    "suspended_official",
    "limit_up_official",
    "limit_down_official",
    "st_flag_official",
    "blocked_reasons",
]

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
    "trades_filtered_entry_tradeability",
    "trades_filtered_exit_tradeability",
    "trades_delayed_exit_tradeability",
    "max_tradeability_exit_delay_days",
    "tradeability_filtered_trades",
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
    "extreme_trade_return_count",
    "extreme_trade_return_rate",
    "hard_blocked",
    "walk_forward_candidate",
    "blockers",
]


def build_turnover_repair_champion_portfolio_conversion(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    factor_name: str = DEFAULT_CHAMPION_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    stock_basic: pd.DataFrame | None = None,
    stk_limit: pd.DataFrame | None = None,
    suspension: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
    tradeability_policy: CNStockTradeabilityPolicy | None = None,
    tradeability_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    daily_basic = load_factor_inputs(factor_input_root, "CN")
    factor_frame = compute_turnover_continuous_capacity_repair_factors(
        bars,
        daily_basic,
        candidate_specs=_champion_specs(factor_name),
        min_signal_date_amount=min_signal_date_amount,
        portfolio_capital=DEFAULT_PORTFOLIO_CAPITAL,
        top_n=top_n,
        max_participation=max_participation_rate,
    )
    if tradeability_frame is None:
        tradeability_frame = _build_tradeability_frame_if_supplied(
            bars,
            stock_basic=stock_basic,
            stk_limit=stk_limit,
            suspension=suspension,
            namechange=namechange,
            policy=tradeability_policy,
        )
    result = summarize_turnover_repair_champion_portfolio_conversion(
        factor_frame,
        bars,
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
        tradeability_frame=tradeability_frame,
    )
    result["data_window"] = _data_window(bars, factor_frame)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round125_turnover_repair_dedup_sensitivity",
        "source_report": "docs/research/cn_stock_turnover_repair_dedup_sensitivity_round125_2026-06-22.md",
        "scope": "single frozen champion only; no broad parameter grid",
    }
    result["markdown"] = render_turnover_repair_champion_portfolio_conversion_markdown(result)
    return result


def summarize_turnover_repair_champion_portfolio_conversion(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    factor_name: str = DEFAULT_CHAMPION_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    extreme_trade_abs_return: float = DEFAULT_EXTREME_TRADE_ABS_RETURN,
    max_extreme_trade_rate: float = DEFAULT_MAX_EXTREME_TRADE_RATE,
    periods_per_year: float | None = None,
    tradeability_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    _validate_inputs(
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        portfolio_values=portfolio_values,
        cost_bps_values=cost_bps_values,
    )
    prepared_factors = _prepare_champion_factors(factor_frame, factor_name)
    prepared_factors = _filter_rebalance_dates(prepared_factors, rebalance_interval)
    prepared_bars = _prepare_bars(bars)
    prepared_bars = _merge_tradeability_masks(prepared_bars, tradeability_frame)
    resolved_periods_per_year = periods_per_year or (252.0 / float(max(rebalance_interval, 1)))
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
                rebalance_interval=rebalance_interval,
                target_gross_exposure=1.0,
                periods_per_year=resolved_periods_per_year,
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
                    max_participation_rate=max_participation_rate,
                    extreme_trade_abs_return=extreme_trade_abs_return,
                    max_extreme_trade_rate=max_extreme_trade_rate,
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
            "periods_per_year": float(resolved_periods_per_year),
            "min_signal_amount": float(min_signal_amount),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "max_calendar_holding_days": int(max_calendar_holding_days or 0),
            "min_overlap_adjusted_sharpe": float(min_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
            "extreme_trade_abs_return": float(extreme_trade_abs_return),
            "max_extreme_trade_rate": float(max_extreme_trade_rate),
        },
        "summary": _summary(prepared_factors, leaderboard),
        "portfolio_conversion_policy": {
            "walk_forward_allowed_candidates": len(walk_forward_candidates),
            "allowed_case_ids": [row["case_id"] for row in walk_forward_candidates],
            "scope": "single frozen champion cost/capital stress only; no new parameter search",
            "next_direction": NEXT_WALK_FORWARD if walk_forward_candidates else NEXT_HIBERNATE,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "costed_conversion_is_not_walk_forward",
                "regime_coverage_not_yet_verified",
                "final_holdout_not_read",
                "dedup_revealed_zero_independent_new_alpha",
            ],
            "reason": "Round126 can only decide whether the single champion deserves walk-forward validation; it cannot promote a factor.",
        },
        "leaderboard": leaderboard,
        "next_direction": NEXT_WALK_FORWARD if walk_forward_candidates else NEXT_HIBERNATE,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_turnover_repair_champion_portfolio_conversion_markdown(result)
    return result


def write_turnover_repair_champion_portfolio_conversion(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "turnover_repair_champion_portfolio_conversion.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "turnover_repair_champion_portfolio_conversion.md").write_text(
        render_turnover_repair_champion_portfolio_conversion_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", []), columns=LEADERBOARD_COLUMNS).to_csv(
        output_path / "turnover_repair_champion_portfolio_conversion_leaderboard.csv",
        index=False,
    )


def render_turnover_repair_champion_portfolio_conversion_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    policy = result.get("portfolio_conversion_policy", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# Turnover Repair Champion Portfolio Conversion",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Factor: {thresholds.get('factor_name', DEFAULT_CHAMPION_FACTOR_NAME)}",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Signal rows: {summary.get('signal_rows', 0)}",
        f"- Factor names: {', '.join(summary.get('factor_names', [])) or 'none'}",
        f"- Walk-forward allowed candidates: {policy.get('walk_forward_allowed_candidates', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: {result.get('next_direction', NEXT_HIBERNATE)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Frozen Parameters",
        "",
        f"- TopN: {thresholds.get('top_n')}",
        f"- Holding period: {thresholds.get('holding_period')}",
        f"- Rebalance interval: {thresholds.get('rebalance_interval')}",
        f"- Execution lag: {thresholds.get('execution_lag')}",
        f"- Periods per year: {_fmt(thresholds.get('periods_per_year'))}",
        f"- Cost bps values: {thresholds.get('cost_bps_values')}",
        f"- Portfolio values: {thresholds.get('portfolio_values')}",
        "",
        "## Leaderboard",
        "",
        "| Case | Cost | Capital | Total | Ann | Sharpe | Overlap Sharpe | MaxDD | Win | CapTrades | ExtremeRate | Candidate | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "| {case} | {cost:.1f} | {capital:.0f} | {total:.2%} | {ann:.2%} | {sharpe:.3f} | {overlap:.3f} | {dd:.2%} | {win:.1%} | {cap} | {extreme:.2%} | {cand} | {blockers} |".format(
                case=row.get("case_id", ""),
                cost=_number(row.get("cost_bps")),
                capital=_number(row.get("portfolio_value")),
                total=_number(row.get("total_return")),
                ann=_number(row.get("annualized_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                win=_number(row.get("win_rate")),
                cap=int(_number(row.get("capacity_limited_trades"))),
                extreme=_number(row.get("extreme_trade_return_rate")),
                cand="yes" if row.get("walk_forward_candidate") else "no",
                blockers=row.get("blockers", "") or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- User drawdown tolerance is represented by the max-drawdown floor; capacity and data-quality blockers remain hard blockers.",
            "- A passing case may only advance to walk-forward cost/regime validation. It is not paper-ready or live/manual usable.",
        ]
    )
    return "\n".join(lines) + "\n"


def _champion_specs(factor_name: str) -> list[TurnoverCapacityRepairCandidateSpec]:
    specs = [spec for spec in default_turnover_continuous_capacity_repair_specs() if spec.factor_name == factor_name]
    if not specs:
        raise ValueError(f"Unknown turnover repair champion factor: {factor_name}")
    return specs


def _validate_inputs(
    *,
    top_n: int,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    portfolio_values: Sequence[float],
    cost_bps_values: Sequence[float],
) -> None:
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if holding_period < 1:
        raise ValueError("holding_period must be positive")
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be positive")
    if execution_lag < 1:
        raise ValueError("execution_lag must be positive")
    if not portfolio_values:
        raise ValueError("portfolio_values must not be empty")
    if not cost_bps_values:
        raise ValueError("cost_bps_values must not be empty")
    if any(float(value) <= 0.0 for value in portfolio_values):
        raise ValueError("portfolio_values must be positive")
    if any(float(value) < 0.0 for value in cost_bps_values):
        raise ValueError("cost_bps_values must be non-negative")


def _prepare_champion_factors(factor_frame: pd.DataFrame, factor_name: str) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(factor_frame, required, "factor_frame")
    frame = factor_frame[required].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    frame = frame[(frame["market"] == "CN") & (frame["factor_name"] == factor_name)]
    return frame.dropna(subset=["factor_value"]).reset_index(drop=True)


def _prepare_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    _require_columns(bars, required, "bars")
    optional = ["amount", *TRADEABILITY_MASK_COLUMNS]
    columns = required + [column for column in optional if column in bars.columns]
    frame = bars[columns].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    if "amount" in frame.columns:
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0)]
        .drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _build_tradeability_frame_if_supplied(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    stk_limit: pd.DataFrame | None,
    suspension: pd.DataFrame | None,
    namechange: pd.DataFrame | None,
    policy: CNStockTradeabilityPolicy | None,
) -> pd.DataFrame | None:
    if all(frame is None or frame.empty for frame in (stock_basic, stk_limit, suspension, namechange)):
        return None
    return build_cn_stock_tradeability_frame(
        _prepare_bars_for_tradeability_gate(bars),
        stock_basic,
        policy=policy,
        stk_limit=stk_limit,
        suspension=suspension,
        namechange=namechange,
    )


def _prepare_bars_for_tradeability_gate(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    _require_columns(bars, required, "bars")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    if "symbol" not in frame.columns:
        frame["symbol"] = frame["asset_id"]
    frame["symbol"] = frame["symbol"].fillna(frame["asset_id"]).astype(str)
    if "exchange" not in frame.columns:
        frame["exchange"] = frame["symbol"].map(_infer_exchange)
    frame["exchange"] = frame["exchange"].fillna("").astype(str)
    close = pd.to_numeric(frame["close"], errors="coerce") if "close" in frame.columns else pd.Series(pd.NA, index=frame.index)
    adj_close = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["close"] = close.fillna(adj_close)
    frame["open"] = (
        pd.to_numeric(frame["open"], errors="coerce") if "open" in frame.columns else pd.Series(pd.NA, index=frame.index)
    ).fillna(frame["close"])
    frame["high"] = pd.to_numeric(frame["high"], errors="coerce").fillna(frame["close"])
    frame["low"] = pd.to_numeric(frame["low"], errors="coerce").fillna(frame["close"])
    if "volume" in frame.columns:
        volume = pd.to_numeric(frame["volume"], errors="coerce")
    else:
        volume = pd.Series(pd.NA, index=frame.index)
    amount = pd.to_numeric(frame["amount"], errors="coerce")
    frame["amount"] = amount
    frame["volume"] = volume.fillna((amount / frame["close"].replace(0, pd.NA)).fillna(0.0))
    return frame[
        [
            "date",
            "asset_id",
            "symbol",
            "market",
            "exchange",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
        ]
    ]


def _merge_tradeability_masks(bars: pd.DataFrame, tradeability_frame: pd.DataFrame | None) -> pd.DataFrame:
    if tradeability_frame is None or tradeability_frame.empty:
        return bars
    mask_columns = [column for column in TRADEABILITY_MASK_COLUMNS if column in tradeability_frame.columns]
    if not mask_columns:
        return bars
    keys = ["date", "asset_id", "market"]
    _require_columns(tradeability_frame, keys, "tradeability_frame")
    masks = tradeability_frame[keys + mask_columns].copy()
    masks["date"] = pd.to_datetime(masks["date"]).dt.date
    masks["asset_id"] = masks["asset_id"].astype(str)
    masks["market"] = masks["market"].fillna("CN").astype(str).str.upper()
    masks = masks.drop_duplicates(keys, keep="last")
    base = bars.drop(columns=[column for column in mask_columns if column in bars.columns])
    merged = base.merge(masks, on=keys, how="left")
    for column in ("entry_tradeable", "exit_tradeable"):
        if column in merged.columns:
            merged[column] = merged[column].fillna(False).astype(bool)
    return merged


def _infer_exchange(symbol: object) -> str:
    text = str(symbol).upper()
    if text.endswith(".SH") or "XSHG" in text:
        return "XSHG"
    if text.endswith(".SZ") or "XSHE" in text:
        return "XSHE"
    if text.endswith(".BJ") or "XBEI" in text:
        return "XBEI"
    return ""


def _filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if rebalance_interval <= 1 or factors.empty:
        return factors.reset_index(drop=True)
    rows = []
    for _, group in factors.groupby(["market", "factor_name"], sort=True):
        signal_dates = sorted(pd.to_datetime(group["date"]).dt.date.unique())
        keep_dates = set(signal_dates[::rebalance_interval])
        rows.append(group[pd.to_datetime(group["date"]).dt.date.isin(keep_dates)])
    if not rows:
        return factors.iloc[0:0].copy()
    return pd.concat(rows, ignore_index=True).reset_index(drop=True)


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
    max_participation_rate: float,
    extreme_trade_abs_return: float,
    max_extreme_trade_rate: float,
) -> dict[str, Any]:
    extreme_count, extreme_rate = _extreme_trade_stats(trades, threshold=extreme_trade_abs_return)
    blockers = _blockers(
        metrics,
        trades=trades,
        cost_bps=cost_bps,
        max_participation_rate=max_participation_rate,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
        extreme_trade_count=extreme_count,
        extreme_trade_rate=extreme_rate,
        max_extreme_trade_rate=max_extreme_trade_rate,
    )
    hard_blocked = bool(blockers)
    walk_forward_candidate = bool(not hard_blocked and cost_bps > 0.0)
    market = str(trades["market"].iloc[0]) if not trades.empty and "market" in trades.columns else "CN"
    case_id = (
        f"{market}_{factor_name}_top{top_n}_hold{holding_period}_reb{rebalance_interval}_"
        f"lag{execution_lag}_cost{_case_number(cost_bps)}_cap{_case_number(portfolio_value)}"
    )
    row = {
        "case_id": case_id,
        "factor_name": factor_name,
        "market": market,
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
        "trades_filtered_entry_tradeability": int(_metric(metrics, "trades_filtered_entry_tradeability")),
        "trades_filtered_exit_tradeability": int(_metric(metrics, "trades_filtered_exit_tradeability")),
        "trades_delayed_exit_tradeability": int(_metric(metrics, "trades_delayed_exit_tradeability")),
        "max_tradeability_exit_delay_days": int(_metric(metrics, "max_tradeability_exit_delay_days")),
        "tradeability_filtered_trades": int(_metric(metrics, "tradeability_filtered_trades")),
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
        "extreme_trade_return_count": int(extreme_count),
        "extreme_trade_return_rate": float(extreme_rate),
        "hard_blocked": hard_blocked,
        "walk_forward_candidate": walk_forward_candidate,
        "blockers": ";".join(blockers),
    }
    return _sanitize(row)


def _blockers(
    metrics: dict[str, Any],
    *,
    trades: pd.DataFrame,
    cost_bps: float,
    max_participation_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
    extreme_trade_count: int,
    extreme_trade_rate: float,
    max_extreme_trade_rate: float,
) -> list[str]:
    blockers: list[str] = []
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
    if _metric(metrics, "max_participation_rate") > max_participation_rate:
        blockers.append("max_participation_rate_exceeded")
    if _metric(metrics, "calendar_limited_trades") > 0:
        blockers.append("calendar_holding_gate_filtered_trades")
    if extreme_trade_count > 0 and extreme_trade_rate > max_extreme_trade_rate:
        blockers.append("extreme_trade_return_present")
    if _metric(metrics, "max_drawdown") < max_drawdown_floor:
        blockers.append("max_drawdown_below_user_floor")
    if cost_bps == 0.0:
        return blockers
    return blockers


def _extreme_trade_stats(trades: pd.DataFrame, *, threshold: float) -> tuple[int, float]:
    if trades.empty or "gross_return" not in trades.columns:
        return 0, 0.0
    gross = pd.to_numeric(trades["gross_return"], errors="coerce").dropna()
    if gross.empty:
        return 0, 0.0
    count = int((gross.abs() > threshold).sum())
    return count, float(count / len(gross))


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
        "max_tradeability_filtered_trades": int(
            max((_number(row.get("tradeability_filtered_trades")) for row in leaderboard), default=0)
        ),
        "max_trades_delayed_exit_tradeability": int(
            max((_number(row.get("trades_delayed_exit_tradeability")) for row in leaderboard), default=0)
        ),
        "max_tradeability_exit_delay_days": int(
            max((_number(row.get("max_tradeability_exit_delay_days")) for row in leaderboard), default=0)
        ),
    }


def _data_window(bars: pd.DataFrame, factors: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _date_min(bars, "date"),
        "max_bar_date": _date_max(bars, "date"),
        "bar_rows": int(len(bars)),
        "min_signal_date": _date_min(factors, "date"),
        "max_signal_date": _date_max(factors, "date"),
        "factor_rows": int(len(factors)),
        "unique_assets": int(factors["asset_id"].nunique()) if "asset_id" in factors.columns else 0,
    }


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _metric(metrics: dict[str, Any], key: str) -> float:
    return _number(metrics.get(key, 0.0))


def _best_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


def _min_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(min((_number(row.get(key)) for row in rows), default=0.0))


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _case_number(value: float) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", "p")


def _fmt(value: Any) -> str:
    return f"{_number(value):.4f}"


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
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
