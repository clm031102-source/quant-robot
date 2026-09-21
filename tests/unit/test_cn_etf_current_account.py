import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.ops.cn_etf_small_capital_inputs import SmallCapitalInputs
from scripts.run_cn_etf_execution_interface_contract_readiness import (
    run_cn_etf_execution_interface_contract_readiness_cli,
)
from scripts.run_paper_simulation import run_simulation


class CurrentResearchAccountTests(unittest.TestCase):
    def test_current_account_supports_confirmed_capital_and_fee_stress(self):
        payload = json.loads(Path('configs/cn_etf_research_account.json').read_text())
        account = SmallCapitalInputs.from_mapping(payload)
        self.assertEqual((account.minimum_capital_cny, account.maximum_capital_cny), (10000, 10000))
        self.assertEqual(account.max_single_position_cny, 1000)
        self.assertEqual([account.round_trip_cost_bps(1000, minimum_fee_cny=f)
                          for f in (0, 5, 10)], [30, 120, 220])
        self.assertFalse(payload['fee_evidence']['broker_confirmed'])

    def test_current_contract_refuses_stale_capital_and_nonfinite_economics(self):
        original = json.loads(Path('configs/cn_etf_research_account.json').read_text())
        for field, value in [('commission_bps_per_side', float('nan')),
                             ('slippage_bps_per_side', float('inf')),
                             ('minimum_commission_cny_stress', float('-inf')),
                             ('max_single_position_cny', float('nan'))]:
            with self.subTest(field=field):
                payload = copy.deepcopy(original)
                payload[field] = value
                with self.assertRaises(ValueError):
                    SmallCapitalInputs.from_mapping(payload)
        payload = copy.deepcopy(original)
        payload['capital_cny'] = {'minimum': 1000, 'maximum': 3000}
        with self.assertRaisesRegex(ValueError, 'capital'):
            SmallCapitalInputs.from_mapping(payload)

    def test_current_contract_cannot_enable_external_execution(self):
        original = json.loads(Path('configs/cn_etf_research_account.json').read_text())
        for key in original['boundaries']:
            with self.subTest(key=key):
                payload = copy.deepcopy(original)
                payload['boundaries'][key] = True
                with self.assertRaisesRegex(ValueError, key):
                    SmallCapitalInputs.from_mapping(payload)

    def test_default_offline_readiness_uses_current_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cn_etf_execution_interface_contract_readiness_cli(output_dir=tmp)
        self.assertEqual(result['status'], 'schema_ready_execution_disabled')
        self.assertEqual(result['risk_contract']['capital_cny'], {'minimum': 10000, 'maximum': 10000})
        self.assertFalse(result['live_boundary_allowed'])
        self.assertFalse(result['fee_evidence']['broker_confirmed'])

    def test_current_risk_contract_matches_the_single_account_source(self):
        account = json.loads(Path('configs/cn_etf_research_account.json').read_text())
        contract = json.loads(Path('configs/cn_etf_execution_interface_contract_current.json').read_text())
        self.assertEqual(contract['risk_contract'], {key: account[key] for key in contract['risk_contract']})
        self.assertEqual(contract['fee_evidence'], account['fee_evidence'])

    def test_default_simulation_starts_with_ten_thousand_and_keeps_explicit_replays(self):
        for explicit, expected in [(None, 10000), (3000, 3000)]:
            with self.subTest(explicit=explicit), tempfile.TemporaryDirectory() as tmp:
                kwargs = {} if explicit is None else {'initial_cash': explicit}
                result = run_simulation(source='fixture', market='CN', factor_name='momentum_2',
                    factor_windows=(2,), top_n=1, rebalance_interval=2,
                    start_date='2024-01-04', end_date='2024-01-10', output_dir=tmp, **kwargs)
                self.assertEqual(result['request']['initial_cash'], expected)
                self.assertEqual(result['request']['execution_economics']['initial_cash'], expected)
                self.assertEqual(result['metrics']['starting_cash'], expected)


if __name__ == '__main__':
    unittest.main()
