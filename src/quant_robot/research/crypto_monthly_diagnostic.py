"""Fixed-schema monthly controller preparation. Public entry points are synthetic only.

This module has no filesystem source reader, network client or financial admission.
Raw schema emulates January 2025, while allowed fixtures are fabricated January 2001.
The future admitted historical entry point must independently guard financial decode;
changing an evidence label here does not confer historical permission.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from quant_robot.research.crypto_carry_driver import audit_minute, json_ready
from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, MINUTE, TradingRule, credit, debit, dec
from quant_robot.research.crypto_carry_policy import CompletedPrices, OHLCMinute, VolumeMinute
from quant_robot.research.crypto_carry_scheduler import CompletedPrefix, SyntheticCarryScheduler, TransferConfirmation

D = Decimal
UTC = timezone.utc
DAY = timedelta(days=1)
START = datetime(2001, 1, 1, tzinfo=UTC)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
HEADER = ('open_time','open','high','low','close','volume','close_time','quote_volume',
          'count','taker_buy_volume','taker_buy_quote_volume','ignore')
FUNDING_HEADER = ('calc_time','funding_interval_hours','last_funding_rate')
MARKETS = ('spot','um','mark')
SCENARIOS = {f'{band}_{slip}': FeeScenario(spot, future, D(slip)/10000)
             for band,spot,future in (('A','.001','.0005'),('B','.0015','.00075'),('C','.002','.001'))
             for slip in (2,5,10)}
PRIMARY = 'B_5'
MAX_ZIP_BYTES = 8_000_000
MAX_CSV_BYTES = 30_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    return json.dumps(json_ready(data), ensure_ascii=False, sort_keys=True, separators=(',',':'))


def _unique(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def _integer(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError('integer_timestamp_required')
    return int(value)


def _milliseconds(at):
    delta = at-EPOCH
    return delta.days*86400000+delta.seconds*1000+delta.microseconds//1000


@dataclass(frozen=True)
class RawArchive:
    filename: str
    member: str
    body: bytes
    checksum: bytes


@dataclass(frozen=True)
class RawMonthlyBundle:
    start: datetime
    end: datetime
    archives: dict[str, RawArchive]
    funding_tool_return: bytes
    expected_funding_times_ms: tuple[int, ...]
    evidence_class: str
    fixture_created_at: datetime | None
    actual_market_acquired_at: datetime | None = None
    historical_first_publication_at: datetime | None = None


@dataclass(frozen=True)
class FundingEvent:
    at: datetime
    rate: Decimal
    mark: Decimal
    synchronous_spot: None = None


@dataclass(frozen=True)
class Bar:
    candle: OHLCMinute
    volume_btc: Decimal | None


@dataclass(frozen=True)
class LoadedMonth:
    start: datetime
    end: datetime
    bars: dict[str, tuple[Bar, ...]]
    funding: tuple[FundingEvent, ...]
    provenance: dict
    coverage: dict


def _csv(archive):
    if (not isinstance(archive,RawArchive) or not isinstance(archive.body,bytes)
            or len(archive.body)>MAX_ZIP_BYTES or not archive.filename.endswith('.zip')
            or Path(archive.filename).name!=archive.filename or '/' in archive.member or '\\' in archive.member):
        raise ValueError('archive_identity_or_size')
    expected=f'{sha(archive.body)}  {archive.filename}'
    if archive.checksum.decode('ascii').strip()!=expected:
        raise ValueError('archive_checksum_mismatch')
    with zipfile.ZipFile(io.BytesIO(archive.body)) as source:
        members=source.infolist()
        if (len(members)!=1 or members[0].filename!=archive.member or members[0].is_dir()
                or members[0].flag_bits & 1 or members[0].file_size>MAX_CSV_BYTES
                or (members[0].external_attr>>16)&0o170000==0o120000):
            raise ValueError('archive_member_contract')
        body=source.read(members[0])
    return list(csv.reader(io.StringIO(body.decode('utf-8'),newline='')))


def load_raw_month(raw: RawMonthlyBundle) -> LoadedMonth:
    """Validate all original-format bytes before creating any account.

