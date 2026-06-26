from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    load_price_basis_audit_bars,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_GUARD_MODES,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_PRICE_BASIS,
    DEFAULT_REBALANCE_INTERVAL,
    DEFAULT_TEST_START_DATE,
    DEFAULT_TOP_N,
    DEFAULT_TRAIN_END_DATE,
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
)


STAGE = "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun"
DEFAULT_ROUND139_AUDIT_REPORT = Path(
    "data/reports/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_round139_20260622/"
    "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.json"
)
NEXT_CLEAN_WALK_FORWARD = "round141_daily_basic_free_float_supply_quality_clean_walk_forward_after_event_adjustment"
NEXT_HIBERNATE_OR_ROTATE = (
    "round141_daily_basic_free_float_supply_quality_hibernation_or_family_rotation_after_event_adjustment"
)
NEXT_EVENT_AUDIT = "round141_daily_basic_free_float_supply_quality_second_pass_extreme_event_audit"
EVENT_PATH_COLUMNS = [
    "asset_id",
    "signal_date",
    "entry_date",
    "exit_date",
    "tradeability_class",
    "reported_gross_return_max",
    "blockers",
]
SUPPORTED_EXCLUSION_SCOPES = ("all", "no_obvious", "blocked")


def build_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
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
    result = summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
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
        train_end_date=train_end_date,
        test_start_date=test_start_date,
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
        "source_round": "round139_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit",
        "source_report": str(round139_audit_report or DEFAULT_ROUND139_AUDIT_REPORT),
        "scope": "same frozen Round138/Round139 candidate after excluding audited extreme event paths",
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_markdown(result)
    return result


def summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
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
    train_end_date: str = DEFAULT_TRAIN_END_DATE,
    test_start_date: str = DEFAULT_TEST_START_DATE,
    periods_per_year: float | None = None,
) -> dict[str, Any]:
    event_paths = event_paths_from_round139_audit(round139_audit, exclusion_scope=exclusion_scope)
    filtered_factors, exclusion_summary = apply_event_path_exclusion_to_factor_frame(factor_frame, event_paths)
    repaired_bars, repair_summary = (
        (bars.copy(), dict(precomputed_repair_summary))
        if precomputed_repair_summary is not None
        else repair_bars_to_single_price_basis(bars, price_basis=price_basis)
    )
    base = summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
        filtered_factors,
        repaired_bars,
        market_state_frame=market_state_frame,
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
        train_end_date=train_end_date,
        test_start_date=test_start_date,
        periods_per_year=periods_per_year,
    )
    base_summary = dict(base.get("summary", {}))
    base_policy = dict(base.get("portfolio_preflight_policy", {}))
    next_direction = _next_direction(base_summary, base_policy)
    result = dict(base)
    result.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "event_exclusion_scope": exclusion_scope,
            "event_paths": event_paths,
            "event_exclusion_summary": exclusion_summary,
            "summary": base_summary
            | {
                "event_exclusion_scope": exclusion_scope,
                "event_excluded_factor_rows": exclusion_summary["excluded_factor_rows"],
                "event_remaining_factor_rows": exclusion_summary["remaining_factor_rows"],
            },
            "portfolio_preflight_policy": {
                **base_policy,
                "scope": "event-adjusted clean rerun; no alpha parameter search",
                "next_direction": next_direction,
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "allowed_candidate_count": 0,
                "blockers": [
                    "event_adjusted_clean_rerun_is_preflight_only",
                    "final_holdout_not_read",
                    "cost_capacity_regime_walk_forward_required_before_promotion",
                ],
                "reason": (
                    "The rerun can decide whether the candidate still deserves walk-forward validation after "
                    "event-path removal. It cannot directly promote the factor."
                ),
            },
            "next_direction": next_direction,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    if int(base_summary.get("repaired_true_close_extreme_trade_count", 0)) > 0:
        result["promotion_policy"]["blockers"].append("true_close_extreme_trades_remain_after_event_adjustment")
    result["markdown"] = render_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_markdown(result)
    return result


def event_paths_from_round139_audit(
    round139_audit: dict[str, Any],
    *,
    exclusion_scope: str = "all",
) -> list[dict[str, Any]]:
    if exclusion_scope not in SUPPORTED_EXCLUSION_SCOPES:
        raise ValueError(f"Unsupported exclusion_scope: {exclusion_scope}")
    rows = list(round139_audit.get("trade_path_audit", []))
    selected = []
    for row in rows:
        blockers = _blocker_list(row.get("blockers", []))
        is_no_obvious = not blockers and str(row.get("tradeability_class", "")) == "no_obvious_tradeability_blocker"
        if exclusion_scope == "no_obvious" and not is_no_obvious:
            continue
        if exclusion_scope == "blocked" and is_no_obvious:
            continue
        selected.append(
            _sanitize(
                {
                    "asset_id": str(row.get("asset_id", "")),
                    "signal_date": _date_str(row.get("signal_date")),
                    "entry_date": _date_str(row.get("entry_date")),
                    "exit_date": _date_str(row.get("exit_date")),
                    "tradeability_class": str(row.get("tradeability_class", "")),
                    "reported_gross_return_max": _number(row.get("reported_gross_return_max")),
                    "blockers": blockers,
                }
            )
        )
    return selected


