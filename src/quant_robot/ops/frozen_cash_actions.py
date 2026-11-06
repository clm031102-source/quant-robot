"""Cumulative cash-action inputs for a causal journal; no source certification."""
from datetime import datetime
from decimal import Decimal, InvalidOperation


FIELDS = {'event_id', 'asset_id', 'kind', 'announced_date', 'record_date',
          'ex_date', 'pay_date', 'cash_per_unit', 'share_multiplier', 'cash_basis'}


def _date(value):
    if not isinstance(value, str):
        raise ValueError('Cash action date must be an ISO day')
    if datetime.strptime(value, '%Y-%m-%d').date().isoformat() != value:
        raise ValueError('Cash action date must be an ISO day')
    return value


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)) or len(str(value)) > 80:
        raise ValueError('Finite cash action numbers required')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Finite cash action numbers required') from exc
    if (not result.is_finite() or len(result.as_tuple().digits) > 40
            or abs(result.as_tuple().exponent) > 40):
        raise ValueError('Finite cash action numbers required')
    return result


def cash_action_snapshot(raw, *, asset, sessions, as_of_session, previous=(), warmup=False):
    """Validate a complete cumulative snapshot without rewriting prior events.

    New events must be received by their record-day observation. A later arrival
    requires a separate correction workflow; this adapter never backfills it.
    The caller must separately validate coverage and acquisition evidence.
    """
    if not isinstance(raw, list) or len(raw) > 1000:
        raise ValueError('Bounded complete cash action response required')
    dates, result, identities, economic = set(sessions), [], set(), set()
    prior = {item['event_id']: item for item in previous}
    for item in raw:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise ValueError('Complete explicit cash action response fields required')
        identity = item['event_id']
        if not isinstance(identity, str) or not identity or len(identity) > 200 or identity in identities:
            raise ValueError('Unique bounded cash action identity required')
        if (item['asset_id'] != asset or item['kind'] != 'cash_dividend'
                or item['cash_basis'] != 'net' or _decimal(item['share_multiplier']) != 1):
            raise ValueError('Only same-asset net cash distributions without share conversion supported')
        announced, record, ex, pay = [_date(item[key]) for key in
                                    ('announced_date', 'record_date', 'ex_date', 'pay_date')]
        if not announced <= record < ex <= pay or announced > as_of_session:
            raise ValueError('Cash action chronology or announcement availability invalid')
        if any(day not in dates for day in (record, ex, pay)):
            raise ValueError('Cash action dates require the frozen exchange calendar')
        cash = _decimal(item['cash_per_unit'])
        if cash <= 0:
            raise ValueError('Positive net cash distribution required')
        key = (record, ex, pay, cash)
        if key in economic:
            raise ValueError('Duplicate economic cash action under different identities')
        amount = format(cash, 'f')
        # Decimal string scale is economically irrelevant, but never round values.
        amount = amount.rstrip('0').rstrip('.') if '.' in amount else amount
        # The canonical event must remain valid when read again after restart.
        _decimal(amount)
        normalized = dict(item, cash_per_unit=amount, share_multiplier='1')
        if identity in prior:
            if normalized != prior[identity]:
                raise ValueError('Immutable cash action was amended; correction review required')
        elif not warmup and record < as_of_session:
            raise ValueError('Late cash action cannot rewrite historical entitlements')
        identities.add(identity)
        economic.add(key)
        result.append(normalized)
    if not set(prior) <= identities:
        raise ValueError('Previously received cash action omitted from complete snapshot')
    return sorted(result, key=lambda item: (item['record_date'], item['ex_date'], item['event_id']))
