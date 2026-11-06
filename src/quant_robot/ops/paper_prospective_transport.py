"""Once-only prospective fund_daily capture for an activated original-bound journal.

No production profile is installed here. Synthetic hooks can only consume a
synthetic journal and stay synthetic in the archive. The legacy historical
scope and its sealed research partitions are unchanged. HTTP, process deadline,
credential lookup, raw parsing and no-replace archive publication are reused.

Historical receipt verification reads a bounded archived journal prefix and
compares its exact original bytes with the current prefix, allowing later
appends. It NEVER calls _active or rebuilds prior source bundles recursively.
It verifies retained evidence, not source admission or actual trading fills.
"""
from __future__ import annotations

from datetime import timedelta
import gzip
import io
import json
from pathlib import Path
import re
import time
from uuid import uuid4
import zlib

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_source_bundle as sources
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops import tushare_live_transport as legacy


ARCHIVE = Path('data/reports/paper_prospective_sources_v1')
RECEIPT_TYPE = 'tushare_prospective_fund_daily_receipt_v1'
CLAIM_TYPE = 'prospective_fund_daily_once_claim_v1'
AUTHORITY_TYPE = 'prospective_journal_authority_archive_v1'
MAX_PREFIX_EVENTS = 4096
MAX_EVENT_BYTES = 2_000_000
MAX_PREFIX_BYTES = 64_000_000
MAX_CHUNK_DECODED_BYTES = 4_000_000
MAX_CHUNKS = 48
MAX_COMPRESSED_BYTES = 12_000_000
MAX_SUPPORTING = 32
MAX_ARCHIVE_BASE_BYTES = 14_000_000  # Leave room within EvidenceContext's 16 MB.
SCOPE_KEYS = {'artifact_type','purpose','market','evidence_mode','journal','journal_binding',
    'candidate_id','asset_id','source_id','source_profile','request','session','next_session',
    'valid_from','valid_until','request_budget','retry_budget','transport_limits','policy',
    'context','implementation_binding'}
BASE_RECEIPT_KEYS = {
    'artifact_type','status','evidence_class','scope_sha256','scope_ref','claim_ref','gate_ref',
    'evidence_refs','request','implementation_binding','request_started_at','received_at',
    'raw_response','normalized_bar','http_clock','daily_observation_not_before',
    'availability_upper_bound','provider_generated_at','provider_available_at',
    'first_publication_verified','source_quality_verified','candidate_qualification_granted',
    'strategy_forward_days_added','http_attempts_started','network_requests_started',
    'mocked_requests_started','representation','deadline_enforcement','power_loss_durability_certified',
}


def request_identity(scope):
    """Context labels and scope timestamps cannot reset a consumed decision."""
    binding=scope['journal_binding']
    return forward.digest(dict(candidate_manifest_sha256=binding['manifest']['sha256'],
        decision_sha256=binding['decision_sha256'],request=parser.request_identity(**scope['request'])))


def _path(root, path):
    path=Path(path)
    if not path.resolve().is_relative_to(root):
        raise ValueError('Prospective archive path escapes repository')
    current=root
    for part in path.relative_to(root).parts:
        current/=part
        if current.is_symlink():raise ValueError('Prospective archive symlink not allowed')
    return path


def _file_bytes(root, ref):
    sources._keys(ref,('path','sha256'))
    path=Path(ref['path'])
    if not path.is_absolute():raise ValueError('Absolute frozen journal evidence reference required')
    path=_path(root,path)
    raw=legacy._read(path)
    if legacy._sha(raw)!=ref['sha256']:raise ValueError('Frozen authority evidence hash changed')
    return raw


