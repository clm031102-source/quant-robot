"""Review-packet preparation against fabricated originals only."""
from copy import deepcopy
from dataclasses import asdict
import io
import json
from contextlib import redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import frozen_candidate_manifest as prepare
from quant_robot.ops import paper_source_connection as connection
from quant_robot.paper.annual_allocation import AllocationConfig
from tests.unit import test_paper_warmup_bundle as fixtures


class FrozenManifestPreparationTests(TestCase):
    def setUp(self):
        self.fixture = fixtures.PaperWarmupBundleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.make_prefix(21)
        profile = connection.PROFILES[connection.PROFILE_ID]
        f.bind(adapters=profile.adapters, adapter_dependencies=profile.dependencies)
        f.save('spec.json', f.spec)
        f.save('schedule.json', f.calendar['sessions'])
        self.output = f.root/'prepared'
        self.request = dict(artifact_type=prepare.REQUEST_TYPE, candidate_id='SYNTHETIC_ONLY',
            asset_id=f.spec['asset_id'], first_session=f.days[21],
            strategy=dict(adapter='existing_predicate_and_v1', components=['sma20_trend'], cadence=1),
            account_config=asdict(AllocationConfig(max_position_cny=10000, max_position_fraction=1,
                max_drawdown=.4, execution_price_field='open')),
            source_id='synthetic-originals', source_profile_id=connection.PROFILE_ID,
            maximum_receive_delay_seconds=86400,
            calendar=forward.file_reference(f.root/'schedule.json'),
            warmup_proof=connection.proof_reference(f.root, 'spec.json'))

    def run_prepare(self, request=None):
        return prepare.prepare_manifest(request or self.request, self.output, now=self.fixture.as_of)

    def test_output_is_exact_runtime_compatible_but_has_no_qualification(self):
        before = deepcopy(self.request)
        result = self.run_prepare()
        self.assertEqual(before, self.request)
        self.assertEqual(result['status'], 'prepared_for_independent_review')
        self.assertFalse(result['qualified'])
        self.assertFalse(result['forward_source_admitted'])
        self.assertEqual(result['real_forward_days'], 0)
        self.assertEqual({p.name for p in self.output.iterdir()},
                         {'request.json', 'warmup.json', 'manifest.json', 'preparation.json'})
        self.assertEqual(forward.file_reference(self.output/'manifest.json'), result['manifest'])
        # A separate fabricated review confirms compatibility only in this test.
        support = self.fixture.root/'artificial_review_support.json'
        support.write_text('{"synthetic_only":true}', encoding='utf-8')
        review = self.fixture.root/'artificial_review.json'
        review.write_text(json.dumps(dict(artifact_type=forward.QUALIFICATION_TYPE,
            manifest_sha256=result['manifest']['sha256'], verdict='qualified',
            review_role='independent_qualification_review', evidence_class='synthetic_test_only',
            gates={name:True for name in forward.GATES},
            supporting_evidence=[forward.file_reference(support)])), encoding='utf-8')
        manifest, _, _, _ = forward._contracts(result['manifest'], forward.file_reference(review))
        with self.assertRaisesRegex(ValueError, 'synthetic profile cannot certify forward'):
            forward._require_verified_forward_source(manifest)

    def test_second_preparation_never_overwrites_first(self):
        result = self.run_prepare()
        with self.assertRaises(FileExistsError):
            self.run_prepare()
        self.assertEqual(forward.file_reference(self.output/'manifest.json'), result['manifest'])

    def test_missing_fee_invalid_risk_and_unsupported_strategy_fail_before_writes(self):
        variants = []
        value=deepcopy(self.request);del value['account_config']['minimum_commission'];variants.append(value)
        value=deepcopy(self.request);value['account_config']['max_drawdown']=.5;variants.append(value)
        value=deepcopy(self.request);value['account_config']['commission_bps']=float('nan');variants.append(value)
        value=deepcopy(self.request);value['strategy']['cadence']=True;variants.append(value)
        value=deepcopy(self.request);value['strategy']['components']=['custom_profit_signal'];variants.append(value)
        value=deepcopy(self.request);value['qualified']=True;variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_prepare(value)
            self.assertFalse(self.output.exists())

    def test_missing_next_session_and_calendar_mutation_reject(self):
        value=deepcopy(self.request);value['first_session']=self.fixture.days[-1]
        with self.assertRaisesRegex(ValueError, 'next session'):
            self.run_prepare(value)
        (self.fixture.root/'schedule.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_source_changed_during_write_leaves_incomplete_packet(self):
        original = prepare._write_new
        def mutate(path, value):
            ref=original(path,value)
            if path.name=='manifest.json':
                (self.fixture.root/'identity/original.json').write_text('{}',encoding='utf-8')
            return ref
        with patch.object(prepare, '_write_new', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'evidence_hash_mismatch'):
                self.run_prepare()
        self.assertTrue((self.output/'manifest.json').exists())
        self.assertFalse((self.output/'preparation.json').exists())

    def test_unknown_source_profile_is_not_a_configuration_override(self):
        value=deepcopy(self.request);value['source_profile_id']='caller_approved_production'
        with self.assertRaisesRegex(ValueError,'reviewed code profile required'):
            self.run_prepare(value)
        self.assertFalse(self.output.exists())

    def test_cli_outputs_review_only_and_does_not_accept_clock_override(self):
        from scripts.prepare_frozen_candidate_manifest import main
        self.fixture.save('request.json', self.request)
        stdout=io.StringIO()
        with redirect_stdout(stdout):
            status=main(['--request',str(self.fixture.root/'request.json'),'--output',str(self.output)])
        self.assertEqual(status,0)
        self.assertFalse(json.loads(stdout.getvalue())['qualification_issued'])
        with self.assertRaises(SystemExit):
            main(['--request','unused','--output','unused','--now','2020-01-01T00:00:00Z'])

    def test_request_reader_has_a_byte_budget(self):
        path=self.fixture.root/'oversized.json'
        path.write_bytes(b' '*(prepare.MAX_REQUEST_BYTES+1))
        with self.assertRaisesRegex(ValueError,'byte budget'):
            prepare.read_request(path)

    def test_preparer_module_or_cli_changed_during_write_cannot_complete(self):
        original=prepare._write_new
        for component in ('module','cli'):
            with self.subTest(component=component):
                fake=self.fixture.root/f'{component}_copy.py'
                fake.write_text('# original artificial code\n',encoding='utf-8')
                def mutate(path,value):
                    ref=original(path,value)
                    if path.name=='manifest.json':
                        fake.write_text('# changed artificial code\n',encoding='utf-8')
                    return ref
                target='__file__' if component=='module' else 'PREPARER_CLI'
                value=str(fake) if component=='module' else fake
                self.output=self.fixture.root/f'failed_{component}'
                with patch.object(prepare,target,value),patch.object(prepare,'_write_new',side_effect=mutate):
                    with self.assertRaisesRegex(ValueError,'Preparer code changed'):
                        self.run_prepare()
                self.assertFalse((self.output/'preparation.json').exists())
