from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


STAGE = "shortlist_delayed_exit_return_repair"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_delayed_exit_return_repair(
    *,
    trades_source: str | Path | pd.DataFrame,
    bars_source: str | Path | pd.DataFrame,
    masks_source: str | Path | pd.DataFrame,
    max_exit_delay_days: int = 10,
    price_column: str = "adj_close",
    output_return_column: str = "delayed_exit_weighted_return",
    override_cost_rate: float | None = None,
) -> dict[str, Any]:
    trades = _load_trades(trades_source)
    bars = _load_bars(bars_source, price_column=price_column)
    masks = _load_masks(masks_source)
    price_lookup = {
        (str(row.asset_id), pd.Timestamp(row.date).date()): float(row.price)
        for row in bars.itertuples(index=False)
    }
    sell_dates_by_asset = {
        str(asset_id): sorted(pd.Timestamp(value).date() for value in frame.loc[frame["can_sell"], "date"])
        for asset_id, frame in masks.groupby("asset_id", sort=False)
    }
    rows = [
        _repair_trade_row(
            row._asdict(),
            price_lookup=price_lookup,
            sell_dates_by_asset=sell_dates_by_asset,
            max_exit_delay_days=int(max_exit_delay_days),
            output_return_column=output_return_column,
            override_cost_rate=override_cost_rate,
        )
        for row in trades.itertuples(index=False)
    ]
    frame = pd.DataFrame(rows)
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "parameters": {
                "max_exit_delay_days": int(max_exit_delay_days),
                "price_column": price_column,
                "output_return_column": output_return_column,
                "override_cost_rate": None if override_cost_rate is None else _number(override_cost_rate),
            },
            "summary": {
                "trade_count": int(len(frame)),
                "delayed_exit_trade_count": int((frame["delayed_exit_status"] == "delayed_exit").sum()) if len(frame) else 0,
                "same_day_exit_trade_count": int((frame["delayed_exit_status"] == "same_day_exit").sum()) if len(frame) else 0,
                "entry_blocked_trade_count": int((frame["delayed_exit_status"] == "entry_blocked").sum()) if len(frame) else 0,
                "unresolved_exit_trade_count": int((frame["delayed_exit_status"] == "unresolved_exit").sum()) if len(frame) else 0,
                "missing_price_trade_count": int(frame["delayed_exit_status"].astype(str).str.startswith("missing_").sum())
                if len(frame)
                else 0,
                "max_exit_delay_days_observed": int(frame["exit_delay_days"].max()) if len(frame) else 0,
                "total_delayed_exit_weighted_return": _number(frame[output_return_column].sum()) if len(frame) else 0.0,
            },
            "trade_rows": _frame_rows(frame),
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Delayed-exit repair is execution-stress evidence before full simulation packaging.",
            },
        }
    )


