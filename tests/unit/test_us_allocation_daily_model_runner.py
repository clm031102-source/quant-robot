"""Artificial transport/controller structure, without market data or strategy runs."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/run_us_allocation_daily_model_observer.py'
spec=importlib.util.spec_from_file_location('us_model_runner_under_test',SCRIPT)
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


def scope_fixture(root):
    days=[(datetime(2026,11,9)+timedelta(days=i)).date().isoformat() for i in range(29)
          if (datetime(2026,11,9)+timedelta(days=i)).weekday()<5
          and (datetime(2026,11,9)+timedelta(days=i)).date().isoformat()!='2026-11-26']
    requests={}
    for day in ['warmup']+days:
        start,end=('2026-10-12','2026-11-07') if day=='warmup' else (day,(datetime.fromisoformat(day)+timedelta(days=1)).date().isoformat())
        at='2026-11-07T18:00:00Z' if day=='warmup' else day+('T18:15:00Z' if day=='2026-11-27' else 'T21:15:00Z')
        requests[day]=dict(urls={s:R.expected_url(s,start,end) for s in R.C.ASSETS},not_before=at,
            expires_at=(R.instant(at)+timedelta(minutes=5)).isoformat())
    return dict(schema='us_daily_model_capture_scope_v1',data_root=str(root),branch=R.BRANCH,
        symbols=list(R.C.ASSETS),maximum_GET=84,retry=0,redirect=0,max_body_bytes=R.CAP,socket_timeout_seconds=20,
        operation_dates=days,requests=requests,initial_cash='1000.00',live_trading_allowed=False,strict_real_forward_days=0)


class RunnerStructureTests(unittest.TestCase):
    def test_fixed_dates_windows_and_urls(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            scope=scope_fixture(Path(td));R.validate_scope(scope)
            for change in ('holiday','clock','url'):
                altered=deepcopy(scope)
                if change=='holiday':altered['operation_dates'][13]='2026-11-26'
                elif change=='clock':altered['requests']['2026-11-27']['not_before']='2026-11-27T21:15:00Z'
                else:altered['requests']['warmup']['urls']['SPY']+='&range=max'
                with self.subTest(change=change),self.assertRaises(ValueError):R.validate_scope(altered)

    def test_authority_is_acyclic_and_guard_rejects_later_change(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            root=Path(td);scope=scope_fixture(root)
            env=R.environment_record();env['python']='3.12.13'
            scope.update(HEAD='artificial-head',environment=env,bindings=[],manifests={r:R.save(root/(r+'.json'),dict(role=r,artificial=True)) for r in ('primary','stress')},
                authority_paths={k:str(root/(k+'.json')) for k in ('release','manager_review','root_review')})
            scope_ref=R.save(root/'scope.json',scope)
            reviews={r:R.save(scope['authority_paths'][r],dict(capture_scope_sha256=scope_ref['sha256'])) for r in ('manager_review','root_review')}
            R.save(scope['authority_paths']['release'],dict(capture_scope_sha256=scope_ref['sha256'],manifests=scope['manifests'],
                manager_review_sha256=reviews['manager_review']['sha256'],root_review_sha256=reviews['root_review']['sha256'],
                not_before='2026-11-07T00:00:00Z',expires_at='2026-12-08T00:00:00Z'))
            class Git:
                def __init__(self,text):self.stdout=text
            with patch.object(R.sys,'version','3.12.13 artificial'),patch.object(R,'utcnow',return_value=R.instant('2026-11-07T18:00:01Z')),\
                 patch.object(R.subprocess,'run',side_effect=lambda command,**kw:Git('artificial-head' if command[1]=='rev-parse' else R.BRANCH)),\
                 patch.object(R.M,'admitted_context',return_value=object()):
                *_,guard=R.load_authority(scope_ref['path'],scope_ref['sha256']);guard()
                Path(scope['authority_paths']['root_review']).write_bytes(b'{}')
                with self.assertRaises(ValueError):guard()

    def test_first_transport_failure_consumes_attempt_without_retry(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            root=Path(td);scope=scope_fixture(root)
            released=dict(artifact=dict(sha256='a'*64))
            item=(b'error',{},dict(HTTP_status=503,raw_complete=True,error='HTTP_503',HTTP_attempts_started=1),{})
            gate=dict(status='ready',selected=dict(current_branch=R.BRANCH),reading_summary=dict(read=7),safety={})
            with patch.object(R,'load_authority',return_value=(scope,released,dict(primary=object(),stress=object()),{},lambda:None)),\
                 patch.object(R,'utcnow',return_value=R.instant('2026-11-07T18:00:01Z')),\
                 patch('scripts.run_quant_pm_startup_gate.run_quant_pm_startup_gate',return_value=gate),\
                 patch.object(R.T,'fetch_one',return_value=item) as fetch:
                with self.assertRaisesRegex(ValueError,'source_request_failed'):R.operate('unused','a'*64,'initialize')
                self.assertEqual(fetch.call_count,1)
                with self.assertRaisesRegex(ValueError,'already_reserved_no_retry'):R.operate('unused','a'*64,'initialize')
                self.assertEqual(fetch.call_count,1)
            result=json.loads((root/'captures/warmup/outcome.json').read_bytes())
            self.assertEqual(result['status'],'failed_consumed_no_retry')
            self.assertFalse((root/'captures/warmup/numeric_exposure_started.json').exists())

    def test_missing_previous_day_stops_before_request(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            root=Path(td);scope=scope_fixture(root)
            with patch.object(R,'load_authority',return_value=(scope,{},dict(primary=object(),stress=object()),{},lambda:None)),\
                 patch.object(R,'utcnow',return_value=R.instant('2026-11-10T21:15:01Z')),\
                 patch.object(R.M,'status',return_value=dict(status='initialized_cash',ledger=dict(date='2026-11-06'))),\
                 patch.object(R.T,'fetch_one') as fetch:
                with self.assertRaises(FileNotFoundError):R.operate('unused','a'*64,'observe')
                fetch.assert_not_called()
            self.assertEqual(json.loads((root/'current_status.json').read_bytes())['status'],'blocked_before_source_request')

    def test_final_aggregate_keeps_positions_and_reads_bom_schedule(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            root=Path(td);scope=scope_fixture(root)
            (root/'schedule_registration.json').write_text(json.dumps(dict(schema='us_allocation_model_schedule_v1',installed=True,capture_scope_sha256='a'*64)),encoding='utf-8-sig')
            account=dict(ledger=dict(NAV='1030',balances=dict(cash='200',q=dict(SPY=1))),real_forward_days=0)
            with patch.object(R,'utcnow',return_value=R.instant('2026-12-07T21:16:00Z')):
                result=R.aggregate(scope,dict(primary=account,stress=account),'observation_window_completed_open_positions_retained',None,'2026-12-07','a'*64)
            self.assertEqual(result['accounts']['primary'],account)
            self.assertTrue(result['schedule']['installed']);self.assertIsNone(result['schedule']['next_capture_at'])
            self.assertEqual(result['strict_real_forward_days'],0)
            self.assertEqual(result['operation_window']['scheduled_sessions'],20)
            self.assertEqual(result['capture_scope_sha256'],'a'*64)
            with patch.object(R,'utcnow',return_value=R.instant('2026-12-07T21:16:00Z')):
                wrong=R.aggregate(scope,dict(primary=account,stress=account),'unchanged_model_state',None,'2026-12-07','b'*64)
            self.assertFalse(wrong['schedule']['installed'])

    def test_completed_outcome_cannot_hide_failed_final_publication(self):
        with tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
            root=Path(td);scope=scope_fixture(root)
            R.save(root/'captures/warmup/outcome.json',dict(status='completed'))
            R.save(root/'captures/warmup/finalization_failure.json',dict(status='failed_consumed_no_retry'))
            with patch.object(R,'load_authority',return_value=(scope,{},dict(primary=object(),stress=object()),{},lambda:None)),\
                 patch.object(R,'utcnow',return_value=R.instant('2026-11-09T21:15:01Z')),\
                 patch.object(R.M,'status',return_value=dict(status='initialized_cash',ledger=dict(date='2026-11-06'))),\
                 patch.object(R.T,'fetch_one') as fetch:
                with self.assertRaisesRegex(ValueError,'prior_finalization_failed_no_retry'):R.operate('unused','a'*64,'observe')
                fetch.assert_not_called()

    def test_final_artifact_drift_or_elapsed_window_cannot_close_success(self):
        for fault in ('claim_drift','elapsed'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as td,patch.object(R,'DATA',Path(td)):
                root=Path(td);scope=scope_fixture(root);now=[R.instant('2026-11-07T18:00:01Z')]
                contexts=dict(primary=object(),stress=object())
                manifests={r:dict(schedule={},authorities={}) for r in contexts}
                gate=dict(status='ready',selected=dict(current_branch=R.BRANCH),reading_summary=dict(read=7),safety={})
                def fetch(url,prefix,**kwargs):
                    raw=R.save(prefix.with_suffix('.raw'),b'artificial');request=R.save(prefix.with_name(prefix.name+'_request.json'),dict(artificial=True))
                    receipt=dict(HTTP_status=200,raw_complete=True,error=None,HTTP_attempts_started=1,request=request)
                    return b'artificial',raw,receipt,R.save(prefix.with_suffix('.receipt.json'),receipt)
                def packet(scope,manifest,key,captured,batch_ref,**kwargs):
                    return dict(purpose='warmup',records={s:dict(source_ref=captured[s][1]) for s in R.C.ASSETS})
                def normalize(*args,**kwargs):return dict(numeric_decode_marker=kwargs['before_numeric_decode'](),artificial_values=True)
                def advance(directory,*args,**kwargs):
                    commit=R.save(directory/'commit_artificial.json',dict(artificial=True))
                    if directory.name=='stress':
                        if fault=='claim_drift':(root/'captures/warmup/claim.json').write_bytes(b'changed')
                        else:now[0]=R.instant(scope['requests']['warmup']['expires_at'])
                    return dict(status='initialized_cash',committed_ref=commit,committed_at='2026-11-07T18:00:02Z')
                with patch.object(R,'load_authority',return_value=(scope,dict(artifact=dict(sha256='a'*64)),contexts,manifests,lambda:None)),\
                     patch.object(R,'utcnow',side_effect=lambda:now[0]),\
                     patch('scripts.run_quant_pm_startup_gate.run_quant_pm_startup_gate',return_value=gate),\
                     patch.object(R.T,'fetch_one',side_effect=fetch),patch.object(R.T,'build_source_packet',side_effect=packet),\
                     patch.object(R.C,'normalize_yahoo_sources',side_effect=normalize),patch.object(R.M,'create'),\
                     patch.object(R.M,'advance_normalized',side_effect=advance):
                    with self.assertRaisesRegex(ValueError,'bound_file_changed' if fault=='claim_drift' else 'finalization_window_expired'):
                        R.operate('unused','a'*64,'initialize')
                self.assertEqual(json.loads((root/'captures/warmup/outcome.json').read_bytes())['status'],'failed_consumed_no_retry')


if __name__=='__main__':unittest.main()
