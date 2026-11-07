"""Bounded fund_daily structure checks without decoding financial numbers.

This module has no network, credential lookup, account model or admission path.
It preserves response bytes at its caller and returns identity/date metadata only.
"""
from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
import re

URL = "https://api.tushare.pro"
API = "fund_daily"
FIELDS = ("ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount")
SYMBOLS = ("510300.SH", "518880.SH")
MAX_BYTES = 262144
MAX_DEPTH = 8
MAX_ROWS = 366
NUMERIC_TEXT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
SECRET_KEYS = {"token", "password", "api_key", "authorization", "secret", "access_token", "refresh_token"}


class WireError(ValueError):
    """Static failure code, with optional validated identity/date metadata."""

    def __init__(self, code, *, metadata=None):
        super().__init__(code)
        self.code = code
        self.metadata = metadata or {}


class OpaqueNumber(str):
    """Original JSON number spelling; conversion is forbidden in this phase."""

    def __int__(self):
        raise WireError("financial_conversion_forbidden")

    def __float__(self):
        raise WireError("financial_conversion_forbidden")


def _require(condition, code):
    if not condition:
        raise WireError(code)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate_JSON_key")
        result[key] = value
    return result


def _constant(_value):
    raise WireError("nonstandard_JSON_number")


def _inspect_tree(value, token, depth=0):
    _require(depth <= MAX_DEPTH, "JSON_depth_limit")
    if isinstance(value, str):
        _require(not token or token not in value, "credential_echo_not_retained")
    elif isinstance(value, list):
        for child in value:
            _inspect_tree(child, token, depth+1)
    elif isinstance(value, dict):
        for key, child in value.items():
            _require(key.lower() not in SECRET_KEYS, "credential_field_not_retained")
            _inspect_tree(key, token, depth+1)
            _inspect_tree(child, token, depth+1)


