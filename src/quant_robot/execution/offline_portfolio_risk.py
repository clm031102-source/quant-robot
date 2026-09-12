"""Shared book valuation and conservative pending-order cost projection."""
from __future__ import annotations

from decimal import Decimal

from .offline_order_state import ACTIVE, ZERO, commission, dividend_receivable, money_context


@money_context
def portfolio_totals(state, marks, additional_orders=()):
    exposure = {key: qty * marks[key] for key, qty in state["positions"].items() if qty}
    pending_cost = ZERO
    for row in [*state["orders"].values(), *additional_orders]:
        if row["status"] not in ACTIVE:
            continue
        qty = row["quantity"] - row["filled_quantity"]
        price, key = row["limit_price"], row["symbol"]
        pending_cost += max(ZERO, commission(state, row["filled_notional"] + qty * price) - row["commission"])
        if row["side"] == "BUY":
            exposure[key] = exposure.get(key, ZERO) + qty * max(price, marks[key])
            pending_cost += qty * max(ZERO, price - marks[key])
        else:
            pending_cost += qty * max(ZERO, marks[key] - price)
    receivable = dividend_receivable(state)
    equity = state["cash"] + receivable + sum((qty * marks[key] for key, qty in state["positions"].items() if qty), ZERO)
    return {"equity": equity, "exposure": exposure, "gross": sum(exposure.values(), ZERO),
        "pending_cost": pending_cost, "dividend_receivable": receivable,
        "projected_loss": Decimal(state["risk_session"]["opening_equity"]) - equity + pending_cost}
