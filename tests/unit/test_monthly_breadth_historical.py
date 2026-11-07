"""Artificial source/guard fixtures only; no retained financial input is opened."""
import copy
import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from quant_robot.research import monthly_breadth_historical as h

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.code = ('src/fake_controller.py', 'src/fake_kernel.py')
        self.originals = []
        for i in range(175):
            relative = f'artificial_sources/role_{i:03}.json'
            raw = json.dumps(dict(artificial=True, ordinal=i)).encode()
            self.write(relative, raw)
            self.originals.append(dict(role=f'role_{i:03}', path=relative, sha256=h.digest(raw), bytes=len(raw)))
        manifest = dict(artifact_type='constant_mix_historical_input_manifest_v1', source_nature=h.SOURCE,
                        input_count=175, inputs=self.originals)
        self.write(h.MANIFEST, h.canonical(manifest))
        method_raw = b'{"artificial_method":true}'
        self.write(h.METHOD, method_raw)
        campaign = dict(campaign_id='quant_manager_72h_20261106', status='active', machine='office_desktop',
            task_branch=h.BRANCH, delivery_deadline='2026-11-09T16:21:39Z',
            old_consumed_scopes_remain_closed=True, holdout_unsealing_authorized=False, live_boundary_allowed=False)
        self.write(h.PM_INPUTS['campaign'], h.canonical(campaign))
        self.protocols = [f'protocol/{i}.md' for i in range(7)]
        self.write(h.PM_INPUTS['pm_policy'], h.canonical(dict(required_reading=[dict(path=p) for p in self.protocols])))
        for key in ('workstations', 'family_scheduler'):
            self.write(h.PM_INPUTS[key], b'{"artificial":true}')
        for path in self.protocols:
            self.write(path, b'artificial\r\nprotocol\r\n')
        for path in self.code:
            self.write(path, b'# artificial code pin\n')
        patches = [
            mock.patch.object(h, 'CODE_FILES', self.code),
            mock.patch.object(h, 'MANIFEST_SHA', h.digest(h.canonical(manifest))),
            mock.patch.object(h, 'METHOD_SHA', h.digest(method_raw)),
            mock.patch.object(h.retained, 'runtime_environment', return_value=dict(python='3.12.13', artificial=True)),
            mock.patch.object(h, '_now', return_value=NOW),
            mock.patch.object(h, '_branch', return_value=h.BRANCH),
            mock.patch.object(h, '_execution_modules'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.packet = h.build_registration(self.root, method_sha256=h.METHOD_SHA, study_number=999)
        self.authorize()

    def write(self, path, raw):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)

    def authorize(self):
        self.write(h.REGISTRATION, h.canonical(self.packet))
        for path, reviewer in [(h.MANAGER_REVIEW, 'quant_manager_72h'), (h.ROOT_REVIEW, 'root')]:
            r = dict(artifact_type='monthly_breadth_exact_review_v1', status='accepted_for_one_conditional_monthly_breadth',
                reviewer=reviewer, mode=h.MODE, registration_sha256=self.packet['registration_sha256'],
                method_sha256=h.METHOD_SHA, financial_execution_authorized=True, qualified=False, real_forward=0)
            self.write(path, h.canonical(r))
        self.release = dict(artifact_type='monthly_breadth_release_v1', status='authorized_once', mode=h.MODE,
            registration=h._ref(self.root, h.REGISTRATION), manager_review=h._ref(self.root, h.MANAGER_REVIEW),
            root_review=h._ref(self.root, h.ROOT_REVIEW), valid_from='2026-11-07T11:00:00Z', expires_at='2026-11-07T13:00:00Z')
        self.write(h.RELEASE, h.canonical(self.release))

    def gate(self):
        return dict(status='ready', blockers=[], generated_at=NOW.isoformat(), primary_market='CN_ETF',
            selected=dict(machine='office_desktop', task='factor_review', branch=h.BRANCH, current_branch=h.BRANCH),
            safety=dict(factor_batch_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False,
                        constant_mix_allowed=False, future_source_observation_allowed=False),
            required_reading=[dict(path=p, status='read', sha256=h.digest(b'artificial\nprotocol\n')) for p in self.protocols])

    def execute(self, gate=None):
        return h.execute(self.root, expected_registration_sha256=self.packet['registration_sha256'],
                         gate_supplier=gate or self.gate)

    def test_exact_original_roles_and_method_are_not_replaceable(self):
        self.assertEqual(len(self.packet['inputs']), 180)
        for change in ('role', 'method', 'code'):
            packet = copy.deepcopy(self.packet)
            if change == 'role':
                packet['inputs']['role_000'] = packet['inputs']['role_001']
            elif change == 'method':
                packet['inputs']['monthly_method']['sha256'] = '0' * 64
            else:
                packet['implementation']['src/fake_controller.py'] = packet['implementation']['src/fake_kernel.py']
            packet['registration_sha256'] = h.digest(h.canonical({k:v for k,v in packet.items() if k!='registration_sha256'}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                h.validate_registration(self.root, packet)
        self.assertFalse((self.root / h.DIRECTORY / 'attempt_claim.json').exists())

    def test_stale_pm_or_open_other_scope_or_raw_hash_rejects_before_claim(self):
        for change in ('stale', 'old_scope_open', 'raw_hash'):
            gate = self.gate()
            if change == 'stale': gate['generated_at'] = '2026-11-07T11:00:00Z'
            elif change == 'old_scope_open': gate['safety']['constant_mix_allowed'] = True
            else: gate['required_reading'][0]['sha256'] = h.digest(b'artificial\r\nprotocol\r\n')
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.execute(lambda:gate)
            self.assertFalse((self.root / h.DIRECTORY / 'attempt_claim.json').exists())

    def test_review_version_and_release_expiry_rejected(self):
        r = h._json((self.root / h.ROOT_REVIEW).read_bytes())
        r['registration_sha256'] = '0' * 64
        self.write(h.ROOT_REVIEW, h.canonical(r))
        self.release['root_review'] = h._ref(self.root, h.ROOT_REVIEW)
        self.write(h.RELEASE, h.canonical(self.release))
        with self.assertRaisesRegex(ValueError, 'acceptance'): self.execute()
        self.authorize()
        self.release['expires_at'] = NOW.isoformat()
        self.write(h.RELEASE, h.canonical(self.release))
        with self.assertRaisesRegex(ValueError, 'expired'): self.execute()

    def test_input_change_during_gate_has_no_claim(self):
        def changed_gate():
            self.write('artificial_sources/role_000.json', b'changed')
            return self.gate()
        with self.assertRaises(ValueError): self.execute(changed_gate)
        self.assertFalse((self.root / h.DIRECTORY / 'attempt_claim.json').exists())

    def test_claim_precedes_marker_failure_consumed_no_second_dispatch(self):
        def failed_load(claim):
            self.assertTrue((self.root / h.DIRECTORY / 'attempt_claim.json').exists())
            self.assertFalse((self.root / h.DIRECTORY / 'financial_decode_started.json').exists())
            claim.begin_financial_decode()
            self.assertTrue((self.root / h.DIRECTORY / 'financial_decode_started.json').exists())
            raise ValueError('artificial numeric failure')
        with mock.patch.object(h, 'load_claimed_inputs', side_effect=failed_load) as load:
            with self.assertRaisesRegex(ValueError, 'artificial numeric'): self.execute()
            with self.assertRaisesRegex(ValueError, 'reserved or consumed'): self.execute()
        self.assertEqual(load.call_count, 1)
        o = h._json((self.root / h.DIRECTORY / 'outcome.json').read_bytes())
        self.assertEqual(o['status'], 'failed_consumed')
        self.assertTrue(o['financial_decode_started'] and o['research_study_consumed'])
        self.assertFalse(o['historical_returns_computed'])

    def test_claimed_predecode_failure_is_reserved_not_financial_consumed(self):
        with mock.patch.object(h, 'load_claimed_inputs', side_effect=ValueError('artificial metadata failure')):
            with self.assertRaisesRegex(ValueError, 'metadata'): self.execute()
        o = h._json((self.root / h.DIRECTORY / 'outcome.json').read_bytes())
        self.assertEqual(o['status'], 'failed_consumed')
        self.assertFalse(o['financial_decode_started'] or o['research_study_consumed'])
        with self.assertRaisesRegex(ValueError, 'reserved or consumed'): self.execute()

    def test_claim_and_release_mutation_detected_before_numeric(self):
        def mutated(claim):
            self.write(h.DIRECTORY + '/attempt_claim.json', b'changed')
            claim.begin_financial_decode()
        with mock.patch.object(h, 'load_claimed_inputs', side_effect=mutated):
            with self.assertRaisesRegex(ValueError, 'Frozen file changed'): self.execute()
        self.assertFalse((self.root / h.DIRECTORY / 'financial_decode_started.json').exists())

    def test_public_loader_cannot_accept_old_or_artificial_claim(self):
        with mock.patch.object(h.normalizer, '_load_core') as old:
            with self.assertRaisesRegex(ValueError, 'new production claim'): h.load_claimed_inputs(object())
        old.assert_not_called()


class PersistenceTests(unittest.TestCase):
    def test_prewrite_expected_bytes_not_postwrite_new_baseline(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            original = h.normalizer.admission.write_exclusive_json
            def tamper(path, value):
                original(path, value)
                Path(path).write_bytes(Path(path).read_bytes().replace(b'123', b'321'))
            with mock.patch.object(h.normalizer.admission, 'write_exclusive_json', side_effect=tamper):
                with self.assertRaisesRegex(ValueError, 'pre-write intent'):
                    h._persist(root, root/'result.json', dict(artificial='123'))


def artificial_historical_fixture():
    """Invented weekday calendar and values in real-year shape; not real sessions."""
    from quant_robot.research import monthly_breadth as k
    dates = []
    d = date(2013, 12, 5)
    while d <= date(2024, 1, 2):
        if d.weekday() < 5 and (d.month, d.day) != (1, 1) and d != date(2015, 1, 2):
            dates.append(d.isoformat())
        d += timedelta(days=1)
    months = {}
    for d in dates[:-1]:
        months[d[:7]] = d
    ends = list(months.values())
    decisions = [dates.index(d) for d in ends[12:-1]]
    bars = {a: [] for a in h.ASSETS}
    with localcontext(k.CONTEXT):
        for i, d in enumerate(dates):
            month = (int(d[:4])-2013)*12+int(d[5:7])-12
            wave = Decimal(month % 24)/20
            for asset, price in zip(h.ASSETS, (Decimal(10)+wave, Decimal(20)-wave)):
                row = dict(open=str(price), close=str(price), volume='1000000',
                           suspended=False, buy_blocked=False, sell_blocked=False)
                if i == len(dates)-1:
                    row.update(close=None, terminal_close_not_observed=True)
                bars[asset].append(row)
    actions = []
    for year in range(2014, 2024):
        indices = [i for i,d in enumerate(dates) if d.startswith(str(year)+'-01')]
        known, record, ex, pay = indices[5:9]
        actions.append(dict(event_id=f'artificial_distribution_{year}', asset=h.ASSETS[0],
            known_index=known, record_index=record, ex_index=ex, pay_index=pay,
            cash_per_share='0.01', share_multiplier='1'))
    return dict(artifact_type='admitted_monthly_breadth_fixture_v1',
        source_nature='test_artificial_values_true_calendar', constructed_from_market_data=False,
        assets=list(h.ASSETS), dates=dates, bars=bars, actions=actions, actions_complete=True,
        terminal_index=len(dates)-1, month_end_sessions=ends,
        first_signal_index=dates.index(ends[12]), monthly_decision_indices=decisions,
        event_indices=[i+1 for i in decisions])


class ArtificialControllerTests(unittest.TestCase):
    def test_month_end_metadata_bounds_and_missing_month(self):
        fixture = artificial_historical_fixture()
        dates = fixture['dates']
        class Claim:
            def read(self, role):
                selected = [d for d in dates if (d<'2015') == (role=='retained_old_calendar')]
                if role == 'retained_calendar':
                    # Calendar metadata extends beyond the price cutoff. Jan2 is
                    # not misdeclared a completed January merely due to slicing.
                    selected += ['2024-01-03', '2024-01-31']
                return ('date,is_open\n'+'\n'.join(d+',1' for d in selected)+'\n').encode()
        ends = h._month_ends(Claim(), dates)
        self.assertEqual(ends, fixture['month_end_sessions'])
        bad = [d for d in dates if not d.startswith('2018-07')]
        with self.assertRaisesRegex(ValueError, 'calendar'): h._month_ends(Claim(), bad)

    def test_complete_28_artificial_saved_ledgers(self):
        from quant_robot.research import monthly_breadth as k
        retained = os.environ.get('MONTHLY_BREADTH_ARTIFICIAL_DEMO')
        if retained:
            root = Path(retained).resolve()
            root.mkdir(parents=True, exist_ok=False)
        else:
            temporary = TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            root = Path(temporary.name).resolve()
        fixture = artificial_historical_fixture()
        provenance = dict(test_injected_values=True, invented_weekday_calendar_not_official_sessions=True,
                          original_market_files_read=False, research_count_delta=0)
        context = k._KnownHistoryContext(h.ASSETS, fixture['source_nature'], 'a'*64,
                                         k.digest(fixture), k.digest(provenance), test_values=True)
        class Claim:
            packet = dict(registration_sha256='a'*64, policy=dict(study_number=999))
            guard_count = 0
            def guard(self, phase, identity): self.guard_count += 1
        claim = Claim()
        claim.root = root
        data = h.LoadedInputs(fixture, provenance, context)
        result = h._run_loaded(claim, data)
        h._final_artifacts(root, result)
        self.assertEqual(len(result['accounts']), 28)
        self.assertEqual(result['artifact_type'], 'artificial_true_calendar_monthly_breadth_matrix_v1')
        self.assertTrue(result['test_injected_values'])
        self.assertFalse(result['historical_returns_computed'])
        self.assertEqual(result['real_forward'], 0)
        self.assertEqual(Decimal(result['accounts']['cash']['summary']['total_commission']), Decimal(0))
        result_ref = h._persist(root, root/h.DIRECTORY/'result.json', result)
        h._persist(root, root/'artificial_completion.json', dict(status='completed_artificial_28', result=result_ref,
            core_sha256=h.retained.file_digest(k.__file__), controller_sha256=h.retained.file_digest(h.__file__),
            test_sha256=h.retained.file_digest(__file__), official_calendar_used=False, raw_market_files_read=False,
            financial_study_consumed=False, research_count_delta=0, guard_calls=claim.guard_count))


if __name__ == '__main__':
    unittest.main()
