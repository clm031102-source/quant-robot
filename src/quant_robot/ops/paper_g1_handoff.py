"""Private one-use bridge from source assembly to the existing G1 owner.

The forward module remains the call facade. Resolve it inside each function so
its exact owner type and runtime hooks remain shared without an import cycle.
No reader, callback, policy or owner can be selected by a source document.
"""
from __future__ import annotations

import json


def _check_source_handoff(owner,assembly,identity):
    """A private, one-use call edge, not a JSON-selected reader or callback."""
    from quant_robot.ops import frozen_candidate_forward as forward
    if type(owner) is not forward._SyntheticG1Action:
        raise ValueError('Exact G1 handoff owner required')
    if (type(assembly) is not forward.source_connection.daily._DeferredAssembly
            or assembly.stage is not owner.stage or owner.source.stage is not owner.stage
            or owner.operation._active is not owner.stage
            or owner.stage.policy is not forward.evidence_sessions.G1_SYNTHETIC_POLICY
            or owner.phase!='source' or owner.readonly or owner.guard is None):
        raise ValueError('Same open G1 source stage required for handoff')
    owner.stage.require_open()
    handoff=owner._source_handoff
    if handoff is None or handoff['stage'] is not owner.stage or handoff['consumed']:
        raise ValueError('Unused G1 source handoff required')
    if (not isinstance(identity,dict) or len(forward.canonical(identity))>16384
            or forward.canonical(identity)!=handoff['identity']):
        raise ValueError('Exact frozen G1 handoff identity required')
    if (owner.contract_reference!=(identity['manifest'],identity['qualification'])
            or len(owner.latest_events)!=identity['prefix_length']
            or owner.latest_events[-1]['sha256']!=identity['prefix_sha256']):
        raise ValueError('G1 handoff authority changed')


def _consume_source_handoff(owner,assembly,identity,packet,*,now):
    """Only the fixed source assembler calls this; no unfinished value escapes."""
    from quant_robot.ops import frozen_candidate_forward as forward
    forward._check_source_handoff(owner,assembly,identity)
    raw=forward.canonical(packet);handoff=owner._source_handoff;ticket=handoff.get('ticket')
    if (handoff.get('assembly') is not assembly or type(ticket) is not forward.evidence_sessions.PendingResult
            or ticket._stage_id!=owner.stage._id or forward.digest(packet)!=handoff.get('packet_sha256')):
        raise ValueError('Exact prepared G1 packet obligation required')
    if (len(raw)>owner.stage.policy.per_file_bytes or not isinstance(packet,dict)
            or packet.get('session_date')!=identity['session_date']
            or packet.get('source_id')!=identity['source_id']
            or packet.get('bar',{}).get('asset_id')!=identity['asset_id']):
        raise ValueError('G1 handoff packet identity differs from frozen authority')
    packet=json.loads(raw)
    # The builder has already reconstructed and validated these originals in
    # this stage. Register its obligation without reading a pending payload.
    owner.verified_sources[('daily',forward.digest(packet))]=(forward._clock(now)[0],ticket)
    owner._source_handoff['consumed']=True
    result=forward.observe(owner.directory,packet,now=now,_reader=owner)
    return owner.finish(result)


def _observe_synthetic_deferred_from_proof(directory,proof,*,evidence_root,acquired_at,now=None,operation=None):
    """P3-only artificial proof: same-stage source build and fixed G1 observe.

    No capture, gate, credentials or network. The caller supplies originals,
    never a packet, reader, stage, callback or policy. All returned data has
    passed the existing three-stage observation finalization.
    """
    from quant_robot.ops import frozen_candidate_forward as forward
    with forward._SyntheticG1Action(evidence_root,directory,operation=operation) as owner:
        return forward._observe_owned_synthetic_from_proof(owner,proof,acquired_at=acquired_at,now=now)


def _observe_owned_synthetic_from_proof(owner,proof,*,acquired_at,now):
    """Fixed continuation for a root that already owns its source stage/guard."""
    from quant_robot.ops import frozen_candidate_forward as forward
    if type(owner) is not forward._SyntheticG1Action or owner.phase!='source' or owner.readonly:
        raise ValueError('Existing synthetic G1 source owner required')
    owner.stage.require_open()
    if owner._source_handoff is not None:raise ValueError('Source handoff already started')
    directory=owner.directory
    if not isinstance(proof,dict) or len(forward.canonical(proof))>65536:
        raise ValueError('Bounded synthetic source proof required')
    proof=json.loads(forward.canonical(proof))
    events=owner.journal(directory)
    activation,manifest,_,schedule,_=forward._active(events,now=now,_reader=owner)
    _,observations,start,_=forward._prefix(events,manifest,schedule,_reader=owner)
    index=start+len(observations)
    if index+1>=len(schedule):raise ValueError('Pending session and next cutoff required')
    session=schedule[index]
    decisions=[e for e in events if e['kind']=='decision' and e['payload']['session_date']==session['date']]
    if len(decisions)!=1:raise ValueError('One durable pending decision required for handoff')
    decision=decisions[0]
    confirmed=forward._decision_receipt(events,decision,cutoff=forward.session_clocks(session,manifest['source_contract']['timestamp_basis'])['cutoff'])
    if confirmed is None:raise ValueError('Durable pending decision required for handoff')
    identity=dict(root=str(owner.root),journal=owner.relative,activation_sha256=events[0]['sha256'],
        manifest=activation['manifest'],qualification=activation['qualification'],calendar=manifest['calendar'],
        manifest_value_sha256=forward.digest(manifest),calendar_value_sha256=forward.digest(schedule),
        prefix_length=len(events),prefix_sha256=events[-1]['sha256'],decision_sha256=decision['sha256'],
        durability_sha256=confirmed['sha256'],session_date=session['date'],source_id=manifest['source_contract']['source_id'],
        asset_id=manifest['asset_id'])
    owner._source_handoff=dict(stage=owner.stage,identity=forward.canonical(identity),consumed=False)
    source=forward.source_connection._DeferredInput(owner.stage,owner.relative_ref(activation['manifest']),
        owner.relative_ref(manifest['calendar']),daily_input=True)
    return source.assembly._handoff_g1(owner,source,proof,identity=identity,acquired_at=acquired_at,now=now)

