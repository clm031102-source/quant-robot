from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import fingerprint
from quant_robot.execution.offline_order_state import DIVIDEND_ENTITLEMENT_UNCERTAIN
from tests.unit.test_offline_dividends import dividend_policy,extended_policy,start
from tests.unit.test_offline_order_admission import NOW,SYMBOL,OTHER,context,intent


def revision_facts(book,path,now,revision_id='revision-one'):
    view=OfflineOrderJournal.inspect_evidence(path);snapshot=view['snapshot'];rule=view['policies']['dividend_policy']['events'][0]
    action=rule['event_id'];capture=next(row for row in view['events'] if row['event']['kind']=='DIVIDEND_ENTITLEMENTS' and action in row['event']['data']['entitlements'])
    rows=[row for row in view['events'] if row['event']['kind']=='FILL' and row['sequence']>capture['sequence']
        and snapshot['orders'][row['event']['data']['order_id']]['symbol']==rule['symbol']]
    binding=dict(genesis_hash=view['events'][0]['event_hash'],sequence=snapshot['sequence'],hash=snapshot['journal_hash'])
    records=[];quantity=snapshot['dividends']['entitlements'][action]['quantity']
    for index,row in enumerate(rows):
        data=row['event']['data'];order=snapshot['orders'][data['order_id']]
        quantity+=(1 if order['side']=='BUY' else -1)*data['quantity']
        records.append(dict(evidence_id='e'+str(index),receipt=dict(sequence=row['sequence'],event_hash=row['event_hash'],order_id=data['order_id'],fill_id=data['fill_id']),
            operation='execution',source=dict(source_id='synthetic',series_id='series'+str(index),message_id='message'+str(index),revision=0,
                previous_evidence_id=None,claimed_artifact_sha256='a'*64),observed_at=now.isoformat(),
            execution=dict(executed_at=(NOW+timedelta(minutes=1)).isoformat(),quantity=data['quantity'],price=data['price'],
                quantity_basis='unconverted_shares',price_basis='raw_execution',basis_event_id=None)))
    settlement_keys=sorted(row['event']['receipt_key'] for row in view['events'] if row['event'].get('receipt_key','').startswith('dividend_cash:')
        and row['event']['data'].get('event_id')==action)
    return dict(schema_version=1,mode='offline_fixture_only',revision_id=revision_id,journal=binding,event_id=action,
        policy_fingerprint=snapshot['dividend_policy_fingerprint'],original_entitlement_fingerprint=fingerprint(snapshot['dividends']['entitlements'][action]),
        corrected_quantity=quantity,record_date=rule['record_date'],facts_as_of=now.isoformat(),
        entitlement_source=dict(mode='assumed_offline_fixture',source_ref='synthetic:register-restatement',sha256='b'*64),
        settlement_receipt_keys=settlement_keys,
        execution_supplement=dict(schema_version=1,mode='offline_fixture_only',journal=binding,records=records),
        receipt_decisions=[dict(evidence_id=row['evidence_id'],entitlement_effect='included') for row in records])


class OfflineDividendRevisionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.path=self.root/'book.sqlite';self.now=NOW+timedelta(days=1,seconds=1)

    def create(self,side='SELL',*,paid=True,accrued=True,quantity=40,initial=100,rate='.6',extra_rule=False,cash='2600'):
        rule=dividend_policy();rule['events'][0].update(pay_date='2026-09-15',net_cash_per_share=rate)
        if extra_rule:rule['events'].append({**rule['events'][0],'event_id':'div-two','record_date':'2026-09-15','ex_date':'2026-09-16','pay_date':'2026-09-16'})
        self.book=OfflineOrderJournal.create(self.path,initial_cash=cash,initial_positions={SYMBOL:initial},commission_bps='.5',minimum_commission='5',
            admission_policy=extended_policy(),dividend_policy=rule);self.addCleanup(self.book.close)
        start(self.book,NOW);self.book.admit(intent(side=side),context(self.book),clock=lambda:NOW)
        self.book.report_status('one','cancel','CANCELLED',0)
        self.book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15))
        if accrued:
            self.book.accrue_dividends(clock=lambda:(NOW+timedelta(days=1)).replace(hour=9))
            start(self.book,NOW+timedelta(days=1),'3.4','cash_dividend:div-one')
            if paid:
                owed=self.book.snapshot()['dividends']['receivables']['div-one']
                self.book.record_dividend_cash_credit('div-one','original-payment',owed,clock=lambda:NOW+timedelta(days=1))
        else:self.now=NOW.replace(hour=15,minute=1)
        self.book.fill('one','late',quantity,'4')
        return self.book

    def facts(self,key='revision-one'):return revision_facts(self.book,self.path,self.now,key)
    def revise(self,facts=None):return self.book.revise_dividend_entitlement(facts or self.facts(),clock=lambda:self.now)
    def refund(self,key,value,revision='revision-one'):
        return self.book.record_dividend_cash_refund('div-one',key,value,expected_revision_id=revision,clock=lambda:self.now)
    def reconcile(self):
        s=self.book.snapshot();self.book.reconcile(snapshot_id='complete-'+str(s['sequence']),expected_sequence=s['sequence'],cash=s['cash'],positions=s['positions'],
            orders={key:{k:row[k] for k in ('status','filled_quantity','filled_notional','commission')} for key,row in s['orders'].items()})
    def valuation(self):
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        self.book.record_valuation(p,clock=lambda:self.now);return self.book.snapshot()['portfolio_valuation']['last_valid']

    def test_paid_reduction_creates_payable_and_reserves_cash_without_moving_it(self):
        self.create();before=self.book.snapshot();self.revise();after=self.book.snapshot()
        self.assertEqual(after['cash'],before['cash']);self.assertEqual(after['positions'],before['positions'])
        self.assertEqual(after['dividends']['entitlements'],before['dividends']['entitlements'])
        self.assertEqual(Decimal(after['dividends']['payable_total']),24)
        self.assertEqual(Decimal(after['available_cash']),Decimal(after['cash'])-24)
        self.assertEqual(after['dividends']['revisions']['div-one']['quantity'],60)
        self.assertNotIn(DIVIDEND_ENTITLEMENT_UNCERTAIN,after['faults'])
        self.assertIn('fill_after_terminal_status',after['faults'])
        value=self.valuation();self.assertEqual(Decimal(value['book_equity']),2995)
        self.assertEqual(Decimal(value['dividend_payable']),24)
        self.assertEqual(Decimal(value['dividend_adjustment_since_open']),-24)
        self.assertEqual(value['performance_attribution_status'],'requires_restatement')

    def test_paid_increase_creates_receivable_and_supplemental_payment_does_not_duplicate_cash(self):
        self.create('BUY');before=self.book.snapshot();self.revise()
        self.assertEqual(self.book.snapshot()['cash'],before['cash'])
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['receivable_total']),24)
        self.assertNotIn('div-one',self.book.snapshot()['dividends']['paid'])
        self.book.record_dividend_cash_installment('div-one','supplement','24',clock=lambda:self.now)
        self.assertEqual(Decimal(self.book.snapshot()['cash']),Decimal(before['cash'])+24)
        self.assertEqual(Decimal(self.valuation()['book_equity']),2995)

    def test_refunds_reduce_payable_in_steps_and_preserve_equity(self):
        self.create();self.revise();before=self.book.snapshot();equity=Decimal(self.valuation()['book_equity'])
        for key,value,owed in [('refund-one','10','14'),('refund-two','14','0')]:
            self.assertTrue(self.refund(key,value));s=self.book.snapshot()
            self.assertEqual(Decimal(s['dividends']['payable_total']),Decimal(owed))
            self.assertEqual(Decimal(self.valuation()['book_equity']),equity)
        self.assertEqual(Decimal(self.book.snapshot()['cash']),Decimal(before['cash'])-24)
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['settled_net']['div-one']),36)

    def test_revision_and_refund_replay_after_restart_are_idempotent(self):
        self.create();facts=self.facts();self.revise(facts);self.refund('refund','10');self.book.close()
        self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close);before=self.book.snapshot()
        self.assertFalse(self.revise(facts));self.assertFalse(self.refund('refund','10'))
        self.assertEqual(self.book.snapshot(),before)

    def test_conflicting_revision_refund_and_cross_direction_receipt_ids_are_rejected(self):
        self.create();facts=self.facts();self.revise(facts);changed=deepcopy(facts);changed['corrected_quantity']=61
        with self.assertRaisesRegex(ValueError,'conflicting'):self.revise(changed)
        with self.assertRaisesRegex(ValueError,'conflicting'):self.refund('original-payment','24')
        self.refund('refund','10')
        with self.assertRaisesRegex(ValueError,'conflicting'):self.refund('refund','11')
        with self.assertRaisesRegex(ValueError,'conflicting'):
            self.book.record_dividend_cash_installment('div-one','refund','10',clock=lambda:self.now)

    def test_stale_anchor_missing_settlement_or_unexplained_quantity_cannot_revise(self):
        self.create();base=self.facts();before=self.book.snapshot()
        for change in (lambda p:p['journal'].update(hash='f'*64),lambda p:p.update(settlement_receipt_keys=[]),lambda p:p.update(corrected_quantity=61),
                lambda p:p.update(original_entitlement_fingerprint='f'*64),lambda p:p.update(policy_fingerprint='f'*64)):
            packet=deepcopy(base);change(packet)
            with self.assertRaises(ValueError):self.revise(packet)
            current=self.book.snapshot();self.assertEqual(current['cash'],before['cash']);self.assertEqual(current['dividends']['entitlements'],before['dividends']['entitlements'])
            base=self.facts()

    def test_unknown_inconsistent_or_unselected_execution_assertions_cannot_revise(self):
        self.create()
        for change in (lambda p:p.update(receipt_decisions=[]),lambda p:p['execution_supplement']['records'][0]['execution'].update(executed_at=None),
                lambda p:p['execution_supplement']['records'][0]['execution'].update(quantity=39),
                lambda p:p['execution_supplement']['records'][0]['execution'].update(quantity_basis='unknown'),
                lambda p:p['receipt_decisions'][0].update(entitlement_effect='excluded')):
            p=self.facts();change(p)
            with self.assertRaises(ValueError):self.revise(p)
        self.assertEqual(self.book.snapshot()['dividends']['revisions'],{})

    def test_before_ex_date_revision_changes_effective_rights_without_accruing_cash(self):
        self.create('BUY',accrued=False);before=self.book.snapshot();self.revise()
        self.assertEqual(self.book.snapshot()['cash'],before['cash'])
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['receivable_total']),0)
        self.assertEqual(self.book.snapshot()['dividends']['entitlements']['div-one']['quantity'],100)
        self.reconcile();self.now=(NOW+timedelta(days=1)).replace(hour=9)
        self.book.accrue_dividends(clock=lambda:self.now)
        self.assertEqual(Decimal(self.book.snapshot()['dividends']['receivable_total']),84)

    def test_unpaid_reduction_changes_receivable_and_never_creates_payable(self):
        self.create(paid=False);self.revise();s=self.book.snapshot()
        self.assertEqual(Decimal(s['dividends']['receivable_total']),36)
        self.assertEqual(Decimal(s['dividends']['payable_total']),0)

    def test_full_holder_rounding_uses_total_quantities(self):
        self.create('BUY',initial=1,quantity=1,rate='.005');self.revise();s=self.book.snapshot()
        self.assertEqual(Decimal(s['dividends']['revisions']['div-one']['net_amount']),Decimal('.01'))
        self.assertEqual(Decimal(s['dividends']['revisions']['div-one']['net_adjustment']),0)
        self.assertEqual(Decimal(s['dividends']['receivable_total']),0)

    def test_zero_or_excess_refund_or_wrong_revision_is_rejected(self):
        self.create();self.revise();before=self.book.snapshot()['cash']
        for value in ('0','-1','.001','24.01','61'):
            with self.subTest(value=value),self.assertRaises(ValueError):self.refund('bad',value)
        with self.assertRaises(ValueError):self.refund('wrong','10','other-revision')
        self.assertEqual(self.book.snapshot()['cash'],before)

    def test_mid_transaction_failure_leaves_no_partial_revision_or_refund(self):
        self.create();before=self.book.snapshot();original=self.book._append
        def fail(state,event):original(state,event);raise OSError('injected before commit')
        with patch.object(self.book,'_append',side_effect=fail),self.assertRaises(OSError):self.revise()
        self.assertEqual(self.book.snapshot(),before);self.revise();before=self.book.snapshot()
        with patch.object(self.book,'_append',side_effect=fail),self.assertRaises(OSError):self.refund('refund','10')
        self.assertEqual(self.book.snapshot(),before);self.assertTrue(self.refund('refund','10'))

    def test_other_stops_and_risk_peak_survive_entitlement_revision(self):
        self.create();self.book.set_kill_switch(True,reason='operator stop');self.book.note_runtime_supervision_fault('monitor loss')
        value=self.valuation();before=self.book.snapshot();self.revise();after=self.book.snapshot()
        self.assertTrue(after['kill_switch']);self.assertIn('runtime_supervision_requires_review',after['faults'])
        self.assertIn('fill_after_terminal_status',after['faults'])
        self.assertEqual(after['risk_session']['valuation_peak_equity'],before['risk_session']['valuation_peak_equity'])
        self.assertGreaterEqual(Decimal(self.valuation()['book_equity_peak']),Decimal(value['book_equity_peak']))

    def test_refund_reserve_blocks_a_buy_that_gross_cash_would_cover(self):
        self.create(cash='200');self.revise();self.reconcile();before=self.book.snapshot()
        self.assertEqual(Decimal(before['cash']),415);self.assertEqual(Decimal(before['available_cash']),391)
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        with self.assertRaisesRegex(ValueError,'cash'):self.book.admit(intent('new',code=OTHER,now=self.now),p,clock=lambda:self.now)
        self.refund('refund','24');self.assertEqual(Decimal(self.book.snapshot()['available_cash']),391)

    def test_next_session_opening_equity_deducts_unpaid_refund(self):
        self.create(cash='200');self.revise();self.reconcile();self.now=NOW+timedelta(days=2)
        start(self.book,self.now,'3.4','cash_dividend:div-one')
        self.assertEqual(Decimal(self.book.snapshot()['risk_session']['opening_equity']),595)
        self.assertEqual(Decimal(self.valuation()['dividend_adjustment_since_open']),0)

    def test_revision_cannot_silently_replace_old_source_evidence(self):
        self.create();self.revise();facts=self.facts('second')
        facts['execution_supplement']['records'][0]['source']['claimed_artifact_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'previous evidence'):self.revise(facts)

    def first_excluded_revision(self):
        facts=self.facts();facts['corrected_quantity']=100;facts['receipt_decisions'][0]['entitlement_effect']='excluded'
        facts['execution_supplement']['records'][0]['execution']['executed_at']=(NOW+timedelta(days=1)-timedelta(minutes=1)).isoformat()
        self.revise(facts);return facts

    def corrected_second_facts(self,first):
        second=self.facts('second');old=deepcopy(first['execution_supplement']['records'][0]);new=deepcopy(old)
        new['evidence_id']='e0-corrected';new['operation']='correction'
        new['source'].update(message_id='corrected-message',revision=1,previous_evidence_id='e0',claimed_artifact_sha256='c'*64)
        new['execution']['executed_at']=(NOW+timedelta(minutes=1)).isoformat()
        second['execution_supplement']['records']=[old,new]
        second['receipt_decisions']=[dict(evidence_id=new['evidence_id'],entitlement_effect='included')]
        second['entitlement_source']['sha256']='c'*64
        return second

    def test_second_source_revision_can_add_a_payable_and_stop_previously_reserved_dispatch(self):
        self.create(cash='200');first=self.first_excluded_revision();self.reconcile()
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        self.book.admit(intent('pending',code=OTHER,now=self.now),p,clock=lambda:self.now)
        second=self.corrected_second_facts(first);self.revise(second)
        s=self.book.snapshot();self.assertEqual(Decimal(s['reserved_cash']),405)
        self.assertEqual(Decimal(s['dividends']['payable_total']),24);self.assertIn('account_or_reservation_deficit',s['faults'])
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        with self.assertRaisesRegex(ValueError,'deficit'):self.book.prepare_dispatch('pending','dispatch',p,clock=lambda:self.now)

    def test_same_entitlement_source_cannot_assert_a_different_quantity(self):
        self.create();first=self.first_excluded_revision();second=self.corrected_second_facts(first)
        second['entitlement_source']['sha256']=first['entitlement_source']['sha256']
        with self.assertRaisesRegex(ValueError,'entitlement source'):self.revise(second)

    def test_entitlement_source_conflicts_are_checked_against_all_previous_revisions(self):
        self.create();first=self.first_excluded_revision();second=self.corrected_second_facts(first);self.revise(second)
        third=self.facts('third');third['execution_supplement']['records']=deepcopy(second['execution_supplement']['records'])
        third['receipt_decisions']=deepcopy(second['receipt_decisions']);third['entitlement_source']['sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'entitlement source'):self.revise(third)

    def test_refund_reservation_checks_ignore_low_caller_decimal_precision(self):
        self.create(cash='214.50');self.revise();self.reconcile()
        p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
        with localcontext() as precision:
            precision.prec=2
            self.book.admit(intent('exact',code=OTHER,now=self.now),p,clock=lambda:self.now)
            p=context(self.book,self.now);p['quotes'][SYMBOL].update(bid='3.4',ask='3.4',price_basis_id='cash_dividend:div-one')
            self.book.prepare_dispatch('exact','exact-dispatch',p,clock=lambda:self.now)
        self.assertEqual(Decimal(self.book.snapshot()['available_cash']),Decimal('.50'))

    def test_competing_revisions_use_one_original_anchor(self):
        self.create();first=self.facts('one');second=deepcopy(first);second['revision_id']='two'
        barrier=threading.Barrier(2);outcomes=[]
        def write(facts):
            try:
                with OfflineOrderJournal(self.path) as book:
                    barrier.wait(timeout=5)
                    try:book.revise_dividend_entitlement(facts,clock=lambda:self.now);outcomes.append('applied')
                    except ValueError:outcomes.append('rejected')
            except BaseException as exc:outcomes.append(type(exc).__name__+':'+str(exc))
        workers=[threading.Thread(target=write,args=(facts,)) for facts in (first,second)]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=10)
        self.assertTrue(all(not worker.is_alive() for worker in workers));self.assertEqual(sorted(outcomes),['applied','rejected'])
        view=OfflineOrderJournal.inspect_evidence(self.path)
        self.assertEqual(sum(row['event']['kind']=='DIVIDEND_ENTITLEMENT_REVISION' for row in view['events']),1)

    def test_later_capture_prevents_single_action_revision(self):
        self.create(extra_rule=True);self.revise();self.reconcile()
        self.now=(NOW+timedelta(days=1)).replace(hour=15,minute=0)
        self.book.record_dividend_entitlements(clock=lambda:self.now)
        self.now+=timedelta(minutes=1)
        with self.assertRaisesRegex(ValueError,'later captured'):self.revise(self.facts('second'))

    def test_unknown_fault_without_receipt_attribution_is_not_cleared(self):
        self.create();self.book._run(lambda state:dict(kind='FAULT',data=dict(reason=DIVIDEND_ENTITLEMENT_UNCERTAIN)))
        self.revise();self.assertIn(DIVIDEND_ENTITLEMENT_UNCERTAIN,self.book.snapshot()['faults'])

    def test_malformed_fact_containers_are_rejected_as_value_errors(self):
        self.create()
        for key,value in [('execution_supplement',None),('execution_supplement',[]),('journal',None),('journal',True)]:
            facts=self.facts();facts[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.revise(facts)

    def crash_command(self,operation,phase,facts):
        source=self.root/('facts-'+operation+'-'+phase+'.json');source.write_text(json.dumps(facts),encoding='utf-8')
        root=Path(__file__).resolve().parents[2]
        code="""import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import instant
path,source,operation,phase=sys.argv[1:]
facts=json.loads(Path(source).read_text());book=OfflineOrderJournal(path)
if phase=='before_commit':
    original=book._append
    def stop(state,event):original(state,event);os._exit(73)
    book._append=stop
if operation=='revision':book.revise_dividend_entitlement(facts,clock=lambda:instant(facts['facts_as_of']))
else:book.record_dividend_cash_refund('div-one','crash-refund','10',expected_revision_id='revision-one',clock=lambda:instant(facts['facts_as_of']))
os._exit(73)
"""
        self.book.close()
        result=subprocess.run([sys.executable,'-c',code,str(self.path),str(source),operation,phase],cwd=root,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,73,result.stderr)
        self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close)

    def test_real_process_exit_before_and_after_revision_commit_is_atomic(self):
        for phase in ('before_commit','after_commit'):
            self.path=self.root/(phase+'.sqlite');self.create();facts=self.facts();before=self.book.snapshot()
            self.crash_command('revision',phase,facts)
            if phase=='before_commit':self.assertEqual(self.book.snapshot(),before);self.assertTrue(self.revise(facts))
            else:self.assertFalse(self.revise(facts));self.assertEqual(Decimal(self.book.snapshot()['dividends']['payable_total']),24)
            self.book.close()

    def test_real_process_exit_before_and_after_refund_commit_is_atomic(self):
        for phase in ('before_commit','after_commit'):
            self.path=self.root/(phase+'.sqlite');self.create();facts=self.facts();self.revise(facts);before=self.book.snapshot()
            self.crash_command('refund',phase,facts)
            if phase=='before_commit':self.assertEqual(self.book.snapshot(),before);self.assertTrue(self.refund('crash-refund','10'))
            else:self.assertFalse(self.refund('crash-refund','10'));self.assertEqual(Decimal(self.book.snapshot()['dividends']['payable_total']),14)
            self.book.close()


if __name__=='__main__':unittest.main()
