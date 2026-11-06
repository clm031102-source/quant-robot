"""PM routing keeps the one-month diagnostic separate from general admission."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import pm_startup_gate as pm


MODE = 'single_campaign_crypto_monthly_10_account_only'
BRANCH = 'codex/factor-review-72h-campaign-20261106'


class CryptoMonthlyPmGateTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        repo = Path(__file__).resolve().parents[2]
        self.config = json.loads((repo/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.family = json.loads((repo/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.workstations = json.loads((repo/'configs/workstations.json').read_bytes())
        for row in self.config['required_reading']:
            target = self.root/row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fabricated protocol; no market data\n', encoding='utf-8')
        self.scope = {'registration_sha256': 'a'*64, 'admission_file_sha256': 'b'*64,
                      'policy': {'qualified': False, 'real_forward': 0}}
        self.comparison = {
            'status': 'passed_specification_only', 'blockers': [],
            'comparison_purpose': 'conditional_one_month_mechanism_only',
            'strategy_accounts': 9, 'cash_controls': 1, 'primary': 'B_5',
            'holding_control_tested': False, 'alpha_or_promotion_eligible': False,
            'no_price_decoding_performed': True, 'net_positive_EV_verified': False,
            'source_quality_verified': False,
        }
        self.scope_patch = patch.object(pm, 'crypto_monthly_scope',
            return_value={'mode': MODE, 'scope': self.scope})
        self.mock_scope = self.scope_patch.start()
        self.addCleanup(self.scope_patch.stop)
        self.comparison_patch = patch(
            'quant_robot.research.crypto_monthly_admission.review_comparison',
            return_value=self.comparison)
        self.mock_comparison = self.comparison_patch.start()
        self.addCleanup(self.comparison_patch.stop)

    def build(self, **overrides):
        arguments = dict(gate_config=self.config, workstations_config=self.workstations,
            family_config=self.family, repo_root=self.root, machine='office_desktop',
            task='factor_review', branch=BRANCH, current_branch=BRANCH)
        arguments.update(overrides)
        return pm.build_quant_pm_startup_gate(**arguments)

    def assert_broad_boundaries_closed(self, result):
        safety = result['safety']
        for key in ('factor_batch_allowed', 'portfolio_grid_allowed', 'walk_forward_allowed',
                    'final_holdout_allowed', 'live_boundary_allowed',
                    'commodity_proxy_36_account_allowed', 'commodity_proxy_lifecycle_repair_allowed'):
            self.assertIs(safety[key], False, key)
        self.assertEqual(safety['factor_batch_scope'], {})

    def test_exact_diagnostic_does_not_open_general_budget_or_qualification(self):
        result = self.build()
        self.assertEqual(result['status'], 'ready', result['blockers'])
        self.assertEqual(result['mode'], MODE)
        self.assertEqual(result['primary_market'], 'CN_ETF')
        self.assertTrue(result['safety']['crypto_monthly_10_account_allowed'])
        self.assertEqual(result['safety']['crypto_monthly_10_account_scope'], self.scope)
        self.assertEqual(result['account_comparison'], self.comparison)
        self.assert_broad_boundaries_closed(result)
        self.mock_comparison.assert_called_once_with(self.root, self.scope)

    def test_missing_comparison_protocol_blocks_before_review(self):
        self.config.pop('account_comparison_protocol')
        result = self.build()
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('account_comparison_protocol_invalid', result['blockers'])
        self.assertFalse(result['safety']['crypto_monthly_10_account_allowed'])
        self.mock_comparison.assert_not_called()

    def test_comparison_failure_cannot_be_ignored(self):
        self.mock_comparison.side_effect = ValueError('frozen evidence changed')
        result = self.build()
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('account_comparison_specification_missing_or_invalid', result['blockers'])
        self.assertFalse(result['safety']['crypto_monthly_10_account_allowed'])
        self.assert_broad_boundaries_closed(result)

    def test_context_and_primary_market_checks_still_apply(self):
        for overrides in ({'machine': 'laptop'}, {'current_branch': 'main'},
                          {'gate_config': {**self.config, 'primary_market': 'CRYPTO'}}):
            with self.subTest(overrides=overrides):
                result = self.build(**overrides)
                self.assertEqual(result['status'], 'blocked')
                self.assertFalse(result['safety']['crypto_monthly_10_account_allowed'])
                self.assert_broad_boundaries_closed(result)

    def test_competing_dedicated_scope_blocks_both(self):
        other = {'mode': 'single_campaign_commodity_proxy_36_account_only',
                 'scope': copy.deepcopy(self.scope)}
        with patch.object(pm, 'commodity_proxy_scope', return_value=other):
            result = self.build()
        self.assertIn('multiple_dedicated_diagnostics_authorized', result['blockers'])
        self.assertFalse(result['safety']['crypto_monthly_10_account_allowed'])
        self.assert_broad_boundaries_closed(result)

    def test_absent_or_consumed_scope_cannot_reopen_research(self):
        self.mock_scope.return_value = None
        result = self.build()
        self.assertFalse(result['safety']['crypto_monthly_10_account_allowed'])
        self.assertEqual(result['safety']['crypto_monthly_10_account_scope'], {})
        self.assert_broad_boundaries_closed(result)
        self.mock_comparison.assert_not_called()


if __name__ == '__main__':
    unittest.main()
