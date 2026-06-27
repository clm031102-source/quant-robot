from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


STAGE = "shortlist_trade_group_contribution"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
MISSING_GROUP = "MISSING"


def build_trade_group_contribution_audit(
    *,
    trades_source: str | Path | pd.DataFrame,
    group_columns: Sequence[str],
    contribution_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "exit_date",
    allowed_column: str | None = "entry_allowed",
    top_n: int = 10,
) -> dict[str, Any]:
    trades = _load_trades(
        trades_source,
        group_columns=group_columns,
        contribution_column=contribution_column,
        date_column=date_column,
        allowed_column=allowed_column,
    )
    summary_frames: list[pd.DataFrame] = []
    top_frames: list[pd.DataFrame] = []
    by_year_frames: list[pd.DataFrame] = []
    summary: dict[str, Any] = {}
    for group_column in group_columns:
        group_summary = _summarize_group(
            trades,
            group_column=group_column,
            contribution_column=contribution_column,
            allowed_column=allowed_column,
        )
        summary_frames.append(group_summary)
        top_frames.append(_top_rows(group_summary, top_n=top_n))
        by_year_frames.append(
            _summarize_group_by_year(
                trades,
                group_column=group_column,
                contribution_column=contribution_column,
            )
        )
        summary[str(group_column)] = _column_summary(group_summary, top_n=top_n)

    summary_frame = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    top_frame = pd.concat(top_frames, ignore_index=True) if top_frames else pd.DataFrame()
    by_year_frame = pd.concat(by_year_frames, ignore_index=True) if by_year_frames else pd.DataFrame()
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "group_columns": list(group_columns),
                "contribution_column": contribution_column,
                "date_column": date_column,
                "allowed_column": allowed_column,
                "top_n": int(top_n),
            },
            "summary": {
                "trade_count": int(len(trades)),
                "group_column_count": int(len(group_columns)),
                "total_contribution": _number(trades[contribution_column].sum()) if len(trades) else 0.0,
                "columns": summary,
            },
            "group_contribution_summary": _frame_rows(summary_frame),
            "group_contribution_top_rows": _frame_rows(top_frame),
            "group_contribution_by_year": _frame_rows(by_year_frame),
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Group contribution is diagnostic exposure evidence, not a standalone alpha factor.",
            },
        }
    )


def write_trade_group_contribution_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    (output / "trade_group_contribution_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("group_contribution_summary", [])).to_csv(
        output / "group_contribution_summary.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("group_contribution_top_rows", [])).to_csv(
        output / "group_contribution_top_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("group_contribution_by_year", [])).to_csv(
        output / "group_contribution_by_year.csv",
        index=False,
    )
    legacy_summary = {
        key: value
        for key, value in sanitized.get("summary", {}).get("columns", {}).items()
    }
    (output / "round390_group_contribution_summary.json").write_text(
        json.dumps(legacy_summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_trades(
    source: str | Path | pd.DataFrame,
    *,
    group_columns: Sequence[str],
    contribution_column: str,
    date_column: str,
    allowed_column: str | None,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = [date_column, contribution_column, *group_columns]
    if allowed_column:
        required.append(allowed_column)
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output[date_column] = pd.to_datetime(output[date_column], errors="coerce")
    output[contribution_column] = pd.to_numeric(output[contribution_column], errors="coerce").fillna(0.0)
    for column in group_columns:
        output[column] = _normalise_group_values(output[column])
    if allowed_column:
        output[allowed_column] = _truthy_series(output[allowed_column])
    output = output.dropna(subset=[date_column]).reset_index(drop=True)
    output["year"] = output[date_column].dt.year.astype(int)
    return output


def _summarize_group(
    trades: pd.DataFrame,
    *,
    group_column: str,
    contribution_column: str,
    allowed_column: str | None,
) -> pd.DataFrame:
    total_contribution = _number(trades[contribution_column].sum()) if len(trades) else 0.0
    rows = []
    for group_value, frame in trades.groupby(group_column, dropna=False, sort=True):
        contribution = pd.to_numeric(frame[contribution_column], errors="coerce").fillna(0.0)
        row = {
            "group_column": group_column,
            "group_value": str(group_value),
            "trade_count": int(len(frame)),
            "contribution_sum": _number(contribution.sum()),
            "abs_contribution_sum": _number(contribution.abs().sum()),
            "positive_contribution_sum": _number(contribution[contribution > 0.0].sum()),
            "negative_contribution_sum": _number(contribution[contribution < 0.0].sum()),
            "positive_trade_rate": _number((contribution > 0.0).mean()) if len(frame) else 0.0,
            "entry_allowed_rate": _number(frame[allowed_column].mean()) if allowed_column else 0.0,
            "share_of_total_contribution": (
                _number(contribution.sum()) / total_contribution if abs(total_contribution) > 0.0 else 0.0
            ),
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values("contribution_sum", ascending=False).reset_index(drop=True)


def _summarize_group_by_year(
    trades: pd.DataFrame,
    *,
    group_column: str,
    contribution_column: str,
) -> pd.DataFrame:
    grouped = (
        trades.groupby(["year", group_column], dropna=False, sort=True)[contribution_column]
        .agg(
            trade_count="count",
            contribution_sum="sum",
            abs_contribution_sum=lambda values: float(pd.Series(values).abs().sum()),
        )
        .reset_index()
        .rename(columns={group_column: "group_value"})
    )
    grouped.insert(0, "group_column", group_column)
    return grouped.sort_values(["group_column", "year", "group_value"]).reset_index(drop=True)


def _top_rows(summary: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    if summary.empty:
        return summary.copy()
    positive = summary.sort_values("contribution_sum", ascending=False).head(int(top_n))
    negative = summary.sort_values("contribution_sum", ascending=True).head(int(top_n))
    return pd.concat([positive, negative], ignore_index=True).drop_duplicates(
        subset=["group_column", "group_value"],
        keep="first",
    )


def _column_summary(summary: pd.DataFrame, *, top_n: int) -> dict[str, Any]:
    if summary.empty:
        return {
            "group_count": 0,
            "total_contribution": 0.0,
            "best_group": None,
            "worst_group": None,
            "top5_contribution": 0.0,
            "top5_share_of_total": 0.0,
            "top10_abs_share": 0.0,
        }
    total_contribution = _number(summary["contribution_sum"].sum())
    top_positive = summary.sort_values("contribution_sum", ascending=False).head(5)
    top5_contribution = _number(top_positive["contribution_sum"].sum())
    abs_total = _number(summary["abs_contribution_sum"].sum())
    top_abs = summary.sort_values("abs_contribution_sum", ascending=False).head(int(top_n))
    return {
        "group_count": int(len(summary)),
        "total_contribution": total_contribution,
        "best_group": str(summary.sort_values("contribution_sum", ascending=False).iloc[0]["group_value"]),
        "worst_group": str(summary.sort_values("contribution_sum", ascending=True).iloc[0]["group_value"]),
        "top5_contribution": top5_contribution,
        "top5_share_of_total": top5_contribution / total_contribution if abs(total_contribution) > 0.0 else 0.0,
        "top10_abs_share": _number(top_abs["abs_contribution_sum"].sum()) / abs_total if abs_total > 0.0 else 0.0,
    }


def _normalise_group_values(series: pd.Series) -> pd.Series:
    values = series.astype("string")
    values = values.fillna("").str.strip()
    values = values.mask(values == "", MISSING_GROUP)
    return values.astype(str)


def _truthy_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0) != 0.0
    normalized = series.astype("string").fillna("").str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "t"})


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in frame.itertuples(index=False):
        rows.append(_sanitize(row._asdict()))
    return rows


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
