"""Pure calculations for the proposed monthly gross diagnostic, with no data I/O.

Callers must qualify vintage/price inputs and obtain separate research admission.
These functions provide neither execution authority nor a net-account backtest.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from collections.abc import Mapping, Sequence


def _number(value, *, positive=False):
    if isinstance(value, bool) or value is None:
        raise ValueError('values must be finite numbers')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('values must be finite numbers') from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('values must be finite and nonnegative; index levels must be positive')
    return result


def _months(dates, *, month_starts=False):
    if not dates or any(type(item) is not date for item in dates):
        raise ValueError('dates must be explicit calendar dates')
    if month_starts and any(item.day != 1 for item in dates):
        raise ValueError('policy observations must be month starts')
    numbers = [item.year * 12 + item.month for item in dates]
    if any(right - left != 1 for left, right in zip(numbers, numbers[1:])):
        raise ValueError('dates must cover consecutive months in order')


def monthly_median_gate(observations: Mapping[date, object]) -> int:
    """Exactly 13 consecutive monthly observations from one qualified vintage.

    The caller selects the latest available month and its preceding 12 months.
    Unordered mapping insertion is harmless; gaps and extra inputs are rejected.
    """
    if not isinstance(observations, Mapping) or len(observations) != 13:
        raise ValueError('exactly thirteen policy observations are required')
    if any(type(item) is not date for item in observations):
        raise ValueError('policy keys must be calendar dates')
    dates = sorted(observations)
    _months(dates, month_starts=True)
    values = [_number(observations[item]) for item in dates]
    previous = sorted(values[:-1])
    with localcontext() as context:
        context.prec = 34
        median = (previous[5] + previous[6]) / 2
    return int(values[-1] <= median)


def monthly_selection_diagnostic(anchors: Sequence[date], signals: Sequence[int],
        index_levels: Sequence[object]) -> dict:
    """One gross selection difference; terminal anchor has no new signal.

    Date membership in the qualified trading calendar and the frozen historical
    window are responsibilities of the separately admitted execution entrypoint.
    A positive value permits further review only. It is not statistical evidence
    of positive expected value, a fill model, or a risk-compliant account result.
    """
    dates = list(anchors)
    _months(dates)
    if len(dates) < 2 or len(signals) != len(dates) - 1:
        raise ValueError('signals must be one fewer than at least two anchors')
    if len(index_levels) != len(dates):
        raise ValueError('every anchor requires exactly one index level')
    if any(type(item) is not int or item not in (0, 1) for item in signals):
        raise ValueError('signals must be integer zero or one')
    levels = [_number(item, positive=True) for item in index_levels]
    with localcontext() as context:
        context.prec = 34
        count = Decimal(len(signals))
        exposure = sum(signals) / count
        returns = [right / left - 1 for left, right in zip(levels, levels[1:])]
        selected = sum(z * value for z, value in zip(signals, returns)) / count
        comparator = exposure * sum(returns) / count
        terms = [(Decimal(z) - exposure) * value / count for z, value in zip(signals, returns)]
        difference = sum(terms)
        years = {}
        for anchor, contribution in zip(dates[:-1], terms):
            year = str(anchor.year)
            years[year] = years.get(year, Decimal(0)) + contribution
        rejected = difference <= 0 or len(set(signals)) < 2
        return {
            'kind': 'conditional_historical_gross_selection_diagnostic',
            'interval_count': len(signals), 'mean_signal': str(exposure),
            'mean_selected_gross_return': str(selected),
            'same_mean_exposure_gross_return': str(comparator),
            'gross_selection_difference': str(difference),
            'signal_switches': sum(a != b for a, b in zip(signals, signals[1:])),
            'year_contributions': {year: str(value) for year, value in years.items()},
            'decision': 'reject_fixed_diagnostic' if rejected else 'positive_descriptive_only_requires_account_review',
            'net_account_result': False, 'risk_compliance_verified': False,
            'formal_positive_ev_verified': False, 'qualifies_for_promotion': False,
            'research_admission_granted': False,
        }
