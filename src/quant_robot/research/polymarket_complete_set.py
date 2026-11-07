"""Public-book complete-set cost screen. No wallets, trades, or fill simulation.

A quote surplus is NOT realized arbitrage: two books are not an atomic fill.
Fees are evaluated as cash charges and as shares withheld on buys; the more
expensive interpretation is retained until a settlement adapter is verified.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_CEILING
import json

D = Decimal
ZERO = D('0')
ONE = D('1')
FEE_UNIT = D('0.00001')


def number(value) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError('missing or boolean numeric value')
    try:
        result = D(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid numeric value') from exc
    if not result.is_finite():
        raise ValueError('nonfinite numeric value')
    return result


def _array(value) -> list:
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, list):
        raise ValueError('expected array')
    return result


def market_assets(market: dict) -> tuple[str, str]:
    if (market.get('active') is not True or market.get('closed') is not False
            or market.get('acceptingOrders') is not True
            or market.get('enableOrderBook') is not True
            or market.get('negRisk') is not False):
        raise ValueError('requires open ordinary binary market with order book')
    outcomes = _array(market.get('outcomes'))
    if len(outcomes) != 2 or {str(s).lower() for s in outcomes} != {'yes', 'no'}:
        raise ValueError('requires exactly Yes and No')
    version = market.get('version', 'v1')
    if version not in ('v1', 'v2'):
        raise ValueError('unsupported protocol version')
    assets = _array(market.get('positionIds' if version == 'v2' else 'clobTokenIds'))
    if (len(assets) != 2 or len(set(assets)) != 2
            or any(not isinstance(s, str) or not s.isdecimal() for s in assets)):
        raise ValueError('invalid or duplicated outcome identifiers')
    return tuple(assets)  # both outcomes, no semantic dependence on their order


def fee_rate(market: dict) -> Decimal:
    if market.get('feesEnabled') is False:
        return ZERO
    schedule = market.get('feeSchedule')
    if (market.get('feesEnabled') is not True or not isinstance(schedule, dict)
            or number(schedule.get('exponent')) != ONE
            or schedule.get('takerOnly') is not True):
        raise ValueError('fee schedule absent or unsupported')
    rate = number(schedule.get('rate'))
    if not ZERO <= rate < ONE:
        raise ValueError('invalid fee rate')
    return rate


def asks(book: dict) -> list[tuple[Decimal, Decimal]]:
    rows = book.get('asks')
    if not isinstance(rows, list) or not rows:
        raise ValueError('empty ask book')
    levels: dict[Decimal, Decimal] = {}
    for row in rows:
        price, size = number(row.get('price')), number(row.get('size'))
        if not ZERO < price < ONE or size <= ZERO:
            raise ValueError('invalid price or size')
        levels[price] = levels.get(price, ZERO) + size
    return sorted(levels.items())  # API returns descending asks; never trust order


def buy_cost(levels: list[tuple[Decimal, Decimal]], quantity: Decimal,
             rate: Decimal, *, fee_in_shares: bool = False) -> dict:
    """Buy equal NET shares, walking depth. Fee rounding is a model estimate.

