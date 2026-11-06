"""One-use admission for the fixed 2025-01 conditional crypto diagnostic.

Preview, PM scope and comparison only hash market originals. A durable exclusive
claim precedes the financial-decode marker and every financial parser. Partial
claims/outcomes are consumed; there is no resume or automatic repair path.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, write_exclusive_json

DIRECTORY='data/reports/campaign_72h_20261106/crypto_monthly_accounts'
REGISTRATION=DIRECTORY+'/registration.json'
REVIEW=DIRECTORY+'/independent_review.json'
ROOT_REVIEW=DIRECTORY+'/root_admission_review.json'
ADMISSION='configs/cn_etf_crypto_monthly_admission_20261106.json'
CAMPAIGN='configs/research_campaign_72h_20261106.json'
MANIFEST='data/reports/campaign_72h_20261106/manager/crypto_202501_input_preparation_manifest.json'
MANIFEST_SHA='396da2c9fc0e06132b03ee3535c67c69ae461495058f14a989d8ed7a2a3d933d'
METHOD_SHA='cfe465613ec0655ecf7c17d19edaa3b0efd432a5426ecbed0acddee40d9299aa'
BRANCH='codex/factor-review-72h-campaign-20261106'
MODE='single_campaign_crypto_monthly_10_account_only'
POLICY=dict(symbol='BTCUSDT',start='2025-01-01T00:00:00+00:00',end_exclusive='2025-02-01T00:00:00+00:00',
    strategy_accounts=9,cash_controls=1,primary='B_5',funding_events=93,minutes_per_market=44640,
    max_executions=1,ordinary_factor_budget_changed=False,conditional_only=True,
    qualification_granted=False,final_holdout_allowed=False,live_boundary_allowed=False,
    prior_continuation_studies=18,consumed_study_number=19,financial_decode_is_new_research=True,
    comparison_purpose='conditional_one_month_mechanism_only',holding_control_tested=False,
    alpha_or_promotion_eligible=False,source_year_2026_allowed=False)
PM_INPUTS={'campaign':CAMPAIGN,'pm_policy':'configs/quant_pm_startup_gate_cn_etf.json',
           'workstations':'configs/workstations.json','family_scheduler':'configs/research_family_scheduler_cn_etf.json'}
SOURCE_ROLES={'spot_1m_zip','spot_1m_checksum','futures_1m_zip','futures_1m_checksum',
    'mark_1m_zip','mark_1m_checksum','funding_zip','funding_checksum','monthly_method','method_root_review',
    'old_v2_method_preserved','rule_assumption_limits','current_metadata_not_backfilled','archive_terms_receipt',
    'time_projection_scope','time_projection_result','time_projection_independent_review',
    'funding_source_scope','funding_source_review','funding_source_claim','funding_source_capture',
    'funding_raw_MCP','funding_source_outcome','funding_source_gate','archive_original_source_scope',
    'archive_original_source_result','spot_checksum_repair_scope','spot_checksum_repair_result'}
IMPLEMENTATION=(
    'src/quant_robot/research/crypto_monthly_admission.py',
    'src/quant_robot/research/crypto_monthly_historical.py',
    'src/quant_robot/research/crypto_monthly_diagnostic.py',
    'src/quant_robot/research/crypto_carry_model.py','src/quant_robot/research/crypto_carry_policy.py',
    'src/quant_robot/research/crypto_carry_scheduler.py','src/quant_robot/research/crypto_carry_driver.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'scripts/run_crypto_monthly_historical.py','scripts/run_crypto_monthly_diagnostic_synthetic.py',
    'scripts/run_quant_pm_startup_gate.py','scripts/start_task_context.py','scripts/bootstrap.py',
    'tests/unit/test_crypto_monthly_diagnostic.py','tests/unit/test_crypto_monthly_admission.py',
    'tests/unit/test_crypto_monthly_historical.py',
    'tests/unit/test_crypto_monthly_pm_gate.py',
)


def digest(raw): return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        obj={}
        for key,value in items:
            if key in obj: raise ValueError('Duplicate admission/evidence JSON key')
            obj[key]=value
        return obj
    def invalid(value): raise ValueError('Nonfinite JSON token')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def file_digest(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): hasher.update(chunk)
    return hasher.hexdigest()


def runtime_environment():
    from importlib.metadata import version
    context=__import__('decimal').getcontext()
    return {'python':platform.python_version(),'implementation':platform.python_implementation(),
        'platform':platform.platform(),'executable':str(Path(sys.executable).resolve()),
        'executable_sha256':file_digest(sys.executable),
        'decimal_context':{**{key:getattr(context,key) for key in ('prec','rounding','Emin','Emax','capitals','clamp')},
                           'traps':{key.__name__:value for key,value in context.traps.items()}},
        'dependencies':{name:version(name) for name in ('numpy','pandas','pyarrow','pydantic')}}


def read_bound(root,ref,*,return_bytes=False):
    if (not isinstance(ref,dict) or set(ref)!={'path','sha256'} or not isinstance(ref['sha256'],str)
            or len(ref['sha256'])!=64 or any(c not in '0123456789abcdef' for c in ref['sha256'])):
        raise ValueError('Exact path and SHA256 reference required')
    path=resolve_path(root,ref['path'])
    # Check each unresolved ancestor as well as the canonical inside-root path.
    cursor=Path(root)/ref['path']
    while cursor!=Path(root) and cursor!=cursor.parent:
        if cursor.is_symlink(): raise ValueError('Symlink source forbidden')
        cursor=cursor.parent
    if file_digest(path)!=ref['sha256']: raise ValueError('Frozen file changed: '+ref['path'])
    if return_bytes:
        raw=path.read_bytes()
        if digest(raw)!=ref['sha256']: raise ValueError('Frozen file changed while reading')
        return raw
    return None


def _manifest_inputs(root,manifest):
    if (manifest.get('artifact_type')!='conditional_crypto_monthly_input_preparation_manifest_v1'
            or manifest.get('method_sha256')!=METHOD_SHA or manifest.get('input_count')!=28
            or len(manifest.get('inputs',[]))!=28 or {x['role'] for x in manifest['inputs']}!=SOURCE_ROLES):
        raise ValueError('Exact28 preselected source roles required')
    root=Path(root).resolve(); pins={}
    for row in manifest['inputs']:
        path=Path(row['path']).resolve()
        relative=path.relative_to(root).as_posix()
        pin={'path':relative,'sha256':row['sha256']}
        if path.stat().st_size!=row['bytes']: raise ValueError('Source size changed')
        read_bound(root,pin)
        pins[row['role']]=pin
    return pins


def validate_registration(packet,root):
    keys={'artifact_type','branch','input_manifest','inputs','implementation','environment','policy','registration_sha256'}
    if (not isinstance(packet,dict) or set(packet)!=keys
            or packet['artifact_type']!='crypto_monthly_conditional_registration_v1'
            or packet['branch']!=BRANCH or canonical(packet['policy'])!=canonical(POLICY)
            or packet['input_manifest']!={'path':MANIFEST,'sha256':MANIFEST_SHA}
            or set(packet['implementation'])!=set(IMPLEMENTATION)):
        raise ValueError('Exact fixed-month registration required')
    if packet['registration_sha256']!=digest(canonical({k:v for k,v in packet.items() if k!='registration_sha256'})):
        raise ValueError('Registration mutated')
    environment=runtime_environment()
    if packet['environment']!=environment or environment['python']!='3.12.13' or environment['decimal_context']['prec']!=28:
        raise ValueError('Frozen Python3.12.13 and Decimal environment required')
    manifest=_json(read_bound(root,packet['input_manifest'],return_bytes=True))
    pins=_manifest_inputs(root,manifest)
    if set(packet['inputs'])!=SOURCE_ROLES|set(PM_INPUTS): raise ValueError('Exact input role set required')
    for role,ref in packet['inputs'].items():
        if role in pins and ref!=pins[role] or role in PM_INPUTS and ref['path']!=PM_INPUTS[role]:
            raise ValueError('Source or PM input alias forbidden')
        read_bound(root,ref)
    if packet['inputs']['monthly_method']['sha256']!=METHOD_SHA: raise ValueError('Frozen method required')
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
        raise ValueError('Active campaign with retained closed boundaries required')
    return packet


def build_registration(root):
    """Return a prospective fingerprint packet; never write or grant admission."""
    manifest_ref={'path':MANIFEST,'sha256':MANIFEST_SHA}
    pins=_manifest_inputs(root,_json(read_bound(root,manifest_ref,return_bytes=True)))
    pins.update({role:{'path':path,'sha256':file_digest(resolve_path(root,path))} for role,path in PM_INPUTS.items()})
    implementation={name:{'path':name,'sha256':file_digest(resolve_path(root,name))} for name in IMPLEMENTATION}
    packet={'artifact_type':'crypto_monthly_conditional_registration_v1','branch':BRANCH,
        'input_manifest':manifest_ref,'inputs':pins,'implementation':implementation,
        'environment':runtime_environment(),'policy':POLICY}
    packet['registration_sha256']=digest(canonical(packet))
    return validate_registration(packet,root)


def require_unused(root):
    folder=resolve_path(root,DIRECTORY)
    if any((folder/name).exists() for name in ('attempt_claim.json','financial_decode_started.json','outcome.json','result.json','accounts','guard_checks')):
        raise ValueError('Monthly diagnostic reserved or consumed; no resume')


def admitted_packet(root,*,unused=True):
    admission=_json(resolve_path(root,ADMISSION).read_bytes())
    if (set(admission)!={'artifact_type','status','registration','review','root_review','policy'}
            or admission['artifact_type']!='crypto_monthly_conditional_admission_v1'
            or admission['status']!='authorized_once' or canonical(admission['policy'])!=canonical(POLICY)
            or admission['registration']['path']!=REGISTRATION or admission['review']['path']!=REVIEW
            or admission['root_review']['path']!=ROOT_REVIEW):
        raise ValueError('Separately reviewed one-use monthly admission required')
    packet=validate_registration(_json(read_bound(root,admission['registration'],return_bytes=True)),root)
    for key,reviewer in (('review','quant_manager_72h'),('root_review','root')):
        review=_json(read_bound(root,admission[key],return_bytes=True))
        if (review.get('status')!='accepted_for_one_conditional_crypto_month'
                or review.get('registration_sha256')!=packet['registration_sha256'] or review.get('reviewer')!=reviewer
                or review.get('qualified') is not False or type(review.get('real_forward_days_added')) is not int
                or review['real_forward_days_added']!=0 or review.get('financial_execution_authorized') is not True):
            raise ValueError('Independent and root approval of exact registration required')
    if unused: require_unused(root)
    return packet,admission


def _scope(packet,root):
    return {'registration_sha256':packet['registration_sha256'],
            'admission_file_sha256':file_digest(resolve_path(root,ADMISSION)),'policy':POLICY}


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_review' or branch!=BRANCH or not resolve_path(root,ADMISSION).exists(): return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0
            or family_schedule['summary'].get('active_primary_families')!=0): return None
    try: packet,_=admitted_packet(root)
    except (OSError,ValueError,KeyError,TypeError): return None
    return {'mode':MODE,'scope':_scope(packet,root)}


def review_comparison(root,scope):
    packet,_=admitted_packet(root)
    if canonical(scope)!=canonical(_scope(packet,root)): raise ValueError('Comparison scope changed')
    return dict(status='passed_specification_only',blockers=[],method=packet['inputs']['monthly_method'],
        input_manifest=packet['input_manifest'],implementation=packet['implementation'],environment=packet['environment'],
        strategy_accounts=9,cash_controls=1,primary='B_5',no_price_decoding_performed=True,
        net_positive_EV_verified=False,source_quality_verified=False,
        comparison_purpose='conditional_one_month_mechanism_only',holding_control_tested=False,alpha_or_promotion_eligible=False)


class _Claim:
    """Process-local handle issued only after durable claim. It cannot resume."""
    def __init__(self,root,packet,admission,claim_hash,token):
        if token is not _TOKEN: raise ValueError('Claim handles are issued by execute only')
        self.root=Path(root).resolve(); self.packet=packet; self.admission=admission
        self.claim_hash=claim_hash; self.active=True; self.decoding_started=False; self.guard_count=0

    def guard(self,phase,identity):
        if not self.active: raise ValueError('Claim handle closed; no resume')
        if file_digest(resolve_path(self.root,DIRECTORY+'/attempt_claim.json'))!=self.claim_hash:
            raise ValueError('Durable claim changed')
        packet,admission=admitted_packet(self.root,unused=False)
        if canonical(packet)!=canonical(self.packet) or canonical(admission)!=canonical(self.admission):
            raise ValueError('Frozen scope changed during execution')
        self.guard_count+=1
        write_exclusive_json(resolve_path(self.root,DIRECTORY+f'/guard_checks/{self.guard_count:03}.json'),
            {'phase':phase,'identity':identity,'at':datetime.now(timezone.utc).isoformat(),
             'registration_sha256':packet['registration_sha256'],'all_inputs_code_environment_checked':True})

    def read(self,role):
        if not self.active or not self.decoding_started: raise ValueError('Financial decode not opened')
        return read_bound(self.root,self.packet['inputs'][role],return_bytes=True)


_TOKEN=object()


def execute(root,*,expected_registration_sha256,gate_supplier):
    """Only this function can issue a process-local live decode capability."""
    packet,admission=admitted_packet(root)
    if expected_registration_sha256!=packet['registration_sha256']: raise ValueError('Exact registration digest required')
    gate=gate_supplier(); safety=gate['safety']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'].replace('Z','+00:00'))).total_seconds()
    if (not 0<=age<=120 or gate['status']!='ready' or gate['blockers'] or gate['mode']!=MODE
            or gate['primary_market']!='CN_ETF'
            or gate['selected']!=dict(machine='office_desktop',task='factor_review',branch=BRANCH,current_branch=BRANCH)
            or safety.get('crypto_monthly_10_account_allowed') is not True
            or canonical(safety.get('crypto_monthly_10_account_scope'))!=canonical(_scope(packet,root))
            or any(safety.get(k) is not False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact monthly diagnostic gate required')
    again,approval=admitted_packet(root)
    if canonical(again)!=canonical(packet) or canonical(approval)!=canonical(admission):
        raise ValueError('Admission changed during gate')
    folder=resolve_path(root,DIRECTORY)
    write_exclusive_json(folder/'attempt_claim.json',dict(registration_sha256=expected_registration_sha256,
        claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_financial_decode',
        admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),gate=gate,policy=POLICY,
        prior_continuation_studies=18,reserved_study_number=19,consumed_even_if_failed=True))
    claim=_Claim(root,packet,admission,file_digest(folder/'attempt_claim.json'),_TOKEN)
    outcome={'status':'failed_consumed','financial_decode_started':False,'qualified':False,'real_forward_days_added':0}
    try:
        claim.guard('before','financial_decode')
        write_exclusive_json(folder/'financial_decode_started.json',dict(
            at=datetime.now(timezone.utc).isoformat(),registration_sha256=expected_registration_sha256,
            study_number=19,meaning='new_financial_research_consumed_not_source_check',qualified=False,real_forward=0))
        claim.decoding_started=True; outcome['financial_decode_started']=True
        from quant_robot.research.crypto_monthly_historical import run_claimed_month
        result=run_claimed_month(claim)
        claim.guard('final','all_accounts')
        expected_ids={f'{band}_{slip}' for band in ('A','B','C') for slip in (2,5,10)}|{'CASH'}
        if (result.get('artifact_type')!='conditional_crypto_monthly_historical_result_v1'
                or result.get('registration_sha256')!=expected_registration_sha256
                or result.get('qualified') is not False or type(result.get('real_forward')) is not int
                or result['real_forward']!=0 or result.get('historical_returns_computed') is not True
                or set(result.get('accounts',{}))!=expected_ids or result.get('strategy_accounts')!=9
                or result.get('cash_controls')!=1 or result.get('study_number')!=19
                or result.get('holding_control_tested') is not False or result.get('alpha_or_promotion_eligible') is not False):
            raise ValueError('Exact ten retained conditional account identities required')
        write_exclusive_json(folder/'result.json',result)
        outcome.update(status='completed',result_sha256=file_digest(folder/'result.json'),strategy_accounts=9,cash_controls=1,
                       historical_returns_computed=True,study_number=19)
    except BaseException as exc:
        outcome['error_type']=type(exc).__name__
        # Only the exception type is public; no financial row or credential echo.
        raise
    finally:
        claim.active=False
        write_exclusive_json(folder/'outcome.json',dict(**outcome,registration_sha256=expected_registration_sha256,
            finished_at=datetime.now(timezone.utc).isoformat(),guard_checks=claim.guard_count))
    return outcome