def write_delayed_exit_return_repair(output_dir: str | Path, result: Mapping[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(dict(result))
    trade_rows = sanitized.pop("trade_rows", [])
    (output / "delayed_exit_return_repair.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(trade_rows).to_csv(output / "delayed_exit_trade_rows.csv", index=False)


def _repair_trade_row(
    row: dict[str, Any],
    *,
    price_lookup: dict[tuple[str, Any], float],
    sell_dates_by_asset: dict[str, list[Any]],
    max_exit_delay_days: int,
    output_return_column: str,
    override_cost_rate: float | None,
) -> dict[str, Any]:
    asset_id = str(row.get("asset_id"))
    entry_date = pd.Timestamp(row.get("entry_date")).date()
    exit_date = pd.Timestamp(row.get("exit_date")).date()
    entry_allowed = _truthy(row.get("entry_allowed", True))
    output = dict(row)
    output["entry_date"] = entry_date.isoformat()
    output["exit_date"] = exit_date.isoformat()
    output["delayed_exit_date"] = exit_date.isoformat()
    output["exit_delay_days"] = 0
    output["delayed_exit_gross_return"] = 0.0
    output[output_return_column] = 0.0

    if not entry_allowed:
        output["delayed_exit_status"] = "entry_blocked"
        return _sanitize(output)

    entry_price = price_lookup.get((asset_id, entry_date))
    if entry_price is None or entry_price <= 0.0:
        output["delayed_exit_status"] = "missing_entry_price"
        return _sanitize(output)

    delayed_exit_date = _first_sellable_date(
        sell_dates_by_asset.get(asset_id, []),
        exit_date=exit_date,
        max_exit_delay_days=max_exit_delay_days,
        price_lookup=price_lookup,
        asset_id=asset_id,
    )
    if delayed_exit_date is None:
        output["delayed_exit_status"] = "unresolved_exit"
        return _sanitize(output)

    exit_price = price_lookup.get((asset_id, delayed_exit_date))
    if exit_price is None or exit_price <= 0.0:
        output["delayed_exit_status"] = "missing_exit_price"
        return _sanitize(output)

    gross_return = exit_price / entry_price - 1.0
    cost_rate = _number(row.get("cost_rate")) if override_cost_rate is None else _number(override_cost_rate)
    target_weight = _number(row.get("target_weight"))
    output["delayed_exit_date"] = delayed_exit_date.isoformat()
    output["exit_delay_days"] = int((delayed_exit_date - exit_date).days)
    output["delayed_exit_gross_return"] = _number(gross_return)
    output[output_return_column] = _number((gross_return - cost_rate) * target_weight)
    output["delayed_exit_status"] = "same_day_exit" if delayed_exit_date == exit_date else "delayed_exit"
    return _sanitize(output)


def _first_sellable_date(
    sell_dates: list[Any],
    *,
    exit_date: Any,
    max_exit_delay_days: int,
    price_lookup: dict[tuple[str, Any], float],
    asset_id: str,
) -> Any | None:
    max_date = exit_date + pd.Timedelta(days=max_exit_delay_days).to_pytimedelta()
    for candidate in sell_dates:
        if candidate < exit_date or candidate > max_date:
            continue
        if (asset_id, candidate) in price_lookup:
            return candidate
    return None


def _load_trades(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    frame = _read_frame_or_copy(source)
    required = {"asset_id", "entry_date", "exit_date", "target_weight"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"trades source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output["entry_date"] = pd.to_datetime(output["entry_date"], errors="coerce")
    output["exit_date"] = pd.to_datetime(output["exit_date"], errors="coerce")
    output["target_weight"] = pd.to_numeric(output["target_weight"], errors="coerce").fillna(0.0)
    if "cost_rate" not in output:
        output["cost_rate"] = 0.0
    output["cost_rate"] = pd.to_numeric(output["cost_rate"], errors="coerce").fillna(0.0)
    return output.dropna(subset=["asset_id", "entry_date", "exit_date"]).reset_index(drop=True)


def _load_bars(source: str | Path | pd.DataFrame, *, price_column: str) -> pd.DataFrame:
    frame = _read_frame_or_copy(source)
    required = {"asset_id", "date", price_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"bars source missing columns: {', '.join(missing)}")
    output = frame[["asset_id", "date", price_column]].copy()
    output = output.rename(columns={price_column: "price"})
    output["asset_id"] = output["asset_id"].astype(str)
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["price"] = pd.to_numeric(output["price"], errors="coerce")
    return output.dropna(subset=["asset_id", "date", "price"]).reset_index(drop=True)


def _load_masks(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    frame = _read_frame_or_copy(source)
    if "can_sell" not in frame and "exit_tradeable" not in frame:
        raise ValueError("masks source missing column: can_sell or exit_tradeable")
    sell_column = "can_sell" if "can_sell" in frame else "exit_tradeable"
    required = {"asset_id", "date", sell_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"masks source missing columns: {', '.join(missing)}")
    output = frame[["asset_id", "date", sell_column]].copy()
    output = output.rename(columns={sell_column: "can_sell"})
    output["asset_id"] = output["asset_id"].astype(str)
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["can_sell"] = output["can_sell"].map(_truthy)
    return output.dropna(subset=["asset_id", "date"]).reset_index(drop=True)


def _read_frame_or_copy(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        return source.copy()
    path = Path(source)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported source file type: {path.suffix}")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "t"}
    try:
        return bool(int(value))
    except (TypeError, ValueError, OverflowError):
        return bool(value)


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
