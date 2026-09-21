"""Frozen electricity-activity proxy; conditional gross evidence, never an account."""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json
import math
import re

import numpy as np

from quant_robot.research.disclosed_flow_diagnostic import open_return


def event_intervals(sources, sessions, *, start='2017-01-01', terminal='2024-01-02'):
    """Use only information available before each open; late history never refreshes state."""
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered sessions required')
    if any(date.fromisoformat(d).isoformat()!=d for d in sessions):
        raise ValueError('Canonical dates required')
    first, end = bisect_left(sessions,start), bisect_left(sessions,terminal)
    if first>=end or end>=len(sessions) or sessions[end]!=terminal:
        raise ValueError('Covered decision window and exact terminal session required')
    arrivals=defaultdict(list); seen=set()
    for source in sources:
        month=source['reference_month']; day=source['availability_date']; value=source['growth_percent']
        if (not isinstance(month,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month)
                or month in seen or date.fromisoformat(day).isoformat()!=day or month>=day[:7]
                or not isinstance(value,str)):
            raise ValueError('Unique earlier monthly observations and printed string values required')
        try:
            growth=Decimal(value)
        except InvalidOperation as exc:
            raise ValueError('Finite printed growth required') from exc
        if not growth.is_finite() or growth < -100 or day < sessions[0]:
            raise ValueError('Finite feasible growth and complete availability calendar required')
        seen.add(month)
        arrivals[bisect_right(sessions,day)].append((source,growth))
    history={}; latest=None; active_until=None; state=None; episode=0
    current=dict(state=None,episode_id=None,reference_month=None,availability_date=None,
                 median_growth_percent=None,prior_valid_months=0,reason='no_eligible_release')
    anchors=[]
    for i, day in enumerate(sessions[:end]):
        incoming=arrivals.get(i,[])
        for source,growth in incoming: history[source['reference_month']]=(source,growth)
        new_month=max((r['reference_month'] for r,_ in incoming),default=None)
        boundary=False; previous_state=state
        # A fresh latest-month release supersedes simultaneous old-state expiry.
        if new_month is not None and (latest is None or new_month>latest):
            latest=new_month; source,growth=history[latest]
            prior=sorted(m for m in history if m<latest)
            values=sorted(history[m][1] for m in prior[-36:])
            median=(values[17]+values[18])/2 if len(values)==36 else None
            state=int(growth<median) if median is not None else None
            active_until=(date.fromisoformat(source['availability_date'])+timedelta(days=62)).isoformat()
            if day>active_until:
                state=None; active_until=None
            if state==1 and previous_state!=1: episode+=1
            current=dict(state=state,episode_id=episode if state==1 else None,
                reference_month=latest,availability_date=source['availability_date'],
                median_growth_percent=str(median) if median is not None else None,
                prior_valid_months=len(prior),reason='latest_release' if state is not None else 'unknown_release')
            boundary=True
        elif active_until is not None and day>active_until:
            state=None; active_until=None
            current={**current,'state':None,'episode_id':None,'reason':'expired_after_62_calendar_days'}
            boundary=True
        if i==first or (i>first and boundary):
            anchors.append({**current,'entry_date':day,'index':i})
    out=[]
    for a,b in zip(anchors,anchors[1:]+[{'entry_date':terminal,'index':end}]):
        out.append({k:v for k,v in a.items() if k!='index'} |
                   dict(exit_date=b['entry_date'],sessions=b['index']-a['index']))
    return out


def describe(rows):
    for r in rows:
        if (r['state'] is not None and (type(r['state']) is not int or r['state'] not in (0,1))
                or type(r['sessions']) is not int or r['sessions']<=0
                or isinstance(r['return_value'],bool) or not math.isfinite(r['return_value']) or r['return_value']<=-1
                or (r['state']==1 and (type(r['episode_id']) is not int or r['episode_id']<=0))
                or (r['state']!=1 and r['episode_id'] is not None)):
            raise ValueError('Valid state, episode, positive duration and finite return greater than-1 required')
    z=np.array([r['state']==1 for r in rows],dtype=float)
    n=np.array([r['sessions'] for r in rows],dtype=float)
    y=np.array([r['return_value'] for r in rows],dtype=float)
    fraction=float((z*n).sum()/n.sum()) if rows else 0.
    return dict(intervals=len(rows),selected_intervals=int(z.sum()),
        known_unselected_intervals=sum(r['state']==0 for r in rows),
        unknown_intervals=sum(r['state'] is None for r in rows),
        unknown_sessions=sum(r['sessions'] for r in rows if r['state'] is None),
        selected_episodes=len({r['episode_id'] for r in rows if r['state']==1}),
        session_transitions=int(n.sum()),selected_session_fraction=fraction,
        D_daily_log=float(((z-fraction)*np.log1p(y)).sum()/n.sum()) if rows else None,
        selected_mean_gross=float(y[z==1].mean()) if z.any() else None,
        selected_positive_fraction=float((y[z==1]>0).mean()) if z.any() else None,
        unconditional_mean_gross=float(y.mean()) if rows else None)


