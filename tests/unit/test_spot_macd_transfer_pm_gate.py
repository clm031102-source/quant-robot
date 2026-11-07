"""Finite spot transfer admission must not open another research or forward boundary."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import pm_startup_gate as pm


MODE = 'single_campaign_spot_macd_transfer_27_account_only'
BRANCH = 'codex/factor-review-72h-campaign-20261106'


class SpotTransferPMRoutingTests(unittest.TestCase):
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
            target.write_text('artificial protocol only\n', encoding='utf-8')
        self.scope = {'registration_sha256': 'a'*64, 'admission_file_sha256': 'b'*64,
                      'policy': {'qualified': False, 'real_forward': 0}}
        self.comparison = dict(status='passed_specification_only', blockers=[],
            comparison_purpose='conditional_external_spot_transfer_only', strategy_accounts=9,
            holding_controls=9, cash_controls=9, holding_control_tested=True,
            holding_policy='fixed_252_day_single_attempt_cycles',
            uninterrupted_passive_holding_tested=False,
            alpha_or_promotion_eligible=False, no_price_decoding_performed=True,
            net_positive_EV_verified=False, source_quality_verified=False)
        scope_patch = patch.object(pm, 'spot_macd_transfer_scope',
                                  return_value={'mode': MODE, 'scope': self.scope})
        self.mock_scope = scope_patch.start()
        self.addCleanup(scope_patch.stop)
        comparison_patch = patch('quant_robot.research.spot_macd_transfer_admission.review_comparison',
                                 return_value=self.comparison)
        self.mock_comparison = comparison_patch.start()
        self.addCleanup(comparison_patch.stop)

    def build(self, **overrides):
        arguments = dict(gate_config=self.config, workstations_config=self.workstations,
            family_config=self.family, repo_root=self.root, machine='office_desktop',
            task='factor_review', branch=BRANCH, current_branch=BRANCH)
        arguments.update(overrides)
        return pm.build_quant_pm_startup_gate(**arguments)

    def assert_other_boundaries_closed(self, result):
        for name in ('factor_batch_allowed', 'portfolio_grid_allowed', 'walk_forward_allowed',
                     'final_holdout_allowed', 'live_boundary_allowed',
                     'commodity_proxy_36_account_allowed', 'commodity_proxy_lifecycle_repair_allowed',
                     'crypto_monthly_10_account_allowed', 'crypto_charge_monthly_allowed',
                     'bond_risk_compensation_allowed'):
            self.assertIs(result['safety'][name], False, name)
        self.assertEqual(result['safety']['factor_batch_scope'], {})

    def test_admitted_transfer_preserves_fixed_holding_identity_and_closed_boundaries(self):
        result = self.build()
        self.assertEqual(result['status'], 'ready', result['blockers'])
        self.assertEqual(result['primary_market'], 'CN_ETF')
        self.assertEqual(result['mode'], MODE)
        self.assertTrue(result['safety']['spot_macd_transfer_allowed'])
        self.assertEqual(result['safety']['spot_macd_transfer_scope'], self.scope)
        self.assertEqual(result['account_comparison'], self.comparison)
        self.assertTrue(result['account_comparison']['holding_control_tested'])
        self.assertFalse(result['account_comparison']['uninterrupted_passive_holding_tested'])
        self.assertFalse(result['account_comparison']['alpha_or_promotion_eligible'])
        self.assert_other_boundaries_closed(result)
        self.mock_comparison.assert_called_once_with(self.root, self.scope)

    def test_missing_comparison_policy_or_invalid_frozen_evidence_blocks(self):
        self.config.pop('account_comparison_protocol')
        result = self.build()
        self.assertIn('account_comparison_protocol_invalid', result['blockers'])
        self.assertFalse(result['safety']['spot_macd_transfer_allowed'])
        self.mock_comparison.assert_not_called()
        self.config['account_comparison_protocol'] = {'version': 1, 'holding_and_cash_required': True}
        self.mock_comparison.side_effect = ValueError('changed frozen evidence')
        result = self.build()
        self.assertIn('account_comparison_specification_missing_or_invalid', result['blockers'])
        self.assertFalse(result['safety']['spot_macd_transfer_allowed'])
        self.assert_other_boundaries_closed(result)

    def test_only_office_correct_context_and_CN_ETF_are_eligible(self):
        for overrides in ({'machine': 'laptop'}, {'machine': 'highspec_desktop'},
                          {'current_branch': 'main'},
                          {'gate_config': {**self.config, 'primary_market': 'CN'}}):
            with self.subTest(overrides=overrides):
                result = self.build(**overrides)
                self.assertEqual(result['status'], 'blocked')
                self.assertFalse(result['safety']['spot_macd_transfer_allowed'])
                self.assert_other_boundaries_closed(result)

    def test_other_finite_scope_collision_blocks_execution(self):
        other = {'mode': 'single_campaign_crypto_charge_monthly_10_account_only', 'scope': self.scope}
        with patch.object(pm, 'crypto_charge_monthly_scope', return_value=other):
            result = self.build()
        self.assertIn('multiple_dedicated_diagnostics_authorized', result['blockers'])
        self.assertFalse(result['safety']['spot_macd_transfer_allowed'])
        self.assert_other_boundaries_closed(result)

    def test_absent_or_consumed_scope_and_missing_reading_never_open_execution(self):
        self.mock_scope.return_value = None
        result = self.build()
        self.assertFalse(result['safety']['spot_macd_transfer_allowed'])
        self.assertEqual(result['safety']['spot_macd_transfer_scope'], {})
        self.mock_comparison.assert_not_called()
        self.assert_other_boundaries_closed(result)
        self.mock_scope.return_value = {'mode': MODE, 'scope': self.scope}
        missing = self.config['required_reading'][0]['path']
        (self.root/missing).unlink()
        result = self.build()
        self.assertIn('required_reading_missing:'+missing, result['blockers'])
        self.assertFalse(result['safety']['spot_macd_transfer_allowed'])


if __name__ == '__main__':
    unittest.main()
