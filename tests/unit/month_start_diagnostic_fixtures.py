"""Synthetic calendar/price sources for the independently scoped monthly study."""
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar
from quant_robot.research.month_start_diagnostic_registration import (
    DIRECTORY, HYPOTHESIS, build_registration, expected_input_paths,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256
from tests.unit.test_month_start_diagnostic_registration import scheduler_fixture


def execution_fixture(root):
    paths=expected_input_paths();inputs={};snapshots={}
    def put(role,value):
        content=value if isinstance(value,bytes) else canonical(value)
        file=root/paths[role];file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(content)
        snapshots[role]=content;inputs[role]={'path':paths[role],'sha256':sha256(content)}
    first,terminal=date(2020,1,2),date(2024,6,3)
    span=(terminal-first).days
    sessions=[first+timedelta(days=span*i//1068) for i in range(1069)]
    frame=pd.DataFrame({'date':sessions,'is_open':1})
    calendar,manifest=build_cn_trading_calendar({'SSE':frame,'SZSE':frame},
        start_date='2015-01-01',end_date='2025-12-31')
    put('calendar',calendar.to_csv(index=False).encode())
    manifest['artifact']={'path':paths['calendar'],'sha256':inputs['calendar']['sha256'],
                          'size_bytes':len(snapshots['calendar'])}
    put('calendar_manifest',manifest)
    put('actions',{'schema_version':3,'source_ref':'synthetic fixture','asset_ids':['CN_ETF_XSHG_510300'],
                   'coverage_start':str(first),'coverage_end':str(terminal),'events':[]})
    for year in range(2020,2025):
        dates=[day for day in sessions if day.year==year]
        frame=pd.DataFrame({'date':dates,'asset_id':'CN_ETF_XSHG_510300','market':'CN_ETF',
                            'currency':'CNY','close':10.0})
        stream=io.BytesIO();frame.to_parquet(stream,index=False);put('bars_'+str(year),stream.getvalue())
    put('proposal',(Path(__file__).resolve().parents[2]/paths['proposal']).read_bytes())
    price_roles=['calendar','calendar_manifest','actions',*['bars_'+str(y) for y in range(2020,2025)]]
    fingerprints={inputs[r]['path']:inputs[r]['sha256'] for r in price_roles}
    put('source_join',{'fingerprints':fingerprints})
    put('source_review',{'status':'conditional_calendar_source_use_reviewed_not_execution_admission',
        'economic_hypothesis_id':HYPOTHESIS,'proposal_sha256':inputs['proposal']['sha256'],
        'inputs':dict(inputs),'retained_source_join_sha256':inputs['source_join']['sha256'],
        'verified_component_fingerprints':fingerprints,'verified_component_file_count':len(fingerprints),
        'complete_civil_day_rows':1616,'open_session_count':1069,'derived_closed_day_count':547,
        'historical_version_assumption_verified':False,'source_audit_verified':False,
        'research_admission_granted':False,'factor_or_return_computed':False,'real_calendar_positions_generated':False})
    code=root/'month_start_fixture.py';code.write_bytes(b'# explicitly synthetic fixture\n')
    packet=build_registration(inputs=inputs,code_files={code.name:sha256(code.read_bytes())},
        environment={'python':'fixture'},source_origin='synthetic_fixture',branch='codex/factor-review-fixture')
    path=root/DIRECTORY/'registration.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(packet))
    scheduler=scheduler_fixture(packet)
    gate={'status':'ready','mode':'single_month_start_diagnostic_only',
        'generated_at':datetime.now(timezone.utc).isoformat(),'primary_market':'CN_ETF','blockers':[],
        'selected':{'machine':'office_desktop','task':'factor_batch','branch':packet['branch'],'current_branch':packet['branch']},
        'safety':{'factor_batch_allowed':False,'factor_batch_scope':{},'monthly_diagnostic_allowed':False,
            'household_diagnostic_allowed':False,'month_start_diagnostic_allowed':True,
            'month_start_diagnostic_scope':scheduler['month_start_diagnostic_decision'],
            'final_holdout_allowed':False,'live_boundary_allowed':False}}
    return packet,scheduler,gate,snapshots
