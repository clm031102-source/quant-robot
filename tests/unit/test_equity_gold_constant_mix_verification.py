"""Handwritten accounting fixtures: no strategy import or account simulation."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal, getcontext, localcontext
from pathlib import Path

from quant_robot.research import equity_gold_constant_mix_verification as V

A, B = 'HAND_EQUITY', 'HAND_GOLD'


def serial(value):
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, dict): return {k:serial(v) for k,v in value.items()}
    if isinstance(value, list): return [serial(v) for v in value]
    return value


def state(cash, quantity_a, quantity_b, *, locked=0, rights=None, receivables=None):
    return dict(book_cash=Decimal(cash),spendable_cash=Decimal(cash)-Decimal(locked),locked_sale_cash=Decimal(locked),
                quantities={A:quantity_a,B:quantity_b},rights=copy.deepcopy(rights or {}),receivables=copy.deepcopy(receivables or {}))


def hand_case(*, risk=False, cash_only=False):
    """A fixed six-day distribution ledger, or eleven days with an explicit stop.

    Low case: buy100+100 at1, cash9790; ex10 cash right offsets A drop.1;
    pay cash9800; sell85+95 at terminal -> cash9980, totalfees20.
    Risk case: buy4000+4000,cash1990; ex400 offsets A drop.1, B drops.5;
    NAV7990 triggers pause; next open sell3595+1995, pay400 -> cash7980.
    """
    with localcontext(V.CONTEXT):
        terminal=30 if risk else 25
        dates=[(date(2001,1,1)+timedelta(days=i)).isoformat() for i in range(terminal+1)]
        bars={a:[dict(open='1',close='1',volume='1000000',suspended=False,buy_blocked=False,sell_blocked=False) for _ in dates] for a in (A,B)}
        for i in range(22,terminal+1):
            bars[A][i].update(open='.9',close='.9')
            if risk:bars[B][i].update(open='.5',close='.5')
        fixture=dict(assets=[A,B],dates=dates,bars=bars,event_indices=[20],terminal_index=terminal,
                     actions=[] if cash_only else [dict(event_id='div',asset=A,known_index=20,record_index=21,ex_index=22,pay_index=23,cash_per_share='.1',share_multiplier='1')])
        runtime=dict(context_initial=dict(prec=40,rounding='ROUND_HALF_UP',Emin=-999999,Emax=999999,capitals=1,clamp=0,
                     traps={k.__name__:v for k,v in V.CONTEXT.traps.items()},flags={k.__name__:False for k in V.CONTEXT.flags}))
        runtime['context_final']=copy.deepcopy(runtime['context_initial'])
        account=dict(policy='cash' if cash_only else 'constant_mix',cost_id='min5_slip0',minimum_commission=5,slippage_bps=0,
                     commission_bps=5,minimum0_counterfactual=False,method_sha256=V.METHOD,fixture_sha256=V._digest(fixture),qualified=False,
                     real_forward=0,historical_returns_computed=False,runtime=runtime,intents=[],fills=[],rejections=[],days=[],risk_records=[],
                     action_records=[],capacity_failures=[],unknown_execution_constraints=[],FIFO_lots={A:[],B:[]})
        q=4000 if risk else 100
        exit_i=23 if risk else terminal
        rights={'div':dict(asset=A,quantity=q,ex_index=22,pay_index=23,included_in_NAV=False)}
        receivable={'div':dict(amount=Decimal(q)/10,quantity=q,pay_index=23)}
        prebuy=state(10000,0,0)
        postbuy=state(10000-2*q-10,q,q)
        recorded=state(10000-2*q-10,q,q,rights=rights)
        ex=state(10000-2*q-10,q,q,receivables=receivable)
        paid=state(10000-2*q-10+q//10,q,q)
        terminal_cash=7980 if risk else 9980
        flat=state(terminal_cash,0,0)
        fills_by_day={}
        def order(i,a,side,quantity,budget=None):
            n=len(account['intents'])
            account['intents'].append(dict(intent_id=n,index=i,asset=a,side=side,quantity=quantity,
                phase='quarter_buy' if side=='buy' else ('quarter_sell' if i==20 else 'risk_exit' if risk and i==23 else 'terminal'),
                frozen_budget=budget,prior_close=Decimal(bars[a][i-1]['close']),prior_capacity=10000))
            return n
        def fill(i,a,side,quantity,price,before,after,budget=None):
            n=order(i,a,side,quantity,budget)
            row=dict(intent_id=n,index=i,date=dates[i],asset=a,side=side,quantity=quantity,raw_open=Decimal(price),price=Decimal(price),
                notional=quantity*Decimal(price),fee=Decimal(5),slippage_cost=Decimal(0),phase=account['intents'][-1]['phase'],
                fee_payment=dict(from_current_sale=Decimal(5) if side=='sell' else Decimal(0),from_free_cash=Decimal(5) if side=='buy' else Decimal(0),from_locked_sale=Decimal(0)),
                frozen_budget=budget,before=before,after=after)
            account['fills'].append(row);fills_by_day.setdefault(i,[]).append(row)
        if not cash_only:
            order(20,A,'sell',0);order(20,B,'sell',0)
            half=state(9995-q,q,0)
            fill(21,A,'buy',q,'1',prebuy,half,Decimal(5000))
            fill(21,B,'buy',q,'1',half,postbuy,Decimal(5000))
            ab=ex if risk else paid
            first_proceeds=Decimal(q)*Decimal('.9')-5
            middle=state(ab['book_cash']+first_proceeds,0,q,locked=first_proceeds,receivables=receivable if risk else None)
            last_proceeds=Decimal(q)*(Decimal('.5') if risk else Decimal(1))-5
            end_sales=state(middle['book_cash']+last_proceeds,0,0,locked=first_proceeds+last_proceeds,receivables=receivable if risk else None)
            fill(exit_i,A,'sell',q,'.9',ab,middle)
            fill(exit_i,B,'sell',q,'.5' if risk else '1',middle,end_sales)
            for i in range(exit_i+1,terminal+1):
                if i==terminal:order(i,A,'sell',0);order(i,B,'sell',0)
            account['action_records']=[dict(index=21,event_id='div',kind='record_right',quantity=q,before=postbuy,after=recorded),
                dict(index=22,event_id='div',kind='ex_receivable',amount=Decimal(q)/10,before=recorded,after=ex),
                dict(index=23,event_id='div',kind='pay_after_fills',amount=Decimal(q)/10,before=end_sales if risk else ex,
                     after=state(terminal_cash,0,0,locked=first_proceeds+last_proceeds) if risk else paid)]
            account['FIFO_lots']={a:[dict(start_index=21,initial=q,remaining=0)] for a in (A,B)}
        else:
            order(terminal,A,'sell',0);order(terminal,B,'sell',0)
        previous=Decimal(10000);peak=Decimal(10000);allparts=dict.fromkeys(V.COMPONENTS,Decimal(0))
        last=prebuy
        for i in range(20,terminal+1):
            before=copy.deepcopy(last)
            if cash_only or i==20:after=prebuy
            elif i==21:after=recorded
            elif i==22:after=ex
            elif risk or i==terminal:after=flat
            else:after=paid
            release=copy.deepcopy(after)
            if not cash_only and i==exit_i:release['locked_sale_cash']=first_proceeds+last_proceeds;release['spendable_cash']-=first_proceeds+last_proceeds
            marks={a:Decimal(bars[a][i]['open' if i==terminal else 'close']) for a in (A,B)}
            prevmarks={a:Decimal(bars[a][i-1]['close']) for a in (A,B)}
            nav=Decimal(10000) if cash_only or i==20 else Decimal(9990) if i==21 or not risk and i<terminal else Decimal(7990) if i==22 else Decimal(terminal_cash)
            parts=dict(carried_exposure=Decimal(0),trade_timing=Decimal(0),dividend_entitlement=Decimal(0),commission=Decimal(0),slippage=Decimal(0))
            if not cash_only:
                if i==21 or i==exit_i:parts['commission']=Decimal(-10)
                if i==22:parts['carried_exposure']=Decimal(-2400 if risk else -10);parts['dividend_entitlement']=Decimal(q)/10
            exposed=not cash_only and 21<=i<=exit_i
            dd=(peak-nav)/peak
            paused=risk and 22<=i<28
            mandatory=risk and i==22
            flat_index=23 if risk and 23<=i<28 else None
            account['days'].append(dict(index=i,date=dates[i],terminal_open_stub=i==terminal,before=before,after=after,
                previous_raw_marks=prevmarks,before_close_cash_release=release,marks=marks,NAV=nav,previous_NAV=previous,peak=peak,DD=dd,
                had_exposure=exposed,paused=paused,mandatory_exit=mandatory,flat_index=flat_index,attribution=parts))
            for k in V.COMPONENTS:allparts[k]+=parts[k]
            last=after;previous=nav
        if risk and not cash_only:
            account['risk_records']=[dict(index=22,kind='daily_2percent_pause',previous_NAV=Decimal(9990),NAV=Decimal(7990),peak=Decimal(10000),DD=Decimal('.201')),
                dict(index=23,kind='flat_cooldown_started',earliest_open_index=29),dict(index=28,kind='eligible_from_next_session_only_next_quarter')]
        account['initial_snapshot']=dict(cash=Decimal(10000) if cash_only else postbuy['book_cash'],quantities={A:0,B:0} if cash_only else {A:q,B:q},
            rights={} if cash_only else rights,receivables={},fees=Decimal(0) if cash_only else Decimal(10))
        account['event_attempts']=[dict(index=20,date=dates[20],sell_fills=0,buy_fills=0 if cash_only else 2)]
        account['annual_contributions']={'2001':previous-10000};account['attribution']=allparts
        account['summary']=dict(terminal_cash=previous,terminal_book_NAV=previous,terminal_quantities={A:0,B:0},terminal_receivables={},terminal_unexercised_rights={},
            unexercised_rights_included_in_NAV=False,terminal_unsettled=False,terminal_cash_netPnL=previous-10000,terminal_cash_netPnL_is_fully_settled=True,
            book_netPnL=previous-10000,observed_maxDD=(10000-previous)/10000,risk_ceiling_pass=True,fill_count=0 if cash_only else 4,
            completed_FIFO_purchase_lots=0 if cash_only else 2,complete_policy_exposure_cycles=0 if cash_only else 1,two_sided_rebalance_events=0,
            initial_two_assets_filled=not cash_only,total_commission=Decimal(0) if cash_only else Decimal(20),total_slippage=Decimal(0),attribution_reconciled=True,
            capacity_pass=True,financial_verdict='not_evaluated_artificial_engineering_only')
        return serial(fixture),serial(account)


class ConstantMixVerificationTests(unittest.TestCase):
    def test_hand_cash_distribution_fifo_and_cooldown(self):
        for kwargs, expected in (({'cash_only':True},'0'),({},'-20'),({'risk':True},'-2020')):
            with self.subTest(kwargs=kwargs):
                fixture,account=hand_case(**kwargs)
                r=V.verify_account(fixture,account)
                self.assertEqual(Decimal(r['summary']['book_netPnL']),Decimal(expected))

    def test_corrupt_economic_fields_not_only_artifact_hash(self):
        fixture,original=hand_case()
        mutations=[lambda a:a['fills'][0].update(fee='6'),lambda a:a['fills'][0]['fee_payment'].update(from_locked_sale='5'),
            lambda a:a['days'][2].update(NAV='9991'),lambda a:a['action_records'][1].update(amount='11'),
            lambda a:a['FIFO_lots'][A][0].update(remaining=1),lambda a:a['summary'].update(terminal_cash='9999'),
            lambda a:a['annual_contributions'].update({'2001':'0'}),lambda a:a['fills'][0].update(index=True)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                account=copy.deepcopy(original);mutate(account)
                with self.assertRaises(ValueError):V.verify_account(fixture,account)

    def test_risk_false_fields_and_cooldown_are_checked(self):
        fixture,original=hand_case(risk=True)
        for mutate in (lambda a:a['risk_records'][0].update(DD='.2'),lambda a:a['days'][3].update(flat_index=22),
                       lambda a:a['risk_records'][1].update(earliest_open_index=28)):
            account=copy.deepcopy(original);mutate(account)
            with self.assertRaises(ValueError):V.verify_account(fixture,account)

    def test_known_constraint_and_capacity_counterfacts_reject(self):
        fixture,account=hand_case()
        fixture['bars'][A][21]['suspended']=True;account['fixture_sha256']=V._digest(fixture)
        with self.assertRaisesRegex(ValueError,'rejected_order_filled'):V.verify_account(fixture,account)
        fixture,account=hand_case();fixture['bars'][A][21]['volume']='1';account['fixture_sha256']=V._digest(fixture)
        with self.assertRaises(ValueError):V.verify_account(fixture,account)

    def test_context_isolation_and_invalid_number(self):
        fixture,account=hand_case();context=getcontext();before=context.copy()
        V.verify_account(fixture,account)
        self.assertEqual(context.flags,before.flags);self.assertEqual(context.prec,before.prec)
        account['fills'][0]['fee']='invalid'
        with self.assertRaises(ValueError):V.verify_account(fixture,account)
        self.assertEqual(context.flags,before.flags)

    def test_exit_fee_free_cash_then_locked_cash_no_borrow(self):
        with localcontext(V.CONTEXT):
            cash,locked,free,used=V._settle_sale(Decimal('.10'),Decimal(0),Decimal(100),Decimal(5))
            self.assertEqual((cash,locked,free,used),(Decimal('95.10'),Decimal(95),Decimal(0),Decimal(0)))
            cash,locked,free,used=V._settle_sale(cash,locked,Decimal('.10'),Decimal(5))
            self.assertEqual((cash,locked,free,used),(Decimal('90.20'),Decimal('90.20'),Decimal('.10'),Decimal('4.80')))
            with self.assertRaisesRegex(ValueError,'unfinanced_sale'):
                V._settle_sale(Decimal('.10'),Decimal(0),Decimal('.10'),Decimal(5))

    def test_root_containment_hash_and_size(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'x.json';p.write_bytes(b'{}')
            ref=dict(path='x.json',sha256=hashlib.sha256(b'{}').hexdigest(),bytes=2)
            self.assertEqual(V._bound(root,ref),b'{}')
            for patch in ({'path':'../x.json'},{'bytes':3},{'sha256':'0'*64}):
                with self.assertRaises(ValueError):V._bound(root,dict(ref,**patch))

    def test_independent_zero_statistics_and_tampering(self):
        import numpy as np
        years=[str(y) for y in range(2014,2024)]
        annual={f'min{m}_slip{s}':{p:dict.fromkeys(years,'0') for p in ('constant_mix','drift')} for m,s in V.COSTS}
        keys=[f'min{m}_slip{s}/{e}' for m,s in V.COSTS for e in ('net','increment')]
        expected_hash=hashlib.sha256(bytes(5000*18*8)).hexdigest()
        stats=dict(status='computed_artificial_fixed_trace_sensitivity',source_nature='test_artificial_values_true_calendar',qualified=False,N=10,years=years,
            replications=5000,seed=20261107,block=2,starts_per_replication=5,shared_indices_for_all18=True,units='CNY_per_artificial_year',
            statistic='arithmetic_mean_annual_PnL',endpoint_keys=keys,lower=dict.fromkeys(keys,0.0),observed_means=dict.fromkeys(keys,0.0),
            replicate_means_sha256=expected_hash,quantile=.05/18,quantile_method='linear',numpy_version=np.__version__,historical_returns_computed=False)
        self.assertEqual(V.verify_statistics(annual,stats,stats['source_nature'],False),expected_hash)
        stats['lower'][keys[0]]=1.0
        with self.assertRaises(ValueError):V.verify_statistics(annual,stats,stats['source_nature'],False)


if __name__=='__main__':unittest.main()
