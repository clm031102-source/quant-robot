from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.clean_technical_portfolio_diagnostic import overlap_metrics


STAGE = "shortlist_return_block_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
RETURN_COLUMN_CANDIDATES = (
    "period_return_variant",
    "period_return",
    "entry_cash_proxy_return",
    "roundtrip_cash_proxy_return",
    "overlay_return",
    "raw_return",
    "weighted_return",
)


def build_shortlist_return_block_audit(
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    *,
    return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    concentration_months: int = 3,
    max_best_month_log_share: float = 0.60,
    min_leave_one_year_annualized_return: float = 0.0,
    min_leave_one_year_overlap_sharpe: float = 0.0,
) -> dict[str, Any]:
    rows = []
    for candidate_name, source in return_sources.items():
        source_path, source_return_column, source_date_column = _normalise_source_spec(
            source,
            default_return_column=return_column,
            default_date_column=date_column,
        )
        returns, resolved_column = load_candidate_period_returns(
            source_path,
            return_column=source_return_column,
            date_column=source_date_column,
        )
        rows.append(
            summarize_return_blocks(
                returns,
                candidate_name=str(candidate_name),
                return_column=resolved_column,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
                concentration_months=concentration_months,
                max_best_month_log_share=max_best_month_log_share,
                min_leave_one_year_annualized_return=min_leave_one_year_annualized_return,
                min_leave_one_year_overlap_sharpe=min_leave_one_year_overlap_sharpe,
            )
        )
    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["annualized_return"]),
            -float(row["overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "return_column": return_column or "auto",
            "date_column": date_column,
            "periods_per_year": float(periods_per_year),
            "holding_period": int(holding_period),
            "concentration_months": int(concentration_months),
            "max_best_month_log_share": float(max_best_month_log_share),
            "min_leave_one_year_annualized_return": float(min_leave_one_year_annualized_return),
            "min_leave_one_year_overlap_sharpe": float(min_leave_one_year_overlap_sharpe),
        },
        "summary": {
            "candidate_count": int(len(rows)),
            "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
            "pass_candidate_count": int(sum(not row["blockers"] for row in rows)),
            "best_candidate": rows[0]["candidate_name"] if rows else None,
        },
        "rows": rows,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Block audits are pre-simulation robustness checks only; final holdout remains sealed.",
        },
    }


def _normalise_source_spec(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    default_return_column: str | None,
    default_date_column: str,
) -> tuple[str | Path | pd.DataFrame, str | None, str]:
    if isinstance(source, Mapping) and not isinstance(source, pd.DataFrame):
        path = source.get("path")
        if path is None:
            raise ValueError("source spec missing path")
        return (
            path,
            str(source.get("return_column")) if source.get("return_column") else default_return_column,
            str(source.get("date_column") or default_date_column),
        )
    return source, default_return_column, default_date_column


