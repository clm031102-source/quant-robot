from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.factors.cn_stock_champion import compute_cn_stock_champion_factors
from quant_robot.research.decision import build_benchmark_curve, compare_strategy_to_benchmark
from quant_robot.research.groups import quantile_group_returns
from quant_robot.research.ic import compute_ic
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.long_short import long_short_returns
from quant_robot.research.pipeline import _factor_summary, _tail_factor_summary
from quant_robot.research.schedules import rebalance_phase_dates


CHAMPION_FACTOR = "rankic_neg1_downside_range_blend"
EXPECTED_VALIDATION_WINDOW = {"start": "2025-01-01", "end": "2025-12-31"}
MAX_ALLOWED_TRADE_GROSS_RETURN = 5.0
REQUIRED_CONTROLS = {
    "twenty_twenty_five_oos_only",
    "overlap_aware_return_statistics",
    "daily_vs_every2_every3_controls",
    "cost_capacity_turnover_stress",
    "cumulative_multiple_testing_accounting",
    "no_parameter_tuning_during_oos",
    "final_holdout_only_after_oos_clearance",
}
REQUIRED_OVERLAP_STATISTICS = {
    "naive_sharpe",
    "autocorr_adjusted_sharpe",
    "newey_west_standard_error_mean",
    "newey_west_t_stat_mean",
    "variance_inflation",
    "effective_sample_size",
    "autocorrelations",
    "overlap_risk_flag",
}


def validate_batch12_oos_contract(
    handoff: dict[str, Any],
    preflight: dict[str, Any],
    *,
    final_holdout_touched: bool = False,
) -> dict[str, Any]:
    if preflight.get("status") != "cleared" or not _dict(preflight.get("decision")).get("validation_preflight_cleared"):
        raise ValueError("Batch12 OOS preflight is not cleared")
    if final_holdout_touched:
        raise ValueError("Batch12 OOS validation cannot run after final holdout has been touched")
    if _dict(handoff.get("validation_window")) != EXPECTED_VALIDATION_WINDOW:
        raise ValueError("Batch12 OOS validation window must be exactly 2025-01-01 to 2025-12-31")
    if _dict(preflight.get("validation_window")) != EXPECTED_VALIDATION_WINDOW:
        raise ValueError("Batch12 OOS preflight validation window must be exactly 2025")
    if _dict(handoff.get("final_holdout_window")).get("allowed_next") is not False:
        raise ValueError("Batch12 final holdout must remain locked")
    if preflight.get("final_holdout_allowed") is not False:
        raise ValueError("Batch12 preflight must keep final holdout disallowed")
    missing_controls = sorted(REQUIRED_CONTROLS - set(_list(handoff.get("required_controls"))))
    if missing_controls:
        raise ValueError(f"Batch12 handoff missing required controls: {', '.join(missing_controls)}")
    missing_overlap = sorted(REQUIRED_OVERLAP_STATISTICS - set(_list(handoff.get("required_overlap_statistics"))))
    if missing_overlap:
        raise ValueError(f"Batch12 handoff missing required overlap statistics: {', '.join(missing_overlap)}")
    return {
        "validation_window": EXPECTED_VALIDATION_WINDOW,
        "final_holdout_allowed": False,
        "live_boundary_allowed": False,
    }


