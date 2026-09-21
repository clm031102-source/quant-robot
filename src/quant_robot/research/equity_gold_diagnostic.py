"""Frozen equity/gold continuous-account summaries; no parameter selection."""
from decimal import Decimal, ROUND_HALF_UP
import json

import numpy as np

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account

ASSETS = ('CN_ETF_XSHG_510300', 'CN_ETF_XSHG_518880')


def annual_contributions(curve):
    endings = {}
    for row in curve:
        endings[row['date'][:4]] = Decimal(str(row['equity']))
    if not all(str(year) in endings for year in range(2014,2025)):
        raise ValueError('All fixed annual endpoints and terminal2024mark required')
    previous, values = Decimal(10000), {}
    for year in range(2014,2024):
        key = str(year); values[key] = endings[key]-previous; previous = endings[key]
    terminal = endings['2024']-endings['2023']
    values['2023'] += terminal
    return {k:float(v) for k,v in values.items()}, float(terminal)


def block_interval(values):
    data = np.asarray(values, dtype=float)
    if data.shape != (10,) or not np.isfinite(data).all():
        raise ValueError('Ten finite annual contributions required')
    starts = np.random.default_rng(20260921).integers(0,10,size=(5000,5))
    indices = ((starts[:,:,None]+np.arange(2))%10).reshape(5000,10)
    return np.quantile(data[indices].mean(axis=1), [.025,.975], method='linear').tolist()


