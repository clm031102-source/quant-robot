"""One immutable Currency-gold study; exclusive claim precedes real signal/outcome computation."""
from datetime import datetime, timezone
import json
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.currency_gold_diagnostic import calculate

DIRECTORY='data/reports/positive_ev_20260922/currency_gold_diagnostic'
REGISTRATION=DIRECTORY+'/registration.json'
REVIEW='configs/cn_etf_currency_gold_gross_review_20260922.json'
REVIEW_SHA256='e8bf689ffd966f6b43539d31d44707c44e2dafb23763284d18621066b3e02f9b'
DECISION='currency_gold_diagnostic_decision'
STAGE='single_currency_gold_gross_diagnostic'
MODE='single_currency_gold_diagnostic_only'
ROLES = {
    'cadence_authority_0',
    'cadence_authority_1',
    'cadence_authority_10',
    'cadence_authority_100',
    'cadence_authority_101',
    'cadence_authority_102',
    'cadence_authority_103',
    'cadence_authority_104',
    'cadence_authority_105',
    'cadence_authority_106',
    'cadence_authority_107',
    'cadence_authority_108',
    'cadence_authority_109',
    'cadence_authority_11',
    'cadence_authority_110',
    'cadence_authority_111',
    'cadence_authority_112',
    'cadence_authority_113',
    'cadence_authority_114',
    'cadence_authority_115',
    'cadence_authority_116',
    'cadence_authority_117',
    'cadence_authority_118',
    'cadence_authority_119',
    'cadence_authority_12',
    'cadence_authority_120',
    'cadence_authority_121',
    'cadence_authority_122',
    'cadence_authority_123',
    'cadence_authority_124',
    'cadence_authority_125',
    'cadence_authority_126',
    'cadence_authority_127',
    'cadence_authority_128',
    'cadence_authority_129',
    'cadence_authority_13',
    'cadence_authority_130',
    'cadence_authority_131',
    'cadence_authority_132',
    'cadence_authority_133',
    'cadence_authority_134',
    'cadence_authority_135',
    'cadence_authority_136',
    'cadence_authority_137',
    'cadence_authority_138',
    'cadence_authority_139',
    'cadence_authority_14',
    'cadence_authority_140',
    'cadence_authority_141',
    'cadence_authority_142',
    'cadence_authority_143',
    'cadence_authority_144',
    'cadence_authority_145',
    'cadence_authority_146',
    'cadence_authority_147',
    'cadence_authority_148',
    'cadence_authority_149',
    'cadence_authority_15',
    'cadence_authority_150',
    'cadence_authority_151',
    'cadence_authority_152',
    'cadence_authority_153',
    'cadence_authority_154',
    'cadence_authority_155',
    'cadence_authority_156',
    'cadence_authority_157',
    'cadence_authority_158',
    'cadence_authority_159',
    'cadence_authority_16',
    'cadence_authority_160',
    'cadence_authority_161',
    'cadence_authority_162',
    'cadence_authority_163',
    'cadence_authority_164',
    'cadence_authority_165',
    'cadence_authority_166',
    'cadence_authority_167',
    'cadence_authority_168',
    'cadence_authority_169',
    'cadence_authority_17',
    'cadence_authority_170',
    'cadence_authority_171',
    'cadence_authority_172',
    'cadence_authority_173',
    'cadence_authority_174',
    'cadence_authority_175',
    'cadence_authority_176',
    'cadence_authority_177',
    'cadence_authority_178',
    'cadence_authority_179',
    'cadence_authority_18',
    'cadence_authority_180',
    'cadence_authority_181',
    'cadence_authority_182',
    'cadence_authority_183',
    'cadence_authority_184',
    'cadence_authority_185',
    'cadence_authority_186',
    'cadence_authority_187',
    'cadence_authority_188',
    'cadence_authority_19',
    'cadence_authority_2',
    'cadence_authority_20',
    'cadence_authority_21',
    'cadence_authority_22',
    'cadence_authority_23',
    'cadence_authority_24',
    'cadence_authority_25',
    'cadence_authority_26',
    'cadence_authority_27',
    'cadence_authority_28',
    'cadence_authority_29',
    'cadence_authority_3',
    'cadence_authority_30',
    'cadence_authority_31',
    'cadence_authority_32',
    'cadence_authority_33',
    'cadence_authority_34',
    'cadence_authority_35',
    'cadence_authority_36',
    'cadence_authority_37',
    'cadence_authority_38',
    'cadence_authority_39',
    'cadence_authority_4',
    'cadence_authority_40',
    'cadence_authority_41',
    'cadence_authority_42',
    'cadence_authority_43',
    'cadence_authority_44',
    'cadence_authority_45',
    'cadence_authority_46',
    'cadence_authority_47',
    'cadence_authority_48',
    'cadence_authority_49',
    'cadence_authority_5',
    'cadence_authority_50',
    'cadence_authority_51',
    'cadence_authority_52',
    'cadence_authority_53',
    'cadence_authority_54',
    'cadence_authority_55',
    'cadence_authority_56',
    'cadence_authority_57',
    'cadence_authority_58',
    'cadence_authority_59',
    'cadence_authority_6',
    'cadence_authority_60',
    'cadence_authority_61',
    'cadence_authority_62',
    'cadence_authority_63',
    'cadence_authority_64',
    'cadence_authority_65',
    'cadence_authority_66',
    'cadence_authority_67',
    'cadence_authority_68',
    'cadence_authority_69',
    'cadence_authority_7',
    'cadence_authority_70',
    'cadence_authority_71',
    'cadence_authority_72',
    'cadence_authority_73',
    'cadence_authority_74',
    'cadence_authority_75',
    'cadence_authority_76',
    'cadence_authority_77',
    'cadence_authority_78',
    'cadence_authority_79',
    'cadence_authority_8',
    'cadence_authority_80',
    'cadence_authority_81',
    'cadence_authority_82',
    'cadence_authority_83',
    'cadence_authority_84',
    'cadence_authority_85',
    'cadence_authority_86',
    'cadence_authority_87',
    'cadence_authority_88',
    'cadence_authority_89',
    'cadence_authority_9',
    'cadence_authority_90',
    'cadence_authority_91',
    'cadence_authority_92',
    'cadence_authority_93',
    'cadence_authority_94',
    'cadence_authority_95',
    'cadence_authority_96',
    'cadence_authority_97',
    'cadence_authority_98',
    'cadence_authority_99',
    'cadence_claim',
    'cadence_outcome',
    'cadence_registration',
    'cadence_result',
    'cadence_verification',
    'market_actions',
    'market_bars',
    'market_config_account_method',
    'market_config_execution_clarification',
    'market_config_payment_source_scope',
    'market_config_price_scope',
    'market_config_source_review',
    'market_config_terminal_action_scope',
    'market_current_research_account',
    'market_cycles',
    'market_daily_source_review',
    'market_equity_early_dates',
    'market_equity_history_annual_2013',
    'market_equity_history_annual_2014',
    'market_equity_history_annual_2015',
    'market_equity_history_annual_2016',
    'market_equity_history_annual_2017',
    'market_equity_history_annual_2018',
    'market_equity_history_annual_2019',
    'market_equity_history_distribution_2016_notice',
    'market_equity_history_early_actions',
    'market_equity_history_early_source_review',
    'market_equity_history_prior_authority_0',
    'market_equity_history_prior_authority_1',
    'market_equity_history_prior_authority_10',
    'market_equity_history_prior_authority_11',
    'market_equity_history_prior_authority_12',
    'market_equity_history_prior_authority_13',
    'market_equity_history_prior_authority_14',
    'market_equity_history_prior_authority_15',
    'market_equity_history_prior_authority_16',
    'market_equity_history_prior_authority_17',
    'market_equity_history_prior_authority_18',
    'market_equity_history_prior_authority_19',
    'market_equity_history_prior_authority_2',
    'market_equity_history_prior_authority_20',
    'market_equity_history_prior_authority_3',
    'market_equity_history_prior_authority_4',
    'market_equity_history_prior_authority_5',
    'market_equity_history_prior_authority_6',
    'market_equity_history_prior_authority_7',
    'market_equity_history_prior_authority_8',
    'market_equity_history_prior_authority_9',
    'market_gold_annual_audit',
    'market_gold_terminal_review',
    'market_initial_source_ledger',
    'market_input_binding',
    'market_input_review',
    'market_late_equity_actions',
    'market_payment_source_scope_distribution_2014-01-21_claim_claim',
    'market_payment_source_scope_distribution_2014-01-21_claim_receipt',
    'market_payment_source_scope_distribution_2014-01-21_claim_source',
    'market_payment_source_scope_distribution_2015-01-20_claim_claim',
    'market_payment_source_scope_distribution_2015-01-20_claim_receipt',
    'market_payment_source_scope_distribution_2015-01-20_claim_source',
    'market_payment_source_scope_distribution_2017-01-23_claim_claim',
    'market_payment_source_scope_distribution_2017-01-23_claim_receipt',
    'market_payment_source_scope_distribution_2017-01-23_claim_source',
    'market_payment_source_scope_distribution_2018-01-23_claim_claim',
    'market_payment_source_scope_distribution_2018-01-23_claim_receipt',
    'market_payment_source_scope_distribution_2018-01-23_claim_source',
    'market_payment_source_scope_distribution_2019-01-16_claim_claim',
    'market_payment_source_scope_distribution_2019-01-16_claim_receipt',
    'market_payment_source_scope_distribution_2019-01-16_claim_source',
    'market_payment_source_scope_distribution_2019-12-11_claim_claim',
    'market_payment_source_scope_distribution_2019-12-11_claim_receipt',
    'market_payment_source_scope_distribution_2019-12-11_claim_source',
    'market_payment_source_scope_distribution_catalog_claim_claim',
    'market_payment_source_scope_distribution_catalog_claim_receipt',
    'market_payment_source_scope_distribution_catalog_claim_source',
    'market_price_scope_equity_early_va_claim_claim',
    'market_price_scope_equity_early_va_claim_receipt',
    'market_price_scope_equity_early_va_claim_source',
    'market_price_scope_gold_dates_claim_claim',
    'market_price_scope_gold_dates_claim_receipt',
    'market_price_scope_gold_dates_claim_source',
    'market_price_scope_gold_ohlcva_claim_claim',
    'market_price_scope_gold_ohlcva_claim_receipt',
    'market_price_scope_gold_ohlcva_claim_source',
    'market_proposal',
    'market_public_exposure',
    'market_registration',
    'market_retained_calendar',
    'market_retained_calendar_manifest',
    'market_retained_equity_2020_2024_ohlc',
    'market_retained_equity_2020_2024_turnover',
    'market_retained_equity_date_index',
    'market_retained_equity_early_ohlc',
    'market_retained_local_bars_2020',
    'market_retained_local_bars_2021',
    'market_retained_local_bars_2022',
    'market_retained_local_bars_2023',
    'market_retained_local_bars_2024',
    'market_retained_official_volume_display_script',
    'market_retained_old_calendar',
    'market_retained_old_calendar_manifest',
    'market_reused_gold_source_0',
    'market_reused_gold_source_1',
    'market_reused_gold_source_2',
    'market_reused_gold_source_3',
    'market_reused_gold_source_4',
    'market_sessions',
    'market_source_review_annual_2013_claim_claim',
    'market_source_review_annual_2013_claim_receipt',
    'market_source_review_annual_2013_claim_source',
    'market_source_review_annual_2014_claim_claim',
    'market_source_review_annual_2014_claim_receipt',
    'market_source_review_annual_2014_claim_source',
    'market_source_review_annual_2015_claim_claim',
    'market_source_review_annual_2015_claim_receipt',
    'market_source_review_annual_2015_claim_source',
    'market_source_review_annual_2016_claim_claim',
    'market_source_review_annual_2016_claim_receipt',
    'market_source_review_annual_2016_claim_source',
    'market_source_review_annual_2017_claim_claim',
    'market_source_review_annual_2017_claim_receipt',
    'market_source_review_annual_2017_claim_source',
    'market_source_review_annual_2018_claim_claim',
    'market_source_review_annual_2018_claim_receipt',
    'market_source_review_annual_2018_claim_source',
    'market_source_review_annual_2019_claim_claim',
    'market_source_review_annual_2019_claim_receipt',
    'market_source_review_annual_2019_claim_source',
    'market_source_review_annual_2020_claim_claim',
    'market_source_review_annual_2020_claim_receipt',
    'market_source_review_annual_2020_claim_source',
    'market_source_review_annual_2021_claim_claim',
    'market_source_review_annual_2021_claim_receipt',
    'market_source_review_annual_2021_claim_source',
    'market_source_review_annual_2022_claim_claim',
    'market_source_review_annual_2022_claim_receipt',
    'market_source_review_annual_2022_claim_source',
    'market_source_review_annual_2023_claim_claim',
    'market_source_review_annual_2023_claim_receipt',
    'market_source_review_annual_2023_claim_source',
    'market_source_review_annual_catalog_claim_claim',
    'market_source_review_annual_catalog_claim_receipt',
    'market_source_review_annual_catalog_claim_source',
    'market_terminal_action_scope_catalog_claim_claim',
    'market_terminal_action_scope_catalog_claim_receipt',
    'market_terminal_action_scope_catalog_claim_source',
    'market_terminal_action_scope_gold_2024_interim_claim_claim',
    'market_terminal_action_scope_gold_2024_interim_claim_receipt',
    'market_terminal_action_scope_gold_2024_interim_claim_source',
    'proposal',
    'source_review',
}
IMPLEMENTATION=('src/quant_robot/research/currency_gold_study.py', 'src/quant_robot/research/currency_gold_diagnostic.py', 'src/quant_robot/research/monthly_diagnostic_registration.py', 'src/quant_robot/research/pm_startup_gate.py', 'src/quant_robot/research/family_scheduler.py', 'src/quant_robot/storage/atomic.py', 'scripts/run_cn_etf_currency_gold_diagnostic.py', 'scripts/bootstrap.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['source_review']!={'path':REVIEW,'sha256':REVIEW_SHA256}:raise ValueError('Frozen currency-gold source-use review required')
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
        raise ValueError('Currency-gold hypothesis consumed; no rerun')


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
    if (review['fixed']!={k:v for k,v in packet['inputs'].items() if k!='source_review'}
            or review['returns_calculated'] is not False or review['net_account_allowed'] is not False):
        raise ValueError('Exact pre-outcome source review required')
    proof=json.loads(snapshots['cadence_verification'])
    cadence=json.loads(snapshots['cadence_result'])
    outcome=json.loads(snapshots['cadence_outcome'])
    if (proof['status']!='passed' or proof['result_sha256']!=sha256(snapshots['cadence_result'])
            or proof['registration_sha256']!=sha256(snapshots['cadence_registration'])
            or outcome['status']!='completed' or outcome['result_sha256']!=proof['result_sha256']
            or cadence['screen']['passed'] is not True or cadence['returns_computed'] is not False
            or len(proof['pins'])!=189):
        raise ValueError('Completed and reconciled cadence pass required')
    for i,original in enumerate(proof['pins']):
        if packet['inputs'][f'cadence_authority_{i}']['sha256']!=original['sha256']:
            raise ValueError('Cadence authority changed')
    market=json.loads(snapshots['market_registration'])
    for role,item in market['inputs'].items():
        if packet['inputs']['market_'+role]!=item:
            raise ValueError('Retained financial source identity changed')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('currency_gold_diagnostic_allowed') is True
            and safety.get('currency_gold_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact Currency-gold PM gate required')
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
