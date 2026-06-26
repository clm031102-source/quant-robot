from __future__ import annotations

from datetime import date
import csv
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
from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    STRICT_RESIDUAL_FACTOR_NAME,
    build_market_state_frame,
    _strict_clean_lead_frame,
)
from quant_robot.ops.daily_basic_non_price_public_carry_lead_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    DEFAULT_RESIDUAL_EXPOSURES,
    build_daily_basic_lead_exposure_frame,
    residualize_daily_basic_lead,
    _merge_lead_exposures,
    _normalise_exposure_frame,
    _normalise_lead,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    SAFETY,
    default_daily_basic_non_price_public_carry_specs,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    _sanitize,
    attach_daily_basic_capacity_fields,
    compute_daily_basic_non_price_public_carry_factors,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (
    DEFAULT_MAX_PARTICIPATION,
)
from quant_robot.ops.turnover_repair_champion_portfolio_conversion import (
    DEFAULT_EXECUTION_LAG,
    DEFAULT_EXTREME_TRADE_ABS_RETURN,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
    DEFAULT_REBALANCE_INTERVAL,
    _case_row,
    _data_window,
    _filter_rebalance_dates,
    _prepare_bars,
    _prepare_champion_factors,
)


STAGE = "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight"
DEFAULT_COST_BPS_VALUES = (10.0, 20.0)
DEFAULT_PORTFOLIO_VALUES = (100_000.0, 500_000.0, 1_000_000.0)
DEFAULT_TOP_N = 100
DEFAULT_MAX_DRAWDOWN_FLOOR = -0.30
DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE = 0.30
DEFAULT_TRAIN_END_DATE = "2024-12-31"
DEFAULT_TEST_START_DATE = "2025-01-01"
DEFAULT_GUARD_MODES = ("none", "block_stress_rebalance_dates")
NEXT_WALK_FORWARD = "round137_daily_basic_free_float_supply_quality_walk_forward_cost_regime_validation"
NEXT_EXTREME_TRADE_AUDIT = "round137_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit"
NEXT_HIBERNATE = "round137_daily_basic_free_float_supply_quality_hibernation_or_family_rotation_after_preflight"

LEADERBOARD_COLUMNS = [
    "case_id",
    "factor_name",
    "guard_mode",
    "market",
    "top_n",
    "holding_period",
    "rebalance_interval",
    "execution_lag",
    "cost_bps",
    "market_impact_bps",
    "portfolio_value",
    "guarded_signal_rows",
    "guarded_signal_dates",
    "stress_guarded_dates_blocked",
    "trades",
    "train_trades",
    "test_trades",
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
    "extreme_trade_return_count",
    "extreme_trade_return_rate",
    "train_total_return",
    "train_annualized_return",
    "train_sharpe",
    "train_overlap_autocorr_adjusted_sharpe",
    "train_max_drawdown",
    "train_win_rate",
    "test_total_return",
    "test_annualized_return",
    "test_sharpe",
    "test_overlap_autocorr_adjusted_sharpe",
    "test_max_drawdown",
    "test_win_rate",
    "test_capacity_limited_trades",
    "hard_blocked",
    "walk_forward_candidate",
    "blockers",
]
EXTREME_TRADE_COLUMNS = [
    "case_id",
    "guard_mode",
    "cost_bps",
    "portfolio_value",
    "signal_date",
    "entry_date",
    "exit_date",
    "asset_id",
    "market",
    "gross_return",
    "net_return",
    "weighted_return",
    "target_notional",
    "entry_amount",
    "participation_rate",
]


