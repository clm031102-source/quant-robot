"""Offline, current-as-of warmup originals for a later prospective decision.

This is NOT a sequence of historically timely daily source bundles. Actual
reception (including any later derivation) stays visible; no historical PIT,
source admission, candidate qualification or forward days are granted. The
entire explicitly chosen prefix seeds the existing feature implementation.

Defaults are fixtures only. Custom SourceAdapters and their dependency file
lists are trusted application code requiring review, never JSON callbacks.
Each adapter must verify provenance, raw unadjusted units, complete coverage,
and report received_at as the latest actual receipt/derivation it used. An
explicit dependency list must cover its transitive parsing/verifying code;
hashing a caller's list cannot prove that the declaration is exhaustive.
The spec freezes runtime_binding() before assembly; code, parameters and all
originals are rechecked afterwards. This module does no writes or networking.
"""
from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from importlib.metadata import version
import inspect
import json
import math
from pathlib import Path
import platform
import re
from typing import Mapping

from quant_robot.ops import paper_source_bundle as source
from quant_robot.ops.frozen_cash_actions import cash_action_snapshot
from quant_robot.research.full_position_factors import CATALOG, combined_state, feature_frame


SPEC_TYPE = 'paper_warmup_spec_v1'
BUNDLE_TYPE = 'paper_warmup_bundle_v1'
FIXTURE_TYPE = 'paper_warmup_synthetic_receipt_v1'
SEED_POLICY = 'entire_explicit_prefix_no_implicit_truncation_v1'
MAX_SESSIONS = 499  # The shared calendar validator bounds the full schedule to 500.
MAX_SPEC_BYTES = 1_000_000
MAX_PREFIX_DOCUMENTS = 8192
MAX_PREFIX_BYTES = 64_000_000
MAX_CODE_FILES = 128
MAX_CODE_BYTES = 16_000_000
MAX_BINDING_BYTES = 256_000
MIN_ACCOUNT_WARMUP = 21
CORE_FILES = (
    'ops/paper_warmup_bundle.py', 'ops/paper_source_bundle.py',
    'ops/frozen_cash_actions.py', 'research/full_position_factors.py',
    'research/indicator_combinations.py',
)


def _fixture(context, ref):
    receipt = context.read_json(ref)
    source._keys(receipt, ('artifact_type', 'component', 'raw',
                           'request_started_at', 'received_at'))
    if (receipt['artifact_type'] != FIXTURE_TYPE
            or receipt['component'] != context.component):
        raise source.BundleError('explicit_warmup_fixture_required')
    facts = context.read_json(receipt['raw'])
    if not isinstance(facts, dict):
        raise source.BundleError('source_facts_object_required')
    return source.Evidence(facts, receipt['request_started_at'],
                           receipt['received_at'], 'synthetic_only')


DEFAULT_ADAPTERS = {f'warmup_synthetic_{kind}_v1': source.SourceAdapter(kind, _fixture)
                    for kind in source.COMPONENTS}


