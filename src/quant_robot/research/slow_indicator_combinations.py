"""Prospective slow trend rules. No source loader, CLI or research admission."""
import pandas as pd
from quant_robot.research.indicator_combinations import indicator_frame

RULES = ('slow_macd', 'slow_macd_pressure')


def slow_features(bars, actions):
    """Only same-close causal total return, MACD(12,26,9) and pressure(20)."""
    frame = indicator_frame(bars, actions)
    price = frame['signal_price']
    average = price.rolling(120, min_periods=120).mean()
    known = average.notna() & frame['macd_histogram'].notna()
    frame['sma120'] = average
    frame['slow_macd'] = ((price > average) & (frame['macd_histogram'] > 0)).where(known).astype('boolean')
    frame['slow_macd_pressure'] = (frame['slow_macd'] & (frame['pressure'] > 0)).where(known & frame['pressure'].notna()).astype('boolean')
    below = (price < average).where(average.notna()).astype('boolean')
    frame['trend_exit'] = (below & below.shift(1)).where(average.notna() & average.shift(1).notna()).astype('boolean')
    return frame


def separated_cycles(sessions, entries, exits, *, first):
    """Enter every five sessions, exit daily after two closes below SMA120.

    A MACD/amount sign reversal alone cannot exit. Missing entry/exit information
    closes an active signal episode next open; missing observations are retained.
    A held episode continues through the engine's 252-session forced liquidation:
    it does not manufacture new entries until a genuine off/on signal episode.
    """
    if sessions != sorted(set(sessions)) or len(entries) != len(sessions) or len(exits) != len(sessions):
        raise ValueError('Exact ordered calendar and signal arrays required')
    start = sessions.index(first)
    if start < 120:
        raise ValueError('120 completed trend sessions required')
    cycles, active = [], None
    terminal = len(sessions) - 1
    for index in range(start - 1, terminal):
        execution = index + 1
        unknown = pd.isna(entries[index]) or pd.isna(exits[index])
        exit_now = unknown or bool(exits[index])
        if active is not None:
            if exit_now:
                cycles.append(dict(cycle_id=f'slow_{len(cycles)+1:04d}',
                                   entry_date=sessions[active], exit_date=sessions[execution]))
                active = None
            continue  # No exit and re-entry at the same open.
        if (not exit_now and (index - start + 1) % 5 == 0
                and bool(entries[index]) and execution < terminal):
            active = execution
    if active is not None:
        cycles.append(dict(cycle_id=f'slow_{len(cycles)+1:04d}',
                           entry_date=sessions[active], exit_date=sessions[-1]))
    return cycles
