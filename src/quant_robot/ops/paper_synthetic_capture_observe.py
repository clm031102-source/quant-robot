"""Five-stage synthetic capture/source/G1 with a fixed artificial response.

The default gate is artificial; the explicitly named actual-PM entry uses real
PM, Git and clocks. Token/session remain fixed local code. No network client,
reader, callback or JSON policy is injected and no production source is enabled.
The v1/v2 once directory is never cleared, renamed or retried by this module.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import time

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_prospective_transport_v2 as v2
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops import tushare_live_transport as archive

_TOKEN='fixed-artificial-token-not-from-any-account'
_MODULE='src/quant_robot/ops/paper_synthetic_capture_observe.py'


@dataclass(frozen=True)
class SyntheticResponse:
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
    code=owner.stage.bind_implementation(sessions.G1_CATALOG)['code']
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
    assembly=daily._DeferredAssembly(owner.stage)
    bundle=daily._build_source_bundle(spec,evidence_root=owner.root,decision_at=forward._clock(now)[1],
        adapters=daily.SYNTHETIC_DEFERRED_ADAPTERS,_deferred=assembly)
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
                    raise ValueError('Existing archived original reference mismatch')
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
        complete_synthetic_capture_observe_io_measured=False,complete_capture_io_measured=False,real_pm_gate_measured=False))
    return stage.commit().result(ticket)


def prepare_synthetic_scope(directory,*,evidence_root,context,now):
    """Separate artificial fixture preparation; not part of a capture invocation."""
    with forward._SyntheticG1Action(evidence_root,directory,readonly=True) as owner:
        scope=scopes.prepare_scope(directory,repo_root=owner.root,context=context,now=now,_reader=owner)
        return owner.finish(scope)


def capture_observe_synthetic(scope_path,*,evidence_root,expected_scope_sha256,template_ref,response,now,operation=None):
    """One full measured artificial root call; genuine PM/capture stay disabled."""
    return _capture_observe(scope_path,evidence_root=evidence_root,expected_scope_sha256=expected_scope_sha256,
        template_ref=template_ref,response=response,now=now,operation=operation,_actual_pm=False)


def capture_observe_actual_pm_synthetic(scope_path,*,evidence_root,expected_scope_sha256,template_ref,response,operation=None):
    """Actual PM/Git/clocks with a fixed artificial response; never live data."""
    return _capture_observe(scope_path,evidence_root=evidence_root,expected_scope_sha256=expected_scope_sha256,
        template_ref=template_ref,response=response,now=None,operation=operation,_actual_pm=True)


def _capture_observe(scope_path,*,evidence_root,expected_scope_sha256,template_ref,response,now,operation,_actual_pm):
    root=Path(evidence_root).resolve(strict=True)
    if type(response) is not SyntheticResponse:raise ValueError('Exact fixed artificial response required')
    if operation is not None and (type(operation) is not sessions.EvidenceOperation or operation.root!=root
            or operation._policy is not sessions.G1_SYNTHETIC_POLICY):
        raise ValueError('Exact five-stage artificial root operation required')
    owned=operation is None;operation=operation or sessions.EvidenceOperation(root,policy=sessions.G1_SYNTHETIC_POLICY)
    counters=dict(mock_gate_calls=0,mock_token_calls=0,mocked_requests_started=0)
    try:
        if _actual_pm:operation._enable_actual_pm()
        stage=operation.stage();stage.bind_implementation(sessions.G1_CATALOG)
        bootstrap=stage.new_child('capture_bootstrap')
        scope,scope_input=_read_scope(stage,bootstrap,scope_path,expected_scope_sha256)
        folder=stage.path_for((v1.ARCHIVE/'mock_requests'/v1.request_identity(scope)).as_posix())
        if folder.exists():
            result=_existing(stage,bootstrap,folder)
        else:
            with forward._SyntheticG1Action(root,root/scope['journal'],operation=operation,_stage=stage) as owner:
                # P1: real source/code/head/guard reads precede any reservation.
                validated=scopes.validate_execution(scope,repo_root=root,now=now,synthetic=True,_reader=owner)
                template=_template(owner,template_ref,scope,now)
                gate=(operation._pm_role().run(stage,scope) if _actual_pm else _fixed_gate(owner,scope,now,counters))
                archive._gate_ready(gate,scope,forward._clock(now)[0])
                preparing=v2.V2Verification.from_stage(stage)
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
                claiming=v2.V2Verification.from_stage(owner.stage)
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
                spec['evidence']['price']=dict(adapter_id='synthetic_prospective_fund_daily_v2',receipt=receipt_ref)
                spec_ref=_published(owner,folder,'daily_specification.json',spec)
                archive._confirm_references(folder,[spec_ref],_reader=owner.root_child)
                proof=dict(artifact_type=connection.PROOF_TYPE,evidence_root=str(root),
                    specification=dict(path=_relative(root,folder/'daily_specification.json'),sha256=spec_ref['sha256']))
                result=forward._observe_owned_synthetic_from_proof(owner,proof,acquired_at=forward._clock(now)[1],now=now)
                result.update(complete_synthetic_capture_observe_io_measured=True,real_pm_gate_measured=False,
                    complete_capture_io_measured=False,receipt_ref=receipt_ref,request_identity=v1.request_identity(scope),**counters)
        if _actual_pm:result.update(operation._pm_role().summary())
        if owned:operation.close()
        result['measurements']=operation.measurements()
        return result
    except BaseException:
        operation.fail();raise
    finally:
        if owned:operation.close()
