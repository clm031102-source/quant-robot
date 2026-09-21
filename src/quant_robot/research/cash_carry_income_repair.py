"""Exact documented format repair; original financial calculation stays unchanged."""
import json
import re
from quant_robot.research.cash_carry_inputs import decimal_value
from quant_robot.research.cash_carry_diagnostic import _calendar_and_intervals, calculate as original_calculate
from quant_robot.research.monthly_diagnostic_registration import sha256

SUFFIX='(节假日期间)'
EXPECTED_ANNOTATIONS=465


def normalize_value(value, *, closed):
    if isinstance(value,str) and value.endswith(SUFFIX):
        amount=value[:-len(SUFFIX)]
        if not closed or not re.fullmatch(r'[+-]?[0-9]+\.[0-9]{4}',amount):
            raise ValueError('Exact four-decimal closed-period annotation required')
        decimal_value(amount)
        return amount,True
    decimal_value(value)
    return value,False


def calculate(snapshots):
    sessions,_=_calendar_and_intervals(snapshots,json.loads(snapshots['proposal']))
    opened=set(sessions);normalized=snapshots.copy();evidence=[];count=0
    for year in range(2015,2025):
        role=f'income_{year}';raw=snapshots[role];page=json.loads(raw);n=0
        for row in page['data']['data']:
            row['incomeUnit'],changed=normalize_value(row['incomeUnit'],closed=row['navDate'] not in opened)
            n+=changed
        normalized[role]=json.dumps(page,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        evidence.append(dict(role=role,original_sha256=sha256(raw),normalized_sha256=sha256(normalized[role]),
                             annotations_normalized=n))
        count+=n
    if count!=EXPECTED_ANNOTATIONS:raise ValueError('Exact frozen annotation inventory required')
    result=original_calculate(normalized)
    return {**result,'format_repair':dict(annotations_normalized=count,inputs=evidence,
        original_source_bytes_modified=False,economic_method_changed=False,new_independent_hypothesis=False,
        values_exposed_during_failure_diagnosis=True,fresh_OOS=False)}
