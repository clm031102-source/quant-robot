"""Prospective entry headroom and early trims; never a guaranteed price cap."""
from decimal import Decimal

BUFFER = dict(entry_budget_cny=800, trim_trigger_cny=900, trim_target_cny=800,
              breach_action='permanent_no_restart', topup=False)


def buffer_limits(policy, config):
    """Keep old accounts unchanged; buffered accounts require a fixed open policy."""
    hard = Decimal(str(config.max_position_cny))
    if policy is None:
        return hard, hard, hard
    if not isinstance(policy, dict) or policy != BUFFER:
        raise ValueError('Exact prospective 800/900/800 position buffer required')
    if config.execution_price_field != 'open' or hard != Decimal(1000):
        raise ValueError('Buffered orders require raw open fills and headroom')
    return Decimal(800), Decimal(900), Decimal(800)
