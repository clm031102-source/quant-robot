"""Independent saved-ledger arithmetic. No strategy imports, wire reads, or orders."""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import (Decimal as D, Context, localcontext, ROUND_HALF_UP, ROUND_CEILING,
                     ROUND_FLOOR, InvalidOperation, DivisionByZero, Overflow)
import hashlib
import json
from pathlib import Path

ASSETS = ('SPY','EFA','IEF','GLD')
POLICIES = ('rotation','positive_equal','fixed_quarters')
COSTS = tuple((m,s) for m in ('0.35','1.00','2.50') for s in (0,10,30))
METHOD = 'dbc19912feded581fd55c4a5e0aa992140e3dfa4743586df2cd3a00c83e04a30'
ZERO, CENT = D(0), D('.01')
CONTEXT = Context(prec=40,rounding=ROUND_HALF_UP,Emin=-999999,Emax=999999,capitals=1,clamp=0)
for signal in CONTEXT.traps:
    CONTEXT.traps[signal] = signal in (InvalidOperation,DivisionByZero,Overflow)
CONTEXT.clear_flags()
PARTS = ('carried_exposure','trade_timing','net_dividend_entitlement','commissions','sell_levies','slippage')


def require(ok, label):
    if not ok: raise ValueError(label)


def decimal(value):
    require(type(value) in (str,int,D), 'decimal_type')
    try: result = D(value)
    except (InvalidOperation,ValueError) as exc: raise ValueError('decimal_syntax') from exc
    require(result.is_finite(),'decimal_nonfinite')
    return result


def same(expected, actual, label):
    if isinstance(expected,D): require(decimal(actual)==expected,label)
    elif isinstance(expected,dict):
        require(type(actual) is dict and set(expected)==set(actual),label+':keys')
        for k,v in expected.items(): same(v,actual[k],label+'/'+str(k))
    elif isinstance(expected,list):
        require(type(actual) is list and len(expected)==len(actual),label+':length')
        for i,v in enumerate(expected): same(v,actual[i],label+'/'+str(i))
    else: require(type(expected) is type(actual) and expected==actual,label)


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def fee(q, minimum):
    return max(D(minimum),D(q)*D('.005')).quantize(CENT,rounding=ROUND_CEILING)


def execution_price(raw, side, slip):
    return (raw*(1+D(slip)/10000*(1 if side=='buy' else -1))).quantize(CENT,
        rounding=ROUND_CEILING if side=='buy' else ROUND_FLOOR)


def capacity(fixture, symbol, before):
    require(type(before) is int and before>=20,'capacity_prior20')
    return max(0,int((sum((decimal(d['prices'][symbol]['volume']) for d in fixture['days'][before-20:before]),ZERO)/20*D('.01')).to_integral_value(rounding=ROUND_FLOOR)))


def dividend_item(symbol, quantity, amount, ex_date):
    require(symbol in ASSETS and type(quantity) is int and quantity>0,'dividend_quantity')
    gross=quantity*decimal(amount);require(gross>=0,'dividend_nonnegative')
    net=(gross*D('.70')).quantize(CENT)
    return dict(symbol=symbol,quantity=quantity,gross=gross,amount=net,modeled_withholding=gross-net,
                earliest_payment_date=(date.fromisoformat(ex_date)+timedelta(days=45)).isoformat())


def sale_lock(intent_id, index, amount, dates):
    require(decimal(amount)>0,'positive_lock')
    due=index+3
    return dict(id='sale_'+str(intent_id),amount=decimal(amount),sale_index=index,release_index=due,
                release_date=dates[due] if due<len(dates) else None)


