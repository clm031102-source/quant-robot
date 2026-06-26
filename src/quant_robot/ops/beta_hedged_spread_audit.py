from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.bottom_exclusion_portfolio_backtest import (
    SAFETY,
    _attach_entry_amount,
    _basket_stats,
    _classification_rank,
    _filter_min_entry_amount,
    _filter_rebalance_dates,
    _kept_mask,
    _merge_inputs,
    _number,
    _prepare_factors,
    _prepare_labels,
    _sanitize,
)
from quant_robot.research.overlap import overlap_aware_return_stats


STAGE = "beta_hedged_spread_audit"


def run_beta_hedged_spread_audit(
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
    hedge_ratio: float = 1.0,
    periods_per_year: float | None = None,
    min_positive_fold_rate: float = 0.6,
    min_overlap_adjusted_sharpe: float = 0.5,
    max_drawdown_limit: float | None = 0.5,
) -> dict[str, Any]:
    if hedge_ratio < 0.0:
        raise ValueError("hedge_ratio must be non-negative")
    factor_frame = _filter_rebalance_dates(_prepare_factors(factors), rebalance_interval)
    label_frame = _prepare_labels(labels)
    merged = _merge_inputs(factor_frame, label_frame)
    merged = _attach_entry_amount(merged, bars)
    merged = _filter_min_entry_amount(merged, min_entry_amount)
    resolved_periods_per_year = periods_per_year or (252.0 / float(max(rebalance_interval, 1)))
    leaderboard = _build_leaderboard(
        merged,
        bottom_quantile=bottom_quantile,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        cost_bps=cost_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        portfolio_value=portfolio_value,
        target_gross_exposure=target_gross_exposure,
        hedge_ratio=hedge_ratio,
        periods_per_year=resolved_periods_per_year,
        min_positive_fold_rate=min_positive_fold_rate,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_limit=max_drawdown_limit,
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
            "hedge_ratio": hedge_ratio,
            "periods_per_year": resolved_periods_per_year,
            "min_positive_fold_rate": min_positive_fold_rate,
            "min_overlap_adjusted_sharpe": min_overlap_adjusted_sharpe,
            "max_drawdown_limit": max_drawdown_limit,
        },
        "summary": _summary(leaderboard, merged),
        "leaderboard": leaderboard,
        "diagnostic_only": True,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_beta_hedged_spread_markdown(result)
    return result


def write_beta_hedged_spread_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "beta_hedged_spread_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "beta_hedged_spread_audit.md").write_text(
        render_beta_hedged_spread_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(output_path / "leaderboard.csv", index=False)


def render_beta_hedged_spread_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    thresholds = _dict(result.get("thresholds"))
    lines = [
        "# Beta-Hedged Spread Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source report: {result.get('source_report') or 'unknown'}",
        f"- Hedge ratio: {_number(thresholds.get('hedge_ratio')):.2f}",
        f"- Target gross exposure: {_number(thresholds.get('target_gross_exposure')):.2f}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Spread candidates: {summary.get('beta_hedged_spread_candidates', 0)}",
        f"- Spread research leads: {summary.get('beta_hedged_spread_research_leads', 0)}",
        f"- Weak or unproven spreads: {summary.get('weak_or_unproven_spreads', 0)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "- {factor}: {classification}, spread_total={spread_total:.4f}, spread_sharpe={spread_sharpe:.4f}, "
            "spread_overlap={spread_overlap:.4f}, spread_dd={spread_dd:.4f}, spread_win={spread_win:.4f}, "
            "folds+={fold_rate:.2f}, selected_total={selected_total:.4f}, benchmark_total={benchmark_total:.4f}".format(
                factor=row.get("factor_name"),
                classification=row.get("classification"),
                spread_total=_number(row.get("spread_total_return")),
                spread_sharpe=_number(row.get("spread_sharpe")),
                spread_overlap=_number(row.get("spread_overlap_autocorr_adjusted_sharpe")),
                spread_dd=_number(row.get("spread_max_drawdown")),
                spread_win=_number(row.get("spread_win_rate")),
                fold_rate=_number(row.get("positive_fold_rate")),
                selected_total=_number(row.get("selected_total_return")),
                benchmark_total=_number(row.get("benchmark_total_return")),
            )
        )
    return "\n".join(lines) + "\n"