def _events_from_originals(originals):
    events=[];previous=None
    if not 1<=len(originals)<=MAX_PREFIX_EVENTS:raise ValueError('Bounded archived journal prefix required')
    for i,item in enumerate(originals):
        sources._keys(item,('name','raw'))
        if item['name']!=f'{i:08d}.json' or not isinstance(item['raw'],str):
            raise ValueError('Archived journal prefix sequence mismatch')
        raw=item['raw'].encode('utf-8')
        if len(raw)>MAX_EVENT_BYTES:raise ValueError('Archived event byte budget exceeded')
        event=legacy._decode(raw)
        if not isinstance(event,dict):raise ValueError('Journal event object required')
        supplied=event.pop('sha256',None)
        if (supplied!=forward.digest(event) or event.get('previous_sha256')!=previous
                or event.get('sequence')!=i or event.get('artifact_type')!=forward.EVENT_TYPE):
            raise ValueError('Archived journal hash chain mismatch')
        event['sha256']=supplied
        if events and forward._instant(event['received_at'])<forward._instant(events[-1]['received_at']):
            raise ValueError('Archived journal clock regressed')
        if event.get('kind') not in ('activation','decision','decision_durability','observation','observation_durability'):
            raise ValueError('Unsupported journal authority event')
        events.append(event);previous=supplied
    return events


def _snapshot_authority(root, scope, folder):
    binding=scope['journal_binding'];count=binding['prefix_length']
    if type(count) is not int or not 1<=count<=MAX_PREFIX_EVENTS:
        raise ValueError('Bounded journal prefix required')
    journal=_path(root,root/scope['journal']);originals=[];total=0
    for index in range(count):
        raw=legacy._read(journal/f'{index:08d}.json',MAX_EVENT_BYTES)
        total+=len(raw)
        if total>MAX_PREFIX_BYTES:raise ValueError('Journal prefix byte budget exceeded')
        originals.append(dict(name=f'{index:08d}.json',raw=raw.decode('utf-8')))
    events=_events_from_originals(originals)
    if events[-1]['sha256']!=binding['prefix_sha256']:raise ValueError('Journal prefix changed before archive')
    activation=events[0]['payload']
    raw_manifest=_file_bytes(root,activation['manifest']);manifest=legacy._decode(raw_manifest)
    raw_qualification=_file_bytes(root,activation['qualification']);qualification=legacy._decode(raw_qualification)
    snapshots=dict(manifest=raw_manifest,qualification=raw_qualification,
        calendar=_file_bytes(root,manifest['calendar']),warmup=_file_bytes(root,manifest['warmup']))
    supporting=qualification.get('supporting_evidence')
    if not isinstance(supporting,list) or not 1<=len(supporting)<=MAX_SUPPORTING:
        raise ValueError('Bounded independent qualification support required')
    for i,ref in enumerate(supporting):snapshots[f'support_{i:03d}']=_file_bytes(root,ref)
    refs={key:legacy._publish(folder/f'{key}.original',raw) for key,raw in snapshots.items()}
    chunks=[];compressed_total=0
    def publish_chunk(items):
        nonlocal compressed_total
        raw=legacy._canonical(items)
        if len(raw)>MAX_CHUNK_DECODED_BYTES:
            if len(items)==1:raise ValueError('Journal event compression budget exceeded')
            middle=len(items)//2;publish_chunk(items[:middle]);publish_chunk(items[middle:]);return
        encoded=gzip.compress(raw,mtime=0)
        if len(encoded)>legacy.MAX_DOCUMENT_BYTES:
            if len(items)==1:raise ValueError('Journal event compression budget exceeded')
            middle=len(items)//2;publish_chunk(items[:middle]);publish_chunk(items[middle:]);return
        if len(chunks)>=MAX_CHUNKS or compressed_total+len(encoded)>MAX_COMPRESSED_BYTES:
            raise ValueError('Journal archive budget exceeded')
        key=f'prefix_{len(chunks):03d}'
        refs[key]=legacy._publish(folder/f'{key}.json.gz',encoded)
        chunks.append(key);compressed_total+=len(encoded)
    publish_chunk(originals)
    authority=dict(artifact_type=AUTHORITY_TYPE,journal=scope['journal'],
        prefix_length=count,prefix_sha256=binding['prefix_sha256'],
        prefix_chunks=chunks,supporting_count=len(supporting),original_bytes=total)
    refs['authority']=legacy._publish_json(folder/'authority.json',authority)
    return refs


def _consume(folder, ref, context=None):
    raw=legacy._bound(folder,ref)
    if context is not None:
        relative=(folder/ref['path']).resolve().relative_to(context.root).as_posix()
        if context.read_bytes(dict(path=relative,sha256=ref['sha256']))!=raw:
            raise ValueError('Archive changed during source adapter read')
    return raw


