"""One immutable electricity-activity study; exclusive claim precedes actual data decode."""
from datetime import datetime, timezone
import json
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.electricity_activity_diagnostic import calculate

DIRECTORY='data/reports/positive_ev_20260921/electricity_activity_diagnostic'
REGISTRATION=DIRECTORY+'/registration.json'
PROPOSAL='configs/cn_etf_electricity_activity_diagnostic_20260922.json'
PROPOSAL_SHA256='ab8f2f2c26ecdcfdbb927c2c56f898ba0bca4aa73babdbe1d515cfbf03e387da'
DECISION='electricity_activity_diagnostic_decision'
STAGE='single_electricity_activity_gross_diagnostic'
MODE='single_electricity_activity_diagnostic_only'
ROLES={
    'actions',
    'calendar',
    'calendar_manifest',
    'distribution_2016_notice',
    'early_actions',
    'early_price',
    'early_source_review',
    'history_source_inventory',
    'history_source_inventory_verification',
    'history_source_manifest',
    'legacy_Word_table',
    'nea_release_004_image_1',
    'nea_release_062_image_1',
    'nea_release_062_image_2',
    'nea_release_068_image_1',
    'nea_release_094_image_1',
    'nea_release_096_image_1',
    'nea_release_098_image_1',
    'nea_release_100_image_1',
    'nea_release_111_image_1',
    'nea_release_130_attachment',
    'nea_release_134_image_1',
    'nea_release_134_image_2',
    'nea_release_145_image_1',
    'nea_release_147_image_1',
    'nea_release_149_image_1',
    'nea_release_153_image_1',
    'nea_release_165_image_1',
    'old_calendar',
    'old_calendar_manifest',
    'old_calendar_review',
    'original_proposal',
    'price_review',
    'proposal',
    'reconciliation_review',
    'source_evidence_May_newspaper_corroboration',
    'source_evidence_candidate_fields',
    'source_evidence_cross_source_conflicts',
    'source_evidence_docx_table_rows',
    'source_evidence_external_word_visual_review',
    'source_evidence_image_table_annotations',
    'source_evidence_materialization_scope',
    'source_evidence_missing_release_ledger',
    'source_evidence_missing_release_scope',
    'source_evidence_monthly_source_ledger',
    'source_evidence_people_20230615_frontpage',
    'source_evidence_reconcile_sources',
    'source_evidence_rounding_boundary_checks',
    'source_evidence_source_dates',
    'source_evidence_source_ledger',
    'source_evidence_supplemental_inventory',
    'source_evidence_within_source_conflicts',
    'source_review',
    'source_rows',
}
ROLES |= {f'raw_nea_release_{i:03d}' for i in range(1,187)}
ROLES |= {f'prior_authority_{i}' for i in range(21)}
ROLES |= {f'bars_{y}' for y in range(2020,2025)} | {f'annual_{y}' for y in range(2013,2020)}
IMPLEMENTATION=('src/quant_robot/research/electricity_activity_study.py','src/quant_robot/research/electricity_activity_diagnostic.py',
    'src/quant_robot/research/us_variance_risk_diagnostic.py','src/quant_robot/research/labor_risk_diagnostic.py',
    'src/quant_robot/research/disclosed_flow_diagnostic.py','src/quant_robot/research/disclosed_flow_bounds.py',
    'src/quant_robot/data/etf_reported_holdings.py','src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/paper/corporate_actions.py','src/quant_robot/data/cn_calendar_snapshot.py',
    'src/quant_robot/data/cn_trading_calendar.py','src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_electricity_activity_diagnostic.py','scripts/bootstrap.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['proposal']!={'path':PROPOSAL,'sha256':PROPOSAL_SHA256}:raise ValueError('Frozen fixed electricity proposal required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,max_executions=1,
        conditional_gross_only=True,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_gross_only=True,general_factor_batch_allowed=False,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Electricity-activity hypothesis consumed; no rerun')


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0 or family_schedule['summary'].get('active_primary_families')!=0):return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):return None
    except (OSError,ValueError,KeyError,TypeError):return None
    return {'mode':MODE,'scope':family_config[DECISION]}


def preflight(root,scheduler,gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():raise ValueError('Exact unused admission/runtime required')
    snapshots={}
    for group in ('code_files','inputs'):
        for role,item in packet[group].items():
            content=resolve_path(root,item['path']).read_bytes()
            if sha256(content)!=item['sha256']:raise ValueError('Pinned file changed: '+role)
            if group=='inputs':snapshots[role]=content
    review=json.loads(snapshots['source_review'])
    if (review.get('status')!='conditional_electricity_inputs_reviewed_before_states'
            or review.get('inputs')!={k:v for k,v in packet['inputs'].items() if k!='source_review'}
            or review.get('conditional_selection_ready') is not True
            or any(review.get(k) is not False for k in ('raw_prices_decoded_this_preparation','factor_generated',
                'returns_computed','historical_vintage_verified','net_account_allowed'))):
        raise ValueError('Exact conditional source-use self-review required')
    proposal=json.loads(snapshots['proposal'])
    if proposal['source_selection_review']!=packet['inputs']['reconciliation_review']:
        raise ValueError('Frozen source selection review differs')
    reconciliation=json.loads(snapshots['reconciliation_review'])
    if (reconciliation.get('conditional_selection_ready') is not True
            or reconciliation.get('same_release_conflicts')!=0
            or reconciliation.get('different_release_conflicts')!=1
            or reconciliation.get('financial_states_generated') is not False):
        raise ValueError('Conditional version-selection evidence differs')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('electricity_activity_diagnostic_allowed') is True
            and safety.get('electricity_activity_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact electricity-activity PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_factor_and_price_decode')
    write_exclusive_json(resolve_path(root,DIRECTORY+'/attempt_claim.json'),receipt)
    try:
        result={**calculate(snapshots),'registration_id':packet['registration_id'],'pm_gate':gate}
        write_exclusive_json(resolve_path(root,DIRECTORY+'/result.json'),result)
        terminal=dict(status='completed',result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal=dict(status='failed_consumed',error_type=type(exc).__name__);raise
    finally:
        write_exclusive_json(resolve_path(root,DIRECTORY+'/outcome.json'),{**receipt,**terminal,'finished_at':datetime.now(timezone.utc).isoformat()})
    return result
