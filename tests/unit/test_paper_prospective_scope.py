"""Bounded synthetic acquisition authority; no network or credential operations."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_prospective_scope as prospective
from tests.unit import test_paper_source_connection as connection_fixtures


class ProspectiveScopeTests(TestCase):
    def setUp(self):
        self.case=connection_fixtures.SourceConnectionTests()
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.case.activate()
        self.day=self.case.fixture.days[21]
        self.context=dict(machine='office_desktop',task='factor_review',branch='codex/factor-review-test')
        self.decision=forward.decide(self.case.journal,now=self.day+'T01:00:00Z')

    def scope(self,at='T07:31:00Z'):
        return prospective.prepare_scope(self.case.journal,repo_root=self.case.root,
                                         context=self.context,now=self.day+at)

    def validate(self,scope,at='T07:31:00Z',synthetic=True):
        return prospective.validate_execution(scope,repo_root=self.case.root,
            now=self.day+at,synthetic=synthetic)

    def test_exact_pending_day_derived_without_credential_or_network_access(self):
        scope=self.scope()
        result=self.validate(scope)
        self.assertEqual(scope['request'],dict(ts_code='510300.SH',trade_date=self.day.replace('-','')))
        self.assertEqual(scope['journal_binding']['decision_sha256'],self.decision['sha256'])
        self.assertEqual(scope['valid_from'],self.day+'T07:30:00.000000Z')
        # This fixture's pending session is Friday: the 24-hour receipt cap
        # closes Saturday, before Monday's next auction cutoff.
        self.assertEqual(scope['valid_until'],'2020-02-01T07:30:00.000000Z')
        self.assertFalse(result['credentials_read'])
        self.assertEqual(result['network_requests_started'],0)
        self.assertFalse(result['policy']['sealed_research_partitions_opened'])
        self.assertEqual(self.validate(self.scope('T08:00:00Z'),'T08:00:00Z')['request_identity'],result['request_identity'])

    def test_before_final_or_after_next_cutoff_rejected(self):
        scope=self.scope('T07:00:00Z')
        with self.assertRaisesRegex(ValueError,'final observable session window'):
            self.validate(scope,'T07:00:00Z')
        with self.assertRaisesRegex(ValueError,'window expired'):
            prospective.validate_execution(scope,repo_root=self.case.root,synthetic=True,
                now=self.case.fixture.days[22]+'T01:15:00Z')

    def test_request_budget_profile_policy_and_future_date_cannot_be_switched(self):
        scope=self.scope()
        for case in ('date','asset','budget','policy','profile','implementation'):
            value=deepcopy(scope)
            if case=='date':value['request']['trade_date']='20261109'
            if case=='asset':value['request']['ts_code']='518880.SH'
            if case=='budget':value['request_budget']=2
            if case=='policy':value['policy']['sealed_research_partitions_opened']=True
            if case=='profile':value['source_profile']['profile_id']='real_provider'
            if case=='implementation':value['implementation_binding']['scope_code_sha256']='0'*64
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'differs from current frozen'):
                self.validate(value)

    def test_fixture_cannot_enable_production_capture(self):
        with self.assertRaisesRegex(ValueError,'must remain separate'):
            self.validate(self.scope(),synthetic=False)

    def test_missing_durable_confirmation_and_incomplete_publication_block(self):
        events=forward._journal(self.case.journal)
        confirmation=next(e for e in events if e['kind']=='decision_durability')
        path=self.case.journal/f'{confirmation["sequence"]:08d}.json'
        raw=path.read_bytes();path.unlink()
        with self.assertRaisesRegex(ValueError,'durability receipt'):
            self.scope()
        path.write_bytes(raw)
        (self.case.journal/'.pending-test.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Stable completed journal'):
            self.scope()

    def test_already_observed_session_cannot_be_requested_again(self):
        scope=self.scope()
        forward.observe(self.case.journal,self.case.daily_packet(),now=self.day+'T08:02:00Z')
        with self.assertRaisesRegex(ValueError,'pre-existing decision'):
            self.validate(scope,'T08:03:00Z')

    def test_writer_appearing_during_final_code_binding_blocks_execution_scope(self):
        scope=self.scope();binding=prospective.implementation_binding
        def late_writer():
            result=binding()
            (self.case.journal/'.writer.lock').write_text('synthetic writer',encoding='utf-8')
            return result
        with patch.object(prospective,'implementation_binding',side_effect=late_writer):
            with self.assertRaisesRegex(ValueError,'Stable completed journal'):
                self.validate(scope)
