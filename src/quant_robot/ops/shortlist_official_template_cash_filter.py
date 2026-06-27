from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.dragon_tiger_pit_ic_prescreen import load_dragon_tiger_stock_day
from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks


STAGE = "shortlist_official_template_cash_filter"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
DEFAULT_CANDIDATES = ("dragon_hot_chase_20d", "dragon_net_buy_20d", "dragon_hot_sell_60d")
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)


@dataclass(frozen=True)
class DragonTigerCashFilterSpec:
    candidate_name: str
    lookback_days: int
    min_abs_pct_change: float | None = None
    net_buy_sign: int | None = None
    institutional: bool = False


DRAGON_TIGER_CASH_FILTER_SPECS: dict[str, DragonTigerCashFilterSpec] = {
    "dragon_hot_chase_20d": DragonTigerCashFilterSpec(
        candidate_name="dragon_hot_chase_20d",
        lookback_days=22,
        min_abs_pct_change=9.5,
        net_buy_sign=1,
    ),
    "dragon_net_buy_20d": DragonTigerCashFilterSpec(
        candidate_name="dragon_net_buy_20d",
        lookback_days=21,
        net_buy_sign=1,
    ),
    "dragon_inst_net_buy_20d": DragonTigerCashFilterSpec(
        candidate_name="dragon_inst_net_buy_20d",
        lookback_days=21,
        net_buy_sign=1,
        institutional=True,
    ),
    "dragon_hot_sell_60d": DragonTigerCashFilterSpec(
        candidate_name="dragon_hot_sell_60d",
        lookback_days=60,
        min_abs_pct_change=9.5,
        net_buy_sign=-1,
    ),
    "dragon_net_sell_60d": DragonTigerCashFilterSpec(
        candidate_name="dragon_net_sell_60d",
        lookback_days=60,
        net_buy_sign=-1,
    ),
}


