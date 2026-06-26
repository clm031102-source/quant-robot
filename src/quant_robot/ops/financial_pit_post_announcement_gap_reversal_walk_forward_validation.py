from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    FORMULA_COLUMNS,
    compute_financial_pit_post_announcement_drift_factor_frame,
    _split_candidates,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    SAFETY,
    _dedupe,
    _filter_date_window,
    _load_bars,
    _load_json,
)
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_walk_forward_preflight import (
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_HOLDING_PERIODS,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_REBALANCE_INTERVALS,
    DEFAULT_TOP_N_VALUES,
    NEXT_ROTATE_DIRECTION,
)
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize


STAGE = "financial_pit_post_announcement_gap_reversal_walk_forward_cost_capacity_regime_validation"
NEXT_PROMOTION_REVIEW_DIRECTION = "round226_financial_pit_gap_reversal_statistical_reality_and_final_holdout_readiness"
NEXT_REPAIR_OR_ROTATE_DIRECTION = "round226_rotate_or_repair_gap_reversal_after_walk_forward_failure"
LEADERBOARD_COLUMNS = [
    "case_id",
    "factor_name",
    "top_n",
    "holding_period",
    "rebalance_interval",
    "execution_lag",
    "cost_bps",
    "portfolio_value",
    "validation_status",
    "accepted_folds",
    "folds",
    "positive_test_folds",
    "positive_test_fold_rate",
    "mean_test_total_return",
    "mean_test_annualized_return",
    "mean_test_overlap_autocorr_adjusted_sharpe",
    "worst_test_max_drawdown",
    "mean_test_win_rate",
    "test_capacity_limited_trades",
    "test_regime_state_count",
    "rejection_reasons",
    "rank",
]
FOLD_COLUMNS = [
    "case_id",
    "fold",
    "factor_name",
    "top_n",
    "holding_period",
    "rebalance_interval",
    "cost_bps",
    "portfolio_value",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "fold_status",
    "fold_rejection_reasons",
    "train_trades",
    "test_trades",
    "train_total_return",
    "test_total_return",
    "train_annualized_return",
    "test_annualized_return",
    "train_overlap_autocorr_adjusted_sharpe",
    "test_overlap_autocorr_adjusted_sharpe",
    "train_max_drawdown",
    "test_max_drawdown",
    "train_win_rate",
    "test_win_rate",
    "train_capacity_limited_trades",
    "test_capacity_limited_trades",
    "test_regime_states",
    "test_regime_state_count",
]
REGIME_COLUMNS = ["fold", "window", "state", "dates", "min_date", "max_date"]


