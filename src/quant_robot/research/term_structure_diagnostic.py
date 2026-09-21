"""Frozen domestic sovereign-curve quarterly gross falsification, not an account."""
from datetime import date, timedelta
from decimal import Decimal
import json
import math
import numpy as np
from quant_robot.research.disclosed_flow_diagnostic import open_return
from quant_robot.research.us_variance_risk_diagnostic import cn_sessions, price_anchors


def month_key(number):
    year, month = divmod(number, 12)
    return f'{year:04}-{month+1:02}'


def signal(month, inputs):
    day = date.fromisoformat(month+'-01')
    number = day.year*12+day.month-1
    needed = [month_key(i) for i in range(number-12, number+1)]
    unknown = [m for m in needed if m not in inputs or inputs[m]['status']=='unknown']
    if unknown:
        return dict(state=None, slope_percentage_points=None, prior12_median_percentage_points=None,
                    unknown_months=unknown)
    slopes = []
    for m in needed:
        row = inputs[m]
        if row['status']!='conditional' or row['month']!=m:
            raise ValueError('Exact conditional monthly inputs required')
        one, ten = Decimal(row['yield_1y_percent']), Decimal(row['yield_10y_percent'])
        if not one.is_finite() or not ten.is_finite():
            raise ValueError('Finite monthly yields required')
        slopes.append(ten-one)
    previous = sorted(slopes[:-1])
    median = (previous[5]+previous[6])/2
    return dict(state=int(slopes[-1]>median), slope_percentage_points=str(slopes[-1]),
                prior12_median_percentage_points=str(median), unknown_months=[])


def quarterly_anchors(sessions):
    if not sessions or sessions!=sorted(set(sessions)):
        raise ValueError('Unique ordered CN calendar required')
    result=[]
    for offset in range(45):
        year, quarter = divmod(offset,4);year+=2013;month=quarter*3+1
        key=f'{year:04}-{month:02}'
        days=[d for d in sessions if d.startswith(key)]
        if not days:raise ValueError('First session for every fixed quarter required')
        prior=date(year,month,1)-timedelta(days=1)
        result.append(dict(entry_date=days[0],observation_month=prior.strftime('%Y-%m'),quarter_end=str(prior)))
    return result


def mark_episodes(rows):
    episode=0; previous=False
    for row in rows:
        selected=row['state']==1
        if selected and not previous:episode+=1
        row['episode_id']=episode if selected else None
        previous=selected


def describe(rows):
    z=np.array([r['state']==1 for r in rows],dtype=float)
    y=np.array([r['return_value'] for r in rows]); n=np.array([r['sessions'] for r in rows])
    fraction=float((z*n).sum()/n.sum())
    return dict(intervals=len(rows),selected_intervals=int(z.sum()),
        known_unselected_intervals=sum(r['state']==0 for r in rows),unknown_intervals=sum(r['state'] is None for r in rows),
        selected_episodes=len({r['episode_id'] for r in rows if r['state']==1}),
        session_transitions=int(n.sum()),selected_session_fraction=fraction,
        D_daily_log=float(((z-fraction)*np.log1p(y)).sum()/n.sum()),
        selected_mean_gross=float(y[z==1].mean()) if z.any() else None,
        selected_positive_intervals=int((y[z==1]>0).sum()),
        selected_positive_fraction=float((y[z==1]>0).mean()) if z.any() else None,
        unconditional_mean_gross=float(y.mean()))


