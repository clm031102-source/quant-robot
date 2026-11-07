"""One reviewed bond-risk diagnostic; hashes before an exclusive decode claim."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, write_exclusive_json

DIRECTORY = 'data/reports/campaign_72h_20261106/bond_risk_compensation_accounts'
REGISTRATION = DIRECTORY + '/registration.json'
REVIEW = DIRECTORY + '/independent_review.json'
ROOT_REVIEW = DIRECTORY + '/root_admission_review.json'
ADMISSION = 'configs/cn_etf_bond_risk_compensation_admission_20261107.json'
MANAGER = 'data/reports/campaign_72h_20261106/manager/bond_risk_compensation/'
MANIFEST = MANAGER + 'historical_input_manifest.json'
# Replaced only by a separately reviewed, complete input package before any
# actual registration. Missing pins cannot be treated as a synthetic waiver.
MANIFEST_SHA = 'ad7643050994e3b4ff0408ac04a499b254402b7d61bace4595e006bae84fc377'
METHOD_SHA = '7912eed9aba911ad9e5dd3dfdef246cbb3c82421a4f061c45e31c6fa2ec72a40'
SPLIT_CONTRACT_SHA = '4e4f7e0d247dcfb434eff227bdf25772855a6b962adb4559a6bcb35493742f5d'
BRANCH = 'codex/factor-review-72h-campaign-20261106'
MODE = 'single_campaign_bond_risk_compensation_10_account_only'
POLICY = dict(asset_id='CN_ETF_XSHG_511220', symbol='511220.SH', start='2020-01-02', end='2024-06-28',
    sessions=1087, first_entry='2020-02-07', capacity_warmup_sessions=20,
    initial_cash_CNY='10000', strategy_accounts=9, cash_controls=1, additional_nontrading_references=1,
    cost_cases=[[m,s] for m in (0,5,10) for s in (0,10,30)], primary='M5_S10',
    hypotheses=1, max_executions=1, ordinary_factor_budget_changed=False, conditional_only=True,
    qualification_granted=False, final_holdout_allowed=False, live_boundary_allowed=False,
    prior_continuation_studies=20, consumed_study_number=21, financial_decode_is_new_research=True,
    comparison_purpose='conditional_bond_risk_compensation_only', holding_control_tested=False,
    theoretical_same_ETF_reference=True, alpha_or_promotion_eligible=False, source_year_2026_allowed=False,
    split_mode='exact_integer_split10_record_close_v1', market_source_class='retained_known_historical_sources')
PM_INPUTS = {'campaign':'configs/research_campaign_72h_20261106.json',
    'pm_policy':'configs/quant_pm_startup_gate_cn_etf.json', 'workstations':'configs/workstations.json',
    'family_scheduler':'configs/research_family_scheduler_cn_etf.json'}
CORE_ROLES = {'calendar','cash_action_facts','cash_action_closure','split_projection','input_authority',
              'report_proposal','method','split_contract', *('bars_'+str(y) for y in range(2020,2025))}
BAR_PATH = 'data/processed/tushare_etf_wide_history_2023_2026/processed/bars/frequency=1d/market=CN_ETF/year={}/part-00000.parquet'
IMPLEMENTATION = (
    'src/quant_robot/research/bond_risk_compensation_admission.py',
    'src/quant_robot/research/bond_risk_compensation_historical.py',
    'src/quant_robot/paper/bond_risk_compensation.py',
    'src/quant_robot/paper/annual_allocation.py','src/quant_robot/paper/daily_recovery.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/ops/paper_evidence_session.py',
    'scripts/run_bond_risk_compensation_historical.py','scripts/run_quant_pm_startup_gate.py',
    'scripts/start_task_context.py','scripts/bootstrap.py',
    'tests/unit/test_bond_risk_compensation.py','tests/unit/test_bond_risk_compensation_admission.py',
    'tests/unit/test_bond_risk_compensation_historical.py',
    'tests/unit/test_bond_risk_compensation_pm_gate.py',
)


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
    from decimal import getcontext
    from importlib.metadata import version
    from quant_robot.paper.bond_risk_compensation import CONTEXT
    def context(c,flags=False):
        result={key:getattr(c,key) for key in ('prec','rounding','Emin','Emax','capitals','clamp')}
        result['traps']={key.__name__:value for key,value in c.traps.items()}
        if flags: result['flags']={key.__name__:value for key,value in c.flags.items()}
        return result
    return {'python':platform.python_version(),'implementation':platform.python_implementation(),
        'platform':platform.platform(),'executable':str(Path(sys.executable).resolve()),
        'executable_sha256':file_digest(sys.executable), 'ambient_decimal_context':context(getcontext()),
        'kernel_decimal_context':context(CONTEXT,True),
        'dependencies':{name:version(name) for name in ('numpy','pandas','pyarrow','pydantic')}}


def _manifest_inputs(root,manifest):
    rows=manifest.get('inputs',[])
    if (manifest.get('artifact_type')!='bond_risk_compensation_input_manifest_v1'
            or manifest.get('method_sha256')!=METHOD_SHA
            or manifest.get('split_contract_sha256')!=SPLIT_CONTRACT_SHA
            or type(manifest.get('input_count')) is not int or manifest['input_count']!=len(rows)
            or len({row['role'] for row in rows})!=len(rows)
            or not CORE_ROLES.issubset({row['role'] for row in rows})):
        raise ValueError('Reviewed exact bond input manifest required')
    pins={}
    for row in rows:
        path=Path(row['path'])
        relative=path.resolve().relative_to(Path(root).resolve()).as_posix() if path.is_absolute() else row['path']
        ref={'path':relative,'sha256':row['sha256']}
        if type(row['bytes']) is not int or resolve_path(root,relative).stat().st_size!=row['bytes']:
            raise ValueError('Source size changed')
        read_bound(root,ref); pins[row['role']]=ref
    if len({p['path'] for p in pins.values()})!=len(pins): raise ValueError('Input alias/duplicate forbidden')
    for year in range(2020,2025):
        if pins['bars_'+str(year)]['path']!=BAR_PATH.format(year): raise ValueError('Only five fixed year partitions allowed')
    if pins['method']['sha256']!=METHOD_SHA or pins['split_contract']['sha256']!=SPLIT_CONTRACT_SHA:
        raise ValueError('Original method and additive split contract required')
    return pins


def validate_registration(packet,root):
    keys={'artifact_type','branch','input_manifest','inputs','implementation','environment','policy','registration_sha256'}
    if (not isinstance(packet,dict) or set(packet)!=keys
            or packet['artifact_type']!='bond_risk_compensation_registration_v1'
            or packet['branch']!=BRANCH or canonical(packet['policy'])!=canonical(POLICY)
            or not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64
            or packet['input_manifest']!={'path':MANIFEST,'sha256':MANIFEST_SHA}
            or set(packet['implementation'])!=set(IMPLEMENTATION)):
        raise ValueError('Exact frozen bond registration required')
    if packet['registration_sha256']!=digest(canonical({k:v for k,v in packet.items() if k!='registration_sha256'})):
        raise ValueError('Registration mutated')
    environment=runtime_environment()
    if (packet['environment']!=environment or environment['python']!='3.12.13'
            or environment['kernel_decimal_context']['prec']!=40):
        raise ValueError('Frozen Python and full Decimal environment required')
    pins=_manifest_inputs(root,_json(read_bound(root,packet['input_manifest'],return_bytes=True)))
    if set(packet['inputs'])!=set(pins)|set(PM_INPUTS): raise ValueError('Exact input role set required')
    for role,ref in packet['inputs'].items():
        if role in pins and ref!=pins[role] or role in PM_INPUTS and ref['path']!=PM_INPUTS[role]:
            raise ValueError('Source/PM input alias forbidden')
        read_bound(root,ref)
    for name,ref in packet['implementation'].items():
        if ref['path']!=name: raise ValueError('Implementation alias forbidden')
        read_bound(root,ref)
    campaign=_json(read_bound(root,packet['inputs']['campaign'],return_bytes=True))
    now=datetime.now(timezone.utc)
    if (campaign.get('campaign_id')!='quant_manager_72h_20261106' or campaign.get('status')!='active'
            or campaign.get('task_branch')!=BRANCH or campaign.get('machine')!='office_desktop'
            or campaign.get('started_at')!='2026-11-06T16:21:39Z'
            or campaign.get('delivery_deadline')!='2026-11-09T16:21:39Z'
            or not datetime.fromisoformat(campaign['started_at'].replace('Z','+00:00'))<=now<datetime.fromisoformat(campaign['delivery_deadline'].replace('Z','+00:00'))
            or campaign.get('finite_preregistered_studies_required') is not True
            or campaign.get('old_consumed_scopes_remain_closed') is not True
            or campaign.get('holdout_unsealing_authorized') is not False or campaign.get('live_boundary_allowed') is not False):
        raise ValueError('Active campaign with closed old/holdout/live boundaries required')
    return packet


def build_registration(root):
    """Pure hash preview, no registration/admission/claim writes."""
    if not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64:
        raise ValueError('Final root-reviewed manifest not frozen; no registration possible')
    ref={'path':MANIFEST,'sha256':MANIFEST_SHA}
    pins=_manifest_inputs(root,_json(read_bound(root,ref,return_bytes=True)))
    pins.update({role:{'path':path,'sha256':file_digest(resolve_path(root,path))} for role,path in PM_INPUTS.items()})
    code={name:{'path':name,'sha256':file_digest(resolve_path(root,name))} for name in IMPLEMENTATION}
    packet={'artifact_type':'bond_risk_compensation_registration_v1','branch':BRANCH,'input_manifest':ref,
            'inputs':pins,'implementation':code,'environment':runtime_environment(),'policy':POLICY}
    packet['registration_sha256']=digest(canonical(packet))
    return validate_registration(packet,root)


def require_unused(root):
    folder=resolve_path(root,DIRECTORY)
    if any((folder/name).exists() for name in ('attempt_claim.json','financial_decode_started.json','decoded_input.json','outcome.json','result.json','accounts','reference','guard_checks')):
        raise ValueError('Bond diagnostic reserved or consumed; no resume')


def admitted_packet(root,*,unused=True):
    admission=_json(resolve_path(root,ADMISSION).read_bytes())
    if (set(admission)!={'artifact_type','status','registration','review','root_review','policy'}
            or admission['artifact_type']!='bond_risk_compensation_admission_v1'
            or admission['status']!='authorized_once' or canonical(admission['policy'])!=canonical(POLICY)
            or admission['registration']['path']!=REGISTRATION or admission['review']['path']!=REVIEW
            or admission['root_review']['path']!=ROOT_REVIEW):
        raise ValueError('Separate reviewed one-use bond admission required')
    packet=validate_registration(_json(read_bound(root,admission['registration'],return_bytes=True)),root)
    for key,reviewer in (('review','quant_manager_72h'),('root_review','root')):
        review=_json(read_bound(root,admission[key],return_bytes=True))
        if (review.get('status')!='accepted_for_one_conditional_bond_risk_compensation'
                or review.get('registration_sha256')!=packet['registration_sha256'] or review.get('reviewer')!=reviewer
                or review.get('qualified') is not False or type(review.get('real_forward_days_added')) is not int
                or review['real_forward_days_added']!=0 or review.get('financial_execution_authorized') is not True):
            raise ValueError('Manager and root approval of exact bond registration required')
    if unused: require_unused(root)
    return packet,admission


def _scope(packet,root):
    return {'registration_sha256':packet['registration_sha256'],
            'admission_file_sha256':file_digest(resolve_path(root,ADMISSION)),'policy':POLICY}


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_review' or branch!=BRANCH: return None
    if not resolve_path(root,ADMISSION).exists(): return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0
            or family_schedule['summary'].get('active_primary_families')!=0): return None
    try: packet,_=admitted_packet(root)
    except (OSError,ValueError,KeyError,TypeError): return None
    return {'mode':MODE,'scope':_scope(packet,root)}


def review_comparison(root,scope):
    packet,_=admitted_packet(root)
    if canonical(scope)!=canonical(_scope(packet,root)): raise ValueError('Comparison scope changed')
    return dict(status='passed_specification_only',blockers=[],method=packet['inputs']['method'],
        split_contract=packet['inputs']['split_contract'],input_manifest=packet['input_manifest'],
        implementation=packet['implementation'],environment=packet['environment'],strategy_accounts=9,
        cash_controls=1,additional_nontrading_references=1,primary='M5_S10',no_price_decoding_performed=True,
        net_positive_EV_verified=False,source_quality_verified=False,
        comparison_purpose='conditional_bond_risk_compensation_only',holding_control_tested=False,
        theoretical_same_ETF_reference=True,alpha_or_promotion_eligible=False)


_TOKEN=object()


class _Claim:
    def __init__(self,root,packet,admission,claim_hash,token):
        if token is not _TOKEN: raise ValueError('Claim handle issued only after durable claim')
        self.root=Path(root).resolve(); self.packet=packet; self.admission=admission
        self.claim_hash=claim_hash; self.active=True; self.decoding_started=False; self.guard_count=0
        self.admission_hash=file_digest(resolve_path(self.root,ADMISSION))

    def guard(self,phase,identity):
        if not self.active: raise ValueError('Claim closed; no resume')
        if file_digest(resolve_path(self.root,DIRECTORY+'/attempt_claim.json'))!=self.claim_hash:
            raise ValueError('Durable claim changed')
        if file_digest(resolve_path(self.root,ADMISSION))!=self.admission_hash:
            raise ValueError('Admission original bytes changed')
        import subprocess
        actual=subprocess.run(['git','symbolic-ref','--short','HEAD'],cwd=self.root,check=True,
            capture_output=True,text=True,timeout=10).stdout.strip()
        if actual!=BRANCH: raise ValueError('Actual execution branch changed')
        packet,admission=admitted_packet(self.root,unused=False)
        if canonical(packet)!=canonical(self.packet) or canonical(admission)!=canonical(self.admission):
            raise ValueError('Scope changed during execution')
        self.guard_count+=1
        write_exclusive_json(resolve_path(self.root,DIRECTORY+f'/guard_checks/{self.guard_count:03}.json'),
            dict(phase=phase,identity=identity,at=datetime.now(timezone.utc).isoformat(),
                 registration_sha256=packet['registration_sha256'],all_inputs_code_environment_PM_checked=True,
                 fresh_initial_PM_gate_retained_in_immutable_claim=True))

    def read(self,role):
        if not self.active: raise ValueError('Claim source access closed')
        return read_bound(self.root,self.packet['inputs'][role],return_bytes=True)

    def begin_financial_decode(self):
        if not self.active or self.decoding_started: raise ValueError('Numerical decode entry is once')
        self.guard('before','numerical_parser')
        write_exclusive_json(resolve_path(self.root,DIRECTORY+'/financial_decode_started.json'),
            dict(at=datetime.now(timezone.utc).isoformat(),registration_sha256=self.packet['registration_sha256'],
                 study_number=21,meaning='entering_financial_parser_not_source_preparation',qualified=False,real_forward=0))
        self.decoding_started=True


def execute(root,*,expected_registration_sha256,gate_supplier):
    packet,admission=admitted_packet(root)
    if expected_registration_sha256!=packet['registration_sha256']: raise ValueError('Exact registration digest required')
    gate=gate_supplier(); safety=gate['safety']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'].replace('Z','+00:00'))).total_seconds()
    if (not 0<=age<=120 or gate['status']!='ready' or gate['blockers'] or gate['mode']!=MODE
            or gate['primary_market']!='CN_ETF'
            or gate['selected']!=dict(machine='office_desktop',task='factor_review',branch=BRANCH,current_branch=BRANCH)
            or safety.get('bond_risk_compensation_allowed') is not True
            or canonical(safety.get('bond_risk_compensation_scope'))!=canonical(_scope(packet,root))
            or any(safety.get(k) is not False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact bond PM gate required')
    again,approval=admitted_packet(root)
    if canonical(again)!=canonical(packet) or canonical(approval)!=canonical(admission): raise ValueError('Admission changed during gate')
    folder=resolve_path(root,DIRECTORY)
    write_exclusive_json(folder/'attempt_claim.json',dict(registration_sha256=expected_registration_sha256,
        claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_financial_decode',
        admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),gate=gate,policy=POLICY,
        prior_continuation_studies=20,reserved_study_number=21,consumed_even_if_failed=True))
    claim=_Claim(root,packet,admission,file_digest(folder/'attempt_claim.json'),_TOKEN)
    outcome=dict(status='failed_consumed',financial_decode_started=False,qualified=False,real_forward_days_added=0,
                 reserved_study_number=21,prior_continuation_studies=20,research_study_consumed=False)
    try:
        claim.guard('before','source_preparation')
        from quant_robot.research.bond_risk_compensation_historical import run_claimed_diagnostic
        result=run_claimed_diagnostic(claim)
        if not claim.decoding_started: raise ValueError('No numerical decode entry for result')
        claim.guard('final','all_accounts_and_reference')
        ids={f'M{m}_S{s}' for m,s in POLICY['cost_cases']}|{'CASH'}
        if (result.get('artifact_type')!='conditional_bond_risk_compensation_result_v1'
                or result.get('registration_sha256')!=expected_registration_sha256
                or result.get('qualified') is not False or type(result.get('real_forward')) is not int or result['real_forward']!=0
                or result.get('historical_returns_computed') is not True
                or set(result.get('accounts',{}))!=ids or result.get('strategy_accounts')!=9
                or result.get('cash_controls')!=1 or result.get('additional_nontrading_references')!=1
                or not result.get('reference') or result.get('study_number')!=21
                or result.get('holding_control_tested') is not False or result.get('alpha_or_promotion_eligible') is not False):
            raise ValueError('Exact ten accounts and nontrading reference required')
        for identity,artifact in result['accounts'].items():
            if artifact['path']!=DIRECTORY+'/accounts/'+identity+'/complete.json':
                raise ValueError('Account artifact identity/path mismatch')
        if result['reference']['path']!=DIRECTORY+'/reference/complete.json':
            raise ValueError('Nontrading reference path mismatch')
        for artifact in [*result['accounts'].values(),result['reference']]:
            read_bound(root,{'path':artifact['path'],'sha256':artifact['sha256']})
        decoded=result.get('decoded_input_artifact')
        if (not isinstance(decoded,dict) or set(decoded)!={'path','sha256','canonical_sha256'}
                or decoded['path']!=DIRECTORY+'/decoded_input.json'
                or decoded['canonical_sha256']!=result.get('decoded_input_sha256')):
            raise ValueError('Exact decoded input artifact identity required')
        snapshot=_json(read_bound(root,{'path':decoded['path'],'sha256':decoded['sha256']},return_bytes=True))
        if (not isinstance(snapshot,dict) or set(snapshot)!={'fixture','provenance'}
                or digest(canonical(snapshot))!=result['decoded_input_sha256']):
            raise ValueError('Decoded input canonical digest changed')
        write_exclusive_json(folder/'result.json',result)
        outcome.update(status='completed',result_sha256=file_digest(folder/'result.json'),strategy_accounts=9,cash_controls=1,
                       additional_nontrading_references=1,historical_returns_computed=True,study_number=21)
    except BaseException as exc:
        outcome['error_type']=type(exc).__name__
        raise
    finally:
        if claim.decoding_started: outcome.update(financial_decode_started=True,research_study_consumed=True,study_number=21)
        claim.active=False
        write_exclusive_json(folder/'outcome.json',dict(**outcome,registration_sha256=expected_registration_sha256,
            finished_at=datetime.now(timezone.utc).isoformat(),guard_checks=claim.guard_count))
    return outcome
