"""Pure US paper-source metadata assessment; no prices, I/O or release authority.

The caller supplies an independently registered authority map and a bound session
calendar. Matching their declared references is not authentication of their bytes
or content. This module never grants paper fills, captures data or changes a bar
timestamp into an exchange-auction event timestamp.

provider_daily_completed means a provider snapshot after the calendar close,
not exchange-certified finality. coverage_complete closes only the registered
query's fields/dates. The prior committed reference can be a durable no-op/state
head from the last session; it need not be a newly rebalanced monthly decision.
"""
from __future__ import annotations
from datetime import date,datetime,time,timedelta,timezone
from dataclasses import dataclass,asdict
from copy import deepcopy
from decimal import Decimal,InvalidOperation
import hashlib
import json
import re
from zoneinfo import ZoneInfo

ASSETS=('SPY','EFA','IEF','GLD')
LOW_UNIT_ASSETS=('SPYM','EFA','IEF','GLDM')
NY=ZoneInfo('America/New_York')


def _asset_scope(assets):
    """An explicit known basket; never infer a universe from provider content."""
    if type(assets) is not tuple or assets not in (ASSETS,LOW_UNIT_ASSETS):
        raise ValueError('registered_asset_scope')
    return assets


def _instant(value):
    if type(value) is not str:return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed if parsed.utcoffset()==timedelta(0) else None
    except (ValueError,TypeError):return None


def _ref(value):
    return (type(value) is dict and set(value)=={'path','sha256','bytes'} and type(value['path']) is str
            and bool(value['path']) and type(value['sha256']) is str
            and re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None
            and type(value['bytes']) is int and value['bytes']>0)


