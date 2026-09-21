"""Synthetic credit-premium decisions: no real sources or ETF outcomes."""
from datetime import date, timedelta
from decimal import Decimal
import unittest

from quant_robot.research.credit_premium_cadence import (
    decision, month_name, monthly_premiums, quarterly_intervals, calculate,
)
from quant_robot.research.enterprise_liquidity_cadence import later_intervals, screen_counts


def months():
    return [dict(month=month_name(i), status='conditional', government_1y_percent='2',
                 corporate_1y_percent=str(Decimal(2)+Decimal(i)/100))
            for i in range(2011*12+11, 2023*12+9)]


def sessions():
    a, b = date(2013, 1, 1), date(2024, 1, 10)
    return [(a+timedelta(days=i)).isoformat() for i in range((b-a).days+1)
            if (a+timedelta(days=i)).weekday() < 5
            and (a+timedelta(days=i)).strftime('%m-%d') != '01-01']


class CreditPremiumCadenceTests(unittest.TestCase):
    def test_prior12_excludes_current_and_uses_even_median(self):
        last = 2012*12+11
        premiums = {month_name(i): Decimal(i-(last-12)) for i in range(last-12, last)}
        premiums[month_name(last)] = Decimal('5.6')
        result = decision(premiums, last)
        self.assertEqual(result['prior12_median_percent'], '5.5')
        self.assertEqual(result['state'], 1)
        premiums[month_name(last)] = Decimal('5.5')
        self.assertEqual(decision(premiums, last)['state'], 0)

    def test_same_tenor_subtraction_and_negative_premiums_are_preserved(self):
        source = months()
        source[0]['corporate_1y_percent'] = '1.0001'
        source[0]['government_1y_percent'] = '2.0002'
        self.assertEqual(monthly_premiums(source)['2011-12'], Decimal('-1.0001'))

    def test_unknown_does_not_use_the_retained_raw_yields(self):
        source = months()
        source[0]['status'] = 'unknown'
        self.assertIsNone(monthly_premiums(source)['2011-12'])
        self.assertIsNone(quarterly_intervals(source, sessions())[0]['state'])

    def test_unknown_propagates_thirteen_calendar_months_without_row_dropping(self):
        source = months()
        next(r for r in source if r['month'] == '2020-01')['status'] = 'unknown'
        rows = quarterly_intervals(source, sessions())
        self.assertEqual([r['source_month'] for r in rows if r['state'] is None],
                         ['2020-03', '2020-06', '2020-09', '2020-12'])
        self.assertEqual(len(rows), 44)
        self.assertEqual(rows[28]['state'], 1)
        self.assertEqual(rows[33]['state'], 1)

    def test_quarter_end_current_unknown_is_included(self):
        source = months()
        next(r for r in source if r['month'] == '2023-09')['status'] = 'unknown'
        row = quarterly_intervals(source, sessions())[-1]
        self.assertIsNone(row['state'])
        self.assertEqual(row['missing_months'], ['2023-09'])

    def test_exact_quarter_anchors_and_complete_partition(self):
        days = sessions()
        rows = quarterly_intervals(months(), days)
        self.assertEqual((rows[0]['entry_date'], rows[-1]['exit_date']), ('2013-01-02', '2024-01-02'))
        self.assertEqual([r['source_month'] for r in rows[:2]], ['2012-12', '2013-03'])
        self.assertEqual(len(rows), 44)
        self.assertTrue(all(a['exit_date'] == b['entry_date'] for a, b in zip(rows, rows[1:])))
        self.assertEqual(sum(r['sessions'] for r in rows), days.index('2024-01-02'))

    def test_persistent_selected_state_is_one_episode_and_later_carry_in(self):
        days = sessions()
        rows = quarterly_intervals(months(), days)
        later = later_intervals(rows, days)
        screen = screen_counts(rows, later)
        self.assertEqual(len(later), 16)
        self.assertEqual(screen['full']['selected_intervals'], 44)
        self.assertEqual(screen['full']['selected_episodes'], 1)
        self.assertEqual(screen['later']['new_selected_episodes'], 0)
        self.assertEqual(screen['later']['carry_in_episodes'], 1)
        self.assertFalse(screen['passed'])

    def test_new_state_on_later_boundary_counts_as_new_entry(self):
        source = months()
        next(r for r in source if r['month'] == '2019-09')['corporate_1y_percent'] = '-999'
        days = sessions()
        rows = quarterly_intervals(source, days)
        screen = screen_counts(rows, later_intervals(rows, days))
        self.assertEqual(rows[27]['state'], 0)
        self.assertEqual(screen['later']['new_selected_episodes'], 1)
        self.assertEqual(screen['later']['carry_in_episodes'], 0)

    def test_nonfinite_or_malformed_conditional_yield_rejected(self):
        for value in ['NaN', 'Infinity', 'bad', None]:
            source = months()
            source[0]['corporate_1y_percent'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                monthly_premiums(source)

    def test_missing_duplicate_or_out_of_order_month_rejected(self):
        source = months()
        for rows in [source[1:], source+[source[-1]], source[::-1]]:
            with self.assertRaises(ValueError):
                monthly_premiums(rows)

    def test_invalid_or_missing_quarter_calendar_rejected(self):
        days = sessions()
        for calendar in [days[::-1], days+[days[-1]],
                         [d for d in days if not d.startswith('2019-04')]]:
            with self.assertRaises(ValueError):
                quarterly_intervals(months(), calendar)

    def test_minima_are_conjunctive_and_require_known_cash(self):
        days = sessions()
        rows = quarterly_intervals(months(), days)
        screen = screen_counts(rows, later_intervals(rows, days))
        self.assertTrue(screen['checks']['full_selected_intervals'])
        self.assertFalse(screen['checks']['full_known_cash'])
        self.assertFalse(screen['checks']['later_known_cash'])
        self.assertFalse(screen['passed'])
