"""Parse a bounded ALFRED monthly CSV without filling historical missing values.

The caller must separately authenticate the download and its requested scope.
Parsing does not certify original publication times or admit a trading strategy.
"""
from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Sequence
from datetime import date

import pandas as pd


def _iso_date(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("dates must use ISO YYYY-MM-DD strings")
    return date.fromisoformat(value)


def _contract(
    series_id: str,
    vintage_dates: Sequence[str],
    observation_start: str,
    observation_end: str,
) -> tuple[list[date], list[date], dict[str, date]]:
    if not isinstance(series_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", series_id):
        raise ValueError("series_id must identify one series")
    if isinstance(vintage_dates, (str, bytes)) or not isinstance(vintage_dates, Sequence):
        raise ValueError("vintage_dates must be a nonempty sequence of dates")
    vintages = [_iso_date(value) for value in vintage_dates]
    if not vintages or len(set(vintages)) != len(vintages):
        raise ValueError("vintage_dates must be nonempty and unique")
    start, end = _iso_date(observation_start), _iso_date(observation_end)
    if start.day != 1 or end.day != 1 or start > end:
        raise ValueError("observation range must be ordered month-start dates")
    months = [timestamp.date() for timestamp in pd.date_range(start, end, freq="MS")]
    columns = {f"{series_id}_{value:%Y%m%d}": value for value in vintages}
    return sorted(vintages), months, columns


def _read_rows(
    content: bytes, columns: dict[str, date], months: list[date],
) -> dict[date, dict[date, float]]:
    try:
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig")), strict=True)
        header = next(reader)
        expected = {"observation_date", *columns}
        if len(header) != len(expected) or set(header) != expected:
            raise ValueError("CSV columns must match exactly the requested series and vintages")
        rows: dict[date, dict[date, float]] = {}
        allowed_months = set(months)
        for values in reader:
            if len(values) != len(header):
                raise ValueError("CSV row width does not match its columns")
            fields = dict(zip(header, values, strict=True))
            observation = _iso_date(fields.pop("observation_date"))
            if observation not in allowed_months or observation in rows:
                raise ValueError("duplicate, non-monthly or out-of-scope observation date")
            rows[observation] = {}
            for column, raw_value in fields.items():
                vintage = columns[column]
                # Empty CSV fields are the missing representation observed in this format.
                # Unknown tokens are errors, never silently converted to absence.
                if raw_value == "":
                    value = math.nan
                else:
                    try:
                        value = float(raw_value)
                    except ValueError as exc:
                        raise ValueError("observation must be finite numeric or an empty field") from exc
                    if not math.isfinite(value):
                        raise ValueError("observation must be finite numeric or an empty field")
                    if observation > vintage:
                        raise ValueError("nonempty future observation is outside its vintage")
                rows[observation][vintage] = value
        return rows
    except (StopIteration, UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("invalid ALFRED UTF-8 CSV") from exc


def parse_alfred_monthly_vintages(
    content: bytes,
    *,
    series_id: str,
    vintage_dates: Sequence[str],
    observation_start: str,
    observation_end: str,
) -> pd.DataFrame:
    """Return the complete requested month/vintage grid, sorted by vintage then month.

    ``value`` retains blank cells as NaN. ``observation_row_present`` distinguishes
    a row the provider omitted entirely from an explicit blank in a returned row.
    Zero is a value; later vintages never fill earlier ones. An all-missing panel
    does not establish that no event occurred or that a source is complete.
    """
    vintages, months, columns = _contract(
        series_id, vintage_dates, observation_start, observation_end,
    )
    rows = _read_rows(content, columns, months)
    records = [
        {
            "observation_date": pd.Timestamp(month),
            "vintage_date": pd.Timestamp(vintage),
            "value": rows.get(month, {}).get(vintage, math.nan),
            "observation_row_present": month in rows,
        }
        for vintage in vintages for month in months
    ]
    return pd.DataFrame.from_records(records)
