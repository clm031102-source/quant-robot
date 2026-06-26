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
    _fold_summary,
    _kept_mask,
    _merge_inputs,
    _number,
    _positive_relative_fold_rate,
    _prepare_factors,
    _prepare_labels,
    _sanitize,
)


STAGE = "dynamic_cash_overlay_backtest"


def run_dynamic_cash_overlay_backtest(
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
    min_signal_date_coverage: float = 0.2,
    min_positive_relative_fold_rate: float = 0.6,
    min_overlap_adjusted_sharpe: float = 0.5,
    max_drawdown_limit: float | None = 0.5,
) -> dict[str, Any]:
    if target_gross_exposure <= 0.0 or target_gross_exposure > 1.0:
        raise ValueError("target_gross_exposure must be greater than 0 and at most 1")
    if risk_off_exposure < 0.0 or risk_off_exposure > target_gross_exposure:
        raise ValueError("risk_off_exposure must be between 0 and target_gross_exposure")
    if market_state_lookback < 1:
        raise ValueError("market_state_lookback must be positive")

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
    leaderboard = _build_dynamic_leaderboard(
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
        date_exposure=date_exposure,
        min_signal_date_coverage=min_signal_date_coverage,
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
            "risk_off_exposure": risk_off_exposure,
            "market_state_lookback": market_state_lookback,
            "periods_per_year": resolved_periods_per_year,
            "min_signal_date_coverage": min_signal_date_coverage,
            "min_positive_relative_fold_rate": min_positive_relative_fold_rate,
            "min_overlap_adjusted_sharpe": min_overlap_adjusted_sharpe,
            "max_drawdown_limit": max_drawdown_limit,
        },
        "summary": _summary(leaderboard, merged, market_state),
        "leaderboard": leaderboard,
        "market_state": _sanitize(market_state.to_dict("records")),
        "diagnostic_only": False,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_dynamic_cash_overlay_markdown(result)
    return result


