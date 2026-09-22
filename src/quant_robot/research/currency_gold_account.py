"""One frozen continuous gold account across source-defined holding episodes."""
import json
from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.research.equity_gold_diagnostic import block_interval, summarize_account

ASSET = 'CN_ETF_XSHG_518880'


def episode_cycles(rows, sessions):
    """Merge adjacent selected quarters; no re-entry after a 252-session exit."""
    if sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered sessions required')
    cycles, omitted = [], []
    i = 0
    while i < len(rows):
        row = rows[i]
        if row['state'] != 1:
            i += 1
            continue
        first = i
        while i+1 < len(rows) and rows[i+1]['state'] == 1:
            if rows[i]['exit_date'] != rows[i+1]['entry_date']:
                raise ValueError('Adjacent selected quarters must join')
            i += 1
        cycle = dict(cycle_id=f"episode_{row['episode_id']:02d}",
            entry_date=rows[first]['entry_date'],exit_date=rows[i]['exit_date'],
            selected_quarters=i-first+1)
        if sessions.index(cycle['entry_date']) < 20:
            omitted.append(dict(cycle,reason='incomplete_prior20_warmup'))
        else:
            cycles.append(cycle)
        i += 1
    return cycles, omitted


def financial_screen(summary, account):
    completed = [r for r in summary['position_episodes'] if r['completed']]
    later = [r for r in completed if r['entry_date'] >= '2020-01-01']
    fraction = lambda records: sum(r['net_PnL_CNY'] > 0 for r in records)/len(records) if records else None
    interval = block_interval(list(summary['annual_contributions_CNY'].values()))
    full_win, later_win = fraction(completed), fraction(later)
    absolute_limit = account['metrics']['maximum_drawdown'] <= .4
    checks = dict(terminal_settled=summary['terminal_settled'],full_net_positive=summary['full_net_PnL_CNY'] > 0,
        later_net_positive=summary['later_net_contribution_CNY'] > 0,full_completed_episodes=len(completed) >= 6,
        later_new_completed_episodes=len(later) >= 3,
        full_net_win_majority=full_win is not None and full_win > .5,
        later_net_win_majority=later_win is not None and later_win > .5,
        annual_block_lower_positive=interval[0] > 0,
        no_observed_risk_breach=summary['risk_within_all_observed_limits'] and absolute_limit)
    return dict(checks=checks,conditional_account_screen_passed=all(checks.values()),
        completed_episodes=len(completed),later_new_completed_episodes=len(later),
        full_net_episode_win_fraction=full_win,later_new_net_episode_win_fraction=later_win,
        block_mean_annual_PnL_CNY_2_5_97_5=interval,bootstrap_replications=5000,
        block_years=2,seed=20260921,net_positive_EV_verified=False,paper_promotion_allowed=False,
        fresh_OOS=False,actual_fills_verified=False,source_quality_certified=False,new_forward_days=0)


def calculate(snapshots):
    cadence = json.loads(snapshots['cadence_result'])
    gross = json.loads(snapshots['gross_result'])
    if cadence['screen']['passed'] is not True or gross['diagnostic']['gross_screen_passed'] is not True:
        raise ValueError('Completed cadence and gross passes required')
    rows = cadence['intervals']
    bars = json.loads(snapshots['bars'])
    sessions = json.loads(snapshots['sessions'])
    actions = json.loads(snapshots['actions'])
    annual = json.loads(snapshots['gold_annual_audit'])['rows']
    terminal = json.loads(snapshots['gold_terminal_review'])
    if (len(rows) != 40 or rows[0]['entry_date'] != '2014-01-02'
            or rows[-1]['exit_date'] != '2024-01-02' or sum(r['sessions'] for r in rows) != 2434
            or len(bars) != 4908 or len(sessions) != 2454
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'
            or any(r['asset_id'] == ASSET for r in actions['events'])):
        raise ValueError('Exact source partition and retained gold inputs required')
    known = [r for r in annual if 2014 <= r['year'] <= 2023]
    if ([r['year'] for r in known] != list(range(2014,2024))
            or any(r['cash_distribution'] != '0' or not r['split_zero'] for r in known)
            or terminal['no_distributions_or_unit_splits_reported'] is not True
            or terminal['covers_terminal_session'] != '2024-01-02'):
        raise ValueError('Gold zero-action source coverage required')
    cycles, omitted = episode_cycles(rows, sessions)
    accounts, summaries, screens = {}, {}, {}
    for minimum in (0,5,10):
        for slippage in (0,10,30):
            key = f'min{minimum}_slip{slippage}'
            account = run_allocation_account(bars,sessions=sessions,assets=(ASSET,),cycles=cycles,actions=[],
                config=AllocationConfig(minimum_commission=minimum,slippage_bps=slippage,execution_price_field='open'))
            accounts[key] = account
            summaries[key] = summarize_account(account,[])
            screens[key] = financial_screen(summaries[key],account)
    return dict(study_id='cny_depreciation_gold_demand_quarterly_v1',accounts=accounts,summaries=summaries,
        scenario_screens=screens,primary_summary=summaries['min5_slip10'],diagnostic=screens['min5_slip10'],
        source_episode_cycles=cycles,warmup_omitted_episodes=omitted,signals_recomputed=False,
        cash_reference=dict(initial_CNY=10000,ending_CNY=10000,net_PnL_CNY=0,interest=0),
        net_positive_EV_verified=False,paper_promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
