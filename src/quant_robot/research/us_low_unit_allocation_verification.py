"""Independent ledger arithmetic for unit changes; no strategy or source I/O.

Uses prior independent verification primitives, never the production account.
Recorded quantities and actions are replayed; full strategy choice is not rerun.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal as D, localcontext, ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR
from quant_robot.research.us_monthly_rotation_verification import (
    CONTEXT, ZERO, CENT, require, decimal, same, digest, fee, execution_price, sale_lock,
)
PARTS=('carried_exposure','trade_timing','cash_in_lieu_timing','cash_in_lieu_cost',
       'net_dividend_entitlement','commissions','sell_levies','slippage')


def floor(value):
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


def capacity_money(fixture,symbol,before):
    require(before>=20,'twenty_prior_sessions')
    return sum((decimal(d['prices'][symbol]['close'])*decimal(d['capacity_volume'][symbol])
                for d in fixture['days'][before-20:before]),ZERO)/20*D('.01')


def ratio_on(fixture,symbol,index):
    day=fixture['days'][index]['date'];ratio=D(1)
    for event in fixture['splits']:
        if event['symbol']==symbol and event['effective_date']==day:
            require(event['numerator']==1 and event['denominator']==2,'fixed_ratio')
            ratio*=D('.5')
    return ratio


def capacity_details(fixture,symbol,due,side,slip):
    money=capacity_money(fixture,symbol,due)
    prior=decimal(fixture['days'][due-1]['prices'][symbol]['close'])
    planned=execution_price(prior,'buy',slip) if side=='buy' else prior
    ratio=ratio_on(fixture,symbol,due)
    return floor(D(floor(money/planned))*ratio),planned/ratio,planned/ratio,money


def dividend_item(symbol,quantity,amount,ex_date):
    require(type(quantity) is int and quantity>0,'dividend_quantity')
    gross=quantity*decimal(amount);net=(gross*D('.70')).quantize(CENT)
    return dict(symbol=symbol,quantity=quantity,gross=gross,amount=net,modeled_withholding=gross-net,
                earliest_payment_date=(date.fromisoformat(ex_date)+timedelta(days=45)).isoformat())


def verify_signals(fixture,actual):
    dates=[r['date'] for r in fixture['days']];first=dates.index(fixture['first_decision_date']);terminal=len(dates)-1
    expected=[dict(index=i,date=dates[i],weights={'fixed_quarters':dict.fromkeys(fixture['assets'],D('.25'))},
                   ordinary_execution_possible=i+4<terminal)
              for i in range(first,terminal) if dates[i][:7]!=dates[i+1][:7]]
    same(expected,actual,'fixed_calendar_signals')
    return expected


def verify_account(fixture,account,*,expected_method=None,expected_registration=None,expected_marker=None):
    with localcontext(CONTEXT):
        return _verify_account(fixture,account,expected_method=expected_method,
                               expected_registration=expected_registration,expected_marker=expected_marker)


def _verify_account(fixture, account, *, expected_method=None,expected_registration=None,expected_marker=None):
    ASSETS = tuple(fixture['assets'])
    require(ASSETS in (('SPY','EFA','IEF','GLD'), ('SPYM','EFA','IEF','GLDM')), 'asset_basket')
    same(list(ASSETS),fixture['assets'],'assets')
    same(expected_method,account['method_sha256'],'account_method')
    same(expected_registration,account['registration_sha256'],'account_registration')
    same(expected_marker,account['numeric_marker_sha256'],'account_numeric_marker')
    same(digest(fixture),account['fixture_sha256'],'fixture_hash')
    kind = 'known_history_conditional' if fixture['provenance']['constructed_from_market_data'] else 'artificial'
    same(kind,account['evidence_kind'],'evidence_kind')
    same(kind=='known_history_conditional',account['historical_returns_computed'],'historical_identity')
    same(kind=='artificial',account['test_injected_values'],'test_identity')
    same(kind=='known_history_conditional',fixture['provenance']['constructed_from_market_data'],'market_identity')
    same(False,account['qualified'],'qualified');same(0,account['real_forward'],'forward')
    policy,minimum,slip=account['policy'],account['minimum_commission'],account['slippage_bps']
    role=account['role']
    require(role in ('old_primary','old_stress','new_primary','new_stress','cash'),'role')
    same(('SPYM','EFA','IEF','GLDM') if role.startswith('new_') else ('SPY','EFA','IEF','GLD'),
         ASSETS,'role_asset_basket')
    expected_cost=('0.35',0) if role=='cash' else ('2.50',30) if role.endswith('stress') else ('1.00',10)
    same(expected_cost,(minimum,slip),'fixed_role_cost')
    same('cash' if role=='cash' else 'fixed_quarters',policy,'fixed_policy')
    same(list(ASSETS),account['assets'],'account_assets')
    same(f'min{minimum}_slip{slip}',account['cost_id'],'cost_id')
    same('.005',account['commission_per_share'],'commission_per_share');same('5',account['sell_levy_bps'],'levy_rate')
    initial_context=dict(prec=40,rounding=ROUND_HALF_UP,Emin=-999999,Emax=999999,capitals=1,clamp=0,
        traps={k.__name__:v for k,v in CONTEXT.traps.items()},flags={k.__name__:False for k in CONTEXT.flags})
    same(initial_context,account['runtime_context']['initial'],'runtime_context')
    final=account['runtime_context']['final']
    same({k:v for k,v in initial_context.items() if k!='flags'},{k:v for k,v in final.items() if k!='flags'},'final_context')
    require(set(final['flags'])==set(initial_context['flags']) and all(type(v) is bool for v in final['flags'].values()),'final_flags')
    dates=[d['date'] for d in fixture['days']];rows=fixture['days'];terminal=len(dates)-1
    require(dates==sorted(set(dates)) and dates[-1]==fixture['terminal_date'],'calendar')
    first=dates.index(fixture['first_decision_date'])
    require(first>=20 and first+4<terminal,'warmup_execution_dates')
    if kind=='known_history_conditional':
        same(('2020-12-01','2020-12-31','2025-12-31'),
             (dates[0],dates[first],dates[-1]),'fixed_history_window')
    signals=verify_signals(fixture,account['signals'])
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
        cap, cap_price, planned, cap_money = capacity_details(fixture,a,i,side,slip)
        same(cap,intent['capacity'],'prior_capacity')
        same(cap_money,intent['capacity_notional'],'prior_nominal_capacity')
        same(cap_price,intent['capacity_reference_price'],'capacity_reference_price')
        require(q<=intent['capacity'] and intent['planned_index']==i-1,'intent_causal_bound')
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
    annual={};parts_total=dict.fromkeys(PARTS,ZERO);fees=levies=slippage_total=net_dividends=cil_total=ZERO
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
        split_factors=dict.fromkeys(ASSETS,D(1));cil_today=[]
        for item in list(locks):
            if item['release_index']<=i:
                b=balance();cash+=item['amount'];locks.remove(item)
                actions.append(dict(index=i,kind='sale_cash_release',item=item,before=b,after=balance()))
        for key,item in list(receivables.items()):
            if item['earliest_payment_date']<=dates[i]:
                b=balance();cash+=item['amount'];del receivables[key]
                actions.append(dict(index=i,kind='cash_in_lieu_payment' if item.get('kind')=='cash_in_lieu' else 'dividend_payment',id=key,item=item,before=b,after=balance()))
        for event in fixture['splits']:
            if event['effective_date'] != dates[i]: continue
            a=event['symbol'];require(a=='GLDM' and event['numerator']==1 and event['denominator']==2,'known_split')
            ratio=D('.5');b=balance();right=D(q[a])*ratio;whole=int(right.to_integral_value(rounding=ROUND_FLOOR));fraction=right-whole
            split_factors[a]=ratio;q[a]=whole
            for lot in lots[a]:
                lot['initial']=decimal(lot['initial'])*ratio;lot['remaining']=decimal(lot['remaining'])*ratio
            left=fraction;released=ZERO;fifo=[]
            for lot in lots[a]:
                take=min(left,lot['remaining'])
                if not take:continue
                cost=lot['remaining_cost'] if take==lot['remaining'] else lot['remaining_cost']*take/lot['remaining']
                lot['remaining']-=take;lot['remaining_cost']-=cost;left-=take;released+=cost
                fifo.append(dict(buy_index=lot['index'],quantity=take,released_cost=cost))
                if not left:break
            require(left==0 and sum((x['remaining'] for x in lots[a]),ZERO)==whole,'split_FIFO')
            matches=[x for x in account['actions'] if x['kind']=='reverse_split_cash_in_lieu' and x['index']==i]
            require(len(matches)==1,'split_action_required')
            pending_before=matches[0]['item']['pending_before'];pending_after=deepcopy(pending_before)
            if pending_after:
                if a in pending_after['targets']:pending_after['targets'][a]=int((D(pending_after['targets'][a])*ratio).to_integral_value(rounding=ROUND_FLOOR))
                for key in ('sell_orders','buy_orders'):
                    for order in pending_after.get(key,[]):
                        if order['asset']!=a:continue
                        order['quantity']=int((D(order['quantity'])*ratio).to_integral_value(rounding=ROUND_FLOOR))
                        order['capacity']=int((D(order['capacity'])*ratio).to_integral_value(rounding=ROUND_FLOOR))
                        order['planned_price']=decimal(order['planned_price'])/ratio
                        if 'capacity_reference_price' in order:order['capacity_reference_price']=decimal(order['capacity_reference_price'])/ratio
                        order['split_adjusted_at']=i
            same(pending_after,matches[0]['item']['pending_after'],'pending_split_transition')
            raw=open_marks[a];price=execution_price(raw,'sell',slip);gross=fraction*price
            commission=fee(fraction,minimum) if fraction else ZERO
            levy=(gross*D('.0005')).quantize(CENT,rounding=ROUND_CEILING) if fraction else ZERO
            net=max(ZERO,gross-commission-levy).quantize(CENT,rounding=ROUND_FLOOR);cost=fraction*raw-net;cil_total+=cost
            delay=90 if role.endswith('stress') else 45
            record=dict(index=i,id=event['id'],asset=a,ratio=ratio,old_quantity=b['quantities'][a],total_right=right,
                whole_quantity=whole,fractional_right=fraction,raw_open=raw,modeled_price=price,modeled_gross=gross,
                assessed_fee=commission,assessed_levy=levy,modeled_net=net,NAV_cost=cost,
                assessed_cost_above_gross=max(ZERO,commission+levy-gross),FIFO=fifo,released_fraction_cost=released,
                payment_delay_calendar_days=delay,pending_before=pending_before,pending_after=pending_after)
            if fraction:
                key='cil:'+event['id'];payment=(date.fromisoformat(dates[i])+timedelta(days=delay)).isoformat()
                require(key not in receivables,'unique_CIL')
                receivables[key]=dict(kind='cash_in_lieu',symbol=a,amount=net,fractional_right=fraction,
                    earliest_payment_date=payment,valuation_clock='effective_session_open',official_payment_verified=False)
                record.update(receivable_id=key,earliest_payment_date=payment)
            cil_today.append(record)
            actions.append(dict(index=i,kind='reverse_split_cash_in_lieu',item=record,before=b,after=balance()))
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
            elif qty*raw>decimal(intent['capacity_notional']):reason='frozen_nominal_capacity'
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
        parts=dict(carried_exposure=sum((prior_q[a]*(split_factors[a]*marks[a]-prior_marks[a]) for a in ASSETS),ZERO),
            cash_in_lieu_timing=-sum((x['fractional_right']*(marks[x['asset']]-x['raw_open']) for x in cil_today),ZERO),
            cash_in_lieu_cost=-sum((x['NAV_cost'] for x in cil_today),ZERO),
            trade_timing=sum(((f['quantity'] if f['side']=='buy' else -f['quantity'])*(marks[f['asset']]-f['raw_open']) for f in today),ZERO),
            net_dividend_entitlement=entitlement,commissions=-sum((f['fee'] for f in today),ZERO),
            sell_levies=-sum((f['sell_levy'] for f in today),ZERO),slippage=-sum((f['slippage_cost'] for f in today),ZERO))
        require(sum(parts.values(),ZERO)==value-previous,'daily_conservation')
        expected=dict(index=i,date=dates[i],terminal_open_only=is_terminal,before=before,after=balance(),
            previous_marks=prior_marks,marks=marks,previous_NAV=previous,NAV=value,PnL=value-previous,peak=peak,split_factors=split_factors,
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
    same(None,account['pending'],'terminal_pending_cleared')
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
    summary.update(total_cash_in_lieu_cost=cil_total,terminal_settled_cash=cash,strict_available_cash=cash,
        terminal_dividend_receivable=sum((x['amount'] for x in receivables.values() if x.get('kind')!='cash_in_lieu'),ZERO),
        terminal_cash_in_lieu_receivable=sum((x['amount'] for x in receivables.values() if x.get('kind')=='cash_in_lieu'),ZERO),
        cash_and_locked_sale_proceeds_net_profit=cash+locked-1000,withdrawal_clock_verified=False,
        same_path_total_execution_cost=fees+levies+slippage_total+cil_total,
        average_cash_and_locked_ratio=sum(((decimal(d['after']['spendable_cash'])+decimal(d['after']['locked_cash']))/decimal(d['NAV']) for d in account['days']),ZERO)/len(account['days']),
        average_market_deployment_ratio=sum((sum((d['after']['quantities'][a]*decimal(d['marks'][a]) for a in ASSETS),ZERO)/decimal(d['NAV']) for d in account['days']),ZERO)/len(account['days']),
        asset_unheld_days={a:sum(d['after']['quantities'][a]==0 for d in account['days']) for a in ASSETS},
        zero_target_legs=sum(n==0 for e in account['monthly_events'] for n in e['targets'].values()),
        cash_in_lieu_scenario='effective_open_adverse_net_nonnegative_'+str(90 if role.endswith('stress') else 45)+'_calendar_days')
    same(summary,account['summary'],'summary')
    require(sum(annual.values(),ZERO)==previous-1000 and sum(parts_total.values(),ZERO)==previous-1000,'whole_conservation')
    return dict(status='recorded_account_consistent',days=len(account['days']),fills=len(fill_by_id),actions=len(actions),
        risk_observations=len(observations),summary=account['summary'],annual=account['annual_contributions'],
        signals_checked=len(signals),recorded_fixed_order_coverage_checked=True,
        strategy_intent_replayed=False,qualified=False)




def _verify_recorded_budgets(fixture,account):
    assets=tuple(fixture['assets']);dates=[r['date'] for r in fixture['days']]
    minimum,slip=account['minimum_commission'],account['slippage_bps']
    signal_map={s['index']:s for s in account['signals']};day_map={d['index']:d for d in account['days']}
    same(list(signal_map),[e['decision_index'] for e in account['monthly_events']],'monthly_event_coverage')
    splits=[a for a in account['actions'] if a['kind']=='reverse_split_cash_in_lieu']
    plans={}
    for event in account['monthly_events']:
        i=event['decision_index'];same(signal_map[i],event['signal'],'event_signal');same(dates[i],event['date'],'event_date')
        same(account['policy'],event['policy'],'event_policy')
        paused=day_map.get(i,{}).get('paused',False);risk_due=day_map.get(i,{}).get('risk_exit_due_index')
        skipped=account['policy']=='cash' or paused or risk_due is not None or not signal_map[i]['ordinary_execution_possible']
        same(skipped,not bool(event['targets']),'fixed_decision_eligibility')
        if skipped:
            same([],event['sell_orders'],'skipped_sell_orders')
            same([],event['buy_orders'],'skipped_buy_orders')
            require('buy_planning_index' not in event,'skipped_buy_planning')
            continue
        same(i+1,event['sell_index'],'D1');same(i+3,event['plan_index'],'D3');same(i+4,event['buy_index'],'D4')
        nav=decimal(day_map[i]['NAV']) if i in day_map else D(1000)
        same(nav,event['decision_NAV'],'decision_NAV')
        wallet=day_map[i]['after'] if i in day_map else dict(spendable_cash=D(1000),locked_cash=ZERO,
            locks=[],quantities=dict.fromkeys(assets,0),receivables={})
        same(wallet,event['pre_decision_balances'],'decision_wallet')
        targets={a:floor(max(nav-10,ZERO)*D('.25')/decimal(fixture['days'][i]['prices'][a]['close'])) for a in assets}
        sell_orders=[]
        for a in assets:
            price=decimal(fixture['days'][i]['prices'][a]['close']);money=capacity_money(fixture,a,i+1)
            cap=floor(money/price)
            sell_orders.append(dict(asset=a,side='sell',quantity=min(max(wallet['quantities'][a]-targets[a],0),cap),
                capacity=cap,capacity_notional=money,capacity_reference_price=price,planned_price=price,
                phase='monthly_sell',budget=None,planned_index=i,due_index=i+1))
        plans[i]=dict(event=event,targets=targets.copy(),sell_orders=sell_orders,buy_orders=[],planned=False)
        applicable=[x for x in splits if x['item']['pending_before'] and x['item']['pending_before'].get('decision_index')==i]
        final_targets=targets.copy()
        for action in applicable:
            a=action['item']['asset'];final_targets[a]=floor(D(final_targets[a])*decimal(action['item']['ratio']))
        same(final_targets,event['targets'],'fixed_quarter_targets')
        if 'buy_planning_index' not in event:continue
        p=event['buy_planning_index'];same(i+3,p,'planning_clock')
        wallet=event['buy_planning_balances'];same(day_map[p]['after'],wallet,'planning_wallet')
        due=sum((decimal(x['amount']) for x in wallet['locks'] if x['release_index']<=p+1),ZERO)
        available=max(decimal(wallet['spendable_cash'])+due-10,ZERO)
        same(due,event['exact_next_open_due_cash'],'contracted_cash_only');same(available,event['buy_available_after_buffer'],'available_budget')
        target_at_plan=targets.copy()
        for action in applicable:
            if action['index']<=p:
                a=action['item']['asset'];target_at_plan[a]=floor(D(target_at_plan[a])*decimal(action['item']['ratio']))
        costs={};needs={};prices={};caps={}
        for a in assets:
            raw=decimal(fixture['days'][p]['prices'][a]['close']);money=capacity_money(fixture,a,p+1)
            needs[a]=min(max(target_at_plan[a]-wallet['quantities'][a],0),floor(money/raw))
            prices[a]=execution_price(raw,'buy',slip);caps[a]=floor(money/prices[a])
            costs[a]=needs[a]*prices[a]+fee(needs[a],minimum) if needs[a] else ZERO
        same(costs,event['planned_costs'],'planned_costs');total=sum(costs.values(),ZERO)
        expected_buys=[]
        for a in assets:
            budget=(available*costs[a]/total).quantize(CENT,rounding=ROUND_FLOOR) if total else ZERO
            qty=min(needs[a],caps[a],floor(budget/prices[a]))
            while qty and qty*prices[a]+fee(qty,minimum)>budget:qty-=1
            expected_buys.append(dict(asset=a,side='buy',quantity=qty,capacity=caps[a],
                capacity_notional=capacity_money(fixture,a,p+1),capacity_reference_price=prices[a],planned_price=prices[a],
                phase='monthly_buy',budget=budget,planned_index=p,due_index=p+1))
        plans[i]['frozen_buys']=expected_buys
    _verify_order_coverage(fixture,account,plans)


def _verify_order_coverage(fixture,account,plans):
    """Check mandatory recorded intents from already verified balances and risk.

    This does not call the strategy, choose assets or generate a second account.
    A pre-open risk cancellation removes the buy list before iteration. A risk
    trigger inside the buy iteration clears its saved list, but all four frozen
    intents still belong to that iteration and must be recorded/rejected.
    """
    assets=tuple(fixture['assets']);rows=fixture['days'];dates=[r['date'] for r in rows]
    first=dates.index(fixture['first_decision_date']);terminal=len(dates)-1
    days={d['index']:d for d in account['days']};by_day=defaultdict(list)
    for intent in account['intents']:by_day[intent['due_index']].append(intent)
    split_map=defaultdict(list)
    for action in account['actions']:
        if action['kind']=='reverse_split_cash_in_lieu':split_map[action['index']].append(action)
    live=plans.get(first);next_intent=0

    def adjust(plan,action):
        if plan is None:return
        item=action['item'];a=item['asset'];ratio=decimal(item['ratio']);index=action['index']
        before=item['pending_before']
        require(type(before) is dict,'split_pending_identity')
        same(plan['event']['decision_index'],before['decision_index'],'split_pending_decision')
        for key in ('targets','sell_orders','buy_orders'):same(plan[key],before[key],'split_pending_before/'+key)
        plan['targets'][a]=floor(D(plan['targets'][a])*ratio)
        for key in ('sell_orders','buy_orders'):
            for order in plan[key]:
                if order['asset']!=a:continue
                order['quantity']=floor(D(order['quantity'])*ratio)
                order['capacity']=floor(D(order['capacity'])*ratio)
                order['planned_price']/=ratio;order['capacity_reference_price']/=ratio
                order['split_adjusted_at']=index
        for key in ('targets','sell_orders','buy_orders'):same(plan[key],item['pending_after'][key],'split_pending_after/'+key)

    for i in range(first+1,terminal+1):
        day=days[i]
        observed=account['risk_observations'][day['observation_range'][0]:day['observation_range'][1]]
        require(observed and observed[0]['phase']=='prior_held_open','first_open_observation')
        if i==first+1:prior_risk=None
        else:prior_risk=days[i-1]['risk_exit_due_index']
        carried=prior_risk is not None and prior_risk<=i
        for action in split_map[i]:
            if live is None:same(None,action['item']['pending_before'],'no_pending_at_split')
            adjust(live,action)
        if live is not None and observed[0]['trigger']:live['buy_orders']=[]
        expected=[]
        if i==terminal or carried:
            live=None
            phase='terminal' if i==terminal else 'risk_exit'
            holdings=observed[0]['balances']['quantities']
            for a in assets:
                # Exit orders are created after the mechanical split transition.
                price=decimal(rows[i-1]['prices'][a]['close'])/ratio_on(fixture,a,i)
                money=capacity_money(fixture,a,i);cap=floor(money/price)
                expected.append(dict(asset=a,side='sell',quantity=min(holdings[a],cap),capacity=cap,
                    capacity_notional=money,capacity_reference_price=price,planned_price=price,
                    phase=phase,budget=None,planned_index=i-1,due_index=i))
        elif live is not None:
            event=live['event']
            if i==event['sell_index']:expected=deepcopy(live['sell_orders'])
            if i==event['buy_index']:expected=deepcopy(live['buy_orders'])
        actual=by_day[i]
        require(len(actual)==len(expected),'fixed_order_count')
        for order,intent in zip(expected,actual):
            same(dict(order,intent_id=next_intent),intent,'fixed_order_intent')
            next_intent+=1
        if live is not None:
            if any(o['trigger'] for o in observed[1:-1]):live['buy_orders']=[]
            if i==live['event']['buy_index']:live=None
        if live is not None and observed[-1]['trigger']:live['buy_orders']=[]
        if live is not None and i==live['event']['plan_index']:
            can_plan=not day['paused'] and day['risk_exit_due_index'] is None
            same(can_plan,'buy_planning_index' in live['event'],'buy_planning_presence')
            if can_plan:
                live['buy_orders']=deepcopy(live['frozen_buys']);live['planned']=True
        if i in plans:
            require(live is None,'monthly_plan_overlap')
            live=plans[i]
    same(len(account['intents']),next_intent,'all_intents_covered')
    for plan in plans.values():
        same(plan['planned'],'buy_planning_index' in plan['event'],'reachable_planning_only')
        for key in ('targets','sell_orders','buy_orders'):same(plan[key],plan['event'][key],'final_month_event/'+key)
