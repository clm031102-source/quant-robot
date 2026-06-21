from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.bottom_exclusion_portfolio_backtest import (
    run_bottom_exclusion_portfolio_backtest,
)


STAGE = "bottom_exclusion_walk_forward"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def run_bottom_exclusion_walk_forward(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    source_report: str | None = None,
    rolling_train_days: int,
    rolling_test_days: int,
    rolling_step_days: int,
    min_accepted_folds: int = 2,
    bottom_quantile: float = 0.2,
    rebalance_interval: int = 1,
    holding_period: int = 1,
    cost_bps: float = 10.0,
    market_impact_bps: float = 20.0,
    max_participation_rate: float | None = 0.01,
    min_entry_amount: float | None = None,
    portfolio_value: float = 1_000_000.0,
    target_gross_exposure: float = 1.0,
    min_positive_relative_fold_rate: float = 0.6,
    min_test_overlap_adjusted_sharpe: float = 0.5,
    max_test_drawdown_limit: float | None = 0.5,
) -> dict[str, Any]:
    _validate_rolling_args(rolling_train_days, rolling_test_days, rolling_step_days, min_accepted_folds)
    prepared_factors = _prepare_dates(factors, columns=("date",))
    prepared_labels = _prepare_dates(labels, columns=("date", "entry_date", "exit_date"))
    prepared_bars = _prepare_dates(bars, columns=("date",))
    folds = _rolling_folds(prepared_factors, prepared_labels, rolling_train_days, rolling_test_days, rolling_step_days)
    if not folds:
        raise ValueError("Rolling bottom-exclusion walk-forward requires enough dates for at least one fold")

    fold_rows: list[dict[str, Any]] = []
    for fold in folds:
        fold_rows.extend(
            _run_fold(
                prepared_factors,
                prepared_labels,
                prepared_bars,
                fold=fold,
                bottom_quantile=bottom_quantile,
                rebalance_interval=rebalance_interval,
                holding_period=holding_period,
                cost_bps=cost_bps,
                market_impact_bps=market_impact_bps,
                max_participation_rate=max_participation_rate,
                min_entry_amount=min_entry_amount,
                portfolio_value=portfolio_value,
                target_gross_exposure=target_gross_exposure,
                min_positive_relative_fold_rate=min_positive_relative_fold_rate,
                min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
                max_test_drawdown_limit=max_test_drawdown_limit,
            )
        )
    leaderboard = _rank_rows(_aggregate_rows(fold_rows, min_accepted_folds=min_accepted_folds))
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "rolling_train_days": rolling_train_days,
            "rolling_test_days": rolling_test_days,
            "rolling_step_days": rolling_step_days,
            "min_accepted_folds": min_accepted_folds,
            "bottom_quantile": bottom_quantile,
            "rebalance_interval": rebalance_interval,
            "holding_period": holding_period,
            "cost_bps": cost_bps,
            "market_impact_bps": market_impact_bps,
            "max_participation_rate": max_participation_rate,
            "min_entry_amount": min_entry_amount,
            "portfolio_value": portfolio_value,
            "target_gross_exposure": target_gross_exposure,
            "min_positive_relative_fold_rate": min_positive_relative_fold_rate,
            "min_test_overlap_adjusted_sharpe": min_test_overlap_adjusted_sharpe,
            "max_test_drawdown_limit": max_test_drawdown_limit,
        },
        "summary": _summary(leaderboard, fold_rows),
        "leaderboard": leaderboard,
        "folds": fold_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_bottom_exclusion_walk_forward_markdown(result)
    return result


