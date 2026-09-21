import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from quant_robot.data.analyst_forecast_events import normalize_analyst_response


OBSERVED = datetime(2024, 1, 3, 2, tzinfo=timezone.utc)
BASE = {
    'ts_code': '600519.SH', 'report_date': '20240102', 'quarter': '2024Q4',
    'org_name': 'Synthetic A', 'author_name': 'Analyst A', 'report_title': 'Forecast',
    'np': '100.01', 'eps': '1.001', 'tp': '200.00',
    'min_price': '10', 'max_price': '14', 'create_time': '2024-01-02 21:30:00',
}


def payload(*rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    return json.dumps({'code': 0, 'data': {'fields': fields, 'items': [[row.get(key) for key in fields] for row in rows]}}, ensure_ascii=False).encode('utf-8')


class AnalystForecastEventTests(unittest.TestCase):
    def normalize(self, *rows, observed=OBSERVED):
        return normalize_analyst_response(payload(*(rows or (BASE,))), observed_at=observed)

    def test_distinct_forecast_periods_survive(self):
        batch = self.normalize(BASE, {**BASE, 'quarter': '2025Q4'})
        self.assertEqual({e.forecast_period for e in batch.events}, {'2024Q4', '2025Q4'})
        self.assertEqual(len({e.record_id for e in batch.events}), 2)

    def test_institution_and_author_changes_have_separate_match_keys(self):
        batch = self.normalize(BASE, {**BASE, 'org_name': 'Synthetic B'}, {**BASE, 'author_name': 'Analyst B'})
        self.assertEqual(len({e.match_key for e in batch.events}), 3)

    def test_profit_total_is_separate_from_target_range(self):
        event = self.normalize().events[0]
        self.assertEqual(event.total_profit, Decimal('200'))
        self.assertEqual(event.target_price, Decimal('12'))
        missing = self.normalize({**BASE, 'min_price': None, 'max_price': None}).events[0]
        self.assertIsNone(missing.target_price)

    def test_same_observation_reordering_preserves_event_identities(self):
        other = {**BASE, 'quarter': '2025Q4'}
        left, right = self.normalize(BASE, other), self.normalize(other, BASE)
        self.assertEqual([e.version_id for e in left.events], [e.version_id for e in right.events])
        self.assertNotEqual(left.source_sha256, right.source_sha256)

    def test_exact_duplicates_retain_source_row_count(self):
        batch = self.normalize(BASE, BASE)
        self.assertEqual(batch.raw_rows, 2)
        self.assertEqual(len(batch.events), 1)
        self.assertEqual(batch.events[0].source_rows, (0, 1))

    def test_conflicting_same_identity_and_update_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'conflicting_forecast_version'):
            self.normalize(BASE, {**BASE, 'np': '101'})

    def test_later_provider_correction_is_retained_separately(self):
        batch = self.normalize(BASE, {**BASE, 'np': '101', 'create_time': '2024-01-03 09:00:00'})
        self.assertEqual(len(batch.events), 2)
        self.assertEqual(len({e.record_id for e in batch.events}), 1)
        self.assertEqual(len({e.version_id for e in batch.events}), 2)

    def test_missing_provider_update_remains_unknown(self):
        event = self.normalize({**BASE, 'create_time': None}).events[0]
        self.assertIsNone(event.provider_updated_at)
        self.assertFalse(event.historical_availability_verified)
        self.assertEqual(event.available_at, OBSERVED)

    def test_historical_report_cannot_precede_actual_observation(self):
        later = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(self.normalize(observed=later).events[0].available_at, later)

    def test_same_day_capture_waits_until_next_china_midnight(self):
        observed = datetime(2024, 1, 2, 14, tzinfo=timezone.utc)
        self.assertEqual(self.normalize(observed=observed).events[0].available_at,
                         datetime(2024, 1, 2, 16, tzinfo=timezone.utc))

    def test_naive_observation_and_future_update_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'observed_at_timezone_required'):
            self.normalize(observed=datetime(2024, 1, 3))
        with self.assertRaisesRegex(ValueError, 'provider_update_after_observation'):
            self.normalize({**BASE, 'create_time': '2024-01-04 09:00:00'})

    def test_update_before_report_and_future_report_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'provider_update_before_report'):
            self.normalize({**BASE, 'create_time': '2024-01-01 09:00:00'})
        with self.assertRaisesRegex(ValueError, 'report_after_observation'):
            self.normalize({**BASE, 'report_date': '20240104'})

    def test_missing_identity_and_invalid_period_are_rejected(self):
        for field in ('org_name', 'author_name', 'report_title', 'quarter', 'ts_code'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.normalize({**BASE, field: None})
        for bad_period in ('2024', '0000Q4', '２０２４Q4'):
            with self.subTest(period=bad_period), self.assertRaises(ValueError):
                self.normalize({**BASE, 'quarter': bad_period})
        with self.assertRaises(ValueError):
            self.normalize({**BASE, 'ts_code': '６００５１９.SH'})

    def test_invalid_numerics_are_rejected_without_silent_filtering(self):
        for value in ('NaN', 'Infinity', True, 'not a number'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.normalize({**BASE, 'np': value})

    def test_missing_and_zero_forecasts_remain_distinct(self):
        missing = self.normalize({**BASE, 'np': None}).events[0]
        zero = self.normalize({**BASE, 'np': 0}).events[0]
        self.assertIsNone(missing.net_profit)
        self.assertEqual(zero.net_profit, Decimal(0))

    def test_json_decimal_is_not_rounded_through_binary_float(self):
        raw = payload(BASE).replace(b'"100.01"', b'100.123456789012345678901')
        event = normalize_analyst_response(raw, observed_at=OBSERVED).events[0]
        self.assertEqual(event.net_profit, Decimal('100.123456789012345678901'))

    def test_malformed_envelopes_and_duplicate_fields_are_rejected(self):
        for packet in ({'code': True, 'data': {}}, {'code': 1, 'data': {}},
                       {'code': 0, 'data': {'fields': ['np', 'np'], 'items': []}},
                       {'code': 0, 'data': {'fields': ['ts_code'], 'items': [[]]}}):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                normalize_analyst_response(json.dumps(packet).encode(), observed_at=OBSERVED)
        with self.assertRaises(ValueError):
            normalize_analyst_response(b'{"code":0,"code":0,"data":{}}', observed_at=OBSERVED)

    def test_processed_cache_is_not_an_original_response(self):
        with self.assertRaises(ValueError):
            normalize_analyst_response(json.dumps([BASE]).encode(), observed_at=OBSERVED)

    def test_target_midpoint_does_not_depend_on_callers_decimal_context(self):
        event = self.normalize({**BASE, 'min_price': '10.00000000000000000001',
                               'max_price': '14.00000000000000000001'}).events[0]
        with localcontext() as context:
            context.prec = 5
            self.assertEqual(event.target_price, Decimal('12.00000000000000000001'))

    def test_equivalent_timezone_and_decimal_spellings_share_version_identity(self):
        other = {**BASE, 'np': '100.010', 'create_time': '2024-01-02T13:30:00+00:00'}
        self.assertEqual(self.normalize().events[0].version_id, self.normalize(other).events[0].version_id)

    def test_pagination_metadata_is_retained_without_completeness_claim(self):
        packet = json.loads(payload(BASE))
        packet['data'].update(has_more=True, count=0)
        batch = normalize_analyst_response(json.dumps(packet).encode(), observed_at=OBSERVED)
        self.assertIs(batch.provider_has_more, True)
        self.assertEqual(batch.provider_count, 0)
        self.assertEqual(batch.raw_rows, 1)
        self.assertFalse(batch.source_completeness_verified)
        self.assertIsNone(self.normalize().provider_has_more)

    def test_malformed_pagination_metadata_is_rejected(self):
        for changes in ({'has_more':'false'}, {'has_more':0}, {'count':True}, {'count':-1}):
            packet = json.loads(payload(BASE))
            packet['data'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                normalize_analyst_response(json.dumps(packet).encode(), observed_at=OBSERVED)
