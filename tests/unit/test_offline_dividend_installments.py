from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from tests.unit.test_offline_dividends import dividend_policy, extended_policy, start
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context


class OfflineDividendInstallmentTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name)/'book.sqlite';self.pay=NOW+timedelta(days=2)
        self.book=OfflineOrderJournal.create(self.path,initial_cash='2600',initial_positions={SYMBOL:100},
            commission_bps='.5',minimum_commission='5',admission_policy=extended_policy(),dividend_policy=dividend_policy())
        self.addCleanup(self.book.close);start(self.book,NOW)
        self.book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15))
        self.book.accrue_dividends(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))

    def credit(self,receipt,value,book=None):
        return (book or self.book).record_dividend_cash_installment('div-one',receipt,value,clock=lambda:self.pay)

    def test_two_installments_move_only_received_cash_and_preserve_equity(self):
        start(self.book,self.pay,'3.4','cash_dividend:div-one')
        for receipt,value,cash,owed,paid in [('first','20','2620','40',False),('second','40','2660','0',True)]:
            self.assertTrue(self.credit(receipt,value));snap=self.book.snapshot()
            self.assertEqual(Decimal(snap['cash']),Decimal(cash))
            self.assertEqual(Decimal(snap['dividends']['receivable_total']),Decimal(owed))
            self.assertEqual('div-one' in snap['dividends']['paid'],paid)
            packet=context(self.book,self.pay);packet['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
            self.book.record_valuation(packet,clock=lambda:self.pay)
            self.assertEqual(Decimal(self.book.snapshot()['portfolio_valuation']['last_valid']['book_equity']),3000)
        self.assertEqual(self.book.snapshot()['positions'],{SYMBOL:100})

    def test_duplicate_and_conflict_remain_safe_after_reopen_and_final_payment(self):
        self.credit('first','20');self.book.close()
        self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close)
        self.assertFalse(self.credit('first','20'))
        with self.assertRaisesRegex(ValueError,'conflicting'):self.credit('first','21')
        self.credit('second','40');self.assertFalse(self.credit('first','20'))
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2660)

    def test_zero_negative_fractional_cent_overpayment_and_early_credit_are_rejected(self):
        for value in ('0','-1','.001','60.01'):
            with self.subTest(value=value),self.assertRaises(ValueError):self.credit('bad',value)
        with self.assertRaises(ValueError):
            self.book.record_dividend_cash_installment('div-one','early','20',clock=lambda:self.pay-timedelta(days=1))
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2600)
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['receivable_total']),60)

    def test_partial_settlement_cannot_clear_unrelated_runtime_or_operator_stops(self):
        self.book.set_kill_switch(True,reason='operator remains stopped')
        self.book.note_runtime_supervision_fault('synthetic monitor loss');before=self.book.snapshot()
        self.credit('first','20');after=self.book.snapshot()
        self.assertEqual(after['faults'],before['faults']);self.assertTrue(after['kill_switch']);self.assertTrue(after['paused'])
        self.assertEqual(after['price_basis'],before['price_basis'])

    def test_failure_after_event_insert_rolls_back_cash_receivable_and_receipt(self):
        before=self.book.snapshot();original=self.book._append
        def fail(state,event):original(state,event);raise OSError('synthetic commit-boundary failure')
        with patch.object(self.book,'_append',side_effect=fail),self.assertRaises(OSError):self.credit('first','20')
        self.assertEqual(self.book.snapshot(),before)
        self.assertTrue(self.credit('first','20'))
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2620)

    def test_competing_installments_cannot_overpay_one_receivable(self):
        barrier=threading.Barrier(2);outcomes=[]
        def write(receipt):
            try:
                with OfflineOrderJournal(self.path) as book:
                    barrier.wait(timeout=5)
                    try:self.credit(receipt,'40',book);outcomes.append('credited')
                    except ValueError:outcomes.append('rejected')
            except BaseException as exc:outcomes.append(type(exc).__name__+':'+str(exc))
        workers=[threading.Thread(target=write,args=(receipt,)) for receipt in ('one','two')]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=10)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(sorted(outcomes),['credited','rejected'])
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2640)
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['receivable_total']),20)

    def test_review_preserves_each_installment_event_and_final_settlement_status(self):
        self.credit('one','20');self.credit('two','40');packet=build_corporate_action_review(self.path)
        action=packet['actions'][0];payments=[row for row in action['recorded_action_events'] if row['kind']=='DIVIDEND_CASH_INSTALLMENT']
        self.assertEqual(len(payments),2)
        self.assertEqual(sum(Decimal(row['payload']['cash_amount']) for row in payments),60)
        self.assertTrue(action['paid']);self.assertIsNone(action['receivable']);self.assertFalse(packet['clears_faults'])

    def test_legacy_full_credit_contract_stays_strict_and_can_settle_the_remaining_balance(self):
        with self.assertRaises(ValueError):self.book.record_dividend_cash_credit('div-one','legacy','20',clock=lambda:self.pay)
        self.credit('part','20')
        with self.assertRaises(ValueError):self.book.record_dividend_cash_credit('div-one','wrong','60',clock=lambda:self.pay)
        self.book.record_dividend_cash_credit('div-one','final','40',clock=lambda:self.pay)
        self.assertFalse(self.credit('final','40'))
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2660)


if __name__=='__main__':unittest.main()
