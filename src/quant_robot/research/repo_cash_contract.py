"""One deliberately artificial repo contract. No market/account input adapter.

All customer settlement and availability clocks are model assumptions. Face plus
accrual NAV is not a market liquidation value or credit-risk certification.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
import hashlib
import json
import re


SOURCE = "artificial_only"
FIXTURE_TYPE = "synthetic_repo_cash_contract_fixture_v1"
CONTEXT = Context(prec=40, rounding=ROUND_HALF_EVEN, Emin=-999999,
                  Emax=999999, capitals=1, clamp=0,
                  flags=[], traps=[InvalidOperation, DivisionByZero, Overflow])
ZERO, CENT = Decimal("0"), Decimal("0.01")
NUMBER = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,18})?\Z")


class ContractError(ValueError):
    """Unsupported or inconsistent artificial fixture; nothing was executed."""


def _number(value: object, name: str, *, money: bool = False) -> Decimal:
    if type(value) is not str or NUMBER.fullmatch(value) is None:
        raise ContractError(f"{name}: explicit nonnegative plain decimal string required")
    result = Decimal(value)
    if not result.is_finite() or (money and result % CENT != ZERO):
        raise ContractError(f"{name}: finite cent-exact amount required")
    return result


def _date(value: object) -> date:
    if type(value) is not str:
        raise ContractError("artificial date string required")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError("invalid artificial date") from exc
    if result.year != 2001 or result.isoformat() != value:
        raise ContractError("only explicitly artificial 2001 dates supported")
    return result


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), timezone.utc)


def _clock(value: object) -> datetime:
    if type(value) is not str:
        raise ContractError("explicit artificial UTC clock required")
    try:
        result = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ContractError("invalid artificial clock") from exc
    if result.year != 2001 or _iso(result) != value:
        raise ContractError("only artificial 2001 UTC clocks supported")
    return result


def _iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _keys(value: object, keys: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ContractError(f"{name}: exact schema required")
    return value


def _next(calendar: list[date], day: date, *, inclusive: bool = False) -> date:
    choices = [d for d in calendar if d >= day] if inclusive else [d for d in calendar if d > day]
    if not choices:
        raise ContractError("artificial calendar does not cover required settlement/release")
    return choices[0]


def _prepare(fixture: object) -> dict:
    f = _keys(fixture, {"artifact_type", "source_nature", "currency", "initial_cash",
                       "calendar", "contract", "confirmations", "terminal_date"}, "fixture")
    if (f["artifact_type"], f["source_nature"], f["currency"]) != (FIXTURE_TYPE, SOURCE, "CNY"):
        raise ContractError("artificial-only fixture identity required")
    if _number(f["initial_cash"], "initial_cash", money=True) != Decimal("10000"):
        raise ContractError("fixed artificial initial capital is 10000 CNY")
    if type(f["calendar"]) is not list or not 2 <= len(f["calendar"]) <= 366:
        raise ContractError("explicit finite artificial calendar required")
    calendar = [_date(x) for x in f["calendar"]]
    if calendar != sorted(set(calendar)):
        raise ContractError("calendar must be strictly ordered and unique")
    c = _keys(f["contract"], {"id", "trade_date", "nominal_term_days", "principal",
                              "quote_per100_year", "entry_fee", "maturity_fee", "tax"}, "contract")
    if c["id"] != "ARTIFICIAL_REPO_001":
        raise ContractError("fixed artificial contract identity required")
    trade, terminal = _date(c["trade_date"]), _date(f["terminal_date"])
    if trade not in calendar or terminal not in calendar or terminal < trade:
        raise ContractError("trade and terminal must be covered artificial open dates")
    h = c["nominal_term_days"]
    if type(h) is not int or not 1 <= h <= 30:
        raise ContractError("explicit artificial term must be 1..30 natural days")
    amounts = {k: _number(c[k], k, money=k != "quote_per100_year")
               for k in ("principal", "quote_per100_year", "entry_fee", "maturity_fee", "tax")}
    if amounts["principal"] <= ZERO or amounts["principal"] % Decimal("1000"):
        raise ContractError("principal must be positive 1000 CNY face multiples")
    if amounts["quote_per100_year"] % Decimal("0.005"):
        raise ContractError("quote must use 0.005 CNY per100 annual increments")
    first = _at(_next(calendar, trade), 8)
    nominal = trade + timedelta(days=h)
    adjusted = _next(calendar, nominal, inclusive=True)
    maturity = _at(_next(calendar, adjusted), 8)
    days = (maturity.date() - first.date()).days
    if days <= 0:
        raise ContractError("positive fixed occupancy period required")
    total_raw = amounts["principal"] / Decimal("100") * amounts["quote_per100_year"] * days / Decimal("365")
    total_interest = total_raw.quantize(CENT, rounding=ROUND_HALF_UP)
    if type(f["confirmations"]) is not list or len(f["confirmations"]) > 20:
        raise ContractError("explicit bounded confirmation list required")
    payments, ids, clocks = [], set(), []
    totals = {k: ZERO for k in ("principal", "interest", "maturity_fee", "tax")}
    for p in f["confirmations"]:
        _keys(p, {"id", "confirmed_at", *totals}, "confirmation")
        if type(p["id"]) is not str or not re.fullmatch(r"ARTIFICIAL_PAYMENT_[0-9]{1,2}", p["id"]) or p["id"] in ids:
            raise ContractError("unique artificial confirmation ID required")
        ids.add(p["id"])
        at = _clock(p["confirmed_at"])
        if at < maturity or (clocks and at <= clocks[-1]):
            raise ContractError("confirmations must be ordered after fixed maturity")
        clocks.append(at)
        payment = {k: _number(p[k], k, money=True) for k in totals}
        if not any(payment.values()):
            raise ContractError("empty payment is not a confirmation")
        for k, v in payment.items():
            totals[k] += v
        payments.append({**payment, "id": p["id"], "at": at,
                         "available_at": _at(_next(calendar, at.date()), 1)})
    limits = {**amounts, "interest": total_interest}
    if any(v > limits[k] for k, v in totals.items()):
        raise ContractError("confirmation components exceed declared entitlements/charges")
    return {"fixture": deepcopy(f), "calendar": calendar, "trade": _at(trade, 1, 30),
            "first": first, "nominal": nominal, "adjusted": adjusted, "maturity": maturity,
            "terminal": _at(terminal, 9, 1), "days": days, "total_raw": total_raw,
            "total_interest": total_interest, "payments": payments, **amounts}


def _plain(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _context_record(ctx: Context) -> dict:
    return {"prec": ctx.prec, "rounding": ctx.rounding, "Emin": ctx.Emin,
            "Emax": ctx.Emax, "capitals": ctx.capitals, "clamp": ctx.clamp,
            "traps": {k.__name__: v for k, v in ctx.traps.items()},
            "flags": {k.__name__: v for k, v in ctx.flags.items()}}


class _Ledger:
    def __init__(self, prepared: dict):
        self.p = prepared
        self.cash = Decimal("10000")
        self.reserved = self.locked = self.interest = self.accrued = ZERO
        self.paid_interest = self.paid_entry = self.paid_fee = self.paid_tax = ZERO
        self.payable_fee = self.payable_tax = ZERO
        self.releases: dict[str, Decimal] = {}
        self.accepted = self.settled = self.matured = False
        self.peak = self.reference = self.cash
        self.max_dd = ZERO
        self.paused = False
        self.cooldown = 0
        self.start_flat = True
        self.day_triggered = False
        self.events, self.observations, self.breaches = [], [], []

    def nav(self):
        return self.cash + self.locked + self.interest - self.payable_fee - self.payable_tax

    def flat(self):
        return not any((self.locked, self.interest, self.reserved, self.payable_fee,
                        self.payable_tax, *self.releases.values()))

    def snapshot(self):
        unavailable = sum(self.releases.values(), ZERO)
        available = self.cash - self.reserved - unavailable
        if min(self.cash, available, self.reserved, self.locked, self.interest,
               self.payable_fee, self.payable_tax) < ZERO:
            raise ContractError("negative cash/subledger balance")
        return _plain({"cash": self.cash, "available": available, "withdrawable": None,
                       "reserved": self.reserved, "unreleased_cash": unavailable,
                       "locked_principal": self.locked, "interest_receivable": self.interest,
                       "accrued_total": self.accrued, "interest_paid": self.paid_interest,
                       "entry_fee_paid": self.paid_entry, "maturity_fee_paid": self.paid_fee,
                       "tax_paid": self.paid_tax, "payable_fee": self.payable_fee,
                       "payable_tax": self.payable_tax, "conditional_book_NAV": self.nav(),
                       "continuous_peak": self.peak, "maximum_observed_drawdown": self.max_dd,
                       "day_reference": self.reference, "paused": self.paused,
                       "complete_flat_days": self.cooldown, "economic_flat": self.flat()})

    def accrue(self, at):
        if not self.settled:
            return
        if at >= self.p["maturity"]:
            total = self.p["total_interest"]
        else:
            days = max(0, (at.date() - self.p["first"].date()).days)
            total = self.p["principal"] / Decimal("100") * self.p["quote_per100_year"] * days / Decimal("365")
        self.accrued = total
        self.interest = total - self.paid_interest

    def risk(self, at, phase):
        nav = self.nav()
        self.peak = max(self.peak, nav)
        dd = Decimal("1") - nav / self.peak
        loss = Decimal("1") - nav / self.reference if self.reference > ZERO else ZERO
        self.max_dd = max(self.max_dd, dd)
        failures = []
        if loss >= Decimal("0.02"):
            failures.append("daily_loss_2_percent")
        if dd >= Decimal("0.40") and not self.flat():
            failures.append("global_drawdown_40_percent_with_unsettled_contract")
        if failures:
            self.paused = True
            self.cooldown = 0
            self.day_triggered = True
            self.breaches.append(_plain({"at": at, "phase": phase, "failures": failures,
                                        "NAV": nav, "drawdown": dd, "daily_loss": loss,
                                        "forced_exit": False}))
        self.observations.append(_plain({"at": at, "phase": phase, "NAV": nav,
                                        "drawdown": dd, "daily_loss": loss,
                                        "peak": self.peak, "day_reference": self.reference,
                                        "failures": failures}))

    def apply(self, kind, at, payload):
        if kind == "day_start":
            self.start_flat = self.flat()
            self.day_triggered = False
            return "day_started"
        if kind == "trade":
            required = sum((self.p[k] for k in ("principal", "entry_fee", "maturity_fee", "tax")), ZERO)
            if self.paused or required > self.cash:
                return "order_rejected_insufficient_available_cash_or_risk"
            self.reserved = required
            self.accepted = True
            return "reserved_not_yet_settled"
        if kind == "first_settlement":
            if not self.accepted:
                return "skipped_no_accepted_contract"
            paid = self.p["principal"] + self.p["entry_fee"]
            self.cash -= paid
            self.reserved -= paid
            self.locked = self.p["principal"]
            self.paid_entry = self.p["entry_fee"]
            self.settled = True
            return "principal_transferred_entry_fee_paid_once"
        if kind == "maturity":
            if not self.settled:
                return "skipped_no_settled_contract"
            self.payable_fee, self.payable_tax = self.p["maturity_fee"], self.p["tax"]
            self.matured = True
            return "charges_recognized_no_automatic_receipt"
        if kind == "confirmation":
            if not self.matured:
                return "rejected_no_matured_contract"
            p = payload
            if any(p[k] > v for k, v in (("principal", self.locked), ("interest", self.interest),
                                         ("maturity_fee", self.payable_fee), ("tax", self.payable_tax))):
                raise ContractError("payment exceeds current outstanding component")
            net = p["principal"] + p["interest"] - p["maturity_fee"] - p["tax"]
            if self.cash + net < ZERO:
                raise ContractError("negative net receipt cannot borrow cash")
            self.cash += net
            self.locked -= p["principal"]
            self.interest -= p["interest"]
            self.paid_interest += p["interest"]
            self.payable_fee -= p["maturity_fee"]
            self.payable_tax -= p["tax"]
            self.reserved -= p["maturity_fee"] + p["tax"]
            self.paid_fee += p["maturity_fee"]
            self.paid_tax += p["tax"]
            self.releases[p["id"]] = max(net, ZERO)
            return "modeled_components_received_once"
        if kind == "available":
            self.releases.pop(payload["id"], None)
            return "cash_attribute_released_no_new_income"
        if kind == "close":
            if self.paused and self.start_flat and self.flat() and not self.day_triggered:
                self.cooldown += 1
                if self.cooldown >= 5:
                    self.paused = False
            self.reference = self.nav()
            return "daily_reference_updated_no_new_contract"
        raise ContractError("unsupported event")

    def run(self):
        p = self.p
        events = [(p["trade"], 20, "trade", {}), (p["first"], 30, "first_settlement", {}),
                  (p["maturity"], 40, "maturity", {})]
        for payment in p["payments"]:
            events.extend([(payment["at"], 50, "confirmation", payment),
                           (payment["available_at"], 10, "available", payment)])
        for day in p["calendar"]:
            if p["trade"].date() <= day <= p["terminal"].date():
                events.extend([(_at(day, 0), 0, "day_start", {}), (_at(day, 9), 90, "close", {})])
        for at, _, kind, payload in sorted(events, key=lambda x: (x[0], x[1])):
            if at > p["terminal"]:
                continue
            before = self.snapshot()
            self.accrue(at)
            if kind != "day_start":
                self.risk(at, f"before_{kind}")
            accrued = self.snapshot()
            status = self.apply(kind, at, payload)
            if kind not in ("day_start", "close"):
                self.risk(at, f"after_{kind}")
            after = self.snapshot()
            self.events.append(_plain({"at": at, "kind": kind, "status": status,
                                       "payload": payload, "before": before,
                                       "after_accrual_before_event": accrued, "after": after}))
        terminal = self.snapshot()
        return {"events": self.events, "observations": self.observations,
                "risk_breaches": self.breaches,
                "summary": {"accepted": self.accepted, "settled": self.settled,
                            "matured": self.matured, "terminal_at": _iso(p["terminal"]),
                            "terminal": terminal, "terminal_unsettled": not self.flat(),
                            "forced_terminal_liquidation": False,
                            "late_payment_extra_interest": "0",
                            "conditional_book_profit": format(self.nav() - Decimal("10000"), "f"),
                            "net_paid_interest_less_all_paid_charges": format(self.paid_interest - self.paid_entry - self.paid_fee - self.paid_tax, "f"),
                            "contracts_attempted": 1, "automatic_reinvestments": 0}}


def run_synthetic_contract(fixture: dict) -> dict:
    """Validate and run explicit fictional 2001 values; never accept real evidence."""
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags()
        p = _prepare(fixture)
        result = _Ledger(p).run()
        result.update({"artifact_type": "synthetic_repo_cash_contract_result_v1",
                       "source_nature": SOURCE, "currency": "CNY", "qualified": False,
                       "real_forward": 0, "historical_returns_computed": False,
                       "fixture_sha256": hashlib.sha256(json.dumps(fixture, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
                       "model_clocks": _plain({k: p[k] for k in ("trade", "first", "nominal", "adjusted", "maturity", "terminal", "days")}),
                       "contract_interest": _plain({"unrounded": p["total_raw"], "rounded_once_at_E": p["total_interest"]}),
                       "limitations": ["All inputs deliberately artificial; no real quote or account.",
                           "Customer T+1 and next-session availability are model assumptions, not certified actual cash clocks.",
                           "Face plus accrual NAV assumes normal performance and does not certify credit/liquidity risk.",
                           "Delayed payment does not extend fixed E or add unknown penalty interest.",
                           "Withdrawable cash unknown; no automatic reinvestment or early exit."],
                       "decimal_context": _context_record(ctx)})
        return result


def synthetic_fixture() -> dict:
    """Fixed invented example; numbers are not market data or retail fee claims."""
    calendar = [(date(2001, 1, 1) + timedelta(days=i)).isoformat()
                for i in range(31) if (date(2001, 1, 1) + timedelta(days=i)).weekday() < 5]
    return {"artifact_type": FIXTURE_TYPE, "source_nature": SOURCE, "currency": "CNY",
            "initial_cash": "10000", "calendar": calendar,
            "contract": {"id": "ARTIFICIAL_REPO_001", "trade_date": "2001-01-04",
                         "nominal_term_days": 1, "principal": "9000", "quote_per100_year": "3.65",
                         "entry_fee": "0.20", "maturity_fee": "0.10", "tax": "0.05"},
            "confirmations": [{"id": "ARTIFICIAL_PAYMENT_1", "confirmed_at": "2001-01-08T08:01:00Z",
                               "principal": "9000", "interest": "2.70", "maturity_fee": "0.10", "tax": "0.05"}],
            "terminal_date": "2001-01-16"}
