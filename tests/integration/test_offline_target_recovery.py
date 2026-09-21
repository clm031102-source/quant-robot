from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_target_compiler import create_target_book, target
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context
from tests.unit.test_offline_conversions import conversion_policy, start
from tests.unit.test_offline_dividends import extended_policy


class OfflineTargetRecoveryTests(unittest.TestCase):
    def test_two_writers_cannot_compile_against_the_same_unreserved_cash(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'race.sqlite'
            with create_target_book(path,cash='1000') as original:
                ready=Barrier(2)
                def writer(key):
                    with OfflineOrderJournal(path) as book:
                        request,packet=target(book,key),context(book)
                        ready.wait(timeout=10)
                        try:
                            book.admit_target(request,packet,clock=lambda:NOW)
                            return 'admitted'
                        except ValueError as exc:
                            return str(exc)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results=list(pool.map(writer,('first','second')))
                self.assertEqual(results.count('admitted'),1)
                self.assertTrue(any('stale journal anchor' in r for r in results))
                snap=original.snapshot()
                self.assertEqual(len(snap['orders']),1)
                self.assertEqual(Decimal(snap['reserved_cash']),805)
                with self.assertRaisesRegex(ValueError,'duplicate'):
                    missing=next(key for key in ('first','second') if key not in snap['orders'])
                    original.admit_target(target(original,missing),context(original),clock=lambda:NOW)
                with self.assertRaisesRegex(ValueError,'lot|covered'):
                    original.admit_target(target(original,'new-decision'),context(original),clock=lambda:NOW)

    def test_process_exit_cannot_separate_compilation_from_identity_and_reservation(self):
        source='''
import os, sys
from tests.unit.test_offline_target_compiler import create_target_book, target
from tests.unit.test_offline_order_admission import NOW, context
book=create_target_book(sys.argv[1],cash='1000')
if sys.argv[2]=='before':
    append=book._append
    def crash(state,event):
        append(state,event)
        if event['kind']=='REGISTER':os._exit(7)
    book._append=crash
book.admit_target(target(book),context(book),clock=lambda:NOW)
os._exit(7)
'''
        with tempfile.TemporaryDirectory() as directory:
            for phase in ('before','after'):
                with self.subTest(phase=phase):
                    path=Path(directory)/(phase+'.sqlite')
                    result=subprocess.run([sys.executable,'-c',source,str(path),phase],
                        capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,7,result.stdout+result.stderr)
                    with OfflineOrderJournal(path) as book:
                        snap=book.snapshot()
                        self.assertEqual(Decimal(snap['cash']),1000)
                        self.assertEqual(snap['positions'],{})
                        if phase=='before':
                            self.assertEqual(snap['orders'],{})
                            self.assertEqual(Decimal(snap['reserved_cash']),0)
                            self.assertTrue(book.admit_target(target(book),context(book),clock=lambda:NOW))
                        else:
                            order=snap['orders']['target-one']
                            self.assertEqual(order['status'],'UNKNOWN')
                            self.assertEqual(order['quantity'],200)
                            self.assertEqual(Decimal(snap['reserved_cash']),805)
                            self.assertEqual(order['admission']['target_compilation']['target']['source_fingerprint'],'a'*64)
                            self.assertNotIn('dispatch',order)
                            self.assertTrue(snap['paused'])
                            self.assertFalse(snap['executable'])

    def test_corporate_action_engine_requires_new_explicit_target_price_basis(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'conversion.sqlite'
            cfg={**extended_policy(),'capital_limit_cny':'10000','schema_version':2,'max_drawdown':'.08'}
            with OfflineOrderJournal.create(path,initial_cash='9600',initial_positions={SYMBOL:100},
                    commission_bps='5',minimum_commission='5',admission_policy=cfg,
                    conversion_policy=conversion_policy()) as book:
                start(book)
                book.record_conversion_entitlements(clock=lambda:NOW.replace(hour=15))
                book.apply_share_conversions(clock=lambda:NOW+timedelta(days=1))
                now=NOW+timedelta(days=2)
                start(book,now,price='8')
                basis=book.snapshot()['price_basis'][SYMBOL]
                request=target(book,target_notional_cny='0',limit_price='8',
                    source_as_of=(now-timedelta(minutes=1)).isoformat(),signal_timestamp=now.isoformat(),
                    expires_at=(now+timedelta(minutes=2)).isoformat())
                packet=context(book,now)
                packet['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id=basis)
                with self.assertRaisesRegex(ValueError,'price basis'):
                    book.admit_target(request,packet,clock=lambda:now)
                request.update(client_intent_id='new-basis',idempotency_key='key-new-basis',price_basis_id=basis)
                book.admit_target(request,context_with_basis(book,now,basis),clock=lambda:now)
                row=book.snapshot()['orders']['new-basis']
                self.assertEqual((row['side'],row['quantity']),('SELL',50))
                self.assertEqual(row['admission']['target_compilation']['target']['price_basis_id'],basis)


def context_with_basis(book,now,basis):
    packet=context(book,now)
    packet['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id=basis)
    return packet
