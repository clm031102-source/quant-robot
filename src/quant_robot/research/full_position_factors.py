"""Frozen daily technical predicates; causal and not an admission to research.

Smart money is a price/volume proxy, never an identification of institutions.
Fibonacci anchors use only the preceding 60 sessions, never future swing pivots.
"""
from itertools import combinations
from decimal import Decimal
import numpy as np
import pandas as pd

from quant_robot.research.indicator_combinations import indicator_frame


CATALOG = {
    'sma20_trend': 'trend', 'ema13_34_trend': 'trend',
    'macd12_26_9_positive': 'trend', 'donchian20_breakout': 'trend',
    'rsi14_above50': 'momentum', 'rsi14_reentry30': 'momentum',
    'stochastic14_3': 'momentum', 'cci20_positive': 'momentum',
    'signed_amount20_positive': 'flow_proxy', 'cmf20_positive': 'flow_proxy',
    'mfi14_above50': 'flow_proxy', 'obv20_positive': 'flow_proxy',
    'amount5_over20': 'liquidity', 'amihud20_below_prior60': 'liquidity',
    'close_above_vwap20': 'liquidity', 'up_volume15': 'liquidity',
    'ema21_55_fibonacci': 'fibonacci', 'fib382_reentry60': 'fibonacci',
    'fib618_reentry60': 'fibonacci', 'fib786_recovery60': 'fibonacci',
    'bollinger20_upper_breakout': 'volatility', 'bollinger20_lower_reentry': 'volatility',
    'atr14_below_prior60': 'volatility', 'adx14_directional': 'volatility',
}


def candidate_combinations():
    """All 1/2/3-component AND combinations of the exact 24 predicates."""
    return [tuple(c) for n in (1, 2, 3) for c in combinations(CATALOG, n)]


def wilder(series, window):
    """SMA seed after a contiguous window, then Wilder recursion; gaps reset."""
    source = np.asarray(series, dtype=float)
    out = np.full(len(source), np.nan)
    pending = []
    previous = np.nan
    for i, value in enumerate(source):
        if not np.isfinite(value):
            pending = []; previous = np.nan
        elif np.isfinite(previous):
            previous = (previous * (window - 1) + value) / window
            out[i] = previous
        else:
            pending.append(value)
            if len(pending) == window:
                previous = float(np.mean(pending)); out[i] = previous
    return pd.Series(out, index=series.index)


