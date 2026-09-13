import unittest
from datetime import date, timedelta
from decimal import Decimal, localcontext

from quant_robot.research.month_start_liquidity_diagnostic import (
    month_start_positions, month_start_diagnostic,
)


def calendar_rows(start=date(2020, 1, 1), end=date(2020, 3, 2), closed=()):
    return [(start + timedelta(days=i), (start + timedelta(days=i)).weekday() < 5
             and start + timedelta(days=i) not in closed)
            for i in range((end-start).days+1)]


class MonthStartLiquidityTests(unittest.TestCase):
    first, last = date(2020, 1, 1), date(2020, 2, 1)

    def positions(self, rows):
        return month_start_positions(rows, first_month=self.first, last_month=self.last)

    def run_study(self, rows, prices):
        return month_start_diagnostic(rows, prices, first_month=self.first, last_month=self.last)

    def test_positions_use_only_observed_first_two_sessions(self):
        rows = calendar_rows(closed=(date(2020, 1, 1), date(2020, 2, 3)))
        positions = dict(self.positions(rows))
        self.assertEqual([positions[date(2020, 1, d)] for d in (2, 3, 6, 7)], [1, 1, 0, 0])
        self.assertEqual([positions[date(2020, 2, d)] for d in (4, 5, 6, 7)], [1, 1, 0, 0])
        self.assertEqual(positions[date(2020, 3, 2)], 0)

    def test_future_calendar_extension_never_changes_past_positions(self):
        rows = calendar_rows()
        for size in (1, 2, 3, 12, 31, 32, 34):
            prefix = rows[:size]
            self.assertEqual(self.positions(prefix), tuple(x for x in self.positions(rows)
                                                         if x[0] <= prefix[-1][0]))

    def test_calendar_requires_civil_days_and_month_start(self):
        rows = calendar_rows()
        for bad in (rows[1:], rows[:7]+rows[8:], rows[:7]+[rows[6]]+rows[7:], list(reversed(rows))):
            with self.subTest(bad_length=len(bad)), self.assertRaises(ValueError):
                self.positions(bad)

    def test_calendar_rejects_non_boolean_open_flags_and_bad_months(self):
        with self.assertRaises(ValueError):
            self.positions([(date(2020, 1, 1), 1)])
        for first, last in ((date(2020, 1, 2), self.last), (self.last, self.first)):
            with self.assertRaises(ValueError):
                month_start_positions(calendar_rows(), first_month=first, last_month=last)

    def test_exact_two_close_changes_and_cost_on_changed_exit_value(self):
        rows = calendar_rows()
        positions = self.positions(rows)
        prices = {}; level = Decimal(100)
        previous = 0
        for day, position in positions:
            if previous:
                level *= Decimal('1.02')
            prices[day] = str(level)
            previous = position
        result = self.run_study(rows, prices)
        self.assertEqual(result['cycle_count'], 2)
        self.assertEqual(result['selected_close_to_close_transitions'], 4)
        cycle = result['cycles'][0]
        self.assertEqual(Decimal(cycle['gross_return']), Decimal('.0404'))
        self.assertEqual(Decimal(cycle['commission_scenarios'][0]['sell_fee_cny']), Decimal('.5202'))
        self.assertEqual(Decimal(cycle['commission_scenarios'][0]['pnl_cny']), Decimal('39.3798'))
        self.assertEqual(Decimal(cycle['commission_scenarios'][1]['pnl_cny']), Decimal('30.4'))
        self.assertEqual(result['decision'], 'review_separate_account_study_only')
        self.assertFalse(result['net_account_result'])
        self.assertFalse(result['formal_positive_ev_verified'])

    def test_constant_prices_close_direction_and_preserve_all_cost_scenarios(self):
        rows = calendar_rows(); prices = {day: '100' for day, _ in self.positions(rows)}
        result = self.run_study(rows, prices)
        self.assertEqual(result['decision'], 'reject_calendar_direction')
        self.assertEqual([Decimal(x['mean_pnl_cny']) for x in result['commission_scenarios']],
                         [Decimal('-1'), Decimal('-10'), Decimal('-20')])

    def test_positive_gross_with_only_zero_minimum_profit_is_fee_dependent(self):
        rows = calendar_rows(); level = Decimal(100); prior = 0; prices = {}
        for day, position in self.positions(rows):
            if prior: level *= Decimal('1.001')
            prices[day] = str(level); prior = position
        result = self.run_study(rows, prices)
        self.assertGreater(Decimal(result['commission_scenarios'][0]['mean_pnl_cny']), 0)
        self.assertLess(Decimal(result['commission_scenarios'][1]['mean_pnl_cny']), 0)
        self.assertEqual(result['decision'], 'defer_fee_dependent_no_account_admission')

    def test_tiny_positive_effect_can_fail_even_without_minimum_commission(self):
        rows = calendar_rows(); level = Decimal(100); prior = 0; prices = {}
        for day, position in self.positions(rows):
            if prior: level *= Decimal('1.00001')
            prices[day] = str(level); prior = position
        self.assertEqual(self.run_study(rows, prices)['decision'], 'reject_commission_screen')

    def test_zero_working_fee_profit_cannot_advance_to_account_review(self):
        rows = calendar_rows(); prices = {}; level = Decimal(100)
        for day, position in self.positions(rows):
            # Place one exactly 1% increase inside each selected holding interval.
            if day in (date(2020, 1, 3), date(2020, 2, 5)): level *= Decimal('1.01')
            prices[day] = str(level)
        result = self.run_study(rows, prices)
        self.assertEqual(Decimal(result['commission_scenarios'][1]['decision_mean_pnl_cny']), 0)
        self.assertEqual(result['decision'], 'defer_fee_dependent_no_account_admission')

    def test_december_to_january_does_not_merge_month_ordinals(self):
        first, last = date(2020, 12, 1), date(2021, 1, 1)
        rows = calendar_rows(start=first, end=date(2021, 2, 1))
        positions = month_start_positions(rows, first_month=first, last_month=last)
        result = month_start_diagnostic(rows, {day: '100' for day, _ in positions},
                                        first_month=first, last_month=last)
        self.assertEqual([c['month'] for c in result['cycles']], ['2020-12', '2021-01'])
        self.assertEqual(result['selected_close_to_close_transitions'], 4)

    def test_incomplete_last_month_or_insufficient_open_days_cannot_be_dropped(self):
        for rows in (calendar_rows(end=date(2020, 2, 6)),
                     [(day, opened and not (day.month == 2 and day.day > 4))
                      for day, opened in calendar_rows()]):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                self.run_study(rows, {day: '100' for day, opened in rows if opened})

    def test_exact_price_coverage_and_positive_finite_values_required(self):
        rows = calendar_rows(); prices = {day: '100' for day, _ in self.positions(rows)}
        for bad in ('NaN', 'Infinity', '0', '-1', True, None):
            altered = dict(prices); altered[next(iter(prices))] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.run_study(rows, altered)
        for changed in ({**prices, date(2020, 4, 1): '100'}, dict(list(prices.items())[1:])):
            with self.assertRaises(ValueError): self.run_study(rows, changed)

    def test_first_session_return_is_excluded(self):
        rows = calendar_rows(); positions = self.positions(rows)
        prices = {day: ('200' if day >= date(2020, 2, 3) else '100') for day, _ in positions}
        result = self.run_study(rows, prices)
        self.assertEqual([Decimal(c['gross_return']) for c in result['cycles']], [Decimal(0)]*2)
        self.assertLess(Decimal(result['gross_diagnostic']['gross_daily_log_selection_difference']), 0)

    def test_decimal_calculation_is_independent_of_callers_context(self):
        rows = calendar_rows(); prices = {day: '100' for day, _ in self.positions(rows)}
        ordinary = self.run_study(rows, prices)
        with localcontext() as context:
            context.prec = 6
            context.rounding = 'ROUND_UP'
            changed = self.run_study(rows, prices)
        self.assertEqual(ordinary, changed)
