from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (
    DEFAULT_ROUND139_AUDIT_REPORT,
    EVENT_PATH_COLUMNS,
    SUPPORTED_EXCLUSION_SCOPES,
    apply_event_path_exclusion_to_factor_frame,
    event_paths_from_round139_audit,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    load_price_basis_audit_bars,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_PRICE_BASIS,
    DEFAULT_REBALANCE_INTERVAL,
    DEFAULT_TOP_N,
    repair_bars_to_single_price_basis,
    summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    STRICT_RESIDUAL_FACTOR_NAME,
    _strict_clean_lead_frame,
    build_market_state_frame,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight import (
    EXTREME_TRADE_COLUMNS,
    LEADERBOARD_COLUMNS,
    _write_csv,
)
from quant_robot.ops.daily_basic_non_price_public_carry_lead_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    DEFAULT_RESIDUAL_EXPOSURES,
    _merge_lead_exposures,
    _normalise_exposure_frame,
    _normalise_lead,
    build_daily_basic_lead_exposure_frame,
    residualize_daily_basic_lead,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    SAFETY,
    default_daily_basic_non_price_public_carry_specs,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    attach_daily_basic_capacity_fields,
    compute_daily_basic_non_price_public_carry_factors,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (
    DEFAULT_MAX_PARTICIPATION,
)
from quant_robot.ops.turnover_repair_champion_portfolio_conversion import (
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
    _filter_rebalance_dates,
    _prepare_champion_factors,
)


STAGE = "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward"
DEFAULT_ROLLING_TRAIN_DAYS = 12
DEFAULT_ROLLING_TEST_DAYS = 6
DEFAULT_ROLLING_STEP_DAYS = 6
DEFAULT_MIN_ACCEPTED_FOLDS = 2
DEFAULT_MIN_TEST_TRADES = 100
DEFAULT_MIN_TEST_TOTAL_RETURN = 0.0
DEFAULT_WALK_FORWARD_GUARD_MODES = ("block_stress_rebalance_dates",)
NEXT_FINAL_HOLDOUT_OR_PAPER_GATE = (
    "round142_daily_basic_free_float_supply_quality_final_holdout_or_paper_gate_after_clean_walk_forward"
)
NEXT_HIBERNATE_OR_ROTATE = "round142_daily_basic_free_float_supply_quality_hibernation_or_family_rotation"

AGGREGATE_LEADERBOARD_COLUMNS = [
    "case_id",
    "factor_name",
    "guard_mode",
    "top_n",
    "holding_period",
    "rebalance_interval",
    "execution_lag",
    "cost_bps",
    "market_impact_bps",
    "portfolio_value",
    "folds",
    "accepted_folds",
    "rejected_folds",
    "fold_acceptance_rate",
    "compounded_test_total_return",
    "mean_test_total_return",
    "mean_test_annualized_return",
    "mean_test_sharpe",
    "mean_test_overlap_autocorr_adjusted_sharpe",
    "worst_test_max_drawdown",
    "mean_test_win_rate",
    "total_test_trades",
    "max_test_capacity_limited_trades",
    "max_extreme_trade_return_count",
    "max_abs_trade_gross_return",
    "stress_guard_blocked_folds",
    "stress_guard_allowed_folds",
    "validation_status",
    "validation_blockers",
]
FOLD_COLUMNS = [
    "fold",
    "case_id",
    "guard_mode",
    "cost_bps",
    "portfolio_value",
    "train_start_date",
    "train_end_date",
    "test_start_date",
    "test_end_date",
    "fold_validation_status",
    "fold_validation_blockers",
    "test_total_return",
    "test_annualized_return",
    "test_sharpe",
    "test_overlap_autocorr_adjusted_sharpe",
    "test_max_drawdown",
    "test_win_rate",
    "test_trades",
    "test_capacity_limited_trades",
    "extreme_trade_return_count",
    "max_abs_trade_gross_return",
    "stress_guarded_dates_blocked",
    "guarded_signal_dates",
]


def build_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    round139_audit_report: dict[str, Any] | str | Path | None = DEFAULT_ROUND139_AUDIT_REPORT,
    exclusion_scope: str = "all",
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    price_basis: str = DEFAULT_PRICE_BASIS,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    factor_name: str = STRICT_RESIDUAL_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    guard_modes: Sequence[str] = DEFAULT_WALK_FORWARD_GUARD_MODES,
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
    rolling_train_days: int = DEFAULT_ROLLING_TRAIN_DAYS,
    rolling_test_days: int = DEFAULT_ROLLING_TEST_DAYS,
    rolling_step_days: int = DEFAULT_ROLLING_STEP_DAYS,
    min_test_trades: int = DEFAULT_MIN_TEST_TRADES,
    min_accepted_folds: int = DEFAULT_MIN_ACCEPTED_FOLDS,
    min_test_total_return: float = DEFAULT_MIN_TEST_TOTAL_RETURN,
) -> dict[str, Any]:
    bars = load_price_basis_audit_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    repaired_bars, repair_summary = repair_bars_to_single_price_basis(bars, price_basis=price_basis)
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
    lead_frame = attach_daily_basic_capacity_fields(lead_frame, repaired_bars)
    exposure_frame = build_daily_basic_lead_exposure_frame(daily_basic, repaired_bars)
    lead = _normalise_lead(lead_frame, lead_factor_name=lead_factor_name)
    exposures = _normalise_exposure_frame(exposure_frame)
    strict_lead = _strict_clean_lead_frame(
        _merge_lead_exposures(lead, exposures),
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_signal_date_amount=min_signal_date_amount,
    )
    strict_residual_frame = residualize_daily_basic_lead(
        strict_lead,
        exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
        residual_factor_name=factor_name,
        min_cross_section=min_cross_section,
    )
    result = summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
        strict_residual_frame,
        repaired_bars,
        round139_audit=_load_round139_audit(round139_audit_report),
        market_state_frame=build_market_state_frame(repaired_bars),
        exclusion_scope=exclusion_scope,
        factor_name=factor_name,
        price_basis=price_basis,
        precomputed_repair_summary=repair_summary,
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
        rolling_train_days=rolling_train_days,
        rolling_test_days=rolling_test_days,
        rolling_step_days=rolling_step_days,
        min_test_trades=min_test_trades,
        min_accepted_folds=min_accepted_folds,
        min_test_total_return=min_test_total_return,
    )
    result["lead_factor_name"] = lead_factor_name
    result["data_window"] = dict(result.get("data_window", {})) | {
        "raw_bar_rows_loaded": int(len(bars)),
        "repaired_bar_rows": int(len(repaired_bars)),
        "lead_rows": int(len(lead_frame)),
        "strict_clean_lead_rows": int(len(strict_lead)),
        "strict_clean_residual_rows_before_event_exclusion": int(len(strict_residual_frame)),
        "strict_clean_residual_rows_after_event_exclusion": int(
            result.get("event_exclusion_summary", {}).get("remaining_factor_rows", 0)
        ),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round140_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun",
        "source_report": (
            "docs/research/"
            "cn_stock_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_round140_2026-06-22.md"
        ),
        "scope": "frozen Round140 event-adjusted clean candidates under rolling walk-forward validation",
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_markdown(result)
    return result


def summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    round139_audit: dict[str, Any],
    market_state_frame: pd.DataFrame | None = None,
    exclusion_scope: str = "all",
    factor_name: str = STRICT_RESIDUAL_FACTOR_NAME,
    price_basis: str = DEFAULT_PRICE_BASIS,
    precomputed_repair_summary: dict[str, Any] | None = None,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    guard_modes: Sequence[str] = DEFAULT_WALK_FORWARD_GUARD_MODES,
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
    rolling_train_days: int = DEFAULT_ROLLING_TRAIN_DAYS,
    rolling_test_days: int = DEFAULT_ROLLING_TEST_DAYS,
    rolling_step_days: int = DEFAULT_ROLLING_STEP_DAYS,
    min_test_trades: int = DEFAULT_MIN_TEST_TRADES,
    min_accepted_folds: int = DEFAULT_MIN_ACCEPTED_FOLDS,
    min_test_total_return: float = DEFAULT_MIN_TEST_TOTAL_RETURN,
    periods_per_year: float | None = None,
) -> dict[str, Any]:
    _validate_rolling_inputs(rolling_train_days, rolling_test_days, rolling_step_days, min_accepted_folds)
    event_paths = event_paths_from_round139_audit(round139_audit, exclusion_scope=exclusion_scope)
    filtered_factors, exclusion_summary = apply_event_path_exclusion_to_factor_frame(factor_frame, event_paths)
    repaired_bars, repair_summary = (
        (bars.copy(), dict(precomputed_repair_summary))
        if precomputed_repair_summary is not None
        else repair_bars_to_single_price_basis(bars, price_basis=price_basis)
    )
    fixed_rebalance_factors = _filter_rebalance_dates(
        _prepare_champion_factors(filtered_factors, factor_name),
        rebalance_interval,
    )
    folds = _rolling_folds(fixed_rebalance_factors, rolling_train_days, rolling_test_days, rolling_step_days)
    fold_rows: list[dict[str, Any]] = []
    extreme_trades: list[dict[str, Any]] = []
    engine_periods_per_year = periods_per_year or (252.0 / float(max(rebalance_interval, 1)))
    for fold in folds:
        fold_factors = _date_window(
            fixed_rebalance_factors,
            start_date=fold["train_start_date"],
            end_date=fold["test_end_date"],
        )
        fold_bars = _date_window(
            repaired_bars,
            start_date=fold["train_start_date"],
            end_date=_extended_bar_end_date(
                repaired_bars,
                fold["test_end_date"],
                extra_trading_days=max(holding_period + execution_lag + 5, 1),
            ),
        )
        fold_state = (
            _date_window(market_state_frame, start_date=fold["train_start_date"], end_date=fold["test_end_date"])
            if market_state_frame is not None
            else None
        )
        fold_result = summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
            fold_factors,
            fold_bars,
            market_state_frame=fold_state,
            factor_name=factor_name,
            price_basis=price_basis,
            precomputed_repair_summary=repair_summary,
            cost_bps_values=cost_bps_values,
            portfolio_values=portfolio_values,
            guard_modes=guard_modes,
            top_n=top_n,
            holding_period=holding_period,
            rebalance_interval=1,
            execution_lag=execution_lag,
            min_signal_amount=min_signal_amount,
            max_participation_rate=max_participation_rate,
            market_impact_bps=market_impact_bps,
            max_calendar_holding_days=max_calendar_holding_days,
            min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
            min_oos_overlap_adjusted_sharpe=min_oos_overlap_adjusted_sharpe,
            max_drawdown_floor=max_drawdown_floor,
            train_end_date=fold["train_end_date"],
            test_start_date=fold["test_start_date"],
            periods_per_year=engine_periods_per_year,
        )
        extreme_trades.extend(
            _with_actual_rebalance_interval(dict(row, fold=fold["fold"]), rebalance_interval)
            for row in fold_result.get("extreme_trades", [])
        )
        for row in fold_result.get("leaderboard", []):
            row = _with_actual_rebalance_interval(dict(row), rebalance_interval)
            status, blockers = _fold_validation_status(
                row,
                min_test_trades=min_test_trades,
                min_oos_overlap_adjusted_sharpe=min_oos_overlap_adjusted_sharpe,
                max_drawdown_floor=max_drawdown_floor,
                min_test_total_return=min_test_total_return,
            )
            fold_rows.append(
                _sanitize(
                    {
                        **row,
                        "fold": int(fold["fold"]),
                        "train_start_date": fold["train_start_date"],
                        "train_end_date": fold["train_end_date"],
                        "test_start_date": fold["test_start_date"],
                        "test_end_date": fold["test_end_date"],
                        "fold_validation_status": status,
                        "fold_validation_blockers": ";".join(blockers),
                    }
                )
            )
    leaderboard = _aggregate_fold_rows(
        fold_rows,
        min_accepted_folds=min_accepted_folds,
        guard_modes=guard_modes,
    )
    accepted = [row for row in leaderboard if row["validation_status"] == "accepted"]
    next_direction = NEXT_FINAL_HOLDOUT_OR_PAPER_GATE if accepted else NEXT_HIBERNATE_OR_ROTATE
    summary = _summary(fixed_rebalance_factors, folds, fold_rows, leaderboard)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "factor_name": factor_name,
        "event_exclusion_scope": exclusion_scope,
        "event_paths": event_paths,
        "event_exclusion_summary": exclusion_summary,
        "price_basis_repair_summary": repair_summary,
        "thresholds": {
            "factor_name": factor_name,
            "guard_modes": list(guard_modes),
            "cost_bps_values": [float(value) for value in cost_bps_values],
            "portfolio_values": [float(value) for value in portfolio_values],
            "top_n": int(top_n),
            "holding_period": int(holding_period),
            "rebalance_interval": int(rebalance_interval),
            "execution_lag": int(execution_lag),
            "min_signal_amount": float(min_signal_amount),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "max_calendar_holding_days": int(max_calendar_holding_days or 0),
            "min_overlap_adjusted_sharpe": float(min_overlap_adjusted_sharpe),
            "min_oos_overlap_adjusted_sharpe": float(min_oos_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
            "rolling_train_days": int(rolling_train_days),
            "rolling_test_days": int(rolling_test_days),
            "rolling_step_days": int(rolling_step_days),
            "min_test_trades": int(min_test_trades),
            "min_accepted_folds": int(min_accepted_folds),
            "min_test_total_return": float(min_test_total_return),
            "periods_per_year": periods_per_year,
        },
        "summary": summary
        | {
            "pre_rebalance_signal_rows": int(len(filtered_factors)),
            "pre_rebalance_signal_dates": int(filtered_factors["date"].nunique()) if not filtered_factors.empty else 0,
        },
        "data_window": _data_window(repaired_bars, fixed_rebalance_factors)
        | {
            "pre_rebalance_factor_rows": int(len(filtered_factors)),
            "pre_rebalance_signal_dates": int(filtered_factors["date"].nunique()) if not filtered_factors.empty else 0,
        },
        "walk_forward_policy": {
            "parameter_search_frozen": True,
            "source_is_round140_preflight_survivors": True,
            "folds_are_chronological": True,
            "fixed_global_rebalance_calendar": True,
            "backtest_engine_rebalance_interval": 1,
            "reported_rebalance_interval": int(rebalance_interval),
            "event_paths_removed_before_portfolio_construction": True,
            "final_holdout_not_read": True,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": (
                ["final_holdout_not_read", "paper_gate_required_after_clean_walk_forward"]
                if accepted
                else [
                    "no_clean_walk_forward_accepted_candidate",
                    "final_holdout_not_read",
                    "family_rotation_or_hibernation_required",
                ]
            ),
            "reason": (
                "Clean walk-forward can only route a frozen candidate toward a final paper gate. "
                "It does not authorize live, manual, or promoted use."
            ),
        },
        "leaderboard": leaderboard,
        "folds": fold_rows,
        "extreme_trades": extreme_trades,
        "next_direction": next_direction,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_markdown(result)
    return result


