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
from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    ASSET_PATH_AUDIT_COLUMNS,
    DATE_BASIS_AUDIT_COLUMNS,
    load_price_basis_audit_bars,
    summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    STRICT_RESIDUAL_FACTOR_NAME,
    _strict_clean_lead_frame,
    build_market_state_frame,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight import (
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_GUARD_MODES,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_TEST_START_DATE,
    DEFAULT_TOP_N,
    DEFAULT_TRAIN_END_DATE,
    EXTREME_TRADE_COLUMNS,
    LEADERBOARD_COLUMNS,
    _csv_value,
    _data_window,
    _number,
    _sanitize,
    _write_csv,
    summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight,
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
    DEFAULT_EXECUTION_LAG,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
    DEFAULT_REBALANCE_INTERVAL,
)


STAGE = "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun"
DEFAULT_PRICE_BASIS = "close"
NEXT_CLEAN_WALK_FORWARD = "round139_daily_basic_free_float_supply_quality_clean_walk_forward_validation"
NEXT_TRUE_CLOSE_EXTREME_AUDIT = (
    "round139_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit"
)
NEXT_HIBERNATE = "round139_daily_basic_free_float_supply_quality_hibernation_after_price_basis_repair"


def repair_bars_to_single_price_basis(
    bars: pd.DataFrame,
    *,
    price_basis: str = DEFAULT_PRICE_BASIS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if price_basis != "close":
        raise ValueError("price_basis currently supports only 'close'")
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")

    frame = bars.copy()
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "adjusted" not in frame:
        frame["adjusted"] = frame["adj_close"] != frame["close"]
    if "amount" not in frame:
        frame["amount"] = 0.0
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["close", "adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["adjusted"] = frame["adjusted"].fillna(False).astype(bool)
    frame = frame.dropna(subset=["date", "asset_id", "market", "close", "adj_close"])
    frame = frame[(frame["close"] > 0.0) & (frame["adj_close"] > 0.0)].copy()

    original_adj_close = frame["adj_close"].copy()
    original_adjusted = frame["adjusted"].copy()
    original_ratio = original_adj_close / frame["close"]
    repriced = (original_adj_close - frame["close"]).abs() > 1e-9
    frame["original_adj_close"] = original_adj_close
    frame["original_adjusted"] = original_adjusted
    frame["price_basis_for_backtest"] = price_basis
    frame["adj_close"] = frame["close"]
    frame["adjusted"] = False
    repaired_ratio = frame["adj_close"] / frame["close"]

    summary = {
        "price_basis": price_basis,
        "bar_rows": int(len(frame)),
        "repriced_bar_rows": int(repriced.sum()),
        "adjusted_true_before": int(original_adjusted.sum()),
        "adjusted_true_after": int(frame["adjusted"].sum()),
        "max_abs_original_ratio_minus_one": _series_abs_max(original_ratio - 1.0),
        "max_abs_repaired_ratio_minus_one": _series_abs_max(repaired_ratio - 1.0),
        "mixed_price_basis_disabled": True,
    }
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True), summary


def build_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
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

    result = summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
        strict_residual_frame,
        repaired_bars,
        market_state_frame=build_market_state_frame(repaired_bars),
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
    window = _data_window(repaired_bars, strict_residual_frame)
    result["lead_factor_name"] = lead_factor_name
    result["data_window"] = window | {
        "min_factor_date": window.get("min_signal_date"),
        "max_factor_date": window.get("max_signal_date"),
        "lead_rows": int(len(lead_frame)),
        "strict_clean_lead_rows": int(len(strict_lead)),
        "strict_clean_residual_rows": int(len(strict_residual_frame)),
        "raw_bar_rows_loaded": int(len(bars)),
        "repaired_bar_rows": int(len(repaired_bars)),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["source_context"] = {
        "source_round": "round137_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit",
        "source_report": (
            "docs/research/"
            "cn_stock_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_2026-06-22.md"
        ),
        "scope": "same frozen Round136 parameters after forcing a single backtest price basis",
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_markdown(
        result
    )
    return result


def summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    market_state_frame: pd.DataFrame | None = None,
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
    if precomputed_repair_summary is None:
        repaired_bars, repair_summary = repair_bars_to_single_price_basis(bars, price_basis=price_basis)
    else:
        repaired_bars = bars.copy()
        repair_summary = dict(precomputed_repair_summary)
    base = summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
        factor_frame,
        repaired_bars,
        market_state_frame=market_state_frame,
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
        periods_per_year=periods_per_year,
    )
    repaired_extreme_audit = summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
        extreme_trades=base.get("extreme_trades", []),
        bars=repaired_bars,
    )
    leaderboard = list(base.get("leaderboard", []))
    summary = dict(base.get("summary", {}))
    summary.update(
        {
            "max_abs_trade_gross_return": _max_metric(leaderboard, "max_abs_trade_gross_return"),
            "max_extreme_trade_return_count": int(
                max((_number(row.get("extreme_trade_return_count")) for row in leaderboard), default=0.0)
            ),
            "repaired_phantom_alpha_trade_count": int(
                repaired_extreme_audit.get("summary", {}).get("phantom_alpha_trade_count", 0)
            ),
            "repaired_true_close_extreme_trade_count": int(
                repaired_extreme_audit.get("summary", {}).get("true_close_extreme_trade_count", 0)
            ),
        }
    )
    next_direction = _next_direction(summary, base, repaired_extreme_audit)
    result = dict(base)
    result.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "summary": summary,
            "price_basis_repair_summary": repair_summary,
            "price_basis_repair_policy": {
                "same_frozen_parameters_as_round136": True,
                "price_basis_for_backtest": price_basis,
                "shared_backtest_engine_modified": False,
                "purpose": "remove mixed adjusted/unadjusted price-basis phantom alpha before any promotion decision",
            },
            "repaired_extreme_trade_audit": {
                "summary": repaired_extreme_audit.get("summary", {}),
                "gate": repaired_extreme_audit.get("gate", {}),
                "promotion_policy": repaired_extreme_audit.get("promotion_policy", {}),
                "asset_path_audit": repaired_extreme_audit.get("asset_path_audit", []),
                "date_basis_audit": repaired_extreme_audit.get("date_basis_audit", []),
            },
            "portfolio_preflight_policy": {
                **dict(base.get("portfolio_preflight_policy", {})),
                "scope": "price-basis repaired rerun of the frozen Round136 candidate; no alpha parameter search",
                "next_direction": next_direction,
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "allowed_candidate_count": 0,
                "blockers": [
                    "price_basis_repair_rerun_is_preflight_only",
                    "clean_walk_forward_required_after_repair",
                    "final_holdout_not_read",
                    "paper_ready_requires_oos_cost_capacity_regime_validation",
                ],
                "reason": (
                    "This rerun can show whether the old high-return result was contaminated. "
                    "It cannot promote a factor until a clean walk-forward rerun survives."
                ),
            },
            "next_direction": next_direction,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    result["markdown"] = render_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_markdown(
        result
    )
    return result


def write_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.md").write_text(
        render_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_leaderboard.csv",
        result.get("leaderboard", []),
        LEADERBOARD_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_extreme_trades.csv",
        result.get("extreme_trades", []),
        EXTREME_TRADE_COLUMNS,
    )
    repaired_audit = result.get("repaired_extreme_trade_audit", {})
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_price_basis_repair_asset_path_audit.csv",
        repaired_audit.get("asset_path_audit", []),
        ASSET_PATH_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_supply_quality_price_basis_repair_date_basis_audit.csv",
        repaired_audit.get("date_basis_audit", []),
        DATE_BASIS_AUDIT_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    repair = result.get("price_basis_repair_summary", {})
    policy = result.get("portfolio_preflight_policy", {})
    audit_summary = result.get("repaired_extreme_trade_audit", {}).get("summary", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Price-Basis Repair Preflight Rerun",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Factor: `{result.get('factor_name', STRICT_RESIDUAL_FACTOR_NAME)}`",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Repriced bars: {repair.get('repriced_bar_rows', 0)} / {repair.get('bar_rows', 0)}",
        f"- Repaired phantom-alpha trades: {audit_summary.get('phantom_alpha_trade_count', 0)}",
        f"- Max abs trade gross return after repair: {_fmt_pct(summary.get('max_abs_trade_gross_return'))}",
        f"- Walk-forward allowed candidates: {policy.get('walk_forward_allowed_candidates', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction', NEXT_HIBERNATE)}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Repair Policy",
        "",
        f"- Backtest price basis: `{repair.get('price_basis', DEFAULT_PRICE_BASIS)}`",
        f"- Adjusted true before: {repair.get('adjusted_true_before', 0)}",
        f"- Adjusted true after: {repair.get('adjusted_true_after', 0)}",
        f"- Mixed price basis disabled: {repair.get('mixed_price_basis_disabled', False)}",
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
            "- A large drawdown can be acceptable only after the return path is clean.",
            "- This rerun intentionally keeps the old parameters frozen, so any performance change is attributable to price-basis repair rather than new parameter mining.",
            "- Promotion remains blocked until the repaired signal survives clean walk-forward validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def _next_direction(
    summary: dict[str, Any],
    base_result: dict[str, Any],
    repaired_extreme_audit: dict[str, Any],
) -> str:
    audit_summary = repaired_extreme_audit.get("summary", {})
    if int(audit_summary.get("phantom_alpha_trade_count", 0)) > 0:
        return NEXT_TRUE_CLOSE_EXTREME_AUDIT
    if int(audit_summary.get("true_close_extreme_trade_count", 0)) > 0:
        return NEXT_TRUE_CLOSE_EXTREME_AUDIT
    if int(base_result.get("portfolio_preflight_policy", {}).get("walk_forward_allowed_candidates", 0)) > 0:
        return NEXT_CLEAN_WALK_FORWARD
    if _number(summary.get("max_abs_trade_gross_return")) > 5.0:
        return NEXT_TRUE_CLOSE_EXTREME_AUDIT
    return NEXT_HIBERNATE


def _max_metric(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


def _series_abs_max(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").abs().dropna()
    if values.empty:
        return 0.0
    value = float(values.max())
    return value if math.isfinite(value) else 0.0


def _fmt_pct(value: Any) -> str:
    return f"{_number(value):.2%}"
