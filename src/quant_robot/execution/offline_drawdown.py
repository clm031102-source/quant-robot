"""Persistent drawdown stop for explicitly versioned synthetic risk policies."""
from __future__ import annotations

from decimal import Decimal


def drawdown_evidence(state, equity, pending_cost=Decimal(0)):
    policy = state.get('admission_policy') or {}
    if policy.get('schema_version') != 2:
        return None
    previous = state.get('drawdown_guard') or {}
    peak = max(Decimal(previous.get('peak_equity', str(equity))), equity)
    if peak <= 0:
        raise ValueError('drawdown guard requires a positive observed equity peak')
    limit = Decimal(policy['max_drawdown'])
    drawdown = (peak-equity)/peak
    projected = (peak-equity+pending_cost)/peak
    return {'peak_equity':str(peak), 'book_equity':str(equity), 'book_drawdown':str(drawdown),
        'pending_cost_bound':str(pending_cost), 'projected_drawdown':str(projected),
        'max_drawdown':str(limit), 'threshold_reached':projected >= limit,
        'stop_latched':bool(previous.get('stop_latched')) or projected >= limit,
        'basis':'recorded_synthetic_book_across_sessions', 'reset_policy':'no_automatic_reset',
        'source_quality_verified':False, 'executable':False}


def apply_drawdown_evidence(state, event):
    kind, data = event['kind'], event['data']
    guard = data.get('drawdown_guard')
    if kind == 'REGISTER':
        guard = data.get('admission', {}).get('risk', {}).get('drawdown_guard')
    elif kind == 'DISPATCH_PREPARED':
        guard = data.get('risk', {}).get('drawdown_guard')
    if guard is not None:
        state['drawdown_guard'] = dict(guard)
        if guard['stop_latched'] and state.get('risk_session') is not None:
            from .offline_exposure_stop import latch_stop
            latch_stop(state, ['cumulative_drawdown'])
