"""Synthetic acceptance checks; temporary receipts are never project qualifications."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.paper.daily_recovery import RECOVERY_40


def save(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return forward.file_reference(path)


class FrozenForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.journal = self.root / 'journal'
        days = []
        current = datetime(2020, 1, 1, tzinfo=timezone.utc)
        while len(days) < 115:
            if current.weekday() < 5:
                days.append(current.date().isoformat())
            current += timedelta(days=1)
        self.days = days
        self.schedule = [dict(date=day, open_at=day+'T01:30:00Z', close_at=day+'T07:00:00Z') for day in days]
        self.bars = [dict(asset_id='SYNTHETIC_ETF', date=day, open=str(5+i*.001),
                          high=str(5+i*.001), low=str(5+i*.001), close=str(5+i*.001),
                          volume='10000000', amount='50000000',
                          suspended=False, limit_up=False, limit_down=False)
                     for i, day in enumerate(days)]
        self.config = AllocationConfig(max_position_cny=10000, max_position_fraction=1,
                                       max_drawdown=.4, execution_price_field='open', slippage_bps=0)
        warmup = dict(bars=self.bars[:80], actions=[], corporate_actions_complete=True,
                      generated_at=days[79]+'T07:00:01Z', available_at=days[79]+'T07:00:02Z',
                      acquired_at=days[79]+'T07:01:00Z')
        self.manifest = dict(artifact_type=forward.MANIFEST_TYPE, candidate_id='SYNTHETIC_ONLY',
            asset_id='SYNTHETIC_ETF', first_session=days[80], runtime_binding=forward.runtime_binding(),
            account_config=asdict(self.config), daily_recovery=RECOVERY_40,
            strategy=dict(adapter='existing_predicate_and_v1', components=['sma20_trend'], cadence=1),
            source_contract=dict(source_id='synthetic-fixture', maximum_receive_delay_seconds=21600,
                                 timestamp_basis='provider_generated_and_available_utc'),
            calendar=save(self.root/'calendar.json', self.schedule),
            warmup=save(self.root/'warmup.json', warmup))
        self.manifest_path = self.root/'manifest.json'
        self.qual_path = self.root/'qualification.json'
        self.evidence = save(self.root/'test_evidence.json',
                             {'fixture_only': True, 'never_real_research_evidence': True})
        self.freeze()

    def freeze(self):
        ref = save(self.manifest_path, self.manifest)
        self.qualification = dict(artifact_type=forward.QUALIFICATION_TYPE,
            manifest_sha256=ref['sha256'], verdict='qualified',
            review_role='independent_qualification_review', evidence_class='synthetic_test_only',
            issued_at=self.days[79]+'T07:10:00Z', supporting_evidence=[self.evidence],
            gates={name: True for name in forward.GATES})
        save(self.qual_path, self.qualification)

    def activate(self, mode='synthetic'):
        return forward.activate(self.journal, self.manifest_path, self.qual_path, mode=mode,
                                now=self.days[79]+'T08:00:00Z')

    def packet(self, index):
        return dict(session_date=self.days[index], source_id='synthetic-fixture',
                    generated_at=self.days[index]+'T07:00:01Z',
                    available_at=self.days[index]+'T07:01:00Z',
                    acquired_at=self.days[index]+'T07:02:00Z', bar=self.bars[index],
                    corporate_actions_complete=True, corporate_actions=[])

    def day(self, index):
        decision = forward.decide(self.journal, now=self.days[index]+'T01:00:00Z')
        observation = forward.observe(self.journal, self.packet(index), now=self.days[index]+'T08:00:00Z')
        return decision, observation

    def test_absent_candidate_is_blocked_without_creating_directory(self):
        result = forward.status(self.journal)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['real_forward_days'], 0)
        self.assertFalse(self.journal.exists())

    def test_synthetic_qualification_cannot_be_used_for_real_forward(self):
        with self.assertRaisesRegex(ValueError, 'Synthetic qualification'):
            forward.activate(self.journal, self.manifest_path, self.qual_path, mode='forward')
        with self.assertRaisesRegex(ValueError, 'caller supplied clock'):
            forward.activate(self.journal, self.manifest_path, self.qual_path,
                             mode='forward', now=self.days[79]+'T08:00:00Z')

    def test_claimed_provider_and_clocks_cannot_replace_raw_source_adapter(self):
        # Even a fixture pretending to be an independent research receipt cannot
        # open the real-source gate. No such receipt survives this temporary test.
        self.qualification['evidence_class'] = 'reviewed_research'
        save(self.qual_path, self.qualification)
        with self.assertRaisesRegex(ValueError, 'verified_raw_source_adapter_missing'):
            forward.activate(self.journal, self.manifest_path, self.qual_path, mode='forward')
        self.assertFalse(self.journal.exists())
        self.assertEqual(forward.status(self.journal)['real_forward_days'], 0)

    def test_external_qualification_and_code_and_source_are_bound(self):
        for gate in forward.GATES:
            broken = deepcopy(self.qualification)
            broken['gates'][gate] = False
            save(self.qual_path, broken)
            with self.assertRaisesRegex(ValueError, 'Independent qualified'):
                self.activate()
        save(self.qual_path, self.qualification)
        self.manifest['runtime_binding']['python'] = 'different'
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'code or environment'):
            self.activate()
        self.manifest['runtime_binding'] = forward.runtime_binding()
        self.freeze()
        (self.root/'warmup.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.activate()

    def test_open_cycle_survives_daily_mark_and_restart_and_duplicate(self):
        self.activate()
        _, first = self.day(80)
        self.assertTrue(first['payload']['account']['positions'])
        self.assertFalse(first['payload']['account']['risk']['terminal_settled'])
        self.assertEqual([f['side'] for f in first['payload']['account']['fills']], ['buy'])
        second_decision = forward.decide(self.journal, now=self.days[81]+'T01:00:00Z')
        self.assertEqual(forward.decide(self.journal, now=self.days[81]+'T01:05:00Z'), second_decision)
        second = forward.observe(self.journal, self.packet(81), now=self.days[81]+'T08:00:00Z')
        repeated = forward.observe(self.journal, self.packet(81), now=self.days[82]+'T08:00:00Z')
        self.assertEqual(second, repeated)
        self.assertEqual(len(list(self.journal.glob('*.json'))), 5)
        account = second['payload']['account']
        expected = run_allocation_account(self.bars[:82], sessions=self.days[:82],
            assets=['SYNTHETIC_ETF'], cycles=[dict(cycle_id='forward_episode_000001',
            entry_date=self.days[80], exit_date=None)], actions=[], config=self.config,
            daily_recovery=RECOVERY_40, allow_open_cycle=True)
        self.assertEqual(account, expected)
        self.assertEqual(forward.status(self.journal)['real_forward_days'], 0)
        self.assertEqual(forward.status(self.journal)['paper_fills'], 1)

    def test_unknown_or_incomplete_action_response_blocks_without_record(self):
        self.activate()
        forward.decide(self.journal, now=self.days[80]+'T01:00:00Z')
        packet = self.packet(80)
        packet['corporate_actions_complete'] = False
        with self.assertRaisesRegex(ValueError, 'action response'):
            forward.observe(self.journal, packet, now=self.days[80]+'T08:00:00Z')
        packet['corporate_actions_complete'] = True
        packet['corporate_actions'] = [{'event_id':'unhandled'}]
        with self.assertRaisesRegex(ValueError, 'action response'):
            forward.observe(self.journal, packet, now=self.days[80]+'T08:00:00Z')
        self.assertEqual(len(list(self.journal.glob('*.json'))), 2)

    def test_missing_nonfinite_or_negative_amount_never_enters_journal(self):
        self.activate()
        forward.decide(self.journal, now=self.days[80]+'T01:00:00Z')
        for value in (None, 'NaN', '-1', 'Infinity', True):
            packet = deepcopy(self.packet(80))
            if value is None:
                packet['bar'].pop('amount')
            else:
                packet['bar']['amount'] = value
            with self.assertRaisesRegex(ValueError, 'amount'):
                forward.observe(self.journal, packet, now=self.days[80]+'T08:00:00Z')
            self.assertEqual(len(list(self.journal.glob('*.json'))), 2)
            self.assertEqual(forward.status(self.journal)['real_forward_days'], 0)

    def test_warmup_missing_amount_or_action_completeness_blocks_activation(self):
        path = self.root/'warmup.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        for problem in ('amount', 'actions'):
            warmup = deepcopy(original)
            if problem == 'amount':
                warmup['bars'][0].pop('amount')
            else:
                warmup.pop('corporate_actions_complete')
            self.manifest['warmup'] = save(path, warmup)
            self.freeze()
            with self.assertRaises(ValueError):
                self.activate()
            self.assertFalse(self.journal.exists())

    def test_missing_late_future_and_conflicting_packets_block(self):
        self.activate()
        with self.assertRaisesRegex(ValueError, 'registered decision'):
            forward.observe(self.journal, self.packet(80), now=self.days[80]+'T08:00:00Z')
        forward.decide(self.journal, now=self.days[80]+'T01:00:00Z')
        with self.assertRaisesRegex(ValueError, 'next frozen exchange session'):
            forward.observe(self.journal, self.packet(81), now=self.days[81]+'T08:00:00Z')
        for generated, available in [('08:01:00', '08:02:00'), ('07:05:00','07:04:00'), ('06:59:00','07:01:00')]:
            packet = self.packet(80)
            packet['generated_at'] = self.days[80]+'T'+generated+'Z'
            packet['available_at'] = self.days[80]+'T'+available+'Z'
            with self.assertRaisesRegex(ValueError, 'clocks are inconsistent'):
                forward.observe(self.journal, packet, now=self.days[80]+'T08:00:00Z')
        with self.assertRaisesRegex(ValueError, 'Late historical'):
            forward.observe(self.journal, self.packet(80), now=self.days[81]+'T08:00:00Z')
        forward.observe(self.journal, self.packet(80), now=self.days[80]+'T08:00:00Z')
        packet = self.packet(80)
        packet['bar'] = {**packet['bar'], 'volume':'20000000'}
        with self.assertRaisesRegex(ValueError, 'Conflicting replacement'):
            forward.observe(self.journal, packet, now=self.days[81]+'T08:00:00Z')

    def test_missed_preopen_and_clock_regression_block(self):
        self.activate()
        with self.assertRaisesRegex(ValueError, 'Missed pre-open'):
            forward.decide(self.journal, now=self.days[80]+'T01:30:00Z')
        with self.assertRaisesRegex(ValueError, 'clock regressed'):
            forward.decide(self.journal, now=self.days[79]+'T07:59:00Z')

    def test_signal_computation_must_finish_before_open(self):
        self.activate()
        times = [self.days[80]+'T01:29:59Z', self.days[80]+'T01:30:00Z']
        values = [(datetime.fromisoformat(stamp.replace('Z','+00:00')), stamp) for stamp in times]
        with patch.object(forward, '_clock', side_effect=values):
            with self.assertRaisesRegex(ValueError, 'calculation crossed'):
                forward.decide(self.journal)
        self.assertEqual(len(list(self.journal.glob('*.json'))), 1)

    def test_replay_cannot_create_forward_days(self):
        self.activate(mode='replay')
        forward.decide(self.journal, now=self.days[82]+'T08:00:00Z')
        forward.observe(self.journal, self.packet(80), now=self.days[82]+'T08:01:00Z')
        result = forward.status(self.journal)
        self.assertEqual(result['mode'], 'replay')
        self.assertEqual(result['real_forward_days'], 0)

    def test_tampering_and_concurrent_writer_fail_closed(self):
        self.activate()
        lock = self.journal/'.writer.lock'
        lock.write_text('held', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'writer active'):
            forward.decide(self.journal, now=self.days[80]+'T01:00:00Z')
        lock.unlink()
        self.day(80)
        path = self.journal/'00000002.json'
        event = json.loads(path.read_text(encoding='utf-8'))
        event['payload']['real_forward_day'] = True
        save(path, event)
        with self.assertRaisesRegex(ValueError, 'hash chain mismatch'):
            forward.status(self.journal)

    def test_changed_risk_policy_is_rejected_before_warmup(self):
        self.manifest['daily_recovery'] = {**RECOVERY_40, 'complete_flat_sessions':4}
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'Exact full NAV'):
            self.activate()


class OpenCycleEngineTests(unittest.TestCase):
    def source(self):
        from tests.unit.test_annual_allocation_account import fixture, A
        days, bars = fixture(45, (A,), price=5)
        for row in bars:
            row['volume'] = '10000000'
        config = AllocationConfig(max_position_cny=10000, max_position_fraction=1,
            max_drawdown=.4, execution_price_field='open', slippage_bps=0)
        return days, bars, A, config

    def test_open_cycle_requires_opt_in_and_only_tail_may_stay_open(self):
        days, bars, asset, config = self.source()
        cycle = dict(cycle_id='open', entry_date=days[20], exit_date=None)
        with self.assertRaises(ValueError):
            run_allocation_account(bars, sessions=days, assets=[asset], cycles=[cycle], actions=[],
                                   config=config, daily_recovery=RECOVERY_40)
        with self.assertRaises(ValueError):
            run_allocation_account(bars, sessions=days, assets=[asset], cycles=[cycle,
                dict(cycle_id='illegal', entry_date=days[30], exit_date=days[35])], actions=[],
                config=config, daily_recovery=RECOVERY_40, allow_open_cycle=True)

    def test_closed_cycles_have_identical_default_and_explicit_modes(self):
        days, bars, asset, config = self.source()
        kwargs = dict(sessions=days, assets=[asset], actions=[], config=config,
                      daily_recovery=RECOVERY_40,
                      cycles=[dict(cycle_id='closed', entry_date=days[20], exit_date=days[30])])
        baseline = run_allocation_account(bars, **kwargs)
        self.assertEqual(baseline, run_allocation_account(bars, **kwargs, allow_open_cycle=False))
        self.assertEqual(baseline, run_allocation_account(bars, **kwargs, allow_open_cycle=True))

    def test_pause_preserves_global_peak_and_requires_new_signal_after_five_flat_days(self):
        days, bars, asset, config = self.source()
        from tests.unit.test_annual_allocation_account import change
        for day in days[21:]:
            change(bars, day, price=2.8)
        cycles = [dict(cycle_id='first', entry_date=days[20], exit_date=days[24]),
                  dict(cycle_id='blocked', entry_date=days[26], exit_date=days[27]),
                  dict(cycle_id='new', entry_date=days[28], exit_date=None)]
        result = run_allocation_account(bars, sessions=days, assets=[asset], cycles=cycles,
            actions=[], config=config, daily_recovery=RECOVERY_40, allow_open_cycle=True)
        buys = [f for f in result['fills'] if f['side']=='buy']
        self.assertEqual([f['date'] for f in buys], [days[20],days[28]])
        self.assertEqual(result['fills'][1]['date'], days[22])
        self.assertGreater(result['metrics']['maximum_drawdown'], .4)
        drawdown_dates = [e['date'] for e in result['daily_recovery_journal']
                          if e['kind']=='global_drawdown_pause']
        self.assertIn(days[21], drawdown_dates)
        self.assertIn(days[28], drawdown_dates)
        self.assertLess(result['equity_curve'][28]['equity'], 10000)
        self.assertFalse(result['risk']['new_entries_halted'])


if __name__ == '__main__':
    unittest.main()
