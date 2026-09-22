"""Prospective same-budget strategy/holding/cash accounts, without study admission.

The caller must freeze the policy, calendars, inputs, implementation and one-use
admission before outcomes. This module does not reopen a consumed hypothesis.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account

HOLDING = dict(kind='unconditional_same_asset',
    initial_entry='first_study_session_with_20_prior_sessions',
    scheduled_exit='earlier_of_entry_plus_252_sessions_or_terminal',
    renewal='session_after_previous_scheduled_exit',
    failed_entry='skip_fixed_cycle_without_retry',
    unresolved_exit='persist_and_skip_occupied_entry',
    trim='no_topup', account_stop='permanent_no_restart', same_day_roundtrip=False)
CASH = dict(kind='idle_cash', annual_interest=0, initial_CNY=10000,
            borrowing=False, cash_etf_overlay=False)
COMMON = dict(initial_cash_CNY=10000, all_in_entry_budget_CNY=1000,
    marked_position_limit_CNY=1000, daily_loss_limit_CNY=60,
    paper_drawdown_limit=.08, absolute_drawdown_limit=.4,
    max_holding_sessions=252, ADV_fraction=.01, commission_bps_each=5,
    lot_shares=100, price_tick_CNY='0.001', entry_fill='raw_open',
    daily_mark='raw_close', sizing='prior_close_and_prior20_volumes',
    entry_budget_failure='whole_cancel_without_resize_or_retry',
    exit_capacity='prior20_ADV_and_current_volume_expost',
    risk_action='next_session_open', position_trim='refresh_after_each_close',
    capital_reset=False, actual_broker_fees_certified=False)
CASES = [dict(minimum_commission_CNY=m, slippage_bps_each=s)
         for m in (0,5,10) for s in (0,10,30)]
METRICS = ['calendar_and_cost_identity', 'net_PnL_CNY', 'later_net_contribution_CNY',
    'strategy_minus_holding_CNY', 'strategy_minus_cash_CNY', 'average_invested_CNY',
    'average_idle_cash_CNY', 'exposed_sessions', 'completed_episode_count',
    'completed_episode_win_fraction', 'fees_CNY', 'fill_count',
    'maximum_drawdown', 'maximum_daily_loss_CNY', 'risk_breaches', 'terminal_settled']


def policy_template(*, study_id, first_session, terminal_session, later_start):
    """A declaration to freeze before use; constructing it grants no permission."""
    return dict(schema_version=1, study_id=study_id,
        window=dict(first_session=first_session,terminal_session=terminal_session,later_start=later_start),
        controls=dict(holding=deepcopy(HOLDING),cash=deepcopy(CASH)),
        common=deepcopy(COMMON), cost_cases=deepcopy(CASES),
        primary=dict(minimum_commission_CNY=5,slippage_bps_each=10),
        required_metrics=METRICS.copy(), selection='no_cost_or_control_selection',
        risk_normalized_alpha_claim=False, admission_granted=False)


def validate_policy(policy, sessions):
    """Reject incomplete controls before iterating any market bars or actions."""
    if not isinstance(policy,dict) or policy.get('schema_version')!=1:
        raise ValueError('Explicit prospective comparison policy required')
    controls=policy.get('controls')
    if not isinstance(controls,dict) or set(controls)!={'holding','cash'}:
        raise ValueError('Both holding and cash controls must be frozen before outcomes')
    if controls['holding']!=HOLDING or controls['cash']!=CASH:
        raise ValueError('Complete fixed holding renewal and cash policies required')
    if policy.get('common')!=COMMON:
        raise ValueError('Identical fixed CNY10000 execution and risk policy required')
    if policy.get('cost_cases')!=CASES or policy.get('primary')!={'minimum_commission_CNY':5,'slippage_bps_each':10}:
        raise ValueError('All nine fixed cost cases and one primary required')
    if (policy.get('required_metrics')!=METRICS or policy.get('selection')!='no_cost_or_control_selection'
            or policy.get('risk_normalized_alpha_claim') is not False or policy.get('admission_granted') is not False):
        raise ValueError('Complete comparisons without selection or alpha certification required')
    if not isinstance(policy.get('study_id'),str) or not policy['study_id'].strip():
        raise ValueError('A specific study identity required')
    if not sessions or sessions!=sorted(set(sessions)):
        raise ValueError('Same explicit ordered calendar required')
    for day in sessions:
        if date.fromisoformat(day).isoformat()!=day:
            raise ValueError('Canonical calendar dates required')
    window=policy.get('window',{})
    if set(window)!={'first_session','terminal_session','later_start'}:
        raise ValueError('Full and later comparison windows required')
    first,terminal,later=(window[k] for k in ('first_session','terminal_session','later_start'))
    if (any(day not in sessions for day in (first,terminal,later)) or not first<=later<terminal
            or terminal!=sessions[-1] or max(sessions.index(first),20)>=len(sessions)-1):
        raise ValueError('Fixed study dates, warmup and common terminal required')
    return policy


def holding_cycles(sessions, policy):
    validate_policy(policy,sessions)
    start=max(sessions.index(policy['window']['first_session']),20)
    terminal=len(sessions)-1
    result=[]
    while start<terminal:
        end=min(start+252,terminal)
        result.append(dict(cycle_id=f'holding_{len(result)+1:03d}',entry_date=sessions[start],exit_date=sessions[end]))
        start=end+1
    return result


def _summary(account, actions, first, later):
    curve=account['equity_curve'];rows=[r for r in curve if r['date']>=first]
    before=[r for r in curve if r['date']<later]
    previous=Decimal(str(before[-1]['equity'])) if before else Decimal(10000)
    terminal=Decimal(str(curve[-1]['equity']))
    episodes={}
    for fill in account['fills']:
        row=episodes.setdefault(fill['cycle_id'],dict(quantity=0,pnl=Decimal(0),entry_date=None))
        direction=1 if fill['side']=='buy' else -1
        if direction==1:
            if row['entry_date'] is not None:
                raise ValueError('A source episode may have only one entry')
            row['entry_date']=fill['date']
        row['quantity']+=direction*fill['quantity']
        row['pnl']-=direction*Decimal(str(fill['notional']))+Decimal(str(fill['fee']))
    action_map={a['event_id']:a for a in actions}
    for event in account['corporate_action_journal']:
        if event['kind']!='record_entitlement' or not event['quantity']:
            continue
        eligible=[r for r in episodes.values() if r['entry_date']<=event['date']]
        if not eligible:
            raise ValueError('Entitlement without an actual modeled entry')
        row=max(eligible,key=lambda r:r['entry_date'])
        row['pnl']+=(Decimal(event['quantity'])*Decimal(str(action_map[event['event_id']]['cash_per_unit']))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    completed=[row for row in episodes.values() if row['quantity']==0]
    invested=[sum(p['market_value'] for p in r['position_values'].values()) for r in rows]
    return dict(net_PnL_CNY=float(terminal-10000),later_net_contribution_CNY=float(terminal-previous),
        average_invested_CNY=sum(invested)/len(rows),average_idle_cash_CNY=sum(r['cash'] for r in rows)/len(rows),
        exposed_sessions=sum(v>0 for v in invested),completed_episode_count=len(completed),
        completed_episode_win_fraction=sum(r['pnl']>0 for r in completed)/len(completed) if completed else None,
        fees_CNY=account['metrics']['fees_paid'],fill_count=len(account['fills']),
        maximum_drawdown=account['metrics']['maximum_drawdown'],maximum_daily_loss_CNY=account['metrics']['maximum_daily_loss_cny'],
        risk_breaches=account['risk']['breaches'],terminal_settled=account['risk']['terminal_settled'])


def run_comparison(bars, *, sessions, asset, strategy_cycles, actions, policy):
    """Numerical single-asset runner; sources need separate study admission."""
    validate_policy(policy,sessions)
    if not isinstance(asset,str) or not asset:
        raise ValueError('A specific asset required')
    first=policy['window']['first_session'];later=policy['window']['later_start']
    if any(c['entry_date']<first or c['exit_date']>sessions[-1] for c in strategy_cycles):
        raise ValueError('Strategy cycles outside common study calendar')
    control_cycles=holding_cycles(sessions,policy)
    accounts={};comparisons={}
    for case in policy['cost_cases']:
        m,s=case['minimum_commission_CNY'],case['slippage_bps_each']
        key=f'min{m}_slip{s}'
        settings=AllocationConfig(initial_cash=COMMON['initial_cash_CNY'],
            max_position_cny=COMMON['all_in_entry_budget_CNY'],max_daily_loss_cny=COMMON['daily_loss_limit_CNY'],
            max_drawdown=COMMON['paper_drawdown_limit'],max_holding_sessions=COMMON['max_holding_sessions'],
            commission_bps=COMMON['commission_bps_each'],participation=COMMON['ADV_fraction'],
            minimum_commission=m,slippage_bps=s,execution_price_field='open')
        accounts[key]={}
        for role,cycles in [('strategy',strategy_cycles),('holding',control_cycles),('cash',[])]:
            accounts[key][role]=run_allocation_account(bars,sessions=sessions,assets=(asset,),cycles=cycles,actions=actions,config=settings)
        a=accounts[key]
        if any([r['date'] for r in value['equity_curve']]!=sessions or value['config']!=a['strategy']['config'] for value in a.values()):
            raise ValueError('Account calendar or execution identity differs')
        summaries={role:_summary(value,actions,first,later) for role,value in a.items()}
        comparisons[key]=dict(accounts=summaries,calendar_and_cost_identity=True,
            strategy_minus_holding_CNY=summaries['strategy']['net_PnL_CNY']-summaries['holding']['net_PnL_CNY'],
            strategy_minus_cash_CNY=summaries['strategy']['net_PnL_CNY']-summaries['cash']['net_PnL_CNY'],
            risk_normalized_alpha_verified=False)
    return dict(accounts=accounts,comparisons=comparisons,holding_cycles=control_cycles,
        policy=deepcopy(policy),net_positive_EV_verified=False,research_admission_verified=False,
        paper_promotion_allowed=False,new_forward_days=0)
