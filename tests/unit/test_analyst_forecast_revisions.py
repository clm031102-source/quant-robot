import unittest
from datetime import datetime, timezone
from decimal import Decimal, Inexact, ROUND_UP, localcontext

from quant_robot.data.analyst_forecast_events import normalize_analyst_response
from quant_robot.data.analyst_forecast_revisions import build_revision_trace
from tests.unit.test_analyst_forecast_events import BASE, payload


def observation(report_day, seen, **changes):
    row = {**BASE, 'report_date': report_day, 'create_time': report_day[:4]+'-'+report_day[4:6]+'-'+report_day[6:]+' 21:00:00', **changes}
    return normalize_analyst_response(payload(row), observed_at=datetime.fromisoformat(seen)).events[0]


END = datetime(2024, 2, 1, tzinfo=timezone.utc)
A = observation('20240102', '2024-01-03T02:00:00+00:00', np='100')
B = observation('20240103', '2024-01-04T02:00:00+00:00', np='120')


class AnalystForecastRevisionTests(unittest.TestCase):
    def trace(self, *events, **kwargs):
        return build_revision_trace(events, as_of=kwargs.pop('as_of', END), **kwargs)

    def test_same_target_new_report_has_real_revision(self):
        row = self.trace(A, B)[-1]
        self.assertEqual(row.kind, 'new_report_revision')
        self.assertEqual(row.net_profit_change, Decimal('20'))
        self.assertEqual(row.net_profit_relative_change, Decimal('.2'))
        self.assertEqual(row.previous_version_id, A.version_id)

    def test_target_period_institution_or_author_switch_cannot_create_revision(self):
        for change in ({'quarter':'2025Q4'}, {'org_name':'Synthetic B'}, {'author_name':'Analyst B'}):
            with self.subTest(change=change):
                other = observation('20240103', '2024-01-04T02:00:00+00:00', np='200', **change)
                rows = self.trace(A, other)
                self.assertEqual([r.kind for r in rows], ['baseline', 'baseline'])
                self.assertTrue(all(r.net_profit_relative_change is None for r in rows))

    def test_initial_bulk_observation_does_not_fabricate_past_revisions(self):
        first = observation('20240102', '2024-01-10T02:00:00+00:00', np='100')
        second = observation('20240103', '2024-01-10T02:00:00+00:00', np='200')
        rows = self.trace(first, second)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, 'baseline')
        self.assertEqual(rows[0].current_version_id, second.version_id)

    def test_existing_state_compares_once_with_latest_same_instant_report(self):
        middle = observation('20240103', '2024-01-10T02:00:00+00:00', np='150')
        latest = observation('20240104', '2024-01-10T02:00:00+00:00', np='200')
        rows = self.trace(A, middle, latest)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1].net_profit_relative_change, Decimal('1'))

    def test_arrival_order_cannot_change_trace(self):
        self.assertEqual(self.trace(A, B), self.trace(B, A))

    def test_future_observations_do_not_change_earlier_trace(self):
        self.assertEqual(self.trace(A, B, as_of=A.available_at), self.trace(A, as_of=A.available_at))

    def test_duplicate_recapture_does_not_create_another_transition(self):
        again = observation('20240102', '2024-01-10T02:00:00+00:00', np='100')
        self.assertEqual(self.trace(A, B, again), self.trace(A, B))

    def test_late_old_report_does_not_replace_current_baseline(self):
        late = observation('20240101', '2024-01-05T02:00:00+00:00', np='500')
        final = observation('20240106', '2024-01-07T02:00:00+00:00', np='180')
        rows = self.trace(A, B, late, final)
        self.assertEqual(rows[-2].kind, 'late_report_ignored')
        self.assertEqual(rows[-1].previous_version_id, B.version_id)
        self.assertEqual(rows[-1].net_profit_relative_change, Decimal('.5'))

    def test_provider_correction_is_separate_and_updates_future_baseline(self):
        correction = observation('20240102', '2024-01-03T06:00:00+00:00', np='110', create_time='2024-01-03 12:00:00')
        rows = self.trace(A, correction, B)
        self.assertEqual(rows[1].kind, 'provider_correction')
        self.assertIsNone(rows[1].net_profit_relative_change)
        self.assertEqual(rows[2].previous_version_id, correction.version_id)

    def test_correction_and_new_report_in_same_capture_are_not_a_pure_revision(self):
        correction = observation('20240102', B.observed_at.isoformat(), np='110',
                                 create_time='2024-01-03 21:00:00')
        later = observation('20240104', '2024-01-05T02:00:00+00:00', np='180')
        rows = self.trace(A, correction, B, later)
        self.assertEqual(rows[1].kind, 'new_report_with_baseline_change')
        self.assertIsNone(rows[1].net_profit_change)
        self.assertIsNone(rows[1].net_profit_relative_change)
        self.assertEqual(rows[1].net_profit_status, 'simultaneous_baseline_change')
        self.assertEqual(set(rows[1].observed_version_ids), {correction.version_id, B.version_id})
        self.assertEqual(rows[2].previous_version_id, B.version_id)
        self.assertEqual(rows[2].net_profit_relative_change, Decimal('.5'))

    def test_simultaneous_baseline_change_blocks_eps_even_with_share_basis(self):
        correction = observation('20240102', B.observed_at.isoformat(), eps='1.1',
                                 create_time='2024-01-03 21:00:00')
        rows = self.trace(A, correction, B, eps_basis_ids={A.version_id:'basis-a', B.version_id:'basis-a'})
        self.assertEqual(rows[-1].kind, 'new_report_with_baseline_change')
        self.assertIsNone(rows[-1].eps_relative_change)
        self.assertEqual(rows[-1].eps_status, 'simultaneous_baseline_change')
        self.assertEqual(rows, self.trace(B, A, correction, eps_basis_ids={A.version_id:'basis-a', B.version_id:'basis-a'}))

    def test_simultaneous_older_baseline_version_does_not_block_new_report(self):
        prior = observation('20240102', A.observed_at.isoformat(), np='100',
                            create_time='2024-01-03 09:00:00')
        stale = observation('20240102', B.observed_at.isoformat(), np='80')
        row = self.trace(prior, stale, B)[-1]
        self.assertEqual(row.kind, 'new_report_revision')
        self.assertEqual(row.net_profit_relative_change, Decimal('.2'))

    def test_simultaneous_missing_baseline_version_time_is_not_ordered(self):
        for missing_side in ('earlier', 'current'):
            with self.subTest(missing_side=missing_side):
                prior = observation('20240102', A.observed_at.isoformat(), np='100',
                                    create_time=None if missing_side == 'earlier' else '2024-01-02 21:00:00')
                changed = observation('20240102', B.observed_at.isoformat(), np='110',
                                      create_time=None if missing_side == 'current' else '2024-01-03 21:00:00')
                self.assertEqual(self.trace(prior, changed, B)[-1].kind, 'new_report_with_baseline_change')

    def test_simultaneous_nonbaseline_old_report_cannot_suppress_revision(self):
        unrelated = observation('20240101', B.observed_at.isoformat(), np='110',
                                create_time='2024-01-03 21:00:00')
        self.assertEqual(self.trace(A, unrelated, B)[-1].net_profit_relative_change, Decimal('.2'))

    def test_same_update_conflict_across_snapshots_is_rejected(self):
        conflict = observation('20240102', '2024-01-04T02:00:00+00:00', np='200')
        with self.assertRaisesRegex(ValueError, 'conflicting_forecast_version'):
            self.trace(A, conflict)

    def test_same_day_distinct_reports_block_until_strictly_later_baseline(self):
        conflict = observation('20240102', '2024-01-03T05:00:00+00:00', report_title='Other report', np='300')
        later = observation('20240104', '2024-01-05T02:00:00+00:00', np='180')
        rows = self.trace(A, conflict, B, later)
        self.assertEqual(rows[1].kind, 'ambiguous_report_order')
        self.assertEqual(rows[2].kind, 'baseline_after_ambiguity')
        self.assertIsNone(rows[2].net_profit_relative_change)
        self.assertEqual(rows[3].net_profit_relative_change, Decimal('.5'))

    def test_zero_previous_value_has_no_fabricated_denominator_floor(self):
        zero = observation('20240102', '2024-01-03T02:00:00+00:00', np='0')
        row = self.trace(zero, B)[-1]
        self.assertEqual(row.net_profit_change, Decimal('120'))
        self.assertIsNone(row.net_profit_relative_change)
        self.assertEqual(row.net_profit_status, 'zero_previous_value')

    def test_missing_value_breaks_comparison(self):
        missing = observation('20240102', '2024-01-03T02:00:00+00:00', np=None)
        row = self.trace(missing, B)[-1]
        self.assertIsNone(row.net_profit_change)
        self.assertEqual(row.net_profit_status, 'missing_previous_value')

    def test_eps_requires_matching_external_share_basis_identity(self):
        row = self.trace(A, B)[-1]
        self.assertIsNone(row.eps_relative_change)
        self.assertEqual(row.eps_status, 'share_basis_unverified')
        matched = self.trace(A, B, eps_basis_ids={A.version_id:'basis-a', B.version_id:'basis-a'})[-1]
        self.assertEqual(matched.eps_relative_change, Decimal('0'))
        self.assertFalse(matched.historical_availability_verified)

    def test_naive_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'as_of_timezone_required'):
            self.trace(A, as_of=datetime(2024, 2, 1))

    def test_same_version_from_different_payloads_has_deterministic_provenance(self):
        row = {**BASE, 'np':'100', 'create_time':'2024-01-02 21:00:00'}
        other = {**row, 'quarter':'2025Q4'}
        batch = normalize_analyst_response(payload(row, other), observed_at=A.observed_at)
        duplicate = next(e for e in batch.events if e.forecast_period == A.forecast_period)
        self.assertEqual(A.version_id, duplicate.version_id)
        self.assertNotEqual(A.source_sha256, duplicate.source_sha256)
        self.assertEqual(self.trace(A, duplicate, B), self.trace(duplicate, A, B))

    def test_missing_update_does_not_order_conflicting_versions(self):
        missing = observation('20240102', '2024-01-03T02:00:00+00:00', np='100', create_time=None)
        known = observation('20240102', '2024-01-03T02:00:00+00:00', np='120')
        rows = self.trace(missing, known, B)
        self.assertEqual(rows[0].kind, 'ambiguous_provider_version')
        self.assertEqual(rows[1].kind, 'baseline_after_ambiguity')

    def test_negative_forecast_improvement_uses_absolute_previous_value(self):
        first = observation('20240102', '2024-01-03T02:00:00+00:00', np='-100')
        second = observation('20240103', '2024-01-04T02:00:00+00:00', np='-80')
        self.assertEqual(self.trace(first, second)[-1].net_profit_relative_change, Decimal('.2'))

    def test_late_update_of_older_report_cannot_overwrite_latest_report(self):
        late = observation('20240102', '2024-01-05T02:00:00+00:00', np='400', create_time='2024-01-04 21:00:00')
        next_report = observation('20240106', '2024-01-07T02:00:00+00:00', np='180')
        self.assertEqual(self.trace(A, B, late, next_report)[-1].previous_version_id, B.version_id)

    def test_revision_arithmetic_does_not_inherit_callers_rounding_or_traps(self):
        first = observation('20240102', '2024-01-03T02:00:00+00:00', np='3')
        second = observation('20240103', '2024-01-04T02:00:00+00:00', np='4')
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_UP
            context.traps[Inexact] = True
            self.assertEqual(self.trace(first, second)[-1].net_profit_relative_change,
                             Decimal('0.' + '3' * 64))
