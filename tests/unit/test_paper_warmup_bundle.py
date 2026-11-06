"""Entirely artificial original files; no market data, credentials or network."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_warmup_bundle as warmup


ASSET = 'CN_ETF_XSHG_510300'


def promoted_fixture(context, ref):
    value = warmup._fixture(context, ref)
    return daily.Evidence(value.facts, value.request_started_at,
                          value.received_at, 'recorded_observation')


def byte_reader_test_adapter(context, ref):
    """Attempt a lineage upgrade while parsing the marked raw bytes directly."""
    wrapper = context.read_json(ref)
    original = json.loads(context.read_bytes(wrapper['raw']))
    return daily.Evidence(original.get('facts', original), wrapper['request_started_at'],
                          wrapper['received_at'], 'recorded_observation')


class PaperWarmupBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.make_prefix()

    def save(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')
        return {'path': name, 'sha256': sha256(path.read_bytes()).hexdigest()}

    def evidence(self, kind, facts, *, label=None, received=None, requested=None):
        label = label or kind
        raw = self.save(label + '/original.json', facts)
        receipt = self.save(label + '/receipt.json', dict(
            artifact_type=warmup.FIXTURE_TYPE, component=kind, raw=raw,
            request_started_at=requested or self.received,
            received_at=received or self.received))
        return dict(adapter_id='warmup_synthetic_' + kind + '_v1', receipt=receipt)

    def make_prefix(self, count=81, *, direction=1, zero_volume=False, flat=False):
        days, day = [], date(2020, 1, 2)
        while len(days) < count + 4:
            if day.weekday() < 5:
                days.append(day.isoformat())
            day += timedelta(days=1)
        self.days = days
        self.received = days[count-1] + 'T08:00:00Z'
        self.as_of = days[count-1] + 'T09:00:00Z'
        self.calendar = dict(exchange='XSHG', sessions=[dict(date=d,
            decision_cutoff_at=d+'T01:15:00Z', open_at=d+'T01:25:00Z',
            auction_close_at=d+'T07:00:00Z', daily_observation_not_before=d+'T07:30:00Z')
            for d in days])
        self.identity = dict(asset_id=ASSET, instrument_type='ETF', currency='CNY',
            price_unit='CNY_per_fund_unit', volume_unit='fund_units', amount_unit='CNY',
            listing_date='2010-01-01', delisting_date=None,
            valid_from=days[count-1], valid_through=days[-1])
        self.actions = dict(asset_id=ASSET, coverage_start=days[0], coverage_end=days[count-1],
            pages=[dict(page_number=1, total_pages=1, total_records=0, records=[])], notices=[])
        self.spec = dict(artifact_type=warmup.SPEC_TYPE, asset_id=ASSET,
            as_of=self.as_of, first_session=days[count], seed_start=days[0],
            seed_policy=warmup.SEED_POLICY, price_basis='raw_unadjusted',
            components=['sma20_trend'], sessions=[], evidence={})
        for kind in ('calendar', 'identity', 'actions'):
            self.spec['evidence'][kind] = self.evidence(kind, getattr(self, kind))
        for i, d in enumerate(days[:count]):
            value = Decimal('20') + (Decimal(i) / 100 * direction if not flat else 0)
            bar = dict(asset_id=ASSET, date=d, open=str(value), close=str(value),
                high=str(value+Decimal('.1')), low=str(value-Decimal('.1')),
                volume='0' if zero_volume else '10000', amount='0' if zero_volume else '200000')
            execution = dict(asset_id=ASSET, session_date=d, suspended=False,
                limit_regime='bounded', up_limit='40', down_limit='1')
            self.spec['sessions'].append(dict(session_date=d,
                price=self.evidence('price', {'bar': bar}, label=d+'/price'),
                execution=self.evidence('execution', execution, label=d+'/execution')))
        self.bind()

    def bind(self, **kwargs):
        self.spec['implementation_binding'] = warmup.runtime_binding(**kwargs)

    def assemble(self, **kwargs):
        return warmup.build_warmup_bundle(self.spec, evidence_root=self.root, **kwargs)

    def codes(self, result):
        return {item['code'] for item in result['blockers']}

    def replace_receipt(self, entry, **changes):
        path = entry['receipt']['path']
        receipt = json.loads((self.root/path).read_bytes())
        receipt.update(changes)
        entry['receipt'] = self.save(path, receipt)

    def replace_facts(self, entry, change):
        receipt = json.loads((self.root/entry['receipt']['path']).read_bytes())
        facts = json.loads((self.root/receipt['raw']['path']).read_bytes())
        change(facts)
        receipt['raw'] = self.save(receipt['raw']['path'], facts)
        entry['receipt'] = self.save(entry['receipt']['path'], receipt)

    def test_81_session_original_prefix_ready_true_and_never_admitted(self):
        self.spec['components'] = ['sma20_trend', 'ema21_55_fibonacci', 'amihud20_below_prior60']
        result = self.assemble()
        self.assertEqual(result['blockers'], [])
        self.assertTrue(result['input_contract_complete'])
        self.assertTrue(result['warmup_ready'])
        self.assertTrue(result['feature_state']['known'])
        self.assertTrue(result['feature_state']['desired'])
        self.assertEqual(result['feature_state']['unknown_components'], [])
        self.assertGreater(result['budget_used']['documents'], 128)
        self.assertEqual(len(result['bars']), 81)
        self.assertEqual(result['seed']['bars_used'], 81)
        self.assertEqual(result['evidence_class'], 'synthetic_only')
        for key in ('source_admission_granted', 'candidate_qualification_granted',
                    'real_forward_eligible', 'historical_point_in_time_certified'):
            self.assertFalse(result[key])
        self.assertEqual(result['real_forward_days_added'], 0)

    def test_short_prefix_reports_unknown_and_not_ready(self):
        self.make_prefix(10)
        result = self.assemble()
        self.assertTrue(result['input_contract_complete'])
        self.assertFalse(result['warmup_ready'])
        self.assertFalse(result['feature_state']['known'])
        self.assertIsNone(result['feature_state']['desired'])
        self.assertEqual(result['feature_state']['unknown_components'], ['sma20_trend'])

    def test_sufficient_but_zero_volume_or_degenerate_is_unknown(self):
        for component, zero, flat in [('cmf20_positive', True, False),
                                      ('cci20_positive', False, True)]:
            with self.subTest(component=component):
                self.make_prefix(81, zero_volume=zero, flat=flat)
                self.spec['components'] = [component]
                result = self.assemble()
                self.assertTrue(result['input_contract_complete'])
                self.assertFalse(result['warmup_ready'])
                self.assertEqual(result['feature_state']['unknown_components'], [component])

    def test_known_false_is_ready_and_distinct_from_unknown(self):
        self.make_prefix(81, direction=-1)
        result = self.assemble()
        self.assertTrue(result['warmup_ready'])
        self.assertTrue(result['feature_state']['known'])
        self.assertIs(result['feature_state']['desired'], False)

    def test_missing_duplicate_reordered_and_wrong_asset_rejected(self):
        original = deepcopy(self.spec)
        for case in ('missing', 'duplicate', 'reordered', 'asset'):
            self.spec = deepcopy(original)
            if case == 'missing':
                self.spec['sessions'].pop(30)
            elif case == 'duplicate':
                self.spec['sessions'][30] = deepcopy(self.spec['sessions'][29])
            elif case == 'reordered':
                self.spec['sessions'][0:2] = reversed(self.spec['sessions'][0:2])
            else:
                self.replace_facts(self.spec['sessions'][0]['price'],
                    lambda x: x['bar'].update(asset_id='CN_ETF_XSHE_159919'))
            with self.subTest(case=case):
                self.assertFalse(self.assemble()['input_contract_complete'])

    def test_actual_times_not_backdated_and_after_asof_rejected(self):
        first = self.spec['sessions'][0]['price']
        self.replace_receipt(first, received_at=self.days[-1]+'T08:00:00Z')
        self.assertIn('evidence_received_after_as_of', self.codes(self.assemble()))

    def test_old_daily_bundle_misses_deadline_current_asof_warmup_accepts(self):
        first = self.spec['sessions'][0]
        registry = {key: value for key, value in warmup.DEFAULT_ADAPTERS.items()}
        daily_spec = dict(artifact_type=daily.SPEC_TYPE, asset_id=ASSET,
            session_date=first['session_date'], window_start=self.spec['seed_start'],
            evidence={**self.spec['evidence'], 'price':first['price'], 'execution':first['execution']})
        identity = deepcopy(self.identity)
        identity['valid_from'] = self.spec['seed_start']
        daily_spec['evidence']['identity'] = self.evidence('identity', identity, label='daily_identity')
        failed = daily.build_source_bundle(daily_spec, evidence_root=self.root,
            decision_at=self.as_of, adapters=registry)
        self.assertIn('decision_at_or_after_next_opening_auction_cutoff', self.codes(failed))
        result = self.assemble()
        self.assertTrue(result['warmup_ready'])
        self.assertEqual(result['input_available_at'], self.received)
        self.assertEqual(result['as_of'], self.as_of)
        self.assertFalse(result['historical_point_in_time_certified'])

    def test_original_changed_after_reference_and_during_assembly(self):
        entry = self.spec['sessions'][0]['price']
        path = self.root/entry['receipt']['path']
        original = path.read_bytes()
        path.write_bytes(b'{}')
        self.assertIn('evidence_hash_mismatch', self.codes(self.assemble()))
        path.write_bytes(original)
        original_feature = warmup.feature_frame
        def mutate(bars, actions):
            frame = original_feature(bars, actions)
            path.write_bytes(b'{}')
            return frame
        with patch.object(warmup, 'feature_frame', side_effect=mutate):
            self.assertIn('evidence_hash_mismatch', self.codes(self.assemble()))

    def test_code_dependency_or_parameter_change_invalidates_frozen_binding(self):
        registry = dict(warmup.DEFAULT_ADAPTERS)
        dependencies = {key: () for key in registry}
        dependency = self.root/'adapter_dependency.py'
        dependency.write_text('VALUE = 1\n', encoding='utf-8')
        key = self.spec['sessions'][0]['price']['adapter_id']
        dependencies[key] = (dependency,)
        self.bind(adapters=registry, adapter_dependencies=dependencies)
        dependency.write_text('VALUE = 2\n', encoding='utf-8')
        self.assertIn('implementation_binding_mismatch', self.codes(self.assemble(
            adapters=registry, adapter_dependencies=dependencies)))
        self.bind(adapters=registry, adapter_dependencies=dependencies)
        registry[key] = daily.SourceAdapter('price', warmup._fixture, {'changed':True})
        self.assertIn('implementation_binding_mismatch', self.codes(self.assemble(
            adapters=registry, adapter_dependencies=dependencies)))

    def test_json_flags_cannot_promote_and_custom_parser_cannot_erase_taint(self):
        self.spec['production_ready'] = True
        self.assertFalse(self.assemble()['input_contract_complete'])
        self.spec.pop('production_ready')
        registry = {key: daily.SourceAdapter(value.component, promoted_fixture)
                    for key, value in warmup.DEFAULT_ADAPTERS.items()}
        dependencies = {key:(Path(warmup.__file__),) for key in registry}
        self.bind(adapters=registry, adapter_dependencies=dependencies)
        result = self.assemble(adapters=registry, adapter_dependencies=dependencies)
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['evidence_class'], 'synthetic_only')
        self.assertFalse(result['real_forward_eligible'])

    def test_complete_cash_action_and_coverage_and_clock(self):
        event = dict(event_id='artificial-cash', asset_id=ASSET, kind='cash_dividend',
            announced_date=self.days[30], record_date=self.days[40], ex_date=self.days[41],
            pay_date=self.days[42], cash_amount='0.125', per_units='10',
            share_multiplier='1', cash_basis='net')
        self.actions['pages'][0].update(total_records=1,
            records=[dict(event_id=event['event_id'], kind='cash_dividend')])
        self.actions['notices'] = [event]
        self.spec['evidence']['actions'] = self.evidence('actions', self.actions)
        result = self.assemble()
        self.assertTrue(result['warmup_ready'])
        self.assertEqual(result['actions'][0]['cash_per_unit'], '0.0125')
        original = deepcopy(self.actions)
        for case in ('missing_notice', 'coverage', 'receipt_before_notice', 'future_pay'):
            self.actions = deepcopy(original)
            if case == 'missing_notice': self.actions['notices'] = []
            if case == 'coverage': self.actions['coverage_start'] = self.days[1]
            if case == 'future_pay': self.actions['notices'][0]['pay_date'] = '2030-01-02'
            received = self.days[0]+'T08:00:00Z' if case == 'receipt_before_notice' else self.received
            self.spec['evidence']['actions'] = self.evidence('actions', self.actions,
                requested=received, received=received)
            with self.subTest(case=case):
                self.assertFalse(self.assemble()['input_contract_complete'])

    def test_budget_document_total_per_file_and_session_limits(self):
        with patch.object(warmup, 'MAX_PREFIX_DOCUMENTS', 100):
            self.assertIn('prefix_document_budget_exceeded', self.codes(self.assemble()))
        with patch.object(warmup, 'MAX_PREFIX_BYTES', 100):
            self.assertIn('prefix_byte_budget_exceeded', self.codes(self.assemble()))
        entry = self.spec['sessions'][0]['price']
        path = self.root/entry['receipt']['path']
        path.write_bytes(b' ' * (daily.MAX_DOCUMENT_BYTES+1))
        entry['receipt']['sha256'] = sha256(path.read_bytes()).hexdigest()
        self.assertIn('document_byte_budget_exceeded', self.codes(self.assemble()))
        self.spec['sessions'] = self.spec['sessions'] * 7
        self.assertIn('bounded_warmup_sessions_required', self.codes(self.assemble()))

    def test_pre_execution_window_and_final_price_request_boundary(self):
        original = self.spec['as_of']
        for moment in (self.days[80]+'T07:00:00Z', self.days[81]+'T01:15:00Z',
                       self.days[81]+'T02:00:00Z'):
            self.spec['as_of'] = moment
            with self.subTest(moment=moment):
                self.assertFalse(self.assemble()['input_contract_complete'])
        self.spec['as_of'] = original
        self.replace_receipt(self.spec['sessions'][0]['price'],
            request_started_at=self.days[0]+'T07:29:59Z')
        self.assertIn('price_requested_before_daily_observation_window', self.codes(self.assemble()))

    def test_units_identity_expiry_and_execution_unknown_do_not_default(self):
        original = deepcopy(self.identity)
        for case in ('units', 'expired', 'delisted'):
            identity = deepcopy(original)
            if case == 'units': identity['volume_unit'] = 'lots'
            if case == 'expired': identity['valid_through'] = self.days[79]
            if case == 'delisted': identity['delisting_date'] = self.days[81]
            self.spec['evidence']['identity'] = self.evidence('identity', identity)
            with self.subTest(case=case):
                self.assertFalse(self.assemble()['input_contract_complete'])
        self.spec['evidence']['identity'] = self.evidence('identity', original)
        entry = self.spec['sessions'][0]['execution']
        for value in (None, True):
            self.replace_facts(entry, lambda x:x.update(suspended=value))
            with self.subTest(suspended=value):
                self.assertFalse(self.assemble()['input_contract_complete'])

    def test_empty_action_coverage_cannot_be_dated_after_actual_receipt(self):
        previous = self.days[79]+'T08:00:00Z'
        self.replace_receipt(self.spec['evidence']['actions'],
            request_started_at=previous, received_at=previous)
        self.assertIn('action_coverage_after_receipt_date', self.codes(self.assemble()))

    def test_dependency_and_parameter_mutation_during_feature_work_rejected(self):
        registry = dict(warmup.DEFAULT_ADAPTERS)
        key = self.spec['sessions'][0]['price']['adapter_id']
        parameters = {'units':'raw'}
        registry[key] = daily.SourceAdapter('price', warmup._fixture, parameters)
        dependencies = {name:() for name in registry}
        dependency = self.root/'during_assembly.py'
        dependencies[key] = (dependency,)
        feature = warmup.feature_frame
        for case in ('dependency', 'parameters'):
            dependency.write_text('VALUE = 1\n', encoding='utf-8')
            parameters['units'] = 'raw'
            self.bind(adapters=registry, adapter_dependencies=dependencies)
            def mutate(bars, actions):
                result = feature(bars, actions)
                if case == 'dependency':
                    dependency.write_text('VALUE = 2\n', encoding='utf-8')
                else:
                    parameters['units'] = 'changed'
                return result
            with self.subTest(case=case), patch.object(warmup, 'feature_frame', side_effect=mutate):
                result = self.assemble(adapters=registry, adapter_dependencies=dependencies)
                self.assertIn('implementation_changed_during_assembly', self.codes(result))

    def test_prefix_seed_and_components_are_frozen_not_implicit_tail(self):
        before = self.assemble()
        self.spec['components'] = ['ema21_55_fibonacci']
        changed = self.assemble()
        self.assertNotEqual(before['prefix_sha256'], changed['prefix_sha256'])
        self.assertNotEqual(before['specification_sha256'], changed['specification_sha256'])
        self.assertEqual(before['input_sha256'], changed['input_sha256'])
        self.spec['sessions'] = self.spec['sessions'][1:]
        self.spec['seed_start'] = self.days[1]
        smaller = self.assemble()
        self.assertTrue(smaller['input_contract_complete'])
        self.assertNotEqual(before['prefix_sha256'], smaller['prefix_sha256'])
        self.assertEqual(smaller['seed']['bars_used'], 80)
        self.assertFalse(smaller['seed']['history_equivalence_claimed'])

    def test_custom_registry_requires_dependencies_and_no_production_default(self):
        with self.assertRaisesRegex(daily.BundleError, 'explicit_adapter_dependencies_required'):
            warmup.runtime_binding(adapters=dict(warmup.DEFAULT_ADAPTERS))
        self.spec['sessions'][0]['price']['adapter_id'] = 'tushare_scoped_fund_daily_v1'
        self.assertIn('unsupported_component_adapter', self.codes(self.assemble()))

    def test_single_marked_original_taints_bytes_reader_and_entire_bundle(self):
        entries = list(self.spec['evidence'].values()) + [entry for row in self.spec['sessions']
            for entry in (row['price'], row['execution'])]
        for entry in entries:
            self.replace_receipt(entry, artifact_type='test_receipt_unmarked')
        marked = self.spec['sessions'][0]['price']
        receipt = json.loads((self.root/marked['receipt']['path']).read_bytes())
        facts = json.loads((self.root/receipt['raw']['path']).read_bytes())
        receipt['raw'] = self.save(receipt['raw']['path'],
            {'artifact_type':'single_synthetic_original_v1', 'facts':facts})
        marked['receipt'] = self.save(marked['receipt']['path'], receipt)
        registry = {name:daily.SourceAdapter(adapter.component, byte_reader_test_adapter)
                    for name, adapter in warmup.DEFAULT_ADAPTERS.items()}
        dependencies = {name:() for name in registry}
        self.bind(adapters=registry, adapter_dependencies=dependencies)
        result = self.assemble(adapters=registry, adapter_dependencies=dependencies)
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['evidence_class'], 'synthetic_only')
        self.assertEqual(result['evidence'][self.days[0]+'/price']['evidence_class'], 'synthetic_only')
        self.assertFalse(result['source_admission_granted'])


if __name__ == '__main__':
    unittest.main()
