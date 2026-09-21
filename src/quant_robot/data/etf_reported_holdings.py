"""Check historical disclosed holdings without conferring source or factor authority.

Inputs must come from separately reviewed report pages and publication records.
The calendar must be validated against the project's official calendar artifact;
this module checks ordering and bounds, not the completeness of that calendar.
It deliberately does not infer index membership, PCF baskets or current holdings.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date
from decimal import Decimal, localcontext
import re
from typing import Any, Mapping, Sequence


SOURCE_CUTOFF = date(2024, 6, 28)


def _day(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("canonical historical date required")
    result = date.fromisoformat(value)
    if result > SOURCE_CUTOFF:
        raise ValueError("date exceeds frozen historical source window")
    return result


def _fund(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?:5\d{5}\.SH|1\d{5}\.SZ)", value):
        raise ValueError("explicit CN ETF symbol required; legal identity still needs source review")
    return value


def _money(value: Any) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9]\d{0,19})\.\d{2}", value):
        raise ValueError("nonnegative exact-cent money string required")
    return Decimal(value)


def _holding(value: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    if not isinstance(value, Mapping) or type(value.get("ordinal")) is not int or value["ordinal"] != ordinal:
        raise ValueError("holdings require contiguous source row ordinals")
    symbol = value.get("symbol")
    if not isinstance(symbol, str) or not re.fullmatch(r"(?:(?:60|68)\d{4}\.SH|(?:00|30)\d{4}\.SZ)", symbol):
        raise ValueError("unsupported or ambiguous constituent security symbol")
    quantity = value.get("quantity")
    if type(quantity) is not int or not 0 < quantity < 10**18:
        raise ValueError("positive integer source quantity required")
    amount = _money(value.get("fair_value_cny"))
    weight = value.get("reported_nav_weight_percent")
    if (not isinstance(weight, str)
            or not re.fullmatch(r"(?:0|[1-9]\d{0,2})(?:\.\d{1,8})?", weight)
            or Decimal(weight) > 100 or amount <= 0):
        raise ValueError("positive fair value and explicit bounded displayed weight required")
    return {"ordinal": ordinal, "symbol": symbol, "quantity": quantity,
            "fair_value_cny": format(amount, "f"), "reported_nav_weight_percent": weight}


def _available(publication: date, session_dates: Sequence[str]) -> str:
    if not isinstance(session_dates, (list, tuple)) or not session_dates:
        raise ValueError("validated historical session calendar required")
    dates = [_day(value) for value in session_dates]
    if dates != sorted(set(dates)) or dates[0] > publication:
        raise ValueError("calendar ordering or lower bound is invalid")
    position = bisect_right(dates, publication)
    if position == len(dates):
        raise ValueError("calendar has no verified session after publication")
    return dates[position].isoformat()


def review_snapshot(record: Mapping[str, Any], *, session_dates: Sequence[str]) -> dict[str, Any]:
    """Validate declared scope and arithmetic; retain all positive-value rows.

    A matching row sum cannot prove that the source declared complete holdings.
    Callers must retain PDF identity, page scope and actual publication evidence.
    Displayed NAV percentages are observations, never used to drop positions or
    to renormalize a partial report into a complete basket.
    """
    if not isinstance(record, Mapping):
        raise ValueError("explicit snapshot record required")
    symbol = _fund(record.get("symbol"))
    period, publication = _day(record.get("period_end")), _day(record.get("publication_date"))
    if publication < period:
        raise ValueError("publication cannot precede the report period end")
    scope = record.get("reported_scope")
    if scope not in {"all_stocks", "top10_only"}:
        raise ValueError("explicit all-stocks or top-ten report scope required")
    source = record.get("source_sha256")
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{64}", source):
        raise ValueError("explicit retained source fingerprint required")
    equity_total = _money(record.get("equity_total_cny"))
    raw_rows = record.get("holdings")
    if (equity_total <= 0 or not isinstance(raw_rows, list) or not 1 <= len(raw_rows) <= 5000
            or (scope == "top10_only" and len(raw_rows) > 10)):
        raise ValueError("invalid equity total or disclosed row scope")
    rows = [_holding(row, n) for n, row in enumerate(raw_rows, 1)]
    if len({row["symbol"] for row in rows}) != len(rows):
        raise ValueError("duplicate constituent security")
    with localcontext() as context:
        context.prec = 50
        total = sum((Decimal(row["fair_value_cny"]) for row in rows), Decimal("0.00"))
        if total > equity_total or (scope == "all_stocks" and total != equity_total):
            raise ValueError("disclosed holdings do not reconcile to the source equity total")
        fraction = total / equity_total
    return {"symbol": symbol, "period_end": period.isoformat(), "publication_date": publication.isoformat(),
            "available_from_session": _available(publication, session_dates), "reported_scope": scope,
            "source_sha256": source, "holdings": rows, "equity_total_cny": format(equity_total, "f"),
            "sum_fair_value_cny": format(total, "f"), "disclosed_equity_value_fraction": format(fraction, "f"),
            "is_complete_disclosure": scope == "all_stocks", "historical_source_authority_verified": False,
            "index_membership_verified": False, "daily_pcf_verified": False, "factor_generation_allowed": False}


def select_complete_snapshot(records: Sequence[Mapping[str, Any]], *, symbol: str, as_of: str,
                             session_dates: Sequence[str]) -> dict[str, Any] | None:
    """Return the latest available complete reported period, or unknown (None).

    This is a historical source-view helper, not a strategy or readiness gate.
    Incomplete quarterly reports do not overwrite a complete annual/interim
    snapshot. An old-period late revision cannot replace a newer report period.
    No current-holdings or maximum-staleness assumption is made.
    """
    target, observed = _fund(symbol), _day(as_of)
    if not isinstance(records, (list, tuple)) or len(records) > 1000:
        raise ValueError("bounded snapshot records required")
    reviewed = [review_snapshot(record, session_dates=session_dates) for record in records]
    eligible = [item for item in reviewed if item["symbol"] == target and item["is_complete_disclosure"]
                and _day(item["available_from_session"]) <= observed]
    if not eligible:
        return None
    key = max((item["period_end"], item["publication_date"]) for item in eligible)
    latest = [item for item in eligible if (item["period_end"], item["publication_date"]) == key]
    if len(latest) != 1:
        raise ValueError("ambiguous same-period publication requires explicit source review")
    result = latest[0]
    result["reported_period_age_days"] = (observed - _day(result["period_end"])).days
    result["publication_age_days"] = (observed - _day(result["publication_date"])).days
    return result