def apply_event_path_exclusion_to_factor_frame(
    factor_frame: pd.DataFrame,
    event_paths: Iterable[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = factor_frame.copy()
    if frame.empty:
        return frame, {
            "requested_event_path_count": len(list(event_paths)),
            "matched_event_path_count": 0,
            "excluded_factor_rows": 0,
            "remaining_factor_rows": 0,
            "event_dates": 0,
            "event_assets": 0,
        }
    paths = list(event_paths)
    frame["_event_signal_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    frame["_event_asset_id"] = frame["asset_id"].astype(str)
    key_set = {
        (str(row.get("asset_id", "")), _date_str(row.get("signal_date")))
        for row in paths
        if str(row.get("asset_id", "")) and _date_str(row.get("signal_date"))
    }
    mask = frame.apply(lambda row: (row["_event_asset_id"], row["_event_signal_date"]) in key_set, axis=1)
    matched_keys = set(zip(frame.loc[mask, "_event_asset_id"], frame.loc[mask, "_event_signal_date"], strict=False))
    filtered = frame.loc[~mask].drop(columns=["_event_signal_date", "_event_asset_id"]).reset_index(drop=True)
    return filtered, {
        "requested_event_path_count": int(len(paths)),
        "matched_event_path_count": int(len(matched_keys)),
        "excluded_factor_rows": int(mask.sum()),
        "remaining_factor_rows": int(len(filtered)),
        "event_dates": int(len({key[1] for key in key_set})),
        "event_assets": int(len({key[0] for key in key_set})),
    }


def write_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.md").write_text(
        render_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_leaderboard.csv",
        result.get("leaderboard", []),
        LEADERBOARD_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_extreme_trades.csv",
        result.get("extreme_trades", []),
        EXTREME_TRADE_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_event_adjusted_event_paths.csv",
        result.get("event_paths", []),
        EVENT_PATH_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    event_summary = result.get("event_exclusion_summary", {})
    policy = result.get("portfolio_preflight_policy", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Event-Adjusted Clean Rerun",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Exclusion scope: `{result.get('event_exclusion_scope', 'all')}`",
        f"- Requested event paths: {event_summary.get('requested_event_path_count', 0)}",
        f"- Matched event paths: {event_summary.get('matched_event_path_count', 0)}",
        f"- Excluded factor rows: {event_summary.get('excluded_factor_rows', 0)}",
        f"- Remaining factor rows: {event_summary.get('remaining_factor_rows', 0)}",
        f"- Walk-forward allowed candidates: {policy.get('walk_forward_allowed_candidates', 0)}",
        f"- True-close extreme trades after adjustment: {summary.get('repaired_true_close_extreme_trade_count', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_HIBERNATE_OR_ROTATE)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
        "| Case | Guard | Cost | Capital | Total | Annual | Sharpe | Overlap Sharpe | MaxDD | Win Rate | Extreme Trades | Candidate | Blockers |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "| {case} | {guard} | {cost:.1f} | {capital:.0f} | {total:.2%} | {ann:.2%} | {sharpe:.3f} | {overlap:.3f} | {dd:.2%} | {wr:.2%} | {extreme} | {cand} | {blockers} |".format(
                case=row.get("case_id", ""),
                guard=row.get("guard_mode", ""),
                cost=_number(row.get("cost_bps")),
                capital=_number(row.get("portfolio_value")),
                total=_number(row.get("total_return")),
                ann=_number(row.get("annualized_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                wr=_number(row.get("win_rate")),
                extreme=int(_number(row.get("extreme_trade_return_count"))),
                cand="yes" if row.get("walk_forward_candidate") else "no",
                blockers=row.get("blockers", "") or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This rerun removes audited event paths before portfolio construction.",
            "- It keeps the frozen factor, cost, capacity, holding, rebalance, and split settings.",
            "- It is still a preflight; promotion requires clean walk-forward validation and an untouched final holdout.",
        ]
    )
    return "\n".join(lines) + "\n"


def _next_direction(summary: dict[str, Any], policy: dict[str, Any]) -> str:
    if int(summary.get("repaired_true_close_extreme_trade_count", 0)) > 0:
        return NEXT_EVENT_AUDIT
    if int(policy.get("walk_forward_allowed_candidates", 0)) > 0:
        return NEXT_CLEAN_WALK_FORWARD
    return NEXT_HIBERNATE_OR_ROTATE


def _load_round139_audit(round139_audit_report: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if round139_audit_report is None:
        round139_audit_report = DEFAULT_ROUND139_AUDIT_REPORT
    if isinstance(round139_audit_report, (str, Path)):
        path = Path(round139_audit_report)
        if not path.exists():
            raise FileNotFoundError(f"Round139 audit report not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    return dict(round139_audit_report)


def _blocker_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        return [item for item in value.split(";") if item]
    return []


def _date_str(value: Any) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(timestamp) else timestamp.date().isoformat()


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
