from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal, _event
from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, intent
from tests.unit.test_offline_dividends import dividend_policy, extended_policy, start
from tests.unit.test_offline_conversions import conversion_policy


class OfflineCorporateReviewTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name)/'review.sqlite'

    def create(self, kind='dividend', rule=None):
        options={'dividend_policy':rule or dividend_policy()} if kind=='dividend' else {'conversion_policy':conversion_policy()}
        self.book=OfflineOrderJournal.create(self.path,initial_cash='2600',initial_positions={SYMBOL:100},
            commission_bps='.5',minimum_commission='5',admission_policy=extended_policy(),**options)
        self.addCleanup(self.book.close);start(self.book,NOW)
        return self.book

    def cancel_order(self, code=SYMBOL):
        self.book.admit(intent(code=code),context(self.book),clock=lambda:NOW)
        self.book.report_status('one','cancel','CANCELLED',0)

    def capture(self, kind='dividend', now=None):
        method=self.book.record_dividend_entitlements if kind=='dividend' else self.book.record_conversion_entitlements
        method(clock=lambda:now or NOW.replace(hour=15))

    def test_late_dividend_fill_keeps_original_rights_and_marks_only_a_candidate_link(self):
        self.create();self.cancel_order();self.capture();self.book.fill('one','late',40,'4')
        before=self.book.snapshot();packet=build_corporate_action_review(self.path)
        action=packet['actions'][0];receipt=action['candidate_receipts'][0]
        self.assertEqual(action['captured_entitlement']['quantity'],100)
        self.assertEqual(packet['account']['positions'][SYMBOL],140)
        self.assertEqual(receipt['payload']['quantity'],40)
        self.assertTrue(receipt['applied_to_book'])
        self.assertFalse(receipt['execution_attribution_confirmed'])
        self.assertIsNone(receipt['actual_execution_at'])
        self.assertTrue(action['missing_evidence'])
        self.assertFalse(packet['automatic_correction_allowed'])
        self.assertNotIn('correction_delta',action)
        self.assertEqual(self.book.snapshot(),before)

    def test_converted_old_unit_receipt_is_retained_without_proposing_new_shares(self):
        self.create('conversion');self.cancel_order();self.capture('conversion')
        self.book.apply_share_conversions(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
        self.book.fill('one','late',40,'4')
        packet=build_corporate_action_review(self.path);action=packet['actions'][0]
        self.assertEqual(packet['account']['positions'][SYMBOL],50)
        self.assertEqual(action['applied_conversion']['new_quantity'],50)
        self.assertEqual(action['unapplied_fills']['late']['quantity'],40)
        self.assertFalse(action['candidate_receipts'][0]['applied_to_book'])
        self.assertEqual(action['captured_entitlement']['quantity'],100)
        self.assertFalse(packet['clears_faults'])

    def test_fill_recorded_before_capture_is_not_presented_as_a_late_candidate(self):
        self.create();self.book.admit(intent(),context(self.book),clock=lambda:NOW)
        self.book.fill('one','early',40,'4');self.book.report_status('one','cancel','CANCELLED',40);self.capture()
        packet=build_corporate_action_review(self.path)
        self.assertEqual(packet['actions'][0]['captured_entitlement']['quantity'],140)
        self.assertEqual(packet['actions'][0]['candidate_receipts'],[])
        self.assertFalse(packet['recorded_corporate_review_required'])
        self.assertEqual(packet['status'],'inspection_only')

    def test_unrelated_symbol_does_not_acquire_a_false_entitlement_link(self):
        self.create();self.cancel_order(OTHER);self.capture();self.book.fill('one','late-other',40,'4')
        packet=build_corporate_action_review(self.path)
        self.assertEqual(packet['actions'][0]['candidate_receipts'],[])
        self.assertTrue(packet['account']['paused'])
        self.assertIn('fill_after_terminal_status',packet['account']['faults'])
        self.assertFalse(packet['recorded_corporate_review_required'])

    def test_pending_order_and_missing_capture_are_not_recovered_or_inferred(self):
        self.create();self.book.admit(intent(),context(self.book),clock=lambda:NOW)
        before=self.book.snapshot();packet=build_corporate_action_review(self.path)
        self.assertIsNone(packet['actions'][0]['captured_entitlement'])
        self.assertEqual(packet['actions'][0]['active_orders']['one']['status'],'PENDING')
        self.assertEqual(self.book.snapshot(),before)
        self.assertFalse(packet['qualifies_for_strategy_promotion'])

    def test_multiple_captures_keep_one_receipt_as_multiple_unconfirmed_candidates(self):
        rules=dividend_policy();rules['events'].append({**rules['events'][0],'event_id':'div-two','record_date':'2026-09-15',
            'ex_date':'2026-09-16','pay_date':'2026-09-16','net_cash_per_share':'0.2'})
        self.create(rule=rules);self.cancel_order();self.capture()
        tomorrow=NOW+timedelta(days=1)
        self.book.accrue_dividends(clock=lambda:tomorrow.replace(hour=9))
        start(self.book,tomorrow,'3.4','cash_dividend:div-one');self.capture(now=tomorrow.replace(hour=15))
        self.book.fill('one','late',40,'4')
        packet=build_corporate_action_review(self.path)
        self.assertEqual(len(packet['actions']),2)
        self.assertEqual([a['candidate_receipts'][0]['payload']['fill_id'] for a in packet['actions']],['late','late'])
        self.assertEqual(packet['actions'][0]['receivable'],'60.00')
        self.assertIsNone(packet['actions'][1]['receivable'])
        self.assertTrue(all(not a['candidate_receipts'][0]['execution_attribution_confirmed'] for a in packet['actions']))

    def test_policy_snapshot_and_events_remain_consistent_when_writer_commits_mid_inspection(self):
        self.create();self.cancel_order();self.capture();before=self.book.snapshot()
        original=OfflineOrderJournal._read;committed=[]
        def read(reader,*args,**kwargs):
            state=original(reader,*args,**kwargs)
            if reader is not self.book and not committed:
                committed.append(True);self.book.set_kill_switch(True,reason='concurrent operator')
            return state
        with patch.object(OfflineOrderJournal,'_read',read):packet=build_corporate_action_review(self.path)
        self.assertEqual(packet['journal']['sequence'],before['sequence'])
        self.assertEqual(packet['journal']['hash'],before['journal_hash'])
        self.assertFalse(packet['account']['kill_switch'])
        self.assertTrue(self.book.snapshot()['kill_switch'])
        self.assertEqual(packet['source_event_count'],before['sequence'])

    def test_size_limits_reject_instead_of_returning_a_partial_packet(self):
        self.create();before=self.book.snapshot()
        for options in ({'max_events':1},{'max_payload_bytes':1},{'max_events':True},{'max_events':0}):
            with self.subTest(options=options),self.assertRaises(ValueError):build_corporate_action_review(self.path,**options)
        self.assertEqual(self.book.snapshot(),before)

    def test_report_edits_cannot_mutate_the_journal_or_the_next_report(self):
        self.create();self.capture();packet=build_corporate_action_review(self.path)
        packet['actions'][0]['rule']['net_cash_per_share']='999'
        packet['actions'][0]['captured_entitlement']['quantity']=999
        packet['account']['faults'].append('fabricated')
        again=build_corporate_action_review(self.path)
        self.assertEqual(again['actions'][0]['rule']['net_cash_per_share'],'0.6')
        self.assertEqual(again['actions'][0]['captured_entitlement']['quantity'],100)
        self.assertNotIn('fabricated',again['account']['faults'])

    def test_paid_dividend_retains_cash_credit_evidence_without_new_receivable(self):
        self.create();self.cancel_order();self.capture()
        self.book.accrue_dividends(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
        self.book.record_dividend_cash_credit('div-one','paid','60',clock=lambda:NOW+timedelta(days=2))
        self.book.fill('one','late',40,'4')
        packet=build_corporate_action_review(self.path);action=packet['actions'][0]
        self.assertTrue(action['paid']);self.assertIsNone(action['receivable'])
        self.assertEqual([row['kind'] for row in action['recorded_action_events']],
            ['DIVIDEND_ENTITLEMENTS','DIVIDEND_ACCRUAL','DIVIDEND_CASH_CREDIT'])
        self.assertEqual(action['recorded_action_events'][-1]['payload']['cash_amount'],'6E+1')
        self.assertEqual(packet['policies']['dividend_policy']['record_cutoff'],'15:00')
        self.assertEqual(action['captured_entitlement']['quantity'],100)

    def test_unattributed_corporate_fault_is_reported_as_missing_evidence(self):
        self.create();self.capture()
        self.book._run(lambda state:_event('FAULT',{'reason':'dividend_entitlement_requires_review'}))
        packet=build_corporate_action_review(self.path)
        self.assertTrue(packet['recorded_corporate_review_required'])
        self.assertEqual(packet['unexplained_review_faults'][0]['fault'],'dividend_entitlement_requires_review')
        self.assertEqual(packet['actions'][0]['candidate_receipts'],[])
        self.assertTrue(packet['actions'][0]['missing_evidence'])

    def test_grouped_capture_does_not_duplicate_other_actions_full_payloads(self):
        rules=dividend_policy();rules['events'].append({**rules['events'][0],'event_id':'other-dividend','symbol':OTHER})
        self.create(rule=rules);self.capture();packet=build_corporate_action_review(self.path)
        self.assertEqual(len(packet['actions']),2)
        for action in packet['actions']:
            event=action['recorded_action_events'][0]
            self.assertEqual(set(event['payload']['entitlements']),{action['event_id']})
            self.assertIn('original_full_event',event['payload_scope'])
        self.assertEqual(packet['actions'][0]['capture_event'],packet['actions'][1]['capture_event'])

    def test_relationship_expansion_limit_refuses_a_partial_review(self):
        self.create();self.capture();before=self.book.snapshot()
        with patch('quant_robot.execution.offline_corporate_review.MAX_REVIEW_ITEMS',1):
            with self.assertRaisesRegex(ValueError,'relationship limit'):
                build_corporate_action_review(self.path)
        self.assertEqual(self.book.snapshot(),before)

    def test_active_order_links_do_not_repeat_the_full_admission_quote_context(self):
        self.create();self.book.admit(intent(),context(self.book),clock=lambda:NOW)
        original=self.book.snapshot()['orders']['one'];self.assertIn('admission',original)
        packet=build_corporate_action_review(self.path)
        linked=packet['actions'][0]['active_orders']['one']
        self.assertEqual(linked['quantity'],100)
        self.assertEqual(linked['status'],'PENDING')
        self.assertNotIn('admission',linked)


if __name__=='__main__':unittest.main()
