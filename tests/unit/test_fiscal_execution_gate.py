import unittest

from quant_robot.research.fiscal_execution_gate import evaluate_fiscal_gate


class FiscalExecutionGateTests(unittest.TestCase):
    def monthly(self, year, amount, published=None):
        return {'period_start': f'{year}-01-01', 'period_end': f'{year}-05-31',
            'scope': 'national_general_public_budget', 'source_value_semantics': 'cumulative_from_january',
            'amount_cny_100m': str(amount), 'published_date_label': published or f'{year}-06-15'}

    def annual(self, year, amount, published=None):
        return {'year': year, 'amount_cny_100m': str(amount),
            'published_date_label': published or f'{year}-03-15',
            'reference_semantics': 'initial_annual_report_plan'}

    def evaluate(self, **changes):
        inputs = {'current': self.monthly(2022, 50), 'prior': self.monthly(2021, 40),
            'current_plan': self.annual(2022, 100), 'prior_plan': self.annual(2021, 100),
            'decision_day': '2022-06-16'}
        return evaluate_fiscal_gate(**{**inputs, **changes})

    def test_ratio_change_is_positive_and_ties_are_not_selected(self):
        result = self.evaluate()
        self.assertTrue(result['selected'])
        self.assertEqual(result['execution_ratio_change'], '0.1')
        self.assertFalse(self.evaluate(current=self.monthly(2022, 40))['selected'])
        self.assertFalse(self.evaluate(current_plan=self.annual(2022, 200))['selected'])

    def test_annual_reference_known_at_current_decision_not_prior_release(self):
        result = self.evaluate(prior_plan=self.annual(2021, 100, '2021-07-01'))
        self.assertTrue(result['selected'])
        self.assertFalse(result['historical_availability_verified'])
        with self.assertRaisesRegex(ValueError, 'known'):
            self.evaluate(current_plan=self.annual(2022, 100, '2022-06-16'))

    def test_mismatched_periods_years_and_noninitial_denominators_rejected(self):
        for changes in [
                {'prior': self.monthly(2020, 40)},
                {'prior': {**self.monthly(2021, 40), 'period_end': '2021-04-30'}},
                {'current_plan': {**self.annual(2022, 100), 'reference_semantics': 'revised_budget'}},
                {'current': {**self.monthly(2022, 50), 'scope': 'central_budget'}}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(**changes)

    def test_all_inputs_must_precede_decision_day_and_monthly_period_must_end(self):
        for changes in [{'decision_day': '2022-06-15'},
                {'current': self.monthly(2022, 50, '2022-05-30')},
                {'prior': self.monthly(2021, 40, '2022-06-16')}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(**changes)

    def test_invalid_amounts_rejected_without_float_coercion(self):
        for value in [True, 'NaN', 'Infinity', '0', '-1', '1e300', '0.1234567']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate(current={**self.monthly(2022, 50), 'amount_cny_100m': value})


if __name__ == '__main__':
    unittest.main()
