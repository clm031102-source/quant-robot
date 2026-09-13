import copy
import json
import ntpath
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.monthly_diagnostic_registration import (
    build_registration, validate_registration, check_scheduler_admission,
    claim_attempt, finish_attempt, verified_input_bytes, sha256,
    resolve_path,
)


def registration_fixture(root):
    inputs = {}
    for role in ['proposal', 'source_review', 'source_join', 'policy_audit', 'policy_scope',
            'calendar', 'actions', 'policy_1', 'policy_2', *['bars_' + str(year) for year in range(2020, 2025)]]:
        path = 'data/' + role + '.json'
        (root / path).parent.mkdir(exist_ok=True)
        (root / path).write_text('{}', encoding='utf-8')
        inputs[role] = {'path': path, 'sha256': sha256(b'{}')}
    code = root / 'implementation.py'; code.write_text('# fixture\n', encoding='utf-8')
    return build_registration(inputs=inputs, code_files={'implementation.py': sha256(code.read_bytes())},
        environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')


def scheduler_fixture(registration):
    return {'monthly_diagnostic_decision': {
        'status': 'authorized_once', 'registration_id': registration['registration_id'],
        'registration_sha256': sha256(json.dumps(registration, sort_keys=True).encode()),
        'registration_path': 'registration.json', 'execution_count': 0,
        'max_executions': 1, 'allowed_stage': registration['stage'],
        'general_factor_batch_allowed': False, 'promotion_allowed': False,
        'holdout_allowed': False, 'paper_account_allowed': False,
        'broker_connection_allowed': False, 'account_read_allowed': False,
        'order_placement_allowed': False, 'conditional_gross_diagnostic_only': True,
        'ledger_path': registration['ledger_path'], 'source_origin': registration['source_origin']}}


class MonthlyRegistrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.registration = registration_fixture(self.root)

    def test_identity_binds_inputs_code_scope_and_branch(self):
        original = self.registration
        for key in ('inputs', 'code_files', 'branch', 'source_origin'):
            modified = copy.deepcopy(original)
            modified[key] = {} if isinstance(original[key], dict) else 'changed'
            with self.subTest(key=key), self.assertRaises(ValueError): validate_registration(modified)

    def test_checked_bytes_are_retained_even_if_source_changes_later(self):
        snapshot = verified_input_bytes(self.root, self.registration, environment={'python': 'fixture'})
        (self.root / self.registration['inputs']['actions']['path']).write_text('changed')
        self.assertEqual(snapshot['actions'], b'{}')
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            verified_input_bytes(self.root, self.registration, environment={'python': 'fixture'})

    def test_outside_root_and_extra_input_roles_are_rejected(self):
        for path in ('../outside', '/outside', 'C:/outside'):
            values = copy.deepcopy(self.registration['inputs']); values['actions']['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_registration(inputs=values, code_files=self.registration['code_files'],
                    environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')
        values = copy.deepcopy(self.registration['inputs']); values['bars_2026'] = values['bars_2024']
        with self.assertRaises(ValueError):
            build_registration(inputs=values, code_files=self.registration['code_files'],
                environment={'python': 'fixture'}, source_origin='synthetic_fixture', branch='codex/factor-review-fixture')

    def test_environment_and_code_fingerprint_changes_fail_before_claim(self):
        with self.assertRaises(ValueError): verified_input_bytes(self.root, self.registration, environment={'python': 'other'})
        (self.root / 'implementation.py').write_text('changed')
        with self.assertRaises(ValueError): verified_input_bytes(self.root, self.registration, environment={'python': 'fixture'})
        self.assertFalse((self.root / self.registration['ledger_path']).exists())

    def test_no_scheduler_or_expanded_boundary_cannot_authorize(self):
        scheduler = scheduler_fixture(self.registration)
        check_scheduler_admission(scheduler, self.registration, registration_path='registration.json',
            registration_sha256=scheduler['monthly_diagnostic_decision']['registration_sha256'])
        for field in ('promotion_allowed', 'holdout_allowed', 'order_placement_allowed', 'general_factor_batch_allowed'):
            altered = copy.deepcopy(scheduler); altered['monthly_diagnostic_decision'][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_scheduler_admission(altered, self.registration, registration_path='registration.json',
                    registration_sha256=scheduler['monthly_diagnostic_decision']['registration_sha256'])
        with self.assertRaises(ValueError):
            check_scheduler_admission({}, self.registration, registration_path='registration.json', registration_sha256='0'*64)

    def test_claim_is_exclusive_and_persists_after_failure(self):
        receipt = claim_attempt(self.root, self.registration)
        finish_attempt(self.root, self.registration, receipt, status='failed', failure_kind='ValueError')
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            claim_attempt(self.root, self.registration)
        saved = json.loads((self.root / self.registration['ledger_path']).read_text())
        self.assertEqual(saved['registration_id'], self.registration['registration_id'])

    def test_changed_registration_cannot_reset_same_study_budget(self):
        claim_attempt(self.root, self.registration)
        changed = build_registration(inputs=self.registration['inputs'], code_files=self.registration['code_files'],
            environment={'python': 'changed'}, source_origin='synthetic_fixture', branch=self.registration['branch'])
        self.assertNotEqual(changed['registration_id'], self.registration['registration_id'])
        with self.assertRaisesRegex(ValueError, 'already claimed'): claim_attempt(self.root, changed)

    def test_partial_claim_from_abrupt_exit_is_not_treated_as_unused(self):
        path = self.root / self.registration['ledger_path']; path.parent.mkdir(parents=True)
        path.write_bytes(b'{')
        with self.assertRaisesRegex(ValueError, 'already claimed'): claim_attempt(self.root, self.registration)

    @unittest.skipUnless(os.name == 'nt', 'Windows final-path namespace race')
    def test_parent_created_during_resolution_keeps_in_workspace_path_valid(self):
        original = ntpath._getfinalpathname
        calls = 0
        def changing_error(path):
            nonlocal calls
            if str(path).endswith('race\\parent\\leaf.json'):
                calls += 1
                error = FileNotFoundError('simulated parent creation race')
                error.winerror = 3 if calls <= 2 else 2
                raise error
            return original(path)
        with patch.object(ntpath, '_getfinalpathname', side_effect=changing_error):
            result = resolve_path(self.root, 'race/parent/leaf.json')
        self.assertTrue(str(result).endswith('race\\parent\\leaf.json'))
        self.assertGreaterEqual(calls, 3)

    def test_symlink_resolving_outside_still_fails(self):
        outside = tempfile.TemporaryDirectory(); self.addCleanup(outside.cleanup)
        link = self.root/'outside-link'
        try:
            link.symlink_to(outside.name, target_is_directory=True)
        except OSError as exc:
            self.skipTest('symlink creation unavailable: '+str(exc))
        with self.assertRaisesRegex(ValueError,'leaves the workspace'):
            resolve_path(self.root,'outside-link/leaf.json')

    @unittest.skipUnless(os.name == 'nt', 'Windows final-path namespace')
    def test_extended_prefix_cannot_turn_an_outside_target_into_an_inside_path(self):
        root=self.root.resolve()
        outside=Path('\\\\?\\'+str(root.parent/'outside'))
        with patch.object(Path,'resolve',side_effect=[root,outside]):
            with self.assertRaisesRegex(ValueError,'leaves the workspace'):
                resolve_path(root,'data/leaf.json')


if __name__ == '__main__': unittest.main()