def _validate_archived_authority(scope, decoded, originals, *, root, context=None):
    """Structural/provenance validation only; deliberately no _active recursion."""
    events=_events_from_originals(originals);binding=scope['journal_binding']
    if (len(events)!=binding['prefix_length'] or events[-1]['sha256']!=binding['prefix_sha256']
            or events[0]['sha256']!=binding['activation_sha256'] or events[0]['kind']!='activation'):
        raise ValueError('Archived scope prefix binding mismatch')
    activation=events[0]['payload'];manifest=decoded['manifest'];qualification=decoded['qualification']
    calendar=decoded['calendar'];warmup=decoded['warmup']
    if activation['manifest']!=binding['manifest'] or activation['qualification']!=binding['qualification']:
        raise ValueError('Archived activation reference mismatch')
    refs=[('manifest',activation['manifest']),('qualification',activation['qualification']),
          ('calendar',manifest['calendar']),('warmup',manifest['warmup'])]
    for name,ref in refs:
        if decoded['_raw_hashes'][name]!=ref['sha256']:
            raise ValueError('Archived original authority hash mismatch')
    if (manifest.get('artifact_type')!=forward.MANIFEST_TYPE
            or qualification.get('artifact_type')!=forward.QUALIFICATION_TYPE
            or qualification.get('manifest_sha256')!=binding['manifest']['sha256']
            or qualification.get('verdict')!='qualified'
            or qualification.get('review_role')!='independent_qualification_review'
            or any(qualification.get('gates',{}).get(name) is not True for name in forward.GATES)):
        raise ValueError('Archived independent candidate qualification required')
    support=qualification['supporting_evidence']
    if not support or len(support)!=decoded['_supporting_count']:
        raise ValueError('Archived supporting evidence incomplete')
    for i,ref in enumerate(support):
        if (decoded['_raw_hashes'][f'support_{i:03d}']!=ref['sha256']
                or ref['sha256'] in (binding['manifest']['sha256'],binding['qualification']['sha256'])):
            raise ValueError('Archived independent support hash mismatch')
    mode=activation.get('mode')
    if mode not in ('synthetic','forward'):raise ValueError('Replay cannot authorize prospective capture')
    allowed_classes=('reviewed_research',) if mode=='forward' else ('synthetic_test_only','reviewed_research')
    if (qualification.get('evidence_class') not in allowed_classes
            or activation.get('evidence_class')!=qualification.get('evidence_class')):
        raise ValueError('Archived candidate lineage mismatch')
    if forward._instant(qualification['issued_at'])>forward._instant(events[0]['received_at']):
        raise ValueError('Qualification postdates activation')
    source=manifest['source_contract'];profile=source.get('originals_binding')
    if (source.get('timestamp_basis')!=scopes.RECEIVED_BASIS or profile!=scope['source_profile']
            or profile.get('runtime',{}).get('lineage')!=('synthetic_only' if mode=='synthetic' else 'recorded_observation')
            or manifest['runtime_binding']!=scope['implementation_binding']['forward']):
        raise ValueError('Archived source and runtime binding mismatch')
    forward.validate_schedule(calendar,source['timestamp_basis'])
    dates=[row['date'] for row in calendar]
    start=dates.index(manifest['first_session'])
    if start<21 or [bar['date'] for bar in warmup['bars']]!=dates[:start]:
        raise ValueError('Archived warmup prefix mismatch')
    observed=[event for event in events if event['kind']=='observation']
    for offset,event in enumerate(observed):
        packet=event['payload']['packet'];index=start+offset
        if packet['session_date']!=dates[index]:raise ValueError('Archived observed session order mismatch')
        forward.validate_input_clocks(packet,calendar[index],source['timestamp_basis'],
                                      now=forward._instant(event['received_at']))
        if forward._observation_receipt(events,event,manifest,calendar,mode=mode) is None:
            raise ValueError('Unconfirmed observation cannot authorize acquisition')
    index=start+len(observed)
    if index+1>=len(calendar):raise ValueError('Archived next-session calendar missing')
    session,next_session=calendar[index:index+2]
    decisions=[event for event in events if event['kind']=='decision' and event['payload']['session_date']==session['date']]
    if len(decisions)!=1:raise ValueError('One archived pending decision required')
    decision=decisions[0];clocks=forward.session_clocks(session,source['timestamp_basis'])
    confirmed=forward._decision_receipt(events,decision,cutoff=clocks['cutoff'])
    if (confirmed is None or decision['sha256']!=binding['decision_sha256']
            or confirmed['sha256']!=binding['durability_sha256']):
        raise ValueError('Archived pre-open durability binding mismatch')
    match=re.fullmatch(r'CN_ETF_(XSHG|XSHE)_([0-9]{6})',manifest['asset_id'])
    if match is None:raise ValueError('Archived ETF identity invalid')
    request=dict(ts_code=match[2]+('.SH' if match[1]=='XSHG' else '.SZ'),trade_date=session['date'].replace('-',''))
    deadline=min(clocks['observable']+timedelta(seconds=source['maximum_receive_delay_seconds']),
                 forward.session_clocks(next_session,source['timestamp_basis'])['cutoff'])
    if (scope['request']!=request or scope['session']!=session or scope['next_session']!=next_session
            or scope['valid_from']!=parser._stamp(clocks['observable']) or scope['valid_until']!=parser._stamp(deadline)
            or scope['asset_id']!=manifest['asset_id'] or scope['candidate_id']!=manifest['candidate_id']
            or scope['source_id']!=source['source_id']
            or scope['evidence_mode']!=('synthetic_only' if mode=='synthetic' else 'recorded_observation')):
        raise ValueError('Archived acquisition scope differs from pending candidate')
    journal=_path(root,root/scope['journal'])
    # Compare only the captured prefix. Later events may legitimately refer to
    # this very receipt; verifying them recursively would create a cycle.
    for item in originals:
        path=journal/item['name'];expected=item['raw'].encode('utf-8')
        if context is None:
            actual=legacy._read(path,MAX_EVENT_BYTES)
        else:
            # These current originals are dependencies too, not just the archive.
            # Use the consumer's unchanged per-document/count/byte hard limits;
            # its final recheck must detect edits after this adapter returns.
            actual=context.read_bytes(dict(path=path.relative_to(context.root).as_posix(),
                                           sha256=legacy._sha(expected)))
        if actual!=expected:
            raise ValueError('Original journal prefix no longer present')
    return mode


