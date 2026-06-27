from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


STAGE = "shortlist_extreme_trade_profile"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
MISSING_GROUP = "MISSING"


def build_extreme_trade_profile(
    trades_source: str | Path | pd.DataFrame,
    *,
    group_columns: Sequence[str],
    numeric_columns: Sequence[str],
    threshold: float = 0.50,
    gross_return_column: str = "gross_return",
    contribution_column: str = "final_return_contribution",
    active_weight_column: str = "final_target_weight",
    top_n: int = 50,
    min_group_extreme_count: int = 3,
    min_extreme_rate_lift: float = 2.0,
) -> dict[str, Any]:
    trades, missing_group_columns, missing_numeric_columns = _prepare_trades(
        trades_source,
        group_columns=tuple(group_columns),
        numeric_columns=tuple(numeric_columns),
        threshold=threshold,
        gross_return_column=gross_return_column,
        contribution_column=contribution_column,
        active_weight_column=active_weight_column,
    )
    baseline_rate = _number(trades["is_extreme"].mean()) if len(trades) else 0.0
    extreme_count = int(trades["is_extreme"].sum()) if len(trades) else 0
    group_rows = []
    for column in group_columns:
        if column in missing_group_columns:
            continue
        group_rows.extend(
            _group_profile_rows(
                trades,
                group_column=column,
                baseline_rate=baseline_rate,
                total_extreme_count=extreme_count,
                min_group_extreme_count=min_group_extreme_count,
                min_extreme_rate_lift=min_extreme_rate_lift,
            )
        )
    numeric_rows = []
    for column in numeric_columns:
        if column in missing_numeric_columns:
            continue
        numeric_rows.append(_numeric_profile_row(trades, column))

    top_columns = _top_columns(
        trades,
        group_columns=[column for column in group_columns if column not in missing_group_columns],
        numeric_columns=[column for column in numeric_columns if column not in missing_numeric_columns],
        gross_return_column=gross_return_column,
        contribution_column=contribution_column,
        active_weight_column=active_weight_column,
    )
    top_extreme = (
        trades[trades["is_extreme"]]
        .sort_values(["abs_gross_return", "asset_id"], ascending=[False, True])
        .head(int(top_n))
        .loc[:, top_columns]
        if len(trades)
        else pd.DataFrame(columns=top_columns)
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "threshold": float(threshold),
                "gross_return_column": gross_return_column,
                "contribution_column": contribution_column,
                "active_weight_column": active_weight_column,
                "top_n": int(top_n),
                "min_group_extreme_count": int(min_group_extreme_count),
                "min_extreme_rate_lift": float(min_extreme_rate_lift),
                "causality_policy": (
                    "This profile may use realized gross returns only to diagnose tail dependence; "
                    "repair rules must use entry-known fields."
                ),
            },
            "summary": {
                "source_trade_count": int(_read_frame_or_copy(trades_source).shape[0]),
                "active_trade_count": int(len(trades)),
                "extreme_trade_count": extreme_count,
                "extreme_trade_rate": baseline_rate,
                "positive_extreme_trade_count": int((trades["gross_return"] > abs(float(threshold))).sum())
                if len(trades)
                else 0,
                "negative_extreme_trade_count": int((trades["gross_return"] < -abs(float(threshold))).sum())
                if len(trades)
                else 0,
                "max_abs_gross_return": _number(trades["abs_gross_return"].max()) if len(trades) else 0.0,
                "extreme_contribution_sum": _number(trades.loc[trades["is_extreme"], "contribution"].sum())
                if len(trades)
                else 0.0,
                "total_contribution_sum": _number(trades["contribution"].sum()) if len(trades) else 0.0,
                "missing_group_columns": list(missing_group_columns),
                "missing_numeric_columns": list(missing_numeric_columns),
            },
            "group_profile_rows": group_rows,
            "numeric_profile_rows": numeric_rows,
            "top_extreme_trade_rows": _frame_rows(top_extreme),
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Extreme-trade profiling is diagnostic evidence, not a standalone alpha factor.",
            },
        }
    )


