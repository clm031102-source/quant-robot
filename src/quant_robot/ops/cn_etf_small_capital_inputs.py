from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


EXTERNAL_BOUNDARY_KEYS = (
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


@dataclass(frozen=True)
class SmallCapitalInputs:
    minimum_capital_cny: float
    maximum_capital_cny: float
    commission_bps_per_side: float
    slippage_bps_per_side: float
    minimum_commission_cny_stress: float
    absolute_max_drawdown: float
    paper_promotion_max_drawdown: float
    max_holding_sessions: int
    max_single_position_cny: float
    max_daily_loss_cny: float
    max_one_way_adv_participation: float
    minimum_paper_days: int
    minimum_paper_fills: int
    minimum_market_regimes: int

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SmallCapitalInputs":
        if payload.get("schema_version") != 1:
            raise ValueError("schema_version must be 1")
        if payload.get("as_of_date") != "2026-07-29":
            raise ValueError("as_of_date must be frozen as 2026-07-29")
        capital = payload.get("capital_cny")
        if not isinstance(capital, Mapping):
            raise ValueError("capital_cny must be an object")
        minimum_capital = _number(capital.get("minimum"), "capital_cny.minimum")
        maximum_capital = _number(capital.get("maximum"), "capital_cny.maximum")
        if minimum_capital != 1000.0 or maximum_capital != 3000.0:
            raise ValueError("capital_cny must remain frozen at CNY 1,000-3,000")

        commission = _nonnegative(
            payload.get("commission_bps_per_side"),
            "commission_bps_per_side",
        )
        slippage = _nonnegative(
            payload.get("slippage_bps_per_side"),
            "slippage_bps_per_side",
        )
        minimum_commission = _nonnegative(
            payload.get("minimum_commission_cny_stress"),
            "minimum_commission_cny_stress",
        )
        absolute_drawdown = _number(
            payload.get("absolute_max_drawdown"),
            "absolute_max_drawdown",
        )
        if not 0.0 < absolute_drawdown <= 0.40:
            raise ValueError("absolute_max_drawdown must be in (0, 0.40]")
        paper_drawdown = _number(
            payload.get("paper_promotion_max_drawdown"),
            "paper_promotion_max_drawdown",
        )
        if not 0.0 < paper_drawdown <= 0.08:
            raise ValueError("paper_promotion_max_drawdown must be in (0, 0.08]")
        max_holding = _integer(payload.get("max_holding_sessions"), "max_holding_sessions")
        if not 1 <= max_holding <= 252:
            raise ValueError("max_holding_sessions must be between 1 and 252")
        max_position = _positive(
            payload.get("max_single_position_cny"),
            "max_single_position_cny",
        )
        if max_position > maximum_capital:
            raise ValueError("max_single_position_cny cannot exceed maximum capital")
        max_daily_loss = _positive(payload.get("max_daily_loss_cny"), "max_daily_loss_cny")
        participation = _number(
            payload.get("max_one_way_adv_participation"),
            "max_one_way_adv_participation",
        )
        if not 0.0 < participation <= 0.01:
            raise ValueError("max_one_way_adv_participation must be in (0, 0.01]")
        minimum_paper_days = _integer(
            payload.get("minimum_paper_days"),
            "minimum_paper_days",
        )
        minimum_paper_fills = _integer(
            payload.get("minimum_paper_fills"),
            "minimum_paper_fills",
        )
        minimum_market_regimes = _integer(
            payload.get("minimum_market_regimes"),
            "minimum_market_regimes",
        )
        if minimum_paper_days < 20:
            raise ValueError("minimum_paper_days cannot be below 20")
        if minimum_paper_fills < 30:
            raise ValueError("minimum_paper_fills cannot be below 30")
        if minimum_market_regimes < 2:
            raise ValueError("minimum_market_regimes cannot be below 2")
        boundaries = payload.get("boundaries")
        if not isinstance(boundaries, Mapping) or set(boundaries) != set(
            EXTERNAL_BOUNDARY_KEYS
        ):
            raise ValueError("boundaries do not match the external execution contract")
        for key in EXTERNAL_BOUNDARY_KEYS:
            if boundaries.get(key) is not False:
                raise ValueError(f"{key} must remain false")
        return cls(
            minimum_capital_cny=minimum_capital,
            maximum_capital_cny=maximum_capital,
            commission_bps_per_side=commission,
            slippage_bps_per_side=slippage,
            minimum_commission_cny_stress=minimum_commission,
            absolute_max_drawdown=absolute_drawdown,
            paper_promotion_max_drawdown=paper_drawdown,
            max_holding_sessions=max_holding,
            max_single_position_cny=max_position,
            max_daily_loss_cny=max_daily_loss,
            max_one_way_adv_participation=participation,
            minimum_paper_days=minimum_paper_days,
            minimum_paper_fills=minimum_paper_fills,
            minimum_market_regimes=minimum_market_regimes,
        )

    def round_trip_cost_bps(
        self,
        notional_cny: float,
        *,
        minimum_fee_cny: float = 0.0,
    ) -> float:
        notional = _positive(notional_cny, "notional_cny")
        minimum_fee = _nonnegative(minimum_fee_cny, "minimum_fee_cny")
        proportional_commission = (
            notional * self.commission_bps_per_side / 10_000.0
        )
        commission_cny = 2.0 * max(proportional_commission, minimum_fee)
        commission_bps = commission_cny / notional * 10_000.0
        return commission_bps + 2.0 * self.slippage_bps_per_side


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return int(value)


def _positive(value: Any, label: str) -> float:
    numeric = _number(value, label)
    if numeric <= 0.0:
        raise ValueError(f"{label} must be positive")
    return numeric


def _nonnegative(value: Any, label: str) -> float:
    numeric = _number(value, label)
    if numeric < 0.0:
        raise ValueError(f"{label} must be non-negative")
    return numeric