def verify_prospective_receipt(receipt_path, *, expected_scope_sha256=None, context=None):
    """Reparse retained bytes and exact original authority, allowing journal append.

    Archived implementation hashes agree with capture; current verifier hashes
    must be bound separately by the consuming SourceAdapter's reviewed registry.
    """
    path=Path(receipt_path).resolve(strict=True);folder=path.parent
    root=path.parents[5]
    if list(folder.glob('.pending-*')):raise ValueError('Pending prospective archive requires recovery')
    raw=legacy._read(path);receipt=legacy._decode(raw)
    if not isinstance(receipt,dict):raise ValueError('Prospective receipt object required')
    supplied=receipt.pop('sha256',None)
    if supplied!=forward.digest(receipt) or receipt.get('artifact_type')!=RECEIPT_TYPE:
        raise ValueError('Prospective receipt hash or type mismatch')
    sources._keys(receipt,BASE_RECEIPT_KEYS,('parsed_contract','elapsed_monotonic_seconds','failure_code'))
    if context is not None:
        context.read_bytes(dict(path=path.relative_to(context.root).as_posix(),sha256=legacy._sha(raw)))
    scope=legacy._decode(_consume(folder,receipt['scope_ref'],context))
    claim=legacy._decode(_consume(folder,receipt['claim_ref'],context))
    gate=legacy._decode(_consume(folder,receipt['gate_ref'],context))
    sources._keys(scope,SCOPE_KEYS)
    if (scope.get('artifact_type')!=scopes.SCOPE_TYPE or scope.get('purpose')!=scopes.PURPOSE
            or scope.get('market')!='CN_ETF' or scope.get('policy')!=scopes.POLICY
            or type(scope.get('request_budget')) is not int or scope['request_budget']!=1
            or type(scope.get('retry_budget')) is not int or scope['retry_budget']!=0
            or scope.get('transport_limits')!=scopes.LIMITS):
        raise ValueError('Exact prospective source policy required')
    scopes._context(scope['context'])
    identity=request_identity(scope)
    lineage=receipt['evidence_class']
    if lineage not in ('mock_transport_contract_test','live_source_observation'):
        raise ValueError('Prospective capture lineage required')
    expected_folder=root/ARCHIVE/('mock_requests' if lineage=='mock_transport_contract_test' else 'requests')/identity
    if folder!=expected_folder:raise ValueError('Prospective archive identity or location mismatch')
    digest=forward.digest(scope)
    if receipt['scope_sha256']!=digest or expected_scope_sha256 is not None and expected_scope_sha256!=digest:
        raise ValueError('Prospective scope hash mismatch')
    references=receipt['evidence_refs']
    if not isinstance(references,dict) or not 5<=len(references)<=MAX_CHUNKS+MAX_SUPPORTING+5:
        raise ValueError('Bounded complete authority archive required')
    archived={name:_consume(folder,ref,context) for name,ref in references.items()}
    base_refs=[receipt['scope_ref'],receipt['claim_ref'],receipt['gate_ref'],*references.values()]
    if sum(len(_consume(folder,ref,context)) for ref in base_refs)>MAX_ARCHIVE_BASE_BYTES:
        raise ValueError('Complete source-adapter archive budget exceeded')
    authority=legacy._decode(archived['authority'])
    sources._keys(authority,('artifact_type','journal','prefix_length','prefix_sha256','prefix_chunks','supporting_count','original_bytes'))
    chunks=authority['prefix_chunks'];support=authority['supporting_count']
    if (authority['artifact_type']!=AUTHORITY_TYPE or authority['journal']!=scope['journal']
            or authority['prefix_length']!=scope['journal_binding']['prefix_length']
            or authority['prefix_sha256']!=scope['journal_binding']['prefix_sha256']
            or not isinstance(chunks,list) or not 1<=len(chunks)<=MAX_CHUNKS
            or chunks!=[f'prefix_{i:03d}' for i in range(len(chunks))]
            or type(support) is not int or not 1<=support<=MAX_SUPPORTING
            or set(references)!=({'authority','manifest','qualification','warmup','calendar'}
                |set(chunks)|{f'support_{i:03d}' for i in range(support)})):
        raise ValueError('Authority archive index mismatch')
    if sum(len(archived[name]) for name in chunks)>MAX_COMPRESSED_BYTES:
        raise ValueError('Compressed authority budget exceeded')
    originals=[];total=0
    for name in chunks:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(archived[name])) as compressed:
                unpacked=compressed.read(MAX_CHUNK_DECODED_BYTES+1)
        except (OSError,EOFError,zlib.error):
            raise ValueError('Invalid compressed authority original') from None
        if len(unpacked)>MAX_CHUNK_DECODED_BYTES:raise ValueError('Authority decompression budget exceeded')
        entries=legacy._decode(unpacked)
        if not isinstance(entries,list):raise ValueError('Authority prefix list required')
        originals.extend(entries)
        if len(originals)>MAX_PREFIX_EVENTS:raise ValueError('Authority prefix event budget exceeded')
        total+=sum(len(item['raw'].encode('utf-8')) for item in entries)
        if total>MAX_PREFIX_BYTES:raise ValueError('Authority decoded prefix budget exceeded')
    if total!=authority['original_bytes']:raise ValueError('Authority original byte count mismatch')
    decoded={name:legacy._decode(archived[name]) for name in ('manifest','qualification','warmup','calendar')}
    decoded['_raw_hashes']={name:legacy._sha(value) for name,value in archived.items()}
    decoded['_supporting_count']=support
    mode=_validate_archived_authority(scope,decoded,originals,root=root,context=context)
    expected_lineage='mock_transport_contract_test' if mode=='synthetic' else 'live_source_observation'
    if lineage!=expected_lineage:raise ValueError('Capture lineage differs from archived journal')
    expected_claim=dict(artifact_type=CLAIM_TYPE,scope_sha256=digest,request_identity=identity,
        request=parser.request_identity(**scope['request']),claimed_at=claim.get('claimed_at'),
        request_budget_reserved=1,retry_budget=0,evidence_class=lineage,
        scope_ref=receipt['scope_ref'],gate_ref=receipt['gate_ref'],evidence_refs=references,
        implementation_binding=scope['implementation_binding'])
    if legacy._canonical(claim)!=legacy._canonical(expected_claim):raise ValueError('Prospective claim binding mismatch')
    claimed=parser._utc(claim['claimed_at'])
    legacy._gate_ready(gate,scope,claimed)
    if not parser._utc(scope['valid_from'])<=claimed<parser._utc(scope['valid_until']):
        raise ValueError('Prospective claim outside authorized window')
    if receipt['implementation_binding']!=scope['implementation_binding'] or receipt['request']!=claim['request']:
        raise ValueError('Prospective receipt implementation or request mismatch')
    enforcement=('mock_injected_transport_clock_checks' if lineage=='mock_transport_contract_test'
                 else 'isolated_process_monotonic_deadline_terminate_and_join')
    if (receipt['representation']!='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes'
            or receipt['deadline_enforcement']!=enforcement):
        raise ValueError('Prospective transport representation mismatch')
    for key in ('first_publication_verified','source_quality_verified','candidate_qualification_granted','power_loss_durability_certified'):
        if receipt[key] is not False:raise ValueError('Capture cannot certify admission or publication')
    if receipt['strategy_forward_days_added']!=0 or receipt['provider_generated_at'] is not None or receipt['provider_available_at'] is not None:
        raise ValueError('Capture cannot create strategy days or publication clocks')
    if receipt['daily_observation_not_before']!=scope['session']['daily_observation_not_before']:
        raise ValueError('Prospective observation boundary mismatch')
    for key in ('http_attempts_started','network_requests_started','mocked_requests_started'):
        if type(receipt[key]) is not int or not 0<=receipt[key]<=1:raise ValueError('One prospective attempt required')
    if (receipt['network_requests_started']!=int(lineage=='live_source_observation')*receipt['http_attempts_started']
            or receipt['mocked_requests_started']!=int(lineage=='mock_transport_contract_test')*receipt['http_attempts_started']):
        raise ValueError('Prospective attempt lineage mismatch')
    if receipt['status']=='source_observed_unqualified':
        if 'failure_code' in receipt:raise ValueError('Successful receipt cannot contain a rejection')
        body=_consume(folder,receipt['raw_response'],context)
        if receipt['raw_response'].get('bytes')!=len(body) or len(body)>scope['transport_limits']['max_response_bytes']:
            raise ValueError('Prospective response byte count mismatch')
        parsed=parser.parse_fund_daily_body(body,**scope['request'])
        if parsed!=receipt['parsed_contract'] or parsed['bar']!=receipt['normalized_bar']:
            raise ValueError('Prospective raw response mapping mismatch')
        started,received=parser._utc(receipt['request_started_at']),parser._utc(receipt['received_at'])
        if not claimed<=started<=received<parser._utc(scope['valid_until']):raise ValueError('Prospective receipt clock mismatch')
        if receipt['availability_upper_bound']!=parser._availability_bound(received):raise ValueError('Prospective availability mismatch')
        if receipt['http_clock']!=parser._http_clock(receipt['http_clock'].get('http_date'),started=started,received=received):
            raise ValueError('Prospective HTTP clock mismatch')
        elapsed=receipt['elapsed_monotonic_seconds']
        if type(elapsed) not in (int,float) or not 0<=elapsed<=scope['transport_limits']['total_seconds'] or abs((received-started).total_seconds()-elapsed)>5:
            raise ValueError('Prospective elapsed-time budget mismatch')
        if receipt['http_attempts_started']!=1:raise ValueError('Successful capture requires one attempt')
    elif receipt['status']=='source_rejected':
        if (receipt['raw_response'] is not None or receipt['normalized_bar'] is not None
                or 'parsed_contract' in receipt or receipt['http_clock'] is not None
                or receipt['availability_upper_bound'] is not None
                or not isinstance(receipt.get('failure_code'),str) or not receipt['failure_code']
                or (folder/'response.entity.json').exists()):
            raise ValueError('Rejected source cannot supply price inputs')
    else:raise ValueError('Unsupported prospective receipt status')
    # Recheck archived originals and the exact existing prefix after parsing.
    final_refs=[*base_refs]
    if receipt['raw_response'] is not None:final_refs.append(receipt['raw_response'])
    for ref in final_refs:_consume(folder,ref,context)
    _validate_archived_authority(scope,decoded,originals,root=root,context=context)
    if legacy._read(path)!=raw:raise ValueError('Receipt changed during verification')
    receipt['sha256']=supplied
    return receipt


