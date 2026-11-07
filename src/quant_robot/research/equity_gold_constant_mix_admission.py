"""Hash-only admission for one fixed constant-mix diagnostic; no eager model import."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from quant_robot.research.monthly_diagnostic_registration import canonical as _persisted_json_bytes, resolve_path, write_exclusive_json

DIRECTORY='data/reports/campaign_72h_20261106/constant_mix_accounts'
REGISTRATION=DIRECTORY+'/registration.json'
REVIEW=DIRECTORY+'/independent_review.json'
ROOT_REVIEW=DIRECTORY+'/root_admission_review.json'
COMPARISON=DIRECTORY+'/comparison_review.json'
ADMISSION='configs/cn_etf_constant_mix_admission_20261107.json'
MANAGER='data/reports/campaign_72h_20261106/manager/constant_mix_design_20261107/'
MANIFEST=MANAGER+'historical_input_manifest.json'
MANIFEST_SHA='0480972b713d1c745d620ec81edc6aa722dbe749a37c3dcc7f6293294d8ce913'
METHOD_SHA='08c3b31007598c339ef679ca0f3fb7bb022a9116789b8724c59f2b1bd51bb5c5'
EXIT_FEE_SHA='e293dd85ce20dfbfbcaa7343f388863117ce813c993b3df3ac4e3aa4e96ca75b'
BRANCH='codex/factor-review-72h-campaign-20261106'
MODE='single_campaign_constant_mix_27_account_only'
SOURCE='known_history_provider_wire_with_retrospective_announced_actions'
POLICY=dict(assets=['CN_ETF_XSHG_510300','CN_ETF_XSHG_518880'],symbols=['510300.SH','518880.SH'],
    start='2013-12-05',end='2024-01-02',sessions=2454,first_sell='2014-01-03',first_buy='2014-01-06',
    initial_cash_CNY='10000',strategy_accounts=9,drift_controls=9,cash_controls=9,account_count=27,
    cost_cases=[[m,s] for m in (0,5,10) for s in (0,10,30)],primary='min5_slip10',
    hypotheses=1,max_executions=1,conditional_only=True,qualification_granted=False,
    final_holdout_allowed=False,live_boundary_allowed=False,source_year_2026_allowed=False,
    financial_decode_is_new_research=True,source_nature=SOURCE,
    comparison_purpose='self_financed_constant_mix_whole_policy_increment',
    same_actual_initial_basket_required=True,alpha_or_promotion_eligible=False)
PM_INPUTS={'campaign':'configs/research_campaign_72h_20261106.json',
    'pm_policy':'configs/quant_pm_startup_gate_cn_etf.json','workstations':'configs/workstations.json',
    'family_scheduler':'configs/research_family_scheduler_cn_etf.json'}
CORE_ROLES={'method','exit_fee_addendum','method_root_review','source_manifest','source_index',
    'source_outcome','source_final_review','source_root_review','sessions','actions','action_bridge',
    'action_review','tax_evidence','tax_review','relocations'}
CODE_FILES=(
    'src/quant_robot/research/equity_gold_constant_mix.py',
    'src/quant_robot/research/equity_gold_constant_mix_admission.py',
    'src/quant_robot/research/equity_gold_constant_mix_historical.py',
    'src/quant_robot/research/equity_gold_constant_mix_verification.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/ops/tushare_fund_daily_wire.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/account_comparison_scope.py','src/quant_robot/ops/paper_evidence_session.py',
    'scripts/run_equity_gold_constant_mix_historical.py','scripts/run_quant_pm_startup_gate.py',
    'scripts/start_task_context.py','scripts/bootstrap.py',
    'tests/unit/test_equity_gold_constant_mix.py',
    'tests/unit/test_equity_gold_constant_mix_context.py',
    'tests/unit/test_equity_gold_constant_mix_admission.py',
    'tests/unit/test_equity_gold_constant_mix_historical.py',
    'tests/unit/test_equity_gold_constant_mix_verification.py','tests/unit/test_constant_mix_pm_gate.py')
IMPLEMENTATION=CODE_FILES

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def _json(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('Duplicate evidence JSON key')
            result[k]=v
        return result
    def invalid(value): raise ValueError('Nonfinite JSON token')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def read_bound(root,ref,*,return_bytes=False):
    if (not isinstance(ref,dict) or set(ref)!={'path','sha256'} or not isinstance(ref['sha256'],str)
            or len(ref['sha256'])!=64 or any(c not in '0123456789abcdef' for c in ref['sha256'])):
        raise ValueError('Exact path and SHA256 reference required')
    path=resolve_path(root,ref['path']); cursor=Path(root)/ref['path']
    while cursor!=Path(root) and cursor!=cursor.parent:
        if cursor.is_symlink(): raise ValueError('Symlink input forbidden')
        cursor=cursor.parent
    if file_digest(path)!=ref['sha256']: raise ValueError('Frozen file changed: '+ref['path'])
    if return_bytes:
        raw=path.read_bytes()
        if digest(raw)!=ref['sha256']: raise ValueError('Frozen file changed while reading')
        return raw



def runtime_environment():
    from decimal import Context, getcontext, ROUND_HALF_UP, InvalidOperation, DivisionByZero, Overflow
    from importlib.metadata import version
    def record(c,flags=False):
        value={k:getattr(c,k) for k in ('prec','rounding','Emin','Emax','capitals','clamp')}
        value['traps']={k.__name__:v for k,v in c.traps.items()}
        if flags:value['flags']={k.__name__:v for k,v in c.flags.items()}
        return value
    context=Context(prec=40,rounding=ROUND_HALF_UP,Emin=-999999,Emax=999999,capitals=1,clamp=0)
    for key in context.traps:context.traps[key]=key in (InvalidOperation,DivisionByZero,Overflow)
    context.clear_flags()
    return dict(python=platform.python_version(),implementation=platform.python_implementation(),
        platform=platform.platform(),executable=str(Path(sys.executable).resolve()),
        executable_sha256=file_digest(sys.executable),ambient_decimal_context=record(getcontext()),
        kernel_decimal_context=record(context,True),dependencies={'numpy':version('numpy')})


def _policy(manifest):
    number=manifest.get('study_number')
    if type(number) is not int or number<=22:raise ValueError('Root must assign a new exact study identity')
    return dict(POLICY,study_number=number)


def _manifest_inputs(root,manifest):
    rows=manifest.get('inputs',[])
    if (manifest.get('artifact_type')!='constant_mix_historical_input_manifest_v1'
            or manifest.get('method_sha256')!=METHOD_SHA or manifest.get('exit_fee_addendum_sha256')!=EXIT_FEE_SHA
            or manifest.get('source_nature')!=SOURCE or type(manifest.get('input_count')) is not int
            or manifest['input_count']!=len(rows) or not rows
            or len({r['role'] for r in rows})!=len(rows)
            or not CORE_ROLES.issubset({r['role'] for r in rows})):
        raise ValueError('Exact complete constant-mix manifest required')
    _policy(manifest)
    pins={}
    for row in rows:
        path=Path(row['path'])
        rel=path.resolve().relative_to(Path(root).resolve()).as_posix() if path.is_absolute() else row['path']
        ref={'path':rel,'sha256':row['sha256']}
        if type(row['bytes']) is not int or row['bytes']!=resolve_path(root,rel).stat().st_size:
            raise ValueError('Frozen source size changed')
        read_bound(root,ref);pins[row['role']]=ref
    if len({str(resolve_path(root,r['path'])).casefold() for r in pins.values()})!=len(pins):raise ValueError('One immutable input role per actual path')
    if pins['method']['sha256']!=METHOD_SHA or pins['exit_fee_addendum']['sha256']!=EXIT_FEE_SHA:
        raise ValueError('Frozen economic method and fee-subledger addendum required')
    relocation=_json(read_bound(root,pins['relocations'],return_bytes=True))
    if relocation.get('artifact_type')!='constant_mix_exact_source_relocations_v1':
        raise ValueError('Explicit exact relocation table required')
    keys=set()
    for row in relocation.get('mappings',[]):
        old=row['original'];new=row['restored'];key=(str(Path(old['path']).resolve()).casefold(),old['sha256'],old['bytes'])
        if (key in keys or not Path(old['path']).is_absolute() or old['sha256']!=new['sha256']
                or old['bytes']!=new['bytes'] or type(old['bytes']) is not int or old['bytes']<0
                or row['target_role'] not in pins):raise ValueError('Exact path/hash/bytes relocation identity required')
        keys.add(key)
        pin=pins[row['target_role']]
        target=resolve_path(root,pin['path'])
        if (target!=Path(new['path']).resolve() or pin['sha256']!=new['sha256']
                or target.stat().st_size!=new['bytes']):raise ValueError('Restored snapshot mismatch')
    return pins


def validate_registration(packet,root):
    keys={'artifact_type','branch','input_manifest','inputs','implementation','environment','policy','registration_sha256'}
    if (not isinstance(packet,dict) or set(packet)!=keys
            or packet['artifact_type']!='constant_mix_registration_v1' or packet['branch']!=BRANCH
            or not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64
            or packet['input_manifest']!={'path':MANIFEST,'sha256':MANIFEST_SHA}
            or set(packet['implementation'])!=set(CODE_FILES)):
        raise ValueError('Exact frozen constant-mix registration required')
    if packet['registration_sha256']!=digest(canonical({k:v for k,v in packet.items() if k!='registration_sha256'})):
        raise ValueError('Registration mutated')
    environment=runtime_environment()
    if packet['environment']!=environment or environment['python']!='3.12.13':
        raise ValueError('Frozen Python/full Decimal/numpy environment required')
    manifest=_json(read_bound(root,packet['input_manifest'],return_bytes=True))
    if canonical(packet['policy'])!=canonical(_policy(manifest)):raise ValueError('Exact fixed policy required')
    pins=_manifest_inputs(root,manifest)
    if set(packet['inputs'])!=set(pins)|set(PM_INPUTS):raise ValueError('Exact input role set required')
    for role,ref in packet['inputs'].items():
        if (role in pins and ref!=pins[role]) or (role in PM_INPUTS and ref['path']!=PM_INPUTS[role]):
            raise ValueError('Input alias forbidden')
        read_bound(root,ref)
    for name,ref in packet['implementation'].items():
        if ref['path']!=name:raise ValueError('Implementation alias forbidden')
        read_bound(root,ref)
    campaign=_json(read_bound(root,packet['inputs']['campaign'],return_bytes=True));now=datetime.now(timezone.utc)
    if (campaign.get('campaign_id')!='quant_manager_72h_20261106' or campaign.get('status')!='active'
            or campaign.get('task_branch')!=BRANCH or campaign.get('machine')!='office_desktop'
            or campaign.get('started_at')!='2026-11-06T16:21:39Z' or campaign.get('delivery_deadline')!='2026-11-09T16:21:39Z'
            or not datetime.fromisoformat(campaign['started_at'].replace('Z','+00:00'))<=now<datetime.fromisoformat(campaign['delivery_deadline'].replace('Z','+00:00'))
            or campaign.get('finite_preregistered_studies_required') is not True
            or campaign.get('old_consumed_scopes_remain_closed') is not True
            or campaign.get('holdout_unsealing_authorized') is not False or campaign.get('live_boundary_allowed') is not False):
        raise ValueError('Active campaign with closed ordinary/holdout/live boundaries required')
    return packet


def build_registration(root):
    """Hash-only preview. No registration or permission is written."""
    if not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64:
        raise ValueError('Final reviewed source manifest is not frozen')
    ref={'path':MANIFEST,'sha256':MANIFEST_SHA};manifest=_json(read_bound(root,ref,return_bytes=True))
    pins=_manifest_inputs(root,manifest)
    pins.update({r:{'path':p,'sha256':file_digest(resolve_path(root,p))} for r,p in PM_INPUTS.items()})
    packet=dict(artifact_type='constant_mix_registration_v1',branch=BRANCH,input_manifest=ref,inputs=pins,
        implementation={n:{'path':n,'sha256':file_digest(resolve_path(root,n))} for n in CODE_FILES},
        environment=runtime_environment(),policy=_policy(manifest))
    packet['registration_sha256']=digest(canonical(packet))
    return validate_registration(packet,root)


def require_unused(root):
    folder=resolve_path(root,DIRECTORY)
    if any((folder/name).exists() for name in ('attempt_claim.json','financial_decode_started.json',
            'decoded_input.json','outcome.json','result.json','accounts','statistics.json','guard_checks','account_index')):
        raise ValueError('Constant-mix attempt reserved or consumed; no resume')


def _comparison(root,ref,packet):
    value=_json(read_bound(root,ref,return_bytes=True))
    expected=dict(status='accepted_specification_only',registration_sha256=packet['registration_sha256'],
        strategy_accounts=9,drift_controls=9,cash_controls=9,same_actual_initial_basket_required=True,
        comparison_purpose=POLICY['comparison_purpose'],alpha_or_promotion_eligible=False,qualified=False)
    if value.get('artifact_type')!='constant_mix_comparison_review_v1' or any(value.get(k)!=v for k,v in expected.items()):
        raise ValueError('Exact external comparison specification review required')
    return value


def admitted_packet(root,*,branch=BRANCH,require_unused=True):
    if branch!=BRANCH:raise ValueError('Wrong execution branch')
    approval=_json(resolve_path(root,ADMISSION).read_bytes())
    if (set(approval)!={'artifact_type','status','registration','review','root_review','comparison','policy'}
            or approval['artifact_type']!='constant_mix_admission_v1' or approval['status']!='authorized_once'
            or approval['registration']['path']!=REGISTRATION or approval['review']['path']!=REVIEW
            or approval['root_review']['path']!=ROOT_REVIEW or approval['comparison']['path']!=COMPARISON):
        raise ValueError('Separate exact one-use constant-mix admission required')
    packet=validate_registration(_json(read_bound(root,approval['registration'],return_bytes=True)),root)
    if canonical(approval['policy'])!=canonical(packet['policy']):raise ValueError('Admission policy mismatch')
    for key,reviewer in (('review','quant_manager_72h'),('root_review','root')):
        review=_json(read_bound(root,approval[key],return_bytes=True))
        if (review.get('status')!='accepted_for_one_conditional_constant_mix'
                or review.get('reviewer')!=reviewer or review.get('registration_sha256')!=packet['registration_sha256']
                or review.get('qualified') is not False or review.get('real_forward_days_added')!=0
                or type(review.get('real_forward_days_added')) is not int
                or review.get('financial_execution_authorized') is not True):
            raise ValueError('Manager and root exact financial acceptance required')
    _comparison(root,approval['comparison'],packet)
    if require_unused:globals()['require_unused'](root)
    return packet,approval


def _scope(packet,root):
    return dict(registration_sha256=packet['registration_sha256'],
                admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),policy=packet['policy'])


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_review' or branch!=BRANCH:return None
    if not resolve_path(root,ADMISSION).exists():return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule.get('summary',{}).get('primary_budget_share')!=0
            or family_schedule.get('summary',{}).get('active_primary_families')!=0):return None
    try:packet,_=admitted_packet(root,branch=branch)
    except (OSError,ValueError,KeyError,TypeError):return None
    return dict(mode=MODE,scope=_scope(packet,root))


def review_comparison(root,scope):
    packet,approval=admitted_packet(root)
    if canonical(scope)!=canonical(_scope(packet,root)):raise ValueError('Comparison scope changed')
    _comparison(root,approval['comparison'],packet)
    return dict(status='passed_specification_only',blockers=[],method=packet['inputs']['method'],
        input_manifest=packet['input_manifest'],implementation=packet['implementation'],environment=packet['environment'],
        strategy_accounts=9,drift_controls=9,cash_controls=9,same_actual_initial_basket_required=True,
        comparison_purpose=POLICY['comparison_purpose'],no_price_decoding_performed=True,
        net_positive_EV_verified=False,source_quality_verified=False,alpha_or_promotion_eligible=False)


_TOKEN=object()


class _Claim:
    def __init__(self,root,packet,approval,claim_hash,token):
        if token is not _TOKEN:raise ValueError('Only durable execution can issue a production claim')
        self.root=Path(root).resolve();self.packet=packet;self.approval=approval;self.claim_hash=claim_hash
        self.active=True;self.decoding_started=False;self.guard_count=0
        self.admission_hash=file_digest(resolve_path(self.root,ADMISSION))

    def guard(self,phase,identity):
        if not self.active:raise ValueError('Claim closed')
        if file_digest(resolve_path(self.root,DIRECTORY+'/attempt_claim.json'))!=self.claim_hash:
            raise ValueError('Durable claim changed')
        if file_digest(resolve_path(self.root,ADMISSION))!=self.admission_hash:raise ValueError('Admission bytes changed')
        import subprocess
        actual=subprocess.run(['git','symbolic-ref','--short','HEAD'],cwd=self.root,check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if actual!=BRANCH:raise ValueError('Execution branch changed')
        packet,approval=admitted_packet(self.root,require_unused=False)
        if canonical(packet)!=canonical(self.packet) or canonical(approval)!=canonical(self.approval):
            raise ValueError('Frozen packet changed')
        self.guard_count+=1
        write_exclusive_json(resolve_path(self.root,DIRECTORY+f'/guard_checks/{self.guard_count:03}.json'),
            dict(phase=phase,identity=identity,at=datetime.now(timezone.utc).isoformat(),
                 registration_sha256=packet['registration_sha256'],all_inputs_code_environment_PM_checked=True))

    def read(self,role):
        if not self.active:raise ValueError('Claim closed')
        return read_bound(self.root,self.packet['inputs'][role],return_bytes=True)

    def begin_financial_decode(self):
        if not self.active or self.decoding_started:raise ValueError('One numerical parser entry only')
        self.guard('before','numerical_parser')
        write_exclusive_json(resolve_path(self.root,DIRECTORY+'/financial_decode_started.json'),
            dict(at=datetime.now(timezone.utc).isoformat(),registration_sha256=self.packet['registration_sha256'],
                 study_number=self.packet['policy']['study_number'],meaning='entering_financial_parser',qualified=False,real_forward=0))
        self.decoding_started=True


def _final_artifacts(root,result):
    ids={f'min{m}_slip{s}/{p}' for m,s in POLICY['cost_cases'] for p in ('constant_mix','drift','cash')}
    if set(result.get('accounts',{}))!=ids:raise ValueError('Exactly27 accounts required')
    for identity,value in result['accounts'].items():
        artifact=value['artifact']
        if artifact['path']!=DIRECTORY+'/accounts/'+identity+'/complete.json':raise ValueError('Account output path mismatch')
        read_bound(root,{'path':artifact['path'],'sha256':artifact['sha256']})
        if resolve_path(root,artifact['path']).stat().st_size!=artifact['bytes']:raise ValueError('Account bytes changed')
    stats=result['statistics']
    if stats['path']!=DIRECTORY+'/statistics.json':raise ValueError('Statistics output path mismatch')
    read_bound(root,{'path':stats['path'],'sha256':stats['sha256']})
    if resolve_path(root,stats['path']).stat().st_size!=stats['bytes']:raise ValueError('Statistics bytes changed')
    decoded=result['decoded_input_artifact']
    if decoded['path']!=DIRECTORY+'/decoded_input.json':raise ValueError('Snapshot path mismatch')
    raw=read_bound(root,{'path':decoded['path'],'sha256':decoded['sha256']},return_bytes=True);snapshot=_json(raw)
    if (set(snapshot)!={'fixture','provenance'} or digest(canonical(snapshot))!=result['decoded_input_sha256']
            or len(raw)!=decoded['bytes']):raise ValueError('Decoded input content changed')


def execute(root,*,expected_registration_sha256,gate_supplier):
    packet,approval=admitted_packet(root)
    if expected_registration_sha256!=packet['registration_sha256']:raise ValueError('Exact registration digest required')
    gate=gate_supplier();safety=gate['safety']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'].replace('Z','+00:00'))).total_seconds()
    if (not 0<=age<=120 or gate['status']!='ready' or gate['blockers'] or gate['mode']!=MODE
            or gate['primary_market']!='CN_ETF'
            or gate['selected']!=dict(machine='office_desktop',task='factor_review',branch=BRANCH,current_branch=BRANCH)
            or safety.get('constant_mix_allowed') is not True
            or canonical(safety.get('constant_mix_scope'))!=canonical(_scope(packet,root))
            or any(safety.get(k) is not False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact constant-mix PM gate required')
    again,approvals=admitted_packet(root)
    if canonical(again)!=canonical(packet) or canonical(approvals)!=canonical(approval):raise ValueError('Gate-time scope changed')
    folder=resolve_path(root,DIRECTORY)
    write_exclusive_json(folder/'attempt_claim.json',dict(registration_sha256=expected_registration_sha256,
        claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_financial_decode',
        gate=gate,policy=packet['policy'],reserved_study_number=packet['policy']['study_number'],consumed_even_if_failed=True))
    claim=_Claim(root,packet,approval,file_digest(folder/'attempt_claim.json'),_TOKEN)
    outcome=dict(status='failed_consumed',financial_decode_started=False,historical_returns_computed=False,
        qualified=False,real_forward_days_added=0,research_study_consumed=False,independently_verified=False)
    try:
        claim.guard('before','source_preparation')
        from quant_robot.research.equity_gold_constant_mix_historical import run_claimed_diagnostic
        result=run_claimed_diagnostic(claim)
        if (not claim.decoding_started or result.get('artifact_type')!='conditional_historical_constant_mix_matrix_v1'
                or result.get('registration_sha256')!=expected_registration_sha256
                or result.get('source_nature')!=SOURCE or result.get('qualified') is not False
                or type(result.get('real_forward')) is not int or result['real_forward']!=0
                or result.get('historical_returns_computed') is not True or result.get('test_injected_values') is not False):
            raise ValueError('Production result identity required')
        claim.guard('final','all_accounts_statistics_and_snapshot');_final_artifacts(root,result)
        intended_result_bytes=_persisted_json_bytes(result)
        intended_result_sha256=digest(intended_result_bytes)
        write_exclusive_json(folder/'result.json',result)
        if (folder/'result.json').read_bytes()!=intended_result_bytes:
            raise ValueError('Final result differs from pre-write intended bytes')
        outcome.update(status='completed_conditional_accounts',account_count=27,historical_returns_computed=True,
                       result_sha256=intended_result_sha256)
    except BaseException as exc:
        outcome['error_type']=type(exc).__name__;raise
    finally:
        outcome.update(financial_decode_started=claim.decoding_started,research_study_consumed=claim.decoding_started)
        if claim.decoding_started:outcome['study_number']=packet['policy']['study_number']
        claim.active=False
        write_exclusive_json(folder/'outcome.json',dict(**outcome,registration_sha256=expected_registration_sha256,
            reserved_study_number=packet['policy']['study_number'],finished_at=datetime.now(timezone.utc).isoformat(),guard_checks=claim.guard_count))
    return outcome
