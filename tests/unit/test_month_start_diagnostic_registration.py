import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research.month_start_diagnostic_registration import (
    DIRECTORY, LEDGER, STAGE, DENIED, build_registration, validate_registration,
    expected_input_paths, check_scheduler_admission, verified_input_bytes,
    claim_attempt, finish_attempt,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256


def packet_fixture():
    return build_registration(inputs={role: {'path': path, 'sha256': '1'*64}
        for role, path in expected_input_paths().items()}, code_files={'fixture.py': '2'*64},
        environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')


def scheduler_fixture(packet):
    return {'month_start_diagnostic_decision': {
        'status': 'authorized_once', 'registration_id': packet['registration_id'],
        'registration_sha256': sha256(canonical(packet)), 'registration_path': DIRECTORY+'/registration.json',
        'execution_count': 0, 'max_executions': 1, 'allowed_stage': STAGE, 'ledger_path': LEDGER,
        'conditional_commission_screen_only': True, 'source_origin': packet['source_origin'],
        **{field: False for field in DENIED}}}


class MonthStartRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.packet = packet_fixture()
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def check_admission(self, scheduler, packet=None):
        return check_scheduler_admission(scheduler, self.packet if packet is None else packet,
            registration_path=DIRECTORY+'/registration.json', registration_sha256=sha256(canonical(self.packet)))

    def test_registration_binds_one_commission_screen_and_separate_paths(self):
        self.assertEqual(validate_registration(self.packet), self.packet)
        self.assertEqual(len(self.packet['inputs']), 11)
        self.assertEqual(self.packet['window']['cycles'], 53)
        self.assertFalse(self.packet['net_account_result'])
        self.assertTrue(self.packet['conditional_commission_screen_only'])
        self.assertEqual(self.packet['max_executions'], 1)
        self.assertIn('month_start', self.packet['ledger_path'])

    def test_scope_and_boundary_changes_invalidate_identity(self):
        for change in ({'window': {'cycles': 54}}, {'max_executions': 2},
                       {'order_placement_allowed': True}, {'net_account_result': True},
                       {'economic_hypothesis_id': 'household_equity_preference_annual_contrast_v1'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_registration({**self.packet, **change})

    def test_input_paths_cannot_redirect_to_holdout_or_another_study(self):
        arguments = {k: self.packet[k] for k in ('inputs','code_files','environment','source_origin','branch')}
        for bad in ('../outside.json', 'data/processed/year=2026/part.parquet',
                    'data/reports/other_study/registration.json'):
            altered = copy.deepcopy(arguments); altered['inputs']['bars_2020']['path'] = bad
            with self.subTest(path=bad), self.assertRaises(ValueError): build_registration(**altered)

    def test_real_inputs_need_full_code_set_and_well_formed_hashes(self):
        arguments = {k: self.packet[k] for k in ('inputs','code_files','environment','source_origin','branch')}
        with self.assertRaises(ValueError): build_registration(**{**arguments,'source_origin':'retained_research_sources'})
        bad = copy.deepcopy(arguments); bad['inputs']['calendar']['sha256'] = 'not-a-hash'
        with self.assertRaises(ValueError): build_registration(**bad)

    def test_previous_or_consumed_admission_cannot_authorize_new_study(self):
        good = scheduler_fixture(self.packet); self.check_admission(good)
        for key in ('household_diagnostic_decision', 'monthly_diagnostic_decision'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check_admission({key: good['month_start_diagnostic_decision']})
        for change in ({'execution_count':1}, {'max_executions':2}, {'registration_sha256':'0'*64},
                       {'allowed_stage':'another'}, {'source_origin':'retained_research_sources'}):
            bad=copy.deepcopy(good);bad['month_start_diagnostic_decision'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.check_admission(bad)

    def test_attempt_is_exclusive_even_when_first_claim_is_partial(self):
        receipt=claim_attempt(self.root,self.packet)
        self.assertEqual(json.loads((self.root/LEDGER).read_bytes()),receipt)
        with self.assertRaises(ValueError): claim_attempt(self.root,self.packet)
        (self.root/LEDGER).write_bytes(b'')
        with self.assertRaises(ValueError): claim_attempt(self.root,self.packet)

    def test_completion_requires_same_attempt_and_exact_result_bytes(self):
        receipt=claim_attempt(self.root,self.packet)
        with self.assertRaises(ValueError):
            finish_attempt(self.root,self.packet,receipt,status='completed',result_sha256='0'*64)
        raw=canonical({'registration_id':self.packet['registration_id'],'synthetic':True})
        (self.root/DIRECTORY/'result.json').write_bytes(raw)
        result=finish_attempt(self.root,self.packet,receipt,status='completed',result_sha256=sha256(raw))
        self.assertEqual(result['status'],'completed')
        with self.assertRaises((ValueError,FileExistsError)):
            finish_attempt(self.root,self.packet,receipt,status='completed',result_sha256=sha256(raw))

    def test_input_or_runtime_drift_fails_before_any_claim(self):
        code=self.root/'fixture.py';code.write_bytes(b'# synthetic\n')
        inputs={}
        for role,path in expected_input_paths().items():
            file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(role.encode())
            inputs[role]={'path':path,'sha256':sha256(file.read_bytes())}
        packet=build_registration(inputs=inputs,code_files={'fixture.py':sha256(code.read_bytes())},
            environment={'python':'fixture'},source_origin='synthetic_fixture',branch='codex/factor-review-fixture')
        self.assertEqual(len(verified_input_bytes(self.root,packet,environment={'python':'fixture'})),11)
        with self.assertRaises(ValueError): verified_input_bytes(self.root,packet,environment={'python':'different'})
        (self.root/inputs['calendar']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError): verified_input_bytes(self.root,packet,environment={'python':'fixture'})
        self.assertFalse((self.root/LEDGER).exists())
