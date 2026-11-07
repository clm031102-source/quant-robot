"""One fixed USD whole-share affordability comparison; no source or account I/O."""
from __future__ import annotations

import re
from decimal import (
    Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)

ASSETS = ("SPY", "EFA", "IEF", "GLD", "SPYM", "GLDM")
BASKETS = {"old": ("SPY", "EFA", "IEF", "GLD"),
           "proposed": ("SPYM", "EFA", "IEF", "GLDM")}
COSTS = {"primary": (100, 10), "stress": (250, 30)}
BUDGET_CENTS = 24750
CAPITAL_CENTS = 100000
RESERVE_CENTS = 1000
_PRICE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z", re.ASCII)


def _context() -> Context:
    return Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999,
                   Emax=999999, capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def _money(cents: int) -> str:
    """Exact cents formatting, including amounts too large for Context50."""
    return f"{cents // 100}.{cents % 100:02d}"


def _fee_cents(quantity: int, minimum_cents: int) -> int:
    # USD0.005/share is half a cent; commission rounds upward once per order.
    return 0 if quantity == 0 else max(minimum_cents, (quantity + 1) // 2)


def _buy_price_cents(price: Decimal, slippage_bps: int) -> int:
    # Exact rational ceiling prevents precision rounding before the cent ceiling.
    # The economic value/ratio reporting below uses the declared Context50.
    numerator, denominator = price.as_integer_ratio()
    scaled = numerator * (10000 + slippage_bps) * 100
    divisor = denominator * 10000
    return (scaled + divisor - 1) // divisor


def _leg(symbol: str, price: Decimal, minimum_cents: int,
         slippage_bps: int) -> dict:
    buy_cents = _buy_price_cents(price, slippage_bps)

    def total(q: int) -> int:
        return q * buy_cents + _fee_cents(q, minimum_cents)

    low, high = 0, BUDGET_CENTS // buy_cents
    while low < high:
        middle = (low + high + 1) // 2
        if total(middle) <= BUDGET_CENTS:
            low = middle
        else:
            high = middle - 1
    quantity = low
    spent = total(quantity)
    next_spent = total(quantity + 1)
    if not (spent <= BUDGET_CENTS < next_spent):
        raise ArithmeticError("maximal_integer_quantity")
    mark = price * quantity
    weight = mark / Decimal("1000")
    return {
        "symbol": symbol,
        "quantity": quantity,
        "zero_share": quantity == 0,
        "independent_budget_usd": "247.50",
        "buy_price_usd": _money(buy_cents),
        "commission_usd": _money(_fee_cents(quantity, minimum_cents)),
        "fill_notional_usd": _money(quantity * buy_cents),
        "cash_spent_usd": _money(spent),
        "budget_remainder_usd": _money(BUDGET_CENTS - spent),
        "economic_exposure_usd": format(mark, "f"),
        "economic_weight": format(weight, "f"),
        "target_weight_deviation": format(weight - Decimal("0.25"), "f"),
        "next_quantity": quantity + 1,
        "next_quantity_cost_usd": _money(next_spent),
        "next_quantity_infeasible": True,
    }


def calculate(prices: dict[str, str]) -> dict:
    """Compare two fixed baskets under two costs using six exact price strings.

    Input syntax is unsigned ordinary decimal notation, without whitespace,
    exponents, commas or leading zeroes (except the single integer zero).
    All values must be finite and strictly positive. One-share increments and
    all costs are conditional model assumptions, not brokerage certification.
    """
    if not isinstance(prices, dict) or set(prices) != set(ASSETS):
        raise ValueError("exact_six_symbols_required")
    with localcontext(_context()) as context:
        parsed = {}
        for symbol in ASSETS:
            literal = prices[symbol]
            if not isinstance(literal, str) or _PRICE.fullmatch(literal) is None:
                raise ValueError(f"strict_decimal_price:{symbol}")
            value = Decimal(literal)
            if not value.is_finite() or value <= 0:
                raise ValueError(f"positive_finite_price:{symbol}")
            parsed[symbol] = value

        results = {}
        for basket, symbols in BASKETS.items():
            for cost, (minimum_cents, slippage_bps) in COSTS.items():
                legs = [_leg(s, parsed[s], minimum_cents, slippage_bps)
                        for s in symbols]
                # Conservation is independently accumulated in integer cents.
                fill_cents = sum(
                    _buy_price_cents(parsed[s], slippage_bps) * leg["quantity"]
                    for s, leg in zip(symbols, legs)
                )
                fee_cents = sum(_fee_cents(leg["quantity"], minimum_cents)
                                for leg in legs)
                spent_cents = fill_cents + fee_cents
                cash_cents = CAPITAL_CENTS - spent_cents
                if cash_cents < RESERVE_CENTS:
                    raise ArithmeticError("reserved_cash_spent")
                economic = sum((parsed[s] * leg["quantity"]
                                for s, leg in zip(symbols, legs)), Decimal(0))
                results[f"{basket}_{cost}"] = {
                    "basket": basket,
                    "cost_case": cost,
                    "minimum_order_commission_usd": _money(minimum_cents),
                    "slippage_bps": str(slippage_bps),
                    "per_share_commission_usd": "0.005",
                    "legs": legs,
                    "summary": {
                        "economic_exposure_usd": format(economic, "f"),
                        "economic_deployment_ratio": format(
                            economic / Decimal("1000"), "f"),
                        "fill_notional_usd": _money(fill_cents),
                        "fill_notional_deployment_ratio": format(
                            Decimal(fill_cents) / Decimal(CAPITAL_CENTS), "f"),
                        "commission_usd": _money(fee_cents),
                        "cash_spent_usd": _money(spent_cents),
                        "cash_remaining_usd": _money(cash_cents),
                        "reserved_cash_usd": "10.00",
                        "unused_leg_budget_usd": _money(cash_cents - RESERVE_CENTS),
                        "zero_share_legs": sum(leg["zero_share"] for leg in legs),
                        "all_four_targets_nonzero": all(leg["quantity"] > 0 for leg in legs),
                        "cash_conservation_checked": True,
                    },
                }
        return {
            "schema": "us_unit_feasibility_result_v1",
            "evidence_kind": "single_close_conditional_whole_share_affordability",
            "capital_usd": "1000.00",
            "reserved_cash_usd": "10.00",
            "independent_budget_per_leg_usd": "247.50",
            "input_prices": {s: prices[s] for s in ASSETS},
            "results": results,
            "arithmetic": {
                "decimal_precision": context.prec,
                "decimal_rounding": context.rounding,
                "Emin": context.Emin, "Emax": context.Emax,
                "capitals": context.capitals, "clamp": context.clamp,
                "traps": sorted(k.__name__ for k, enabled in context.traps.items() if enabled),
                "flags": sorted(k.__name__ for k, enabled in context.flags.items() if enabled),
                "buy_price_and_commission": "exact integer/rational ceil to cents",
                "quantity": "integer maximality with q+1 infeasibility",
            },
            "account_count": 0,
            "return_computed": False,
            "qualified": False,
            "real_forward_days": 0,
            "live_boundary_allowed": False,
        }