def write_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.md").write_text(
        render_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_leaderboard.csv",
        result.get("leaderboard", []),
        AGGREGATE_LEADERBOARD_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_folds.csv",
        result.get("folds", []),
        FOLD_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_extreme_trades.csv",
        result.get("extreme_trades", []),
        ["fold", *EXTREME_TRADE_COLUMNS],
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_event_paths.csv",
        result.get("event_paths", []),
        EVENT_PATH_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    thresholds = result.get("thresholds", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Event-Adjusted Clean Walk-Forward",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Factor: `{result.get('factor_name', STRICT_RESIDUAL_FACTOR_NAME)}`",
        f"- Folds: {summary.get('fold_count', 0)}",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Accepted candidates: {summary.get('walk_forward_accepted_candidates', 0)}",
        f"- Event paths removed: {result.get('event_exclusion_summary', {}).get('excluded_factor_rows', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_HIBERNATE_OR_ROTATE)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Frozen Validation Parameters",
        "",
        f"- Guard modes: {thresholds.get('guard_modes', [])}",
        f"- TopN / hold / rebalance / lag: {thresholds.get('top_n')} / {thresholds.get('holding_period')} / {thresholds.get('rebalance_interval')} / {thresholds.get('execution_lag')}",
        f"- Costs: {thresholds.get('cost_bps_values')}",
        f"- Portfolio values: {thresholds.get('portfolio_values')}",
        f"- Rolling train/test/step signal days: {thresholds.get('rolling_train_days')} / {thresholds.get('rolling_test_days')} / {thresholds.get('rolling_step_days')}",
        f"- Min accepted folds: {thresholds.get('min_accepted_folds')}",
        f"- Max drawdown floor: {_fmt_pct(thresholds.get('max_drawdown_floor'))}",
        "",
        "## Aggregate Leaderboard",
        "",
        "| Case | Status | Folds | Accepted | Test Total | Ann | Sharpe | Overlap | Worst DD | Win | Trades | Blockers |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "| {case} | {status} | {folds} | {accepted} | {total:.2%} | {ann:.2%} | {sharpe:.3f} | {overlap:.3f} | {dd:.2%} | {win:.2%} | {trades} | {blockers} |".format(
                case=row.get("case_id", ""),
                status=row.get("validation_status", ""),
                folds=int(_number(row.get("folds"))),
                accepted=int(_number(row.get("accepted_folds"))),
                total=_number(row.get("compounded_test_total_return")),
                ann=_number(row.get("mean_test_annualized_return")),
                sharpe=_number(row.get("mean_test_sharpe")),
                overlap=_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("worst_test_max_drawdown")),
                win=_number(row.get("mean_test_win_rate")),
                trades=int(_number(row.get("total_test_trades"))),
                blockers=row.get("validation_blockers", "") or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a validation pass over frozen Round140 candidates, not a new alpha search.",
            "- A candidate can move forward only if enough chronological folds survive costs, capacity, drawdown, OOS overlap Sharpe, and event-clean checks.",
            "- Even accepted walk-forward candidates remain research-to-paper only until the final holdout and paper gate are read once.",
        ]
    )
    return "\n".join(lines) + "\n"