def build_batch12_oos_case_specs(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    frozen = []
    for candidate in _list(handoff.get("frozen_candidates")):
        item = _dict(candidate)
        frozen.append(
            {
                "case_id": str(item["case_id"]),
                "role": "frozen_candidate",
                "factor_name": CHAMPION_FACTOR,
                "cost_bps": float(item["cost_bps"]),
                "schedule_interval": int(item["schedule_interval"]),
                "schedule_offset": int(item["schedule_offset"]),
                "holding_period": int(item["holding_period"]),
                "top_n": int(item["top_n"]),
                "previous_month_return_threshold": float(item["previous_month_return_threshold"]),
            }
        )
    if not frozen:
        raise ValueError("Batch12 handoff has no frozen candidates")

    costs = sorted({float(item["cost_bps"]) for item in frozen})
    base = frozen[0]
    diagnostics = []
    for control in _list(handoff.get("diagnostic_controls")):
        interval = int(_dict(control).get("schedule_interval", 0))
        if interval not in {2, 3}:
            continue
        for offset in range(interval):
            for cost in costs:
                diagnostics.append(
                    {
                        "case_id": (
                            f"{CHAMPION_FACTOR}_hold20_top50_every{interval}_offset{offset}_"
                            f"cost{_format_cost(cost)}_prev_month_ret_gt_neg1"
                        ),
                        "role": "diagnostic_control",
                        "factor_name": CHAMPION_FACTOR,
                        "cost_bps": cost,
                        "schedule_interval": interval,
                        "schedule_offset": offset,
                        "holding_period": int(base["holding_period"]),
                        "top_n": int(base["top_n"]),
                        "previous_month_return_threshold": float(base["previous_month_return_threshold"]),
                    }
                )
    return frozen + diagnostics


def run_batch12_oos_validation(
    *,
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    handoff: dict[str, Any],
    preflight: dict[str, Any],
    output_dir: str | Path,
    final_holdout_touched: bool = False,
    feature_window_start: str = "2024-10-01",
) -> dict[str, Any]:
    contract = validate_batch12_oos_contract(
        handoff,
        preflight,
        final_holdout_touched=final_holdout_touched,
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    start = pd.to_datetime(EXPECTED_VALIDATION_WINDOW["start"]).date()
    end = pd.to_datetime(EXPECTED_VALIDATION_WINDOW["end"]).date()
    feature_start = pd.to_datetime(feature_window_start).date()
    bars_frame = _prepare_window_frame(bars, start=feature_start, end=end, label="bars")
    inputs_frame = _prepare_window_frame(daily_basic_inputs, start=feature_start, end=end, label="daily-basic inputs")
    _require_coverage(inputs_frame, start=start, end=end, label="daily-basic inputs")

    factors = compute_cn_stock_champion_factors(
        bars_frame,
        inputs_frame,
        factor_names=(CHAMPION_FACTOR,),
    )
    market_state = build_market_state(bars_frame)
    labels = make_forward_returns(bars_frame, horizons=(20,), execution_lag=1)
    case_specs = build_batch12_oos_case_specs(handoff)
    cumulative_hypothesis_count = int(handoff.get("prior_related_hypotheses", 0) or 0) + len(case_specs)
    cumulative_bonferroni_alpha = 0.05 / max(1, cumulative_hypothesis_count)
    rows = []
    for spec in case_specs:
        spec = {
            **spec,
            "cumulative_hypothesis_count": cumulative_hypothesis_count,
            "cumulative_bonferroni_alpha": cumulative_bonferroni_alpha,
        }
        scheduled = _schedule_case_factors(factors, market_state, spec, start=start, end=end)
        result = _run_case(bars_frame, labels, scheduled, spec, end=end, output_dir=output_path / spec["case_id"])
        row = _row_from_result(spec, result)
        rows.append(row)

    leaderboard = pd.DataFrame(rows).sort_values(
        ["role", "paper_ready", "research_lead", "overlap_autocorr_adjusted_sharpe", "relative_return"],
        ascending=[False, False, False, False, False],
    ).reset_index(drop=True)
    leaderboard.insert(0, "rank", range(1, len(leaderboard) + 1))
    leaderboard.to_csv(output_path / "batch12_oos_leaderboard.csv", index=False)
    (output_path / "batch12_oos_leaderboard.json").write_text(
        json.dumps(_sanitize(leaderboard.to_dict(orient="records")), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "stage": "cn_stock_batch12_oos_validation",
        "status": "completed",
        "validation_window": contract["validation_window"],
        "feature_window_start": feature_start.isoformat(),
        "final_holdout_allowed": False,
        "final_holdout_touched": False,
        "live_boundary_allowed": False,
        "factor_name": CHAMPION_FACTOR,
        "prior_related_hypotheses": int(handoff.get("prior_related_hypotheses", 0) or 0),
        "cumulative_hypothesis_count": cumulative_hypothesis_count,
        "cumulative_bonferroni_alpha": cumulative_bonferroni_alpha,
        "summary": {
            "cases": len(case_specs),
            "frozen_candidates": int((leaderboard["role"] == "frozen_candidate").sum()),
            "diagnostic_controls": int((leaderboard["role"] == "diagnostic_control").sum()),
            "paper_ready": int(leaderboard["paper_ready"].sum()),
            "research_lead": int(leaderboard["research_lead"].sum()),
        },
        "output_dir": str(output_path),
    }
    (output_path / "batch12_oos_manifest.json").write_text(
        json.dumps(_sanitize(manifest), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "report.md").write_text(_render_report(manifest, leaderboard), encoding="utf-8")
    return _sanitize(manifest)


def build_market_state(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars[["date", "asset_id", "adj_close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["asset_return"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change()
    daily = (
        frame.groupby("date", as_index=False)["asset_return"]
        .mean()
        .rename(columns={"asset_return": "market_return"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    daily["market_return"] = pd.to_numeric(daily["market_return"], errors="coerce").fillna(0.0)
    daily["month"] = pd.to_datetime(daily["date"]).dt.to_period("M")
    monthly = (
        daily.groupby("month", as_index=False)["market_return"]
        .apply(lambda values: float((1.0 + values).prod() - 1.0))
        .rename(columns={"market_return": "month_return"})
    )
    monthly["previous_month"] = monthly["month"] + 1
    previous = monthly[["previous_month", "month_return"]].rename(
        columns={"previous_month": "month", "month_return": "previous_month_return"}
    )
    return daily.merge(previous, on="month", how="left").drop(columns=["month"])


def _schedule_case_factors(
    factors: pd.DataFrame,
    market_state: pd.DataFrame,
    spec: dict[str, Any],
    *,
    start: Any,
    end: Any,
) -> pd.DataFrame:
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    signal_window = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()
    allowed = set(
        market_state.loc[
            pd.to_numeric(market_state["previous_month_return"], errors="coerce")
            > float(spec["previous_month_return_threshold"]),
            "date",
        ]
    )
    valid_dates = sorted(set(signal_window.dropna(subset=["factor_value"])["date"]) & allowed)
    scheduled_dates = set(
        rebalance_phase_dates(
            valid_dates,
            interval=int(spec["schedule_interval"]),
            offset=int(spec["schedule_offset"]),
        )
    )
    return signal_window[signal_window["date"].isin(scheduled_dates)].dropna(subset=["factor_value"]).reset_index(drop=True)


def _run_case(
    bars: pd.DataFrame,
    labels: pd.DataFrame,
    scheduled_factors: pd.DataFrame,
    spec: dict[str, Any],
    *,
    end: Any,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ic = compute_ic(scheduled_factors, labels)
    groups = quantile_group_returns(scheduled_factors, labels, quantiles=5)
    long_short = long_short_returns(scheduled_factors, labels, quantiles=5)
    backtest = run_factor_backtest(
        scheduled_factors,
        bars,
        top_n=int(spec["top_n"]),
        cost_bps=float(spec["cost_bps"]),
        portfolio_scope="market",
        execution_lag=1,
        holding_period=int(spec["holding_period"]),
        rebalance_interval=int(spec["schedule_interval"]),
        target_gross_exposure=1.0,
        periods_per_year=252 / int(spec["schedule_interval"]),
        market_impact_bps=10.0,
        max_participation_rate=0.05,
        portfolio_value=1_000_000.0,
    )
    if not backtest.trades.empty:
        max_exit = pd.to_datetime(backtest.trades["exit_date"]).max().date()
        if max_exit > end:
            raise ValueError(f"Batch12 OOS case touched final holdout exit date: {max_exit}")
    tail_ic = compute_ic(backtest.positions, labels)
    comparison_bars = _comparison_bars(bars, scheduled_factors)
    benchmark = build_benchmark_curve(comparison_bars)
    benchmark_metrics = compare_strategy_to_benchmark(
        backtest.equity_curve,
        benchmark,
        periods_per_year=252 / int(spec["schedule_interval"]),
    )
    metrics = dict(backtest.metrics)
    metrics.update(_trade_return_quality_metrics(backtest.trades))
    result = {
        "factor_summary": {**_factor_summary(ic), **_tail_factor_summary(tail_ic)},
        "metrics": metrics,
        "benchmark_metrics": benchmark_metrics,
        "monthly_positive_rate": _monthly_positive_rate(backtest.equity_curve),
        "artifact_rows": {
            "scheduled_factors": len(scheduled_factors),
            "signal_dates": int(scheduled_factors["date"].nunique()) if "date" in scheduled_factors else 0,
            "trades": len(backtest.trades),
            "holdings": len(backtest.positions),
            "ic": len(ic),
            "tail_ic": len(tail_ic),
        },
        "equity_curve": backtest.equity_curve,
        "trades": backtest.trades,
        "positions": backtest.positions,
        "ic": ic,
        "tail_ic": tail_ic,
        "group_returns": groups,
        "long_short": long_short,
    }
    _write_case_artifacts(output_dir, result)
    return result


def _row_from_result(spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    factor = result["factor_summary"]
    benchmark = result["benchmark_metrics"]
    alpha = float(spec.get("cumulative_bonferroni_alpha", 0.05) or 0.05)
    rank_p = _number(factor.get("rank_ic_p_value"), default=1.0)
    tail_rank_p = _number(factor.get("tail_rank_ic_p_value"), default=1.0)
    mean_rank_ic = _number(factor.get("mean_rank_ic"))
    tail_mean_rank_ic = _number(factor.get("tail_mean_rank_ic"))
    relative_return = _number(benchmark.get("relative_return"))
    total_return = _number(metrics.get("total_return"))
    max_drawdown = _number(metrics.get("max_drawdown"))
    capacity_limited = int(_number(metrics.get("capacity_limited_trades")))
    overlap_adjusted = _number(metrics.get("overlap_autocorr_adjusted_sharpe"))
    monthly_positive = _number(result.get("monthly_positive_rate"))
    max_trade_gross_return = _number(metrics.get("max_trade_gross_return"))
    extreme_trade_return_flag = max_trade_gross_return > MAX_ALLOWED_TRADE_GROSS_RETURN
    rank_ic_direction_ok = mean_rank_ic > 0.0
    tail_rank_ic_direction_ok = tail_mean_rank_ic > 0.0
    research_lead = (
        total_return > 0.0
        and relative_return > 0.0
        and max_drawdown >= -0.20
        and capacity_limited == 0
        and overlap_adjusted > 0.0
        and monthly_positive >= 0.50
        and rank_ic_direction_ok
        and tail_rank_ic_direction_ok
        and not extreme_trade_return_flag
    )
    paper_ready = research_lead and rank_p <= alpha and tail_rank_p <= alpha
    return {
        "case_id": spec["case_id"],
        "role": spec["role"],
        "factor_name": spec["factor_name"],
        "schedule_interval": int(spec["schedule_interval"]),
        "schedule_offset": int(spec["schedule_offset"]),
        "holding_period": int(spec["holding_period"]),
        "top_n": int(spec["top_n"]),
        "cost_bps": float(spec["cost_bps"]),
        "scheduled_factor_rows": result["artifact_rows"]["scheduled_factors"],
        "executed_signal_dates": result["artifact_rows"]["signal_dates"],
        "trades": result["artifact_rows"]["trades"],
        "total_return": total_return,
        "annualized_return": _number(metrics.get("annualized_return")),
        "sharpe": _number(metrics.get("sharpe")),
        "win_rate": _number(metrics.get("win_rate")),
        "max_drawdown": max_drawdown,
        "relative_return": relative_return,
        "mean_rank_ic": mean_rank_ic,
        "tail_mean_rank_ic": tail_mean_rank_ic,
        "rank_ic_direction_ok": bool(rank_ic_direction_ok),
        "tail_rank_ic_direction_ok": bool(tail_rank_ic_direction_ok),
        "rank_ic_p_value": rank_p,
        "tail_rank_ic_p_value": tail_rank_p,
        "cumulative_hypothesis_count": int(spec.get("cumulative_hypothesis_count", 1) or 1),
        "cumulative_bonferroni_alpha": alpha,
        "monthly_positive_rate": monthly_positive,
        "max_trade_gross_return": max_trade_gross_return,
        "p99_trade_gross_return": _number(metrics.get("p99_trade_gross_return")),
        "extreme_trade_return_flag": bool(extreme_trade_return_flag),
        "overlap_naive_sharpe": _number(metrics.get("overlap_naive_sharpe")),
        "overlap_autocorr_adjusted_sharpe": overlap_adjusted,
        "overlap_newey_west_standard_error_mean": _number(metrics.get("overlap_newey_west_standard_error_mean")),
        "overlap_newey_west_t_stat_mean": _number(metrics.get("overlap_newey_west_t_stat_mean")),
        "overlap_variance_inflation": _number(metrics.get("overlap_variance_inflation")),
        "overlap_effective_sample_size": _number(metrics.get("overlap_effective_sample_size")),
        "overlap_risk_flag": bool(metrics.get("overlap_risk_flag", False)),
        "turnover": _number(metrics.get("turnover")),
        "avg_participation_rate": _number(metrics.get("avg_participation_rate")),
        "max_participation_rate": _number(metrics.get("max_participation_rate")),
        "capacity_limited_trades": capacity_limited,
        "research_lead": bool(research_lead),
        "paper_ready": bool(paper_ready),
    }


def _prepare_window_frame(frame: pd.DataFrame, *, start: Any, end: Any, label: str) -> pd.DataFrame:
    if "date" not in frame.columns:
        raise ValueError(f"{label} missing date column")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date
    return result[(result["date"] >= start) & (result["date"] <= end)].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _require_coverage(frame: pd.DataFrame, *, start: Any, end: Any, label: str) -> None:
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.date
    if dates.empty or dates.min() > start or dates.max() < end:
        raise ValueError(f"{label} coverage must include {start} to {end}")


def _comparison_bars(bars: pd.DataFrame, scheduled_factors: pd.DataFrame) -> pd.DataFrame:
    if scheduled_factors.empty:
        return bars.iloc[0:0].copy()
    start = min(pd.to_datetime(scheduled_factors["date"]).dt.date)
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame[frame["date"] >= start].reset_index(drop=True)


def _monthly_positive_rate(equity_curve: pd.DataFrame) -> float:
    if equity_curve.empty or "date" not in equity_curve or "period_return" not in equity_curve:
        return 0.0
    frame = equity_curve.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["period_return"] = pd.to_numeric(frame["period_return"], errors="coerce")
    monthly = frame.groupby(frame["date"].dt.to_period("M"))["period_return"].apply(
        lambda values: float((1.0 + values.dropna()).prod() - 1.0)
    )
    if monthly.empty:
        return 0.0
    return float((monthly > 0.0).mean())


def _trade_return_quality_metrics(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty or "gross_return" not in trades:
        return {
            "max_trade_gross_return": 0.0,
            "p99_trade_gross_return": 0.0,
        }
    gross = pd.to_numeric(trades["gross_return"], errors="coerce").dropna()
    if gross.empty:
        return {
            "max_trade_gross_return": 0.0,
            "p99_trade_gross_return": 0.0,
        }
    return {
        "max_trade_gross_return": float(gross.max()),
        "p99_trade_gross_return": float(gross.quantile(0.99)),
    }


def _write_case_artifacts(output_dir: Path, result: dict[str, Any]) -> None:
    for name in ["equity_curve", "trades", "positions", "ic", "tail_ic", "group_returns", "long_short"]:
        frame = result[name]
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(output_dir / f"{name}.csv", index=False)
    (output_dir / "metrics.json").write_text(
        json.dumps(_sanitize(result["metrics"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "factor_summary.json").write_text(
        json.dumps(_sanitize(result["factor_summary"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "benchmark_metrics.json").write_text(
        json.dumps(_sanitize(result["benchmark_metrics"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _render_report(manifest: dict[str, Any], leaderboard: pd.DataFrame) -> str:
    lines = [
        "# CN Stock Batch12 OOS Validation",
        "",
        f"- Status: {manifest['status']}",
        f"- Validation window: {manifest['validation_window']['start']} to {manifest['validation_window']['end']}",
        f"- Final holdout touched: {str(manifest['final_holdout_touched']).lower()}",
        f"- Cases: {manifest['summary']['cases']}",
        f"- Paper-ready: {manifest['summary']['paper_ready']}",
        f"- Research leads: {manifest['summary']['research_lead']}",
        "",
        "| Case | Role | Cost | Interval | Return | Sharpe | Win | Max DD | Relative | Ovlp Sharpe | Cap Trades | Lead | Paper |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in leaderboard.to_dict(orient="records"):
        lines.append(
            f"| {row['case_id']} | {row['role']} | {_fmt(row['cost_bps'])} | {row['schedule_interval']} | "
            f"{_fmt(row['total_return'])} | {_fmt(row['sharpe'])} | {_fmt(row['win_rate'])} | "
            f"{_fmt(row['max_drawdown'])} | {_fmt(row['relative_return'])} | "
            f"{_fmt(row['overlap_autocorr_adjusted_sharpe'])} | {row['capacity_limited_trades']} | "
            f"{row['research_lead']} | {row['paper_ready']} |"
        )
    lines.extend(
        [
            "",
            "## Judgment",
            "",
            "This is a locked-parameter 2025 OOS validation. The 2026 final holdout remains untouched.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_cost(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")


def _fmt(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:.4f}" if math.isfinite(number) else ""


def _number(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return _sanitize(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return _sanitize(value.to_list())
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return number if math.isfinite(number) else 0.0
    if isinstance(value, float):
        return value if math.isfinite(value) else 0.0
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value
