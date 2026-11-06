"""Bound original evidence into a daily paper-input contract, without granting admission.

Adapters are trusted, reviewed Python code, never callbacks loaded from a spec.
They must verify their receipt provenance and parse referenced original data using
EvidenceContext. The assembler independently binds all consumed bytes and checks
identity, timing, coverage and economic field relationships. Hashes cannot prove
that a self-authored receipt came from an exchange. Default metadata adapters are
explicit fixtures; a production capture verifier registers its own SourceAdapter.
Neither complete input contracts nor recorded observations qualify a strategy or
open the forward gate. This module performs no network calls or filesystem writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import csv
from decimal import Decimal, Inexact, InvalidOperation, localcontext
from hashlib import sha256
import inspect
import io
import json
from pathlib import Path
import re
from typing import Callable, Mapping
from types import MappingProxyType

from quant_robot.ops import tushare_daily_receipt
from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact
from quant_robot.data.sources.tushare_calendar_contract import validate_calendar_records
from quant_robot.ops import paper_evidence_session as sessions


SPEC_TYPE = 'paper_source_bundle_spec_v1'
BUNDLE_TYPE = 'paper_source_bundle_v1'
FIXTURE_TYPE = 'paper_source_fixture_receipt_v1'
COMPONENTS = ('price', 'calendar', 'identity', 'execution', 'actions')
MAX_DOCUMENT_BYTES = 2_000_000
MAX_TOTAL_BYTES = 16_000_000
MAX_DOCUMENTS = 128
MAX_CASH_EVENTS = 1000
MAX_EVENT_ID_LENGTH = 200
MAX_CASH_DECIMAL_DIGITS = 40


class BundleError(ValueError):
    """A finite local diagnostic code, with no untrusted response text."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _keys(value, required, optional=()):
    if (not isinstance(value, dict) or not set(required) <= set(value)
            or not set(value) <= set(required) | set(optional)):
        raise BundleError('fields_missing_or_unsupported')


def _instant(value):
    if not isinstance(value, str) or not value.endswith('Z') or 'T' not in value:
        raise BundleError('explicit_UTC_time_required')
    try:
        result = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise BundleError('invalid_UTC_time') from exc
    if result.tzinfo is None or result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise BundleError('explicit_UTC_time_required')
    return result


def _day(value):
    if not isinstance(value, str):
        raise BundleError('ISO_session_date_required')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BundleError('ISO_session_date_required') from exc
    if parsed.isoformat() != value:
        raise BundleError('ISO_session_date_required')
    return value


