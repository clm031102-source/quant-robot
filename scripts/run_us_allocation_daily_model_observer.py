"""Finite public daily observations for the conditional USD model; never orders."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.ops import us_allocation_source_contract as C
from quant_robot.ops import us_allocation_daily_model_observer as M
from quant_robot.ops import us_allocation_model_capture as T

CHECKOUT = Path(__file__).resolve().parents[1]
DATA = Path('F:/lhjqr/data/reports/us_allocation_model_20261109_20261207')
BRANCH = 'codex/factor-review-us-paper-source-20261107'
CAP = 4 * 1024 * 1024


def require(ok, code):
    if not ok: raise ValueError(code)


def utcnow(): return datetime.now(timezone.utc)
def instant(value):
    result = C._instant(value)
    require(result is not None, 'UTC_clock')
    return result
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def reference(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), sha256=digest(raw), bytes=len(raw))
def bound(ref):
    require(C._ref(ref), 'exact_reference')
    path = Path(ref['path']).resolve(); raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'bound_file_changed')
    return raw
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else canonical(value)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    require(path.read_bytes() == raw, 'published_bytes_changed')
    return dict(path=str(path.resolve()), sha256=digest(raw), bytes=len(raw))


def environment_record():
    versions={}
    for package in ('numpy','pandas','tzdata'):
        try:versions[package]=metadata.version(package)
        except metadata.PackageNotFoundError:versions[package]=None
    return dict(python=sys.version.split()[0],executable=reference(sys.executable),
                decimal=M.kernel.context_record(M.kernel.CONTEXT),**versions)


def expected_url(symbol, start, end):
    require(symbol in C.ASSETS, 'symbol')
    start = int(instant(start + 'T00:00:00Z').timestamp())
    end = int(instant(end + 'T00:00:00Z').timestamp())
    return (f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}'
            '&interval=1d&events=div%2Csplits%2CcapitalGains&includeAdjustedClose=true')


def validate_scope(scope):
    require(scope.get('schema') == 'us_daily_model_capture_scope_v1' and scope.get('data_root') == str(DATA), 'fixed_scope')
    require(scope.get('branch') == BRANCH and scope.get('symbols') == list(C.ASSETS), 'fixed_identity')
    require(scope.get('maximum_GET') == 84 and scope.get('retry') == 0 and scope.get('redirect') == 0
            and scope.get('max_body_bytes') == CAP and scope.get('socket_timeout_seconds') == 20, 'fixed_budget')
    days = scope['operation_dates']
    expected_days = [(instant('2026-11-09T00:00:00Z')+timedelta(days=i)).date().isoformat()
                     for i in range(29) if (instant('2026-11-09T00:00:00Z')+timedelta(days=i)).weekday()<5
                     and (instant('2026-11-09T00:00:00Z')+timedelta(days=i)).date().isoformat()!='2026-11-26']
    require(days == expected_days, 'fixed_operation_window')
    require(set(scope['requests']) == {'warmup', *days}, 'request_groups')
    for key, request in scope['requests'].items():
        require(set(request['urls']) == set(C.ASSETS), 'request_symbols')
        if key == 'warmup': start, end = '2026-10-12', '2026-11-07'
        else:
            start = key; end = (instant(key + 'T00:00:00Z') + timedelta(days=1)).date().isoformat()
        require(request['urls'] == {s:expected_url(s,start,end) for s in C.ASSETS}, 'exact_URLs')
        start_clock, end_clock = instant(request['not_before']), instant(request['expires_at'])
        if key == 'warmup':
            require(instant('2026-11-06T21:00:00Z') <= start_clock < end_clock
                    <= instant('2026-11-09T14:30:00Z'), 'warmup_window')
        else:
            expected_clock=instant(key+('T18:15:00Z' if key=='2026-11-27' else 'T21:15:00Z'))
            require(start_clock==expected_clock and end_clock==expected_clock+timedelta(minutes=5),'exact_daily_window')
    require(scope.get('initial_cash') == '1000.00' and scope.get('live_trading_allowed') is False
            and scope.get('strict_real_forward_days') == 0, 'paper_only')
    return scope


def load_authority(scope_path, scope_sha):
    raw = Path(scope_path).read_bytes(); require(digest(raw) == scope_sha, 'scope_hash')
    scope = validate_scope(json.loads(raw))
    # Scope contains paths only. Reviews bind its full byte SHA; the independent
    # root release pins those reviews. No artifact contains its own hash cycle.
    paths = scope['authority_paths']
    require(set(paths)=={'release','manager_review','root_review'},'authority_paths')
    require(all(Path(p).resolve().is_relative_to(DATA.resolve()) for p in paths.values()),'authority_path_boundary')
    refs = {key:reference(path) for key,path in paths.items()}
    release = json.loads(bound(refs['release']))
    for key in ('release', 'manager_review', 'root_review'):
        value = json.loads(bound(refs[key]))
        require(value.get('capture_scope_sha256') == scope_sha, 'capture_scope_release_binding')
    require(release.get('manifests') == scope['manifests'], 'exact_role_manifests')
    require(release.get('manager_review_sha256')==refs['manager_review']['sha256']
            and release.get('root_review_sha256')==refs['root_review']['sha256'],'review_pins')
    require(sys.version.split()[0] == '3.12.13', 'interpreter_version')
    require(scope['environment']==environment_record(),'frozen_environment')
    def guard():
        require(Path(scope_path).read_bytes() == raw, 'scope_changed')
        for ref in scope['bindings'] + list(refs.values()) + list(scope['manifests'].values()): bound(ref)
        head = subprocess.run(['git','rev-parse','HEAD'], cwd=CHECKOUT, text=True, capture_output=True, check=True).stdout.strip()
        branch = subprocess.run(['git','symbolic-ref','--short','HEAD'], cwd=CHECKOUT, text=True, capture_output=True, check=True).stdout.strip()
        require(head == scope['HEAD'] and branch == BRANCH, 'frozen_checkout')
        require(instant(release['not_before']) <= utcnow() < instant(release['expires_at']), 'release_window')
    guard()
    contexts = {role:M.admitted_context(Path('F:/lhjqr'), ref, refs['release'], refs['manager_review'], refs['root_review'])
                for role,ref in scope['manifests'].items()}
    manifests = {role:json.loads(bound(ref)) for role,ref in scope['manifests'].items()}
    require(set(contexts) == {'primary','stress'}, 'two_cost_roles')
    return scope, dict(release, artifact=refs['release']), contexts, manifests, guard


def aggregate(scope, accounts, status, reason, key, capture_scope_sha256):
    schedule_state={}
    schedule_path=DATA/'schedule_registration.json'
    if schedule_path.exists():
        saved=json.loads(schedule_path.read_bytes())
        if saved.get('schema')=='us_allocation_model_schedule_v1' and saved.get('capture_scope_sha256')==capture_scope_sha256:schedule_state=saved
    current=utcnow()
    following=[scope['requests'][d]['not_before'] for d in scope['operation_dates']
               if instant(scope['requests'][d]['not_before'])>current]
    value = dict(schema='us_allocation_model_operations_v1',updated_at=utcnow().isoformat(),status=status,reason=reason,capture_scope_sha256=capture_scope_sha256,
        operation_window=dict(start=scope['operation_dates'][0],end=scope['operation_dates'][-1],scheduled_sessions=len(scope['operation_dates'])),
        accounts=accounts,schedule=dict(installed=schedule_state.get('installed') is True,next_capture_at=following[0] if following else None,
            last_attempt_at=utcnow().isoformat(),last_attempt_status=status),last_operation=key,strict_real_forward_days=0)
    temp=DATA/'current_status.next'; final=DATA/'current_status.json'
    save(temp,value);os.replace(temp,final);require(final.read_bytes()==canonical(value),'status_publication')
    return value


def operate(scope_path, scope_sha, action):
    scope,release,contexts,manifests,guard=load_authority(scope_path,scope_sha)
    now=utcnow();key='warmup' if action=='initialize' else next((d for d in scope['operation_dates']
        if instant(scope['requests'][d]['not_before'])<=now<instant(scope['requests'][d]['expires_at'])),None)
    require(key is not None,'no_current_scheduled_window')
    request=scope['requests'][key]
    require(instant(request['not_before'])<=now<instant(request['expires_at']),'operation_window')
    directory=DATA/'captures'/key
    require(not directory.exists(),'already_reserved_no_retry')
    accounts={}
    try:
        if key!='warmup':
            accounts={role:M.status(DATA/'journals'/role,context=contexts[role]) for role in contexts}
            previous=['warmup']+scope['operation_dates'][:scope['operation_dates'].index(key)]
            for day in previous:
                require(not (DATA/'captures'/day/'finalization_failure.json').exists(),'prior_finalization_failed_no_retry')
                record=json.loads((DATA/'captures'/day/'outcome.json').read_bytes())
                require(record['status']=='completed','prior_operation_missing_or_failed_no_backfill')
            require(all(not x['status'].startswith('blocked') for x in accounts.values()),'model_continuity_blocked')
        else: require(all(not (DATA/'journals'/role).exists() for role in contexts),'journals_already_exist')
    except Exception as exc:
        aggregate(scope,accounts,'blocked_before_source_request',type(exc).__name__+': '+str(exc),key,scope_sha)
        raise
    try:
        from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
        gate=run_quant_pm_startup_gate(machine='office_desktop',task='factor_review',branch=BRANCH,output_dir=DATA/'startup_gates'/key)
        require(gate['status']=='ready' and gate['selected']['current_branch']==BRANCH and gate['reading_summary']['read']==7,'fresh_PM')
        require(not any(value is True for name,value in gate.get('safety',{}).items() if name.endswith('_allowed')),'unrelated_permission_open')
        guard();require(utcnow()<instant(request['expires_at']),'claim_window_expired')
    except Exception as exc:
        aggregate(scope,accounts,'blocked_before_source_request',type(exc).__name__+': '+str(exc),key,scope_sha)
        raise
    directory.mkdir(parents=True)
    claim_ref=save(directory/'claim.json',dict(scope_sha256=scope_sha,operation=key,claimed_at=utcnow().isoformat(),maximum_GET=4,release_sha256=release['artifact']['sha256']))
    captured={};normalized=None
    try:
        for symbol in C.ASSETS:
            guard();require(utcnow()<instant(request['expires_at']),'capture_window_expired')
            item=T.fetch_one(request['urls'][symbol],directory/symbol.lower(),deadline_at=request['expires_at']);captured[symbol]=item
            require(item[2]['HTTP_status']==200 and item[2]['raw_complete'] and item[2]['error'] is None,'source_request_failed')
        manifest_ref=save(directory/'sources.json',{s:dict(raw=x[1],receipt=x[3]) for s,x in captured.items()})
        prior=accounts.get('primary')
        packet=T.build_source_packet(scope,manifests['primary'],key,captured,manifest_ref,
            prior_session_date=None if prior is None else prior['ledger']['date'],
            prior_committed_ref=None if prior is None else prior['committed_ref'],
            prior_committed_at=None if prior is None else prior['committed_at'])
        packet_ref=save(directory/'source_metadata.json',packet)
        context=C._SourceDecodeContext(packet['purpose'],C._digest(packet),C._digest({s:packet['records'][s]['source_ref'] for s in C.ASSETS}),
                                       release['artifact']['sha256'],'conditional_provider_observation')
        def marker():
            guard();require(utcnow()<instant(request['expires_at']),'normalization_window_expired')
            return save(directory/'numeric_exposure_started.json',dict(started_at=utcnow().isoformat(),purpose=packet['purpose'],
                research_count_delta=0,model_only=True,strict_real_forward_days=0,source_refs={s:x[1] for s,x in captured.items()}))
        normalized=C.normalize_yahoo_sources({s:x[0] for s,x in captured.items()},packet,manifests['primary']['schedule'],
            authorities=manifests['primary']['authorities'],context=context,before_numeric_decode=marker)
        normalized_ref=save(directory/'normalized_input.json',normalized)
        for role in ('primary','stress'):
            if key=='warmup': M.create(DATA/'journals'/role,manifests[role],context=contexts[role])
            accounts[role]=M.advance_normalized(DATA/'journals'/role,normalized,context=contexts[role])
            require(not accounts[role]['status'].startswith('blocked'),'normalized_model_transition_blocked')
        guard();require(utcnow()<instant(request['expires_at']),'finalization_window_expired')
        for raw,ref,receipt,receipt_ref in captured.values():bound(ref);bound(receipt_ref)
        execution_refs=[claim_ref,manifest_ref,packet_ref,normalized_ref,normalized['numeric_decode_marker']]
        for ref in execution_refs:bound(ref)
        for account in accounts.values():bound(account['committed_ref'])
        outcome=dict(status='completed',operation=key,finished_at=utcnow().isoformat(),GET_attempts_started=sum(x[2]['HTTP_attempts_started'] for x in captured.values()),normalized=normalized_ref,
            execution_artifacts=execution_refs,model_only=True,strict_real_forward_days=0,accounts={r:dict(committed_ref=s['committed_ref'],committed_at=s['committed_at']) for r,s in accounts.items()})
        save(directory/'outcome.json',outcome)
        status='initialized_waiting_for_next_completed_session' if key=='warmup' else 'completed_model_observation'
        if key==scope['operation_dates'][-1]:status='observation_window_completed_open_positions_retained'
        return aggregate(scope,accounts,status,None,key,scope_sha)
    except Exception as exc:
        # A publication failure must never overwrite an already closed outcome.
        failed=directory/('finalization_failure.json' if (directory/'outcome.json').exists() else 'outcome.json')
        receipts=[x[2] for x in captured.values()]
        save(failed,dict(status='failed_consumed_no_retry',operation=key,finished_at=utcnow().isoformat(),
            GET_attempts_confirmed=sum(x['HTTP_attempts_started'] for x in receipts),
            complete_attempt_count_known=len(list(directory.glob('*_request.json')))==len(captured),
            error_type=type(exc).__name__,reason=str(exc),strict_real_forward_days=0))
        aggregate(scope,accounts,'blocked_no_retry',str(exc),key,scope_sha)
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('preview','initialize','observe'))
    parser.add_argument('--scope',required=True);parser.add_argument('--scope-sha',required=True)
    args=parser.parse_args(argv)
    if args.action=='preview':
        scope,*_=load_authority(args.scope,args.scope_sha)
        print(json.dumps(dict(status='admitted_not_executed',GET=0,numeric_decode=False,operating_days=len(scope['operation_dates']))));return 0
    value=operate(args.scope,args.scope_sha,args.action)
    print(json.dumps(dict(status=value['status'],strict_real_forward_days=0)))
    return 0


if __name__=='__main__':raise SystemExit(main())