def assess_source_metadata(packet, schedule, *, authorities, assets=ASSETS):
    """Return fixed-code findings. Unknown/late/mislabelled sources cannot fill.

schedule={source_ref,sessions:[{date,open_at,close_at}]}; records are exact four
symbols. Authority declarations are external to packet: id->{kind,definition_ref}.
Warmup records use exact dates/session_complete arrays; open/close records use
effective_at/provider_available_at/received_at. No monetary fields are inspected.
"""
    assets=_asset_scope(assets)
    missing=[]
    def need(ok,code):
        if not ok:missing.append(code)
        return bool(ok)
    purpose=packet.get('purpose') if type(packet) is dict else None
    def result(count=0):
        valid=not missing
        return dict(schema='us_source_assessment_v1',purpose=purpose,
            status=('conditional_daily_model_metadata_valid' if valid and purpose=='daily_model' else 'metadata_requirements_satisfied' if valid else 'unfilled_source_unproven' if purpose=='open' else 'source_waiting'),
            requirements_met=valid,missing=sorted(set(missing)),warmup_session_count=count,
            paper_fills_allowed=False,metadata_only=True,authority_content_authenticated=False,
            model_observation_only=purpose=='daily_model',real_forward=0,
            receipt_does_not_prove_historical_first_publication=True)
    if not need(type(packet) is dict and type(schedule) is dict and type(authorities) is dict,'packet_schema'):return result()
    need(packet.get('schema')=='us_allocation_source_evidence_v1','packet_schema')
    need(purpose in ('warmup','open','close','daily_model'),'purpose')
    need(packet.get('symbols')==list(assets),'four_symbols')
    need(_ref(packet.get('source_ref')),'source_ref')
    need(_ref(schedule.get('source_ref')) and packet.get('calendar_ref')==schedule.get('source_ref'),'calendar_ref')
    sessions=schedule.get('sessions');target=packet.get('session_date')
    if not need(type(sessions) is list and bool(sessions) and all(type(s) is dict for s in sessions),'session_schema'):return result()
    dates=[s.get('date') for s in sessions]
    if not need(all(type(d) is str for d in dates) and dates==sorted(set(dates)) and target in dates,'session_dates'):return result()
    for s in sessions:
        opening,closing=_instant(s.get('open_at')),_instant(s.get('close_at'))
        try:day=date.fromisoformat(s['date'])
        except ValueError:need(False,'session_date_format');return result()
        need(day.isoformat()==s['date'],'canonical_session_date')
        if not need(opening is not None and closing is not None and opening<closing,'session_clock'):return result()
        local_open,local_close=opening.astimezone(NY),closing.astimezone(NY)
        need(local_open.date()==day==local_close.date() and local_open.time()==time(9,30)
             and local_close.time() in (time(13),time(16)),'NYSE_regular_or_bound_early_session')
    i=dates.index(target);session=sessions[i];opened=_instant(session['open_at']);closed=_instant(session['close_at'])
    received=_instant(packet.get('received_at'))
    if not need(received is not None,'packet_receipt_clock'):return result()
    records=packet.get('records')
    if not need(type(records) is dict and set(records)==set(assets),'four_records'):return result()
    def authority(record,key,refkey,kind):
        identifier=record.get(key);definition=authorities.get(identifier) if type(identifier) is str else None
        return (type(definition) is dict and definition.get('kind')==kind
                and _ref(definition.get('definition_ref')) and record.get(refkey)==definition['definition_ref'])
    expected=dates[max(0,i-20):i]
    if purpose=='warmup':
        need(i>=20 and packet.get('warmup_dates')==expected,'last20_exact_calendar')
        if i:need(_instant(sessions[i-1]['close_at'])<=received<opened,'warmup_after_prior_close_before_open')
    if purpose=='daily_model':
        need(i>0 and packet.get('previous_observed_session_date')==dates[i-1],'next_natural_session_only')
        decision=_instant(packet.get('previous_committed_decision_at'))
        need(decision is not None and decision<opened and _ref(packet.get('previous_committed_decision_ref')),'committed_before_open')
        next_open=_instant(sessions[i+1]['open_at']) if i+1<len(sessions) else None
        need(next_open is not None and closed+timedelta(minutes=15)<=received<next_open,'completed_day_receipt_window')
    for symbol in assets:
        row=records[symbol]
        if not need(type(row) is dict,'record_schema'):continue
        prefix=symbol+':'
        need(row.get('currency')=='USD' and row.get('timezone')=='America/New_York',prefix+'identity_units')
        need(_ref(row.get('source_ref')),prefix+'source_ref')
        need(row.get('complete') is True,prefix+'complete')
        rec=_instant(row.get('received_at'))
        if not need(rec is not None and rec<=received,prefix+'receipt_clock'):continue
        if purpose=='warmup':
            need(row.get('observation_kind')=='completed_daily',prefix+'completed_daily_kind')
            need(authority(row,'source_authority','definition_ref','provider_daily_completed'),prefix+'completed_daily_definition')
            need(row.get('dates')==expected,prefix+'last20_exact_calendar')
            need(row.get('session_complete')==[True]*20 and type(row.get('session_complete')) is list
                 and all(type(v) is bool for v in row['session_complete']),prefix+'all20_complete')
            if i:need(_instant(sessions[i-1]['close_at'])<=rec<opened,prefix+'warmup_received_after_close')
        elif purpose=='daily_model':
            need(row.get('observation_kind')=='completed_daily' and row.get('provider_bar_interval')=='1d',prefix+'daily_model_bar')
            need(authority(row,'source_authority','definition_ref','provider_daily_completed'),prefix+'completed_daily_definition')
            need(row.get('provider_trading_date')==target,prefix+'provider_trading_date')
            token=row.get('provider_bucket_timestamp')
            bucket_day=None
            if type(token) is str and re.fullmatch('[0-9]{1,12}',token):
                try:bucket_day=datetime.fromtimestamp(int(token),NY).date().isoformat()
                except (ValueError,OverflowError,OSError):pass
            need(bucket_day==target,prefix+'provider_bucket_day')
            need(_instant(row.get('session_open_at'))==opened and _instant(row.get('session_close_at'))==closed,prefix+'reference_session_clocks')
            need(row.get('effective_at') is None and row.get('provider_available_at') is None,prefix+'no_invented_event_or_publication_clock')
            need(next_open is not None and closed+timedelta(minutes=15)<=rec<next_open,prefix+'daily_receipt_after_close')
            need(row.get('finality')=='provider_snapshot_finality_unknown',prefix+'no_exchange_finality_claim')
            need(row.get('execution')==dict(suspended=None,buy_blocked=None,sell_blocked=None),prefix+'execution_remains_unknown')
            need(row.get('units')=={'prices':'USD_per_share','volume':'shares','dividend':'USD_per_share'},prefix+'daily_units')
        elif purpose in ('open','close'):
            is_open=purpose=='open';effective=opened if is_open else closed;deadline=effective+timedelta(minutes=5 if is_open else 30)
            need(row.get('observation_kind')==('official_open' if is_open else 'completed_daily'),prefix+'observation_kind')
            need(authority(row,'source_authority','definition_ref','exchange_official_open' if is_open else 'provider_daily_completed'),prefix+'event_definition')
            need(_instant(row.get('effective_at'))==effective,prefix+'effective_clock')
            known=_instant(row.get('provider_available_at'))
            need(authority(row,'publication_authority','publication_definition_ref','provider_publication_clock'),prefix+'publication_definition')
            need(known is not None and effective<=known<=rec<=received<=deadline,prefix+'publication_receipt_window')
            if is_open:
                execution=row.get('execution')
                need(authority(row,'execution_authority','execution_definition_ref','exchange_security_status'),prefix+'execution_authority')
                valid=type(execution) is dict and set(execution)=={'suspended','buy_blocked','sell_blocked'} and all(type(v) is bool for v in execution.values())
                need(valid,prefix+'execution_known')
                need(valid and not any(execution.values()),prefix+'execution_unblocked')
                state_at=_instant(row.get('execution_effective_at'));state_received=_instant(row.get('execution_received_at'))
                need(state_at==opened and state_received is not None and opened<=state_received<=rec,prefix+'execution_clock')
        actions=row.get('corporate_actions')
        if need(type(actions) is dict,prefix+'actions_schema'):
            need(authority(actions,'authority','definition_ref','corporate_action_coverage'),prefix+'action_authority')
            need(actions.get('coverage_complete') is True and actions.get('units')=='USD_per_share'
                 and actions.get('splits_absent') is True and actions.get('capital_gains_absent') is True,prefix+'actions_coverage_units')
            need(actions.get('coverage_dates')==(expected if purpose=='warmup' else [target]),prefix+'action_dates')
            if purpose in ('warmup','daily_model'):
                need(actions.get('coverage_basis')=='provider_query_snapshot_only',prefix+'conditional_action_snapshot_basis')
            if purpose=='daily_model':need(actions.get('split_ratio_unit')=='new_shares_per_old_share',prefix+'split_ratio_units')
            if purpose=='open':
                known=_instant(actions.get('known_at'))
                need(known is not None and known<=opened,prefix+'actions_known_before_open')
    return result(20 if purpose=='warmup' and not missing else 0)


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class _SourceDecodeContext:
    """Identity from the caller's separately admitted release; not a release itself."""
    purpose: str
    packet_sha256: str
    source_refs_sha256: str
    release_sha256: str
    evidence_kind: str
    test_values: bool = False

    def __post_init__(self):
        if self.purpose not in ('warmup','daily_model') or type(self.test_values) is not bool:
            raise ValueError('decode_context_purpose')
        if self.evidence_kind != ('artificial_source_values' if self.test_values else 'conditional_provider_observation'):
            raise ValueError('decode_context_identity')
        for value in (self.packet_sha256,self.source_refs_sha256,self.release_sha256):
            if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:raise ValueError('decode_context_hash')


