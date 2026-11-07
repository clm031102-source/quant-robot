"""Complete finite synthetic event driver. No files, network or historical admission.

The accepted domain is explicitly fabricated 2001 UTC fixtures. Funding events
and transfer acknowledgements are supplied facts, never inferred zeros or fills.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, FundingChargeEvent, MINUTE, TradingRule, dec, stamp
from quant_robot.research.crypto_carry_policy import (
    CompletedPrices, KnownPoint, OHLCMinute, VolumeMinute, WalletState, minute_risk_envelope,
)
from quant_robot.research.crypto_carry_scheduler import CompletedPrefix, SyntheticCarryScheduler, TransferConfirmation

D = Decimal
DAY = timedelta(days=1)
YEAR_START = datetime(2001, 1, 1, tzinfo=timezone.utc)
YEAR_END = datetime(2002, 1, 1, tzinfo=timezone.utc)
DEMO_START = YEAR_START + DAY
MARKETS = ('spot', 'um', 'mark')
PRIMARY_FEES = FeeScenario('.0015', '.00075', '.0005')


@dataclass(frozen=True)
class SyntheticBar:
    market: str
    candle: OHLCMinute
    volume_btc: Decimal | None
    time_unit: str = 'UTC_datetime'
    price_unit: str = 'USDT_per_BTC'
    volume_unit: str = 'BTC'


@dataclass(frozen=True)
class SyntheticFunding:
    """Facts available at at; optional spot is a strategy-known synchronous quote.

