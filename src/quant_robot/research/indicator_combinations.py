"""Finite causal indicator comparisons on an explicitly admitted historical source.

No data acquisition or admission occurs here. Signal calculations are forward
only; the account runner supplies raw-price fills, cash actions and fixed costs.
"""
from __future__ import annotations

import json
from decimal import Decimal
import numpy as np
import pandas as pd

from quant_robot.paper.comparative_allocation import run_comparison

RULES = ('pressure_positive', 'macd_positive', 'pressure_and_macd', 'equal_weight_zscore')
ASSETS = ('CN_ETF_XSHG_510300', 'CN_ETF_XSHG_518880')


def _positive(series):
    out = pd.Series(pd.NA, index=series.index, dtype='boolean')
    known = series.notna()
    out.loc[known] = series.loc[known] > 0
    return out


def indicator_frame(bars, actions):
    frame = pd.DataFrame(bars).copy()
    if (frame.empty or frame['asset_id'].nunique() != 1
            or frame['date'].tolist() != sorted(set(frame['date']))):
        raise ValueError('One asset on a unique ordered calendar required')
    close = pd.to_numeric(frame['close'], errors='raise')
    amount = pd.to_numeric(frame['amount'], errors='raise')
    if not np.isfinite(close).all() or (close <= 0).any() or not np.isfinite(amount).all() or (amount < 0).any():
        raise ValueError('Positive prices and nonnegative finite amounts required')
    cash = {}
    for action in actions:
        if action['asset_id'] == frame.iloc[0]['asset_id']:
            if float(action.get('share_multiplier', 1)) != 1 or float(action['cash_per_unit']) < 0:
                raise ValueError('Only previously reviewed cash distributions supported')
            cash[action['ex_date']] = cash.get(action['ex_date'], Decimal(0)) + Decimal(str(action['cash_per_unit']))
    exact_close = [Decimal(str(value)) for value in frame['close']]
    ratios, signs = [1.0], [float('nan')]
    for index in range(1, len(frame)):
        numerator = exact_close[index] + cash.get(frame.iloc[index]['date'], Decimal(0))
        change = numerator - exact_close[index-1]
        ratios.append(float(numerator / exact_close[index-1]))
        signs.append(1.0 if change > 0 else -1.0 if change < 0 else 0.0)
    growth = pd.Series(ratios, index=frame.index)
    price = close.iloc[0] * growth.cumprod()
    direction = pd.Series(signs, index=frame.index)
    pressure = (amount * direction).rolling(20, min_periods=20).sum() / amount.rolling(20, min_periods=20).sum().replace(0, np.nan)
    macd = price.ewm(span=12, adjust=False, min_periods=12).mean() - price.ewm(span=26, adjust=False, min_periods=26).mean()
    histogram = (macd - macd.ewm(span=9, adjust=False, min_periods=9).mean()) / price

    def zscore(series):
        prior = series.shift(1).rolling(252, min_periods=252)
        return (series - prior.mean()) / prior.std(ddof=0).replace(0, np.nan)

    blend = .5 * zscore(pressure) + .5 * zscore(histogram)
    output = pd.DataFrame(dict(date=frame['date'], signal_price=price, pressure=pressure, macd_histogram=histogram, blended_zscore=blend))
    output['pressure_positive'] = _positive(pressure)
    output['macd_positive'] = _positive(histogram)
    output['pressure_and_macd'] = (output['pressure_positive'] & output['macd_positive']).where(pressure.notna() & histogram.notna())
    output['equal_weight_zscore'] = _positive(blend)
    return output


def state_cycles(sessions, states, *, first, cadence):
    if cadence not in (1, 5) or len(states) != len(sessions) or sessions != sorted(set(sessions)):
        raise ValueError('Frozen cadence and exact calendar states required')
    start = sessions.index(first)
    if start < 20:
        raise ValueError('Complete account warmup required')
    cycles, entry = [], None
    terminal = len(sessions) - 1
    for index in range(start - 1, terminal, cadence):
        desired = bool(states[index]) if pd.notna(states[index]) else False
        execution = index + 1
        if entry is not None and not desired:
            cycles.append(dict(cycle_id=f'episode_{len(cycles)+1:04d}', entry_date=sessions[entry], exit_date=sessions[execution]))
            entry = None
        elif entry is None and desired and execution < terminal:
            entry = execution
    if entry is not None:
        cycles.append(dict(cycle_id=f'episode_{len(cycles)+1:04d}', entry_date=sessions[entry], exit_date=sessions[-1]))
    return cycles


def daily_pnl(account):
    rows = account['equity_curve']
    equity = pd.Series([r['equity'] for r in rows], index=[r['date'] for r in rows], dtype=float)
    return equity.diff().fillna(equity.iloc[0] - account['config']['initial_cash'])


def uncertainty(strategy, holding, *, replications=5000, block=20, seed=20261010, hypotheses=16):
    """Paired circular blocks; account trajectories are never re-simulated."""
    values = np.column_stack([np.asarray(strategy, dtype=float), np.asarray(strategy) - np.asarray(holding)])
    if len(values) < block or not np.isfinite(values).all():
        raise ValueError('Sufficient finite paired evaluation observations required')
    rng = np.random.default_rng(seed)
    means = np.empty((replications, 2))
    offsets = np.arange(block)
    blocks = (len(values) + block - 1) // block
    for i in range(replications):
        indexes = ((rng.integers(0, len(values), size=blocks)[:, None] + offsets) % len(values)).ravel()[:len(values)]
        means[i] = values[indexes].mean(axis=0)
    q = .05 / hypotheses
    return dict(mean_daily_PnL_CNY=values[:, 0].mean(), mean_daily_difference_CNY=values[:, 1].mean(),
        net_PnL_mean_CI95_CNY=np.quantile(means[:, 0], [.025, .975]).tolist(),
        paired_difference_mean_CI95_CNY=np.quantile(means[:, 1], [.025, .975]).tolist(),
        corrected_one_sided_net_lower_CNY=float(np.quantile(means[:, 0], q)),
        corrected_one_sided_difference_lower_CNY=float(np.quantile(means[:, 1], q)),
        correction='Bonferroni16_within_batch_not_all_historical_search',
        bootstrap_replications=replications, block_sessions=block, seed=seed, evaluation_sessions=len(values))


