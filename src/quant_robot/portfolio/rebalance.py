from __future__ import annotations

import math

import pandas as pd


FORBIDDEN_REAL_ACCOUNT_COLUMNS = {
    "account",
    "account_id",
    "broker",
    "broker_id",
    "client_id",
    "order_id",
}


def build_rebalance_plan(
    targets: pd.DataFrame,
    current_positions: pd.DataFrame,
    latest_prices: pd.DataFrame,
    portfolio_value: float,
) -> pd.DataFrame:
    _validate_research_only(current_positions)
    _require_columns(targets, ["asset_id", "market", "target_weight"], "targets")
    _require_columns(current_positions, ["asset_id", "quantity"], "current_positions")
    _require_columns(latest_prices, ["asset_id", "latest_price"], "latest_prices")
    if portfolio_value <= 0.0 or not math.isfinite(portfolio_value):
        raise ValueError("portfolio_value must be positive")

    target_frame = targets.copy()
    target_frame["target_weight"] = pd.to_numeric(target_frame["target_weight"], errors="coerce").fillna(0.0)
    if (target_frame["target_weight"] < 0.0).any():
        raise ValueError("target_weight cannot be negative")
    if float(target_frame["target_weight"].sum()) > 1.0 + 1e-9:
        raise ValueError("target weights cannot exceed 100%")

    price_lookup = _price_lookup(target_frame, latest_prices)
    target_lookup = target_frame.set_index("asset_id").to_dict(orient="index")
    position_lookup = current_positions.set_index("asset_id")["quantity"].to_dict()
    asset_ids = sorted(set(target_lookup) | set(position_lookup))

    rows = []
    for asset_id in asset_ids:
        latest_price = price_lookup.get(asset_id)
        if latest_price is None or latest_price <= 0.0:
            raise ValueError(f"Missing positive latest_price for {asset_id}")
        target = target_lookup.get(asset_id, {})
        current_quantity = float(position_lookup.get(asset_id, 0.0))
        target_weight = float(target.get("target_weight", 0.0))
        current_value = current_quantity * latest_price
        current_weight = current_value / portfolio_value
        target_value = target_weight * portfolio_value
        delta_value = target_value - current_value
        rows.append(
            {
                "asset_id": asset_id,
                "market": str(target.get("market", "")),
                "latest_price": latest_price,
                "current_quantity": current_quantity,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "current_value": current_value,
                "target_value": target_value,
                "delta_value": delta_value,
                "estimated_quantity_delta": delta_value / latest_price,
                "action": _action(delta_value),
                "intent_type": "research_rebalance_plan",
                "executable": False,
                "safety_note": "Research-only advisory plan. No broker routing or order placement.",
            }
        )
    return pd.DataFrame(rows).sort_values(["asset_id"]).reset_index(drop=True)


def _validate_research_only(frame: pd.DataFrame) -> None:
    forbidden = sorted(FORBIDDEN_REAL_ACCOUNT_COLUMNS & set(frame.columns))
    if forbidden:
        raise ValueError("current_positions contains real account or broker columns: " + ", ".join(forbidden))


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _price_lookup(targets: pd.DataFrame, latest_prices: pd.DataFrame) -> dict[str, float]:
    prices = latest_prices.copy()
    if "latest_price" in targets.columns:
        target_prices = targets[["asset_id", "latest_price"]].dropna()
        prices = pd.concat([prices, target_prices], ignore_index=True)
    prices["latest_price"] = pd.to_numeric(prices["latest_price"], errors="coerce")
    return prices.dropna(subset=["latest_price"]).drop_duplicates("asset_id", keep="last").set_index("asset_id")["latest_price"].to_dict()


def _action(delta_value: float) -> str:
    if abs(delta_value) < 1e-9:
        return "hold"
    return "increase" if delta_value > 0.0 else "decrease"