def capture_prospective_source(scope_path, *, repo_root='.', execute=False,
                               expected_scope_sha256=None, mock_hooks=None):
    """Preview by default. Every attempted request consumes its durable identity."""
    root=Path(repo_root).resolve(strict=True);mocked=mock_hooks is not None
    if mocked and (not isinstance(mock_hooks,dict) or set(mock_hooks)!={'clock','monotonic','gate','token','session'}
                   or any(not callable(value) for value in mock_hooks.values())):
        raise ValueError('Complete explicit prospective mock hooks required')
    clock=mock_hooks['clock'] if mocked else legacy._now
    def now_arg():return parser._stamp(parser._utc(clock())) if mocked else None
    scope=scopes.read_scope(scope_path,repo_root=root);digest=forward.digest(scope)
    identity=request_identity(scope)
    folder=_path(root,root/ARCHIVE/('mock_requests' if mocked else 'requests')/identity)
    if execute and expected_scope_sha256!=digest:raise ValueError('exact_frozen_scope_hash_required_for_execution')
    if execute and folder.exists():
        try:
            receipt=verify_prospective_receipt(folder/'receipt.json')
            legacy._confirm_files(folder,receipt)
            return dict(status='already_consumed',receipt_path=str(folder/'receipt.json'),
                        receipt_sha256=receipt['sha256'],strategy_forward_days_added=0)
        except (OSError,ValueError,KeyError,TypeError,EOFError):return legacy.inspect_attempt(folder)
    validated=scopes.validate_execution(scope,repo_root=root,now=now_arg(),synthetic=mocked)
    if not execute:
        return dict(status='preview',**validated,attempt_directory=str(folder),
                    request_already_reserved=folder.exists(),candidate_qualification_granted=False)
    gate_output=root/ARCHIVE/'preflight'/uuid4().hex
    gate=(mock_hooks['gate'](root,scope,gate_output) if mocked else legacy._fresh_gate(root,scope,gate_output))
    legacy._gate_ready(gate,scope,parser._utc(clock()))
    if forward.digest(scopes.read_scope(scope_path,repo_root=root))!=digest:
        raise ValueError('Prospective scope changed during preflight')
    reserved=False
    try:
        with scopes.protected_execution(scope,repo_root=root,now=now_arg(),synthetic=mocked) as refresh:
            folder.parent.mkdir(parents=True,exist_ok=True)
            try:folder.mkdir()
            except FileExistsError:return legacy.inspect_attempt(folder)
            reserved=True
            scope_ref=legacy._publish_json(folder/'scope.json',scope)
            gate_ref=legacy._publish_json(folder/'gate.json',gate)
            evidence_refs=_snapshot_authority(root,scope,folder)
            again=refresh(now=now_arg())
            if again!=validated:raise ValueError('Prospective authority changed before claim')
            claimed=parser._utc(clock());legacy._gate_ready(gate,scope,claimed)
            if not parser._utc(scope['valid_from'])<=claimed<parser._utc(scope['valid_until']):
                raise ValueError('Prospective window expired before durable claim')
            lineage='mock_transport_contract_test' if mocked else 'live_source_observation'
            claim=dict(artifact_type=CLAIM_TYPE,scope_sha256=digest,request_identity=identity,
                request=validated['request'],claimed_at=parser._stamp(claimed),
                request_budget_reserved=1,retry_budget=0,evidence_class=lineage,
                scope_ref=scope_ref,gate_ref=gate_ref,evidence_refs=evidence_refs,
                implementation_binding=scope['implementation_binding'])
            claim_ref=legacy._publish_json(folder/'claim.json',claim)
            if sum(path.stat().st_size for path in folder.iterdir())>MAX_ARCHIVE_BASE_BYTES:
                raise ValueError('Complete source-adapter archive budget exceeded')
            legacy._confirm_references(folder,[scope_ref,gate_ref,claim_ref,*evidence_refs.values()])
        # Writer exclusion is released only after the once claim is persisted.
        # The shared bounded capture rechecks the live window before credentials
        # and again before sending; no retries and no environment proxy are used.
        receipt=dict(artifact_type=RECEIPT_TYPE,status='source_rejected',evidence_class=lineage,
            scope_sha256=digest,scope_ref=scope_ref,claim_ref=claim_ref,gate_ref=gate_ref,
            evidence_refs=evidence_refs,request=validated['request'],implementation_binding=scope['implementation_binding'],
            request_started_at=None,received_at=None,raw_response=None,normalized_bar=None,http_clock=None,
            daily_observation_not_before=scope['session']['daily_observation_not_before'],
            availability_upper_bound=None,provider_generated_at=None,provider_available_at=None,
            first_publication_verified=False,source_quality_verified=False,candidate_qualification_granted=False,
            strategy_forward_days_added=0,http_attempts_started=0,network_requests_started=0,mocked_requests_started=0,
            representation='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes',
            deadline_enforcement='mock_injected_transport_clock_checks' if mocked else 'isolated_process_monotonic_deadline_terminate_and_join',
            power_loss_durability_certified=False)
        legacy._capture_once(folder,scope,receipt,clock=clock,
            monotonic=mock_hooks['monotonic'] if mocked else time.monotonic,
            get_token=mock_hooks['token'] if mocked else legacy._existing_token,
            new_session=mock_hooks['session'] if mocked else legacy._new_session)
        receipt['sha256']=forward.digest(receipt)
        legacy._publish_json(folder/'receipt.json',receipt)
        verified=verify_prospective_receipt(folder/'receipt.json')
        legacy._confirm_files(folder,verified)
        return dict(status=verified['status'],receipt_path=str(folder/'receipt.json'),
            receipt_sha256=verified['sha256'],evidence_class=verified['evidence_class'],
            network_requests_started=verified['network_requests_started'],
            strategy_forward_days_added=0,candidate_qualification_granted=False)
    except (OSError,ValueError,KeyError,TypeError,EOFError):
        if reserved:return legacy.inspect_attempt(folder)
        raise


