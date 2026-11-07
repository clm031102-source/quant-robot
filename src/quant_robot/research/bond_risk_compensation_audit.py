"""Independent arithmetic verification of completed bond ledgers.

Accepts already-authorized data in memory, performs no strategy decisions or
I/O, and imports no model helpers. This verifies accounting, not historical
availability, actual execution, optimal decisions, or qualification.
"""
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, localcontext

_CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999,
                   capitals=1, clamp=0, traps=[DivisionByZero, InvalidOperation, Overflow])
_ZERO = Decimal(0)
_INITIAL = Decimal(10000)


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _decimal(value):
    _require(type(value) in (str, int, Decimal), 'Exact decimal string/integer required')
    number = Decimal(value)
    _require(number.is_finite(), 'Nonfinite accounting value')
    return number


def _same(actual, expected, field):
    _require(_decimal(actual) == expected, 'Accounting mismatch: ' + field)


def _source(fixture):
    days = fixture['sessions']
    _require(len(days) > 20 and days == sorted(set(days)), 'Distinct ordered sessions required')
    bars = {r['date']: r for r in fixture['bars']}
    _require(len(bars) == len(fixture['bars']) == len(days) and set(bars) == set(days),
             'Exact source session coverage required')
    for bar in bars.values():
        op, hi, lo, close = (_decimal(bar[k]) for k in ('open', 'high', 'low', 'close'))
        _require(0 < lo <= min(op, close) <= max(op, close) <= hi
                 and _decimal(bar['volume']) >= 0, 'Invalid source OHLC/volume')
    splits = fixture.get('split_events', [])
    _require(len(splits) <= 1, 'At most one exact split10 supported')
    split = splits[0] if splits else None
    if split:
        _require(_decimal(split['share_multiplier']) == 10
                 and split['record_date'] in days
                 and (split['ex_date'] in days or split['record_date'] == days[-1] < split['ex_date'])
                 and split['known_date'] <= split['record_date'] < split['ex_date'],
                 'Invalid fixed split10 mapping')
    actions = fixture.get('actions', [])
    _require(len({a['event_id'] for a in actions}) == len(actions), 'Duplicate cash action')
    normalized = []
    for action in actions:
        _require(action['record_date'] < action['ex_date'] <= action['pay_date']
                 and _decimal(action['share_multiplier']) == 1, 'Invalid cash action ordering')
        amount = _decimal(action['cash_per_unit'])
        _require(amount >= 0, 'Negative cash action')
        if split:
            unit = 'pre_split' if action['record_date'] < split['ex_date'] else 'post_split'
            _require(action['record_quantity_unit'] == unit, 'Cash record unit mismatch')
            basis = action['cash_per_unit_basis']
            _require(basis in ('pre_split', 'post_split'), 'Unknown cash amount unit')
            if basis != unit:
                _require(action.get('cash_basis_mapping') == 'explicit_split10_conversion',
                         'Explicit cash basis conversion required')
                amount = amount * 10 if unit == 'pre_split' else amount / 10
        normalized.append((action, amount))
    return days, bars, split, normalized


def _factor(source_day, target_day, split):
    return 10 if split and source_day < split['ex_date'] <= target_day else 1


def _valuation(day, close, split):
    divisor = 10 if split and split['record_date'] <= day < split['ex_date'] else 1
    return close / divisor, divisor


def _pending(actions, rights, terminal):
    return {a['event_id']: (rights[a['event_id']], amount)
            for a, amount in actions if a['ex_date'] > terminal and rights.get(a['event_id'], 0) > 0}


def _check_pending(rows, pending):
    _require(len(rows) == len(pending) and {r['event_id'] for r in rows} == set(pending),
             'Pending record rights missing/duplicated')
    for row in rows:
        quantity, amount = pending[row['event_id']]
        _same(row['record_quantity'], quantity, 'pending record quantity')
        _same(row['declared_cash_per_unit'], amount, 'pending cash per unit')
        _require(row['included_in_NAV'] is False and row['spendable_cash'] is False,
                 'Unexercised rights cannot become cash/NAV')


