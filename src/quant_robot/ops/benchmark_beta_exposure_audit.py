from __future__ import annotations

from collections import Counter
from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.bottom_exclusion_portfolio_backtest import (
    SAFETY,
    _attach_entry_amount,
    _basket_stats,
    _classification_rank,
    _empty_metrics,
    _filter_min_entry_amount,
    _filter_rebalance_dates,
    _kept_mask,
    _merge_inputs,
    _number,
    _prepare_factors,
    _prepare_labels,
    _sanitize,
)
from quant_robot.ops.dynamic_cash_overlay_backtest import _date_exposure, _market_state_frame


STAGE = "benchmark_beta_exposure_audit"


def run_benchmark_beta_exposure_audit(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    source_report: str | None = None,
    bottom_quantile: float = 0.2,
    rebalance_interval: int = 1,
    holding_period: int = 1,
    cost_bps: float = 0.0,
    market_impact_bps: float = 0.0,
    max_participation_rate: float | None = None,
    min_entry_amount: float | None = None,
    portfolio_value: float = 1_000_000.0,
    target_gross_exposure: float = 0.6,
    risk_off_exposure: float = 0.0,
    market_state_lookback: int = 20,
    periods_per_year: float | None = None,
    min_alpha_t_stat: float = 2.0,
    min_residual_sharpe: float = 0.5,
    min_beta_dominated_r_squared: float = 0.6,
    min_meaningful_beta: float = 0.2,
) -> dict[str, Any]:
    factor_frame = _filter_rebalance_dates(_prepare_factors(factors), rebalance_interval)
    label_frame = _prepare_labels(labels)
    merged = _merge_inputs(factor_frame, label_frame)
    merged = _attach_entry_amount(merged, bars)
    merged = _filter_min_entry_amount(merged, min_entry_amount)
    resolved_periods_per_year = periods_per_year or (252.0 / float(max(rebalance_interval, 1)))
    market_state = _market_state_frame(
        bars,
        lookback=market_state_lookback,
        target_gross_exposure=target_gross_exposure,
        risk_off_exposure=risk_off_exposure,
    )
    date_exposure = _date_exposure(market_state)
    leaderboard = _build_leaderboard(
        merged,
        market_state=market_state,
        bottom_quantile=bottom_quantile,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        cost_bps=cost_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        portfolio_value=portfolio_value,
        target_gross_exposure=target_gross_exposure,
        periods_per_year=resolved_periods_per_year,
        date_exposure=date_exposure,
        min_alpha_t_stat=min_alpha_t_stat,
        min_residual_sharpe=min_residual_sharpe,
        min_beta_dominated_r_squared=min_beta_dominated_r_squared,
        min_meaningful_beta=min_meaningful_beta,
    )
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "bottom_quantile": bottom_quantile,
            "rebalance_interval": rebalance_interval,
            "holding_period": holding_period,
            "cost_bps": cost_bps,
            "market_impact_bps": market_impact_bps,
            "max_participation_rate": max_participation_rate,
            "min_entry_amount": min_entry_amount,
            "portfolio_value": portfolio_value,
            "target_gross_exposure": target_gross_exposure,
            "risk_off_exposure": risk_off_exposure,
            "market_state_lookback": market_state_lookback,
            "periods_per_year": resolved_periods_per_year,
            "min_alpha_t_stat": min_alpha_t_stat,
            "min_residual_sharpe": min_residual_sharpe,
            "min_beta_dominated_r_squared": min_beta_dominated_r_squared,
            "min_meaningful_beta": min_meaningful_beta,
        },
        "summary": _summary(leaderboard, merged, market_state),
        "leaderboard": leaderboard,
        "diagnostic_only": True,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_benchmark_beta_exposure_markdown(result)
    return result