Real evidence is rejected before ZIP decode. Source acquisition clocks remain in
provenance; OHLC received_at below is explicitly an offline availability assumption.
    """
    if (not isinstance(raw,RawMonthlyBundle) or raw.evidence_class!='synthetic_raw_fixture'
            or raw.actual_market_acquired_at is not None or raw.historical_first_publication_at is not None):
        raise ValueError('historical_decode_requires_separate_admission_guard')
    days=(raw.end-raw.start).days
    if (raw.start!=START or not 2<=days<=31 or raw.end!=START+days*DAY
            or raw.fixture_created_at.tzinfo is None or set(raw.archives)!=set(MARKETS)|{'funding'}):
        raise ValueError('fixed_fabricated_january_scope_required')
    return _decode_month_core(raw)


def _decode_month_core(raw: RawMonthlyBundle, *, source_provenance=None) -> LoadedMonth:
    """Shared numerical parser; historical callers must own a verified claim.

This internal primitive does not grant access to files or confer admission.
Public synthetic and historical entry points enforce their distinct boundaries.
    """
    days=(raw.end-raw.start).days
    count=days*1440
    indexed={}
    for market in MARKETS:
        rows=_csv(raw.archives[market])
        if market!='spot':
            if not rows or tuple(rows.pop(0))!=HEADER:
                raise ValueError('exact_202501_header_required:'+market)
        if len(rows)!=count:
            raise ValueError('minute_coverage_count:'+market)
        factor=1000 if market=='spot' else 1
        bars=[]
        for index,row in enumerate(rows):
            if len(row)!=12:
                raise ValueError('twelve_bar_columns_required')
            at=raw.start+index*MINUTE
            expected=_milliseconds(at)*factor
            if _integer(row[0])!=expected or _integer(row[6])!=expected+60000*factor-1:
                raise ValueError('bar_time_unit_grid_duplicate_or_close_mismatch:'+market)
            op,hi,lo,cl,vol=tuple(dec(v) for v in row[1:6])
            if vol<0 or any(dec(row[j])<0 for j in (7,9,10)):
                raise ValueError('negative_volume_or_quote_amount')
            _integer(row[8]); dec(row[11])
            candle=OHLCMinute(at,at+MINUTE,at+MINUTE,op,hi,lo,cl)
            bars.append(Bar(candle,None if market=='mark' else vol))
        indexed[market]=tuple(bars)
    rows=_csv(raw.archives['funding'])
    if not rows or tuple(rows.pop(0))!=FUNDING_HEADER:
        raise ValueError('funding_archive_header')
    archive=[]
    for row in rows:
        if len(row)!=3 or dec(row[1])<=0:
            raise ValueError('funding_archive_fields')
        archive.append((_integer(row[0]),dec(row[2])))
    actual_times=tuple(at for at,_ in archive)
    if (actual_times!=raw.expected_funding_times_ms or actual_times!=tuple(sorted(set(actual_times)))
            or len(actual_times)!=days*3 or any(not _milliseconds(raw.start)<=at<_milliseconds(raw.end) for at in actual_times)):
        raise ValueError('funding_exact_event_coverage')
    tool=json.loads(raw.funding_tool_return, object_pairs_hook=_unique)
    if tool.get('isError') is not False or not isinstance(tool.get('structuredContent'),dict):
        raise ValueError('funding_mcp_schema')
    content=tool.get('content')
    if (not isinstance(content,list) or len(content)!=1 or content[0].get('type')!='text'
            or json.loads(content[0]['text'],object_pairs_hook=_unique)!=tool['structuredContent']):
        raise ValueError('funding_mcp_mirror_mismatch')
    events=tool['structuredContent'].get('result')
    if not isinstance(events,list) or len(events)!=len(archive):
        raise ValueError('funding_mcp_event_count')
    funding=[]
    for event,(clock,rate) in zip(events,archive):
        if (event.get('symbol')!='BTCUSDT' or type(event.get('fundingTime')) is not int
                or event['fundingTime']!=clock or not isinstance(event.get('fundingRate'),str)
                or not isinstance(event.get('markPrice'),str) or dec(event['fundingRate'])!=rate
                or not isinstance(event.get('rateType'),str) or not event['rateType'] or dec(event['markPrice'])<=0):
            raise ValueError('funding_mcp_archive_time_rate_or_mark_mismatch')
        at=EPOCH+timedelta(milliseconds=clock)
        mark=dec(event['markPrice'])
        candle=indexed['mark'][int((at-raw.start).total_seconds()//60)].candle
        if not candle.low<=mark<=candle.high:
            raise ValueError('event_mark_outside_minute_ohlc')
        funding.append(FundingEvent(at,rate,mark))
    provenance={'evidence_class':raw.evidence_class,'schema_emulates':'2025-01_original_formats',
        'fixture_created_at':raw.fixture_created_at.isoformat() if raw.fixture_created_at else None,'actual_market_acquired_at':None,
        'historical_first_publication_at':None,'actual_market_values_decoded':False,
        'archives':{k:{'filename':v.filename,'member':v.member,'sha256':sha(v.body),
                       'checksum_sha256':sha(v.checksum)} for k,v in raw.archives.items()},
        'funding_tool_return_sha256':sha(raw.funding_tool_return),
        'clock_assumptions':{'bar_available':'right_endpoint_instantaneously_model_assumed',
            'opening_available':'same_minute_boundary_model_assumed',
            'funding_available':'original_event_clock_model_assumed',
            'transfer_confirmation':'model_assumed_transfer_confirmation_after_five_complete_minutes'}}
    if source_provenance is not None:
        provenance.update(source_provenance)
    coverage={'status':'complete','minutes_per_market':count,'days':days,'funding_events':len(funding),
        'off_minute_funding_events':sum(bool(t%60000) for t in actual_times),
        'time_units':{'spot':'microseconds','um':'milliseconds','mark':'milliseconds','funding':'milliseconds'},
        'price_unit':'USDT_per_BTC','capacity_volume_unit':'BTC','funding_rate_unit':'fraction_per_event',
        'qualified':False,'real_forward':0}
    return LoadedMonth(raw.start,raw.end,indexed,tuple(funding),provenance,coverage)


def _archive(name, rows):
    buffer=io.StringIO(newline='')
    csv.writer(buffer,lineterminator='\n').writerows(rows)
    output=io.BytesIO()
    member=name+'.csv'; filename=name+'.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        info=zipfile.ZipInfo(member,(2001,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
        bundle.writestr(info,buffer.getvalue().encode())
    body=output.getvalue()
    return RawArchive(filename,member,body,f'{sha(body)}  {filename}\n'.encode())


def synthetic_raw_fixture(*, days=31, volume='100', funding_rate='.0001', shock=False):
    """Artificial 2001 observations in the exact frozen 2025 source layouts.

