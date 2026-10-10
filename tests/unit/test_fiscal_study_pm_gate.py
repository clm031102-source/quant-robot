import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.fiscal_study_registration import expected_admission, claim_attempt
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate
from tests.unit.test_fiscal_study_registration import fixture


class FiscalStudyPmGateTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.packet=fixture(self.root)
        project=Path(__file__).resolve().parents[2]
        self.workstations=json.loads((project/'configs/workstations.json').read_bytes())
        self.family=json.loads((project/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family['fiscal_event_account_decision']=expected_admission(self.packet,sha256(canonical(self.packet)))
        self.config=json.loads((project/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        for row in self.config['required_reading']:
            target=self.root/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture',encoding='utf-8')

    def gate(self, family=None, branch=None):
        # Test only the consumed protocol's lifecycle; current admission is covered
        # by test_account_comparison_pm_scope. No production legacy bypass exists.
        with patch('quant_robot.research.pm_startup_gate.review_account_comparison',
                   return_value=dict(status='mocked_consumed_protocol_fixture', blockers=[])):
            return build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
                repo_root=self.root,machine='office_desktop',task='factor_batch',branch=branch or self.packet['branch'],
                current_branch=branch or self.packet['branch'],family_config=family or self.family)

    def test_only_exact_fiscal_account_allowed_without_reopening_batch_or_holdout(self):
        result=self.gate()
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['mode'],'single_fiscal_event_account_only')
        self.assertTrue(result['safety']['fiscal_event_account_allowed'])
        for key in ('factor_batch_allowed','monthly_diagnostic_allowed','household_diagnostic_allowed',
                    'month_start_diagnostic_allowed','final_holdout_allowed','live_boundary_allowed'):
            self.assertFalse(result['safety'][key])
        self.assertEqual(result['safety']['factor_batch_scope'],{})

    def test_consumed_expanded_wrong_branch_or_wrong_identity_admission_blocked(self):
        for change in ({'execution_count':1},{'order_placement_allowed':True},{'registration_id':'0'*64}):
            family=copy.deepcopy(self.family);family['fiscal_event_account_decision'].update(change)
            with self.subTest(change=change):self.assertEqual(self.gate(family)['status'],'blocked')
        self.assertEqual(self.gate(branch='codex/factor-review-wrong')['status'],'blocked')
        claim_attempt(self.root,self.packet)
        self.assertEqual(self.gate()['status'],'blocked')


if __name__=='__main__':unittest.main()