def write_bottom_exclusion_walk_forward(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "bottom_exclusion_walk_forward.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "bottom_exclusion_walk_forward.md").write_text(
        render_bottom_exclusion_walk_forward_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(output_path / "walk_forward_leaderboard.csv", index=False)
    pd.DataFrame(result.get("folds", [])).to_csv(output_path / "walk_forward_folds.csv", index=False)


def render_bottom_exclusion_walk_forward_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    thresholds = _dict(result.get("thresholds"))
    lines = [
        "# Bottom-Exclusion Walk-Forward",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source report: {result.get('source_report') or 'unknown'}",
        f"- Train days: {thresholds.get('rolling_train_days')}",
        f"- Test days: {thresholds.get('rolling_test_days')}",
        f"- Step days: {thresholds.get('rolling_step_days')}",
        f"- Min accepted folds: {thresholds.get('min_accepted_folds')}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Accepted: {summary.get('accepted', 0)}",
        f"- Rejected: {summary.get('rejected', 0)}",
        f"- Fold rows: {summary.get('fold_rows', 0)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Leaderboard",
        "",
    ]
    for row in result.get("leaderboard", []):
        lines.append(
            "- {factor}: {status}, accepted_folds={accepted}/{folds}, mean_test_relative={relative:.4f}, "
            "mean_test_overlap={overlap:.4f}, worst_test_dd={dd:.4f}, cap_limited={cap}, reasons={reasons}".format(
                factor=row.get("factor_name"),
                status=row.get("validation_status"),
                accepted=int(_number(row.get("accepted_folds"))),
                folds=int(_number(row.get("folds"))),
                relative=_number(row.get("mean_test_relative_return")),
                overlap=_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
                dd=_number(row.get("worst_test_max_drawdown")),
                cap=int(_number(row.get("test_capacity_limited_trades"))),
                reasons=",".join(str(item) for item in row.get("rejection_reasons", []) or []),
            )
        )
    return "\n".join(lines) + "\n"


def _run_fold(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    fold: dict[str, Any],
    bottom_quantile: float,
    rebalance_interval: int,
    holding_period: int,
    cost_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
    min_entry_amount: float | None,
    portfolio_value: float,
    target_gross_exposure: float,
    min_positive_relative_fold_rate: float,
    min_test_overlap_adjusted_sharpe: float,
    max_test_drawdown_limit: float | None,
) -> list[dict[str, Any]]:
    train_factors = _slice_signal_dates(factors, fold["train_start_date"], fold["train_end_date"])
    test_factors = _slice_signal_dates(factors, fold["test_start_date"], fold["test_end_date"])
    train_labels = _slice_labels(labels, fold["train_start_date"], fold["train_end_date"])
    test_labels = _slice_labels(labels, fold["test_start_date"], fold["test_end_date"])
    common_kwargs = {
        "bottom_quantile": bottom_quantile,
        "rebalance_interval": rebalance_interval,
        "holding_period": holding_period,
        "cost_bps": cost_bps,
        "market_impact_bps": market_impact_bps,
        "max_participation_rate": max_participation_rate,
        "min_entry_amount": min_entry_amount,
        "portfolio_value": portfolio_value,
        "target_gross_exposure": target_gross_exposure,
        "min_positive_relative_fold_rate": min_positive_relative_fold_rate,
        "min_overlap_adjusted_sharpe": min_test_overlap_adjusted_sharpe,
        "max_drawdown_limit": max_test_drawdown_limit,
    }
    train_rows = run_bottom_exclusion_portfolio_backtest(
        train_factors,
        train_labels,
        bars,
        source_report=f"fold={fold['fold']} train",
        **common_kwargs,
    )["leaderboard"]
    test_rows = run_bottom_exclusion_portfolio_backtest(
        test_factors,
        test_labels,
        bars,
        source_report=f"fold={fold['fold']} test",
        **common_kwargs,
    )["leaderboard"]
    train_by_key = {_row_key(row): row for row in train_rows}
    test_by_key = {_row_key(row): row for row in test_rows}
    keys = sorted(set(train_by_key) | set(test_by_key))
    return [
        _fold_row(
            fold,
            train_by_key.get(key),
            test_by_key.get(key),
            min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
            max_test_drawdown_limit=max_test_drawdown_limit,
        )
        for key in keys
    ]


def _fold_row(
    fold: dict[str, Any],
    train: dict[str, Any] | None,
    test: dict[str, Any] | None,
    *,
    min_test_overlap_adjusted_sharpe: float,
    max_test_drawdown_limit: float | None,
) -> dict[str, Any]:
    source = test or train or {}
    reasons = []
    if train is None:
        reasons.append("train_not_completed")
    if test is None:
        reasons.append("test_not_completed")
    test_classification = str((test or {}).get("classification", "missing"))
    if test_classification != "costed_risk_filter_candidate":
        reasons.append("test_not_costed_risk_filter_candidate")
    if _number((test or {}).get("overlap_autocorr_adjusted_sharpe")) < min_test_overlap_adjusted_sharpe:
        reasons.append("test_overlap_adjusted_sharpe_below_min")
    if max_test_drawdown_limit is not None and _number((test or {}).get("max_drawdown")) < -abs(float(max_test_drawdown_limit)):
        reasons.append("test_drawdown_above_limit")
    if int(_number((test or {}).get("capacity_limited_trades"))) > 0:
        reasons.append("test_capacity_limited_trades_present")
    strict_violation = 1 if pd.to_datetime(fold["test_start_date"]).date() <= pd.to_datetime(fold["train_end_date"]).date() else 0
    return _sanitize(
        {
            "fold": fold["fold"],
            "market": source.get("market"),
            "factor_name": source.get("factor_name"),
            "horizon": source.get("horizon"),
            "execution_lag": source.get("execution_lag"),
            "train_start_date": fold["train_start_date"],
            "train_end_date": fold["train_end_date"],
            "test_start_date": fold["test_start_date"],
            "test_end_date": fold["test_end_date"],
            "strict_split_status": "pass" if strict_violation == 0 else "block",
            "strict_split_violations": strict_violation,
            "fold_status": "accepted" if not reasons and strict_violation == 0 else "rejected",
            "fold_rejection_reasons": reasons,
            "train_classification": (train or {}).get("classification", "missing"),
            "test_classification": test_classification,
            "train_total_return": _number((train or {}).get("total_return")),
            "test_total_return": _number((test or {}).get("total_return")),
            "train_relative_return": _number((train or {}).get("relative_return")),
            "test_relative_return": _number((test or {}).get("relative_return")),
            "train_overlap_autocorr_adjusted_sharpe": _number((train or {}).get("overlap_autocorr_adjusted_sharpe")),
            "test_overlap_autocorr_adjusted_sharpe": _number((test or {}).get("overlap_autocorr_adjusted_sharpe")),
            "train_max_drawdown": _number((train or {}).get("max_drawdown")),
            "test_max_drawdown": _number((test or {}).get("max_drawdown")),
            "train_win_rate": _number((train or {}).get("win_rate")),
            "test_win_rate": _number((test or {}).get("win_rate")),
            "train_average_holdings": _number((train or {}).get("average_holdings")),
            "test_average_holdings": _number((test or {}).get("average_holdings")),
            "train_capacity_limited_trades": int(_number((train or {}).get("capacity_limited_trades"))),
            "test_capacity_limited_trades": int(_number((test or {}).get("capacity_limited_trades"))),
        }
    )


def _aggregate_rows(rows: list[dict[str, Any]], *, min_accepted_folds: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("market")),
            str(row.get("factor_name")),
            int(_number(row.get("horizon"))),
            int(_number(row.get("execution_lag"))),
        )
        grouped.setdefault(key, []).append(row)
    aggregates = []
    for (market, factor_name, horizon, execution_lag), items in grouped.items():
        accepted_folds = sum(1 for row in items if row.get("fold_status") == "accepted")
        strict_violations = sum(int(_number(row.get("strict_split_violations"))) for row in items)
        reasons = _dedupe_reasons(items)
        if accepted_folds < min_accepted_folds:
            reasons.append("accepted_folds_below_min")
        if strict_violations > 0:
            reasons.append("strict_split_violation")
        aggregates.append(
            _sanitize(
                {
                    "market": market,
                    "factor_name": factor_name,
                    "horizon": horizon,
                    "execution_lag": execution_lag,
                    "validation_status": "accepted" if not reasons else "rejected",
                    "rejection_reasons": reasons,
                    "folds": len(items),
                    "accepted_folds": accepted_folds,
                    "rejected_folds": len(items) - accepted_folds,
                    "strict_split_status": "pass" if strict_violations == 0 else "block",
                    "strict_split_violations": strict_violations,
                    "mean_train_total_return": _mean(items, "train_total_return"),
                    "mean_test_total_return": _mean(items, "test_total_return"),
                    "mean_train_relative_return": _mean(items, "train_relative_return"),
                    "mean_test_relative_return": _mean(items, "test_relative_return"),
                    "mean_train_overlap_autocorr_adjusted_sharpe": _mean(
                        items,
                        "train_overlap_autocorr_adjusted_sharpe",
                    ),
                    "mean_test_overlap_autocorr_adjusted_sharpe": _mean(
                        items,
                        "test_overlap_autocorr_adjusted_sharpe",
                    ),
                    "worst_test_max_drawdown": min((_number(row.get("test_max_drawdown")) for row in items), default=0.0),
                    "mean_test_win_rate": _mean(items, "test_win_rate"),
                    "mean_test_average_holdings": _mean(items, "test_average_holdings"),
                    "test_capacity_limited_trades": sum(int(_number(row.get("test_capacity_limited_trades"))) for row in items),
                }
            )
        )
    return aggregates


