"""One immutable dividend-style study; exclusive claim precedes real signal/outcome computation."""
from datetime import datetime, timezone
import json
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.dividend_style_diagnostic import calculate

DIRECTORY='data/reports/positive_ev_20260921/dividend_style_diagnostic'
REGISTRATION=DIRECTORY+'/registration.json'
PROPOSAL='configs/cn_etf_dividend_style_diagnostic_20260921.json'
PROPOSAL_SHA256='0f94aead7d335f26f17e4a3c739580e9256c0dec9161778d97cd27dc5dd39e31'
DECISION='dividend_style_diagnostic_decision'
STAGE='single_dividend_style_endpoint_cost_diagnostic'
MODE='single_dividend_style_diagnostic_only'
ROLES={
    'ETF_date_index', 'actions', 'annual_2013', 'annual_2014',
    'annual_2015', 'annual_2016', 'annual_2017', 'annual_2018',
    'annual_2019', 'annual_catalog', 'bars_2020', 'bars_2021',
    'bars_2022', 'bars_2023', 'bars_2024', 'calendar',
    'calendar_SSE', 'calendar_SZSE', 'calendar_manifest', 'distribution_2016_notice',
    'distribution_catalog', 'distribution_scope', 'dividend_annual_2008', 'dividend_annual_2009',
    'dividend_annual_2010', 'dividend_annual_2011', 'dividend_annual_2012', 'dividend_annual_2013',
    'dividend_annual_2014', 'dividend_annual_2015', 'dividend_annual_2016', 'dividend_annual_2017',
    'dividend_annual_2018', 'dividend_annual_2019', 'dividend_annual_2020', 'dividend_annual_2021',
    'dividend_annual_2022', 'dividend_annual_2023', 'dividend_prices', 'dp_method',
    'early_actions', 'early_calendar', 'early_calendar_manifest', 'early_price',
    'early_source_review', 'index_2022', 'index_original', 'legacy_catalog',
    'legacy_scope', 'lot_review', 'notice_2015', 'notice_2020',
    'old_calendar', 'old_calendar_manifest', 'old_calendar_review', 'original_proposal',
    'price_receipt', 'price_review', 'proposal', 'prospectus',
    'prospectus_catalog', 'raw_crosscheck_2020', 'raw_crosscheck_2021', 'raw_crosscheck_2022',
    'raw_crosscheck_2023', 'raw_crosscheck_2024', 'source_ledger', 'source_review',
    'price_claim',
}

IMPLEMENTATION=('src/quant_robot/research/dividend_style_study.py','src/quant_robot/research/dividend_style_diagnostic.py',
    'src/quant_robot/research/rrr_effective_diagnostic.py',
    'src/quant_robot/research/us_variance_risk_diagnostic.py',
    'src/quant_robot/research/labor_risk_diagnostic.py','src/quant_robot/research/disclosed_flow_diagnostic.py',
    'src/quant_robot/research/disclosed_flow_bounds.py','src/quant_robot/data/etf_reported_holdings.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py','src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py','src/quant_robot/data/cn_calendar_snapshot.py',
    'src/quant_robot/data/cn_trading_calendar.py','src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_dividend_style_diagnostic.py','scripts/bootstrap.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['proposal']!={'path':PROPOSAL,'sha256':PROPOSAL_SHA256}:raise ValueError('Frozen positive-direction proposal required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,max_executions=1,
        conditional_endpoint_cost_only=True,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_endpoint_cost_only=True,general_factor_batch_allowed=False,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('dividend-style hypothesis consumed; no rerun')


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
    proposal=json.loads(snapshots['proposal'])
    if any(proposal[role]!=packet['inputs'][role] for role in ('original_proposal','source_ledger')):
        raise ValueError('Source identities differ from frozen proposal')
    receipt=json.loads(snapshots['price_receipt']); claim=json.loads(snapshots['price_claim'])
    price_scope=proposal['source_scope']
    if any(r['snapshot']!=packet['inputs'][f"raw_crosscheck_{r['date'][:4]}"]
           for r in price_scope['retained_raw_crosschecks']):
        raise ValueError('Frozen raw price crosscheck identity differs')
    if (receipt.get('status')!='retained_current_source_version' or receipt.get('http_status')!=200
            or receipt.get('sha256')!=sha256(snapshots['dividend_prices'])
            or receipt.get('bytes')!=len(snapshots['dividend_prices'])
            or claim.get('scope_sha256')!=PROPOSAL_SHA256
            or any(r.get(k)!=price_scope[k] for r in (receipt,claim) for k in ('url','params'))):
        raise ValueError('Exact frozen price collection receipt required')
    review=json.loads(snapshots['source_review'])
    if (review.get('status')!='conditional_source_use_reviewed'
            or review.get('inputs')!={k:v for k,v in packet['inputs'].items() if k!='source_review'}
            or any(review.get(k) is not False for k in ('returns_calculated','factor_generated','historical_availability_verified','net_account_allowed'))):
        raise ValueError('Exact source-use self-review required')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('dividend_style_diagnostic_allowed') is True
            and safety.get('dividend_style_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact dividend-style PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_factor_and_outcome_decode')
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
