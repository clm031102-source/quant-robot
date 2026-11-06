"""One frozen soybean-meal curve proxy, with no source or strategy qualification.

The contract inventory is a current vendor vintage. Last-trade dates select a
proxy pair, not an ETF's actual portfolio or realizable roll yield. Settlement
availability is a declared two-ETF-session execution lag, not a PIT certificate.
No parameter search, price acquisition or account execution occurs here.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
import re


MIN_DAYS_TO_LAST_TRADE = 60
EXECUTION_LAG_SESSIONS = 2


def _day(value, *, compact=False):
    if not isinstance(value, str):
        raise ValueError('Explicit contract or session date required')
    fmt = '%Y%m%d' if compact else '%Y-%m-%d'
    result = datetime.strptime(value, fmt).date()
    if result.strftime(fmt) != value:
        raise ValueError('Canonical contract or session date required')
    return result


def _sessions(sessions):
    if not isinstance(sessions, list) or not sessions or len(sessions) > 10000:
        raise ValueError('Bounded nonempty ETF calendar required')
    if sessions != sorted(set(sessions)):
        raise ValueError('Unique ordered ETF sessions required')
    return [_day(day) for day in sessions]


def _inventory(records):
    if not isinstance(records, list) or not 2 <= len(records) <= 1000:
        raise ValueError('Bounded contract lifecycle inventory required')
    contracts, identities, expiries = [], set(), set()
    for row in records:
        code = row['ts_code']
        if (not isinstance(code, str) or re.fullmatch(r'M\d{4}\.DCE', code) is None
                or code in identities or row['fut_code'] != 'M' or row['exchange'] != 'DCE'):
            raise ValueError('Unique DCE soybean-meal contracts required')
        listed, last_trade, delivery = (_day(row[key], compact=True)
                                       for key in ('list_date', 'delist_date', 'last_ddate'))
        if not listed < last_trade <= delivery:
            raise ValueError('Listed, last-trade and delivery chronology invalid')
        if (str(row['per_unit']) not in ('10', '10.0') or row['trade_unit'] != '吨'
                or row['quote_unit'] != '人民币元/吨'):
            raise ValueError('Frozen soybean-meal contract units changed')
        if last_trade in expiries:
            raise ValueError('Ambiguous contracts with identical last-trade date')
        contracts.append(dict(code=code, listed=listed, last_trade=last_trade))
        identities.add(code)
        expiries.add(last_trade)
    return sorted(contracts, key=lambda row: (row['last_trade'], row['code']))


def select_contract_pairs(lifecycle_records, etf_sessions):
    """Select only by already listed lifecycle, never volume, OI or price."""
    days, contracts = _sessions(etf_sessions), _inventory(lifecycle_records)
    pairs = []
    for label, day in zip(etf_sessions, days, strict=True):
        eligible = [row for row in contracts if row['listed'] <= day
                    and (row['last_trade'] - day).days >= MIN_DAYS_TO_LAST_TRADE]
        pair = dict(source_date=label, near_contract=None, far_contract=None,
                    near_last_trade=None, far_last_trade=None,
                    reason='fewer_than_two_lifecycle_eligible_contracts')
        if len(eligible) >= 2:
            near, far = eligible[:2]
            pair.update(near_contract=near['code'], far_contract=far['code'],
                near_last_trade=near['last_trade'].isoformat(),
                far_last_trade=far['last_trade'].isoformat(), reason=None)
        pairs.append(pair)
    return pairs


def _settlement(value):
    if type(value) not in (str, int, float, Decimal) or len(str(value)) > 80:
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    if (not number.is_finite() or number <= 0 or len(number.as_tuple().digits) > 40
            or abs(number.as_tuple().exponent) > 20):
        return None
    return number


def build_proxy_signals(lifecycle_records, settlement_rows, etf_sessions):
    """Settle(t) is usable only for execution at ETF session t+2.

    Missing/invalid chosen legs produce an explicit unknown/exit instruction;
    no substitute contract, forward fill or alternate price field is used.
    The consumer must honor executable exits and account risks separately.
    """
    pairs = select_contract_pairs(lifecycle_records, etf_sessions)
    registered = {row['ts_code'] for row in lifecycle_records}
    if not isinstance(settlement_rows, list) or len(settlement_rows) > 2_000_000:
        raise ValueError('Bounded settlement observations required')
    observed = {}
    for row in settlement_rows:
        day = _day(row['trade_date'], compact=True).isoformat()
        code = row['ts_code']
        if code not in registered or (code, day) in observed:
            raise ValueError('Unknown contract or duplicate daily settlement observation')
        observed[(code, day)] = _settlement(row.get('settle'))
    signals = []
    for index, execution_date in enumerate(etf_sessions):
        signal = dict(execution_date=execution_date, source_date=None,
            near_contract=None, far_contract=None, known=False, desired=False,
            annualized_log_curve=None, reason='insufficient_fixed_lag_history')
        if index >= EXECUTION_LAG_SESSIONS:
            pair = pairs[index - EXECUTION_LAG_SESSIONS]
            signal.update({key: pair[key] for key in ('source_date', 'near_contract', 'far_contract', 'reason')})
            if pair['reason'] is None:
                near = observed.get((pair['near_contract'], pair['source_date']))
                far = observed.get((pair['far_contract'], pair['source_date']))
                if near is None or far is None:
                    signal['reason'] = 'selected_settlement_missing_or_nonpositive'
                else:
                    distance = (_day(pair['far_last_trade']) - _day(pair['near_last_trade'])).days
                    with localcontext() as context:
                        context.prec = 34
                        curve = (near / far).ln() * Decimal(365) / Decimal(distance)
                    signal.update(known=True, desired=near > far,
                                  annualized_log_curve=str(curve), reason=None)
        signals.append(signal)
    return dict(artifact_type='soybean_meal_curve_proxy_v1', signals=signals,
        formula='log(settle_near/settle_far)*365/(last_trade_far-last_trade_near)',
        min_days_to_last_trade=MIN_DAYS_TO_LAST_TRADE,
        execution_lag_etf_sessions=EXECUTION_LAG_SESSIONS,
        input_vintage='current_provider_inventory_not_certified_historical_vintage',
        availability_basis='fixed_lag_model_assumption_not_observed_publication',
        interpretation='commodity_curve_predictor_not_ETF_holdings_or_actual_roll_yield',
        qualified=False, real_forward_days_added=0)
