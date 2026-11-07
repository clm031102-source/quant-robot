"""Hand-written ledger/contract counterexamples. Never import the strategy."""
from copy import deepcopy
import calendar
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.research import us_monthly_rotation_verification as V


def hand_cash_ledger():
    dates=[]
    for year,month in [(2000,12)]+[(2001,m) for m in range(1,13)]:
        dates.extend(f'{year}-{month:02d}-{d:02d}' for d in (1,15,calendar.monthrange(year,month)[1]))
    dates+=['2002-01-02','2002-01-03'];first=len(dates)-3;terminal=len(dates)-1
    rows=[]
    for i,day in enumerate(dates):
        prices={a:{k:('1000000' if k=='volume' else '10') for k in ('open','high','low','close','adj_close','volume')} for a in V.ASSETS}
        if i==terminal:
            for p in prices.values():
                for k in ('high','low','close','adj_close','volume'):p[k]=None
        rows.append({'date':day,'prices':prices,'terminal_open_only':i==terminal})
    fixture={'schema':'us_monthly_rotation_fixture_v1','evidence_kind':'artificial','assets':list(V.ASSETS),
        'days':rows,'dividends':[],'first_decision_date':dates[first],'terminal_date':dates[-1],
        'method_sha256':V.METHOD,'provenance':{'constructed_from_market_data':False,'split_policy_verified':True,'capital_gains_present':False}}
    wallet={'spendable_cash':'1000','locked_cash':'0','locks':[],'quantities':dict.fromkeys(V.ASSETS,0),'receivables':{}}
    marks=dict.fromkeys(V.ASSETS,'10');parts=dict.fromkeys(V.PARTS,'0');observations=[];days=[]
    for i in range(first+1,terminal+1):
        start=len(observations)
        for phase in ('prior_held_open','terminal_open_end' if i==terminal else 'completed_close'):
            observations.append(dict(index=i,date=dates[i],phase=phase,marks=deepcopy(marks),balances=deepcopy(wallet),
                NAV='1000',reference_NAV='1000',peak='1000',DD='0',daily_loss='0',fresh_DD_cross=False,day_active=False,
                DD_trigger=False,daily_trigger=False,trigger=False))
        days.append(dict(index=i,date=dates[i],terminal_open_only=i==terminal,before=deepcopy(wallet),after=deepcopy(wallet),
            previous_marks=deepcopy(marks),marks=deepcopy(marks),previous_NAV='1000',NAV='1000',PnL='0',peak='1000',
            observed_maxDD='0',paused=False,cooldown=0,risk_exit_due_index=None,observation_range=[start,len(observations)],attribution=deepcopy(parts)))
    signal=dict(index=first,date=dates[first],prior_date='2000-12-31',returns=dict.fromkeys(V.ASSETS,'0'),positive=[],ranked_positive=[],
        intended_gross='0',weights={'rotation':dict.fromkeys(V.ASSETS,'0'),'positive_equal':dict.fromkeys(V.ASSETS,'0'),
        'fixed_quarters':dict.fromkeys(V.ASSETS,'.25')},ordinary_execution_possible=False)
    summary=dict(initial_cash='1000',terminal_book_NAV='1000',terminal_book_cash='1000',terminal_spendable_cash='1000',
        terminal_locked_cash='0',terminal_receivables='0',terminal_inventory_value='0',terminal_quantities=dict.fromkeys(V.ASSETS,0),
        terminal_book_net_profit='0',terminal_cash_only_net_profit='0',terminal_spendable_cash_net_profit='0',
        terminal_cash_only_definition='includes contracted locked sale proceeds; excludes dividend receivables and remaining inventory; not immediately withdrawable cash',
        terminal_inventory_closed=True,terminal_fully_settled=True,observed_maxDD='0',book_CAGR='0',
        total_commission='0',total_sell_levy='0',total_slippage='0',total_net_dividend='0',same_path_trading_cost_drag='0',
        same_path_before_trading_cost_net_profit='0',cost_headroom_meaning='accounting attribution on the same trades, not a fee-reoptimized portfolio',
        fills=0,rejections=0,accounting_reconciled=True,qualified=False)
    with localcontext(V.CONTEXT):summary['CAGR_years']=str(D(3)/D('365.25'))
    context=dict(prec=40,rounding='ROUND_HALF_UP',Emin=-999999,Emax=999999,capitals=1,clamp=0,
        traps={k.__name__:v for k,v in V.CONTEXT.traps.items()},flags={k.__name__:False for k in V.CONTEXT.flags})
    account=dict(schema='us_monthly_rotation_account_v1',policy='cash',cost_id='min0.35_slip0',minimum_commission='0.35',slippage_bps=0,
        commission_per_share='.005',sell_levy_bps='5',summary=summary,days=days,fills=[],intents=[],signals=[signal],
        monthly_events=[dict(decision_index=first,date=dates[first],signal=deepcopy(signal),policy='cash',status='skipped_cash_risk_or_terminal',targets={},sell_orders=[],buy_orders=[])],
        actions=[],rejections=[],risk_records=[],risk_observations=observations,unknown_execution_constraints=[],annual_contributions={'2002':'0'},
        attribution=parts,terminal_locks=[],terminal_receivable_items={},pending=None,FIFO_lots={a:[] for a in V.ASSETS},
        evidence_kind='artificial',historical_returns_computed=False,test_injected_values=False,qualified=False,real_forward=0,
        method_sha256=V.METHOD,fixture_sha256=V.digest(fixture),provenance_sha256=V.digest(fixture['provenance']),registration_sha256=None,
        runtime={'context_initial':context,'context_final':deepcopy(context)})
    return fixture,account