def calculate_benchmark_beta_exposure(
    strategy_curve: pd.DataFrame,
    benchmark_curve: pd.DataFrame,
    *,
    market_state: pd.DataFrame | None = None,
    periods_per_year: float = 252.0,
) -> dict[str, Any]:
    aligned = _aligned_returns(strategy_curve, benchmark_curve)
    if len(aligned) < 3:
        return _empty_beta_stats()

    strategy = aligned["strategy_return"].astype(float)
    benchmark = aligned["benchmark_return"].astype(float)
    benchmark_mean = float(benchmark.mean())
    strategy_mean = float(strategy.mean())
    benchmark_deviation = benchmark - benchmark_mean
    strategy_deviation = strategy - strategy_mean
    benchmark_variance = float((benchmark_deviation * benchmark_deviation).sum())
    if benchmark_variance <= 0.0:
        return _empty_beta_stats(observations=len(aligned))

    beta = float((benchmark_deviation * strategy_deviation).sum() / benchmark_variance)
    beta_adjusted_return = strategy - beta * benchmark
    alpha_per_period = float(beta_adjusted_return.mean())
    alpha_annualized = alpha_per_period * periods_per_year
    residual_std = float(beta_adjusted_return.std(ddof=1))
    residual_sharpe = _sharpe(beta_adjusted_return, periods_per_year)
    alpha_t_stat = 0.0 if residual_std <= 1e-12 else alpha_per_period / (residual_std / math.sqrt(len(beta_adjusted_return)))
    fitted = alpha_per_period + beta * benchmark
    ss_resid = float(((strategy - fitted) ** 2).sum())
    ss_total = float(((strategy - strategy_mean) ** 2).sum())
    r_squared = 0.0 if ss_total <= 0.0 else max(0.0, min(1.0, 1.0 - ss_resid / ss_total))

    stats = {
        "observations": int(len(aligned)),
        "beta": beta,
        "r_squared": r_squared,
        "alpha_per_period": alpha_per_period,
        "alpha_annualized": alpha_annualized,
        "alpha_t_stat": alpha_t_stat,
        "residual_sharpe": residual_sharpe,
        "strategy_total_return": _total_return(strategy),
        "benchmark_total_return": _total_return(benchmark),
        "beta_adjusted_total_return": _total_return(beta_adjusted_return),
        "strategy_mean_return": strategy_mean,
        "benchmark_mean_return": benchmark_mean,
    }
    stats.update(_market_state_return_stats(aligned, market_state, periods_per_year=periods_per_year))
    return _sanitize(stats)


def classify_benchmark_beta_exposure(
    stats: dict[str, Any],
    *,
    min_alpha_t_stat: float = 2.0,
    min_residual_sharpe: float = 0.5,
    min_beta_dominated_r_squared: float = 0.6,
    min_meaningful_beta: float = 0.2,
) -> str:
    alpha_ok = (
        _number(stats.get("beta_adjusted_total_return")) > 0.0
        and _number(stats.get("alpha_t_stat")) >= min_alpha_t_stat
        and _number(stats.get("residual_sharpe")) >= min_residual_sharpe
    )
    beta_dominated = (
        abs(_number(stats.get("beta"))) >= min_meaningful_beta
        and _number(stats.get("r_squared")) >= min_beta_dominated_r_squared
    )
    if alpha_ok and not beta_dominated:
        return "stock_selection_alpha_candidate"
    if alpha_ok:
        return "stock_selection_research_lead_with_beta"
    if beta_dominated:
        return "beta_dominated_or_market_timing"
    return "weak_or_unproven_after_beta"


def write_benchmark_beta_exposure_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "benchmark_beta_exposure_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "benchmark_beta_exposure_audit.md").write_text(
        render_benchmark_beta_exposure_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(output_path / "leaderboard.csv", index=False)


def render_benchmark_beta_exposure_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    thresholds = _dict(result.get("thresholds"))
    lines = [
        "# Benchmark Beta Exposure Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source report: {result.get('source_report') or 'unknown'}",
        f"- Market-state lookback: {thresholds.get('market_state_lookback')}",
        f"- Target gross exposure: {_number(thresholds.get('target_gross_exposure')):.2f}",
        f"- Risk-off exposure: {_number(thresholds.get('risk_off_exposure')):.2f}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Alpha candidates: {summary.get('stock_selection_alpha_candidates', 0)}",
        f"- Research leads with beta: {summary.get('stock_selection_research_leads_with_beta', 0)}",
        f"- Beta dominated or market timing: {summary.get('beta_dominated_or_market_timing', 0)}",
        f"- Weak or unproven after beta: {summary.get('weak_or_unproven_after_beta', 0)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "- {factor}: {classification}, dyn_total={dyn_total:.4f}, dyn_beta={dyn_beta:.4f}, "
            "dyn_r2={dyn_r2:.4f}, dyn_alpha_t={dyn_alpha_t:.4f}, dyn_resid_sharpe={dyn_resid:.4f}, "
            "dyn_beta_adj={dyn_beta_adj:.4f}, static_beta={static_beta:.4f}, static_r2={static_r2:.4f}".format(
                factor=row.get("factor_name"),
                classification=row.get("classification"),
                dyn_total=_number(row.get("dynamic_total_return")),
                dyn_beta=_number(row.get("dynamic_beta")),
                dyn_r2=_number(row.get("dynamic_r_squared")),
                dyn_alpha_t=_number(row.get("dynamic_alpha_t_stat")),
                dyn_resid=_number(row.get("dynamic_residual_sharpe")),
                dyn_beta_adj=_number(row.get("dynamic_beta_adjusted_total_return")),
                static_beta=_number(row.get("static_beta")),
                static_r2=_number(row.get("static_r_squared")),
            )
        )
    return "\n".join(lines) + "\n"