_NUMERIC_TOKEN=re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')


def _number(token, *, positive):
    if type(token) is not str or _NUMERIC_TOKEN.fullmatch(token) is None:raise ValueError('numeric_token')
    try:value=Decimal(token)
    except InvalidOperation as exc:raise ValueError('numeric_value') from exc
    if not value.is_finite() or (value<=0 if positive else value<0):raise ValueError('numeric_domain')
    return str(value)


def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate_source_key')
        result[key]=value
    return result


def _source_row(raw,source_ref,symbol,*,assets=ASSETS):
    assets=_asset_scope(assets)
    if symbol not in assets or not _ref(source_ref) or type(raw) is not bytes or len(raw)!=source_ref['bytes'] or hashlib.sha256(raw).hexdigest()!=source_ref['sha256']:
        raise ValueError('source_bytes_hash')
    try:
        obj=json.loads(raw,parse_int=str,parse_float=str,object_pairs_hook=_unique_pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonstandard_source_number')))
    except (UnicodeError,json.JSONDecodeError) as exc:raise ValueError('source_json') from exc
    chart=obj.get('chart') if type(obj) is dict else None
    if type(chart) is not dict or chart.get('error') is not None or type(chart.get('result')) is not list or len(chart['result'])!=1:
        raise ValueError('source_chart')
    row=chart['result'][0];meta=row.get('meta',{}) if type(row) is dict else {}
    if any(meta.get(k)!=v for k,v in {'symbol':symbol,'currency':'USD','exchangeTimezoneName':'America/New_York','instrumentType':'ETF','dataGranularity':'1d'}.items()):
        raise ValueError('source_identity_units')
    return row


def _source_dates(row):
    times=row.get('timestamp');observed=[]
    if type(times) is not list:raise ValueError('source_timestamps')
    for token in times:
        if type(token) is not str or re.fullmatch('[0-9]{1,12}',token) is None:raise ValueError('source_timestamp')
        try:observed.append(datetime.fromtimestamp(int(token),NY).date().isoformat())
        except (ValueError,OverflowError,OSError) as exc:raise ValueError('source_timestamp') from exc
    return observed


def describe_yahoo_source(raw,source_ref,*,symbol,assets=ASSETS):
    """Bound bytes to identity/date/schema only. No Decimal, price or amount values."""
    row=_source_row(raw,source_ref,symbol,assets=assets);dates=_source_dates(row)
    quote=row.get('indicators',{}).get('quote')
    if type(quote) is not list or len(quote)!=1 or type(quote[0]) is not dict:raise ValueError('source_quote_schema')
    if not set(quote[0])<={'open','high','low','close','volume'}:raise ValueError('source_quote_fields')
    events=row.get('events',{})
    if type(events) is not dict or not set(events)<={'dividends','splits','capitalGains'} or any(type(x) is not dict for x in events.values()):
        raise ValueError('source_actions_unknown')
    return dict(symbol=symbol,currency='USD',timezone='America/New_York',instrument_type='ETF',interval='1d',
        dates=dates,provider_bucket_timestamps=row['timestamp'],rows=len(dates),quote_fields=sorted(quote[0]),
        event_counts={k:len(events.get(k,{})) for k in ('dividends','splits','capitalGains')},source_ref=deepcopy(source_ref),
        financial_values_decoded=False,current_quote_values_projected=False,provider_available_at=None,
        finality='provider_snapshot_finality_unknown')


def normalize_yahoo_sources(raw_by_symbol,packet,schedule,*,authorities,context,before_numeric_decode,assets=ASSETS,
                            daily_fields=('open','close','volume'),dividend_assets=None):
    """Pure bound-byte decoder, called only by a separately admitted controller.

No file/network/credential access. The callback must durably mark the approved
numeric transition; constructing context or passing metadata does not authorize
source use. All source parsing and selected-value checks use these same bytes.
"""
    assets=_asset_scope(assets)
    dividend_assets=assets if dividend_assets is None else dividend_assets
    if type(dividend_assets) is not tuple or dividend_assets not in (assets,LOW_UNIT_ASSETS[:3]):
        raise ValueError('registered_dividend_assets')
    if not set(dividend_assets)<=set(assets):raise ValueError('dividend_asset_scope')
    if type(daily_fields) is not tuple or daily_fields not in (
            ('open','close','volume'),('open','high','low','close','volume')):
        raise ValueError('registered_daily_fields')
    if type(context) is not _SourceDecodeContext or not callable(before_numeric_decode):raise ValueError('admitted_context_required')
    packet=deepcopy(packet)
    if context.packet_sha256!=_digest(packet) or context.purpose!=packet.get('purpose'):raise ValueError('packet_context_hash')
    refs={s:packet.get('records',{}).get(s,{}).get('source_ref') for s in assets}
    if context.source_refs_sha256!=_digest(refs):raise ValueError('refs_context_hash')
    assessment=assess_source_metadata(packet,schedule,authorities=authorities,assets=assets)
    if not assessment['requirements_met']:raise ValueError('source_metadata_not_admissible')
    if type(raw_by_symbol) is not dict or set(raw_by_symbol)!=set(assets):raise ValueError('four_immutable_sources')
    retained={}
    for symbol in assets:
        raw=raw_by_symbol[symbol];ref=refs[symbol]
        if type(raw) is not bytes or len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
            raise ValueError('source_bytes_hash')
        retained[symbol]=raw
    dates=packet['warmup_dates'] if context.purpose=='warmup' else [packet['session_date']]
    fields=('close','volume') if context.purpose=='warmup' else daily_fields
    quotes={};dividends=[]
    for symbol in assets:
        row=_source_row(retained[symbol],refs[symbol],symbol,assets=assets);times=row['timestamp'];observed=_source_dates(row)
        if observed!=dates:raise ValueError('source_dates_exact_no_intersection')
        if context.purpose=='daily_model' and times[0]!=packet['records'][symbol]['provider_bucket_timestamp']:
            raise ValueError('source_bucket_original')
        indicators=row.get('indicators',{});q=indicators.get('quote') if type(indicators) is dict else None
        if type(q) is not list or len(q)!=1 or type(q[0]) is not dict:raise ValueError('source_quote_schema')
        for field in fields:
            values=q[0].get(field)
            if type(values) is not list or len(values)!=len(dates) or any(type(x) is not str or _NUMERIC_TOKEN.fullmatch(x) is None for x in values):
                raise ValueError('selected_field_missing_or_null')
        quotes[symbol]=q[0]
        events=row.get('events',{})
        if type(events) is not dict or not set(events)<={'dividends','splits','capitalGains'}:raise ValueError('source_actions_schema')
        if any(type(value) is not dict for value in events.values()):raise ValueError('source_actions_unknown')
        if events.get('splits') or events.get('capitalGains'):raise ValueError('source_split_or_capital_gain')
        if events.get('dividends') and symbol not in dividend_assets:raise ValueError('source_dividend_asset_unsupported')
        for key,event in events.get('dividends',{}).items():
            if type(event) is not dict or not {'date','amount'}<=set(event) or key!=event['date']:
                raise ValueError('source_dividend_schema')
            if type(key) is not str or re.fullmatch('[0-9]{1,12}',key) is None:raise ValueError('source_dividend_date')
            try:ex=datetime.fromtimestamp(int(key),NY).date().isoformat()
            except (ValueError,OverflowError,OSError) as exc:raise ValueError('source_dividend_date') from exc
            if ex not in dates:raise ValueError('source_dividend_outside_window')
            if context.purpose=='daily_model':
                amount=event['amount']
                if type(amount) is not str or _NUMERIC_TOKEN.fullmatch(amount) is None:raise ValueError('source_dividend_amount')
                dividends.append((symbol,key,ex,amount))
    marker=before_numeric_decode()
    days=[{'date':when,'prices':{symbol:{field:_number(quotes[symbol][field][i],positive=field!='volume') for field in fields}
                                for symbol in assets}} for i,when in enumerate(dates)]
    actions=[{'id':symbol+':'+key,'symbol':symbol,'ex_date':ex,'amount_per_share':_number(amount,positive=False)}
             for symbol,key,ex,amount in dividends]
    return dict(schema='us_source_normalized_packet_v1',purpose=context.purpose,evidence_kind=context.evidence_kind,
        context_identity=asdict(context),numeric_decode_marker=marker,source_refs=refs,assessment=assessment,
        days=days,dividends=actions,source_metadata=packet,qualified=False,real_forward=0,
        adjusted_close_decoded=False,current_quote_decoded=False,warmup_dividend_amount_decoded=False)