def summarize(rows, later):
    full,late=describe(rows),describe(later)
    if len(rows)<=12:
        raise ValueError('More intervals than the fixed12-interval block required')
    z=np.array([r['state']==1 for r in rows],dtype=float)
    n=np.array([r['sessions'] for r in rows],dtype=float)
    y=np.array([r['return_value'] for r in rows],dtype=float)
    count=len(rows)
    starts=np.random.default_rng(20260922).integers(0,count,size=(5000,math.ceil(count/12)))
    ids=((starts[:,:,None]+np.arange(12))%count).reshape(5000,-1)[:,:count]
    zr,nr,lr=z[ids],n[ids],np.log1p(y[ids])
    exposure=(zr*nr).sum(axis=1)/nr.sum(axis=1)
    effects=((zr-exposure[:,None])*lr).sum(axis=1)/nr.sum(axis=1)
    interval=[float(v) for v in np.quantile(effects,[.025,.975],method='linear')]
    positive=lambda v:v is not None and v>0
    checks=dict(full_count=full['selected_intervals']>=12,later_count=late['selected_intervals']>=6,
        full_episodes=full['selected_episodes']>=6,later_episodes=late['selected_episodes']>=3,
        full_known_unselected=full['known_unselected_intervals']>0,
        later_known_unselected=late['known_unselected_intervals']>0,
        effect_lower_positive=interval[0]>0,full_mean_positive=positive(full['selected_mean_gross']),
        later_mean_positive=positive(late['selected_mean_gross']),later_effect_positive=positive(late['D_daily_log']))
    return dict(full=full,later_2021_onward=late,checks=checks,gross_screen_passed=all(checks.values()),
        bootstrap_D_daily_log_2_5_97_5=interval,bootstrap_replications=5000,block_release_intervals=12,
        seed=20260922,percentile_method='linear',net_positive_EV_verified=False,fresh_OOS=False,
        multiple_testing_adjusted=False,historical_vintage_verified=False,completed_account_trade_count=None)


def clip_later(rows,sessions,*,start='2021-01-01'):
    first=sessions[bisect_left(sessions,start)]; indices={d:i for i,d in enumerate(sessions)}
    return [{**r,'entry_date':max(r['entry_date'],first),
             'sessions':indices[r['exit_date']]-indices[max(r['entry_date'],first)],
             'left_clipped':r['entry_date']<first} for r in rows if r['exit_date']>first]


def calculate(snapshots):
    from quant_robot.research.us_variance_risk_diagnostic import cn_sessions,price_anchors
    sources=json.loads(snapshots['source_rows'])['rows']
    if len(sources)!=108:
        raise ValueError('Exactly108frozen monthly observations required')
    sessions=cn_sessions(snapshots)
    rows=event_intervals(sources,sessions)
    later=clip_later(rows,sessions)
    anchors=sorted({r[k] for r in rows+later for k in ('entry_date','exit_date')})
    opens=price_anchors(snapshots,anchors,sessions)
    events=json.loads(snapshots['actions'])['events']
    events += [dict(asset_id=r['asset_id'],kind='cash_dividend',cash_amount_basis='gross',
        record_date=r['record_date'],ex_date=r['ex_date'],cash_per_share=r['cash_per_unit'])
        for r in json.loads(snapshots['early_actions'])['events']]
    if len(events)!=11 or len({r['record_date'] for r in events})!=11:
        raise ValueError('Exactly11unique reviewed historical distributions required')
    indices={d:i for i,d in enumerate(sessions)}
    for r in events:
        if (r['asset_id']!='CN_ETF_XSHG_510300' or r['record_date'] not in indices or r['ex_date'] not in indices
                or indices[r['record_date']]+1!=indices[r['ex_date']]):
            raise ValueError('Reviewed cash record/ex adjacent sessions required')
    for r in rows+later:
        r['return_value']=open_return(r['entry_date'],r['exit_date'],opens[r['entry_date']],opens[r['exit_date']],events)
    return dict(diagnostic=summarize(rows,later),observations=rows,later_observations=later,
        net_account_run=False,new_forward_paper_days=0,ETF_open_values_used=len(opens),
        price_basis='one_share_open_to_open_declared_cash_gross_v1')