def summarize(rows):
    later=[r for r in rows if r['entry_date']>='2020-01-01']
    if len(rows)!=44 or len(later)!=16:raise ValueError('Fixed44quarters and16later quarters required')
    for row in rows:
        if ((row['state'] is not None and (type(row['state']) is not int or row['state'] not in (0,1)))
                or type(row['sessions']) is not int or row['sessions']<=0
                or not math.isfinite(row['return_value']) or row['return_value']<=-1):
            raise ValueError('Binary/unknown states, positive durations and finite returns above-1 required')
    full, late=describe(rows),describe(later)
    z=np.array([r['state']==1 for r in rows],dtype=float)
    y=np.array([r['return_value'] for r in rows]);n=np.array([r['sessions'] for r in rows])
    starts=np.random.default_rng(20260922).integers(0,44,size=(5000,11))
    ids=((starts[:,:,None]+np.arange(4))%44).reshape(5000,44)
    zr,nr,lr=z[ids],n[ids],np.log1p(y[ids]);exposure=(zr*nr).sum(axis=1)/nr.sum(axis=1)
    effects=((zr-exposure[:,None])*lr).sum(axis=1)/nr.sum(axis=1)
    interval=[float(v) for v in np.quantile(effects,[.025,.975],method='linear')]
    positive=lambda v:v is not None and v>0
    checks=dict(full_count=full['selected_intervals']>=16,later_count=late['selected_intervals']>=6,
        full_episodes=full['selected_episodes']>=6,later_episodes=late['selected_episodes']>=3,
        full_known_unselected=full['known_unselected_intervals']>0,later_known_unselected=late['known_unselected_intervals']>0,
        effect_lower_positive=interval[0]>0,full_mean_positive=positive(full['selected_mean_gross']),
        later_mean_positive=positive(late['selected_mean_gross']),later_effect_positive=positive(late['D_daily_log']))
    return dict(full=full,later_2020_onward=late,checks=checks,gross_screen_passed=all(checks.values()),
        later_carry_in_episode=rows[27]['state']==1 and rows[28]['state']==1,
        bootstrap_D_daily_log_2_5_97_5=interval,bootstrap_replications=5000,block_quarters=4,seed=20260922,
        annual={str(y):describe([r for r in rows if r['entry_date'].startswith(str(y))]) for y in range(2013,2024)},
        net_positive_EV_verified=False,fresh_OOS=False,multiple_testing_adjusted=False,
        historical_vintage_verified=False,completed_account_trade_count=None)


def calculate(snapshots):
    months=json.loads(snapshots['source_rows'])['months']
    expected=[month_key(i) for i in range(2011*12+11,2023*12+9)]
    if [r['month'] for r in months]!=expected:raise ValueError('Exact142ordered source months required')
    by={r['month']:r for r in months}
    sessions=cn_sessions(snapshots);anchors=quarterly_anchors(sessions)
    indices={d:i for i,d in enumerate(sessions)}
    rows=[]
    for a,b in zip(anchors,anchors[1:]):
        if a['entry_date']<=a['quarter_end']:raise ValueError('Entry must follow completed source quarter')
        rows.append(dict(**a,**signal(a['observation_month'],by),exit_date=b['entry_date'],
            sessions=indices[b['entry_date']]-indices[a['entry_date']]))
    mark_episodes(rows)
    opens=price_anchors(snapshots,[a['entry_date'] for a in anchors],sessions)
    events=json.loads(snapshots['actions'])['events']
    events += [dict(asset_id=r['asset_id'],kind='cash_dividend',cash_amount_basis='gross',
        record_date=r['record_date'],ex_date=r['ex_date'],cash_per_share=r['cash_per_unit'])
        for r in json.loads(snapshots['early_actions'])['events']]
    if len(events)!=11 or len({r['record_date'] for r in events})!=11:
        raise ValueError('Exactly11unique reviewed distributions required')
    for r in events:
        if (r['asset_id']!='CN_ETF_XSHG_510300' or r['record_date'] not in indices or r['ex_date'] not in indices
                or indices[r['record_date']]+1!=indices[r['ex_date']]):
            raise ValueError('Reviewed record/ex adjacent sessions required')
    for r in rows:
        r['return_value']=open_return(r['entry_date'],r['exit_date'],opens[r['entry_date']],opens[r['exit_date']],events)
    return dict(diagnostic=summarize(rows),observations=rows,net_account_run=False,
        new_forward_paper_days=0,ETF_open_values_used=len(opens),
        price_basis='one_share_open_to_open_declared_cash_gross_v1',historical_curve_publication_assumed=True)
