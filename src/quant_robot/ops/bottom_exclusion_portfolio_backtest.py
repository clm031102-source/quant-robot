from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.research.overlap import overlap_aware_return_stats


STAGE = "bottom_exclusion_portfolio_backtest"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def run_bottom_exclusion_portfolio_backtest(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    bars: pd.DataFrame | None = None,
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
    target_gross_exposure: float = 1.0,
    periods_per_year: float | None = None,
    min_positive_relative_fold_rate: float = 0.6,
    min_overlap_adjusted_sharpe: float = 0.5,
    max_drawdown_limit: float | None = 0.5,
) -> dict[str, Any]:
    if bottom_quantile <= 0.0 or bottom_quantile >= 1.0:
        raise ValueError("bottom_quantile must be greater than 0 and less than 1")
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    if holding_period < 1:
        raise ValueError("holding_period must be at least 1")
    if portfolio_value <= 0.0:
        raise ValueError("portfolio_value must be positive")
    if target_gross_exposure <= 0.0 or target_gross_exposure > 1.0:
        raise ValueError("target_gross_exposure must be greater than 0 and at most 1")
    if max_participation_rate is not None and max_participation_rate <= 0.0:
        raise ValueError("max_participation_rate must be positive when provided")
    if min_entry_amount is not None and min_entry_amount < 0.0:
        raise ValueError("min_entry_amount must be non-negative when provided")
    if max_drawdown_limit is not None and max_drawdown_limit <= 0.0:
        raise ValueError("max_drawdown_limit must be positive when provided")

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
        periods_per_year=resolved_periods_per_year,
        min_positive_relative_fold_rate=min_positive_relative_fold_rate,
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
            "periods_per_year": resolved_periods_per_year,
            "min_positive_relative_fold_rate": min_positive_relative_fold_rate,
            "min_overlap_adjusted_sharpe": min_overlap_adjusted_sharpe,
            "max_drawdown_limit": max_drawdown_limit,
        },
        "summary": _summary(leaderboard, merged),
        "leaderboard": leaderboard,
        "diagnostic_only": False,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_bottom_exclusion_portfolio_markdown(result)
    return result


