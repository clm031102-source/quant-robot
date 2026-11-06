"""Rebuild paper inputs from originals before using them in a frozen journal.

Profiles are reviewed application code, not a setting that a JSON file can
enable. The only shipped profile is synthetic. No production source is admitted
by this module. A future profile must supply all five independently reviewed
parsers and their transitive dependencies before it can enter the code registry.

Acquisition, candidate qualification and account execution remain separate.
This module performs no network requests, file writes or historical downloads.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_warmup_bundle as warmup
from quant_robot.ops.frozen_input_clocks import RECEIVED_BASIS
from quant_robot.ops import paper_evidence_session as sessions


PROFILE_ID = 'synthetic_bound_originals_v1'
CONTRACT_TYPE = 'original_bound_paper_source_v1'
PROOF_TYPE = 'original_bound_paper_input_v1'
DEFERRED_PROFILE_ID = 'synthetic_deferred_bound_originals_v1'


@dataclass(frozen=True)
class SourceProfile:
    """Application-owned provenance policy; not deserialized from user input."""
    adapters: Mapping[str, daily.SourceAdapter]
    dependencies: Mapping[str, tuple]
    lineage: str


_FIXTURES = MappingProxyType(dict(warmup.DEFAULT_ADAPTERS))
# Warmup fixture readers also satisfy the daily assembler's Evidence interface.
# Using one explicit registry keeps every parser and dependency frozen together.
PROFILES = MappingProxyType({PROFILE_ID: SourceProfile(
    _FIXTURES, MappingProxyType({key: () for key in _FIXTURES}), 'synthetic_only')})

# Deliberately outside PROFILES: frozen G1/default callers cannot select this
# pending-result protocol simply by changing a JSON profile string.
_DEFERRED_PROFILE = SourceProfile(daily.SYNTHETIC_DEFERRED_ADAPTERS,
    MappingProxyType({key:() for key in daily.SYNTHETIC_DEFERRED_ADAPTERS}),'synthetic_only')


class _DeferredInput:
    def __init__(self,stage,manifest_ref,schedule_ref,*,daily_input):
        self.assembly=daily._DeferredAssembly(stage)
        self.context=self.assembly.context('spec')
        self.manifest=self.context.read_json(manifest_ref)
        self.schedule=self.context.read_json(schedule_ref)
        # Spec + manifest + frozen schedule share the daily price reader's
        # unchanged 128/16 MB cap. This is one input responsibility, not an
        # extra child per day or a renewed budget after failure.
        if daily_input:self.assembly._reuse['price']=self.context

    def runtime(self):
        return dict(profile_id=DEFERRED_PROFILE_ID,lineage='synthetic_only',
                    assembler_binding=self.assembly.binding())

    def validate(self,manifest):
        source=manifest.get('source_contract',{});binding=source.get('originals_binding',{})
        if (set(binding)!={'artifact_type','profile_id','runtime'}
                or binding['artifact_type']!=CONTRACT_TYPE
                or binding['profile_id']!=DEFERRED_PROFILE_ID
                or source.get('timestamp_basis')!=RECEIVED_BASIS
                or daily._canonical(binding['runtime'])!=daily._canonical(self.runtime())):
            raise ValueError('Exact synthetic deferred source contract required')

    def input_context(self,manifest,proof,*,require_recorded):
        if require_recorded:raise ValueError('Synthetic deferred profile cannot certify forward')
        self.validate(manifest)
        daily._keys(proof,('artifact_type','evidence_root','specification'))
        if (proof['artifact_type']!=PROOF_TYPE or not isinstance(proof['evidence_root'],str)
                or not Path(proof['evidence_root']).is_absolute()
                or Path(proof['evidence_root']).resolve(strict=True)!=self.assembly.stage.root):
            raise ValueError('Deferred proof must share the operation evidence root')
        return _DEFERRED_PROFILE,self.runtime(),self.context.read_json(proof['specification']),self.context

    def finish(self,manifest,context,before):
        context.recheck();self.validate(manifest)
        if daily._canonical(before)!=daily._canonical(self.runtime()):
            raise ValueError('Deferred source binding changed')
        # Actual original/code re-reads are owned by the enclosing commit.
        # No successful public payload is returned by this preparation step.


class SyntheticSourceVerification:
    """One explicit synthetic top-level stage for many warmup/daily inputs.

    All input methods return opaque tickets, including verify methods. Closing
    without commit or any preparation failure poisons the owning operation.
    No G1 journal, writer lock, gate, capture or filesystem publication is run.
    """
    def __init__(self,evidence_root,*,operation=None):
        self.root=Path(evidence_root).resolve(strict=True)
        if operation is not None and (type(operation) is not sessions.EvidenceOperation
                or operation.root!=self.root or operation._policy is not sessions.SYNTHETIC_POLICY):
            raise ValueError('Exact shared synthetic operation required')
        self.operation=operation or sessions.EvidenceOperation(self.root)
        self._owned=operation is None;self.stage=None

    def __enter__(self):
        self.stage=self.operation.stage();return self

    def __exit__(self,kind,value,traceback):
        if self.stage is not None:self.stage.__exit__(kind,value,traceback)
        if self._owned:self.operation.close()
        return False

    def runtime_binding(self):
        """Preparation metadata only; not verified evidence or admission."""
        try:
            assembly=daily._DeferredAssembly(self.stage)
            return dict(profile_id=DEFERRED_PROFILE_ID,lineage='synthetic_only',
                        assembler_binding=assembly.binding())
        except BaseException:
            self.stage.abort();raise

    def source_contract(self,source_id,*,maximum_receive_delay_seconds=86400):
        return dict(source_id=source_id,maximum_receive_delay_seconds=maximum_receive_delay_seconds,
            timestamp_basis=RECEIVED_BASIS,originals_binding=dict(artifact_type=CONTRACT_TYPE,
                profile_id=DEFERRED_PROFILE_ID,runtime=self.runtime_binding()))

    def _prepare(self,kind,manifest_ref,proof,schedule_ref,now,acquired_at=None,expected=None,
                 require_recorded=False):
        self.stage.require_open()
        try:
            owner=_DeferredInput(self.stage,manifest_ref,schedule_ref,daily_input=kind=='daily')
            if kind=='daily':
                result=_build_daily_input(owner.manifest,proof,schedule=owner.schedule,now=now,
                    acquired_at=acquired_at,require_recorded=require_recorded,_deferred=owner)
            else:
                result=_build_warmup_input(owner.manifest,proof,schedule=owner.schedule,now=now,
                    require_recorded=require_recorded,_deferred=owner)
            if expected is not None and daily._canonical(expected)!=daily._canonical(result):
                raise ValueError('Deferred packet differs from rebuilt original evidence')
            return owner.assembly.propose(result)
        except BaseException:
            self.stage.abort();raise

    def prepare_daily_input(self,manifest_ref,proof,*,schedule_ref,acquired_at,now,require_recorded=False):
        return self._prepare('daily',manifest_ref,proof,schedule_ref,now,acquired_at,
                             require_recorded=require_recorded)

    def prepare_warmup_input(self,manifest_ref,proof,*,schedule_ref,now,require_recorded=False):
        return self._prepare('warmup',manifest_ref,proof,schedule_ref,now,require_recorded=require_recorded)

    def verify_daily_input(self,manifest_ref,payload,*,schedule_ref,now):
        try:
            if not isinstance(payload,dict):raise ValueError('Deferred packet object required')
            return self._prepare('daily',manifest_ref,payload.get('source_proof'),schedule_ref,now,
                                 payload.get('acquired_at'),expected=payload)
        except BaseException:
            self.stage.abort();raise

    def verify_warmup_input(self,manifest_ref,payload,*,schedule_ref,now):
        try:
            if not isinstance(payload,dict):raise ValueError('Deferred packet object required')
            return self._prepare('warmup',manifest_ref,payload.get('source_proof'),schedule_ref,now,expected=payload)
        except BaseException:
            self.stage.abort();raise

    def commit(self):return self.stage.commit()


def _profile(profile_id, *, require_recorded=False):
    profile = PROFILES.get(profile_id)
    if not isinstance(profile, SourceProfile):
        raise ValueError('verified_raw_source_adapter_missing: reviewed code profile required')
    if (profile.lineage not in ('synthetic_only', 'recorded_observation')
            or {adapter.component for adapter in profile.adapters.values()} != set(daily.COMPONENTS)):
        raise ValueError('Complete reviewed five-component source profile required')
    if require_recorded and profile.lineage != 'recorded_observation':
        raise ValueError('verified_raw_source_adapter_missing: synthetic profile cannot certify forward')
    return profile


def runtime_binding(profile_id=PROFILE_ID):
    profile = _profile(profile_id)
    return dict(profile_id=profile_id, lineage=profile.lineage,
        connection_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        assembler_binding=warmup.runtime_binding(adapters=profile.adapters,
                                                adapter_dependencies=profile.dependencies))


def validate_contract(manifest, *, require_recorded=False):
    source = manifest.get('source_contract', {})
    binding = source.get('originals_binding')
    if not isinstance(binding, dict) or set(binding) != {'artifact_type', 'profile_id', 'runtime'}:
        raise ValueError('verified_raw_source_adapter_missing: original-bound source contract required')
    if binding['artifact_type'] != CONTRACT_TYPE or source.get('timestamp_basis') != RECEIVED_BASIS:
        raise ValueError('Original receipts require the observed-originals clock basis')
    profile = _profile(binding['profile_id'], require_recorded=require_recorded)
    if daily._canonical(binding['runtime']) != daily._canonical(runtime_binding(binding['profile_id'])):
        raise ValueError('Source profile code, dependencies or parameters changed')
    return profile


def source_contract(source_id, *, profile_id=PROFILE_ID, maximum_receive_delay_seconds=86400):
    """Prepare an explicit contract for review; this grants no qualification."""
    return dict(source_id=source_id, maximum_receive_delay_seconds=maximum_receive_delay_seconds,
        timestamp_basis=RECEIVED_BASIS, originals_binding=dict(artifact_type=CONTRACT_TYPE,
            profile_id=profile_id, runtime=runtime_binding(profile_id)))


def _read_proof(proof):
    daily._keys(proof, ('artifact_type', 'evidence_root', 'specification'))
    if proof['artifact_type'] != PROOF_TYPE or not isinstance(proof['evidence_root'], str):
        raise ValueError('Explicit original-bound input proof required')
    root = Path(proof['evidence_root'])
    if not root.is_absolute():
        raise ValueError('Absolute evidence root required')
    context = daily.EvidenceContext(root)
    spec = context.read_json(proof['specification'])
    return spec, context


def proof_reference(evidence_root, relative_specification):
    """Reference an existing bounded spec; never imports callbacks or sources."""
    root = Path(evidence_root).resolve(strict=True)
    context = daily.EvidenceContext(root)
    path = context.path_for(dict(path=relative_specification, sha256='0'*64))
    with path.open('rb') as stream:
        raw = stream.read(daily.MAX_DOCUMENT_BYTES+1)
    if len(raw) > daily.MAX_DOCUMENT_BYTES:
        raise ValueError('Source specification exceeds document byte budget')
    ref = dict(path=relative_specification, sha256=sha256(raw).hexdigest())
    proof = dict(artifact_type=PROOF_TYPE, evidence_root=str(root), specification=ref)
    _read_proof(proof)
    return proof


def _lineage(bundle, profile, *, require_recorded):
    if bundle.get('input_contract_complete') is not True:
        codes = [entry['code'] for entry in bundle.get('blockers', [])]
        raise ValueError('Original input contract incomplete: ' + ', '.join(codes))
    if bundle.get('evidence_class') != profile.lineage:
        raise ValueError('Original evidence lineage does not match reviewed source profile')
    if require_recorded and bundle['evidence_class'] != 'recorded_observation':
        raise ValueError('Synthetic original evidence cannot count as forward')


def _finish(manifest, context, before, *, require_recorded):
    context.recheck()
    validate_contract(manifest, require_recorded=require_recorded)
    after = runtime_binding(before['profile_id'])
    if daily._canonical(before) != daily._canonical(after):
        raise ValueError('Source implementation changed during reconstruction')


def build_warmup_input(manifest, proof, *, schedule, now, require_recorded=False):
    return _build_warmup_input(manifest,proof,schedule=schedule,now=now,require_recorded=require_recorded)


def _build_warmup_input(manifest, proof, *, schedule, now, require_recorded=False,_deferred=None):
    """Reconstruct the entire current-as-of prefix, including later-known notices.

    `now` is supplied by the journal's host clock. The frozen as-of labels when
    this input snapshot was prepared, not when its older prices first existed.
    """
    if _deferred is None:
        profile = validate_contract(manifest, require_recorded=require_recorded)
        before = runtime_binding(manifest['source_contract']['originals_binding']['profile_id'])
        spec, context = _read_proof(proof)
    else:
        profile,before,spec,context = _deferred.input_context(manifest,proof,require_recorded=require_recorded)
    if (spec.get('asset_id') != manifest['asset_id']
            or spec.get('first_session') != manifest['first_session']
            or spec.get('components') != manifest['strategy']['components']):
        raise ValueError('Warmup spec differs from frozen candidate')
    if daily._instant(spec['as_of']) > now:
        raise ValueError('Warmup as-of is later than the actual journal clock')
    bundle = (warmup.build_warmup_bundle(spec, evidence_root=context.root,
        adapters=profile.adapters, adapter_dependencies=profile.dependencies) if _deferred is None
        else warmup._build_warmup_bundle(spec,evidence_root=context.root,
            adapters=profile.adapters,_deferred=_deferred.assembly))
    _lineage(bundle, profile, require_recorded=require_recorded)
    if bundle.get('warmup_ready') is not True or bundle['calendar'] != schedule:
        raise ValueError('Complete ready warmup and exact frozen calendar required')
    last = bundle['bars'][-1]['date']
    price = bundle['evidence'][last+'/price']
    result = dict(bars=bundle['bars'], actions=bundle['actions'], corporate_actions_complete=True,
        action_as_of_session=(daily._instant(spec['as_of'])+timedelta(hours=8)).date().isoformat(),
        generated_at=None, provider_first_publication_at=None,
        price_request_started_at=price['request_started_at'], price_received_at=price['received_at'],
        available_at=bundle['input_available_at'], acquired_at=spec['as_of'],
        source_proof=proof, source_bundle_sha256=bundle['sha256'])
    if _deferred is None:
        _finish(manifest, context, before, require_recorded=require_recorded)
    else:
        _deferred.finish(manifest,context,before)
        result.update(evidence_class='synthetic_only',deferred_profile=DEFERRED_PROFILE_ID,
                      production_admission=False,real_forward_days_added=0)
    return result


def verify_warmup_input(manifest, schedule, payload, *, now, require_recorded=False):
    expected = build_warmup_input(manifest, payload.get('source_proof'), schedule=schedule,
                                 now=now, require_recorded=require_recorded)
    if daily._canonical(payload) != daily._canonical(expected):
        raise ValueError('Warmup differs from rebuilt original evidence')
    return expected


def build_daily_input(manifest, proof, *, schedule, acquired_at, now, require_recorded=False):
    return _build_daily_input(manifest,proof,schedule=schedule,acquired_at=acquired_at,now=now,
                              require_recorded=require_recorded)


def _build_daily_input(manifest, proof, *, schedule, acquired_at, now, require_recorded=False,_deferred=None):
    """Build a final-bar packet known before the next frozen decision cutoff.

    This cannot authorize an earlier execution: observe() separately requires
    its already durable pre-open decision and enforces its receipt deadline.
    """
    if _deferred is None:
        profile = validate_contract(manifest, require_recorded=require_recorded)
        before = runtime_binding(manifest['source_contract']['originals_binding']['profile_id'])
        spec, context = _read_proof(proof)
    else:
        profile,before,spec,context = _deferred.input_context(manifest,proof,require_recorded=require_recorded)
    if (spec.get('asset_id') != manifest['asset_id']
            or spec.get('window_start') != schedule[0]['date']):
        raise ValueError('Daily original scope differs from frozen asset or prefix')
    if daily._instant(acquired_at) > now:
        raise ValueError('Daily import is later than the actual journal clock')
    bundle = (daily.build_source_bundle(spec, evidence_root=context.root,
        decision_at=acquired_at, adapters=profile.adapters) if _deferred is None
        else daily._build_source_bundle(spec,evidence_root=context.root,decision_at=acquired_at,
            adapters=profile.adapters,_deferred=_deferred.assembly))
    _lineage(bundle, profile, require_recorded=require_recorded)
    action_received_day = (daily._instant(bundle['evidence']['actions']['received_at'])
                           + timedelta(hours=8)).date().isoformat()
    if bundle['action_coverage']['coverage_end'] > action_received_day:
        raise ValueError('action_coverage_after_receipt_date')
    index = [row['date'] for row in schedule].index(bundle['session_date'])
    if (index + 1 >= len(schedule) or bundle['session'] != schedule[index]
            or bundle['next_session'] != schedule[index+1]):
        raise ValueError('Source session clocks differ from frozen calendar')
    price = bundle['evidence']['price']
    result = dict(session_date=bundle['session_date'], source_id=manifest['source_contract']['source_id'],
        generated_at=None, provider_first_publication_at=None,
        price_request_started_at=price['request_started_at'], price_received_at=price['received_at'],
        available_at=bundle['input_available_at'], acquired_at=acquired_at,
        bar=bundle['bar'], corporate_actions_complete=True,
        corporate_actions=bundle['corporate_actions'], source_proof=proof,
        source_bundle_sha256=bundle['sha256'])
    if _deferred is None:
        _finish(manifest, context, before, require_recorded=require_recorded)
    else:
        _deferred.finish(manifest,context,before)
        result.update(evidence_class='synthetic_only',deferred_profile=DEFERRED_PROFILE_ID,
                      production_admission=False,real_forward_days_added=0)
    return result


def verify_daily_input(manifest, schedule, payload, *, now, require_recorded=False):
    expected = build_daily_input(manifest, payload.get('source_proof'), schedule=schedule,
        acquired_at=payload.get('acquired_at'), now=now, require_recorded=require_recorded)
    if daily._canonical(payload) != daily._canonical(expected):
        raise ValueError('Daily packet differs from rebuilt original evidence')
    return expected
