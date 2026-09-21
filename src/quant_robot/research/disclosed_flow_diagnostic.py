"""Fixed conditional monthly flow diagnostic; preserve unknown-state bounds."""
from datetime import date
from decimal import Decimal
import io
import json
import math
import numpy as np
import pandas as pd

from quant_robot.research.disclosed_flow_bounds import breadth_bounds


def performance_bounds(states, returns):
    if (not isinstance(states,list) or not states or len(states)!=len(returns)
            or any(s is not None and (type(s) is not int or s not in (0,1)) for s in states)):
        raise ValueError('Nonempty aligned binary-or-unknown states required')
    y=np.asarray(returns,dtype=float)
    if y.ndim!=1 or not np.isfinite(y).all():raise ValueError('Finite scalar outcomes required')
    known=np.array([s==1 for s in states]); unknown=np.array([s is None for s in states])
    c=(y-y.mean())/len(y); fixed=c[known].sum(); uncertain=c[unknown]
    def ratio_range(values):
        base=values[known].sum(); ordered=np.sort(values[unknown]); n=int(known.sum())
        lows=[]; highs=[]
        for k in range(len(ordered)+1):
            if n+k:
                lows.append((base+ordered[:k].sum())/(n+k))
                highs.append((base+(ordered[-k:].sum() if k else 0))/(n+k))
        return [float(min(lows)),float(max(highs))] if lows else None
    return {'months':len(y),'identified_positive':int(known.sum()),'identified_zero':states.count(0),
        'unknown_months':int(unknown.sum()),'selected_count':[int(known.sum()),int((known|unknown).sum())],
        'empty_selection_possible':not known.any(), 'unconditional_mean':float(y.mean()),
        'D':[float(fixed+np.minimum(uncertain,0).sum()),float(fixed+np.maximum(uncertain,0).sum())],
        'selected_mean':ratio_range(y),'selected_win_rate':ratio_range((y>0).astype(float))}


def open_return(entry, exit_date, entry_open, exit_open, events):
    if entry>=exit_date or any(not math.isfinite(float(v)) or float(v)<=0 for v in (entry_open,exit_open)):
        raise ValueError('Ordered dates and positive finite raw opens required')
    cash=Decimal(0)
    for event in events:
        if event['kind']!='cash_dividend' or event['cash_amount_basis']!='gross':
            raise ValueError('Only reviewed gross cash events supported')
        value=Decimal(str(event['cash_per_share']))
        if not value.is_finite() or value<=0 or event['record_date']>=event['ex_date']:
            raise ValueError('Invalid distribution or record/ex ordering')
        if entry<=event['record_date']<exit_date:cash+=value
    opening=Decimal(str(entry_open)); ending=Decimal(str(exit_open))
    return float((ending+cash-opening)/opening)


