"""Fixed annual dividend-style endpoint cost screen, not an account simulation."""
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
import json
import io
import math
import numpy as np
import pandas as pd

from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
from quant_robot.research.disclosed_flow_diagnostic import open_return
from quant_robot.research.rrr_effective_diagnostic import describe, reviewed_actions, endpoint as benchmark_endpoint
from quant_robot.research.us_variance_risk_diagnostic import price_anchors


def annual_intervals(sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered CN sessions required')
    first={}
    for year in range(2008,2025):
        days=[d for d in sessions if d.startswith(str(year)+'-')]
        if not days: raise ValueError('Every fixed calendar year required')
        first[year]=days[0]
    rows=[dict(year=y,entry_date=first[y],exit_date=first[y+1],
        sessions=sessions.index(first[y+1])-sessions.index(first[y])) for y in range(2008,2024)]
    if any(not 1<=r['sessions']<=252 for r in rows):
        raise ValueError('Fixed252session holding cap exceeded')
    return rows


def _decimal(value, *, positive=False):
    x=Decimal(str(value))
    if not x.is_finite() or (x<=0 if positive else x<0):
        raise ValueError('Finite valid nonnegative value required')
    return x


def endpoint(entry,exit_,entry_open,exit_open,actions,minimum,slippage_bp):
    if date.fromisoformat(entry)>=date.fromisoformat(exit_):
        raise ValueError('Strictly forward endpoints required')
    a,b=_decimal(entry_open,positive=True),_decimal(exit_open,positive=True)
    minimum,slip=_decimal(minimum),_decimal(slippage_bp)/10000
    if slip>=1: raise ValueError('Slippage must be below100percent')
    buy=(a*(1+slip)).quantize(Decimal('.001'),rounding=ROUND_CEILING)
    sell=(b*(1-slip)).quantize(Decimal('.001'),rounding=ROUND_FLOOR)
    if sell<=0: raise ValueError('Positive rounded sell quote required')
    def fee(value):
        return max(minimum,value*Decimal('.0005')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    quantity=int(Decimal(1000)//(buy*100))*100
    while quantity and quantity*buy+fee(quantity*buy)>1000: quantity-=100
    if len({r['record_date'] for r in actions})!=len(actions):
        raise ValueError('Unique cash distribution identities required')
    cash=Decimal(0)
    for r in actions:
        if (r['asset_id']!='CN_ETF_XSHG_510880' or r['kind']!='cash_dividend'
                or r['cash_amount_basis']!='gross' or r['record_date']>=r['ex_date']):
            raise ValueError('Reviewed gross510880cash distributions required')
        amount=_decimal(r['cash_per_share'],positive=True)
        if entry<=r['record_date']<exit_: cash+=amount
    buy_fee=fee(quantity*buy) if quantity else Decimal(0)
    sell_fee=fee(quantity*sell) if quantity else Decimal(0)
    debit=quantity*buy+buy_fee
    credit=quantity*sell-sell_fee
    cash*=quantity
    return dict(shares=quantity,raw_entry_open=float(a),raw_exit_open=float(b),
        modeled_buy_price=float(buy),modeled_sell_price=float(sell),buy_debit_CNY=float(debit),
        exit_credit_CNY=float(credit),cash_entitlement_CNY=float(cash),
        total_commission_CNY=float(buy_fee+sell_fee),net_PnL_CNY=float(credit+cash-debit),
        one_share_gross_return=open_return(entry,exit_,a,b,actions))


def parse_opens(raw,sessions,anchors):
    wire=json.loads(raw)
    if wire.get('code')!='510880' or any(len(r)!=2 for r in wire['kline']):
        raise ValueError('Exact510880date/open schema required')
    dates=[datetime.strptime(str(r[0]),'%Y%m%d').date().isoformat() for r in wire['kline']]
    expected=[d for d in sessions if anchors[0]<=d<=anchors[-1]]
    if (dates!=expected or anchors!=sorted(set(anchors)) or any(d>'2024-01-02' for d in anchors)):
        raise ValueError('Exact fixed historical ETF date coverage required')
    opens={d:r[1] for d,r in zip(dates,wire['kline'],strict=True) if d in anchors}
    if sorted(opens)!=anchors or any(not math.isfinite(float(v)) or float(v)<=0 for v in opens.values()):
        raise ValueError('Complete positive fixed historical opens required')
    return opens


def summarize(rows):
    if ([r['year'] for r in rows]!=list(range(2008,2024))
            or any(not math.isfinite(r['net_PnL_CNY']) for r in rows)):
        raise ValueError('Exactly16ordered finite annual outcomes required')
    full=describe(rows);later=describe([r for r in rows if r['year']>=2020])
    starts=np.random.default_rng(20260921).integers(0,16,size=(5000,8))
    ids=((starts[:,:,None]+np.arange(2))%16).reshape(5000,16)
    draws=np.array([r['net_PnL_CNY'] for r in rows])[ids].mean(axis=1)
    ci=[float(x) for x in np.quantile(draws,[.025,.975])]
    checks=dict(executed_count=full['executed']>=12,later_executed_count=later['executed']>=4,
        full_mean_positive=full['mean_net_PnL_CNY']>0,later_mean_positive=later['mean_net_PnL_CNY']>0,
        positive_frequency=full['positive_frequency']>=.55,block_lower_positive=ci[0]>0)
    return dict(full=full,later_2020_onward=later,annual_block=dict(mean_PnL_CNY_2_5_97_5=ci,
        block_annual_opportunities=2,replications=5000,seed=20260921),checks=checks,
        endpoint_cost_screen_passed=all(checks.values()),net_positive_EV_verified=False,
        fresh_OOS=False,multiple_testing_adjusted=False,historical_vintage_verified=False,daily_risk_validated=False)


def study_sessions(snapshots):
    sessions=[]
    for role,start,end in [('early_calendar',date(2008,1,1),date(2011,12,31)),
            ('old_calendar',date(2012,1,1),date(2014,12,31)),('calendar',date(2015,1,1),date(2024,6,28))]:
        rows=calendar_rows_from_snapshot(snapshots[role],snapshots[role+'_manifest'],start=start,end=end)
        sessions.extend(str(d) for d,opened in rows if opened)
    if sessions!=sorted(set(sessions)): raise ValueError('Merged CN calendar is not unique and ordered')
    return sessions


def calculate(snapshots):
    ledger=json.loads(snapshots['source_ledger'])
    if (ledger['status']!='conditional_current_official_source_reconciliation_complete'
            or ledger['returns_calculated'] is not False or len(ledger['annual_reports'])!=16
            or any(r['residual']!=0 for r in ledger['annual_reports'])):
        raise ValueError('Reviewed source ledger required')
    sessions=study_sessions(snapshots)
    rows=annual_intervals(sessions)
    if rows!=ledger['intervals']: raise ValueError('Annual dates differ from frozen source ledger')
    anchors=sorted({r[k] for r in rows for k in ('entry_date','exit_date')})
    actions=ledger['events']
    if len(actions)!=16 or len({r['record_date'] for r in actions})!=16:
        raise ValueError('Exactly16reviewed cash distributions required')
    for r in actions:
        if (r['record_date'] not in sessions or r['ex_date'] not in sessions
                or sessions.index(r['record_date'])+1!=sessions.index(r['ex_date'])):
            raise ValueError('Record/ex session order differs')
    opens=parse_opens(snapshots['dividend_prices'],sessions,anchors)
    for year in range(2020,2025):
        check=pd.read_parquet(io.BytesIO(snapshots[f'raw_crosscheck_{year}']),
            columns=['symbol','date','open'],filters=[('symbol','==','510880.SH')])
        day=next(d for d in anchors if d.startswith(str(year)))
        if (len(check)!=1 or check.iloc[0]['symbol']!='510880.SH'
                or pd.Timestamp(check.iloc[0]['date']).date().isoformat()!=day
                or _decimal(check.iloc[0]['open'],positive=True)!=_decimal(opens[day],positive=True)):
            raise ValueError('SSEopen and retained raw Tushare anchor differ')
    scenarios=[]
    for minimum in (0,5,10):
        for slip in (0,10,30):
            observations=[{**r,**endpoint(r['entry_date'],r['exit_date'],opens[r['entry_date']],
                opens[r['exit_date']],actions,minimum,slip)} for r in rows]
            scenarios.append(dict(minimum_commission_CNY=minimum,slippage_bp=slip,observations=observations,
                full=describe(observations),later_2020_onward=describe([r for r in observations if r['year']>=2020])))
    main=next(r for r in scenarios if r['minimum_commission_CNY']==5 and r['slippage_bp']==10)
    common=[r for r in rows if r['year']>=2013]
    benchmark_anchors=sorted({r[k] for r in common for k in ('entry_date','exit_date')})
    benchmark_opens=price_anchors(snapshots,benchmark_anchors,[d for d in sessions if d>='2013-01-01'])
    benchmark_actions=reviewed_actions(snapshots,sessions)
    benchmark=[{**r,**benchmark_endpoint(r['entry_date'],r['exit_date'],benchmark_opens[r['entry_date']],
        benchmark_opens[r['exit_date']],benchmark_actions,5,10)} for r in common]
    return dict(diagnostic=summarize(main['observations']),scenarios=scenarios,observations=main['observations'],
        descriptive_comparisons=dict(cash_PnL_CNY=0,common_entry_years=list(range(2013,2024)),
            dividend_style=describe([r for r in main['observations'] if r['year']>=2013]),
            broad_equity=describe(benchmark),broad_equity_observations=benchmark,not_alpha_qualification=True),
        ETF_open_values_used={'510880':len(opens),'510300':len(benchmark_opens)},net_account_run=False,
        completed_account_trade_count=None,new_forward_paper_days=0,
        price_basis='raw_open_modeled_adverse_ticks_plus_entitled_gross_cash',
        dividend_pay_date_cash_availability_modeled=False,invariant_index_method_assumed=False)
