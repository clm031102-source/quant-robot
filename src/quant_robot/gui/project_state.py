"""Current operator status, isolated from historical readiness artifacts.

This is a display projection, never an execution or promotion authorization.
Missing/stale state must not fall back to an old paper-ready candidate.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

STATE_PATH = Path('configs/project_state_cn_etf.json')
SAFETY = '研究与模拟阶段；不连接券商、不读取实盘账户、不下单。'
COUNT_KEYS = {'return_studies', 'source_screens', 'qualified_strategies',
              'forward_observation_days', 'prepared_candidates'}


def _confirmed_costs_projection(data: dict) -> dict:
    """Expose the ETF-only user confirmation, not a verified all-in tariff."""
    costs = data.get('user_confirmed_costs')
    if not isinstance(costs, dict):
        return {}
    minimum = costs.get('ETF_minimum_commission_CNY_per_transaction')
    source = costs.get('source')
    pending = costs.get('broker_and_rate_unconfirmed')
    if (type(minimum) not in (int, float) or minimum != 5
            or type(pending) is not bool
            or not isinstance(source, str)
            or not source.startswith('user_reported_') or not source.endswith('UTC')):
        return {}
    try:
        # This is a UTC source label, not the local status-update date.
        source_date = source[len('user_reported_'):-len('UTC')]
        if date.fromisoformat(source_date).isoformat() != source_date:
            return {}
    except ValueError:
        return {}
    result = dict(ETF_minimum_commission_CNY_per_transaction=minimum,
                  source=source, broker_and_rate_unconfirmed=pending)
    if pending:
        return result
    rate = costs.get('ETF_commission_rate')
    if (costs.get('broker') != '华宝证券'
            or type(rate) not in (int, float) or rate != 0.0001):
        return {}
    return dict(result, broker='华宝证券', ETF_commission_rate=rate)


def _risk_projection(data: dict) -> tuple[dict, float | None]:
    """An incomplete display record must not inherit an old risk profile."""
    risk = data.get('current_risk_policy')
    exposure = data.get('max_single_position_fraction_NAV')
    if not isinstance(risk, dict):
        return {}, None
    fractions = [exposure, risk.get('drawdown'), risk.get('daily_loss_fraction_previous_NAV')]
    if (any(type(v) not in (int, float) or not 0 < v <= 1 for v in fractions)
            or type(risk.get('complete_flat_cooldown_sessions')) is not int
            or risk['complete_flat_cooldown_sessions'] < 0):
        return {}, None
    return {key: risk[key] for key in ('drawdown', 'daily_loss_fraction_previous_NAV',
                                       'complete_flat_cooldown_sessions')}, exposure


def _campaign_projection(root: Path, campaign: dict) -> dict:
    """Show a checkpoint as a work record, never as proof a worker is alive."""
    if not isinstance(campaign, dict) or not campaign:
        return {}
    summary = dict(campaign_id=campaign.get('id'), deadline=campaign.get('deadline'),
                   checkpoint_available=False, checkpoint_at=None, tasks=[])
    try:
        checkpoint_path = Path(campaign['checkpoint'])
        if (checkpoint_path.is_absolute() or '..' in checkpoint_path.parts
                or not (root / checkpoint_path).resolve().is_relative_to(root.resolve())):
            return summary
        checkpoint = json.loads((root / checkpoint_path).read_text(encoding='utf-8-sig'))
        if (checkpoint['campaign_id'] != campaign['id']
                or checkpoint['deadline'] != campaign['deadline']
                or not isinstance(checkpoint['at'], str)
                or not isinstance(checkpoint['phase'], str)
                or not isinstance(checkpoint['active_tasks'], list)):
            return summary
        tasks = []
        for row in checkpoint['active_tasks']:
            if any(not isinstance(row.get(k), str) for k in ('id', 'stage', 'next')):
                return summary
            tasks.append(dict(task_id=row['id'], stage=row['stage'], next=row['next']))
        return dict(summary, checkpoint_available=True, checkpoint_at=checkpoint['at'],
                    phase=checkpoint['phase'], tasks=tasks)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return summary


def _load(root: Path, today: date) -> dict:
    data = json.loads((root / STATE_PATH).read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('schema_version') != 1
            or data.get('display_only') is not True or data.get('market') != 'CN_ETF'):
        raise ValueError('Invalid project status schema')
    age = (today - date.fromisoformat(data['updated_at'])).days
    if age < 0 or age > 7:
        raise ValueError('Project status requires a current evidence update')
    counts = data['counts']
    if (not isinstance(counts, dict) or set(counts) != COUNT_KEYS
            or any(type(n) is not int or n < 0 for n in counts.values())):
        raise ValueError('Invalid evidence counts')
    if (data.get('state') not in {'research_in_progress', 'paused', 'evidence_blocked'}
            or data.get('paper_observation_allowed') is not False
            or data.get('selected_candidate') is not None
            or counts['qualified_strategies'] != 0):
        raise ValueError('Display state cannot authorize or select a strategy')
    if (not isinstance(data.get('state_label'), str)
            or type(data.get('capital_cny')) is not int or data['capital_cny'] <= 0
            or type(data.get('actual_fees_verified')) is not bool):
        raise ValueError('Invalid account display fields')
    document = Path(data['authority_document'])
    if document.is_absolute() or '..' in document.parts or not (root / document).is_file():
        raise ValueError('Current authority document missing')
    for key in ('blockers', 'next_actions'):
        if not isinstance(data.get(key), list) or not data[key] or any(not isinstance(r, dict) for r in data[key]):
            raise ValueError('Explicit blockers and next actions required')
    for row in data['blockers']:
        if any(not isinstance(row.get(k), str) or not row[k].strip()
               for k in ('blocker_id', 'severity', 'track_id', 'evidence')):
            raise ValueError('Complete blocker descriptions required')
    for row in data['next_actions']:
        if (type(row.get('priority')) is not int or row['priority'] < 1
                or any(not isinstance(row.get(k), str) or not row[k].strip()
                       for k in ('track_id', 'title', 'reason'))):
            raise ValueError('Complete next actions required')
    return data


def current_project_status(root: str | Path = '.', *, today: date | None = None) -> dict:
    root = Path(root)
    observed = today or date.today()
    boundary = dict(broker_connection='disabled', account_reads='disabled',
                    order_placement='disabled', live_trading='disabled',
                    would_cross_live_boundary=False)
    base = dict(stage='gui_project_status', authority='current_project_state',
                source_path=str(STATE_PATH), checked_at=observed.isoformat(),
                display_only=True, selected_candidate={}, safety=SAFETY,
                boundary=boundary, paper_observation_allowed=False,
                live_boundary_allowed=False, data_gaps={}, provider_remediation={},
                residual_focus={}, tushare={'required_now': False,
                'reason': '仅解决选定候选实际依赖的数据缺口。'})
    try:
        data = _load(root, observed)
    except (OSError, ValueError, KeyError, TypeError):
        blocker = dict(blocker_id='current_project_state_unavailable', severity='block',
                       track_id='status', evidence='当前状态缺失、过期或不完整，需要核对最新证据。')
        return dict(base, overall_status='evidence_blocked', state_label='当前状态待核实',
                    generated_at=None, evidence_counts={}, blocker_count=1,
                    blockers=[blocker], readiness_items=[], next_actions=[
                        dict(priority=1, track_id='status', title='核对最新项目状态',
                             command='', reason=blocker['evidence'])])
    risk, exposure = _risk_projection(data)
    return dict(base, overall_status=data['state'], state_label=data['state_label'],
                generated_at=data['updated_at'], authority_document=data['authority_document'],
                evidence_counts=data['counts'], capital_cny=data['capital_cny'],
                actual_fees_verified=data['actual_fees_verified'],
                user_confirmed_costs=_confirmed_costs_projection(data),
                current_risk_policy=risk,
                max_single_position_fraction_NAV=exposure,
                campaign=_campaign_projection(root, data.get('campaign', {})),
                blockers=data['blockers'], blocker_count=len(data['blockers']),
                readiness_items=[], next_actions=data['next_actions'])


def current_daily_ops(root: str | Path, legacy_path: str | Path) -> dict:
    state = current_project_status(root)
    return dict(stage='gui_daily_ops', artifact_present=False, source_path=str(STATE_PATH),
                run_date=None, candidate={}, decision=dict(status='no_qualified_strategy',
                paper_trading_allowed=False, live_boundary_allowed=False,
                blocking_reasons=[r['blocker_id'] for r in state['blockers']],
                non_manual_blocking_reasons=[r['blocker_id'] for r in state['blockers']]),
                blockers=state['blockers'], signal={}, risk={}, risk_policy={},
                paper_profile={}, ticket_count=0, advisory_tickets=[], safety=SAFETY,
                current_project_state=state, legacy_artifact_path=str(legacy_path),
                legacy_artifact_is_current_authority=False)


def historical_daily_ops(pack: dict) -> dict:
    """An explicitly opened archive may be inspected, never activated."""
    return dict(pack, historical_decision=pack['decision'],
                historical_advisory_tickets=pack['advisory_tickets'],
                legacy_artifact_is_current_authority=False,
                decision=dict(status='historical_only', paper_trading_allowed=False,
                              live_boundary_allowed=False,
                              blocking_reasons=['historical_artifact_not_current_authority'],
                              non_manual_blocking_reasons=['historical_artifact_not_current_authority']),
                blockers=['historical_artifact_not_current_authority'],
                advisory_tickets=[], ticket_count=0)