The optional fixed day-three spot shock exercises pause/cooldown, never selects
a price path from real data. It changes no economic parameter.
    """
    if not 2<=days<=31:
        raise ValueError('fixture_days_2_to_31')
    archives={}
    for market in MARKETS:
        rows=[] if market=='spot' else [HEADER]
        factor=1000 if market=='spot' else 1
        for minute in range(days*1440):
            at=START+minute*MINUTE; clock=_milliseconds(at)*factor
            price='900' if shock and minute>=2*1440+12*60 and market=='spot' else '1000'
            rows.append((str(clock),price,price,price,price,volume,str(clock+60000*factor-1),
                         str(dec(volume)*dec(price)),'10',str(dec(volume)/2),str(dec(volume)*dec(price)/2),'0'))
        archives[market]=_archive('synthetic_'+market+'_BTCUSDT_200101',rows)
    times=tuple(_milliseconds(START+day*DAY+timedelta(hours=hour))+(15 if day*3+i<12 else 0)
                for day in range(days) for i,hour in enumerate((0,8,16)))
    archives['funding']=_archive('synthetic_funding_BTCUSDT_200101',
        [FUNDING_HEADER]+[(str(t),'8',funding_rate) for t in times])
    structured={'result':[{'symbol':'BTCUSDT','fundingTime':t,'fundingRate':funding_rate,
                           'markPrice':'1000','rateType':'synthetic_fixture'} for t in times]}
    tool={'isError':False,'structuredContent':structured,'content':[{'type':'text','text':_json(structured)}]}
    return RawMonthlyBundle(START,START+days*DAY,archives,_json(tool).encode(),times,
        'synthetic_raw_fixture',datetime.now(UTC))


def _assert_loaded(data):
    if (not isinstance(data,LoadedMonth) or data.provenance.get('evidence_class')!='synthetic_raw_fixture'
            or data.provenance.get('actual_market_acquired_at') is not None or data.start!=START
            or data.end>START+31*DAY or data.coverage.get('status')!='complete'):
        raise ValueError('historical_account_requires_separate_admission_guard')
    minutes=int((data.end-data.start).total_seconds()/60)
    if (set(data.bars)!=set(MARKETS) or any(len(data.bars[m])!=minutes for m in MARKETS)
            or len(data.funding)!=data.coverage['funding_events']):
        raise ValueError('loaded_coverage_modified_or_missing')
    for market in MARKETS:
        for i,bar in enumerate(data.bars[market]):
            if not isinstance(bar,Bar) or bar.candle.start!=data.start+i*MINUTE:
                raise ValueError('loaded_minute_grid_modified')


def _base(data):
    historical=data.provenance['evidence_class']=='retained_historical_sources'
    return {'input_evidence_class':data.provenance['evidence_class'],
        'execution_class':'conditional_historical_month' if historical else 'synthetic_controller_validation',
        'qualified':False,'real_forward':0,'historical_returns_computed':historical,
        'real_market_files_read':data.provenance.get('financial_source_files_decoded',0),
        'network_requests':0,'initial_capital_usdt':'1000','source_provenance':data.provenance,
        'coverage':data.coverage,'source_start':data.start.isoformat(),'source_end_exclusive':data.end.isoformat(),
        'synchronous_funding_spot_observed':False,'day_one_policy':'warmup_only_first_entry_day_two_0002',
        'rules_status':'fixed_conditional_assumption_not_historical_certification',
        'per_minute_conditional_envelope_limitation':'observed_peak_and_supplied_wallet_states_only_not_all_month_paths',
        'next_month_opening_or_funding_consumed':False}


def run_account(data: LoadedMonth, *, scenario=PRIMARY, output_dir: str | Path):
    """Run one continuous synthetic account, writing compressed evidence as it advances.