def _rolling_folds(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    train_days: int,
    test_days: int,
    step_days: int,
) -> list[dict[str, Any]]:
    factor_dates = set(pd.to_datetime(factors["date"]).dt.date.unique())
    label_dates = set(pd.to_datetime(labels["date"]).dt.date.unique())
    dates = sorted(factor_dates & label_dates)
    limit = len(dates) - train_days - test_days + 1
    if limit <= 0:
        return []
    folds = []
    for fold_number, start in enumerate(range(0, limit, step_days), start=1):
        train_dates = dates[start : start + train_days]
        test_dates = dates[start + train_days : start + train_days + test_days]
        folds.append(
            {
                "fold": fold_number,
                "train_start_date": train_dates[0],
                "train_end_date": train_dates[-1],
                "test_start_date": test_dates[0],
                "test_end_date": test_dates[-1],
            }
        )
    return folds


def _slice_signal_dates(frame: pd.DataFrame, start: Any, end: Any) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date"]).dt.date
    start_date = pd.to_datetime(start).date()
    end_date = pd.to_datetime(end).date()
    return frame[(dates >= start_date) & (dates <= end_date)].reset_index(drop=True)


def _slice_labels(labels: pd.DataFrame, start: Any, end: Any) -> pd.DataFrame:
    start_date = pd.to_datetime(start).date()
    end_date = pd.to_datetime(end).date()
    signal_dates = pd.to_datetime(labels["date"]).dt.date
    entry_dates = pd.to_datetime(labels["entry_date"]).dt.date
    exit_dates = pd.to_datetime(labels["exit_date"]).dt.date
    mask = (
        (signal_dates >= start_date)
        & (signal_dates <= end_date)
        & (entry_dates >= start_date)
        & (exit_dates <= end_date)
    )
    return labels[mask].reset_index(drop=True)