def build_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    factor_name: str = STRICT_RESIDUAL_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    guard_modes: Sequence[str] = DEFAULT_GUARD_MODES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_cross_section: int = 30,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_field_coverage_ratio: float = 0.95,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    min_oos_overlap_adjusted_sharpe: float = DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    train_end_date: str = DEFAULT_TRAIN_END_DATE,
    test_start_date: str = DEFAULT_TEST_START_DATE,
) -> dict[str, Any]:
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        daily_basic_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    lead_specs = [
        spec for spec in default_daily_basic_non_price_public_carry_specs() if spec.factor_name == lead_factor_name
    ]
    lead_frame = compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=lead_specs)
    lead_frame = attach_daily_basic_capacity_fields(lead_frame, bars)
    exposure_frame = build_daily_basic_lead_exposure_frame(daily_basic, bars)
    lead = _normalise_lead(lead_frame, lead_factor_name=lead_factor_name)
    exposures = _normalise_exposure_frame(exposure_frame)
    lead_with_exposures = _merge_lead_exposures(lead, exposures)
    strict_lead = _strict_clean_lead_frame(
        lead_with_exposures,
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_signal_date_amount=min_signal_date_amount,
    )
    strict_residual_frame = residualize_daily_basic_lead(
        strict_lead,
        exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
        residual_factor_name=factor_name,
        min_cross_section=min_cross_section,
    )
    result = summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
        strict_residual_frame,
        bars,
        market_state_frame=build_market_state_frame(bars),
        factor_name=factor_name,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        guard_modes=guard_modes,
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        min_signal_amount=min_signal_amount,
        max_participation_rate=max_participation_rate,
        market_impact_bps=market_impact_bps,
        max_calendar_holding_days=max_calendar_holding_days,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        min_oos_overlap_adjusted_sharpe=min_oos_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
        train_end_date=train_end_date,
        test_start_date=test_start_date,
    )
    window = _data_window(bars, strict_residual_frame)
    result["lead_factor_name"] = lead_factor_name
    result["data_window"] = window | {
        "min_factor_date": window.get("min_signal_date"),
        "max_factor_date": window.get("max_signal_date"),
        "lead_rows": int(len(lead_frame)),
        "strict_clean_lead_rows": int(len(strict_lead)),
        "strict_clean_residual_rows": int(len(strict_residual_frame)),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round134_daily_basic_free_float_supply_quality_residual_stability_audit",
        "source_report": "docs/research/cn_stock_daily_basic_free_float_supply_quality_residual_stability_audit_round134_2026-06-22.md",
        "review_report": "docs/research/cn_stock_round132_134_three_round_review_2026-06-22.md",
        "scope": "single frozen strict-clean residual candidate; no alpha parameter expansion",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "min_signal_amount": min_signal_amount,
        "min_field_coverage_ratio": min_field_coverage_ratio,
        "max_participation_rate": max_participation_rate,
        "capacity_and_extreme_trade_gates_remain_hard": True,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_markdown(result)
    return result


def summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    market_state_frame: pd.DataFrame | None = None,
    factor_name: str = STRICT_RESIDUAL_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    guard_modes: Sequence[str] = DEFAULT_GUARD_MODES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    min_oos_overlap_adjusted_sharpe: float = DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    extreme_trade_abs_return: float = DEFAULT_EXTREME_TRADE_ABS_RETURN,
    train_end_date: str = DEFAULT_TRAIN_END_DATE,
    test_start_date: str = DEFAULT_TEST_START_DATE,
    periods_per_year: float | None = None,
) -> dict[str, Any]:
    _validate_inputs(
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        portfolio_values=portfolio_values,
        cost_bps_values=cost_bps_values,
        guard_modes=guard_modes,
    )
    prepared_factors = _prepare_champion_factors(factor_frame, factor_name)
    prepared_factors = _filter_rebalance_dates(prepared_factors, rebalance_interval)
    prepared_bars = _prepare_bars(bars)
    resolved_periods_per_year = periods_per_year or (252.0 / float(max(rebalance_interval, 1)))
    leaderboard: list[dict[str, Any]] = []
    extreme_trades: list[dict[str, Any]] = []
    for guard_mode in guard_modes:
        guarded_factors = apply_stress_guard_to_factor_frame(
            prepared_factors,
            market_state_frame,
            guard_mode=guard_mode,
        )
        blocked_dates = _blocked_stress_date_count(prepared_factors, guarded_factors, guard_mode)
        for cost_bps in cost_bps_values:
            for portfolio_value in portfolio_values:
                full = _run_backtest(
                    guarded_factors,
                    prepared_bars,
                    top_n=top_n,
                    cost_bps=float(cost_bps),
                    holding_period=holding_period,
                    rebalance_interval=rebalance_interval,
                    execution_lag=execution_lag,
                    min_signal_amount=min_signal_amount,
                    max_participation_rate=max_participation_rate,
                    market_impact_bps=market_impact_bps,
                    max_calendar_holding_days=max_calendar_holding_days,
                    portfolio_value=float(portfolio_value),
                    periods_per_year=resolved_periods_per_year,
                )
                train = _run_backtest(
                    *_window_frames(guarded_factors, prepared_bars, end_date=train_end_date),
                    top_n=top_n,
                    cost_bps=float(cost_bps),
                    holding_period=holding_period,
                    rebalance_interval=rebalance_interval,
                    execution_lag=execution_lag,
                    min_signal_amount=min_signal_amount,
                    max_participation_rate=max_participation_rate,
                    market_impact_bps=market_impact_bps,
                    max_calendar_holding_days=max_calendar_holding_days,
                    portfolio_value=float(portfolio_value),
                    periods_per_year=resolved_periods_per_year,
                )
                test = _run_backtest(
                    *_window_frames(guarded_factors, prepared_bars, start_date=test_start_date),
                    top_n=top_n,
                    cost_bps=float(cost_bps),
                    holding_period=holding_period,
                    rebalance_interval=rebalance_interval,
                    execution_lag=execution_lag,
                    min_signal_amount=min_signal_amount,
                    max_participation_rate=max_participation_rate,
                    market_impact_bps=market_impact_bps,
                    max_calendar_holding_days=max_calendar_holding_days,
                    portfolio_value=float(portfolio_value),
                    periods_per_year=resolved_periods_per_year,
                )
                row = _case_row(
                    full.metrics,
                    full.trades,
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
                    max_extreme_trade_rate=0.0,
                )
                row.update(
                    _split_metrics(
                        train.metrics,
                        test.metrics,
                        train_trades=len(train.trades),
                        test_trades=len(test.trades),
                    )
                )
                row["case_id"] = row["case_id"].replace(
                    f"CN_{factor_name}_",
                    f"CN_{factor_name}_{guard_mode}_",
                    1,
                )
                row["guard_mode"] = guard_mode
                row["guarded_signal_rows"] = int(len(guarded_factors))
                row["guarded_signal_dates"] = int(guarded_factors["date"].nunique()) if not guarded_factors.empty else 0
                row["stress_guarded_dates_blocked"] = int(blocked_dates)
                blockers = _merge_blockers(
                    row.get("blockers", ""),
                    _oos_blockers(
                        row,
                        min_oos_overlap_adjusted_sharpe=min_oos_overlap_adjusted_sharpe,
                        max_drawdown_floor=max_drawdown_floor,
                        market_state_missing=guard_mode != "none"
                        and (market_state_frame is None or market_state_frame.empty),
                    ),
                )
                row["blockers"] = ";".join(blockers)
                row["hard_blocked"] = bool(blockers)
                row["walk_forward_candidate"] = bool(not blockers and float(cost_bps) > 0.0)
                extreme_trades.extend(
                    _extreme_trade_rows(
                        full.trades,
                        case_id=str(row["case_id"]),
                        guard_mode=guard_mode,
                        cost_bps=float(cost_bps),
                        portfolio_value=float(portfolio_value),
                        threshold=extreme_trade_abs_return,
                    )
                )
                leaderboard.append(_sanitize(row))
    walk_forward_candidates = [row for row in leaderboard if row["walk_forward_candidate"]]
    next_direction = _next_direction(leaderboard, walk_forward_candidates)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "factor_name": factor_name,
        "lead_factor_name": DEFAULT_LEAD_FACTOR_NAME,
        "thresholds": {
            "factor_name": factor_name,
            "stress_guard_mode": list(guard_modes),
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
            "min_oos_overlap_adjusted_sharpe": float(min_oos_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
            "extreme_trade_abs_return": float(extreme_trade_abs_return),
            "train_end_date": train_end_date,
            "test_start_date": test_start_date,
        },
        "summary": _summary(prepared_factors, leaderboard),
        "market_state_coverage": _market_state_coverage(market_state_frame),
        "portfolio_preflight_policy": {
            "walk_forward_allowed_candidates": len(walk_forward_candidates),
            "allowed_case_ids": [row["case_id"] for row in walk_forward_candidates],
            "scope": "single frozen strict-clean residual cost/capital/stress-guard preflight; no alpha parameter search",
            "next_direction": next_direction,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "preflight_is_not_walk_forward",
                "final_holdout_not_read",
                "market_state_guard_not_yet_walk_forward_validated",
                "capacity_and_extreme_trade_gates_required_before_promotion",
            ],
            "reason": (
                "Round136 can only decide whether the strict-clean residual deserves walk-forward "
                "validation. It cannot promote a factor."
            ),
        },
        "leaderboard": leaderboard,
        "extreme_trade_diagnostic": _extreme_trade_diagnostic(extreme_trades),
        "extreme_trades": extreme_trades,
        "next_direction": next_direction,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_markdown(result)
    return result