def calculate(snapshots, *, progress=None):
    proposal = json.loads(snapshots['proposal'])
    bars = json.loads(snapshots['bars'])
    sessions = json.loads(snapshots['sessions'])
    actions = json.loads(snapshots['actions'])['events']
    policy = json.loads(snapshots['comparison_policy'])
    if (tuple(proposal['assets']) != ASSETS or tuple(proposal['rules']) != RULES
            or proposal['cadences_sessions'] != [1, 5]
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'
            or len(sessions) != 2454 or len(bars) != 4908):
        raise ValueError('Exact retained universe, calendar and finite experiment required')
    findings, full_accounts, signals = [], {}, {}
    for asset in ASSETS:
        asset_bars = sorted([r for r in bars if r['asset_id'] == asset], key=lambda r:r['date'])
        if [r['date'] for r in asset_bars] != sessions:
            raise ValueError('Missing or duplicate source sessions')
        source_actions = [a for a in actions if a['asset_id'] == asset]
        frame = indicator_frame(asset_bars, source_actions)
        # JSON nulls preserve unknown states rather than silently labeling them false.
        signals[asset] = json.loads(frame.to_json(orient='records'))
        for rule in RULES:
            for cadence in (1, 5):
                case = f'{asset}__{rule}__every{cadence}'
                cycles = state_cycles(sessions, frame[rule].tolist(), first=proposal['first_session'], cadence=cadence)
                result = run_comparison(asset_bars, sessions=sessions, asset=asset, strategy_cycles=cycles, actions=source_actions, policy=policy)
                full_accounts[case] = dict(result, strategy_cycles=cycles)
                primary = result['comparisons']['min5_slip10']
                summary = primary['accounts']['strategy']
                accounts = result['accounts']['min5_slip10']
                pnls = {role:daily_pnl(account) for role,account in accounts.items()}
                evaluation = {role:values.loc[proposal['evaluation_first']:] for role,values in pnls.items()}
                interval = uncertainty(evaluation['strategy'].to_numpy(), evaluation['holding'].to_numpy())
                annual = {str(year):float(pnls['strategy'][[d.startswith(str(year)) for d in pnls['strategy'].index]].sum()) for year in range(2015, 2024)}
                folds = []
                for year in proposal['evaluation_years']:
                    mask = [d.startswith(str(year)) for d in pnls['strategy'].index]
                    folds.append(dict(year=year,strategy_PnL_CNY=float(pnls['strategy'][mask].sum()),holding_PnL_CNY=float(pnls['holding'][mask].sum()),selection='fixed_no_fit_no_overlapping_folds',capital_reset=False))
                stress = daily_pnl(result['accounts']['min10_slip30']['strategy']).loc[proposal['evaluation_first']:].sum()
                checks = dict(full_net_positive=summary['net_PnL_CNY'] > 0,
                    evaluation_net_positive=float(evaluation['strategy'].sum()) > 0,
                    later_net_positive=summary['later_net_contribution_CNY'] > 0,
                    beat_holding_evaluation=float((evaluation['strategy']-evaluation['holding']).sum()) > 0,
                    profitable_evaluation_years=sum(f['strategy_PnL_CNY'] > 0 for f in folds) >= 3,
                    completed_episodes=summary['completed_episode_count'] >= 30,
                    drawdown=summary['maximum_drawdown'] <= .08,
                    no_risk_breaches=not summary['risk_breaches'],terminal_settled=summary['terminal_settled'],
                    corrected_net_lower_positive=interval['corrected_one_sided_net_lower_CNY'] > 0,
                    corrected_difference_lower_positive=interval['corrected_one_sided_difference_lower_CNY'] > 0,
                    high_cost_evaluation_positive=float(stress) > 0)
                findings.append(dict(case_id=case,asset=asset,rule=rule,cadence=cadence,
                    primary=rule==proposal['primary_rule'] and cadence==proposal['primary_cadence_sessions'],
                    summary=summary,comparison=primary,annual_PnL_CNY=annual,evaluation_folds=folds,
                    development_PnL_CNY=float(pnls['strategy'].loc[proposal['first_session']:proposal['development_last']].sum()),
                    evaluation_PnL_CNY=float(evaluation['strategy'].sum()),evaluation_holding_PnL_CNY=float(evaluation['holding'].sum()),
                    high_cost_evaluation_PnL_CNY=float(stress),uncertainty=interval,checks=checks,
                    conditional_screen_passed=all(checks.values()),
                    cost_summaries=result['comparisons'],unknown_signal_sessions=int(frame.loc[frame['date']>=proposal['first_session'],rule].isna().sum())))
                if progress:
                    progress(dict(completed=len(findings),total=16,case_id=case,primary_net_PnL_CNY=summary['net_PnL_CNY']))
    return dict(study_id=proposal['study_id'],findings=findings,accounts=full_accounts,signals=signals,
        conditional_pass_count=sum(r['conditional_screen_passed'] for r in findings),hypotheses=16,
        fresh_out_of_sample=False,net_positive_EV_verified=False,paper_promotion_allowed=False,
        final_holdout_allowed=False,live_boundary_allowed=False,new_forward_days=0,
        source_limitations=proposal['source_limitations'])