def verify_signals(fixture, actual):
    with localcontext(CONTEXT):
        dates=[r['date'] for r in fixture['days']]
        require(dates==sorted(set(dates)),'calendar_order')
        ends=[i for i in range(len(dates)-1) if dates[i][:7]!=dates[i+1][:7]]
        months=[int(dates[i][:4])*12+int(dates[i][5:7]) for i in ends]
        require(len(ends)>=13 and all(b-a==1 for a,b in zip(months,months[1:])),'signal_months')
        same(dates[ends[12]],fixture['first_decision_date'],'first_decision')
        expected=[]
        for j in range(12,len(ends)):
            i,p=ends[j],ends[j-12]
            returns={a:decimal(fixture['days'][i]['prices'][a]['adj_close'])/decimal(fixture['days'][p]['prices'][a]['adj_close'])-1 for a in ASSETS}
            positive=[a for a in ASSETS if returns[a]>0]
            ranked=sorted(positive,key=lambda a:(-returns[a],ASSETS.index(a)))
            gross=D(min(len(positive),2))/2
            weights={'rotation':{a:D('.5') if a in ranked[:2] else ZERO for a in ASSETS},
                'positive_equal':{a:gross/len(positive) if a in positive else ZERO for a in ASSETS},
                'fixed_quarters':dict.fromkeys(ASSETS,D('.25'))}
            expected.append(dict(index=i,date=dates[i],prior_date=dates[p],returns=returns,positive=positive,
                ranked_positive=ranked,intended_gross=gross,weights=weights,ordinary_execution_possible=i+4<len(dates)-1))
        same(expected,actual,'signals')
        return expected


def verify_account(fixture, account):
    with localcontext(CONTEXT):
        return _verify_account(fixture, account)


