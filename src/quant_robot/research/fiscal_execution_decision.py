"""Readout of a frozen conditional account comparison, never EV certification."""
import math
from decimal import Decimal, ROUND_HALF_UP


def compare_fiscal_accounts(selected, unconditional):
    def metrics(account):
        if account.get('artifact_type') != 'event_hold_conditional_cash_account_v1':
            raise ValueError('Explicit event-hold account artifact required')
        values = account['metrics']
        for key in ('initial_equity', 'ending_equity', 'pnl_cny'):
            if isinstance(values[key], bool) or not isinstance(values[key], (int, float)) or not math.isfinite(values[key]):
                raise ValueError('Finite account values required')
        if not math.isclose(values['ending_equity'] - values['initial_equity'], values['pnl_cny'], abs_tol=1e-8):
            raise ValueError('Reported PnL does not reconcile')
        return values
    left, right = metrics(selected), metrics(unconditional)
    contract_left = {key: value for key, value in selected['request'].items() if key != 'entries'}
    contract_right = {key: value for key, value in unconditional['request'].items() if key != 'entries'}
    if contract_left != contract_right or selected['input_provenance'] != unconditional['input_provenance']:
        raise ValueError('Comparison requires identical account rules, calendar and price inputs')
    if selected['accounting'] != unconditional['accounting']:
        raise ValueError('Comparison requires identical corporate-action source and assumptions')
    selected_pnl, unconditional_pnl = (Decimal(str(value['pnl_cny'])).quantize(
        Decimal('.01'), rounding=ROUND_HALF_UP) for value in (left, right))
    excess = selected_pnl - unconditional_pnl
    reasons = []
    if selected_pnl <= 0:
        reasons.append('selected_absolute_pnl_not_positive')
    if excess <= 0:
        reasons.append('selected_minus_unconditional_not_positive')
    if left['completed_round_trips'] < 15:
        reasons.append('fewer_than_15_completed_round_trips')
    if selected['risk']['breaches']:
        reasons.append('selected_account_risk_breached')
    if not selected['risk']['terminal_settled']:
        reasons.append('selected_terminal_account_unsettled')
    return {'selected_pnl_cny': float(selected_pnl), 'unconditional_pnl_cny': float(unconditional_pnl),
        'selected_minus_unconditional_pnl_cny': float(excess),
        'decision_precision': 'each_account_pnl_half_up_CNY_0.01_then_subtract',
        'decision': 'conditional_candidate_review_only' if not reasons else 'fixed_contract_not_passed',
        'reasons': reasons, 'formal_significance_test': None,
        'minimum_commission_cny': selected['request']['minimum_commission'],
        'cash_amount_policy': selected['request']['cash_amount_policy'],
        'net_positive_ev_verified': False, 'promotion_allowed': False, 'new_forward_paper_days': 0}
