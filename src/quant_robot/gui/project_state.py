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
    return dict(base, overall_status=data['state'], state_label=data['state_label'],
                generated_at=data['updated_at'], authority_document=data['authority_document'],
                evidence_counts=data['counts'], capital_cny=data['capital_cny'],
                actual_fees_verified=data['actual_fees_verified'],
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
