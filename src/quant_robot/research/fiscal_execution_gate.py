"""Fixed fiscal execution-ratio hypothesis, with no I/O or research admission."""
from datetime import date
from decimal import Decimal, localcontext
import calendar
import re

HYPOTHESIS = 'general_public_budget_execution_pace_v1'
REFERENCE = 'initial_annual_report_plan'


def evaluate_fiscal_gate(*, current, prior, current_plan, prior_plan, decision_day):
    decision = _date(decision_day)
    now, before = _monthly(current, decision), _monthly(prior, decision)
    if now[0].year != before[0].year + 1 or now[0].month != before[0].month:
        raise ValueError('Current and prior must be the same elapsed month in consecutive years')
    denominator = _annual(current_plan, now[0].year, decision)
    prior_denominator = _annual(prior_plan, before[0].year, decision)
    with localcontext() as context:
        context.prec = 64
        ratio, prior_ratio = now[1] / denominator, before[1] / prior_denominator
        # Exact finite-decimal products fix the strict threshold, even for ties
        # whose repeating ratios cannot be represented by finite precision.
        selected = now[1] * prior_denominator > before[1] * denominator
        return {'economic_hypothesis_id': HYPOTHESIS, 'period': now[0].strftime('%Y-%m'),
            'decision_day': decision.isoformat(), 'reference_semantics': REFERENCE,
            'current_execution_ratio': str(ratio), 'prior_execution_ratio': str(prior_ratio),
            'execution_ratio_change': str(ratio - prior_ratio), 'selected': selected,
            'comparison': 'strictly_positive_current_minus_prior_ratio',
            'historical_availability_verified': False, 'research_admission_granted': False,
            'predictive_or_causal_effect_verified': False}


def _date(value):
    if not isinstance(value, str):
        raise ValueError('Canonical date string required')
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError('Canonical date string required')
    return result


def _amount(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,12}(?:\.[0-9]{1,6})?', value):
        raise ValueError('Explicit positive fixed-point amount string required')
    number = Decimal(value)
    if number <= 0:
        raise ValueError('Amount must be positive')
    return number


def _monthly(value, decision):
    if value.get('scope') != 'national_general_public_budget' or value.get('source_value_semantics') != 'cumulative_from_january':
        raise ValueError('National cumulative general public budget expenditure required')
    end, start, publication = (_date(value[key]) for key in ('period_end', 'period_start', 'published_date_label'))
    if start != date(end.year, 1, 1) or end.day != calendar.monthrange(end.year, end.month)[1] or not end < publication < decision:
        raise ValueError('Ended cumulative report period must be known before decision day')
    return end, _amount(value['amount_cny_100m'])


def _annual(value, year, decision):
    if type(value.get('year')) is not int or value['year'] != year or value.get('reference_semantics') != REFERENCE:
        raise ValueError('Matching initial annual report plan required')
    publication = _date(value['published_date_label'])
    if publication.year != year or publication >= decision:
        raise ValueError('Annual reference must be known before current decision day')
    return _amount(value['amount_cny_100m'])
