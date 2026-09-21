"""Decision-time synthetic targets compiled inside the existing admission transaction."""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import re

from .offline_admission import _check_context, _check_intent, _marks, admission_event, deny
from .offline_intent_contract import exact, fingerprint, instant, normalize_intent, version
from .offline_order_state import ACTIVE, ZERO, amount, commission, identity, money_context, public_snapshot, symbol
from .offline_portfolio_risk import portfolio_totals


TARGET_FIELDS = {'schema_version','mode','client_intent_id','idempotency_key','strategy_id','strategy_version',
    'case_id','signal_timestamp','source_as_of','source_ref','source_fingerprint','policy_fingerprint',
    'symbol','exchange','price_basis_id','target_notional_cny','limit_price','max_slippage_bps','expires_at'}


def normalize_target(value):
    exact(value, TARGET_FIELDS, 'synthetic target')
    version(value)
    if value['mode'] != 'offline_fixture_only':
        raise ValueError('only offline_fixture_only targets are supported')
    result = {**value}
    for key in ('client_intent_id','idempotency_key','strategy_id','strategy_version','case_id','source_ref','price_basis_id'):
        result[key] = identity(value[key])
    result['symbol'] = symbol(value['symbol'])
    for key in ('source_fingerprint','policy_fingerprint'):
        if not isinstance(value[key],str) or not re.fullmatch('[0-9a-f]{64}',value[key]):
            raise ValueError('target requires explicit source and policy fingerprints')
    for key in ('signal_timestamp','source_as_of','expires_at'):
        result[key] = instant(value[key]).isoformat()
    if instant(result['source_as_of']) > instant(result['signal_timestamp']):
        raise ValueError('source was not known at the declared signal timestamp')
    for key in ('target_notional_cny','limit_price','max_slippage_bps'):
        result[key] = str(amount(value[key], positive=key=='limit_price'))
    if value['exchange'] != ('SSE' if result['symbol'].endswith('.SH') else 'SZSE'):
        raise ValueError('target symbol and exchange mismatch')
    return result


def _base_intent(target):
    return {key:target[key] for key in ('client_intent_id','idempotency_key','strategy_id','strategy_version',
        'signal_timestamp','symbol','exchange','limit_price','max_slippage_bps','expires_at')} | {
            'schema_version':1,'order_type':'LIMIT','time_in_force':'DAY'}


def _affordable_lots(state, upper, lot, price, cash):
    low, high = 0, upper
    while low < high:
        middle = (low+high+1)//2
        notional = middle*lot*price
        if notional+commission(state,notional) <= cash:
            low = middle
        else:
            high = middle-1
    return low


@money_context
def compile_target_event(state, target, packet, now):
    policy, now = _check_context(state,packet,now)
    if policy['schema_version'] != 2:
        deny('target compilation requires explicit v2 drawdown policy')
    if target['policy_fingerprint'] != state['admission_policy_fingerprint']:
        deny('target policy fingerprint differs from frozen journal policy')
    base = _base_intent(target)
    _check_intent(state,{**base,'side':'BUY'},packet,policy,now)
    code = target['symbol']
    if target['price_basis_id'] != state['price_basis'].get(code,'initial_raw'):
        deny('target limit price uses a different corporate-action price basis')
    target_value = Decimal(target['target_notional_cny'])
    if target_value > Decimal(policy['max_position_cny']):
        deny('target notional exceeds the frozen single-position limit')
    active = [row for row in state['orders'].values() if row['status'] in ACTIVE]
    required = {key for key,qty in state['positions'].items() if qty} | {code} | {row['symbol'] for row in active}
    marks = _marks(policy,packet,now,required,state=state)
    metadata = state['risk_session']['instruments'][code]
    lot, tick = metadata['lot_size'], Decimal(metadata['price_tick'])
    held = state['positions'].get(code,0)
    side = 'BUY' if target_value >= held*marks[code] else 'SELL'
    own = [row for row in active if row['symbol']==code]
    if any(row['side'] != side for row in own):
        deny('resolve opposite pending orders before compiling a new target')
    pending = sum(row['quantity']-row['filled_quantity'] for row in own)
    rounding = ROUND_FLOOR if side=='BUY' else ROUND_CEILING
    price = (Decimal(target['limit_price'])/tick).to_integral_value(rounding=rounding)*tick
    if price <= 0:
        deny('target price ceiling is below one positive tick')
    snapshot = public_snapshot(state)
    cash = Decimal(snapshot['available_cash'])
    totals = portfolio_totals(state,marks)
    if side=='BUY':
        remaining = min(target_value-totals['exposure'].get(code,ZERO),
                        Decimal(policy['capital_limit_cny'])-totals['gross'])
        upper = max(0,int((remaining/max(price,marks[code])/lot).to_integral_value(rounding=ROUND_FLOOR)))
        quantity = _affordable_lots(state,upper,lot,price,cash)*lot
        if quantity == 0:
            deny('target already covered or remaining cash/notional cannot fund one whole lot with fees')
    else:
        required_sale = (Decimal(held)-target_value/marks[code])-pending
        wanted = max(0,int((required_sale/lot).to_integral_value(rounding=ROUND_CEILING))*lot)
        available = snapshot['available_positions'].get(code,0)
        quantity = min(wanted,available)
        if quantity % lot and not (quantity==available and metadata['odd_lot_sell_allowed']):
            quantity = quantity//lot*lot
        if quantity <= 0:
            deny('target already covered or no eligible unreserved sellable lot')
    compiled = normalize_intent({**base,'side':side,'quantity':quantity,'limit_price':str(price)})
    event = admission_event(state,compiled,packet,now)
    position_after = held+(pending+quantity)*(1 if side=='BUY' else -1)
    committed_position = totals['exposure'].get(code,ZERO)+(quantity*max(price,marks[code]) if side=='BUY' else ZERO)
    event['data']['admission']['target_compilation'] = {
        'compiler_version':1,'target':target,'target_fingerprint':fingerprint(target),
        'context_fingerprint':fingerprint(packet),'journal_sequence':state['sequence'],
        'journal_hash':state['journal_hash'],'decision_at':now.isoformat(),
        'quantity':quantity,'rounded_limit_price':str(price),'known_mark_price':str(marks[code]),
        'available_cash_before':str(cash),'held_quantity_before':held,
        'sellable_quantity_before':snapshot['available_positions'].get(code,0),'same_side_pending_quantity':pending,
        'position_quantity_if_all_same_side_orders_fill':position_after,
        'target_gap_at_known_mark_cny':str(target_value-position_after*marks[code]),
        'commission_bps':str(state['commission_bps']),'minimum_commission':str(state['minimum_commission']),
        'fee_at_full_limit_fill':str(commission(state,quantity*price)),
        'post_order_committed_position_cny':str(committed_position),
        'post_order_gross_committed_exposure_cny':event['data']['admission']['risk']['gross_committed_exposure'],
        'source_quality_verified':False,'research_admission_verified':False,'executable':False}
    return event