def _price(context, ref):
    receipt=context.read_json(ref)
    if receipt.get('artifact_type')!=RECEIPT_TYPE:raise ValueError('Prospective raw-source receipt required')
    verified=verify_prospective_receipt(context.path_for(ref),context=context)
    if verified['status']!='source_observed_unqualified':raise ValueError('Prospective capture not successful')
    return sources.Evidence(dict(bar=verified['normalized_bar']),verified['request_started_at'],
        verified['received_at'],'synthetic_only' if verified['evidence_class']=='mock_transport_contract_test' else 'recorded_observation',
        dict(verifier_sha256=legacy._sha(Path(__file__).read_bytes()),
             captured_implementation=verified['implementation_binding'],receipt_sha256=verified['sha256']))


def price_adapter():
    """Factory for a reviewed registry; never registers production.

    The unchanged EvidenceContext budget includes archived files AND every
    current prefix original. A successful standard archive consumes E+S+C+10
    unique files (prefix events E, supports S, compressed chunks C), at most 128
    files / 16 MB total / 2 MB per file. Already-consumed context files reduce
    this capacity. Larger valid standalone archives may fail adapter admission.
    """
    return sources.SourceAdapter('price',_price,dict(receipt_type=RECEIPT_TYPE,
        authority='archived_original_prefix_no_recursive_active',admission_granted=False))


def adapter_dependency_files():
    root=Path(__file__).resolve().parents[3]
    names=set(legacy.CODE_FILES)|{'src/quant_robot/ops/paper_prospective_scope.py',
        'src/quant_robot/ops/frozen_candidate_forward.py','src/quant_robot/ops/frozen_input_clocks.py',
        'src/quant_robot/ops/paper_source_bundle.py','scripts/capture_tushare_prospective_source.py'}
    return tuple(root/name for name in sorted(names))
