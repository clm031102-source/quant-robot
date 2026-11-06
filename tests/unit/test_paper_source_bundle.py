"""Offline assembly tests: no credentials, provider requests or market prices."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.ops import paper_source_bundle as bundle
from quant_robot.ops import tushare_daily_receipt
from quant_robot.ops import tushare_live_transport as live
from quant_robot.ops.frozen_cash_actions import cash_action_snapshot
from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar, write_cn_trading_calendar
from tests.unit.test_tushare_daily_receipt import Response, Transport, TOKEN
from tests.unit import test_tushare_live_transport as live_fixture


ASSET = 'CN_ETF_XSHG_510300'
DAY = '2020-01-02'
DECISION = '2020-01-03T01:00:00Z'
START = '2020-01-02T08:00:01Z'
RECEIVED = '2020-01-02T08:00:03Z'


def fabricated_boolean_adapter(context, ref):
    return True


def attempted_fixture_promotion(context, ref):
    original = bundle._metadata_fixture(context, ref)
    return bundle.Evidence(original.facts, original.request_started_at,
                           original.received_at, 'recorded_observation')


def changing_original_adapter(context, ref):
    original = bundle._metadata_fixture(context, ref)
    wrapper = context.read_json(ref)
    context.path_for(wrapper['raw']).write_bytes(b'{}')
    return original


class PaperSourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = (Path(self.temporary.name)/'evidence').resolve()
        self.root.mkdir()
        times = iter((START, RECEIVED))
        response = Response(date='Thu, 02 Jan 2020 08:00:02 GMT')
        captured = tushare_daily_receipt.capture_synthetic_receipt(
            self.root/'prices', ts_code='510300.SH', trade_date='20200102', token=TOKEN,
            transport=Transport(response), clock=lambda: next(times))
        self.spec = dict(artifact_type=bundle.SPEC_TYPE, asset_id=ASSET, session_date=DAY,
            window_start='2019-12-01', evidence={'price':dict(adapter_id='tushare_synthetic_fund_daily_v1',
                receipt=self.ref(Path(captured['receipt_path'])))})
        self.facts = {
            'calendar':dict(exchange='XSHG', sessions=[dict(date=day,
                decision_cutoff_at=day+'T01:15:00Z', open_at=day+'T01:30:00Z',
                auction_close_at=day+'T07:00:00Z', daily_observation_not_before=day+'T07:30:00Z')
                for day in ('2020-01-02', '2020-01-03')]),
            'identity':dict(asset_id=ASSET, instrument_type='ETF', currency='CNY',
                price_unit='CNY_per_fund_unit', volume_unit='fund_units', amount_unit='CNY',
                listing_date='2010-01-01', delisting_date=None, valid_from='2010-01-01',
                valid_through='2030-01-01'),
            'execution':dict(asset_id=ASSET, session_date=DAY, suspended=False,
                limit_regime='bounded', up_limit='5', down_limit='3'),
            'actions':dict(asset_id=ASSET, coverage_start='2019-12-01', coverage_end=DAY,
                pages=[dict(page_number=1, total_pages=1, total_records=0, records=[])], notices=[]),
        }
        for component in self.facts:
            self.write_component(component)

    def ref(self, path):
        return dict(path=path.relative_to(self.root).as_posix(), sha256=sha256(path.read_bytes()).hexdigest())

    def save(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        return self.ref(path)

    def write_component(self, component, *, received=RECEIVED):
        raw = self.save(self.root/component/'original.json', self.facts[component])
        receipt = self.save(self.root/component/'receipt.json', dict(artifact_type=bundle.FIXTURE_TYPE,
            component=component, request_started_at=START, received_at=received, raw=raw))
        self.spec['evidence'][component] = dict(adapter_id=f'synthetic_{component}_evidence_v1', receipt=receipt)

    def assemble(self, **kwargs):
        return bundle.build_source_bundle(self.spec, evidence_root=self.root,
                                         decision_at=kwargs.pop('decision_at', DECISION), **kwargs)

    def codes(self, result):
        return {(item['component'], item['code']) for item in result['blockers']}

    def add_cash(self):
        action = dict(event_id='cash-001', asset_id=ASSET, kind='cash_dividend',
            announced_date='2020-01-01', record_date='2020-01-03', ex_date='2020-01-06',
            pay_date='2020-01-09', cash_amount='0.12345', per_units='10',
            share_multiplier='1', cash_basis='net')
        self.facts['actions']['pages'][0].update(total_records=1,
            records=[dict(event_id='cash-001', kind='cash_dividend')])
        self.facts['actions']['notices'] = [action]
        self.write_component('actions')
        return action

    def scoped_price(self):
        fixture = live_fixture.ScopedTransportTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.root = self.root
        fixture.scope_path = self.root/'scope.json'
        fixture.make_scope('20200102')
        fixture.now = datetime(2020, 1, 2, 7, 30, 2, tzinfo=timezone.utc)
        response = live_fixture.Response(live_fixture.payload('20200102'),
                                        date='Thu, 02 Jan 2020 07:30:02 GMT')
        with patch.object(live, '_existing_token', side_effect=AssertionError('host credential read')), \
                patch.object(live, '_new_session', side_effect=AssertionError('real network')):
            result = fixture.collect(response)
        self.assertEqual(result['status'], 'source_observed_unqualified')
        receipt_path = Path(result['receipt_path']).resolve()
        self.spec['evidence']['price'] = dict(adapter_id='tushare_scoped_fund_daily_v1',
                                            receipt=self.ref(receipt_path))
        return receipt_path

    def published_calendar(self):
        folder = self.root/'published_calendar'
        sources, frames = [], {}
        for exchange in ('SSE', 'SZSE'):
            rows = [[exchange, '20200101', 0, '20191231'],
                    [exchange, '20200102', 1, '20191231'],
                    [exchange, '20200103', 1, '20200102'],
                    [exchange, '20200104', 0, '20200103'],
                    [exchange, '20200105', 0, '20200103']]
            reference = self.save(folder/(exchange+'.json'), dict(code=0, data=dict(
                fields=['exchange','cal_date','is_open','pretrade_date'], items=rows, has_more=False)))
            sources.append(dict(kind='trade_cal', exchange=exchange, received_at=RECEIVED, **reference))
            frames[exchange] = pd.DataFrame(dict(exchange=exchange,
                date=[DAY,'2020-01-03'], is_open=[1,1]))
        calendar, manifest = build_cn_trading_calendar(frames, start_date='2020-01-01', end_date='2020-01-05')
        written = write_cn_trading_calendar(folder/'derived', calendar, manifest)
        rule_path = folder/'synthetic_rule.txt'
        rule_path.write_text('SYNTHETIC_ONLY calendar rule fixture', encoding='utf-8')
        sources.append(dict(kind='official_rule_or_schedule', received_at=RECEIVED, **self.ref(rule_path)))
        calendar_ref, manifest_ref = (self.ref(Path(written[key])) for key in ('calendar_path','manifest_path'))
        rows = [dict(date=day, exchange_codes=['SSE','SZSE'],
            open_auction_start_utc=day+'T01:15:00+00:00',
            open_auction_end_utc=day+'T01:25:00+00:00',
            auction_close_utc=day+'T07:00:00+00:00',
            daily_observation_not_before_utc=day+'T07:30:00+00:00',
            next_session_open_utc='2020-01-03T01:15:00+00:00' if day==DAY else None)
            for day in (DAY,'2020-01-03')]
        metadata = dict(artifact_type='cn_etf_published_session_metadata_v1',
            evidence_class='synthetic_metadata_only', timezone='Asia/Shanghai',
            created_at='2020-01-02T08:00:04+00:00', effective_from=DAY, effective_through='2020-01-03',
            calendar_path=calendar_ref['path'], calendar_sha256=calendar_ref['sha256'],
            calendar_manifest_path=manifest_ref['path'], calendar_manifest_sha256=manifest_ref['sha256'],
            sources=sources, session_rows=rows)
        self.calendar_metadata = metadata
        self.calendar_metadata_path = folder/'session_metadata.json'
        return self.register_calendar()

    def register_calendar(self):
        reference = self.save(self.calendar_metadata_path, self.calendar_metadata)
        self.spec['evidence']['calendar'] = dict(adapter_id='reviewed_calendar_test', receipt=reference)
        registry = dict(bundle.DEFAULT_ADAPTERS)
        registry['reviewed_calendar_test'] = bundle.published_calendar_adapter(
            exchange='XSHG', reviewed_metadata_sha256=reference['sha256'])
        return registry

    def test_scoped_transport_mock_receipt_integrates_without_source_admission(self):
        self.scoped_price()
        result = self.assemble()
        self.assertEqual(result['blockers'], [])
        self.assertTrue(result['input_contract_complete'])
        self.assertEqual(result['evidence']['price']['evidence_class'], 'synthetic_only')
        self.assertEqual(result['bar']['volume'], '1234567')
        self.assertFalse(result['source_admission_granted'])
        self.assertFalse(result['real_forward_eligible'])
        self.assertEqual(result['real_forward_days_added'], 0)

    def test_scoped_receipt_reconstruction_rejects_mapping_and_lineage_tampering(self):
        path = self.scoped_price()
        original = json.loads(path.read_bytes())
        for case in ('bar', 'lineage', 'clock'):
            receipt = deepcopy(original)
            if case == 'bar':
                receipt['normalized_bar']['close'] = '4.11'
            elif case == 'lineage':
                receipt['evidence_class'] = 'live_source_observation'
            else:
                receipt['received_at'] = '2020-01-02T06:00:00Z'
            self.spec['evidence']['price']['receipt'] = self.save(path, receipt)
            with self.subTest(case=case):
                result = self.assemble()
                self.assertFalse(result['input_contract_complete'])
                self.assertIn('price', {b['component'] for b in result['blockers']})

    def test_scoped_receipt_review_original_is_consumed_and_hash_checked(self):
        path = self.scoped_price()
        receipt = json.loads(path.read_bytes())
        reference = next(iter(receipt['evidence_refs'].values()))
        (path.parent/reference['path']).write_text('changed review', encoding='utf-8')
        self.assertIn(('price','evidence_hash_mismatch'), self.codes(self.assemble()))

    def test_published_calendar_requires_code_registered_reviewed_fingerprint(self):
        registry = self.published_calendar()
        self.assertIn(('calendar','unsupported_component_adapter'), self.codes(self.assemble()))
        result = self.assemble(adapters=registry)
        self.assertEqual(result['blockers'], [])
        self.assertTrue(result['input_contract_complete'])
        self.assertEqual(result['input_available_at'], '2020-01-02T08:00:04Z')
        self.assertEqual(result['evidence']['calendar']['evidence_class'], 'synthetic_only')
        self.calendar_metadata['created_at'] = '2020-01-02T08:00:05+00:00'
        self.spec['evidence']['calendar']['receipt'] = self.save(self.calendar_metadata_path, self.calendar_metadata)
        self.assertIn(('calendar','calendar_not_the_reviewed_metadata_version'),
                      self.codes(self.assemble(adapters=registry)))

    def test_published_calendar_crosschecks_original_coverage_rules_and_next_cutoff(self):
        self.published_calendar()
        original = deepcopy(self.calendar_metadata)
        for case in ('missing_exchange', 'missing_rule', 'missing_session', 'next_cutoff'):
            self.calendar_metadata = deepcopy(original)
            if case == 'missing_exchange':
                self.calendar_metadata['sources'].pop(1)
            elif case == 'missing_rule':
                self.calendar_metadata['sources'].pop()
            elif case == 'missing_session':
                self.calendar_metadata['session_rows'].pop()
            else:
                self.calendar_metadata['session_rows'][0]['next_session_open_utc'] = '2020-01-03T01:30:00+00:00'
            registry = self.register_calendar()
            with self.subTest(case=case):
                self.assertFalse(self.assemble(adapters=registry)['input_contract_complete'])

    def test_published_calendar_reconstructs_complete_raw_civil_dates(self):
        self.published_calendar()
        original = self.calendar_metadata['sources'][0]
        path = self.root/original['path']
        raw = json.loads(path.read_bytes())
        raw['data']['items'].pop()  # Removing a closed day must also block coverage.
        original.update(self.save(path, raw))
        registry = self.register_calendar()
        self.assertFalse(self.assemble(adapters=registry)['input_contract_complete'])

    def test_published_calendar_original_mutation_and_late_derivation_block(self):
        registry = self.published_calendar()
        rule = self.root/self.calendar_metadata['sources'][-1]['path']
        original_bytes = rule.read_bytes()
        rule.write_bytes(b'different rule')
        self.assertIn(('calendar','evidence_hash_mismatch'), self.codes(self.assemble(adapters=registry)))
        rule.write_bytes(original_bytes)
        self.calendar_metadata['created_at'] = '2020-01-03T02:00:00+00:00'
        registry = self.register_calendar()
        self.assertFalse(self.assemble(adapters=registry)['input_contract_complete'])

    def test_complete_original_bundle_has_no_publication_or_qualification_claim(self):
        self.write_component('identity', received='2020-01-02T08:00:05Z')
        before = {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.assemble()
        self.assertEqual(result['blockers'], [])
        self.assertTrue(result['input_contract_complete'])
        self.assertEqual(result['evidence_class'], 'synthetic_only')
        self.assertEqual(result['input_available_at'], '2020-01-02T08:00:05Z')
        price_receipt = json.loads((self.root/self.spec['evidence']['price']['receipt']['path']).read_bytes())
        self.assertEqual(result['evidence']['price']['request_started_at'], price_receipt['request_started_at'])
        self.assertIsNone(result['provider_generated_at'])
        self.assertIsNone(result['provider_first_publication_at'])
        self.assertFalse(result['candidate_qualification_granted'])
        self.assertFalse(result['source_admission_granted'])
        self.assertFalse(result['real_forward_eligible'])
        self.assertEqual(result['real_forward_days_added'], 0)
        self.assertEqual(result['bar']['amount'], '98765432')
        self.assertFalse(result['bar']['suspended'])
        self.assertEqual(result['action_coverage']['indexed_events'], 0)
        self.assertEqual(self.assemble(), result)
        self.assertEqual(before, {p.relative_to(self.root).as_posix():p.read_bytes()
                                 for p in self.root.rglob('*') if p.is_file()})

    def test_all_missing_components_report_individually(self):
        self.spec['evidence'] = {}
        result = self.assemble()
        self.assertEqual(self.codes(result), {(kind,'missing_evidence') for kind in bundle.COMPONENTS})
        self.assertFalse(result['input_contract_complete'])
        self.assertNotIn('bar', result)

    def test_date_only_naive_or_offset_decision_is_rejected_cleanly(self):
        for value in ('2020-01-03Z','2020-01-03T01:00:00','2020-01-03T09:00:00+08:00'):
            with self.subTest(value=value):
                result=self.assemble(decision_at=value)
                self.assertEqual(result['status'],'blocked')
                self.assertEqual(result['blockers'][0]['component'],'spec')

    def test_verified_flags_cannot_replace_missing_original_evidence(self):
        self.spec['evidence']['identity'] = dict(verified=True)
        result = self.assemble()
        self.assertIn(('identity','fields_missing_or_unsupported'), self.codes(result))
        self.spec['evidence'].pop('identity')
        self.spec['verified'] = True
        self.assertEqual(self.assemble()['status'], 'blocked')

    def test_raw_hash_change_rejects_evidence(self):
        (self.root/'execution'/'original.json').write_bytes(b'{}')
        self.assertIn(('execution','evidence_hash_mismatch'), self.codes(self.assemble()))

    def test_reference_cannot_escape_evidence_root(self):
        outside = self.root.parent/'outside.json'
        outside.write_bytes(b'{}')
        self.spec['evidence']['identity']['receipt'] = dict(path='../outside.json', sha256=sha256(b'{}').hexdigest())
        self.assertIn(('identity','evidence_path_escapes_root'), self.codes(self.assemble()))

    def test_receipt_component_must_match_registered_role(self):
        ref = self.spec['evidence']['identity']['receipt']
        path = self.root/ref['path']
        value = json.loads(path.read_bytes()); value['component'] = 'calendar'
        self.spec['evidence']['identity']['receipt'] = self.save(path,value)
        self.assertIn(('identity','explicit_metadata_fixture_required'), self.codes(self.assemble()))

    def test_received_before_full_daily_observation_window_blocks(self):
        self.facts['calendar']['sessions'][0]['daily_observation_not_before'] = '2020-01-02T08:30:00Z'
        self.write_component('calendar')
        self.assertIn(('cross_evidence','price_received_before_daily_observation_window'), self.codes(self.assemble()))

    def test_early_request_late_receipt_cannot_certify_a_complete_daily_response(self):
        # Request begins before the daily window, but its final byte arrives after it.
        self.facts['calendar']['sessions'][0]['daily_observation_not_before'] = '2020-01-02T08:00:02Z'
        self.write_component('calendar')
        result = self.assemble()
        self.assertIn(('cross_evidence','price_requested_before_daily_observation_window'), self.codes(result))
        price_receipt = json.loads((self.root/self.spec['evidence']['price']['receipt']['path']).read_bytes())
        self.assertEqual(result['evidence']['price']['request_started_at'], price_receipt['request_started_at'])
        self.assertEqual(result['evidence']['price']['received_at'], price_receipt['received_at'])
        self.assertFalse(result['real_forward_eligible'])
        # Equality at the lower boundary is allowed, with both clocks preserved.
        self.facts['calendar']['sessions'][0]['daily_observation_not_before'] = START
        self.write_component('calendar')
        self.assertTrue(self.assemble()['input_contract_complete'])

    def test_decision_cutoff_is_auction_start_not_continuous_open(self):
        for moment in ('2020-01-03T01:15:00Z', '2020-01-03T01:29:59Z'):
            with self.subTest(moment=moment):
                self.assertIn(('cross_evidence','decision_at_or_after_next_opening_auction_cutoff'),
                              self.codes(self.assemble(decision_at=moment)))
        self.assertTrue(self.assemble(decision_at='2020-01-03T01:14:59Z')['input_contract_complete'])

    def test_any_auxiliary_evidence_received_after_decision_blocks(self):
        self.write_component('actions', received='2020-01-03T01:00:01Z')
        self.assertIn(('actions','evidence_not_received_before_decision'), self.codes(self.assemble()))

    def test_bad_calendar_order_or_missing_successor_blocks(self):
        original = deepcopy(self.facts['calendar'])
        self.facts['calendar']['sessions'][0]['daily_observation_not_before'] = '2020-01-02T06:59:59Z'
        self.write_component('calendar')
        self.assertIn(('calendar','session_clock_order_invalid'), self.codes(self.assemble()))
        self.facts['calendar'] = original
        self.facts['calendar']['sessions'][1]['date'] = DAY
        self.write_component('calendar')
        self.assertFalse(self.assemble()['input_contract_complete'])

    def test_session_clocks_must_belong_to_the_labeled_China_session_date(self):
        self.facts['calendar']['sessions'][0]['date'] = '2020-01-01'
        self.write_component('calendar')
        self.assertIn(('calendar','session_clock_date_mismatch'), self.codes(self.assemble()))

    def test_wrong_ETF_identity_units_or_lifecycle_blocks(self):
        for key,value in (('instrument_type','LOF'), ('currency','USD'), ('volume_unit','hands'),
                          ('listing_date','2020-01-03'), ('delisting_date',DAY)):
            with self.subTest(key=key):
                original=self.facts['identity'][key]
                self.facts['identity'][key]=value; self.write_component('identity')
                self.assertFalse(self.assemble()['input_contract_complete'])
                self.facts['identity'][key]=original
        self.write_component('identity')
        self.facts['identity']['valid_through']=DAY; self.write_component('identity')
        self.assertIn(('cross_evidence','ETF_identity_not_valid_for_next_session'),self.codes(self.assemble()))

    def test_unknown_execution_flags_and_suspended_days_do_not_get_filled_false(self):
        for value,code in ((None,'known_suspension_state_required'),
                           (True,'suspended_session_valuation_adapter_required')):
            self.facts['execution']['suspended']=value; self.write_component('execution')
            self.assertIn(('execution',code),self.codes(self.assemble()))

    def test_verified_price_limits_map_opening_flags_and_reject_outside_range(self):
        raw = json.loads(Response().raw)
        raw['data']['items'][0][3] = 4.111  # high equals the opening upper limit
        raw['data']['items'][0][5] = 4.105
        times = iter((START, RECEIVED))
        captured = tushare_daily_receipt.capture_synthetic_receipt(self.root/'limit_price',
            ts_code='510300.SH', trade_date='20200102', token=TOKEN,
            transport=Transport(Response(json.dumps(raw).encode(), date='Thu, 02 Jan 2020 08:00:02 GMT')),
            clock=lambda: next(times))
        self.spec['evidence']['price']['receipt'] = self.ref(Path(captured['receipt_path']))
        self.facts['execution']['up_limit']='4.111'; self.write_component('execution')
        result=self.assemble()
        self.assertTrue(result['bar']['limit_up'])
        self.assertFalse(result['bar']['limit_down'])
        self.facts['execution']['up_limit']='4.110'; self.write_component('execution')
        self.assertIn(('cross_evidence','OHLC_outside_verified_limits'),self.codes(self.assemble()))

    def test_intraday_extreme_outside_verified_limit_blocks_even_if_open_is_inside(self):
        self.facts['execution']['up_limit'] = '4.2'
        self.write_component('execution')
        self.assertIn(('cross_evidence','OHLC_outside_verified_limits'), self.codes(self.assemble()))

    def test_future_announcement_cannot_be_received_before_its_publication_date(self):
        action = self.add_cash()
        action['announced_date'] = '2020-01-03'
        self.facts['actions']['coverage_end'] = '2020-01-03'
        self.write_component('actions')
        self.assertIn(('actions','notice_announced_after_session'),
                      self.codes(self.assemble()))

    def test_receipt_date_check_is_retained_even_when_announcement_is_in_session(self):
        action = self.add_cash()
        action['announced_date'] = DAY
        self.write_component('actions')
        path = self.root/'actions'/'receipt.json'
        receipt = json.loads(path.read_bytes())
        receipt.update(request_started_at=None, received_at='2020-01-01T01:00:00Z')
        self.spec['evidence']['actions']['receipt'] = self.save(path, receipt)
        self.assertIn(('cross_evidence','notice_announcement_after_receipt_date'),
                      self.codes(self.assemble()))

    def test_cash_event_count_boundary_matches_account_consumer(self):
        example = deepcopy(self.add_cash())
        for count in (1000, 1001):
            self.facts['actions']['pages'][0].update(total_records=count, records=[
                dict(event_id=str(index), kind='cash_dividend') for index in range(count)])
            self.facts['actions']['notices'] = [dict(example, event_id=str(index), cash_amount=str(index+1))
                                              for index in range(count)]
            self.write_component('actions')
            result = self.assemble()
            with self.subTest(count=count):
                if count == 1000:
                    self.assertTrue(result['input_contract_complete'], result['blockers'])
                    self.assertEqual(len(result['corporate_actions']), count)
                else:
                    self.assertIn(('actions','action_event_count_exceeds_account_limit'), self.codes(result))
        # An oversized index cannot bypass the bound by omitting notices.
        self.facts['actions']['notices'] = []
        self.write_component('actions')
        self.assertIn(('actions','action_event_count_exceeds_account_limit'), self.codes(self.assemble()))

    def test_cash_event_id_boundary_matches_account_consumer(self):
        action = self.add_cash()
        for length in (200, 201):
            identity = 'x' * length
            action['event_id'] = identity
            self.facts['actions']['pages'][0]['records'][0]['event_id'] = identity
            self.write_component('actions')
            with self.subTest(length=length):
                self.assertEqual(self.assemble()['input_contract_complete'], length == 200)

    def test_cash_precision_is_checked_on_exact_emitted_consumer_value(self):
        action = self.add_cash()
        action['per_units'] = '1'
        for amount, accepted in (('9'*40, True), ('9'*41, False),
                                 ('1e-40', True), ('1e-41', False),
                                 ('1e39', True), ('1e40', False)):
            action['cash_amount'] = amount
            self.write_component('actions')
            result = self.assemble()
            with self.subTest(amount=amount):
                self.assertEqual(result['input_contract_complete'], accepted, result['blockers'])
                if not accepted:
                    self.assertIn(('actions','cash_per_unit_exceeds_account_precision'), self.codes(result))

    def test_assembled_cash_composes_with_bridge_and_keeps_frozen_calendar_check_there(self):
        self.add_cash()
        assembled = self.assemble()
        self.assertTrue(assembled['input_contract_complete'])
        actions = assembled['corporate_actions']
        complete_calendar = [DAY, '2020-01-03', '2020-01-06', '2020-01-09']
        first = cash_action_snapshot(actions, asset=ASSET, sessions=complete_calendar, as_of_session=DAY)
        repeated = cash_action_snapshot(actions, asset=ASSET, sessions=complete_calendar,
                                        as_of_session='2020-01-03', previous=first)
        self.assertEqual(first, repeated)
        self.assertEqual(first[0]['cash_per_unit'], '0.012345')
        with self.assertRaisesRegex(ValueError, 'Previously received'):
            cash_action_snapshot([], asset=ASSET, sessions=complete_calendar,
                                 as_of_session='2020-01-03', previous=first)
        with self.assertRaisesRegex(ValueError, 'frozen exchange calendar'):
            cash_action_snapshot(actions, asset=ASSET, sessions=[DAY, '2020-01-03'], as_of_session=DAY)
        self.assertFalse(assembled['source_admission_granted'])
        self.assertFalse(assembled['real_forward_eligible'])

    def test_scalar_or_array_originals_fail_closed_without_raising(self):
        for component in bundle.COMPONENTS:
            with self.subTest(component=component):
                original = self.spec['evidence'][component]['receipt']
                self.spec['evidence'][component]['receipt'] = self.save(self.root/'wrong_shape.json', [])
                self.assertFalse(self.assemble()['input_contract_complete'])
                self.spec['evidence'][component]['receipt'] = original

    def test_unbounded_limits_require_explicit_null_thresholds(self):
        self.facts['execution']['limit_regime']='unbounded'; self.write_component('execution')
        self.assertFalse(self.assemble()['input_contract_complete'])
        self.facts['execution'].update(up_limit=None,down_limit=None); self.write_component('execution')
        self.assertTrue(self.assemble()['input_contract_complete'])

    def test_cash_action_requires_all_indexed_notices_and_exact_units(self):
        self.add_cash()
        result=self.assemble()
        self.assertEqual(result['corporate_actions'][0]['cash_per_unit'],'0.012345')
        self.assertFalse(result['real_forward_eligible'])
        self.facts['actions']['notices']=[]; self.write_component('actions')
        self.assertIn(('actions','indexed_action_notice_missing'),self.codes(self.assemble()))

    def test_incomplete_or_duplicate_index_cannot_certify_no_actions(self):
        for field,value in (('total_pages',2),('total_records',1),('page_number',0)):
            with self.subTest(field=field):
                old=self.facts['actions']['pages'][0][field]
                self.facts['actions']['pages'][0][field]=value; self.write_component('actions')
                self.assertFalse(self.assemble()['input_contract_complete'])
                self.facts['actions']['pages'][0][field]=old
        self.facts['actions']['coverage_start']='2020-01-01'; self.write_component('actions')
        self.assertIn(('actions','action_coverage_window_incomplete'),self.codes(self.assemble()))

    def test_share_conversion_and_unreviewed_cash_basis_are_rejected(self):
        action=self.add_cash()
        action['share_multiplier']='1.1'; self.write_component('actions')
        self.assertIn(('actions','unsupported_share_conversion_or_action'),self.codes(self.assemble()))
        action['share_multiplier']='1'; action['cash_basis']='gross'; self.write_component('actions')
        self.assertIn(('actions','net_cash_basis_required_for_account'),self.codes(self.assemble()))

    def test_cash_chronology_bad_numbers_and_nonterminating_units_block(self):
        action=self.add_cash()
        for key,value in (('ex_date',action['record_date']),('cash_amount','NaN'),('cash_amount',True),
                          ('per_units','0'),('per_units','3')):
            with self.subTest(key=key,value=value):
                old=action[key]; action[key]=value; self.write_component('actions')
                # 0.12345/3 is exact; use 0.1 for the nonterminating case.
                if key=='per_units' and value=='3':
                    action['cash_amount']='0.1'; self.write_component('actions')
                self.assertFalse(self.assemble()['input_contract_complete'])
                action[key]=old; action['cash_amount']='0.12345'

    def test_adapter_registry_requires_code_and_parsed_originals(self):
        registry=dict(bundle.DEFAULT_ADAPTERS)
        registry['fake']=bundle.SourceAdapter('identity',fabricated_boolean_adapter)
        self.spec['evidence']['identity']['adapter_id']='fake'
        self.assertIn(('identity','parsed_original_evidence_required'),self.codes(self.assemble(adapters=registry)))
        registry['fake']=True
        self.assertIn(('identity','unsupported_component_adapter'),self.codes(self.assemble(adapters=registry)))

    def test_synthetic_lineage_survives_claimed_recorded_observation(self):
        registry=dict(bundle.DEFAULT_ADAPTERS)
        registry['promote']=bundle.SourceAdapter('identity',attempted_fixture_promotion)
        self.spec['evidence']['identity']['adapter_id']='promote'
        result=self.assemble(adapters=registry)
        self.assertTrue(result['input_contract_complete'])
        self.assertEqual(result['evidence']['identity']['evidence_class'],'synthetic_only')
        self.assertEqual(result['evidence_class'],'synthetic_only')

    def test_source_changed_during_assembly_is_detected_before_success(self):
        registry=dict(bundle.DEFAULT_ADAPTERS)
        registry['change']=bundle.SourceAdapter('identity',changing_original_adapter)
        self.spec['evidence']['identity']['adapter_id']='change'
        self.assertIn(('cross_evidence','evidence_hash_mismatch'),self.codes(self.assemble(adapters=registry)))

    def test_duplicate_json_and_nonfinite_constants_do_not_enter_evidence(self):
        for raw in (b'{"asset_id":"a","asset_id":"b"}',b'{"x":NaN}'):
            path=self.root/'identity'/'original.json'; path.write_bytes(raw)
            wrapper=json.loads((self.root/'identity'/'receipt.json').read_bytes())
            wrapper['raw']=self.ref(path)
            self.spec['evidence']['identity']['receipt']=self.save(self.root/'identity'/'receipt.json',wrapper)
            self.assertFalse(self.assemble()['input_contract_complete'])


if __name__=='__main__':
    unittest.main()
