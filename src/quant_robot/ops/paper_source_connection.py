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


PROFILE_ID = 'synthetic_bound_originals_v1'
CONTRACT_TYPE = 'original_bound_paper_source_v1'
PROOF_TYPE = 'original_bound_paper_input_v1'


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
    """Reconstruct the entire current-as-of prefix, including later-known notices.

    `now` is supplied by the journal's host clock. The frozen as-of labels when
    this input snapshot was prepared, not when its older prices first existed.
    """
    profile = validate_contract(manifest, require_recorded=require_recorded)
    before = runtime_binding(manifest['source_contract']['originals_binding']['profile_id'])
    spec, context = _read_proof(proof)
    if (spec.get('asset_id') != manifest['asset_id']
            or spec.get('first_session') != manifest['first_session']
            or spec.get('components') != manifest['strategy']['components']):
        raise ValueError('Warmup spec differs from frozen candidate')
    if daily._instant(spec['as_of']) > now:
        raise ValueError('Warmup as-of is later than the actual journal clock')
    bundle = warmup.build_warmup_bundle(spec, evidence_root=context.root,
        adapters=profile.adapters, adapter_dependencies=profile.dependencies)
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
    _finish(manifest, context, before, require_recorded=require_recorded)
    return result


def verify_warmup_input(manifest, schedule, payload, *, now, require_recorded=False):
    expected = build_warmup_input(manifest, payload.get('source_proof'), schedule=schedule,
                                 now=now, require_recorded=require_recorded)
    if daily._canonical(payload) != daily._canonical(expected):
        raise ValueError('Warmup differs from rebuilt original evidence')
    return expected


def build_daily_input(manifest, proof, *, schedule, acquired_at, now, require_recorded=False):
    """Build a final-bar packet known before the next frozen decision cutoff.

    This cannot authorize an earlier execution: observe() separately requires
    its already durable pre-open decision and enforces its receipt deadline.
    """
    profile = validate_contract(manifest, require_recorded=require_recorded)
    before = runtime_binding(manifest['source_contract']['originals_binding']['profile_id'])
    spec, context = _read_proof(proof)
    if (spec.get('asset_id') != manifest['asset_id']
            or spec.get('window_start') != schedule[0]['date']):
        raise ValueError('Daily original scope differs from frozen asset or prefix')
    if daily._instant(acquired_at) > now:
        raise ValueError('Daily import is later than the actual journal clock')
    bundle = daily.build_source_bundle(spec, evidence_root=context.root,
        decision_at=acquired_at, adapters=profile.adapters)
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
    _finish(manifest, context, before, require_recorded=require_recorded)
    return result


def verify_daily_input(manifest, schedule, payload, *, now, require_recorded=False):
    expected = build_daily_input(manifest, payload.get('source_proof'), schedule=schedule,
        acquired_at=payload.get('acquired_at'), now=now, require_recorded=require_recorded)
    if daily._canonical(payload) != daily._canonical(expected):
        raise ValueError('Daily packet differs from rebuilt original evidence')
    return expected