def runtime_binding(*, adapters: Mapping[str, source.SourceAdapter] | None = None,
                    adapter_dependencies: Mapping[str, tuple] | None = None):
    """Snapshot reviewed application code; this helper grants no source authority.

    A custom registry must explicitly declare dependencies for every adapter,
    even when empty. Parameters are deep-copied so in-place changes cannot alter
    an already frozen snapshot. Dependency paths are application-controlled.
    """
    registry = dict(DEFAULT_ADAPTERS if adapters is None else adapters)
    if not 1 <= len(registry) <= 32 or any(
            not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', key)
            for key in registry):
        raise source.BundleError('bounded_code_registry_required')
    dependencies = ({key: () for key in registry}
                    if adapters is None and adapter_dependencies is None
                    else adapter_dependencies)
    if not isinstance(dependencies, Mapping) or set(dependencies) != set(registry):
        raise source.BundleError('explicit_adapter_dependencies_required')
    package = Path(__file__).resolve().parents[1]
    fingerprints, total = {}, 0

    def code_file(path):
        nonlocal total
        path = Path(path).resolve(strict=True)
        key = path.as_posix()
        if key not in fingerprints:
            if len(fingerprints) >= MAX_CODE_FILES:
                raise source.BundleError('code_document_budget_exceeded')
            with path.open('rb') as stream:
                raw = stream.read(source.MAX_DOCUMENT_BYTES + 1)
            if len(raw) > source.MAX_DOCUMENT_BYTES:
                raise source.BundleError('code_file_budget_exceeded')
            total += len(raw)
            if total > MAX_CODE_BYTES:
                raise source.BundleError('code_byte_budget_exceeded')
            fingerprints[key] = sha256(raw).hexdigest()
        return dict(path=key, sha256=fingerprints[key])

    core = {name: code_file(package/name) for name in CORE_FILES}
    bound = {}
    for name, adapter in sorted(registry.items()):
        if (not isinstance(adapter, source.SourceAdapter)
                or adapter.component not in source.COMPONENTS):
            raise source.BundleError('registered_code_adapter_required')
        files = dependencies[name]
        if not isinstance(files, (tuple, list)) or len(files) > MAX_CODE_FILES:
            raise source.BundleError('bounded_adapter_dependencies_required')
        # Adapter files and declared dependencies share the bounded code reader.
        origin = inspect.getsourcefile(adapter.parse)
        if origin is None:
            raise source.BundleError('adapter_implementation_file_required')
        origin_ref = code_file(origin)
        bound[name] = dict(component=adapter.component, module=adapter.parse.__module__,
                          function=adapter.parse.__qualname__, parameters=adapter.parameters,
                          implementation_sha256=origin_ref['sha256'],
                          dependencies=[code_file(path) for path in files])
    result = dict(core=core, adapters=bound, python=platform.python_version(),
                  packages={name:version(name) for name in ('numpy', 'pandas')})
    raw = source._canonical(result)
    if len(raw) > MAX_BINDING_BYTES:
        raise source.BundleError('implementation_binding_budget_exceeded')
    return json.loads(raw)


class _Ledger:
    def __init__(self):
        self.references = {}
        self.total_bytes = 0
        self.synthetic = False

    def record(self, context, ref, raw):
        key = context.path_for(ref).resolve().relative_to(context.root).as_posix()
        prior = self.references.get(key)
        if prior is not None and prior['sha256'] != ref['sha256']:
            raise source.BundleError('original_changed_across_prefix')
        if prior is None:
            if len(self.references) >= MAX_PREFIX_DOCUMENTS:
                raise source.BundleError('prefix_document_budget_exceeded')
            if self.total_bytes + len(raw) > MAX_PREFIX_BYTES:
                raise source.BundleError('prefix_byte_budget_exceeded')
            self.total_bytes += len(raw)
            self.references[key] = dict(path=key, sha256=ref['sha256'], bytes=len(raw))
        # Conservative explicit-marker taint also covers adapters using read_bytes.
        # Unmarked fabricated bytes still require trusted provenance verification.
        tainted = any(marker in raw for marker in (
                b'synthetic_only', b'SYNTHETIC_ONLY', b'_synthetic_',
                b'synthetic_test_only', b'synthetic_metadata_only',
                b'mock_transport_contract_test'))
        if tainted:
            self.synthetic = True
        return tainted


class _Context(source.EvidenceContext):
    """Keep the shared per-adapter limits and add a deduplicated prefix budget."""
    def __init__(self, root, *, component, ledger):
        super().__init__(root, component=component)
        self.ledger = ledger

    def read_bytes(self, ref):
        raw = super().read_bytes(ref)
        self.synthetic_seen |= self.ledger.record(self, ref, raw)
        return raw


def build_warmup_bundle(spec, *, evidence_root, adapters=None, adapter_dependencies=None):
    return _build_warmup_bundle(spec,evidence_root=evidence_root,adapters=adapters,
                                adapter_dependencies=adapter_dependencies)


