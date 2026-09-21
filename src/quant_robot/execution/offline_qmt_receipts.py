"""Review synthetic QMT-shaped observations without SDK, transport or journal writes.

The caller supplies a declared fixture date and order identity; these are not
certified capture metadata. A matching receipt total is never permission to
release funds, retry a request or connect to any trading service.
"""
from __future__ import annotations

from .offline_intent_contract import day, exact, fingerprint
from .offline_order_state import amount, identity, money_context, symbol, units


SCOPE_FIELDS = {"mode", "session_date", "source_ref", "account_id", "account_type",
                "stock_code", "order_id", "order_sysid", "order_volume", "offset_flag"}
IDENTITY_FIELDS = ("account_id", "account_type", "stock_code", "order_id", "order_sysid", "offset_flag")
STATUS_MAP = {48: "PENDING", 49: "PENDING", 50: "ACCEPTED", 51: "CANCEL_PENDING",
              52: "CANCEL_PENDING", 53: "CANCELLED", 54: "CANCELLED", 55: "PARTIAL",
              56: "FILLED", 57: "REJECTED", 255: "UNKNOWN"}


def _integer(value, *, positive=False):
    if type(value) is not int or not int(positive) <= value <= 2**63 - 1:
        raise ValueError("invalid nonnegative protocol integer")
    return value


def _row(value):
    if not isinstance(value, dict):
        raise ValueError("protocol observation must be a dictionary")
    return value


def _identity(row):
    _row(row)
    result = {key: identity(row.get(key)) for key in ("account_id", "order_sysid")}
    result.update(account_type=_integer(row.get("account_type")),
                  stock_code=symbol(row.get("stock_code")),
                  order_id=_integer(row.get("order_id"), positive=True),
                  offset_flag=_integer(row.get("offset_flag")))
    if result["offset_flag"] not in (48, 49):
        raise ValueError("only cash security buy/sell offset flags are reviewed")
    return result


def _scope(value):
    exact(value, SCOPE_FIELDS, "QMT fixture scope")
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only offline_fixture_only review is supported")
    result = {**_identity(value), "mode": "offline_fixture_only",
              "session_date": day(value["session_date"]).isoformat(),
              "source_ref": identity(value["source_ref"]),
              "order_volume": units(value["order_volume"], positive=True)}
    if not result["account_id"].startswith("fixture-") or not result["source_ref"].startswith("fixture:"):
        raise ValueError("synthetic account alias and source reference required")
    return result


def _bound_identity(row, scope):
    result = _identity(row)
    if any(result[key] != scope[key] for key in IDENTITY_FIELDS):
        raise ValueError("observation identity mismatch; remarks cannot bind an order")
    return result


def _status_consistent(raw_status, filled, quantity):
    if raw_status in (48, 49, 50, 51, 54, 57):
        return filled == 0
    if raw_status in (52, 53, 55):
        return 0 < filled < quantity
    if raw_status == 56:
        return filled == quantity
    return False


@money_context
def review_qmt_receipts(expected, snapshot, trades):
    """Check one synthetic order snapshot against explicit trade observations.

    None is ambiguous according to the documented query contract. Empty lists
    are explicit local observations, not evidence of successful API transport.
    All returned integration permissions remain false, even for matched totals.
    Raw timestamps and counter price types are deliberately not reinterpreted.
    """
    scope = _scope(expected)
    blockers = []
    observed = None
    projected = "UNKNOWN"
    if snapshot is None:
        blockers.append("order_observation_unavailable")
    else:
        observed = {**_bound_identity(snapshot, scope),
                    "order_volume": units(snapshot.get("order_volume"), positive=True),
                    "traded_volume": units(snapshot.get("traded_volume")),
                    "order_status": _integer(snapshot.get("order_status"))}
        if observed["order_volume"] != scope["order_volume"]:
            raise ValueError("order volume differs from original fixture intent")
        raw_status = observed["order_status"]
        projected = STATUS_MAP.get(raw_status, "UNKNOWN")
        if projected == "UNKNOWN":
            blockers.append("unknown_order_status")
        elif not _status_consistent(raw_status, observed["traded_volume"], scope["order_volume"]):
            blockers.append("status_quantity_inconsistent")

    unique = {}
    duplicate_count = 0
    if trades is None:
        blockers.append("trade_query_failed_or_empty")
    else:
        if not isinstance(trades, list) or len(trades) > 10000:
            raise ValueError("bounded explicit trade list required")
        for row in trades:
            bound = _bound_identity(row, scope)
            normalized = {**bound, "traded_id": identity(row.get("traded_id")),
                          "traded_time": _integer(row.get("traded_time"), positive=True),
                          "traded_volume": units(row.get("traded_volume"), positive=True),
                          "traded_price": str(amount(row.get("traded_price"), positive=True)),
                          "traded_amount": str(amount(row.get("traded_amount"), positive=True))}
            # The date and exchange scope are explicit fixture metadata, not
            # inferred from the integer clock or from a globally unique fill ID.
            key = fingerprint({"account_id": scope["account_id"], "account_type": scope["account_type"],
                               "session_date": scope["session_date"],
                               "exchange": scope["stock_code"].rsplit(".", 1)[1],
                               "traded_id": normalized["traded_id"]})
            normalized["receipt_key"] = key
            if key in unique:
                if unique[key] != normalized:
                    raise ValueError("conflicting trade identity requires review")
                duplicate_count += 1
            else:
                unique[key] = normalized

    receipts = [unique[key] for key in sorted(unique)]
    filled = sum(row["traded_volume"] for row in receipts) if trades is not None else None
    value = sum((amount(row["traded_amount"]) for row in receipts), amount("0")) if trades is not None else None
    if filled is not None:
        if filled > scope["order_volume"]:
            blockers.append("trade_quantity_exceeds_intent")
        if observed is not None:
            if observed["traded_volume"] > filled:
                blockers.append("snapshot_references_missing_fills")
            elif observed["traded_volume"] < filled:
                blockers.append("snapshot_behind_trade_evidence")
    return {"mode": "offline_fixture_only", "scope": scope,
            "projected_status": projected, "order_observation": observed,
            "terminal_status_observed": projected in {"FILLED", "CANCELLED", "REJECTED"},
            "receipt_quantities_match": not blockers, "blockers": blockers,
            "filled_quantity": filled, "filled_amount": str(value) if value is not None else None,
            "receipts": receipts, "duplicate_receipts": duplicate_count,
            "capture_date_verified": False, "counter_price_type_verified": False,
            "amount_price_consistency_verified": False,
            "accounting_verified": False, "reservation_release_allowed": False,
            "automatic_retry_allowed": False, "executable": False,
            "integration_gaps": ["verified_package_and_broker_enum_mapping", "verified_capture_date_and_query_completeness",
                                 "original_intent_and_journal_binding", "trade_amount_precision_and_price_consistency",
                                 "fee_cash_position_reconciliation"]}
