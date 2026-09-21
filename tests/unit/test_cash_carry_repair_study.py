import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests.unit import test_cash_carry_study as original_fixture
from quant_robot.research import cash_carry_study as original
from quant_robot.research import cash_carry_repair_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256


class CashCarryRepairStudyTests(unittest.TestCase):
    def setUp(self):
        original_fixture.CashCarryStudyTests.setUp(self)
        self.original_packet=self.packet
        old=self.root/original.DIRECTORY
        (old/'attempt_claim.json').write_bytes(canonical({'status':'claimed_before_income_value_decode'}))
        (old/'outcome.json').write_bytes(canonical(dict(status='failed_consumed',error_type='ValueError',
            error_message='Finite decimal required',registration_id=self.original_packet['registration_id'])))
        def put(role,content,path):
            target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            self.inputs[role]=dict(path=path,sha256=sha256(content))
        for role,path in [('prior_registration',original.REGISTRATION),('prior_outcome',original.DIRECTORY+'/outcome.json')]:
            self.inputs[role]=dict(path=path,sha256=sha256((self.root/path).read_bytes()))
        put('failure_review',b'{}','data/failure_review.json')
        proposal=json.loads((original_fixture.REPO/study.PROPOSAL).read_bytes())
        for key,role in [('repair_of_registration','prior_registration'),('prior_outcome','prior_outcome'),
                         ('original_proposal','proposal'),('format_failure_review','failure_review')]:proposal[key]=self.inputs[role]
        raw=canonical(proposal)
        override=patch.object(study,'PROPOSAL_SHA256',sha256(raw));override.start();self.addCleanup(override.stop)
        put('repair_proposal',raw,study.PROPOSAL)
        code=self.original_packet['code_files'].copy()
        for name in study.IMPLEMENTATION:
            if name not in code:
                path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'# fixture')
                code[name]=dict(path=name,sha256=sha256(path.read_bytes()))
        self.packet=study.build_registration(inputs=self.inputs,code_files=code,
            branch=self.original_packet['branch'],environment=self.original_packet['environment'])
        raw=canonical(self.packet);target=self.root/study.REGISTRATION;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        self.family[original.DECISION]['status']='consumed_source_format_failure_closed'
        self.family[study.DECISION]=study.admission(self.packet,raw)

    gate=original_fixture.CashCarryStudyTests.gate

    def test_only_repair_is_open_and_preflight_never_normalizes(self):
        gate=self.gate();self.assertEqual(gate['status'],'ready',gate['blockers'])
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertEqual(gate['safety']['cash_carry_diagnostic_scope'],self.family[study.DECISION])
        with patch.object(study,'calculate',side_effect=AssertionError('early value access')):
            study.preflight(self.root,self.family,self.gate)

    def test_changed_raw_data_rejected_before_claim(self):
        (self.root/self.inputs['income_2021']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Pinned file changed'):
            study.execute(self.root,self.family,self.gate)
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_original_result_disqualifies_format_repair(self):
        (self.root/original.DIRECTORY/'result.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'Original failed format-only attempt'):
            study.preflight(self.root,self.family,self.gate)

    def test_success_preserves_original_and_cannot_repeat(self):
        old=(self.root/original.DIRECTORY/'outcome.json').read_bytes()
        def calculate(_):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            return {'synthetic':True}
        with patch.object(study,'calculate',side_effect=calculate):study.execute(self.root,self.family,self.gate)
        self.assertEqual(old,(self.root/original.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(self.gate()['status'],'blocked')
        with self.assertRaisesRegex(ValueError,'consumed'):study.execute(self.root,self.family,self.gate)

    def test_identity_failure_is_terminal(self):
        with patch.object(study,'calculate',side_effect=ValueError('income identity failed')):
            with self.assertRaisesRegex(ValueError,'income identity failed'):study.execute(self.root,self.family,self.gate)
        terminal=json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(terminal['status'],'failed_consumed')
        with self.assertRaisesRegex(ValueError,'consumed'):study.execute(self.root,self.family,self.gate)
