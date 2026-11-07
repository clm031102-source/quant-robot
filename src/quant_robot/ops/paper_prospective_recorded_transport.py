"""Isolated offline receipt framework for the proposed recorded 518880 connection.

No production profile or live receipt is admitted. Reuses the v1 once identity
and bounded original-prefix verifier without changing v1/v2 behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_recorded_518880_profile as profile
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_source_bundle as sources
from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops import tushare_live_transport as archive


RECEIPT_TYPE = 'synthetic_recorded_connection_receipt_v1'
CLAIM_TYPE = 'synthetic_recorded_connection_once_claim_v1'
AUTHORITY_TYPE = 'synthetic_recorded_connection_authority_v1'
LINEAGE = 'mock_transport_contract_test'
ARCHIVE = v1.ARCHIVE  # A format change never creates a fresh request budget.
POLICY = sessions.G1_RECORDED_POLICY
_REPO = Path(__file__).resolve().parents[3]
_CODE_FILES = tuple(sorted({p.relative_to(_REPO).as_posix() for p in v1.adapter_dependency_files()}
    | {'src/quant_robot/ops/paper_prospective_transport.py',
       'src/quant_robot/ops/paper_prospective_transport_v2.py',
       'src/quant_robot/ops/paper_source_connection.py',
       'src/quant_robot/ops/paper_warmup_bundle.py'}))


def request_identity(scope):return v1.request_identity(scope)


def _fail(code):raise sessions.EvidenceSessionError(code)


def _keys(value,required,optional=()):sources._keys(value,required,optional)


def _reference(root,path,sha):
    path=Path(path).resolve(strict=False)
    if not path.is_relative_to(root):_fail('v2_original_outside_consumer_root')
    return dict(path=path.relative_to(root).as_posix(),sha256=sha)


def _binding(stage):
    """Fixed trusted implementation paths; every content read uses the meter."""
    return dict(artifact_type='synthetic_recorded_connection_capture_binding_v1',
        **stage.bind_implementation(sessions.RECORDED_CATALOG),
        business_validator='v1_archived_authority_with_existing_durability_helpers')


def _price_evidence(receipt):
    if receipt['status']!='source_observed_unqualified':_fail('v2_rejected_receipt_has_no_price')
    return sources.Evidence(dict(bar=receipt['normalized_bar']),receipt['request_started_at'],
        receipt['received_at'],'synthetic_only',dict(verifier_binding=receipt['capture_binding'],
            receipt_sha256=receipt['sha256'],prefix_dependency=receipt['verified_prefix_dependency'],
            production_admission=False))


@dataclass(frozen=True)
class VerifiedFrameworkReceipt:
    _verified: sessions.VerifiedStage

    def receipt(self,ticket):return self._verified.result(ticket)

    def price(self,ticket):
        return _price_evidence(self.receipt(ticket))

    def measurements(self):return self._verified.receipt()['measurements']


class RecordedReceiptVerification:
    """Closed deferred verification stage; proposals never escape before commit."""
    def __init__(self,evidence_root,*,operation=None):
        profile.reviewed_profile_518880()
        self.root=Path(evidence_root).resolve(strict=True)
        self.operation=operation or sessions.EvidenceOperation(self.root,policy=POLICY)
        if self.operation.root!=self.root or self.operation._policy is not POLICY:
            _fail('v2_exact_reviewed_operation_required')
        self._owned=operation is None;self.stage=None;self.binding=None;self._counter=0

    def __enter__(self):
        self.stage=self.operation.stage()
        try:self.binding=_binding(self.stage)
        except BaseException:self.stage.abort();raise
        return self

    @classmethod
    def from_stage(cls,stage,*,_offline=False):
        """Only the fixed synthetic G1 root may finalize this borrowed stage."""
        if (type(stage) is not sessions.VerificationSession or stage.policy is not sessions.G1_RECORDED_POLICY):
            _fail('v2_exact_g1_borrowed_stage_required')
        if _offline is not True:
            stage.abort()
            profile.reviewed_profile_518880()
        stage.require_open();result=object.__new__(cls)
        result.root=stage.root;result.operation=stage._operation;result._owned=False
        result.stage=stage;result._counter=0;result._borrowed=True
        result.binding=_binding(stage)
        return result

    def __exit__(self,kind,value,traceback):
        if self.stage is not None:self.stage.__exit__(kind,value,traceback)
        if self._owned:self.operation.close()
        return False

    def _child(self,label):
        self.stage.require_open();self._counter+=1
        return self.stage.child(f'{label}_{self._counter}')

    def commit(self):
        if getattr(self,'_borrowed',False):_fail('v2_borrowed_stage_owned_by_root')
        self.stage.require_open()
        try:
            if _binding(self.stage)!=self.binding:_fail('v2_implementation_changed_during_verification')
            return VerifiedFrameworkReceipt(self.stage.commit())
        except BaseException:self.stage.abort();raise

    def prepare_price(self,reference):
        self.stage.require_open()
        try:return _prepare_receipt(self,reference)
        except BaseException:self.stage.abort();raise


@dataclass(frozen=True)
class DeferredPriceAdapter:
    """Intentionally incompatible with the old immediate SourceAdapter parser."""
    component: str = 'price'
    lineage: str = 'synthetic_only'

    def prepare(self,verification,reference):
        if type(verification) is not RecordedReceiptVerification:_fail('v2_deferred_verification_required')
        return verification.prepare_price(reference)


def price_adapter():return DeferredPriceAdapter()


def adapter_dependency_files():
    return tuple(_REPO/name for name in _CODE_FILES)+(Path(sessions.__file__).resolve(),)


def verify_receipt(reference,*,evidence_root):
    """Reference SHA is supplied by the caller; no unmetered bootstrap file read."""
    with RecordedReceiptVerification(evidence_root) as verification:
        ticket=price_adapter().prepare(verification,reference)
        committed=verification.commit()
    return dict(receipt=committed.receipt(ticket),measurements=verification.operation.measurements())


def _read_archive(verification,child,folder,reference,*,expected_name=None):
    _keys(reference,('path','sha256'),('bytes',))
    name=reference['path']
    if (not isinstance(name,str) or Path(name).name!=name or name.startswith('.')
            or '/' in name or '\\' in name or expected_name is not None and name!=expected_name):
        _fail('v2_archive_basename_required')
    ref=_reference(verification.root,folder/name,reference['sha256'])
    raw=child.read_bytes(ref)
    if len(raw)>archive.MAX_DOCUMENT_BYTES or 'bytes' in reference and reference['bytes']!=len(raw):
        _fail('v2_archive_size_mismatch')
    return raw


def _scope(scope):
    if not isinstance(scope,dict) or scope.get('asset_id')!=profile.ASSET_ID or scope.get('request',{}).get('ts_code')!=profile.TS_CODE:
        _fail('recorded_framework_requires_518880')
    _keys(scope,v1.SCOPE_KEYS)
    if (scope['artifact_type']!=scopes.SCOPE_TYPE or scope['purpose']!=scopes.PURPOSE
            or scope['market']!='CN_ETF' or scope['evidence_mode']!='synthetic_only'
            or scope['policy']!=scopes.POLICY or scope['transport_limits']!=scopes.LIMITS
            or type(scope['request_budget']) is not int or scope['request_budget']!=1
            or type(scope['retry_budget']) is not int or scope['retry_budget']!=0):
        _fail('v2_exact_synthetic_scope_required')
    scopes._context(scope['context'])


def _authority(verification,child,scope,references,folder):
    if not isinstance(references,dict) or not 6<=len(references)<=5+v1.MAX_SUPPORTING:
        _fail('v2_bounded_ordinary_authority_required')
    raw={name:_read_archive(verification,child,folder,ref) for name,ref in references.items()}
    authority=archive._decode(raw['authority'])
    _keys(authority,('artifact_type','prefix_dependency','supporting_count'))
    support=authority['supporting_count'];descriptor=authority['prefix_dependency']
    if (authority['artifact_type']!=AUTHORITY_TYPE or type(support) is not int
            or not 1<=support<=v1.MAX_SUPPORTING
            or set(references)!=({'authority','manifest','qualification','calendar','warmup'}
                |{f'support_{i:03d}' for i in range(support)})):
        _fail('v2_authority_index_mismatch')
    if not isinstance(descriptor,dict):_fail('v2_exact_prefix_descriptor_required')
    binding=scope['journal_binding']
    if (descriptor.get('journal_relative_path')!=scope['journal']
            or descriptor.get('prefix_length')!=binding['prefix_length']
            or descriptor.get('prefix_canonical_tail_sha256')!=binding['prefix_sha256']
            or descriptor.get('activation_sha256')!=binding['activation_sha256']):
        _fail('v2_scope_prefix_dependency_mismatch')
    view=child.prefix_view(descriptor)
    decoded={name:archive._decode(raw[name]) for name in ('manifest','qualification','calendar','warmup')}
    decoded['_raw_hashes']={name:archive._sha(value) for name,value in raw.items()}
    decoded['_supporting_count']=support
    mode=v1._validate_archived_authority(scope,decoded,view.originals(),root=verification.root,context=view)
    if mode!='synthetic':_fail('v2_only_synthetic_authority_is_implemented')
    return descriptor,raw


def _claim(scope,scope_ref,gate_ref,references,capture_binding,claimed_at):
    return dict(artifact_type=CLAIM_TYPE,scope_sha256=forward.digest(scope),
        request_identity=request_identity(scope),request=parser.request_identity(**scope['request']),
        claimed_at=claimed_at,request_budget_reserved=1,retry_budget=0,evidence_class=LINEAGE,
        scope_ref=scope_ref,gate_ref=gate_ref,evidence_refs=references,
        implementation_binding=scope['implementation_binding'],capture_binding=capture_binding)


def _validate_response(verification,child,folder,receipt,scope,claimed):
    for name in ('first_publication_verified','source_quality_verified','candidate_qualification_granted','power_loss_durability_certified'):
        if receipt[name] is not False:_fail('v2_cannot_certify_qualification_or_publication')
    if (type(receipt['strategy_forward_days_added']) is not int or receipt['strategy_forward_days_added']!=0
            or receipt['provider_generated_at'] is not None or receipt['provider_available_at'] is not None
            or receipt['daily_observation_not_before']!=scope['session']['daily_observation_not_before']
            or receipt['evidence_class']!=LINEAGE
            or receipt['representation']!='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes'
            or receipt['deadline_enforcement']!='mock_injected_transport_clock_checks'):
        _fail('v2_synthetic_lineage_or_clock_policy_mismatch')
    for name in ('http_attempts_started','mocked_requests_started','network_requests_started'):
        if type(receipt[name]) is not int or not 0<=receipt[name]<=1:_fail('v2_one_mock_attempt_required')
    if receipt['network_requests_started']!=0 or receipt['http_attempts_started']!=receipt['mocked_requests_started']:
        _fail('v2_real_request_not_supported')
    if receipt['status']=='source_observed_unqualified':
        if 'failure_code' in receipt or receipt['http_attempts_started']!=1:_fail('v2_success_attempt_mismatch')
        body=_read_archive(verification,child,folder,receipt['raw_response'],expected_name='response.entity.json')
        if len(body)>scope['transport_limits']['max_response_bytes'] or receipt['raw_response'].get('bytes')!=len(body):
            _fail('v2_response_byte_budget_mismatch')
        parsed=parser.parse_fund_daily_body(body,**scope['request'])
        if parsed!=receipt['parsed_contract'] or parsed['bar']!=receipt['normalized_bar']:_fail('v2_raw_mapping_mismatch')
        started,received=parser._utc(receipt['request_started_at']),parser._utc(receipt['received_at'])
        if not claimed<=started<=received<parser._utc(scope['valid_until']):_fail('v2_receive_clock_mismatch')
        if receipt['availability_upper_bound']!=parser._availability_bound(received):_fail('v2_availability_mismatch')
        if receipt['http_clock']!=parser._http_clock(receipt['http_clock'].get('http_date'),started=started,received=received):
            _fail('v2_http_clock_mismatch')
        elapsed=receipt['elapsed_monotonic_seconds']
        if type(elapsed) not in (int,float) or not 0<=elapsed<=scope['transport_limits']['total_seconds'] or abs((received-started).total_seconds()-elapsed)>5:
            _fail('v2_elapsed_budget_mismatch')
    elif receipt['status']=='source_rejected':
        if (receipt['raw_response'] is not None or receipt['normalized_bar'] is not None
                or receipt['http_clock'] is not None or receipt['availability_upper_bound'] is not None
                or 'parsed_contract' in receipt or not isinstance(receipt.get('failure_code'),str)
                or not receipt['failure_code'] or (folder/'response.entity.json').exists()):
            _fail('v2_rejected_source_cannot_supply_price')
    else:_fail('v2_unknown_receipt_status')


def _prepare_receipt(verification,reference):
    child=verification._child('price')
    return child.propose(_receipt_snapshot(verification,reference,child))


def _parse_for_deferred(context,reference):
    """Private parser; the owning source assembler exposes only a pending ticket."""
    from types import SimpleNamespace
    verification=SimpleNamespace(stage=context.stage,root=context.root,binding=_binding(context.stage))
    return _price_evidence(_receipt_snapshot(verification,reference,context))


def _receipt_snapshot(verification,reference,child):
    raw=child.read_bytes(reference)
    if len(raw)>archive.MAX_DOCUMENT_BYTES:_fail('v2_receipt_byte_budget_exceeded')
    receipt=archive._decode(raw);_keys(receipt,v1.BASE_RECEIPT_KEYS|{'sha256','capture_binding'},
                                     ('parsed_contract','elapsed_monotonic_seconds','failure_code'))
    supplied=receipt.pop('sha256')
    if supplied!=forward.digest(receipt) or receipt['artifact_type']!=RECEIPT_TYPE:_fail('v2_receipt_hash_or_type_mismatch')
    path=verification.stage.path_for(reference['path']);folder=path.parent
    if path.name!='receipt.json' or list(folder.glob('.pending-*')):_fail('v2_incomplete_archive')
    scope=archive._decode(_read_archive(verification,child,folder,receipt['scope_ref'],expected_name='scope.json'))
    _scope(scope)
    if folder!=verification.root/ARCHIVE/'mock_requests'/request_identity(scope):_fail('v2_once_identity_or_archive_location_mismatch')
    if receipt['scope_sha256']!=forward.digest(scope):_fail('v2_scope_digest_mismatch')
    if (receipt['capture_binding']!=verification.binding
            or receipt['implementation_binding']!=scope['implementation_binding']):
        _fail('v2_exact_capture_and_consumer_binding_required')
    gate=archive._decode(_read_archive(verification,child,folder,receipt['gate_ref'],expected_name='gate.json'))
    claim=archive._decode(_read_archive(verification,child,folder,receipt['claim_ref'],expected_name='claim.json'))
    expected=_claim(scope,receipt['scope_ref'],receipt['gate_ref'],receipt['evidence_refs'],
                    receipt['capture_binding'],claim.get('claimed_at'))
    if archive._canonical(claim)!=archive._canonical(expected):_fail('v2_claim_binding_mismatch')
    claimed=parser._utc(claim['claimed_at']);archive._gate_ready(gate,scope,claimed)
    if not parser._utc(scope['valid_from'])<=claimed<parser._utc(scope['valid_until']):_fail('v2_claim_window_mismatch')
    if receipt['request']!=claim['request']:_fail('v2_request_mismatch')
    descriptor,_=_authority(verification,child,scope,receipt['evidence_refs'],folder)
    _validate_response(verification,child,folder,receipt,scope,claimed)
    receipt['sha256']=supplied;receipt['verified_prefix_dependency']=descriptor
    return receipt


def _snapshot(verification,scope):
    """Synthetic producer's initial authority scan; not an input JSON capability."""
    child=verification._child('preclaim');binding=scope['journal_binding'];count=binding['prefix_length']
    if type(count) is not int or not 1<=count<=POLICY.prefix_events:_fail('v2_bounded_prefix_required')
    view=child.snapshot_prefix(scope['journal'],binding['activation_sha256'],count)
    descriptor=view.descriptor();originals=view.originals()
    if descriptor['prefix_canonical_tail_sha256']!=binding['prefix_sha256']:
        _fail('v2_scope_prefix_dependency_mismatch')
    activation=archive._decode(originals[0]['raw'])['payload']
    originals_refs={name:activation[name] for name in ('manifest','qualification')}
    raw={}
    def read(name,ref,*,decode=True):
        _keys(ref,('path','sha256'))
        if not Path(ref['path']).is_absolute():_fail('v2_absolute_frozen_authority_reference_required')
        value=child.read_bytes(_reference(verification.root,ref['path'],ref['sha256']))
        if len(value)>archive.MAX_DOCUMENT_BYTES:_fail('v2_ordinary_archive_file_budget_exceeded')
        raw[name]=value;originals_refs[name]=ref
        return archive._decode(value) if decode else value
    manifest=read('manifest',activation['manifest']);qualification=read('qualification',activation['qualification'])
    calendar=read('calendar',manifest['calendar']);warmup=read('warmup',manifest['warmup'])
    supporting=qualification['supporting_evidence']
    if not isinstance(supporting,list) or not 1<=len(supporting)<=v1.MAX_SUPPORTING:_fail('v2_support_budget_exceeded')
    for index,ref in enumerate(supporting):read(f'support_{index:03d}',ref,decode=False)
    decoded=dict(manifest=manifest,qualification=qualification,calendar=calendar,warmup=warmup,
                 _raw_hashes={name:archive._sha(value) for name,value in raw.items()},_supporting_count=len(supporting))
    if v1._validate_archived_authority(scope,decoded,originals,root=verification.root,context=view)!='synthetic':
        _fail('v2_only_synthetic_authority_is_implemented')
    child.propose(dict(status='synthetic_preclaim_originals',prefix=descriptor))
    return descriptor,raw,originals_refs