def decode_opaque(raw, *, token=None):
    """Private-safe decode boundary; never return this tree in a receipt/log."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "response_byte_limit")
    _require(token is None or type(token) is str and bool(token), "invalid_credential_input")
    _require(not token or token.encode("utf-8") not in raw, "credential_echo_not_retained")
    try:
        parsed = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                            parse_int=OpaqueNumber, parse_float=OpaqueNumber,
                            parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise WireError("invalid_JSON_not_retained") from None
    _inspect_tree(parsed, token)
    return parsed


def _iso_date(value, *, compact=False):
    pattern = r"[0-9]{8}" if compact else r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    _require(type(value) is str and re.fullmatch(pattern, value) is not None, "invalid_identity_date")
    try:
        parsed = datetime.strptime(value, "%Y%m%d").date() if compact else date.fromisoformat(value)
    except ValueError:
        raise WireError("invalid_identity_date") from None
    return parsed.isoformat()


def date_digest(dates, symbol=None):
    lines = [f"{symbol}|{d}" if symbol else d for d in sorted(dates)]
    return sha256(("\n".join(lines)+"\n").encode("utf-8")).hexdigest()


def validate_manifest(manifest, sessions):
    """Fix all 24 roles from the accepted calendar, without opening any bars."""
    _require(type(manifest) is dict and type(sessions) is list, "manifest_shape")
    dates = [_iso_date(x) for x in sessions]
    _require(len(dates) == 2454 and dates == sorted(set(dates))
             and dates[0] == "2013-12-05" and dates[-1] == "2024-01-02", "fixed_calendar_required")
    _require(manifest.get("artifact_type") == "constant_mix_fixed_24_provider_requests_v1"
             and manifest.get("symbols") == list(SYMBOLS)
             and manifest.get("range") == [dates[0], dates[-1]]
             and manifest.get("request_count") == 24
             and manifest.get("expected_total_symbol_date_rows") == 4908
             and manifest.get("old_dayk_or_971_mapped_rows_used_as_authority") is False,
             "fixed_manifest_required")
    _require(manifest.get("request_budget") == {
        "max_POST": 24, "GET": 0, "automatic_pagination": 0, "retry": 0,
        "redirect": 0, "substitute_dates_or_symbols": False, "resume_failed_batch": False},
        "fixed_request_budget_required")
    requests = manifest.get("requests")
    _require(type(requests) is list and len(requests) == 24, "fixed_request_list_required")
    total = 0
    for index, (year, symbol) in enumerate((y, s) for y in range(2013, 2025) for s in SYMBOLS):
        item = requests[index]
        expected = [d for d in dates if d.startswith(str(year)+"-")]
        start = "20131205" if year == 2013 else f"{year}0101"
        end = "20240102" if year == 2024 else f"{year}1231"
        request_id = f"{index+1:02d}_fund_daily_{symbol.replace('.', '_')}_{year}"
        _require(type(item) is dict and item.get("order") == index+1
                 and item.get("id") == request_id
                 and item.get("role") == f"fund_daily_{symbol[:6]}_{year}_provider_wire"
                 and item.get("endpoint") == URL and item.get("method") == "POST"
                 and item.get("api_name") == API
                 and item.get("params") == {"ts_code": symbol, "start_date": start, "end_date": end}
                 and item.get("fields") == ",".join(FIELDS)
                 and item.get("expected_trade_dates") == [d.replace("-", "") for d in expected]
                 and item.get("expected_rows") == len(expected)
                 and item.get("expected_ISO_dates_sha256") == date_digest(expected)
                 and item.get("expected_symbol_date_sha256") == date_digest(expected, symbol)
                 and item.get("planned_capture_directory") == f"capture/requests/{request_id}"
                 and item.get("actual_response_ref") is None, "request_contract_mismatch")
        total += len(expected)
    _require(total == 4908, "fixed_total_rows_required")
    return {"request_count": 24, "expected_rows": total, "calendar_sessions": len(dates),
            "financial_values_decoded": False, "network_requests": 0}


def _cell_kind(value):
    if isinstance(value, OpaqueNumber):
        return "JSON_numeric_token"
    if value is None:
        return "null"
    if type(value) is str and NUMERIC_TEXT.fullmatch(value):
        return "numeric_string"
    raise WireError("financial_cell_schema_invalid")


def inspect_structure(raw, request, *, token=None):
    """Validate exact identity coverage; return no prices, volume or amount."""
    parsed = decode_opaque(raw, token=token)
    _require(type(parsed) is dict and isinstance(parsed.get("code"), OpaqueNumber)
             and str(parsed["code"]) == "0", "provider_envelope_rejected")
    data = parsed.get("data")
    _require(type(data) is dict, "data_object_missing")
    _require(data.get("fields") == list(FIELDS), "exact_field_order_required")
    _require("has_more" not in data or data["has_more"] is False, "pagination_not_allowed")
    rows = data.get("items")
    _require(type(rows) is list and len(rows) <= MAX_ROWS, "response_rows_limit")
    symbol = request["params"]["ts_code"]
    _require(symbol in SYMBOLS, "request_symbol_out_of_scope")
    expected = {_iso_date(d, compact=True) for d in request["expected_trade_dates"]}
    dates, seen, duplicates = [], set(), []
    kinds = {"JSON_numeric_token": 0, "numeric_string": 0, "null": 0}
    for row in rows:
        _require(type(row) is list and len(row) == len(FIELDS), "row_width_invalid")
        _require(type(row[0]) is str and row[0] == symbol, "response_symbol_mismatch")
        day = _iso_date(row[1], compact=True)
        if day in seen:
            duplicates.append(day)
        seen.add(day); dates.append(day)
        for value in row[2:]:
            kinds[_cell_kind(value)] += 1
    differences = {"missing_dates": sorted(expected-seen), "unexpected_dates": sorted(seen-expected),
                   "duplicate_dates": sorted(set(duplicates))}
    if any(differences.values()):
        raise WireError("response_date_set_mismatch", metadata=differences)
    _require(len(rows) == request["expected_rows"], "response_row_count_mismatch")
    observed_order = "ascending" if dates == sorted(dates) else "descending" if dates == sorted(dates, reverse=True) else "mixed"
    return {"artifact_type": "fund_daily_wire_structure_only_v1", "ts_code": symbol,
            "rows": len(rows), "fields": list(FIELDS), "source_row_order": observed_order,
            "expected_ISO_dates_sha256": date_digest(dates),
            "expected_symbol_date_sha256": date_digest(dates, symbol),
            "financial_cell_syntax_counts": kinds, "provider_count_semantics_verified": False,
            "financial_numeric_values_decoded": False, "financial_values_printed": False,
            "numerical_quality_verified": False, "historical_PIT_verified": False,
            "qualified": False, "real_forward": 0}
