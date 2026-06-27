from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


STAGE = "shortlist_exposure_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
DEFAULT_GROUP_COLUMNS = ("industry", "stock_market")


def build_shortlist_exposure_audit(
    trades_source: str | Path | pd.DataFrame,
    *,
    group_columns: Iterable[str] = DEFAULT_GROUP_COLUMNS,
    date_column: str = "signal_date",
    weight_column: str = "target_weight",
    return_column: str = "entry_cash_proxy_weighted_return",
    max_missing_weight_share: float = 0.20,
    max_top_weight_share_p95: float = 0.45,
    max_mean_hhi: float = 0.20,
    max_abs_return_contribution_share: float = 0.45,
) -> dict[str, Any]:
    trades = load_trade_exposure_frame(
        trades_source,
        date_column=date_column,
        weight_column=weight_column,
        return_column=return_column,
    )
    dimensions = [str(column) for column in group_columns]
    missing = [column for column in dimensions if column not in trades]
    if missing:
        raise ValueError(f"trades missing group columns: {', '.join(missing)}")

    event_rows = []
    dimension_rows = []
    dimension_summaries: dict[str, Any] = {}
    blockers: list[str] = []
    for dimension in dimensions:
        dim_event_rows, dim_group_rows, dim_summary, dim_blockers = summarize_dimension_exposure(
            trades,
            dimension,
            max_missing_weight_share=max_missing_weight_share,
            max_top_weight_share_p95=max_top_weight_share_p95,
            max_mean_hhi=max_mean_hhi,
            max_abs_return_contribution_share=max_abs_return_contribution_share,
        )
        event_rows.extend(dim_event_rows)
        dimension_rows.extend(dim_group_rows)
        dimension_summaries[dimension] = dim_summary
        blockers.extend(dim_blockers)

    event_dates = pd.DatetimeIndex(trades["date"].dropna().sort_values().unique())
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "date_column": date_column,
                "weight_column": weight_column,
                "return_column": return_column,
                "group_columns": dimensions,
                "max_missing_weight_share": float(max_missing_weight_share),
                "max_top_weight_share_p95": float(max_top_weight_share_p95),
                "max_mean_hhi": float(max_mean_hhi),
                "max_abs_return_contribution_share": float(max_abs_return_contribution_share),
            },
            "summary": {
                "trade_count": int(len(trades)),
                "event_count": int(len(event_dates)),
                "date_start": _date_value(event_dates.min()) if len(event_dates) else None,
                "date_end": _date_value(event_dates.max()) if len(event_dates) else None,
                "total_weight": _number(trades["weight"].sum()),
                "total_return_contribution": _number(trades["return_contribution"].sum()),
                "blocked": bool(blockers),
            },
            "dimension_summaries": dimension_summaries,
            "event_rows": event_rows,
            "dimension_rows": sorted(
                dimension_rows,
                key=lambda row: (
                    row["dimension"],
                    -abs(float(row["return_contribution"])),
                    -float(row["total_weight"]),
                    str(row["group_value"]),
                ),
            ),
            "blockers": blockers,
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Exposure audit diagnoses hidden beta/concentration only; it is not final validation.",
            },
        }
    )


