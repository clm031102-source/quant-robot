"""Exact next-session acquisition scope for an already activated paper journal.

This is an offline admission component, not a network transport. A scope cannot
authorize historical research, a different asset/date, or a retry. The journal
must already contain a pre-open durable decision. Production callers use the
host clock; explicit clocks are restricted to synthetic/replay preparations.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import tushare_live_transport as transport
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops.frozen_input_clocks import RECEIVED_BASIS, session_clocks


SCOPE_TYPE = 'activated_paper_prospective_fund_daily_scope_v1'
PURPOSE = 'activated_candidate_prospective_observation_only'
POLICY = dict(sealed_research_partitions_opened=False,
              historical_backfill_allowed=False, candidate_qualification_granted=False,
              real_forward_days_added=0, live_trading_allowed=False)
LIMITS = dict(max_response_bytes=65536, connect_seconds=5, read_seconds=5, total_seconds=20)


def implementation_binding():
    root=Path(__file__).resolve().parents[3]
    return dict(scope_code_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                transport=transport.implementation_binding(), forward=forward.runtime_binding(),
                prospective_capture_code={name:sha256((root/name).read_bytes()).hexdigest()
                    for name in ('src/quant_robot/ops/paper_prospective_transport.py',
                                 'scripts/capture_tushare_prospective_source.py')})


def _context(context):
    if (not isinstance(context, dict) or set(context) != {'machine', 'task', 'branch'}
            or context['machine'] not in ('office_desktop', 'highspec_desktop')
            or context['task'] not in ('factor_review', 'data_pipeline')
            or not isinstance(context['branch'], str) or not context['branch'].startswith('codex/')):
        raise ValueError('Explicit desktop source-acquisition context required')


def _inside(root, path):
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError('Prospective evidence must stay inside the repository')
    return path


@dataclass(frozen=True)
class _ClaimGuard:
    folder: Path
    lock_bytes: bytes


def _writer_blocked(folder, guard=None):
    lock = folder/'.writer.lock'
    if guard is None:
        return lock.exists()
    if not isinstance(guard, _ClaimGuard) or guard.folder != folder:
        raise ValueError('Owned journal claim guard required')
    if not lock.is_file() or transport._read(lock, 16384) != guard.lock_bytes:
        raise ValueError('Journal claim writer exclusion changed')
    return False


def _journal_state(root, journal, *, now, _guard=None):
    folder = _inside(root, journal)
    if not folder.is_dir() or _writer_blocked(folder,_guard) or forward._pending_files(folder):
        raise ValueError('Stable completed journal prefix required before source acquisition')
    events = forward._journal(folder)
    activation, manifest, qualification, schedule, _ = forward._active(events, now=now)
    if activation['mode'] not in ('forward', 'synthetic'):
        raise ValueError('Replay journals cannot acquire prospective prices')
    if (not forward._has_originals(manifest)
            or manifest['source_contract']['timestamp_basis'] != RECEIVED_BASIS):
        raise ValueError('Original-bound source profile required before acquisition')
    connection.validate_contract(manifest, require_recorded=activation['mode']=='forward')
    for reference in (activation['manifest'], activation['qualification'],
                      manifest['warmup'], manifest['calendar']):
        _inside(root, reference['path'])
    _, observations, start, _ = forward._prefix(events, manifest, schedule)
    index = start + len(observations)
    if index+1 >= len(schedule):
        raise ValueError('Pending session and its next cutoff require frozen calendar coverage')
    session = schedule[index]
    decisions = [e for e in events if e['kind']=='decision'
                 and e['payload']['session_date']==session['date']]
    if len(decisions)!=1:
        raise ValueError('Exactly one pre-existing decision for the pending session required')
    decision = decisions[0]
    cutoff = session_clocks(session, RECEIVED_BASIS)['cutoff']
    confirmed = forward._decision_receipt(events, decision, cutoff=cutoff)
    if confirmed is None:
        raise ValueError('Pre-open durability receipt required before acquisition')
    if _instant(qualification['issued_at']) > _instant(events[0]['received_at']):
        raise ValueError('Candidate qualification must precede activation')
    # Detect concurrent publication during this read-only preparation. A later
    # executor must repeat this check immediately before its durable claim.
    if _writer_blocked(folder,_guard) or forward._pending_files(folder) or forward._journal(folder)!=events:
        raise ValueError('Journal changed during prospective scope preparation')
    return folder, events, activation, manifest, schedule, index, decision, confirmed


def _instant(value):
    return forward._instant(value)


def _confirm_prefix(root, scope, _guard=None):
    """Last read-only check; a transport must still protect validation+claim.

    Re-reading is not a journal lock and does not make the next filesystem or
    network action atomic. An executor must not release its writer exclusion
    between final authority validation and publishing its one-attempt claim.
    """
    folder=_inside(root,root/scope['journal'])
    if _writer_blocked(folder,_guard) or forward._pending_files(folder):
        raise ValueError('Stable completed journal prefix required before source acquisition')
    events=forward._journal(folder)
    binding=scope['journal_binding']
    if (len(events)!=binding['prefix_length'] or not events
            or events[-1]['sha256']!=binding['prefix_sha256']
            or _writer_blocked(folder,_guard) or forward._pending_files(folder)):
        raise ValueError('Journal changed after prospective scope reconstruction')


def prepare_scope(journal, *, repo_root, context, now=None, _guard=None):
    """Derive the single allowed asset/day from durable state, never from a query.

    The result may be prepared before close, but validate_execution() will not
    admit it until the final daily observation window. No credentials are read.
    """
    _context(context)
    root = Path(repo_root).resolve(strict=True)
    folder, events, activation, manifest, schedule, index, decision, confirmed = _journal_state(root,journal,now=now,_guard=_guard)
    instant, _ = forward._clock(now)
    if instant < _instant(events[-1]['received_at']):
        raise ValueError('Scope clock precedes the durable journal prefix')
    asset = manifest['asset_id']
    match = re.fullmatch(r'CN_ETF_(XSHG|XSHE)_([0-9]{6})',asset)
    if match is None:
        raise ValueError('One exact exchange ETF identity required')
    session, next_session = schedule[index:index+2]
    clocks = session_clocks(session,RECEIVED_BASIS)
    end = min(clocks['observable']+timedelta(seconds=manifest['source_contract']['maximum_receive_delay_seconds']),
              session_clocks(next_session,RECEIVED_BASIS)['cutoff'])
    if instant >= end:
        raise ValueError('Pending session acquisition window expired; no historical backfill')
    request = dict(ts_code=match[2]+('.SH' if match[1]=='XSHG' else '.SZ'),
                   trade_date=session['date'].replace('-',''))
    parser.request_identity(**request)
    result = dict(artifact_type=SCOPE_TYPE,purpose=PURPOSE,market='CN_ETF',
        evidence_mode='synthetic_only' if activation['mode']=='synthetic' else 'recorded_observation',
        journal=folder.relative_to(root).as_posix(),
        journal_binding=dict(activation_sha256=events[0]['sha256'],
            manifest=activation['manifest'],qualification=activation['qualification'],
            prefix_length=len(events),prefix_sha256=events[-1]['sha256'],
            decision_sha256=decision['sha256'],durability_sha256=confirmed['sha256']),
        candidate_id=manifest['candidate_id'],asset_id=asset,
        source_id=manifest['source_contract']['source_id'],
        source_profile=manifest['source_contract']['originals_binding'],request=request,
        session=session,next_session=next_session,
        valid_from=parser._stamp(clocks['observable']),valid_until=parser._stamp(end),
        request_budget=1,retry_budget=0,transport_limits=dict(LIMITS),
        policy=dict(POLICY),context=dict(context),implementation_binding=implementation_binding())
    _confirm_prefix(root,result,_guard)
    return result


def validate_execution(scope, *, repo_root, now=None, synthetic=False, _guard=None):
    """Rebuild authority from the actual current journal before any credential read.

    No arbitrary date selector, qualification flag, holdout switch, or provider
    name can substitute for the actual pending decision and source profile.
    """
    root = Path(repo_root).resolve(strict=True)
    if not isinstance(scope,dict) or not isinstance(scope.get('journal'),str):
        raise ValueError('Frozen prospective scope required')
    if Path(scope['journal']).is_absolute():
        raise ValueError('Repository-relative journal reference required')
    if type(synthetic) is not bool:
        raise ValueError('Explicit synthetic execution boolean required')
    expected=prepare_scope(root/scope['journal'],repo_root=root,context=scope.get('context'),now=now,_guard=_guard)
    if forward.canonical(scope)!=forward.canonical(expected):
        raise ValueError('Prospective scope differs from current frozen journal authority')
    if synthetic != (expected['evidence_mode']=='synthetic_only'):
        raise ValueError('Synthetic and production acquisitions must remain separate')
    instant,_=forward._clock(now)
    if not _instant(scope['valid_from'])<=instant<_instant(scope['valid_until']):
        raise ValueError('Prospective acquisition requires the final observable session window')
    identity=dict(candidate_manifest_sha256=scope['journal_binding']['manifest']['sha256'],
        decision_sha256=scope['journal_binding']['decision_sha256'],request=parser.request_identity(**scope['request']))
    result = dict(scope_sha256=forward.digest(scope),request_identity=forward.digest(identity),
                request=identity['request'],evidence_mode=expected['evidence_mode'],
                policy=dict(POLICY),credentials_read=False,network_requests_started=0)
    _confirm_prefix(root,scope,_guard)
    return result


@contextmanager
def protected_execution(scope, *, repo_root, now=None, synthetic=False):
    """Hold journal writer exclusion through final revalidation and durable claim.

    Yield a revalidation callable for use immediately before claim publication.
    No credentials/network belong in this section. A crash leaves the lock for
    manual recovery; a changed lock is preserved, never removed as our own.
    The private guard is a Python capability, never accepted from scope JSON.
    """
    root=Path(repo_root).resolve(strict=True)
    if not isinstance(scope,dict) or not isinstance(scope.get('journal'),str) or Path(scope['journal']).is_absolute():
        raise ValueError('Repository-relative journal reference required')
    folder=_inside(root,root/scope['journal'])
    lock=folder/'.writer.lock'
    raw=(json.dumps(dict(pid=os.getpid(),instance_id=uuid4().hex,
        purpose='prospective_source_claim',automatic_lock_removal_allowed=False))+'\n').encode()
    try:
        with lock.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except FileExistsError:
        raise ValueError('Journal writer active or interrupted before source claim') from None
    guard=_ClaimGuard(folder,raw)
    try:
        if forward._pending_files(folder):
            raise ValueError('Incomplete journal publication requires recovery')
        def refresh(*, now=None):
            return validate_execution(scope,repo_root=root,now=now,synthetic=synthetic,_guard=guard)
        refresh(now=now)
        yield refresh
        _confirm_prefix(root,scope,guard)
    finally:
        if lock.is_file() and transport._read(lock,16384)==raw:
            lock.unlink()


def read_scope(path, *, repo_root):
    """Read a bounded frozen file without accepting duplicate JSON keys."""
    root=Path(repo_root).resolve(strict=True)
    path=_inside(root,path)
    return transport._decode(transport._read(path))
