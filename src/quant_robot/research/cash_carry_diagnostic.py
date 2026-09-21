"""One frozen annual primary cash-carry cost screen, not realized account profit."""
from datetime import date
from decimal import Decimal
import json
import math
import numpy as np

from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
from quant_robot.research.cash_carry_inputs import (
    decimal_value, parse_pcf, income_periods, check_income_identities,
)


def _capacity(pcf, shares, side):
    if not pcf['creation' if side=='Creation' else 'redemption']:
        return False
    for key,cap in pcf['caps'].items():
        if side not in key or cap is None or cap==0:
            continue
        limit=cap if 'PerUser' in key else cap*Decimal('.01')
        if shares>limit:
            return False
    return True


def annual_observation(entry, exit_, income_unit, calendar_days, fee, allowance):
    gross,fee,allowance=map(decimal_value,(income_unit,fee,allowance))
    if (fee<0 or fee>=1000 or allowance<0 or type(calendar_days) is not int or calendar_days<=0 or
            entry['cash_in']!=100 or exit_['cash_out']!=100):
        raise ValueError('Fixed cash basis, nonnegative costs and positive whole days required')
    shares=int((Decimal(1000)-fee)//100)
    if not _capacity(entry,shares,'Creation'):
        shares=0
    if shares and not _capacity(exit_,shares,'Redemption'):
        raise ValueError('Unresolved exit; future refusal cannot cancel historical entry')
    costs=fee*2 if shares else Decimal(0)
    cash=gross*shares/100
    stress=allowance*calendar_days if shares else Decimal(0)
    pnl=cash-costs-stress
    return dict(shares=shares,calendar_days_held=calendar_days if shares else 0,
                entry_debit_CNY=float(shares*100+(fee if shares else 0)),
                pro_rata_income_CNY=float(cash),flat_execution_fees_CNY=float(costs),
                rounding_allowance_CNY=float(stress),modeled_net_PnL_CNY=float(pnl),
                additional_unmodeled_fee_headroom_CNY=float(pnl),actual_fill_verified=False)


def _describe(rows):
    amounts=[r['modeled_net_PnL_CNY'] for r in rows]
    return dict(opportunities=len(rows),conditionally_filled=sum(r['shares']>0 for r in rows),
                positive=sum(x>0 for x in amounts),positive_frequency=sum(x>0 for x in amounts)/len(rows),
                total_modeled_net_PnL_CNY=sum(amounts),mean_modeled_net_PnL_CNY=sum(amounts)/len(rows),
                worst_modeled_net_PnL_CNY=min(amounts),reference_capital_contribution=sum(amounts)/10000)


def summarize(rows):
    if ([r['entry_year'] for r in rows]!=list(range(2015,2024)) or
            any(not math.isfinite(r['modeled_net_PnL_CNY']) for r in rows)):
        raise ValueError('All nine fixed annual opportunities required')
    full=_describe(rows);later=_describe([r for r in rows if r['entry_year']>=2020])
    starts=np.random.default_rng(20260921).integers(0,9,size=(5000,5))
    ids=((starts[:,:,None]+np.arange(2))%9).reshape(5000,10)[:,:9]
    values=np.array([r['modeled_net_PnL_CNY'] for r in rows])
    interval=[float(x) for x in np.quantile(values[ids].mean(axis=1),[.025,.975])]
    checks=dict(all_nine_filled=full['conditionally_filled']==9,all_four_later_filled=later['conditionally_filled']==4,
                full_mean_positive=full['mean_modeled_net_PnL_CNY']>0,
                later_mean_positive=later['mean_modeled_net_PnL_CNY']>0,
                high_positive_frequency=full['positive_frequency']>=.70,block_lower_positive=interval[0]>0)
    return dict(full=full,later_2020_onward=later,block_interval_mean_PnL_CNY=interval,
                checks=checks,conditional_cash_screen_passed=all(checks.values()),
                net_positive_EV_verified=False,fresh_OOS=False,multiple_testing_adjusted=False,
                investor_fees_confirmed=False,daily_risk_validated=False,actual_fills_verified=False)


def _income_rows(snapshots):
    rows={}
    for year in range(2015,2025):
        data=json.loads(snapshots[f'income_{year}'],parse_float=Decimal)
        page=data.get('data',{});items=page.get('data',[])
        last=f'{year}-12-31' if year<2024 else '2024-01-02'
        if data.get('status')!=1 or page.get('total')!=len(items) or not items:
            raise ValueError('Complete bounded income pages required')
        for row in items:
            d=row['navDate']
            if d in rows or not f'{year}-01-01'<=d<=last:
                raise ValueError('Income dates duplicate or outside fixed window')
            decimal_value(row['incomeUnit'])
            rows[d]=row
    if len(rows)!=2658:
        raise ValueError('Exact preflight income-date inventory required')
    return rows


def _calendar_and_intervals(snapshots, proposal):
    days=calendar_rows_from_snapshot(snapshots['calendar'],snapshots['calendar_manifest'],
                                    start=date(2015,1,1),end=date(2024,6,28))
    sessions=[str(d) for d,opened in days if opened]
    if sessions!=sorted(set(sessions)):
        raise ValueError('Unique ordered CN calendar required')
    intervals=proposal['intervals']
    if [r['entry_year'] for r in intervals]!=list(range(2015,2024)):
        raise ValueError('Fixed annual opportunities required')
    for row in intervals:
        year=row['entry_year'];a=next(d for d in sessions if d.startswith(str(year)+'-'))
        b=next(d for d in sessions if d.startswith(str(year+1)+'-'))
        n=sessions.index(b)-sessions.index(a)
        if (row['entry_date']!=a or row['exit_date']!=b or row['income_first_date']!=sessions[sessions.index(a)+1]
                or row['income_last_date']!=b or row['holding_sessions']!=n or not 1<=n<=252):
            raise ValueError('Frozen endpoints or entitlement boundaries differ from calendar')
    return sessions,intervals


def calculate(snapshots):
    proposal=json.loads(snapshots['proposal']);preflight=json.loads(snapshots['source_preflight'])
    if (preflight['status']!='opaque_inputs_retained_requires_registered_income_identity_checks' or
            preflight['income_value_inspection'] is not False or preflight['income_rows']!=2658):
        raise ValueError('Opaque source preflight required')
    sessions,intervals=_calendar_and_intervals(snapshots,proposal)
    pcf={d:parse_pcf(snapshots['pcf_'+d[:4]],d) for d in proposal['source_scope']['PCF_anchor_dates']}
    for d,p in pcf.items():
        if d!='2015-01-05' and p['previous_date']!=sessions[sessions.index(d)-1]:
            raise ValueError('PCF previous trading day mismatch')
        if d=='2015-01-05' and p['previous_date']!='2014-12-31':
            raise ValueError('First PCF previous trading day mismatch')
    rows=_income_rows(snapshots)
    periods=income_periods(sessions,list(rows),'2015-01-01','2024-01-02')
    identities=check_income_identities(rows,periods,proposal['income']['seven_day_consistency']['check_end_dates'])
    totals={}
    for r in intervals:
        a,b=r['income_first_date'],r['income_last_date']
        selected=[p for p in periods if p['end']>=a and p['start']<=b]
        days=(date.fromisoformat(b)-date.fromisoformat(a)).days+1
        if (not selected or selected[0]['start']!=a or selected[-1]['end']!=b or
                sum(p['days'] for p in selected)!=days):
            raise ValueError('Entitlement cannot split reporting periods')
        totals[r['entry_year']]=(sum((decimal_value(rows[p['end']]['incomeUnit']) for p in selected),Decimal(0)),days)
    scenarios=[]
    for fee in (0,5,10):
        for allowance in (Decimal(0),Decimal('.01')):
            observations=[{**r,**annual_observation(pcf[r['entry_date']],pcf[r['exit_date']],
                          *totals[r['entry_year']],fee,allowance)} for r in intervals]
            scenarios.append(dict(flat_fee_CNY_per_leg=fee,daily_rounding_allowance_CNY=float(allowance),
                                  full=_describe(observations),later=_describe(observations[-4:]),observations=observations))
    primary=next(s for s in scenarios if s['flat_fee_CNY_per_leg']==5 and s['daily_rounding_allowance_CNY']==.01)
    return dict(study_id=proposal['study_id'],source_identity_checks=identities,scenarios=scenarios,
                diagnostic=summarize(primary['observations']),net_account_run=False,paper_promotion_allowed=False,
                actual_market_return_diagnostic_completed=True,new_forward_paper_days=0,live_boundary_allowed=False)
