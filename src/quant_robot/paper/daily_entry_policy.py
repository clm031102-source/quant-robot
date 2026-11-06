"""Opt-in 90% prior-NAV entry budget and daily retry of a fixed signal episode."""
from decimal import Decimal
from datetime import date


NAV90_DAILY_RETRY = 'nav90_daily_retry_v1'


def cycles_from_daily_targets(targets, sessions, *, episode_prefix):
    """Keep20cash warmup sessions and precommit the last session's open exit."""
    if (not isinstance(sessions,list) or not 21 <= len(sessions) <= 10000
            or sessions != sorted(set(sessions)) or not isinstance(targets,list)
            or len(targets) != len(sessions) or not isinstance(episode_prefix,str)
            or not 1 <= len(episode_prefix) <= 80):
        raise ValueError('Bounded exact daily target calendar and episode identity required')
    for day,row in zip(sessions,targets,strict=True):
        if (date.fromisoformat(day).isoformat() != day or row['execution_date'] != day
                or type(row['known']) is not bool or type(row['desired']) is not bool
                or not row['known'] and row['desired']):
            raise ValueError('Explicit causal daily target and known-state flags required')
    cycles,active=[],None
    for index in range(20,len(sessions)):
        desired=targets[index]['desired'] and index<len(sessions)-1
        if active is None and desired:
            active=dict(cycle_id=f'{episode_prefix}_{len(cycles)+1:06d}',entry_date=sessions[index])
        elif active is not None and not desired:
            cycles.append(dict(active,exit_date=sessions[index]));active=None
    return cycles


def daily_entry_plans(policy, plan, *, calendar, full_nav, holding_sessions):
    if policy is None:
        return plan
    if policy != NAV90_DAILY_RETRY or not full_nav or holding_sessions != 252:
        raise ValueError('Exact NAV90 daily retry contract with252-session holding limit required')
    expanded = {}
    for episode in plan.values():
        if episode['exit_index'] is None:
            raise ValueError('Daily retry diagnostic requires a precommitted terminal exit')
        for index in range(episode['entry_index'], episode['exit_index']):
            expanded[index] = dict(episode, cycle_id=f"{episode['cycle_id']}::attempt:{index}",
                episode_id=episode['cycle_id'], entry_index=index, entry_date=calendar[index])
    return expanded


def entry_budget(policy, *, cash, prior_nav, ordinary_budget, full_nav):
    if policy == NAV90_DAILY_RETRY:
        return min(cash, Decimal('.90')*prior_nav)
    return cash if full_nav else min(ordinary_budget, cash)


def policy_evidence():
    return dict(contract=NAV90_DAILY_RETRY, entry_budget_fraction_previous_NAV=.9,
        entry_budget_includes_commission=True, actual_open_cost_must_fit_precommitted_budget=True,
        daily_rebalance=False, retry='flat_and_current_positive_episode_after_cooldown',
        holding_clock='each_actual_successful_entry', same_open_exit_and_reentry=False,
        sizing_capacity='one_percent_mean_previous20_complete_session_volumes',
        current_day_volume_gate='retrospective_conditional_fill_assumption_not_known_at_open')
