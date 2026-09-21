"""Frozen broad-RMB-reserve-cut endpoint cost diagnostic; no account simulation."""
from bisect import bisect_right
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
import json
import math

import numpy as np

from quant_robot.research.disclosed_flow_diagnostic import open_return
from quant_robot.research.us_variance_risk_diagnostic import cn_sessions, price_anchors


def event_intervals(events, sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered CN sessions required')
    if len({r['event_id'] for r in events}) != len(events):
        raise ValueError('Unique announcement identities required')
    candidates = []
    for event in events:
        available, effective = (event[k] for k in ('conservative_available_date', 'first_effective_date'))
        if any(date.fromisoformat(d).isoformat() != d for d in (available, effective)):
            raise ValueError('ISO civil dates required')
        candidates.append((bisect_right(sessions, max(available, effective)), event))
    rows, skipped, last_exit = [], [], -1
    for i, event in sorted(candidates, key=lambda p: (p[0], p[1]['event_id'])):
        if i <= last_exit:
            skipped.append(dict(event_id=event['event_id'], reason='overlap_or_exit_session'))
        elif i+20 >= len(sessions):
            skipped.append(dict(event_id=event['event_id'], reason='incomplete_terminal_interval'))
        else:
            rows.append(dict(event_id=event['event_id'], entry_date=sessions[i], exit_date=sessions[i+20], sessions=20))
            last_exit = i+20
    return rows, skipped


def _decimal(value, *, positive=False):
    x = Decimal(str(value))
    if not x.is_finite() or (x <= 0 if positive else x < 0):
        raise ValueError('Finite valid nonnegative value required')
    return x


def endpoint(entry, exit_, entry_open, exit_open, actions, minimum, slippage_bp):
    if date.fromisoformat(entry) >= date.fromisoformat(exit_):
        raise ValueError('Strictly forward endpoints required')
    a, b = _decimal(entry_open, positive=True), _decimal(exit_open, positive=True)
    minimum, slip = _decimal(minimum), _decimal(slippage_bp)/10000
    if slip >= 1:
        raise ValueError('Slippage must be below100percent')
    buy = (a*(1+slip)).quantize(Decimal('.001'), rounding=ROUND_CEILING)
    sell = (b*(1-slip)).quantize(Decimal('.001'), rounding=ROUND_FLOOR)
    if sell <= 0:
        raise ValueError('Positive rounded sell quote required')
    def commission(value):
        return max(minimum, value*Decimal('.0005')).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    quantity = int(Decimal(1000)//(buy*100))*100
    while quantity and quantity*buy+commission(quantity*buy) > 1000:
        quantity -= 100
    dividend = Decimal(0)
    for action in actions:
        if (action['asset_id'] != 'CN_ETF_XSHG_510300' or action['kind'] != 'cash_dividend'
                or action['cash_amount_basis'] != 'gross'):
            raise ValueError('Reviewed gross ETF cash distribution required')
        cash = _decimal(action['cash_per_share'])
        if entry <= action['record_date'] < exit_:
            dividend += cash
    buy_fee = commission(quantity*buy) if quantity else Decimal(0)
    sell_fee = commission(quantity*sell) if quantity else Decimal(0)
    debit = quantity*buy+buy_fee
    exit_credit = quantity*sell-sell_fee
    cash = quantity*dividend
    pnl = exit_credit+cash-debit
    return dict(shares=quantity, raw_entry_open=float(a), raw_exit_open=float(b),
        modeled_buy_price=float(buy), modeled_sell_price=float(sell), buy_debit_CNY=float(debit),
        exit_credit_CNY=float(exit_credit), cash_entitlement_CNY=float(cash),
        total_commission_CNY=float(buy_fee+sell_fee), net_PnL_CNY=float(pnl),
        one_share_gross_return=open_return(entry, exit_, a, b, actions))


def describe(rows):
    n = len(rows)
    total = math.fsum(r['net_PnL_CNY'] for r in rows)
    return dict(opportunities=n, executed=sum(r['shares'] > 0 for r in rows),
        positive=sum(r['net_PnL_CNY'] > 0 for r in rows),
        positive_frequency=sum(r['net_PnL_CNY'] > 0 for r in rows)/n if n else None,
        mean_net_PnL_CNY=total/n if n else None, total_net_PnL_CNY=total,
        reference_capital_contribution=total/10000)


def cluster_interval(rows):
    sums = np.array([math.fsum(r['net_PnL_CNY'] for r in rows if r['entry_date'].startswith(str(y))) for y in range(2013, 2025)])
    counts = np.array([sum(r['entry_date'].startswith(str(y)) for r in rows) for y in range(2013, 2025)])
    indices = np.random.default_rng(20260921).integers(0, 12, size=(5000, 12))
    den = counts[indices].sum(axis=1)
    means = np.divide(sums[indices].sum(axis=1), den, out=np.zeros(5000), where=den > 0)
    return dict(mean_PnL_CNY_2_5_97_5=[float(x) for x in np.quantile(means, [.025, .975])],
        zero_count_draws=int((den == 0).sum()), replications=5000, years=list(range(2013, 2025)), seed=20260921)


def summarize(rows):
    if not rows or any(not '2013-01-01' <= r['entry_date'] <= '2024-06-28'
                       or not math.isfinite(r['net_PnL_CNY']) for r in rows):
        raise ValueError('Finite fixed-window observations required')
    full = describe(rows)
    later = describe([r for r in rows if r['entry_date'] >= '2020-01-01'])
    interval = cluster_interval(rows)
    checks = dict(executed_count=full['executed'] >= 12, later_executed_count=later['executed'] >= 5,
        full_mean_positive=full['mean_net_PnL_CNY'] > 0,
        later_mean_positive=later['mean_net_PnL_CNY'] is not None and later['mean_net_PnL_CNY'] > 0,
        positive_frequency=full['positive_frequency'] >= .55,
        cluster_lower_positive=interval['mean_PnL_CNY_2_5_97_5'][0] > 0)
    return dict(full=full, later_2020_onward=later, calendar_year_cluster=interval, checks=checks,
        endpoint_cost_screen_passed=all(checks.values()),
        annual={str(y): describe([r for r in rows if r['entry_date'].startswith(str(y))]) for y in range(2013, 2025)},
        net_positive_EV_verified=False, fresh_OOS=False, multiple_testing_adjusted=False,
        historical_vintage_verified=False, daily_risk_validated=False)


def reviewed_actions(snapshots, sessions):
    events = json.loads(snapshots['actions'])['events']
    events += [dict(asset_id=r['asset_id'], kind='cash_dividend', cash_amount_basis='gross',
        record_date=r['record_date'], ex_date=r['ex_date'], cash_per_share=r['cash_per_unit'])
        for r in json.loads(snapshots['early_actions'])['events']]
    if len(events) != 11 or len({r['record_date'] for r in events}) != 11:
        raise ValueError('Exactly11 unique reviewed distributions required')
    for r in events:
        if (r['asset_id'] != 'CN_ETF_XSHG_510300' or r['record_date'] not in sessions
                or r['ex_date'] not in sessions or sessions.index(r['record_date'])+1 != sessions.index(r['ex_date'])):
            raise ValueError('Reviewed record/ex session order required')
    return events


def calculate(snapshots):
    ledger = json.loads(snapshots['event_ledger'])
    reconciliation = json.loads(snapshots['annual_reconciliation'])
    if (reconciliation['status'] != 'reconciled_to_retained_official_annual_accounts'
            or reconciliation['unresolved_count_discrepancies'] or reconciliation['total_general_announcements'] != 15):
        raise ValueError('Reconciled event universe required')
    sessions = cn_sessions(snapshots)
    rows, skipped = event_intervals(ledger['included'], sessions)
    if len(rows) != 15 or skipped or sum(r['entry_date'] >= '2020-01-01' for r in rows) != 8:
        raise ValueError('Fixed15full/8later complete nonoverlapping opportunities required')
    by = {r['event_id']: r for r in ledger['included']}
    if any(any(r[k] != by[r['event_id']][k] for k in ('entry_date', 'exit_date')) for r in rows):
        raise ValueError('Recomputed calendar dates differ from frozen ledger')
    benchmark = [dict(entry_date=sessions[i], exit_date=sessions[i+20]) for i in range(0, len(sessions)-20, 20)]
    hold = dict(entry_date=sessions[0], exit_date=sessions[-1])
    anchors = sorted({r[k] for r in rows+benchmark+[hold] for k in ('entry_date', 'exit_date')})
    opens = price_anchors(snapshots, anchors, sessions)
    actions = reviewed_actions(snapshots, sessions)
    def costed(r, minimum, slip):
        return {**r, **endpoint(r['entry_date'], r['exit_date'], opens[r['entry_date']], opens[r['exit_date']], actions, minimum, slip)}
    scenarios = []
    for minimum in (0, 5, 10):
        for slip in (0, 10, 30):
            observations = [costed(r, minimum, slip) for r in rows]
            scenarios.append(dict(minimum_commission_CNY=minimum, slippage_bp=slip,
                full=describe(observations), later_2020_onward=describe([r for r in observations if r['entry_date'] >= '2020-01-01']),
                observations=observations))
    main = next(r for r in scenarios if r['minimum_commission_CNY'] == 5 and r['slippage_bp'] == 10)
    benchmark_rows = [costed(r, 5, 10) for r in benchmark]
    return dict(diagnostic=summarize(main['observations']), scenarios=scenarios, observations=main['observations'],
        descriptive_comparisons=dict(duration_matched_grid=describe(benchmark_rows), duration_matched_observations=benchmark_rows,
            buy_and_hold=costed(hold, 5, 10), not_timing_alpha_test=True), skipped=skipped,
        ETF_open_values_used=len(opens), net_account_run=False, completed_account_trade_count=None,
        new_forward_paper_days=0, price_basis='raw_open_modeled_adverse_ticks_plus_entitled_gross_cash',
        dividend_pay_date_cash_availability_modeled=False)
