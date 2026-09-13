import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar, write_cn_trading_calendar
from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot


class CalendarSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.first, self.last = date(2020, 1, 1), date(2020, 2, 2)
        frame = pd.DataFrame({'date': ['2020-01-02', '2020-01-03', '2020-01-06', '2020-02-01'], 'is_open': 1})
        calendar, manifest = build_cn_trading_calendar(
            {'SSE': frame, 'SZSE': frame}, start_date='2020-01-01', end_date='2020-02-02')
        with tempfile.TemporaryDirectory() as tmp:
            written = write_cn_trading_calendar(tmp, calendar, manifest)
            self.raw = Path(written['calendar_path']).read_bytes()
            self.manifest = json.loads(Path(written['manifest_path']).read_bytes())

    def convert(self, raw=None, manifest=None, start=None, end=None):
        return calendar_rows_from_snapshot(self.raw if raw is None else raw,
            json.dumps(self.manifest if manifest is None else manifest).encode(),
            start=self.first if start is None else start, end=self.last if end is None else end)

    def test_dense_rows_are_explicit_complement_of_manifest_bound_open_sessions(self):
        rows = self.convert()
        self.assertEqual(len(rows), 33)
        self.assertEqual(rows[0], (date(2020, 1, 1), False))
        self.assertEqual(rows[1], (date(2020, 1, 2), True))
        self.assertEqual(rows[-1], (date(2020, 2, 2), False))
        self.assertEqual(sum(opened for _, opened in rows), 4)

    def test_missing_session_cannot_be_silently_reclassified_closed(self):
        altered = b''.join(line for line in self.raw.splitlines(keepends=True) if b'2020-01-03' not in line)
        self.assertNotEqual(altered, self.raw)
        with self.assertRaises(ValueError): self.convert(raw=altered)

    def test_requested_range_must_cover_entire_target(self):
        for start, end in ((date(2019, 12, 31), self.last), (self.first, date(2020, 2, 3))):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.convert(start=start, end=end)

    def test_exchange_metadata_must_agree_with_merged_sessions(self):
        for key, value in [('exchange_session_rows', {'SSE': 4, 'SZSE': 3}),
                           ('exchange_date_sha256', {'SSE': '0'*64, 'SZSE': '1'*64})]:
            manifest = copy.deepcopy(self.manifest); manifest['summary'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.convert(manifest=manifest)

    def test_uncleared_or_unbound_artifact_is_not_calendar_authority(self):
        for change in ({'status': 'unreviewed'}, {'decision': {'calendar_cleared': False}},
                       {'artifact': {'sha256': '0'*64}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.convert(manifest={**self.manifest, **change})

    def test_invalid_bytes_boundaries_and_overlarge_inputs_fail(self):
        for raw in (None, 'csv', b'x'*2_000_001):
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(ValueError):
                calendar_rows_from_snapshot(raw, b'{}', start=self.first, end=self.last)
        with self.assertRaises(ValueError): self.convert(start=self.last, end=self.first)
