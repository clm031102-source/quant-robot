"""Immutable single-study registration, exact PM scope, claim before outcome read."""
from datetime import date, datetime, timezone
import io
import json
from pathlib import Path
import tempfile

from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, sha256, write_exclusive_json,
)

DIRECTORY = 'data/reports/positive_ev_20260921/option_diagnostic'
REGISTRATION = DIRECTORY + '/registration.json'
PROPOSAL = 'configs/cn_etf_option_activity_diagnostic_20260921.json'
PROPOSAL_SHA256 = '8493b130eccbf0c2c4f25ea96bcd073b221a29656d828d5cfff614a033c4a6ac'
STAGE = 'single_option_activity_gross_diagnostic'
MODE = 'single_option_activity_diagnostic_only'
DECISION = 'option_activity_diagnostic_decision'
ROLES = {'proposal', 'source_review', 'history', 'history_claim', 'history_scope',
    'calendar', 'calendar_manifest', 'actions', 'dividend_review',
    *['bars_'+str(y) for y in range(2020, 2025)]}
IMPLEMENTATION = (
    'src/quant_robot/research/option_activity_study.py',
    'src/quant_robot/research/option_activity_diagnostic.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/price_basis.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/paper/corporate_actions.py',
    'src/quant_robot/data/cn_calendar_snapshot.py',
    'src/quant_robot/data/cn_trading_calendar.py',
    'src/quant_robot/storage/atomic.py',
    'src/quant_robot/storage/fingerprints.py',
    'scripts/run_cn_etf_option_activity_diagnostic.py', 'scripts/bootstrap.py',
)


def build_registration(*, inputs, code_files, branch, environment):
    if set(inputs) != ROLES or set(code_files) != set(IMPLEMENTATION):
        raise ValueError('Exact option study input roles and implementation required')
    for item in [*inputs.values(), *code_files.values()]:
        if set(item) != {'path', 'sha256'}:
            raise ValueError('Explicit path and hash required')
        resolve_path('.', item['path'])
        if len(item['sha256']) != 64 or any(c not in '0123456789abcdef' for c in item['sha256']):
            raise ValueError('SHA256 required')
    if any(k != v['path'] for k, v in code_files.items()):
        raise ValueError('Implementation path alias rejected')
    if inputs['proposal'] != {'path': PROPOSAL, 'sha256': PROPOSAL_SHA256}:
        raise ValueError('Exact frozen positive-direction option proposal required')
    if not branch.startswith('codex/factor-') or not environment:
        raise ValueError('Research branch and runtime required')
    body = dict(schema_version=1, stage=STAGE, inputs=inputs, code_files=code_files,
        branch=branch, environment=environment, max_executions=1,
        source_origin='retained_research_sources', conditional_gross_only=True,
        net_account_allowed=False, paper_promotion_allowed=False, final_holdout_allowed=False)
    return {**body, 'registration_id': sha256(canonical(body))}


def validate_registration(packet):
    expected = build_registration(**{k: packet[k] for k in ('inputs', 'code_files', 'branch', 'environment')})
    if canonical(expected) != canonical(packet):
        raise ValueError('Registration identity or scope changed')
    return packet


