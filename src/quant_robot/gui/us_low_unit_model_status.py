"""Read only the saved four-model projection; never import a strategy or fetch data."""
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from quant_robot.gui.us_model_status import _amount, _clock


STATUS_PATH = Path('data/reports/us_low_unit_models_20261109_20261207/current_status.json')
ASSETS = ('SPYM','EFA','IEF','GLDM')
ROLES = ('monthly_primary','monthly_stress','drift_primary','drift_stress')


def _account(value, role, days, received, balance_date):
    cost = role.split('_')[1]
    if (value['scenario_id'] != role or value['scenario_role'] != cost
            or value['currency'] != 'USD' or value['initial_cash'] != '1000.00'
            or (value['minimum_commission'],value['slippage_bps']) !=
            (('1.00',10) if cost == 'primary' else ('2.50',30))):
        raise ValueError('Scenario identity differs')
    ledger=value['ledger']; balances=ledger['balances']; quantities=balances['quantities']
    if (set(quantities) != set(ASSETS) or any(type(q) is not int or q < 0 for q in quantities.values())
            or ledger['date'] != balance_date or len(ledger['days']) != days
            or any(fill.get('model_only') is not True or fill.get('execution_certified') is not False
                   for fill in ledger['fills'])):
        raise ValueError('Four-model ledger shape differs')
    nav=_amount(ledger['NAV'])
    return dict(initialized=True, model_forward_days=days, balance_date=balance_date,
        NAV_USD=str(nav), model_profit_USD=str(nav-Decimal('1000')) if days else None,
        spendable_cash_USD=str(_amount(balances['spendable_cash'])),
        locked_cash_USD=str(_amount(balances['locked_cash'])),
        receivable_USD=str(sum((_amount(x['amount']) for x in balances['receivables'].values()),Decimal(0))),
        quantities=quantities, max_drawdown=str(_amount(ledger['maxDD'])),
        model_fill_count=len(ledger['fills']), latest_receipt=received,
        execution_cost_USD=str(sum((_amount(ledger[k]) for k in
            ('total_commission','total_slippage','total_sell_levy','total_CIL_cost')),Decimal(0))))


def _installed(root, data):
    parent=Path(root)/STATUS_PATH.parent
    record=json.loads((parent/'schedule_registration.json').read_bytes())
    if (record['schema'] != 'us_low_unit_model_schedule_v1' or record['installed'] is not True
            or record['capture_scope_sha256'] != data['capture_scope_sha256']
            or record['task_name'] != 'USDLowUnitFourModels_20261109_20261207'):
        return False
    exported=parent/'scheduled_task_preparation/registered.utf16.xml'; ref=record['actual_export']
    raw=exported.read_bytes()
    return (Path(ref['path']).resolve() == exported.resolve() and len(raw) == ref['bytes']
            and hashlib.sha256(raw).hexdigest() == ref['sha256'])


def current_low_unit_model_status(root='.'):
    empty=dict(available=False, status='not_deployed', reason='四模型日常运行正在准备，尚未初始化。',
        source_path=str(STATUS_PATH), saved_at=None, accounts={}, schedule={}, model_forward_days=None,
        real_forward_days=0, qualified=False, currency='USD', initial_model_cash='1000.00',
        independent_scenarios_not_one_4000USD_portfolio=True, display_only=True, execution_certified=False)
    try:
        raw=(Path(root)/STATUS_PATH).read_bytes()
        if len(raw)>4*1024*1024: raise ValueError('Status too large')
        data=json.loads(raw); snapshot=data['snapshot']; window=data['operation_window']
        if (data['schema']!='us_low_unit_model_operations_v1' or data['qualified'] is not False
                or data['strict_real_forward_days']!=0
                or (window['start'],window['end'],window['scheduled_sessions']) != ('2026-11-09','2026-12-07',20)):
            raise ValueError('Operations identity differs')
        accounts={}; days=None
        if snapshot:
            days=snapshot['model_forward_days']
            if (snapshot['schema']!='us_low_unit_four_model_snapshot_v1'
                    or snapshot['evidence_kind']!='conditional_provider_observation'
                    or snapshot['constructed_from_market_data'] is not True or snapshot['qualified'] is not False
                    or type(snapshot['strict_forward_days']) is not int or snapshot['strict_forward_days']!=0
                    or snapshot['artificial_model_days']!=0 or type(days) is not int or not 0<=days<=20
                    or snapshot['assets']!=list(ASSETS) or set(snapshot['accounts'])!=set(ROLES)
                    or snapshot['independent_scenarios_not_one_4000USD_portfolio'] is not True):
                raise ValueError('Four conditional scenarios required')
            received=_clock(snapshot['last_source_received_at'])
            accounts={role:_account(snapshot['accounts'][role],role,days,received,snapshot['date']) for role in ROLES}
        elif not data['status'].startswith('blocked'):
            raise ValueError('Missing four-model snapshot')
        installed=False
        try: installed=_installed(root,data)
        except (OSError,ValueError,KeyError,TypeError,AttributeError): pass
        return dict(empty,available=True,status=data['status'],reason=data.get('reason'),
            saved_at=_clock(data['updated_at']),accounts=accounts,model_forward_days=days,
            schedule=dict(installed=installed,next_capture_at=_clock(data['schedule'].get('next_capture_at')),
                last_attempt_at=_clock(data['schedule'].get('last_attempt_at')),
                last_attempt_status=data['schedule'].get('last_attempt_status')),
            operation_window=window)
    except FileNotFoundError: return empty
    except (OSError,ValueError,KeyError,TypeError,AttributeError,InvalidOperation):
        return dict(empty,status='saved_record_unavailable',reason='四模型记录不完整，收益和观察天数待核对。')
