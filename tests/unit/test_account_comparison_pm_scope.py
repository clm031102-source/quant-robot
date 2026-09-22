"""Current PM protocol refuses account permission without frozen controls."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.paper.comparative_allocation import policy_template
from quant_robot.research.account_comparison_scope import REQUIRED_CODE
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO=Path(__file__).resolve().parents[2]


class AccountComparisonPmScopeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.config=json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.family=json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.workstations=json.loads((REPO/'configs/workstations.json').read_bytes())
        self.assertEqual(self.config['account_comparison_protocol'],dict(version=1,holding_and_cash_required=True))
        for item in self.config['required_reading']:
            path=self.root/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
        self.days=[str(date(2014,1,1)+timedelta(days=i)) for i in range(35)]
        self.policy=policy_template(study_id='prospective_fixture',first_session=self.days[20],
            terminal_session=self.days[-1],later_start=self.days[27])
        self.inputs={}
        self.inputs['sessions']=self.put('data/sessions.json',canonical(self.days))
        self.inputs['strategy_cycles']=self.put('data/cycles.json',canonical([]))
        self.policy['strategy_cycles']=self.inputs['strategy_cycles']
        self.code={p:self.put(p,b'# synthetic comparison implementation') for p in REQUIRED_CODE}
        # Intentionally absent market outcomes: PM review must not open them.
        self.inputs['bars']=dict(path='data/absent_market_outcomes.json',sha256='0'*64)
        self.register()

    def put(self,path,raw):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        return dict(path=path,sha256=sha256(raw))

    def register(self,include_policy=True):
        if include_policy:self.inputs['comparison_policy']=self.put('configs/comparison.json',canonical(self.policy))
        else:self.inputs.pop('comparison_policy',None)
        packet=dict(study_id='prospective_fixture',inputs=self.inputs.copy(),code_files=self.code)
        packet['registration_id']=sha256(canonical(packet))
        pin=self.put('data/registration.json',canonical(packet))
        self.scope=dict(registration_id=packet['registration_id'],registration_path=pin['path'],
            registration_sha256=pin['sha256'],net_account_allowed=True)

    def gate(self,mode='single_currency_gold_account_only'):
        with patch('quant_robot.research.pm_startup_gate.currency_gold_account_scope',return_value=dict(mode=mode,scope=self.scope)):
            return build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
                repo_root=self.root,machine='office_desktop',task='factor_batch',
                branch='codex/factor-review-synthetic',current_branch='codex/factor-review-synthetic',family_config=self.family)

    def test_complete_controls_pass_specification_without_reading_outcomes(self):
        gate=self.gate()
        self.assertEqual(gate['status'],'ready',gate['blockers'])
        self.assertEqual(gate['account_comparison']['status'],'passed_specification_only')
        self.assertTrue(gate['safety']['currency_gold_account_allowed'])
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertFalse(gate['safety']['live_boundary_allowed'])

    def test_missing_registration_policy_blocks_account(self):
        self.register(include_policy=False);gate=self.gate()
        self.assertEqual(gate['status'],'blocked')
        self.assertFalse(gate['safety']['currency_gold_account_allowed'])

    def test_missing_holding_or_cash_or_renewal_blocks_account(self):
        original=deepcopy(self.policy)
        for missing in ('holding','cash','renewal'):
            self.policy=deepcopy(original)
            if missing=='renewal':del self.policy['controls']['holding']['renewal']
            else:del self.policy['controls'][missing]
            self.register()
            with self.subTest(missing=missing):self.assertEqual(self.gate()['status'],'blocked')

    def test_changed_calendar_or_implementation_rejected(self):
        for role in ('sessions','implementation'):
            pin=self.inputs['sessions'] if role=='sessions' else self.code[REQUIRED_CODE[0]]
            old=(self.root/pin['path']).read_bytes();(self.root/pin['path']).write_bytes(b'changed')
            with self.subTest(role=role):self.assertEqual(self.gate()['status'],'blocked')
            (self.root/pin['path']).write_bytes(old)

    def test_different_strategy_schedule_or_study_identity_rejected(self):
        original=deepcopy(self.policy)
        for field,value in [('study_id','another_candidate'),('strategy_cycles',dict(path='data/another.json',sha256='1'*64))]:
            self.policy=deepcopy(original);self.policy[field]=value;self.register()
            with self.subTest(field=field):self.assertEqual(self.gate()['status'],'blocked')

    def test_lower_cost_or_higher_position_cap_is_not_a_valid_control(self):
        self.policy['common']['marked_position_limit_CNY']=2000;self.register()
        self.assertEqual(self.gate()['status'],'blocked')

    def test_outside_workspace_pin_fails_closed(self):
        self.inputs['sessions']=dict(path='../outside.json',sha256='0'*64);self.register()
        self.assertEqual(self.gate()['status'],'blocked')

    def test_account_scope_is_checked_even_if_mode_omits_account_word(self):
        self.register(include_policy=False)
        self.assertEqual(self.gate(mode='single_term_structure_diagnostic_only')['status'],'blocked')