def admission(packet, raw):
    validate_registration(packet)
    return dict(status='authorized_once', registration_id=packet['registration_id'],
        registration_path=REGISTRATION, registration_sha256=sha256(raw),
        max_executions=1, execution_count=0, allowed_stage=STAGE,
        ledger_path=DIRECTORY+'/attempt_claim.json', conditional_gross_only=True,
        general_factor_batch_allowed=False, net_account_allowed=False,
        promotion_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root, DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json', 'result.json', 'outcome.json')):
        raise ValueError('Option hypothesis already consumed; no rerun')


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
    return {'mode': MODE, 'scope': family_config[DECISION]}


def preflight(root, scheduler, gate_supplier):
    raw = resolve_path(root, REGISTRATION).read_bytes()
    packet = validate_registration(json.loads(raw))
    require_unused(root)
    if scheduler.get(DECISION) != admission(packet, raw) or packet['environment'] != runtime_environment():
        raise ValueError('Exact unused admission and runtime required')
    snapshots = {}
    for group in ('code_files', 'inputs'):
        for role, record in packet[group].items():
            content = resolve_path(root, record['path']).read_bytes()
            if sha256(content) != record['sha256']:
                raise ValueError('Pinned file changed: '+role)
            if group == 'inputs': snapshots[role] = content
    review = json.loads(snapshots['source_review'])
    if (review.get('status') != 'conditional_source_use_reviewed'
            or review.get('inputs') != {k: v for k, v in packet['inputs'].items() if k != 'source_review'}
            or any(review.get(k) is not False for k in ('prices_decoded', 'factor_generated',
                'historical_availability_verified', 'net_account_allowed'))):
        raise ValueError('Exact conditional source-use review required')
    history_claim = json.loads(snapshots['history_claim'])
    history = json.loads(snapshots['history'])
    if (history_claim.get('status') != 'completed'
            or history_claim.get('result_sha256') != sha256(snapshots['history'])
            or history.get('scope_sha256') != sha256(snapshots['history_scope'])):
        raise ValueError('Official collection receipts and history scope differ')
    gate = gate_supplier()
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    safety, selected = gate['safety'], gate['selected']
    if not (0 <= age <= 30 and gate['status'] == 'ready' and not gate['blockers'] and gate['mode'] == MODE
            and gate['primary_market'] == 'CN_ETF' and safety.get('option_activity_diagnostic_allowed') is True
            and safety.get('option_activity_diagnostic_scope') == scheduler[DECISION]
            and safety.get('factor_batch_scope') == {} and selected['machine'] == 'office_desktop'
            and selected['task'] == 'factor_batch' and selected['branch'] == packet['branch']
            and selected['current_branch'] == packet['branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed', 'final_holdout_allowed', 'live_boundary_allowed'))):
        raise ValueError('Fresh exact option-activity PM gate required')
    return packet, snapshots, gate


def calculate(snapshots):
    import pandas as pd
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    from quant_robot.research.option_activity_diagnostic import monthly_rows, summarize
    from quant_robot.research.price_basis import build_cash_action_research_prices
    calendar = calendar_rows_from_snapshot(snapshots['calendar'], snapshots['calendar_manifest'],
        start=date(2020, 1, 2), end=date(2024, 6, 28))
    sessions = [d for d, opened in calendar if opened]
    history = json.loads(snapshots['history'])
    if len(sessions) != 1087 or history['status'] != 'count_structure_qualified' or not history['all_monthly_checks_passed']:
        raise ValueError('Qualified complete calendar and official source history required')
    frames = []
    for year in range(2020, 2025):
        frame = pd.read_parquet(io.BytesIO(snapshots['bars_'+str(year)]),
            columns=['asset_id', 'date', 'market', 'currency', 'close'],
            filters=[('asset_id', '==', 'CN_ETF_XSHG_510050')])
        if not pd.to_datetime(frame['date']).dt.year.eq(year).all():
            raise ValueError('Bar year differs from frozen partition')
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    with tempfile.TemporaryDirectory(prefix='option-activity-gross-') as temp:
        path = Path(temp)/'actions.json'; path.write_bytes(snapshots['actions'])
        basis = build_cash_action_research_prices(bars, path, sessions=sessions)
    levels = basis.bars.set_index('date')['adj_close']
    rows = monthly_rows(history['daily'], levels, sessions)
    if len(rows) != 52 or rows[0]['feature_month'] != '2020-01' or rows[-1]['feature_month'] != '2024-04':
        raise ValueError('Frozen complete interval count or endpoints differ')
    return {'stage': STAGE, 'diagnostic': summarize(rows), 'observations': rows,
        'price_basis': basis.evidence, 'net_account_result': False, 'formal_positive_ev_verified': False,
        'counts_as_forward_paper_days': 0, 'prior_search_history_complete': False}


def execute(root, scheduler, gate_supplier):
    packet, snapshots, gate = preflight(root, scheduler, gate_supplier)
    receipt = dict(registration_id=packet['registration_id'], claimed_at=datetime.now(timezone.utc).isoformat(),
        status='claimed_before_factor_and_price_decode')
    write_exclusive_json(resolve_path(root, DIRECTORY+'/attempt_claim.json'), receipt)
    try:
        result = {**calculate(snapshots), 'registration_id': packet['registration_id'], 'pm_gate': gate}
        write_exclusive_json(resolve_path(root, DIRECTORY+'/result.json'), result)
        terminal = dict(status='completed', result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal = dict(status='failed_consumed', error_type=type(exc).__name__)
        raise
    finally:
        write_exclusive_json(resolve_path(root, DIRECTORY+'/outcome.json'), {**receipt, **terminal,
            'finished_at': datetime.now(timezone.utc).isoformat()})
    return result