None means unobserved spot, not an assertion that the preceding opening still
holds. The funding mark never becomes a new perpetual execution quote.
    """
    at: datetime
    received_at: datetime
    rate: Decimal | None
    mark: Decimal | None
    synchronous_spot: Decimal | None
    rate_unit: str = 'fraction_per_event'
    price_unit: str = 'USDT_per_BTC'


@dataclass(frozen=True)
class SyntheticDataset:
    start: datetime
    end: datetime
    bars: tuple[SyntheticBar, ...]
    funding: tuple[SyntheticFunding, ...]
    confirmations: tuple[TransferConfirmation, ...]
    spot_cash: Decimal = D('600')
    futures_cash: Decimal = D('400')
    synthetic_only: bool = True
    initial_warmup_policy: str = 'twenty_or_absent_cancel_first_day'


def funding_schedule(start, end):
    events = [start + DAY*day + timedelta(hours=hour)
              for day in range((end-start).days) for hour in (0,8,16)]
    return tuple(sorted(events + [start+9*MINUTE, start+9*MINUTE+timedelta(milliseconds=15)]))


def audit_dataset(data: SyntheticDataset):
    """Coverage facts precede account creation. Failure never fills missing data."""
    errors = []
    try:
        start, end = stamp(data.start), stamp(data.end)
        if (data.synthetic_only is not True or not YEAR_START <= start < end <= YEAR_END
                or (start.hour,start.minute,start.second,start.microsecond)!=(0,0,0,0)
                or (end.hour,end.minute,end.second,end.microsecond)!=(0,0,0,0)
                or end-start != 2*DAY):
            errors.append('exact_two_day_fabricated_2001_scope_required')
        if data.initial_warmup_policy != 'twenty_or_absent_cancel_first_day':
            errors.append('warmup_policy_changed')
        if min(dec(data.spot_cash),dec(data.futures_cash)) < 0 or dec(data.spot_cash)+dec(data.futures_cash)!=1000:
            errors.append('initial_wallet_budget_mismatch')
        indexed = {market:{} for market in MARKETS}
        for bar in data.bars:
            if not isinstance(bar,SyntheticBar) or bar.market not in indexed:
                errors.append('unknown_bar_market'); continue
            c=bar.candle
            if not isinstance(c,OHLCMinute):
                errors.append('missing_ohlc_fields'); continue
            if (bar.time_unit,bar.price_unit,bar.volume_unit)!=('UTC_datetime','USDT_per_BTC','BTC'):
                errors.append('bar_units_mismatch')
            if not YEAR_START<=c.start<end or not start-20*MINUTE<=c.start or c.end>end:
                errors.append('bar_outside_scope')
            if c.received_at!=c.end:
                errors.append('synchronous_synthetic_close_receipt_required')
            if c.start in indexed[bar.market]: errors.append('duplicate_minute')
            indexed[bar.market][c.start]=bar
            if bar.market=='mark':
                if bar.volume_btc is not None: errors.append('mark_volume_must_not_supply_capacity')
            elif bar.volume_btc is None or dec(bar.volume_btc)<0:
                errors.append('missing_or_negative_volume')
        expected={start+i*MINUTE for i in range(2880)}
        warmup={start-i*MINUTE for i in range(1,21)}
        warmup_sets=[]
        for market,rows in indexed.items():
            if {at for at in rows if at>=start} != expected: errors.append('missing_or_extra_required_minute:'+market)
            before={at for at in rows if at<start}
            if before not in (set(),warmup): errors.append('partial_warmup:'+market)
            warmup_sets.append(before)
        if any(rows!=warmup_sets[0] for rows in warmup_sets): errors.append('warmup_market_alignment')
        expected_funding=funding_schedule(start,end)
        actual=[]
        for event in data.funding:
            if not isinstance(event,SyntheticFunding): errors.append('missing_funding_fields'); continue
            at=stamp(event.at); actual.append(at)
            if not start<=at<end: errors.append('funding_outside_scope')
            if event.received_at!=at: errors.append('synchronous_synthetic_funding_receipt_required')
            if (event.rate_unit,event.price_unit)!=('fraction_per_event','USDT_per_BTC'):
                errors.append('funding_units_mismatch')
            if event.rate is None or event.mark is None: errors.append('missing_funding_rate_or_mark'); continue
            dec(event.rate)
            if dec(event.mark)<=0: errors.append('nonpositive_event_mark')
            bar_start=at.replace(second=0,microsecond=0)
            mark=indexed['mark'].get(bar_start)
            spot=indexed['spot'].get(bar_start)
            if mark and not mark.candle.low<=dec(event.mark)<=mark.candle.high:
                errors.append('event_mark_outside_declared_ohlc')
            if event.synchronous_spot is not None:
                value=dec(event.synchronous_spot)
                if value<=0 or spot and not spot.candle.low<=value<=spot.candle.high:
                    errors.append('event_spot_outside_declared_ohlc')
        if tuple(actual)!=expected_funding: errors.append('funding_schedule_missing_duplicate_or_unordered')
        dues=[]
        for receipt in data.confirmations:
            if not isinstance(receipt,TransferConfirmation): errors.append('confirmation_schema'); continue
            dues.append(receipt.due_at)
            if not start<receipt.due_at<end or receipt.received_at!=receipt.due_at:
                errors.append('confirmation_scope_or_time')
        if dues!=sorted(set(dues)): errors.append('confirmation_duplicate_or_unordered')
    except (ValueError,TypeError,AttributeError,ArithmeticError):
        errors.append('invalid_required_numeric_or_clock_field')
    return {'status':'blocked' if errors else 'complete', 'errors':sorted(set(errors)),
        'required_span_minutes':2880,'markets':MARKETS,'warmup_minutes':
        len(warmup_sets[0]) if not errors else None,'synthetic_only':True,
        'qualified':False,'real_forward':0}


def _wallet(row):
    return WalletState(row.at,row.event+':'+row.stage,row.spot_cash,row.futures_cash,
        row.spot_btc,row.short_btc,row.entry_vwap,row.in_transit,row.global_peak,row.daily_reference)


def audit_minute(*, rows, spot, mark, funding):
    """All immutable event-before/after states, plus explicitly synchronous points."""
    start,end=spot.start,spot.end
    rows=[row for row in rows if start<=row.at<end and row.event not in {'completed_close','day_end'}]
    if not rows or rows[0].at!=start or rows[0].event!='quote' or rows[0].stage!='before':
        raise ValueError('minute_start_wallet_trace_missing')
    states=tuple(_wallet(row) for row in rows)
    points=[]
    for index,row in enumerate(rows):
        event=funding.get(row.at)
        # No stale opening spot is paired with a midminute funding mark.
        if event is not None and row.event!='quote':
            # A charge-associated basis is never a market observation, even if
            # its numeric value happens to equal the latest independent mark.
            if not isinstance(event, FundingChargeEvent) and event.synchronous_spot is not None:
                points.append(KnownPoint(row.at,index,event.synchronous_spot,event.mark))
        elif row.at==start:
            points.append(KnownPoint(row.at,index,spot.open,mark.open))
    points.append(KnownPoint(end,len(states)-1,spot.close,mark.close))
    result=minute_risk_envelope(states=states,spot=spot,mark=mark,evaluated_at=end,
                               known_points=points,coverage_complete=True)
    return {'start':start.isoformat(),'end':end.isoformat(),'state_count':len(states),
            'known_point_count':len(points),'known_points':tuple(asdict(point) for point in points),
            'envelope':asdict(result)}


def run_synthetic_driver(data: SyntheticDataset):
    coverage=audit_dataset(data)
    base={'synthetic_only':True,'qualified':False,'real_forward':0,'historical_returns_computed':False,
          'real_market_files_read':0,'network_requests':0,'coverage':coverage}
    if coverage['status']!='complete':
        return {**base,'status':'blocked_input_coverage','reason':coverage['errors'],
                'economic_exercise_complete':False,'account_created':False}
    indexed={market:{bar.candle.start:bar for bar in data.bars if bar.market==market} for market in MARKETS}
    funding={event.at:event for event in data.funding}
    receipts={receipt.due_at:receipt for receipt in data.confirmations}
    model=CarryModel(start=data.start,spot_rule=TradingRule('.001','.001','10'),
        futures_rule=TradingRule('.001','.001','10'),fees=PRIMARY_FEES,
        spot_cash=data.spot_cash,futures_cash=data.futures_cash,audit_event_states=True)
    scheduler=SyntheticCarryScheduler(model)
    for event in data.funding:
        scheduler.queue_funding(event.at,rate=event.rate,mark=event.mark,synchronous_spot=event.synchronous_spot)
    for day in (1,2): scheduler.queue_day_end(data.start+day*DAY)
    cursor=0; trace=[]; by_minute={}; envelope_rows=[]; consumed=[]; blocked=None
    terminal_at=data.end-DAY+timedelta(hours=22)
    for minute in range(2881):
        at=data.start+minute*MINUTE
        if at<data.end:
            scheduler.queue_opening(at,spot=indexed['spot'][at].candle.open,
                future=indexed['um'][at].candle.open,mark=indexed['mark'][at].candle.open)
        prior=at-MINUTE
        prices=None; completed=None
        if prior in indexed['spot'] and prior in indexed['um'] and prior in indexed['mark']:
            prices=CompletedPrices(at,at,indexed['spot'][prior].candle.close,
                                   indexed['um'][prior].candle.close,indexed['mark'][prior].candle.close)
            starts=[at-(20-i)*MINUTE for i in range(20)]
            if all(t in indexed['spot'] and t in indexed['um'] for t in starts):
                volumes=tuple(tuple(VolumeMinute(t+MINUTE,t+MINUTE,indexed[market][t].volume_btc)
                              for t in starts) for market in ('spot','um'))
                completed=CompletedPrefix(prices,*volumes)
        receipt=receipts.get(at)
        transfer=model.transfer
        if transfer is not None and transfer.due==at and receipt is None:
            blocked='missing_explicit_transfer_confirmation'; break
        if receipt is not None and (transfer is None or transfer.due!=at or transfer.source!=receipt.source or transfer.amount!=receipt.amount):
            blocked='unexpected_or_mismatched_transfer_confirmation'; break
        result=scheduler.advance(at,prefix=completed,completed_prices=prices if completed is None else None,
                                 confirmation=receipt,terminal_intent=at==terminal_at)
        if result['status']=='blocked': blocked=result['reason']; break
        if receipt is not None: consumed.append(at)
        cursor,new=model.audit_states_since(cursor)
        trace.extend(new)
        for row in new:
            key=row.at.replace(second=0,microsecond=0)
            by_minute.setdefault(key,[]).append(row)
        if minute:
            envelope_rows.append(audit_minute(rows=by_minute.get(prior,[]),
                spot=indexed['spot'][prior].candle,mark=indexed['mark'][prior].candle,funding=funding))
    # Midminute events are advanced by the next boundary call. Their exact clocks
    # stay in the kernel, and their states remain attached to the preceding bar.
    counts=Counter(row['envelope']['status'] for row in envelope_rows)
    fills=[row for row in model.journal if row['event']=='leg_filled']
    cash_events=[row for row in model.journal if row['event']=='funding']
    daily=[row for row in model.journal if row['event']=='day_end']
    exact_event_coverage=tuple(datetime.fromisoformat(row['time']) for row in cash_events)==tuple(funding)
    economic=(blocked is None and len(daily)==2 and len(envelope_rows)==2880 and exact_event_coverage
        and len(consumed)==len(receipts) and len(fills)>=4 and model.fees_quote>0
        and any(dec(row['cash_delta'])!=0 for row in cash_events)
        and {'spot_buy','short_open','short_close','spot_sell'}<={row['side'] for row in fills})
    terminal=model.finish() if blocked is None else None
    if terminal is not None and terminal['terminal_unsettled']: economic=False
    status=('blocked_execution' if blocked else 'incomplete_economic_exercise' if not economic else
            'completed_with_confirmed_breach' if counts['confirmed_breach'] else
            'completed_with_unresolved_path' if counts['unresolved_path'] else 'completed_synthetic_exercise')
    return {**base,'status':status,'reason':blocked,'account_created':True,'economic_exercise_complete':economic,
        'single_continuous_account':True,'initial_cash':str(data.spot_cash+data.futures_cash),
        'terminal_trigger_at':terminal_at.isoformat(),'final_processing_at':model.now.isoformat(),
        'source_bar_end_exclusive':data.end.isoformat(),'next_interval_opening_or_funding_consumed':False,
        'processed_minutes':len(envelope_rows),'funding_event_coverage_complete':exact_event_coverage,
        'confirmed_transfer_count':len(consumed),'fill_count':len(fills),'envelope_status_counts':dict(counts),
        'daily_nav':daily,'terminal':terminal,'kernel':model.snapshot(),'envelopes':envelope_rows,
        'event_states':tuple(asdict(row) for row in trace),'kernel_journal':model.journal,
        'scheduler_journal':scheduler.journal,'no_actual_liquidation_inferred_from_envelope':True,
        'remaining':['historical_source_and_effective_rules_not_admitted','prospective_method_delta_not_financially_admitted',
                     'nine_scenario_comparison_and_statistical_validation_not_run']}


def fabricated_fixture(*, start=DEMO_START, warmup=True):
    """Hand-authored flat-price two-day fixture; no data imports or parameter search."""
    start=stamp(start); end=start+2*DAY
    bars=[]
    first=start-(20*MINUTE if warmup else timedelta())
    for number in range(int((end-first)/MINUTE)):
        at=first+number*MINUTE
        for market in MARKETS:
            bars.append(SyntheticBar(market,OHLCMinute(at,at+MINUTE,at+MINUTE,'1000','1000','1000','1000'),
                                     None if market=='mark' else D('100')))
    events=tuple(SyntheticFunding(at,at,D('.0003') if at.microsecond else D('.0001'),D('1000'),D('1000'))
                 for at in funding_schedule(start,end))
    # Amounts are fixed hand-calculated consequences of the primary fee case,
    # not a callback that silently confirms whatever transfer the engine asks for.
    if warmup:
        confirmations=(TransferConfirmation(start+7*MINUTE,start+7*MINUTE,'spot','100'),
            TransferConfirmation(start+DAY+7*MINUTE,start+DAY+7*MINUTE,'futures','.99079962'),
            TransferConfirmation(start+DAY+timedelta(hours=22,minutes=7),start+DAY+timedelta(hours=22,minutes=7),'spot','.33109925'))
    else:
        confirmations=(TransferConfirmation(start+DAY+7*MINUTE,start+DAY+7*MINUTE,'spot','100'),
            TransferConfirmation(start+DAY+timedelta(hours=22,minutes=7),start+DAY+timedelta(hours=22,minutes=7),'futures','.54000037'))
    return SyntheticDataset(start,end,tuple(bars),events,confirmations)


def json_ready(value):
    if isinstance(value,Decimal): return str(value)
    if isinstance(value,datetime): return value.isoformat()
    if isinstance(value,dict): return {key:json_ready(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)): return [json_ready(item) for item in value]
    return value