def audit_account(fixture, account):
    """Rebuild cash/positions from fills, not from strategy decisions."""
    with localcontext(_CONTEXT):
        return _audit_account(fixture, account)


def _audit_account(fixture, account):
    days, bars, split, actions = _source(fixture)
    cost = account['cost_case']
    minimum, slip = cost['minimum_commission_CNY'], cost['slippage_bps_each']
    _require(type(minimum) is int and type(slip) is int and minimum in (0, 5, 10)
             and slip in (0, 10, 30) and cost['commission_bps_each'] == 5,
             'One of nine frozen cost cases required')
    _same(account['initial_cash_CNY'], _INITIAL, 'initial capital')
    rows = account['rows']
    _require([r['date'] for r in rows] == days, 'Missing/duplicate/account dates')
    fills = {f['date']: f for f in account['fills']}
    _require(len(fills) == len(account['fills']) and set(fills).issubset(days),
             'Duplicate or out-of-window fill')
    cash = previous = peak = _INITIAL
    quantity = conversion = episodes = roundtrips = max_holding = 0
    entry_index = None
    fees = paid = impact_sum = max_dd = _ZERO
    rights, due, expected_actions = {}, {}, []
    for index, day in enumerate(days):
        bar = bars[day]
        for action, amount in actions:
            key = action['event_id']
            if action['ex_date'] == day:
                due[key] = (rights.get(key, 0) * amount).quantize(Decimal('.01'))
                expected_actions.append((day, key, 'receivable_created', due[key]))
        if day in fills:
            fill = fills[day]
            qty = fill['quantity']
            side = fill['side']
            _require(index >= 20 and type(qty) is int and qty > 0 and qty % 100 == 0
                     and side in ('buy', 'sell'), 'Invalid fill quantity/day/side')
            _require(fill.get('rejected') is None, 'Rejected order cannot be a fill')
            _require(bar.get('suspended') is not True
                     and bar.get('limit_up' if side == 'buy' else 'limit_down') is not True,
                     'Known execution constraint ignored')
            sign = 1 if side == 'buy' else -1
            raw_open = _decimal(bar['open'])
            price = (raw_open * (1 + Decimal(slip) * sign / 10000)).quantize(
                Decimal('.001'), rounding=ROUND_CEILING if side == 'buy' else ROUND_FLOOR)
            notional = qty * price
            fee = max(notional * Decimal('0.0005'), Decimal(minimum)).quantize(Decimal('.01'))
            cap = int(sum((_decimal(bars[d]['volume']) * _factor(d, day, split)
                           for d in days[index-20:index]), _ZERO) / 20 * Decimal('.01'))
            _require(qty <= cap // 100 * 100, 'Fill exceeds prior-only capacity')
            for field, expected in (('quantity', qty), ('requested_quantity', qty),
                    ('raw_open_price', raw_open), ('execution_price', price),
                    ('notional', notional), ('fee', fee), ('cash_before', cash)):
                _same(fill[field], expected, 'fill ' + field)
            if side == 'buy':
                _require(not quantity and index != len(days)-1 and notional+fee <= min(cash, previous),
                         'Buy violates flat/terminal/no-borrowing budget')
                _same(fill['plan']['budget'], min(cash, previous), 'prior budget')
                cash -= notional + fee
                quantity += qty
                episodes += 1
                entry_index = index
            else:
                _require(qty <= quantity and cash+notional >= fee, 'Invalid sale inventory/cash')
                cash += notional - fee
                quantity -= qty
                if not quantity:
                    roundtrips += 1
                    entry_index = None
            impact = qty * (price - raw_open) * sign
            fees += fee
            impact_sum += impact
            _same(fill['slippage_and_tick_cost_CNY'], impact, 'fill price impact')
            _same(fill['cash_after'], cash, 'fill cash after')
            _same(fill['position_after'], quantity, 'fill position after')
        before_payment = cash
        for action, amount in actions:
            key = action['event_id']
            if action['record_date'] == day:
                rights[key] = quantity
                expected_actions.append((day, key, 'record_entitlement', Decimal(quantity)))
            if action['pay_date'] == day:
                payment = due.pop(key, _ZERO)
                cash += payment
                paid += payment
                expected_actions.append((day, key, 'paid_after_fills', payment))
        if split and day == split['record_date']:
            prior_quantity = quantity
            quantity *= 10
            conversion += quantity - prior_quantity
            expected_actions.append((day, split['event_id'], 'split_registration', Decimal(quantity)))
        valuation, divisor = _valuation(day, _decimal(bar['close']), split)
        receivable = sum(due.values(), _ZERO)
        value = quantity * valuation
        nav = cash + receivable + value
        _require(cash >= 0 and quantity >= 0 and nav > 0, 'Impossible cash/position/NAV')
        peak = max(peak, nav)
        dd = 1 - nav / peak
        max_dd = max(max_dd, dd)
        holding = index-entry_index+1 if entry_index is not None else 0
        max_holding = max(max_holding, holding)
        expected = dict(index=index, cash=cash, cash_before_distribution_payment=before_payment,
            quantity=quantity, market_value=value, dividend_receivable=receivable, equity=nav,
            previous_close_NAV=previous, global_peak=peak, daily_loss_CNY=max(previous-nav, _ZERO),
            sampled_close_drawdown=dd, holding_sessions=holding)
        if split:
            expected.update(raw_close=_decimal(bar['close']), valuation_price=valuation,
                post_registration_quote_unit_factor=divisor, cumulative_conversion_delta=conversion)
            _require(rows[index]['split_event_applied'] is (day >= split['record_date']),
                     'Split applied flag mismatch')
        for key, value in expected.items():
            _same(rows[index][key], value, day + ' ' + key)
        _require(rows[index]['terminal_session'] is (index == len(days)-1), 'Terminal flag mismatch')
        previous = nav
    journal = account['actions']
    _require(len(journal) == len(expected_actions), 'Missing/duplicate corporate action journal')
    for actual, (day, key, kind, value) in zip(journal, expected_actions):
        _require((actual['date'], actual['event_id'], actual['kind']) == (day, key, kind),
                 'Corporate action identity/order mismatch')
        field = 'quantity_after' if kind == 'split_registration' else 'quantity' if kind == 'record_entitlement' else 'amount'
        _same(actual[field], value, 'corporate action ' + field)
        if kind == 'split_registration':
            _same(actual['quantity_before'], value/10, 'split before')
            _same(actual['conversion_delta'], value-value/10, 'split delta')
    summary = account['summary']
    totals = dict(cash=cash, remaining_quantity=quantity, dividend_receivable=sum(due.values(), _ZERO),
        terminal_book_NAV=previous, net_book_PnL=previous-_INITIAL, cash_PnL=cash-_INITIAL,
        total_commission_CNY=fees, dividend_cash_received=paid,
        total_slippage_and_tick_cost_CNY=impact_sum, daily_close_model_max_drawdown=max_dd,
        episodes_started=episodes, completed_roundtrips=roundtrips, maximum_holding_sessions=max_holding)
    if split:
        totals['nontrade_conversion_delta'] = conversion
    for key, value in totals.items():
        _same(summary[key], value, 'summary ' + key)
    pending = _pending(actions, rights, days[-1])
    _check_pending(summary['pending_record_entitlements'], pending)
    _require(summary['terminal_unsettled'] is bool(quantity or any(due.values()) or pending),
             'Terminal unsettled mismatch')
    _require(summary['observed_drawdown_over_40pct'] is (max_dd > Decimal('.40')),
             'Drawdown exceedance mismatch')
    return dict(status='accounting_consistent', rows=len(rows), fills=len(fills),
                terminal_NAV=str(previous), decisions_independently_validated=False,
                execution_certified=False, qualified=False, real_forward_added=0)


def audit_reference(fixture, reference):
    """Check the declared ideal fractional reference, never an executable account."""
    with localcontext(_CONTEXT):
        days, bars, split, actions = _source(fixture)
        rows = reference['rows']
        _require([r['date'] for r in rows] == days, 'Reference session mismatch')
        initial_quantity = _INITIAL / _decimal(bars[days[20]]['open'])
        _same(reference['fixed_theoretical_quantity'], initial_quantity, 'reference initial quantity')
        quantity, cash = _ZERO, _INITIAL
        rights, due, payments = {}, {}, []
        for index, day in enumerate(days):
            for action, amount in actions:
                key = action['event_id']
                if action['ex_date'] == day:
                    due[key] = rights.get(key, _ZERO) * amount
            if index == 20:
                quantity, cash = initial_quantity, _ZERO
            if index == len(days)-1:
                cash += quantity * _decimal(bars[day]['open'])
                quantity = _ZERO
            for action, amount in actions:
                key = action['event_id']
                if action['record_date'] == day:
                    rights[key] = quantity
                if action['pay_date'] == day:
                    payment = due.pop(key, _ZERO)
                    cash += payment
                    payments.append((day, key, payment))
            if split and day == split['record_date']:
                quantity *= 10
            valuation, _ = _valuation(day, _decimal(bars[day]['close']), split)
            receivable = sum(due.values(), _ZERO)
            nav = cash + receivable + quantity * valuation
            for key, value in dict(quantity=quantity, cash=cash, dividend_receivable=receivable,
                                   economic_value=nav).items():
                _same(rows[index][key], value, 'reference ' + day + ' ' + key)
        _require(len(reference['payments']) == len(payments), 'Reference payment count mismatch')
        for actual, (day, key, value) in zip(reference['payments'], payments):
            _require((actual['date'], actual['event_id']) == (day, key), 'Reference payment identity mismatch')
            _same(actual['cash_distribution'], value, 'reference cash distribution')
        summary = reference['summary']
        for key, value in dict(terminal_economic_value=nav, terminal_cash=cash,
                               terminal_unpaid_receivable=sum(due.values(), _ZERO)).items():
            _same(summary[key], value, 'reference summary ' + key)
        pending = _pending(actions, rights, days[-1])
        _check_pending(summary['pending_record_entitlements'], pending)
        _require(summary['terminal_unsettled'] is bool(quantity or any(due.values()) or pending),
                 'Reference terminal status mismatch')
        _require(reference['not_an_executable_account'] is True and reference['qualified'] is False,
                 'Reference cannot be executable/qualified')
        return dict(status='reference_accounting_consistent', rows=len(rows), qualified=False)


def audit_bundle(fixture, bundle):
    """Nine distinct fee accounts, zero-interest cash and one ideal reference."""
    accounts = bundle['fee_accounts']
    cases = [(a['cost_case']['minimum_commission_CNY'], a['cost_case']['slippage_bps_each']) for a in accounts]
    _require(len(cases) == 9 and set(cases) == {(m,s) for m in (0,5,10) for s in (0,10,30)},
             'Exact nine distinct cost accounts required')
    results = [audit_account(fixture, account) for account in accounts]
    cash = bundle['cash_control']
    _require([r['date'] for r in cash['rows']] == fixture['sessions'], 'Cash coverage mismatch')
    _same(cash['initial_cash_CNY'], _INITIAL, 'cash initial')
    for row in cash['rows']:
        _same(row['cash'], _INITIAL, 'cash control cash')
        _same(row['equity'], _INITIAL, 'cash control NAV')
    reference = audit_reference(fixture, bundle['reference'])
    return dict(status='accounting_consistent', accounts=results, cash_rows=len(cash['rows']),
                reference=reference, strategy_reexecuted=False, financial_admission_created=False,
                qualified=False, real_forward_added=0)