def _number(value, *, positive=False):
    if type(value) not in (str, int, Decimal):
        raise BundleError('exact_decimal_required')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise BundleError('exact_decimal_required') from exc
    if (not number.is_finite() or number < 0 or positive and number == 0
            or len(number.as_tuple().digits) > 128
            or abs(number.as_tuple().exponent) > 128):
        raise BundleError('decimal_out_of_range')
    return number


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BundleError('duplicate_JSON_key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise BundleError('nonfinite_JSON_constant')


class EvidenceContext:
    """Constrained reader used by adapters; every consumed original is fingerprinted."""

    def __init__(self, root, *, component=None):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise BundleError('evidence_root_not_directory')
        self.references = {}
        self.synthetic_seen = False
        self.total_bytes = 0
        self.component = component

    def path_for(self, ref):
        _keys(ref, ('path', 'sha256'))
        if (not isinstance(ref['path'], str) or not ref['path']
                or Path(ref['path']).is_absolute()
                or not isinstance(ref['sha256'], str)
                or re.fullmatch(r'[0-9a-f]{64}', ref['sha256']) is None):
            raise BundleError('invalid_evidence_reference')
        path = self.root / ref['path']
        if not path.resolve().is_relative_to(self.root):
            raise BundleError('evidence_path_escapes_root')
        relative = path.relative_to(self.root)
        current = self.root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise BundleError('evidence_symlink_not_allowed')
        return path

    def read_bytes(self, ref):
        path = self.path_for(ref)
        with path.open('rb') as stream:
            raw = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(raw) > MAX_DOCUMENT_BYTES:
            raise BundleError('document_byte_budget_exceeded')
        digest = sha256(raw).hexdigest()
        if digest != ref['sha256']:
            raise BundleError('evidence_hash_mismatch')
        key = path.resolve().relative_to(self.root).as_posix()
        if key not in self.references:
            self.total_bytes += len(raw)
            if len(self.references) >= MAX_DOCUMENTS or self.total_bytes > MAX_TOTAL_BYTES:
                raise BundleError('evidence_budget_exceeded')
            self.references[key] = dict(path=key, sha256=digest, bytes=len(raw))
        elif self.references[key]['sha256'] != digest:
            raise BundleError('evidence_changed_during_assembly')
        return raw

    def read_json(self, ref):
        value = json.loads(self.read_bytes(ref), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
        if isinstance(value, dict) and (
                value.get('evidence_class') == 'synthetic_only'
                or value.get('artifact_type') == FIXTURE_TYPE
                or '_synthetic_' in str(value.get('artifact_type', ''))):
            self.synthetic_seen = True
        return value

    def recheck(self):
        for reference in tuple(self.references.values()):
            self.read_bytes({key: reference[key] for key in ('path', 'sha256')})


@dataclass(frozen=True)
class Evidence:
    facts: dict
    request_started_at: str | None
    received_at: str
    evidence_class: str
    implementation_binding: dict | None = None


@dataclass(frozen=True)
class SourceAdapter:
    component: str
    parse: Callable[[EvidenceContext, dict], Evidence]
    parameters: dict | None = None


@dataclass(frozen=True)
class DeferredSourceAdapter:
    """Code-owned parser identity; not compatible with immediate SourceAdapter."""
    component: str
    parser_id: str


SYNTHETIC_DEFERRED_ADAPTERS = MappingProxyType({
    **{f'warmup_synthetic_{kind}_v1':DeferredSourceAdapter(kind,'warmup_fixture') for kind in COMPONENTS},
    'synthetic_prospective_fund_daily_v2':DeferredSourceAdapter('price','prospective_v2'),
})


class _DeferredContext(EvidenceContext):
    """All content goes through a bounded child; recheck belongs to final commit."""
    def __init__(self,assembly,component,ledger=None):
        super().__init__(assembly.stage.root,component=component)
        self.child=assembly.stage.new_child('source');self.stage=assembly.stage;self.ledger=ledger

    def path_for(self,ref):
        _keys(ref,('path','sha256'))
        return self.stage.path_for(ref['path'])

    def read_bytes(self,ref):
        raw=self.child.read_bytes(ref)
        self.references={item['path']:item for item in self.child.references}
        self.total_bytes=sum(item['bytes'] for item in self.references.values())
        if self.ledger is not None:self.synthetic_seen |= self.ledger.record(self,ref,raw)
        return raw

    def prefix_view(self,descriptor):return self.child.prefix_view(descriptor)

    def recheck(self):return self.child.recheck()


class _DeferredAssembly:
    """Private preparation engine. Public entrypoints release only opaque tickets."""
    def __init__(self,stage):
        if type(stage) is not sessions.VerificationSession or stage.policy is not sessions.SYNTHETIC_POLICY:
            raise BundleError('exact_synthetic_session_required')
        stage.require_open();self.stage=stage
        self.catalog=stage.bind_implementation(sessions.SOURCE_CATALOG)
        # Bind the full supported parser graph, even if a batch uses fixtures only.
        self.v2_catalog=stage.bind_implementation(sessions.V2_CATALOG)
        self.contexts=[];self._reuse={}

    def context(self,kind,ledger=None):
        if kind in self._reuse:
            context=self._reuse.pop(kind);context.component=kind
            if ledger is not None:raise BundleError('deferred_ledger_context_cannot_be_reassigned')
            return context
        context=_DeferredContext(self,kind,ledger);self.contexts.append(context);return context

    def adapter(self,adapter,kind):
        if (not any(adapter is value for value in SYNTHETIC_DEFERRED_ADAPTERS.values())
                or adapter.component!=kind):raise BundleError('code_owned_deferred_adapter_required')
        return dict(component=kind,parser_id=adapter.parser_id,lineage='synthetic_only',
            implementation_binding=self.binding())

    def parse(self,adapter,context,ref):
        self.adapter(adapter,context.component)
        if adapter.parser_id=='warmup_fixture':
            from quant_robot.ops.paper_warmup_bundle import _fixture
            return _fixture(context,ref)
        from quant_robot.ops.paper_prospective_transport_v2 import _parse_for_deferred
        return _parse_for_deferred(context,ref)

    def binding(self):
        # Loaded package version attributes avoid importlib.metadata file reads.
        from quant_robot.research.full_position_factors import np, pd
        import platform
        return dict(protocol='synthetic_deferred_sources_v1',source=self.catalog,prospective=self.v2_catalog,
            adapters={key:dict(component=value.component,parser_id=value.parser_id)
                      for key,value in SYNTHETIC_DEFERRED_ADAPTERS.items()},
            python=platform.python_version(),packages=dict(numpy=np.__version__,pandas=pd.__version__),
            production_admission=False)

    def propose(self,value):
        self.stage.require_open()
        if not self.contexts:self.stage.fail('no_deferred_originals')
        return self.contexts[-1].child.propose(value)


def _adapter_binding(adapter):
    if not isinstance(adapter, SourceAdapter) or not callable(adapter.parse):
        raise BundleError('registered_code_adapter_required')
    source = inspect.getsourcefile(adapter.parse)
    if source is None or not Path(source).is_file():
        raise BundleError('adapter_implementation_file_required')
    _canonical(adapter.parameters)
    return dict(module=adapter.parse.__module__, function=adapter.parse.__qualname__,
                parameters=adapter.parameters,
                implementation_sha256=sha256(Path(source).read_bytes()).hexdigest())


def _price_fixture(context, ref):
    receipt = context.read_json(ref)
    if not isinstance(receipt, dict):
        raise BundleError('price_receipt_object_required')
    path = context.path_for(ref)
    # Consume and bind every original that the established verifier will read.
    for name in ('claim', 'response_body'):
        item = receipt.get(name)
        if not isinstance(item, dict) or set(item) != {'name', 'sha256'}:
            raise BundleError('price_original_reference_missing')
        if Path(item['name']).is_absolute():
            raise BundleError('invalid_relative_price_original')
        relative = (path.parent/item['name']).relative_to(context.root).as_posix()
        context.read_json(dict(path=relative, sha256=item['sha256']))
    verified = tushare_daily_receipt.verify_receipt(path)
    if not verified['status'].startswith('captured_'):
        raise BundleError('price_capture_not_successful')
    return Evidence(dict(bar=verified['parsed']['bar']), verified['request_started_at'],
                    verified['received_at'], 'synthetic_only',
                    _adapter_binding(SourceAdapter('price', tushare_daily_receipt.verify_receipt)))


def _price_live(context, ref):
    """Exact integration point for the separately reviewed scoped transport."""
    receipt = context.read_json(ref)
    path = context.path_for(ref)
    if not isinstance(receipt, dict) or receipt.get('artifact_type') != 'tushare_scoped_fund_daily_receipt_v1':
        raise BundleError('scoped_live_receipt_required')
    for name in ('raw_response', 'scope_ref', 'claim_ref', 'gate_ref'):
        item = receipt.get(name)
        if not isinstance(item, dict) or not {'path', 'sha256'} <= set(item):
            raise BundleError('live_price_original_reference_missing')
        if not isinstance(item['path'], str) or Path(item['path']).is_absolute():
            raise BundleError('invalid_relative_price_original')
        relative = (path.parent/item['path']).relative_to(context.root).as_posix()
        context.read_json(dict(path=relative, sha256=item['sha256']))
    evidence_refs = receipt.get('evidence_refs')
    if not isinstance(evidence_refs, dict) or not 1 <= len(evidence_refs) <= 32:
        raise BundleError('live_capture_supporting_originals_required')
    for item in evidence_refs.values():
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or Path(item['path']).is_absolute()):
            raise BundleError('invalid_relative_supporting_original')
        relative = (path.parent/item['path']).relative_to(context.root).as_posix()
        context.read_bytes(dict(path=relative, sha256=item['sha256']))
    try:
        from quant_robot.ops.tushare_live_transport import verify_scoped_source_receipt
    except ImportError as exc:
        raise BundleError('scoped_live_receipt_verifier_unavailable') from exc
    verified = verify_scoped_source_receipt(path)
    if verified.get('status') != 'source_observed_unqualified':
        raise BundleError('live_price_capture_not_successful')
    lineage = verified.get('evidence_class')
    if lineage not in ('live_source_observation', 'mock_transport_contract_test'):
        raise BundleError('unsupported_live_capture_lineage')
    return Evidence(dict(bar=verified['normalized_bar']), verified['request_started_at'],
        verified['received_at'], 'recorded_observation' if lineage == 'live_source_observation'
        else 'synthetic_only', _adapter_binding(SourceAdapter('price', verify_scoped_source_receipt)))


def _metadata_fixture(context, ref):
    receipt = context.read_json(ref)
    _keys(receipt, ('artifact_type', 'component', 'request_started_at', 'received_at', 'raw'))
    if (receipt['artifact_type'] != FIXTURE_TYPE or receipt['component'] not in COMPONENTS[1:]
            or receipt['component'] != context.component):
        raise BundleError('explicit_metadata_fixture_required')
    facts = context.read_json(receipt['raw'])
    if not isinstance(facts, dict):
        raise BundleError('source_facts_object_required')
    # This adapter cannot be upgraded to live by adding or changing JSON flags.
    return Evidence(facts, receipt['request_started_at'], receipt['received_at'], 'synthetic_only')


DEFAULT_ADAPTERS = {
    'tushare_synthetic_fund_daily_v1': SourceAdapter('price', _price_fixture),
    'tushare_scoped_fund_daily_v1': SourceAdapter('price', _price_live),
    **{f'synthetic_{kind}_evidence_v1': SourceAdapter(kind, _metadata_fixture)
       for kind in COMPONENTS[1:]},
}


def _metadata_utc(value):
    if not isinstance(value, str) or 'T' not in value:
        raise BundleError('metadata_UTC_time_required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise BundleError('metadata_UTC_time_required')
    return parsed.isoformat().replace('+00:00', 'Z')


def _metadata_ref(context, path, digest):
    path = Path(path)
    if path.is_absolute():
        path = path.relative_to(context.root)
    ref = dict(path=path.as_posix(), sha256=digest)
    context.path_for(ref)
    return ref


def published_calendar_adapter(*, exchange, reviewed_metadata_sha256):
    """Register an independently reviewed metadata fingerprint in application code.

    Not present in DEFAULT_ADAPTERS. A JSON spec cannot approve its own metadata.
    The reviewed hash pins the human interpretation of official rule originals;
    this reader additionally reconstructs open days from both raw calendars. It
    does not infer rule meaning from PDF bytes or treat a review flag as evidence.
    """
    if exchange not in ('XSHG', 'XSHE') or re.fullmatch(r'[0-9a-f]{64}', reviewed_metadata_sha256 or '') is None:
        raise BundleError('reviewed_calendar_binding_required')

    def parse(context, ref):
        if ref['sha256'] != reviewed_metadata_sha256:
            raise BundleError('calendar_not_the_reviewed_metadata_version')
        metadata = context.read_json(ref)
        if (not isinstance(metadata, dict) or metadata.get('artifact_type') != 'cn_etf_published_session_metadata_v1'
                or metadata.get('evidence_class') not in ('real_public_metadata_only', 'synthetic_metadata_only')
                or metadata.get('timezone') != 'Asia/Shanghai'):
            raise BundleError('unsupported_published_session_metadata')
        calendar_ref = _metadata_ref(context, metadata['calendar_path'], metadata['calendar_sha256'])
        manifest_ref = _metadata_ref(context, metadata['calendar_manifest_path'], metadata['calendar_manifest_sha256'])
        calendar_raw = context.read_bytes(calendar_ref)
        context.read_json(manifest_ref)
        manifest = validate_cn_trading_calendar_artifact(context.path_for(calendar_ref), context.path_for(manifest_ref))
        dates = [row['date'] for row in csv.DictReader(io.StringIO(calendar_raw.decode('utf-8-sig')))]
        if dates != sorted(set(dates)):
            raise BundleError('calendar_CSV_dates_not_unique_ordered')
        requested = manifest['requested_range']
        params = dict(start_date=requested['start'].replace('-', ''), end_date=requested['end'].replace('-', ''))
        sources = metadata['sources']
        if not isinstance(sources, list) or not 3 <= len(sources) <= 32:
            raise BundleError('calendar_original_sources_missing')
        exchanges, rules, received = set(), 0, []
        for item in sources:
            original = _metadata_ref(context, item['path'], item['sha256'])
            if item['kind'] == 'trade_cal':
                payload = context.read_json(original)
                if not isinstance(payload, dict) or type(payload.get('code')) is not int or payload['code'] != 0:
                    raise BundleError('calendar_provider_response_rejected')
                data = payload['data']
                fields = data['fields']
                if (set(fields) != {'exchange','cal_date','is_open','pretrade_date'} or len(fields) != 4
                        or not isinstance(data['items'], list) or data.get('has_more', False) is not False):
                    raise BundleError('calendar_original_fields_or_pagination_invalid')
                rows = []
                for values in data['items']:
                    if not isinstance(values, list) or len(values) != len(fields):
                        raise BundleError('calendar_original_row_shape_invalid')
                    rows.append(dict(zip(fields, values, strict=True)))
                source_exchange = item['exchange']
                if source_exchange not in ('SSE', 'SZSE') or source_exchange in exchanges:
                    raise BundleError('calendar_exchange_sources_incomplete')
                validate_calendar_records(rows, dict(params, exchange=source_exchange))
                opened = sorted(datetime.strptime(row['cal_date'], '%Y%m%d').date().isoformat()
                                for row in rows if str(row['is_open']) == '1')
                if opened != dates:
                    raise BundleError('raw_exchange_calendar_differs_from_CSV')
                exchanges.add(source_exchange)
            elif item['kind'] == 'official_rule_or_schedule':
                context.read_bytes(original)
                rules += 1
            else:
                raise BundleError('unknown_calendar_original_source_kind')
            received.append(_metadata_utc(item['received_at']))
        if exchanges != {'SSE','SZSE'} or not rules:
            raise BundleError('calendar_exchange_or_rule_sources_incomplete')
        first, last = _day(metadata['effective_from']), _day(metadata['effective_through'])
        if not requested['start'] <= first <= last <= requested['end']:
            raise BundleError('session_rule_window_outside_calendar')
        rows = metadata['session_rows']
        expected = [day for day in dates if first <= day <= last]
        if not isinstance(rows, list) or [row['date'] for row in rows] != expected:
            raise BundleError('derived_session_coverage_differs_from_original_calendar')
        sessions = []
        for index, row in enumerate(rows):
            if set(row['exchange_codes']) != {'SSE','SZSE'}:
                raise BundleError('session_exchange_identity_mismatch')
            expected_next = rows[index+1]['open_auction_start_utc'] if index+1 < len(rows) else None
            if row['next_session_open_utc'] != expected_next:
                raise BundleError('next_session_auction_cutoff_mismatch')
            sessions.append(dict(date=row['date'],
                decision_cutoff_at=_metadata_utc(row['open_auction_start_utc']),
                open_at=_metadata_utc(row['open_auction_end_utc']),
                auction_close_at=_metadata_utc(row['auction_close_utc']),
                daily_observation_not_before=_metadata_utc(row['daily_observation_not_before_utc'])))
        # The assembled metadata did not exist before its derivation completed.
        received.append(_metadata_utc(metadata['created_at']))
        context.recheck()
        return Evidence(dict(exchange=exchange, sessions=sessions), None,
            max(received, key=_instant), 'recorded_observation' if
            metadata['evidence_class']=='real_public_metadata_only' else 'synthetic_only')

    return SourceAdapter('calendar', parse, dict(exchange=exchange,
                         reviewed_metadata_sha256=reviewed_metadata_sha256))


def _price(facts, spec):
    _keys(facts, ('bar',))
    bar = facts['bar']
    fields = ('asset_id', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount')
    _keys(bar, fields, ('suspended', 'limit_up', 'limit_down'))
    if bar['asset_id'] != spec['asset_id'] or bar['date'] != spec['session_date']:
        raise BundleError('price_asset_or_session_mismatch')
    numbers = {key: _number(bar[key], positive=key in ('open', 'high', 'low', 'close'))
               for key in fields[2:]}
    if not (numbers['low'] <= min(numbers['open'], numbers['close'])
            <= max(numbers['open'], numbers['close']) <= numbers['high']):
        raise BundleError('inconsistent_OHLC')
    return dict(asset_id=bar['asset_id'], date=bar['date'],
                **{key: format(value, 'f') for key, value in numbers.items()})


def _calendar(facts, spec):
    _keys(facts, ('exchange', 'sessions'))
    if facts['exchange'] != spec['asset_id'].split('_')[2]:
        raise BundleError('calendar_exchange_mismatch')
    sessions = facts['sessions']
    if not isinstance(sessions, list) or not 2 <= len(sessions) <= 500:
        raise BundleError('bounded_session_calendar_required')
    labels, previous = [], None
    for item in sessions:
        _keys(item, ('date', 'decision_cutoff_at', 'open_at', 'auction_close_at',
                     'daily_observation_not_before'))
        labels.append(_day(item['date']))
        cutoff, opening, closing, final = (_instant(item[key]) for key in (
            'decision_cutoff_at', 'open_at', 'auction_close_at', 'daily_observation_not_before'))
        if any((instant + timedelta(hours=8)).date().isoformat() != item['date']
               for instant in (cutoff, opening, closing, final)):
            raise BundleError('session_clock_date_mismatch')
        if not cutoff <= opening < closing <= final or previous is not None and cutoff <= previous:
            raise BundleError('session_clock_order_invalid')
        previous = final
    if labels != sorted(set(labels)):
        raise BundleError('session_dates_not_unique_ordered')
    index = labels.index(spec['session_date'])
    if index + 1 >= len(labels):
        raise BundleError('next_session_missing')
    return dict(current=sessions[index], next=sessions[index+1])


def _identity(facts, spec):
    required = ('asset_id', 'instrument_type', 'currency', 'price_unit', 'volume_unit',
                'amount_unit', 'listing_date', 'delisting_date', 'valid_from', 'valid_through')
    _keys(facts, required)
    if (facts['asset_id'] != spec['asset_id'] or facts['instrument_type'] != 'ETF'
            or facts['currency'] != 'CNY' or facts['price_unit'] != 'CNY_per_fund_unit'
            or facts['volume_unit'] != 'fund_units' or facts['amount_unit'] != 'CNY'):
        raise BundleError('ETF_identity_or_units_mismatch')
    session = spec['session_date']
    if not _day(facts['listing_date']) <= session:
        raise BundleError('session_before_ETF_listing')
    if facts['delisting_date'] is not None and session >= _day(facts['delisting_date']):
        raise BundleError('session_on_or_after_ETF_delisting')
    if not _day(facts['valid_from']) <= session <= _day(facts['valid_through']):
        raise BundleError('identity_window_does_not_cover_session')
    return facts


def _execution(facts, spec):
    _keys(facts, ('asset_id', 'session_date', 'suspended', 'limit_regime', 'up_limit', 'down_limit'))
    if facts['asset_id'] != spec['asset_id'] or facts['session_date'] != spec['session_date']:
        raise BundleError('execution_asset_or_session_mismatch')
    if type(facts['suspended']) is not bool:
        raise BundleError('known_suspension_state_required')
    if facts['suspended']:
        raise BundleError('suspended_session_valuation_adapter_required')
    if facts['limit_regime'] == 'bounded':
        if not _number(facts['down_limit'], positive=True) < _number(facts['up_limit'], positive=True):
            raise BundleError('price_limit_order_invalid')
    elif facts['limit_regime'] != 'unbounded' or facts['up_limit'] is not None or facts['down_limit'] is not None:
        raise BundleError('known_price_limit_regime_required')
    return facts


def _actions(facts, spec):
    _keys(facts, ('asset_id', 'coverage_start', 'coverage_end', 'pages', 'notices'))
    if facts['asset_id'] != spec['asset_id']:
        raise BundleError('action_asset_mismatch')
    if not (_day(facts['coverage_start']) <= spec['window_start']
            <= spec['session_date'] <= _day(facts['coverage_end'])):
        raise BundleError('action_coverage_window_incomplete')
    pages, notices = facts['pages'], facts['notices']
    if not isinstance(pages, list) or not 1 <= len(pages) <= 32 or not isinstance(notices, list):
        raise BundleError('bounded_action_index_required')
    if len(notices) > MAX_CASH_EVENTS:
        raise BundleError('action_event_count_exceeds_account_limit')
    indexed = []
    total = None
    for number, page in enumerate(pages, 1):
        _keys(page, ('page_number', 'total_pages', 'total_records', 'records'))
        if (any(type(page[key]) is not int for key in ('page_number', 'total_pages', 'total_records'))
                or page['page_number'] != number or page['total_pages'] != len(pages)
                or not isinstance(page['records'], list) or page['total_records'] < 0):
            raise BundleError('action_index_page_coverage_incomplete')
        if total is not None and total != page['total_records']:
            raise BundleError('action_index_totals_conflict')
        total = page['total_records']
        if total > MAX_CASH_EVENTS or len(indexed) + len(page['records']) > MAX_CASH_EVENTS:
            raise BundleError('action_event_count_exceeds_account_limit')
        for record in page['records']:
            _keys(record, ('event_id', 'kind'))
            if record['kind'] != 'cash_dividend':
                raise BundleError('unsupported_share_conversion_or_action')
            if (not isinstance(record['event_id'], str) or not record['event_id']
                    or len(record['event_id']) > MAX_EVENT_ID_LENGTH):
                raise BundleError('action_identity_required')
            indexed.append(record['event_id'])
    if total != len(indexed) or len(set(indexed)) != len(indexed):
        raise BundleError('action_index_count_or_identity_mismatch')
    events, seen, economic = [], set(), set()
    for notice in notices:
        _keys(notice, ('event_id', 'asset_id', 'kind', 'announced_date', 'record_date',
                      'ex_date', 'pay_date', 'cash_amount', 'per_units', 'share_multiplier', 'cash_basis'))
        if notice['kind'] != 'cash_dividend' or _number(notice['share_multiplier'], positive=True) != 1:
            raise BundleError('unsupported_share_conversion_or_action')
        identity = notice['event_id']
        if (not isinstance(identity, str) or identity not in indexed or identity in seen
                or notice['asset_id'] != spec['asset_id']):
            raise BundleError('notice_not_unique_or_not_in_complete_index')
        dates = {key: _day(notice[key]) for key in ('announced_date', 'record_date', 'ex_date', 'pay_date')}
        if not dates['announced_date'] <= dates['record_date'] < dates['ex_date'] <= dates['pay_date']:
            raise BundleError('cash_action_chronology_invalid')
        if dates['announced_date'] > facts['coverage_end']:
            raise BundleError('notice_outside_covered_publication_window')
        if dates['announced_date'] > spec['session_date']:
            raise BundleError('notice_announced_after_session')
        if notice['cash_basis'] != 'net':
            raise BundleError('net_cash_basis_required_for_account')
        try:
            with localcontext() as context:
                context.prec = 256
                context.traps[Inexact] = True
                cash = _number(notice['cash_amount'], positive=True) / _number(notice['per_units'], positive=True)
        except Inexact as exc:
            raise BundleError('nonterminating_cash_per_unit') from exc
        # Validate the exact emitted string, which the consumer reparses. A
        # compact 1E+40 has one coefficient digit but emits 41 fixed-point digits.
        cash_text = format(cash, 'f')
        emitted = Decimal(cash_text)
        if (len(cash_text) > 80 or len(emitted.as_tuple().digits) > MAX_CASH_DECIMAL_DIGITS
                or abs(emitted.as_tuple().exponent) > MAX_CASH_DECIMAL_DIGITS):
            raise BundleError('cash_per_unit_exceeds_account_precision')
        key = (dates['record_date'], dates['ex_date'], dates['pay_date'], cash)
        if key in economic:
            raise BundleError('duplicate_economic_cash_action')
        seen.add(identity); economic.add(key)
        events.append(dict(event_id=identity, asset_id=spec['asset_id'], kind='cash_dividend',
                           **dates, cash_per_unit=cash_text, share_multiplier='1', cash_basis='net'))
    if seen != set(indexed):
        raise BundleError('indexed_action_notice_missing')
    return dict(coverage_start=facts['coverage_start'], coverage_end=facts['coverage_end'],
                indexed_events=len(indexed), events=sorted(events, key=lambda row: (row['ex_date'], row['event_id'])))


_VALIDATORS = dict(price=_price, calendar=_calendar, identity=_identity,
                   execution=_execution, actions=_actions)


def build_source_bundle(spec, *, evidence_root, decision_at, adapters: Mapping[str, SourceAdapter] | None = None):
    return _build_source_bundle(spec,evidence_root=evidence_root,decision_at=decision_at,adapters=adapters)


def prepare_source_bundle(spec, *, session, decision_at):
    """Explicit synthetic path: only commit().result(ticket) exposes the bundle."""
    try:
        assembly=_DeferredAssembly(session)
        result=_build_source_bundle(json.loads(_canonical(spec)),evidence_root=session.root,
            decision_at=decision_at,adapters=SYNTHETIC_DEFERRED_ADAPTERS,_deferred=assembly)
        if result['input_contract_complete'] is not True:
            raise BundleError('deferred_bundle_incomplete:'+','.join(row['code'] for row in result['blockers']))
        return assembly.propose(result)
    except BaseException:
        session.abort();raise


def _build_source_bundle(spec, *, evidence_root, decision_at, adapters=None, _deferred=None):
    """Assemble evidence for the *next* decision; never certifies an earlier order.

    A custom registry is executable application code requiring independent review.
    It is not an input-file escape hatch: booleans, unbound parser code, parsers
    that consume no original bytes, and unsupported fact schemas are rejected.
    Production adapters must validate capture provenance before returning Evidence.
    """
    blockers, results, validations, contexts = [], {}, {}, []
    output = dict(artifact_type=BUNDLE_TYPE, status='blocked', input_contract_complete=False,
                  candidate_qualification_granted=False, source_admission_granted=False,
                  real_forward_eligible=False, real_forward_days_added=0, live_trading_allowed=False)
    try:
        if len(_canonical(spec)) > 65536:
            raise BundleError('specification_byte_budget_exceeded')
        _keys(spec, ('artifact_type', 'asset_id', 'session_date', 'window_start', 'evidence'))
        if spec['artifact_type'] != SPEC_TYPE or re.fullmatch(r'CN_ETF_(XSHG|XSHE)_[0-9]{6}', spec['asset_id']) is None:
            raise BundleError('unsupported_spec_or_asset')
        if not _day(spec['window_start']) <= _day(spec['session_date']):
            raise BundleError('inverted_input_window')
        if not isinstance(spec['evidence'], dict) or not set(spec['evidence']) <= set(COMPONENTS):
            raise BundleError('unsupported_evidence_component')
        decision = _instant(decision_at)
        registry = dict(DEFAULT_ADAPTERS if adapters is None else adapters)
    except (ValueError, TypeError, KeyError):
        output['blockers'] = [dict(component='spec', code='invalid_bundle_spec_or_decision_time')]
        return output
    for kind in COMPONENTS:
        if kind not in spec['evidence']:
            blockers.append(dict(component=kind, code='missing_evidence'))
            continue
        try:
            entry = spec['evidence'][kind]
            _keys(entry, ('adapter_id', 'receipt'))
            adapter = registry.get(entry['adapter_id'])
            if adapter is None or (not isinstance(adapter, SourceAdapter) and _deferred is None) or adapter.component != kind:
                raise BundleError('unsupported_component_adapter')
            binding = _adapter_binding(adapter) if _deferred is None else _deferred.adapter(adapter,kind)
            context = EvidenceContext(evidence_root, component=kind) if _deferred is None else _deferred.context(kind)
            context.read_json(entry['receipt'])
            evidence = (adapter.parse(context, entry['receipt']) if _deferred is None
                        else _deferred.parse(adapter,context,entry['receipt']))
            if not isinstance(evidence, Evidence) or len(context.references) < 2:
                raise BundleError('parsed_original_evidence_required')
            if evidence.evidence_class not in ('synthetic_only', 'recorded_observation'):
                raise BundleError('explicit_evidence_lineage_required')
            if evidence.request_started_at is None and kind == 'price':
                raise BundleError('price_request_time_required')
            if (evidence.request_started_at is not None
                    and _instant(evidence.request_started_at) > _instant(evidence.received_at)
                    or _instant(evidence.received_at) > decision):
                raise BundleError('evidence_not_received_before_decision')
            facts = _VALIDATORS[kind](evidence.facts, spec)
            _canonical(facts)
            _canonical(evidence.implementation_binding)
            evidence_class = 'synthetic_only' if context.synthetic_seen else evidence.evidence_class
            results[kind] = facts
            validations[kind] = dict(adapter_id=entry['adapter_id'], **binding,
                request_started_at=evidence.request_started_at,
                received_at=evidence.received_at, evidence_class=evidence_class,
                verifier_implementation=evidence.implementation_binding,
                originals=list(context.references.values()))
            contexts.append(context)
        except BundleError as exc:
            blockers.append(dict(component=kind, code=str(exc)))
        except (ValueError, TypeError, KeyError, OSError, OverflowError):
            blockers.append(dict(component=kind, code='invalid_evidence_or_source_schema'))
    if not blockers:
        try:
            current, next_session = results['calendar']['current'], results['calendar']['next']
            if not _instant(current['daily_observation_not_before']) <= _instant(validations['price']['received_at']):
                raise BundleError('price_received_before_daily_observation_window')
            if not _instant(current['daily_observation_not_before']) <= _instant(validations['price']['request_started_at']):
                raise BundleError('price_requested_before_daily_observation_window')
            if not decision < _instant(next_session['decision_cutoff_at']):
                raise BundleError('decision_at_or_after_next_opening_auction_cutoff')
            identity = results['identity']
            if (next_session['date'] > identity['valid_through'] or identity['delisting_date'] is not None
                    and next_session['date'] >= identity['delisting_date']):
                raise BundleError('ETF_identity_not_valid_for_next_session')
            known_on = (_instant(validations['actions']['received_at']) + timedelta(hours=8)).date().isoformat()
            if any(event['announced_date'] > known_on for event in results['actions']['events']):
                raise BundleError('notice_announcement_after_receipt_date')
            bar, execution = results['price'], results['execution']
            opening = _number(bar['open'], positive=True)
            bounded = execution['limit_regime'] == 'bounded'
            if bounded and not (_number(execution['down_limit']) <= _number(bar['low'])
                                <= _number(bar['high']) <= _number(execution['up_limit'])):
                raise BundleError('OHLC_outside_verified_limits')
            bar = dict(bar, suspended=False,
                limit_up=bounded and opening == _number(execution['up_limit']),
                limit_down=bounded and opening == _number(execution['down_limit']))
            for context in contexts:
                context.recheck()
            latest = max((item['received_at'] for item in validations.values()), key=_instant)
            lineage = ('synthetic_only' if any(item['evidence_class'] == 'synthetic_only'
                       for item in validations.values()) else 'recorded_observation')
            output.update(status='input_contract_complete', input_contract_complete=True,
                evidence_class=lineage, input_available_at=latest,
                availability_basis='all_bound_evidence_received_not_provider_first_publication',
                provider_generated_at=None, provider_first_publication_at=None,
                session_date=spec['session_date'], next_session_date=next_session['date'],
                next_decision_at=decision_at, bar=bar, corporate_actions=results['actions']['events'],
                action_coverage={key: value for key, value in results['actions'].items() if key != 'events'},
                session=current, next_session=next_session,
                execution_claim='conditional_open_price_paper_model_not_observed_fills')
        except BundleError as exc:
            blockers.append(dict(component='cross_evidence', code=str(exc)))
        except (ValueError, TypeError, KeyError, OSError):
            blockers.append(dict(component='cross_evidence', code='inconsistent_bound_inputs'))
    output.update(blockers=blockers, evidence=validations,
                  specification_sha256=sha256(_canonical(spec)).hexdigest(),
                  assembler_sha256=(sha256(Path(__file__).read_bytes()).hexdigest() if _deferred is None
                    else _deferred.catalog['code']['src/quant_robot/ops/paper_source_bundle.py']))
    if _deferred is not None:output['deferred_implementation_binding']=_deferred.binding()
    output['sha256'] = sha256(_canonical(output)).hexdigest()
    return output
