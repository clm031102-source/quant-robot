"""Historical record reuse must not compromise cash, receipt identity or isolation."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal, _event


class OfflineHistoryIsolationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'book.sqlite'
        self.book = OfflineOrderJournal.create(self.path, initial_cash='3000', initial_positions={},
            commission_bps='0.5', minimum_commission='5')
        self.addCleanup(self.book.close)

    def order(self, key='one'):
        self.book.register(order_id=key, idempotency_key=key, symbol='510300.SH', side='BUY', quantity=100, limit_price='4')

    def cancelled(self, key='one'):
        self.order(key); self.book.report_status(key, key+'-cancel', 'CANCELLED', 0)

    def test_unchanged_receipt_and_terminal_record_payloads_are_reused(self):
        self.cancelled()
        previous = self.book._projection[1]
        receipt = previous['receipts']['status:one-cancel']; order = previous['orders']['one']
        self.book.set_kill_switch(True, reason='copy workload probe')
        current = self.book._projection[1]
        self.assertIs(current['receipts']['status:one-cancel'], receipt)
        self.assertIs(current['orders']['one'], order)
        with self.assertRaises(TypeError): receipt['status'] = 'FILLED'
        with self.assertRaises(TypeError): order['quantity'] = 999

    def test_public_and_private_read_results_remain_independently_mutable(self):
        self.cancelled()
        state = self.book._read(); state['orders']['one']['quantity'] = 900
        state['receipts']['status:one-cancel']['cumulative_quantity'] = 900
        snapshot = self.book.snapshot(); snapshot['orders']['one']['status'] = 'FILLED'
        self.assertEqual(self.book.snapshot()['orders']['one']['quantity'], 100)
        self.assertEqual(self.book.snapshot()['orders']['one']['status'], 'CANCELLED')
        self.assertFalse(self.book.report_status('one', 'one-cancel', 'CANCELLED', 0))

    def test_late_fill_thaws_only_the_affected_terminal_order(self):
        self.cancelled(); self.cancelled('two')
        old = self.book._projection[1]; untouched = old['orders']['two']
        self.book.fill('one', 'late', 40, '4')
        actual = self.book.snapshot()
        self.assertEqual(Decimal(actual['cash']), 2835)
        self.assertEqual(actual['positions'], {'510300.SH': 40})
        self.assertTrue(actual['paused'])
        self.assertEqual(old['orders']['one']['filled_quantity'], 0)
        self.assertIs(self.book._projection[1]['orders']['two'], untouched)

    def test_late_unknown_status_and_restart_keep_terminal_fill_evidence(self):
        self.order(); self.book.fill('one', 'fill', 100, '4')
        self.book.report_status('one', 'late-unknown', 'UNKNOWN', 100)
        self.assertEqual(self.book.snapshot()['orders']['one']['filled_quantity'], 100)
        self.assertEqual(self.book.snapshot()['orders']['one']['status'], 'UNKNOWN')
        with OfflineOrderJournal(self.path) as reopened:
            self.assertEqual(Decimal(reopened.snapshot()['cash']), 2595)
            self.assertFalse(reopened.fill('one', 'fill', 100, '4'))

    def test_reconcile_with_terminal_orders_can_validate_disposable_state(self):
        self.cancelled(); self.book.set_kill_switch(True, reason='operator')
        state = self.book.snapshot()
        evidence = {key: {name: row[name] for name in ('status','filled_quantity','filled_notional','commission')}
                    for key,row in state['orders'].items()}
        self.book.reconcile(snapshot_id='reconciled', expected_sequence=state['sequence'], cash=state['cash'],
                            positions=state['positions'], orders=evidence)
        self.assertTrue(self.book.snapshot()['paused'])
        self.assertEqual(self.book.snapshot()['orders']['one']['status'], 'CANCELLED')

    def test_nested_receipts_are_immutable_in_cache_but_mutable_in_read_copy(self):
        payload = {'reason': 'nested', 'extra': {'rows': [{'quantity': 100}]}}
        self.book._run(lambda state: _event('FAULT', payload, 'custom:one'))
        cached = self.book._projection[1]['receipts']['custom:one']
        with self.assertRaises(TypeError): cached['extra']['rows'][0]['quantity'] = 1
        with self.assertRaises(TypeError): cached['extra']['rows'].append({})
        with self.assertRaises(TypeError): cached.update(reason='changed')
        self.assertIs(deepcopy(cached), cached)
        read = self.book._read(); read['receipts']['custom:one']['extra']['rows'][0]['quantity'] = 2
        payload['extra']['rows'].append({'quantity': 999})
        self.assertEqual(self.book._read()['receipts']['custom:one']['extra']['rows'], [{'quantity':100}])

    def test_failed_late_fill_does_not_mutate_a_shared_terminal_record(self):
        self.cancelled(); previous = self.book._projection[1]['orders']['one']
        append = self.book._append
        def fail(state, event):
            append(state, event); raise RuntimeError('injected after insertion')
        self.book._append = fail
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            self.book.fill('one', 'late', 40, '4')
        self.book._append = append
        self.assertEqual(previous['filled_quantity'], 0)
        self.assertEqual(Decimal(self.book.snapshot()['cash']), 3000)
        self.assertEqual(self.book.snapshot()['orders']['one']['filled_quantity'], 0)

    def test_nested_duplicate_payloads_still_match_and_conflicts_remain_durable(self):
        payload = {'reason':'nested', 'extra':{'rows':[{'quantity':100}]}}
        self.book._run(lambda state: _event('FAULT', payload, 'custom:one'))
        old = self.book._projection[1]['receipts']['custom:one']
        self.assertFalse(self.book._run(lambda state: None if self.book._duplicate(state, 'custom:one', deepcopy(payload)) else _event('FAULT', {})))
        conflicting = deepcopy(payload); conflicting['extra']['rows'][0]['quantity'] = 101
        with self.assertRaisesRegex(ValueError, 'conflicting receipt identity'):
            self.book._run(lambda state: self.book._duplicate(state, 'custom:one', conflicting))
        self.assertEqual(old['extra']['rows'][0]['quantity'], 100)
        with OfflineOrderJournal(self.path) as reopened:
            self.assertTrue(any('conflicting receipt identity' in fault for fault in reopened.snapshot()['faults']))

    def test_guarded_terminal_admission_and_session_snapshots_stay_isolated(self):
        from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
        with OfflineOrderJournal.create(self.path.parent / 'guarded.sqlite', initial_cash='3000', initial_positions={},
                commission_bps='0.5', minimum_commission='5', admission_policy=policy()) as guarded:
            opening=context(guarded); opening.update(instruments={s:instrument(s) for s in (SYMBOL,OTHER)}, sellable_positions={})
            guarded.begin_session(opening, clock=lambda:NOW)
            guarded.admit(intent(), context(guarded), clock=lambda:NOW)
            guarded.fill('one', 'guarded-fill', 100, '4')
            copy=guarded.snapshot()
            copy['orders']['one']['admission']['intent']['quantity']=900
            copy['risk_session']['instruments'][SYMBOL]['lot_size']=1
            actual=guarded.snapshot()
            self.assertEqual(actual['orders']['one']['admission']['intent']['quantity'],100)
            self.assertEqual(actual['risk_session']['instruments'][SYMBOL]['lot_size'],100)
            self.assertEqual(Decimal(actual['cash']),2595)
            self.assertFalse(guarded.fill('one', 'guarded-fill', 100, '4'))


if __name__ == '__main__': unittest.main()
