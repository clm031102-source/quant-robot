"""One-use admission is exercised with opaque invented bytes and fake runtime."""
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import commodity_proxy_admission as admission


class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 6, 19, tzinfo=timezone.utc)


class CommodityAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.env = patch.object(admission, 'runtime_environment', return_value={'synthetic': 'only'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.clock = patch.object(admission, 'datetime', FrozenClock)
        self.clock.start(); self.addCleanup(self.clock.stop)
        campaign = dict(campaign_id='quant_manager_72h_20261106', status='active',
            task_branch=admission.BRANCH, started_at='2026-11-06T16:21:39Z',
            delivery_deadline='2026-11-09T16:21:39Z', finite_preregistered_studies_required=True,
            old_consumed_scopes_remain_closed=True, holdout_unsealing_authorized=False,
            live_boundary_allowed=False)
        inputs = {}
        for role in admission.INPUT_ROLES:
            protocol_paths = {'campaign': admission.CAMPAIGN,
                'pm_policy': 'configs/quant_pm_startup_gate_cn_etf.json',
                'workstations': 'configs/workstations.json',
                'family_scheduler': 'configs/research_family_scheduler_cn_etf.json'}
            path = ('synthetic/year='+role[-4:]+'/bars.parquet' if role.startswith('bars_')
                    else protocol_paths[role] if role in protocol_paths else 'synthetic/'+role+'.json')
            inputs[role] = self.save(path, campaign if role == 'campaign' else {'opaque': role})
        code = {name: self.save(name, {'synthetic_code': name}) for name in admission.IMPLEMENTATION}
        self.packet = dict(artifact_type='commodity_proxy_account_registration_v1',
            branch=admission.BRANCH, inputs=inputs, implementation=code,
            environment={'synthetic': 'only'}, policy=admission.POLICY)
        self.packet['registration_sha256'] = admission.digest(admission.canonical(self.packet))
        registration = self.save(admission.REGISTRATION, self.packet)
        review = self.save(admission.REVIEW, dict(status='accepted_for_one_conditional_batch',
            registration_sha256=self.packet['registration_sha256'], reviewer='quant_manager_72h',
            qualified=False, real_forward_days_added=0))
        self.save(admission.ADMISSION, dict(artifact_type='commodity_proxy_finite_admission_v1',
            status='authorized_once', registration=registration, review=review, policy=admission.POLICY))

    def save(self, name, value):
        path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True)
        raw = admission.canonical(value); path.write_bytes(raw)
        return dict(path=name, sha256=admission.digest(raw))

    def gate(self):
        return dict(generated_at=FrozenClock.now().isoformat(), status='ready', blockers=[],
            mode=admission.MODE, primary_market='CN_ETF', selected=dict(machine='office_desktop',
                task='factor_review', branch=admission.BRANCH, current_branch=admission.BRANCH),
            safety=dict(commodity_proxy_36_account_allowed=True,
                commodity_proxy_36_account_scope={'registration_sha256': self.packet['registration_sha256']},
                factor_batch_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False))

    def execute(self, loader, calculator, gate=None):
        return admission.execute(self.root, expected_registration_sha256=self.packet['registration_sha256'],
            gate_supplier=gate or self.gate, load_inputs=loader, calculate=calculator)

    def test_preview_hashes_opaque_bytes_without_financial_parsing(self):
        packet, _ = admission.admitted_packet(self.root)
        self.assertEqual(packet, self.packet)
        self.assertFalse((self.root/admission.DIRECTORY/'attempt_claim.json').exists())
        scheduler = dict(blockers=['insufficient_active_research_families'],
                         summary=dict(primary_budget_share=0, active_primary_families=0))
        value = admission.scope('factor_review', {}, scheduler, root=self.root, branch=admission.BRANCH)
        self.assertEqual(value['mode'], admission.MODE)
        self.assertFalse(value['scope']['policy']['qualification_granted'])

    def test_PM_opens_only_exact_batch_and_still_requires_comparison_protocol(self):
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
                task='factor_review', branch=admission.BRANCH, current_branch=admission.BRANCH)
        result = build()
        self.assertEqual(result['status'], 'ready', result['blockers'])
        self.assertEqual(result['account_comparison']['status'], 'passed_specification_only')
        self.assertTrue(result['safety']['commodity_proxy_36_account_allowed'])
        self.assertFalse(result['safety']['factor_batch_allowed'])
        self.assertEqual(result['safety']['factor_batch_scope'], {})
        self.assertFalse(result['safety']['final_holdout_allowed'])
        gate.pop('account_comparison_protocol')
        result = build()
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['safety']['commodity_proxy_36_account_allowed'])

    def test_claim_precedes_decode_and_failure_cannot_resume(self):
        def loader(snapshots):
            claim = self.root/admission.DIRECTORY/'attempt_claim.json'
            self.assertTrue(claim.is_file())
            self.assertEqual(json.loads(claim.read_bytes())['status'], 'claimed_before_financial_decode')
            raise ValueError('synthetic financial validation failed')
        with self.assertRaisesRegex(ValueError, 'synthetic financial validation failed'):
            self.execute(loader, lambda **args: self.fail('No account after source failure'))
        outcome = json.loads((self.root/admission.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['status'], 'failed_consumed')
        with self.assertRaisesRegex(ValueError, 'consumed'):
            self.execute(lambda _: self.fail('Must not decode twice'), lambda **args: {})

    def test_review_only_gate_cannot_be_mistaken_for_financial_admission(self):
        def gate():
            result = self.gate(); result['mode'] = 'family_rotation_review_only'; return result
        with self.assertRaisesRegex(ValueError, 'dedicated finite financial gate'):
            self.execute(lambda _: self.fail('No decode'), lambda **args: {}, gate)
        self.assertFalse((self.root/admission.DIRECTORY/'attempt_claim.json').exists())

    def test_post_claim_input_mutation_fails_guard_and_consumes_batch(self):
        def calculate(**kwargs):
            role = self.packet['inputs']['settlement_01']['path']
            (self.root/role).write_bytes(b'mutated_after_claim')
            kwargs['guard']('before', 'synthetic/account')
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            self.execute(lambda _: {}, calculate)
        self.assertFalse((self.root/admission.DIRECTORY/'result.json').exists())
        self.assertTrue((self.root/admission.DIRECTORY/'outcome.json').exists())

    def test_modified_runtime_review_and_unrequested_partition_fail_before_claim(self):
        with patch.object(admission, 'runtime_environment', return_value={'changed': True}):
            with self.assertRaisesRegex(ValueError, 'environment changed'):
                admission.admitted_packet(self.root)
        review = self.root/admission.REVIEW
        review.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Frozen file changed'):
            admission.admitted_packet(self.root)
        packet = dict(self.packet); packet['inputs'] = dict(packet['inputs'])
        packet['inputs']['bars_2024'] = self.save('synthetic/year=2026/bars.parquet', {})
        packet['registration_sha256'] = admission.digest(admission.canonical(
            {key: value for key, value in packet.items() if key != 'registration_sha256'}))
        with self.assertRaisesRegex(ValueError, '2020-2024'):
            admission.validate_registration(packet, self.root)


if __name__ == '__main__':
    unittest.main()
