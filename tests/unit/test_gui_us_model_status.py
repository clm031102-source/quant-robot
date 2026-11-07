import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.gui.us_model_status import STATUS_PATH, current_us_model_status


def snapshot(days=0):
    return dict(schema='us_daily_model_snapshot_v1', evidence_kind='conditional_forward_model',
                execution_certified=False, qualified=False, real_forward_days=0,
                model_forward_days=days, artificial_model_days=0,
                status='initialized_cash_waiting_normal_month_end', reason=None,
                source_receipts=[dict(received_at='2026-11-07T18:00:00+00:00')],
                ledger=dict(date='2026-11-06', NAV='1000.00', maxDD='0', days=[{}] * days,
                            fills=[], balances=dict(spendable_cash='1000.00', locked_cash='0',
                            receivables={}, quantities=dict.fromkeys(('SPY', 'EFA', 'IEF', 'GLD'), 0))))


class SavedModelStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / STATUS_PATH
        self.path.parent.mkdir(parents=True)
        self.record = dict(schema='us_allocation_model_operations_v1',
            updated_at='2026-11-07T18:00:01Z', status='waiting_first_session', reason=None,
            operation_window=dict(start='2026-11-09', end='2026-12-07', scheduled_sessions=20),
            schedule=dict(installed=True, next_capture_at='2026-11-09T21:15:00Z'),
            accounts=dict(primary=snapshot(), stress=snapshot()))

    def read(self):
        self.path.write_text(json.dumps(self.record), encoding='utf-8')
        return current_us_model_status(self.root)

    def test_missing_and_initialization_are_not_observed_profit(self):
        empty = current_us_model_status(self.root)
        self.assertFalse(empty['available'])
        self.assertIsNone(empty['model_forward_days'])
        loaded = self.read()
        self.assertTrue(loaded['available'])
        self.assertEqual(loaded['real_forward_days'], 0)
        self.assertEqual(loaded['accounts']['primary']['NAV_USD'], '1000.00')
        self.assertIsNone(loaded['accounts']['primary']['model_profit_USD'])
        self.record['accounts']['primary']['ledger'] = None
        waiting = self.read()['accounts']['primary']
        self.assertFalse(waiting['initialized'])
        self.assertIsNone(waiting['NAV_USD'])

    def test_model_values_are_separate_from_cash_available_and_real_forward(self):
        for role in ('primary', 'stress'):
            account = snapshot(1)
            account['ledger'].update(NAV='1010.25', date='2026-11-09', maxDD='0.01')
            account['ledger']['balances'].update(spendable_cash='600.00', locked_cash='400.00',
                                                receivables={'dividend': dict(amount='10.25')})
            self.record['accounts'][role] = account
        before = copy.deepcopy(self.record)
        loaded = self.read()
        self.assertEqual(loaded['model_forward_days'], 1)
        self.assertEqual(loaded['real_forward_days'], 0)
        primary = loaded['accounts']['primary']
        self.assertEqual(primary['model_profit_USD'], '10.25')
        self.assertEqual(primary['spendable_cash_USD'], '600.00')
        self.assertEqual(primary['receivable_USD'], '10.25')
        self.assertNotIn('ledger', primary)
        self.assertEqual(json.loads(self.path.read_text()), before)

    def test_artificial_or_inconsistent_records_do_not_show_results(self):
        changes = [dict(evidence_kind='artificial'), dict(real_forward_days=1),
                   dict(model_forward_days=True), dict(execution_certified=True),
                   dict(qualified=True), dict(ledger=None, model_forward_days=1)]
        for changeset in changes:
            with self.subTest(changes=changeset):
                self.record['accounts']['primary'] = dict(snapshot(), **changeset)
                result = self.read()
                self.assertFalse(result['available'])
                self.assertEqual(result['accounts'], {})
                self.assertIsNone(result['model_forward_days'])

    def test_later_installation_receipt_and_pre_source_failure_stay_visible(self):
        self.record['schedule']['installed'] = False
        self.record['capture_scope_sha256'] = 'a' * 64
        exported = self.path.parent / 'scheduled_task_preparation/registered.utf16.xml'
        exported.parent.mkdir()
        exported.write_text('<artificial-export/>', encoding='utf-16')
        raw = exported.read_bytes()
        registration = dict(schema='us_allocation_model_schedule_v1', installed=True,
            task_name='USDAllocationConditionalModel_20261109_20261207', capture_scope_sha256='a'*64,
            actual_export=dict(path=str(exported), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        receipt = self.path.parent / 'schedule_registration.json'
        receipt.write_text(json.dumps(registration), encoding='utf-8-sig')
        self.assertTrue(self.read()['schedule']['installed'])
        registration['capture_scope_sha256'] = 'b'*64
        receipt.write_text(json.dumps(registration), encoding='utf-8-sig')
        self.assertFalse(self.read()['schedule']['installed'])
        self.record.update(accounts={}, status='blocked_before_source_request', reason='missing prior day')
        result = self.read()
        self.assertTrue(result['available'])
        self.assertEqual(result['status'], 'blocked_before_source_request')
        self.assertEqual(result['accounts'], {})
        self.assertIsNone(result['model_forward_days'])


if __name__ == '__main__':
    unittest.main()