def _rolling_folds(
    factors: pd.DataFrame,
    train_days: int,
    test_days: int,
    step_days: int,
) -> list[dict[str, Any]]:
    if factors.empty:
        return []
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    dates = sorted(frame["date"].dropna().dt.date.unique())
    limit = len(dates) - train_days - test_days + 1
    if limit <= 0:
        return []
    folds = []
    for fold_number, start in enumerate(range(0, limit, step_days), start=1):
        train_dates = dates[start : start + train_days]
        test_dates = dates[start + train_days : start + train_days + test_days]
        folds.append(
            {
                "fold": int(fold_number),
                "train_start_date": train_dates[0].isoformat(),
                "train_end_date": train_dates[-1].isoformat(),
                "test_start_date": test_dates[0].isoformat(),
                "test_end_date": test_dates[-1].isoformat(),
            }
        )
    return folds


def _fold_validation_status(
    row: dict[str, Any],
    *,
    min_test_trades: int,
    min_oos_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
    min_test_total_return: float,
) -> tuple[str, list[str]]:
    blockers = _blocker_list(row.get("blockers", ""))
    if int(_number(row.get("test_trades"))) < min_test_trades:
        blockers.append("test_trades_below_minimum")
    if _number(row.get("test_total_return")) < min_test_total_return:
        blockers.append("test_total_return_below_minimum")
    if _number(row.get("test_overlap_autocorr_adjusted_sharpe")) < min_oos_overlap_adjusted_sharpe:
        blockers.append("test_overlap_adjusted_sharpe_below_minimum")
    if _number(row.get("test_max_drawdown")) < max_drawdown_floor:
        blockers.append("test_max_drawdown_below_floor")
    if int(_number(row.get("test_capacity_limited_trades"))) > 0:
        blockers.append("test_capacity_limited_trades_present")
    if int(_number(row.get("extreme_trade_return_count"))) > 0:
        blockers.append("extreme_trade_return_present")
    blockers = _dedupe(blockers)
    return ("accepted" if not blockers else "rejected"), blockers


