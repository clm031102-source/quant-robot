from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_conversion_revisions import conversion_facts
from tests.unit.test_offline_conversions import conversion_policy,start
from tests.unit.test_offline_dividends import extended_policy
from tests.unit.test_offline_order_admission import NOW,SYMBOL,OTHER,context,intent,instrument
from tests.unit.test_offline_order_timeouts import timeout_policy


def create_fixture(path,side='BUY',*,resumed=False):
    with OfflineOrderJournal.create(path,initial_cash='2600',initial_positions={SYMBOL:100},commission_bps='.5',minimum_commission='5',
            admission_policy=extended_policy(),timeout_policy=timeout_policy(),conversion_policy=conversion_policy()) as book:
        start(book);book.admit(intent(side=side),context(book),clock=lambda:NOW);book.report_status('one','cancel','CANCELLED',0)
        book.record_conversion_entitlements(clock=lambda:NOW.replace(hour=15));book.apply_share_conversions(clock=lambda:NOW+timedelta(days=1))
        if resumed:start(book,NOW+timedelta(days=2),price='8')
        book.fill('one','late',40,'4')


class OfflineConversionRevisionRuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'book.sqlite';self.now=NOW+timedelta(days=2,seconds=1)
        create_fixture(self.path);self.runtime=OfflineRuntime(self.path,clock=lambda:self.now);self.addCleanup(self.runtime.close)

    def feed(self,receipts=(),opening=False):
        p=context(self.runtime.book,self.now);p.pop('journal_sequence');p.pop('journal_hash');p['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id='share_conversion:merge-one')
        p['receipts']=list(receipts)
        if opening:p['opening']=dict(instruments={s:{**instrument(s),'valid_until':'2026-09-16'} for s in (SYMBOL,OTHER)},sellable_positions=self.runtime.book.snapshot()['positions'])
        return p

    def commands(self):return [dict(kind='conversion_resolution',facts=conversion_facts(self.path,self.now))]
    def reconcile(self):
        s=self.runtime.book.snapshot()
        return dict(kind='reconcile',snapshot_id='after-'+str(s['sequence']),expected_sequence=s['sequence'],cash=s['cash'],positions=s['positions'],
            orders={key:{f:r[f] for f in ('status','filled_quantity','filled_notional','commission')} for key,r in s['orders'].items()})

    def test_driver_resolves_once_and_keeps_terminal_fill_fault_before_opening(self):
        feed=self.feed(self.commands(),opening=True);first=self.runtime.tick(feed);s=self.runtime.book.snapshot()
        self.assertEqual(Decimal(s['cash']),2435);self.assertEqual(s['positions'][SYMBOL],70)
        self.assertEqual(s['risk_session']['session_date'],'2026-09-14');self.assertEqual(first['status'],'attention')
        self.assertIn('fill_after_terminal_status',s['faults']);self.runtime.tick(feed)
        self.assertEqual(self.runtime.book.snapshot()['cash'],s['cash']);self.assertEqual(len(self.runtime.book.snapshot()['conversions']['participation']),1)

    def test_explicit_reconcile_then_opening_consumes_budget_and_prepares_unfilled_order(self):
        self.runtime.tick(self.feed(self.commands()));feed=self.feed([self.reconcile()],opening=True);feed['intents']=[intent('next',code=OTHER,now=self.now)]
        report=self.runtime.tick(feed);s=self.runtime.book.snapshot()
        self.assertEqual(report['status'],'ready');self.assertFalse(s['paused']);self.assertEqual(s['risk_session']['carryover_fill_shares'][SYMBOL]['BUY'],20)
        self.assertEqual(s['sellable_positions'][SYMBOL],70);self.assertEqual(s['orders']['next']['filled_quantity'],0);self.assertIn('dispatch',s['orders']['next'])
        self.assertEqual(Decimal(s['portfolio_valuation']['last_valid']['book_equity']),2995)
        self.assertEqual(s['portfolio_valuation']['last_valid']['performance_attribution_status'],'requires_restatement')

    def test_readonly_report_distinguishes_original_receipt_and_resolved_economics(self):
        self.runtime.tick(self.feed(self.commands()));r=build_corporate_action_review(self.path);action=r['actions'][0]
        self.assertEqual(action['captured_entitlement']['quantity'],100);self.assertEqual(action['applied_conversion']['new_quantity'],50)
        self.assertEqual(action['effective_conversion']['new_quantity'],70);self.assertEqual(action['unapplied_fills'],{})
        self.assertIn('late',action['accounted_fills']);self.assertIn('late',r['retained_conversion_fill_receipts'])
        self.assertTrue(action['candidate_receipts'][0]['applied_to_book']);self.assertFalse(action['revision_source_authenticated'])
        self.assertFalse(r['clears_faults']);self.assertFalse(r['automatic_correction_allowed'])

    def test_stale_resolution_is_not_silently_reanchored_and_live_facts_reject(self):
        command=self.commands();self.runtime.book.set_kill_switch(True,reason='advanced source state');report=self.runtime.tick(self.feed(command))
        self.assertTrue(any(s['stage']=='receipt' and s['status']=='rejected' for s in report['steps']))
        self.assertEqual(self.runtime.book.snapshot()['conversions']['revisions'],{})
        facts=conversion_facts(self.path,self.now);facts['mode']='live';self.runtime.tick(self.feed([dict(kind='conversion_resolution',facts=facts)]))
        self.assertEqual(Decimal(self.runtime.book.snapshot()['cash']),2600)

    def test_resumed_session_keeps_sellable_bound_while_cash_and_participation_change(self):
        self.runtime.close();self.path=self.path.parent/'resumed.sqlite';create_fixture(self.path,'SELL',resumed=True)
        self.runtime=OfflineRuntime(self.path,clock=lambda:self.now);self.addCleanup(self.runtime.close);self.runtime.tick(self.feed(self.commands()))
        s=self.runtime.book.snapshot();self.assertEqual(s['positions'][SYMBOL],30);self.assertEqual(s['sellable_positions'][SYMBOL],30)
        self.assertEqual(Decimal(s['cash']),2755);self.assertEqual(s['risk_session']['carryover_fill_shares'][SYMBOL]['SELL'],20)