def position_episodes(result, actions):
    episodes = {}
    for fill in result['fills']:
        key = (fill['cycle_id'],fill['asset_id'])
        row = episodes.setdefault(key,dict(cycle_id=key[0],asset_id=key[1],entry_date=None,
            remaining_quantity=0,fees=Decimal(0),net_cash=Decimal(0),earned_distribution=Decimal(0)))
        quantity = fill['quantity']; notional = Decimal(str(fill['notional'])); fee = Decimal(str(fill['fee']))
        row['fees'] += fee
        if fill['side'] == 'buy':
            if row['entry_date'] is not None:
                raise ValueError('Only one annual entry per asset and cycle allowed')
            row['entry_date'] = fill['date']; row['remaining_quantity'] += quantity; row['net_cash'] -= notional+fee
        else:
            row['remaining_quantity'] -= quantity; row['net_cash'] += notional-fee
    action_map = {a['event_id']:a for a in actions}
    for event in result['corporate_action_journal']:
        if event['kind'] != 'record_entitlement' or event['quantity'] == 0:
            continue
        action = action_map[event['event_id']]
        eligible = [row for row in episodes.values() if row['asset_id']==action['asset_id'] and row['entry_date']<=event['date']]
        if not eligible:
            raise ValueError('Earned distribution must follow an actual modeled entry')
        row = max(eligible,key=lambda item:item['entry_date'])
        row['earned_distribution'] += (Decimal(event['quantity'])*Decimal(str(action['cash_per_unit']))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return [dict(cycle_id=row['cycle_id'],asset_id=row['asset_id'],entry_date=row['entry_date'],
        remaining_quantity=row['remaining_quantity'],completed=row['remaining_quantity']==0,
        fees_CNY=float(row['fees']),earned_distribution_CNY=float(row['earned_distribution']),
        net_PnL_CNY=float(row['net_cash']+row['earned_distribution']) if row['remaining_quantity']==0 else None)
        for row in episodes.values()]


def summarize_account(result, actions):
    annual, terminal = annual_contributions(result['equity_curve'])
    episodes = position_episodes(result, actions)
    completed = [row for row in episodes if row['completed']]
    study_rows = [row for row in result['equity_curve'] if row['date']>='2014-01-01']
    invested = [sum(p['market_value'] for p in row['position_values'].values()) for row in study_rows]
    if abs(sum(annual.values())-result['metrics']['pnl_cny'])>1e-8:
        raise ValueError('Annual contribution accounting differs')
    return dict(full_net_PnL_CNY=result['metrics']['pnl_cny'], annual_contributions_CNY=annual,
        terminal_2024_contribution_CNY=terminal,later_net_contribution_CNY=sum(v for y,v in annual.items() if y>='2020'),
        positive_years=sum(v>0 for v in annual.values()),positive_year_frequency=sum(v>0 for v in annual.values())/10,
        paired_entry_cycles=result['metrics']['paired_entry_cycles'],terminal_settled=result['risk']['terminal_settled'],
        risk_within_all_observed_limits=result['risk']['within_all_observed_limits'],
        completed_positions=len(completed),positive_completed_positions=sum(row['net_PnL_CNY']>0 for row in completed),
        completed_position_positive_frequency=sum(row['net_PnL_CNY']>0 for row in completed)/len(completed) if completed else None,
        position_episodes=episodes,fees_CNY=result['metrics']['fees_paid'],fill_count=len(result['fills']),
        average_invested_CNY=sum(invested)/len(study_rows), average_idle_cash_CNY=sum(row['cash'] for row in study_rows)/len(study_rows),
        exposed_sessions=sum(value>0 for value in invested),study_sessions=len(study_rows),
        maximum_drawdown=result['metrics']['maximum_drawdown'],maximum_daily_loss_CNY=result['metrics']['maximum_daily_loss_cny'],
        entry_halted=result['risk']['new_entries_halted'],risk_breach_count=len(result['risk']['breaches']))


def financial_screen(summary):
    interval = block_interval(list(summary['annual_contributions_CNY'].values()))
    paired = summary['paired_entry_cycles']
    checks = dict(terminal_settled=summary['terminal_settled'],full_net_profit_positive=summary['full_net_PnL_CNY']>0,
        later_net_contribution_positive=summary['later_net_contribution_CNY']>0,at_least_six_positive_years=summary['positive_years']>=6,
        at_least_eight_paired_years=len(paired)>=8,at_least_three_later_paired_years=sum(y>='2020' for y in paired)>=3,
        block_lower_positive=interval[0]>0)
    return dict(checks=checks,conditional_financial_screen_passed=all(checks.values()),
        block_mean_annual_PnL_CNY_2_5_97_5=interval,risk_within_all_observed_limits=summary['risk_within_all_observed_limits'],
        net_positive_EV_verified=False,paper_promotion_allowed=False,fresh_OOS=False,
        source_quality_certified=False,actual_fills_verified=False,counts_as_forward_paper_days=0)


def calculate(snapshots):
    bars = json.loads(snapshots['bars']); sessions = json.loads(snapshots['sessions'])
    cycles = json.loads(snapshots['cycles']); actions = json.loads(snapshots['actions'])['events']
    if (len(bars)!=4908 or len(sessions)!=2454 or sessions[0]!='2013-12-05' or sessions[-1]!='2024-01-02'
            or len(actions)!=10 or [c['cycle_id'] for c in cycles]!=[str(y) for y in range(2014,2024)]):
        raise ValueError('Frozen source/window identities differ')
    accounts, summaries = {}, {}
    for minimum in (0,5,10):
        for slippage in (0,10,30):
            key = f'min{minimum}_slip{slippage}'
            accounts[key], summaries[key] = {}, {}
            for name, assets in [('paired',ASSETS),('equity',(ASSETS[0],)),('gold',(ASSETS[1],))]:
                account = run_allocation_account(bars,sessions=sessions,cycles=cycles,actions=actions,assets=assets,
                    config=AllocationConfig(minimum_commission=minimum,slippage_bps=slippage))
                accounts[key][name] = account
                summaries[key][name] = summarize_account(account,actions)
    primary = summaries['min5_slip10']['paired']
    return dict(study_id='fixed_equity_gold_risk_diversification_v1',accounts=accounts,summaries=summaries,
        diagnostic=financial_screen(primary),primary_summary=primary,
        cash_reference=dict(initial_cash_CNY=10000,ending_cash_CNY=10000,net_PnL_CNY=0,interest=0),
        general_factor_batch_allowed=False,paper_promotion_allowed=False,live_boundary_allowed=False)
