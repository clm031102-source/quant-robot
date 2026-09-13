"""Compare declared cash-account results without certifying strategy alpha."""
from __future__ import annotations

from datetime import date
import math

import pandas as pd

from quant_robot.paper.economics import execution_economics_from_request, normalize_execution_economics


def calendar_date(value) -> date:
    if not isinstance(value, (str, date, pd.Timestamp)):
        raise ValueError('Account dates must be explicit calendar dates')
    try:
        parsed = pd.Timestamp(value)
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid account calendar date') from exc
    if pd.isna(parsed) or parsed.tzinfo is not None or parsed != parsed.normalize():
        raise ValueError('Account dates must be timezone-free calendar dates')
    return parsed.date()


def compare_cash_accounts(strategy: dict, benchmark: dict) -> dict:
    """Require the same dates, starting cash and declared execution economics.

    These checks establish arithmetic comparability only. Source completeness,
    feasible quotes, common risk and research admission require separate proof.
    Returns are calculated from cash-account equity, never a theoretical index.
    """
    left, left_cost = _account(strategy)
    right, right_cost = _account(benchmark)
    if left['date'].tolist() != right['date'].tolist():
        raise ValueError('Cash accounts must use the same complete calendar')
    if left_cost != right_cost:
        raise ValueError('Cash accounts must use identical declared execution economics')
    if not math.isclose(left.iloc[0]['equity'], right.iloc[0]['equity'], rel_tol=0, abs_tol=1e-8):
        raise ValueError('Cash accounts must use the same initial capital')
    strategy_return = float(left.iloc[-1]['equity'] / left.iloc[0]['equity'] - 1)
    benchmark_return = float(right.iloc[-1]['equity'] / right.iloc[0]['equity'] - 1)
    from quant_robot.paper.risk_evidence import audit_cash_account_risk
    return {'comparison_type': 'same_calendar_cash_accounts_v1',
        'strategy_total_return': strategy_return, 'benchmark_total_return': benchmark_return,
        'relative_return': strategy_return - benchmark_return,
        'cash_total_return': 0.0, 'cash_return_assumption': 'zero_interest_scenario',
        'excess_over_cash': strategy_return, 'initial_capital': float(left.iloc[0]['equity']),
        'first_date': str(left.iloc[0]['date']), 'last_date': str(left.iloc[-1]['date']),
        'sessions': len(left), 'risk_adjusted_alpha_verified': False,
        'risk_comparison':{'strategy':audit_cash_account_risk(strategy), 'benchmark':audit_cash_account_risk(benchmark)},
        'source_quality_verified': False, 'research_admission_verified': False}


def _account(result):
    if not isinstance(result, dict):
        raise ValueError('A declared cash-account result is required')
    request = result.get('request', {})
    costs = normalize_execution_economics(request.get('execution_economics'))
    if execution_economics_from_request(request) != costs:
        raise ValueError('Cash-account request differs from its declared execution economics')
    if request.get('cash_annual_return', 0) != 0:
        raise ValueError('Only the explicit zero-interest cash scenario is supported')
    # A common event file is required here as well as common fees. Its hash does
    # not prove the events, prices or source revisions are independently valid.
    if result.get('accounting', {}).get('corporate_actions_fingerprint') != costs['corporate_actions_fingerprint']:
        raise ValueError('Cash-account action identity differs from its economics')
    curve = pd.DataFrame(result.get('equity_curve', []))
    if len(curve) < 2 or not {'date', 'equity', 'cash', 'dividend_receivable'}.issubset(curve.columns):
        raise ValueError('A dated cash-account equity curve is required, not a theoretical index')
    curve['date'] = curve['date'].map(calendar_date)
    if curve['date'].tolist() != sorted(set(curve['date'])):
        raise ValueError('Cash-account dates must be unique and increasing')
    if 'sessions' in request and [calendar_date(value) for value in request['sessions']] != curve['date'].tolist():
        raise ValueError('Cash-account curve differs from its declared calendar')
    for field in ('equity', 'cash', 'dividend_receivable'):
        if curve[field].map(lambda x: isinstance(x, bool)).any():
            raise ValueError('Invalid cash-account numeric values')
        curve[field] = pd.to_numeric(curve[field], errors='coerce')
        if not curve[field].map(math.isfinite).all() or (curve[field] < 0).any():
            raise ValueError('Cash-account values must be finite and nonnegative')
    if (curve['equity'] <= 0).any() or not math.isclose(
            curve.iloc[0]['equity'], costs['initial_cash'], rel_tol=0, abs_tol=1e-8):
        raise ValueError('Cash-account initial equity must equal declared initial cash')
    if not math.isclose(curve.iloc[0]['cash'], costs['initial_cash'], rel_tol=0, abs_tol=1e-8) or curve.iloc[0]['dividend_receivable'] != 0:
        raise ValueError('Comparison requires an all-cash opening without preloaded rights or holdings')
    if ((curve['cash'] + curve['dividend_receivable']) > curve['equity'] + 1e-8).any():
        raise ValueError('Cash and receivables exceed long-only account equity')
    if 'period_return' in curve:
        expected = curve['equity'].pct_change().fillna(0)
        actual = pd.to_numeric(curve['period_return'], errors='coerce')
        if not actual.map(math.isfinite).all() or ((expected - actual).abs() > 1e-9).any():
            raise ValueError('Cash-account period returns contradict its equity curve')
    return curve, costs
