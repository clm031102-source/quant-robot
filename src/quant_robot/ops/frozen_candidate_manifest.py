"""Prepare original-bound paper manifests for independent review, never qualify them.

This module does not run an account, activate a journal, fetch data or issue a
qualification receipt. Final activation retains its independent checks. Only
the supported single-ETF predicate adapter can be prepared here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops.frozen_input_clocks import RECEIVED_BASIS, validate_schedule
from quant_robot.paper.annual_allocation import AllocationConfig
from quant_robot.paper.daily_recovery import RECOVERY_40


REQUEST_TYPE = 'frozen_candidate_preparation_request_v1'
RESULT_TYPE = 'frozen_candidate_preparation_result_v1'
REQUEST_KEYS = {'artifact_type', 'candidate_id', 'asset_id', 'first_session',
                'strategy', 'account_config', 'source_id', 'source_profile_id',
                'maximum_receive_delay_seconds', 'calendar', 'warmup_proof'}
MAX_REQUEST_BYTES = 131072
PREPARER_CLI = Path(__file__).resolve().parents[3]/'scripts/prepare_frozen_candidate_manifest.py'


def preparer_binding():
    """Freeze the code producing the review packet, separately from its runtime."""
    return {name: dict(path=str(path.resolve()), sha256=sha256(path.read_bytes()).hexdigest())
            for name, path in (('module', Path(__file__)), ('cli', PREPARER_CLI))}


def read_request(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('Preparation request exceeds byte budget')
    return json.loads(raw)


def _config(value):
    # All settings are explicit. In particular, no missing fee uses a default.
    if not isinstance(value, dict) or set(value) != set(asdict(AllocationConfig())):
        raise ValueError('Every account and fee setting must be explicit')
    config = AllocationConfig(**value)
    numbers = {}
    for key, item in value.items():
        if key in ('execution_price_field', 'max_holding_sessions'):
            continue
        try:
            number = Decimal(str(item))
        except InvalidOperation as exc:
            raise ValueError('Finite numeric account settings required') from exc
        if isinstance(item, bool) or not number.is_finite() or number < 0:
            raise ValueError('Finite nonnegative account settings required')
        numbers[key] = number
    if (numbers['initial_cash'] != 10000 or numbers['max_position_cny'] != 10000
            or numbers['max_position_fraction'] != 1 or numbers['max_drawdown'] != Decimal('.4')
            or value['execution_price_field'] != 'open'
            or type(value['max_holding_sessions']) is not int or value['max_holding_sessions'] < 1
            or numbers['max_daily_loss_cny'] <= 0
            or not 0 < numbers['participation'] <= 1 or numbers['slippage_bps'] >= 10000):
        raise ValueError('Supported full-NAV 40-percent recovery account settings required')
    # Match the runtime's concrete dataclass comparison, not only Decimal values.
    if (config.initial_cash != 10000 or config.max_position_cny != 10000
            or config.max_position_fraction != 1 or config.max_drawdown != .4):
        raise ValueError('Runtime-compatible numeric account settings required')
    return asdict(config)


def _skeleton(request):
    if (not isinstance(request, dict) or set(request) != REQUEST_KEYS
            or request['artifact_type'] != REQUEST_TYPE):
        raise ValueError('Exact preparation request schema required')
    for key in ('candidate_id', 'asset_id', 'source_id', 'source_profile_id'):
        if not isinstance(request[key], str) or not request[key].strip():
            raise ValueError('Explicit candidate, asset and source identities required')
    strategy = request['strategy']
    if not isinstance(strategy, dict) or set(strategy) != {'adapter', 'components', 'cadence'}:
        raise ValueError('Exact supported strategy fields required')
    components = strategy['components']
    if (strategy['adapter'] != 'existing_predicate_and_v1'
            or type(strategy['cadence']) is not int or strategy['cadence'] not in (1, 5)
            or not isinstance(components, list) or not 1 <= len(components) <= 3
            or any(not isinstance(item, str) or item not in forward.CATALOG for item in components)
            or len(set(components)) != len(components)):
        raise ValueError('Supported distinct predicates and fixed cadence required')
    delay = request['maximum_receive_delay_seconds']
    if type(delay) is not int or not 0 < delay <= 86400:
        raise ValueError('Bounded receipt delay required')
    calendar_raw = forward._reference(request['calendar'])
    schedule = json.loads(calendar_raw)
    if not isinstance(schedule, list) or not 23 <= len(schedule) <= 10000:
        raise ValueError('Explicit warmup, first session and following session required')
    dates = [row['date'] for row in schedule]
    if dates != sorted(set(dates)):
        raise ValueError('Unique ordered exchange schedule required')
    validate_schedule(schedule, RECEIVED_BASIS)
    if request['first_session'] not in dates or not 21 <= dates.index(request['first_session']) < len(dates)-1:
        raise ValueError('At least21 warmup sessions and an explicit next session required')
    manifest = dict(artifact_type=forward.MANIFEST_TYPE,
        candidate_id=request['candidate_id'], asset_id=request['asset_id'],
        first_session=request['first_session'], strategy=deepcopy(strategy),
        account_config=_config(request['account_config']), daily_recovery=deepcopy(RECOVERY_40),
        calendar=deepcopy(request['calendar']), runtime_binding=forward.runtime_binding(),
        source_contract=connection.source_contract(request['source_id'],
            profile_id=request['source_profile_id'], maximum_receive_delay_seconds=delay))
    return manifest, schedule


def _write_new(path, value):
    raw = forward.canonical(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(path=str(path), sha256=sha256(raw).hexdigest())


def prepare_manifest(request, output_directory, *, now=None):
    """Write a review packet to a new directory; never overwrite an earlier packet.

    An interrupted directory has no completed preparation receipt and is retained.
    The optional clock is restricted to the code-owned synthetic source profile.
    This is preparation, not a post-flush forward durability certificate.
    """
    before = preparer_binding()
    request = deepcopy(request)
    manifest, schedule = _skeleton(request)
    profile = connection.validate_contract(manifest)
    synthetic = profile.lineage == 'synthetic_only'
    if now is not None and not synthetic:
        raise ValueError('Clock injection is synthetic-only')
    clock, timestamp = forward._clock(now)
    proof = request['warmup_proof']
    warmup = connection.build_warmup_input(manifest, proof, schedule=schedule,
        now=clock, require_recorded=not synthetic)
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    request_ref = _write_new(output/'request.json', request)
    manifest['warmup'] = _write_new(output/'warmup.json', warmup)
    manifest_ref = _write_new(output/'manifest.json', manifest)
    # Reconstruct from originals again after output writes. A mutation during
    # preparation leaves the directory incomplete, without a completion receipt.
    connection.verify_warmup_input(manifest, schedule, warmup, now=clock,
                                  require_recorded=not synthetic)
    forward._reference(manifest['calendar'])
    forward._reference(request_ref)
    forward._reference(manifest['warmup'])
    forward._reference(manifest_ref)
    if manifest['runtime_binding'] != forward.runtime_binding():
        raise ValueError('Runtime changed during preparation')
    if preparer_binding() != before:
        raise ValueError('Preparer code changed during preparation')
    result = dict(artifact_type=RESULT_TYPE, status='prepared_for_independent_review',
        prepared_at=timestamp, evidence_class=profile.lineage,
        request=request_ref, manifest=manifest_ref,
        preparer_sha256=before['module']['sha256'], preparer_binding=before,
        required_independent_gates=list(forward.GATES),
        qualification_issued=False, qualified=False, activation_performed=False,
        forward_source_admitted=False, real_forward_days=0, live_trading_allowed=False,
        limitations=['Preparation is not independent candidate qualification.',
                    'Final activation rechecks originals, runtime, calendar and clocks.',
                    'Receipt does not certify a future cutoff or operating deadline.'])
    _write_new(output/'preparation.json', result)
    return result