def build_financial_pit_post_announcement_gap_reversal_walk_forward_validation(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    preflight_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    top_n_values: Sequence[int] | None = None,
    holding_periods: Sequence[int] | None = None,
    rebalance_intervals: Sequence[int] | None = None,
    cost_bps_values: Sequence[float] | None = None,
    portfolio_values: Sequence[float] | None = None,
    market_impact_bps: float | None = None,
    max_participation_rate: float | None = None,
    min_signal_amount: float | None = 10_000_000.0,
    min_test_overlap_adjusted_sharpe: float = 0.30,
    max_test_drawdown_limit: float = 0.45,
    min_accepted_folds: int = 2,
    min_positive_test_fold_rate: float = 0.50,
    min_test_trades: int = 5,
    min_regime_states: int = 2,
) -> dict[str, Any]:
    preflight = _load_json(preflight_json)
    frozen_names = set(_frozen_factor_names(preflight))
    financial = _filter_date_window(
        _load_fina_indicator_inputs(Path(financial_root)),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="signal_date",
    )
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial else []
    bars = _filter_date_window(
        _load_bars([Path(root) for root in bars_roots], assets),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="date",
    )
    preregistration = _load_json(preregistration_json)
    gate_packet = _load_json(candidate_plan_gate_json)
    active_candidates, _ = _split_candidates(preregistration, gate_packet)
    active_candidates = [
        candidate
        for candidate in active_candidates
        if candidate.get("factor_name") in FORMULA_COLUMNS and str(candidate.get("factor_name", "")) in frozen_names
    ]
    factor_frame = compute_financial_pit_post_announcement_drift_factor_frame(financial, active_candidates, bars)
    result = run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames(
        factor_frame=factor_frame,
        bars=bars,
        preflight=preflight,
        top_n_values=top_n_values,
        holding_periods=holding_periods,
        rebalance_intervals=rebalance_intervals,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_signal_amount=min_signal_amount,
        min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
        max_test_drawdown_limit=max_test_drawdown_limit,
        min_accepted_folds=min_accepted_folds,
        min_positive_test_fold_rate=min_positive_test_fold_rate,
        min_test_trades=min_test_trades,
        min_regime_states=min_regime_states,
    )
    result.update(
        {
            "financial_root": str(Path(financial_root)),
            "bars_roots": [str(Path(root)) for root in bars_roots],
            "preregistration_json": str(Path(preregistration_json)),
            "preflight_json": str(Path(preflight_json)),
            "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
            "data_window": {
                "factor_rows": int(len(factor_frame)),
                "bar_rows": int(len(bars)),
                "min_factor_date": _date_min(factor_frame, "date"),
                "max_factor_date": _date_max(factor_frame, "date"),
            },
            "holdout_policy": {
                "final_holdout_included": bool(include_final_holdout),
                "analysis_start_date": str(analysis_start_date),
                "analysis_end_date": str(analysis_end_date),
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_walk_forward_and_reality_check_clearance",
            },
        }
    )
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_walk_forward_validation_markdown(result)
    return result