def load_trade_exposure_frame(
    source: str | Path | pd.DataFrame,
    *,
    date_column: str,
    weight_column: str,
    return_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = [date_column, weight_column, return_column]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades missing columns: {', '.join(missing)}")
    working = frame.copy()
    working["date"] = pd.to_datetime(working[date_column], errors="coerce")
    working["weight"] = pd.to_numeric(working[weight_column], errors="coerce").fillna(0.0).clip(lower=0.0)
    working["return_contribution"] = pd.to_numeric(working[return_column], errors="coerce").fillna(0.0)
    working = working.dropna(subset=["date"]).reset_index(drop=True)
    if working.empty:
        return pd.DataFrame(columns=["date", "weight", "return_contribution"])
    return working


def summarize_dimension_exposure(
    trades: pd.DataFrame,
    dimension: str,
    *,
    max_missing_weight_share: float,
    max_top_weight_share_p95: float,
    max_mean_hhi: float,
    max_abs_return_contribution_share: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[str]]:
    working = trades[["date", "weight", "return_contribution", dimension]].copy()
    working["group_value"] = working[dimension].where(working[dimension].notna(), "UNKNOWN")
    working["group_value"] = working["group_value"].astype(str).replace({"": "UNKNOWN", "nan": "UNKNOWN"})

    event_total = (
        working.groupby("date", as_index=False)
        .agg(event_total_weight=("weight", "sum"), event_return_contribution=("return_contribution", "sum"))
    )
    grouped = (
        working.groupby(["date", "group_value"], as_index=False)
        .agg(weight=("weight", "sum"), return_contribution=("return_contribution", "sum"), trade_count=("weight", "size"))
        .merge(event_total, on="date", how="left")
    )
    grouped["weight_share"] = np.where(
        grouped["event_total_weight"] > 0.0,
        grouped["weight"] / grouped["event_total_weight"],
        0.0,
    )

    event_rows = []
    for date, event in grouped.groupby("date", sort=True):
        event = event.sort_values(["weight_share", "weight"], ascending=[False, False])
        total_weight = _number(event["event_total_weight"].iloc[0])
        top = event.iloc[0] if len(event) else None
        unknown = event[event["group_value"] == "UNKNOWN"]
        hhi = _number((event["weight_share"] ** 2).sum())
        event_rows.append(
            {
                "dimension": dimension,
                "date": _date_value(date),
                "event_total_weight": total_weight,
                "event_return_contribution": _number(event["event_return_contribution"].iloc[0]) if len(event) else 0.0,
                "group_count": int((event["weight"] > 0.0).sum()),
                "top_group": str(top["group_value"]) if top is not None else None,
                "top_weight_share": _number(top["weight_share"]) if top is not None else 0.0,
                "missing_weight_share": _number(unknown["weight_share"].sum()) if not unknown.empty else 0.0,
                "hhi": hhi,
            }
        )

    event_frame = pd.DataFrame(event_rows)
    dimension_rows = _dimension_group_rows(grouped, dimension)
    total_weight = float(working["weight"].sum())
    missing_weight = float(working.loc[working["group_value"] == "UNKNOWN", "weight"].sum())
    missing_weight_share = missing_weight / total_weight if total_weight > 0.0 else 0.0
    top_abs_return_share = max((row["abs_return_contribution_share"] for row in dimension_rows), default=0.0)
    summary = {
        "missing_weight_share": _number(missing_weight_share),
        "average_top_weight_share": _number(event_frame["top_weight_share"].mean() if not event_frame.empty else 0.0),
        "p95_top_weight_share": _number(event_frame["top_weight_share"].quantile(0.95) if not event_frame.empty else 0.0),
        "max_top_weight_share": _number(event_frame["top_weight_share"].max() if not event_frame.empty else 0.0),
        "average_hhi": _number(event_frame["hhi"].mean() if not event_frame.empty else 0.0),
        "p95_hhi": _number(event_frame["hhi"].quantile(0.95) if not event_frame.empty else 0.0),
        "average_group_count": _number(event_frame["group_count"].mean() if not event_frame.empty else 0.0),
        "top_abs_return_contribution_share": _number(top_abs_return_share),
    }
    blockers = _dimension_blockers(
        dimension,
        summary,
        max_missing_weight_share=max_missing_weight_share,
        max_top_weight_share_p95=max_top_weight_share_p95,
        max_mean_hhi=max_mean_hhi,
        max_abs_return_contribution_share=max_abs_return_contribution_share,
    )
    return _sanitize(event_rows), _sanitize(dimension_rows), _sanitize(summary), blockers


def write_shortlist_exposure_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(audit)
    (output / "shortlist_exposure_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("dimension_rows", [])).to_csv(
        output / "shortlist_exposure_dimension_rows.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("event_rows", [])).to_csv(
        output / "shortlist_exposure_event_rows.csv",
        index=False,
    )


def _dimension_group_rows(grouped: pd.DataFrame, dimension: str) -> list[dict[str, Any]]:
    total_weight = float(grouped["weight"].sum())
    total_abs_return = float(grouped["return_contribution"].abs().sum())
    rows = []
    for group_value, group in grouped.groupby("group_value", sort=False):
        rows.append(
            {
                "dimension": dimension,
                "group_value": str(group_value),
                "event_count": int(len(group)),
                "total_weight": _number(group["weight"].sum()),
                "weight_share": _number(group["weight"].sum() / total_weight if total_weight > 0.0 else 0.0),
                "average_event_weight_share": _number(group["weight_share"].mean()),
                "max_event_weight_share": _number(group["weight_share"].max()),
                "return_contribution": _number(group["return_contribution"].sum()),
                "abs_return_contribution_share": _number(
                    group["return_contribution"].abs().sum() / total_abs_return if total_abs_return > 0.0 else 0.0
                ),
                "trade_count": int(group["trade_count"].sum()),
            }
        )
    return rows


def _dimension_blockers(
    dimension: str,
    summary: dict[str, Any],
    *,
    max_missing_weight_share: float,
    max_top_weight_share_p95: float,
    max_mean_hhi: float,
    max_abs_return_contribution_share: float,
) -> list[str]:
    blockers = []
    if float(summary["missing_weight_share"]) > float(max_missing_weight_share):
        blockers.append(f"missing_{dimension}_weight_share_too_high")
    if float(summary["p95_top_weight_share"]) > float(max_top_weight_share_p95):
        blockers.append(f"{dimension}_top_weight_share_p95_too_high")
    if float(summary["average_hhi"]) > float(max_mean_hhi):
        blockers.append(f"{dimension}_average_hhi_too_high")
    if float(summary["top_abs_return_contribution_share"]) > float(max_abs_return_contribution_share):
        blockers.append(f"{dimension}_single_group_abs_return_share_too_high")
    return blockers


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported trades file type: {path.suffix}")


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