def _aggregate_fold_rows(
    fold_rows: list[dict[str, Any]],
    *,
    min_accepted_folds: int,
    guard_modes: Sequence[str],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in fold_rows:
        grouped.setdefault(str(row.get("case_id", "")), []).append(row)
    leaderboard = []
    for case_id, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: int(_number(row.get("fold"))))
        accepted_folds = sum(1 for row in rows if row.get("fold_validation_status") == "accepted")
        rejected_folds = len(rows) - accepted_folds
        blockers = []
        if accepted_folds < min_accepted_folds:
            blockers.append("accepted_folds_below_minimum")
        guard_mode = str(rows[0].get("guard_mode", ""))
        if guard_mode == "block_stress_rebalance_dates" and "block_stress_rebalance_dates" in guard_modes:
            if sum(1 for row in rows if int(_number(row.get("stress_guarded_dates_blocked"))) > 0) == 0:
                blockers.append("stress_guard_never_blocked_a_fold")
            if sum(1 for row in rows if int(_number(row.get("guarded_signal_dates"))) > 0) == 0:
                blockers.append("stress_guard_no_allowed_signal_dates")
        validation_status = "accepted" if not blockers else "rejected"
        returns = [_number(row.get("test_total_return")) for row in rows]
        compounded = 1.0
        for value in returns:
            compounded *= 1.0 + value
        source = rows[0]
        leaderboard.append(
            _sanitize(
                {
                    "case_id": case_id,
                    "factor_name": source.get("factor_name"),
                    "guard_mode": guard_mode,
                    "top_n": int(_number(source.get("top_n"))),
                    "holding_period": int(_number(source.get("holding_period"))),
                    "rebalance_interval": int(_number(source.get("rebalance_interval"))),
                    "execution_lag": int(_number(source.get("execution_lag"))),
                    "cost_bps": _number(source.get("cost_bps")),
                    "market_impact_bps": _number(source.get("market_impact_bps")),
                    "portfolio_value": _number(source.get("portfolio_value")),
                    "folds": int(len(rows)),
                    "accepted_folds": int(accepted_folds),
                    "rejected_folds": int(rejected_folds),
                    "fold_acceptance_rate": float(accepted_folds / len(rows)) if rows else 0.0,
                    "compounded_test_total_return": float(compounded - 1.0),
                    "mean_test_total_return": _mean(rows, "test_total_return"),
                    "mean_test_annualized_return": _mean(rows, "test_annualized_return"),
                    "mean_test_sharpe": _mean(rows, "test_sharpe"),
                    "mean_test_overlap_autocorr_adjusted_sharpe": _mean(
                        rows,
                        "test_overlap_autocorr_adjusted_sharpe",
                    ),
                    "worst_test_max_drawdown": _min(rows, "test_max_drawdown"),
                    "mean_test_win_rate": _mean(rows, "test_win_rate"),
                    "total_test_trades": int(sum(_number(row.get("test_trades")) for row in rows)),
                    "max_test_capacity_limited_trades": int(_max(rows, "test_capacity_limited_trades")),
                    "max_extreme_trade_return_count": int(_max(rows, "extreme_trade_return_count")),
                    "max_abs_trade_gross_return": _max(rows, "max_abs_trade_gross_return"),
                    "stress_guard_blocked_folds": int(
                        sum(1 for row in rows if int(_number(row.get("stress_guarded_dates_blocked"))) > 0)
                    ),
                    "stress_guard_allowed_folds": int(
                        sum(1 for row in rows if int(_number(row.get("guarded_signal_dates"))) > 0)
                    ),
                    "validation_status": validation_status,
                    "validation_blockers": ";".join(_dedupe(blockers)),
                    "rejected_fold_blockers": ";".join(
                        _dedupe(
                            blocker
                            for row in rows
                            for blocker in _blocker_list(row.get("fold_validation_blockers", ""))
                        )
                    ),
                }
            )
        )
    return sorted(
        leaderboard,
        key=lambda row: (
            0 if row["validation_status"] == "accepted" else 1,
            -_number(row.get("accepted_folds")),
            -_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
            -_number(row.get("compounded_test_total_return")),
        ),
    )


