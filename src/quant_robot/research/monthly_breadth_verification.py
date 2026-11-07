"""Independent accounting of recorded orders; never imports the strategy engine.

Inputs are the already-decoded immutable snapshot and completed ledgers. This
does not reconstruct strategy intent, certify source timing, or issue eligibility.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
                     ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, localcontext)
from pathlib import Path

METHOD = "f3d77564288628ebd67e37bd36735197d7f49f9fab63d65398ee28a1a9d16a89"
CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999,
                  capitals=1, clamp=0)
for _signal in CONTEXT.traps:
    CONTEXT.traps[_signal] = _signal in (InvalidOperation, DivisionByZero, Overflow)
CONTEXT.clear_flags()
ZERO, CENT, TICK = Decimal(0), Decimal('.01'), Decimal('.001')
COSTS = [(m, s) for m in (0, 5, 10) for s in (0, 10, 30)]
POLICIES = ('breadth', 'monthly_50_50', 'own_trend')
COMPONENTS = ('carried_exposure', 'trade_timing', 'dividend_entitlement', 'commission', 'slippage')


def _require(condition, label):
    if not condition:
        raise ValueError(label)


def _d(value):
    _require(type(value) in (str, int, Decimal), 'decimal_type')
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('decimal_syntax') from exc
    _require(result.is_finite(), 'decimal_finite')
    return result


def _int(value, label, lower=0):
    _require(type(value) is int and value >= lower, label)
    return value


def _same(expected, actual, label):
    if isinstance(expected, Decimal):
        _require(_d(actual) == expected, label)
    elif isinstance(expected, dict):
        _require(type(actual) is dict and set(actual) == set(expected), label + ':keys')
        for key, value in expected.items():
            _same(value, actual[key], label + '/' + str(key))
    elif isinstance(expected, list):
        _require(type(actual) is list and len(actual) == len(expected), label + ':length')
        for index, value in enumerate(expected):
            _same(value, actual[index], label + '/' + str(index))
    else:
        _require(type(expected) is type(actual) and expected == actual, label)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _bound(root, reference):
    root = Path(root).resolve()
    _require(type(reference) is dict and {'path', 'sha256', 'bytes'} <= reference.keys(), 'artifact_reference')
    path = Path(reference['path'])
    path = (path if path.is_absolute() else root/path).resolve()
    _require(path.is_relative_to(root), 'artifact_outside_root')
    raw = path.read_bytes()
    _require(type(reference['bytes']) is int and len(raw) == reference['bytes'], 'artifact_size')
    _require(hashlib.sha256(raw).hexdigest() == reference['sha256'], 'artifact_hash')
    return raw


def _fee(notional, minimum):
    return max(Decimal(minimum), notional * Decimal('.0001')).quantize(CENT)


def _price(raw, side, slip):
    multiplier = Decimal(1) + Decimal(slip) / 10000 * (1 if side == 'buy' else -1)
    return (raw * multiplier).quantize(TICK, rounding=ROUND_CEILING if side == 'buy' else ROUND_FLOOR)


def _capacity(rows, index):
    return max(0, int((sum((_d(r['volume']) for r in rows[index-20:index]), ZERO) / 20 * Decimal('.01')) // 100) * 100)


def _settle_sale(cash, locked, notional, fee):
    """Exit costs can consume a sale-cash lock, never create purchase credit."""
    net = notional-fee
    _require(cash+net >= 0, 'unfinanced_sale')
    free_fee = min(-net, cash-locked) if net < 0 else ZERO
    locked_fee = -net-free_fee if net < 0 else ZERO
    new_locked = locked-locked_fee if net < 0 else locked+net
    return cash+net, new_locked, free_fee, locked_fee


def verify_account(fixture, account):
    """Check an existing ledger with independent arithmetic, not strategy replay."""
    with localcontext(CONTEXT):
        return _verify_account(fixture, account)


def _verify_account(fixture, account):
    assets, dates, bars = tuple(fixture['assets']), fixture['dates'], fixture['bars']
    _require(len(assets) == 2 and len(set(assets)) == 2 and set(bars) == set(assets), 'asset_identity')
    first, terminal = fixture['event_indices'][0], fixture['terminal_index']
    _require(type(first) is int and type(terminal) is int and 20 <= first < terminal < len(dates), 'calendar_bounds')
    _require(dates == sorted(set(dates)), 'calendar_unique_order')
    for asset in assets:
        _require(len(bars[asset]) == terminal+1, 'bar_count')
    policy, minimum, slip = account['policy'], account['minimum_commission'], account['slippage_bps']
    _require(policy in (*POLICIES, 'cash') and type(minimum) is int and type(slip) is int and (minimum, slip) in COSTS, 'policy_cost')
    _same(f'min{minimum}_slip{slip}', account['cost_id'], 'cost_id')
    _same(1, account['commission_bps'], 'commission_bps')
    _same(minimum == 0, account['minimum0_counterfactual'], 'counterfactual')
    _same(METHOD, account['method_sha256'], 'method')
    _same(_digest(fixture), account['fixture_sha256'], 'fixture_digest')
    _same(False, account['qualified'], 'qualification')
    _same(0, account['real_forward'], 'forward')
    initial_context = account['runtime']['context_initial']
    expected_context = dict(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999, capitals=1, clamp=0,
                            traps={k.__name__:v for k,v in CONTEXT.traps.items()},
                            flags={k.__name__:False for k in CONTEXT.flags})
    _same(expected_context, initial_context, 'decimal_context')
    final_context = account['runtime']['context_final']
    _same({k:v for k,v in expected_context.items() if k != 'flags'},
          {k:v for k,v in final_context.items() if k != 'flags'}, 'final_context')
    _require(set(final_context['flags']) == set(expected_context['flags']) and all(type(v) is bool for v in final_context['flags'].values()), 'final_flags')

    by_intent, by_day = {}, defaultdict(list)
    for n, intent in enumerate(account['intents']):
        _same(n, intent['intent_id'], 'intent_sequence')
        i = _int(intent['index'], 'intent_index', first)
        _require(i <= terminal and intent['asset'] in assets and intent['side'] in ('buy', 'sell'), 'intent_identity')
        _int(intent['quantity'], 'intent_quantity')
        _require(intent['quantity'] % 100 == 0, 'intent_lot')
        _same(_d(bars[intent['asset']][i-1]['close']), intent['prior_close'], 'intent_prior_price')
        _same(_capacity(bars[intent['asset']], i), intent['prior_capacity'], 'intent_prior_capacity')
        _require(intent['quantity'] <= intent['prior_capacity'], 'intent_capacity')
        by_day[i].append(intent)
    _require([x['index'] for x in account['intents']] == sorted(x['index'] for x in account['intents']), 'intent_time_order')
    for fill in account['fills']:
        n = _int(fill['intent_id'], 'fill_intent')
        _require(n < len(account['intents']) and n not in by_intent, 'fill_unique_intent')
        by_intent[n] = fill
    _require([x['intent_id'] for x in account['fills']] == sorted(by_intent), 'fill_order')
    actions = fixture.get('actions', [])
    _require(len({a['event_id'] for a in actions}) == len(actions), 'action_unique')
    for a in actions:
        _require(a['asset'] in assets and a['known_index'] <= a['record_index'] < a['ex_index'] <= a['pay_index'], 'action_sequence')
        _same(Decimal(1), a['share_multiplier'], 'no_share_conversion')
        _require(_d(a['cash_per_share']) >= 0, 'cash_distribution_nonnegative')

    cash, locked, previous, peak, maximum_dd = Decimal(10000), ZERO, Decimal(10000), Decimal(10000), ZERO
    quantities = dict.fromkeys(assets, 0)
    rights, receivables = {}, {}
    lots = {a: [] for a in assets}
    action_log, risk_log, capacity_failures, unknowns, rejections = [], [], [], [], []
    annual, total_components = {}, dict.fromkeys(COMPONENTS, ZERO)
    total_fee = total_slip = ZERO
    completed_lots = completed_cycles = 0
    cycle_active = paused = mandatory = False
    flat_index = None
    initial_snapshot = None
    def balance():
        return dict(book_cash=cash, spendable_cash=cash-locked, locked_sale_cash=locked,
                    quantities=dict(quantities), rights=copy.deepcopy(rights), receivables=copy.deepcopy(receivables))
    _same(list(range(first, terminal+1)), [d['index'] for d in account['days']], 'day_indices')
    for day in account['days']:
        i, terminal_day = day['index'], day['index'] == terminal
        before = balance()
        q_start = quantities.copy()
        previous_marks = {a:_d(bars[a][i-1]['close']) for a in assets}
        recognised = ZERO
        for a in actions:
            key = a['event_id']
            if i == a['ex_index'] and key in rights:
                ab = balance(); right = rights.pop(key)
                amount = (right['quantity']*_d(a['cash_per_share'])).quantize(CENT)
                receivables[key] = dict(amount=amount, quantity=right['quantity'], pay_index=a['pay_index'])
                recognised += amount
                action_log.append(dict(index=i,event_id=key,kind='ex_receivable',amount=amount,before=ab,after=balance()))
        today = []
        for intent in by_day[i]:
            n, asset, side, qty = (intent[k] for k in ('intent_id','asset','side','quantity'))
            row, phase = bars[asset][i], intent['phase']
            _require(phase in ('monthly_sell','monthly_buy','risk_exit','terminal'), 'phase')
            _require((side == 'buy') == (phase == 'monthly_buy'), 'side_phase')
            _require(not terminal_day or phase == 'terminal', 'terminal_priority')
            if mandatory:
                _require(side == 'sell' and phase in ('risk_exit','terminal'), 'risk_priority')
            if policy == 'cash':
                _require(qty == 0, 'cash_account_no_order')
            if qty == 0:
                _require(n not in by_intent, 'zero_quantity_fill'); continue
            rejection = dict(index=i,asset=asset,side=side,quantity=qty,phase=phase)
            reason = None
            if row['suspended'] is True or row[side+'_blocked'] is True:
                reason = 'known_execution_constraint'
            else:
                for flag in ('suspended',side+'_blocked'):
                    _require(row[flag] is None or type(row[flag]) is bool, 'constraint_type')
                    if row[flag] is None:
                        unknowns.append(dict(index=i,asset=asset,flag=flag,phase=phase))
            raw = _d(row['open']); price = _price(raw,side,slip)
            notional = qty*price; fee = _fee(notional,minimum)
            budget = None if intent['frozen_budget'] is None else _d(intent['frozen_budget'])
            if reason is None and price <= 0:
                reason = 'nonpositive_adverse_tick_price'
            if reason is None and side == 'buy':
                cost = notional+fee
                if budget is None or cost > budget or cost > cash-locked:
                    reason = 'frozen_budget_or_spendable_cash'
                    rejection.update(frozen_budget=budget,actual_cost=cost,spendable_cash=cash-locked)
                else:
                    exposure = sum((quantities[a]*_d(bars[a][i]['open']) for a in assets),ZERO)
                    equity = cash+sum((r['amount'] for r in receivables.values()),ZERO)+exposure
                    if exposure+qty*raw > equity-cost+qty*raw:
                        reason = 'marked_exposure_limit'
            if reason is None and side == 'sell':
                _require(qty <= quantities[asset], 'oversell')
                if cash+notional-fee < 0:
                    reason = 'cannot_finance_exit_fee'
            if reason is not None:
                _require(n not in by_intent, 'rejected_order_filled')
                rejection['reason']=reason; rejections.append(rejection); continue
            _require(n in by_intent, 'valid_recorded_order_missing_fill')
            fb=balance(); free_fee=fee if side=='buy' else ZERO; locked_fee=ZERO
            if side == 'buy':
                cash -= notional+fee; quantities[asset] += qty
                lots[asset].append(dict(start_index=i,initial=qty,remaining=qty)); cycle_active=True
            else:
                cash,locked,free_fee,locked_fee=_settle_sale(cash,locked,notional,fee)
                quantities[asset] -= qty
                remaining=qty
                for lot in lots[asset]:
                    taken=min(lot['remaining'],remaining)
                    lot['remaining']-=taken; remaining-=taken
                    if taken and lot['remaining']==0: completed_lots+=1
                    if not remaining: break
                _require(remaining==0,'FIFO_quantity')
                if cycle_active and not any(quantities.values()):
                    completed_cycles+=1;cycle_active=False
            _require(ZERO <= locked <= cash,'cash_conservation')
            loss=qty*((price-raw) if side=='buy' else (raw-price))
            total_fee+=fee;total_slip+=loss
            expected=dict(intent_id=n,index=i,date=dates[i],asset=asset,side=side,quantity=qty,
                          raw_open=raw,price=price,notional=notional,fee=fee,slippage_cost=loss,phase=phase,
                          fee_payment=dict(from_current_sale=min(fee,notional) if side=='sell' else ZERO,
                                           from_free_cash=free_fee,from_locked_sale=locked_fee),
                          frozen_budget=budget,before=fb,after=balance())
            _same(expected,by_intent[n],f'fill/{n}');today.append(expected)
            if Decimal(qty)>_d(row['volume'])*Decimal('.01'):
                capacity_failures.append(dict(index=i,asset=asset,quantity=qty,phase=phase,
                                              audit_clock='after_full_day_volume_available',reason='ex_post_day_volume_failed_trade_retained'))
        for a in actions:
            key,asset=a['event_id'],a['asset']
            if not terminal_day and i==a['record_index'] and quantities[asset]>0:
                ab=balance()
                rights[key]=dict(asset=asset,quantity=quantities[asset],ex_index=a['ex_index'],pay_index=a['pay_index'],included_in_NAV=False)
                action_log.append(dict(index=i,event_id=key,kind='record_right',quantity=quantities[asset],before=ab,after=balance()))
            if not terminal_day and i==a['pay_index'] and key in receivables:
                ab=balance(); amount=receivables.pop(key)['amount'];cash+=amount
                action_log.append(dict(index=i,event_id=key,kind='pay_after_fills',amount=amount,before=ab,after=balance()))
        before_release=balance()
        if not terminal_day:
            locked=ZERO
        marks={a:_d(bars[a][i]['open' if terminal_day else 'close']) for a in assets}
        nav=cash+sum((r['amount'] for r in receivables.values()),ZERO)+sum((quantities[a]*marks[a] for a in assets),ZERO)
        parts=dict(carried_exposure=sum((q_start[a]*(marks[a]-previous_marks[a]) for a in assets),ZERO),
                   trade_timing=sum(((f['quantity'] if f['side']=='buy' else -f['quantity'])*(marks[f['asset']]-f['raw_open']) for f in today),ZERO),
                   dividend_entitlement=recognised,commission=-sum((f['fee'] for f in today),ZERO),
                   slippage=-sum((f['slippage_cost'] for f in today),ZERO))
        _require(sum(parts.values(),ZERO)==nav-previous,'daily_attribution_identity')
        peak=max(peak,nav);dd=(peak-nav)/peak;maximum_dd=max(maximum_dd,dd)
        exposed=any(q_start.values()) or any(f['side']=='buy' for f in today)
        triggers=[]
        if previous-nav>=previous*Decimal('.02'):triggers.append('daily_2percent_pause')
        if exposed and dd>=Decimal('.40'):triggers.append('global_40percent_pause')
        for reason in triggers:
            paused,flat_index=True,None
            risk_log.append(dict(index=i,kind=reason,previous_NAV=previous,NAV=nav,peak=peak,DD=dd))
        mandatory=paused and any(quantities.values())
        if paused and not any(quantities.values()) and flat_index is None:
            flat_index=i;risk_log.append(dict(index=i,kind='flat_cooldown_started',earliest_open_index=i+6))
        if paused and not any(quantities.values()) and flat_index is not None and i>=flat_index+5:
            paused=False;flat_index=None;risk_log.append(dict(index=i,kind='eligible_from_next_session_only_next_month'))
        expected=dict(index=i,date=dates[i],terminal_open_stub=terminal_day,before=before,after=balance(),
                      previous_raw_marks=previous_marks,before_close_cash_release=before_release,marks=marks,
                      NAV=nav,previous_NAV=previous,peak=peak,DD=dd,had_exposure=exposed,paused=paused,
                      mandatory_exit=mandatory,flat_index=flat_index,attribution=parts)
        _same(expected,day,f'day/{i}')
        if i==first+1:
            initial_snapshot=dict(cash=cash,quantities=quantities.copy(),rights=copy.deepcopy(rights),receivables=copy.deepcopy(receivables),fees=total_fee)
        year=dates[i-1 if terminal_day else i][:4]
        annual[year]=annual.get(year,ZERO)+(nav-previous)
        for key in COMPONENTS:total_components[key]+=parts[key]
        previous=nav
    _same(rejections,account['rejections'],'rejections')
    _same(action_log,account['action_records'],'actions')
    _same(risk_log,account['risk_records'],'risks')
    _same(capacity_failures,account['capacity_failures'],'capacity')
    _same(unknowns,account['unknown_execution_constraints'],'unknown_constraints')
    _same(lots,account['FIFO_lots'],'FIFO')
    _same(annual,account['annual_contributions'],'annual_contributions')
    _same(total_components,account['attribution'],'attribution')
    _same(initial_snapshot,account['initial_snapshot'],'initial_basket')
    _require(sum(total_components.values(),ZERO)==previous-10000,'account_attribution_identity')
    events=account['event_attempts']
    _same(fixture['event_indices'],[e['index'] for e in events],'event_indices')
    for event in events:
        _same(dates[event['index']],event['date'],'event_date')
        sell=sum(f['index']==event['index'] and f['phase']=='monthly_sell' for f in account['fills'])
        buy=sum(f['index']==event['index']+1 and f['phase']=='monthly_buy' for f in account['fills'])
        _same(sell,event['sell_fills'],'event_sell_count');_same(buy,event['buy_fills'],'event_buy_count')
    unsettled=bool(any(quantities.values()) or rights or receivables)
    expected_summary=dict(terminal_cash=cash,terminal_spendable_cash=cash-locked,
        terminal_locked_sale_cash=locked,terminal_book_NAV=previous,terminal_quantities=quantities,
        terminal_receivables=receivables,terminal_unexercised_rights=rights,unexercised_rights_included_in_NAV=False,
        terminal_unsettled=unsettled,terminal_cash_netPnL=cash-10000,
        terminal_inventory_and_rights_closed=not unsettled,
        terminal_cash_netPnL_is_fully_settled=not unsettled and locked==0,
        book_netPnL=previous-10000,observed_maxDD=maximum_dd,risk_ceiling_pass=maximum_dd<=Decimal('.40'),
        fill_count=len(account['fills']),completed_FIFO_purchase_lots=completed_lots,complete_policy_exposure_cycles=completed_cycles,
        two_sided_rebalance_events=sum(bool(e['sell_fills']) and bool(e['buy_fills']) for e in events),
        initial_two_assets_filled=bool(initial_snapshot and all(initial_snapshot['quantities'].values())),
        total_commission=total_fee,total_slippage=total_slip,attribution_reconciled=True,capacity_pass=not capacity_failures,
        financial_verdict='conditional_historical_diagnostic_only' if account['historical_returns_computed'] else 'not_evaluated_artificial_engineering_only')
    _same(expected_summary,account['summary'],'summary')
    return dict(intervals=terminal-first+1,fills=len(account['fills']),actions=len(action_log),risk_records=len(risk_log),
                annual={k:str(v) for k,v in annual.items()},summary=account['summary'],initial_snapshot=account['initial_snapshot'],
                attribution={k:str(v) for k,v in total_components.items()},events=events)


ENDPOINTS = ('breadth_net', 'breadth_minus_monthly_50_50', 'breadth_minus_own_trend')


def verify_signal_frame(fixture, actual):
    """Independent arithmetic of the saved TR table, without order decisions."""
    with localcontext(CONTEXT):
        assets, dates = fixture['assets'], fixture['dates']
        ends = fixture['month_end_sessions']
        indices = [dates.index(d) for d in ends]
        serials = [int(d[:4])*12+int(d[5:7]) for d in ends]
        _require(len(indices) >= 13 and ends == sorted(set(ends))
                 and all(b-a == 1 for a,b in zip(serials, serials[1:])), 'consecutive_month_ends')
        _require(all(i < fixture['terminal_index'] and dates[i][:7] != dates[i+1][:7]
                     for i in indices), 'completed_month_ends')
        distributions = defaultdict(lambda: ZERO)
        for event in fixture['actions']:
            _require(event['known_index'] <= event['record_index'] < event['ex_index'] <= event['pay_index'], 'signal_action_clock')
            _same(Decimal(1), event['share_multiplier'], 'signal_no_conversion')
            distributions[(event['asset'], event['ex_index'])] += _d(event['cash_per_share'])
        levels, monthly, expected = dict.fromkeys(assets, Decimal(100)), {a:[] for a in assets}, []
        ends_set = set(indices)
        for index in range(indices[0], indices[-1]+1):
            if index > indices[0]:
                for a in assets:
                    previous = _d(fixture['bars'][a][index-1]['close'])
                    close = _d(fixture['bars'][a][index]['close'])
                    _require(previous > 0 and close > 0, 'signal_positive_raw_close')
                    levels[a] = levels[a]*(close+distributions[(a,index)])/previous
            if index not in ends_set:
                continue
            for a in assets:
                monthly[a].append(levels[a])
            count = len(monthly[assets[0]])
            if count < 13:
                continue
            signs = [int(monthly[a][-1] > monthly[a][-13]) for a in assets]
            weights = dict(breadth=dict.fromkeys(assets,Decimal(sum(signs))/4),
                monthly_50_50=dict.fromkeys(assets,Decimal('.5')),
                own_trend={a:Decimal(s)/2 for a,s in zip(assets,signs)})
            expected.append(dict(index=index,date=dates[index],month_count=13,
                prior_month_date=dates[indices[count-13]],TR={a:monthly[a][-1] for a in assets},
                TR_prior12={a:monthly[a][-13] for a in assets}, signs=signs,
                exposure=Decimal(sum(signs))/2,weights=weights,
                terminal_overrides=index+1 >= fixture['terminal_index']))
        _same(expected, actual, 'signal_frame')
        eligible = [r['index'] for r in expected if r['index']+2 < fixture['terminal_index']]
        _same(eligible, fixture['monthly_decision_indices'], 'monthly_decision_indices')
        _same([i+1 for i in eligible], fixture['event_indices'], 'monthly_sell_indices')
        return expected


def verify_statistics(annual, statistics, source, historical):
    """Reconstruct paired arithmetic from recorded annual cash ledgers only."""
    import numpy as np
    with localcontext(CONTEXT):
        years = sorted(annual['min0_slip0']['breadth'])
        _require(len(years) == 9, 'statistics_nine_years')
        if historical:
            _same([str(y) for y in range(2015, 2024)], years, 'historical_years')
        keys, columns = [], []
        for minimum, slip in COSTS:
            cost = f'min{minimum}_slip{slip}'
            pair = annual[cost]
            for policy in POLICIES:
                _same(years, sorted(pair[policy]), 'paired_years')
            for endpoint, baseline in zip(ENDPOINTS, (None, 'monthly_50_50', 'own_trend')):
                keys.append(cost+'/'+endpoint)
                columns.append([float(_d(pair['breadth'][y])-(
                    _d(pair[baseline][y]) if baseline else ZERO)) for y in years])
        data = np.asarray(columns, dtype='float64').T
        _require(data.shape == (9, 27) and bool(np.isfinite(data).all()), 'statistics_shape')
        rng = np.random.Generator(np.random.PCG64(20261107))
        replicates = np.empty((5000, 27), dtype='float64')
        for i in range(5000):
            starts = rng.integers(0, 9, size=5)
            rows = ((starts[:, None]+np.arange(2)) % 9).reshape(-1)[:9]
            replicates[i] = data[rows].mean(axis=0)
        lower = np.quantile(replicates, .05/27, axis=0, method='linear')
        expected = dict(status='computed_conditional_historical_trace_sensitivity' if historical else 'computed_artificial_fixed_trace_sensitivity',
            source_nature=source, qualified=False, N=9, years=years, replications=5000, seed=20261107,
            block=2, starts_per_replication=5, truncate_rows_to=9, shared_indices_for_all27=True,
            units='CNY_per_observed_year' if historical else 'CNY_per_artificial_year',
            statistic='arithmetic_mean_annual_PnL', endpoint_keys=keys, lower=dict(zip(keys, lower.tolist())),
            observed_means=dict(zip(keys, data.mean(axis=0).tolist())),
            replicate_means_sha256=hashlib.sha256(replicates.astype('<f8').tobytes()).hexdigest(),
            quantile=.05/27, quantile_method='linear', numpy_version=np.__version__, historical_returns_computed=historical)
        _same(expected, statistics, 'statistics')
        return expected['replicate_means_sha256']


def _fixed_checks(results, annual, statistics, signal_rows, primary_exposure_paths):
    """Frozen economic questions, separate from accounting validity/eligibility."""
    with localcontext(CONTEXT):
        checks = {'all28_recorded_accounting': True}
        diagnostics = {}
        for cost in ('min5_slip10', 'min10_slip30'):
            new = results[cost+'/breadth']['summary']
            checks[cost+'/breadth_net_cash_positive'] = _d(new['terminal_cash_netPnL']) > 0
            checks[cost+'/breadth_DD_within40'] = _d(new['observed_maxDD']) <= Decimal('.40')
            for policy in POLICIES:
                row = results[cost+'/'+policy]['summary']
                checks[cost+'/'+policy+'/settled'] = not row['terminal_unsettled']
                checks[cost+'/'+policy+'/capacity'] = row['capacity_pass']
            for baseline in POLICIES[1:]:
                other = results[cost+'/'+baseline]['summary']
                checks[cost+'/increment_'+baseline+'_positive'] = (
                    _d(new['terminal_cash']) > _d(other['terminal_cash']))
        primary = annual['min5_slip10']
        years = sorted(primary['breadth'])
        for label, subset in (('earlier', years[:5]), ('later', years[5:])):
            for baseline in POLICIES[1:]:
                checks[label+'/increment_'+baseline+'_positive'] = sum((
                    _d(primary['breadth'][y])-_d(primary[baseline][y]) for y in subset), ZERO) > 0
            checks[label+'/discordant_signal'] = any(r['date'][:4] in subset and
                r['signs'] in ([0,1], [1,0]) and not r['terminal_overrides'] for r in signal_rows)
            checks[label+'/actual_exposure_difference_vs_B'] = any(
                day[:4] in subset and quantities != primary_exposure_paths['own_trend'][day]
                for day, quantities in primary_exposure_paths['breadth'].items())
        for endpoint in ENDPOINTS:
            checks['primary/'+endpoint+'/adjusted_lower_positive'] = statistics['lower']['min5_slip10/'+endpoint] > 0
        for key, row in results.items():
            summary = row['summary']
            diagnostics[key] = dict(net_cash_PnL=summary['terminal_cash_netPnL'],
                book_PnL=summary['book_netPnL'], observed_DD=summary['observed_maxDD'],
                settled=not summary['terminal_unsettled'], capacity=summary['capacity_pass'],
                fills=summary['fill_count'], commission=summary['total_commission'],
                slippage=summary['total_slippage'])
        return dict(checks=checks, all_fixed_conditions_passed=all(checks.values()),
            diagnostics=diagnostics, qualified=False,
            meaning='conditional seen-history mechanism support only, never automatic operational eligibility')


def verify_recorded_accounts(root, decoded_ref, accounts, statistics_ref, registration_sha256):
    """Saved-output check, without model import, original wire reads or trading."""
    root = Path(root).resolve()
    _require(type(registration_sha256) is str and len(registration_sha256) == 64
             and all(c in '0123456789abcdef' for c in registration_sha256), 'registration_digest')
    snapshot = json.loads(_bound(root, decoded_ref))
    _require(set(snapshot) == {'fixture', 'provenance'}, 'snapshot_schema')
    fixture, provenance = snapshot['fixture'], snapshot['provenance']
    _same(registration_sha256, provenance['registration_sha256'], 'snapshot_registration')
    source = fixture['source_nature']
    test = source == 'test_artificial_values_true_calendar'
    _require(source in ('test_artificial_values_true_calendar',
        'known_history_provider_wire_with_retrospective_announced_actions'), 'source_identity')
    _same(source, provenance['source_nature'], 'provenance_source')
    _same(test, provenance['test_injected_values'], 'provenance_test')
    _same(not test, fixture['constructed_from_market_data'], 'fixture_market_identity')
    _same(['CN_ETF_XSHG_510300','CN_ETF_XSHG_518880'], fixture['assets'], 'historical_assets')
    expected = {f'min{m}_slip{s}/{p}' for m, s in COSTS for p in POLICIES} | {'cash'}
    _require(set(accounts) == expected, 'exact_28_account_keys')
    annual, results, refs = {}, {}, [decoded_ref, statistics_ref]
    signal_rows = None
    primary_exposure_paths = {}
    fixture_sha, provenance_sha = _digest(fixture), _digest(provenance)
    identities = [(f'min{m}_slip{s}/{p}', p, m, s) for m,s in COSTS for p in POLICIES]
    identities.append(('cash', 'cash', 0, 0))
    for key, policy, minimum, slip in identities:
        wrapper = accounts[key]
        _require(set(wrapper) == {'artifact','summary'}, 'account_index_schema')
        ref = wrapper['artifact']; refs.append(ref)
        account = json.loads(_bound(root, ref))
        for field, value in dict(policy=policy, cost_id=f'min{minimum}_slip{slip}',
                source_nature=source, evidence_class=source, registration_sha256=registration_sha256,
                fixture_sha256=fixture_sha, normalized_input_sha256=fixture_sha,
                provenance_sha256=provenance_sha, test_injected_values=test,
                historical_returns_computed=not test).items():
            _same(value, account[field], 'identity/'+field)
        _same(account['summary'], wrapper['summary'], 'index_summary')
        if signal_rows is None:
            signal_rows = verify_signal_frame(fixture, account['signal_frame'])
        else:
            _same(signal_rows, account['signal_frame'], 'same_signal_frame')
        checked = verify_account(fixture, account); results[key] = checked
        if minimum == 5 and slip == 10 and policy in ('breadth','own_trend'):
            primary_exposure_paths[policy] = {d['date']:d['after']['quantities'] for d in account['days']}
        if policy != 'cash':
            annual.setdefault(f'min{minimum}_slip{slip}', {})[policy] = checked['annual']
    stats = json.loads(_bound(root, statistics_ref))
    stats_sha = verify_statistics(annual, stats, source, not test)
    decision = _fixed_checks(results, annual, stats, signal_rows, primary_exposure_paths)
    differences = {}
    with localcontext(CONTEXT):
        for m, s in COSTS:
            cost = f'min{m}_slip{s}'; new = results[cost+'/breadth']
            differences[cost] = {}
            for policy in ('monthly_50_50','own_trend'):
                other = results[cost+'/'+policy]
                parts = {k:_d(new['attribution'][k])-_d(other['attribution'][k]) for k in COMPONENTS}
                delta = _d(new['summary']['terminal_book_NAV'])-_d(other['summary']['terminal_book_NAV'])
                _require(sum(parts.values(), ZERO) == delta, 'policy_difference_attribution')
                differences[cost][policy] = dict(components={k:str(v) for k,v in parts.items()},
                    book_NAV_difference=str(delta), meaning='whole_policy_difference_including_risk_cash_and_dividends')
    _require(len({str((root/Path(r['path'])).resolve()) for r in refs}) == len(refs), 'artifact_paths_unique')
    for ref in refs:
        _bound(root, ref)
    return dict(status='recorded_accounting_consistent', accounts_checked=28,
        intervals_checked=sum(r['intervals'] for r in results.values()),
        fills_checked=sum(r['fills'] for r in results.values()),
        action_records_checked=sum(r['actions'] for r in results.values()),
        risk_records_checked=sum(r['risk_records'] for r in results.values()),
        registration_sha256=registration_sha256, fixture_sha256=fixture_sha,
        provenance_sha256=provenance_sha, decoded_input_sha256=_digest(snapshot),
        statistics_replicates_sha256=stats_sha, policy_difference_attribution=differences,
        summaries={k:r['summary'] for k,r in results.items()},
        annual_contributions={k:r['annual'] for k,r in results.items()},
        fixed_method_decision=decision,
        recorded_accounting_fields_checked=True, recorded_signal_arithmetic_checked=True,
        signal_state_counts={str(a)+str(b):sum(r['signs'] == [a,b] and not r['terminal_overrides']
            for r in signal_rows) for a in (0,1) for b in (0,1)}, strategy_intent_replayed=False,
        source_nature=source, test_injected_values=test, qualified=False, real_forward=0,
        limits=['Recorded cash, positions, actions, FIFO, NAV, risk and statistics only',
                'No original financial source reads, strategy rerun, PIT or execution certification'])

