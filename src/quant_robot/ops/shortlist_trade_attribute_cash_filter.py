from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks


STAGE = "shortlist_trade_attribute_cash_filter"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
METRIC_KEYS = (
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_autocorr_adjusted_sharpe",
    "max_drawdown",
    "win_rate",
)
NUMERIC_OPERATORS = {"gt", "ge", "lt", "le", "between"}


@dataclass(frozen=True)
class AttributeFilterSpec:
    name: str
    column: str
    operator: str
    values: tuple[str, ...] = ()


def build_trade_attribute_cash_filter_audit(
    *,
    template_period_returns: str | Path | pd.DataFrame,
    trades_source: str | Path | pd.DataFrame,
    candidates: Sequence[AttributeFilterSpec],
    template_return_column: str = "period_return",
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    date_column: str = "date",
    trade_exit_date_column: str = "exit_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_unmatched_abs_contribution: float = 0.005,
) -> dict[str, Any]:
    template = _load_template_returns(
        template_period_returns,
        return_column=template_return_column,
        date_column=date_column,
    )
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        exit_date_column=trade_exit_date_column,
    )
    base_metrics = _metrics(
        template,
        candidate_name="official_template_base",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    rows: list[dict[str, Any]] = []
    period_return_frames: dict[str, pd.DataFrame] = {}
    for spec in candidates:
        flagged = _flag_trades(trades, spec)
        candidate_returns, contribution_summary = _project_to_template(
            template,
            flagged,
            candidate_name=f"cash_{spec.name}",
            trade_return_column=trade_return_column,
            exit_date_column=trade_exit_date_column,
        )
        period_return_frames[f"cash_{spec.name}"] = candidate_returns
        candidate_metrics = _metrics(
            candidate_returns,
            candidate_name=f"cash_{spec.name}",
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
        metric_diffs = {
            key: _number(candidate_metrics.get(key)) - _number(base_metrics.get(key))
            for key in METRIC_KEYS
        }
        rows.append(
            {
                "candidate_name": f"cash_{spec.name}",
                "column": spec.column,
                "operator": spec.operator,
                "values": list(spec.values),
                **contribution_summary,
                "base_metrics": {key: base_metrics.get(key) for key in METRIC_KEYS},
                "candidate_metrics": {key: candidate_metrics.get(key) for key in METRIC_KEYS},
                "metric_diffs": metric_diffs,
                "blockers": _blockers(
                    contribution_summary,
                    max_unmatched_abs_contribution=max_unmatched_abs_contribution,
                ),
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
                "trade_exit_date_column": trade_exit_date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_unmatched_abs_contribution": float(max_unmatched_abs_contribution),
            },
            "summary": {
                "candidate_count": int(len(rows)),
                "template_date_count": int(len(template)),
                "trade_count": int(len(trades)),
                "blocked_candidate_count": int(sum(bool(row["blockers"]) for row in rows)),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "base_metrics": base_metrics,
            "rows": rows,
            "period_return_frames": {name: _frame_rows(frame) for name, frame in period_return_frames.items()},
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Attribute cash filters are official-template projections, not final simulation evidence.",
            },
        }
    )


def write_trade_attribute_cash_filter_audit(output_dir: str | Path, audit: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(audit))
    period_return_frames = sanitized.pop("period_return_frames", {})
    (output / "trade_attribute_cash_filter_audit.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "trade_attribute_cash_filter_rows.csv",
        index=False,
    )
    for candidate_name, rows in period_return_frames.items():
        safe_name = str(candidate_name).replace("/", "_").replace("\\", "_")
        pd.DataFrame(rows).to_csv(output / f"{safe_name}_official_template_period_returns.csv", index=False)


def parse_attribute_filter_spec(value: str) -> AttributeFilterSpec:
    if "=" not in value:
        raise ValueError("candidate spec must use name=column:operator:value")
    name, expression = value.split("=", 1)
    parts = expression.split(":", 2)
    if len(parts) < 2:
        raise ValueError("candidate expression must use column:operator or column:operator:value")
    column, operator = parts[0].strip(), parts[1].strip()
    raw_values = parts[2] if len(parts) == 3 else ""
    values = tuple(item.strip() for item in raw_values.split(",") if item.strip())
    if not name.strip() or not column or not operator:
        raise ValueError("candidate name, column, and operator are required")
    if operator in {"eq", "ne", "in", "not_in", *NUMERIC_OPERATORS} and not values:
        raise ValueError(f"operator {operator} requires at least one value")
    if operator == "between" and len(values) != 2:
        raise ValueError("operator between requires exactly two numeric values")
    return AttributeFilterSpec(name=name.strip(), column=column, operator=operator, values=values)


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
    return output.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _load_trades(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    exit_date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    required = [exit_date_column, return_column]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"trades source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output[exit_date_column] = pd.to_datetime(output[exit_date_column], errors="coerce")
    output[return_column] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output = output.dropna(subset=[exit_date_column]).reset_index(drop=True)
    output["trade_id"] = np.arange(len(output), dtype=int)
    return output


def _flag_trades(trades: pd.DataFrame, spec: AttributeFilterSpec) -> pd.DataFrame:
    if spec.column not in trades:
        raise ValueError(f"trades source missing attribute column: {spec.column}")
    series = trades[spec.column]
    normalized = series.astype("string")
    missing = series.isna() | (normalized.fillna("").str.strip() == "")
    values = {str(value) for value in spec.values}
    if spec.operator == "missing":
        mask = missing
    elif spec.operator == "not_missing":
        mask = ~missing
    elif spec.operator == "eq":
        mask = normalized.isin(values)
    elif spec.operator == "ne":
        mask = ~normalized.isin(values)
    elif spec.operator == "in":
        mask = normalized.isin(values)
    elif spec.operator == "not_in":
        mask = ~normalized.isin(values)
    elif spec.operator in NUMERIC_OPERATORS:
        numeric = pd.to_numeric(series, errors="coerce")
        thresholds = tuple(_parse_numeric_filter_value(value, spec=spec) for value in spec.values)
        if spec.operator == "gt":
            mask = numeric > thresholds[0]
        elif spec.operator == "ge":
            mask = numeric >= thresholds[0]
        elif spec.operator == "lt":
            mask = numeric < thresholds[0]
        elif spec.operator == "le":
            mask = numeric <= thresholds[0]
        elif spec.operator == "between":
            low, high = sorted((thresholds[0], thresholds[1]))
            mask = numeric.between(low, high, inclusive="both")
        else:  # pragma: no cover - guarded by NUMERIC_OPERATORS
            raise ValueError(f"unsupported operator: {spec.operator}")
    else:
        raise ValueError(f"unsupported operator: {spec.operator}")
    return trades[mask.fillna(False)].copy()


def _parse_numeric_filter_value(value: str, *, spec: AttributeFilterSpec) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"operator {spec.operator} for {spec.column} requires numeric values"
        ) from exc
    if not math.isfinite(number):
        raise ValueError(f"operator {spec.operator} for {spec.column} requires finite numeric values")
    return number


def _project_to_template(
    template: pd.DataFrame,
    flagged: pd.DataFrame,
    *,
    candidate_name: str,
    trade_return_column: str,
    exit_date_column: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
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
    output = template.copy()
    output = output.merge(
        matched[["exit_date", "flagged_contribution", "flagged_trade_count"]].rename(columns={"exit_date": "date"}),
        on="date",
        how="left",
    )
    output["flagged_contribution"] = pd.to_numeric(output["flagged_contribution"], errors="coerce").fillna(0.0)
    output["flagged_trade_count"] = pd.to_numeric(output["flagged_trade_count"], errors="coerce").fillna(0).astype(int)
    output["base_period_return"] = pd.to_numeric(output["period_return"], errors="coerce").fillna(0.0)
    output["period_return"] = output["base_period_return"] - output["flagged_contribution"]
    output["candidate_name"] = candidate_name
    matched_count = int(matched["flagged_trade_count"].sum()) if not matched.empty else 0
    unmatched_count = int(unmatched["flagged_trade_count"].sum()) if not unmatched.empty else 0
    total_abs_contribution = _number(contributions["flagged_abs_contribution"].sum()) if not contributions.empty else 0.0
    unmatched_abs_contribution = _number(unmatched["flagged_abs_contribution"].sum()) if not unmatched.empty else 0.0
    return (
        output[["date", "period_return", "base_period_return", "flagged_contribution", "flagged_trade_count", "candidate_name"]],
        {
            "flagged_trade_count": int(len(flagged)),
            "matched_flagged_trade_count": matched_count,
            "unmatched_flagged_trade_count": unmatched_count,
            "matched_flagged_contribution": _number(matched["flagged_contribution"].sum()) if not matched.empty else 0.0,
            "unmatched_flagged_contribution": _number(unmatched["flagged_contribution"].sum()) if not unmatched.empty else 0.0,
            "unmatched_abs_flagged_contribution": unmatched_abs_contribution,
            "total_abs_flagged_contribution": total_abs_contribution,
            "unmatched_abs_contribution_share": (
                unmatched_abs_contribution / total_abs_contribution if total_abs_contribution > 0 else 0.0
            ),
        },
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
    contribution_summary: Mapping[str, Any],
    *,
    max_unmatched_abs_contribution: float,
) -> list[str]:
    blockers = []
    if int(contribution_summary.get("flagged_trade_count", 0)) <= 0:
        blockers.append("no_flagged_trades")
    if float(contribution_summary.get("unmatched_abs_flagged_contribution", 0.0)) > float(max_unmatched_abs_contribution):
        blockers.append("unmatched_flagged_contribution_above_limit")
    return blockers


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in frame.sort_values("date").itertuples(index=False):
        record = row._asdict()
        record["date"] = pd.Timestamp(record["date"]).date().isoformat()
        rows.append(_sanitize(record))
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
