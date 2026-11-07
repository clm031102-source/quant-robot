"""Offline five-stage engineering of the proposed recorded 518880 connection.

The public production entry fails closed on missing reviewed facts. Private
fixture entrypoints have explicit synthetic lineage and never register a real
profile or dispatch a real worker. Frozen G1/account methods are left unchanged.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import time

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_prospective_recorded_transport as v2
from quant_robot.ops import paper_recorded_sources as recorded_sources
from quant_robot.ops import paper_recorded_518880_profile as profile
import json
import platform
from uuid import uuid4
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops import tushare_live_transport as archive

_TOKEN='fixed-artificial-token-not-from-any-account'
_MODULE='src/quant_robot/ops/paper_recorded_capture_observe.py'


evidence_sessions=sessions
source_connection=connection
CODE_FILES=forward.CODE_FILES
canonical=forward.canonical
digest=forward.digest
_sync_directory=forward._sync_directory


class _RecordedG1Action:
    """Root-owned open stages. No pending peek and no I/O after commit.

    Source stages retain exact head/guard obligations through their final read.
    Publication stages check immutable files, exact head and owned guard before
    commit; only metadata identity checking and lock removal follow commit.
    """
    def __init__(self,root,directory,*,operation=None,readonly=False,_stage=None,_offline=False):
        if _offline is not True:profile.reviewed_profile_518880()
        self.offline=True
        self.root=Path(root).resolve(strict=True);self.directory=Path(directory).resolve(strict=False)
        if not self.directory.is_relative_to(self.root):raise ValueError('Journal outside synthetic evidence root')
        self.relative=self.directory.relative_to(self.root).as_posix()
        if operation is not None and (type(operation) is not evidence_sessions.EvidenceOperation
                or operation.root!=self.root or operation._policy is not evidence_sessions.G1_RECORDED_POLICY):
            raise ValueError('Exact G1 five-stage synthetic operation required')
        self.operation=operation or evidence_sessions.EvidenceOperation(self.root,policy=evidence_sessions.G1_RECORDED_POLICY)
        self.owned_operation=operation is None;self.readonly=readonly;self.guard=None
        self.stage=None;self.phase=None;self.contract_reference=None;self.published_any=False
        self.boundary_records=[];self._runtime=None;self.initial_code=None;self.latest_events=[]
        self._source_handoff=None
        self._initial_stage=_stage

    def __enter__(self):
        try:
            self._begin('source')
            # Path validation precedes mkdir, preventing symlink/junction escape.
            self.stage.path_for(self.relative)
            if not self.readonly:
                self.directory.mkdir(parents=True,exist_ok=True)
                raw=(json.dumps(dict(pid=os.getpid(),instance_id=uuid4().hex,
                    purpose='synthetic_recorded_connection',automatic_lock_removal_allowed=False))+'\n').encode()
                with (self.directory/'.writer.lock').open('xb') as stream:
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                self.guard=raw
                self.check_guard(at_commit=True)
            self.journal(self.directory)
            return self
        except BaseException:
            self.operation.close();raise

    def __exit__(self,kind,value,traceback):
        if kind is not None:self.operation.fail()
        # Failure preserves publications and any still-held lock. A guard already
        # released after successful publication checks is never recreated; an
        # interrupted transaction or foreign replacement is never auto-cleared.
        if self.owned_operation:self.operation.close()
        return False

    def _begin(self,phase):
        if self._initial_stage is not None:
            stage=self._initial_stage;self._initial_stage=None
            if (type(stage) is not evidence_sessions.VerificationSession
                    or stage is not self.operation._active or stage._operation is not self.operation):
                self.operation.fail();raise ValueError('Exact existing root stage required')
            stage.require_open();self.stage=stage
        else:self.stage=self.operation.stage()
        self.phase=phase
        catalog=self.stage.bind_implementation(evidence_sessions.RECORDED_CATALOG)
        if self.initial_code is not None and catalog!=self.initial_code:
            self.stage.fail('g1_code_changed_between_stages')
        self.initial_code=catalog
        self.root_child=self.stage.new_child('g1_authority')
        self.source=recorded_sources.RecordedSourceVerification.from_stage(self.stage,_offline=True)
        self.verified_sources={};self._runtime=None
        if self.guard is not None:self.check_guard(at_commit=phase=='source')

    def relative_ref(self,ref):
        if not isinstance(ref,dict) or set(ref)!={'path','sha256'}:raise ValueError('Exact frozen reference required')
        path=Path(ref['path'])
        if not path.is_absolute():raise ValueError('Absolute frozen authority reference required')
        if not path.resolve(strict=False).is_relative_to(self.root):raise ValueError('Frozen authority outside evidence root')
        relative=path.resolve(strict=False).relative_to(self.root).as_posix()
        self.stage.path_for(relative)
        return dict(path=relative,sha256=ref['sha256'])

    def reference(self,ref):return self.root_child.read_bytes(self.relative_ref(ref))

    def file_reference(self,path):
        path=Path(path).resolve(strict=False)
        if not path.is_relative_to(self.root):raise ValueError('Frozen authority outside evidence root')
        _,ref=self.root_child.snapshot_original(path.relative_to(self.root).as_posix())
        return dict(path=str(path),sha256=ref['sha256'])

    def contract_refs(self,manifest_ref,qualification_ref):
        current=(manifest_ref,qualification_ref)
        if self.contract_reference is not None and current!=self.contract_reference:
            raise ValueError('G1 authority changed within operation')
        self.contract_reference=current

    def runtime_binding(self):
        if self._runtime is None:
            from quant_robot.research.full_position_factors import np,pd
            code=self.stage.bind_implementation(evidence_sessions.RECORDED_CATALOG)['code']
            self._runtime=dict(code={name:code['src/quant_robot/'+name] for name in CODE_FILES},
                python=platform.python_version(),packages=dict(numpy=np.__version__,pandas=pd.__version__))
        return self._runtime

    def validate_source_contract(self,manifest):
        source=manifest.get('source_contract',{})
        expected=dict(artifact_type=source_connection.CONTRACT_TYPE,
            profile_id=profile.OFFLINE_PROFILE_ID,runtime=self.source.runtime_binding())
        if (source.get('timestamp_basis')!=source_connection.RECEIVED_BASIS
                or canonical(source.get('originals_binding'))!=canonical(expected)):
            raise ValueError('Exact five-stage original-bound synthetic source contract required')

    def journal(self,directory):
        if Path(directory).resolve(strict=False)!=self.directory:raise ValueError('One G1 journal per operation')
        if self.phase=='source':
            self.latest_events=self.root_child.current_journal(self.relative)
            return json.loads(canonical(self.latest_events))
        raise ValueError('Journal source reconstruction requires an open source stage')

    def verify_source(self,kind,manifest,payload,now,require_recorded):
        if require_recorded:raise ValueError('Synthetic G1 cannot verify recorded-forward sources')
        if self.phase!='source':raise ValueError('No source verification in publication-only stage')
        key=(kind,digest(payload))
        if key in self.verified_sources:
            earliest,ticket=self.verified_sources[key]
            if now<earliest:raise ValueError('G1 source verification clock regressed')
            return ticket
        if self.contract_reference is None:raise ValueError('Frozen authority must precede source verification')
        ref=self.relative_ref(self.contract_reference[0]);schedule=self.relative_ref(manifest['calendar'])
        method=self.source.verify_warmup_input if kind=='warmup' else self.source.verify_daily_input
        ticket=method(ref,payload,schedule_ref=schedule,now=now)
        self.verified_sources[key]=(now,ticket)
        return ticket

    def check_guard(self,*,at_commit=False):
        if self.guard is None:raise ValueError('Owned synthetic G1 writer guard required')
        self.stage.read_writer_guard(self.relative,self.guard,require_at_commit=at_commit)

    def _commit_private(self,label):
        self.root_child.propose(dict(boundary=label,synthetic_only=True))
        verified=self.stage.commit()
        self.boundary_records.append(verified.receipt())
        return verified

    def seal_calculation(self,*,observation=False):
        if self.phase=='source':
            self._commit_private('calculation_and_actual_originals_checked')
            self._begin('source' if observation else 'publication')

    def seal_postflush(self):
        if self.phase!='source':raise ValueError('Post-flush source stage required')
        self._commit_private('body_postflush_actual_originals_checked')
        self._begin('publication')

    def before_append(self,event):
        if self.readonly:raise ValueError('Read-only G1 cannot publish')
        if self.phase=='source' and event['kind']!='observation':
            raise ValueError('Publication before source finalization forbidden')
        if (event['sequence']!=len(self.latest_events)
                or event['previous_sha256']!=(self.latest_events[-1]['sha256'] if self.latest_events else None)):
            raise ValueError('Publication must extend the exact checked journal head')
        if len((json.dumps(event,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())>self.stage.policy.per_file_bytes:
            raise ValueError('Journal event exceeds original document budget')
        self.check_guard()

    def published(self,event):
        self.published_any=True
        raw,ref=self.root_child.snapshot_original(f'{self.relative}/{event["sequence"]:08d}.json')
        if json.loads(raw)!=event:raise ValueError('Published journal event differs')
        self.root_child.confirm_durable(ref)
        self.latest_events.append(json.loads(canonical(event)))

    def confirm_event(self,event):
        raw,ref=self.root_child.snapshot_original(f'{self.relative}/{event["sequence"]:08d}.json')
        if json.loads(raw)!=event:raise ValueError('Journal event changed before persistence confirmation')
        self.root_child.confirm_durable(ref);_sync_directory(self.directory)
        return event

    def finish(self,result):
        # Immutable value snapshot only; source tickets are never peeked.
        frozen=json.loads(canonical(result))
        ticket=self.root_child.propose(frozen)
        if not self.readonly:
            if self.phase!='publication':raise ValueError('G1 writer did not reach publication stage')
            self.stage.check_publication_head(self.relative,len(self.latest_events),require_at_commit=True)
            self.check_guard(at_commit=True)
        verified=self.stage.commit();self.boundary_records.append(verified.receipt())
        if not self.readonly:
            # All content reads, including the last ownership read, are finished.
            # Only metadata identity comparison and unlink happen after commit.
            # stat + unlink is not atomic against an external file replacement.
            path=self.directory/'.writer.lock';info=path.stat(follow_symlinks=False)
            current=dict(device=info.st_dev,inode=info.st_ino,size=info.st_size,
                         mtime_ns=info.st_mtime_ns)
            if current!=verified.receipt()['guard_metadata'][self.relative]:
                raise ValueError('Writer guard identity changed before cleanup')
            path.unlink();self.guard=None
        completed=verified.result(ticket)
        if self.owned_operation:self.operation.close()
        return dict(artifact_type='synthetic_recorded_connection_operation_v1',status='completed',
            result=completed,measurements=self.operation.measurements(),
            source_boundaries=[dict(stage=index+1,receipt_sha256=digest(item),
                active_journal_lengths={name:len(values) for name,values in item['active_journal_heads'].items()},
                guards_checked=item['writer_guards_checked']) for index,item in enumerate(self.boundary_records)],
            production_admission=False,real_forward_days_added=0,complete_capture_io_measured=False,
            offline_only=True,real_network_requests=0,actual_credentials=0)

    def require_owner(self):
        if (type(self) is not _RecordedG1Action or self.offline is not True
                or self.operation._policy is not sessions.G1_RECORDED_POLICY
                or self.stage is not self.operation._active):
            raise ValueError('exact_offline_recorded_framework_owner_required')
        self.stage.require_open()

@dataclass(frozen=True)
class _OfflineResponse:
    body: bytes
    http_date: str | None = None

    def __post_init__(self):
        if (type(self.body) is not bytes or not 0<len(self.body)<=scopes.LIMITS['max_response_bytes']
                or self.http_date is not None and (type(self.http_date) is not str or len(self.http_date)>128)):
            raise ValueError('Bounded artificial response bytes required')


class _Response:
    url=parser.SOURCE_URL
    status_code=200
    def __init__(self,fixture):self.fixture=fixture;self.headers={} if fixture.http_date is None else {'date':fixture.http_date}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def iter_content(self,chunk_size):
        for offset in range(0,len(self.fixture.body),chunk_size):yield self.fixture.body[offset:offset+chunk_size]


class _Session:
    def __init__(self,fixture,scope,counters):self.fixture=fixture;self.scope=scope;self.counters=counters
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def post(self,url,**kwargs):
        if (url!=parser.SOURCE_URL or kwargs.get('json')!=dict(api_name=parser.API_NAME,token=_TOKEN,
                params=self.scope['request'],fields=','.join(parser.FIELDS))
                or self.counters['mocked_requests_started']!=0):
            raise ValueError('Exactly one fixed artificial request required')
        self.counters['mocked_requests_started']+=1
        return _Response(self.fixture)


def _fixed_gate(owner,scope,now,counters):
    counters['mock_gate_calls']+=1
    code=owner.stage.bind_implementation(sessions.RECORDED_CATALOG)['code']
    return dict(status='ready',primary_market='CN_ETF',blockers=[],generated_at=forward._clock(now)[1],
        selected={**scope['context'],'current_branch':scope['context']['branch']},
        required_reading=[dict(path='synthetic_fixed_gate_code_only',status='read',sha256=code[_MODULE])],
        reading_summary=dict(required=1,read=1,missing=0),
        safety=dict(final_holdout_allowed=False,live_boundary_allowed=False),
        synthetic_gate_only=True,real_pm_gate_measured=False,production_admission=False)


def _fixed_token(owner,counters):
    owner.check_guard(at_commit=True);counters['mock_token_calls']+=1
    if counters['mock_token_calls']!=1:raise ValueError('One artificial token use only')
    return _TOKEN


def _relative(root,path):return Path(path).resolve(strict=False).relative_to(root).as_posix()


def _read_scope(stage,child,path,expected):
    raw,ref=child.snapshot_original(_relative(stage.root,path))
    if len(raw)>archive.MAX_DOCUMENT_BYTES:raise ValueError('Artificial scope byte budget exceeded')
    scope=archive._decode(raw)
    v2._scope(scope)
    if forward.digest(scope)!=expected:raise ValueError('Exact artificial scope digest required')
    stage.path_for(scope['journal'])
    return scope,ref


def _template(owner,reference,scope,now):
    spec=archive._decode(owner.root_child.read_bytes(reference))
    manifest=archive._decode(owner.reference(scope['journal_binding']['manifest']))
    calendar=archive._decode(owner.reference(manifest['calendar']))
    if (not isinstance(spec,dict) or spec.get('asset_id')!=scope['asset_id']
            or spec.get('session_date')!=scope['session']['date']
            or spec.get('window_start')!=calendar[0]['date']
            or set(spec.get('evidence',{}))!=set(daily.COMPONENTS)-{'price'}):
        raise ValueError('Exact four-component artificial template required')
    assembly=recorded_sources._RecordedAssembly(owner.stage,_offline=True)
    bundle=daily._build_source_bundle(spec,evidence_root=owner.root,decision_at=forward._clock(now)[1],
        adapters=assembly.profile.adapters,_deferred=assembly)
    if bundle['blockers']!=[dict(component='price',code='missing_evidence')]:
        raise ValueError('Artificial nonprice originals incomplete')
    assembly.propose(dict(status='four_artificial_components_pending',template_sha256=forward.digest(spec)))
    return spec


def _published(owner,folder,name,value,*,raw=False):
    owner.stage.path_for(_relative(owner.root,folder/name))
    ref=archive._publish(folder/name,value) if raw else archive._publish_json(folder/name,value)
    bound=dict(path=_relative(owner.root,folder/name),sha256=ref['sha256'])
    owner.root_child.read_bytes(bound)
    return ref


def _existing(stage,child,folder):
    """Bounded consumed-identity inspection; never certifies a historical price."""
    names=[];markers={};originals={};pending=False
    with os.scandir(folder) as entries:
        for count,entry in enumerate(entries,1):
            if count>stage.policy.ordinary_files:raise ValueError('Existing archive entry budget exceeded')
            names.append(entry.name);pending |= entry.name.startswith('.pending-')
            if not entry.is_file(follow_symlinks=False):raise ValueError('Existing archive regular originals required')
            raw,ref=child.snapshot_original(_relative(stage.root,entry.path))
            originals[entry.name]=dict(sha256=ref['sha256'],bytes=len(raw))
            if entry.name in ('scope.json','claim.json','receipt.json'):
                try:markers[entry.name]=archive._decode(raw)
                except ValueError:markers[entry.name]=None
    receipt=markers.get('receipt.json');marker_valid=False
    if isinstance(receipt,dict) and receipt.get('artifact_type') in (v1.RECEIPT_TYPE,v2.RECEIPT_TYPE):
        body=dict(receipt);supplied=body.pop('sha256',None);marker_valid=supplied==forward.digest(body)
    references_match=False
    if marker_valid:
        try:
            evidence=receipt['evidence_refs']
            if not isinstance(evidence,dict) or not 1<=len(evidence)<=5+v1.MAX_SUPPORTING:
                raise ValueError('Bounded archived marker references required')
            refs=[(receipt[key],name) for key,name in (('scope_ref','scope.json'),('gate_ref','gate.json'),('claim_ref','claim.json'))]
            refs.extend((ref,None) for ref in evidence.values())
            if receipt['status']=='source_observed_unqualified':refs.append((receipt['raw_response'],'response.entity.json'))
            elif receipt['status']!='source_rejected' or receipt['raw_response'] is not None:
                raise ValueError('Existing source marker status invalid')
            for ref,expected in refs:
                if (not isinstance(ref,dict) or set(ref) not in ({'path','sha256'},{'path','sha256','bytes'})
                        or not isinstance(ref['path'],str) or Path(ref['path']).name!=ref['path']
                        or ref['path'].startswith('.') or expected is not None and ref['path']!=expected
                        or ref['path'] not in originals or originals[ref['path']]['sha256']!=ref['sha256']
                        or 'bytes' in ref and (type(ref['bytes']) is not int or ref['bytes']!=originals[ref['path']]['bytes'])):
                    raise ValueError('Existing framework archived original reference mismatch')
            references_match=True
        except (KeyError,TypeError,ValueError):pass
    complete=(marker_valid and references_match and not pending and all(name in names for name in ('scope.json','gate.json','claim.json','receipt.json'))
        and isinstance(markers.get('scope.json'),dict) and isinstance(markers.get('claim.json'),dict)
        and (receipt.get('raw_response') is None or 'response.entity.json' in names))
    ticket=child.propose(dict(status='already_consumed' if complete else 'recovery_review_required',
        request_reservation_consumed=True,automatic_retry_allowed=False,receipt_success_not_assumed=True,
        existing_receipt_marker_valid=marker_valid,existing_archive_references_match=references_match,
        originals_examined=sorted(names),pending_files=pending,
        mocked_requests_started=0,mock_token_calls=0,real_network_requests=0,credentials_read=0,
        production_admission=False,real_forward_days_added=0,existing_branch_io_measured=True,
        complete_offline_connection_io_measured=False,complete_capture_io_measured=False,real_pm_gate_measured=False))
    return stage.commit().result(ticket)


def _prepare_offline_scope(directory,*,evidence_root,context,now):
    """Separate artificial fixture preparation; not part of a capture invocation."""
    with _RecordedG1Action(evidence_root,directory,readonly=True,_offline=True) as owner:
        scope=scopes.prepare_scope(directory,repo_root=owner.root,context=context,now=now,_reader=owner)
        return owner.finish(scope)


def capture_observe_recorded(scope_path,*,evidence_root,expected_scope_sha256,template_ref):
    """Production admission is unavailable; no token, network or journal is touched."""
    profile.reviewed_profile_518880()


def _check_handoff(owner, assembly, identity):
    if type(owner) is not _RecordedG1Action:
        raise ValueError('exact_framework_handoff_owner_required')
    owner.require_owner()
    handoff=owner._source_handoff
    if (type(assembly) is not recorded_sources._RecordedAssembly
            or assembly.stage is not owner.stage or owner.source.stage is not owner.stage
            or owner.phase!='source' or owner.readonly or owner.guard is None
            or handoff is None or handoff['stage'] is not owner.stage or handoff['consumed']):
        raise ValueError('same_open_unused_framework_handoff_required')
    if (not isinstance(identity,dict) or len(canonical(identity))>16384
            or canonical(identity)!=handoff['identity']
            or owner.contract_reference!=(identity['manifest'],identity['qualification'])
            or len(owner.latest_events)!=identity['prefix_length']
            or owner.latest_events[-1]['sha256']!=identity['prefix_sha256']):
        raise ValueError('exact_framework_handoff_identity_required')


def _consume_handoff(owner, assembly, identity, packet, *, now):
    _check_handoff(owner,assembly,identity)
    handoff=owner._source_handoff;ticket=handoff.get('ticket')
    if (handoff.get('assembly') is not assembly or type(ticket) is not sessions.PendingResult
            or ticket._stage_id!=owner.stage._id or digest(packet)!=handoff.get('packet_sha256')
            or len(canonical(packet))>owner.stage.policy.per_file_bytes
            or packet.get('session_date')!=identity['session_date']
            or packet.get('source_id')!=identity['source_id']
            or packet.get('bar',{}).get('asset_id')!=profile.ASSET_ID):
        raise ValueError('exact_framework_packet_obligation_required')
    packet=json.loads(canonical(packet))
    owner.verified_sources[('daily',digest(packet))]=(forward._clock(now)[0],ticket)
    handoff['consumed']=True
    return owner.finish(forward.observe(owner.directory,packet,now=now,_reader=owner))


def _observe_owned_offline_from_proof(owner, proof, *, acquired_at, now):
    if type(owner) is not _RecordedG1Action:
        raise ValueError('exact_framework_owner_required')
    owner.require_owner()
    if owner.phase!='source' or owner.readonly or owner._source_handoff is not None:
        raise ValueError('unused_framework_source_owner_required')
    if not isinstance(proof,dict) or len(canonical(proof))>65536:
        raise ValueError('bounded_framework_proof_required')
    proof=json.loads(canonical(proof));events=owner.journal(owner.directory)
    activation,manifest,_,schedule,_=forward._active(events,now=now,_reader=owner)
    if activation['mode']!='synthetic' or manifest['asset_id']!=profile.ASSET_ID:
        raise ValueError('offline_518880_authority_required')
    _,observations,start,_=forward._prefix(events,manifest,schedule,_reader=owner)
    index=start+len(observations)
    if index+1>=len(schedule):raise ValueError('pending_session_and_next_cutoff_required')
    session=schedule[index]
    decisions=[event for event in events if event['kind']=='decision'
               and event['payload']['session_date']==session['date']]
    if len(decisions)!=1:raise ValueError('one_durable_pending_decision_required')
    decision=decisions[0]
    confirmed=forward._decision_receipt(events,decision,
        cutoff=forward.session_clocks(session,manifest['source_contract']['timestamp_basis'])['cutoff'])
    if confirmed is None:raise ValueError('durable_pending_decision_required')
    identity=dict(root=str(owner.root),journal=owner.relative,activation_sha256=events[0]['sha256'],
        manifest=activation['manifest'],qualification=activation['qualification'],calendar=manifest['calendar'],
        manifest_value_sha256=digest(manifest),calendar_value_sha256=digest(schedule),
        prefix_length=len(events),prefix_sha256=events[-1]['sha256'],decision_sha256=decision['sha256'],
        durability_sha256=confirmed['sha256'],session_date=session['date'],source_id=manifest['source_contract']['source_id'],
        asset_id=manifest['asset_id'])
    owner._source_handoff=dict(stage=owner.stage,identity=canonical(identity),consumed=False)
    source=recorded_sources._RecordedInput(owner.stage,owner.relative_ref(activation['manifest']),
        owner.relative_ref(manifest['calendar']),daily_input=True,_offline=True)
    _check_handoff(owner,source.assembly,identity)
    packet=source.build('daily',proof,acquired_at=acquired_at,now=forward._clock(now)[0])
    owner._source_handoff.update(assembly=source.assembly,packet_sha256=digest(packet),
                                ticket=source.assembly.propose(packet))
    return _consume_handoff(owner,source.assembly,identity,packet,now=now)


def _offline_journal_action(action,directory,*,evidence_root,now,**kwargs):
    """Explicit fixture lifecycle, never a public production activation path."""
    if action not in ('activate','decide','observe','status'):
        raise ValueError('fixed_offline_journal_action_required')
    with _RecordedG1Action(evidence_root,directory,readonly=action=='status',_offline=True) as owner:
        if action=='activate':
            result=forward.activate(directory,kwargs['manifest_path'],kwargs['qualification_path'],
                                    mode='synthetic',now=now,_reader=owner)
        elif action=='decide':result=forward.decide(directory,now=now,_reader=owner)
        elif action=='observe':result=forward.observe(directory,kwargs['packet'],now=now,_reader=owner)
        else:result=forward.status(directory,_reader=owner)
        return owner.finish(result)


def _capture_observe_offline(scope_path,*,evidence_root,expected_scope_sha256,template_ref,response,now,operation=None,_actual_pm=False):
    if type(_actual_pm) is not bool or _actual_pm and now is not None:
        raise ValueError('actual_pm_framework_requires_host_clock')
    root=Path(evidence_root).resolve(strict=True)
    if type(response) is not _OfflineResponse:raise ValueError('Exact fixed artificial response required')
    if operation is not None and (type(operation) is not sessions.EvidenceOperation or operation.root!=root
            or operation._policy is not sessions.G1_RECORDED_POLICY):
        raise ValueError('Exact five-stage artificial root operation required')
    owned=operation is None;operation=operation or sessions.EvidenceOperation(root,policy=sessions.G1_RECORDED_POLICY)
    counters=dict(mock_gate_calls=0,mock_token_calls=0,mocked_requests_started=0)
    try:
        if _actual_pm:operation._enable_actual_pm()
        stage=operation.stage();stage.bind_implementation(sessions.RECORDED_CATALOG)
        bootstrap=stage.new_child('capture_bootstrap')
        scope,scope_input=_read_scope(stage,bootstrap,scope_path,expected_scope_sha256)
        folder=stage.path_for((v1.ARCHIVE/'mock_requests'/v1.request_identity(scope)).as_posix())
        if folder.exists():
            result=_existing(stage,bootstrap,folder)
        else:
            with _RecordedG1Action(root,root/scope['journal'],operation=operation,_stage=stage,_offline=True) as owner:
                # P1: real source/code/head/guard reads precede any reservation.
                validated=scopes.validate_execution(scope,repo_root=root,now=now,synthetic=True,_reader=owner)
                template=_template(owner,template_ref,scope,now)
                gate=(operation._pm_role().run(stage,scope) if _actual_pm else _fixed_gate(owner,scope,now,counters))
                archive._gate_ready(gate,scope,forward._clock(now)[0])
                preparing=v2.RecordedReceiptVerification.from_stage(stage,_offline=True)
                descriptor,snapshots,current_refs=v2._snapshot(preparing,scope)
                capture_binding=preparing.binding
                owner._commit_private('capture_preclaim_actual_originals_checked')
                # P2: same guard, unchanged once identity, bounded durable claim.
                owner._begin('source');owner.root_child.read_bytes(scope_input)
                if scopes.validate_execution(scope,repo_root=root,now=now,synthetic=True,_reader=owner)!=validated:
                    raise ValueError('Artificial scope changed before claim')
                if _template(owner,template_ref,scope,now)!=template:raise ValueError('Artificial template changed')
                archive._gate_ready(gate,scope,forward._clock(now)[0])
                owner.stage.path_for(_relative(root,folder))
                folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
                scope_ref=_published(owner,folder,'scope.json',scope)
                gate_ref=_published(owner,folder,'gate.json',gate)
                evidence_refs={name:_published(owner,folder,f'{name}.original',raw,raw=True) for name,raw in snapshots.items()}
                evidence_refs['authority']=_published(owner,folder,'authority.json',dict(artifact_type=v2.AUTHORITY_TYPE,
                    prefix_dependency=descriptor,supporting_count=len(snapshots)-4))
                claiming=v2.RecordedReceiptVerification.from_stage(owner.stage,_offline=True)
                if claiming.binding!=capture_binding:raise ValueError('Artificial capture code changed before claim')
                v2._authority(claiming,claiming._child('claim'),scope,evidence_refs,folder)
                for ref in current_refs.values():owner.root_child.read_bytes(owner.relative_ref(ref))
                claimed=forward._clock(now)[1]
                archive._gate_ready(gate,scope,parser._utc(claimed))
                if not parser._utc(scope['valid_from'])<=parser._utc(claimed)<parser._utc(scope['valid_until']):
                    raise ValueError('Artificial claim window expired')
                claim=v2._claim(scope,scope_ref,gate_ref,evidence_refs,capture_binding,claimed)
                claim_ref=_published(owner,folder,'claim.json',claim)
                archive._confirm_references(folder,[scope_ref,gate_ref,claim_ref,*evidence_refs.values()],_reader=owner.root_child)
                owner._commit_private('capture_claim_persisted_and_actual_originals_checked')
                # P3: one fixed mock request and private same-stage G1 handoff.
                owner._begin('source');owner.root_child.read_bytes(scope_input)
                scopes.validate_execution(scope,repo_root=root,now=now,synthetic=True,_reader=owner)
                _template(owner,template_ref,scope,now)
                archive._gate_ready(gate,scope,forward._clock(now)[0])
                receipt=dict(artifact_type=v2.RECEIPT_TYPE,status='source_rejected',evidence_class=v2.LINEAGE,
                    scope_sha256=forward.digest(scope),scope_ref=scope_ref,claim_ref=claim_ref,gate_ref=gate_ref,evidence_refs=evidence_refs,
                    request=validated['request'],implementation_binding=scope['implementation_binding'],capture_binding=capture_binding,
                    request_started_at=None,received_at=None,raw_response=None,normalized_bar=None,http_clock=None,
                    daily_observation_not_before=scope['session']['daily_observation_not_before'],availability_upper_bound=None,
                    provider_generated_at=None,provider_available_at=None,first_publication_verified=False,source_quality_verified=False,
                    candidate_qualification_granted=False,strategy_forward_days_added=0,http_attempts_started=0,
                    network_requests_started=0,mocked_requests_started=0,
                    representation='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes',
                    deadline_enforcement='mock_injected_transport_clock_checks',power_loss_durability_certified=False)
                def token():return _fixed_token(owner,counters)
                def fixed_session():return _Session(response,scope,counters)
                archive._capture_once(folder,scope,receipt,clock=lambda:forward._clock(now)[0],monotonic=time.monotonic,
                    get_token=token,new_session=fixed_session,_reader=owner.root_child)
                receipt['sha256']=forward.digest(receipt)
                published=_published(owner,folder,'receipt.json',receipt)
                archive._confirm_files(folder,receipt,_reader=owner.root_child)
                if receipt['status']!='source_observed_unqualified':raise ValueError('Artificial response rejected; reservation consumed')
                receipt_ref=dict(path=_relative(root,folder/'receipt.json'),sha256=published['sha256'])
                spec=archive._decode(archive._canonical(template))
                spec['evidence']['price']=dict(adapter_id='synthetic_recorded_connection_price_v1',receipt=receipt_ref)
                spec_ref=_published(owner,folder,'daily_specification.json',spec)
                archive._confirm_references(folder,[spec_ref],_reader=owner.root_child)
                proof=dict(artifact_type=connection.PROOF_TYPE,evidence_root=str(root),
                    specification=dict(path=_relative(root,folder/'daily_specification.json'),sha256=spec_ref['sha256']))
                result=_observe_owned_offline_from_proof(owner,proof,acquired_at=forward._clock(now)[1],now=now)
                result.update(complete_offline_connection_io_measured=True,real_pm_gate_measured=False,
                    complete_capture_io_measured=False,receipt_ref=receipt_ref,request_identity=v1.request_identity(scope),**counters)
        if _actual_pm:result.update(operation._pm_role().summary())
        if owned:operation.close()
        result['measurements']=operation.measurements()
        return result
    except BaseException:
        operation.fail();raise
    finally:
        if owned:operation.close()