def _build_leaderboard(
    merged: pd.DataFrame,
    *,
    bottom_quantile: float,
    holding_period: int,
    rebalance_interval: int,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
    portfolio_value: float,
    target_gross_exposure: float,
    hedge_ratio: float,
    periods_per_year: float,
    min_positive_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
) -> list[dict[str, Any]]:
    if merged.empty:
        return []
    rows = []
    for key, group in merged.groupby(["market", "factor_name", "horizon", "execution_lag"], sort=True):
        market, factor_name, horizon, execution_lag = key
        kept_mask = _kept_mask(group, bottom_quantile=bottom_quantile)
        selected = _basket_stats(
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
        benchmark = _basket_stats(
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
        spread_curve = _spread_curve(selected["curve"], benchmark["curve"], hedge_ratio=hedge_ratio)
        spread_metrics = _spread_metrics(spread_curve, holding_period=holding_period, periods_per_year=periods_per_year)
        folds = _folds(spread_curve, periods_per_year=periods_per_year)
        positive_fold_rate = _positive_fold_rate(folds)
        capacity_limited = int(
            _number(selected["metrics"].get("capacity_limited_trades"))
            + _number(benchmark["metrics"].get("capacity_limited_trades"))
        )
        classification = _classify_spread(
            metrics=spread_metrics,
            positive_fold_rate=positive_fold_rate,
            capacity_limited_trades=capacity_limited,
            min_positive_fold_rate=min_positive_fold_rate,
            min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
            max_drawdown_limit=max_drawdown_limit,
        )
        rows.append(
            _sanitize(
                {
                    "market": market,
                    "factor_name": factor_name,
                    "horizon": int(horizon),
                    "execution_lag": int(execution_lag),
                    "classification": classification,
                    "hedge_ratio": hedge_ratio,
                    "spread_total_return": spread_metrics["total_return"],
                    "spread_annualized_return": spread_metrics["annualized_return"],
                    "spread_sharpe": spread_metrics["sharpe"],
                    "spread_overlap_autocorr_adjusted_sharpe": spread_metrics["overlap_autocorr_adjusted_sharpe"],
                    "spread_newey_west_t_stat_mean": spread_metrics["overlap_newey_west_t_stat_mean"],
                    "spread_max_drawdown": spread_metrics["max_drawdown"],
                    "spread_win_rate": spread_metrics["win_rate"],
                    "positive_fold_rate": positive_fold_rate,
                    "positive_folds": sum(1 for fold in folds if _number(fold.get("total_return")) > 0.0),
                    "fold_count": len(folds),
                    "capacity_limited_trades": capacity_limited,
                    "selected_total_return": selected["metrics"]["total_return"],
                    "benchmark_total_return": benchmark["metrics"]["total_return"],
                    "folds": folds,
                }
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            _spread_classification_rank(str(row.get("classification"))),
            -_number(row.get("spread_overlap_autocorr_adjusted_sharpe")),
            -_number(row.get("spread_total_return")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _spread_curve(selected_curve: pd.DataFrame, benchmark_curve: pd.DataFrame, *, hedge_ratio: float) -> pd.DataFrame:
    selected = selected_curve[["date", "period_return"]].rename(columns={"period_return": "selected_return"})
    benchmark_columns = ["date", "period_return"]
    if "gross_period_return" in benchmark_curve.columns:
        benchmark_columns.append("gross_period_return")
    benchmark = benchmark_curve[benchmark_columns].rename(
        columns={"period_return": "benchmark_return", "gross_period_return": "benchmark_gross_return"}
    )
    merged = selected.merge(benchmark, on="date", how="outer").fillna(0.0).sort_values("date").reset_index(drop=True)
    if "benchmark_gross_return" not in merged.columns:
        merged["benchmark_gross_return"] = merged["benchmark_return"]
    benchmark_cost = merged["benchmark_gross_return"].astype(float) - merged["benchmark_return"].astype(float)
    short_benchmark_return = -merged["benchmark_gross_return"].astype(float) - benchmark_cost
    merged["period_return"] = merged["selected_return"].astype(float) + float(hedge_ratio) * short_benchmark_return
    merged["equity"] = (1.0 + merged["period_return"]).cumprod()
    return merged[["date", "period_return", "equity"]]


def _spread_metrics(curve: pd.DataFrame, *, holding_period: int, periods_per_year: float) -> dict[str, Any]:
    if curve.empty:
        return _empty_spread_metrics()
    metrics = summarize_returns(curve["period_return"], periods_per_year=periods_per_year)
    overlap = overlap_aware_return_stats(
        curve["period_return"],
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    metrics.update({f"overlap_{key}": value for key, value in overlap.items() if key != "autocorrelations"})
    return metrics


def _folds(curve: pd.DataFrame, *, periods_per_year: float) -> list[dict[str, Any]]:
    if curve.empty:
        return []
    frame = curve.copy()
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    rows = []
    for year, group in frame.groupby("year", sort=True):
        metrics = summarize_returns(group["period_return"], periods_per_year=periods_per_year)
        rows.append(
            {
                "fold": str(year),
                "observations": int(len(group)),
                "total_return": metrics["total_return"],
                "sharpe": metrics["sharpe"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
            }
        )
    return _sanitize(rows)


def _positive_fold_rate(folds: list[dict[str, Any]]) -> float:
    if not folds:
        return 0.0
    return float(sum(1 for fold in folds if _number(fold.get("total_return")) > 0.0) / len(folds))


def _classify_spread(
    *,
    metrics: dict[str, Any],
    positive_fold_rate: float,
    capacity_limited_trades: int,
    min_positive_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
) -> str:
    positive_lead = _number(metrics.get("total_return")) > 0.0 and positive_fold_rate >= min_positive_fold_rate
    risk_quality_ok = _number(metrics.get("overlap_autocorr_adjusted_sharpe")) >= min_overlap_adjusted_sharpe and (
        max_drawdown_limit is None or _number(metrics.get("max_drawdown")) >= -float(max_drawdown_limit)
    )
    if positive_lead and risk_quality_ok and capacity_limited_trades == 0:
        return "beta_hedged_spread_candidate"
    if positive_lead:
        return "beta_hedged_spread_research_lead"
    return "weak_or_unproven_spread"


def _summary(leaderboard: list[dict[str, Any]], merged: pd.DataFrame) -> dict[str, Any]:
    classifications = Counter(str(row.get("classification")) for row in leaderboard)
    return {
        "input_rows": int(len(merged)),
        "cases": len(leaderboard),
        "beta_hedged_spread_candidates": classifications.get("beta_hedged_spread_candidate", 0),
        "beta_hedged_spread_research_leads": classifications.get("beta_hedged_spread_research_lead", 0),
        "weak_or_unproven_spreads": classifications.get("weak_or_unproven_spread", 0),
        "best_spread_total_return": max((_number(row.get("spread_total_return")) for row in leaderboard), default=0.0),
        "best_spread_overlap_autocorr_adjusted_sharpe": max(
            (_number(row.get("spread_overlap_autocorr_adjusted_sharpe")) for row in leaderboard),
            default=0.0,
        ),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _empty_spread_metrics() -> dict[str, float]:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "overlap_autocorr_adjusted_sharpe": 0.0,
        "overlap_newey_west_t_stat_mean": 0.0,
    }


def _spread_classification_rank(classification: str) -> int:
    order = {
        "beta_hedged_spread_candidate": 0,
        "beta_hedged_spread_research_lead": 1,
        "weak_or_unproven_spread": 2,
    }
    return order.get(classification, _classification_rank(classification))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