def _verify_account(fixture, account, *, expected_method=METHOD, signal_verifier=verify_signals):
    same(list(ASSETS),fixture['assets'],'assets')
    same(expected_method,fixture['method_sha256'],'fixture_method')
    same(expected_method,account['method_sha256'],'account_method')
    same(digest(fixture),account['fixture_sha256'],'fixture_hash')
    same(digest(fixture['provenance']),account['provenance_sha256'],'provenance_hash')
    same(fixture['evidence_kind'],account['evidence_kind'],'evidence_kind')
    same(fixture['evidence_kind']=='known_history_conditional',account['historical_returns_computed'],'historical_identity')
    same(fixture['evidence_kind']=='artificial_values_true_calendar',account['test_injected_values'],'test_identity')
    same(fixture['evidence_kind']=='known_history_conditional',fixture['provenance']['constructed_from_market_data'],'market_identity')
    same(False,account['qualified'],'qualified');same(0,account['real_forward'],'forward')
    policy,minimum,slip=account['policy'],account['minimum_commission'],account['slippage_bps']
    require(policy in (*POLICIES,'cash') and type(slip) is int and (minimum,slip) in COSTS,'policy_cost')
    same(f'min{minimum}_slip{slip}',account['cost_id'],'cost_id')
    same('.005',account['commission_per_share'],'commission_per_share');same('5',account['sell_levy_bps'],'levy_rate')
    initial_context=dict(prec=40,rounding=ROUND_HALF_UP,Emin=-999999,Emax=999999,capitals=1,clamp=0,
        traps={k.__name__:v for k,v in CONTEXT.traps.items()},flags={k.__name__:False for k in CONTEXT.flags})
    same(initial_context,account['runtime']['context_initial'],'runtime_context')
    final=account['runtime']['context_final']
    same({k:v for k,v in initial_context.items() if k!='flags'},{k:v for k,v in final.items() if k!='flags'},'final_context')
    require(set(final['flags'])==set(initial_context['flags']) and all(type(v) is bool for v in final['flags'].values()),'final_flags')
    dates=[d['date'] for d in fixture['days']];rows=fixture['days'];terminal=len(dates)-1
    require(dates==sorted(set(dates)) and dates[-1]==fixture['terminal_date'],'calendar')
    first=dates.index(fixture['first_decision_date'])
    signals=signal_verifier(fixture,account['signals'])
    same(list(range(first+1,terminal+1)),[d['index'] for d in account['days']],'day_indices')
    dividends=fixture['dividends'];require(len({x['id'] for x in dividends})==len(dividends),'dividend_ids')
    for x in dividends:
        require(x['symbol'] in ASSETS and x['ex_date'] in dates and decimal(x['amount_per_share'])>=0,'dividend_input')
    by_day=defaultdict(list);fill_by_id={}
    for n,intent in enumerate(account['intents']):
        same(n,intent['intent_id'],'intent_id')
        i=intent['due_index'];a=intent['asset'];side=intent['side'];q=intent['quantity']
        require(type(i) is int and first<i<=terminal and a in ASSETS and side in ('buy','sell'),'intent_identity')
        require(type(q) is int and q>=0 and type(intent['capacity']) is int,'integer_quantity')
        same(capacity(fixture,a,i),intent['capacity'],'prior_capacity')
        require(q<=intent['capacity'] and intent['planned_index']==i-1,'intent_causal_bound')
        planned=decimal(rows[i-1]['prices'][a]['close'])
        if side=='buy': planned=execution_price(planned,side,slip)
        same(planned,intent['planned_price'],'intent_prior_price')
        require(intent['phase'] in ('monthly_sell','monthly_buy','risk_exit','terminal'),'intent_phase')
        require((side=='buy')==(intent['phase']=='monthly_buy'),'intent_side_phase')
        if side=='buy': require(intent['budget'] is not None and decimal(intent['budget'])>=0,'buy_budget')
        else: same(None,intent['budget'],'sell_budget')
        if policy=='cash': same(0,q,'cash_no_orders')
        by_day[i].append(intent)
    same(sorted(x['due_index'] for x in account['intents']),[x['due_index'] for x in account['intents']],'intent_time_order')
    for f in account['fills']:
        n=f['intent_id'];require(type(n) is int and 0<=n<len(account['intents']) and n not in fill_by_id,'fill_unique')
        fill_by_id[n]=f
    same(sorted(fill_by_id),[f['intent_id'] for f in account['fills']],'fill_order')
    cash=D('1000');q=dict.fromkeys(ASSETS,0);locks=[];receivables={};lots={a:[] for a in ASSETS}
    previous=peak=D('1000');previous_dd=max_dd=ZERO;paused=False;cooldown=0;risk_due=None
    annual={};parts_total=dict.fromkeys(PARTS,ZERO);fees=levies=slippage_total=net_dividends=ZERO
    actions=[];risks=[];observations=[];rejects=[];unknowns=[]
    def balance():
        return dict(spendable_cash=cash,locked_cash=sum((x['amount'] for x in locks),ZERO),
                    locks=deepcopy(locks),quantities=q.copy(),receivables=deepcopy(receivables))
    def nav(marks):
        return cash+sum((x['amount'] for x in locks),ZERO)+sum((x['amount'] for x in receivables.values()),ZERO)+sum((q[a]*marks[a] for a in ASSETS),ZERO)
    def observe(i,marks,phase):
        nonlocal peak,previous_dd,max_dd,paused,cooldown,risk_due,day_active,triggered
        value=nav(marks);require(value>0 and cash>=0 and all(n>=0 for n in q.values()),'wallet_invariant')
        day_active=day_active or any(q.values());peak=max(peak,value)
        dd=(peak-value)/peak;loss=(previous-value)/previous
        fresh=previous_dd<D('.40')<=dd;dd_trigger=dd>=D('.40') and (day_active or fresh);daily=loss>=D('.02')
        trigger=dd_trigger or daily
        item=dict(index=i,date=dates[i],phase=phase,marks=marks,balances=balance(),NAV=value,reference_NAV=previous,
            peak=peak,DD=dd,daily_loss=loss,fresh_DD_cross=fresh,day_active=day_active,DD_trigger=bool(dd_trigger),
            daily_trigger=bool(daily),trigger=bool(trigger))
        observations.append(item)
        if dd>=D('.40') or daily:risks.append(deepcopy(item))
        if trigger:
            paused=True;cooldown=0;triggered=True
            if any(q.values()):risk_due=min(risk_due,i+1) if risk_due is not None else i+1
        previous_dd=dd;max_dd=max(max_dd,dd)
        return value
    for day in account['days']:
        i=day['index'];is_terminal=i==terminal;before=balance();prior_q=q.copy()
        prior_marks={a:decimal(rows[i-1]['prices'][a]['close']) for a in ASSETS}
        open_marks={a:decimal(rows[i]['prices'][a]['open']) for a in ASSETS}
        day_active=bool(any(q.values()));triggered=False
        if paused and cooldown>=5 and not any(q.values()):
            paused=False;cooldown=0;risks.append(dict(index=i,kind='resume_only_at_next_monthly_decision'))
        carried_risk=risk_due is not None and risk_due<=i
        obs_start=len(observations);entitlement=ZERO
        for item in list(locks):
            if item['release_index']<=i:
                b=balance();cash+=item['amount'];locks.remove(item)
                actions.append(dict(index=i,kind='sale_cash_release',item=item,before=b,after=balance()))
        for key,item in list(receivables.items()):
            if item['earliest_payment_date']<=dates[i]:
                b=balance();cash+=item['amount'];del receivables[key]
                actions.append(dict(index=i,kind='dividend_payment',id=key,item=item,before=b,after=balance()))
        for d in dividends:
            a=d['symbol']
            if d['ex_date']==dates[i] and q[a]>0:
                b=balance();item=dividend_item(a,q[a],d['amount_per_share'],d['ex_date']);net=item['amount']
                receivables[d['id']]=item;entitlement+=net;net_dividends+=net
                actions.append(dict(index=i,kind='ex_entitlement',id=d['id'],item=deepcopy(item),before=b,after=balance()))
        observe(i,open_marks,'prior_held_open');today=[]
        for intent in by_day[i]:
            n=intent['intent_id'];a=intent['asset'];side=intent['side'];qty=intent['quantity'];phase=intent['phase']
            if is_terminal or carried_risk:require(phase==('terminal' if is_terminal else 'risk_exit'),'prior_exit_priority')
            if not qty:require(n not in fill_by_id,'zero_fill');continue
            flags=rows[i].get('execution',{s:dict(suspended=None,buy_blocked=None,sell_blocked=None) for s in ASSETS})[a]
            require(set(flags)=={'suspended','buy_blocked','sell_blocked'} and all(v is None or type(v) is bool for v in flags.values()),'execution_flag_schema')
            if flags['suspended'] or flags[side+'_blocked']:
                require(n not in fill_by_id,'known_constraint_fill')
                rejects.append(dict(index=i,intent_id=n,reason='known_execution_constraint'));continue
            for flag in ('suspended',side+'_blocked'):
                require(flags[flag] is None or type(flags[flag]) is bool,'execution_flag_type')
                if flags[flag] is None:unknowns.append(dict(index=i,asset=a,flag=flag,intent_id=n))
            raw=open_marks[a];price=execution_price(raw,side,slip);notional=qty*price;commission=fee(qty,minimum)
            levy=(notional*D('.0005')).quantize(CENT,rounding=ROUND_CEILING) if side=='sell' else ZERO
            budget=None if intent['budget'] is None else decimal(intent['budget'])
            reason=None
            if price<=0:reason='nonpositive_adverse_price'
            elif side=='buy' and paused:reason='risk_cancelled_increase'
            elif side=='buy' and (notional+commission>budget or notional+commission>cash):reason='frozen_budget_or_spendable_cash'
            elif side=='sell' and qty>q[a]:reason='quantity_no_longer_available'
            elif side=='sell' and notional-commission-levy < -cash:reason='free_cash_insufficient_exit_fee'
            if side=='buy' and reason is None:
                exposure=sum((q[s]*open_marks[s] for s in ASSETS),ZERO)+qty*raw
                if exposure>nav(open_marks)-notional-commission+qty*raw:reason='marked_exposure_exceeds_NAV'
            if reason:
                require(n not in fill_by_id,'rejected_fill')
                rejects.append(dict(index=i,intent_id=n,reason=reason,actual_price=price,actual_notional=notional,fee=commission,levy=levy));continue
            require(n in fill_by_id,'recorded_valid_intent_missing_fill');b=balance();fifo=[]
            if side=='buy':
                cash-=notional+commission;q[a]+=qty
                lots[a].append(dict(index=i,initial=qty,remaining=qty,original_cost=notional+commission,remaining_cost=notional+commission))
            else:
                q[a]-=qty;net=notional-commission-levy
                if net>0:
                    locks.append(sale_lock(n,i,net,dates))
                else:cash+=net
                left=qty
                for lot in lots[a]:
                    take=min(left,lot['remaining'])
                    if not take:continue
                    released=lot['remaining_cost'] if take==lot['remaining'] else lot['remaining_cost']*take/lot['remaining']
                    lot['remaining']-=take;lot['remaining_cost']-=released;left-=take
                    fifo.append(dict(buy_index=lot['index'],quantity=take,released_cost=released))
                    if not left:break
                require(left==0,'fifo_inventory')
            slip_cost=qty*((price-raw) if side=='buy' else (raw-price))
            fees+=commission;levies+=levy;slippage_total+=slip_cost
            expected=dict(index=i,date=dates[i],intent_id=n,asset=a,side=side,quantity=qty,phase=phase,
                raw_open=raw,price=price,notional=notional,fee=commission,sell_levy=levy,slippage_cost=slip_cost,
                frozen_budget=budget,FIFO=fifo,before=b,after=balance(),
                observed_full_day_volume=None if is_terminal else decimal(rows[i]['prices'][a]['volume']),
                volume_observation_clock='unavailable_at_terminal_open' if is_terminal else 'after_completed_session_not_available_to_order')
            same(expected,fill_by_id[n],f'fill/{n}');today.append(expected)
            observe(i,open_marks,'post_fill_'+str(n))
        if is_terminal or carried_risk:risk_due=i+1 if any(q.values()) else None
        if not any(q.values()):risk_due=None
        marks=open_marks if is_terminal else {a:decimal(rows[i]['prices'][a]['close']) for a in ASSETS}
        value=observe(i,marks,'terminal_open_end' if is_terminal else 'completed_close')
        if not is_terminal and paused:
            cooldown=cooldown+1 if not day_active and not triggered and not any(q.values()) else 0
        parts=dict(carried_exposure=sum((prior_q[a]*(marks[a]-prior_marks[a]) for a in ASSETS),ZERO),
            trade_timing=sum(((f['quantity'] if f['side']=='buy' else -f['quantity'])*(marks[f['asset']]-f['raw_open']) for f in today),ZERO),
            net_dividend_entitlement=entitlement,commissions=-sum((f['fee'] for f in today),ZERO),
            sell_levies=-sum((f['sell_levy'] for f in today),ZERO),slippage=-sum((f['slippage_cost'] for f in today),ZERO))
        require(sum(parts.values(),ZERO)==value-previous,'daily_conservation')
        expected=dict(index=i,date=dates[i],terminal_open_only=is_terminal,before=before,after=balance(),
            previous_marks=prior_marks,marks=marks,previous_NAV=previous,NAV=value,PnL=value-previous,peak=peak,
            observed_maxDD=max_dd,paused=paused,cooldown=cooldown,risk_exit_due_index=risk_due,
            observation_range=[obs_start,len(observations)],attribution=parts)
        same(expected,day,f'day/{i}')
        annual[dates[i][:4]]=annual.get(dates[i][:4],ZERO)+(value-previous)
        for k in PARTS:parts_total[k]+=parts[k]
        previous=value
    for label,expected in [('actions',actions),('risk_observations',observations),('risk_records',risks),
            ('rejections',rejects),('unknown_execution_constraints',unknowns),('annual_contributions',annual),
            ('attribution',parts_total),('FIFO_lots',lots),('terminal_locks',locks),('terminal_receivable_items',receivables)]:
        same(expected,account[label],label)
    _verify_recorded_budgets(fixture,account)
    locked=sum((x['amount'] for x in locks),ZERO);unpaid=sum((x['amount'] for x in receivables.values()),ZERO)
    inventory=sum((q[a]*decimal(rows[-1]['prices'][a]['open']) for a in ASSETS),ZERO)
    elapsed=(date.fromisoformat(dates[-1])-date.fromisoformat(dates[first])).days
    summary=dict(initial_cash=D('1000'),terminal_book_NAV=previous,terminal_book_cash=cash+locked,
        terminal_spendable_cash=cash,terminal_locked_cash=locked,terminal_receivables=unpaid,terminal_inventory_value=inventory,
        terminal_quantities=q,terminal_book_net_profit=previous-1000,terminal_cash_only_net_profit=cash+locked-1000,
        terminal_spendable_cash_net_profit=cash-1000,
        terminal_cash_only_definition='includes contracted locked sale proceeds; excludes dividend receivables and remaining inventory; not immediately withdrawable cash',
        terminal_inventory_closed=not any(q.values()),terminal_fully_settled=not any(q.values()) and not locks and not receivables,
        observed_maxDD=max_dd,book_CAGR=(previous/1000)**(D('365.25')/elapsed)-1,CAGR_years=D(elapsed)/D('365.25'),
        total_commission=fees,total_sell_levy=levies,total_slippage=slippage_total,total_net_dividend=net_dividends,
        same_path_trading_cost_drag=fees+levies+slippage_total,same_path_before_trading_cost_net_profit=previous-1000+fees+levies+slippage_total,
        cost_headroom_meaning='accounting attribution on the same trades, not a fee-reoptimized portfolio',
        fills=len(fill_by_id),rejections=len(rejects),accounting_reconciled=True,qualified=False)
    same(summary,account['summary'],'summary')
    require(sum(annual.values(),ZERO)==previous-1000 and sum(parts_total.values(),ZERO)==previous-1000,'whole_conservation')
    return dict(status='recorded_account_consistent',days=len(account['days']),fills=len(fill_by_id),actions=len(actions),
        risk_observations=len(observations),summary=account['summary'],annual=account['annual_contributions'],
        signals_checked=len(signals),strategy_intent_replayed=False,qualified=False)