Only one account's kernel history is resident. Callers run scenarios serially;
full trace/envelope rows are never returned or replicated across nine accounts.
    """
    _assert_loaded(data)
    return _run_account_core(data,scenario=scenario,output_dir=output_dir)


def _component_snapshot(model, data, terminal=None):
    result=terminal if terminal is not None else model.snapshot()
    if data.provenance['evidence_class']=='retained_historical_sources':
        result=dict(result)
        for key in ('synthetic_only','historical_returns_computed','diagnostic_engine_incomplete','financial_verdict'):
            result.pop(key,None)
        result.update(evidence_class='conditional_historical_account_state',historical_returns_computed=True,
                      financial_verdict='conditional_month_not_strategy_qualification')
    return result


def _run_account_core(data: LoadedMonth, *, scenario=PRIMARY, output_dir: str | Path):
    """Shared account arithmetic. Public callers own source/admission validation."""
    if scenario not in SCENARIOS:
        raise ValueError('one_of_nine_frozen_scenarios_required')
    output=Path(output_dir); output.mkdir(parents=True,exist_ok=False)
    model=CarryModel(start=data.start,spot_rule=TradingRule('.00001','.00001','5'),
        futures_rule=TradingRule('.001','.001','100'),fees=SCENARIOS[scenario],
        spot_cash='500',futures_cash='500',audit_event_states=True)
    scheduler=SyntheticCarryScheduler(model)
    funding={event.at:event for event in data.funding}
    for event in data.funding:
        scheduler.queue_funding(event.at,rate=event.rate,mark=event.mark,synchronous_spot=None)
    days=(data.end-data.start).days; minutes=days*1440
    for day in range(1,days+1): scheduler.queue_day_end(data.start+day*DAY)
    terminal_at=data.end-DAY+timedelta(hours=22)
    trace_cursor=journal_cursor=scheduler_cursor=0
    by_minute={}; receipts={}; assumptions=[]; counts=Counter(); blocked=None; processed=0
    observed_dd=D(0); daily=[]; fills=[]; cash_events=[]; rejected=[]; futures_fees=D(0); spot_sell_fees=D(0)
    complete_flat_roundtrips=0; had_pair=False
    with ExitStack() as stack:
        files={name:stack.enter_context(gzip.open(output/(name+'.jsonl.gz'),'xt',encoding='utf-8'))
               for name in ('event_states','kernel_journal','scheduler_journal','minute_envelopes','transfer_assumptions')}
        def emit(name,row): files[name].write(_json(row)+'\n')
        for minute in range(minutes+1):
            at=data.start+minute*MINUTE
            if minute<minutes:
                scheduler.queue_opening(at,spot=data.bars['spot'][minute].candle.open,
                    future=data.bars['um'][minute].candle.open,mark=data.bars['mark'][minute].candle.open)
            prices=prefix=None
            if minute:
                prices=CompletedPrices(at,at,*(data.bars[m][minute-1].candle.close for m in MARKETS))
                if minute>=20:
                    volumes=tuple(tuple(VolumeMinute(data.start+(i+1)*MINUTE,data.start+(i+1)*MINUTE,
                        data.bars[m][i].volume_btc) for i in range(minute-20,minute)) for m in ('spot','um'))
                    prefix=CompletedPrefix(prices,*volumes)
            receipt=receipts.get(at)
            if model.transfer is not None and model.transfer.due==at and receipt is None:
                blocked='missing_model_assumed_transfer_confirmation'; break
            result=scheduler.advance(at,prefix=prefix,completed_prices=prices if prefix is None else None,
                                     confirmation=receipt,terminal_intent=at==terminal_at)
            new_journal=model.journal[journal_cursor:]; journal_cursor=len(model.journal)
            for row in new_journal:
                emit('kernel_journal',row)
                if row['event']=='transfer_pending':
                    requested=datetime.fromisoformat(row['time']); due=datetime.fromisoformat(row['due'])
                    if due!=requested+5*MINUTE or due<=at or due in receipts:
                        blocked='model_transfer_clock_or_duplicate'; break
                    confirmation=TransferConfirmation(due,due,row['source'],dec(row['amount']))
                    receipts[due]=confirmation
                    assumption={'event':'model_assumed_transfer_confirmation','requested_at':requested,
                        'scheduled_at':at,'due_at':due,'source':row['source'],'amount':row['amount'],
                        'historical_api_receipt':False,'actual_source_acquired_at':None}
                    assumptions.append(assumption); emit('transfer_assumptions',assumption)
                if row['event']=='leg_filled':
                    fills.append(row)
                    if row['side'] in ('short_open','short_close'):
                        futures_fees+=debit(dec(row['quantity'])*dec(row['price'])*model.fees.futures)
                    elif row['side']=='spot_sell':
                        spot_sell_fees+=debit(credit(dec(row['quantity'])*dec(row['price']))*model.fees.spot)
                elif row['event']=='funding': cash_events.append(row)
                elif row['event']=='day_end': daily.append(row)
                elif 'reject' in row['event']: rejected.append(row)
            for row in scheduler.journal[scheduler_cursor:]: emit('scheduler_journal',row)
            scheduler_cursor=len(scheduler.journal)
            trace_cursor,new=model.audit_states_since(trace_cursor)
            for row in new:
                emit('event_states',asdict(row))
                key=row.at.replace(second=0,microsecond=0)
                by_minute.setdefault(key,[]).append(row)
            if minute:
                audit=audit_minute(rows=by_minute.pop(at-MINUTE,[]),spot=data.bars['spot'][minute-1].candle,
                                   mark=data.bars['mark'][minute-1].candle,funding=funding)
                if data.provenance['evidence_class']=='retained_historical_sources':
                    audit['envelope'].pop('synthetic_only',None)
                    audit['envelope']['evidence_class']='conditional_historical_minute_envelope'
                emit('minute_envelopes',audit); counts[audit['envelope']['status']]+=1; processed+=1
            observed_dd=model.max_drawdown
            if model.short_btc>0 and model.spot_btc>0: had_pair=True
            if had_pair and model.short_btc==0 and not model.has_tradable_spot() and model.plan is None:
                complete_flat_roundtrips+=1; had_pair=False
            if result['status']=='blocked': blocked=result['reason']
            if model.nav<=0: blocked='nonpositive_model_nav_stop_preserve_exposure'
            if blocked: break
    terminal=model.finish() if blocked is None else None
    spot_pnl=model.realized_spot+model.spot_btc*model.spot_price-model.spot_cost
    futures_pnl=model.realized_futures+model.unrealized_futures
    expected=D(1000)+model.funding_cash+spot_pnl+futures_pnl-futures_fees
    difference=model.nav-expected
    # Every quote debit/credit rounds to eight decimal places. The independent
    # aggregate identity permits one such quantum per fill; no fee is subtracted twice.
    tolerance=D('.00000001')*max(1,len(fills))
    ledger={'initial_capital':'1000','funding_cash':str(model.funding_cash),
        'spot_pnl_after_spot_fees':str(spot_pnl),'futures_pnl_before_futures_fees':str(futures_pnl),
        'futures_fees_usdt':str(futures_fees),'expected_nav':str(expected),'actual_nav':str(model.nav),
        'rounding_residual':str(difference),'rounding_tolerance':str(tolerance),'reconciled':abs(difference)<=tolerance,
        'base_fee_btc_informational_not_double_subtracted':str(model.base_fee_btc),
        'spot_sell_fees_usdt_already_in_spot_pnl':str(spot_sell_fees),
        'spot_buy_fee_quote_equivalent_already_in_spot_pnl':str(model.fees_quote-futures_fees-spot_sell_fees),
        'all_fees_quote_equivalent_informational':str(model.fees_quote)}
    event_complete=tuple(datetime.fromisoformat(r['time']) for r in cash_events)==tuple(funding)
    complete=blocked is None and processed==minutes and len(daily)==days and event_complete and ledger['reconciled']
    exercised=(complete and len(fills)>=4 and any(dec(r['cash_delta'])!=0 for r in cash_events)
               and {'spot_buy','short_open','short_close','spot_sell'}<={r['side'] for r in fills})
    status=('blocked_execution' if blocked else 'incomplete_account' if not complete else
            'completed_with_execution_failures' if model.failures else
            'completed_without_economic_exercise' if not exercised else
            'completed_with_unresolved_path' if counts['unresolved_path'] else
            'completed_conditional_historical_account' if data.provenance['evidence_class']=='retained_historical_sources'
            else 'completed_synthetic_account')
    summary={**_base(data),'scenario':scenario,'primary':scenario==PRIMARY,'status':status,'reason':blocked,
        'fee_scenario':asdict(model.fees),'spot_rule':asdict(model.spot_rule),'futures_rule':asdict(model.futures_rule),
        'account_complete':complete,'economic_exercise_complete':exercised,'processed_minutes':processed,
        'final_processing_at':model.now.isoformat(),'terminal_intent_at':terminal_at.isoformat(),
        'fill_count':len(fills),'orders':fills,'rejections':rejected,'daily_nav':daily,
        'funding_events':cash_events,'funding_event_coverage_complete':event_complete,
        'model_assumed_transfer_count':len(assumptions),'complete_flat_roundtrips':complete_flat_roundtrips,
        'risk_observation_counts':dict(Counter(reason for row in model.journal if row['event']=='risk_observation'
                                              for reason in row['reasons'])),
        'scheduler_event_counts':dict(Counter(row['event'] for row in scheduler.journal)),
        'sampled_model_drawdown':str(observed_dd),
        'sampled_book_drawdown_before_terminal_haircut':str(observed_dd),
        'conditional_drawdown_including_terminal_haircut':str(model.max_drawdown),
        'final_drawdown_metric':'conditional_drawdown_including_terminal_haircut',
        'per_minute_conditional_envelope':dict(counts),
        'ledger':ledger,'terminal':_component_snapshot(model,data,terminal) if terminal is not None else None,
        'kernel_component':_component_snapshot(model,data),
        'no_actual_liquidation_inferred_from_envelope':True,
        'remaining':(['financial_admission_not_granted'] if data.provenance['evidence_class']=='synthetic_raw_fixture' else [])+
                    ['historical_rules_and_execution_not_certified','long_term_validation_and_real_forward_not_completed']}
    summary['artifacts']={path.name:{'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size}
                          for path in sorted(output.glob('*.jsonl.gz'))}
    (output/'summary.json').write_text(_json(summary)+'\n',encoding='utf-8')
    return summary


def run_matrix(data: LoadedMonth, *, output_dir):
    """All nine identities, serially, retaining even blocked or failed accounts."""
    _assert_loaded(data)
    root=Path(output_dir); root.mkdir(parents=True,exist_ok=False)
    summaries={}
    for scenario in SCENARIOS:
        summaries[scenario]=run_account(data,scenario=scenario,output_dir=root/scenario)
    cash={**_base(data),'scenario':'CASH','nav':'1000','interest':'0','fees':'0',
          'daily_nav':[{'day':(data.start+i*DAY).date().isoformat(),'nav':'1000'} for i in range((data.end-data.start).days)],
          'economic_exercise_complete':False,'reason':'cash_reference_has_no_trading_mechanism'}
    (root/'cash.json').write_text(_json(cash)+'\n',encoding='utf-8')
    result={'qualified':False,'real_forward':0,'historical_returns_computed':False,'synthetic_only':True,
            'scenario_ids':list(SCENARIOS)+['CASH'],'primary':PRIMARY,'accounts':summaries,'cash':cash}
    (root/'matrix.json').write_text(_json(result)+'\n',encoding='utf-8')
    return result