def build_official_template_cash_filter_audit(
    *,
    template_period_returns: str | Path | pd.DataFrame,
    trades_source: str | Path | pd.DataFrame,
    dragon_tiger_source: str | Path | pd.DataFrame,
    candidates: Sequence[str] = DEFAULT_CANDIDATES,
    template_return_column: str = "period_return",
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    lookback_anchor_column: str = "available_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_unmatched_abs_contribution: float = 0.005,
    require_candidate_improvement: bool = False,
) -> dict[str, Any]:
    template = _load_template_returns(
        template_period_returns,
        return_column=template_return_column,
        date_column=date_column,
    )
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        entry_date_column=trade_entry_date_column,
        exit_date_column=trade_exit_date_column,
    )
    dragon = _load_dragon_tiger(dragon_tiger_source)
    base_metrics = _metrics(
        template,
        candidate_name="official_template_base",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    rows: list[dict[str, Any]] = []
    period_return_frames: dict[str, pd.DataFrame] = {}
    flag_rows: list[dict[str, Any]] = []
    specs = [_resolve_spec(candidate) for candidate in candidates]
    for spec in specs:
        flagged = _flag_trades(
            trades,
            dragon,
            spec=spec,
            entry_date_column=trade_entry_date_column,
            lookback_anchor_column=lookback_anchor_column,
        )
        candidate_returns, contribution_summary, flags_for_candidate = _project_to_template(
            template,
            flagged,
            candidate_name=f"cash_{spec.candidate_name}",
            trade_return_column=trade_return_column,
            exit_date_column=trade_exit_date_column,
        )
        period_return_frames[f"cash_{spec.candidate_name}"] = candidate_returns
        flag_rows.extend(flags_for_candidate)
        candidate_metrics = _metrics(
            candidate_returns,
            candidate_name=f"cash_{spec.candidate_name}",
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        metric_diffs = {
            key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key))
            for key in METRIC_KEYS
        }
        blockers = _blockers(
            candidate_metrics,
            base_metrics=base_metrics,
            contribution_summary=contribution_summary,
            max_unmatched_abs_contribution=max_unmatched_abs_contribution,
            require_candidate_improvement=require_candidate_improvement,
        )
        rows.append(
            {
                "candidate_name": f"cash_{spec.candidate_name}",
                "source_flag_name": spec.candidate_name,
                "lookback_days": int(spec.lookback_days),
                "min_abs_pct_change": spec.min_abs_pct_change,
                "net_buy_sign": spec.net_buy_sign,
                "institutional": bool(spec.institutional),
                **contribution_summary,
                "base_metrics": {key: base_metrics.get(key) for key in METRIC_KEYS},
                "candidate_metrics": {key: candidate_metrics.get(key) for key in METRIC_KEYS},
                "metric_diffs": metric_diffs,
                "blockers": blockers,
            }
        )
    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["metric_diffs"]["annualized_return"]),
            -float(row["candidate_metrics"]["overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "template_return_column": template_return_column,
                "trade_return_column": trade_return_column,
                "date_column": date_column,
                "trade_entry_date_column": trade_entry_date_column,
                "trade_exit_date_column": trade_exit_date_column,
                "lookback_anchor_column": lookback_anchor_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_unmatched_abs_contribution": float(max_unmatched_abs_contribution),
                "require_candidate_improvement": bool(require_candidate_improvement),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "template_date_count": int(len(template)),
                "trade_count": int(len(trades)),
                "dragon_tiger_event_count": int(len(dragon)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "base_metrics": base_metrics,
            "rows": rows,
            "flag_rows": flag_rows,
            "period_return_frames": {
                name: _frame_rows(frame)
                for name, frame in period_return_frames.items()
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Official-template projection is a calendar-safety audit, not final simulation evidence.",
            },
        }
    )


def write_official_template_cash_filter_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    period_return_frames = sanitized.pop("period_return_frames", {})
    (output / "official_template_cash_filter_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "official_template_cash_filter_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("flag_rows", [])).to_csv(
        output / "official_template_cash_filter_flag_rows.csv",
        index=False,
    )
    for candidate_name, rows in period_return_frames.items():
        safe_name = str(candidate_name).replace("/", "_").replace("\\", "_")
        pd.DataFrame(rows).to_csv(output / f"{safe_name}_official_template_period_returns.csv", index=False)


def _load_template_returns(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    missing = [column for column in (date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"template period returns missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    output["period_return"] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return output


def _load_trades(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    entry_date_column: str,
    exit_date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = ["asset_id", entry_date_column, exit_date_column, return_column]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output[entry_date_column] = pd.to_datetime(output[entry_date_column], errors="coerce")
    output[exit_date_column] = pd.to_datetime(output[exit_date_column], errors="coerce")
    output[return_column] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=["asset_id", entry_date_column, exit_date_column]).reset_index(drop=True)
    output["trade_id"] = np.arange(len(output), dtype=int)
    return output


def _load_dragon_tiger(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        frame = source.copy()
    else:
        path = Path(source)
        if path.is_dir():
            frame = load_dragon_tiger_stock_day(path, market="CN", start_year=2015, end_year=2025)
        else:
            frame = _read_frame(path)
    required = ["asset_id", "date", "available_date"]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Dragon-Tiger source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["available_date"] = pd.to_datetime(output["available_date"], errors="coerce")
    for column in (
        "top_list_event_count",
        "top_list_net_amount_sum",
        "top_list_abs_pct_change_max",
        "top_inst_net_buy_sum",
    ):
        if column not in output:
            output[column] = 0.0
        output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0.0)
    return output.dropna(subset=["asset_id", "date", "available_date"]).reset_index(drop=True)


def _resolve_spec(candidate_name: str) -> DragonTigerCashFilterSpec:
    if candidate_name not in DRAGON_TIGER_CASH_FILTER_SPECS:
        raise ValueError(
            f"unsupported Dragon-Tiger cash filter candidate: {candidate_name}. "
            f"Supported: {', '.join(sorted(DRAGON_TIGER_CASH_FILTER_SPECS))}"
        )
    return DRAGON_TIGER_CASH_FILTER_SPECS[candidate_name]


def _flag_trades(
    trades: pd.DataFrame,
    dragon: pd.DataFrame,
    *,
    spec: DragonTigerCashFilterSpec,
    entry_date_column: str,
    lookback_anchor_column: str,
) -> pd.DataFrame:
    if lookback_anchor_column not in dragon:
        raise ValueError(f"Dragon-Tiger source missing lookback anchor column: {lookback_anchor_column}")
    candidates = trades[["trade_id", "asset_id", entry_date_column]].merge(
        dragon,
        on="asset_id",
        how="inner",
        validate="many_to_many",
    )
    anchor = pd.to_datetime(candidates[lookback_anchor_column], errors="coerce")
    entry = pd.to_datetime(candidates[entry_date_column], errors="coerce")
    in_window = (anchor <= entry) & (anchor >= entry - pd.Timedelta(days=int(spec.lookback_days)))
    mask = in_window & (_num(candidates, "top_list_event_count") > 0.0)
    if spec.min_abs_pct_change is not None:
        mask &= _num(candidates, "top_list_abs_pct_change_max") >= float(spec.min_abs_pct_change)
    net_column = "top_inst_net_buy_sum" if spec.institutional else "top_list_net_amount_sum"
    if spec.net_buy_sign is not None:
        net_values = _num(candidates, net_column)
        mask &= net_values > 0.0 if spec.net_buy_sign > 0 else net_values < 0.0
    flagged_ids = candidates.loc[mask, "trade_id"].drop_duplicates()
    return trades[trades["trade_id"].isin(set(flagged_ids))].copy()


def _project_to_template(
    template: pd.DataFrame,
    flagged: pd.DataFrame,
    *,
    candidate_name: str,
    trade_return_column: str,
    exit_date_column: str,
) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    template_dates = set(pd.to_datetime(template["date"]))
    contributions = (
        flagged.assign(exit_date=pd.to_datetime(flagged[exit_date_column], errors="coerce"))
        .dropna(subset=["exit_date"])
        .groupby("exit_date", as_index=False)
        .agg(
            flagged_trade_count=("trade_id", "count"),
            flagged_contribution=(trade_return_column, "sum"),
            flagged_abs_contribution=(trade_return_column, lambda values: float(pd.Series(values).abs().sum())),
        )
    )
    contributions["in_template"] = contributions["exit_date"].isin(template_dates)
    matched = contributions[contributions["in_template"]].copy()
    unmatched = contributions[~contributions["in_template"]].copy()
    template_working = template.copy()
    template_working = template_working.merge(
        matched[["exit_date", "flagged_contribution", "flagged_trade_count"]].rename(columns={"exit_date": "date"}),
        on="date",
        how="left",
    )
    template_working["flagged_contribution"] = pd.to_numeric(
        template_working["flagged_contribution"],
        errors="coerce",
    ).fillna(0.0)
    template_working["flagged_trade_count"] = pd.to_numeric(
        template_working["flagged_trade_count"],
        errors="coerce",
    ).fillna(0).astype(int)
    template_working["base_period_return"] = pd.to_numeric(
        template_working["period_return"],
        errors="coerce",
    ).fillna(0.0)
    template_working["period_return"] = template_working["base_period_return"] - template_working["flagged_contribution"]
    template_working["candidate_name"] = candidate_name

    matched_count = int(matched["flagged_trade_count"].sum()) if not matched.empty else 0
    unmatched_count = int(unmatched["flagged_trade_count"].sum()) if not unmatched.empty else 0
    total_count = int(len(flagged))
    matched_contribution = _number(matched["flagged_contribution"].sum()) if not matched.empty else 0.0
    unmatched_contribution = _number(unmatched["flagged_contribution"].sum()) if not unmatched.empty else 0.0
    unmatched_abs_contribution = _number(unmatched["flagged_abs_contribution"].sum()) if not unmatched.empty else 0.0
    total_abs_contribution = _number(contributions["flagged_abs_contribution"].sum()) if not contributions.empty else 0.0
    unmatched_abs = pd.to_numeric(
        unmatched.get("flagged_abs_contribution", 0.0),
        errors="coerce",
    ).fillna(0.0)
    unmatched_nonzero = unmatched[unmatched_abs > 0.0]
    unmatched_zero = unmatched[unmatched_abs <= 0.0]
    unmatched_by_year: dict[str, float] = {}
    if not unmatched_nonzero.empty:
        yearly = unmatched_nonzero.assign(exit_year=pd.to_datetime(unmatched_nonzero["exit_date"]).dt.year).groupby(
            "exit_year"
        )["flagged_abs_contribution"].sum()
        unmatched_by_year = {str(int(year)): _number(value) for year, value in yearly.items()}
    contribution_summary = {
        "flagged_trade_count": total_count,
        "matched_flagged_trade_count": matched_count,
        "unmatched_flagged_trade_count": unmatched_count,
        "matched_flagged_contribution": matched_contribution,
        "unmatched_flagged_contribution": unmatched_contribution,
        "unmatched_abs_flagged_contribution": unmatched_abs_contribution,
        "unmatched_nonzero_date_count": int(len(unmatched_nonzero)),
        "unmatched_zero_date_count": int(len(unmatched_zero)),
        "unmatched_abs_contribution_by_year": unmatched_by_year,
        "total_abs_flagged_contribution": total_abs_contribution,
        "unmatched_abs_contribution_share": (
            unmatched_abs_contribution / total_abs_contribution if total_abs_contribution > 0 else 0.0
        ),
    }
    flag_rows = [
        {
            "candidate_name": candidate_name,
            "exit_date": pd.Timestamp(row.exit_date).date().isoformat(),
            "flagged_trade_count": int(row.flagged_trade_count),
            "flagged_contribution": _number(row.flagged_contribution),
            "flagged_abs_contribution": _number(row.flagged_abs_contribution),
            "in_template": bool(row.in_template),
        }
        for row in contributions.sort_values("flagged_abs_contribution", ascending=False).itertuples(index=False)
    ]
    return (
        _candidate_output_columns(template_working),
        contribution_summary,
        flag_rows,
    )


def _metrics(
    period_returns: pd.DataFrame,
    *,
    candidate_name: str,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    row = summarize_return_blocks(
        period_returns[["date", "period_return"]],
        candidate_name=candidate_name,
        return_column="period_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    return {key: row.get(key) for key in ("candidate_name", "period_count", *METRIC_KEYS)}


def _blockers(
    candidate_metrics: Mapping[str, Any],
    *,
    base_metrics: Mapping[str, Any],
    contribution_summary: Mapping[str, Any],
    max_unmatched_abs_contribution: float,
    require_candidate_improvement: bool,
) -> list[str]:
    blockers = []
    if int(contribution_summary.get("flagged_trade_count", 0)) <= 0:
        blockers.append("no_flagged_trades")
    if float(contribution_summary.get("unmatched_abs_flagged_contribution", 0.0)) > float(max_unmatched_abs_contribution):
        blockers.append("unmatched_flagged_contribution_above_limit")
    if require_candidate_improvement and (
        _number(candidate_metrics.get("annualized_return")) <= _number(base_metrics.get("annualized_return"))
    ):
        blockers.append("candidate_does_not_improve_annualized_return")
    return blockers


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _num(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in frame.sort_values("date").itertuples(index=False):
        record = {}
        for column, value in row._asdict().items():
            if column in {"date", "signal_date", "entry_date", "decision_date"} and not pd.isna(value):
                record[column] = pd.Timestamp(value).date().isoformat()
            elif column in {"period_return", "base_period_return", "flagged_contribution"}:
                record[column] = _number(value)
            elif column == "flagged_trade_count":
                record[column] = int(value)
            else:
                record[column] = value
        rows.append(record)
    return rows


def _candidate_output_columns(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        column
        for column in (
            "date",
            "signal_date",
            "entry_date",
            "decision_date",
            "signal_date_count",
            "entry_date_count",
            "period_return",
            "base_period_return",
            "flagged_contribution",
            "flagged_trade_count",
            "filter_name",
            "candidate_name",
        )
        if column in frame
    ]
    if "date" not in columns or "period_return" not in columns:
        raise ValueError("candidate output must contain date and period_return")
    return frame[columns]


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