def apply_stress_guard_to_factor_frame(
    factor_frame: pd.DataFrame,
    market_state_frame: pd.DataFrame | None,
    *,
    guard_mode: str,
) -> pd.DataFrame:
    if guard_mode == "none":
        return factor_frame.copy().reset_index(drop=True)
    if guard_mode != "block_stress_rebalance_dates":
        raise ValueError("guard_mode must be 'none' or 'block_stress_rebalance_dates'")
    if factor_frame.empty or market_state_frame is None or market_state_frame.empty:
        return factor_frame.copy().reset_index(drop=True)
    state = market_state_frame.copy()
    state["date"] = pd.to_datetime(state["date"]).dt.date
    stress_dates = set(state[state["trend_state"].astype(str) == "stress"]["date"])
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame[~frame["date"].isin(stress_dates)].reset_index(drop=True)


def write_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight.md").write_text(
        render_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_leaderboard.csv",
        result.get("leaderboard", []),
        LEADERBOARD_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_extreme_trades.csv",
        result.get("extreme_trades", []),
        EXTREME_TRADE_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    policy = result.get("portfolio_preflight_policy", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Strict-Clean Stress-Guard Preflight",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Lead: `{result.get('lead_factor_name', DEFAULT_LEAD_FACTOR_NAME)}`",
        f"- Factor: `{thresholds.get('factor_name', STRICT_RESIDUAL_FACTOR_NAME)}`",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Guard modes: {', '.join(thresholds.get('stress_guard_mode', []))}",
        f"- Signal rows after rebalance filter: {summary.get('signal_rows', 0)}",
        f"- Walk-forward allowed candidates: {policy.get('walk_forward_allowed_candidates', 0)}",
        f"- Extreme trades: {result.get('extreme_trade_diagnostic', {}).get('extreme_trade_count', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_HIBERNATE)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Fixed Parameters",
        "",
        f"- TopN: {thresholds.get('top_n')}",
        f"- Holding period: {thresholds.get('holding_period')}",
        f"- Rebalance interval: {thresholds.get('rebalance_interval')}",
        f"- Execution lag: {thresholds.get('execution_lag')}",
        f"- Cost bps values: {thresholds.get('cost_bps_values')}",
        f"- Portfolio values: {thresholds.get('portfolio_values')}",
        f"- Train end: {thresholds.get('train_end_date')}",
        f"- Test start: {thresholds.get('test_start_date')}",
        f"- Max drawdown floor: {_fmt_pct(thresholds.get('max_drawdown_floor'))}",
        "",
        "## Leaderboard",
        "",
        "| Case | Guard | Cost | Capital | Full Total | Full Sharpe | Full Overlap | Test Total | Test Overlap | MaxDD | CapTrades | Candidate | Blockers |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "| {case} | {guard} | {cost:.1f} | {capital:.0f} | {total:.2%} | {sharpe:.3f} | {overlap:.3f} | {test_total:.2%} | {test_overlap:.3f} | {dd:.2%} | {cap} | {cand} | {blockers} |".format(
                case=row.get("case_id", ""),
                guard=row.get("guard_mode", ""),
                cost=_number(row.get("cost_bps")),
                capital=_number(row.get("portfolio_value")),
                total=_number(row.get("total_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                test_total=_number(row.get("test_total_return")),
                test_overlap=_number(row.get("test_overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                cap=int(_number(row.get("capacity_limited_trades"))),
                cand="yes" if row.get("walk_forward_candidate") else "no",
                blockers=row.get("blockers", "") or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Drawdown near 30% is treated as tolerable only when return quality, costs, capacity, extreme-trade, and OOS gates survive.",
            "- Passing this preflight only routes the factor to walk-forward validation; it is not paper-ready or live/manual usable.",
        ]
    )
    return "\n".join(lines) + "\n"


def _run_backtest(
    factors: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    top_n: int,
    cost_bps: float,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    min_signal_amount: float,
    max_participation_rate: float,
    market_impact_bps: float,
    max_calendar_holding_days: int | None,
    portfolio_value: float,
    periods_per_year: float,
):
    return run_factor_backtest(
        factors,
        bars,
        top_n=top_n,
        cost_bps=float(cost_bps),
        portfolio_scope="market",
        execution_lag=execution_lag,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        target_gross_exposure=1.0,
        periods_per_year=periods_per_year,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_signal_amount=min_signal_amount,
        max_calendar_holding_days=max_calendar_holding_days,
        portfolio_value=float(portfolio_value),
    )


def _window_frames(
    factors: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    start = pd.to_datetime(start_date).date() if start_date else None
    end = pd.to_datetime(end_date).date() if end_date else None
    factor_frame = factors.copy()
    bar_frame = bars.copy()
    factor_frame["date"] = pd.to_datetime(factor_frame["date"]).dt.date
    bar_frame["date"] = pd.to_datetime(bar_frame["date"]).dt.date
    if start is not None:
        factor_frame = factor_frame[factor_frame["date"] >= start]
        bar_frame = bar_frame[bar_frame["date"] >= start]
    if end is not None:
        factor_frame = factor_frame[factor_frame["date"] <= end]
        bar_frame = bar_frame[bar_frame["date"] <= end]
    return factor_frame.reset_index(drop=True), bar_frame.reset_index(drop=True)


def _split_metrics(
    train_metrics: dict[str, Any],
    test_metrics: dict[str, Any],
    *,
    train_trades: int,
    test_trades: int,
) -> dict[str, Any]:
    return {
        "train_trades": int(train_trades),
        "test_trades": int(test_trades),
        "train_total_return": _metric(train_metrics, "total_return"),
        "train_annualized_return": _metric(train_metrics, "annualized_return"),
        "train_sharpe": _metric(train_metrics, "sharpe"),
        "train_overlap_autocorr_adjusted_sharpe": _metric(train_metrics, "overlap_autocorr_adjusted_sharpe"),
        "train_max_drawdown": _metric(train_metrics, "max_drawdown"),
        "train_win_rate": _metric(train_metrics, "win_rate"),
        "test_total_return": _metric(test_metrics, "total_return"),
        "test_annualized_return": _metric(test_metrics, "annualized_return"),
        "test_sharpe": _metric(test_metrics, "sharpe"),
        "test_overlap_autocorr_adjusted_sharpe": _metric(test_metrics, "overlap_autocorr_adjusted_sharpe"),
        "test_max_drawdown": _metric(test_metrics, "max_drawdown"),
        "test_win_rate": _metric(test_metrics, "win_rate"),
        "test_capacity_limited_trades": int(_metric(test_metrics, "capacity_limited_trades")),
    }


def _oos_blockers(
    row: dict[str, Any],
    *,
    min_oos_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
    market_state_missing: bool,
) -> list[str]:
    blockers = []
    if market_state_missing:
        blockers.append("market_state_missing_for_stress_guard")
    if int(_number(row.get("test_trades"))) <= 0:
        blockers.append("oos_no_trades")
    if _number(row.get("test_total_return")) <= 0.0:
        blockers.append("oos_non_positive_total_return_after_cost")
    if _number(row.get("test_annualized_return")) <= 0.0:
        blockers.append("oos_non_positive_annualized_return_after_cost")
    if _number(row.get("test_overlap_autocorr_adjusted_sharpe")) < min_oos_overlap_adjusted_sharpe:
        blockers.append("oos_overlap_adjusted_sharpe_below_min")
    if _number(row.get("test_capacity_limited_trades")) > 0:
        blockers.append("oos_capacity_limited_trades_present")
    if _number(row.get("test_max_drawdown")) < max_drawdown_floor:
        blockers.append("oos_max_drawdown_below_user_floor")
    return blockers


def _merge_blockers(existing: Any, extra: list[str]) -> list[str]:
    values: list[str] = []
    if isinstance(existing, str):
        values.extend(item for item in existing.split(";") if item)
    elif isinstance(existing, list):
        values.extend(str(item) for item in existing if item)
    values.extend(extra)
    return _dedupe(values)


def _blocked_stress_date_count(prepared_factors: pd.DataFrame, guarded_factors: pd.DataFrame, guard_mode: str) -> int:
    if guard_mode == "none" or prepared_factors.empty:
        return 0
    before = set(pd.to_datetime(prepared_factors["date"]).dt.date)
    after = set(pd.to_datetime(guarded_factors["date"]).dt.date) if not guarded_factors.empty else set()
    return len(before - after)


def _summary(factors: pd.DataFrame, leaderboard: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "factor_names": sorted(factors["factor_name"].dropna().astype(str).unique().tolist()) if not factors.empty else [],
        "signal_rows": int(len(factors)),
        "signal_dates": int(factors["date"].nunique()) if not factors.empty else 0,
        "guard_mode_count": int(len({row.get("guard_mode") for row in leaderboard})),
        "case_count": int(len(leaderboard)),
        "hard_blocked_cases": int(sum(1 for row in leaderboard if row.get("hard_blocked"))),
        "walk_forward_allowed_candidates": int(sum(1 for row in leaderboard if row.get("walk_forward_candidate"))),
        "best_total_return": _best_metric(leaderboard, "total_return"),
        "best_overlap_adjusted_sharpe": _best_metric(leaderboard, "overlap_autocorr_adjusted_sharpe"),
        "best_test_overlap_adjusted_sharpe": _best_metric(leaderboard, "test_overlap_autocorr_adjusted_sharpe"),
        "min_max_drawdown": _min_metric(leaderboard, "max_drawdown"),
        "max_capacity_limited_trades": int(max((_number(row.get("capacity_limited_trades")) for row in leaderboard), default=0)),
    }


def _market_state_coverage(market_state_frame: pd.DataFrame | None) -> dict[str, Any]:
    if market_state_frame is None or market_state_frame.empty:
        return {"rows": 0, "stress_dates": 0, "non_stress_dates": 0, "coverage_present": False}
    state = market_state_frame.copy()
    state["trend_state"] = state["trend_state"].fillna("unknown").astype(str)
    return {
        "rows": int(len(state)),
        "stress_dates": int((state["trend_state"] == "stress").sum()),
        "non_stress_dates": int((state["trend_state"] != "stress").sum()),
        "coverage_present": True,
    }


def _next_direction(leaderboard: list[dict[str, Any]], walk_forward_candidates: list[dict[str, Any]]) -> str:
    if walk_forward_candidates:
        return NEXT_WALK_FORWARD
    if any(_blocker_set(row) == {"extreme_trade_return_present"} for row in leaderboard):
        return NEXT_EXTREME_TRADE_AUDIT
    return NEXT_HIBERNATE


def _blocker_set(row: dict[str, Any]) -> set[str]:
    blockers = row.get("blockers", "")
    if isinstance(blockers, str):
        return {item for item in blockers.split(";") if item}
    if isinstance(blockers, list):
        return {str(item) for item in blockers if item}
    return set()


def _extreme_trade_rows(
    trades: pd.DataFrame,
    *,
    case_id: str,
    guard_mode: str,
    cost_bps: float,
    portfolio_value: float,
    threshold: float,
) -> list[dict[str, Any]]:
    if trades.empty or "gross_return" not in trades.columns:
        return []
    frame = trades.copy()
    frame["gross_return"] = pd.to_numeric(frame["gross_return"], errors="coerce")
    frame = frame[frame["gross_return"].abs() > threshold].copy()
    if frame.empty:
        return []
    frame = frame.reindex(frame["gross_return"].abs().sort_values(ascending=False).index)
    rows = []
    for trade in frame.itertuples(index=False):
        rows.append(
            _sanitize(
                {
                    "case_id": case_id,
                    "guard_mode": guard_mode,
                    "cost_bps": float(cost_bps),
                    "portfolio_value": float(portfolio_value),
                    "signal_date": _date_str(getattr(trade, "signal_date", None)),
                    "entry_date": _date_str(getattr(trade, "entry_date", None)),
                    "exit_date": _date_str(getattr(trade, "exit_date", None)),
                    "asset_id": getattr(trade, "asset_id", ""),
                    "market": getattr(trade, "market", "CN"),
                    "gross_return": _number(getattr(trade, "gross_return", 0.0)),
                    "net_return": _number(getattr(trade, "net_return", 0.0)),
                    "weighted_return": _number(getattr(trade, "weighted_return", 0.0)),
                    "target_notional": _number(getattr(trade, "target_notional", 0.0)),
                    "entry_amount": _number(getattr(trade, "entry_amount", 0.0)),
                    "participation_rate": _number(getattr(trade, "participation_rate", 0.0)),
                }
            )
        )
    return rows


def _extreme_trade_diagnostic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "extreme_trade_count": 0,
            "unique_assets": 0,
            "unique_exit_dates": 0,
            "max_abs_gross_return": 0.0,
            "top_assets": [],
        }
    assets = [str(row.get("asset_id", "")) for row in rows]
    exit_dates = [str(row.get("exit_date", "")) for row in rows]
    gross = [_number(row.get("gross_return")) for row in rows]
    counts = {}
    for asset in assets:
        counts[asset] = counts.get(asset, 0) + 1
    top_assets = [
        {"asset_id": asset, "extreme_trade_count": count}
        for asset, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "extreme_trade_count": int(len(rows)),
        "unique_assets": int(len(set(assets))),
        "unique_exit_dates": int(len(set(exit_dates))),
        "max_abs_gross_return": float(max(abs(value) for value in gross)),
        "top_assets": top_assets,
    }


def _date_str(value: Any) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(timestamp) else timestamp.date().isoformat()


def _validate_inputs(
    *,
    top_n: int,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    portfolio_values: Sequence[float],
    cost_bps_values: Sequence[float],
    guard_modes: Sequence[str],
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
    if not guard_modes:
        raise ValueError("guard_modes must not be empty")
    if any(float(value) <= 0.0 for value in portfolio_values):
        raise ValueError("portfolio_values must be positive")
    if any(float(value) < 0.0 for value in cost_bps_values):
        raise ValueError("cost_bps_values must be non-negative")
    allowed = set(DEFAULT_GUARD_MODES)
    bad_modes = [mode for mode in guard_modes if mode not in allowed]
    if bad_modes:
        raise ValueError(f"Unsupported guard modes: {', '.join(bad_modes)}")


def _metric(metrics: dict[str, Any], key: str) -> float:
    return _number(metrics.get(key, 0.0))


def _best_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


def _min_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(min((_number(row.get(key)) for row in rows), default=0.0))


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _fmt_pct(value: Any) -> str:
    return f"{_number(value):.2%}"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
