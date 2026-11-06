"""Prospective paper-journal foundation for a qualified, frozen candidate.

This module issues neither research admission nor qualification.  Its external
qualification receipt is an explicit review boundary, not a display-state flag.
Only the existing predicate and annual-account engines are supported.  Synthetic
and replay journals never contribute real forward days. Real-source admission
remains closed until a raw-source/receipt adapter is independently reviewed.
No broker is involved.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
from uuid import uuid4

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.paper.daily_recovery import RECOVERY_40
from quant_robot.research.full_position_factors import CATALOG, combined_state, feature_frame
from quant_robot.ops.frozen_cash_actions import cash_action_snapshot
from quant_robot.ops.frozen_input_clocks import BASES, session_clocks, validate_schedule, validate_input_clocks


MANIFEST_TYPE = 'frozen_candidate_forward_manifest_v1'
QUALIFICATION_TYPE = 'independent_candidate_qualification_v1'
EVENT_TYPE = 'frozen_candidate_forward_event_v1'
GATES = ('research_admission_verified', 'source_quality_verified',
         'point_in_time_verified', 'economic_validation_passed',
         'nine_cost_scenarios_passed', 'risk_policy_verified')
CODE_FILES = (
    'paper/annual_allocation.py', 'paper/daily_recovery.py',
    'paper/position_buffer.py', 'research/full_position_factors.py',
    'research/indicator_combinations.py', 'ops/frozen_candidate_forward.py',
    'ops/frozen_cash_actions.py',
    'ops/frozen_input_clocks.py',
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_reference(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256(path.read_bytes()).hexdigest()}


def runtime_binding():
    package = Path(__file__).resolve().parents[1]
    return {'code': {name: sha256((package / name).read_bytes()).hexdigest()
                     for name in CODE_FILES},
            'python': platform.python_version(),
            'packages': {name: version(name) for name in ('numpy', 'pandas')}}


def _reference(ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('Exact path and SHA256 reference required')
    data = Path(ref['path']).read_bytes()
    if sha256(data).hexdigest() != ref['sha256']:
        raise ValueError('Frozen file SHA256 mismatch')
    return data


def _instant(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Explicit UTC timestamp ending in Z required')
    try:
        result = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise ValueError('Invalid UTC timestamp') from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ValueError('UTC required')
    return result


def _clock(now=None):
    # Injection exists only for synthetic tests; CLI has no clock override.
    result = datetime.now(timezone.utc) if now is None else _instant(now)
    return result, result.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _require_verified_forward_source():
    # No raw-source parser plus independently bound acquisition receipt has yet
    # been reviewed. Self-reported source names/timestamps are not certification.
    # A real adapter must be added and reviewed before this boundary can open.
    raise ValueError('verified_raw_source_adapter_missing: declared packet metadata cannot certify real forward evidence')


def _validate_bar(bar, *, asset, session):
    if not isinstance(bar, dict) or bar.get('date') != session or bar.get('asset_id') != asset:
        raise ValueError('Wrong bar session or asset')
    numbers = {}
    for field in ('open', 'high', 'low', 'close', 'volume', 'amount'):
        try:
            value = bar[field]
            number = Decimal(str(value))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ValueError(f'Complete finite {field} required') from exc
        if isinstance(value, bool) or not number.is_finite() or number < 0:
            raise ValueError(f'Finite nonnegative {field} required')
        if field in ('open', 'high', 'low', 'close') and number == 0:
            raise ValueError('Positive OHLC required')
        numbers[field] = number
    if not (numbers['low'] <= min(numbers['open'], numbers['close'])
            <= max(numbers['open'], numbers['close']) <= numbers['high']):
        raise ValueError('Internally consistent OHLC required')
    if any(type(bar.get(flag)) is not bool for flag in ('suspended', 'limit_up', 'limit_down')):
        raise ValueError('Known execution constraint flags required')


def _contracts(manifest_ref, qualification_ref):
    manifest_raw = _reference(manifest_ref)
    manifest = json.loads(manifest_raw)
    qualification = json.loads(_reference(qualification_ref))
    if manifest.get('artifact_type') != MANIFEST_TYPE:
        raise ValueError('Frozen candidate manifest required')
    if (qualification.get('artifact_type') != QUALIFICATION_TYPE
            or qualification.get('manifest_sha256') != manifest_ref['sha256']
            or qualification.get('verdict') != 'qualified'
            or qualification.get('review_role') != 'independent_qualification_review'
            or any(qualification.get('gates', {}).get(gate) is not True for gate in GATES)):
        raise ValueError('Independent qualified evidence bound to this exact manifest required')
    evidence = qualification.get('supporting_evidence', [])
    if not evidence or any(ref['sha256'] in {manifest_ref['sha256'], qualification_ref['sha256']}
                           for ref in evidence):
        raise ValueError('Separate supporting qualification evidence required')
    for ref in evidence:
        _reference(ref)
    if manifest.get('runtime_binding') != runtime_binding():
        raise ValueError('Frozen code or environment changed; independent review required')
    strategy = manifest.get('strategy', {})
    components = strategy.get('components', [])
    if (strategy.get('adapter') != 'existing_predicate_and_v1'
            or strategy.get('cadence') not in (1, 5)
            or not 1 <= len(components) <= 3 or len(set(components)) != len(components)
            or any(c not in CATALOG for c in components)):
        raise ValueError('Reviewed existing predicate adapter and frozen cadence required')
    config = AllocationConfig(**manifest['account_config'])
    if (config.initial_cash != 10000 or config.max_position_cny != 10000
            or config.max_position_fraction != 1 or config.max_drawdown != .40
            or config.execution_price_field != 'open'
            or manifest.get('daily_recovery') != RECOVERY_40):
        raise ValueError('Exact full NAV / 40 percent / 2 percent / five flat sessions policy required')
    if not isinstance(manifest.get('candidate_id'), str) or not manifest['candidate_id']:
        raise ValueError('Frozen candidate identity required')
    if not isinstance(manifest.get('asset_id'), str) or not manifest['asset_id']:
        raise ValueError('One explicit asset required')
    source = manifest.get('source_contract', {})
    delay = source.get('maximum_receive_delay_seconds')
    if (not source.get('source_id') or type(delay) is not int or not 0 < delay <= 86400
            or source.get('timestamp_basis') not in BASES):
        raise ValueError('Frozen source identity and bounded independent source clocks required')
    schedule = json.loads(_reference(manifest['calendar']))
    if not isinstance(schedule, list) or len(schedule) < 21:
        raise ValueError('Explicit frozen exchange schedule required')
    dates = [r['date'] for r in schedule]
    if dates != sorted(set(dates)):
        raise ValueError('Unique ordered exchange sessions required')
    validate_schedule(schedule, source['timestamp_basis'])
    start = dates.index(manifest['first_session'])
    if start < 21:
        raise ValueError('At least twenty-one complete warmup sessions required')
    return manifest, qualification, schedule, config


def _journal(directory):
    directory = Path(directory)
    events, previous = [], None
    for index, path in enumerate(sorted(directory.glob('[0-9]' * 8 + '.json'))):
        if path.name != f'{index:08d}.json':
            raise ValueError('Missing or reordered journal event')
        event = _read(path)
        if not isinstance(event, dict):
            raise ValueError('Invalid journal event object')
        supplied = event.pop('sha256', None)
        if (supplied != digest(event) or event.get('previous_sha256') != previous
                or event.get('sequence') != index or event.get('artifact_type') != EVENT_TYPE):
            raise ValueError('Immutable journal hash chain mismatch')
        event['sha256'] = supplied
        if events and _instant(event['received_at']) < _instant(events[-1]['received_at']):
            raise ValueError('Journal host clock regressed')
        events.append(event)
        previous = supplied
    return events


def _pending_files(directory):
    return sorted(path.name for path in Path(directory).glob('.pending-*.json'))


def _sync_directory(directory):
    # POSIX can also persist directory entries. Python's Windows CRT has no
    # equivalent directory fsync: file fsync + atomic publication does not prove
    # physical power-loss durability on Windows. Never fall back to overwriting.
    if os.name == 'nt':
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _confirm_durable_event(directory, event):
    """An idempotent success still requires a fresh persistence confirmation."""
    path = Path(directory) / f'{event["sequence"]:08d}.json'
    # A writable descriptor is needed by Windows FlushFileBuffers via fsync.
    # No bytes are changed; the complete event must still equal the validated one.
    with path.open('r+b') as stream:
        if json.loads(stream.read()) != event:
            raise ValueError('Journal event changed before persistence confirmation')
        os.fsync(stream.fileno())
    _sync_directory(Path(directory))
    return event


@contextmanager
def _locked(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / '.writer.lock'
    try:
        handle = lock.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise ValueError('Journal writer active or interrupted; inspect lock before recovery') from exc
    try:
        handle.write(json.dumps(dict(pid=os.getpid(), instance_id=uuid4().hex,
            acquired_at=datetime.now(timezone.utc).isoformat(),
            automatic_lock_removal_allowed=False)) + '\n')
        handle.close()
        if _pending_files(directory):
            raise ValueError('Incomplete journal write; preserve pending files and inspect before recovery')
        yield
    finally:
        handle.close()
        lock.unlink(missing_ok=True)


def _append(directory, events, kind, payload, received_at):
    if events and _instant(received_at) < _instant(events[-1]['received_at']):
        raise ValueError('Host clock regressed')
    event = dict(artifact_type=EVENT_TYPE, sequence=len(events), kind=kind,
                 previous_sha256=events[-1]['sha256'] if events else None,
                 received_at=received_at, payload=payload)
    event['sha256'] = digest(event)
    directory = Path(directory)
    target = directory / f'{len(events):08d}.json'
    pending = directory / f'.pending-{len(events):08d}-{uuid4().hex}.json'
    # Failed/abandoned staging files remain available for forensic recovery.
    # Only a complete, fsynced file can acquire a numbered journal name.
    with pending.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    # Same-directory hard-link creation publishes atomically and fails if the
    # destination exists on both Windows and POSIX; rename/replace may overwrite.
    # Filesystems without hard-link support fail closed, preserving the staging file.
    os.link(pending, target)
    _sync_directory(directory)
    pending.unlink()
    _sync_directory(directory)
    return event


def _active(events, *, now=None):
    if not events or events[0]['kind'] != 'activation':
        raise ValueError('No qualified frozen candidate activated')
    activation = events[0]['payload']
    if now is not None and activation['mode'] == 'forward':
        raise ValueError('Real forward mode does not accept a caller supplied clock')
    if activation['mode'] == 'forward':
        _require_verified_forward_source()
    manifest, qualification, schedule, config = _contracts(
        activation['manifest'], activation['qualification'])
    if qualification['evidence_class'] != activation['evidence_class']:
        raise ValueError('Qualification class changed')
    return activation, manifest, qualification, schedule, config


def activate(directory, manifest_path, qualification_path, *, mode='forward', now=None):
    if mode not in ('forward', 'synthetic', 'replay'):
        raise ValueError('Explicit forward, synthetic or replay mode required')
    if mode == 'forward' and now is not None:
        raise ValueError('Real forward mode does not accept a caller supplied clock')
    manifest_ref, qualification_ref = file_reference(manifest_path), file_reference(qualification_path)
    manifest, qualification, schedule, config = _contracts(manifest_ref, qualification_ref)
    instant, stamp = _clock(now)
    evidence_class = qualification.get('evidence_class')
    if evidence_class not in ('reviewed_research', 'synthetic_test_only'):
        raise ValueError('Explicit qualification evidence class required')
    if mode == 'forward' and evidence_class != 'reviewed_research':
        raise ValueError('Synthetic qualification cannot activate real forward observation')
    if mode == 'forward':
        _require_verified_forward_source()
    if _instant(qualification['issued_at']) > instant:
        raise ValueError('Qualification was issued in the future')
    first = next(row for row in schedule if row['date'] == manifest['first_session'])
    basis = manifest['source_contract']['timestamp_basis']
    if mode != 'replay' and instant >= session_clocks(first, basis)['cutoff']:
        raise ValueError('Activation must precede the first execution session')
    warmup = json.loads(_reference(manifest['warmup']))
    start = [row['date'] for row in schedule].index(first['date'])
    if [row['date'] for row in warmup['bars']] != [row['date'] for row in schedule[:start]]:
        raise ValueError('Exact consecutive warmup prefix required')
    for row in warmup['bars']:
        _validate_bar(row, asset=manifest['asset_id'], session=row['date'])
    if session_clocks(schedule[start-1], basis)['observable'] > instant:
        raise ValueError('Warmup session has not closed')
    validate_input_clocks(warmup, schedule[start-1], basis, now=instant)
    if warmup.get('corporate_actions_complete') is not True:
        raise ValueError('Warmup requires a complete cash action response')
    actions = cash_action_snapshot(warmup.get('actions'), asset=manifest['asset_id'],
        sessions=[row['date'] for row in schedule], as_of_session=schedule[start-1]['date'], warmup=True)
    # The same engine validates warmup without fabricated orders or terminal exits.
    run_allocation_account(warmup['bars'], sessions=[r['date'] for r in schedule[:start]],
        assets=[manifest['asset_id']], cycles=[], actions=actions, config=config,
        daily_recovery=RECOVERY_40, allow_open_cycle=True)
    # Validation must finish before activation; a slow validation may cross open.
    instant, stamp = _clock(now)
    if mode != 'replay' and instant >= session_clocks(first, basis)['cutoff']:
        raise ValueError('Activation validation crossed the first execution open')
    payload = dict(manifest=manifest_ref, qualification=qualification_ref, mode=mode,
                   evidence_class=evidence_class, qualification_source='external_independent_review',
                   first_session=first['date'])
    with _locked(directory):
        events = _journal(directory)
        if events:
            if events[0]['kind'] == 'activation' and events[0]['payload'] == payload:
                return _confirm_durable_event(directory, events[0])
            raise ValueError('Journal is already bound to another activation')
        return _append(directory, events, 'activation', payload, stamp)


def _prefix(events, manifest, schedule):
    warmup = json.loads(_reference(manifest['warmup']))
    bars = list(warmup['bars'])
    observations = [e for e in events if e['kind'] == 'observation']
    start = [r['date'] for r in schedule].index(manifest['first_session'])
    actions = cash_action_snapshot(warmup['actions'], asset=manifest['asset_id'],
        sessions=[row['date'] for row in schedule], as_of_session=schedule[start-1]['date'], warmup=True)
    for offset, event in enumerate(observations):
        packet = event['payload']['packet']
        if packet['session_date'] != schedule[start+offset]['date']:
            raise ValueError('Skipped or reordered observed session')
        bars.append(packet['bar'])
        actions = cash_action_snapshot(packet['corporate_actions'], asset=manifest['asset_id'],
            sessions=[row['date'] for row in schedule], as_of_session=packet['session_date'], previous=actions)
    return bars, observations, start, actions


def decide(directory, *, now=None):
    """Register the next session's frozen-rule decision before its open."""
    with _locked(directory):
        events = _journal(directory)
        activation, manifest, _, schedule, _ = _active(events, now=now)
        bars, observations, start, actions = _prefix(events, manifest, schedule)
        index = start + len(observations)
        if index >= len(schedule):
            raise ValueError('Frozen calendar exhausted; extension requires review')
        session = schedule[index]
        decisions = [e for e in events if e['kind'] == 'decision']
        existing = [e for e in decisions if e['payload']['session_date'] == session['date']]
        if existing:
            return _confirm_durable_event(directory, existing[0])
        instant, stamp = _clock(now)
        basis = manifest['source_contract']['timestamp_basis']
        input_available_at = (observations[-1]['payload']['packet']['available_at']
            if observations else json.loads(_reference(manifest['warmup']))['available_at'])
        if instant < max(_instant(events[-1]['received_at']), _instant(input_available_at)):
            raise ValueError('Signal clock regressed: precedes known input or journal receipt')
        if activation['mode'] != 'replay' and instant >= session_clocks(session, basis)['cutoff']:
            raise ValueError('Missed pre-open decision; historical entry cannot count as forward')
        if instant < session_clocks(schedule[index-1], basis)['observable']:
            raise ValueError('Prior input session has not closed')
        strategy = manifest['strategy']
        if len(observations) % strategy['cadence'] == 0:
            frame = feature_frame(bars, actions)
            value = combined_state(frame, strategy['components'])[-1]
            known, desired = bool(math.isfinite(value)), bool(value == 1)
        else:
            known, desired = decisions[-1]['payload']['known'], decisions[-1]['payload']['desired']
        generated_stamp = stamp
        instant, stamp = _clock(now)
        if instant < _instant(generated_stamp):
            raise ValueError('Signal calculation clock regressed')
        if activation['mode'] != 'replay' and instant >= session_clocks(session, basis)['cutoff']:
            raise ValueError('Signal calculation crossed execution open')
        payload = dict(session_date=session['date'], input_last_session=bars[-1]['date'],
                       input_sha256=digest(dict(bars=bars, actions=actions)), strategy_sha256=digest(strategy),
                       cash_action_input_sha256=digest(actions),
                       signal_input_available_at=input_available_at,
                       signal_generated_at=generated_stamp, signal_available_at=stamp,
                       known=known, desired=desired)
        return _append(directory, events, 'decision', payload, stamp)


