from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_dividend_revisions import revision_facts
from tests.unit.test_offline_dividends import dividend_policy,extended_policy,start
from tests.unit.test_offline_order_admission import NOW,SYMBOL,OTHER,context,intent
from tests.unit.test_offline_order_timeouts import timeout_policy


def create_fixture(path,side='SELL'):
    rules=dividend_policy();rules['events'][0]['pay_date']='2026-09-15'
    with OfflineOrderJournal.create(path,initial_cash='2600',initial_positions={SYMBOL:100},commission_bps='.5',minimum_commission='5',
            admission_policy=extended_policy(),timeout_policy=timeout_policy(),dividend_policy=rules) as book:
        start(book,NOW);book.admit(intent(side=side),context(book),clock=lambda:NOW)
        book.report_status('one','cancel','CANCELLED',0)
        book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15))
        book.accrue_dividends(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
        start(book,NOW+timedelta(days=1),'3.4','cash_dividend:div-one')
        book.record_dividend_cash_credit('div-one','original','60',clock=lambda:NOW+timedelta(days=1))
        book.fill('one','late',40,'4')


class OfflineDividendRevisionRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.path=self.root/'book.sqlite';self.now=NOW+timedelta(days=1,seconds=1)
        self.open_runtime()

    def open_runtime(self,side='SELL'):
        create_fixture(self.path,side);self.runtime=OfflineRuntime(self.path,clock=lambda:self.now)
        self.addCleanup(self.runtime.close)

    def feed(self,receipts=()):
        packet=context(self.runtime.book,self.now);packet.pop('journal_sequence');packet.pop('journal_hash')
        packet['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        packet['receipts']=list(receipts);return packet

    def commands(self):
        facts=revision_facts(self.runtime.book,self.path,self.now)
        return [dict(kind='dividend_revision',facts=facts),dict(kind='dividend_refund',event_id='div-one',receipt_id='refund',cash_amount='24',expected_revision_id='revision-one')]

    def test_driver_applies_revision_and_refund_once_and_keeps_other_faults(self):
        feed=self.feed(self.commands());self.runtime.tick(feed);first=self.runtime.book.snapshot()
        self.runtime.tick(feed);second=self.runtime.book.snapshot()
        self.assertEqual(Decimal(first['cash']),2791);self.assertEqual(second['cash'],first['cash'])
        self.assertEqual(Decimal(second['dividends']['payable_total']),0)
        self.assertEqual(Decimal(second['portfolio_valuation']['last_valid']['book_equity']),2995)
        self.assertIn('fill_after_terminal_status',second['faults']);self.assertTrue(second['paused'])

    def test_driver_instalment_can_complete_increased_entitlement_without_inventing_profit(self):
        self.runtime.close();self.path=self.root/'buy.sqlite';self.open_runtime('BUY')
        facts=revision_facts(self.runtime.book,self.path,self.now)
        feed=self.feed([dict(kind='dividend_revision',facts=facts),dict(kind='dividend_installment',event_id='div-one',receipt_id='supplement',cash_amount='24')])
        self.runtime.tick(feed);s=self.runtime.book.snapshot()
        self.assertEqual(Decimal(s['cash']),2519);self.assertEqual(Decimal(s['dividends']['receivable_total']),0)
        self.assertEqual(Decimal(s['portfolio_valuation']['last_valid']['book_equity']),2995)
        self.assertEqual(s['portfolio_valuation']['last_valid']['performance_attribution_status'],'requires_restatement')

    def test_driver_does_not_refresh_stale_revision_facts_or_accept_live_scope(self):
        commands=self.commands();self.runtime.book.set_kill_switch(True,reason='operator state advanced')
        before=self.runtime.book.snapshot();report=self.runtime.tick(self.feed(commands[:1]))
        self.assertTrue(any(step['stage']=='receipt' and step['status']=='rejected' for step in report['steps']))
        self.assertEqual(self.runtime.book.snapshot()['dividends']['revisions'],{})
        self.assertEqual(self.runtime.book.snapshot()['cash'],before['cash'])
        facts=revision_facts(self.runtime.book,self.path,self.now);facts['mode']='live'
        self.runtime.tick(self.feed([dict(kind='dividend_revision',facts=facts)]))
        self.assertEqual(self.runtime.book.snapshot()['dividends']['revisions'],{})

    def test_report_retains_original_rights_revision_and_signed_settlements(self):
        self.runtime.tick(self.feed(self.commands()));report=build_corporate_action_review(self.path);action=report['actions'][0]
        self.assertEqual(action['captured_entitlement']['quantity'],100)
        self.assertEqual(action['effective_entitlement']['quantity'],60)
        self.assertEqual(Decimal(action['settled_net']),36)
        kinds={row['kind'] for row in action['recorded_action_events']}
        self.assertTrue({'DIVIDEND_CASH_CREDIT','DIVIDEND_ENTITLEMENT_REVISION','DIVIDEND_CASH_REFUND'}.issubset(kinds))
        self.assertFalse(report['automatic_correction_allowed']);self.assertFalse(action['revision_source_authenticated'])

    def test_explicit_full_reconciliation_can_resume_normal_guarded_flow_after_settlement(self):
        self.runtime.tick(self.feed(self.commands()));s=self.runtime.book.snapshot()
        receipt=dict(kind='reconcile',snapshot_id='after-correction',expected_sequence=s['sequence'],cash=s['cash'],positions=s['positions'],
            orders={key:{k:row[k] for k in ('status','filled_quantity','filled_notional','commission')} for key,row in s['orders'].items()})
        feed=self.feed([receipt]);feed['intents']=[intent('next',code=OTHER,now=self.now)]
        report=self.runtime.tick(feed);s=self.runtime.book.snapshot()
        self.assertEqual(report['status'],'ready');self.assertFalse(s['paused']);self.assertIn('dispatch',s['orders']['next'])
        self.assertEqual(s['orders']['next']['filled_quantity'],0)
        self.assertFalse(report['executable']);self.assertEqual(report['counts_as_forward_paper_days'],0)


if __name__=='__main__':unittest.main()
