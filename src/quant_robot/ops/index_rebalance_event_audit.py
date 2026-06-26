from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "index_rebalance_event_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_INDEX_WEIGHT_COLUMNS = ("index_code", "con_code", "trade_date", "weight")


def build_index_rebalance_event_audit(
    *,
    index_weight: pd.DataFrame,
    trade_calendar: pd.DataFrame,
    min_abs_weight_change: float = 0.5,
) -> dict[str, Any]:
    snapshots = _prepare_index_weight(index_weight)
    calendar_dates = _prepare_calendar(trade_calendar)
    next_trade_date = _next_trade_date_map(calendar_dates)
    missing_columns = [column for column in REQUIRED_INDEX_WEIGHT_COLUMNS if column not in index_weight.columns]
    duplicate_keys = int(snapshots.duplicated(["index_code", "symbol", "date"]).sum()) if not snapshots.empty else 0
    events = _build_events(snapshots, next_trade_date, min_abs_weight_change=min_abs_weight_change)
    snapshots_with_availability = snapshots.copy()
    if not snapshots_with_availability.empty:
        snapshots_with_availability["available_date"] = snapshots_with_availability["date"].map(next_trade_date)
    missing_available = int(sum(1 for row in events if not row.get("available_date")))
    blockers = []
    if index_weight.empty:
        blockers.append("missing_index_weight_rows")
    if missing_columns:
        blockers.append("missing_required_index_weight_columns")
    if duplicate_keys:
        blockers.append("duplicate_index_weight_keys")
    if not calendar_dates:
        blockers.append("missing_trade_calendar_rows")
    if not events:
        blockers.append("no_rebalance_events_detected")
    if missing_available:
        blockers.append("missing_available_date_rows")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": _dedupe(blockers),
            "snapshot_rows": int(len(snapshots)),
            "snapshot_dates": int(snapshots["date"].nunique()) if not snapshots.empty else 0,
            "index_count": int(snapshots["index_code"].nunique()) if not snapshots.empty else 0,
            "constituent_count": int(snapshots["symbol"].nunique()) if not snapshots.empty else 0,
            "event_rows": int(len(events)),
            "added_events": sum(1 for row in events if row["event_type"] == "added"),
            "removed_events": sum(1 for row in events if row["event_type"] == "removed"),
            "weight_changed_events": sum(1 for row in events if row["event_type"] == "weight_changed"),
            "duplicate_index_weight_keys": duplicate_keys,
            "missing_required_index_weight_columns": missing_columns,
            "missing_available_date_rows": missing_available,
        },
        "availability_policy": {
            "event_date_column": "trade_date",
            "signal_date_rule": "first_trade_date_strictly_after_index_weight_trade_date",
            "same_day_event_trading_allowed": False,
            "min_abs_weight_change": float(min_abs_weight_change),
        },
        "promotion_policy": {
            "portfolio_backtest_allowed": False,
            "promotion_claim_allowed": False,
            "next_allowed_action": "Use event rows as PIT-safe index rebalance contamination/control inputs before testing inclusion/exclusion alpha.",
        },
        "index_weight_snapshots": _rows(snapshots_with_availability),
        "event_rows": events,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_index_rebalance_event_audit_markdown(result)
    return result


def write_index_rebalance_event_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "index_rebalance_event_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "index_rebalance_event_audit.md").write_text(
        render_index_rebalance_event_audit_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("index_weight_snapshots", [])).to_csv(output_path / "index_weight_snapshots.csv", index=False)
    pd.DataFrame(result.get("event_rows", [])).to_csv(output_path / "index_rebalance_events.csv", index=False)


def render_index_rebalance_event_audit_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    availability = result.get("availability_policy", {}) or {}
    lines = [
        "# Index Rebalance Event Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Snapshot rows: {summary.get('snapshot_rows', 0)}",
        f"- Snapshot dates: {summary.get('snapshot_dates', 0)}",
        f"- Index count: {summary.get('index_count', 0)}",
        f"- Constituent count: {summary.get('constituent_count', 0)}",
        f"- Event rows: {summary.get('event_rows', 0)}",
        f"- Added events: {summary.get('added_events', 0)}",
        f"- Removed events: {summary.get('removed_events', 0)}",
        f"- Weight-changed events: {summary.get('weight_changed_events', 0)}",
        f"- Signal date rule: `{availability.get('signal_date_rule', '')}`",
        f"- Same-day event trading allowed: {availability.get('same_day_event_trading_allowed', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
        "- This audit converts index-weight snapshots into PIT-safe added, removed, and weight-change events.",
        "- It is event coverage evidence only; it is not IC, Sharpe, total return, win-rate, or promotion evidence.",
    ]
    return "\n".join(lines) + "\n"


