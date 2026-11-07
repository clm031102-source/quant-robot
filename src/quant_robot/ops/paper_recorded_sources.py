"""Bounded connection framework; the sole available parser set is explicitly offline.

Production construction stops at the missing reviewed 518880 profile. No JSON
can select a parser, clear fixture lineage, or expand an existing reader budget.
"""
from types import MappingProxyType

from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_recorded_518880_profile as profile
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import paper_warmup_bundle as warmup


_OFFLINE_ADAPTERS = MappingProxyType({
    **{f'warmup_synthetic_{kind}_v1': daily.DeferredSourceAdapter(kind, 'warmup_fixture')
       for kind in daily.COMPONENTS},
    'synthetic_recorded_connection_price_v1': daily.DeferredSourceAdapter('price', 'recorded_connection_fixture'),
})
_OFFLINE_PROFILE = connection.SourceProfile(_OFFLINE_ADAPTERS,
    MappingProxyType({key: () for key in _OFFLINE_ADAPTERS}), 'synthetic_only')


def _check_stage(stage):
    if type(stage) is not sessions.VerificationSession or stage.policy is not sessions.G1_RECORDED_POLICY:
        raise ValueError('exact_recorded_framework_stage_required')
    stage.require_open()


def _profile(offline):
    if type(offline) is not bool:
        raise ValueError('fixed_framework_mode_required')
    return _OFFLINE_PROFILE if offline else profile.reviewed_profile_518880()


class _RecordedAssembly:
    def __init__(self, stage, *, _offline=False):
        _check_stage(stage)
        try:
            self.profile = _profile(_offline)
        except BaseException:
            stage.abort()
            raise
        self.offline = _offline
        self.stage = stage
        self.catalog = stage.bind_implementation(sessions.RECORDED_CATALOG)
        self.contexts = []
        self._reuse = {}

    def context(self, kind, ledger=None):
        if kind in self._reuse:
            value = self._reuse.pop(kind)
            if ledger is not None:
                raise ValueError('framework_context_ledger_cannot_be_reassigned')
            value.component = kind
        else:
            value = daily._DeferredContext(self, kind, ledger)
        self.contexts.append(value)
        return value

    def adapter(self, adapter, kind):
        if (not any(adapter is value for value in self.profile.adapters.values())
                or adapter.component != kind):
            raise ValueError('fixed_framework_adapter_required')
        return dict(component=kind, parser_id=adapter.parser_id, lineage=self.profile.lineage,
                    implementation_binding=self.binding())

    def parse(self, adapter, context, ref):
        self.adapter(adapter, context.component)
        if adapter.parser_id == 'warmup_fixture':
            return warmup._fixture(context, ref)
        from quant_robot.ops import paper_prospective_recorded_transport as transport
        return transport._parse_for_deferred(context, ref)

    def binding(self):
        from quant_robot.research.full_position_factors import np, pd
        import platform
        return dict(protocol='synthetic_recorded_connection_sources_v1', source=self.catalog,
            adapters={key: dict(component=value.component, parser_id=value.parser_id)
                      for key, value in self.profile.adapters.items()},
            python=platform.python_version(), packages=dict(numpy=np.__version__, pandas=pd.__version__),
            production_admission=False)

    def propose(self, value):
        self.stage.require_open()
        if not self.contexts:
            self.stage.fail('framework_originals_required')
        return self.contexts[-1].child.propose(value)


