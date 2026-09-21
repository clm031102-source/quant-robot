import tempfile
import unittest

import pandas as pd

from quant_robot.data.ingest.tushare_analyst_reports import (
    _normalize_analyst_report_rc,
    run_tushare_analyst_report_cache,
)
from quant_robot.ops.analyst_report_revision_prescreen import _daily_report_snapshot


class AnalystReportSourceContractTests(unittest.TestCase):
    def test_profit_total_cannot_supply_missing_target_price(self):
        frame = _normalize_analyst_report_rc(pd.DataFrame([_row(tp=1000000)]))
        self.assertTrue(pd.isna(_daily_report_snapshot(frame).iloc[0]['target_price']))

    def test_target_midpoint_uses_price_fields_and_ignores_profit_total(self):
        frame = _normalize_analyst_report_rc(pd.DataFrame([_row(tp=1000000, min_price=10, max_price=14)]))
        self.assertEqual(_daily_report_snapshot(frame).iloc[0]['target_price'], 12)

    def test_invalid_target_ranges_are_not_prices(self):
        for low, high in [(14, 10), (-2, 10), (0, 10), (10, float('inf')), (None, 14)]:
            with self.subTest(low=low, high=high):
                frame = _normalize_analyst_report_rc(pd.DataFrame([_row(tp=1000000, min_price=low, max_price=high)]))
                self.assertTrue(pd.isna(_daily_report_snapshot(frame).iloc[0]['target_price']))

    def test_default_cap_detects_3000_raw_rows_before_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_analyst_report_cache(
                _CappedResponse(), '2024-01-01', '2024-01-31', tmp,
                execute_write_processed=False, request_sleep_seconds=0,
            )
        self.assertEqual(result['summary']['rows'], 1)
        self.assertEqual(result['summary']['row_cap_warning_windows'], 1)

    def test_user_warning_threshold_cannot_hide_documented_provider_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_analyst_report_cache(
                _CappedResponse(), '2024-01-01', '2024-01-31', tmp,
                execute_write_processed=False, request_sleep_seconds=0, max_rows_per_window=5000,
            )
        self.assertEqual(result['effective_row_warning_threshold'], 3000)
        self.assertEqual(result['summary']['row_cap_warning_windows'], 1)


def _row(**fields):
    return {'ts_code': '000001.SZ', 'report_date': '20240102', 'quarter': '2024Q4',
            'org_name': 'Synthetic', 'author_name': 'Synthetic', 'report_title': 'Synthetic', **fields}


class _CappedResponse:
    def fetch_report_rc(self, **kwargs):
        return pd.DataFrame([_row()] * 3000)
