from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioConstraints:
    max_asset_weight: float = 1.0
    max_market_weight: float = 1.0
    max_gross_exposure: float = 1.0
    min_cash_weight: float = 0.0

    def __post_init__(self) -> None:
        values = {
            "max_asset_weight": self.max_asset_weight,
            "max_market_weight": self.max_market_weight,
            "max_gross_exposure": self.max_gross_exposure,
            "min_cash_weight": self.min_cash_weight,
        }
        invalid = [name for name, value in values.items() if value < 0.0 or value > 1.0]
        if invalid:
            raise ValueError(f"Portfolio constraint values must be between 0 and 1: {', '.join(invalid)}")
        if self.max_asset_weight == 0.0:
            raise ValueError("max_asset_weight must be positive")
        if self.max_market_weight == 0.0:
            raise ValueError("max_market_weight must be positive")
        if self.max_gross_exposure == 0.0:
            raise ValueError("max_gross_exposure must be positive")


def apply_portfolio_constraints(
    targets: pd.DataFrame,
    constraints: PortfolioConstraints,
) -> tuple[pd.DataFrame, float, list[str]]:
    required = ["asset_id", "market", "target_weight"]
    missing = [column for column in required if column not in targets.columns]
    if missing:
        raise ValueError(f"targets is missing columns: {', '.join(missing)}")

    frame = targets.copy()
    frame["target_weight"] = pd.to_numeric(frame["target_weight"], errors="coerce").fillna(0.0)
    if (frame["target_weight"] < 0.0).any():
        raise ValueError("target_weight cannot be negative")

    warnings: list[str] = []
    frame = frame[frame["target_weight"] > 0.0].copy()
    if frame.empty:
        return frame, 1.0, warnings

    before_asset = frame["target_weight"].copy()
    frame["target_weight"] = frame["target_weight"].clip(upper=constraints.max_asset_weight)
    if not frame["target_weight"].equals(before_asset):
        warnings.append("asset_weight_cap_applied")

    frame = _apply_market_cap(frame, constraints.max_market_weight, warnings)
    gross_cap = min(constraints.max_gross_exposure, max(0.0, 1.0 - constraints.min_cash_weight))
    gross = float(frame["target_weight"].sum())
    if gross > gross_cap and gross > 0.0:
        frame["target_weight"] = frame["target_weight"] * (gross_cap / gross)
        warnings.append("gross_exposure_cap_applied")

    total_weight = float(frame["target_weight"].sum())
    cash_weight = max(0.0, 1.0 - total_weight)
    return frame.sort_values(["market", "asset_id"]).reset_index(drop=True), cash_weight, warnings


def _apply_market_cap(frame: pd.DataFrame, max_market_weight: float, warnings: list[str]) -> pd.DataFrame:
    adjusted = frame.copy()
    applied = False
    for market, index in adjusted.groupby("market").groups.items():
        market_weight = float(adjusted.loc[index, "target_weight"].sum())
        if market_weight > max_market_weight and market_weight > 0.0:
            adjusted.loc[index, "target_weight"] = adjusted.loc[index, "target_weight"] * (max_market_weight / market_weight)
            applied = True
    if applied:
        warnings.append("market_weight_cap_applied")
    return adjusted
