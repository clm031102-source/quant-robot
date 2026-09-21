"""Sharp missing-observation bounds; callers need separate real-factor admission."""
from fractions import Fraction


def breadth_bounds(rows, *, total_value_cents, sessions):
    """Preserve complete report weights and every session, without imputing signs."""
    if (type(total_value_cents) is not int or total_value_cents <= 0
            or type(sessions) is not int or sessions <= 0
            or not isinstance(rows, list) or not 1 <= len(rows) <= 5000):
        raise ValueError('Positive integer total, sessions and explicit source rows required')
    total = lower = unknown = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'value_cents', 'positive_days', 'unknown_days'}:
            raise ValueError('Exact source amount and day counts required')
        value, positive, missing = (row[k] for k in ('value_cents', 'positive_days', 'unknown_days'))
        if (any(type(v) is not int for v in (value, positive, missing)) or value <= 0
                or min(positive, missing) < 0 or positive+missing > sessions):
            raise ValueError('Invalid amount or overlapping/excessive day counts')
        total += value; lower += value*positive; unknown += value*missing
    if total != total_value_cents:
        raise ValueError('Full report denominator must reconcile; no partial renormalization')
    denominator = total*sessions
    state = 1 if 2*lower > denominator else 0 if 2*(lower+unknown) <= denominator else None
    return {'lower': str(Fraction(lower, denominator)), 'upper': str(Fraction(lower+unknown, denominator)),
        'lower_numerator': lower, 'unknown_numerator': unknown, 'denominator': denominator,
        'identified_state': state, 'complete_flow_coverage': unknown == 0,
        'covers_stale_holdings_or_source_revisions': False}