def _cycles(decisions, through):
    cycles, active = [], None
    for event in decisions:
        value = event['payload']
        if value['session_date'] > through:
            continue
        if active is None and value['desired']:
            active = dict(cycle_id=f'forward_episode_{len(cycles)+1:06d}',
                          entry_date=value['session_date'], exit_date=None)
            cycles.append(active)
        elif active is not None and not value['desired']:
            active['exit_date'] = value['session_date']
            active = None
    return cycles


def observe(directory, packet, *, now=None):
    """Receive one final daily bar; replay the immutable causal prefix, never a future bar."""
    with _locked(directory):
        events = _journal(directory)
        activation, manifest, _, schedule, config = _active(events, now=now)
        prior = [e for e in events if e['kind'] == 'observation'
                 and e['payload']['packet']['session_date'] == packet.get('session_date')]
        if prior:
            if prior[0]['payload']['packet'] == packet:
                return _confirm_durable_event(directory, prior[0])
            raise ValueError('Conflicting replacement of immutable observation')
        bars, observations, start, actions = _prefix(events, manifest, schedule)
        index = start + len(observations)
        if index >= len(schedule):
            raise ValueError('Frozen calendar exhausted')
        session = schedule[index]
        if packet.get('session_date') != session['date']:
            raise ValueError('Exactly the next frozen exchange session is required')
        decision = next((e for e in events if e['kind'] == 'decision'
                         and e['payload']['session_date'] == session['date']), None)
        if decision is None:
            raise ValueError('Prospectively registered decision required')
        instant, stamp = _clock(now)
        clocks = validate_input_clocks(packet, session, manifest['source_contract']['timestamp_basis'], now=instant)
        if activation['mode'] != 'replay':
            if _instant(decision['received_at']) >= clocks['cutoff']:
                raise ValueError('Decision was not registered before execution open')
            if (instant-clocks['observable']).total_seconds() > manifest['source_contract']['maximum_receive_delay_seconds']:
                raise ValueError('Late historical bar cannot be counted as live forward')
        if packet.get('source_id') != manifest['source_contract']['source_id']:
            raise ValueError('Wrong frozen data source')
        if packet.get('corporate_actions_complete') is not True:
            raise ValueError('Explicit complete cash action response required')
        updated_actions = cash_action_snapshot(packet.get('corporate_actions'), asset=manifest['asset_id'],
            sessions=[row['date'] for row in schedule], as_of_session=session['date'], previous=actions)
        bar = packet['bar']
        _validate_bar(bar, asset=manifest['asset_id'], session=session['date'])
        if decision['payload']['input_sha256'] != digest(dict(bars=bars, actions=actions)):
            raise ValueError('Decision inputs no longer match the immutable prefix')
        bars.append(bar)
        account = run_allocation_account(bars, sessions=[r['date'] for r in schedule[:index+1]],
            assets=[manifest['asset_id']], cycles=_cycles([e for e in events if e['kind'] == 'decision'], session['date']),
            actions=updated_actions, config=config, daily_recovery=RECOVERY_40, allow_open_cycle=True)
        # Retain all unresolved holdings and the original peak: there is no terminal sale.
        prior_curve = observations[-1]['payload']['account']['equity_curve'] if observations else []
        if prior_curve and account['equity_curve'][:len(prior_curve)] != prior_curve:
            raise ValueError('New input changed historical account marks')
        payload = dict(packet=packet, decision_sha256=decision['sha256'], account=account,
                       real_forward_day=activation['mode'] == 'forward',
                       execution_claim='conditional_daily_bar_paper_model_not_actual_fills')
        return _append(directory, events, 'observation', payload, stamp)


