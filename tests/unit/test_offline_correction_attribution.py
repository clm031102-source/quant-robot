from datetime import timedelta
from decimal import Decimal,localcontext
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from quant_robot.execution.offline_correction_attribution import build_correction_attribution
from quant_robot.execution.offline_corporate_review import build_corporate_action_review
from tests.unit.test_offline_dividend_revision_runtime import create_fixture as dividend_fixture
from tests.unit.test_offline_dividend_revisions import revision_facts
from tests.unit.test_offline_conversion_revision_runtime import create_fixture as conversion_fixture
from tests.unit.test_offline_conversion_revisions import conversion_facts
from tests.unit.test_offline_conversions import conversion_policy,start as conversion_start
from tests.unit.test_offline_dividends import dividend_policy,extended_policy,start as dividend_start
from tests.unit.test_offline_order_admission import NOW,SYMBOL,OTHER,context,intent,instrument


class OfflineCorrectionAttributionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'book.sqlite'

    def dividend(self,side='SELL'):
        dividend_fixture(self.path,side);self.now=NOW+timedelta(days=1,seconds=1)
        self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close)
        facts=revision_facts(self.book,self.path,self.now);self.book.revise_dividend_entitlement(facts,clock=lambda:self.now)
        if side=='SELL':self.book.record_dividend_cash_refund('div-one','refund','24',expected_revision_id='revision-one',clock=lambda:self.now)
        else:self.book.record_dividend_cash_installment('div-one','extra','24',clock=lambda:self.now)
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        self.book.record_valuation(p,clock=lambda:self.now)

    def conversion(self,*,reference=True,initial=100,qty=40,side='BUY',quote_status='TRADING',quote_basis='share_conversion:merge-one'):
        self.now=NOW+timedelta(days=1,seconds=1)
        self.book=OfflineOrderJournal.create(self.path,initial_cash='2600',initial_positions={SYMBOL:initial},commission_bps='.5',minimum_commission='5',
            admission_policy=extended_policy(),conversion_policy=conversion_policy());self.addCleanup(self.book.close)
        conversion_start(self.book);self.book.admit(intent(side=side),context(self.book),clock=lambda:NOW);self.book.report_status('one','cancel','CANCELLED',0)
        self.book.record_conversion_entitlements(clock=lambda:NOW.replace(hour=15));self.book.apply_share_conversions(clock=lambda:NOW+timedelta(days=1))
        self.book.fill('one','late',qty,'4');self.book.resolve_conversion_fills(conversion_facts(self.path,self.now),clock=lambda:self.now)
        if reference:
            s=self.book.snapshot();self.book.reconcile(snapshot_id='done',expected_sequence=s['sequence'],cash=s['cash'],positions=s['positions'],
                orders={k:{f:r[f] for f in ('status','filled_quantity','filled_notional','commission')} for k,r in s['orders'].items()})
            self.now=NOW+timedelta(days=2);opening=context(self.book,self.now)
            opening['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id=quote_basis,trade_status=quote_status)
            opening.update(instruments={s:{**instrument(s),'valid_until':'2026-09-16'} for s in (SYMBOL,OTHER)},sellable_positions=self.book.snapshot()['positions'])
            self.book.begin_session(opening,clock=lambda:self.now)
            p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id=quote_basis,trade_status=quote_status);self.book.record_valuation(p,clock=lambda:self.now)

    def test_late_dividend_sell_gain_is_offset_by_rights_revision_and_refund_has_no_equity_gain(self):
        self.dividend();r=build_correction_attribution(self.path);rows={row['kind']:row for row in r['movements']}
        self.assertEqual(Decimal(rows['FILL']['recognized_correction_effect']),19)
        self.assertEqual(Decimal(rows['DIVIDEND_ENTITLEMENT_REVISION']['recognized_correction_effect']),-24)
        self.assertEqual(Decimal(rows['DIVIDEND_CASH_REFUND']['recognized_correction_effect']),0)
        self.assertEqual(Decimal(r['groups'][0]['listed_movement_effect_at_reference']),-5)
        self.assertFalse(r['restated_performance_complete']);self.assertFalse(r['qualifies_for_strategy_promotion'])

    def test_late_dividend_buy_and_cash_installment_do_not_double_count_rights(self):
        self.dividend('BUY');r=build_correction_attribution(self.path);rows={row['kind']:row for row in r['movements']}
        self.assertEqual(Decimal(rows['FILL']['recognized_correction_effect']),-29)
        self.assertEqual(Decimal(rows['DIVIDEND_ENTITLEMENT_REVISION']['recognized_correction_effect']),24)
        self.assertEqual(Decimal(rows['DIVIDEND_CASH_INSTALLMENT']['recognized_correction_effect']),0)
        self.assertEqual(Decimal(r['groups'][0]['listed_movement_effect_at_reference']),-5)

    def test_conversion_old_principal_new_shares_and_fee_reconcile_at_recorded_mark(self):
        self.conversion();r=build_correction_attribution(self.path);row=r['movements'][0]
        self.assertEqual(Decimal(row['cash_delta']),-165);self.assertEqual(row['share_delta'],20)
        self.assertEqual(Decimal(row['principal_and_rights_effect']),0);self.assertEqual(Decimal(row['fee_effect']),-5)
        self.assertEqual(Decimal(row['rounding_effect']),0);self.assertEqual(Decimal(row['recognized_correction_effect']),-5)
        self.assertEqual(row['reference']['mark'],'8');self.assertTrue(row['reference']['retrospective'])

    def test_holder_rounding_loss_is_not_hidden_inside_the_commission(self):
        self.conversion(initial=1,qty=1);row=build_correction_attribution(self.path)['movements'][0]
        self.assertEqual(row['share_delta'],0);self.assertEqual(Decimal(row['unrounded_share_delta']),Decimal('.5'))
        self.assertEqual(Decimal(row['rounding_effect']),-4);self.assertEqual(Decimal(row['fee_effect']),-5)
        self.assertEqual(Decimal(row['recognized_correction_effect']),-9)

    def test_no_valid_reference_keeps_effect_unknown_without_inferring_conversion_price(self):
        self.conversion(reference=False);r=build_correction_attribution(self.path);row=r['movements'][0]
        self.assertEqual(r['status'],'reference_gaps');self.assertIsNone(row['recognized_correction_effect']);self.assertIsNone(row['reference'])
        self.assertIsNone(r['groups'][0]['listed_movement_effect_at_reference'])
        self.assertEqual(Decimal(row['cash_delta']),-165)

    def test_zero_current_share_delta_still_requires_a_reference_for_rounding_decomposition(self):
        self.conversion(reference=False,initial=1,qty=1);row=build_correction_attribution(self.path)['movements'][0]
        self.assertEqual(row['share_delta'],0);self.assertIsNone(row['rounding_effect']);self.assertIsNone(row['reference'])
        self.assertEqual(Decimal(row['recognized_correction_effect']),-9)

    def test_revision_before_accrual_separates_original_accrual_from_correction_component(self):
        rules=dividend_policy();rules['events'][0]['pay_date']='2026-09-15'
        self.book=OfflineOrderJournal.create(self.path,initial_cash='2600',initial_positions={SYMBOL:100},commission_bps='.5',minimum_commission='5',
            admission_policy=extended_policy(),dividend_policy=rules);self.addCleanup(self.book.close)
        dividend_start(self.book,NOW);self.book.admit(intent(),context(self.book),clock=lambda:NOW);self.book.report_status('one','cancel','CANCELLED',0)
        self.book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15));self.book.fill('one','late',40,'4')
        now=NOW.replace(hour=15,minute=1);self.book.revise_dividend_entitlement(revision_facts(self.book,self.path,now),clock=lambda:now)
        self.book.accrue_dividends(clock=lambda:NOW+timedelta(days=1));r=build_correction_attribution(self.path)
        row=next(r for r in r['movements'] if r['kind']=='DIVIDEND_ACCRUAL')
        self.assertEqual(Decimal(row['receivable_delta']),84);self.assertEqual(Decimal(row['baseline_accrual']),60)
        self.assertEqual(Decimal(row['recognized_correction_effect']),24)
        revision=next(r for r in r['movements'] if r['kind']=='DIVIDEND_ENTITLEMENT_REVISION')
        self.assertEqual(Decimal(revision['recognized_correction_effect']),0)

    def test_report_cannot_recover_a_pending_order_or_modify_the_source(self):
        self.conversion();self.book.admit(intent('next',code=OTHER,now=self.now),self.current_context(),clock=lambda:self.now)
        before=self.book.snapshot();digest=hashlib.sha256(self.path.read_bytes()).hexdigest();report=build_correction_attribution(self.path)
        self.assertEqual(self.book.snapshot(),before);self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),digest)
        self.assertEqual(self.book.snapshot()['orders']['next']['status'],'PENDING');self.assertFalse(report['executable'])

    def current_context(self):
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id='share_conversion:merge-one');return p

    def test_limits_reject_partial_attribution_and_caller_precision_does_not_change_effects(self):
        self.dividend()
        with self.assertRaises(ValueError):build_correction_attribution(self.path,max_events=1)
        with self.assertRaises(ValueError):build_correction_attribution(self.path,max_movements=1)
        with localcontext() as precision:
            precision.prec=2;r=build_correction_attribution(self.path)
        self.assertEqual(Decimal(r['groups'][0]['listed_movement_effect_at_reference']),-5)

    def test_report_marks_are_evidence_refs_and_returned_data_isolated_from_source(self):
        self.dividend();r=build_correction_attribution(self.path);ref=r['groups'][0]['reference']
        self.assertEqual(ref['kind'],'PORTFOLIO_VALUATION');self.assertGreater(ref['sequence'],max(row['sequence'] for row in r['movements']))
        self.assertEqual(len(ref['event_hash']),64);r['movements'][0]['cash_delta']='999999'
        self.assertNotEqual(build_correction_attribution(self.path)['movements'][0]['cash_delta'],'999999')

    def test_full_liquidation_uses_independently_validated_supplied_quote(self):
        self.conversion(side='SELL',qty=100);s=self.book.snapshot();self.assertNotIn(SYMBOL,s['portfolio_valuation']['last_valid']['marks'])
        row=build_correction_attribution(self.path)['movements'][0]
        self.assertEqual(row['share_delta'],-50);self.assertEqual(Decimal(row['recognized_correction_effect']),-5)

    def test_unheld_nontrading_quote_cannot_become_an_attribution_reference(self):
        self.conversion(side='SELL',qty=100,quote_status='HALTED');r=build_correction_attribution(self.path)
        self.assertEqual(r['status'],'reference_gaps');self.assertIsNone(r['movements'][0]['reference'])

    def test_multiple_revisions_link_the_original_fill_without_counting_it_twice(self):
        self.dividend();self.book.fill('one','late-two',10,'4');facts=revision_facts(self.book,self.path,self.now,'revision-two')
        facts['entitlement_source']['sha256']='c'*64;self.book.revise_dividend_entitlement(facts,clock=lambda:self.now)
        self.book.record_dividend_cash_refund('div-one','refund-two','6',expected_revision_id='revision-two',clock=lambda:self.now)
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one');self.book.record_valuation(p,clock=lambda:self.now)
        r=build_correction_attribution(self.path);fills=[row for row in r['movements'] if row['kind']=='FILL']
        self.assertEqual(len(fills),2);self.assertEqual(len(fills[0]['supporting_revision_events']),2)
        self.assertEqual(Decimal(r['groups'][0]['listed_movement_effect_at_reference']),-5)

    def test_unheld_wrong_basis_quote_cannot_price_old_correction_units(self):
        self.conversion(side='SELL',qty=100,quote_basis='unknown-old-units');r=build_correction_attribution(self.path)
        self.assertEqual(r['status'],'reference_gaps');self.assertIsNone(r['movements'][0]['reference'])

    def test_integrated_review_uses_one_read_view_for_account_and_attribution(self):
        self.dividend();original=OfflineOrderJournal.inspect_evidence
        with patch.object(OfflineOrderJournal,'inspect_evidence',wraps=original) as read:
            report=build_corporate_action_review(self.path,include_attribution=True)
        self.assertEqual(read.call_count,1)
        self.assertEqual(report['journal']['hash'],report['correction_attribution']['journal']['hash'])
        self.assertEqual(Decimal(report['correction_attribution']['groups'][0]['listed_movement_effect_at_reference']),-5)

    def test_cli_exports_requested_attribution_without_changing_source_or_default_output(self):
        self.dividend();before=self.book.snapshot();output=self.path.parent/'review.json'
        result=subprocess.run([sys.executable,'scripts/run_offline_corporate_review.py','--journal',str(self.path),'--output',str(output),'--include-attribution'],
            cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);report=json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(report['correction_attribution']['status'],'listed_movements_reconciled');self.assertEqual(self.book.snapshot(),before)
        self.assertNotIn('correction_attribution',build_corporate_action_review(self.path))

    def test_unlinked_ordinary_trade_cost_is_excluded_from_listed_correction_effect(self):
        self.conversion();self.book.admit(intent('ordinary',code=OTHER,now=self.now),self.current_context(),clock=lambda:self.now)
        self.book.fill('ordinary','ordinary-fill',100,'4');self.book.record_valuation(self.current_context(),clock=lambda:self.now)
        r=build_correction_attribution(self.path)
        self.assertEqual(r['excluded_unlinked_fill_count'],1);self.assertEqual(Decimal(r['groups'][0]['listed_movement_effect_at_reference']),-5)
        self.assertEqual(Decimal(self.book.snapshot()['portfolio_valuation']['last_valid']['book_equity']),2990)
        self.assertFalse(r['return_series_derived'])

    def test_unresolved_original_receipt_is_not_treated_as_an_accepted_correction(self):
        conversion_fixture(self.path);r=build_correction_attribution(self.path)
        self.assertEqual(r['status'],'no_recorded_corrections');self.assertEqual(r['movements'],[])
        self.assertEqual(Decimal(OfflineOrderJournal.inspect_snapshot(self.path)['cash']),2600)
