import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate
from quant_robot.research.monthly_diagnostic_registration import claim_attempt
from tests.unit.test_monthly_diagnostic_execution import execution_fixture, REPO


class MonthlyDiagnosticPMGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root=Path(tmp.name)
        self.packet, decision, _ = execution_fixture(self.root)
        self.family=json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_text())
        self.family['monthly_diagnostic_decision']=decision['monthly_diagnostic_decision']
        self.config=json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_text())
        self.workstations=json.loads((REPO/'configs/workstations.json').read_text())
        for row in self.config['required_reading']:
            path=self.root/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture protocol')

    def gate(self, family=None):
        return build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
            repo_root=self.root,machine='office_desktop',task='factor_batch',branch=self.packet['branch'],
            current_branch=self.packet['branch'],family_config=self.family if family is None else family)

    def test_exact_unconsumed_study_can_run_without_opening_general_batches(self):
        result=self.gate()
        self.assertEqual(result['status'],'ready',result['blockers'])
        self.assertEqual(result['mode'],'single_monthly_diagnostic_only')
        self.assertTrue(result['safety']['monthly_diagnostic_allowed'])
        self.assertFalse(result['safety']['factor_batch_allowed'])
        self.assertFalse(result['safety']['final_holdout_allowed'])
        self.assertEqual(result['research_family_schedule']['summary']['primary_budget_share'],0)

    def test_consumed_or_changed_registration_cannot_reopen_gate(self):
        claim_attempt(self.root,self.packet)
        result=self.gate();self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['safety']['monthly_diagnostic_allowed'])

    def test_expanding_flags_or_missing_registration_is_blocked(self):
        for field in ('promotion_allowed','general_factor_batch_allowed','holdout_allowed'):
            family=copy.deepcopy(self.family);family['monthly_diagnostic_decision'][field]=True
            with self.subTest(field=field):self.assertEqual(self.gate(family)['status'],'blocked')
        (self.root/'registration.json').write_text('{}')
        self.assertEqual(self.gate()['status'],'blocked')

    def test_auxiliary_moneyflow_violation_still_blocks(self):
        family=copy.deepcopy(self.family)
        for item in family['families']:
            if item['family_id']=='cn_stock_moneyflow_selection':item['status']='active';item['budget_share']=.1
        self.assertEqual(self.gate(family)['status'],'blocked')


if __name__=='__main__':unittest.main()
