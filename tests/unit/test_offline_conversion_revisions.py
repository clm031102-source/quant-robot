from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import fingerprint
from tests.unit.test_offline_conversions import conversion_policy, start
from tests.unit.test_offline_dividends import extended_policy, dividend_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, intent, instrument


def conversion_facts(path, now, key='revision-one',event_id=None):
    view=OfflineOrderJournal.inspect_evidence(path);s=view['snapshot'];rules=view['policies']['conversion_policy']['events']
    rule=rules[0] if event_id is None else next(r for r in rules if r['event_id']==event_id)
    binding=dict(genesis_hash=view['events'][0]['event_hash'],sequence=s['sequence'],hash=s['journal_hash'])
    rows=[r for r in view['events'] if r['event']['kind']=='CONVERSION_UNAPPLIED_FILL' and s['orders'][r['event']['data']['order_id']]['symbol']==rule['symbol']]
    records=[];quantity=s['conversions']['entitlements'][rule['event_id']]['quantity']
    for index,row in enumerate(rows):
        d=row['event']['data'];order=s['orders'][d['order_id']]
        quantity+=(1 if order['side']=='BUY' else -1)*d['quantity']
        records.append(dict(evidence_id='e'+str(index),receipt=dict(sequence=row['sequence'],event_hash=row['event_hash'],order_id=d['order_id'],fill_id=d['fill_id']),
            operation='execution',source=dict(source_id='synthetic',series_id='s'+str(index),message_id='m'+str(index),revision=0,
                previous_evidence_id=None,claimed_artifact_sha256='a'*64),observed_at=(NOW+timedelta(days=1)).isoformat(),
            execution=dict(executed_at=(NOW+timedelta(minutes=1)).isoformat(),quantity=d['quantity'],price=d['price'],
                quantity_basis='pre_action_shares',price_basis='raw_execution',basis_event_id=rule['event_id'])))
    pending=[r['event']['data'] for r in rows if r['event']['data']['fill_id'] not in s['conversions'].get('accounted_fills',{})]
    totals={order_id:s['orders'][order_id]['filled_quantity']+sum(d['quantity'] for d in pending if d['order_id']==order_id) for order_id in {d['order_id'] for d in pending}}
    order_resolutions=[dict(order_id=order_id,final_status='FILLED' if total==s['orders'][order_id]['quantity'] else 'CANCELLED',
        source_ref='synthetic:terminal-order-review',source_sha256=fingerprint([key,order_id,total])) for order_id,total in sorted(totals.items())]
    return dict(schema_version=1,mode='offline_fixture_only',revision_id=key,journal=binding,event_id=rule['event_id'],
        policy_fingerprint=s['conversion_policy_fingerprint'],original_entitlement_fingerprint=fingerprint(s['conversions']['entitlements'][rule['event_id']]),
        original_conversion_fingerprint=fingerprint(s['conversions']['applied'][rule['event_id']]),corrected_old_quantity=quantity,
        facts_as_of=now.isoformat(),entitlement_source=dict(mode='assumed_offline_fixture',source_ref='synthetic:corrected-register',sha256=fingerprint([key,quantity])),
        execution_supplement=dict(schema_version=1,mode='offline_fixture_only',journal=binding,records=records),
        selected_evidence_ids=[r['evidence_id'] for r in records],order_resolutions=order_resolutions)


class OfflineConversionRevisionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'book.sqlite';self.now=NOW+timedelta(days=1,seconds=1)

    def create(self,side='BUY',*,initial=100,qty=40,prior=0,ratio='.5',rounding='ceil_per_holder',resumed=False,
            terminal='CANCELLED',cash='2600',before_late=None,extra_dividend=False,second_conversion=False,second_side=None,other_conversion=False):
        rule=conversion_policy();rule['events'][0].update(share_ratio=ratio,share_rounding=rounding,
            fractional_disposition='fund_assets' if rounding=='floor_per_holder' else 'holder_share_credit')
        admission=extended_policy()
        if second_conversion:
            admission['session_dates']+=['2026-09-17','2026-09-18'];rule['coverage_end']='2026-09-18'
            rule['events'].append({**rule['events'][0],'event_id':'merge-two','record_date':'2026-09-16','suspension_date':'2026-09-17',
                'conversion_date':'2026-09-17','tradable_date':'2026-09-18'})
        if other_conversion:rule['events'].append({**rule['events'][0],'event_id':'other-merge','symbol':OTHER})
        holdings={SYMBOL:initial,**({OTHER:100} if other_conversion else {})}
        self.book=OfflineOrderJournal.create(self.path,initial_cash=cash,initial_positions=holdings,commission_bps='.5',minimum_commission='5',
            admission_policy=admission,conversion_policy=rule,dividend_policy=dividend_policy() if extra_dividend else None);self.addCleanup(self.book.close)
        start(self.book);self.book.admit(intent(side=side),context(self.book),clock=lambda:NOW)
        if prior:self.book.fill('one','prior',prior,'4')
        self.book.report_status('one','cancel',terminal,prior)
        if second_side or other_conversion:
            self.book.admit(intent('two',side=second_side or 'BUY',code=OTHER if other_conversion else SYMBOL),context(self.book),clock=lambda:NOW)
            self.book.report_status('two','cancel-two','CANCELLED',0)
        if extra_dividend:self.book.record_dividend_entitlements(clock=lambda:NOW.replace(hour=15))
        self.book.record_conversion_entitlements(clock=lambda:NOW.replace(hour=15))
        self.book.apply_share_conversions(clock=lambda:NOW+timedelta(days=1))
        if resumed:
            self.now=NOW+timedelta(days=2,seconds=1);start(self.book,NOW+timedelta(days=2),price='8')
        if before_late:before_late(self.book,self.now)
        self.book.fill('one','late',qty,'4')
        if second_side or other_conversion:self.book.fill('two','late-other',qty,'4')
        return self.book

    def facts(self,key='revision-one'):return conversion_facts(self.path,self.now,key)
    def resolve(self,facts=None):return self.book.resolve_conversion_fills(facts or self.facts(),clock=lambda:self.now)
    def reconcile(self):
        s=self.book.snapshot();self.book.reconcile(snapshot_id='reconcile-'+str(s['sequence']),expected_sequence=s['sequence'],cash=s['cash'],positions=s['positions'],
            orders={k:{f:r[f] for f in ('status','filled_quantity','filled_notional','commission')} for k,r in s['orders'].items()})

    def test_buy_corrects_three_unit_spaces_and_cash_but_preserves_original_records(self):
        self.create();before=self.book.snapshot();self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'],{SYMBOL:70});self.assertEqual(Decimal(s['cash']),2435)
        self.assertEqual(s['orders']['one']['filled_quantity'],40);self.assertEqual(Decimal(s['orders']['one']['filled_notional']),160)
        self.assertEqual(Decimal(s['orders']['one']['commission']),5)
        for key in ('entitlements','applied','unapplied_fills'):self.assertEqual(s['conversions'][key],before['conversions'][key])
        self.assertEqual(s['conversions']['unresolved_fills'],{});self.assertEqual(s['conversions']['locks'][SYMBOL]['quantity'],70)
        self.assertEqual(s['sellable_positions'].get(SYMBOL,0),0)
        self.assertNotIn('share_conversion_requires_review',s['faults']);self.assertIn('fill_after_terminal_status',s['faults'])

    def test_sell_and_prepaid_minimum_are_accounted_in_original_order_units(self):
        self.create('SELL',prior=20);self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],20);self.assertEqual(Decimal(s['cash']),2835)
        self.assertEqual(s['orders']['one']['filled_quantity'],60);self.assertEqual(Decimal(s['orders']['one']['commission']),5)

    def test_original_session_does_not_deadlock_resume_and_budget_is_carried_once(self):
        self.create();self.resolve();self.reconcile();resume=NOW+timedelta(days=2)
        start(self.book,resume,price='8');s=self.book.snapshot()
        self.assertEqual(s['risk_session']['carryover_fill_shares'][SYMBOL]['BUY'],20)
        self.assertEqual(s['conversions']['participation']['revision-one']['consumed_session'],'2026-09-16')
        self.assertEqual(s['sellable_positions'][SYMBOL],70);self.assertFalse(s['paused'])
        self.reconcile();self.assertEqual(self.book.snapshot()['risk_session']['carryover_fill_shares'][SYMBOL]['BUY'],20)
        with self.assertRaisesRegex(ValueError,'reset'):start(self.book,resume,price='8')

    def test_current_unit_session_consumes_budget_without_increasing_sellable_or_resetting_baseline(self):
        self.create(resumed=True);before=self.book.snapshot();self.resolve();s=self.book.snapshot()
        self.assertEqual(s['risk_session']['carryover_fill_shares'][SYMBOL]['BUY'],20)
        self.assertEqual(s['sellable_positions'][SYMBOL],50)
        self.assertEqual(s['risk_session']['opening_equity'],before['risk_session']['opening_equity'])

    def test_holder_rounding_zero_delta_still_consumes_participation_and_cash(self):
        self.create(initial=1,qty=1);self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],1);self.assertEqual(Decimal(s['cash']),2591)
        self.assertEqual(s['conversions']['participation']['revision-one']['shares']['BUY'],1)

    def test_two_pending_receipts_apply_holder_rounding_once_and_minimum_once(self):
        self.create(initial=1,qty=1);self.book.fill('one','late-two',1,'4');self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],2);self.assertEqual(Decimal(s['cash']),2587)
        self.assertEqual(Decimal(s['orders']['one']['commission']),5)

    def test_accounted_receipt_is_not_counted_twice_against_original_order_capacity(self):
        self.create();self.resolve();self.book.fill('one','late-two',60,'4');self.resolve(self.facts('revision-two'));s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],100);self.assertEqual(Decimal(s['cash']),2195)
        self.assertEqual(s['orders']['one']['filled_quantity'],100);self.assertEqual(s['orders']['one']['status'],'FILLED')
        self.assertEqual(len(s['conversions']['accounted_fills']),2);self.assertEqual(len(s['conversions']['unapplied_fills']),2)

    def test_duplicate_after_restart_is_noop_and_conflicting_identity_rejects(self):
        self.create();f=self.facts();self.resolve(f);s=self.book.snapshot();self.book.close();self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close)
        self.assertFalse(self.resolve(f));self.assertEqual(self.book.snapshot()['sequence'],s['sequence'])
        changed=deepcopy(f);changed['corrected_old_quantity']+=1
        with self.assertRaisesRegex(ValueError,'conflict'):self.resolve(changed)

    def test_stale_or_incomplete_facts_cannot_apply_cash_or_inventory(self):
        self.create();f=self.facts();f['selected_evidence_ids']=[];before=self.book.snapshot()
        with self.assertRaises(ValueError):self.resolve(f)
        self.assertEqual(self.book.snapshot()['cash'],before['cash']);self.assertEqual(self.book.snapshot()['positions'],before['positions'])
        with self.assertRaisesRegex(ValueError,'stale'):self.resolve(f)

    def test_unknown_or_wrong_units_time_and_changed_fill_are_rejected(self):
        self.create();before=self.book.snapshot()
        for field,value in [('executed_at',None),('executed_at','2026-09-14T15:01:00+08:00'),('quantity_basis','post_action_shares'),('quantity',41),('price','4.1')]:
            with self.subTest(field=field,value=value):
                f=self.facts();f['execution_supplement']['records'][0]['execution'][field]=value
                with self.assertRaises(ValueError):self.resolve(f)
                self.assertEqual(self.book.snapshot()['cash'],before['cash'])

    def test_prior_accounted_evidence_cannot_be_rewritten_by_later_resolution(self):
        self.create();self.resolve();self.book.fill('one','late-two',10,'4');f=self.facts('revision-two')
        f['execution_supplement']['records'][0]['execution']['executed_at']='2026-09-14T10:02:00+08:00'
        with self.assertRaisesRegex(ValueError,'retained|accounted'):self.resolve(f)

    def test_other_fault_operator_stop_and_risk_stop_are_preserved(self):
        self.create(resumed=True);self.book.note_runtime_supervision_fault('fixture-stop');self.book.set_kill_switch(True,reason='fixture operator stop')
        self.resolve();s=self.book.snapshot();self.assertTrue(s['kill_switch']);self.assertIn('runtime_supervision_requires_review',s['faults'])

    def test_low_decimal_precision_does_not_truncate_ratio_cash_or_budget(self):
        self.create(ratio='.83788015')
        with localcontext() as context:
            context.prec=2;self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],118);self.assertEqual(Decimal(s['cash']),2435)
        self.assertEqual(s['conversions']['participation']['revision-one']['shares']['BUY'],34)

    def current_packet(self,book=None,now=None):
        packet=context(book or self.book,now or self.now)
        packet['quotes'][SYMBOL].update(bid='8',ask='8',price_basis_id='share_conversion:merge-one')
        return packet

    def test_terminal_order_evidence_is_required_before_correcting_rejected_order(self):
        self.create(terminal='REJECTED');facts=self.facts();facts['order_resolutions']=[]
        with self.assertRaisesRegex(ValueError,'terminal order'):self.resolve(facts)
        self.assertEqual(self.book.snapshot()['orders']['one']['status'],'REJECTED')
        self.resolve();s=self.book.snapshot();self.assertEqual(s['orders']['one']['status'],'CANCELLED')
        self.assertEqual(s['reserved_positions'],{});self.assertEqual(Decimal(s['reserved_cash']),0)
        self.reconcile();self.assertNotIn('fill_after_terminal_status',self.book.snapshot()['faults'])

    def test_post_conversion_same_symbol_trading_blocks_correction_even_after_full_liquidation(self):
        def trade(book,now):
            book.admit(intent('sale',side='SELL',quantity=50,price='8',now=now),self.current_packet(book,now),clock=lambda:now)
            book.fill('sale','normal-sale',50,'8')
        self.create(resumed=True,before_late=trade);before=self.book.snapshot()
        with self.assertRaisesRegex(ValueError,'subsequent'):self.resolve()
        self.assertEqual(self.book.snapshot()['cash'],before['cash']);self.assertEqual(self.book.snapshot()['conversions']['accounted_fills'],{})

    def test_active_same_symbol_order_prevents_resolution_without_cancelling_it(self):
        def admit(book,now):book.admit(intent('sale',side='SELL',quantity=50,price='8',now=now),self.current_packet(book,now),clock=lambda:now)
        self.create(resumed=True,before_late=admit)
        with self.assertRaisesRegex(ValueError,'active'):self.resolve()
        self.assertEqual(self.book.snapshot()['orders']['sale']['status'],'PENDING')

    def test_actual_cash_deficit_is_recorded_and_preserved_when_money_was_spent_elsewhere(self):
        def spend(book,now):
            book.admit(intent('other',code=OTHER,now=now),self.current_packet(book,now),clock=lambda:now)
            book.fill('other','other-fill',100,'4')
        self.create(resumed=True,cash='405',before_late=spend);self.resolve();s=self.book.snapshot()
        self.assertEqual(Decimal(s['cash']),-165);self.assertEqual(s['positions'][SYMBOL],70)
        self.assertIn('account_or_reservation_deficit',s['faults']);self.assertTrue(s['paused'])

    def test_unknown_same_named_fault_is_not_automatically_cleared(self):
        self.create();self.book._run(lambda state:dict(kind='FAULT',data=dict(reason='share_conversion_requires_review')))
        self.resolve();self.assertIn('share_conversion_requires_review',self.book.snapshot()['faults'])

    def test_later_evidence_cannot_discard_or_restate_an_accounted_source_chain(self):
        self.create();self.resolve();self.book.fill('one','late-two',60,'4');facts=self.facts('revision-two')
        facts['execution_supplement']['records']=facts['execution_supplement']['records'][1:];facts['selected_evidence_ids']=['e1']
        with self.assertRaisesRegex(ValueError,'retained'):self.resolve(facts)
        facts=self.facts('revision-two')
        old=self.book._read()['receipts']['conversion_revision:revision-one']['facts']['entitlement_source']['sha256']
        facts['entitlement_source']['sha256']=old
        with self.assertRaisesRegex(ValueError,'same entitlement source'):self.resolve(facts)

    def test_malformed_facts_and_unsupported_live_mode_are_rejected(self):
        self.create()
        for key,value in [('execution_supplement',None),('journal',[]),('order_resolutions',{}),('mode','live')]:
            f=self.facts();f[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolve(f)
        self.assertEqual(self.book.snapshot()['conversions']['revisions'],{})

    def test_transaction_exception_rolls_back_all_economic_projections(self):
        self.create();before=self.book.snapshot();append=self.book._append
        def fail(state,event):append(state,event);raise RuntimeError('after append')
        with patch.object(self.book,'_append',side_effect=fail),self.assertRaisesRegex(RuntimeError,'after append'):self.resolve()
        self.assertEqual(self.book.snapshot(),before)

    def test_competing_writers_resolve_a_shared_anchor_only_once(self):
        self.create();one=self.facts('one');two=deepcopy(one);two['revision_id']='two';barrier=threading.Barrier(2);outcomes=[]
        def run(facts):
            try:
                with OfflineOrderJournal(self.path) as book:
                    barrier.wait(timeout=5)
                    try:book.resolve_conversion_fills(facts,clock=lambda:self.now);outcomes.append('applied')
                    except ValueError:outcomes.append('rejected')
            except BaseException as exc:outcomes.append(type(exc).__name__+':'+str(exc))
        workers=[threading.Thread(target=run,args=(f,)) for f in (one,two)]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=10)
        self.assertTrue(all(not w.is_alive() for w in workers));self.assertEqual(sorted(outcomes),['applied','rejected'])
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2435)

    def test_real_process_exit_before_and_after_commit_preserves_atomicity_and_deduplication(self):
        self.create();facts=self.facts();source=self.path.parent/'facts.json';source.write_text(json.dumps(facts),encoding='utf-8')
        code="""import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import instant
book=OfflineOrderJournal(sys.argv[1]);facts=json.loads(Path(sys.argv[2]).read_text())
if sys.argv[3]=='before':
    append=book._append
    def stop(state,event):append(state,event);os._exit(73)
    book._append=stop
book.resolve_conversion_fills(facts,clock=lambda:instant(facts['facts_as_of']))
os._exit(73)
"""
        for phase in ('before','after'):
            self.book.close();result=subprocess.run([sys.executable,'-c',code,str(self.path),str(source),phase],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,73,result.stderr);self.book=OfflineOrderJournal(self.path);self.addCleanup(self.book.close)
            self.assertEqual(Decimal(self.book.snapshot()['cash']),2600 if phase=='before' else 2435)
        self.assertFalse(self.resolve(facts));self.assertEqual(len(self.book.snapshot()['conversions']['accounted_fills']),1)

    def test_deferred_participation_actually_blocks_next_buy_at_adv_limit(self):
        self.create(initial=1,qty=1);self.resolve();self.reconcile();self.now=NOW+timedelta(days=2)
        p=self.current_packet();p.update(instruments={s:{**instrument(s),'valid_until':'2026-09-16','adv_shares':'10000'} for s in (SYMBOL,OTHER)},
            sellable_positions=self.book.snapshot()['positions'])
        self.book.begin_session(p,clock=lambda:self.now)
        with self.assertRaisesRegex(ValueError,'ADV participation'):
            self.book.admit(intent('next',price='8',now=self.now),self.current_packet(),clock=lambda:self.now)

    def test_actual_risk_stop_and_prior_peak_remain_after_resolution(self):
        def valuation(book,now):
            p=self.current_packet(book,now);p['quotes'][SYMBOL].update(bid='6',ask='6');book.record_valuation(p,clock=lambda:now)
        self.create(resumed=True,before_late=valuation);before=self.book.snapshot();self.assertTrue(before['risk_session']['risk_stop'])
        self.resolve();s=self.book.snapshot();self.assertTrue(s['risk_session']['risk_stop'])
        for key in ('opening_equity','valuation_peak_equity'):self.assertEqual(s['risk_session'][key],before['risk_session'][key])
        self.assertFalse(s['portfolio_valuation']['matches_current_journal'])

    def test_captured_dividend_dependency_blocks_single_conversion_resolution(self):
        self.create(extra_dividend=True)
        with self.assertRaisesRegex(ValueError,'dividend depends'):self.resolve()
        self.assertEqual(Decimal(self.book.snapshot()['cash']),2600)

    def test_later_captured_conversion_blocks_further_single_action_resolution(self):
        self.create(second_conversion=True);self.resolve();self.reconcile();start(self.book,NOW+timedelta(days=2),price='8')
        self.now=(NOW+timedelta(days=2)).replace(hour=15,minute=0);self.book.record_conversion_entitlements(clock=lambda:self.now)
        self.book.fill('one','late-two',10,'4');self.now+=timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError,'later captured'):self.resolve(self.facts('second'))

    def test_terminal_status_artifact_cannot_be_reused_for_a_conflicting_final_status(self):
        self.create();first=self.facts();self.resolve(first);self.book.fill('one','late-two',60,'4');facts=self.facts('revision-two')
        facts['order_resolutions'][0]['source_sha256']=first['order_resolutions'][0]['source_sha256']
        with self.assertRaisesRegex(ValueError,'same terminal-order source'):self.resolve(facts)

    def test_two_opposite_orders_do_not_net_fees_or_directional_participation(self):
        self.create(qty=20,second_side='SELL');self.resolve();s=self.book.snapshot()
        self.assertEqual(s['positions'][SYMBOL],50);self.assertEqual(Decimal(s['cash']),2590)
        self.assertEqual(s['conversions']['participation']['revision-one']['shares'],{'BUY':10,'SELL':10})
        self.assertEqual(sum(Decimal(r['commission']) for r in s['orders'].values()),10)

    def test_unresolved_other_asset_conversion_keeps_the_shared_fault_until_separately_resolved(self):
        self.create(other_conversion=True);self.resolve();s=self.book.snapshot()
        self.assertIn('share_conversion_requires_review',s['faults']);self.assertEqual(set(s['conversions']['unresolved_fills']),{'late-other'})
        facts=conversion_facts(self.path,self.now,'other-resolution','other-merge');self.resolve(facts);s=self.book.snapshot()
        self.assertNotIn('share_conversion_requires_review',s['faults']);self.assertEqual(s['positions'],{SYMBOL:70,OTHER:70})
