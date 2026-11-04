"""Frozen GPRT account plan and reporting; no acquisition or study admission.

Real market inputs require a separate one-use registration. These pure helpers
also support synthetic verification before any new historical price access.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import math

import numpy as np

from quant_robot.paper import comparative_allocation
from quant_robot.research.equity_gold_diagnostic import position_episodes

STUDY = 'published_geopolitical_threat_gold_monthly_v1'
ASSET = 'CN_ETF_XSHG_518880'
MONTHS = tuple(f'{year}{month:02d}' for year in range(2022, 2026)
               for month in range(1, 13) if (year, month) >= (2022, 3))


def make_plan(calendar, cadence_rows):
    """Map frozen monthly source states to dates, without reading market prices."""
    if (not calendar or calendar != sorted(set(calendar))
            or any(date.fromisoformat(d).isoformat() != d for d in calendar)
            or any(d > '2025-12-31' for d in calendar)):
        raise ValueError('Unique historical calendar ending no later than 2025 required')
    if [r['month'] for r in cadence_rows] != list(MONTHS):
        raise ValueError('All 46 fixed monthly states required')
    if any(r['state'] is not None and type(r['state']) is not int for r in cadence_rows):
        raise ValueError('Integer or unknown monthly state required')
    if any(r['state'] not in (None, 0, 1) for r in cadence_rows):
        raise ValueError('Invalid source state')
    first = next((i for i, d in enumerate(calendar) if d >= '2022-03-15'), None)
    if first is None or first < 20 or calendar[-1][:7] != '2025-12':
        raise ValueError('Fixed first decision, 20 prior sessions and 2025 terminal required')
    sessions = calendar[first-20:]
    first_session = sessions[20]
    later_start = next(d for d in sessions if d >= '2024-01-01')
    decisions = []
    for row in cadence_rows:
        month = row['month']; cutoff = f'{month[:4]}-{month[4:]}-15'
        opening = next((d for d in sessions if d >= cutoff), None)
        if opening is None or opening[:7] != cutoff[:7]:
            raise ValueError('Each monthly decision needs an eligible opening in its month')
        decisions.append(dict(month=month, state=row['state'], decision_date=cutoff,
                              opening_date=opening))
    cycles = []
    for i, decision in enumerate(decisions):
        if decision['state'] != 1 or (i and decisions[i-1]['state'] == 1):
            continue
        next_cash = next((r['opening_date'] for r in decisions[i+1:] if r['state'] != 1), sessions[-1])
        start = sessions.index(decision['opening_date'])
        end = min(sessions.index(next_cash), start + 252, len(sessions)-1)
        if end <= start:
            raise ValueError('No same-session source roundtrip allowed')
        cycles.append(dict(cycle_id='gprt_'+decision['month'],
            entry_date=sessions[start], exit_date=sessions[end],
            source_episode_start=decision['month'],
            new_later_episode=decision['month'] >= '202401'))
    policy = comparative_allocation.policy_template(study_id=STUDY,
        first_session=first_session, terminal_session=sessions[-1], later_start=later_start)
    return dict(study_id=STUDY, asset=ASSET, sessions=sessions,
                decisions=decisions, strategy_cycles=cycles, comparison_policy=policy)


def monthly_contributions(curve, sessions):
    """All 46 civil months, including cash and the partial first study month."""
    if [r['date'] for r in curve] != sessions:
        raise ValueError('Exact frozen daily account calendar required')
    values = {month: Decimal(0) for month in MONTHS}
    previous = Decimal(10000)
    for row in curve:
        equity = Decimal(str(row['equity']))
        if not equity.is_finite():
            raise ValueError('Finite daily equity required')
        contribution = equity - previous
        if row['date'] < sessions[20]:
            if contribution != 0:
                raise ValueError('No investment outcomes during warmup')
        else:
            values[row['date'][:7].replace('-', '')] += contribution
        previous = equity
    if sum(values.values()) != previous - 10000:
        raise ValueError('Monthly contributions do not reconcile to terminal equity')
    return {month: float(value) for month, value in values.items()}


def block_interval(values):
    """Fixed circular six-month blocks, truncated to 46 observations per draw."""
    data = np.asarray(values, dtype=float)
    if data.shape != (46,) or not np.isfinite(data).all():
        raise ValueError('46 finite monthly contributions required')
    starts = np.random.default_rng(20260922).integers(0, 46, size=(5000, 8))
    indices = ((starts[:, :, None] + np.arange(6)) % 46).reshape(5000, 48)[:, :46]
    interval = np.quantile(data[indices].mean(axis=1), [.025, .975], method='linear')
    return dict(mean_monthly_PnL_CNY=float(data.mean()),
        lower_95_CNY=float(interval[0]), upper_95_CNY=float(interval[1]),
        replicates=5000, block_months=6, sample_months=46, seed=20260922,
        quantile_method='linear', final_block='truncate_after_46_months',
        interpretation='historical_sensitivity_not_independent_EV_certification')


def report_comparison(result, *, plan, actions):
    """Apply the original necessary tests, without selecting a winning cost case."""
    # The historical engine's terminal flag covers positions/receivables only.
    # A recorded entitlement can still be unpaid before its ex date at terminal.
    # Preserve the old economic engine and audit those rights explicitly here.
    action_map = {a['event_id']: a for a in actions}
    for case, roles in result['accounts'].items():
        for role, value in roles.items():
            paid = {e['event_id']: Decimal(str(e['amount']))
                    for e in value['corporate_action_journal'] if e['kind'] == 'cash_paid_after_fills'}
            pending = []
            for event in value['corporate_action_journal']:
                if event['kind'] != 'record_entitlement' or not event['quantity']:
                    continue
                earned = (Decimal(event['quantity'])*Decimal(str(action_map[event['event_id']]['cash_per_unit']))).quantize(
                    Decimal('.01'), rounding=ROUND_HALF_UP)
                remaining = earned - paid.get(event['event_id'], Decimal(0))
                if remaining > 0:
                    pending.append(dict(event_id=event['event_id'], unpaid_CNY=float(remaining)))
            value['terminal_entitlement_audit'] = dict(unpaid_rights=pending,
                terminal_settled=value['risk']['terminal_settled'] and not pending)
            result['comparisons'][case]['accounts'][role]['terminal_settled'] = value['terminal_entitlement_audit']['terminal_settled']
    primary = result['comparisons']['min5_slip10']
    summary = primary['accounts']['strategy']
    accounts = result['accounts']['min5_slip10']
    monthly = monthly_contributions(accounts['strategy']['equity_curve'], plan['sessions'])
    interval = block_interval(list(monthly.values()))
    episodes = position_episodes(accounts['strategy'], actions)
    cycle_map = {r['cycle_id']: r for r in plan['strategy_cycles']}
    for episode in episodes:
        original = cycle_map[episode['cycle_id']]
        if episode['entry_date'] != original['entry_date']:
            raise ValueError('Entry retry or episode identity changed')
        episode['source_episode_start'] = original['source_episode_start']
        episode['new_later_episode'] = original['new_later_episode']
    completed = [r for r in episodes if r['completed']]
    later = [r for r in completed if r['new_later_episode']]
    if summary['terminal_settled'] and not math.isclose(
            sum(r['net_PnL_CNY'] for r in completed), summary['net_PnL_CNY'], abs_tol=1e-7):
        raise ValueError('Settled episodes do not reconcile with account net PnL')
    checks = dict(
        full_net_positive=summary['net_PnL_CNY'] > 0,
        later_net_positive=summary['later_net_contribution_CNY'] > 0,
        completed_full_episodes_at_least_six=len(completed) >= 6,
        completed_new_later_episodes_at_least_three=len(later) >= 3,
        majority_full_episodes_profitable=sum(r['net_PnL_CNY'] > 0 for r in completed)*2 > len(completed),
        majority_new_later_episodes_profitable=sum(r['net_PnL_CNY'] > 0 for r in later)*2 > len(later),
        monthly_interval_lower_positive=interval['lower_95_CNY'] > 0,
        beat_holding_full=summary['net_PnL_CNY'] > primary['accounts']['holding']['net_PnL_CNY'],
        beat_cash_full=summary['net_PnL_CNY'] > primary['accounts']['cash']['net_PnL_CNY'],
        beat_holding_later=summary['later_net_contribution_CNY'] > primary['accounts']['holding']['later_net_contribution_CNY'],
        beat_cash_later=summary['later_net_contribution_CNY'] > primary['accounts']['cash']['later_net_contribution_CNY'],
        no_primary_strategy_risk_breach=not summary['risk_breaches'],
        primary_strategy_terminal_settled=summary['terminal_settled'],
        primary_controls_terminal_settled=all(v['terminal_settled'] for v in primary['accounts'].values()))
    return dict(study_id=STUDY, primary_case='min5_slip10', checks=checks,
        conditional_screen_passed=all(checks.values()), primary_summary=summary,
        monthly_PnL_CNY=monthly, uncertainty=interval, primary_position_episodes=episodes,
        completed_full_episodes=len(completed), completed_new_later_episodes=len(later),
        cost_summaries=result['comparisons'], comparison=result,
        fresh_out_of_sample=False, net_positive_EV_verified=False,
        paper_promotion_allowed=False, final_holdout_allowed=False,
        live_boundary_allowed=False, new_forward_days=0)


def calculate(*, bars, actions, plan, cadence_rows):
    """Numerical execution only; real use must be wrapped by an exclusive claim."""
    if plan != make_plan(plan['sessions'], cadence_rows):
        raise ValueError('Frozen price-independent calendar plan changed')
    result = comparative_allocation.run_comparison(bars, sessions=plan['sessions'],
        asset=ASSET, strategy_cycles=plan['strategy_cycles'], actions=actions,
        policy=plan['comparison_policy'])
    return report_comparison(result, plan=plan, actions=actions)
