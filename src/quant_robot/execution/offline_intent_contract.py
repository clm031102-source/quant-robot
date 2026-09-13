"""Strict, explicitly synthetic input contracts for guarded order admission."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from .offline_order_state import amount, identity, positions, symbol, units

SHANGHAI = ZoneInfo("Asia/Shanghai")
INTENT_FIELDS = {"schema_version", "client_intent_id", "idempotency_key", "strategy_id", "strategy_version",
    "signal_timestamp", "symbol", "exchange", "side", "quantity", "order_type", "limit_price",
    "time_in_force", "max_slippage_bps", "expires_at"}
POLICY_MONEY = {"capital_limit_cny", "max_position_cny", "max_daily_loss_cny", "max_adv_participation",
    "max_slippage_bps", "max_spread_bps"}
POLICY_SECONDS = {"max_quote_age_seconds", "max_context_age_seconds", "max_signal_age_seconds", "max_adv_age_days"}
PACKET_FIELDS = {"schema_version", "mode", "snapshot_id", "source_ref", "as_of", "session_date",
    "journal_sequence", "journal_hash", "quotes"}


def exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(label + " has missing or unsupported fields")


def version(value):
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("unsupported schema_version")


def day(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("invalid session date")
    return date.fromisoformat(value)


def instant(value):
    if not isinstance(value, (str, datetime)):
        raise ValueError("timestamp must be timezone aware")
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone aware")
    return parsed.astimezone(timezone.utc)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def exchange(code, value):
    expected = "SSE" if code.endswith(".SH") else "SZSE"
    if value != expected:
        raise ValueError("symbol and exchange mismatch")
    return value


def normalize_policy(value):
    policy_version = value.get('schema_version') if isinstance(value, dict) else None
    if type(policy_version) is not int or policy_version not in {1, 2}:
        raise ValueError('unsupported admission policy schema_version')
    drawdown_fields = {'max_drawdown'} if policy_version == 2 else set()
    stop_fields = {'exposure_stop_action'} if policy_version == 2 and 'exposure_stop_action' in value else set()
    exact(value, {"schema_version", "mode", "policy_id", "strategy_id", "strategy_version", "allowed_symbols",
        "session_dates", "trading_windows", *POLICY_MONEY, *POLICY_SECONDS, *drawdown_fields, *stop_fields}, "admission policy")
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only offline_fixture_only admission is supported")
    result = {"schema_version": policy_version, "mode": "offline_fixture_only"}
    if stop_fields:
        if value['exposure_stop_action'] not in ('halt_all', 'reduce_only'):
            raise ValueError('unsupported exposure_stop_action')
        result['exposure_stop_action'] = value['exposure_stop_action']
    if policy_version == 2:
        limit = amount(value['max_drawdown'], positive=True)
        if limit >= 1:
            raise ValueError('max_drawdown must be a positive fraction below 1')
        result['max_drawdown'] = str(limit)
    for key in ("policy_id", "strategy_id", "strategy_version"):
        result[key] = identity(value[key])
    for key in POLICY_MONEY:
        result[key] = str(amount(value[key], positive=key not in {"max_slippage_bps", "max_spread_bps"}))
    if amount(result["max_adv_participation"]) > 1 or amount(result["max_slippage_bps"]) >= 10000:
        raise ValueError("invalid participation or slippage limit")
    if amount(result["max_position_cny"]) > amount(result["capital_limit_cny"]):
        raise ValueError("position limit exceeds capital limit")
    for key in POLICY_SECONDS:
        result[key] = units(value[key], positive=True)
    for key, validator in (("allowed_symbols", symbol), ("session_dates", lambda x: day(x).isoformat())):
        if not isinstance(value[key], list) or not value[key]:
            raise ValueError("nonempty list required: " + key)
        items = [validator(item) for item in value[key]]
        if len(items) != len(set(items)):
            raise ValueError("duplicate entries: " + key)
        result[key] = sorted(items)
    windows = value["trading_windows"]
    if not isinstance(windows, list) or not windows:
        raise ValueError("trading windows required")
    result["trading_windows"] = []
    previous_end = None
    for window in windows:
        if (not isinstance(window, list) or len(window) != 2
                or any(not isinstance(v, str) or re.fullmatch(r"[0-9]{2}:[0-9]{2}", v) is None for v in window)):
            raise ValueError("invalid trading window")
        start, end = map(time.fromisoformat, window)
        if start >= end or (previous_end is not None and start < previous_end):
            raise ValueError("overlapping or invalid trading windows")
        result["trading_windows"].append(list(window))
        previous_end = end
    return result


def normalize_intent(value):
    exact(value, INTENT_FIELDS, "order intent")
    version(value)
    result = {"schema_version": 1}
    for key in ("client_intent_id", "idempotency_key", "strategy_id", "strategy_version", "side", "order_type", "time_in_force"):
        result[key] = identity(value[key])
    result["symbol"] = symbol(value["symbol"])
    result["exchange"] = exchange(result["symbol"], value["exchange"])
    result["quantity"] = units(value["quantity"], positive=True)
    result["limit_price"] = str(amount(value["limit_price"], positive=True))
    result["max_slippage_bps"] = str(amount(value["max_slippage_bps"]))
    for key in ("signal_timestamp", "expires_at"):
        result[key] = instant(value[key]).isoformat()
    return result


def rejection_evidence(value, error):
    """Keep valid identities and bounded primitive fields, never arbitrary objects."""
    ids, supplied = {}, {}
    if isinstance(value, dict):
        for key in ("client_intent_id", "idempotency_key"):
            try:
                ids[key] = identity(value.get(key))
            except ValueError:
                pass
        for key in INTENT_FIELDS.intersection(value):
            raw = value[key]
            if type(raw) is str:
                supplied[key] = raw[:2000]
            elif raw is None or type(raw) is bool:
                supplied[key] = raw
            elif type(raw) is int and abs(raw) <= 10**30:
                supplied[key] = raw
            elif type(raw) is float:
                supplied[key] = str(raw)
            else:
                supplied[key] = {"unserializable_or_out_of_range_type": type(raw).__name__}
    return {"intent": ids, "parse_failure": str(error), "provided_intent_fields": supplied}


def normalize_instrument(value, code):
    exact(value, {"symbol", "exchange", "instrument_type", "lot_size", "price_tick", "settlement",
        "odd_lot_sell_allowed", "adv_shares", "adv_as_of", "valid_from", "valid_until", "source_ref"}, "instrument")
    if symbol(value["symbol"]) != code or value["instrument_type"] != "ETF" or value["settlement"] not in ("T0", "T1"):
        raise ValueError("unsupported ETF instrument metadata")
    if type(value["odd_lot_sell_allowed"]) is not bool:
        raise ValueError("odd_lot_sell_allowed must be boolean")
    return {"symbol": code, "exchange": exchange(code, value["exchange"]), "instrument_type": "ETF",
        "lot_size": units(value["lot_size"], positive=True), "price_tick": str(amount(value["price_tick"], positive=True)),
        "settlement": value["settlement"], "odd_lot_sell_allowed": value["odd_lot_sell_allowed"],
        "adv_shares": str(amount(value["adv_shares"], positive=True)), "adv_as_of": day(value["adv_as_of"]).isoformat(),
        "valid_from": day(value["valid_from"]).isoformat(), "valid_until": day(value["valid_until"]).isoformat(),
        "source_ref": identity(value["source_ref"])}


def normalize_packet(value, *, opening=False):
    exact(value, PACKET_FIELDS | ({"instruments", "sellable_positions"} if opening else set()), "risk context")
    version(value)
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only offline_fixture_only risk context is supported")
    result = {"schema_version": 1, "mode": value["mode"], "snapshot_id": identity(value["snapshot_id"]),
        "source_ref": identity(value["source_ref"]), "as_of": instant(value["as_of"]).isoformat(),
        "session_date": day(value["session_date"]).isoformat(), "journal_sequence": units(value["journal_sequence"]),
        "journal_hash": value["journal_hash"], "quotes": {}}
    if not isinstance(result["journal_hash"], str) or re.fullmatch(r"[0-9a-f]{64}", result["journal_hash"]) is None:
        raise ValueError("invalid journal hash")
    if not isinstance(value["quotes"], dict):
        raise ValueError("quotes must be a mapping")
    for key, quote in value["quotes"].items():
        code = symbol(key)
        quote_fields = {"symbol", "exchange", "timestamp", "bid", "ask", "trade_status", "source_ref"}
        if isinstance(quote, dict) and "price_basis_id" in quote:
            quote_fields.add("price_basis_id")
        exact(quote, quote_fields, "quote")
        if quote["symbol"] != code:
            raise ValueError("quote symbol mismatch")
        result["quotes"][code] = {"symbol": code, "exchange": exchange(code, quote["exchange"]),
            "timestamp": instant(quote["timestamp"]).isoformat(), "bid": str(amount(quote["bid"], positive=True)),
            "ask": str(amount(quote["ask"], positive=True)), "trade_status": identity(quote["trade_status"]),
            "source_ref": identity(quote["source_ref"])}
        if "price_basis_id" in quote:
            result["quotes"][code]["price_basis_id"] = identity(quote["price_basis_id"])
    if opening:
        if not isinstance(value["instruments"], dict):
            raise ValueError("instruments must be a mapping")
        result["instruments"] = {symbol(key): normalize_instrument(row, key) for key, row in value["instruments"].items()}
        result["sellable_positions"] = positions(value["sellable_positions"], bounded=False)
    return result
