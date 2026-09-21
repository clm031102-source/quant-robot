"""One-use credit-premium cadence screen; no price or cash-distribution roles."""
from datetime import datetime, timezone
import json

from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, sha256, write_exclusive_json,
)
from quant_robot.research.credit_premium_cadence import calculate

DIRECTORY = 'data/reports/positive_ev_20260922/credit_premium_cadence'
REGISTRATION = DIRECTORY + '/registration.json'
DECISION = 'credit_premium_cadence_decision'
STAGE = 'single_credit_premium_cadence_screen'
MODE = 'single_credit_premium_cadence_only'
FROZEN = {
    'proposal': {'path': 'configs/cn_etf_credit_premium_proposal_20260922.json',
                 'sha256': '7f1fda7d41552e5b701a63e2bb425f86bdbbaf073410b818351bdd40a89ba0af'},
    'source_summary': {'path': 'configs/cn_etf_credit_premium_source_review_20260922.json',
                 'sha256': '33bc2bf502b707822da9965f31dfa2137dc07dbd0f95f1b9f7a485074896d492'},
    'calendar': {'path': 'data/reports/positive_ev_20260921/labor_risk_diagnostic/inputs/calendar.csv',
                 'sha256': 'dbecac271ded4b95da6234658742177569405c477097ec1b780914ebddcaa11a'},
    'calendar_manifest': {'path': 'data/reports/positive_ev_20260921/labor_risk_diagnostic/inputs/calendar_manifest.json',
                          'sha256': '4b0e6a524e567a3ea81c94cc1a822371699562df9ac0a5591e51f324d2199d6b'},
    'old_calendar': {'path': 'data/reports/positive_ev_20260921/us_variance_risk_diagnostic/inputs/old_calendar.csv',
                     'sha256': '62d254f0c4743b2e153d52b818eb3e663ca96e85bae32a57c804cf1ef2d14bb9'},
    'old_calendar_manifest': {'path': 'data/reports/positive_ev_20260921/us_variance_risk_diagnostic/inputs/old_calendar_manifest.json',
                              'sha256': '4e76cc247564ed24ab38481e407216526a8dcdef18b082b8ca9cd754c383aef9'},
    'old_calendar_review': {'path': 'data/reports/positive_ev_20260921/us_variance_risk_diagnostic/inputs/old_calendar_review.json',
                            'sha256': 'a565a029589751d77c90f5a7b0214e266b0f792a523ca1a1c563f4f5c9f181d0'},
}
ROLES = {'proposal', 'source_summary', 'source_inventory', 'source_verification', 'source_scope',
         'source_review', 'calendar', 'calendar_manifest', 'old_calendar',
         'old_calendar_manifest', 'old_calendar_review', *[f'source_authority_{i}' for i in range(73)]}
IMPLEMENTATION = (
    'src/quant_robot/research/credit_premium_cadence.py',
    'src/quant_robot/research/credit_premium_cadence_study.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py', 'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/data/cn_calendar_snapshot.py', 'src/quant_robot/data/cn_trading_calendar.py',
    'src/quant_robot/research/enterprise_liquidity_cadence.py', 'src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_credit_premium_cadence.py', 'scripts/bootstrap.py',
)


def build_registration(*, inputs, code_files, branch, environment):
    if set(inputs) != ROLES or set(code_files) != set(IMPLEMENTATION):
        raise ValueError('Exact source/calendar inputs and implementation required; no outcome roles')
    for item in [*inputs.values(), *code_files.values()]:
        if set(item) != {'path', 'sha256'}:
            raise ValueError('Path and SHA256 required')
        resolve_path('.', item['path'])
        digest = item['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Lowercase SHA256 required')
    if any(name != item['path'] for name, item in code_files.items()):
        raise ValueError('Implementation aliases rejected')
    if any(inputs[role] != pin for role, pin in FROZEN.items()):
        raise ValueError('Frozen proposal, interpretation and source summary required')
    if not branch.startswith('codex/factor-') or not environment:
        raise ValueError('Task branch and runtime required')
    body = dict(schema_version=1, stage=STAGE, inputs=inputs, code_files=code_files,
                branch=branch, environment=environment, max_executions=1,
                source_cadence_only=True, returns_allowed=False, net_account_allowed=False,
                promotion_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False)
    return dict(body, registration_id=sha256(canonical(body)))


def validate_registration(packet):
    expected = build_registration(**{k: packet[k] for k in ('inputs', 'code_files', 'branch', 'environment')})
    if canonical(expected) != canonical(packet):
        raise ValueError('Registration changed')
    return packet


def admission(packet, raw):
    validate_registration(packet)
    return dict(status='authorized_once', registration_id=packet['registration_id'],
                registration_path=REGISTRATION, registration_sha256=sha256(raw),
                max_executions=1, execution_count=0, allowed_stage=STAGE,
                ledger_path=DIRECTORY+'/attempt_claim.json', source_cadence_only=True,
                returns_allowed=False, general_factor_batch_allowed=False,
                net_account_allowed=False, promotion_allowed=False,
                final_holdout_allowed=False, live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root, DIRECTORY+'/'+name).exists()
           for name in ('attempt_claim.json', 'result.json', 'outcome.json')):
        raise ValueError('Credit-premium cadence hypothesis consumed; no rerun')


def scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_batch' or family_config.get(DECISION, {}).get('status') != 'authorized_once':
        return None
    if (set(family_schedule.get('blockers', [])) != {'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share') != 0
            or family_schedule['summary'].get('active_primary_families') != 0):
        return None
    try:
        raw = resolve_path(root, REGISTRATION).read_bytes()
        packet = validate_registration(json.loads(raw))
        require_unused(root)
        if packet['branch'] != branch or family_config[DECISION] != admission(packet, raw):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return dict(mode=MODE, scope=family_config[DECISION])


def _source_chain(packet, snapshots):
    inputs = packet['inputs']
    summary = json.loads(snapshots['source_summary'])
    for role, key in [('proposal', 'economic_proposal'), ('source_scope', 'source_scope'),
                      ('source_inventory', 'corpus_review'),
                      ('source_verification', 'second_implementation_verification')]:
        if inputs[role] != summary['pins'][key]:
            raise ValueError('Frozen source summary and input identity differ')
    proof = json.loads(snapshots['source_verification'])
    if (proof.get('status') != 'passed' or proof.get('spreads_calculated') is not False
            or proof.get('ETF_outcomes_read') is not False or len(proof['pins']) != 73):
        raise ValueError('Pre-state original-history verification required')
    for i, original in enumerate(proof['pins']):
        # Copies preserve the exact bytes of all73original authority files;
        # fixed local names keep external absolute paths out of the executor.
        expected = dict(path=DIRECTORY+f'/authority/{i:02d}.source', sha256=original['sha256'])
        if inputs[f'source_authority_{i}'] != expected:
            raise ValueError('Original source authority identity differs')
    corpus = json.loads(snapshots['source_inventory'])
    if (corpus['scope_sha256'] != inputs['source_scope']['sha256']
            or any(corpus.get(k) is not False for k in
                   ('spreads_calculated', 'signals_generated', 'ETF_outcomes_read',
                    'historical_vintage_certified', 'historical_release_clock_certified'))):
        raise ValueError('Conditional pre-state source corpus required')
    review = json.loads(snapshots['source_review'])
    if (review.get('status') != 'conditional_cadence_inputs_reviewed_before_states'
            or review.get('inputs') != {k: v for k, v in inputs.items() if k != 'source_review'}
            or any(review.get(k) is not False for k in
                   ('factor_generated', 'returns_computed', 'ETF_outcomes_read', 'historical_vintage_verified'))):
        raise ValueError('Exact conditional source-use review required')


def preflight(root, scheduler, gate_supplier):
    raw = resolve_path(root, REGISTRATION).read_bytes()
    packet = validate_registration(json.loads(raw))
    require_unused(root)
    if scheduler.get(DECISION) != admission(packet, raw) or packet['environment'] != runtime_environment():
        raise ValueError('Exact unused cadence admission/runtime required')
    snapshots = {}
    for group in ('code_files', 'inputs'):
        for role, pin in packet[group].items():
            content = resolve_path(root, pin['path']).read_bytes()
            if sha256(content) != pin['sha256']:
                raise ValueError('Pinned file changed: '+role)
            if group == 'inputs':
                snapshots[role] = content
    _source_chain(packet, snapshots)
    gate = gate_supplier()
    safety, selected = gate['safety'], gate['selected']
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0 <= age <= 30 and gate['status'] == 'ready' and not gate['blockers']
            and gate['mode'] == MODE and gate['primary_market'] == 'CN_ETF'
            and safety.get('credit_premium_cadence_allowed') is True
            and safety.get('credit_premium_cadence_scope') == scheduler[DECISION]
            and safety.get('factor_batch_scope') == {}
            and selected['machine'] == 'office_desktop' and selected['task'] == 'factor_batch'
            and selected['branch'] == packet['branch'] == selected['current_branch']
            and all(safety.get(k) is False for k in
                    ('factor_batch_allowed', 'final_holdout_allowed', 'live_boundary_allowed'))):
        raise ValueError('Fresh exact credit-premium-cadence PM gate required')
    return packet, snapshots, gate


def execute(root, scheduler, gate_supplier):
    packet, snapshots, gate = preflight(root, scheduler, gate_supplier)
    receipt = dict(registration_id=packet['registration_id'],
                   claimed_at=datetime.now(timezone.utc).isoformat(), status='claimed_before_real_states')
    write_exclusive_json(resolve_path(root, DIRECTORY+'/attempt_claim.json'), receipt)
    try:
        result = dict(calculate(snapshots), registration_id=packet['registration_id'], pm_gate=gate)
        write_exclusive_json(resolve_path(root, DIRECTORY+'/result.json'), result)
        terminal = dict(status='completed', result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal = dict(status='failed_consumed', error_type=type(exc).__name__)
        raise
    finally:
        write_exclusive_json(resolve_path(root, DIRECTORY+'/outcome.json'),
                             dict(receipt, **terminal, finished_at=datetime.now(timezone.utc).isoformat()))
    return result