def _with_actual_rebalance_interval(row: dict[str, Any], rebalance_interval: int) -> dict[str, Any]:
    old_interval = int(_number(row.get("rebalance_interval")) or 1)
    row["rebalance_interval"] = int(rebalance_interval)
    if row.get("case_id"):
        row["case_id"] = str(row["case_id"]).replace(
            f"_reb{old_interval}_",
            f"_reb{int(rebalance_interval)}_",
        )
    return row


def _summary(
    factors: pd.DataFrame,
    folds: list[dict[str, Any]],
    fold_rows: list[dict[str, Any]],
    leaderboard: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "factor_names": sorted(factors["factor_name"].dropna().astype(str).unique().tolist()) if not factors.empty else [],
        "signal_rows": int(len(factors)),
        "signal_dates": int(factors["date"].nunique()) if not factors.empty else 0,
        "fold_count": int(len(folds)),
        "fold_row_count": int(len(fold_rows)),
        "case_count": int(len(leaderboard)),
        "walk_forward_accepted_candidates": int(
            sum(1 for row in leaderboard if row.get("validation_status") == "accepted")
        ),
        "best_compounded_test_total_return": _max(leaderboard, "compounded_test_total_return"),
        "best_mean_test_overlap_adjusted_sharpe": _max(
            leaderboard,
            "mean_test_overlap_autocorr_adjusted_sharpe",
        ),
        "worst_test_max_drawdown": _min(leaderboard, "worst_test_max_drawdown"),
        "max_extreme_trade_return_count": int(_max(leaderboard, "max_extreme_trade_return_count")),
        "max_test_capacity_limited_trades": int(_max(leaderboard, "max_test_capacity_limited_trades")),
    }


