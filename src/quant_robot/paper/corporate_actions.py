"""Offline cash dividends and share conversions, with explicit unsettled rights.

Source completeness is a separate audit. A supplied event file is never itself
proof that prices are raw or that the corporate-action history is complete.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any


class CorporateActionLedger:
    def __init__(self, path: Path | None, assets: set[str], dates: list[date], positions: dict[str, float]):
        self.events: list[dict[str, Any]] = []
        self.fingerprint: str | None = None
        self.journal: list[dict[str, Any]] = []
        self.receivables: dict[str, float] = {}
        self.entitlements: dict[str, float] = {}
        self.processed: set[str] = set()
        self.paid: set[str] = set()
        self.locked: dict[str, list[tuple[date, float]]] = {}
        self.dividend_cash_received = 0.0
        self.source_ref: str | None = None
        self.first_date = dates[0]
        if path is not None:
            raw = Path(path).read_bytes()
            # V2 share ratios must retain the decimal declared in the event file.
            # Event validation still normalizes legacy V1 amounts to float.
            data = json.loads(raw, parse_float=Decimal)
            self.events = _validate_dataset(data, assets, dates)
            self.fingerprint = hashlib.sha256(raw).hexdigest()
            self.source_ref = data["source_ref"]
        for event in self.events:
            asset = event["asset_id"]
            if event["kind"] == "cash_dividend" and event["record_date"] < dates[0]:
                if event["pay_date"] >= dates[0] and positions.get(asset, 0):
                    raise ValueError("initial dividend entitlement before simulation window is unknown")
                self.entitlements[event["event_id"]] = 0.0
            elif event["kind"] == "share_split" and event["ex_date"] <= dates[0]:
                self.processed.add(event["event_id"])
                if event["tradable_date"] > dates[0]:
                    self.locked.setdefault(asset, []).append((event["tradable_date"], positions.get(asset, 0.0)))

    @property
    def receivable(self) -> float:
        return sum(self.receivables.values())

    def record_close(self, session: date, positions: dict[str, float]) -> None:
        for event in self.events:
            if event["kind"] == "cash_dividend" and event["record_date"] == session:
                event_id = event["event_id"]
                if event_id not in self.entitlements:
                    quantity = positions.get(event["asset_id"], 0.0)
                    if quantity < 0:
                        raise ValueError("short dividend liabilities are not supported by the cash ledger")
                    self.entitlements[event_id] = quantity
                    self._record("dividend_entitlement", event, session, quantity=quantity)

    def before_session(self, session: date, positions: dict[str, float], intents: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
        adjusted = [dict(intent) for intent in intents]
        for event in self.events:
            event_id = event["event_id"]
            if event_id in self.processed or event["ex_date"] > session:
                continue
            asset = event["asset_id"]
            if event["kind"] == "cash_dividend":
                if event_id not in self.entitlements:
                    raise ValueError("dividend record-date holdings were not observed")
                quantity = self.entitlements[event_id]
                amount = float((Decimal(str(quantity)) * Decimal(str(event["net_cash_per_share"]))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP))
                self.receivables[event_id] = amount
                self._record("dividend_receivable", event, session, quantity=quantity, amount=amount)
            else:
                ratio = event["share_ratio"]
                old_quantity = positions.get(asset, 0.0)
                rounding_evidence = {}
                if "share_rounding" in event:
                    new_quantity, rounding_evidence = _convert_whole_shares(old_quantity, event)
                else:
                    new_quantity = old_quantity * ratio
                if "share_rounding" not in event and asset.startswith("CN_ETF_"):
                    if not math.isclose(new_quantity, round(new_quantity), rel_tol=0, abs_tol=1e-9):
                        raise ValueError("fractional ETF share conversion requires an explicit cash-in-lieu model")
                    new_quantity = float(round(new_quantity))
                adjusted = _convert_intents(adjusted, event, old_quantity, new_quantity)
                if old_quantity:
                    positions[asset] = new_quantity
                if event["tradable_date"] > session:
                    self.locked.setdefault(asset, []).append((event["tradable_date"], new_quantity))
                self._record("share_conversion", event, session, old_quantity=old_quantity,
                             quantity=new_quantity, **rounding_evidence)
            self.processed.add(event_id)
        adjusted = self._limit_sales_to_available_holdings(session, positions, adjusted)
        return self._pay(session, include_today=False), adjusted

    def after_session(self, session: date, positions: dict[str, float]) -> float:
        self.record_close(session, positions)
        # Date-only payment data does not establish pre-trade intraday availability.
        return self._pay(session, include_today=True)

    def require_post_action_prices(self, session: date, positions: dict[str, float], price_dates: dict[str, str]) -> None:
        for event in self.events:
            asset = event["asset_id"]
            if event["ex_date"] <= session and positions.get(asset, 0.0):
                if asset not in price_dates or _date(price_dates[asset]) < event["ex_date"]:
                    raise ValueError(f"post-action valuation price missing for {asset}")

    def evidence(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref, "corporate_actions_fingerprint": self.fingerprint,
            "event_count": len(self.events), "declared_coverage_validated": self.fingerprint is not None,
            "source_audit_verified": False,
            "blocking_reasons": ["raw_price_source_not_audited",
                "corporate_action_source_not_audited" if self.fingerprint else "corporate_action_source_missing"],
            "cash_payment_timing": "after_pay_date_close",
            "cash_rounding": "per_entitlement_half_up_0.01_unverified_for_broker",
            "execution_price_assumption": "next_available_session_raw_close_plus_slippage",
        }

    def _pay(self, session: date, *, include_today: bool) -> float:
        cash = 0.0
        for event in self.events:
            event_id = event["event_id"]
            if event["kind"] != "cash_dividend" or event_id not in self.receivables or event_id in self.paid:
                continue
            if event["pay_date"] > session or (event["pay_date"] == session and not include_today):
                continue
            amount = self.receivables.pop(event_id)
            cash += amount
            self.paid.add(event_id)
            self._record("dividend_cash_payment", event, session, amount=amount)
        self.dividend_cash_received += cash
        return cash

    def _limit_sales_to_available_holdings(self, session: date, positions: dict[str, float], intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed = []
        for intent in intents:
            if intent["signed_quantity"] < 0:
                asset = intent["asset_id"]
                locked = sum(quantity for until, quantity in self.locked.get(asset, []) if session < until)
                available = max(0.0, positions.get(asset, 0.0) - locked)
                intent["available_sell_quantity"] = available
                requested = abs(intent["signed_quantity"])
                quantity = min(requested, available)
                if quantity < requested:
                    self.journal.append({"event_type": "unavailable_shares_blocked_sale", "date": str(session),
                        "asset_id": asset, "intent_id": intent["intent_id"],
                        "requested_quantity": requested, "available_quantity": available})
                    intent["signed_quantity"] = -quantity
                    intent["intended_quantity"] = quantity
                if quantity == 0:
                    continue
            allowed.append(intent)
        return allowed

    def _record(self, kind: str, event: dict[str, Any], session: date, **values: Any) -> None:
        self.journal.append({"event_type": kind, "event_id": event["event_id"],
                             "asset_id": event["asset_id"], "date": str(session), **values})


def _convert_intents(intents: list[dict[str, Any]], event: dict[str, Any], old_quantity: float,
                     new_quantity: float) -> list[dict[str, Any]]:
    adjusted = [dict(intent) for intent in intents]
    matching = [intent for intent in adjusted if intent["asset_id"] == event["asset_id"]]
    explicit = "share_rounding" in event
    sales = [intent for intent in matching if intent["signed_quantity"] < 0]
    if explicit and _sum_sale_quantities(sales) > Decimal(str(old_quantity)):
        raise ValueError("aggregate pending sales exceed the holder's pre-conversion holdings")
    for intent in matching:
        full_sale = (explicit and len(sales) == 1 and old_quantity > 0
                     and intent["signed_quantity"] == -old_quantity)
        for field in ("signed_quantity", "intended_quantity", "reference_price"):
            value = intent[field]
            if explicit:
                number, ratio = Decimal(str(value)), Decimal(event["share_ratio_exact"])
                with localcontext() as context:
                    context.prec = max(28, len(number.as_tuple().digits) + len(ratio.as_tuple().digits) + 2)
                    scaled = float(number / ratio if field == "reference_price" else number * ratio)
                if not math.isfinite(scaled):
                    raise ValueError("converted intent quantity or price cannot be safely represented")
            else:
                scaled = value / event["share_ratio"] if field == "reference_price" else value * event["share_ratio"]
            intent[field] = scaled
        # Only an unambiguous full liquidation inherits the one holder credit.
        # Multiple partial orders keep proportional units without per-order rounding.
        if full_sale:
            intent["signed_quantity"] = -new_quantity
            intent["intended_quantity"] = new_quantity
    return adjusted


def _sum_sale_quantities(sales: list[dict[str, Any]]) -> Decimal:
    values = [Decimal(str(-intent["signed_quantity"])) for intent in sales]
    if not values:
        return Decimal(0)
    if not all(value.is_finite() for value in values):
        raise ValueError("pending sale quantities must be finite")
    # Align all decimal places and reserve carry digits; caller precision must
    # never round an over-subscribed aggregate down to the available holding.
    places = max(value.adjusted() for value in values) - min(value.as_tuple().exponent for value in values) + 1
    with localcontext() as context:
        context.prec = max(28, places + len(str(len(values))))
        return sum(values, Decimal(0))


def _convert_whole_shares(quantity: float, event: dict[str, Any]) -> tuple[float, dict[str, str]]:
    """One ledger represents one holder; never round individual order lots."""
    max_quantity = 2 ** 53 - 1  # Subsequent position/execution interfaces use float.
    old = Decimal(str(quantity))
    if (not old.is_finite() or old < 0 or old > max_quantity
            or old != old.to_integral_value()):
        raise ValueError("share conversion requires a nonnegative, safely represented whole quantity")
    ratio = Decimal(event["share_ratio_exact"])
    with localcontext() as context:
        context.prec = max(28, len(old.as_tuple().digits) + len(ratio.as_tuple().digits) + 2)
        theoretical = old * ratio
        converted = theoretical.to_integral_value(rounding=ROUND_CEILING)
        if event["share_rounding"] == "reject_fractional" and theoretical != converted:
            raise ValueError("fractional share conversion is forbidden by the declared rounding rule")
        if converted > max_quantity:
            raise ValueError("converted share quantity cannot be safely represented")
        evidence = {"share_ratio_exact": str(ratio), "share_rounding": event["share_rounding"],
                    "unrounded_quantity": str(theoretical), "rounding_share_credit": str(converted - theoretical)}
    return float(converted), evidence


def _validate_dataset(data: Any, assets: set[str], dates: list[date]) -> list[dict[str, Any]]:
    expected = {"schema_version", "source_ref", "coverage_start", "coverage_end", "asset_ids", "events"}
    if not isinstance(data, dict) or set(data) != expected or type(data["schema_version"]) is not int or data["schema_version"] not in (1, 2):
        raise ValueError("corporate action dataset has an unsupported schema")
    if not isinstance(data["source_ref"], str) or not data["source_ref"].strip():
        raise ValueError("corporate action source_ref is required")
    if not isinstance(data["asset_ids"], list) or not all(isinstance(asset, str) for asset in data["asset_ids"]):
        raise ValueError("corporate action asset coverage must be explicit")
    if not assets.issubset(data["asset_ids"]) or _date(data["coverage_start"]) > dates[0] or _date(data["coverage_end"]) < dates[-1]:
        raise ValueError("corporate action declared coverage does not cover the simulation")
    if not isinstance(data["events"], list):
        raise ValueError("corporate action events must be an explicit list")
    result = []
    ids: set[str] = set()
    economic_events: set[tuple[str, str, date]] = set()
    splits: dict[str, list[dict[str, Any]]] = {}
    for raw in data["events"]:
        event = _validate_event(raw, version=data["schema_version"])
        if event["event_id"] in ids:
            raise ValueError("duplicate corporate action event_id")
        ids.add(event["event_id"])
        economic_key = (event["asset_id"], event["kind"], event["ex_date"])
        if economic_key in economic_events:
            raise ValueError("duplicate or conflicting corporate action economic event")
        economic_events.add(economic_key)
        if event["asset_id"] not in data["asset_ids"]:
            raise ValueError("corporate action event outside declared assets")
        if event["asset_id"] not in assets:
            continue
        if event["kind"] == "cash_dividend":
            if dates[0] <= event["record_date"] <= dates[-1] and event["record_date"] not in dates:
                raise ValueError("corporate action record date missing from simulation sessions")
        else:
            splits.setdefault(event["asset_id"], []).append(event)
        result.append(event)
    for events in splits.values():
        ordered = sorted(events, key=lambda event: event["ex_date"])
        if any(after["ex_date"] <= before["tradable_date"] for before, after in zip(ordered, ordered[1:])):
            raise ValueError("overlapping share conversions require a separate settlement model")
    return sorted(result, key=lambda event: (event["ex_date"], event["event_id"]))


def _validate_event(raw: Any, *, version: int = 1) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("corporate action event must be an object")
    fields = {"event_id", "asset_id", "kind", "announced_date", "ex_date"}
    if raw.get("kind") == "cash_dividend":
        fields |= {"record_date", "pay_date", "net_cash_per_share"}
        number_field = "net_cash_per_share"
    elif raw.get("kind") == "share_split":
        fields |= {"tradable_date", "share_ratio"}
        if version == 2:
            fields.add("share_rounding")
        number_field = "share_ratio"
    else:
        raise ValueError("unsupported corporate action kind")
    if set(raw) != fields or any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in ("event_id", "asset_id")):
        raise ValueError("corporate action fields are incomplete or unsupported")
    event = dict(raw)
    for key in fields:
        if key.endswith("_date"):
            event[key] = _date(raw[key])
    number = float(raw[number_field])
    if isinstance(raw[number_field], bool) or not math.isfinite(number) or number <= 0:
        raise ValueError("corporate action amount or ratio must be finite and positive")
    event[number_field] = number
    if event["kind"] == "share_split" and version == 2:
        if raw["share_rounding"] not in ("reject_fractional", "ceil_per_holder"):
            raise ValueError("unsupported share rounding rule")
        if not isinstance(raw["share_ratio"], (int, Decimal)):
            raise ValueError("V2 share ratio must be a JSON number")
        event["share_ratio_exact"] = str(raw["share_ratio"])
    if event["kind"] == "cash_dividend":
        valid = event["announced_date"] <= event["record_date"] < event["ex_date"] <= event["pay_date"]
    else:
        valid = event["announced_date"] < event["ex_date"] <= event["tradable_date"]
    if not valid:
        raise ValueError("corporate action chronology is invalid")
    return event


def _date(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("corporate action date must be YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("corporate action date must be YYYY-MM-DD")
    return parsed
