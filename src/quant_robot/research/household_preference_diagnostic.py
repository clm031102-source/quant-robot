"""Pure calculations for one proposed household-preference gross diagnostic.

No I/O, source certification, registration, or execution permission is provided.
Callers must separately qualify historical versions and the complete calendar.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Context, Decimal, InvalidOperation, localcontext
import re


@dataclass(frozen=True)
class SurveyObservation:
    quarter: str
    available_on: date
    stock_preference_pct: object


def _quarter_number(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9]{4}Q[1-4]', value) is None:
        raise ValueError('report quarter must have YYYYQ1 through YYYYQ4 form')
    return int(value[:4]) * 4 + int(value[-1]) - 1


def _number(value, *, percentage=False):
    if isinstance(value, bool) or value is None:
        raise ValueError('values must be finite numeric observations')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('values must be finite numeric observations') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('values must be finite and nonnegative')
    if (percentage and number > 100) or (not percentage and number == 0):
        raise ValueError('percentage must be within 0..100; index level must be positive')
    return number


def _annual_values(observations):
    if not isinstance(observations, Mapping) or len(observations) != 5:
        raise ValueError('exactly five consecutive report quarters are required')
    ordered = sorted(observations, key=_quarter_number)
    numbers = [_quarter_number(q) for q in ordered]
    if any(b - a != 1 for a, b in zip(numbers, numbers[1:])):
        raise ValueError('report quarters must be consecutive')
    return {q: _number(observations[q], percentage=True) for q in ordered}


def visible_annual_window(reports: Sequence[SurveyObservation], as_of: date) -> dict[str, Decimal]:
    """Batch all reports available on the cutoff day before selecting five quarters.

    The caller supplies an explicitly reviewed availability day, not quarter end.
    Future values are not validated or used; visible duplicate versions require
    a separate review rather than silently selecting one.
    """
    if type(as_of) is not date:
        raise ValueError('as-of must be an explicit date')
    visible = {}
    for report in reports:
        if not isinstance(report, SurveyObservation) or type(report.available_on) is not date:
            raise ValueError('each report needs an explicit availability date')
        number = _quarter_number(report.quarter)
        if report.available_on > as_of:
            continue
        if number in visible:
            raise ValueError('duplicate visible report quarter requires version review')
        visible[number] = report
    if not visible:
        raise ValueError('no report is visible at the cutoff')
    latest = max(visible)
    required = range(latest - 4, latest + 1)
    if any(number not in visible for number in required):
        raise ValueError('five consecutive visible report quarters are required')
    return _annual_values({visible[n].quarter: visible[n].stock_preference_pct for n in required})


def annual_preference_gate(observations: Mapping[str, object]) -> int:
    """Strictly below the preceding four quarters' mean holds; equality is cash."""
    values = list(_annual_values(observations).values())
    with localcontext(Context()) as context:
        # Bound the value to percentages above, then retain every supplied
        # fractional digit for the sign comparison, including near ties.
        context.prec = max(64, max(-v.as_tuple().exponent for v in values) + 6)
        return int(4 * values[-1] < sum(values[:-1], Decimal(0)))


def _ordered_dates(values, label):
    dates = list(values)
    if not dates or any(type(value) is not date for value in dates):
        raise ValueError(label + ' must contain explicit dates')
    if any(right <= left for left, right in zip(dates, dates[1:])):
        raise ValueError(label + ' must be strictly ordered and unique')
    return dates


def event_log_selection_diagnostic(anchors: Sequence[date], signals: Sequence[int],
        index_levels: Sequence[object], calendar_sessions: Sequence[date]) -> dict:
    """One descriptive, session-weighted gross log selection difference.

    Session counts come from the supplied qualified calendar, never civil-day
    differences. Neither the difference nor its ex-post comparator is an account
    return. The terminal anchor has no signal. No significance test is supplied.
    """
    dates = _ordered_dates(anchors, 'anchors')
    sessions = _ordered_dates(calendar_sessions, 'calendar sessions')
    if len(dates) < 2 or len(signals) != len(dates) - 1:
        raise ValueError('signals must be one fewer than at least two anchors')
    if len(index_levels) != len(dates):
        raise ValueError('one index level is required at every anchor')
    if any(type(value) is not int or value not in (0, 1) for value in signals):
        raise ValueError('signals must be integer zero or one')
    positions = {value: index for index, value in enumerate(sessions)}
    if dates[0] != sessions[0] or dates[-1] != sessions[-1] or any(d not in positions for d in dates):
        raise ValueError('anchors must belong to the complete bounded calendar')
    counts = [positions[b] - positions[a] for a, b in zip(dates, dates[1:])]
    levels = [_number(value) for value in index_levels]
    with localcontext(Context(prec=64)):
        total = Decimal(sum(counts))
        exposure = sum(n * z for n, z in zip(counts, signals)) / total
        changes = [(right / left).ln() for left, right in zip(levels, levels[1:])]
        selected = sum(z * change for z, change in zip(signals, changes)) / total
        comparator = exposure * sum(changes) / total
        terms = [(Decimal(z) - exposure) * change / total for z, change in zip(signals, changes)]
        unrounded = sum(terms)
        # The decision precision is frozen before outcome access. In an exactly
        # constant-growth example, independent logarithms leave ~1e-64 noise.
        # Keep that raw value for audit, but do not classify it as an advantage.
        difference = unrounded.quantize(Decimal('1e-40'))
        reject = difference <= 0 or len(set(signals)) < 2
        return {
            'kind': 'conditional_historical_event_log_selection_diagnostic',
            'interval_count': len(signals), 'session_counts': counts,
            'total_close_to_close_transitions': int(total),
            'session_weighted_exposure': str(exposure),
            'mean_selected_gross_log_change': str(selected),
            'matched_exposure_gross_log_change': str(comparator),
            'gross_daily_log_selection_difference': str(difference),
            'unrounded_gross_daily_log_selection_difference': str(unrounded),
            'decision_decimal_places': 40,
            'calculation_precision': 64,
            'rounding': 'ROUND_HALF_EVEN',
            'interval_contributions': [str(term) for term in terms],
            'signal_switches': sum(a != b for a, b in zip(signals, signals[1:])),
            'decision': 'reject_fixed_diagnostic' if reject else 'positive_descriptive_only_requires_account_review',
            'net_account_result': False, 'risk_compliance_verified': False,
            'formal_positive_ev_verified': False, 'qualifies_for_promotion': False,
            'research_admission_granted': False,
        }