def _verify_recorded_budgets(fixture,account):
    dates=[r['date'] for r in fixture['days']];minimum=account['minimum_commission'];slip=account['slippage_bps']
    signal_map={s['index']:s for s in account['signals']}
    day_map={d['index']:d for d in account['days']}
    same(list(signal_map),[e['decision_index'] for e in account['monthly_events']],'monthly_event_coverage')
    for event in account['monthly_events']:
        i=event['decision_index'];same(signal_map[i],event['signal'],'event_signal');same(dates[i],event['date'],'event_date')
        same(account['policy'],event['policy'],'event_policy')
        if not event['targets']:continue
        same(i+1,event['sell_index'],'D1');same(i+3,event['plan_index'],'D3');same(i+4,event['buy_index'],'D4')
        require(set(event['targets'])==set(ASSETS) and all(type(q) is int and q>=0 for q in event['targets'].values()),'recorded_targets')
        if 'buy_planning_index' not in event:continue
        p=event['buy_planning_index'];same(i+3,p,'planning_clock')
        b=event['buy_planning_balances'];same(day_map[p]['after'],b,'planning_recorded_wallet')
        due=sum((decimal(x['amount']) for x in b['locks'] if x['release_index']<=p+1),ZERO)
        available=max(decimal(b['spendable_cash'])+due-10,ZERO)
        same(due,event['exact_next_open_due_cash'],'contracted_due_only');same(available,event['buy_available_after_buffer'],'spendable_budget')
        costs={};max_quantities={}
        for a in ASSETS:
            needed=min(max(event['targets'][a]-b['quantities'][a],0),capacity(fixture,a,p+1))
            price=execution_price(decimal(fixture['days'][p]['prices'][a]['close']),'buy',slip)
            max_quantities[a]=needed;costs[a]=needed*price+fee(needed,minimum) if needed else ZERO
        same(costs,event['planned_costs'],'planned_cost_arithmetic');total=sum(costs.values(),ZERO)
        # A risk observation can erase the event's pending list after some legs
        # were attempted. The immutable recorded intents still require each leg's
        # original independent budget; do not trust the surviving event list alone.
        recorded=[{k:v for k,v in x.items() if k!='intent_id'} for x in account['intents']
                  if x['phase']=='monthly_buy' and x['due_index']==event['buy_index']]
        for order in event['buy_orders']+recorded:
            a=order['asset'];budget=(available*costs[a]/total).quantize(CENT,rounding=ROUND_FLOOR) if total else ZERO
            same(budget,order['budget'],'independent_leg_budget')
            require(0<=order['quantity']<=max_quantities[a],'recorded_buy_bound')
            if order['quantity']:
                require(order['quantity']*decimal(order['planned_price'])+fee(order['quantity'],minimum)<=budget,'planned_leg_affordability')
    # Intent choice/completeness is deliberately not reconstructed.