def write_extreme_trade_profile(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    (output / "extreme_trade_profile.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("group_profile_rows", [])).to_csv(
        output / "extreme_trade_group_profile.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("numeric_profile_rows", [])).to_csv(
        output / "extreme_trade_numeric_profile.csv",
        index=False,
    )
    pd.DataFrame(sanitized.get("top_extreme_trade_rows", [])).to_csv(
        output / "top_extreme_trade_rows.csv",
        index=False,
    )


def _prepare_trades(
    source: str | Path | pd.DataFrame,
    *,
    group_columns: Sequence[str],
    numeric_columns: Sequence[str],
    threshold: float,
    gross_return_column: str,
    contribution_column: str,
    active_weight_column: str,
) -> tuple[pd.DataFrame, tuple[str, ...], tuple[str, ...]]:
    frame = _read_frame_or_copy(source)
    if gross_return_column not in frame:
        raise ValueError(f"trades source missing column: {gross_return_column}")
    output = frame.copy()
    output["gross_return"] = pd.to_numeric(output[gross_return_column], errors="coerce")
    output["abs_gross_return"] = output["gross_return"].abs()
    if contribution_column in output:
        output["contribution"] = pd.to_numeric(output[contribution_column], errors="coerce").fillna(0.0)
    else:
        output["contribution"] = 0.0
    if active_weight_column in output:
        active_weight = pd.to_numeric(output[active_weight_column], errors="coerce").fillna(0.0)
        output = output[active_weight.abs() > 0.0].copy()
        output[active_weight_column] = active_weight.loc[output.index]
    output = output.dropna(subset=["gross_return"]).reset_index(drop=True)
    output["is_extreme"] = output["abs_gross_return"] > abs(float(threshold))
    missing_group_columns = tuple(column for column in group_columns if column not in output)
    missing_numeric_columns = tuple(column for column in numeric_columns if column not in output)
    for column in group_columns:
        if column not in missing_group_columns:
            output[column] = _normalise_group_values(output[column])
    for column in numeric_columns:
        if column not in missing_numeric_columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    return output, missing_group_columns, missing_numeric_columns


def _group_profile_rows(
    trades: pd.DataFrame,
    *,
    group_column: str,
    baseline_rate: float,
    total_extreme_count: int,
    min_group_extreme_count: int,
    min_extreme_rate_lift: float,
) -> list[dict[str, Any]]:
    rows = []
    for group_value, frame in trades.groupby(group_column, dropna=False, sort=True):
        extreme = frame[frame["is_extreme"]]
        trade_count = int(len(frame))
        extreme_count = int(len(extreme))
        extreme_rate = extreme_count / trade_count if trade_count else 0.0
        lift = extreme_rate / baseline_rate if baseline_rate > 0.0 else 0.0
        rows.append(
            {
                "group_column": group_column,
                "group_value": str(group_value),
                "trade_count": trade_count,
                "extreme_trade_count": extreme_count,
                "extreme_trade_rate": _number(extreme_rate),
                "extreme_rate_lift": _number(lift),
                "group_extreme_share": _number(extreme_count / total_extreme_count)
                if total_extreme_count
                else 0.0,
                "contribution_sum": _number(frame["contribution"].sum()),
                "extreme_contribution_sum": _number(extreme["contribution"].sum()) if extreme_count else 0.0,
                "max_abs_gross_return": _number(frame["abs_gross_return"].max()) if trade_count else 0.0,
                "risk_candidate": bool(
                    extreme_count >= int(min_group_extreme_count)
                    and lift >= float(min_extreme_rate_lift)
                ),
            }
        )
    return sorted(rows, key=lambda row: (not row["risk_candidate"], -row["extreme_rate_lift"], -row["extreme_trade_count"], row["group_value"]))


def _numeric_profile_row(trades: pd.DataFrame, column: str) -> dict[str, Any]:
    extreme = pd.to_numeric(trades.loc[trades["is_extreme"], column], errors="coerce").dropna()
    non_extreme = pd.to_numeric(trades.loc[~trades["is_extreme"], column], errors="coerce").dropna()
    extreme_mean = _number(extreme.mean()) if not extreme.empty else 0.0
    non_extreme_mean = _number(non_extreme.mean()) if not non_extreme.empty else 0.0
    return {
        "numeric_column": column,
        "extreme_count": int(len(extreme)),
        "non_extreme_count": int(len(non_extreme)),
        "extreme_mean": extreme_mean,
        "non_extreme_mean": non_extreme_mean,
        "mean_diff": _number(extreme_mean - non_extreme_mean),
        "mean_ratio": _number(extreme_mean / non_extreme_mean) if abs(non_extreme_mean) > 0.0 else 0.0,
        "extreme_median": _quantile(extreme, 0.50),
        "non_extreme_median": _quantile(non_extreme, 0.50),
        "extreme_p25": _quantile(extreme, 0.25),
        "extreme_p75": _quantile(extreme, 0.75),
        "non_extreme_p25": _quantile(non_extreme, 0.25),
        "non_extreme_p75": _quantile(non_extreme, 0.75),
    }


def _top_columns(
    trades: pd.DataFrame,
    *,
    group_columns: Sequence[str],
    numeric_columns: Sequence[str],
    gross_return_column: str,
    contribution_column: str,
    active_weight_column: str,
) -> list[str]:
    preferred = [
        "signal_date",
        "entry_date",
        "exit_date",
        "asset_id",
        gross_return_column,
        "abs_gross_return",
        contribution_column,
        active_weight_column,
        *group_columns,
        *numeric_columns,
    ]
    return [column for column in dict.fromkeys(preferred) if column in trades]


def _read_frame_or_copy(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        return source.copy()
    path = Path(source)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _normalise_group_values(series: pd.Series) -> pd.Series:
    values = series.astype("string").fillna("").str.strip()
    values = values.mask(values == "", MISSING_GROUP)
    return values.astype(str)


def _quantile(series: pd.Series, q: float) -> float:
    return _number(series.quantile(q)) if not series.empty else 0.0


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_sanitize(row._asdict()) for row in frame.itertuples(index=False)]


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