def _date_window(
    frame: pd.DataFrame | None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    if frame.empty or "date" not in frame.columns:
        return frame.copy()
    output = frame.copy()
    values = pd.to_datetime(output["date"], errors="coerce").dt.date
    if start_date is not None:
        values_start = pd.to_datetime(start_date).date()
        output = output[values >= values_start]
        values = pd.to_datetime(output["date"], errors="coerce").dt.date
    if end_date is not None:
        values_end = pd.to_datetime(end_date).date()
        output = output[values <= values_end]
    return output.reset_index(drop=True)


def _extended_bar_end_date(bars: pd.DataFrame, signal_end_date: str, *, extra_trading_days: int) -> str:
    if bars.empty or "date" not in bars.columns:
        return signal_end_date
    dates = sorted(pd.to_datetime(bars["date"], errors="coerce").dropna().dt.date.unique())
    if not dates:
        return signal_end_date
    signal_end = pd.to_datetime(signal_end_date).date()
    index = max((idx for idx, value in enumerate(dates) if value <= signal_end), default=0)
    return dates[min(index + max(extra_trading_days, 0), len(dates) - 1)].isoformat()


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


def _validate_rolling_inputs(train_days: int, test_days: int, step_days: int, min_accepted_folds: int) -> None:
    if min(train_days, test_days, step_days, min_accepted_folds) < 1:
        raise ValueError("rolling day counts and min_accepted_folds must be positive")


def _load_round139_audit(round139_audit_report: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if isinstance(round139_audit_report, dict):
        return round139_audit_report
    path = Path(round139_audit_report or DEFAULT_ROUND139_AUDIT_REPORT)
    return json.loads(path.read_text(encoding="utf-8"))


def _blocker_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item for item in value.split(";") if item]
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def _dedupe(values: Iterable[Any]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        item = str(value)
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [_number(row.get(key)) for row in rows]
    return float(sum(values) / len(values)) if values else 0.0


def _min(rows: list[dict[str, Any]], key: str) -> float:
    return float(min((_number(row.get(key)) for row in rows), default=0.0))


def _max(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


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


def _fmt_pct(value: Any) -> str:
    return f"{_number(value):.2%}"


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
    if isinstance(value, pd.Timestamp):
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
        return value if math.isfinite(value) else 0.0
    return value
