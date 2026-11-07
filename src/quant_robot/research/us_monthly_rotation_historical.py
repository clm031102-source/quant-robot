"""Once-only US rotation controller; preview hashes sources, execute requires two reviews."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, subprocess
from quant_robot.research import equity_gold_constant_mix_admission as U
from quant_robot.ops.paper_evidence_session import _PM_FILES
from quant_robot.research.monthly_diagnostic_registration import canonical as persisted_bytes

# Independent repair attempt: the pre-numeric original attempt/claim remain immutable.
DIRECTORY='data/reports/campaign_72h_20261106/us_monthly_rotation_repair1_accounts'
DESIGN='data/reports/campaign_72h_20261106/manager/us_multi_asset_20261107'
METHOD=DESIGN+'/contract_v2.json'
METHOD_SHA='dbc19912feded581fd55c4a5e0aa992140e3dfa4743586df2cd3a00c83e04a30'
MANIFEST=DESIGN+'/source_manifest_v1.json'
MANIFEST_SHA='9e3cde59e3d6a4412a0bcfd6f89ec411fb1fd5001a637c5abbc64fde6e7e2417'
BRANCH='codex/factor-review-72h-campaign-20261106'
NEW_FILES=(
 'src/quant_robot/research/us_monthly_rotation.py',
 'src/quant_robot/research/us_monthly_rotation_inputs.py',
 'src/quant_robot/research/us_monthly_rotation_historical.py',
 'src/quant_robot/research/us_monthly_rotation_verification.py',
 'scripts/run_us_monthly_rotation_historical.py',
 'tests/unit/test_us_monthly_rotation.py',
 'tests/unit/test_us_monthly_rotation_inputs.py',
 'tests/unit/test_us_monthly_rotation_historical.py',
 'tests/unit/test_us_monthly_rotation_verification.py',
)
CODE_FILES=tuple(sorted(set(_PM_FILES)|set(NEW_FILES)|{
 'src/quant_robot/research/equity_gold_constant_mix_admission.py',
 'src/quant_robot/research/monthly_diagnostic_registration.py'}))
PM_INPUTS=dict(U.PM_INPUTS)
POLICY=dict(method='us_four_asset_monthly_positive_top2_v1',market='US_ETF',currency='USD',
    initial_cash='1000.00',assets=['SPY','EFA','IEF','GLD'],source_start='2004-12-01',source_end='2024-12-31',
    first_decision='2005-12-30',first_sell='2006-01-03',first_buy='2006-01-06',terminal_open='2024-12-31',
    policies=['rotation','positive_equal','fixed_quarters'],costs=[[m,s] for m in ('0.35','1.00','2.50') for s in (0,10,30)],
    account_count=28,cash_count=1,max_executions=1,qualified=False,real_forward=0,conditional_only=True,
    source_year2025_prices_allowed=False,source_year2026_prices_allowed=False,live_boundary_allowed=False)
canonical=U.canonical
digest=U.digest
resolve_path=U.resolve_path

def require(value,reason):
    if not value: raise ValueError(reason)

def now(): return datetime.now(timezone.utc)

def _time(value):
    x=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(x.tzinfo is not None,'aware_clock')
    return x.astimezone(timezone.utc)

def _read(root,ref):
    return U.read_bound(root,{'path':ref['path'],'sha256':ref['sha256']},return_bytes=True)

def _ref(root,p): return dict(path=p,sha256=U.file_digest(resolve_path(root,p)))

def _json(raw): return U._json(raw)

def _persist(root,p,value):
    expected=persisted_bytes(value)
    U.write_exclusive_json(resolve_path(root,p),value)
    require(resolve_path(root,p).read_bytes()==expected,'persisted_bytes_changed')
    return dict(path=p,sha256=digest(expected))

def _branch(root):
    return subprocess.run(['git','symbolic-ref','--short','HEAD'],cwd=root,
        check=True,capture_output=True,text=True,timeout=10).stdout.strip()

def _inputs(root):
    manifest=_json(_read(root,dict(path=MANIFEST,sha256=MANIFEST_SHA)))
    refs={}
    def walk(x):
        if isinstance(x,dict):
            if set(x)=={'path','sha256','bytes'}:
                raw=_read(root,x); require(len(raw)==x['bytes'],'source_size')
                if x['path'] in refs: require(refs[x['path']]['sha256']==x['sha256'],'alias_hash')
                refs[x['path']]={'path':x['path'],'sha256':x['sha256']}
            else:
                for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(manifest)
    require(len(refs)==23,'fixed_23_source_roles')
    require(refs.get(METHOD)==dict(path=METHOD,sha256=METHOD_SHA),'fixed_method')
    inputs={'source_manifest':dict(path=MANIFEST,sha256=MANIFEST_SHA)}
    inputs.update({f'source_{i:02d}':refs[p] for i,p in enumerate(sorted(refs))})
    inputs.update({role:_ref(root,path) for role,path in PM_INPUTS.items()})
    require(len({p['path'] for p in inputs.values()})==len(inputs),'input_path_alias')
    return inputs

def _protocols(root,inputs):
    cfg=_json(_read(root,inputs['pm_policy']))
    paths=[x['path'] for x in cfg['required_reading']]
    require(len(paths)==len(set(paths))==7,'exact7protocols')
    return {p:_ref(root,p) for p in paths}

def build_registration(root,*,study_number):
    require(type(study_number) is int and study_number>25,'new_study_number')
    inputs=_inputs(root)
    packet=dict(artifact_type='us_monthly_rotation_registration_v1',branch=BRANCH,
        input_manifest=dict(path=MANIFEST,sha256=MANIFEST_SHA),inputs=inputs,
        implementation={p:_ref(root,p) for p in CODE_FILES},protocols=_protocols(root,inputs),
        environment=U.runtime_environment(),policy=dict(POLICY,study_number=study_number))
    packet['registration_sha256']=digest(canonical(packet))
    return validate_registration(root,packet)

def validate_registration(root,p):
    require(set(p)=={'artifact_type','branch','input_manifest','inputs','implementation','protocols','environment','policy','registration_sha256'},'registration_schema')
    require(p['artifact_type']=='us_monthly_rotation_registration_v1' and p['branch']==BRANCH
        and p['input_manifest']==dict(path=MANIFEST,sha256=MANIFEST_SHA),'fixed_registration')
    require(p['registration_sha256']==digest(canonical({k:v for k,v in p.items() if k!='registration_sha256'})),'registration_hash')
    number=p['policy'].get('study_number')
    require(type(number) is int and number>25 and p['policy']==dict(POLICY,study_number=number),'fixed_policy')
    require(p['inputs']==_inputs(root),'fixed_input_set')
    require(set(p['implementation'])==set(CODE_FILES),'implementation_set')
    for path,ref in p['implementation'].items():
        require(ref['path']==path,'implementation_alias');_read(root,ref)
    require(p['protocols']==_protocols(root,p['inputs']),'protocol_set')
    env=U.runtime_environment()
    require(p['environment']==env and env['python']=='3.12.13','frozen_runtime')
    campaign=_json(_read(root,p['inputs']['campaign']))
    require(campaign['status']=='active' and campaign['task_branch']==BRANCH
        and campaign['machine']=='office_desktop'
        and _time(campaign['started_at'])<=now()<_time(campaign['delivery_deadline'])
        and campaign['live_boundary_allowed'] is False and campaign['holdout_unsealing_authorized'] is False,'active_closed_live_campaign')
    return p

def require_unused(root):
    directory=resolve_path(root,DIRECTORY)
    require(not any((directory/name).exists() for name in
        ('attempt_claim.json','financial_decode_started.json','decoded_input.json','accounts','statistics.json','result.json','outcome.json','guard_checks')),'attempt_already_reserved')

def admitted(root,*,unused=True):
    registration_ref=_ref(root,DIRECTORY+'/registration.json')
    p=validate_registration(root,_json(_read(root,registration_ref)))
    require(_branch(root)==BRANCH,'actual_branch')
    refs={}
    for name,reviewer in (('manager_review','quant_manager_72h'),('root_review','root')):
        ref=_ref(root,DIRECTORY+'/'+name+'.json');r=_json(_read(root,ref))
        require(r.get('status')=='accepted_for_one_conditional_us_monthly_rotation'
            and r.get('reviewer')==reviewer and r.get('registration_sha256')==p['registration_sha256']
            and r.get('method_sha256')==METHOD_SHA and r.get('qualified') is False,'independent_review')
        refs[name]=ref
    release_ref=_ref(root,DIRECTORY+'/release.json')
    release=_json(_read(root,release_ref))
    require(release.get('status')=='authorized_one_us_monthly_rotation'
        and release.get('registration_sha256')==p['registration_sha256']
        and release.get('manager_review_sha256')==refs['manager_review']['sha256']
        and release.get('root_review_sha256')==refs['root_review']['sha256']
        and release.get('max_executions')==1
        and _time(release['not_before'])<=now()<=_time(release['expires_at']),'exact_fresh_release')
    if unused:require_unused(root)
    return p,dict(refs,release=release_ref,registration=registration_ref)

def _gate(root,p,gate):
    require(gate.get('status')=='ready','PM_ready')
    selected=gate.get('selected',{})
    require(selected.get('machine')=='office_desktop' and selected.get('task')=='factor_review'
        and selected.get('current_branch')==BRANCH and selected.get('branch')==BRANCH,'PM_context')
    require(0<=(now()-_time(gate['generated_at'])).total_seconds()<=120,'fresh_PM')
    readings={x['path']:x for x in gate['required_reading']}
    require(set(readings)==set(p['protocols']),'PM_reading_set')
    for path,ref in p['protocols'].items():
        raw=_read(root,ref)
        normalized=raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n').encode()
        require(readings[path]['sha256']==digest(normalized),'PM_normalized_reading')
    require(not any(v is True for k,v in gate.items() if k.endswith('_allowed')),'PM_old_permissions_closed')

def _financial_modules(root):
    from quant_robot.research import us_monthly_rotation as M
    from quant_robot.research import us_monthly_rotation_inputs as I
    for module,path in ((M,NEW_FILES[0]),(I,NEW_FILES[1])):
        require(Path(module.__file__).resolve()==resolve_path(root,path),'financial_module_origin')
    return M,I

def execute(root,*,expected_registration_sha256,gate_supplier):
    root=Path(root).resolve()
    p,authority=admitted(root)
    require(p['registration_sha256']==expected_registration_sha256,'expected_registration')
    gate=gate_supplier()
    _gate(root,p,gate)
    gate_ref=_persist(root,DIRECTORY+'/execution_startup_gate.json',gate)
    _persist(root,DIRECTORY+'/attempt_claim.json',dict(registration_sha256=expected_registration_sha256,
        claimed_at=now().isoformat(),authority=authority,gate=gate_ref,max_executions=1))
    guards=[];decoded=False
    def guard(stage):
        validate_registration(root,p)
        for ref in authority.values():_read(root,ref)
        require(_branch(root)==BRANCH,'execution_branch_changed')
        guards.append(_persist(root,DIRECTORY+f'/guard_checks/{len(guards):03d}.json',dict(stage=stage,checked_at=now().isoformat(),registration_sha256=expected_registration_sha256)))
    def marker():
        nonlocal decoded
        require(not decoded,'duplicate_numeric_marker');guard('before_numeric_decode')
        ref=_persist(root,DIRECTORY+'/financial_decode_started.json',dict(
            registration_sha256=expected_registration_sha256,study_number=p['policy']['study_number'],
            started_at=now().isoformat(),research_scope_consumed=True,accounts_completed=0))
        decoded=True
        return ref
    try:
        guard('claim_complete')
        # These financial modules are imported only after exact authority + once claim.
        M,I=_financial_modules(root)
        manifest=_json(_read(root,p['input_manifest']))
        fixture=I.load_inputs(root,manifest,method_sha256=METHOD_SHA,
            registration_sha256=expected_registration_sha256,before_numeric_decode=marker)
        snapshot=_persist(root,DIRECTORY+'/decoded_input.json',fixture)
        context=M._ExecutionContext('known_history_conditional',METHOD_SHA,M.digest(fixture),
            M.digest(fixture['provenance']),expected_registration_sha256)
        prepared=M.prepare(fixture,context=context)
        accounts={};annual={}
        for minimum,slip in M.COSTS:
            cost=f'min{minimum}_slip{slip}';annual[cost]={}
            for policy in M.POLICIES:
                key=cost+'/'+policy;guard('before_'+key)
                account=M.run_prepared(prepared,policy,minimum,slip,context=context)
                artifact=_persist(root,DIRECTORY+'/accounts/'+key+'/account.json',account)
                completion=_persist(root,DIRECTORY+'/accounts/'+key+'/complete.json',dict(
                    status='complete',account_id=key,artifact=artifact,registration_sha256=expected_registration_sha256,
                    finished_at=now().isoformat()))
                accounts[key]=dict(artifact=artifact,completion=completion,summary=account['summary'])
                annual[cost][policy]=account['annual_contributions']
                guard('after_'+key)
        guard('before_cash')
        cash=M.run_prepared(prepared,'cash','0.35',0,context=context)
        artifact=_persist(root,DIRECTORY+'/accounts/cash/account.json',cash)
        completion=_persist(root,DIRECTORY+'/accounts/cash/complete.json',dict(status='complete',account_id='cash',
            artifact=artifact,registration_sha256=expected_registration_sha256,finished_at=now().isoformat()))
        accounts['cash']=dict(artifact=artifact,completion=completion,summary=cash['summary'])
        guard('after_cash')
        statistics=_persist(root,DIRECTORY+'/statistics.json',M.fixed_statistics(annual,context=context))
        guard('all_accounts_complete')
        result=dict(artifact_type='us_monthly_rotation_result_v1',status='completed_conditional_historical',
            registration_sha256=expected_registration_sha256,study_number=p['policy']['study_number'],
            method_sha256=METHOD_SHA,historical_returns_computed=True,conditional_only=True,qualified=False,real_forward=0,
            account_count=28,all_accounts_complete=True,decoded_input_artifact=snapshot,
            decoded_input_canonical_sha256=M.digest(fixture),accounts=accounts,statistics_artifact=statistics,guard_checks=guards,
            finished_at=now().isoformat())
        for row in accounts.values():
            _read(root,row['artifact']);_read(root,row['completion'])
        _read(root,snapshot);_read(root,statistics)
        result_ref=_persist(root,DIRECTORY+'/result.json',result)
        _persist(root,DIRECTORY+'/outcome.json',dict(status='completed_conditional_historical',
            registration_sha256=expected_registration_sha256,study_number=p['policy']['study_number'],
            financial_decode_started=decoded,account_count=28,result=result_ref,guard_count=len(guards),
            finished_at=now().isoformat(),qualified=False,real_forward=0))
        return result
    except BaseException as exc:
        failure_path=DIRECTORY+('/finalization_failure.json' if resolve_path(root,DIRECTORY+'/outcome.json').exists() else '/outcome.json')
        _persist(root,failure_path,dict(status='failed_consumed' if decoded else 'failed_before_numeric_decode',
            registration_sha256=expected_registration_sha256,study_number=p['policy']['study_number'],
            financial_decode_started=decoded,error_type=type(exc).__name__,error=str(exc),
            guard_count=len(guards),finished_at=now().isoformat(),qualified=False,real_forward=0))
        raise

