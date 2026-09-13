"""Pure monthly calendar/commission screen; no I/O or research admission.

Analytical index exposure is fractional and reinvested. The fixed-notional fee
screen is not an executable account, a fill model, or a positive-EV certificate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

from quant_robot.research.household_preference_diagnostic import event_log_selection_diagnostic


HYPOTHESIS = 'month_start_cash_demand_continuation_v1'
NOTIONAL = Decimal('1000')
COMMISSION_RATE = Decimal('0.0005')
MINIMUMS = (Decimal('0'), Decimal('5'), Decimal('10'))
DECISION_QUANTUM = Decimal('1e-40')


def _month_number(day):
    return day.year * 12 + day.month - 1


def month_start_positions(calendar: Sequence[tuple[date, bool]], *, first_month: date,
                          last_month: date) -> tuple[tuple[date, int], ...]:
    """State after each observed close, using no later calendar row.

    Supply every civil day starting on the first of the initial month, including
    closed days. Prefixes are permitted here; complete studies are checked below.
    The caller must separately qualify calendar provenance and completeness.
    """
    if (type(first_month) is not date or type(last_month) is not date
            or first_month.day != 1 or last_month.day != 1 or first_month > last_month):
        raise ValueError('ordered first-of-month study boundaries required')
    if not isinstance(calendar, Sequence) or not calendar:
        raise ValueError('explicit daily calendar required')
    expected = first_month
    current_month, ordinal = None, 0
    positions = []
    for row in calendar:
        if (not isinstance(row, (tuple, list)) or len(row) != 2
                or type(row[0]) is not date or type(row[1]) is not bool):
            raise ValueError('calendar rows require a date and boolean open flag')
        day, opened = row
        if day != expected:
            raise ValueError('calendar must start at month boundary and contain every civil day in order')
        expected = day + timedelta(days=1)
        month = _month_number(day)
        if month != current_month:
            current_month, ordinal = month, 0
        if opened:
            ordinal += 1
            within_study = _month_number(first_month) <= month <= _month_number(last_month)
            positions.append((day, int(within_study and ordinal in (1, 2))))
    return tuple(positions)


def _positive_level(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('index levels must be positive finite numbers')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('index levels must be positive finite numbers') from exc
    if not number.is_finite() or number <= 0:
        raise ValueError('index levels must be positive finite numbers')
    return number


def _cycle_costs(gross):
    exit_notional = NOTIONAL * (1 + gross)
    costs = []
    for minimum in MINIMUMS:
        buy_fee = max(NOTIONAL * COMMISSION_RATE, minimum)
        sell_fee = max(exit_notional * COMMISSION_RATE, minimum)
        costs.append({'minimum_commission_cny': str(minimum),
                      'buy_fee_cny': str(buy_fee), 'sell_fee_cny': str(sell_fee),
                      'pnl_cny': str(NOTIONAL * gross - buy_fee - sell_fee)})
    return costs


def month_start_diagnostic(calendar: Sequence[tuple[date, bool]], index_levels: Mapping[date, object],
                           *, first_month: date, last_month: date) -> dict:
    """One fixed two-session rule, with all three frozen fee scenarios.

    Calendar must cover every specified month and end at a later open close.
    Every open close requires an analytical index value, even when exposure is
    zero, because the descriptive comparator uses the complete fixed window.
    Claim a separately authorized attempt before calling with real outcomes.
    """
    positions = month_start_positions(calendar, first_month=first_month, last_month=last_month)
    if (_month_number(calendar[-1][0]) <= _month_number(last_month) or not calendar[-1][1]
            or not positions):
        raise ValueError('complete study months and a later terminal open close required')
    sessions = [day for day, _ in positions]
    groups = {month: [] for month in range(_month_number(first_month), _month_number(last_month) + 1)}
    for day in sessions:
        if _month_number(day) in groups:
            groups[_month_number(day)].append(day)
    if any(len(days) < 3 for days in groups.values()):
        raise ValueError('each fixed study month needs at least three actual trading sessions')
    if not isinstance(index_levels, Mapping) or set(index_levels) != set(sessions):
        raise ValueError('exact complete open-session index coverage required')
    levels = {day: _positive_level(index_levels[day]) for day in sessions}
    gross_diagnostic = event_log_selection_diagnostic(
        sessions, [z for _, z in positions[:-1]], [levels[day] for day in sessions], sessions)
    with localcontext(Context(prec=64, rounding=ROUND_HALF_EVEN)):
        cycles = []
        for days in groups.values():
            entry, exit_day = days[0], days[2]
            gross = levels[exit_day] / levels[entry] - 1
            cycles.append({'month': entry.strftime('%Y-%m'), 'entry_close': entry.isoformat(),
                           'exit_close': exit_day.isoformat(), 'close_to_close_transitions': 2,
                           'gross_return': str(gross), 'commission_scenarios': _cycle_costs(gross)})
        scenarios = []
        for index, minimum in enumerate(MINIMUMS):
            total = sum((Decimal(c['commission_scenarios'][index]['pnl_cny']) for c in cycles), Decimal(0))
            mean = total / len(cycles)
            scenarios.append({'minimum_commission_cny': str(minimum),
                              'total_pnl_cny': str(total), 'mean_pnl_cny': str(mean),
                              'decision_mean_pnl_cny': str(mean.quantize(DECISION_QUANTUM))})
        difference = Decimal(gross_diagnostic['gross_daily_log_selection_difference'])
        if difference <= 0:
            decision = 'reject_calendar_direction'
        elif Decimal(scenarios[0]['decision_mean_pnl_cny']) <= 0:
            decision = 'reject_commission_screen'
        elif Decimal(scenarios[1]['decision_mean_pnl_cny']) <= 0:
            decision = 'defer_fee_dependent_no_account_admission'
        else:
            decision = 'review_separate_account_study_only'
    return {'kind': 'conditional_month_start_commission_screen',
            'economic_hypothesis_id': HYPOTHESIS, 'cycle_count': len(cycles),
            'selected_close_to_close_transitions': sum(z for _, z in positions[:-1]),
            'gross_diagnostic': gross_diagnostic, 'cycles': cycles,
            'commission_scenarios': scenarios, 'decision': decision,
            'entry_notional_cny': str(NOTIONAL), 'commission_rate_per_side': str(COMMISSION_RATE),
            'working_minimum_commission_cny': '5', 'minimum_commission_confirmed': False,
            'fee_precision': 'unrounded_analytical_amounts_not_actual_broker_cent_rounding',
            'calculation_precision': 64, 'decision_decimal_places': 40,
            'fixed_notional_reset_each_cycle': True, 'integer_lot_or_fill_model': False,
            'risk_compliance_certified': False, 'net_account_result': False,
            'source_audit_verified': False, 'formal_positive_ev_verified': False,
            'qualifies_for_promotion': False, 'counts_as_forward_paper_days': 0}