def run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames(
    *,
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    preflight: dict[str, Any],
    top_n_values: Sequence[int] | None = None,
    holding_periods: Sequence[int] | None = None,
    rebalance_intervals: Sequence[int] | None = None,
    cost_bps_values: Sequence[float] | None = None,
    portfolio_values: Sequence[float] | None = None,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    market_impact_bps: float | None = None,
    max_participation_rate: float | None = None,
    min_signal_amount: float | None = 10_000_000.0,
    min_test_overlap_adjusted_sharpe: float = 0.30,
    max_test_drawdown_limit: float = 0.45,
    min_accepted_folds: int = 2,
    min_positive_test_fold_rate: float = 0.50,
    min_test_trades: int = 5,
    min_regime_states: int = 2,
) -> dict[str, Any]:
    _validate_preflight(preflight)
    factors = _prepare_factors(factor_frame)
    bars = _prepare_bars(bars)
    portfolio_policy = _dict(preflight.get("portfolio_grid_policy"))
    top_values = tuple(int(value) for value in (top_n_values or portfolio_policy.get("top_n_values") or DEFAULT_TOP_N_VALUES))
    hold_values = tuple(int(value) for value in (holding_periods or portfolio_policy.get("holding_periods") or DEFAULT_HOLDING_PERIODS))
    rebalance_values = tuple(int(value) for value in (rebalance_intervals or portfolio_policy.get("rebalance_intervals") or DEFAULT_REBALANCE_INTERVALS))
    cost_values = tuple(float(value) for value in (cost_bps_values or portfolio_policy.get("cost_bps_values") or DEFAULT_COST_BPS_VALUES))
    capital_values = tuple(float(value) for value in (portfolio_values or portfolio_policy.get("portfolio_values") or DEFAULT_PORTFOLIO_VALUES))
    impact_bps = float(market_impact_bps if market_impact_bps is not None else portfolio_policy.get("market_impact_bps", 10.0))
    participation = float(
        max_participation_rate
        if max_participation_rate is not None
        else portfolio_policy.get("max_participation_rate", 0.01)
    )
    frozen_names = _frozen_factor_names(preflight)
    fold_plan = _fold_plan(preflight)
    regime = _market_regime_frame(bars)
    fold_rows: list[dict[str, Any]] = []
    for factor_name in frozen_names:
        for top_n in top_values:
            for holding_period in hold_values:
                for rebalance_interval in rebalance_values:
                    for cost_bps in cost_values:
                        for portfolio_value in capital_values:
                            fold_rows.extend(
                                _case_fold_rows(
                                    factors,
                                    bars,
                                    regime,
                                    fold_plan,
                                    factor_name=factor_name,
                                    top_n=top_n,
                                    holding_period=holding_period,
                                    rebalance_interval=rebalance_interval,
                                    execution_lag=execution_lag,
                                    cost_bps=cost_bps,
                                    market_impact_bps=impact_bps,
                                    max_participation_rate=participation,
                                    min_signal_amount=min_signal_amount,
                                    portfolio_value=portfolio_value,
                                    min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
                                    max_test_drawdown_limit=max_test_drawdown_limit,
                                    min_test_trades=min_test_trades,
                                    min_regime_states=min_regime_states,
                                )
                            )
    regime_coverage = _regime_coverage_rows(regime, fold_plan)
    leaderboard = _rank_rows(
        _aggregate_fold_rows(
            fold_rows,
            min_accepted_folds=min_accepted_folds,
            min_positive_test_fold_rate=min_positive_test_fold_rate,
            min_regime_states=min_regime_states,
        )
    )
    accepted = [row for row in leaderboard if row["validation_status"] == "accepted"]
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "thresholds": {
            "top_n_values": list(top_values),
            "holding_periods": list(hold_values),
            "rebalance_intervals": list(rebalance_values),
            "execution_lag": int(execution_lag),
            "cost_bps_values": list(cost_values),
            "portfolio_values": list(capital_values),
            "market_impact_bps": impact_bps,
            "max_participation_rate": participation,
            "min_signal_amount": float(min_signal_amount or 0.0),
            "min_test_overlap_adjusted_sharpe": float(min_test_overlap_adjusted_sharpe),
            "max_test_drawdown_limit": float(max_test_drawdown_limit),
            "min_accepted_folds": int(min_accepted_folds),
            "min_positive_test_fold_rate": float(min_positive_test_fold_rate),
            "min_test_trades": int(min_test_trades),
            "min_regime_states": int(min_regime_states),
        },
        "summary": {
            "cases": len(leaderboard),
            "accepted": len(accepted),
            "rejected": len(leaderboard) - len(accepted),
            "fold_rows": len(fold_rows),
            "frozen_factor_count": len(frozen_names),
            "next_direction": NEXT_PROMOTION_REVIEW_DIRECTION if accepted else NEXT_REPAIR_OR_ROTATE_DIRECTION,
        },
        "leaderboard": leaderboard,
        "folds": fold_rows,
        "regime_coverage": regime_coverage,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "walk_forward_validation_is_not_final_holdout",
                "statistical_reality_check_not_run",
                "final_holdout_not_read",
            ],
        },
        "next_direction": NEXT_PROMOTION_REVIEW_DIRECTION if accepted else NEXT_REPAIR_OR_ROTATE_DIRECTION,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_walk_forward_validation_markdown(result)
    return result