def verify_statistics(annual, actual, evidence_kind, historical):
    import numpy as np
    with localcontext(CONTEXT):
        years=sorted(annual['min0.35_slip0']['rotation']);keys=[];columns=[]
        for m,s in COSTS:
            key=f'min{m}_slip{s}';group=annual[key]
            require(all(sorted(group[p])==years for p in POLICIES),'paired_years')
            for endpoint,baseline in (('net',None),('minus_positive_equal','positive_equal'),('minus_fixed_quarters','fixed_quarters')):
                keys.append(key+'/'+endpoint)
                columns.append([float(decimal(group['rotation'][y])-(decimal(group[baseline][y]) if baseline else ZERO)) for y in years])
        if len(years)!=19:
            same(dict(status='not_computed_requires19years',annual_years=years,qualified=False),actual,'statistics_short');return
        if historical:same([str(y) for y in range(2006,2025)],years,'historical_annual_years')
        matrix=np.asarray(columns,dtype='float64').T
        require(matrix.shape==(19,27) and bool(np.isfinite(matrix).all()),'statistics_matrix')
        rng=np.random.Generator(np.random.PCG64(20261107));means=np.empty((5000,27),dtype='float64')
        for n in range(5000):
            starts=rng.integers(0,19,size=10);indices=((starts[:,None]+np.arange(2))%19).reshape(-1)[:19]
            means[n]=matrix[indices].mean(axis=0)
        bounds=np.quantile(means,[.025,.975],axis=0,method='linear')
        expected=dict(status='computed_seen_trace_sensitivity',evidence_kind=evidence_kind,historical_returns_computed=historical,
            qualified=False,N=19,years=years,block=2,seed=20261107,generator='PCG64',replications=5000,starts_per_replication=10,
            truncate_rows_to=19,shared_indices_for_all27=True,endpoint_keys=keys,units='USD_per_observed_year',statistic='arithmetic_mean_annual_PnL',
            lower=dict(zip(keys,bounds[0].tolist())),upper=dict(zip(keys,bounds[1].tolist())),observed_means=dict(zip(keys,matrix.mean(axis=0).tolist())),
            quantiles=[.025,.975],quantile_method='linear',replicate_means_sha256=hashlib.sha256(means.astype('<f8').tobytes()).hexdigest(),numpy_version=np.__version__)
        same(expected,actual,'statistics')


