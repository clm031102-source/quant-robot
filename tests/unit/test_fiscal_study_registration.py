import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research.fiscal_study_registration import (
    DIRECTORY, REVIEW_PATH, build_registration, validate_registration,
    verified_input_bytes, check_scheduler_admission, claim_attempt, finish_attempt,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, write_exclusive_json


def fixture(root):
    code = 'src/fixture.py'
    (root/code).parent.mkdir(parents=True)
    (root/code).write_bytes(b'# fixture implementation')
    source_path = 'data/reports/fixture_source.json'
    (root/source_path).parent.mkdir(parents=True)
    (root/source_path).write_bytes(b'{"synthetic":true}')
    review = {'status': 'conditional_source_use_reviewed_not_admitted',
        'economic_hypothesis_id': 'general_public_budget_execution_pace_v1',
        'source_fingerprints': {source_path: sha256((root/source_path).read_bytes())},
        'source_audit_verified': False, 'historical_availability_verified': False,
        'research_admission_granted': False, 'local_ETF_price_columns_decoded': False,
        'real_fiscal_ratios_computed': False, 'net_account_cash_verified': False}
    write_exclusive_json(root/REVIEW_PATH, review)
    inputs = {**review['source_fingerprints'], REVIEW_PATH: sha256((root/REVIEW_PATH).read_bytes())}
    packet = build_registration(inputs=inputs, code_files={code: sha256((root/code).read_bytes())},
        environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')
    write_exclusive_json(root/DIRECTORY/'registration.json', packet)
    return packet


class FiscalRegistrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.packet = fixture(self.root)

    def test_changed_scope_and_paths_cannot_validate_under_same_identity(self):
        for field, value in [('max_executions', 2), ('stage', 'other'), ('holdout_allowed', True)]:
            changed = copy.deepcopy(self.packet); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): validate_registration(changed)
        args = {key: self.packet[key] for key in ('inputs','code_files','environment','source_origin','branch')}
        with self.assertRaises(ValueError): build_registration(**{**args, 'inputs': {'../outside': '0'*64}})

    def test_snapshot_rejects_changed_source_implementation_or_environment(self):
        for path in ('data/reports/fixture_source.json', 'src/fixture.py'):
            original=(self.root/path).read_bytes(); (self.root/path).write_bytes(b'changed')
            with self.subTest(path=path), self.assertRaises(ValueError):
                verified_input_bytes(self.root,self.packet,environment={'python':'fixture'})
            (self.root/path).write_bytes(original)
        with self.assertRaises(ValueError): verified_input_bytes(self.root,self.packet,environment={'python':'different'})

    def test_claim_is_exclusive_and_failure_is_not_an_unused_attempt(self):
        receipt=claim_attempt(self.root,self.packet)
        finish_attempt(self.root,self.packet,receipt,status='failed',failure_kind='ValueError')
        with self.assertRaises(ValueError): claim_attempt(self.root,self.packet)
        outcome=json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['status'],'failed')

    def test_other_study_or_missing_admission_is_not_permission(self):
        for scheduler in ({}, {'month_start_diagnostic_decision': {'status':'authorized_once'}}):
            with self.assertRaises(ValueError): check_scheduler_admission(scheduler,self.packet,
                registration_path=DIRECTORY+'/registration.json',registration_sha256=sha256(canonical(self.packet)))

    def test_fixture_inputs_cannot_be_declared_real_sources(self):
        args={key:self.packet[key] for key in ('inputs','code_files','environment','source_origin','branch')}
        with self.assertRaises(ValueError): build_registration(**{**args,'source_origin':'retained_research_sources'})


if __name__ == '__main__': unittest.main()
