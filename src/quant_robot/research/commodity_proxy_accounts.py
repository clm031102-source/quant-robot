"""One fixed 36-account soybean-meal diagnostic; no qualification is granted.

This numerical kernel has no source access or execution admission. Its caller
must freeze originals, implementation and environment before any real run.
"""
from collections import Counter
from math import isfinite

import numpy as np

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.paper.daily_entry_policy import NAV90_DAILY_RETRY, cycles_from_daily_targets
from quant_robot.paper.daily_recovery import RECOVERY_40_DAILY_RETRY
from quant_robot.research.commodity_curve_proxy import build_proxy_signals


ASSET = 'CN_ETF_XSHE_159985'
WINDOWS = {'development': ('2020-01-02', '2021-12-31'),
           'later': ('2022-01-04', '2024-06-28')}
FEES = tuple((minimum, slip) for minimum in (0, 5, 10) for slip in (0, 10, 30))
PRIMARY = 'min5_slip10'
INITIAL = 10000


def paired_bootstrap(strategy, control):
    """Daily paired log excess, including initial capital and all cash days."""
    if len(strategy) != len(control) or len(strategy) < 20:
        raise ValueError('Aligned daily curves with at least20 observations required')
    if any(a['date'] != b['date'] for a, b in zip(strategy, control, strict=True)):
        raise ValueError('Paired curves require identical dates')
    a = np.asarray([INITIAL, *(row['equity'] for row in strategy)], dtype=float)
    b = np.asarray([INITIAL, *(row['equity'] for row in control)], dtype=float)
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.any(a <= 0) or np.any(b <= 0):
        raise ValueError('Finite positive NAV required')
    excess = np.log(a[1:]/a[:-1])-np.log(b[1:]/b[:-1])
    rng = np.random.default_rng(20261106)
    length, block, repeats = len(excess), 20, 5000
    starts = rng.integers(0, length, size=(repeats, (length+block-1)//block))
    means = []
    for batch in range(0, repeats, 500):
        indices = (starts[batch:batch+500, :, None]+np.arange(block)) % length
        means.extend(excess[indices.reshape(len(indices), -1)[:, :length]].mean(axis=1).tolist())
    return dict(method='paired_daily_log_excess_circular_block_bootstrap',
        block_sessions=block, replicates=repeats, seed=20261106,
        quantile_method='linear', observations=length, includes_cash_days=True,
        initial_NAV_each=INITIAL, mean_daily_log_excess=float(excess.mean()),
        fifth_percentile_mean_daily_log_excess=float(np.quantile(means, .05, method='linear')),
        inference_scope='used_history_single_ETF_conditional_diagnostic_not_new_blind_evidence')


def completed_roundtrips(fills):
    """Count actual fully closed attempts, including multi-fill liquidations."""
    opened, closed = {}, []
    for fill in fills:
        identity, quantity = fill['cycle_id'], fill['quantity']
        if type(quantity) is not int or quantity <= 0:
            raise ValueError('Positive actual whole-unit fills required')
        if fill['side'] == 'buy':
            if identity in opened or any(row['cycle_id'] == identity for row in closed):
                raise ValueError('One successful buy per attempt required')
            opened[identity] = dict(cycle_id=identity, entry_date=fill['date'],
                                    quantity=quantity, remaining=quantity)
        elif fill['side'] == 'sell':
            if identity not in opened or quantity > opened[identity]['remaining']:
                raise ValueError('Sale must reduce its actual owned attempt')
            opened[identity]['remaining'] -= quantity
            if opened[identity]['remaining'] == 0:
                closed.append({**opened.pop(identity), 'exit_date': fill['date']})
        else:
            raise ValueError('Only actual buy and sell fills supported')
    return dict(completed=closed, unclosed=list(opened.values()), count=len(closed),
                minimum_30_observation_met=len(closed) >= 30,
                minimum_is_not_profit_evidence=True)


def annual_decomposition(curve):
    """Year slices reference the prior actual NAV; never restart capital/peak."""
    result, prior = {}, float(INITIAL)
    for row in curve:
        year, nav = row['date'][:4], row['equity']
        if year not in result:
            result[year] = dict(first_date=row['date'], starting_NAV=prior)
        result[year].update(last_date=row['date'], ending_NAV=nav,
            pnl_cny=nav-result[year]['starting_NAV'],
            net_return=nav/result[year]['starting_NAV']-1)
        prior = nav
    return result


def summarize_account(account):
    return dict(metrics=account['metrics'], terminal_settled=account['risk']['terminal_settled'],
        recorded_risk_breaches=account['risk']['breaches'],
        annual=annual_decomposition(account['equity_curve']),
        actual_buy_fills=sum(fill['side'] == 'buy' for fill in account['fills']),
        actual_sell_fills=sum(fill['side'] == 'sell' for fill in account['fills']),
        events_by_reason=dict(Counter(row['reason'] for row in account['events'])),
        roundtrips=completed_roundtrips(account['fills']),
        pauses_and_recoveries=account['daily_recovery_journal'],
        unknown_execution_flag_rows=account['unknown_execution_flag_rows'])


def support_assessment(accounts, bootstrap):
    expected = {f'{window}/{rule}/min{minimum}_slip{slip}' for window in WINDOWS
                for rule in ('curve', 'holding') for minimum, slip in FEES}
    if set(accounts) != expected:
        raise ValueError('All36 fixed accounts required; omitted fee paths forbidden')
    reasons = {}
    for identity, account in accounts.items():
        dd = account['metrics']['maximum_drawdown']
        if not isfinite(dd) or dd < 0:
            raise ValueError('Finite nonnegative actual drawdown required')
        failures = []
        if dd > .40:
            failures.append('actual_drawdown_exceeds_40percent')
        if not account['risk']['terminal_settled']:
            failures.append('terminal_inventory_or_receivable_unsettled')
        if failures:
            reasons[identity] = failures
    primary = {window: accounts[f'{window}/curve/{PRIMARY}']['metrics']['ending_equity']
               for window in WINDOWS}
    control = accounts[f'later/holding/{PRIMARY}']['metrics']['ending_equity']
    checks = dict(both_primary_strategies_net_positive=all(value > INITIAL for value in primary.values()),
        later_primary_exceeds_matched_holding=primary['later'] > control,
        later_all_nine_strategy_fee_paths_net_positive=all(
            accounts[f'later/curve/min{minimum}_slip{slip}']['metrics']['ending_equity'] > INITIAL
            for minimum, slip in FEES),
        paired_bootstrap_lower_bound_positive=bootstrap['fifth_percentile_mean_daily_log_excess'] > 0,
        all_36_actual_drawdowns_within_40percent_and_terminal_settled=not reasons)
    return dict(checks=checks, financial_conditions_supported=all(checks.values()),
        account_comparability_failures=reasons, qualification_granted=False,
        true_forward_admitted=False, real_forward_days_added=0,
        qualification_reason='Conditional historical execution and source evidence are not certified')


def calculate(*, lifecycle, settlements, sessions, bars, actions, guard=None, account_sink=None):
    """Execute exactly the fixed pair of windows, rules and all nine fee paths.

    A production caller supplies guard to recheck frozen bytes/environment before
    and after every account, plus an exclusive claim before invoking this kernel.
    """
    if not sessions or sessions[0] != '2019-12-30' or sessions[-1] != '2024-06-28':
        raise ValueError('Exact full signal-calendar endpoints required')
    signals = build_proxy_signals(lifecycle, settlements, sessions)
    by_date = {row['execution_date']: row for row in signals['signals']}
    if any(row['asset_id'] != ASSET for row in bars) or any(row['asset_id'] != ASSET for row in actions):
        raise ValueError('Only the frozen159985 ETF may enter this diagnostic')
    allowed_dates = {day for day in sessions if any(start <= day <= end for start, end in WINDOWS.values())}
    if any(row['date'] not in allowed_dates for row in bars):
        raise ValueError('ETF observations outside the two frozen windows forbidden')
    accounts, summaries, cash = {}, {}, {}
    for window, (start, end) in WINDOWS.items():
        calendar = [day for day in sessions if start <= day <= end]
        if len(calendar) < 21 or calendar[0] != start or calendar[-1] != end:
            raise ValueError('Exact frozen window endpoints and complete warmup required')
        selected_bars = [row for row in bars if start <= row['date'] <= end]
        targets = [by_date[day] for day in calendar]
        holding = [dict(execution_date=day, known=True, desired=True) for day in calendar]
        cash[window] = dict(initial_cash=INITIAL, ending_cash=INITIAL,
            pnl_cny=0, interest_assumption=0, equity_curve=[dict(date=day, equity=INITIAL) for day in calendar])
        for rule, desired in (('curve', targets), ('holding', holding)):
            cycles = cycles_from_daily_targets(desired, calendar, episode_prefix=f'{window}_{rule}')
            for minimum, slip in FEES:
                identity = f'{window}/{rule}/min{minimum}_slip{slip}'
                if guard is not None:
                    guard('before', identity)
                account = run_allocation_account(selected_bars, sessions=calendar, assets=[ASSET],
                    cycles=cycles, actions=actions, config=AllocationConfig(initial_cash=INITIAL,
                        max_position_cny=INITIAL, max_position_fraction=1, max_drawdown=.40,
                        execution_price_field='open', commission_bps=5, minimum_commission=minimum,
                        slippage_bps=slip), daily_recovery=RECOVERY_40_DAILY_RETRY,
                    entry_policy=NAV90_DAILY_RETRY)
                if guard is not None:
                    guard('after', identity)
                if account_sink is not None:
                    account_sink(identity, account)
                accounts[identity] = account
                summaries[identity] = summarize_account(account)
    bootstrap = paired_bootstrap(accounts[f'later/curve/{PRIMARY}']['equity_curve'],
                                 accounts[f'later/holding/{PRIMARY}']['equity_curve'])
    return dict(artifact_type='commodity_proxy_36_account_diagnostic_v1',
        hypothesis_count=1, account_count=len(accounts), cash_benchmark_count=len(cash),
        windows=WINDOWS, initial_cash_each_window=INITIAL, accounts=accounts,
        account_summaries=summaries, cash_benchmarks=cash, signal_evidence=signals,
        bootstrap=bootstrap, assessment=support_assessment(accounts, bootstrap),
        drawdown_observation_basis='modeled_daily_close_NAV_not_certified_intraday_maximum',
        unknown_execution_flags_are_conditional=True,
        current_day_volume_is_retrospective_fill_assumption=True,
        source_quality_verified=False, qualified=False, real_forward_days_added=0)
