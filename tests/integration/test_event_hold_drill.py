import copy
import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_etf_event_hold_drill import run_drill
from quant_robot.research.fiscal_execution_decision import compare_fiscal_accounts


class EventHoldDrillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name) / 'run'
        cls.result = run_drill(cls.directory)

    def test_exact_twenty_transition_round_trips_pay_both_sides(self):
        account = self.result['scenarios']['5']['selected']
        self.assertEqual(account['metrics']['completed_round_trips'], 2)
        self.assertEqual(account['metrics']['pnl_cny'], -20)
        self.assertEqual(account['fills'][1]['execution_date'], '2022-06-22')
        self.assertEqual(account['fills'][0]['execution_date'], '2022-06-02')
        self.assertEqual(account['positions'], [])
        self.assertFalse(self.result['real_prices_read'])

    def test_positive_relative_comparison_does_not_pass_a_losing_account(self):
        decision = self.result['scenarios']['5']['comparison']
        self.assertEqual(decision['selected_minus_unconditional_pnl_cny'], 10)
        self.assertEqual(decision['selected_pnl_cny'], -20)
        self.assertEqual(decision['decision'], 'fixed_contract_not_passed')
        self.assertIn('selected_absolute_pnl_not_positive', decision['reasons'])
        self.assertFalse(decision['net_positive_ev_verified'])
        self.assertAlmostEqual(self.result['scenarios']['0']['selected']['metrics']['pnl_cny'], -1.6)

    def test_different_fee_contracts_and_result_overwrite_refused(self):
        accounts = self.result['scenarios']['5']
        changed = copy.deepcopy(accounts['unconditional'])
        changed['request']['minimum_commission'] = 0
        with self.assertRaisesRegex(ValueError, 'identical account'):
            compare_fiscal_accounts(accounts['selected'], changed)
        with self.assertRaises(FileExistsError):
            run_drill(self.directory)


if __name__ == '__main__':
    unittest.main()
