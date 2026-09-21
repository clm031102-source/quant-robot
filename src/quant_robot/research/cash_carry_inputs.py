"""Strict primary-money-ETF PCF and income-period parsing; no source downloads."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET

NS = '{http://ts.szse.cn/Fund}'
CAPS = ('CreationLimit', 'RedemptionLimit', 'CreationLimitPerUser', 'RedemptionLimitPerUser',
        'NetCreationLimit', 'NetRedemptionLimit', 'NetCreationLimitPerUser', 'NetRedemptionLimitPerUser')
ACTIVE_CAPS = ('NetCreationLimit', 'NetRedemptionLimit', 'NetCreationLimitPerUser', 'CreationLimitPerUser')


def decimal_value(value, *, percentage=False):
    try:
        text=str(value).strip()
        if percentage:
            text=text.removesuffix('%')
        result=Decimal(text)
    except (InvalidOperation, ValueError) as e:
        raise ValueError('Finite decimal required') from e
    if not result.is_finite():
        raise ValueError('Finite decimal required')
    return result


def _unique_fields(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate PCF field')
        result[key]=value
    return result


def _legacy(raw):
    text=raw.decode('gb18030')
    if text.count('TAGTAG')!=1 or text.count('ENDENDEND')!=1:
        raise ValueError('Single complete legacy PCF required')
    head,tail=text.split('TAGTAG')
    fields=_unique_fields(line.split('=',1) for line in head.splitlines() if '=' in line)
    parts=[line.strip() for line in tail.splitlines() if line.strip()]
    if len(parts)!=2 or parts[-1]!='ENDENDEND':
        raise ValueError('Single cash component required')
    row=[p.strip() for p in parts[0].split('|')]
    if (fields.get('Version')!='2.0' or fields.get('Type')!='4' or
            len(row)!=9 or row[0]!='159900' or row[3]!='2' or row[7]!='XSHE'):
        raise ValueError('Legacy money ETF cash schema required')
    if row[2] and decimal_value(row[2])!=0:
        raise ValueError('Pure cash component required')
    return fields, fields.get('FundID'), row[5], row[6], ('0','1')


def _xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('PCF entity declarations rejected')
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError('Valid PCF XML required') from e
    if root.tag!=NS+'PCFFile' or len(root.findall(NS+'Components'))!=1:
        raise ValueError('SZSE PCF namespace required')
    fields=_unique_fields((e.tag.removeprefix(NS),e.text) for e in root if e.tag!=NS+'Components')
    components=root.findall(NS+'Components/'+NS+'Component')
    if len(components)!=1:
        raise ValueError('Single cash component required')
    row=_unique_fields((e.tag.removeprefix(NS),e.text) for e in components[0])
    if (fields.get('Version')!='1.0' or fields.get('SecurityIDSource')!='102' or
            row.get('UnderlyingSecurityID')!='159900' or row.get('SubstituteFlag')!='2' or
            row.get('UnderlyingSecurityIDSource')!='102' or decimal_value(row.get('ComponentShare'))!=0):
        raise ValueError('Money ETF cash XML required')
    return fields, fields.get('SecurityID'), row.get('CreationCashSubstitute'), row.get('RedemptionCashSubstitute'), ('N','Y')


def parse_pcf(raw, expected_date):
    stamp=date.fromisoformat(expected_date).strftime('%Y%m%d')
    fields,fund,cash_in,cash_out,flags=_legacy(raw) if raw.startswith(b'[ETFHZ]') else _xml(raw)
    if fund!='159001' or fields.get('TradingDay')!=stamp:
        raise ValueError('Exact historical fund/date required')
    for key in ('Creation','Redemption'):
        if fields.get(key) not in flags:
            raise ValueError('Known subscription/redemption flag required')
    if flags==('0','1') and fields.get('CashCreation') not in flags:
        raise ValueError('Known cash-creation flag required')
    for key in ('CreationRedemptionUnit','RecordNum','TotalRecordNum'):
        if decimal_value(fields.get(key))!=1:
            raise ValueError('One-share unit and one cash component required')
    for key in ('CashComponent','EstimateCashComponent'):
        if decimal_value(fields.get(key))!=0:
            raise ValueError('Nonzero cash differences outside frozen study')
    for value in (cash_in,cash_out,fields.get('NAV'),fields.get('NAVperCU')):
        if decimal_value(value)!=100:
            raise ValueError('Fixed100CNY cash basis required')
    if any(k not in fields for k in ACTIVE_CAPS):
        raise ValueError('Active cap absent; do not infer zero')
    caps={k:None if k not in fields else decimal_value(fields[k]) for k in CAPS}
    if any(x is not None and (x<0 or x!=x.to_integral_value()) for x in caps.values()):
        raise ValueError('Nonnegative integer share caps required')
    previous=str(fields.get('PreTradingDay',''))
    try:
        previous_date=date(int(previous[:4]),int(previous[4:6]),int(previous[6:]))
    except ValueError as e:
        raise ValueError('Valid previous valuation date required') from e
    if len(previous)!=8 or previous_date>=date.fromisoformat(expected_date):
        raise ValueError('Strictly earlier valuation date required')
    return dict(date=expected_date,previous_date=previous_date.isoformat(),
                creation=fields['Creation']==flags[1] and (flags!=('0','1') or fields['CashCreation']=='1'),
                redemption=fields['Redemption']==flags[1],caps=caps,cash_in=Decimal(100),cash_out=Decimal(100))


def _closed_periods(days, observed):
    hits=[d for d in days if d in observed]
    if hits==days:
        ends=days
    elif hits==[days[-1]]:
        ends=hits
    else:
        ends=sorted(set([d for d in days if d.endswith('-12-31')]+[days[-1]]))
        if hits!=ends:
            raise ValueError('Unexplained partial closed-calendar run')
    result=[];start=days[0]
    for end in ends:
        count=(date.fromisoformat(end)-date.fromisoformat(start)).days+1
        result.append(dict(start=start,end=end,days=count))
        start=(date.fromisoformat(end)+timedelta(days=1)).isoformat()
    return result


def income_periods(sessions, observed_dates, start, end):
    a,b=date.fromisoformat(start),date.fromisoformat(end)
    if (a>b or len(observed_dates)!=len(set(observed_dates)) or sessions!=sorted(set(sessions)) or
            any(date.fromisoformat(d).isoformat()!=d for d in sessions)):
        raise ValueError('Unique dates and forward range required')
    observed=set(observed_dates);opened=set(sessions)
    if any(not start<=d<=end or date.fromisoformat(d).isoformat()!=d for d in observed):
        raise ValueError('Observed dates outside fixed source window')
    result=[];closed=[]
    for i in range((b-a).days+1):
        day=(a+timedelta(days=i)).isoformat()
        if day in opened:
            if closed:
                result.extend(_closed_periods(closed,observed));closed=[]
            if day not in observed:
                raise ValueError('Open-session income missing')
            result.append(dict(start=day,end=day,days=1))
        else:
            closed.append(day)
    if closed:
        result.extend(_closed_periods(closed,observed))
    if {r['end'] for r in result}!=observed:
        raise ValueError('Unconsumed income dates')
    return result


def check_income_identities(rows, periods, end_dates):
    """Called only after one-use registration, never during blind source preparation."""
    tolerance=Decimal('.00005')*7+Decimal('.0005')*700/365
    result=[]
    for end in end_dates:
        start=(date.fromisoformat(end)-timedelta(days=6)).isoformat()
        selected=[p for p in periods if p['start']<=end and p['end']>=start]
        if (not selected or selected[0]['start']!=start or selected[-1]['end']!=end or
                sum(p['days'] for p in selected)!=7):
            raise ValueError('Seven-day check cannot split a reporting period')
        total=sum((decimal_value(rows[p['end']]['incomeUnit']) for p in selected),Decimal(0))
        implied=decimal_value(rows[end]['incomeRatio'],percentage=True)*700/365
        error=abs(total-implied)
        if error>tolerance:
            raise ValueError('Fixed seven-day income identity failed at '+end)
        result.append(dict(end_date=end,absolute_error_income_unit=float(error),tolerance=float(tolerance)))
    return result