def _prepare_index_weight(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["index_code", "symbol", "asset_id", "date", "weight"])
    missing = [column for column in REQUIRED_INDEX_WEIGHT_COLUMNS if column not in frame.columns]
    if missing:
        return pd.DataFrame(columns=["index_code", "symbol", "asset_id", "date", "weight"])
    output = pd.DataFrame(
        {
            "index_code": frame["index_code"].astype(str),
            "symbol": frame["con_code"].astype(str),
            "asset_id": frame["con_code"].astype(str).map(_asset_id_from_tushare_symbol),
            "date": _parse_dates(frame["trade_date"]),
            "weight": pd.to_numeric(frame["weight"], errors="coerce"),
        }
    )
    return output.dropna(subset=["date", "weight"]).sort_values(["index_code", "date", "symbol"]).reset_index(drop=True)


def _prepare_calendar(frame: pd.DataFrame) -> list[object]:
    if frame.empty:
        return []
    source = frame.copy()
    date_column = "date" if "date" in source.columns else "cal_date" if "cal_date" in source.columns else "trade_date"
    if date_column not in source.columns:
        return []
    if "is_open" in source.columns:
        source = source[pd.to_numeric(source["is_open"], errors="coerce").fillna(1).astype(int) == 1]
    dates = _parse_dates(source[date_column]).dropna().sort_values().drop_duplicates()
    return [pd.Timestamp(value).date() for value in dates]


def _next_trade_date_map(calendar_dates: list[object]) -> dict[object, object]:
    result: dict[object, object] = {}
    for index, day in enumerate(calendar_dates[:-1]):
        result[day] = calendar_dates[index + 1]
    return result


def _build_events(
    snapshots: pd.DataFrame,
    next_trade_date: dict[object, object],
    *,
    min_abs_weight_change: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if snapshots.empty:
        return rows
    for index_code, index_frame in snapshots.groupby("index_code", sort=True):
        previous: dict[str, dict[str, Any]] | None = None
        for snapshot_date, group in index_frame.groupby("date", sort=True):
            current = {
                str(row.symbol): {
                    "asset_id": str(row.asset_id),
                    "weight": float(row.weight),
                }
                for row in group.itertuples(index=False)
            }
            if previous is None:
                previous = current
                continue
            event_date = pd.Timestamp(snapshot_date).date()
            available_date = next_trade_date.get(event_date)
            for symbol in sorted(set(current) - set(previous)):
                rows.append(
                    _event_row(
                        index_code=index_code,
                        symbol=symbol,
                        asset_id=current[symbol]["asset_id"],
                        event_date=event_date,
                        available_date=available_date,
                        event_type="added",
                        prior_weight=0.0,
                        current_weight=current[symbol]["weight"],
                    )
                )
            for symbol in sorted(set(previous) - set(current)):
                rows.append(
                    _event_row(
                        index_code=index_code,
                        symbol=symbol,
                        asset_id=previous[symbol]["asset_id"],
                        event_date=event_date,
                        available_date=available_date,
                        event_type="removed",
                        prior_weight=previous[symbol]["weight"],
                        current_weight=0.0,
                    )
                )
            for symbol in sorted(set(previous) & set(current)):
                prior_weight = previous[symbol]["weight"]
                current_weight = current[symbol]["weight"]
                if abs(current_weight - prior_weight) >= float(min_abs_weight_change):
                    rows.append(
                        _event_row(
                            index_code=index_code,
                            symbol=symbol,
                            asset_id=current[symbol]["asset_id"],
                            event_date=event_date,
                            available_date=available_date,
                            event_type="weight_changed",
                            prior_weight=prior_weight,
                            current_weight=current_weight,
                        )
                    )
            previous = current
    return rows


def _event_row(
    *,
    index_code: str,
    symbol: str,
    asset_id: str,
    event_date: object,
    available_date: object | None,
    event_type: str,
    prior_weight: float,
    current_weight: float,
) -> dict[str, Any]:
    return {
        "index_code": str(index_code),
        "event_date": _iso_date(event_date),
        "available_date": _iso_date(available_date),
        "symbol": str(symbol),
        "asset_id": str(asset_id),
        "event_type": event_type,
        "prior_weight": float(prior_weight),
        "current_weight": float(current_weight),
        "weight_delta": float(current_weight - prior_weight),
        "source": "tushare_index_weight",
    }


def _rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    output = frame.copy()
    for column in ("date", "available_date"):
        if column in output.columns:
            output[column] = pd.to_datetime(output[column], errors="coerce").dt.date.astype(str)
    return output.to_dict(orient="records")


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    digit_mask = text.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d")
    if (~digit_mask).any():
        parsed.loc[~digit_mask] = pd.to_datetime(values.loc[~digit_mask], errors="coerce")
    return parsed.dt.date


def _asset_id_from_tushare_symbol(symbol: str) -> str:
    code, suffix = str(symbol).split(".")
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    exchange = exchange_by_suffix.get(suffix.upper(), suffix.upper())
    return f"CN_{exchange}_{code}"


def _iso_date(value: object | None) -> str | None:
    if value is None:
        return None
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    return timestamp.date().isoformat()


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value in output:
            continue
        output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