class _RecordedInput:
    def __init__(self, stage, manifest_ref, schedule_ref, *, daily_input, _offline=False):
        self.assembly = _RecordedAssembly(stage, _offline=_offline)
        self.context = self.assembly.context('spec')
        self.manifest = self.context.read_json(manifest_ref)
        self.schedule = self.context.read_json(schedule_ref)
        if self.manifest.get('asset_id') != profile.ASSET_ID:
            raise ValueError('framework_requires_exact_518880_identity')
        if daily_input:
            self.assembly._reuse['price'] = self.context

    def runtime(self):
        return dict(profile_id=profile.OFFLINE_PROFILE_ID, lineage='synthetic_only',
                    assembler_binding=self.assembly.binding())

    def validate(self, manifest):
        source = manifest.get('source_contract', {})
        expected = dict(artifact_type=connection.CONTRACT_TYPE,
            profile_id=profile.OFFLINE_PROFILE_ID, runtime=self.runtime())
        if (source.get('timestamp_basis') != connection.RECEIVED_BASIS
                or daily._canonical(source.get('originals_binding')) != daily._canonical(expected)):
            raise ValueError('exact_offline_framework_contract_required')

    def input_context(self, manifest, proof, *, require_recorded):
        if require_recorded:
            raise ValueError('offline_framework_cannot_certify_recorded_sources')
        self.validate(manifest)
        daily._keys(proof, ('artifact_type', 'evidence_root', 'specification'))
        from pathlib import Path
        if (proof['artifact_type'] != connection.PROOF_TYPE
                or not isinstance(proof['evidence_root'], str)
                or not Path(proof['evidence_root']).is_absolute()
                or Path(proof['evidence_root']).resolve(strict=True) != self.assembly.stage.root):
            raise ValueError('framework_proof_must_share_root')
        return self.assembly.profile, self.runtime(), self.context.read_json(proof['specification']), self.context

    def finish(self, manifest, context, before):
        context.recheck()
        self.validate(manifest)
        if daily._canonical(before) != daily._canonical(self.runtime()):
            raise ValueError('framework_binding_changed')

    def build(self, kind, proof, *, now, acquired_at=None, require_recorded=False):
        if kind == 'daily':
            value = connection._build_daily_input(self.manifest, proof, schedule=self.schedule,
                acquired_at=acquired_at, now=now, require_recorded=require_recorded, _deferred=self)
        elif kind == 'warmup':
            value = connection._build_warmup_input(self.manifest, proof, schedule=self.schedule,
                now=now, require_recorded=require_recorded, _deferred=self)
        else:
            raise ValueError('fixed_framework_input_kind_required')
        # The reused builder has independently rejected recorded admission. This
        # changes only the explicit offline protocol ID, never evidence lineage.
        if value.get('evidence_class') != 'synthetic_only' or not self.assembly.offline:
            raise ValueError('framework_result_must_remain_offline')
        value['deferred_profile'] = profile.OFFLINE_PROFILE_ID
        return value


class RecordedSourceVerification:
    """Borrow an exact root stage; public production construction remains unavailable."""
    @classmethod
    def from_stage(cls, stage, *, _offline=False):
        _check_stage(stage)
        try:
            _profile(_offline)
        except BaseException:
            stage.abort()
            raise
        result = object.__new__(cls)
        result.stage, result.offline = stage, _offline
        return result

    def runtime_binding(self):
        assembly = _RecordedAssembly(self.stage, _offline=self.offline)
        return dict(profile_id=profile.OFFLINE_PROFILE_ID, lineage='synthetic_only',
                    assembler_binding=assembly.binding())

    def source_contract(self, source_id, *, maximum_receive_delay_seconds=86400):
        return dict(source_id=source_id, maximum_receive_delay_seconds=maximum_receive_delay_seconds,
            timestamp_basis=connection.RECEIVED_BASIS, originals_binding=dict(
                artifact_type=connection.CONTRACT_TYPE, profile_id=profile.OFFLINE_PROFILE_ID,
                runtime=self.runtime_binding()))

    def _prepare(self, kind, manifest_ref, proof, *, schedule_ref, now, acquired_at=None,
                 require_recorded=False, expected=None):
        try:
            owner = _RecordedInput(self.stage, manifest_ref, schedule_ref,
                                   daily_input=kind == 'daily', _offline=self.offline)
            value = owner.build(kind, proof, now=now, acquired_at=acquired_at, require_recorded=require_recorded)
            if expected is not None and daily._canonical(value) != daily._canonical(expected):
                raise ValueError('framework_packet_differs_from_originals')
            return owner.assembly.propose(value)
        except BaseException:
            self.stage.abort()
            raise

    def prepare_warmup_input(self, manifest_ref, proof, *, schedule_ref, now, require_recorded=False):
        return self._prepare('warmup', manifest_ref, proof, schedule_ref=schedule_ref, now=now,
                             require_recorded=require_recorded)

    def prepare_daily_input(self, manifest_ref, proof, *, schedule_ref, acquired_at, now, require_recorded=False):
        return self._prepare('daily', manifest_ref, proof, schedule_ref=schedule_ref, now=now,
                             acquired_at=acquired_at, require_recorded=require_recorded)

    def verify_warmup_input(self, manifest_ref, payload, *, schedule_ref, now):
        return self._prepare('warmup', manifest_ref, payload.get('source_proof'), schedule_ref=schedule_ref,
                             now=now, expected=payload)

    def verify_daily_input(self, manifest_ref, payload, *, schedule_ref, now):
        return self._prepare('daily', manifest_ref, payload.get('source_proof'), schedule_ref=schedule_ref,
                             now=now, acquired_at=payload.get('acquired_at'), expected=payload)
