import copy
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research.household_diagnostic_registration import (
    DIRECTORY, HYPOTHESIS, expected_input_paths, build_registration,
    validate_registration, verified_input_bytes, check_scheduler_admission,
    claim_attempt, finish_attempt,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256


def registration_fixture(root):
    inputs = {}
    for role, path in expected_input_paths().items():
        target = root / path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'fixture bytes')
        inputs[role] = {'path': path, 'sha256': sha256(target.read_bytes())}
    code = root / 'household_fixture.py'; code.write_bytes(b'# synthetic\n')
    return build_registration(inputs=inputs, code_files={code.name: sha256(code.read_bytes())},
        environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')


def scheduler_fixture(packet):
    return {'household_diagnostic_decision': {
        'status': 'authorized_once', 'registration_id': packet['registration_id'],
        'registration_sha256': sha256(canonical(packet)),
        'registration_path': DIRECTORY + '/registration.json',
        'execution_count': 0, 'max_executions': 1, 'allowed_stage': packet['stage'],
        'ledger_path': packet['ledger_path'], 'source_origin': packet['source_origin'],
        'conditional_gross_diagnostic_only': True,
        **{field: False for field in ('general_factor_batch_allowed', 'promotion_allowed',
            'holdout_allowed', 'paper_account_allowed', 'broker_connection_allowed',
            'account_read_allowed', 'order_placement_allowed')}}}


class HouseholdRegistrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name); self.packet = registration_fixture(self.root)

    def authorize_check(self, scheduler, packet=None):
        return check_scheduler_admission(scheduler, packet or self.packet,
            registration_path=DIRECTORY + '/registration.json',
            registration_sha256=sha256(canonical(packet or self.packet)))

    def test_sixty_one_inputs_and_seventeen_intervals_have_new_identity(self):
        self.assertEqual(len(self.packet['inputs']), 61)
        self.assertEqual(self.packet['window']['intervals'], 17)
        self.assertEqual(self.packet['economic_hypothesis_id'], HYPOTHESIS)
        self.assertNotIn('policy_uncertainty', self.packet['ledger_path'])
        self.assertEqual(validate_registration(self.packet), self.packet)

    def test_scope_identity_and_permission_changes_are_rejected(self):
        for key, value in [('economic_hypothesis_id', 'policy_uncertainty_monthly_median_v1'),
                ('output_directory', 'data/another_attempt'), ('holdout_allowed', True),
                ('window', {'intervals': 53}), ('max_executions', 2)]:
            with self.subTest(key=key):
                altered = copy.deepcopy(self.packet); altered[key] = value
                with self.assertRaises(ValueError): validate_registration(altered)

    def test_wrong_year_extra_role_and_unregistered_source_path_fail(self):
        for kind in ('year', 'extra', 'path'):
            inputs = copy.deepcopy(self.packet['inputs'])
            if kind == 'year': inputs['bars_2024']['path'] = inputs['bars_2024']['path'].replace('year=2024', 'year=2026')
            if kind == 'extra': inputs['bars_2026'] = inputs['bars_2024']
            if kind == 'path': inputs['survey_pdf_2024Q1']['path'] = 'data/alternate.pdf'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                build_registration(inputs=inputs, code_files=self.packet['code_files'],
                    environment=self.packet['environment'], source_origin='synthetic_fixture', branch=self.packet['branch'])

    def test_real_input_cannot_omit_implementation_binding(self):
        with self.assertRaises(ValueError):
            build_registration(inputs=self.packet['inputs'], code_files=self.packet['code_files'],
                environment=self.packet['environment'], source_origin='retained_research_sources', branch=self.packet['branch'])

    def test_changed_source_code_or_environment_fails_without_claim(self):
        with self.assertRaises(ValueError): verified_input_bytes(self.root, self.packet, environment={'python': 'changed'})
        source = self.root / self.packet['inputs']['survey_pdf_2024Q1']['path']
        source.write_bytes(b'changed')
        with self.assertRaises(ValueError): verified_input_bytes(self.root, self.packet, environment=self.packet['environment'])
        source.write_bytes(b'fixture bytes'); (self.root / 'household_fixture.py').write_bytes(b'changed code')
        with self.assertRaises(ValueError): verified_input_bytes(self.root, self.packet, environment=self.packet['environment'])
        self.assertFalse((self.root / self.packet['ledger_path']).exists())

    def test_snapshot_remains_the_verified_bytes_after_later_file_change(self):
        snapshots = verified_input_bytes(self.root, self.packet, environment=self.packet['environment'])
        (self.root / self.packet['inputs']['actions']['path']).write_bytes(b'later content')
        self.assertEqual(snapshots['actions'], b'fixture bytes')

    def test_previous_study_scheduler_key_confers_no_new_authority(self):
        valid = scheduler_fixture(self.packet)
        self.authorize_check(valid)
        with self.assertRaises(ValueError): self.authorize_check({})
        with self.assertRaises(ValueError): self.authorize_check({'monthly_diagnostic_decision': valid['household_diagnostic_decision']})

    def test_consumed_or_broadened_scheduler_decisions_fail(self):
        for key, value in [('execution_count', 1), ('max_executions', 2), ('status', 'completed'),
                ('registration_sha256', '0'*64), ('general_factor_batch_allowed', True),
                ('promotion_allowed', True), ('order_placement_allowed', True)]:
            with self.subTest(key=key):
                scheduler = scheduler_fixture(self.packet); scheduler['household_diagnostic_decision'][key] = value
                with self.assertRaises(ValueError): self.authorize_check(scheduler)

    def test_failed_attempt_and_changed_registration_cannot_restore_budget(self):
        receipt = claim_attempt(self.root, self.packet)
        finish_attempt(self.root, self.packet, receipt, status='failed', failure_kind='ValueError')
        changed = build_registration(inputs=self.packet['inputs'], code_files=self.packet['code_files'],
            environment={'python': 'changed'}, source_origin='synthetic_fixture', branch=self.packet['branch'])
        with self.assertRaisesRegex(ValueError, 'already claimed'): claim_attempt(self.root, changed)

    def test_partial_claim_is_used_and_never_overwritten(self):
        claim = self.root / self.packet['ledger_path']; claim.parent.mkdir(parents=True)
        claim.write_bytes(b'{')
        with self.assertRaisesRegex(ValueError, 'already claimed'): claim_attempt(self.root, self.packet)
        self.assertEqual(claim.read_bytes(), b'{')

    def test_completion_requires_matching_result_and_terminal_is_immutable(self):
        receipt = claim_attempt(self.root, self.packet)
        with self.assertRaises(ValueError): finish_attempt(self.root, self.packet, receipt, status='completed', result_sha256='0'*64)
        result = self.root / DIRECTORY / 'result.json'; result.write_bytes(b'{"result":1}')
        finish_attempt(self.root, self.packet, receipt, status='completed', result_sha256=sha256(result.read_bytes()))
        terminal = self.root / DIRECTORY / 'outcome.json'; before = terminal.read_bytes()
        with self.assertRaises(FileExistsError): finish_attempt(self.root, self.packet, receipt, status='failed')
        self.assertEqual(terminal.read_bytes(), before)

    def test_claim_for_closed_previous_study_does_not_consume_new_hypothesis(self):
        from tests.unit.test_monthly_diagnostic_registration import registration_fixture as old_fixture
        from quant_robot.research.monthly_diagnostic_registration import claim_attempt as old_claim
        prior = old_fixture(self.root); old_claim(self.root, prior)
        new = claim_attempt(self.root, self.packet)
        self.assertEqual(new['economic_hypothesis_id'], HYPOTHESIS)
        self.assertTrue((self.root / prior['ledger_path']).exists())


if __name__ == '__main__': unittest.main()