def write_financial_pit_post_announcement_gap_reversal_walk_forward_validation(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in result.items() if key != "markdown"}
    (output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_validation.json").write_text(
        json.dumps(_sanitize(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_validation.md").write_text(
        render_financial_pit_post_announcement_gap_reversal_walk_forward_validation_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "walk_forward_leaderboard.csv", result.get("leaderboard", []) or [], LEADERBOARD_COLUMNS)
    _write_csv(output_path / "walk_forward_folds.csv", result.get("folds", []) or [], FOLD_COLUMNS)
    _write_csv(output_path / "walk_forward_regime_coverage.csv", result.get("regime_coverage", []) or [], REGIME_COLUMNS)


def render_financial_pit_post_announcement_gap_reversal_walk_forward_validation_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    lines = [
        "# Financial PIT Gap Reversal Walk-Forward Validation",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Accepted: {summary.get('accepted', 0)}",
        f"- Rejected: {summary.get('rejected', 0)}",
        f"- Fold rows: {summary.get('fold_rows', 0)}",
        f"- Next direction: `{result.get('next_direction', NEXT_REPAIR_OR_ROTATE_DIRECTION)}`",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Leaderboard",
        "",
        "| Rank | Factor | TopN | Cost | Capital | Status | Folds | Test Total | Test Ann | Test Overlap | Worst DD | Win | CapLimited | Reasons |",
        "|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in (result.get("leaderboard", []) or [])[:20]:
        lines.append(
            "| {rank} | {factor} | {top} | {cost:.1f} | {cap:.0f} | {status} | {accepted}/{folds} | {total:.2%} | {ann:.2%} | {overlap:.3f} | {dd:.2%} | {win:.1%} | {caplim} | {reasons} |".format(
                rank=int(_number(row.get("rank"))),
                factor=row.get("factor_name", ""),
                top=int(_number(row.get("top_n"))),
                cost=_number(row.get("cost_bps")),
                cap=_number(row.get("portfolio_value")),
                status=row.get("validation_status", ""),
                accepted=int(_number(row.get("accepted_folds"))),
                folds=int(_number(row.get("folds"))),
                total=_number(row.get("mean_test_total_return")),
                ann=_number(row.get("mean_test_annualized_return")),
                overlap=_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("worst_test_max_drawdown")),
                win=_number(row.get("mean_test_win_rate")),
                caplim=int(_number(row.get("test_capacity_limited_trades"))),
                reasons=",".join(str(item) for item in row.get("rejection_reasons", []) or []) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Accepted rows are walk-forward validation candidates only, not promotable or paper-ready factors.",
            "- Any accepted row still requires statistical reality checks and final-holdout readiness before promotion review.",
        ]
    )
    return "\n".join(lines) + "\n"


def _case_fold_rows(
    factors: pd.DataFrame,
    bars: pd.DataFrame,
    regime: pd.DataFrame,
    fold_plan: list[dict[str, Any]],
    *,
    factor_name: str,
    top_n: int,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float,
    min_signal_amount: float | None,
    portfolio_value: float,
    min_test_overlap_adjusted_sharpe: float,
    max_test_drawdown_limit: float,
    min_test_trades: int,
    min_regime_states: int,
) -> list[dict[str, Any]]:
    rows = []
    case_id = _case_id(factor_name, top_n, holding_period, rebalance_interval, execution_lag, cost_bps, portfolio_value)
    for fold in fold_plan:
        train_factors = _slice_dates(factors[factors["factor_name"] == factor_name], fold["train_start"], fold["train_end"])
        test_factors = _slice_dates(factors[factors["factor_name"] == factor_name], fold["test_start"], fold["test_end"])
        train_bars = _slice_dates(bars, fold["train_start"], fold["train_end"])
        test_bars = _slice_dates(bars, fold["test_start"], fold["test_end"])
        train = _run_backtest_case(
            train_factors,
            train_bars,
            top_n=top_n,
            cost_bps=cost_bps,
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            execution_lag=execution_lag,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            min_signal_amount=min_signal_amount,
            portfolio_value=portfolio_value,
        )
        test = _run_backtest_case(
            test_factors,
            test_bars,
            top_n=top_n,
            cost_bps=cost_bps,
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            execution_lag=execution_lag,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            min_signal_amount=min_signal_amount,
            portfolio_value=portfolio_value,
        )
        states = _states_for_window(regime, fold["test_start"], fold["test_end"])
        reasons = _fold_reasons(
            train,
            test,
            test_regime_state_count=len(states),
            min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
            max_test_drawdown_limit=max_test_drawdown_limit,
            min_test_trades=min_test_trades,
            min_regime_states=min_regime_states,
        )
        rows.append(
            _sanitize(
                {
                    "case_id": case_id,
                    "fold": str(fold.get("fold")),
                    "factor_name": factor_name,
                    "top_n": int(top_n),
                    "holding_period": int(holding_period),
                    "rebalance_interval": int(rebalance_interval),
                    "cost_bps": float(cost_bps),
                    "portfolio_value": float(portfolio_value),
                    "train_start": str(fold.get("train_start")),
                    "train_end": str(fold.get("train_end")),
                    "test_start": str(fold.get("test_start")),
                    "test_end": str(fold.get("test_end")),
                    "fold_status": "accepted" if not reasons else "rejected",
                    "fold_rejection_reasons": reasons,
                    "train_trades": int(train.get("trades", 0)),
                    "test_trades": int(test.get("trades", 0)),
                    "train_total_return": _number(train.get("total_return")),
                    "test_total_return": _number(test.get("total_return")),
                    "train_annualized_return": _number(train.get("annualized_return")),
                    "test_annualized_return": _number(test.get("annualized_return")),
                    "train_overlap_autocorr_adjusted_sharpe": _number(train.get("overlap_autocorr_adjusted_sharpe")),
                    "test_overlap_autocorr_adjusted_sharpe": _number(test.get("overlap_autocorr_adjusted_sharpe")),
                    "train_max_drawdown": _number(train.get("max_drawdown")),
                    "test_max_drawdown": _number(test.get("max_drawdown")),
                    "train_win_rate": _number(train.get("win_rate")),
                    "test_win_rate": _number(test.get("win_rate")),
                    "train_capacity_limited_trades": int(_number(train.get("capacity_limited_trades"))),
                    "test_capacity_limited_trades": int(_number(test.get("capacity_limited_trades"))),
                    "test_regime_states": ",".join(states),
                    "test_regime_state_count": len(states),
                }
            )
        )
    return rows


def _run_backtest_case(factors: pd.DataFrame, bars: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
    if factors.empty or bars.empty:
        return {"status": "missing", "trades": 0}
    try:
        result = run_factor_backtest(
            factors,
            bars,
            top_n=int(kwargs["top_n"]),
            cost_bps=float(kwargs["cost_bps"]),
            portfolio_scope="market",
            execution_lag=int(kwargs["execution_lag"]),
            holding_period=int(kwargs["holding_period"]),
            rebalance_interval=int(kwargs["rebalance_interval"]),
            target_gross_exposure=1.0,
            periods_per_year=252.0,
            market_impact_bps=float(kwargs["market_impact_bps"]),
            max_participation_rate=float(kwargs["max_participation_rate"]),
            min_signal_amount=kwargs["min_signal_amount"],
            max_calendar_holding_days=int(kwargs["holding_period"] * 6),
            portfolio_value=float(kwargs["portfolio_value"]),
        )
    except Exception as exc:  # pragma: no cover - defensive reporting for long real runs
        return {"status": "failed", "error": str(exc), "trades": 0}
    metrics = dict(result.metrics)
    metrics["status"] = "completed"
    metrics["trades"] = int(len(result.trades))
    return metrics


def _fold_reasons(
    train: dict[str, Any],
    test: dict[str, Any],
    *,
    test_regime_state_count: int,
    min_test_overlap_adjusted_sharpe: float,
    max_test_drawdown_limit: float,
    min_test_trades: int,
    min_regime_states: int,
) -> list[str]:
    reasons: list[str] = []
    if train.get("status") != "completed":
        reasons.append("train_not_completed")
    if test.get("status") != "completed":
        reasons.append("test_not_completed")
    if int(_number(test.get("trades"))) < int(min_test_trades):
        reasons.append("test_trades_below_min")
    if _number(test.get("total_return")) <= 0.0:
        reasons.append("test_total_return_non_positive")
    if _number(test.get("annualized_return")) <= 0.0:
        reasons.append("test_annualized_return_non_positive")
    if _number(test.get("overlap_autocorr_adjusted_sharpe")) < float(min_test_overlap_adjusted_sharpe):
        reasons.append("test_overlap_adjusted_sharpe_below_min")
    if _number(test.get("max_drawdown")) < -abs(float(max_test_drawdown_limit)):
        reasons.append("test_drawdown_above_limit")
    if int(_number(test.get("capacity_limited_trades"))) > 0:
        reasons.append("test_capacity_limited_trades_present")
    if bool(test.get("extreme_trade_return_flag")):
        reasons.append("test_extreme_trade_return")
    if int(test_regime_state_count) < int(min_regime_states):
        reasons.append("test_regime_state_count_below_min")
    return _dedupe(reasons)


def _aggregate_fold_rows(
    rows: list[dict[str, Any]],
    *,
    min_accepted_folds: int,
    min_positive_test_fold_rate: float,
    min_regime_states: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("case_id")), []).append(row)
    aggregates = []
    for case_id, items in grouped.items():
        source = items[0]
        accepted_folds = sum(1 for row in items if row.get("fold_status") == "accepted")
        positive_test_folds = sum(1 for row in items if _number(row.get("test_total_return")) > 0.0)
        positive_rate = positive_test_folds / len(items) if items else 0.0
        state_count = len(_dedupe(",".join(str(row.get("test_regime_states", "")) for row in items).split(",")))
        reasons = _dedupe(
            [
                reason
                for row in items
                if row.get("fold_status") != "accepted"
                for reason in row.get("fold_rejection_reasons", []) or []
            ]
        )
        if accepted_folds < int(min_accepted_folds):
            reasons.append("accepted_folds_below_min")
        if positive_rate < float(min_positive_test_fold_rate):
            reasons.append("positive_test_fold_rate_below_min")
        if state_count < int(min_regime_states):
            reasons.append("aggregate_regime_state_count_below_min")
        aggregates.append(
            _sanitize(
                {
                    "case_id": case_id,
                    "factor_name": source.get("factor_name"),
                    "top_n": int(_number(source.get("top_n"))),
                    "holding_period": int(_number(source.get("holding_period"))),
                    "rebalance_interval": int(_number(source.get("rebalance_interval"))),
                    "execution_lag": DEFAULT_EXECUTION_LAG,
                    "cost_bps": _number(source.get("cost_bps")),
                    "portfolio_value": _number(source.get("portfolio_value")),
                    "validation_status": "accepted" if not reasons else "rejected",
                    "accepted_folds": accepted_folds,
                    "folds": len(items),
                    "positive_test_folds": positive_test_folds,
                    "positive_test_fold_rate": positive_rate,
                    "mean_test_total_return": _mean(items, "test_total_return"),
                    "mean_test_annualized_return": _mean(items, "test_annualized_return"),
                    "mean_test_overlap_autocorr_adjusted_sharpe": _mean(items, "test_overlap_autocorr_adjusted_sharpe"),
                    "worst_test_max_drawdown": min((_number(row.get("test_max_drawdown")) for row in items), default=0.0),
                    "mean_test_win_rate": _mean(items, "test_win_rate"),
                    "test_capacity_limited_trades": sum(int(_number(row.get("test_capacity_limited_trades"))) for row in items),
                    "test_regime_state_count": state_count,
                    "rejection_reasons": _dedupe(reasons),
                }
            )
        )
    return aggregates


def _rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            str(row.get("validation_status")) != "accepted",
            -_number(row.get("accepted_folds")),
            -_number(row.get("mean_test_total_return")),
            -_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
            _number(row.get("cost_bps")),
            _number(row.get("portfolio_value")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _market_regime_frame(bars: pd.DataFrame, *, lookback: int = 60) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["date", "regime_state"])
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    market = frame.groupby("date", as_index=False)["adj_close"].mean().sort_values("date")
    returns = market["adj_close"].pct_change(max(1, min(lookback, max(len(market) // 4, 1))))
    market["regime_state"] = ["risk_on" if value >= 0 else "risk_off" for value in returns.fillna(0.0)]
    return market[["date", "regime_state"]]


def _states_for_window(regime: pd.DataFrame, start: Any, end: Any) -> list[str]:
    if regime.empty:
        return []
    dates = pd.to_datetime(regime["date"], errors="coerce")
    start_date = pd.Timestamp(start)
    end_date = pd.Timestamp(end)
    states = sorted(str(state) for state in regime[(dates >= start_date) & (dates <= end_date)]["regime_state"].dropna().unique())
    return states


def _regime_coverage_rows(regime: pd.DataFrame, fold_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for fold in fold_plan:
        for window in ("train", "test"):
            start = fold[f"{window}_start"]
            end = fold[f"{window}_end"]
            sliced = _slice_dates(regime.rename(columns={"regime_state": "state"}), start, end)
            for state, group in sliced.groupby("state", sort=True):
                rows.append(
                    {
                        "fold": str(fold.get("fold")),
                        "window": window,
                        "state": str(state),
                        "dates": int(len(group)),
                        "min_date": _date_min(group, "date"),
                        "max_date": _date_max(group, "date"),
                    }
                )
    return rows


def _validate_preflight(preflight: dict[str, Any]) -> None:
    if preflight.get("status") != "cleared":
        raise ValueError("Round225 validation requires a cleared Round224 preflight")
    policy = _dict(preflight.get("preflight_policy"))
    if policy.get("walk_forward_preflight_cleared") is not True:
        raise ValueError("Round225 validation requires walk_forward_preflight_cleared")
    if not _frozen_factor_names(preflight):
        raise ValueError("Round225 validation requires frozen factor names")
    if not _fold_plan(preflight):
        raise ValueError("Round225 validation requires a walk-forward plan")
    if _dict(preflight.get("promotion_policy")).get("promotion_allowed") is not False:
        raise ValueError("Round225 validation requires promotion to remain blocked")


def _frozen_factor_names(preflight: dict[str, Any]) -> list[str]:
    return _dedupe(str(name) for name in _dict(preflight.get("preflight_policy")).get("frozen_factor_names", []) if str(name))


def _fold_plan(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in preflight.get("walk_forward_plan", []) or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "fold": str(row.get("fold")),
                "train_start": str(row.get("train_start")),
                "train_end": str(row.get("train_end")),
                "test_start": str(row.get("test_start")),
                "test_end": str(row.get("test_end")),
            }
        )
    return rows


def _prepare_factors(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    if frame.empty:
        return pd.DataFrame(columns=required)
    _require_columns(frame, required, "factor_frame")
    output = frame[required].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output[(output["market"] == "CN") & output["date"].notna()].dropna(subset=["factor_value"]).reset_index(drop=True)


def _prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    if frame.empty:
        return pd.DataFrame(columns=required + ["amount"])
    _require_columns(frame, required, "bars")
    columns = required + (["amount"] if "amount" in frame.columns else [])
    output = frame[columns].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["adj_close"] = pd.to_numeric(output["adj_close"], errors="coerce")
    if "amount" in output:
        output["amount"] = pd.to_numeric(output["amount"], errors="coerce")
    return (
        output[(output["market"] == "CN") & output["date"].notna() & (output["adj_close"] > 0)]
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _slice_dates(frame: pd.DataFrame, start: Any, end: Any) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame.iloc[0:0].copy()
    dates = pd.to_datetime(frame["date"], errors="coerce")
    return frame[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))].reset_index(drop=True)


def _case_id(
    factor_name: str,
    top_n: int,
    holding_period: int,
    rebalance_interval: int,
    execution_lag: int,
    cost_bps: float,
    portfolio_value: float,
) -> str:
    return (
        f"CN_{factor_name}_top{top_n}_hold{holding_period}_reb{rebalance_interval}_"
        f"lag{execution_lag}_cost{_case_number(cost_bps)}_cap{_case_number(portfolio_value)}"
    )


def _case_number(value: float) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number).replace(".", "p")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, bool):
        return str(value)
    return value


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else str(value.date())


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else str(value.date())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return sum(_number(row.get(key)) for row in rows) / len(rows) if rows else 0.0


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if pd.notna(number) else default
