from copy import deepcopy
from decimal import Decimal, localcontext
import unittest

from quant_robot.data.etf_reported_holdings import review_snapshot, select_complete_snapshot


SESSIONS = ['2020-04-08', '2020-04-09', '2020-04-10', '2020-07-20',
            '2020-07-21', '2020-08-28', '2020-08-31', '2020-09-01', '2020-09-02', '2020-09-03']


def snapshot(*, period='2019-12-31', published='2020-04-09', scope='all_stocks', source='1'):
    return dict(symbol='510050.SH', period_end=period, publication_date=published,
                reported_scope=scope, source_sha256=source * 64, equity_total_cny='1000.01',
                holdings=[dict(ordinal=1, symbol='600000.SH', quantity=100,
                               fair_value_cny='1000.00', reported_nav_weight_percent='99.99'),
                          dict(ordinal=2, symbol='688001.SH', quantity=1,
                               fair_value_cny='0.01', reported_nav_weight_percent='0.00')])


class ReportedHoldingsTests(unittest.TestCase):
    def test_zero_displayed_weight_keeps_positive_holding_and_exact_sum(self):
        record = snapshot()
        result = review_snapshot(record, session_dates=SESSIONS)
        self.assertEqual(len(result['holdings']), 2)
        self.assertEqual(result['sum_fair_value_cny'], '1000.01')
        self.assertEqual(result['holdings'][1]['reported_nav_weight_percent'], '0.00')
        self.assertTrue(result['is_complete_disclosure'])
        self.assertFalse(result['historical_source_authority_verified'])
        self.assertFalse(result['factor_generation_allowed'])
        self.assertEqual(record, snapshot())

    def test_publication_date_is_not_period_end_or_same_day_availability(self):
        record = snapshot()
        self.assertEqual(review_snapshot(record, session_dates=SESSIONS)['available_from_session'], '2020-04-10')
        self.assertIsNone(select_complete_snapshot([record], symbol='510050.SH', as_of='2020-04-09', session_dates=SESSIONS))
        result = select_complete_snapshot([record], symbol='510050.SH', as_of='2020-04-10', session_dates=SESSIONS)
        self.assertEqual(result['period_end'], '2019-12-31')
        self.assertEqual(result['reported_period_age_days'], 101)

    def test_weekend_publication_waits_for_next_verified_session(self):
        record = snapshot(period='2020-06-30', published='2020-08-29')
        self.assertEqual(review_snapshot(record, session_dates=SESSIONS)['available_from_session'], '2020-08-31')
        self.assertIsNone(select_complete_snapshot([record], symbol='510050.SH', as_of='2020-08-30', session_dates=SESSIONS))

    def test_later_partial_report_cannot_replace_full_snapshot(self):
        full = snapshot()
        partial = snapshot(period='2020-06-30', published='2020-07-20', scope='top10_only', source='2')
        partial['holdings'] = partial['holdings'][:1]
        result = select_complete_snapshot([full, partial], symbol='510050.SH', as_of='2020-07-21', session_dates=SESSIONS)
        self.assertEqual(result['source_sha256'], full['source_sha256'])
        reviewed = review_snapshot(partial, session_dates=SESSIONS)
        self.assertFalse(reviewed['is_complete_disclosure'])
        self.assertLess(Decimal(reviewed['disclosed_equity_value_fraction']), 1)

    def test_partial_equal_to_total_is_still_not_declared_complete(self):
        partial = snapshot(scope='top10_only')
        result = review_snapshot(partial, session_dates=SESSIONS)
        self.assertEqual(Decimal(result['disclosed_equity_value_fraction']), 1)
        self.assertFalse(result['is_complete_disclosure'])
        self.assertIsNone(select_complete_snapshot([partial], symbol='510050.SH', as_of='2020-04-10', session_dates=SESSIONS))

    def test_new_full_snapshot_is_unavailable_until_its_own_publication(self):
        old = snapshot()
        new = snapshot(period='2020-06-30', published='2020-08-29', source='2')
        before = select_complete_snapshot([old, new], symbol='510050.SH', as_of='2020-08-28', session_dates=SESSIONS)
        after = select_complete_snapshot([old, new], symbol='510050.SH', as_of='2020-08-31', session_dates=SESSIONS)
        self.assertEqual(before['period_end'], '2019-12-31')
        self.assertEqual(after['period_end'], '2020-06-30')

    def test_late_old_period_revision_cannot_displace_newer_report_period(self):
        newer = snapshot(period='2020-06-30', published='2020-08-29', source='2')
        old_revision = snapshot(published='2020-09-01', source='3')
        result = select_complete_snapshot([newer, old_revision], symbol='510050.SH', as_of='2020-09-02', session_dates=SESSIONS)
        self.assertEqual(result['source_sha256'], newer['source_sha256'])

    def test_conflicting_same_period_same_publication_needs_review(self):
        first = snapshot()
        second = snapshot(source='2')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            select_complete_snapshot([first, second], symbol='510050.SH', as_of='2020-04-10', session_dates=SESSIONS)

    def test_missing_or_duplicate_holding_is_rejected(self):
        removed = snapshot()
        removed['holdings'].pop()
        duplicate = snapshot()
        duplicate['holdings'][1]['symbol'] = duplicate['holdings'][0]['symbol']
        gap = snapshot()
        gap['holdings'][1]['ordinal'] = 3
        for record in (removed, duplicate, gap):
            with self.subTest(record=record), self.assertRaises(ValueError):
                review_snapshot(record, session_dates=SESSIONS)

    def test_invalid_cash_quantity_weight_and_security_values_fail(self):
        for key, values in [('fair_value_cny', ['NaN', '1e3', '0.001', -1, 1000.0]),
                            ('quantity', [True, 0, 1.5, '100']),
                            ('reported_nav_weight_percent', ['NaN', '-1', '100.01', 1.0]),
                            ('symbol', ['600000', '600000.SZ', '000001.SH', ''] )]:
            for value in values:
                record = snapshot()
                record['holdings'][0][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    review_snapshot(record, session_dates=SESSIONS)

    def test_dates_scope_and_source_identity_require_explicit_valid_evidence(self):
        mutations = [('publication_date', '2019-12-30'), ('publication_date', '2026-01-01'),
                     ('period_end', '20191231'), ('reported_scope', 'index_constituents'),
                     ('source_sha256', ''), ('equity_total_cny', '0.00'), ('symbol', '600000')]
        for key, value in mutations:
            record = snapshot()
            record[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                review_snapshot(record, session_dates=SESSIONS)

    def test_unbounded_or_unordered_calendar_does_not_guess_availability(self):
        for dates in [[], ['2020-04-10'], ['2020-04-08', '2020-04-09'],
                      ['2020-04-08', '2020-04-10', '2020-04-09'], SESSIONS + [SESSIONS[-1]]]:
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                review_snapshot(snapshot(), session_dates=dates)

    def test_decimal_results_ignore_callers_low_precision(self):
        record = snapshot()
        with localcontext() as context:
            context.prec = 3
            result = review_snapshot(record, session_dates=SESSIONS)
        self.assertEqual(result['sum_fair_value_cny'], '1000.01')
        self.assertEqual(Decimal(result['disclosed_equity_value_fraction']), 1)

    def test_other_fund_snapshot_does_not_fill_missing_target_history(self):
        record = deepcopy(snapshot())
        record['symbol'] = '510300.SH'
        self.assertIsNone(select_complete_snapshot([record], symbol='510050.SH', as_of='2020-04-10', session_dates=SESSIONS))

    def test_partial_total_overflow_and_more_than_ten_rows_are_rejected(self):
        record = snapshot(scope='top10_only')
        record['equity_total_cny'] = '500.00'
        with self.assertRaises(ValueError):
            review_snapshot(record, session_dates=SESSIONS)

        record = snapshot(scope='top10_only')
        record['holdings'] = [dict(ordinal=i + 1, symbol=f'600{i:03d}.SH', quantity=1,
                                   fair_value_cny='1.00', reported_nav_weight_percent='0.01') for i in range(11)]
        with self.assertRaises(ValueError):
            review_snapshot(record, session_dates=SESSIONS)

    def test_malformed_record_fails_before_selecting_another_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'snapshot record'):
            select_complete_snapshot([snapshot(), None], symbol='510050.SH',
                                     as_of='2020-04-10', session_dates=SESSIONS)


if __name__ == '__main__':
    unittest.main()
