"""Expand a manifest-bound open-session snapshot, never guess from price gaps."""
from __future__ import annotations

import csv
from datetime import date, timedelta
import io
from pathlib import Path
import tempfile

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact


def calendar_rows_from_snapshot(calendar_bytes: bytes, manifest_bytes: bytes, *,
                                start: date, end: date) -> tuple[tuple[date, bool], ...]:
    """Return every civil day in a covered range, with derived open/closed flags.

    The source contains open days only. Closed flags are their complement within
    the declared complete range, not separately observed provider records.
    Manifest consistency is not independent historical source certification.
    """
    if (type(start) is not date or type(end) is not date or start > end
            or end == date.max):
        raise ValueError('ordered bounded dates required')
    if (not isinstance(calendar_bytes, bytes) or not isinstance(manifest_bytes, bytes)
            or not calendar_bytes or not manifest_bytes or len(calendar_bytes) > 2_000_000
            or len(manifest_bytes) > 100_000):
        raise ValueError('bounded calendar and manifest bytes required')
    with tempfile.TemporaryDirectory(prefix='cn-calendar-snapshot-') as temporary:
        calendar_path, manifest_path = Path(temporary)/'calendar.csv', Path(temporary)/'manifest.json'
        calendar_path.write_bytes(calendar_bytes)
        manifest_path.write_bytes(manifest_bytes)
        manifest = validate_cn_trading_calendar_artifact(calendar_path, manifest_path)
    try:
        requested = manifest['requested_range']
        if not date.fromisoformat(requested['start']) <= start <= end <= date.fromisoformat(requested['end']):
            raise ValueError('calendar requested range does not cover the full target')
        summary = manifest['summary']
        count, digest = summary['session_rows'], summary['session_date_sha256']
        if (summary['exchange_session_rows'] != {'SSE': count, 'SZSE': count}
                or summary['exchange_date_sha256'] != {'SSE': digest, 'SZSE': digest}):
            raise ValueError('merged and exchange calendar declarations disagree')
        records = list(csv.DictReader(io.StringIO(calendar_bytes.decode('utf-8-sig'))))
        sessions = [date.fromisoformat(row['date']) for row in records]
        if sessions != sorted(sessions):
            raise ValueError('open-session artifact must be chronological')
    except (KeyError, TypeError) as exc:
        raise ValueError('calendar source declarations are incomplete') from exc
    opened = set(sessions)
    days = (start + timedelta(days=i) for i in range((end-start).days + 1))
    return tuple((day, day in opened) for day in days)