def _build_leaderboard(
    merged: pd.DataFrame,
    *,
    market_state: pd.DataFrame,
    bottom_quantile: float,
    holding_period: int,
    rebalance_interval: int,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
    portfolio_value: float,
    target_gross_exposure: float,
    periods_per_year: float,
    date_exposure: dict[Any, float],
    min_alpha_t_stat: float,
    min_residual_sharpe: float,
    min_beta_dominated_r_squared: float,
    min_meaningful_beta: float,
) -> list[dict[str, Any]]:
    if merged.empty:
        return []
    rows = []
    for key, group in merged.groupby(["market", "factor_name", "horizon", "execution_lag"], sort=True):
        market, factor_name, horizon, execution_lag = key
        kept_mask = _kept_mask(group, bottom_quantile=bottom_quantile)
        static_strategy = _basket_stats(
            group,
            kept_mask,
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            cost_bps=cost_bps,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            portfolio_value=portfolio_value,
            target_gross_exposure=target_gross_exposure,
            periods_per_year=periods_per_year,
        )
        static_benchmark = _basket_stats(
            group,
            pd.Series(True, index=group.index),
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            cost_bps=cost_bps,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            portfolio_value=portfolio_value,
            target_gross_exposure=target_gross_exposure,
            periods_per_year=periods_per_year,
        )
        dynamic_strategy = _basket_stats(
            group,
            kept_mask,
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            cost_bps=cost_bps,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            portfolio_value=portfolio_value,
            target_gross_exposure=target_gross_exposure,
            periods_per_year=periods_per_year,
            date_exposure=date_exposure,
        )
        dynamic_benchmark = _basket_stats(
            group,
            pd.Series(True, index=group.index),
            holding_period=holding_period,
            rebalance_interval=rebalance_interval,
            cost_bps=cost_bps,
            market_impact_bps=market_impact_bps,
            max_participation_rate=max_participation_rate,
            portfolio_value=portfolio_value,
            target_gross_exposure=target_gross_exposure,
            periods_per_year=periods_per_year,
            date_exposure=date_exposure,
        )
        static_beta = calculate_benchmark_beta_exposure(
            static_strategy["curve"],
            static_benchmark["curve"],
            market_state=market_state,
            periods_per_year=periods_per_year,
        )
        dynamic_beta = calculate_benchmark_beta_exposure(
            dynamic_strategy["curve"],
            dynamic_benchmark["curve"],
            market_state=market_state,
            periods_per_year=periods_per_year,
        )
        classification = classify_benchmark_beta_exposure(
            dynamic_beta,
            min_alpha_t_stat=min_alpha_t_stat,
            min_residual_sharpe=min_residual_sharpe,
            min_beta_dominated_r_squared=min_beta_dominated_r_squared,
            min_meaningful_beta=min_meaningful_beta,
        )
        rows.append(
            _sanitize(
                {
                    "market": market,
                    "factor_name": factor_name,
                    "horizon": int(horizon),
                    "execution_lag": int(execution_lag),
                    "classification": classification,
                    "static_total_return": static_strategy["metrics"]["total_return"],
                    "static_benchmark_total_return": static_benchmark["metrics"]["total_return"],
                    "static_max_drawdown": static_strategy["metrics"]["max_drawdown"],
                    "static_beta": static_beta["beta"],
                    "static_r_squared": static_beta["r_squared"],
                    "static_alpha_t_stat": static_beta["alpha_t_stat"],
                    "static_residual_sharpe": static_beta["residual_sharpe"],
                    "static_beta_adjusted_total_return": static_beta["beta_adjusted_total_return"],
                    "dynamic_total_return": dynamic_strategy["metrics"]["total_return"],
                    "dynamic_benchmark_total_return": dynamic_benchmark["metrics"]["total_return"],
                    "dynamic_max_drawdown": dynamic_strategy["metrics"]["max_drawdown"],
                    "dynamic_beta": dynamic_beta["beta"],
                    "dynamic_r_squared": dynamic_beta["r_squared"],
                    "dynamic_alpha_t_stat": dynamic_beta["alpha_t_stat"],
                    "dynamic_residual_sharpe": dynamic_beta["residual_sharpe"],
                    "dynamic_beta_adjusted_total_return": dynamic_beta["beta_adjusted_total_return"],
                    "dynamic_risk_on_mean_return": dynamic_beta["risk_on_mean_return"],
                    "dynamic_risk_off_mean_return": dynamic_beta["risk_off_mean_return"],
                    "dynamic_risk_on_observations": dynamic_beta["risk_on_observations"],
                    "dynamic_risk_off_observations": dynamic_beta["risk_off_observations"],
                }
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            _beta_classification_rank(str(row.get("classification"))),
            -_number(row.get("dynamic_alpha_t_stat")),
            -_number(row.get("dynamic_residual_sharpe")),
            _number(row.get("dynamic_r_squared")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _aligned_returns(strategy_curve: pd.DataFrame, benchmark_curve: pd.DataFrame) -> pd.DataFrame:
    if strategy_curve.empty or benchmark_curve.empty:
        return pd.DataFrame(columns=["date", "strategy_return", "benchmark_return"])
    strategy = strategy_curve[["date", "period_return"]].copy().rename(columns={"period_return": "strategy_return"})
    benchmark = benchmark_curve[["date", "period_return"]].copy().rename(columns={"period_return": "benchmark_return"})
    strategy["date"] = pd.to_datetime(strategy["date"])
    benchmark["date"] = pd.to_datetime(benchmark["date"])
    merged = strategy.merge(benchmark, on="date", how="inner").dropna(subset=["strategy_return", "benchmark_return"])
    return merged.sort_values("date").reset_index(drop=True)


def _market_state_return_stats(
    aligned: pd.DataFrame,
    market_state: pd.DataFrame | None,
    *,
    periods_per_year: float,
) -> dict[str, Any]:
    empty = {
        "risk_on_observations": 0,
        "risk_off_observations": 0,
        "risk_on_mean_return": 0.0,
        "risk_off_mean_return": 0.0,
        "risk_on_win_rate": 0.0,
        "risk_off_win_rate": 0.0,
    }
    if market_state is None or market_state.empty or aligned.empty:
        return empty
    states = market_state[["date", "risk_on"]].copy()
    states["date"] = pd.to_datetime(states["date"])
    merged = aligned.merge(states, on="date", how="left").dropna(subset=["risk_on"])
    if merged.empty:
        return empty
    result = empty.copy()
    for risk_on, group in merged.groupby("risk_on", sort=True):
        prefix = "risk_on" if bool(risk_on) else "risk_off"
        returns = group["strategy_return"].astype(float)
        result[f"{prefix}_observations"] = int(len(group))
        result[f"{prefix}_mean_return"] = float(returns.mean() * periods_per_year)
        result[f"{prefix}_win_rate"] = float((returns > 0.0).mean())
    return result


def _summary(leaderboard: list[dict[str, Any]], merged: pd.DataFrame, market_state: pd.DataFrame) -> dict[str, Any]:
    classifications = Counter(str(row.get("classification")) for row in leaderboard)
    return {
        "input_rows": int(len(merged)),
        "cases": len(leaderboard),
        "stock_selection_alpha_candidates": classifications.get("stock_selection_alpha_candidate", 0),
        "stock_selection_research_leads_with_beta": classifications.get("stock_selection_research_lead_with_beta", 0),
        "beta_dominated_or_market_timing": classifications.get("beta_dominated_or_market_timing", 0),
        "weak_or_unproven_after_beta": classifications.get("weak_or_unproven_after_beta", 0),
        "market_state_rows": int(len(market_state)),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _empty_beta_stats(observations: int = 0) -> dict[str, Any]:
    stats = {
        "observations": int(observations),
        "beta": 0.0,
        "r_squared": 0.0,
        "alpha_per_period": 0.0,
        "alpha_annualized": 0.0,
        "alpha_t_stat": 0.0,
        "residual_sharpe": 0.0,
        "strategy_total_return": 0.0,
        "benchmark_total_return": 0.0,
        "beta_adjusted_total_return": 0.0,
        "strategy_mean_return": 0.0,
        "benchmark_mean_return": 0.0,
    }
    stats.update(_market_state_return_stats(pd.DataFrame(), None, periods_per_year=252.0))
    return stats


def _total_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    return float((1.0 + returns.astype(float)).prod() - 1.0)


def _sharpe(returns: pd.Series, periods_per_year: float) -> float:
    if returns.empty:
        return 0.0
    std = float(returns.std(ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(returns.mean() / std * math.sqrt(periods_per_year))


def _beta_classification_rank(classification: str) -> int:
    order = {
        "stock_selection_alpha_candidate": 0,
        "stock_selection_research_lead_with_beta": 1,
        "beta_dominated_or_market_timing": 2,
        "weak_or_unproven_after_beta": 3,
    }
    return order.get(classification, _classification_rank(classification))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
