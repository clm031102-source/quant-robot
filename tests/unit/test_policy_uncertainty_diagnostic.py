from datetime import date
from decimal import Decimal
import tempfile
import unittest

from quant_robot.research.policy_uncertainty_diagnostic import monthly_median_gate, monthly_selection_diagnostic
from quant_robot.research.price_basis import build_cash_action_research_prices
from tests.unit.test_research_price_basis import fixture_bars, explicit_dividend, write_actions


class PolicyUncertaintyDiagnosticTests(unittest.TestCase):
    def history(self):
        return {date(2020, month, 1): str(month) for month in range(1, 13)} | {date(2021, 1, 1): '6.5'}

    def test_tie_uses_previous_twelve_median_and_holds(self):
        self.assertEqual(monthly_median_gate(self.history()), 1)

    def test_latest_is_not_in_its_own_reference_window(self):
        values = self.history(); values[date(2021, 1, 1)] = '6.75'
        self.assertEqual(monthly_median_gate(values), 0)

    def test_missing_month_cannot_be_replaced_by_older_input(self):
        values = self.history(); values.pop(date(2020, 4, 1)); values[date(2019, 12, 1)] = '4'
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            monthly_median_gate(values)

    def test_invalid_or_incomplete_policy_values_are_rejected(self):
        for invalid in (True, None, 'NaN', 'Infinity', '-1', ''):
            with self.subTest(invalid=invalid):
                values = self.history(); values[date(2021, 1, 1)] = invalid
                with self.assertRaises(ValueError): monthly_median_gate(values)
        with self.assertRaises(ValueError): monthly_median_gate({})

    def test_primary_difference_matches_hand_calculation(self):
        result = monthly_selection_diagnostic([date(2020, 1, 2), date(2020, 2, 3), date(2020, 3, 2)], [1, 0], ['100', '110', '99'])
        self.assertEqual(Decimal(result['gross_selection_difference']), Decimal('.05'))
        self.assertEqual(Decimal(result['same_mean_exposure_gross_return']), 0)
        self.assertEqual(result['signal_switches'], 1)
        self.assertEqual(result['decision'], 'positive_descriptive_only_requires_account_review')
        self.assertFalse(result['net_account_result'])
        self.assertFalse(result['qualifies_for_promotion'])
        self.assertFalse(result['formal_positive_ev_verified'])

    def test_negative_selection_is_rejected(self):
        result = monthly_selection_diagnostic([date(2020, 1, 2), date(2020, 2, 3), date(2020, 3, 2)], [0, 1], ['100', '110', '99'])
        self.assertEqual(result['decision'], 'reject_fixed_diagnostic')

    def test_constant_signal_and_zero_difference_are_rejected(self):
        anchors = [date(2020, 1, 2), date(2020, 2, 3), date(2020, 3, 2)]
        for signal in ([0, 0], [1, 1], [0, 1]):
            with self.subTest(signal=signal):
                result = monthly_selection_diagnostic(anchors, signal, ['100', '100', '100'])
                self.assertEqual(result['decision'], 'reject_fixed_diagnostic')

    def test_terminal_anchor_cannot_have_an_extra_signal(self):
        with self.assertRaisesRegex(ValueError, 'one fewer'):
            monthly_selection_diagnostic([date(2020, 1, 2), date(2020, 2, 3)], [1, 0], [100, 110])

    def test_missing_month_and_invalid_labels_or_signals_fail(self):
        anchors = [date(2020, 1, 2), date(2020, 2, 3)]
        for levels in ([100, 0], [100, 'NaN'], [100, True], [100]):
            with self.subTest(levels=levels):
                with self.assertRaises(ValueError): monthly_selection_diagnostic(anchors, [1], levels)
        with self.assertRaises(ValueError): monthly_selection_diagnostic(anchors, [True], [100, 110])
        with self.assertRaises(ValueError): monthly_selection_diagnostic([anchors[0], date(2020, 3, 2)], [1], [100, 110])

    def test_year_contributions_sum_to_primary_without_subgroup_selection(self):
        result = monthly_selection_diagnostic([date(2020, 12, 1), date(2021, 1, 4), date(2021, 2, 1)], [1, 0], ['100', '110', '99'])
        self.assertEqual(set(result['year_contributions']), {'2020', '2021'})
        self.assertEqual(sum(map(Decimal, result['year_contributions'].values())), Decimal(result['gross_selection_difference']))

    def test_ex_dividend_drop_does_not_invent_monthly_selection_advantage(self):
        sessions = [date(2024, 1, 2), date(2024, 1, 31), date(2024, 2, 1), date(2024, 3, 1)]
        bars = fixture_bars([10, 10, 9, 9]); bars['date'] = sessions
        event = explicit_dividend(announced_date='2024-01-02', record_date='2024-01-31',
            ex_date='2024-02-01', pay_date='2024-03-01')
        with tempfile.TemporaryDirectory() as tmp:
            actions = write_actions(tmp, [event], version=3, coverage_end='2024-03-01')
            prices = build_cash_action_research_prices(bars, actions, sessions=sessions)
        anchors = [sessions[index] for index in (0, 2, 3)]
        levels = prices.bars['adj_close'].iloc[[0, 2, 3]].tolist()
        result = monthly_selection_diagnostic(anchors, [0, 1], levels)
        self.assertEqual(Decimal(result['gross_selection_difference']), 0)
        self.assertEqual(result['decision'], 'reject_fixed_diagnostic')


if __name__ == '__main__': unittest.main()
