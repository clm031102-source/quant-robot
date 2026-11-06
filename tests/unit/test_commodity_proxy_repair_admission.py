"""Repair admission tests use invented opaque sources in isolated temporary roots."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import commodity_proxy_admission as original
from quant_robot.research import commodity_proxy_repair_admission as repair


class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 6, 20, tzinfo=timezone.utc)


class CommodityRepairAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for module in (original, repair):
            clock = patch.object(module, 'datetime', FrozenClock)
            clock.start(); self.addCleanup(clock.stop)
        env = patch.object(original, 'runtime_environment', return_value={'synthetic': 'only'})
        env.start(); self.addCleanup(env.stop)
        campaign = dict(campaign_id='quant_manager_72h_20261106', status='active',
            task_branch=repair.BRANCH, started_at='2026-11-06T16:21:39Z',
            delivery_deadline='2026-11-09T16:21:39Z', finite_preregistered_studies_required=True,
            old_consumed_scopes_remain_closed=True, holdout_unsealing_authorized=False,
            live_boundary_allowed=False)
        inputs = {}
        for role in original.INPUT_ROLES:
            fixed = {'campaign': original.CAMPAIGN,
                'pm_policy': 'configs/quant_pm_startup_gate_cn_etf.json',
                'workstations': 'configs/workstations.json',
                'family_scheduler': 'configs/research_family_scheduler_cn_etf.json'}
            path = ('synthetic/year='+role[-4:]+'/bars.parquet' if role.startswith('bars_')
                else fixed.get(role, 'synthetic/'+role+'.json'))
            inputs[role] = self.save(path, campaign if role == 'campaign' else {'opaque': role})
        code = {name: self.save(name, {'synthetic_original_code': name}) for name in original.IMPLEMENTATION}
        self.old = dict(artifact_type='commodity_proxy_account_registration_v1',
            branch=repair.BRANCH, inputs=inputs, implementation=code,
            environment={'synthetic': 'only'}, policy=repair.POLICY)
        self.sign(self.old)
        constant = patch.object(repair, 'PREDECESSOR_REGISTRATION_SHA256', self.old['registration_sha256'])
        constant.start(); self.addCleanup(constant.stop)
        old_registration = self.save(original.REGISTRATION, self.old)
        old_review = self.save(original.REVIEW, dict(status='accepted_for_one_conditional_batch',
            registration_sha256=self.old['registration_sha256'], reviewer='quant_manager_72h',
            qualified=False, real_forward_days_added=0))
        old_admission = dict(artifact_type='commodity_proxy_finite_admission_v1', status='authorized_once',
            registration=old_registration, review=old_review, policy=repair.POLICY)
        predecessor = dict(registration=old_registration, independent_review=old_review,
            admission=self.save(original.ADMISSION, old_admission))
        predecessor['attempt_claim'] = self.save(repair.PREDECESSOR_PATHS['attempt_claim'], dict(
            registration_sha256=self.old['registration_sha256'], claimed_at=FrozenClock.now().isoformat(),
            status='claimed_before_financial_decode', admission_sha256=repair.digest(repair.canonical(old_admission)),
            gate=dict(mode=original.MODE, status='ready', safety=dict(commodity_proxy_36_account_scope={
                'registration_sha256': self.old['registration_sha256']})), policy=repair.POLICY))
        predecessor['outcome'] = self.save(repair.PREDECESSOR_PATHS['outcome'], dict(
            registration_sha256=self.old['registration_sha256'], finished_at=FrozenClock.now().isoformat(),
            status='failed_consumed', error_type='ValueError'))
        failure = dict(artifact_type='commodity_first_attempt_engineering_failure_review_v1',
            status='confirmed_pre_signal_interface_failure_consumed', reviewer='quant_manager_72h',
            registration_sha256=self.old['registration_sha256'], qualified=False, real_forward_days_added=0,
            execution_boundary=dict(financial_accounts_computed=0, result_files=0, signal_values_computed=0,
                real_ETF_and_settlement_fields_decoded_by_original_loader=True),
            allowed_next_proposal=dict(old_attempt_preserved=True, new_parameter_search=False,
                same_originals_method_dates_costs_risk_and_numeric_kernel=True,
                new_separate_finite_technical_registration_required=True),
            lifecycle_original=dict(**inputs['lifecycle'], outer_type='dict', records=43,
                outer_keys=['source_sha256', 'records', 'delist_date_semantics', 'historical_vintage_verified'],
                records_inventory_validation_passed=True),
            metadata_only_reproduction=dict(function='commodity_curve_proxy._inventory',
                real_financial_values_read=False, same_error='Bounded contract lifecycle inventory required'),
            files={name+'.json': predecessor[name] for name in (
                'registration', 'attempt_claim', 'outcome', 'independent_review')})
        predecessor['failure_review'] = self.save(repair.PREDECESSOR_PATHS['failure_review'], failure)
        base = deepcopy(self.old)
        for name in repair.ALLOWED_CHANGED_IMPLEMENTATION:
            base['implementation'][name] = self.save(name, {'synthetic_repaired_code': name})
        self.sign(base)
        self.packet = dict(artifact_type='commodity_proxy_lifecycle_repair_registration_v1',
            branch=repair.BRANCH, predecessor=predecessor, base_registration=base, policy=repair.POLICY,
            implementation={name: self.save(name, {'synthetic_repair_code': name}) for name in repair.IMPLEMENTATION})
        self.publish()

    def sign(self, packet):
        packet['registration_sha256'] = repair.digest(repair.canonical(
            {key: value for key, value in packet.items() if key != 'registration_sha256'}))

    def save(self, name, value):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True)
        raw = repair.canonical(value); path.write_bytes(raw)
        return dict(path=name, sha256=repair.digest(raw))

    def publish(self):
        self.sign(self.packet)
        registration = self.save(repair.REGISTRATION, self.packet)
        review = self.save(repair.REVIEW, dict(status='accepted_for_one_conditional_lifecycle_repair',
            registration_sha256=self.packet['registration_sha256'],
            predecessor_registration_sha256=self.old['registration_sha256'],
            reviewer='quant_manager_72h', qualified=False, real_forward_days_added=0))
        self.save(repair.ADMISSION, dict(artifact_type='commodity_proxy_lifecycle_repair_admission_v1',
            status='authorized_once', registration=registration, review=review, policy=repair.POLICY))

    def rebind_predecessor(self, name, mutate):
        path = self.packet['predecessor'][name]['path']
        document = json.loads((self.root/path).read_bytes()); mutate(document)
        self.packet['predecessor'][name] = self.save(path, document)
        if name in ('registration', 'attempt_claim', 'outcome', 'independent_review'):
            failure_path = self.packet['predecessor']['failure_review']['path']
            failure = json.loads((self.root/failure_path).read_bytes())
            failure['files'][name+'.json'] = self.packet['predecessor'][name]
            self.packet['predecessor']['failure_review'] = self.save(failure_path, failure)
        self.publish()

    def gate(self):
        return dict(generated_at=FrozenClock.now().isoformat(), status='ready', blockers=[],
            mode=repair.MODE, primary_market='CN_ETF', selected=dict(machine='office_desktop',
                task='factor_review', branch=repair.BRANCH, current_branch=repair.BRANCH),
            safety=dict(commodity_proxy_lifecycle_repair_allowed=True,
                commodity_proxy_lifecycle_repair_scope=repair._scope(self.packet, self.root),
                commodity_proxy_36_account_allowed=False, factor_batch_allowed=False,
                final_holdout_allowed=False, live_boundary_allowed=False))

    def execute(self, loader=None, calculator=None, gate=None):
        return repair.execute(self.root, expected_registration_sha256=self.packet['registration_sha256'],
            gate_supplier=gate or self.gate, load_inputs=loader or (lambda _: {}),
            calculate=calculator or self.calculator)

    def calculator(self, **kwargs):
        for identity in sorted(repair.ACCOUNT_IDENTITIES):
            kwargs['guard']('before', identity)
            kwargs['guard']('after', identity)
            kwargs['account_sink'](identity, {'synthetic': True})
        return dict(account_count=36, cash_benchmark_count=2, qualified=False, real_forward_days_added=0)

    def test_real_shape_preview_and_comparison_accept_only_three_code_changes(self):
        packet, _ = repair.admitted_packet(self.root)
        self.assertEqual(len(packet['base_registration']['inputs']), 63)
        self.assertEqual(len(packet['base_registration']['implementation']), 16)
        self.assertEqual(packet['base_registration']['inputs'], self.old['inputs'])
        schedule = dict(blockers=['insufficient_active_research_families'],
            summary=dict(primary_budget_share=0, active_primary_families=0))
        scope = repair.scope('factor_review', {}, schedule, root=self.root, branch=repair.BRANCH)
        self.assertEqual(scope['mode'], repair.MODE)
        result = repair.review_comparison(self.root, scope['scope'])
        self.assertTrue(result['no_price_decoding_performed'])
        self.assertTrue(result['predecessor_financial_fields_decoded'])
        self.assertEqual(len(result['implementation']), 18)
        self.assertFalse((self.root/repair.DIRECTORY/'attempt_claim.json').exists())

    def test_actual_PM_and_comparison_route_only_this_repair(self):
        from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate
        repo = Path(__file__).resolve().parents[2]
        gate = json.loads((repo/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        family = json.loads((repo/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        workstations = json.loads((repo/'configs/workstations.json').read_bytes())
        for reference in gate['required_reading']:
            path = self.root/reference['path']; path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists(): path.write_bytes(b'synthetic protocol')
        def build():
            return build_quant_pm_startup_gate(gate_config=gate, workstations_config=workstations,
                family_config=family, repo_root=self.root, machine='office_desktop',
                task='factor_review', branch=repair.BRANCH, current_branch=repair.BRANCH)
        result = build()
        self.assertEqual(result['status'], 'ready', result['blockers'])
        self.assertEqual(result['mode'], repair.MODE)
        self.assertEqual(result['account_comparison']['status'], 'passed_specification_only')
        self.assertTrue(result['safety']['commodity_proxy_lifecycle_repair_allowed'])
        for name in ('commodity_proxy_36_account_allowed', 'factor_batch_allowed',
                     'final_holdout_allowed', 'live_boundary_allowed'):
            self.assertFalse(result['safety'][name])
        self.assertEqual(result['safety']['factor_batch_scope'], {})
        self.assertEqual(result['safety']['commodity_proxy_36_account_scope'], {})
        gate.pop('account_comparison_protocol')
        result = build()
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['safety']['commodity_proxy_lifecycle_repair_allowed'])

    def test_claim_is_fsynced_before_decode_and_completed_cannot_reexecute(self):
        import os
        real_fsync = os.fsync
        with patch('quant_robot.research.monthly_diagnostic_registration.os.fsync', wraps=real_fsync) as fsync:
            def loader(snapshots):
                self.assertEqual(len(snapshots), 63)
                claim = json.loads((self.root/repair.DIRECTORY/'attempt_claim.json').read_bytes())
                self.assertEqual(claim['status'], 'claimed_before_financial_decode')
                self.assertEqual(claim['predecessor_registration_sha256'], self.old['registration_sha256'])
                self.assertGreaterEqual(fsync.call_count, 1)
                return {}
            result = self.execute(loader=loader)
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['qualified'])
        self.assertEqual(len(list((self.root/repair.DIRECTORY/'accounts').glob('*.json'))), 36)
        with self.assertRaisesRegex(ValueError, 'consumed'):
            self.execute(loader=lambda _: self.fail('No second financial decode'))
        self.assertEqual(json.loads((self.root/original.DIRECTORY/'outcome.json').read_bytes())['status'], 'failed_consumed')

    def test_loader_failure_retained_and_second_claim_rejected(self):
        def loader(_):
            raise ValueError('invented decode failure')
        with self.assertRaisesRegex(ValueError, 'invented decode failure'):
            self.execute(loader=loader)
        outcome = json.loads((self.root/repair.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual((outcome['status'], outcome['error_type']), ('failed_consumed', 'ValueError'))
        self.assertFalse((self.root/repair.DIRECTORY/'result.json').exists())
        with self.assertRaisesRegex(ValueError, 'consumed'):
            self.execute()

    def test_original_input_change_rejected_even_with_new_hash_and_review(self):
        reference = self.packet['base_registration']['inputs']['settlement_01']
        self.packet['base_registration']['inputs']['settlement_01'] = self.save(reference['path'], {'changed': True})
        self.sign(self.packet['base_registration']); self.publish()
        with self.assertRaisesRegex(ValueError, 'retain all original inputs'):
            repair.admitted_packet(self.root)

    def test_original_method_environment_policy_and_branch_cannot_drift(self):
        for key, value in (('environment', {'different': True}), ('branch', 'main'), ('policy', {'changed': True})):
            with self.subTest(key=key):
                packet = deepcopy(self.packet); packet['base_registration'][key] = value
                self.sign(packet['base_registration']); self.sign(packet)
                with self.assertRaisesRegex(ValueError, 'retain all original inputs'):
                    repair.validate_registration(packet, self.root)

    def test_unrelated_implementation_change_rejected_even_when_rebound(self):
        name = 'src/quant_robot/research/commodity_proxy_accounts.py'
        self.packet['base_registration']['implementation'][name] = self.save(name, {'changed': True})
        self.sign(self.packet['base_registration']); self.publish()
        with self.assertRaisesRegex(ValueError, 'Numerical implementation'):
            repair.admitted_packet(self.root)

    def test_original_success_or_any_accounts_or_result_prevents_repair(self):
        for name in ('accounts', 'result.json'):
            with self.subTest(name=name):
                path = self.root/original.DIRECTORY/name
                if name == 'accounts': path.mkdir()
                else: path.write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError, 'Predecessor with any result'):
                    repair.admitted_packet(self.root)
                if path.is_dir(): path.rmdir()
                else: path.unlink()
        self.rebind_predecessor('outcome', lambda value: value.update(status='completed'))
        with self.assertRaisesRegex(ValueError, 'pre-signal ValueError'):
            repair.admitted_packet(self.root)

    def test_predecessor_hash_change_and_claim_mismatch_are_rejected(self):
        path = self.root/repair.PREDECESSOR_PATHS['outcome']; raw = path.read_bytes()
        path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            repair.admitted_packet(self.root)
        path.write_bytes(raw)
        self.rebind_predecessor('attempt_claim', lambda value: value.update(registration_sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'Original attempt claim'):
            repair.admitted_packet(self.root)

    def test_failure_review_must_acknowledge_exposure_and_zero_accounts(self):
        for key, value in (('real_ETF_and_settlement_fields_decoded_by_original_loader', False),
                           ('financial_accounts_computed', 1), ('signal_values_computed', False)):
            with self.subTest(key=key):
                path = self.root/repair.PREDECESSOR_PATHS['failure_review']; raw = path.read_bytes()
                saved_packet = deepcopy(self.packet)
                self.rebind_predecessor('failure_review',
                    lambda document: document['execution_boundary'].update({key: value}))
                with self.assertRaisesRegex(ValueError, 'boundary failure evidence'):
                    repair.admitted_packet(self.root)
                path.write_bytes(raw); self.packet = saved_packet; self.publish()

    def test_wrong_stale_or_broad_gate_cannot_create_claim(self):
        mutations = [lambda g: g.update(mode=original.MODE),
            lambda g: g.update(generated_at='2026-11-06T19:50:00+00:00'),
            lambda g: g['safety'].update(commodity_proxy_36_account_allowed=True),
            lambda g: g['safety'].update(factor_batch_allowed=True),
            lambda g: g['safety']['commodity_proxy_lifecycle_repair_scope'].update(registration_sha256='0'*64),
            lambda g: g['safety']['commodity_proxy_lifecycle_repair_scope'].update(admission_file_sha256='0'*64)]
        for mutate in mutations:
            gate = self.gate(); mutate(gate)
            with self.assertRaisesRegex(ValueError, 'dedicated lifecycle repair'):
                self.execute(gate=lambda: gate, loader=lambda _: self.fail('No decode'))
            self.assertFalse((self.root/repair.DIRECTORY/'attempt_claim.json').exists())

    def test_input_mutation_during_decode_consumes_before_calculator(self):
        def loader(_):
            (self.root/self.old['inputs']['settlement_01']['path']).write_bytes(b'changed')
            return {}
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            self.execute(loader=loader, calculator=lambda **_: self.fail('No account'))
        self.assertTrue((self.root/repair.DIRECTORY/'outcome.json').is_file())

    def test_mutation_during_calculation_is_caught_before_result(self):
        def calculator(**kwargs):
            result = self.calculator(**kwargs)
            (self.root/repair.PREDECESSOR_PATHS['outcome']).write_bytes(b'changed')
            return result
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            self.execute(calculator=calculator)
        self.assertFalse((self.root/repair.DIRECTORY/'result.json').exists())
        self.assertEqual(len(list((self.root/repair.DIRECTORY/'accounts').glob('*.json'))), 36)

    def test_missing_or_duplicate_accounts_cannot_be_completed(self):
        with self.assertRaisesRegex(ValueError, 'Exact36'):
            self.execute(calculator=lambda **_: dict(account_count=36, cash_benchmark_count=2,
                qualified=False, real_forward_days_added=0))
        self.assertFalse((self.root/repair.DIRECTORY/'result.json').exists())

    def test_wrong_new_implementation_or_review_hash_rejected_before_decode(self):
        (self.root/repair.IMPLEMENTATION[0]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            self.execute(loader=lambda _: self.fail('No decode'))
        self.assertFalse((self.root/repair.DIRECTORY/'attempt_claim.json').exists())


if __name__ == '__main__':
    unittest.main()
