"""Causal multi-asset annual allocation in a conditional, continuous cash account.

This numerical engine grants no data admission, actual fill certification or
permission to run an economic study. Callers must bind their own exact inputs.
"""
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


@dataclass(frozen=True)
class AllocationConfig:
    initial_cash: float = 10000
    max_position_cny: float = 1000
    max_daily_loss_cny: float = 60
    max_drawdown: float = .08
    max_holding_sessions: int = 252
    commission_bps: float = 5
    minimum_commission: float = 5
    slippage_bps: float = 10
    participation: float = .01


def _decimal(value):
    if isinstance(value, bool):
        raise ValueError('Boolean monetary or volume value')
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError('Invalid decimal value') from exc
    if not result.is_finite():
        raise ValueError('Finite decimal required')
    return result


def _day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError('Canonical ISO date required')
    return value


def _price(raw, side, settings):
    value = raw * (1 + settings['slippage_bps'] / 10000 * side)
    rounding = ROUND_CEILING if side > 0 else ROUND_FLOOR
    value = value.quantize(Decimal('.001'), rounding=rounding)
    if value <= 0:
        raise ValueError('Modeled tick price must be positive')
    return value


def _fee(notional, settings):
    return max(notional * settings['commission_bps'] / 10000,
               settings['minimum_commission']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def _capacity(volumes, settings):
    return int((sum(volumes, Decimal(0)) / len(volumes) * settings['participation']).to_integral_value(rounding=ROUND_FLOOR))


def _blocked(row, side):
    return row.get('suspended') is True or row.get('limit_up' if side == 'buy' else 'limit_down') is True


def _json(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    return value


def _inputs(bars, sessions, assets, cycles, actions, config):
    if not isinstance(config, AllocationConfig):
        raise ValueError('Explicit allocation config required')
    settings = {k: _decimal(v) for k, v in asdict(config).items() if k != 'max_holding_sessions'}
    if any(v < 0 for v in settings.values()):
        raise ValueError('Nonnegative settings required')
    if any(settings[k] <= 0 for k in ('initial_cash', 'max_position_cny', 'max_daily_loss_cny', 'max_drawdown', 'participation')):
        raise ValueError('Positive capital and risk limits required')
    if not 0 < settings['max_drawdown'] < 1 or not 0 < settings['participation'] <= 1 or settings['slippage_bps'] >= 10000:
        raise ValueError('Invalid fractional limit')
    if settings['max_position_cny'] > settings['initial_cash']:
        raise ValueError('Position cap exceeds capital')
    if type(config.max_holding_sessions) is not int or config.max_holding_sessions < 1:
        raise ValueError('Positive integer holding limit required')
    calendar = [_day(d) for d in sessions]
    if len(calendar) < 21 or calendar != sorted(set(calendar)):
        raise ValueError('Dense ordered explicit calendar with20warmup sessions required')
    selected = tuple(sorted(assets))
    if not selected or len(selected) != len(set(selected)) or any(not isinstance(a, str) or not a for a in selected):
        raise ValueError('Unique named assets required')
    prices = {}
    for raw in bars:
        asset, day = raw['asset_id'], _day(raw['date'])
        if asset not in selected:
            continue
        key = (day, asset)
        if day not in calendar or key in prices:
            raise ValueError('Unexpected or duplicate bar')
        row = {**raw, **{k: _decimal(raw[k]) for k in ('open', 'high', 'low', 'close', 'volume')}}
        if any(row[k] <= 0 for k in ('open', 'high', 'low', 'close')) or row['volume'] < 0:
            raise ValueError('Invalid price or volume')
        if not row['low'] <= min(row['open'], row['close']) <= max(row['open'], row['close']) <= row['high']:
            raise ValueError('Invalid OHLC ordering')
        for flag in ('suspended', 'limit_up', 'limit_down'):
            if flag in row and row[flag] is not None and type(row[flag]) is not bool:
                raise ValueError('Execution flags must be explicit booleans or unknown')
        prices[key] = row
    if len(prices) != len(calendar) * len(selected):
        raise ValueError('Every asset requires every explicit calendar mark')
    plan, ids, previous_exit = {}, set(), -1
    for cycle in cycles:
        identity = cycle['cycle_id']
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError('Unique cycle identity required')
        entry, exit_day = _day(cycle['entry_date']), _day(cycle['exit_date'])
        if entry not in calendar or exit_day not in calendar:
            raise ValueError('Cycle date outside calendar')
        start, end = calendar.index(entry), calendar.index(exit_day)
        if start < 20 or end <= start or start <= previous_exit:
            raise ValueError('Ordered nonoverlapping cycles after complete warmup required')
        ids.add(identity); previous_exit = end
        plan[start] = {**cycle, 'entry_index': start, 'exit_index': end}
    events, seen = [], set()
    for raw in actions:
        if raw['asset_id'] not in selected:
            continue
        event = {**raw, 'cash_per_unit': _decimal(raw['cash_per_unit'])}
        if not isinstance(event.get('event_id'), str) or not event['event_id'] or event['event_id'] in seen:
            raise ValueError('Unique corporate action identity required')
        if _decimal(event.get('share_multiplier', '1')) != 1 or event['cash_per_unit'] < 0:
            raise ValueError('Only reviewed cash distributions with no conversion supported')
        record, ex, pay = [_day(event[k]) for k in ('record_date', 'ex_date', 'pay_date')]
        if not record < ex <= pay:
            raise ValueError('Invalid corporate-action date order')
        if any(calendar[0] <= d <= calendar[-1] and d not in calendar for d in (record, ex, pay)):
            raise ValueError('Corporate-action date is not a calendar session')
        seen.add(event['event_id']); events.append(event)
    return settings, calendar, selected, prices, plan, events


def run_allocation_account(bars, *, sessions, assets, cycles, actions, config=AllocationConfig()):
    settings, calendar, selected, prices, plan, actions = _inputs(bars, sessions, assets, cycles, actions, config)
    cash = settings['initial_cash']
    positions, active, mandatory, trims, entitlements, receivables = {}, {}, {}, {}, {}, {}
    rows, fills, events, action_journal, breaches = [], [], [], [], []
    peak = previous = cash
    halted = False
    received = Decimal(0)
    filled_cycles = {cycle['cycle_id']: set() for cycle in plan.values()}

    def capacity(index, asset):
        return _capacity([prices[calendar[j], asset]['volume'] for j in range(index-20, index)], settings)

    def fill(day, asset, quantity, side, reason, cycle_id, requested, prior_capacity, current_capacity):
        nonlocal cash
        price = _price(prices[day, asset]['close'], 1 if side == 'buy' else -1, settings)
        notional = quantity * price
        fee = _fee(notional, settings)
        cash += -notional-fee if side == 'buy' else notional-fee
        positions[asset] = positions.get(asset, 0) + (quantity if side == 'buy' else -quantity)
        if positions[asset] == 0:
            del positions[asset]
        if cash < 0 or any(q <= 0 for q in positions.values()):
            raise ValueError('No borrowing or negative positions permitted')
        fills.append(dict(date=day, asset_id=asset, side=side, quantity=quantity, price=price,
                          notional=notional, fee=fee, reason=reason, cycle_id=cycle_id,
                          requested_quantity=requested, prior_capacity=prior_capacity, current_capacity=current_capacity))

    for index, day in enumerate(calendar):
        occupied = set(positions)
        prior_cash = cash
        entry_plans = {}
        # All entry sizes are fixed from information available before this session.
        if index in plan:
            reserve = prior_cash
            for asset in selected:
                prior_price = _price(prices[calendar[index-1], asset]['close'], 1, settings)
                limit = min(settings['max_position_cny'], reserve)
                quantity = min(int(limit / prior_price / 100)*100, capacity(index, asset)//100*100)
                while quantity > 0 and quantity*prior_price+_fee(quantity*prior_price, settings) > limit:
                    quantity -= 100
                entry_plans[asset] = quantity
                if quantity:
                    reserve -= quantity*prior_price+_fee(quantity*prior_price, settings)

        for action in actions:
            identity = action['event_id']
            if action['ex_date'] == day:
                credit = (entitlements.get(identity, 0)*action['cash_per_unit']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                receivables[identity] = credit
                action_journal.append(dict(date=day, kind='receivable_created', event_id=identity, amount=credit))

        for asset in selected:
            if asset not in positions:
                continue
            cycle = active[asset]
            if halted:
                mandatory[asset] = 'account_risk_exit'
            elif index >= cycle['exit_index']:
                mandatory.setdefault(asset, 'scheduled_exit')
            elif index >= cycle['entry_index']+config.max_holding_sessions:
                mandatory.setdefault(asset, 'max_holding_exit')
            reason = mandatory.get(asset, 'position_trim' if trims.get(asset, 0) else None)
            if reason is None:
                continue
            target = positions[asset] if asset in mandatory else min(positions[asset], trims[asset])
            prior_cap = capacity(index, asset)
            requested = min(target, prior_cap)//100*100
            if asset in mandatory and positions[asset] <= min(target, prior_cap):
                requested = positions[asset]
            current_cap = _capacity([prices[day, asset]['volume']], settings)
            quantity = min(requested, current_cap)//100*100
            if asset in mandatory and positions[asset] <= min(target, prior_cap, current_cap):
                quantity = positions[asset]
            price = _price(prices[day, asset]['close'], -1, settings)
            rejected = ('known_execution_constraint' if _blocked(prices[day, asset], 'sell') else
                        'exit_capacity' if quantity <= 0 else
                        'exit_fee_exceeds_available_cash' if cash+quantity*price < _fee(quantity*price, settings) else None)
            if rejected:
                events.append(dict(date=day, asset_id=asset, reason=rejected, order_reason=reason,
                                   requested_quantity=requested, prior_capacity=prior_cap, current_capacity=current_cap))
            else:
                fill(day, asset, quantity, 'sell', reason, cycle['cycle_id'], requested, prior_cap, current_cap)
                if asset not in positions:
                    active.pop(asset); mandatory.pop(asset, None)

        if index in plan:
            cycle = plan[index]
            for asset in selected:
                quantity = entry_plans[asset]
                price = _price(prices[day, asset]['close'], 1, settings)
                current_cap = _capacity([prices[day, asset]['volume']], settings)
                cost = quantity*price+_fee(quantity*price, settings) if quantity else Decimal(0)
                rejected = ('risk_halted' if halted else 'occupied_at_session_start' if asset in occupied else
                            'entry_below_one_lot' if not quantity else
                            'known_execution_constraint' if _blocked(prices[day, asset], 'buy') else
                            'entry_current_capacity' if quantity > current_cap else
                            'entry_budget_or_cash' if cost > min(settings['max_position_cny'], cash) else None)
                if rejected:
                    events.append(dict(date=day, asset_id=asset, reason=rejected, requested_quantity=quantity,
                                       cycle_id=cycle['cycle_id'], prior_capacity=capacity(index, asset), current_capacity=current_cap))
                else:
                    fill(day, asset, quantity, 'buy', 'annual_entry', cycle['cycle_id'], quantity, capacity(index, asset), current_cap)
                    active[asset] = cycle
                    filled_cycles[cycle['cycle_id']].add(asset)

        before_payment = cash
        for action in actions:
            identity = action['event_id']
            if action['record_date'] == day:
                entitlements[identity] = positions.get(action['asset_id'], 0)
                action_journal.append(dict(date=day, kind='record_entitlement', event_id=identity, quantity=entitlements[identity]))
            if action['pay_date'] == day:
                amount = receivables.pop(identity, Decimal(0))
                cash += amount; received += amount
                action_journal.append(dict(date=day, kind='cash_paid_after_fills', event_id=identity, amount=amount))

        marked = {a: {'quantity': q, 'price': prices[day,a]['close'], 'price_date': day,
                      'market_value': q*prices[day,a]['close']} for a,q in positions.items()}
        pending_cash = sum(receivables.values(), Decimal(0))
        equity = cash+pending_cash+sum((p['market_value'] for p in marked.values()), Decimal(0))
        if equity <= 0:
            raise ValueError('Nonpositive account equity')
        peak = max(peak, equity)
        reasons = []
        if previous-equity >= settings['max_daily_loss_cny']:
            reasons.append('daily_loss_limit')
        if 1-equity/peak >= settings['max_drawdown']:
            reasons.append('drawdown_limit')
        if reasons:
            halted = True
        breaches.extend(dict(date=day, reason=reason, equity=equity) for reason in reasons)
        trims = {}  # Expired unfilled trims are replaced from the current mark.
        for asset, position in marked.items():
            if position['market_value'] > settings['max_position_cny']:
                breaches.append(dict(date=day, asset_id=asset, reason='position_limit', market_value=position['market_value']))
                excess = position['market_value']-settings['max_position_cny']
                trims[asset] = min(position['quantity'], 100*int((excess/(100*position['price'])).to_integral_value(rounding=ROUND_CEILING)))
            if index-active[asset]['entry_index'] >= config.max_holding_sessions:
                breaches.append(dict(date=day, asset_id=asset, reason='holding_limit'))
        rows.append(dict(date=day, cash=cash, cash_before_distribution_payment=before_payment,
                         dividend_receivable=pending_cash, position_values=marked, equity=equity,
                         drawdown=1-equity/peak, daily_loss=max(previous-equity, Decimal(0))))
        previous = equity

    return _json(dict(artifact_type='annual_allocation_conditional_continuous_account_v1',
        executable=False, source_quality_verified=False, net_positive_EV_verified=False,
        unknown_execution_flag_rows=sum(any(row.get(k) is None for k in ('suspended','limit_up','limit_down')) for row in prices.values()),
        config=asdict(config), assets=selected, cycles=list(plan.values()),
        metrics=dict(initial_cash=settings['initial_cash'], ending_cash=cash, ending_equity=rows[-1]['equity'],
            pnl_cny=rows[-1]['equity']-settings['initial_cash'], fees_paid=sum((f['fee'] for f in fills), Decimal(0)),
            dividend_cash_received=received, maximum_drawdown=max(row['drawdown'] for row in rows),
            maximum_daily_loss_cny=max(row['daily_loss'] for row in rows),
            paired_entry_cycles=[k for k,v in filled_cycles.items() if v == set(selected)],
            entries_by_cycle={k:sorted(v) for k,v in filled_cycles.items()}),
        risk=dict(terminal_settled=not positions and not any(receivables.values()), new_entries_halted=halted,
                  within_all_observed_limits=not breaches, breaches=breaches, triggers_are_not_guaranteed_caps=True),
        positions=positions, receivables=receivables, equity_curve=rows, fills=fills, events=events,
        corporate_action_journal=action_journal))