def _prepare_dates(frame: pd.DataFrame, *, columns: tuple[str, ...]) -> pd.DataFrame:
    prepared = frame.copy()
    for column in columns:
        if column in prepared.columns:
            prepared[column] = pd.to_datetime(prepared[column]).dt.date
    return prepared


def _row_key(row: dict[str, Any]) -> tuple[str, str, int, int]:
    return (
        str(row.get("market")),
        str(row.get("factor_name")),
        int(_number(row.get("horizon"))),
        int(_number(row.get("execution_lag"))),
    )


def _rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            str(row.get("validation_status")) != "accepted",
            -_number(row.get("accepted_folds")),
            -_number(row.get("mean_test_relative_return")),
            -_number(row.get("mean_test_overlap_autocorr_adjusted_sharpe")),
            str(row.get("factor_name")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _summary(leaderboard: list[dict[str, Any]], fold_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(leaderboard),
        "accepted": sum(1 for row in leaderboard if row.get("validation_status") == "accepted"),
        "rejected": sum(1 for row in leaderboard if row.get("validation_status") == "rejected"),
        "folds": max((int(_number(row.get("folds"))) for row in leaderboard), default=0),
        "fold_rows": len(fold_rows),
    }


def _validate_rolling_args(train_days: int, test_days: int, step_days: int, min_accepted_folds: int) -> None:
    if train_days < 1 or test_days < 1 or step_days < 1:
        raise ValueError("rolling_train_days, rolling_test_days, and rolling_step_days must be positive")
    if min_accepted_folds < 1:
        raise ValueError("min_accepted_folds must be positive")


def _dedupe_reasons(rows: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for row in rows:
        if row.get("fold_status") == "accepted":
            continue
        for reason in row.get("fold_rejection_reasons", []) or []:
            text = str(reason)
            if text not in reasons:
                reasons.append(text)
    return reasons


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return sum(_number(row.get(key)) for row in rows) / len(rows) if rows else 0.0


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