def status(directory):
    """Read-only status; absent qualification cannot be inferred from legacy packs."""
    events = _journal(directory)
    if not events:
        result = dict(status='blocked', reason='no_qualified_frozen_candidate',
                    qualified_candidate=False, real_forward_days=0, paper_fills=0,
                    real_forward_available=False, source_adapter_status='not_verified',
                    live_trading_allowed=False)
    else:
        activation, manifest, _, _, _ = _active(events)
        observations = [e for e in events if e['kind'] == 'observation']
        latest = observations[-1]['payload']['account'] if observations else None
        result = dict(status='awaiting_prospective_session' if not observations else 'paper_journal_active',
                candidate_id=manifest['candidate_id'], mode=activation['mode'],
                qualified_candidate=activation['evidence_class'] == 'reviewed_research',
                real_forward_days=sum(e['payload']['real_forward_day'] is True for e in observations),
                paper_fills=len(latest['fills']) if latest else 0,
                last_session=observations[-1]['payload']['packet']['session_date'] if observations else None,
                latest_account_sha256=digest(latest) if latest else None,
                activation_sha256=events[0]['sha256'], last_event_sha256=events[-1]['sha256'],
                real_forward_available=False, source_adapter_status='not_verified',
                live_trading_allowed=False)
    # This reports a lock, not that its process is dead. Never probe or kill its PID.
    result['writer_lock_present'] = (Path(directory) / '.writer.lock').exists()
    result['pending_event_files'] = _pending_files(directory)
    result['recovery_required'] = bool(result['writer_lock_present'] or result['pending_event_files'])
    if result['recovery_required']:
        result.update(status='blocked', reason='journal_writer_or_recovery_pending',
            recovery_hint='Verify writers stopped; preserve original files and hashes; validate '
                          'the committed prefix and restore a verified copy. Do not remove locks '
                          'or pending files automatically, or backfill missed forward decisions.')
    return result
