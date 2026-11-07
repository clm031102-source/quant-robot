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
from quant_robot.research.crypto_monthly_admission import SOURCE_ROLES as LEGACY_SOURCE_ROLES
from quant_robot.research.crypto_carry_model import CHARGE_BASIS_FUNDING

DIRECTORY='data/reports/campaign_72h_20261106/crypto_charge_monthly_accounts'
REGISTRATION=DIRECTORY+'/registration.json'
REVIEW=DIRECTORY+'/independent_review.json'
ROOT_REVIEW=DIRECTORY+'/root_admission_review.json'
ADMISSION='configs/cn_etf_crypto_charge_monthly_admission_20261106.json'
CAMPAIGN='configs/research_campaign_72h_20261106.json'
MANAGER='data/reports/campaign_72h_20261106/manager/'
MANIFEST=MANAGER+'crypto_charge_202501_input_preparation_manifest.json'
MANIFEST_SHA='91b2822b53736d977d6ca1558a57bd452097e7d7c311abcbd17f03373f883f96'
METHOD_SHA='692c619fe04c867d7b2faff4954b1143603e43d89b818656363c8fa9bd1b396c'
LEGACY_MANIFEST_SHA='396da2c9fc0e06132b03ee3535c67c69ae461495058f14a989d8ed7a2a3d933d'
BRANCH='codex/factor-review-72h-campaign-20261106'
MODE='single_campaign_crypto_charge_monthly_10_account_only'
POLICY=dict(symbol='BTCUSDT',start='2025-01-01T00:00:00+00:00',end_exclusive='2025-02-01T00:00:00+00:00',
    strategy_accounts=9,cash_controls=1,primary='B_5',funding_events=93,minutes_per_market=44640,
    max_executions=1,ordinary_factor_budget_changed=False,conditional_only=True,
    qualification_granted=False,final_holdout_allowed=False,live_boundary_allowed=False,
    prior_continuation_studies=19,consumed_study_number=20,financial_decode_is_new_research=True,
    comparison_purpose='conditional_one_month_mechanism_only',holding_control_tested=False,
    alpha_or_promotion_eligible=False,source_year_2026_allowed=False,
    funding_mode=CHARGE_BASIS_FUNDING,old_study19_resume_allowed=False,
    cash_formula_and_availability='conditional_model_not_historical_payment_certification')
PM_INPUTS={'campaign':CAMPAIGN,'pm_policy':'configs/quant_pm_startup_gate_cn_etf.json',
           'workstations':'configs/workstations.json','family_scheduler':'configs/research_family_scheduler_cn_etf.json'}