class USVerifierTests(unittest.TestCase):
    def test_direct_historical_fixture_requires_registration_and_completion(self):
        fixture,_=hand_cash_ledger();fixture['evidence_kind']='known_history_conditional'
        fixture['provenance'].update(constructed_from_market_data=True,registration_sha256='a'*64)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def save(name,obj):
                raw=json.dumps(obj).encode();(root/name).write_bytes(raw)
                return {'path':name,'sha256':hashlib.sha256(raw).hexdigest()}
            ref=save('decoded.json',fixture)
            with self.assertRaisesRegex(ValueError,'registration_hash'):
                V.verify_recorded_accounts(root,ref,{},ref,None)
            marker=save('complete.json',{'status':'complete','account_id':'wrong','registration_sha256':'a'*64,'artifact':ref})
            accounts={f'min{m}_slip{s}/{p}':{'artifact':ref,'completion':marker,'summary':{}} for m,s in V.COSTS for p in V.POLICIES}
            accounts['cash']={'artifact':ref,'completion':marker,'summary':{}}
            with self.assertRaisesRegex(ValueError,'completion_identity'):
                V.verify_recorded_accounts(root,ref,accounts,ref,'a'*64)

    def test_hand_written_cash_ledger_and_NAV_fee_tampering(self):
        f,a=hand_cash_ledger();result=V.verify_account(f,a)
        self.assertEqual((result['days'],result['fills'],result['risk_observations']),(2,0,4))
        for field in ('NAV','fee','risk','annual'):
            with self.subTest(field=field):
                bad=deepcopy(a)
                if field=='NAV':bad['days'][0]['NAV']='1001'
                elif field=='fee':bad['summary']['total_commission']='.01'
                elif field=='risk':bad['risk_observations'][0]['DD']='.01'
                else:bad['annual_contributions']['2002']='1'
                with self.assertRaises(ValueError):V.verify_account(f,bad)

    def test_fee_tick_levy_and_negative_syntax(self):
        with localcontext(V.CONTEXT):
            self.assertEqual(V.fee(71,'0.35'),D('.36'))
            self.assertEqual(V.execution_price(D('10'),'buy',10),D('10.01'))
            self.assertEqual(V.execution_price(D('10'),'sell',10),D('9.99'))
            self.assertEqual((D('9.99')*7*D('.0005')).quantize(D('.01'),rounding='ROUND_CEILING'),D('.04'))
        for token in (float('nan'),True,'NaN'):
            with self.subTest(token=str(token)),self.assertRaises(ValueError):V.decimal(token)

    def test_hand_entitlement_and_T3_lock_reject_tampering(self):
        with localcontext(V.CONTEXT):
            expected=V.dividend_item('SPY',3,'.055','2006-01-03')
        self.assertEqual(expected['gross'],D('.165'))
        self.assertEqual(expected['amount'],D('.12'))
        self.assertEqual(expected['earliest_payment_date'],'2006-02-17')
        for field,value in [('amount','.13'),('quantity',4),('earliest_payment_date','2006-02-16')]:
            bad=deepcopy(expected);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):V.same(expected,bad,'entitlement')
        dates=['2006-01-03','2006-01-04','2006-01-05','2006-01-06']
        lock=V.sale_lock(4,0,D('9.63'),dates)
        self.assertEqual((lock['release_index'],lock['release_date']),(3,'2006-01-06'))
        for field,value in [('release_index',2),('amount','9.64')]:
            bad=deepcopy(lock);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):V.same(lock,bad,'lock')

    def test_signal_formula_cannot_accept_tampered_rank(self):
        f,a=hand_cash_ledger();bad=deepcopy(a['signals']);bad[0]['ranked_positive']=['SPY']
        with self.assertRaises(ValueError):V.verify_signals(f,bad)

    def test_constant_annual_statistics_have_exact_constant_intervals(self):
        import numpy as np
        years=[str(y) for y in range(2006,2025)];annual={};keys=[]
        for m,s in V.COSTS:
            k=f'min{m}_slip{s}'
            annual[k]={p:dict.fromkeys(years,v) for p,v in zip(V.POLICIES,('3','2','1'))}
            keys.extend(k+'/'+e for e in ('net','minus_positive_equal','minus_fixed_quarters'))
        column=np.asarray([3.,1.,2.]*9);means=np.tile(column,(5000,1));mapping=dict(zip(keys,column.tolist()))
        actual=dict(status='computed_seen_trace_sensitivity',evidence_kind='artificial',historical_returns_computed=False,
            qualified=False,N=19,years=years,block=2,seed=20261107,generator='PCG64',replications=5000,starts_per_replication=10,
            truncate_rows_to=19,shared_indices_for_all27=True,endpoint_keys=keys,units='USD_per_observed_year',statistic='arithmetic_mean_annual_PnL',
            lower=mapping.copy(),upper=mapping.copy(),observed_means=mapping.copy(),quantiles=[.025,.975],quantile_method='linear',
            replicate_means_sha256=hashlib.sha256(means.astype('<f8').tobytes()).hexdigest(),numpy_version=np.__version__)
        V.verify_statistics(annual,actual,'artificial',False)
        actual['lower'][keys[0]]=4.
        with self.assertRaises(ValueError):V.verify_statistics(annual,actual,'artificial',False)


if __name__=='__main__':unittest.main()