def summarize(rows):
    states=[r['state'] for r in rows]; returns=np.array([r['return'] for r in rows])
    full=performance_bounds(states,returns)
    later=[r for r in rows if r['decision_date']>='2023-01-01']
    late=performance_bounds([r['state'] for r in later],[r['return'] for r in later])
    rng=np.random.default_rng(20260921); n=len(rows)
    starts=rng.integers(0,n,size=(5000,(n+2)//3))
    ids=((starts[:,:,None]+np.arange(3))%n).reshape(5000,-1)[:,:n]
    y=returns[ids]; c=(y-y.mean(axis=1,keepdims=True))/n
    z=np.array([-1 if s is None else s for s in states])[ids]
    fixed=np.where(z==1,c,0).sum(axis=1)
    lower=fixed+np.where(z==-1,np.minimum(c,0),0).sum(axis=1)
    upper=fixed+np.where(z==-1,np.maximum(c,0),0).sum(axis=1)
    confidence=[float(np.quantile(lower,.05)),float(np.quantile(upper,.95))]
    passed=(full['identified_positive']>=6 and late['identified_positive']>=3
        and full['identified_zero']>=1 and confidence[0]>0 and full['selected_mean'][0]>0
        and late['selected_mean'][0]>0 and late['D'][0]>0)
    return {'full':full,'later_2023_onward':late,'bootstrap_D_outer_5_95':confidence,
        'gross_screen_passed':bool(passed),'fresh_OOS':False,'historical_vintage_verified':False,
        'net_positive_EV_verified':False,'bootstrap':'paired circular months; n=5000; block=3; seed=20260921'}


def calculate(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    from quant_robot.data.etf_reported_holdings import review_snapshot
    from quant_robot.paper.corporate_actions import validate_corporate_action_dataset
    scope=json.loads(snapshots['coverage_scope']); coverage=json.loads(snapshots['coverage_result'])
    holdings=[json.loads(snapshots[f'holdings_{i}']) for i in range(7)]
    calendar=calendar_rows_from_snapshot(snapshots['calendar'],snapshots['calendar_manifest'],start=date(2020,1,2),end=date(2024,6,28))
    sessions=[str(d) for d,opened in calendar if opened]
    reviewed=[review_snapshot(r,session_dates=sessions) for r in holdings]
    months=scope['months']
    if (len(months)!=38 or months[0]['decision_date']!='2021-04-01'
            or months[-1]['decision_date']!='2024-05-06' or months[-1]['exit_date']!='2024-06-03'):
        raise ValueError('Frozen month endpoints differ')
    observations=[]
    for m,previous in zip(months,coverage['months'],strict=True):
        selected=max((r for r in reviewed if r['available_from_session']<=m['decision_date']),key=lambda r:(r['period_end'],r['publication_date']))
        assert selected['period_end']==m['period_end'] and previous['decision_date']==m['decision_date']
        assert m['sessions']==[d for d in sessions if d[:7]==m['source_month']]
        assert m['decision_date']==min(d for d in sessions if d[:7]==m['decision_date'][:7])
        assert m['exit_date']==min(d for d in sessions if d[:7]==m['exit_date'][:7])
        hmap={r['symbol']:int(Decimal(r['fair_value_cny'])*100) for r in selected['holdings']}
        assert set(hmap)==set(m['symbols'])
        observed={}
        for i,item in enumerate(scope['inputs']):
            days=[date.fromisoformat(d) for d in m['sessions'] if item['segment_start']<=d<=item['segment_end'] and f'year={d[:4]}' in item['path']]
            if not days:continue
            frame=pd.read_parquet(io.BytesIO(snapshots[f'flow_{i}']),columns=scope['fields'],filters=[('date','in',days),('symbol','in',list(hmap))])
            for r in frame.to_dict('records'):
                day=str(r['date']); key=(day,r['symbol']); code,suffix=r['symbol'].split('.')
                assert day in m['sessions'] and r['symbol'] in hmap and key not in observed
                assert r['asset_id']=='CN_'+{'SH':'XSHG','SZ':'XSHE'}[suffix]+'_'+code and r['market']=='CN' and r['source']=='tushare_moneyflow'
                value=r['net_mf_amount']; observed[key]=None if pd.isna(value) or not math.isfinite(value) else value>0
        counts=[]; missing=[]
        for symbol,cents in hmap.items():
            states=[observed.get((d,symbol)) for d in m['sessions']]
            missing.extend((d,symbol) for d,s in zip(m['sessions'],states,strict=True) if s is None)
            counts.append({'value_cents':cents,'positive_days':sum(s is True for s in states),'unknown_days':states.count(None)})
        assert sorted(missing)==sorted((r['date'],r['symbol']) for r in previous['missing_cells'])
        bound=breadth_bounds(counts,total_value_cents=int(Decimal(selected['equity_total_cny'])*100),sessions=len(m['sessions']))
        assert bound['unknown_numerator']==previous['unknown_weighted_numerator'] and bound['denominator']==previous['full_denominator']
        observations.append({'decision_date':m['decision_date'],'exit_date':m['exit_date'],'source_month':m['source_month'],'period_end':selected['period_end'],'state':bound['identified_state'],'breadth_bounds':bound})
    anchors=sorted(set([r['decision_date'] for r in observations]+[r['exit_date'] for r in observations])); opens={}
    for year in range(2021,2025):
        days=[date.fromisoformat(d) for d in anchors if d[:4]==str(year)]
        bars=pd.read_parquet(io.BytesIO(snapshots[f'bars_{year}']),columns=['date','asset_id','market','currency','open'],filters=[('date','in',days),('asset_id','==','CN_ETF_XSHG_510300')])
        for r in bars.to_dict('records'):
            day=str(r['date']); assert day in anchors and day not in opens and r['market']=='CN_ETF' and r['currency']=='CNY'
            opens[day]=r['open']
    assert sorted(opens)==anchors
    actions=json.loads(snapshots['actions'])
    validate_corporate_action_dataset(actions,{'CN_ETF_XSHG_510300'},[date.fromisoformat(d) for d in sessions])
    for event in actions['events']:
        assert event['asset_id']=='CN_ETF_XSHG_510300' and event['record_date'] in sessions
        assert event['ex_date'] in sessions and sessions[sessions.index(event['ex_date'])-1]==event['record_date']
    for r in observations:r['return']=open_return(r['decision_date'],r['exit_date'],opens[r['decision_date']],opens[r['exit_date']],actions['events'])
    return {'diagnostic':summarize(observations),'observations':observations,'net_account_run':False,'new_forward_paper_days':0,
        'price_basis':'one_share_open_to_open_declared_cash_gross_v1','ETF_open_values_decoded':len(opens),'prior_search_history_complete':False}