def load_candidate_period_returns(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str | None = None,
    date_column: str = "date",
) -> tuple[pd.DataFrame, str]:
    frame = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(Path(source))
    if date_column not in frame:
        raise ValueError(f"return source missing date column: {date_column}")
    resolved_return_column = _resolve_return_column(frame, return_column=return_column)
    working = frame[[date_column, resolved_return_column]].copy()
    working["date"] = pd.to_datetime(working[date_column], errors="coerce")
    working["period_return"] = pd.to_numeric(working[resolved_return_column], errors="coerce").fillna(0.0)
    working = working.dropna(subset=["date"])
    if working.empty:
        return pd.DataFrame(columns=["date", "period_return"]), resolved_return_column
    grouped = (
        working.groupby("date", as_index=False)["period_return"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )
    return grouped, resolved_return_column


def summarize_return_blocks(
    period_returns: pd.DataFrame,
    *,
    candidate_name: str,
    return_column: str = "period_return",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    concentration_months: int = 3,
    max_best_month_log_share: float = 0.60,
    min_leave_one_year_annualized_return: float = 0.0,
    min_leave_one_year_overlap_sharpe: float = 0.0,
) -> dict[str, Any]:
    returns = _period_return_series(period_returns)
    metrics = _metric_pack(returns, periods_per_year=periods_per_year, holding_period=holding_period)
    by_year = _compound_by_period(returns, "Y")
    by_month = _compound_by_period(returns, "M")
    leave_one_year = _leave_one_year_metrics(
        returns,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    concentration = _month_concentration(
        returns,
        top_months=concentration_months,
    )
    blockers = _blockers(
        metrics,
        leave_one_year=leave_one_year,
        concentration=concentration,
        max_best_month_log_share=max_best_month_log_share,
        min_leave_one_year_annualized_return=min_leave_one_year_annualized_return,
        min_leave_one_year_overlap_sharpe=min_leave_one_year_overlap_sharpe,
    )
    return _sanitize(
        {
            "candidate_name": candidate_name,
            "return_column": return_column,
            "period_count": int(len(returns)),
            "date_start": _date_value(returns.index.min()) if len(returns) else None,
            "date_end": _date_value(returns.index.max()) if len(returns) else None,
            **metrics,
            "year_count": int(len(by_year)),
            "best_year": _period_extreme(by_year, largest=True),
            "worst_year": _period_extreme(by_year, largest=False),
            "best_month": _period_extreme(by_month, largest=True),
            "worst_month": _period_extreme(by_month, largest=False),
            **leave_one_year,
            **concentration,
            "blockers": blockers,
        }
    )


def write_shortlist_return_block_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(audit)
    (output / "shortlist_return_block_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "shortlist_return_block_audit_rows.csv",
        index=False,
    )


def _resolve_return_column(frame: pd.DataFrame, *, return_column: str | None) -> str:
    if return_column:
        if return_column not in frame:
            raise ValueError(f"return source missing return column: {return_column}")
        return return_column
    for candidate in RETURN_COLUMN_CANDIDATES:
        if candidate in frame:
            return candidate
    raise ValueError(
        "return source missing a supported return column: "
        + ", ".join(RETURN_COLUMN_CANDIDATES)
    )


def _period_return_series(period_returns: pd.DataFrame) -> pd.Series:
    required = ["date", "period_return"]
    missing = [column for column in required if column not in period_returns]
    if missing:
        raise ValueError(f"period_returns missing columns: {', '.join(missing)}")
    frame = period_returns[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["period_return"] = pd.to_numeric(frame["period_return"], errors="coerce").fillna(0.0)
    frame = frame.dropna(subset=["date"]).sort_values("date")
    if frame.empty:
        return pd.Series(dtype=float)
    return pd.Series(frame["period_return"].to_numpy(dtype=float), index=pd.DatetimeIndex(frame["date"]))


def _metric_pack(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, float]:
    metrics = summarize_returns(returns.reset_index(drop=True), periods_per_year=periods_per_year)
    metrics.update(
        overlap_metrics(
            returns.reset_index(drop=True),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
    )
    keys = (
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "sharpe",
        "overlap_autocorr_adjusted_sharpe",
        "overlap_newey_west_t_stat_mean",
        "max_drawdown",
        "win_rate",
    )
    return {key: _number(metrics.get(key)) for key in keys}


def _leave_one_year_metrics(
    returns: pd.Series,
    *,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    if returns.empty:
        return {
            "leave_one_year_min_annualized_return": 0.0,
            "leave_one_year_min_overlap_sharpe": 0.0,
            "leave_one_year_worst_removed_year": None,
        }
    years = sorted(pd.DatetimeIndex(returns.index).year.unique())
    rows = []
    for year in years:
        kept = returns[pd.DatetimeIndex(returns.index).year != int(year)]
        if kept.empty:
            continue
        metrics = _metric_pack(kept, periods_per_year=periods_per_year, holding_period=holding_period)
        rows.append(
            {
                "removed_year": int(year),
                "annualized_return": metrics["annualized_return"],
                "overlap_autocorr_adjusted_sharpe": metrics["overlap_autocorr_adjusted_sharpe"],
                "total_return": metrics["total_return"],
                "max_drawdown": metrics["max_drawdown"],
            }
        )
    if not rows:
        return {
            "leave_one_year_min_annualized_return": 0.0,
            "leave_one_year_min_overlap_sharpe": 0.0,
            "leave_one_year_worst_removed_year": None,
        }
    worst_ann = min(rows, key=lambda row: row["annualized_return"])
    worst_overlap = min(rows, key=lambda row: row["overlap_autocorr_adjusted_sharpe"])
    return {
        "leave_one_year_min_annualized_return": _number(worst_ann["annualized_return"]),
        "leave_one_year_worst_removed_year": int(worst_ann["removed_year"]),
        "leave_one_year_min_overlap_sharpe": _number(worst_overlap["overlap_autocorr_adjusted_sharpe"]),
        "leave_one_year_worst_overlap_removed_year": int(worst_overlap["removed_year"]),
    }


def _month_concentration(returns: pd.Series, *, top_months: int) -> dict[str, float]:
    if returns.empty:
        return {
            "best_month_log_share_of_total": 0.0,
            "top_month_count_for_concentration": int(top_months),
        }
    frame = pd.DataFrame({"date": pd.DatetimeIndex(returns.index), "return": returns.to_numpy(dtype=float)})
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    frame["log_return"] = np.log1p(frame["return"].clip(lower=-0.999999))
    month_logs = frame.groupby("month")["log_return"].sum().sort_values(ascending=False)
    total_log = float(frame["log_return"].sum())
    if total_log <= 0.0 or month_logs.empty:
        share = 0.0
    else:
        share = float(month_logs.head(int(top_months)).sum() / total_log)
    return {
        "best_month_log_share_of_total": _number(share),
        "top_month_count_for_concentration": int(top_months),
    }


def _compound_by_period(returns: pd.Series, period: str) -> pd.Series:
    if returns.empty:
        return pd.Series(dtype=float)
    frame = pd.DataFrame({"date": pd.DatetimeIndex(returns.index), "return": returns.to_numpy(dtype=float)})
    frame["period"] = frame["date"].dt.to_period(period).astype(str)
    return frame.groupby("period")["return"].apply(lambda values: float((1.0 + values).prod() - 1.0))


def _period_extreme(values: pd.Series, *, largest: bool) -> dict[str, Any] | None:
    if values.empty:
        return None
    period = values.idxmax() if largest else values.idxmin()
    return {"period": str(period), "return": _number(values.loc[period])}


def _blockers(
    metrics: dict[str, float],
    *,
    leave_one_year: dict[str, Any],
    concentration: dict[str, float],
    max_best_month_log_share: float,
    min_leave_one_year_annualized_return: float,
    min_leave_one_year_overlap_sharpe: float,
) -> list[str]:
    blockers = []
    if metrics["total_return"] <= 0.0:
        blockers.append("non_positive_total_return")
    if metrics["annualized_return"] <= 0.0:
        blockers.append("non_positive_annualized_return")
    if leave_one_year["leave_one_year_min_annualized_return"] <= min_leave_one_year_annualized_return:
        blockers.append("leave_one_year_annualized_return_below_min")
    if leave_one_year["leave_one_year_min_overlap_sharpe"] < min_leave_one_year_overlap_sharpe:
        blockers.append("weak_overlap_when_year_removed")
    if concentration["best_month_log_share_of_total"] > max_best_month_log_share:
        blockers.append("best_months_contribution_too_high")
    return blockers


def _date_value(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


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
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _number(value)
    if isinstance(value, float):
        return _number(value)
    return value