EXTRA_INPUTS={role:MANAGER+path for role,path in {
    'new_monthly_method':'crypto_charge_202501_conditional_diagnostic_contract.md',
    'new_method_manager_review':'crypto_charge_202501_method_manager_review.json',
    'new_method_root_review':'crypto_charge_202501_method_root_review.json',
    'legacy_input_manifest':'crypto_202501_input_preparation_manifest.json',
    'charge_role_contract':'crypto_charge_basis_valuation_candidate_contract.md',
    'charge_role_handcases':'crypto_charge_basis_valuation_candidate_handcases.json',
    'charge_role_manager_review':'crypto_charge_basis_valuation_candidate_manager_review.json',
    'charge_role_root_review':'crypto_charge_basis_valuation_root_method_review.json',
    'charge_implementation_review':'crypto_charge_basis_implementation_manager_final_review.json',
    'charge_implementation_root_review':'crypto_charge_basis_implementation_root_review.json',
    'charge_implementation_delivery':'crypto_charge_basis_implementation_delivery.json',
    'charge_independent_event_review':'BP_adversarial_actual_review.json',
    'charge_persisted_evidence_review':'BP_manager_persisted_evidence_check.json',
    'official_charge_scope':'crypto_event_semantics_native_web_root_scope.json',
    'official_charge_original':'crypto_event_semantics_native_web_result.json',
    'official_charge_semantic_review':'crypto_event_semantics_native_web_semantic_review.json',
    'official_charge_semantic_independent_review':'crypto_event_semantics_native_web_semantic_independent_review.json',
    'event93_scope':'crypto_event_mark_numeric_scope.json',
    'event93_claim':'crypto_event_mark_numeric_diagnostic/attempt_claim.json',
    'event93_result':'crypto_event_mark_numeric_diagnostic/result.json',
    'event93_outcome':'crypto_event_mark_numeric_diagnostic/outcome.json',
    'event93_manager_review':'crypto_event_mark_numeric_manager_review.json',
    'event93_root_review':'crypto_event_mark_numeric_root_review.json',
    'event93_independent_review':'crypto_event_mark_numeric_actual_independent_review.json',
    'legacy_failed_review':'crypto_monthly_failed_decode_independent_review.json',
    'prechange_runtime_manifest':'BP_prechange_runtime/manifest.json',
    'prechange_model':'BP_prechange_runtime/crypto_carry_model.py',
    'prechange_scheduler':'BP_prechange_runtime/crypto_carry_scheduler.py',
    'prechange_driver':'BP_prechange_runtime/crypto_carry_driver.py',
    'prechange_monthly':'BP_prechange_runtime/crypto_monthly_diagnostic.py',
    'legacy_D_archive_receipt':'event_mark_diagnostic93_backup_receipt.json',
    'faq_failed_scope':'BP_funding_formula_clock_source/scope.json',
    'faq_failed_claim':'BP_funding_formula_clock_source/claim.json',
    'faq_failed_request':'BP_funding_formula_clock_source/request_attempt.json',
    'faq_failed_outcome':'BP_funding_formula_clock_source/outcome.json',
    'faq_failure_boundary':'BP_FAQ_persistence_failure_boundary.json',
    'faq_repair_scope':'BP_funding_formula_clock_repair_source/scope.json',
    'faq_repair_claim':'BP_funding_formula_clock_repair_source/claim.json',
    'faq_repair_outcome':'BP_funding_formula_clock_repair_source/outcome.json',
    'faq_repair_original':'BP_funding_formula_clock_repair_source/tool_return.json',
    'faq_repair_projection':'BP_funding_formula_clock_repair_source/semantic_projection.json',
    'faq_repair_semantic_review':'BP_funding_formula_clock_manager_semantic_review.json',
}.items()}
EXTRA_INPUTS.update({role:'data/reports/campaign_72h_20261106/crypto_monthly_accounts/'+name for role,name in {
    'legacy_registration':'registration.json','legacy_claim':'attempt_claim.json',
    'legacy_outcome':'outcome.json','legacy_decode_marker':'financial_decode_started.json',
    'legacy_independent_admission_review':'independent_review.json','legacy_root_admission_review':'root_admission_review.json',
    'legacy_guard_before_decode':'guard_checks/001.json','legacy_guard_before_source':'guard_checks/002.json',
    'legacy_process_receipt':'process_receipt.json','legacy_execution_log':'execution.log',
}.items()})
SOURCE_ROLES=LEGACY_SOURCE_ROLES|set(EXTRA_INPUTS)
IMPLEMENTATION=(
    'src/quant_robot/research/crypto_charge_monthly_admission.py',
    'src/quant_robot/research/crypto_charge_monthly_historical.py',
    'src/quant_robot/research/crypto_monthly_admission.py',
    'src/quant_robot/research/crypto_charge_basis.py',
    'src/quant_robot/research/crypto_monthly_diagnostic.py',
    'src/quant_robot/research/crypto_carry_model.py','src/quant_robot/research/crypto_carry_policy.py',
    'src/quant_robot/research/crypto_carry_scheduler.py','src/quant_robot/research/crypto_carry_driver.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'scripts/run_crypto_charge_monthly_historical.py','scripts/run_crypto_monthly_diagnostic_synthetic.py',
    'scripts/run_quant_pm_startup_gate.py','scripts/start_task_context.py','scripts/bootstrap.py',
    'tests/unit/test_crypto_monthly_diagnostic.py','tests/unit/test_crypto_charge_monthly_admission.py',
    'tests/unit/test_crypto_charge_monthly_historical.py',
    'tests/unit/test_crypto_charge_basis.py',
    'tests/unit/test_crypto_charge_monthly_pm_gate.py',
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
    if (manifest.get('artifact_type')!='conditional_crypto_charge_monthly_input_manifest_v1'
            or manifest.get('method_sha256')!=METHOD_SHA or manifest.get('input_count')!=len(SOURCE_ROLES)
            or len(manifest.get('inputs',[]))!=len(SOURCE_ROLES)
            or {x['role'] for x in manifest['inputs']}!=SOURCE_ROLES):
        raise ValueError('Exact original28 and prospective evidence roles required')
    root=Path(root).resolve(); pins={}
    for row in manifest['inputs']:
        path=Path(row['path']).resolve()
        relative=path.relative_to(root).as_posix()
        pin={'path':relative,'sha256':row['sha256']}
        if path.stat().st_size!=row['bytes']: raise ValueError('Source size changed')
        read_bound(root,pin)
        pins[row['role']]=pin
    for role,path in EXTRA_INPUTS.items():
        if pins[role]['path']!=path: raise ValueError('Prospective evidence alias forbidden')
    if pins['legacy_input_manifest']['sha256']!=LEGACY_MANIFEST_SHA:
        raise ValueError('Original28 manifest changed')
    legacy=_json(read_bound(root,pins['legacy_input_manifest'],return_bytes=True))
    if (legacy.get('input_count')!=28 or len(legacy.get('inputs',[]))!=28
            or {r['role'] for r in legacy['inputs']}!=LEGACY_SOURCE_ROLES):
        raise ValueError('Original28 manifest schema changed')
    for row in legacy['inputs']:
        ref={'path':Path(row['path']).resolve().relative_to(root).as_posix(),'sha256':row['sha256']}
        if pins[row['role']]!=ref: raise ValueError('Original28 source reference changed')
    _validate_predecessor(root,pins)
    return pins


def _validate_predecessor(root,pins):
    """Check retained metadata, never require current code to equal old code."""
    def metadata(role): return _json(read_bound(root,pins[role],return_bytes=True))
    old=metadata('legacy_registration')
    old_sha=digest(canonical({k:v for k,v in old.items() if k!='registration_sha256'}))
    if (old.get('registration_sha256')!=old_sha or old['policy'].get('consumed_study_number')!=19
            or old['policy'].get('prior_continuation_studies')!=18
            or any(old['inputs'].get(role)!=pins[role] for role in LEGACY_SOURCE_ROLES)):
        raise ValueError('Old19 identity or original source chain changed')
    for role in ('legacy_claim','legacy_outcome','legacy_decode_marker'):
        if metadata(role).get('registration_sha256')!=old_sha:
            raise ValueError('Old19 failure-chain registration mismatch')
    outcome=metadata('legacy_outcome'); marker=metadata('legacy_decode_marker')
    if outcome.get('status')!='failed_consumed' or outcome.get('financial_decode_started') is not True or marker.get('study_number')!=19:
        raise ValueError('Old19 failed decode identity must be preserved')
    backup=metadata('legacy_D_archive_receipt')
    if (backup.get('all_source_archive_restore_hashes_match') is not True
            or any(backup.get('source_files',{}).get(name)!=ref['sha256'] for name,ref in old['implementation'].items())):
        raise ValueError('Retained old-code backup receipt mismatch')
    copies=metadata('prechange_runtime_manifest')['files']
    for role in ('prechange_model','prechange_scheduler','prechange_driver','prechange_monthly'):
        name=Path(pins[role]['path']).name; record=copies[name]
        if pins[role]['sha256']!=record['sha256'] or old['implementation'][record['source']]['sha256']!=record['sha256']:
            raise ValueError('Exact prechange code preservation required')


def validate_registration(packet,root):
    keys={'artifact_type','branch','input_manifest','inputs','implementation','environment','policy','registration_sha256'}
    if (not isinstance(packet,dict) or set(packet)!=keys
            or packet['artifact_type']!='crypto_charge_monthly_conditional_registration_v1'
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
    if packet['inputs']['new_monthly_method']['sha256']!=METHOD_SHA: raise ValueError('Frozen new method required')
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
    packet={'artifact_type':'crypto_charge_monthly_conditional_registration_v1','branch':BRANCH,
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
            or admission['artifact_type']!='crypto_charge_monthly_conditional_admission_v1'
            or admission['status']!='authorized_once' or canonical(admission['policy'])!=canonical(POLICY)
            or admission['registration']['path']!=REGISTRATION or admission['review']['path']!=REVIEW
            or admission['root_review']['path']!=ROOT_REVIEW):
        raise ValueError('Separately reviewed one-use monthly admission required')
    packet=validate_registration(_json(read_bound(root,admission['registration'],return_bytes=True)),root)
    for key,reviewer in (('review','quant_manager_72h'),('root_review','root')):
        review=_json(read_bound(root,admission[key],return_bytes=True))
        if (review.get('status')!='accepted_for_one_conditional_crypto_charge_month'
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
    return dict(status='passed_specification_only',blockers=[],method=packet['inputs']['new_monthly_method'],
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
        # Bytes may be hash-checked and metadata prepared under the durable
        # claim. The numerical parser has a separate exact entry marker.
        if not self.active: raise ValueError('Claim source access not opened')
        return read_bound(self.root,self.packet['inputs'][role],return_bytes=True)

    def begin_financial_decode(self):
        if not self.active or self.decoding_started:
            raise ValueError('Numerical decode entry is once per active claim')
        self.guard('before','numerical_parser')
        write_exclusive_json(resolve_path(self.root,DIRECTORY+'/financial_decode_started.json'),dict(
            at=datetime.now(timezone.utc).isoformat(),registration_sha256=self.packet['registration_sha256'],
            study_number=20,meaning='entering_financial_numerical_parser_not_source_preparation',
            qualified=False,real_forward=0))
        self.decoding_started=True


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
            or safety.get('crypto_charge_monthly_allowed') is not True
            or canonical(safety.get('crypto_charge_monthly_scope'))!=canonical(_scope(packet,root))
            or any(safety.get(k) is not False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact monthly diagnostic gate required')
    again,approval=admitted_packet(root)
    if canonical(again)!=canonical(packet) or canonical(approval)!=canonical(admission):
        raise ValueError('Admission changed during gate')
    folder=resolve_path(root,DIRECTORY)
    write_exclusive_json(folder/'attempt_claim.json',dict(registration_sha256=expected_registration_sha256,
        claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_financial_decode',
        admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),gate=gate,policy=POLICY,
        prior_continuation_studies=19,reserved_study_number=20,consumed_even_if_failed=True))
    claim=_Claim(root,packet,admission,file_digest(folder/'attempt_claim.json'),_TOKEN)
    outcome={'status':'failed_consumed','financial_decode_started':False,'qualified':False,'real_forward_days_added':0,
             'reserved_study_number':20,'prior_continuation_studies':19,'research_study_consumed':False}
    try:
        claim.guard('before','source_preparation')
        from quant_robot.research.crypto_charge_monthly_historical import run_claimed_month
        result=run_claimed_month(claim)
        if not claim.decoding_started: raise ValueError('No numerical decode entry for returned accounts')
        claim.guard('final','all_accounts')
        expected_ids={f'{band}_{slip}' for band in ('A','B','C') for slip in (2,5,10)}|{'CASH'}
        if (result.get('artifact_type')!='conditional_crypto_charge_monthly_historical_result_v1'
                or result.get('registration_sha256')!=expected_registration_sha256
                or result.get('qualified') is not False or type(result.get('real_forward')) is not int
                or result['real_forward']!=0 or result.get('historical_returns_computed') is not True
                or set(result.get('accounts',{}))!=expected_ids or result.get('strategy_accounts')!=9
                or result.get('cash_controls')!=1 or result.get('study_number')!=20
                or result.get('funding_mode')!=CHARGE_BASIS_FUNDING or result.get('old_study19_resumed') is not False
                or result.get('holding_control_tested') is not False or result.get('alpha_or_promotion_eligible') is not False):
            raise ValueError('Exact ten retained conditional account identities required')
        write_exclusive_json(folder/'result.json',result)
        outcome.update(status='completed',result_sha256=file_digest(folder/'result.json'),strategy_accounts=9,cash_controls=1,
                       historical_returns_computed=True,study_number=20)
    except BaseException as exc:
        outcome['error_type']=type(exc).__name__
        # Only the exception type is public; no financial row or credential echo.
        raise
    finally:
        if claim.decoding_started:
            outcome.update(financial_decode_started=True,research_study_consumed=True,study_number=20)
        claim.active=False
        write_exclusive_json(folder/'outcome.json',dict(**outcome,registration_sha256=expected_registration_sha256,
            finished_at=datetime.now(timezone.utc).isoformat(),guard_checks=claim.guard_count))
    return outcome