def prepare_warmup_bundle(spec, *, session):
    """Stage an entire synthetic prefix; no ready bundle escapes before commit."""
    try:
        assembly=source._DeferredAssembly(session)
        result=_build_warmup_bundle(spec,evidence_root=session.root,
            adapters=source.SYNTHETIC_DEFERRED_ADAPTERS,_deferred=assembly)
        if result['input_contract_complete'] is not True:
            raise source.BundleError('deferred_warmup_incomplete:'+','.join(row['code'] for row in result['blockers']))
        return assembly.propose(result)
    except BaseException:
        session.abort();raise


def _build_warmup_bundle(spec, *, evidence_root, adapters=None, adapter_dependencies=None,_deferred=None):
    """Assemble complete originals as known now, without backdating old sessions.

    input_contract_complete describes evidence structure, not feature readiness.
    warmup_ready additionally requires the existing account minimum and all
    selected predicates known at the last prefix row. Neither is source admission.
    Calendar originals must enumerate every exchange session; their parser owns
    that source completeness proof. Dates are never inferred from weekdays here.
    """
    output = dict(artifact_type=BUNDLE_TYPE, status='blocked', input_contract_complete=False,
                  warmup_ready=False, source_admission_granted=False,
                  candidate_qualification_granted=False, historical_point_in_time_certified=False,
                  real_forward_eligible=False, real_forward_days_added=0, live_trading_allowed=False)
    ledger, contexts, evidence = _Ledger(), [], {}
    stage = 'spec'
    try:
        spec_bytes = source._canonical(spec)
        if len(spec_bytes) > MAX_SPEC_BYTES:
            raise source.BundleError('warmup_spec_byte_budget_exceeded')
        output['specification_sha256'] = sha256(spec_bytes).hexdigest()
        # Work from an immutable-value snapshot, not mutable caller dictionaries.
        original_spec = spec
        spec = json.loads(spec_bytes)
        source._keys(spec, ('artifact_type', 'asset_id', 'as_of', 'first_session',
            'seed_start', 'seed_policy', 'price_basis', 'components', 'sessions',
            'evidence', 'implementation_binding'))
        if (spec['artifact_type'] != SPEC_TYPE
                or re.fullmatch(r'CN_ETF_(XSHG|XSHE)_[0-9]{6}', spec['asset_id']) is None
                or spec['seed_policy'] != SEED_POLICY or spec['price_basis'] != 'raw_unadjusted'):
            raise source.BundleError('unsupported_warmup_contract')
        as_of = source._instant(spec['as_of'])
        as_of_day = (as_of + timedelta(hours=8)).date().isoformat()
        first, seed = source._day(spec['first_session']), source._day(spec['seed_start'])
        components = spec['components']
        if (not isinstance(components, list) or not 1 <= len(components) <= 3
                or any(not isinstance(c, str) or c not in CATALOG for c in components)
                or len(set(components)) != len(components)):
            raise source.BundleError('one_to_three_registered_predicates_required')
        rows = spec['sessions']
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_SESSIONS:
            raise source.BundleError('bounded_warmup_sessions_required')
        for row in rows:
            source._keys(row, ('session_date', 'price', 'execution'))
        labels = [source._day(row['session_date']) for row in rows]
        if labels != sorted(set(labels)) or labels[0] != seed or not labels[-1] < first:
            raise source.BundleError('unique_ordered_explicit_prefix_required')
        source._keys(spec['evidence'], ('calendar', 'identity', 'actions'))
        registry = dict(DEFAULT_ADAPTERS if adapters is None else adapters)
        before = (runtime_binding(adapters=adapters, adapter_dependencies=adapter_dependencies)
                  if _deferred is None else _deferred.binding())
        if source._canonical(before) != source._canonical(spec['implementation_binding']):
            raise source.BundleError('implementation_binding_mismatch')

        def parse(kind, entry, label):
            nonlocal stage
            stage = label
            source._keys(entry, ('adapter_id', 'receipt'))
            adapter = registry.get(entry['adapter_id'])
            if (not isinstance(adapter, source.SourceAdapter) and _deferred is None) or adapter is None or adapter.component != kind:
                raise source.BundleError('unsupported_component_adapter')
            context = (_Context(evidence_root, component=kind, ledger=ledger) if _deferred is None
                       else _deferred.context(kind,ledger))
            context.read_json(entry['receipt'])
            parsed = (adapter.parse(context, entry['receipt']) if _deferred is None
                      else _deferred.parse(adapter,context,entry['receipt']))
            if not isinstance(parsed, source.Evidence) or len(context.references) < 2:
                raise source.BundleError('parsed_original_evidence_required')
            if parsed.evidence_class not in ('recorded_observation', 'synthetic_only'):
                raise source.BundleError('explicit_evidence_lineage_required')
            received = source._instant(parsed.received_at)
            if received > as_of:
                raise source.BundleError('evidence_received_after_as_of')
            if kind == 'price' and parsed.request_started_at is None:
                raise source.BundleError('price_request_time_required')
            if (parsed.request_started_at is not None
                    and source._instant(parsed.request_started_at) > received):
                raise source.BundleError('request_after_receipt')
            if len(source._canonical(parsed.implementation_binding)) > MAX_BINDING_BYTES:
                raise source.BundleError('evidence_binding_budget_exceeded')
            lineage = ('synthetic_only' if context.synthetic_seen
                       or parsed.evidence_class == 'synthetic_only' else 'recorded_observation')
            ledger.synthetic |= lineage == 'synthetic_only'
            evidence[label] = dict(adapter_id=entry['adapter_id'], receipt=entry['receipt'],
                request_started_at=parsed.request_started_at, received_at=parsed.received_at,
                evidence_class=lineage, verifier_implementation=parsed.implementation_binding,
                originals=list(context.references.values()))
            contexts.append(context)
            return parsed

        calendar = parse('calendar', spec['evidence']['calendar'], 'calendar').facts
        current_spec = dict(asset_id=spec['asset_id'], session_date=labels[-1])
        pair = source._calendar(calendar, current_spec)
        dates = [row['date'] for row in calendar['sessions']]
        expected = [d for d in dates if seed <= d < first]
        if labels != expected or pair['next']['date'] != first:
            raise source.BundleError('calendar_prefix_missing_or_extra_session')
        if not (source._instant(pair['current']['daily_observation_not_before'])
                <= as_of < source._instant(pair['next']['decision_cutoff_at'])):
            raise source.BundleError('as_of_outside_pre_execution_window')
        schedule = {row['date']: row for row in calendar['sessions']}
        identity = source._identity(parse('identity', spec['evidence']['identity'], 'identity').facts,
            dict(asset_id=spec['asset_id'], session_date=as_of_day))
        if (identity['listing_date'] > seed or identity['valid_through'] < first
                or identity['delisting_date'] is not None and identity['delisting_date'] <= first):
            raise source.BundleError('identity_not_valid_for_prefix_and_first_session')
        parsed_actions = parse('actions', spec['evidence']['actions'], 'actions')
        actions = source._actions(parsed_actions.facts, dict(asset_id=spec['asset_id'],
            session_date=as_of_day, window_start=seed))
        known_on = (source._instant(parsed_actions.received_at)+timedelta(hours=8)).date().isoformat()
        if actions['coverage_end'] > known_on:
            raise source.BundleError('action_coverage_after_receipt_date')
        if any(event['announced_date'] > known_on for event in actions['events']):
            raise source.BundleError('notice_announcement_after_receipt_date')
        cash = cash_action_snapshot(actions['events'], asset=spec['asset_id'],
                                    sessions=dates, as_of_session=as_of_day, warmup=True)
        bars = []
        for row in rows:
            day = row['session_date']
            day_spec = dict(asset_id=spec['asset_id'], session_date=day)
            price = parse('price', row['price'], day+'/price')
            if source._instant(price.request_started_at) < source._instant(schedule[day]['daily_observation_not_before']):
                raise source.BundleError('price_requested_before_daily_observation_window')
            bar = source._price(price.facts, day_spec)
            execution = source._execution(parse('execution', row['execution'], day+'/execution').facts, day_spec)
            bounded = execution['limit_regime'] == 'bounded'
            if bounded and not (source._number(execution['down_limit']) <= source._number(bar['low'])
                    <= source._number(bar['high']) <= source._number(execution['up_limit'])):
                raise source.BundleError('OHLC_outside_verified_limits')
            bars.append(dict(bar, suspended=False,
                limit_up=bounded and source._number(bar['open']) == source._number(execution['up_limit']),
                limit_down=bounded and source._number(bar['open']) == source._number(execution['down_limit'])))

        stage = 'features'
        frame = feature_frame(bars, cash)
        last = frame.iloc[-1]
        unknown = [name for name in components if not math.isfinite(float(last[name]))]
        state = float(combined_state(frame, components)[-1])
        known = math.isfinite(state)
        feature_state = dict(known=known, desired=bool(state == 1) if known else None,
            unknown_components=unknown, by_component={name:(bool(last[name] == 1)
                if name not in unknown else None) for name in components})
        reasons = ([] if known else ['selected_predicate_undefined'])
        if len(bars) < MIN_ACCOUNT_WARMUP:
            reasons.append('fewer_than_twenty_one_account_warmup_sessions')
        stage = 'final_recheck'
        for context in contexts:
            context.recheck()
        after = (runtime_binding(adapters=adapters, adapter_dependencies=adapter_dependencies)
                 if _deferred is None else _deferred.binding())
        if source._canonical(before) != source._canonical(after):
            raise source.BundleError('implementation_changed_during_assembly')
        if source._canonical(original_spec) != spec_bytes:
            raise source.BundleError('spec_changed_during_assembly')
        prefix = dict(bars=bars, actions=cash, schedule=calendar['sessions'],
                      seed_start=seed, seed_end=labels[-1], seed_policy=SEED_POLICY,
                      as_of=spec['as_of'], first_session=first, components=components)
        output.update(status='input_contract_complete', input_contract_complete=True,
            warmup_ready=not reasons, readiness_reasons=reasons, feature_state=feature_state,
            evidence_class='synthetic_only' if ledger.synthetic else 'recorded_observation',
            as_of=spec['as_of'], first_session=first, first_session_clock=pair['next'],
            input_available_at=max((item['received_at'] for item in evidence.values()), key=source._instant),
            availability_basis='current_as_of_bound_originals_not_historical_reception',
            provider_generated_at=None, provider_first_publication_at=None,
            bars=bars, actions=cash, action_coverage={k:v for k,v in actions.items() if k != 'events'},
            calendar=calendar['sessions'], identity=identity,
            seed=dict(policy=SEED_POLICY, first_session=seed, last_session=labels[-1],
                      bars_used=len(bars), history_equivalence_claimed=False),
            prefix_sha256=sha256(source._canonical(prefix)).hexdigest(),
            input_sha256=sha256(source._canonical(dict(bars=bars, actions=cash))).hexdigest(),
            implementation_binding=before, evidence=evidence,
            originals=list(ledger.references.values()))
        output['blockers'] = []
    except source.BundleError as exc:
        output['blockers'] = [dict(component=stage, code=str(exc))]
    except (ValueError, TypeError, KeyError, OSError, OverflowError, AttributeError, IndexError):
        output['blockers'] = [dict(component=stage, code='invalid_warmup_input_or_evidence')]
    output['budget_used'] = dict(documents=len(ledger.references), bytes=ledger.total_bytes)
    output['budget_limits'] = dict(sessions=MAX_SESSIONS, documents=MAX_PREFIX_DOCUMENTS,
        total_bytes=MAX_PREFIX_BYTES, per_file_bytes=source.MAX_DOCUMENT_BYTES,
        per_adapter_documents=source.MAX_DOCUMENTS, per_adapter_bytes=source.MAX_TOTAL_BYTES)
    output['sha256'] = sha256(source._canonical(output)).hexdigest()
    return output
