"""Complete, explicit SSE/SZSE calendar requests and response relationships.

This validates a received calendar, not its historical publication vintage.
The predecessor before the first requested day is a provider assertion.
"""
from datetime import datetime, timedelta
import re


CALENDAR_FIELDS = {"exchange", "cal_date", "is_open", "pretrade_date"}


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{8}", value) is None:
        raise ValueError("calendar dates require YYYYMMDD strings")
    return datetime.strptime(value, "%Y%m%d").date()


def _dates(params):
    start, end = _day(params["start_date"]), _day(params["end_date"])
    count = (end - start).days + 1
    if not 1 <= count <= 366:
        raise ValueError("calendar request requires a closed range of at most 366 days")
    return [(start + timedelta(days=i)).strftime("%Y%m%d") for i in range(count)]


def validate_calendar_query(names, max_rows, params, max_date):
    if set(names) != CALENDAR_FIELDS or set(params) != {"exchange", "start_date", "end_date"}:
        raise ValueError("calendar requires four fields, an exchange and both bounds; no open-day filter")
    if params["exchange"] not in ("SSE", "SZSE"):
        raise ValueError("calendar requires one explicit SSE or SZSE exchange")
    dates = _dates(params)
    if dates[-1] > max_date or max_rows < len(dates):
        raise ValueError("calendar exceeds its frozen date ceiling or row budget")


def validate_calendar_records(records, params):
    dates = _dates(params)
    if len(records) != len(dates) or sorted(row["cal_date"] for row in records) != dates:
        raise ValueError("calendar response must contain each requested civil date exactly once")
    expected_previous = None
    for row in sorted(records, key=lambda item: item["cal_date"]):
        if row["exchange"] != params["exchange"]:
            raise ValueError("calendar response differs from requested exchange")
        status = row["is_open"]
        if type(status) not in (str, int) or str(status) not in ("0", "1"):
            raise ValueError("calendar open status must be literal 0 or 1")
        previous, current = _day(row["pretrade_date"]), _day(row["cal_date"])
        if previous >= current:
            raise ValueError("calendar predecessor must precede its date")
        if expected_previous is not None and row["pretrade_date"] != expected_previous:
            raise ValueError("calendar predecessor chain disagrees with prior open status")
        expected_previous = row["cal_date"] if str(status) == "1" else row["pretrade_date"]