def _bound(root, ref):
    require(type(ref) is dict and {'path','sha256'}<=set(ref),'artifact_ref')
    path=Path(ref['path']);path=(path if path.is_absolute() else root/path).resolve()
    require(path.is_relative_to(root),'artifact_outside_root')
    raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==ref['sha256'],'artifact_hash')
    if 'bytes' in ref:require(type(ref['bytes']) is int and ref['bytes']==len(raw),'artifact_size')
    return raw,path


def verify_recorded_accounts(root, decoded_ref, accounts, statistics_ref, registration_sha256):
    root=Path(root).resolve();refs=[decoded_ref,statistics_ref]
    decoded=json.loads(_bound(root,decoded_ref)[0]);fixture=decoded.get('fixture',decoded)
    if 'fixture' in decoded:
        require(set(decoded)=={'fixture','provenance'},'decoded_wrapper')
        same(fixture['provenance'],decoded['provenance'],'decoded_provenance')
    provenance=fixture['provenance'];kind=fixture['evidence_kind'];historical=kind=='known_history_conditional'
    require(kind in ('known_history_conditional','artificial_values_true_calendar','artificial'),'evidence_kind')
    if kind=='artificial':require(registration_sha256 is None,'artificial_no_registration')
    else:require(type(registration_sha256) is str and len(registration_sha256)==64
                 and all(c in '0123456789abcdef' for c in registration_sha256),'registration_hash')
    if historical:same(registration_sha256,provenance['registration_sha256'],'decoded_registration')
    identities=[(f'min{m}_slip{s}/{p}',p,m,s) for m,s in COSTS for p in POLICIES]+[('cash','cash','0.35',0)]
    same(set(k for k,_,_,_ in identities),set(accounts),'account_keys')
    results={};annual={};paths=[]
    for key,policy,minimum,slip in identities:
        wrapper=accounts[key];ref=wrapper['artifact'];refs.append(ref)
        if historical:require('completion' in wrapper,'historical_completion_marker_required')
        if 'completion' in wrapper:
            refs.append(wrapper['completion']);completion=json.loads(_bound(root,wrapper['completion'])[0])
            same('complete',completion['status'],'completion_status');same(key,completion['account_id'],'completion_identity')
            same(registration_sha256,completion['registration_sha256'],'completion_registration')
            same(ref,completion['artifact'],'completion_artifact')
        raw,path=_bound(root,ref);paths.append(str(path));account=json.loads(raw)
        for field,value in {'policy':policy,'minimum_commission':minimum,'slippage_bps':slip,'evidence_kind':kind,
                'historical_returns_computed':historical,'registration_sha256':registration_sha256}.items():
            same(value,account[field],'account_identity/'+field)
        same(account['summary'],wrapper['summary'],'indexed_summary')
        checked=verify_account(fixture,account);results[key]=checked
        if policy!='cash':annual.setdefault(f'min{minimum}_slip{slip}',{})[policy]=checked['annual']
    require(len(paths)==len(set(paths)),'account_artifacts_unique')
    stats=json.loads(_bound(root,statistics_ref)[0]);verify_statistics(annual,stats,kind,historical)
    primary=results['min1.00_slip10/rotation']['summary'];stress=results['min2.50_slip30/rotation']['summary']
    with localcontext(CONTEXT):
        checks={'primary_cash_profit_positive':decimal(primary['terminal_cash_only_net_profit'])>0,
            'primary_book_CAGR_at_least3percent':decimal(primary['book_CAGR'])>=D('.03'),
            'stress_cash_profit_positive':decimal(stress['terminal_cash_only_net_profit'])>0,
            'primary_DD_strictly_below40':decimal(primary['observed_maxDD'])<D('.40'),
            'stress_DD_strictly_below40':decimal(stress['observed_maxDD'])<D('.40'),
            'all_inventory_closed':all(v['summary']['terminal_inventory_closed'] for v in results.values()),
            'later2015_2024_primary_net_positive':sum((decimal(v) for y,v in annual['min1.00_slip10']['rotation'].items() if '2015'<=y<='2024'),ZERO)>0}
        increment=sum((decimal(v)-decimal(annual['min1.00_slip10']['positive_equal'][y]) for y,v in annual['min1.00_slip10']['rotation'].items()),ZERO)
    for ref in refs:_bound(root,ref)
    return dict(status='recorded_accounting_consistent',accounts_checked=28,days_checked=sum(v['days'] for v in results.values()),
        fills_checked=sum(v['fills'] for v in results.values()),action_records_checked=sum(v['actions'] for v in results.values()),
        risk_observations_checked=sum(v['risk_observations'] for v in results.values()),registration_sha256=registration_sha256,
        fixture_sha256=digest(fixture),summaries={k:v['summary'] for k,v in results.items()},annual_contributions={k:v['annual'] for k,v in results.items()},
        fixed_economic_checks=checks,all_fixed_economic_conditions_passed=all(checks.values()),
        ranking_increment_vs_positive_equal=str(increment),positive_ranking_increment_observed=increment>0,ranking_alpha_certified=False,
        strategy_intent_replayed=False,qualified=False,real_forward=0,
        limits=['Recorded arithmetic and signal/statistics formulas only; order-selection completeness not replayed',
                'No original source, execution, historical publication, broker tariff or personal tax certification',
                'Cash profit includes locked proceeds, excludes unpaid dividends; not immediately withdrawable cash'])