def write_bottom_exclusion_portfolio_backtest(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "bottom_exclusion_portfolio_backtest.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "bottom_exclusion_portfolio_backtest.md").write_text(
        render_bottom_exclusion_portfolio_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(output_path / "leaderboard.csv", index=False)


def render_bottom_exclusion_portfolio_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    thresholds = _dict(result.get("thresholds"))
    lines = [
        "# Bottom-Exclusion Portfolio Backtest",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source report: {result.get('source_report') or 'unknown'}",
        f"- Bottom quantile: {_number(thresholds.get('bottom_quantile')):.2f}",
        f"- Rebalance interval: {thresholds.get('rebalance_interval')}",
        f"- Holding period: {thresholds.get('holding_period')}",
        f"- Cost bps: {_number(thresholds.get('cost_bps')):.2f}",
        f"- Market impact bps: {_number(thresholds.get('market_impact_bps')):.2f}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Costed risk-filter candidates: {summary.get('costed_risk_filter_candidates', 0)}",
        f"- Capacity-limited candidates: {summary.get('capacity_limited_risk_filter_candidates', 0)}",
        f"- Research leads: {summary.get('research_lead_risk_filters', 0)}",
        f"- Weak or unproven: {summary.get('weak_or_unproven_risk_filters', 0)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "- {factor}: {classification}, total={total:.4f}, bench={bench:.4f}, relative={relative:.4f}, "
            "gross={gross:.4f}, sharpe={sharpe:.4f}, overlap={overlap:.4f}, dd={dd:.4f}, "
            "win={win:.4f}, folds+={fold_rate:.2f}, cap_limited={cap}".format(
                factor=row.get("factor_name"),
                classification=row.get("classification"),
                total=_number(row.get("total_return")),
                bench=_number(row.get("benchmark_total_return")),
                relative=_number(row.get("relative_return")),
                gross=_number(row.get("gross_total_return")),
                sharpe=_number(row.get("sharpe")),
                overlap=_number(row.get("overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("max_drawdown")),
                win=_number(row.get("win_rate")),
                fold_rate=_number(row.get("positive_relative_fold_rate")),
                cap=int(_number(row.get("capacity_limited_trades"))),
            )
        )
    return "\n".join(lines) + "\n"


def _prepare_factors(factors: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(factors, required, "factors")
    frame = factors[required].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    return frame


def _prepare_labels(labels: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "forward_return", "entry_date", "exit_date"]
    _require_columns(labels, required, "labels")
    frame = labels.copy()
    if "horizon" not in frame.columns:
        frame["horizon"] = 0
    if "execution_lag" not in frame.columns:
        frame["execution_lag"] = 0
    frame = frame[required + ["horizon", "execution_lag"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.date
    frame["exit_date"] = pd.to_datetime(frame["exit_date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["forward_return"] = pd.to_numeric(frame["forward_return"], errors="coerce")
    frame["horizon"] = pd.to_numeric(frame["horizon"], errors="coerce").fillna(0).astype(int)
    frame["execution_lag"] = pd.to_numeric(frame["execution_lag"], errors="coerce").fillna(0).astype(int)
    return frame


def _merge_inputs(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    return factors.merge(labels, on=["date", "asset_id", "market"], how="inner").dropna(
        subset=["factor_value", "forward_return"]
    ).reset_index(drop=True)


def _attach_entry_amount(merged: pd.DataFrame, bars: pd.DataFrame | None) -> pd.DataFrame:
    frame = merged.copy()
    if bars is None or bars.empty or "amount" not in bars.columns:
        frame["entry_amount"] = 0.0
        return frame
    required = ["date", "asset_id", "market", "amount"]
    _require_columns(bars, required, "bars")
    amounts = bars[required].copy()
    amounts["date"] = pd.to_datetime(amounts["date"]).dt.date
    amounts["asset_id"] = amounts["asset_id"].astype(str)
    amounts["market"] = amounts["market"].astype(str).str.upper()
    amounts["amount"] = pd.to_numeric(amounts["amount"], errors="coerce").fillna(0.0)
    amounts = amounts.rename(columns={"date": "entry_date", "amount": "entry_amount"})
    frame = frame.merge(amounts, on=["entry_date", "asset_id", "market"], how="left")
    frame["entry_amount"] = pd.to_numeric(frame["entry_amount"], errors="coerce").fillna(0.0)
    return frame


def _filter_min_entry_amount(frame: pd.DataFrame, min_entry_amount: float | None) -> pd.DataFrame:
    if min_entry_amount is None or frame.empty:
        return frame.reset_index(drop=True)
    return frame[pd.to_numeric(frame["entry_amount"], errors="coerce").fillna(0.0) >= float(min_entry_amount)].reset_index(drop=True)


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
    periods_per_year: float,
    min_positive_relative_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
) -> list[dict[str, Any]]:
    if merged.empty:
        return []
    rows = []
    group_keys = ["market", "factor_name", "horizon", "execution_lag"]
    for key, group in merged.groupby(group_keys, sort=True):
        market, factor_name, horizon, execution_lag = key
        kept_mask = _kept_mask(group, bottom_quantile=bottom_quantile)
        strategy = _basket_stats(
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
        folds = _fold_summary(strategy["curve"], benchmark["curve"], periods_per_year=periods_per_year)
        positive_fold_rate = _positive_relative_fold_rate(folds)
        relative_return = strategy["metrics"]["total_return"] - benchmark["metrics"]["total_return"]
        classification = _classification(
            total_return=strategy["metrics"]["total_return"],
            relative_return=relative_return,
            overlap_sharpe=strategy["metrics"]["overlap_autocorr_adjusted_sharpe"],
            max_drawdown=strategy["metrics"]["max_drawdown"],
            positive_relative_fold_rate=positive_fold_rate,
            capacity_limited_trades=strategy["metrics"]["capacity_limited_trades"],
            min_positive_relative_fold_rate=min_positive_relative_fold_rate,
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
                    "total_return": strategy["metrics"]["total_return"],
                    "gross_total_return": strategy["metrics"]["gross_total_return"],
                    "benchmark_total_return": benchmark["metrics"]["total_return"],
                    "benchmark_gross_total_return": benchmark["metrics"]["gross_total_return"],
                    "relative_return": relative_return,
                    "annualized_return": strategy["metrics"]["annualized_return"],
                    "sharpe": strategy["metrics"]["sharpe"],
                    "overlap_autocorr_adjusted_sharpe": strategy["metrics"]["overlap_autocorr_adjusted_sharpe"],
                    "overlap_newey_west_t_stat_mean": strategy["metrics"]["overlap_newey_west_t_stat_mean"],
                    "max_drawdown": strategy["metrics"]["max_drawdown"],
                    "win_rate": strategy["metrics"]["win_rate"],
                    "average_holdings": strategy["metrics"]["average_holdings"],
                    "benchmark_average_holdings": benchmark["metrics"]["average_holdings"],
                    "turnover": strategy["metrics"]["turnover"],
                    "avg_cost_rate": strategy["metrics"]["avg_cost_rate"],
                    "max_cost_rate": strategy["metrics"]["max_cost_rate"],
                    "avg_participation_rate": strategy["metrics"]["avg_participation_rate"],
                    "max_participation_rate": strategy["metrics"]["max_participation_rate"],
                    "capacity_limited_trades": strategy["metrics"]["capacity_limited_trades"],
                    "folds": folds,
                    "positive_relative_folds": sum(1 for row in folds if _number(row.get("relative_return")) > 0.0),
                    "fold_count": len(folds),
                    "positive_relative_fold_rate": positive_fold_rate,
                }
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            _classification_rank(str(row.get("classification"))),
            -_number(row.get("relative_return")),
            -_number(row.get("overlap_autocorr_adjusted_sharpe")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _kept_mask(group: pd.DataFrame, *, bottom_quantile: float) -> pd.Series:
    ranked = group.sort_values(["date", "market", "factor_value", "asset_id"], ascending=[True, True, True, True]).copy()
    signal_group = ["date", "market"]
    ranked["_rank_order"] = ranked.groupby(signal_group).cumcount() + 1
    ranked["_group_size"] = ranked.groupby(signal_group)["asset_id"].transform("size")
    bottom_count = (ranked["_group_size"] * bottom_quantile).apply(math.floor).astype(int).clip(lower=1)
    upper = (ranked["_group_size"] - 1).clip(lower=1)
    ranked["_bottom_count"] = bottom_count.where(bottom_count <= upper, upper)
    kept = ranked["_rank_order"] > ranked["_bottom_count"]
    mask = pd.Series(False, index=group.index)
    mask.loc[ranked.index] = kept.to_numpy()
    return mask


def _basket_stats(
    group: pd.DataFrame,
    selected_mask: pd.Series,
    *,
    holding_period: int,
    rebalance_interval: int,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
    portfolio_value: float,
    target_gross_exposure: float,
    periods_per_year: float,
) -> dict[str, Any]:
    selected = group.loc[selected_mask].copy()
    if selected.empty:
        curve = pd.DataFrame(columns=["date", "period_return", "gross_period_return", "equity"])
        return {"curve": curve, "metrics": _empty_metrics()}
    sleeve_scale = 1.0 if holding_period <= 1 else min(float(rebalance_interval) / float(holding_period), 1.0)
    signal_group = ["date", "market"]
    counts = selected.groupby(signal_group)["asset_id"].transform("count")
    selected["target_weight"] = float(target_gross_exposure) * sleeve_scale / counts
    selected["participation_rate"] = _participation_rate(selected["target_weight"], selected["entry_amount"], portfolio_value)
    selected["cost_rate"] = _cost_rate(
        selected["participation_rate"],
        cost_bps=cost_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
    )
    selected["capacity_limited"] = (
        False
        if max_participation_rate is None
        else selected["participation_rate"] > float(max_participation_rate)
    )
    selected["weighted_gross_return"] = selected["target_weight"] * selected["forward_return"]
    selected["weighted_return"] = selected["target_weight"] * (selected["forward_return"] - selected["cost_rate"])
    curve = (
        selected.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"), gross_period_return=("weighted_gross_return", "sum"))
        .rename(columns={"exit_date": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    curve["equity"] = (1.0 + curve["period_return"]).cumprod()
    metrics = summarize_returns(curve["period_return"], periods_per_year=periods_per_year)
    gross_metrics = summarize_returns(curve["gross_period_return"], periods_per_year=periods_per_year)
    overlap = overlap_aware_return_stats(
        curve["period_return"],
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    metrics.update({f"overlap_{key}": value for key, value in overlap.items() if key != "autocorrelations"})
    metrics["gross_total_return"] = gross_metrics["total_return"]
    metrics["average_holdings"] = float(selected.groupby(signal_group)["asset_id"].nunique().mean())
    metrics["turnover"] = float(selected.groupby(signal_group)["target_weight"].sum().mean())
    metrics["avg_cost_rate"] = float(selected["cost_rate"].mean())
    metrics["max_cost_rate"] = float(selected["cost_rate"].max())
    metrics["avg_participation_rate"] = float(selected["participation_rate"].mean())
    metrics["max_participation_rate"] = float(selected["participation_rate"].max())
    metrics["capacity_limited_trades"] = int(selected["capacity_limited"].sum())
    return {"curve": curve, "metrics": metrics}


def _fold_summary(strategy_curve: pd.DataFrame, benchmark_curve: pd.DataFrame, *, periods_per_year: float) -> list[dict[str, Any]]:
    if strategy_curve.empty or benchmark_curve.empty:
        return []
    strategy = strategy_curve[["date", "period_return"]].rename(columns={"period_return": "strategy_return"})
    benchmark = benchmark_curve[["date", "period_return"]].rename(columns={"period_return": "benchmark_return"})
    merged = strategy.merge(benchmark, on="date", how="outer").fillna(0.0).sort_values("date")
    merged["year"] = pd.to_datetime(merged["date"]).dt.year
    rows = []
    for year, group in merged.groupby("year", sort=True):
        strategy_metrics = summarize_returns(group["strategy_return"], periods_per_year=periods_per_year)
        benchmark_metrics = summarize_returns(group["benchmark_return"], periods_per_year=periods_per_year)
        rows.append(
            {
                "fold": str(year),
                "observations": int(len(group)),
                "total_return": strategy_metrics["total_return"],
                "benchmark_total_return": benchmark_metrics["total_return"],
                "relative_return": strategy_metrics["total_return"] - benchmark_metrics["total_return"],
                "sharpe": strategy_metrics["sharpe"],
                "max_drawdown": strategy_metrics["max_drawdown"],
                "win_rate": strategy_metrics["win_rate"],
            }
        )
    return _sanitize(rows)


def _positive_relative_fold_rate(folds: list[dict[str, Any]]) -> float:
    if not folds:
        return 0.0
    return float(sum(1 for row in folds if _number(row.get("relative_return")) > 0.0) / len(folds))


def _classification(
    *,
    total_return: float,
    relative_return: float,
    overlap_sharpe: float,
    max_drawdown: float,
    positive_relative_fold_rate: float,
    capacity_limited_trades: int,
    min_positive_relative_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
) -> str:
    positive_lead = (
        total_return > 0.0
        and relative_return > 0.0
        and positive_relative_fold_rate >= min_positive_relative_fold_rate
    )
    risk_quality_ok = overlap_sharpe >= min_overlap_adjusted_sharpe and (
        max_drawdown_limit is None or max_drawdown >= -float(max_drawdown_limit)
    )
    candidate = positive_lead and risk_quality_ok
    if candidate and capacity_limited_trades > 0:
        return "capacity_limited_risk_filter_candidate"
    if candidate:
        return "costed_risk_filter_candidate"
    if positive_lead:
        return "research_lead_risk_filter"
    return "weak_or_unproven_risk_filter"


def _participation_rate(target_weight: pd.Series, entry_amount: pd.Series, portfolio_value: float) -> pd.Series:
    amount = pd.to_numeric(entry_amount, errors="coerce").fillna(0.0)
    participation = abs(target_weight.astype(float)) * float(portfolio_value) / amount.where(amount > 0.0, math.inf)
    return participation.fillna(0.0).replace([math.inf, -math.inf], 0.0)


def _cost_rate(
    participation_rate: pd.Series,
    *,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
) -> pd.Series:
    base_bps = float(cost_bps)
    if market_impact_bps <= 0.0:
        impact_bps = pd.Series(0.0, index=participation_rate.index)
    elif max_participation_rate is not None:
        impact_bps = float(market_impact_bps) * (participation_rate / float(max_participation_rate)).clip(lower=0.0, upper=1.0)
    else:
        impact_bps = float(market_impact_bps) * participation_rate.clip(lower=0.0, upper=1.0)
    return 2.0 * (base_bps + impact_bps) / 10000.0


def _summary(leaderboard: list[dict[str, Any]], merged: pd.DataFrame) -> dict[str, Any]:
    classifications = [str(row.get("classification")) for row in leaderboard]
    return {
        "input_rows": int(len(merged)),
        "cases": len(leaderboard),
        "costed_risk_filter_candidates": classifications.count("costed_risk_filter_candidate"),
        "capacity_limited_risk_filter_candidates": classifications.count("capacity_limited_risk_filter_candidate"),
        "research_lead_risk_filters": classifications.count("research_lead_risk_filter"),
        "weak_or_unproven_risk_filters": classifications.count("weak_or_unproven_risk_filter"),
        "best_total_return": max((_number(row.get("total_return")) for row in leaderboard), default=0.0),
        "best_relative_return": max((_number(row.get("relative_return")) for row in leaderboard), default=0.0),
        "best_overlap_autocorr_adjusted_sharpe": max(
            (_number(row.get("overlap_autocorr_adjusted_sharpe")) for row in leaderboard),
            default=0.0,
        ),
    }


def _empty_metrics() -> dict[str, float | int]:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "annualized_volatility": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "gross_total_return": 0.0,
        "overlap_autocorr_adjusted_sharpe": 0.0,
        "overlap_newey_west_t_stat_mean": 0.0,
        "average_holdings": 0.0,
        "turnover": 0.0,
        "avg_cost_rate": 0.0,
        "max_cost_rate": 0.0,
        "avg_participation_rate": 0.0,
        "max_participation_rate": 0.0,
        "capacity_limited_trades": 0,
    }


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _classification_rank(classification: str) -> int:
    order = {
        "costed_risk_filter_candidate": 0,
        "capacity_limited_risk_filter_candidate": 1,
        "research_lead_risk_filter": 2,
        "weak_or_unproven_risk_filter": 3,
    }
    return order.get(classification, 99)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