The public L2 book does not expose individual maker-order fragmentation.
Rounding per price level cannot certify exact per-match charges.
"""
    remaining, notional, fees, gross_shares = quantity, ZERO, ZERO, ZERO
    used = []
    for price, available in levels:
        fee_per_share = rate * price * (ONE - price)
        keep = ONE - fee_per_share / price if fee_in_shares else ONE
        gross = min(available, remaining / keep)
        fee = (gross * fee_per_share).quantize(FEE_UNIT, rounding=ROUND_CEILING)
        net = gross - fee / price if fee_in_shares else gross
        # Round-up fees can cost a fraction of a share more than the algebraic
        # estimate; use the same price level's remaining depth to cover it.
        if fee_in_shares and net < remaining and gross < available:
            gross = min(available, (remaining + fee / price).quantize(
                D('0.00000001'), rounding=ROUND_CEILING))
            fee = (gross * fee_per_share).quantize(FEE_UNIT, rounding=ROUND_CEILING)
            net = gross - fee / price
        taken = min(remaining, net)
        remaining -= taken
        notional += gross * price
        gross_shares += gross
        fees += fee
        used.append(dict(price=str(price), gross_shares=str(gross), net_shares=str(net)))
        if remaining <= D('0.000000001'):
            remaining = ZERO
            break
    return dict(complete=remaining == ZERO, net_shares=str(quantity - remaining),
                gross_shares=str(gross_shares), notional=str(notional),
                estimated_fee=str(fees),
                cash_cost=str(notional if fee_in_shares else notional + fees), levels=used)


def screen(market: dict, books: dict[str, dict], *, observed_ms: int,
           quantities=('5', '25', '100'), max_age_ms=10000, max_skew_ms=2000,
           reserve_bps='20', fixed_reserve='1') -> dict:
    result = dict(market_id=str(market.get('id', '')), question=market.get('question', ''),
                  slug=market.get('slug', ''), observations=[], status='not_evaluated',
                  realized_profit=None, fills=0)
    try:
        ids = market_assets(market)
        rate = fee_rate(market)
        selected = [books[key] for key in ids]
        if any(b.get('asset_id') != key or b.get('market') != market.get('conditionId')
               or b.get('neg_risk') is not False for key, b in zip(ids, selected)):
            raise ValueError('book asset, condition, or risk mismatch')
        timestamps = [int(number(b.get('timestamp'))) for b in selected]
        ages = [observed_ms - stamp for stamp in timestamps]
        fresh = all(0 <= age <= max_age_ms for age in ages)
        synchronous = max(timestamps) - min(timestamps) <= max_skew_ms
        levels = [asks(b) for b in selected]
        minimums = [number(b.get('min_order_size')) for b in selected]
        if any(m <= ZERO for m in minimums):
            raise ValueError('invalid minimum order size')
        reserve, fixed = number(reserve_bps) / D('10000'), number(fixed_reserve)
        if reserve < ZERO or fixed < ZERO:
            raise ValueError('negative reserve')
        result.update(fee_rate=str(rate), book_age_ms=ages,
                      timestamp_skew_ms=max(timestamps) - min(timestamps),
                      fresh=fresh, synchronous=synchronous,
                      best_ask_sum=str(sum(row[0][0] for row in levels)))
        for requested in quantities:
            q = number(requested)
            if q <= ZERO:
                raise ValueError('nonpositive requested quantity')
            cash_mode = [buy_cost(row, q, rate) for row in levels]
            shares_mode = [buy_cost(row, q, rate, fee_in_shares=True) for row in levels]
            all_costs = cash_mode + shares_mode
            complete = all(row['complete'] for row in all_costs)
            # Current docs describe USDC minimums; also require the share
            # threshold to avoid ambiguity with older CTF API semantics.
            minimum_met = all(number(c['notional']) >= m and q >= m
                              for costs in (cash_mode, shares_mode)
                              for c, m in zip(costs, minimums))
            cash_total = sum(number(c['cash_cost']) for c in cash_mode)
            share_total = sum(number(c['cash_cost']) for c in shares_mode)
            cost = max(cash_total, share_total)
            allowance = cost * reserve + fixed
            surplus = q - cost - allowance if complete else None
            result['observations'].append(dict(net_pairs=str(q), depth_complete=complete,
                minimum_met=minimum_met, cash_fee_cost=str(cash_total),
                withheld_share_fee_cost=str(share_total), conservative_cost=str(cost),
                additional_cost_reserve=str(allowance),
                quote_surplus=str(surplus) if surplus is not None else None,
                positive_quote_candidate=bool(complete and minimum_met and fresh
                                             and synchronous and surplus > ZERO),
                cash_fee_legs=cash_mode, withheld_fee_legs=shares_mode))
        result['status'] = 'quoted'
    except (ValueError, TypeError, KeyError, InvalidOperation, json.JSONDecodeError) as exc:
        result.update(status='unavailable', reason=str(exc))
    return result
