"""Read-only projection of the finite USD model operation's saved record."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

STATUS_PATH = Path('data/reports/us_allocation_model_20261109_20261207/current_status.json')
ASSETS = ('SPY', 'EFA', 'IEF', 'GLD')


def _amount(value):
    if not isinstance(value, str):
        raise ValueError('Amount must be a decimal string')
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError('Amount must be finite')
    return number


def _clock(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('Timestamp needs a time zone')
    return value


def _account(value):
    days = value['model_forward_days']
    if (value['schema'] != 'us_daily_model_snapshot_v1'
            or value['evidence_kind'] != 'conditional_forward_model'
            or value['execution_certified'] is not False
            or value['qualified'] is not False
            or type(value['real_forward_days']) is not int or value['real_forward_days'] != 0
            or value['artificial_model_days'] != 0
            or type(days) is not int or not 0 <= days <= 20):
        raise ValueError('Conditional model identity required')
    receipts = [_clock(row['received_at']) for row in value['source_receipts']]
    result = dict(status=value['status'], reason=value.get('reason'), model_forward_days=days,
                  initialized=False, latest_receipt=max(receipts, key=lambda x: datetime.fromisoformat(x.replace('Z', '+00:00'))) if receipts else None,
                  balance_date=None, NAV_USD=None, model_profit_USD=None,
                  spendable_cash_USD=None, locked_cash_USD=None, receivable_USD=None,
                  quantities=None, max_drawdown=None, model_fill_count=0)
    ledger = value['ledger']
    if ledger is None:
        if days:
            raise ValueError('Observed days require a ledger')
        return result
    balances = ledger['balances']
    quantities = balances['quantities']
    if (set(quantities) != set(ASSETS)
            or any(type(q) is not int or q < 0 for q in quantities.values())
            or len(ledger['days']) != days
            or any(fill.get('model_only') is not True for fill in ledger['fills'])):
        raise ValueError('Model ledger shape is inconsistent')
    nav = _amount(ledger['NAV'])
    return dict(result, initialized=True, balance_date=ledger['date'], NAV_USD=str(nav),
                model_profit_USD=str(nav - Decimal('1000')) if days else None,
                spendable_cash_USD=str(_amount(balances['spendable_cash'])),
                locked_cash_USD=str(_amount(balances['locked_cash'])),
                receivable_USD=str(sum((_amount(r['amount']) for r in balances['receivables'].values()), Decimal('0'))),
                quantities=quantities, max_drawdown=str(_amount(ledger['maxDD'])),
                model_fill_count=len(ledger['fills']))


def _installed_schedule(root, data):
    """An exact installation receipt can arrive after initial account creation."""
    parent = Path(root) / STATUS_PATH.parent
    saved = json.loads((parent / 'schedule_registration.json').read_bytes())
    if (saved['schema'] != 'us_allocation_model_schedule_v1' or saved['installed'] is not True
            or saved['capture_scope_sha256'] != data.get('capture_scope_sha256')
            or saved['task_name'] != 'USDAllocationConditionalModel_20261109_20261207'):
        return False
    exported = parent / 'scheduled_task_preparation/registered.utf16.xml'
    reference = saved['actual_export']
    if Path(reference['path']).resolve() != exported.resolve():
        return False
    raw = exported.read_bytes()
    return len(raw) == reference['bytes'] and hashlib.sha256(raw).hexdigest() == reference['sha256']


def current_us_model_status(root: str | Path = '.') -> dict:
    """Never run a strategy, fetch a price, or infer worker liveness from a file."""
    empty = dict(available=False, source_path=str(STATUS_PATH), status='not_deployed',
                 saved_at=None, model_forward_days=None, real_forward_days=0,
                 currency='USD', initial_model_cash='1000.00', accounts={}, schedule={},
                 operation_window={}, reason='日常美元模型尚未部署。',
                 display_only=True, execution_certified=False)
    try:
        raw = (Path(root) / STATUS_PATH).read_bytes()
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError('Saved model status is too large')
        data = json.loads(raw)
        if data['schema'] != 'us_allocation_model_operations_v1':
            raise ValueError('Unknown operation status')
        window = data['operation_window']
        if (window['start'], window['end'], window['scheduled_sessions']) != ('2026-11-09', '2026-12-07', 20):
            raise ValueError('Unexpected operation window')
        raw_accounts = data['accounts']
        if set(raw_accounts) != {'primary', 'stress'} and not data['status'].startswith('blocked'):
            raise ValueError('Complete accounts required outside a recorded failure')
        if not set(raw_accounts) <= {'primary', 'stress'}:
            raise ValueError('Unknown account role')
        accounts = {role: _account(value) for role, value in raw_accounts.items()}
        schedule = data['schedule']
        if type(schedule['installed']) is not bool:
            raise ValueError('Explicit installation record required')
        installed = schedule['installed']
        try:
            installed = _installed_schedule(root, data)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass  # Retain the runner's saved installation record, not a liveness claim.
        return dict(empty, available=True, status=data['status'], saved_at=_clock(data['updated_at']),
                    reason=data.get('reason'), accounts=accounts,
                    model_forward_days=min(a['model_forward_days'] for a in accounts.values()) if len(accounts) == 2 else None,
                    operation_window=dict(start=window['start'], end=window['end'], scheduled_sessions=20),
                    schedule=dict(installed=installed,
                                  next_capture_at=_clock(schedule.get('next_capture_at')),
                                  last_attempt_at=_clock(schedule.get('last_attempt_at')),
                                  last_attempt_status=schedule.get('last_attempt_status')))
    except FileNotFoundError:
        return empty
    except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
        return dict(empty, status='saved_record_unavailable', reason='日常美元模型的保存记录无法读取；收益与天数待核对。')