def write_dynamic_cash_overlay_backtest(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "dynamic_cash_overlay_backtest.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "dynamic_cash_overlay_backtest.md").write_text(
        render_dynamic_cash_overlay_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(output_path / "leaderboard.csv", index=False)
    pd.DataFrame(result.get("market_state", [])).to_csv(output_path / "market_state.csv", index=False)


def render_dynamic_cash_overlay_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    thresholds = _dict(result.get("thresholds"))
    lines = [
        "# Dynamic Cash Overlay Backtest",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source report: {result.get('source_report') or 'unknown'}",
        f"- Market-state lookback: {thresholds.get('market_state_lookback')}",
        f"- Target gross exposure: {_number(thresholds.get('target_gross_exposure')):.2f}",
        f"- Risk-off exposure: {_number(thresholds.get('risk_off_exposure')):.2f}",
        f"- Risk-on rate: {_number(summary.get('risk_on_rate')):.2f}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Dynamic cash overlay candidates: {summary.get('dynamic_cash_overlay_candidates', 0)}",
        f"- Research leads: {summary.get('research_leads', 0)}",
        f"- Weak or unproven: {summary.get('weak_or_unproven', 0)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "- {factor}: {classification}, dyn_total={dyn_total:.4f}, static_total={static_total:.4f}, "
            "dyn_rel={dyn_rel:.4f}, dyn_overlap={dyn_overlap:.4f}, dyn_dd={dyn_dd:.4f}, "
            "static_dd={static_dd:.4f}, coverage={coverage:.2f}, folds+={fold_rate:.2f}".format(
                factor=row.get("factor_name"),
                classification=row.get("classification"),
                dyn_total=_number(row.get("dynamic_total_return")),
                static_total=_number(row.get("static_total_return")),
                dyn_rel=_number(row.get("dynamic_relative_return")),
                dyn_overlap=_number(row.get("dynamic_overlap_autocorr_adjusted_sharpe")),
                dyn_dd=_number(row.get("dynamic_max_drawdown")),
                static_dd=_number(row.get("static_max_drawdown")),
                coverage=_number(row.get("signal_date_coverage")),
                fold_rate=_number(row.get("dynamic_positive_relative_fold_rate")),
            )
        )
    return "\n".join(lines) + "\n"


def _build_dynamic_leaderboard(
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
    date_exposure: dict[Any, float],
    min_signal_date_coverage: float,
    min_positive_relative_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
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
        folds = _fold_summary(dynamic_strategy["curve"], dynamic_benchmark["curve"], periods_per_year=periods_per_year)
        positive_fold_rate = _positive_relative_fold_rate(folds)
        dynamic_relative = dynamic_strategy["metrics"]["total_return"] - dynamic_benchmark["metrics"]["total_return"]
        coverage = _signal_date_coverage(group, date_exposure)
        classification = _classify_dynamic(
            metrics=dynamic_strategy["metrics"],
            relative_return=dynamic_relative,
            positive_relative_fold_rate=positive_fold_rate,
            signal_date_coverage=coverage,
            min_signal_date_coverage=min_signal_date_coverage,
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
                    "signal_date_coverage": coverage,
                    "dynamic_total_return": dynamic_strategy["metrics"]["total_return"],
                    "static_total_return": static_strategy["metrics"]["total_return"],
                    "dynamic_benchmark_total_return": dynamic_benchmark["metrics"]["total_return"],
                    "dynamic_relative_return": dynamic_relative,
                    "dynamic_sharpe": dynamic_strategy["metrics"]["sharpe"],
                    "dynamic_overlap_autocorr_adjusted_sharpe": dynamic_strategy["metrics"]["overlap_autocorr_adjusted_sharpe"],
                    "dynamic_max_drawdown": dynamic_strategy["metrics"]["max_drawdown"],
                    "static_max_drawdown": static_strategy["metrics"]["max_drawdown"],
                    "dynamic_win_rate": dynamic_strategy["metrics"]["win_rate"],
                    "dynamic_turnover": dynamic_strategy["metrics"]["turnover"],
                    "dynamic_capacity_limited_trades": dynamic_strategy["metrics"]["capacity_limited_trades"],
                    "dynamic_positive_relative_fold_rate": positive_fold_rate,
                    "dynamic_positive_relative_folds": sum(1 for row in folds if _number(row.get("relative_return")) > 0.0),
                    "fold_count": len(folds),
                    "folds": folds,
                }
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            _dynamic_classification_rank(str(row.get("classification"))),
            -_number(row.get("dynamic_overlap_autocorr_adjusted_sharpe")),
            -_number(row.get("dynamic_relative_return")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _market_state_frame(
    bars: pd.DataFrame,
    *,
    lookback: int,
    target_gross_exposure: float,
    risk_off_exposure: float,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    _require_columns(bars, required, "bars")
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.dropna(subset=["adj_close"]).sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["asset_return"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change().fillna(0.0)
    curve = (
        frame.groupby("date", as_index=False)["asset_return"]
        .mean()
        .rename(columns={"asset_return": "market_return"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    curve["market_equity"] = (1.0 + curve["market_return"]).cumprod()
    curve["market_momentum"] = curve["market_equity"] / curve["market_equity"].shift(lookback) - 1.0
    curve["risk_on"] = curve["market_momentum"] > 0.0
    curve["dynamic_exposure"] = curve["risk_on"].map(lambda allowed: target_gross_exposure if bool(allowed) else risk_off_exposure)
    return curve[["date", "market_return", "market_equity", "market_momentum", "risk_on", "dynamic_exposure"]]


def _date_exposure(market_state: pd.DataFrame) -> dict[Any, float]:
    return {
        row.date: float(row.dynamic_exposure)
        for row in market_state.itertuples(index=False)
    }


def _signal_date_coverage(group: pd.DataFrame, date_exposure: dict[Any, float]) -> float:
    dates = sorted(pd.to_datetime(group["date"]).dt.date.unique())
    if not dates:
        return 0.0
    active = sum(1 for value in dates if _number(date_exposure.get(value)) > 0.0)
    return float(active / len(dates))


def _classify_dynamic(
    *,
    metrics: dict[str, Any],
    relative_return: float,
    positive_relative_fold_rate: float,
    signal_date_coverage: float,
    min_signal_date_coverage: float,
    min_positive_relative_fold_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_limit: float | None,
) -> str:
    positive_lead = (
        _number(metrics.get("total_return")) > 0.0
        and relative_return > 0.0
        and positive_relative_fold_rate >= min_positive_relative_fold_rate
    )
    risk_quality_ok = _number(metrics.get("overlap_autocorr_adjusted_sharpe")) >= min_overlap_adjusted_sharpe and (
        max_drawdown_limit is None or _number(metrics.get("max_drawdown")) >= -float(max_drawdown_limit)
    )
    coverage_ok = signal_date_coverage >= min_signal_date_coverage
    if positive_lead and risk_quality_ok and coverage_ok:
        return "dynamic_cash_overlay_candidate"
    if positive_lead and coverage_ok:
        return "dynamic_cash_overlay_research_lead"
    return "weak_or_unproven_dynamic_overlay"


def _summary(leaderboard: list[dict[str, Any]], merged: pd.DataFrame, market_state: pd.DataFrame) -> dict[str, Any]:
    classifications = Counter(str(row.get("classification")) for row in leaderboard)
    risk_on = market_state["risk_on"] if "risk_on" in market_state else pd.Series(dtype=bool)
    return {
        "input_rows": int(len(merged)),
        "cases": len(leaderboard),
        "dynamic_cash_overlay_candidates": classifications.get("dynamic_cash_overlay_candidate", 0),
        "research_leads": classifications.get("dynamic_cash_overlay_research_lead", 0),
        "weak_or_unproven": classifications.get("weak_or_unproven_dynamic_overlay", 0),
        "risk_on_rate": float(risk_on.mean()) if len(risk_on) else 0.0,
        "market_state_rows": int(len(market_state)),
        "best_dynamic_total_return": max((_number(row.get("dynamic_total_return")) for row in leaderboard), default=0.0),
        "best_dynamic_overlap_autocorr_adjusted_sharpe": max(
            (_number(row.get("dynamic_overlap_autocorr_adjusted_sharpe")) for row in leaderboard),
            default=0.0,
        ),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _dynamic_classification_rank(classification: str) -> int:
    order = {
        "dynamic_cash_overlay_candidate": 0,
        "dynamic_cash_overlay_research_lead": 1,
        "weak_or_unproven_dynamic_overlay": 2,
    }
    return order.get(classification, _classification_rank(classification))


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
