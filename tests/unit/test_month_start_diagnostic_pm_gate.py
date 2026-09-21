import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research.month_start_diagnostic_registration import DIRECTORY, claim_attempt
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate
from tests.unit.month_start_diagnostic_fixtures import execution_fixture

REPO = Path(__file__).resolve().parents[2]


class MonthStartPMGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.packet, scheduler, _, _ = execution_fixture(self.root)
        self.family = json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family['month_start_diagnostic_decision'] = scheduler['month_start_diagnostic_decision']
        self.config = json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.workstations = json.loads((REPO/'configs/workstations.json').read_bytes())
        for row in self.config['required_reading']:
            path = self.root/row['path']; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture protocol', encoding='utf-8')

    def gate(self, family=None):
        return build_quant_pm_startup_gate(gate_config=self.config, workstations_config=self.workstations,
            repo_root=self.root, machine='office_desktop', task='factor_batch', branch=self.packet['branch'],
            current_branch=self.packet['branch'], family_config=self.family if family is None else family)

    def test_only_new_exact_study_is_open_with_zero_general_budget(self):
        result = self.gate()
        self.assertEqual(result['status'], 'ready', result['blockers'])
        self.assertEqual(result['mode'], 'single_month_start_diagnostic_only')
        self.assertTrue(result['safety']['month_start_diagnostic_allowed'])
        self.assertFalse(result['safety']['monthly_diagnostic_allowed'])
        self.assertFalse(result['safety']['household_diagnostic_allowed'])
        self.assertFalse(result['safety']['factor_batch_allowed'])
        self.assertEqual(result['safety']['factor_batch_scope'], {})
        self.assertEqual(result['research_family_schedule']['summary']['primary_budget_share'], 0)

    def test_claimed_or_changed_registration_is_blocked(self):
        claim_attempt(self.root, self.packet)
        self.assertEqual(self.gate()['status'], 'blocked')
        (self.root/DIRECTORY/'registration.json').write_bytes(b'{}')
        self.assertEqual(self.gate()['status'], 'blocked')

    def test_broadened_permission_and_auxiliary_stock_selection_remain_blocked(self):
        altered = copy.deepcopy(self.family); altered['month_start_diagnostic_decision']['promotion_allowed'] = True
        self.assertEqual(self.gate(altered)['status'], 'blocked')
        altered = copy.deepcopy(self.family)
        for row in altered['families']:
            if row['family_id'] == 'cn_stock_moneyflow_selection': row.update(status='active', budget_share=.1)
        self.assertEqual(self.gate(altered)['status'], 'blocked')

    def test_terminal_artifact_without_claim_does_not_restore_permission(self):
        (self.root/DIRECTORY/'outcome.json').write_bytes(b'{')
        self.assertEqual(self.gate()['status'], 'blocked')

    def test_two_simultaneous_dedicated_authorities_are_ambiguous_and_blocked(self):
        from tests.unit.test_monthly_diagnostic_execution import execution_fixture as old_fixture
        _, old_scheduler, _ = old_fixture(self.root)
        self.family['monthly_diagnostic_decision'] = old_scheduler['monthly_diagnostic_decision']
        result = self.gate()
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('multiple_dedicated_diagnostics_authorized', result['blockers'])


if __name__ == '__main__': unittest.main()
