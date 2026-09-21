"""Complete claimed fiscal-to-account path on artificial sources and prices."""
import calendar
from datetime import date, timedelta, datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_etf_research_price_basis_drill import _bars
from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar
from quant_robot.research.fiscal_study_inputs import CALENDAR, CALENDAR_MANIFEST, ACTIONS, BARS, ASSET
from quant_robot.research.fiscal_study_registration import (
    DIRECTORY, REVIEW_PATH, PROPOSAL_PATH, build_registration, expected_admission,
)
from quant_robot.research.fiscal_study_execution import execute_registration
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, write_exclusive_json


def full_fixture(root):
    snapshots={}
    def put(path,value):
        raw=value if isinstance(value,bytes) else canonical(value)
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);snapshots[path]=raw
    sessions=[x.date() for x in pd.bdate_range('2020-01-02','2024-06-28')]
    calendar_frame=pd.DataFrame({'date':sessions,'is_open':1})
    frame,manifest=build_cn_trading_calendar({'SSE':calendar_frame,'SZSE':calendar_frame},
        start_date='2015-01-01',end_date='2025-12-31')
    put(CALENDAR,frame.to_csv(index=False).encode())
    manifest['artifact']={'path':CALENDAR,'sha256':sha256(snapshots[CALENDAR]),'size_bytes':len(snapshots[CALENDAR])}
    put(CALENDAR_MANIFEST,manifest)
    put(ACTIONS,{'schema_version':3,'source_ref':'synthetic fixture','asset_ids':[ASSET],
        'coverage_start':str(sessions[0]),'coverage_end':str(sessions[-1]),'events':[]})
    template=_bars([4]*6).iloc[[0]]
    for year in range(2020,2025):
        days=[day for day in sessions if day.year==year]
        frame=pd.concat([template]*len(days),ignore_index=True)
        frame['date'],frame['timestamp']=days,pd.to_datetime(days)
        frame['amount'],frame['volume']=4_000_000,1_000_000
        stream=io.BytesIO();frame.to_parquet(stream,index=False);put(BARS.format(year=year),stream.getvalue())
    proposal=(Path(__file__).resolve().parents[2]/PROPOSAL_PATH).read_bytes();put(PROPOSAL_PATH,proposal)
    months,annual,rows={},{},[]
    excluded={'2020-02','2020-03','2020-04','2020-07','2024-05'}
    for year in range(2019,2025):
        annual[str(year)]={'year':year,'amount_cny_100m':'10000','published_date_label':f'{year}-03-01',
                          'reference_semantics':'initial_annual_report_plan'}
        for month in range(2,6 if year==2024 else 13):
            period=f'{year}-{month:02d}';end=date(year,month,calendar.monthrange(year,month)[1])
            published=end+timedelta(days=15)
            observation={'period_start':f'{year}-01-01','period_end':str(end),'scope':'national_general_public_budget',
                'source_value_semantics':'cumulative_from_january','published_date_label':str(published),
                'amount_cny_100m':str(month*100+(year-2019)*10)}
            path=f'data/reports/fiscal_fixture/{period}.json';put(path,{'observation':observation})
            months[period]={'observation_path':path}
            if year==2019:continue
            if period in excluded:
                rows.append({'period':period,'source_and_calendar_eligible':False,'exclusions':['fixture_predeclared_exclusion']})
                continue
            index=next(i for i,day in enumerate(sessions) if day>published)
            rows.append({'period':period,'source_and_calendar_eligible':True,'exclusions':[],
                'assumed_entry_day':str(sessions[index]),'scheduled_exit_day':str(sessions[index+20])})
    eligibility='data/reports/fiscal_fixture/eligibility.json';put(eligibility,{'rows':rows})
    review={'status':'conditional_source_use_reviewed_not_admitted','economic_hypothesis_id':'general_public_budget_execution_pace_v1',
        'source_fingerprints':{path:sha256(raw) for path,raw in snapshots.items()},
        'monthly_sources':months,'annual_references':annual,'eligibility_manifest_path':eligibility,
        **{key:False for key in ('source_audit_verified','historical_availability_verified','research_admission_granted',
                                'local_ETF_price_columns_decoded','real_fiscal_ratios_computed','net_account_cash_verified')}}
    put(REVIEW_PATH,review)
    code=root/'fixture.py';code.write_bytes(b'# synthetic fixture')
    packet=build_registration(inputs={path:sha256(raw) for path,raw in snapshots.items()},
        code_files={'fixture.py':sha256(code.read_bytes())},environment={'python':'fixture'},
        source_origin='synthetic_fixture',branch='codex/factor-review-fixture')
    write_exclusive_json(root/DIRECTORY/'registration.json',packet)
    scope=expected_admission(packet,sha256(canonical(packet)))
    gate={'status':'ready','mode':'single_fiscal_event_account_only','primary_market':'CN_ETF','blockers':[],
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'selected':{'machine':'office_desktop','task':'factor_batch','branch':packet['branch'],'current_branch':packet['branch']},
        'safety':{'fiscal_event_account_allowed':True,'fiscal_event_account_scope':scope,'factor_batch_scope':{},
            **{key:False for key in ('factor_batch_allowed','monthly_diagnostic_allowed','household_diagnostic_allowed',
                                    'month_start_diagnostic_allowed','final_holdout_allowed','live_boundary_allowed')}}}
    return packet,{'fiscal_event_account_decision':scope},gate


class FiscalStudyPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp=tempfile.TemporaryDirectory();cls.addClassCleanup(temp.cleanup);cls.root=Path(temp.name)
        packet,scheduler,gate=full_fixture(cls.root)
        from quant_robot.research.fiscal_execution_gate import evaluate_fiscal_gate
        read_parquet=pd.read_parquet
        def after_claim(function):
            def call(*args,**kwargs):
                if not (cls.root/DIRECTORY/'attempt_claim.json').is_file():raise AssertionError('calculation before claim')
                return function(*args,**kwargs)
            return call
        with patch('quant_robot.research.fiscal_study_inputs.evaluate_fiscal_gate',side_effect=after_claim(evaluate_fiscal_gate)), \
                patch('pandas.read_parquet',side_effect=after_claim(read_parquet)):
            cls.result=execute_registration(root=cls.root,scheduler=scheduler,gate_supplier=lambda:gate,environment={'python':'fixture'})

    def test_all_frozen_periods_are_accounted_for_without_dropping_failures(self):
        self.assertEqual(self.result['observation_count'],48)
        self.assertEqual(self.result['eligible_periods'],43)
        self.assertEqual(self.result['selected_signal_periods'],43)
        self.assertEqual(sum(row['status']=='excluded_before_factor' for row in self.result['fiscal_observations']),5)

    def test_equal_selected_and_unconditional_schedules_cannot_create_excess_profit(self):
        result=self.result['primary_decision']
        self.assertEqual(result['selected_minus_unconditional_pnl_cny'],0)
        self.assertLess(result['selected_pnl_cny'],0)
        self.assertEqual(result['decision'],'fixed_contract_not_passed')
        self.assertFalse(self.result['formal_positive_ev_verified'])
        self.assertEqual(self.result['counts_as_forward_paper_days'],0)

    def test_annual_contributions_reconcile_and_result_has_durable_completion(self):
        for scenario in self.result['scenarios'].values():
            for role in ('selected','unconditional'):
                account=scenario[role]
                self.assertAlmostEqual(sum(account['annual_pnl_cny'].values()),account['metrics']['pnl_cny'])
                self.assertTrue(account['risk']['terminal_settled'])
        outcome=json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['status'],'completed')
        self.assertEqual(outcome['result_sha256'],sha256((self.root/DIRECTORY/'result.json').read_bytes()))


if __name__=='__main__':unittest.main()