def feature_frame(bars, actions):
    raw = pd.DataFrame(bars).copy()
    prices = raw[['open', 'high', 'low', 'close']].apply(pd.to_numeric)
    if (not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any()
            or (prices['high'] < prices[['open','close','low']].max(axis=1)).any()
            or (prices['low'] > prices[['open','close','high']].min(axis=1)).any()):
        raise ValueError('Complete positive internally consistent OHLC required')
    base = indicator_frame(bars, actions)
    c = base['signal_price']
    multiplier = c / pd.to_numeric(raw['close'])
    h = pd.to_numeric(raw['high']) * multiplier
    l = pd.to_numeric(raw['low']) * multiplier
    v = pd.to_numeric(raw['volume'])
    a = pd.to_numeric(raw['amount'])
    if not np.isfinite(v).all() or (v < 0).any():
        raise ValueError('Finite nonnegative share volumes required')
    # Label prices must not use the same day's close-derived adjustment factor.
    # This is an open-to-open total-return proxy, not a realized cash account.
    cash_by_ex = {}
    for action in actions:
        if action['asset_id'] == raw.iloc[0]['asset_id']:
            cash_by_ex[action['ex_date']] = cash_by_ex.get(action['ex_date'], Decimal(0)) + Decimal(str(action['cash_per_unit']))
    opens = [Decimal(str(x)) for x in raw['open']]
    if any(not x.is_finite() or x <= 0 for x in opens):
        raise ValueError('Positive finite opens required')
    open_ratios = [1.0] + [float((opens[i] + cash_by_ex.get(raw.iloc[i]['date'], Decimal(0))) / opens[i-1]) for i in range(1,len(raw))]
    open_index = float(opens[0]) * np.cumprod(open_ratios)
    out = pd.DataFrame({'date': raw['date'], 'signal_price': c, 'signal_open': open_index})

    def add(name, condition, *needed):
        known = np.logical_and.reduce([np.isfinite(np.asarray(x, dtype=float)) for x in needed])
        out[name] = np.where(known, condition.astype(float), np.nan)

    ema = lambda n: c.ewm(span=n, adjust=False, min_periods=n).mean()
    sma20 = c.rolling(20).mean()
    e13, e34, e21, e55 = ema(13), ema(34), ema(21), ema(55)
    hh20 = h.shift(1).rolling(20).max()
    add('sma20_trend', c > sma20, sma20)
    add('ema13_34_trend', e13 > e34, e13, e34)
    add('macd12_26_9_positive', base['macd_histogram'] > 0, base['macd_histogram'])
    add('donchian20_breakout', c > hh20, hh20)
    delta = c.diff()
    gain, loss = wilder(delta.clip(lower=0), 14), wilder(-delta.clip(upper=0), 14)
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100).mask((loss == 0) & (gain == 0), 50)
    add('rsi14_above50', rsi > 50, rsi)
    add('rsi14_reentry30', (rsi > 30) & (rsi.shift(1) <= 30), rsi, rsi.shift(1))
    lo14, hi14 = l.rolling(14).min(), h.rolling(14).max()
    k = 100 * (c - lo14) / (hi14 - lo14).replace(0, np.nan)
    d = k.rolling(3).mean()
    add('stochastic14_3', k > d, k, d)
    typical = (h + l + c) / 3
    mean = typical.rolling(20).mean()
    deviation = typical.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    cci = (typical - mean) / (.015 * deviation.replace(0, np.nan))
    add('cci20_positive', cci > 0, cci)
    add('signed_amount20_positive', base['pressure'] > 0, base['pressure'])
    cmf = (((2 * c - h - l) / (h - l).replace(0, np.nan)) * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    add('cmf20_positive', cmf > 0, cmf)
    flow = typical * v
    sign = typical.diff()
    positive = flow.where(sign > 0, 0).rolling(14).sum()
    negative = flow.where(sign < 0, 0).rolling(14).sum()
    mfi = 100 - 100 / (1 + positive / negative.replace(0, np.nan))
    mfi = mfi.mask((negative == 0) & (positive > 0), 100).mask((negative == 0) & (positive == 0), 50)
    add('mfi14_above50', mfi > 50, mfi, sign.rolling(14).count().where(lambda x: x == 14))
    obv = (np.sign(delta) * v).rolling(20).sum()
    add('obv20_positive', obv > 0, obv)
    amount5, amount20 = a.rolling(5).mean(), a.rolling(20).mean()
    add('amount5_over20', amount5 > amount20, amount5, amount20)
    amihud = (c.pct_change(fill_method=None).abs() / a.replace(0, np.nan)).rolling(20).mean()
    prior_illiquidity = amihud.shift(1).rolling(60).median()
    add('amihud20_below_prior60', amihud < prior_illiquidity, amihud, prior_illiquidity)
    vwap = (typical * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    add('close_above_vwap20', c > vwap, vwap)
    prior_volume = v.shift(1).rolling(20).mean()
    add('up_volume15', (delta > 0) & (v > 1.5 * prior_volume), delta, prior_volume)
    add('ema21_55_fibonacci', e21 > e55, e21, e55)
    high60, low60 = h.shift(1).rolling(60).max(), l.shift(1).rolling(60).min()
    high_index = h.shift(1).rolling(60).apply(np.argmax, raw=True)
    low_index = l.shift(1).rolling(60).apply(np.argmin, raw=True)
    rising_swing = (high_index > low_index) & (high60 > low60)
    for ratio, name in [(.382, 'fib382_reentry60'), (.618, 'fib618_reentry60')]:
        level = high60 - ratio * (high60 - low60)
        add(name, rising_swing & (c > level) & (c.shift(1) <= level), high60, low60, c.shift(1))
    level786 = low60 + .786 * (high60 - low60)
    add('fib786_recovery60', rising_swing & (c > level786), high60, low60)
    width = c.rolling(20).std(ddof=0)
    upper, lower = sma20 + 2 * width, sma20 - 2 * width
    add('bollinger20_upper_breakout', c > upper.shift(1), upper.shift(1))
    add('bollinger20_lower_reentry', (c > lower) & (c.shift(1) <= lower.shift(1)), lower, lower.shift(1))
    true_range = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    atr = wilder(true_range, 14)
    relative_atr = atr / c
    prior_atr = relative_atr.shift(1).rolling(60).median()
    add('atr14_below_prior60', relative_atr < prior_atr, relative_atr, prior_atr)
    up, down = h.diff(), -l.diff()
    plus = up.where((up > down) & (up > 0), 0).where(up.notna())
    minus = down.where((down > up) & (down > 0), 0).where(down.notna())
    pdi, mdi = 100 * wilder(plus, 14) / atr, 100 * wilder(minus, 14) / atr
    dx = (100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)).mask((pdi + mdi) == 0, 0)
    adx = wilder(dx, 14)
    add('adx14_directional', (adx > 20) & (pdi > mdi), adx, pdi, mdi)
    if set(CATALOG) != set(out) - {'date', 'signal_price', 'signal_open'}:
        raise ValueError('Exact frozen catalogue required')
    return out


def combined_state(frame, components):
    if not 1 <= len(components) <= 3 or len(set(components)) != len(components) or any(c not in CATALOG for c in components):
        raise ValueError('One to three distinct registered predicates required')
    values = frame[list(components)].to_numpy(dtype=float)
    return np.where(np.isfinite(values).all(axis=1), (values == 1).all(axis=1).astype(float), np.nan)


def screen_training(frame, *, first, last, horizon=5, minimum_selected=30):
    """Predictive factor screen, NOT a cash-account return or significance test.

    Labels start at the next open and end five sessions later. Both endpoints
    must be in the training window; no holdout label enters model selection.
    """
    if any(day > last for day in frame['date']):
        raise ValueError('Training screen may not receive evaluation dates')
    opening = frame['signal_open']
    labels = opening.shift(-(horizon + 1)) / opening.shift(-1) - 1
    eligible = (frame['date'] >= first).to_numpy() & np.isfinite(labels.to_numpy())
    y = labels.to_numpy()
    rows = []
    for components in candidate_combinations():
        values = combined_state(frame, components)
        known = eligible & np.isfinite(values)
        selected = known & (values == 1)
        other = known & (values == 0)
        n, n0 = int(selected.sum()), int(other.sum())
        valid = n >= minimum_selected and n0 >= minimum_selected and np.std(y[known]) > 0
        correlation = float(np.corrcoef(values[known], y[known])[0, 1]) if valid else None
        mean = float(y[selected].mean()) if n else None
        rows.append(dict(candidate_id='+'.join(components), components=list(components),
            families=sorted({CATALOG[c] for c in components}), training_selected_days=n,
            training_other_days=n0, training_point_biserial_IC=correlation,
            training_mean_forward_5session_return=mean,
            training_effect_vs_other=(mean-float(y[other].mean()) if n and n0 else None),
            selection_eligible=bool(valid and correlation > 0 and mean > 0),
            account_profit_claim=False, independent_observation_claim=False))
    return rows


def choose_training_candidates(rows, count=3):
    valid = [r for r in rows if r['selection_eligible']]
    return sorted(valid, key=lambda r: (-r['training_point_biserial_IC'], r['candidate_id']))[:count]
