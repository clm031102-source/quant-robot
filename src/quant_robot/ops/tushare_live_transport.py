"""One frozen fund_daily source observation, independent of strategy qualification.

This new scope does not relax legacy source ceilings. 2026 prices remain sealed.
No request is possible without a reviewed, hashed single-symbol/single-day scope,
a fresh project startup gate, and a durably published one-attempt claim.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
import multiprocessing
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from uuid import uuid4

from quant_robot.ops import tushare_daily_receipt as parser


SCOPE_TYPE = 'cn_etf_scoped_fund_daily_source_v1'
RECEIPT_TYPE = 'tushare_scoped_fund_daily_receipt_v1'
ARCHIVE = Path('data/reports/tushare_scoped_sources_v1')
EVIDENCE_ROLES = {'scope_decision', 'source_definition', 'holdout_policy', 'etf_identity', 'calendar'}
MAX_DOCUMENT_BYTES = 1_000_000
HOLDOUT = dict(sealed_price_years=[2026], allow_2026_prices=False,
               use='source_observation_only_no_strategy_selection_or_validation')
CODE_FILES = ('src/quant_robot/ops/tushare_live_transport.py',
              'src/quant_robot/ops/tushare_daily_receipt.py',
              'scripts/capture_tushare_scoped_source.py',
              'src/quant_robot/config/secrets.py',
              'src/quant_robot/research/pm_startup_gate.py',
              'scripts/run_quant_pm_startup_gate.py')
SCOPE_KEYS = {'artifact_type', 'scope_id', 'purpose', 'market', 'request', 'session',
              'valid_from', 'valid_until', 'request_budget', 'retry_budget',
              'transport_limits', 'holdout', 'context', 'review_evidence', 'implementation_binding'}


class ScopeError(ValueError):
    pass


class ArchiveWriteError(OSError):
    pass


def _canonical(value):
    return parser._canonical(value)


def _sha(raw):
    return sha256(raw).hexdigest()


def _digest(value):
    return _sha(_canonical(value))


def _now():
    return datetime.now(timezone.utc)


def implementation_binding(*,_reader=None):
    if _reader is not None:
        from quant_robot.ops import frozen_candidate_forward as forward
        from quant_robot.ops import paper_evidence_session as sessions
        if type(_reader) is not forward._SyntheticG1Action:
            from quant_robot.ops.paper_recorded_capture_observe import _RecordedG1Action
            if type(_reader) is not _RecordedG1Action:
                raise ScopeError('fixed_synthetic_root_reader_required')
            _reader.require_owner()
            code=_reader.stage.bind_implementation(sessions.RECORDED_CATALOG)['code']
        else:
            code=_reader.stage.bind_implementation(sessions.G1_CATALOG)['code']
        return dict(code={name:code[name] for name in CODE_FILES},python=platform.python_version(),
                    requests=None,synthetic_fixed_transport=True)
    root = Path(__file__).resolve().parents[3]
    try:
        requests_version = version('requests')
    except PackageNotFoundError:
        requests_version = None
    return dict(code={name: _sha((root/name).read_bytes()) for name in CODE_FILES},
                python=platform.python_version(), requests=requests_version)


def _read(path, limit=MAX_DOCUMENT_BYTES):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit+1)
    if len(raw) > limit:
        raise ScopeError('document_byte_budget_exceeded')
    return raw


def _decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=parser._object,
                          parse_constant=parser._reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ScopeError('invalid_JSON_document') from exc


def _reference_bytes(root, ref):
    if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
            or not isinstance(ref['path'], str) or Path(ref['path']).is_absolute()
            or not isinstance(ref['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', ref['sha256'])):
        raise ScopeError('invalid_frozen_evidence_reference')
    path = (root/ref['path']).resolve()
    if not path.is_relative_to(root.resolve()) or path.suffix.lower() not in ('.json', '.md'):
        raise ScopeError('evidence_must_be_reviewed_metadata_inside_repository')
    raw = _read(path)
    if _sha(raw) != ref['sha256']:
        raise ScopeError('frozen_evidence_hash_changed')
    return raw


def _validate(scope, *, as_of, evidence_loader, require_current_binding):
    if not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise ScopeError('exact_source_scope_schema_required')
    if (scope['artifact_type'] != SCOPE_TYPE or scope['purpose'] != 'source_observation_only'
            or scope['market'] != 'CN_ETF'):
        raise ScopeError('source_observation_scope_required')
    if not isinstance(scope['scope_id'], str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,79}', scope['scope_id']):
        raise ScopeError('invalid_scope_id')
    if _canonical(scope['holdout']) != _canonical(HOLDOUT):
        raise ScopeError('2026_price_holdout_must_remain_explicitly_closed')
    request = scope['request']
    if not isinstance(request, dict) or set(request) != {'ts_code', 'trade_date'}:
        raise ScopeError('one_symbol_and_one_trade_date_required')
    identity = parser.request_identity(**request)
    if request['trade_date'].startswith('2026'):
        raise ScopeError('2026_price_holdout_closed')
    if type(scope['request_budget']) is not int or scope['request_budget'] != 1 or type(scope['retry_budget']) is not int or scope['retry_budget'] != 0:
        raise ScopeError('exactly_one_request_and_zero_retries_required')
    first, last = parser._utc(scope['valid_from']), parser._utc(scope['valid_until'])
    if not first < last <= first+timedelta(hours=72) or not first <= as_of < last:
        raise ScopeError('scope_outside_frozen_execution_window')
    session = scope['session']
    if (not isinstance(session, dict) or set(session) != {'date','open_at','close_at','daily_observation_not_before','timezone','exchange'}
            or session['timezone'] != 'Asia/Shanghai'
            or session['date'] != datetime.strptime(request['trade_date'],'%Y%m%d').date().isoformat()
            or session['exchange'] != ('XSHG' if request['ts_code'].endswith('.SH') else 'XSHE')):
        raise ScopeError('scope_session_identity_mismatch')
    opening, closing = parser._utc(session['open_at']), parser._utc(session['close_at'])
    observation_boundary=parser._utc(session['daily_observation_not_before'])
    china = timezone(timedelta(hours=8))
    if (not opening < closing <= observation_boundary <= as_of
            or opening.astimezone(china).date().isoformat() != session['date']
            or closing.astimezone(china).date().isoformat() != session['date']
            or observation_boundary.astimezone(china).date().isoformat() != session['date']):
        raise ScopeError('source_observation_requires_closed_frozen_session')
    limits = scope['transport_limits']
    if not isinstance(limits, dict) or set(limits) != {'max_response_bytes','connect_seconds','read_seconds','total_seconds'}:
        raise ScopeError('exact_transport_budgets_required')
    if (any(type(value) is not int for value in limits.values())
            or not 1 <= limits['max_response_bytes'] <= parser.MAX_BYTES
            or not 1 <= limits['connect_seconds'] <= 10
            or not 1 <= limits['read_seconds'] <= 10
            or not max(limits['connect_seconds'], limits['read_seconds']) <= limits['total_seconds'] <= 30):
        raise ScopeError('transport_budget_exceeded')
    context = scope['context']
    if (not isinstance(context, dict) or set(context) != {'machine','task','branch'}
            or context['machine'] not in ('office_desktop','highspec_desktop')
            or context['task'] not in ('factor_review','data_pipeline')
            or not isinstance(context['branch'], str) or not context['branch'].startswith('codex/')):
        raise ScopeError('explicit_desktop_task_branch_required')
    evidence = scope['review_evidence']
    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_ROLES:
        raise ScopeError('complete_source_scope_review_evidence_required')
    if require_current_binding and scope['implementation_binding'] != implementation_binding():
        raise ScopeError('implementation_or_environment_changed')
    binding = scope['implementation_binding']
    if (not isinstance(binding, dict) or set(binding) != {'code','python','requests'}
            or not isinstance(binding['code'],dict)
            or set(binding['code']) != set(CODE_FILES)
            or any(not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value) for value in binding['code'].values())):
        raise ScopeError('complete_implementation_binding_required')
    snapshots = {role: evidence_loader(ref) for role, ref in evidence.items()}
    return dict(scope_sha256=_digest(scope), request=identity,
                request_identity=_digest(identity), evidence=snapshots)


def _load_scope(path, root, as_of):
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise ScopeError('scope_must_be_inside_repository')
    scope = _decode(_read(path))
    validated = _validate(scope, as_of=as_of,
        evidence_loader=lambda ref:_reference_bytes(root,ref), require_current_binding=True)
    return scope, validated


def _sync_directory(path):
    if os.name == 'nt':
        return  # File flush + atomic publication does not certify Windows power-loss durability.
    descriptor = os.open(path, os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish(path, raw):
    pending = path.parent/f'.pending-{path.name}-{uuid4().hex}'
    try:
        with pending.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(pending,path)  # Atomic no-replace on Windows/POSIX; no unsafe fallback.
        _sync_directory(path.parent)
        pending.unlink()
        _sync_directory(path.parent)
    except OSError:
        raise ArchiveWriteError('atomic_archive_publication_failed') from None
    return dict(path=path.name,sha256=_sha(raw))


def _publish_json(path, value):
    return _publish(path,_canonical(value)+b'\n')


def _bound(folder, ref, *, expected_name=None,_reader=None):
    if (not isinstance(ref,dict) or set(ref) not in ({'path','sha256'},{'path','sha256','bytes'})
            or not isinstance(ref.get('path'),str) or Path(ref['path']).name != ref['path']
            or ref['path'].startswith('.') or expected_name is not None and ref['path'] != expected_name):
        raise ScopeError('invalid_local_receipt_reference')
    path = folder/ref['path']
    if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
        raise ScopeError('receipt_reference_escapes_archive')
    raw = (_read(path) if _reader is None else _reader.read_bytes(_meter_reference(_reader,path,ref['sha256'])))
    if len(raw)>MAX_DOCUMENT_BYTES:raise ScopeError('document_byte_budget_exceeded')
    if _sha(raw) != ref['sha256'] or 'bytes' in ref and ref['bytes'] != len(raw):
        raise ScopeError('receipt_file_hash_or_size_mismatch')
    return raw


def inspect_attempt(directory):
    folder = Path(directory)
    missing = [name for name in ('scope.json','gate.json','claim.json','response.entity.json','receipt.json')
               if not (folder/name).is_file()]
    pending = sorted(path.name for path in folder.glob('.pending-*')) if folder.exists() else []
    return dict(status='recovery_review_required',attempt_directory=str(folder.resolve()),
                missing_files=missing,pending_files=pending,automatic_retry_allowed=False,
                request_reservation_consumed=folder.exists(),
                receipt_success_not_assumed=True,
                recovery_note='Preserve files; never infer a lost receive timestamp from filesystem modification time.')


def _fresh_gate(root, scope, output):
    args=[sys.executable,str(root/'scripts/run_quant_pm_startup_gate.py'),
          '--machine',scope['context']['machine'],'--task',scope['context']['task'],
          '--branch',scope['context']['branch'],'--output-dir',str(output)]
    result=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=60,check=False)
    if result.returncode != 0:
        raise ScopeError('fresh_project_startup_gate_failed')
    return _decode(_read(output/'quant_pm_startup_gate_pack.json'))


def _existing_token():
    """Capture accepts only the named process credential; never search dotenv files."""
    value = os.environ.get('TUSHARE_TOKEN')
    if not isinstance(value, str) or not value.strip():
        raise ScopeError('existing_credential_unavailable')
    return value.strip()


def _new_session():
    import requests
    session=requests.Session()
    session.trust_env=False
    session.proxies={}
    session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
    return session


def _http_exchange(scope,token,new_session,check_budget):
    """One request; the production caller also imposes an isolated-process deadline."""
    limits=scope['transport_limits']
    with new_session() as session:
        session.trust_env=False
        session.proxies={}
        check_budget()
        with session.post(parser.SOURCE_URL,json=dict(api_name=parser.API_NAME,token=token,
                params=scope['request'],fields=','.join(parser.FIELDS)),
                timeout=(limits['connect_seconds'],limits['read_seconds']),stream=True,
                allow_redirects=False,verify=True) as response:
            check_budget()
            parser._endpoint(response.url)
            if response.status_code!=200:raise ScopeError('HTTP_status_rejected')
            headers={str(key).lower():value for key,value in response.headers.items()}
            http_date=headers.get('date')
            if http_date is not None and (not isinstance(http_date,str) or token in http_date):
                raise ScopeError('unsafe_HTTP_Date_not_retained')
            body=bytearray()
            for chunk in response.iter_content(8192):
                check_budget()
                if not isinstance(chunk,bytes):raise ScopeError('nonbyte_response_chunk')
                body.extend(chunk)
                if len(body)>limits['max_response_bytes']:raise ScopeError('response_byte_budget_exceeded')
    return dict(body=bytes(body),http_date=http_date)


def _http_worker(connection,scope,token):
    # Spawn IPC serializes arguments in memory, never in command-line text/files.
    # A separate process bounds DNS, TLS, response headers, buffered streaming,
    # and cleanup even if a library's per-read timeout is repeatedly reset.
    try:
        connection.send({'event':'request_worker_entered'})
        result=_http_exchange(scope,token,_new_session,lambda:None)
        connection.send({'result':result})
    except Exception as exc:
        allowed=set(parser.SAFE_FAILURE_CODES)|{'unsafe_HTTP_Date_not_retained','nonbyte_response_chunk','HTTP_status_rejected'}
        code=str(exc) if isinstance(exc,(ScopeError,parser.ReceiptError)) and str(exc) in allowed else 'transport_or_validation_failed_redacted'
        connection.send({'error':code})
    finally:
        token=None
        connection.close()


def _bounded_worker(worker,args,timeout_seconds):
    """Hard client-side deadline; terminate/kill and join before returning failure."""
    if not 0<timeout_seconds<=30:raise ScopeError('isolated_transport_deadline_exceeded')
    context=multiprocessing.get_context('spawn')
    incoming,outgoing=context.Pipe(duplex=False)
    process=context.Process(target=worker,args=(outgoing,*args),daemon=True)
    deadline=time.monotonic()+timeout_seconds
    events=[]
    try:
        process.start()
        outgoing.close()
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0 or not incoming.poll(remaining):
                error=ScopeError('isolated_transport_deadline_exceeded')
                error.worker_events=tuple(events)
                raise error
            try:message=incoming.recv()
            except EOFError:raise ScopeError('isolated_worker_failed') from None
            if not isinstance(message,dict):raise ScopeError('isolated_worker_protocol_error')
            if set(message)=={'event'} and message['event'] in ('request_worker_entered','slow_fixture_read_started'):
                events.append(message['event'])
                continue
            if set(message)=={'error'}:
                allowed=set(parser.SAFE_FAILURE_CODES)|{'unsafe_HTTP_Date_not_retained','nonbyte_response_chunk','HTTP_status_rejected','transport_or_validation_failed_redacted'}
                raise ScopeError(message['error'] if message['error'] in allowed else 'isolated_worker_failed')
            if set(message)=={'result'}:
                if time.monotonic()>deadline:raise ScopeError('isolated_transport_deadline_exceeded')
                return message['result']
            raise ScopeError('isolated_worker_protocol_error')
    finally:
        outgoing.close();incoming.close()
        if process.pid is not None:
            if process.is_alive():process.terminate()
            process.join(timeout=.5)
            if process.is_alive():process.kill();process.join(timeout=.5)
            if process.is_alive():raise ScopeError('worker_termination_unconfirmed')
            process.close()


def _gate_ready(gate, scope, as_of):
    if not isinstance(gate,dict) or gate.get('status')!='ready' or gate.get('primary_market')!='CN_ETF' or gate.get('blockers')!=[]:
        raise ScopeError('fresh_project_startup_gate_blocked')
    selected=gate.get('selected',{})
    if any(selected.get(key)!=value for key,value in scope['context'].items()) or selected.get('current_branch')!=scope['context']['branch']:
        raise ScopeError('startup_gate_context_mismatch')
    try:
        generated=datetime.fromisoformat(gate['generated_at'].replace('Z','+00:00'))
        generated=parser._utc(generated)
    except (KeyError,ValueError,TypeError,AttributeError):
        raise ScopeError('startup_gate_clock_missing') from None
    if not generated<=as_of<=generated+timedelta(seconds=120):
        raise ScopeError('startup_gate_not_fresh')
    reading=gate.get('reading_summary',{})
    rows=gate.get('required_reading',[])
    if (not isinstance(rows,list) or not rows or reading.get('required')!=len(rows)
            or reading.get('read')!=len(rows) or reading.get('missing')!=0
            or any(not isinstance(row,dict) or row.get('status')!='read'
                   or not isinstance(row.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',row['sha256']) for row in rows)):
        raise ScopeError('startup_protocol_reading_incomplete')
    if gate.get('safety',{}).get('final_holdout_allowed') is not False or gate.get('safety',{}).get('live_boundary_allowed') is not False:
        raise ScopeError('startup_holdout_or_live_boundary_changed')


def capture_scoped_source(scope_path, *, repo_root='.', execute=False, expected_scope_sha256=None,
                          mock_hooks=None):
    """Preview by default; mock hooks produce a permanently distinct evidence class.

    mock_hooks must provide clock, monotonic, gate, token and session callables.
    Production execution never accepts individual transport/credential overrides.
    """
    root=Path(repo_root).resolve()
    mocked=mock_hooks is not None
    if mocked and (not isinstance(mock_hooks,dict) or set(mock_hooks)!={'clock','monotonic','gate','token','session'}
                   or any(not callable(value) for value in mock_hooks.values())):
        raise ScopeError('complete_explicit_mock_hooks_required')
    clock=mock_hooks['clock'] if mocked else _now
    monotonic=mock_hooks['monotonic'] if mocked else time.monotonic
    now=parser._utc(clock())
    scope,validated=_load_scope(scope_path,root,now)
    folder=root/ARCHIVE/('mock_requests' if mocked else 'requests')/validated['request_identity']
    preview=dict(status='preview',scope_sha256=validated['scope_sha256'],request=validated['request'],
                 request_identity=validated['request_identity'],attempt_directory=str(folder),
                 request_already_reserved=folder.exists(),credentials_read=False,network_requests_started=0,
                 candidate_qualification_required=False,strategy_forward_days_added=0)
    if not execute:
        return preview
    if expected_scope_sha256!=validated['scope_sha256']:
        raise ScopeError('exact_frozen_scope_hash_required_for_execution')
    if folder.exists():
        try:
            if (folder/'receipt.json').is_file() and not list(folder.glob('.pending-*')):
                receipt=verify_scoped_source_receipt(folder/'receipt.json')
                _confirm_files(folder,receipt)
                return dict(status='already_consumed',receipt_path=str(folder/'receipt.json'),
                            receipt_sha256=receipt['sha256'],strategy_forward_days_added=0)
        except (OSError,ValueError,KeyError,TypeError):
            pass
        return inspect_attempt(folder)
    if not mocked and validated['request'] and scope['implementation_binding']['requests'] is None:
        raise ScopeError('requests_transport_dependency_missing')
    gate_output=root/ARCHIVE/'preflight'/uuid4().hex
    gate=(mock_hooks['gate'](root,scope,gate_output) if mocked else _fresh_gate(root,scope,gate_output))
    _gate_ready(gate,scope,parser._utc(clock()))
    # The fresh gate may take time or reveal a changed protocol; recheck before reserving.
    scope_again,again=_load_scope(scope_path,root,parser._utc(clock()))
    if again['scope_sha256']!=validated['scope_sha256']:
        raise ScopeError('scope_changed_during_preflight')
    folder.parent.mkdir(parents=True,exist_ok=True)
    try:
        folder.mkdir()
    except FileExistsError:
        return inspect_attempt(folder)
    receipt=None
    try:
        scope_ref=_publish_json(folder/'scope.json',scope_again)
        gate_ref=_publish_json(folder/'gate.json',gate)
        evidence_refs={role:_publish(folder/f'evidence-{role}.original',raw)
                       for role,raw in validated['evidence'].items()}
        claimed=parser._utc(clock())
        if not parser._utc(scope['valid_from'])<=claimed<parser._utc(scope['valid_until']):
            raise ScopeError('scope_expired_before_claim')
        evidence_class='mock_transport_contract_test' if mocked else 'live_source_observation'
        claim=dict(artifact_type='scoped_fund_daily_one_attempt_claim_v1',scope_sha256=validated['scope_sha256'],
                   request_identity=validated['request_identity'],request=validated['request'],
                   claimed_at=parser._stamp(claimed),request_budget_reserved=1,retry_budget=0,
                   evidence_class=evidence_class,scope_ref=scope_ref,gate_ref=gate_ref,
                   evidence_refs=evidence_refs,implementation_binding=scope['implementation_binding'])
        claim_ref=_publish_json(folder/'claim.json',claim)
        _confirm_references(folder,[scope_ref,gate_ref,claim_ref,*evidence_refs.values()])
        receipt=dict(artifact_type=RECEIPT_TYPE,status='source_rejected',evidence_class=evidence_class,
            scope_sha256=validated['scope_sha256'],scope_ref=scope_ref,claim_ref=claim_ref,gate_ref=gate_ref,
            evidence_refs=evidence_refs,request=validated['request'],implementation_binding=scope['implementation_binding'],
            request_started_at=None,received_at=None,raw_response=None,normalized_bar=None,http_clock=None,
            daily_observation_not_before=scope['session']['daily_observation_not_before'],
            availability_upper_bound=None,provider_generated_at=None,provider_available_at=None,
            first_publication_verified=False,source_quality_verified=False,
            candidate_qualification_granted=False,strategy_forward_days_added=0,
            http_attempts_started=0,network_requests_started=0,mocked_requests_started=0,
            representation='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes',
            deadline_enforcement=('mock_injected_transport_clock_checks' if mocked
                                  else 'isolated_process_monotonic_deadline_terminate_and_join'),
            power_loss_durability_certified=False)
        _capture_once(folder,scope,receipt,clock=clock,monotonic=monotonic,
            get_token=mock_hooks['token'] if mocked else _existing_token,
            new_session=mock_hooks['session'] if mocked else _new_session)
        receipt['sha256']=_digest(receipt)
        _publish_json(folder/'receipt.json',receipt)
        verified=verify_scoped_source_receipt(folder/'receipt.json')
        _confirm_files(folder,verified)
        return dict(status=verified['status'],receipt_path=str(folder/'receipt.json'),
                    receipt_sha256=verified['sha256'],evidence_class=verified['evidence_class'],
                    network_requests_started=verified['network_requests_started'],
                    strategy_forward_days_added=0,candidate_qualification_granted=False)
    except (OSError,ScopeError,ValueError):
        return inspect_attempt(folder)


def _capture_once(folder,scope,receipt,*,clock,monotonic,get_token,new_session,_reader=None):
    token=None
    stage='credential'
    try:
        now=parser._utc(clock())
        claim_raw=(_bound(folder,receipt['claim_ref'],expected_name='claim.json') if _reader is None else
                   _bound(folder,receipt['claim_ref'],expected_name='claim.json',_reader=_reader))
        claimed_at=parser._utc(_decode(claim_raw)['claimed_at'])
        if now<claimed_at:raise ScopeError('claim_clock_regressed_before_credential_read')
        if not parser._utc(scope['valid_from'])<=now<parser._utc(scope['valid_until']):
            raise ScopeError('scope_expired_before_credential_read')
        token=get_token()
        if not isinstance(token,str) or not 16<=len(token)<=256:
            raise ScopeError('existing_credential_unavailable')
        stage='request'
        started=parser._utc(clock())
        if started<claimed_at or started<now:raise ScopeError('claim_clock_regressed_before_request')
        if not parser._utc(scope['valid_from'])<=started<parser._utc(scope['valid_until']):
            raise ScopeError('scope_expired_before_request')
        receipt['request_started_at']=parser._stamp(started)
        start_tick=monotonic()
        limits=scope['transport_limits']
        def budget():
            elapsed=monotonic()-start_tick
            if elapsed<0 or elapsed>limits['total_seconds']:
                raise ScopeError('monotonic_request_deadline_exceeded')
            return elapsed
        budget()
        receipt['http_attempts_started']=1
        receipt['mocked_requests_started']=int(receipt['evidence_class']=='mock_transport_contract_test')
        receipt['network_requests_started']=int(receipt['evidence_class']=='live_source_observation')
        if receipt['evidence_class']=='mock_transport_contract_test':
            transferred=_http_exchange(scope,token,new_session,budget)
        else:
            transferred=_bounded_worker(_http_worker,(scope,token),limits['total_seconds']-budget())
        body,http_date=transferred['body'],transferred['http_date']
        elapsed=budget()
        received=parser._utc(clock())
        receipt['received_at']=parser._stamp(received)
        receipt['elapsed_monotonic_seconds']=elapsed
        if received<started or received>=parser._utc(scope['valid_until']):
            raise ScopeError('receipt_clock_or_scope_window_violation')
        if abs((received-started).total_seconds()-elapsed)>5:
            raise ScopeError('UTC_and_monotonic_duration_disagree')
        http_clock=parser._http_clock(http_date,started=started,received=received)
        if http_clock['status']=='unparseable':
            raise ScopeError('invalid_HTTP_Date_header')
        parser.decode_body(bytes(body),token=token)
        parsed=parser.parse_fund_daily_body(bytes(body),**scope['request'])
        # Wrong-date/schema/credential payloads never become retained price inputs.
        raw_ref=_publish(folder/'response.entity.json',bytes(body))
        receipt.update(raw_response={**raw_ref,'bytes':len(body)},normalized_bar=parsed['bar'],
            parsed_contract=parsed,http_clock=http_clock,availability_upper_bound=parser._availability_bound(received),
            status='source_observed_unqualified')
    except ArchiveWriteError:
        raise
    except Exception as exc:
        known=set(parser.SAFE_FAILURE_CODES)|{'scope_expired_before_credential_read',
            'existing_credential_unavailable','scope_expired_before_request','monotonic_request_deadline_exceeded',
            'HTTP_status_rejected','unsafe_HTTP_Date_not_retained','nonbyte_response_chunk',
            'receipt_clock_or_scope_window_violation','UTC_and_monotonic_duration_disagree',
            'claim_clock_regressed_before_credential_read','claim_clock_regressed_before_request',
            'isolated_transport_deadline_exceeded','isolated_worker_failed','isolated_worker_protocol_error',
            'worker_termination_unconfirmed','transport_or_validation_failed_redacted'}
        code=str(exc) if isinstance(exc,(ScopeError,parser.ReceiptError)) and str(exc) in known else (
            'credential_read_failed_redacted' if stage=='credential' else 'transport_or_validation_failed_redacted')
        receipt['failure_code']=code
        receipt['status']='source_rejected'
    finally:
        token=None


def _meter_reference(reader,path,sha):
    from quant_robot.ops import paper_evidence_session as sessions
    if type(reader) is not sessions._Child or not any(reader._session.policy is value for value in
            (sessions.G1_SYNTHETIC_POLICY,sessions.G1_RECORDED_POLICY)):
        raise ScopeError('fixed_g1_content_reader_required')
    reader._session.require_open()
    root=reader._session.root;relative=Path(path).resolve(strict=True).relative_to(root).as_posix()
    return dict(path=relative,sha256=sha)


def _confirm_references(folder,refs,*,_reader=None):
    for ref in refs:
        if _reader is not None:
            _bound(folder,ref,_reader=_reader)
            _reader.confirm_durable(_meter_reference(_reader,folder/ref['path'],ref['sha256']))
            continue
        expected=_bound(folder,ref)
        with (folder/ref['path']).open('r+b') as stream:
            if stream.read()!=expected:
                raise ScopeError('archive_changed_before_fsync_confirmation')
            os.fsync(stream.fileno())
    _sync_directory(folder)


def _confirm_files(folder,receipt,*,_reader=None):
    refs=[receipt['scope_ref'],receipt['claim_ref'],receipt['gate_ref'],*receipt['evidence_refs'].values()]
    if receipt['raw_response'] is not None:refs.append(receipt['raw_response'])
    if _reader is None:receipt_sha=_sha(_read(folder/'receipt.json'))
    else:
        _,ref=_reader.snapshot_original((folder/'receipt.json').resolve().relative_to(_reader._session.root).as_posix())
        receipt_sha=ref['sha256']
    refs.append(dict(path='receipt.json',sha256=receipt_sha))
    if _reader is None:_confirm_references(folder,refs)
    else:_confirm_references(folder,refs,_reader=_reader)


def verify_scoped_source_receipt(receipt_path, *, expected_scope_sha256=None):
    """Revalidate archived bindings and raw mapping, not current-code equivalence.

    Historical scope/claim/receipt implementation hashes must agree with each
    other. Consumers must separately bind the current verifier/parser hashes;
    this function does not assert the current code equals the capture version.
    """
    path=Path(receipt_path)
    folder=path.parent
    if list(folder.glob('.pending-*')):
        raise ScopeError('pending_archive_write_requires_recovery_review')
    receipt=_decode(_read(path))
    if not isinstance(receipt,dict):raise ScopeError('receipt_object_required')
    claimed_hash=receipt.pop('sha256',None)
    if claimed_hash!=_digest(receipt) or receipt.get('artifact_type')!=RECEIPT_TYPE:
        raise ScopeError('receipt_hash_or_type_mismatch')
    if receipt.get('evidence_class') not in ('live_source_observation','mock_transport_contract_test'):
        raise ScopeError('wrong_source_evidence_class')
    for key in ('first_publication_verified','source_quality_verified','candidate_qualification_granted'):
        if receipt.get(key) is not False:raise ScopeError('source_observation_cannot_grant_qualification')
    if receipt.get('strategy_forward_days_added')!=0 or receipt.get('provider_generated_at') is not None or receipt.get('provider_available_at') is not None:
        raise ScopeError('source_observation_cannot_create_publication_or_forward_claims')
    scope=_decode(_bound(folder,receipt['scope_ref'],expected_name='scope.json'))
    claim=_decode(_bound(folder,receipt['claim_ref'],expected_name='claim.json'))
    gate=_decode(_bound(folder,receipt['gate_ref'],expected_name='gate.json'))
    _gate_ready(gate,scope,parser._utc(claim['claimed_at']))
    evidence=receipt['evidence_refs']
    if set(evidence)!=EVIDENCE_ROLES:raise ScopeError('missing_scope_evidence_snapshots')
    snapshots={role:_bound(folder,ref,expected_name=f'evidence-{role}.original')
               for role,ref in evidence.items()}
    def load_snapshot(ref):
        role=next((key for key,value in scope['review_evidence'].items() if value==ref),None)
        if role is None:raise ScopeError('unknown_scope_evidence')
        raw=snapshots[role]
        if _sha(raw)!=ref['sha256']:raise ScopeError('scope_evidence_snapshot_hash_mismatch')
        return raw
    as_of=parser._utc(receipt['request_started_at'] or claim['claimed_at'])
    validated=_validate(scope,as_of=as_of,evidence_loader=load_snapshot,require_current_binding=False)
    if (validated['scope_sha256']!=receipt['scope_sha256']
            or expected_scope_sha256 is not None and expected_scope_sha256!=receipt['scope_sha256']
            or claim.get('scope_sha256')!=receipt['scope_sha256']
            or claim.get('request')!=validated['request'] or receipt['request']!=validated['request']
            or claim.get('request_identity')!=validated['request_identity']
            or claim.get('artifact_type')!='scoped_fund_daily_one_attempt_claim_v1'
            or claim.get('request_budget_reserved')!=1 or claim.get('retry_budget')!=0
            or claim.get('evidence_class')!=receipt['evidence_class']
            or claim.get('scope_ref')!=receipt['scope_ref'] or claim.get('gate_ref')!=receipt['gate_ref']
            or claim.get('evidence_refs')!=receipt['evidence_refs']
            or receipt['implementation_binding']!=scope['implementation_binding']
            or claim.get('implementation_binding')!=scope['implementation_binding']):
        raise ScopeError('claim_scope_or_implementation_binding_mismatch')
    claimed_at=parser._utc(claim['claimed_at'])
    if not parser._utc(scope['valid_from'])<=claimed_at<parser._utc(scope['valid_until']) or claimed_at>as_of:
        raise ScopeError('claim_must_precede_request_inside_scope')
    if any(type(receipt.get(key)) is not int or not 0<=receipt[key]<=1
           for key in ('http_attempts_started','network_requests_started','mocked_requests_started')):
        raise ScopeError('single_attempt_counter_required')
    if receipt['status']=='source_observed_unqualified':
        if receipt['raw_response'] is None or receipt['received_at'] is None or receipt['normalized_bar'] is None:
            raise ScopeError('successful_source_requires_original_bytes_and_clocks')
        raw=_bound(folder,receipt['raw_response'],expected_name='response.entity.json')
        if type(receipt['raw_response'].get('bytes')) is not int or receipt['raw_response']['bytes']!=len(raw):
            raise ScopeError('response_byte_count_required')
        parsed=parser.parse_fund_daily_body(raw,**scope['request'])
        if parsed['bar']!=receipt['normalized_bar'] or parsed!=receipt.get('parsed_contract'):
            raise ScopeError('raw_source_mapping_mismatch')
        started,received=parser._utc(receipt['request_started_at']),parser._utc(receipt['received_at'])
        if (receipt.get('daily_observation_not_before')!=scope['session']['daily_observation_not_before']
                or not parser._utc(scope['session']['daily_observation_not_before'])<=started<=received<parser._utc(scope['valid_until'])):
            raise ScopeError('source_receipt_session_clock_mismatch')
        if receipt['availability_upper_bound']!=parser._availability_bound(received):
            raise ScopeError('source_availability_bound_mismatch')
        if (not isinstance(receipt['http_clock'],dict)
                or receipt['http_clock']!=parser._http_clock(receipt['http_clock'].get('http_date'),started=started,received=received)):
            raise ScopeError('source_HTTP_clock_mismatch')
        elapsed=receipt.get('elapsed_monotonic_seconds')
        if type(elapsed) not in (int,float) or not 0<=elapsed<=scope['transport_limits']['total_seconds'] or abs((received-started).total_seconds()-elapsed)>5:
            raise ScopeError('source_elapsed_time_budget_mismatch')
        if receipt.get('http_attempts_started')!=1:raise ScopeError('one_source_attempt_required')
    elif receipt['status']=='source_rejected':
        if receipt['raw_response'] is not None or receipt['normalized_bar'] is not None or (folder/'response.entity.json').exists():
            raise ScopeError('rejected_source_cannot_bind_price_inputs')
    else:raise ScopeError('unsupported_source_receipt_status')
    expected_live=int(receipt['evidence_class']=='live_source_observation')*receipt['http_attempts_started']
    if receipt['network_requests_started']!=expected_live or receipt['mocked_requests_started']!=receipt['http_attempts_started']-expected_live:
        raise ScopeError('transport_evidence_class_mismatch')
    receipt['sha256']=claimed_hash
    return receipt
