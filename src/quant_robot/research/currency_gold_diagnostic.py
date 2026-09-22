"""Frozen 40-quarter currency/gold gross diagnostic; not a trading account."""
from decimal import Decimal
import json
import math
import numpy as np

ASSET = 'CN_ETF_XSHG_518880'


def open_return(entry, exit_date, entry_open, exit_open, events):
    prices = [Decimal(str(v)) for v in (entry_open, exit_open)]
    if entry >= exit_date or any(not v.is_finite() or v <= 0 for v in prices):
        raise ValueError('Ordered dates and positive finite raw opens required')
    cash = Decimal(0)
    for event in events:
        if event['asset_id'] != ASSET:
            continue
        amount = Decimal(str(event['cash_per_share']))
        if (event['kind'] != 'cash_dividend' or not amount.is_finite() or amount <= 0
                or event['record_date'] >= event['ex_date']):
            raise ValueError('Reviewed positive gold cash distribution required')
        if entry <= event['record_date'] < exit_date:
            cash += amount
    return float((prices[1] + cash - prices[0]) / prices[0])


def describe(rows):
    z = np.array([r['state'] == 1 for r in rows], dtype=float)
    y = np.array([r['return_value'] for r in rows])
    n = np.array([r['sessions'] for r in rows])
    exposure = float((z*n).sum()/n.sum())
    return dict(intervals=len(rows), selected_intervals=int(z.sum()),
        selected_episodes=len({r['episode_id'] for r in rows if r['state'] == 1}),
        session_transitions=int(n.sum()), selected_session_fraction=exposure,
        D_daily_log=float(((z-exposure)*np.log1p(y)).sum()/n.sum()),
        selected_mean_gross=float(y[z == 1].mean()) if z.any() else None,
        selected_positive_intervals=int((y[z == 1] > 0).sum()),
        selected_positive_fraction=float((y[z == 1] > 0).mean()) if z.any() else None,
        unconditional_mean_gross=float(y.mean()))


def summarize(rows):
    later = [r for r in rows if r['entry_date'] >= '2020-01-01']
    if len(rows) != 40 or len(later) != 16:
        raise ValueError('Exact 40 full and 16 later quarters required')
    for row in rows:
        if ((row['state'] is not None and (type(row['state']) is not int or row['state'] not in (0, 1)))
                or type(row['sessions']) is not int or row['sessions'] <= 0
                or not math.isfinite(row['return_value']) or row['return_value'] <= -1):
            raise ValueError('Valid state, duration and gross return required')
    full, late = describe(rows), describe(later)
    z = np.array([r['state'] == 1 for r in rows], dtype=float)
    n = np.array([r['sessions'] for r in rows])
    log_returns = np.log1p([r['return_value'] for r in rows])
    starts = np.random.default_rng(20260922).integers(0, 40, size=(5000, 10))
    ids = ((starts[:, :, None]+np.arange(4)) % 40).reshape(5000, 40)
    zr, nr, lr = z[ids], n[ids], log_returns[ids]
    exposure = (zr*nr).sum(axis=1)/nr.sum(axis=1)
    effects = ((zr-exposure[:, None])*lr).sum(axis=1)/nr.sum(axis=1)
    interval = [float(v) for v in np.quantile(effects, [.025, .975], method='linear')]
    positive = lambda value: value is not None and value > 0
    checks = dict(effect_lower_positive=interval[0] > 0,
        full_mean_positive=positive(full['selected_mean_gross']),
        later_mean_positive=positive(late['selected_mean_gross']),
        later_effect_positive=positive(late['D_daily_log']))
    return dict(full=full, later_2020_onward=late, checks=checks, gross_screen_passed=all(checks.values()),
        bootstrap_D_daily_log_2_5_97_5=interval, bootstrap_replications=5000, block_quarters=4,
        seed=20260922, net_positive_EV_verified=False, fresh_OOS=False,
        multiple_testing_adjusted=False, historical_vintage_verified=False,
        completed_account_trade_count=None)


def calculate(snapshots):
    cadence = json.loads(snapshots['cadence_result'])
    rows = [dict(r) for r in cadence['intervals']]
    if cadence['screen']['passed'] is not True or cadence['returns_computed'] is not False:
        raise ValueError('Passed source-only cadence required')
    sessions = json.loads(snapshots['market_sessions'])
    bars = json.loads(snapshots['market_bars'])
    gold = [r for r in bars if r['asset_id'] == ASSET]
    if (len(bars) != 4908 or len(sessions) != 2454 or sessions != sorted(set(sessions))
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'
            or len(gold) != len(sessions) or sorted(r['date'] for r in gold) != sessions):
        raise ValueError('Exact retained daily gold history and sessions required')
    actions = json.loads(snapshots['market_actions'])
    annual = json.loads(snapshots['market_gold_annual_audit'])['rows']
    annual = [r for r in annual if 2014 <= r['year'] <= 2023]
    terminal = json.loads(snapshots['market_gold_terminal_review'])
    if (actions['cash_amount_basis'] != 'announced_not_investor_verified'
            or any(r['asset_id'] == ASSET for r in actions['events'])
            or [r['year'] for r in annual] != list(range(2014, 2024))
            or any(r['code'] != '518880' or Decimal(r['cash_distribution']) != 0
                   or not r['split_zero'] or not r['unit_identity_passed'] for r in annual)
            or terminal['covers_terminal_session'] != '2024-01-02'
            or terminal['no_distributions_or_unit_splits_reported'] is not True):
        raise ValueError('Retained gold zero cash/split coverage required')
    anchors = [r['entry_date'] for r in rows]+[rows[-1]['exit_date']]
    expected = [min(d for d in sessions if d.startswith(f'{y}-{m:02d}-'))
                for y in range(2014, 2024) for m in (1, 4, 7, 10)]+['2024-01-02']
    if anchors != expected or sum(r['sessions'] for r in rows) != 2434:
        raise ValueError('Frozen quarterly partition differs')
    by = {r['date']: r for r in gold}
    for i, row in enumerate(rows):
        if (row['exit_date'] != anchors[i+1]
                or sessions.index(row['exit_date'])-sessions.index(row['entry_date']) != row['sessions']):
            raise ValueError('Frozen interval dates and session count differ')
        row['return_value'] = open_return(row['entry_date'], row['exit_date'],
            by[row['entry_date']]['open'], by[row['exit_date']]['open'], actions['events'])
    return dict(diagnostic=summarize(rows), observations=rows, net_account_run=False,
        new_forward_paper_days=0, ETF_open_values_used=41,
        price_basis='one_share_raw_open_to_open_entitled_cash_gross_no_reinvestment',
        historical_currency_publication_assumed=True, signals_recomputed=False)
