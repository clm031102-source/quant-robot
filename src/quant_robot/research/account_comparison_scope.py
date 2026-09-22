"""Prospective PM admission check for full account control specifications."""
import json

from quant_robot.paper.comparative_allocation import validate_policy
from quant_robot.research.monthly_diagnostic_registration import resolve_path, sha256

REQUIRED_CODE = (
    'src/quant_robot/paper/comparative_allocation.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/research/pm_startup_gate.py',
)


def review_account_comparison(root, *, mode, scope, protocol):
    full_account = '_account_' in mode or scope.get('net_account_allowed') is True
    if not full_account:
        return dict(status='not_applicable',blockers=[])
    if protocol != {'version':1,'holding_and_cash_required':True}:
        return dict(status='blocked',blockers=['account_comparison_protocol_invalid'])
    try:
        def content(pin):
            if set(pin)!={'path','sha256'}:
                raise ValueError('exact path/hash pin required')
            raw=resolve_path(root,pin['path']).read_bytes()
            if sha256(raw)!=pin['sha256']:
                raise ValueError('comparison input changed')
            return raw
        raw=content(dict(path=scope['registration_path'],sha256=scope['registration_sha256']))
        packet=json.loads(raw)
        if packet['registration_id']!=scope['registration_id']:
            raise ValueError('comparison registration differs')
        pins=packet['inputs']
        if not {'comparison_policy','sessions','strategy_cycles'}.issubset(pins):
            raise ValueError('registered comparison policy, calendar and strategy cycles required')
        policy=json.loads(content(pins['comparison_policy']))
        sessions=json.loads(content(pins['sessions']))
        # Validate the calendar and complete controls without decoding prices.
        validate_policy(policy,sessions)
        if (policy['study_id']!=packet['study_id']
                or policy['strategy_cycles']!=pins['strategy_cycles']):
            raise ValueError('comparison belongs to a different study or source schedule')
        content(pins['strategy_cycles'])
        for path in REQUIRED_CODE:
            pin=packet['code_files'][path]
            if pin['path']!=path:
                raise ValueError('comparison implementation alias rejected')
            content(pin)
        return dict(status='passed_specification_only',blockers=[],
            comparison_policy=pins['comparison_policy'],sessions=pins['sessions'],
            strategy_cycles=pins['strategy_cycles'],study_id=policy['study_id'],
            net_positive_EV_verified=False,source_quality_verified=False)
    except (OSError,ValueError,KeyError,TypeError,IndexError):
        return dict(status='blocked',blockers=['account_comparison_specification_missing_or_invalid'])
