"""Observed receipt clocks never manufacture a provider publication instant."""
from copy import deepcopy
from datetime import datetime
import json
import unittest
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops.frozen_input_clocks import RECEIVED_BASIS
from tests.unit import test_frozen_candidate_forward as fixtures

save = fixtures.save


class ObservedInputClockTests(unittest.TestCase):
    def setUp(self):
        fixture = self.fixture = fixtures.FrozenForwardTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.schedule = [dict(date=day, decision_cutoff_at=day+'T01:15:00Z',
            open_at=day+'T01:25:00Z', auction_close_at=day+'T07:00:00Z',
            daily_observation_not_before=day+'T07:30:00Z') for day in fixture.days]
        fixture.manifest['calendar'] = save(fixture.root/'calendar.json', fixture.schedule)
        fixture.manifest['source_contract']['timestamp_basis'] = RECEIVED_BASIS
        path = fixture.root/'warmup.json'
        warmup = json.loads(path.read_text())
        warmup.update(self.clock_fields(79))
        fixture.manifest['warmup'] = save(path, warmup)
        fixture.freeze()

    def clock_fields(self, index):
        day = self.fixture.days[index]
        return dict(generated_at=None, provider_first_publication_at=None,
            price_request_started_at=day+'T07:31:00Z', price_received_at=day+'T07:32:00Z',
            available_at=day+'T07:33:00Z', acquired_at=day+'T07:34:00Z')

    def packet(self, index):
        return dict(self.fixture.packet(index), **self.clock_fields(index))

    def test_actual_receipt_basis_keeps_unknown_publication_null_across_restart(self):
        f = self.fixture
        f.activate()
        for index in (80, 81):
            decision = forward.decide(f.journal, now=f.days[index]+'T01:14:59Z')
            packet = self.packet(index)
            observed = forward.observe(f.journal, packet, now=f.days[index]+'T08:00:00Z')
            self.assertIsNone(observed['payload']['packet']['generated_at'])
            self.assertIsNone(observed['payload']['packet']['provider_first_publication_at'])
            self.assertEqual(forward.observe(f.journal, packet, now=f.days[index+1]+'T08:00:00Z'), observed)
            self.assertEqual(decision['payload']['signal_input_available_at'],
                             f.days[index-1]+'T07:33:00Z')
        self.assertTrue(observed['payload']['account']['positions'])
        self.assertEqual(forward.status(f.journal)['real_forward_days'], 0)

    def test_opening_auction_cutoff_precedes_open_price_and_rejects_late_activation(self):
        f = self.fixture
        with self.assertRaisesRegex(ValueError, 'Activation must precede'):
            forward.activate(f.journal, f.manifest_path, f.qual_path, mode='synthetic',
                             now=f.days[80]+'T01:15:00Z')
        self.assertFalse(f.journal.exists())
        f.activate()
        with self.assertRaisesRegex(ValueError, 'Missed pre-open'):
            forward.decide(f.journal, now=f.days[80]+'T01:15:00Z')
        with self.assertRaisesRegex(ValueError, 'Missed pre-open'):
            forward.decide(f.journal, now=f.days[80]+'T01:24:59Z')

    def test_signal_calculation_must_finish_before_auction_cutoff(self):
        f = self.fixture
        f.activate()
        times = [f.days[80]+'T01:14:59Z', f.days[80]+'T01:15:00Z']
        with patch.object(forward, '_clock', side_effect=[
                (datetime.fromisoformat(value.replace('Z','+00:00')), value) for value in times]):
            with self.assertRaisesRegex(ValueError, 'calculation crossed'):
                forward.decide(f.journal)
        self.assertEqual(len(list(f.journal.glob('*.json'))), 1)

    def test_partial_session_request_cannot_pass_with_a_later_receipt(self):
        f = self.fixture
        f.activate()
        forward.decide(f.journal, now=f.days[80]+'T01:00:00Z')
        original = self.packet(80)
        for changes in (
            dict(price_request_started_at=f.days[80]+'T07:29:59Z'),
            dict(price_received_at=f.days[80]+'T07:30:59Z'),
            dict(available_at=f.days[80]+'T07:31:59Z'),
            dict(acquired_at=f.days[80]+'T07:32:59Z'),
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'clocks are inconsistent'):
                forward.observe(f.journal, dict(original, **changes), now=f.days[80]+'T08:00:00Z')
        self.assertEqual(len(list(f.journal.glob('*.json'))), 2)

    def test_unknown_provider_time_cannot_be_replaced_by_host_time(self):
        f = self.fixture
        f.activate()
        forward.decide(f.journal, now=f.days[80]+'T01:00:00Z')
        for field in ('generated_at', 'provider_first_publication_at'):
            packet = self.packet(80)
            packet[field] = packet['price_received_at']
            with self.assertRaisesRegex(ValueError, 'explicit null'):
                forward.observe(f.journal, packet, now=f.days[80]+'T08:00:00Z')
            packet.pop(field)
            with self.assertRaisesRegex(ValueError, 'explicit null'):
                forward.observe(f.journal, packet, now=f.days[80]+'T08:00:00Z')

    def test_calendar_cannot_alias_daily_volume_close_or_change_local_day(self):
        f = self.fixture
        original = deepcopy(f.schedule)
        for changes in (
            dict(close_at=f.days[80]+'T07:00:00Z'),
            dict(daily_observation_not_before=f.days[80]+'T06:59:59Z'),
            dict(decision_cutoff_at=f.days[79]+'T01:15:00Z'),
        ):
            schedule = deepcopy(original)
            schedule[80].update(changes)
            f.manifest['calendar'] = save(f.root/'calendar.json', schedule)
            f.freeze()
            with self.assertRaises(ValueError):
                f.activate()
        self.assertFalse(f.journal.exists())

    def test_historical_receipts_replay_without_backdating_or_forward_credit(self):
        f = self.fixture
        actual_day = f.days[90]
        forward.activate(f.journal, f.manifest_path, f.qual_path, mode='replay',
                         now=actual_day+'T08:00:00Z')
        forward.decide(f.journal, now=actual_day+'T08:01:00Z')
        packet = self.packet(80)
        packet.update(price_request_started_at=actual_day+'T08:02:00Z',
            price_received_at=actual_day+'T08:03:00Z', available_at=actual_day+'T08:04:00Z',
            acquired_at=actual_day+'T08:05:00Z')
        observed = forward.observe(f.journal, packet, now=actual_day+'T08:06:00Z')
        self.assertEqual(observed['payload']['packet']['price_received_at'], actual_day+'T08:03:00Z')
        self.assertFalse(observed['payload']['real_forward_day'])

    def test_received_basis_does_not_open_real_forward_gate(self):
        f = self.fixture
        f.qualification['evidence_class'] = 'reviewed_research'
        save(f.qual_path, f.qualification)
        with self.assertRaisesRegex(ValueError, 'verified_raw_source_adapter_missing'):
            forward.activate(f.journal, f.manifest_path, f.qual_path, mode='forward')
        self.assertFalse(f.journal.exists())

    def test_wall_clock_recovery_cannot_hide_generation_before_inputs_or_journal(self):
        f = self.fixture
        f.activate()
        for first in ('T07:31:00Z', 'T07:50:00Z'):
            times = [f.days[79]+first, f.days[80]+'T01:10:00Z']
            with patch.object(forward, '_clock', side_effect=[
                    (datetime.fromisoformat(value.replace('Z','+00:00')), value) for value in times]):
                with self.assertRaisesRegex(ValueError, 'precedes known input or journal'):
                    forward.decide(f.journal)
        self.assertEqual(len(list(f.journal.glob('*.json'))), 1)

    def test_clock_regression_during_calculation_cannot_reverse_signal_times(self):
        f = self.fixture
        f.activate()
        times = [f.days[80]+'T01:10:00Z', f.days[80]+'T01:09:59Z']
        with patch.object(forward, '_clock', side_effect=[
                (datetime.fromisoformat(value.replace('Z','+00:00')), value) for value in times]):
            with self.assertRaisesRegex(ValueError, 'calculation clock regressed'):
                forward.decide(f.journal)
        self.assertEqual(len(list(f.journal.glob('*.json'))), 1)
