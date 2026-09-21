from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, policy
from tests.unit.test_offline_order_timeouts import timeout_policy
from tests.unit.test_offline_runtime import observation


def create_drawdown_book(path):
    return OfflineOrderJournal.create(path,initial_cash='600',initial_positions={SYMBOL:100},
        commission_bps='5',minimum_commission='5',timeout_policy=timeout_policy(),
        admission_policy={**policy(),'schema_version':2,'max_drawdown':'.08'})


class OfflineDrawdownRecoveryTests(unittest.TestCase):
    def test_real_driver_continues_valuation_but_does_not_clear_cross_day_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'runtime.sqlite'
            with create_drawdown_book(path):pass
            now=NOW
            with OfflineRuntime(path,clock=lambda:now) as runtime:
                runtime.tick(observation(runtime,now,opening=True))
                feed=observation(runtime,now)
                feed['quotes'][SYMBOL].update(bid='3.6',ask='3.6')
                runtime.tick(feed)
                now+=timedelta(days=1)
                feed=observation(runtime,now,opening=True)
                feed['quotes'][SYMBOL].update(bid='3.2',ask='3.2')
                result=runtime.tick(feed)
                self.assertTrue(result['paused'])
                self.assertTrue(result['drawdown_guard_configured'])
                self.assertEqual(Decimal(result['drawdown_guard']['book_drawdown']),Decimal('.08'))
                result=runtime.tick(observation(runtime,now))
                self.assertTrue(result['paused'])
                self.assertEqual(Decimal(result['drawdown_guard']['book_drawdown']),0)
                self.assertEqual(result['counts_as_forward_paper_days'],0)
                self.assertFalse(result['executable'])

    def test_process_exit_cannot_separate_drawdown_observation_from_persistent_stop(self):
        source='''
import os, sys
from tests.integration.test_offline_drawdown_recovery import create_drawdown_book
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument
book=create_drawdown_book(sys.argv[1])
packet=context(book)
packet.update(instruments={s:instrument(s) for s in (SYMBOL,OTHER)},sellable_positions={SYMBOL:100})
book.begin_session(packet,clock=lambda:NOW)
if sys.argv[2]=='before':
    append=book._append
    def crash(state,event):
        append(state,event)
        if event['kind']=='PORTFOLIO_VALUATION':os._exit(7)
    book._append=crash
packet=context(book)
packet['quotes'][SYMBOL].update(bid='3.2',ask='3.2')
book.record_valuation(packet,clock=lambda:NOW)
os._exit(7)
'''
        with tempfile.TemporaryDirectory() as directory:
            for phase in ('before','after'):
                path=Path(directory)/(phase+'.sqlite')
                result=subprocess.run([sys.executable,'-c',source,str(path),phase],capture_output=True,
                    text=True,timeout=30)
                self.assertEqual(result.returncode,7,result.stdout+result.stderr)
                with OfflineOrderJournal(path) as book:
                    snap=book.snapshot()
                    self.assertEqual(snap['drawdown_guard']['stop_latched'],phase=='after')
                    self.assertEqual(snap['paused'],phase=='after')
                    self.assertEqual(Decimal(snap['drawdown_guard']['peak_equity']),1000)
