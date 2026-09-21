"""One fixed option-activity hypothesis; pure gross diagnostics, never an account."""
from collections import defaultdict
from datetime import date
import math

import numpy as np
import pandas as pd


def monthly_rows(counts, levels, sessions):
    """Prior complete month -> second close next month -> second close after it."""
    if not sessions or sessions != sorted(set(sessions)) or list(levels.index) != sessions:
        raise ValueError('Dense ordered price calendar required')
    if not np.isfinite(levels).all() or (levels <= 0).any():
        raise ValueError('Finite positive total-return index required')
    if [r['date'] for r in counts] != [str(d) for d in sessions]:
        raise ValueError('Every source date must exactly match the calendar once')
    groups = defaultdict(list)
    for row in counts:
        for key in ('CALL_VOLUME', 'PUT_VOLUME', 'LEAVES_CALL_QTY', 'LEAVES_PUT_QTY'):
            v = row[key]
            if (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    or v < 0 or ('LEAVES' in key and v == 0) or int(v) != v):
                raise ValueError('Integer nonnegative counts and positive OI required')
        groups[row['date'][:7]].append(row)
    months = list(groups)
    numbers = [int(m[:4])*12 + int(m[5:]) for m in months]
    if any(b-a != 1 for a, b in zip(numbers, numbers[1:])) or any(len(v) < 2 for v in groups.values()):
        raise ValueError('Consecutive complete calendar months with two anchors required')
    returns = levels.pct_change()
    rows = []
    for i, month in enumerate(months[:-2]):
        source = groups[month]
        cv, pv, co, po = [sum(r[k] for r in source) for k in
            ('CALL_VOLUME', 'PUT_VOLUME', 'LEAVES_CALL_QTY', 'LEAVES_PUT_QTY')]
        if min(cv, pv, co, po) <= 0:
            raise ValueError('Zero monthly activity is unknown, not a neutral score')
        score = math.log((cv/co)/(pv/po))
        entry = date.fromisoformat(groups[months[i+1]][1]['date'])
        exit_day = date.fromisoformat(groups[months[i+2]][1]['date'])
        available = date.fromisoformat(source[-1]['date'])
        prior = levels.loc[:available]
        rows.append({'feature_month': month, 'last_source_date': str(available),
            'assumed_available_after': groups[months[i+1]][0]['date'],
            'entry_date': str(entry), 'exit_date': str(exit_day), 'score': score,
            'selected': int(score > 0), 'total_return': float(levels.loc[exit_day]/levels.loc[entry]-1),
            'prior_10_session_return': float(prior.iloc[-1]/prior.iloc[-11]-1) if len(prior)>10 else None,
            'prior_10_session_volatility': float(returns.loc[:available].iloc[-10:].std(ddof=1)) if len(prior)>10 else None})
    return rows


def _correlation(x, y):
    a, b = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _description(rows):
    if not rows:
        return {'n': 0, 'spearman': None, 'both_states': False,
                'selection_difference': None, 'selected_mean': None}
    x = np.array([r['score'] for r in rows])
    y = np.array([r['total_return'] for r in rows])
    z = np.array([r['selected'] for r in rows])
    return {'n': len(rows), 'spearman': _correlation(x, y), 'both_states': len(set(z)) == 2,
        'selected_months': int(sum(z)), 'mean_exposure': float(z.mean()),
        'selected_mean': float(y[z == 1].mean()) if z.any() else None,
        'selected_win_rate': float((y[z == 1] > 0).mean()) if z.any() else None,
        'unconditional_mean': float(y.mean()),
        'selection_difference': float(((z-z.mean())*y).mean())}


def summarize(rows, *, replications=5000, seed=20260921, block_months=3):
    if len(rows) < 6 or replications < 50 or not 1 <= block_months < len(rows):
        raise ValueError('Insufficient rows or invalid fixed bootstrap settings')
    x, y = np.array([r['score'] for r in rows]), np.array([r['total_return'] for r in rows])
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Nonfinite diagnostic inputs')
    n = len(rows)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(replications, math.ceil(n/block_months)))
    indices = ((starts[:, :, None] + np.arange(block_months)) % n).reshape(replications, -1)[:, :n]
    xr, yr = (pd.DataFrame(a[indices]).rank(axis=1).to_numpy() for a in (x, y))
    xr = xr - xr.mean(axis=1)[:, None]
    yr = yr - yr.mean(axis=1)[:, None]
    denominator = np.sqrt((xr*xr).sum(axis=1)*(yr*yr).sum(axis=1))
    correlations = np.divide((xr*yr).sum(axis=1), denominator,
        out=np.full(replications, np.nan), where=denominator>0)
    valid = correlations[np.isfinite(correlations)]
    interval = [float(v) for v in np.quantile(valid, [0.05, 0.95])] if len(valid) else [None, None]
    full = _description(rows)
    early = _description([r for r in rows if r['entry_date'] < '2023-01-01'])
    later = _description([r for r in rows if r['entry_date'] >= '2023-01-01'])
    passed = bool(len(valid) >= .95*replications and interval[0] is not None and interval[0] > 0
        and full['both_states'] and early['both_states'] and later['both_states']
        and later['spearman'] is not None and later['spearman'] > 0
        and full['selection_difference'] > 0 and later['selection_difference'] > 0
        and later['selected_mean'] > 0)
    controls = [r for r in rows if r.get('prior_10_session_return') is not None]
    coefficient = None
    if len(controls) >= 10:
        design = np.array([[1, r['score'], r['prior_10_session_return'],
            r['prior_10_session_volatility']] for r in controls])
        if np.linalg.matrix_rank(design) == 4:
            coefficient = float(np.linalg.lstsq(design,
                [r['total_return'] for r in controls], rcond=None)[0][1])
    return {**full, 'early': early, 'later': later,
        'bootstrap_spearman_5_95': interval, 'bootstrap_valid_replicates': len(valid),
        'bootstrap_replications': replications, 'bootstrap_block_months': block_months,
        'bootstrap_seed': seed, 'controlled_score_coefficient_descriptive_only': coefficient,
        'annual': {year: _description([r for r in rows if r['entry_date'].startswith(year)])
            for year in sorted({r['entry_date'][:4] for r in rows})},
        'gross_screen_passed': passed,
        'decision': 'account_review_required' if passed else 'not_qualified_close_fixed_hypothesis',
        'not_qualified_does_not_prove_zero_population_effect': True,
        'net_account_result': False, 'formal_positive_ev_verified': False,
        'historical_availability_verified': False, 'counts_as_forward_paper_days': 0,
        'qualifies_for_promotion': False, 'multiple_testing_adjusted': False}
