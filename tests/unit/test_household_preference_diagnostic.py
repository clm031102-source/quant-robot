from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
import tempfile
import unittest

from quant_robot.research.household_preference_diagnostic import (
    SurveyObservation, annual_preference_gate, visible_annual_window,
    event_log_selection_diagnostic,
)


class HouseholdPreferenceDiagnosticTests(unittest.TestCase):
    def history(self):
        return {'2019Q1': '10', '2019Q2': '20', '2019Q3': '10',
                '2019Q4': '20', '2020Q1': '15'}

    def observations(self):
        return [SurveyObservation(q, date(2020, 4, 1), value)
                for q, value in self.history().items()]

    def test_annual_tie_is_cash_and_strictly_lower_is_holding(self):
        values = self.history()
        self.assertEqual(annual_preference_gate(values), 0)
        values['2020Q1'] = '14.9'
        self.assertEqual(annual_preference_gate(values), 1)

    def test_exact_decimal_comparison_does_not_depend_on_ambient_precision(self):
        values = self.history(); values['2020Q1'] = '14.999999999999999999999999999999999999999999'
        with localcontext() as context:
            context.prec = 5
            self.assertEqual(annual_preference_gate(values), 1)

    def test_missing_quarter_cannot_be_replaced_by_an_older_one(self):
        values = self.history(); values['2018Q4'] = values.pop('2019Q3')
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            annual_preference_gate(values)

    def test_invalid_quarters_and_percentage_values_are_rejected(self):
        for bad in (True, None, 'NaN', 'Infinity', '-1', '100.01', ''):
            with self.subTest(value=bad):
                values = self.history(); values['2020Q1'] = bad
                with self.assertRaises(ValueError): annual_preference_gate(values)
        for key in ('2020Q0', '2020Q5', '2020-Q1'):
            values = self.history(); values[key] = values.pop('2020Q1')
            with self.assertRaises(ValueError): annual_preference_gate(values)
        with self.assertRaises(ValueError): annual_preference_gate({})

    def test_same_day_release_batch_uses_latest_quarter_once(self):
        rows = self.observations() + [SurveyObservation('2020Q2', date(2020, 4, 1), '12')]
        window = visible_annual_window(list(reversed(rows)), date(2020, 4, 1))
        self.assertEqual(list(window), ['2019Q2', '2019Q3', '2019Q4', '2020Q1', '2020Q2'])
        self.assertEqual(window['2020Q2'], Decimal('12'))

    def test_future_observation_does_not_enter_reference_or_value_validation(self):
        rows = self.observations() + [SurveyObservation('2020Q2', date(2020, 5, 1), 'not yet visible')]
        self.assertEqual(visible_annual_window(rows, date(2020, 4, 1)),
                         {q: Decimal(v) for q, v in self.history().items()})
        with self.assertRaises(ValueError): visible_annual_window(rows, date(2020, 5, 1))

    def test_duplicate_or_missing_visible_report_is_not_silently_replaced(self):
        rows = self.observations()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            visible_annual_window(rows + rows[:1], date(2020, 4, 1))
        with self.assertRaises(ValueError): visible_annual_window(rows[:-1], date(2020, 4, 1))
        with self.assertRaises(ValueError): visible_annual_window(rows, date(2020, 3, 31))

    def test_availability_is_explicit_date_not_report_quarter_or_datetime(self):
        rows = self.observations()
        for bad in ('2020-04-01', datetime(2020, 4, 1)):
            with self.assertRaises(ValueError): visible_annual_window(rows, bad)
            invalid = [SurveyObservation('2019Q1', bad, '10')] + rows[1:]
            with self.assertRaises(ValueError): visible_annual_window(invalid, date(2020, 4, 1))

    def calendar(self):
        return [date(2020, 1, 1) + timedelta(days=i) for i in range(5)]

    def test_variable_intervals_match_session_weighted_hand_calculation(self):
        sessions = self.calendar()
        result = event_log_selection_diagnostic([sessions[0], sessions[1], sessions[4]],
                                               [1, 0], ['1', '2', '4'], sessions)
        with localcontext() as context:
            context.prec = 34
            expected = Decimal(2).ln() / 8
        self.assertLess(abs(Decimal(result['gross_daily_log_selection_difference']) - expected), Decimal('1e-32'))
        self.assertEqual(result['session_weighted_exposure'], '0.25')
        self.assertEqual(result['session_counts'], [1, 3])
        self.assertFalse(result['net_account_result'])
        self.assertFalse(result['formal_positive_ev_verified'])
        self.assertFalse(result['research_admission_granted'])

    def test_subdividing_same_signal_interval_cannot_create_an_advantage(self):
        sessions = self.calendar()
        whole = event_log_selection_diagnostic([sessions[0], sessions[2], sessions[4]], [1, 0], [1, 4, 16], sessions)
        split = event_log_selection_diagnostic([sessions[0], sessions[1], sessions[2], sessions[4]], [1, 1, 0], [1, 2, 4, 16], sessions)
        self.assertLess(abs(Decimal(whole['gross_daily_log_selection_difference']) - Decimal(split['gross_daily_log_selection_difference'])), Decimal('1e-32'))
        self.assertEqual(whole['signal_switches'], split['signal_switches'])

    def test_negative_zero_and_constant_signal_are_rejected(self):
        sessions = self.calendar(); anchors = [sessions[0], sessions[1], sessions[4]]
        for signals, levels in (([0, 1], [1, 2, 4]), ([1, 0], [1, 1, 1]), ([1, 1], [1, 2, 4])):
            with self.subTest(signals=signals, levels=levels):
                result = event_log_selection_diagnostic(anchors, signals, levels, sessions)
                self.assertEqual(result['decision'], 'reject_fixed_diagnostic')

    def test_terminal_signal_invalid_levels_or_nonbinary_signals_fail(self):
        sessions = self.calendar(); anchors = [sessions[0], sessions[4]]
        for signals, levels in (([1, 0], [1, 2]), ([True], [1, 2]), ([2], [1, 2]), ([1], [1]), ([1], [1, 0]), ([1], [1, 'NaN'])):
            with self.subTest(signals=signals, levels=levels):
                with self.assertRaises(ValueError): event_log_selection_diagnostic(anchors, signals, levels, sessions)

    def test_anchors_must_be_ordered_unique_and_present_in_calendar(self):
        sessions = self.calendar()
        for anchors in ([sessions[1], sessions[0]], [sessions[0], sessions[0]], [sessions[0], date(2020, 2, 1)]):
            with self.assertRaises(ValueError): event_log_selection_diagnostic(anchors, [1], [1, 2], sessions)
        for calendar in (sessions[::-1], sessions + sessions[-1:], sessions[:-1]):
            with self.assertRaises(ValueError): event_log_selection_diagnostic([sessions[0], sessions[-1]], [1], [1, 2], calendar)

    def test_scale_and_ambient_precision_do_not_change_primary_diagnostic(self):
        sessions = self.calendar(); anchors = [sessions[0], sessions[1], sessions[4]]
        a = event_log_selection_diagnostic(anchors, [1, 0], [1, 2, 4], sessions)
        with localcontext() as context:
            context.prec = 5
            b = event_log_selection_diagnostic(anchors, [1, 0], [10, 20, 40], sessions)
        self.assertEqual(a['gross_daily_log_selection_difference'], b['gross_daily_log_selection_difference'])

    def test_closed_calendar_days_do_not_inflate_interval_exposure(self):
        sessions = [date(2020, 5, day) for day in (1, 6, 7, 8, 9)]
        result = event_log_selection_diagnostic([sessions[0], sessions[1], sessions[-1]],
                                               [1, 0], [1, 2, 4], sessions)
        self.assertEqual(result['session_counts'], [1, 3])
        self.assertEqual(result['session_weighted_exposure'], '0.25')

    def test_identical_growth_per_session_has_no_timing_advantage(self):
        for base in (2, 3, 5, 10):
            for n1, n2 in ((1, 2), (2, 3), (3, 7)):
                with self.subTest(base=base, lengths=(n1, n2)):
                    sessions = [date(2000, 1, 1) + timedelta(days=i) for i in range(n1 + n2 + 1)]
                    result = event_log_selection_diagnostic([sessions[0], sessions[n1], sessions[-1]],
                                                           [1, 0], [1, base**n1, base**(n1+n2)], sessions)
                    self.assertEqual(Decimal(result['gross_daily_log_selection_difference']), 0)
                    self.assertEqual(result['decision'], 'reject_fixed_diagnostic')

    def test_gross_cash_reinvestment_does_not_turn_ex_dividend_drop_into_edge(self):
        from quant_robot.research.price_basis import build_cash_action_research_prices
        from tests.unit.test_research_price_basis import fixture_bars, explicit_dividend, write_actions

        sessions = [date(2024, 1, 2), date(2024, 1, 31), date(2024, 2, 1), date(2024, 3, 1)]
        bars = fixture_bars([10, 10, 9, 9]); bars['date'] = sessions
        event = explicit_dividend(announced_date='2024-01-02', record_date='2024-01-31',
                                  ex_date='2024-02-01', pay_date='2024-03-01')
        with tempfile.TemporaryDirectory() as tmp:
            actions = write_actions(tmp, [event], version=3, coverage_end='2024-03-01')
            prices = build_cash_action_research_prices(bars, actions, sessions=sessions)
        result = event_log_selection_diagnostic([sessions[0], sessions[2], sessions[3]],
                                               [0, 1], prices.bars['adj_close'].iloc[[0, 2, 3]].tolist(), sessions)
        self.assertEqual(Decimal(result['gross_daily_log_selection_difference']), 0)
        self.assertEqual(result['decision'], 'reject_fixed_diagnostic')


if __name__ == '__main__':
    unittest.main()
