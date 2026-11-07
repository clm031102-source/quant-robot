"""Isolated synthetic prototype for bounded original-evidence verification.

Explicit synthetic source assembly can share this reader. No production path.
Only content reads routed through these helpers are measured. Capture callers have NOT
been shown to fit the four-stage operation ceiling. Counts are unbuffered bytes
returned by os.read and attempted os.open calls, not disk/controller read-ahead.

Finalization proves bytes actually observed at those reads. It cannot detect
every transient edit-and-restore or changes after the verification boundary.
Publication still needs the owner's exclusion and final durability protocol.
Event checks cover type/shape, canonical hash chain and monotonic UTC clocks
only. Decision/observation durability semantics still require the existing
reviewed business validators; prototype commit is NOT journal admission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from functools import wraps
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType
from uuid import uuid4


class EvidenceSessionError(ValueError):
    """Finite local error code; never includes source content."""


@dataclass(frozen=True)
class _Policy:
    policy_id: str
    ordinary_files: int = 128
    ordinary_bytes: int = 16_000_000
    per_file_bytes: int = 2_000_000
    prefix_events: int = 2048
    prefix_bytes: int = 64_000_000
    descriptor_bytes: int = 16_384
    descriptors: int = 500
    union_files: int = 32768
    union_bytes: int = 256_000_000
    reference_bytes: int = 1024
    metadata_bytes: int = 32_000_000
    children: int = 2500
    output_bytes: int = 16_000_000
    stages: int = 4
    stage_io_bytes: int = 512_000_000
    stage_opens: int = 65536
    operation_io_bytes: int = 2_048_000_000
    operation_opens: int = 262144


SYNTHETIC_POLICY = _Policy('synthetic_original_prefix_prototype_v1')
# Explicit G1-only engineering policy. Existing four-stage policy and all its
# values are unchanged; the cumulative physical budget does not increase.
G1_SYNTHETIC_POLICY = replace(SYNTHETIC_POLICY,policy_id='synthetic_g1_deferred_operation_v1',stages=5)
# Fixed code-owned reduced policies exist only to exercise hard-stop boundaries
# without reading gigabytes. Constructors accept these exact objects, not IDs,
# dataclass lookalikes, JSON, environment settings, or caller-supplied limits.
_SMALL_POLICY = replace(SYNTHETIC_POLICY, policy_id='synthetic_small_budget_probe_v1',
    ordinary_files=2, ordinary_bytes=64, per_file_bytes=2048,
    prefix_events=8, prefix_bytes=4096, union_files=10, union_bytes=8192,
    metadata_bytes=8192, output_bytes=4096)
_IO_POLICY = replace(SYNTHETIC_POLICY, policy_id='synthetic_physical_io_probe_v1',
    stage_io_bytes=128_000, operation_io_bytes=256_000)
_OPEN_POLICY = replace(SYNTHETIC_POLICY, policy_id='synthetic_open_budget_probe_v1',
    stage_opens=4, operation_opens=8)
_UNION_POLICY = replace(SYNTHETIC_POLICY, policy_id='synthetic_union_byte_probe_v1',
    union_files=10,union_bytes=128)
_POLICIES = MappingProxyType({p.policy_id:p for p in
    (SYNTHETIC_POLICY,G1_SYNTHETIC_POLICY,_SMALL_POLICY,_IO_POLICY,_OPEN_POLICY,_UNION_POLICY)})
PREFIX_TYPE = 'journal_original_prefix_v2_prototype'
EVENT_TYPE = 'frozen_candidate_forward_event_v1'
_DESCRIPTOR_KEYS = {'dependency_type','policy_id','journal_relative_path',
    'activation_sha256','prefix_length','prefix_canonical_tail_sha256',
    'prefix_raw_commitment','total_original_bytes'}
_EVENT_KEYS = {'artifact_type','sequence','kind','previous_sha256','received_at','payload','sha256'}
_KINDS = {'activation','decision','decision_durability','observation','observation_durability'}

# Fixed application-owned catalogs. IDs select reviewed code, never arbitrary
# filesystem paths or callbacks supplied by a source document.
SOURCE_CATALOG = 'synthetic_deferred_sources_v1'
V2_CATALOG = 'synthetic_prospective_transport_v2'
G1_CATALOG = 'synthetic_g1_account_originals_v1'
_REPO = Path(__file__).resolve().parents[3]
_SOURCE_FILES = (
    'src/quant_robot/ops/paper_source_bundle.py',
    'src/quant_robot/ops/paper_source_connection.py',
    'src/quant_robot/ops/paper_warmup_bundle.py',
    'src/quant_robot/ops/frozen_cash_actions.py',
    'src/quant_robot/ops/frozen_input_clocks.py',
    'src/quant_robot/research/full_position_factors.py',
    'src/quant_robot/research/indicator_combinations.py',
)
_V2_FILES = tuple(sorted(set(_SOURCE_FILES) | {
    'src/quant_robot/ops/paper_synthetic_capture_observe.py',
    'src/quant_robot/ops/paper_prospective_transport_v2.py',
    'src/quant_robot/ops/paper_prospective_transport.py',
    'src/quant_robot/ops/paper_prospective_scope.py',
    'src/quant_robot/ops/frozen_candidate_forward.py',
    'src/quant_robot/ops/paper_g1_handoff.py',
    'src/quant_robot/ops/paper_actual_pm_gate.py',
    'src/quant_robot/ops/tushare_live_transport.py',
    'src/quant_robot/ops/tushare_daily_receipt.py',
    'src/quant_robot/config/secrets.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'scripts/capture_tushare_scoped_source.py',
    'scripts/capture_tushare_prospective_source.py',
    'scripts/run_quant_pm_startup_gate.py',
}))
_G1_FILES = tuple(sorted(set(_V2_FILES) | {
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/paper/daily_recovery.py',
    'src/quant_robot/paper/position_buffer.py',
    'src/quant_robot/paper/daily_entry_policy.py',
}))
PM_CATALOG = 'actual_pm_closed_review_code_v1'
_PM_FILES = (
    'src/quant_robot/ops/paper_actual_pm_gate.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/research/cash_carry_repair_study.py',
    'src/quant_robot/research/cash_carry_study.py',
    'src/quant_robot/research/commodity_proxy_admission.py',
    'src/quant_robot/research/commodity_proxy_repair_admission.py',
    'src/quant_robot/research/credit_premium_cadence_study.py',
    'src/quant_robot/research/crypto_charge_monthly_admission.py',
    'src/quant_robot/research/crypto_monthly_admission.py',
    'src/quant_robot/research/currency_gold_account_study.py',
    'src/quant_robot/research/currency_gold_cadence_study.py',
    'src/quant_robot/research/currency_gold_study.py',
    'src/quant_robot/research/dd40_reentry_study.py',
    'src/quant_robot/research/disclosed_flow_study.py',
    'src/quant_robot/research/dividend_style_study.py',
    'src/quant_robot/research/electricity_activity_study.py',
    'src/quant_robot/research/enterprise_liquidity_cadence_study.py',
    'src/quant_robot/research/equity_gold_study.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/fiscal_study_pm_scope.py',
    'src/quant_robot/research/full_position_recovery_study.py',
    'src/quant_robot/research/full_position_study.py',
    'src/quant_robot/research/geopolitical_account_study.py',
    'src/quant_robot/research/geopolitical_cadence_study.py',
    'src/quant_robot/research/household_diagnostic_pm_scope.py',
    'src/quant_robot/research/indicator_combination_study.py',
    'src/quant_robot/research/labor_risk_study.py',
    'src/quant_robot/research/month_start_diagnostic_pm_scope.py',
    'src/quant_robot/research/monthly_diagnostic_pm_scope.py',
    'src/quant_robot/research/option_activity_study.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/rrr_effective_study.py',
    'src/quant_robot/research/slow_indicator_study.py',
    'src/quant_robot/research/term_structure_study.py',
    'src/quant_robot/research/us_variance_risk_study.py',
)
_PM_DOCUMENTS = (
    'configs/quant_pm_startup_gate_cn_etf.json',
    'AGENTS.md',
    'configs/workstations.json',
    'docs/workstation_protocol.md',
    'README.md',
    'configs/research_family_scheduler_cn_etf.json',
    'docs/research/research_family_scheduler_2026-06-17.md',
    'docs/research/quant_pm_startup_gate_2026-06-17.md',
)
_CATALOGS = MappingProxyType({SOURCE_CATALOG:_SOURCE_FILES, V2_CATALOG:_V2_FILES,
                            G1_CATALOG:_G1_FILES, PM_CATALOG:_PM_FILES})


def _canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def _sha(raw):return sha256(raw).hexdigest()


def _hex(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise EvidenceSessionError('duplicate_json_key')
        result[key]=value
    return result


def _decode(raw):
    def reject(_):raise EvidenceSessionError('nonfinite_json')
    try:return json.loads(raw,object_pairs_hook=_pairs,parse_constant=reject)
    except (UnicodeError,RecursionError,json.JSONDecodeError):
        raise EvidenceSessionError('invalid_json_original') from None


def _relative(value):
    if (not isinstance(value,str) or not value or '\\' in value or ':' in value
            or len(value.encode('utf-8'))>768):
        raise EvidenceSessionError('invalid_relative_path')
    path=PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix()!=value or value=='.':
        raise EvidenceSessionError('invalid_relative_path')
    return path


def raw_prefix_seed(journal_relative_path,activation_sha256):
    """Pure commitment primitive; no filesystem reads or authority grant."""
    _relative(journal_relative_path)
    if not _hex(activation_sha256):raise EvidenceSessionError('invalid_activation_hash')
    return _sha(b'paper-prefix-seed-v2\0'+_canonical([journal_relative_path,activation_sha256]))


def raw_prefix_step(previous,index,raw):
    if not _hex(previous) or type(index) is not int or index<0 or not isinstance(raw,bytes):
        raise EvidenceSessionError('invalid_prefix_step')
    return _sha(b'paper-prefix-step-v2\0'+bytes.fromhex(previous)+index.to_bytes(8,'big')
                +len(raw).to_bytes(8,'big')+sha256(raw).digest())


def policy_binding(policy=SYNTHETIC_POLICY):
    if not any(policy is p for p in _POLICIES.values()):
        raise EvidenceSessionError('code_owned_policy_required')
    return dict(policy=asdict(policy),policy_sha256=_sha(_canonical(asdict(policy))),
                prefix_type=PREFIX_TYPE,prototype_only=True,production_admission=False)


def _guarded(method):
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        self._require_open()
        try:return method(self,*args,**kwargs)
        except BaseException:
            self._abort();raise
    return wrapped


@dataclass(frozen=True)
class PendingResult:
    """Opaque ticket, intentionally has no payload, status or success property."""
    _stage_id: str
    _index: int

    def result(self):
        raise EvidenceSessionError('enclosing_session_not_finalized_use_committed_result')


@dataclass(frozen=True)
class VerifiedStage:
    """Synthetic result from a completed read boundary; never a future guarantee."""
    _stage_id: str
    _payloads: tuple[bytes,...]
    _record: bytes

    def result(self,ticket):
        if (type(ticket) is not PendingResult or ticket._stage_id!=self._stage_id
                or type(ticket._index) is not int or not 0<=ticket._index<len(self._payloads)):
            raise EvidenceSessionError('foreign_result_ticket')
        return _decode(self._payloads[ticket._index])

    def receipt(self):return _decode(self._record)


class EvidenceOperation:
    """Read-only synthetic operation. A failure poisons all subsequent stages."""
    def __init__(self,root,*,policy=SYNTHETIC_POLICY):
        policy_binding(policy)
        self._policy=policy
        self.root=Path(root).resolve(strict=True)
        if not self.root.is_dir():raise EvidenceSessionError('evidence_root_required')
        self._state='open';self._active=None;self._stages=[]
        self._bytes=0;self._opens=0;self._reads=0;self._actual_pm=None

    def _enable_actual_pm(self):
        if self._state!='open' or self._stages or self._actual_pm is not None:
            raise EvidenceSessionError('actual_pm_requires_fresh_existing_operation')
        from quant_robot.ops.paper_actual_pm_gate import _ActualPMGate
        self._actual_pm=_ActualPMGate(self)

    def _pm_role(self):
        if self._actual_pm is not None:
            from quant_robot.ops.paper_actual_pm_gate import _ActualPMGate
            if type(self._actual_pm) is not _ActualPMGate or self._actual_pm.operation is not self:
                raise EvidenceSessionError('fixed_actual_pm_role_required')
        return self._actual_pm

    def stage(self):
        if self._state!='open':raise EvidenceSessionError('operation_not_open')
        if self._active is not None:
            self._active._abort();raise EvidenceSessionError('nested_stage_forbidden')
        if len(self._stages)>=self._policy.stages:
            self._state='failed';raise EvidenceSessionError('operation_stage_budget_exceeded')
        stage=VerificationSession(self);self._active=stage;self._stages.append(stage)
        try:stage._start()
        except BaseException:stage._abort();raise
        return stage

    def close(self):
        if self._active is not None:self._active._abort()
        if self._state=='open':self._state='closed'

    def fail(self):
        """Root cleanup failure cannot turn a completed source stage into success."""
        if self._active is not None:self._active._abort()
        self._state='failed'

    def measurements(self):
        return dict(state=self._state,stages_started=len(self._stages),
            io_bytes_returned=self._bytes,open_attempts=self._opens,read_calls=self._reads,
            stages=[stage.measurements() for stage in self._stages],
            prototype_only=True,real_network_requests=0,credentials_read=0,
            existing_top_level_paths_measured=False)

    def _read(self,stage,path,limit,label,*,flush=False,expected_sha=None):
        """The sole file-content I/O gateway, including implementation reads."""
        p=self._policy
        if self._opens>=p.operation_opens:raise EvidenceSessionError('operation_open_budget_exceeded')
        if stage._opens>=p.stage_opens:raise EvidenceSessionError('stage_open_budget_exceeded')
        self._opens+=1;stage._opens+=1
        counts=stage._per_path.setdefault(label,dict(opens=0,bytes=0,reads=0))
        counts['opens']+=1
        flags=(os.O_RDWR if flush else os.O_RDONLY)|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)
        fd=os.open(path,flags)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):raise EvidenceSessionError('regular_original_required')
            if info.st_size>limit:raise EvidenceSessionError('document_byte_budget_exceeded')
            parts=[];received=0
            while received<info.st_size:
                remaining=min(p.operation_io_bytes-self._bytes,p.stage_io_bytes-stage._bytes)
                if remaining<=0:raise EvidenceSessionError('physical_io_byte_budget_exceeded')
                requested=min(65536,info.st_size-received,remaining)
                self._reads+=1;stage._reads+=1;counts['reads']+=1
                raw=os.read(fd,requested)
                # Bytes successfully returned before a later read failure remain charged.
                self._bytes+=len(raw);stage._bytes+=len(raw);counts['bytes']+=len(raw)
                if not raw:raise EvidenceSessionError('original_truncated_during_read')
                parts.append(raw);received+=len(raw)
            final_info=os.fstat(fd)
            if final_info.st_size!=received:raise EvidenceSessionError('original_size_changed_during_read')
            if stage._control_journal is not None and label==stage._control_journal+'/.writer.lock':
                stage._read_metadata[label]=dict(device=final_info.st_dev,inode=final_info.st_ino,
                    size=final_info.st_size,mtime_ns=final_info.st_mtime_ns)
            result=b''.join(parts)
            if flush:
                if expected_sha is None or _sha(result)!=expected_sha:
                    raise EvidenceSessionError('publication_changed_before_fsync_confirmation')
                os.fsync(fd)
            return result
        finally:os.close(fd)


class _Child:
    def __init__(self,session,name):
        self._session=session;self.name=name;self._refs={};self._bytes=0;self._prefixes=set();self._heads=set()

    def read_bytes(self,reference):return self._session._ordinary(self,reference)

    def snapshot_original(self,relative):return self._session._bootstrap(self,relative)

    def confirm_durable(self,reference):return self._session._confirm_durable(self,reference)

    def current_journal(self,journal):return self._session._current_journal(self,journal)

    def require_prefix(self,descriptor):return self._session._prefix_dependency(self,descriptor)

    def prefix_view(self,descriptor):
        self.require_prefix(descriptor)
        return RegisteredPrefixView(self._session,descriptor)

    def snapshot_prefix(self,journal,activation,count):
        return self._session._snapshot_prefix(self,journal,activation,count)

    @property
    def references(self):
        self._session.require_open()
        return [{key:self._session._originals[identity][key] for key in ('path','sha256','bytes')}
                for identity in self._refs]

    def propose(self,value):return self._session._propose(self,value)

    def recheck(self):
        self._session._require_open()
        # Responsibility stays with the enclosing session; this returns no success.
        return None


class RegisteredPrefixView:
    """Read-only view of exactly one registered endpoint, while its stage is open."""
    def __init__(self,session,descriptor):
        self._session=session
        self._descriptor=_canonical(descriptor)

    @property
    def root(self):return self._session.root

    def descriptor(self):
        self._session.require_open()
        return _decode(self._descriptor)

    def _entry(self,index):
        self._session.require_open()
        descriptor=self.descriptor()
        if (self._descriptor not in self._session._descriptors.values()
                or type(index) is not int or not 0<=index<descriptor['prefix_length']):
            self._session.fail('prefix_view_outside_registered_range')
        name=f'{descriptor["journal_relative_path"]}/{index:08d}.json'
        _,_,identity=self._session._path(name)
        entry=self._session._originals.get(identity)
        if entry is None:self._session.fail('prefix_view_not_registered')
        return entry

    def originals(self):
        return [dict(name=f'{i:08d}.json',raw=self._entry(i)['raw'].decode('utf-8'))
                for i in range(self.descriptor()['prefix_length'])]

    def read_bytes(self,reference):
        descriptor=self.descriptor();prefix=descriptor['journal_relative_path']+'/'
        if (not isinstance(reference,dict) or set(reference)!={'path','sha256'}
                or not isinstance(reference['path'],str) or not reference['path'].startswith(prefix)):
            self._session.fail('prefix_view_outside_registered_range')
        suffix=reference['path'][len(prefix):]
        if not re.fullmatch(r'[0-9]{8}\.json',suffix):self._session.fail('prefix_view_outside_registered_range')
        entry=self._entry(int(suffix[:8]))
        if entry['sha256']!=reference['sha256']:self._session.fail('prefix_view_hash_conflict')
        return entry['raw']


class VerificationSession:
    """One bounded initial snapshot plus one final pass, with merged prefixes."""
    def __init__(self,operation):
        self._operation=operation;self._policy=operation._policy
        self._id=uuid4().hex;self._state='open';self._bytes=0;self._opens=0;self._reads=0
        self._per_path={};self._originals={};self._unique_bytes=0;self._unique_files=0;self._metadata=0
        self._children={};self._payloads=[];self._output_bytes=0
        self._prefix=None;self._descriptors={};self._code=None;self._binding=None
        self._catalog_code={};self._code_bytes=0;self._pm_documents={}
        self._heads={};self._guards={};self._control_journal=None;self._control_expected=None;self._read_metadata={}

    @property
    def root(self):return self._operation.root

    @property
    def policy(self):return self._policy

    def require_open(self):self._require_open()

    def abort(self):self._abort()

    def fail(self,code):
        self._abort();raise EvidenceSessionError(code)

    def binding(self):
        self._require_open();return _decode(_canonical(self._binding))

    @_guarded
    def path_for(self,relative):return self._path(relative)[0]

    @_guarded
    def new_child(self,label):
        return self.child(f'{label}_{len(self._children)}')

    @_guarded
    def bind_implementation(self,catalog_id):
        if not isinstance(catalog_id,str) or catalog_id not in _CATALOGS:
            raise EvidenceSessionError('code_owned_catalog_required')
        names=_CATALOGS[catalog_id]
        for name in names:
            if name in self._catalog_code:continue
            if len(self._catalog_code)>=128:raise EvidenceSessionError('code_document_budget_exceeded')
            raw=self._operation._read(self,_REPO/name,2_000_000,'@code/'+name)
            if self._code_bytes+len(raw)>16_000_000:raise EvidenceSessionError('code_byte_budget_exceeded')
            item=dict(sha256=_sha(raw),bytes=len(raw))
            self._metadata_charge(len(_canonical(dict(path=name,**item))))
            self._code_bytes+=len(raw);self._catalog_code[name]=item
        return dict(catalog_id=catalog_id,code={name:self._catalog_code[name]['sha256'] for name in names},
                    session=self.binding(),production_admission=False)

    def _pm_document_path(self,name):
        if not isinstance(name,str) or name not in _PM_DOCUMENTS:
            raise EvidenceSessionError('actual_pm_dependency_outside_closed_graph')
        path=_REPO
        for part in Path(name).parts:
            path/=part
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
                raise EvidenceSessionError('actual_pm_document_link_forbidden')
        if not path.resolve(strict=True).is_relative_to(_REPO):
            raise EvidenceSessionError('actual_pm_document_outside_worktree')
        return path

    @_guarded
    def read_pm_document(self,name):
        if self._operation._pm_role() is None:
            raise EvidenceSessionError('fixed_actual_pm_role_required')
        path=self._pm_document_path(name)
        if name not in self._pm_documents:
            raw=self._operation._read(self,path,self.policy.per_file_bytes,'@pm/'+name)
            if (self._unique_files>=self.policy.union_files
                    or self._unique_bytes+len(raw)>self.policy.union_bytes):
                raise EvidenceSessionError('actual_pm_document_union_budget_exceeded')
            pin=dict(sha256=_sha(raw),bytes=len(raw))
            self._metadata_charge(len(_canonical(dict(path=name,**pin))))
            self._unique_files+=1;self._unique_bytes+=len(raw)
            self._pm_documents[name]=dict(raw=raw,**pin)
        return self._pm_documents[name]['raw']

    def pm_document_pins(self):
        self._require_open()
        return {name:{k:item[k] for k in ('sha256','bytes')} for name,item in self._pm_documents.items()}

    @_guarded
    def read_writer_guard(self,journal,expected,*,require_at_commit=False):
        # Ephemeral owned lock bytes are control evidence, never a reusable
        # ordinary original. Only this fixed role/path is supported.
        if not isinstance(expected,bytes) or not 0<len(expected)<=16384:
            raise EvidenceSessionError('bounded_writer_guard_required')
        if self._control_journal is None:
            self._metadata_charge(len(expected)+len(journal.encode()))
            self._control_journal=journal;self._control_expected=expected
        elif journal!=self._control_journal or expected!=self._control_expected:
            raise EvidenceSessionError('one_exact_owned_writer_guard_required')
        path,key,_=self._path(journal+'/.writer.lock')
        raw=self._operation._read(self,path,16384,key)
        if raw!=expected:raise EvidenceSessionError('writer_guard_ownership_changed')
        if require_at_commit:
            if journal not in self._guards:
                if self._guards:raise EvidenceSessionError('one_owned_journal_guard_required')
            elif self._guards[journal]!=expected:raise EvidenceSessionError('writer_guard_ownership_changed')
            self._guards[journal]=expected
        return raw

    def _journal_names(self,journal):
        directory,_,_=self._path(journal)
        names=[];pending=False
        with os.scandir(directory) as entries:
            # Bound directory metadata work too; do not materialize an arbitrary
            # directory before deciding that the journal is oversized.
            for count,entry in enumerate(entries,1):
                if count>self._policy.prefix_events+64:
                    raise EvidenceSessionError('journal_directory_entry_budget_exceeded')
                if entry.name.startswith('.pending-'):pending=True
                if re.fullmatch(r'[0-9]{8}\.json',entry.name):names.append(entry.name)
        if pending:raise EvidenceSessionError('journal_pending_publication')
        names.sort()
        if len(names)>self._policy.prefix_events or names!=[f'{i:08d}.json' for i in range(len(names))]:
            raise EvidenceSessionError('current_journal_gap_or_event_budget')
        return names

    @_guarded
    def check_publication_head(self,journal,count,*,require_at_commit=False):
        if type(count) is not int or not 0<=count<=self._policy.prefix_events:
            raise EvidenceSessionError('bounded_publication_head_required')
        if self._journal_names(journal)!=[f'{i:08d}.json' for i in range(count)]:
            raise EvidenceSessionError('publication_journal_head_changed')
        if require_at_commit:
            names=[f'{i:08d}.json' for i in range(count)]
            if journal not in self._heads:self._metadata_charge(len(_canonical(names))+len(journal.encode()))
            elif self._heads[journal]!=names:raise EvidenceSessionError('active_journal_head_changed')
            self._heads[journal]=names

    @_guarded
    def _current_journal(self,child,journal):
        names=self._journal_names(journal)
        previous=self._heads.get(journal)
        if previous is not None and previous!=names:raise EvidenceSessionError('active_journal_head_changed')
        if journal not in self._heads:
            if self._heads:raise EvidenceSessionError('one_active_journal_required')
            self._metadata_charge(len(_canonical(names))+len(journal.encode()));self._heads[journal]=names
        child._heads.add(journal)
        if not names:return []
        first=self._original(journal+'/'+names[0]);activation=_decode(first['raw'])['sha256']
        view=child.snapshot_prefix(journal,activation,len(names))
        return [_decode(item['raw']) for item in view.originals()]

    def __enter__(self):self._require_open();return self

    def __exit__(self,kind,value,traceback):
        if kind is not None or self._state=='open':self._abort()
        return False

    def _require_open(self):
        if self._state!='open' or self._operation._state!='open':
            raise EvidenceSessionError('session_not_open')

    def _abort(self):
        if self._state!='committed':
            self._state='failed';self._operation._state='failed'
            self._payloads.clear();self._originals.clear()
        if self._operation._active is self:self._operation._active=None

    def _implementation(self):
        source=Path(__file__).resolve(strict=True)
        raw=self._operation._read(self,source,2_000_000,'@implementation/paper_evidence_session.py')
        return dict(**policy_binding(self._policy),implementation_sha256=_sha(raw),implementation_bytes=len(raw))

    def _start(self):
        self._binding=self._implementation()
        role=self._operation._pm_role()
        if role is not None:role.stage_start(self)

    def _path(self,relative):
        parts=_relative(relative).parts;current=self._operation.root
        for part in parts:
            current/=part
            if current.is_symlink() or getattr(current,'is_junction',lambda:False)():
                raise EvidenceSessionError('original_link_forbidden')
        resolved=current.resolve(strict=False)
        if not resolved.is_relative_to(self._operation.root):raise EvidenceSessionError('original_outside_root')
        key=resolved.relative_to(self._operation.root).as_posix()
        # Normalize spelling aliases on Windows, while preserving distinct paths
        # for distinct hard links or identical-content copies.
        identity=os.path.normcase(str(resolved))
        return resolved,key,identity

    def _metadata_charge(self,amount):
        if self._metadata+amount>self._policy.metadata_bytes:raise EvidenceSessionError('metadata_budget_exceeded')
        self._metadata+=amount

    def _original(self,relative,expected=None):
        path,key,identity=self._path(relative)
        previous=self._originals.get(identity)
        if previous is not None:
            if expected is not None and previous['sha256']!=expected:raise EvidenceSessionError('expected_sha_conflict')
            return previous
        if len(self._originals)>=self._policy.union_files:raise EvidenceSessionError('union_file_budget_exceeded')
        raw=self._operation._read(self,path,self._policy.per_file_bytes,key)
        digest=_sha(raw)
        if expected is not None and digest!=expected:raise EvidenceSessionError('original_sha_mismatch')
        if self._unique_bytes+len(raw)>self._policy.union_bytes:raise EvidenceSessionError('union_byte_budget_exceeded')
        reference=dict(path=key,sha256=digest,bytes=len(raw))
        encoded=_canonical(reference)
        if len(encoded)>self._policy.reference_bytes:raise EvidenceSessionError('reference_metadata_too_large')
        self._metadata_charge(len(encoded));self._unique_bytes+=len(raw);self._unique_files+=1
        result=dict(**reference,raw=raw);self._originals[identity]=result
        return result

    @_guarded
    def child(self,name):
        if (not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',name)
                or name in self._children):raise EvidenceSessionError('unique_child_name_required')
        if len(self._children)>=self._policy.children:raise EvidenceSessionError('child_budget_exceeded')
        child=_Child(self,name);self._children[name]=child;return child

    @_guarded
    def _ordinary(self,child,reference):
        if not isinstance(reference,dict) or set(reference)!={'path','sha256'} or not _hex(reference['sha256']):
            raise EvidenceSessionError('exact_original_reference_required')
        _,key,identity=self._path(reference['path'])
        if identity not in child._refs and len(child._refs)>=self._policy.ordinary_files:
            raise EvidenceSessionError('ordinary_file_budget_exceeded')
        original=self._original(key,reference['sha256'])
        if identity not in child._refs:
            if child._bytes+original['bytes']>self._policy.ordinary_bytes:
                raise EvidenceSessionError('ordinary_byte_budget_exceeded')
            child._refs[identity]=original['sha256'];child._bytes+=original['bytes']
        elif child._refs[identity]!=original['sha256']:raise EvidenceSessionError('expected_sha_conflict')
        return original['raw']

    @_guarded
    def _bootstrap(self,child,relative):
        _,_,identity=self._path(relative)
        if identity not in child._refs and len(child._refs)>=self._policy.ordinary_files:
            raise EvidenceSessionError('ordinary_file_budget_exceeded')
        item=self._original(relative)
        ref=dict(path=item['path'],sha256=item['sha256'])
        raw=self._ordinary(child,ref)
        return raw,ref

    @_guarded
    def _confirm_durable(self,child,reference):
        # Register first under the unchanged ordinary limits; the writable
        # descriptor only rereads and fsyncs, never changes source bytes.
        original=self._ordinary(child,reference)
        path,key,_=self._path(reference['path'])
        raw=self._operation._read(self,path,self._policy.per_file_bytes,key,flush=True,expected_sha=_sha(original))
        if raw!=original:raise EvidenceSessionError('publication_changed_before_fsync_confirmation')
        return raw

    @_guarded
    def _prefix_dependency(self,child,descriptor):
        p=self._policy
        if (not isinstance(descriptor,dict) or set(descriptor)!=_DESCRIPTOR_KEYS
                or len(_canonical(descriptor))>p.descriptor_bytes):
            raise EvidenceSessionError('bounded_exact_prefix_descriptor_required')
        if descriptor['dependency_type']!=PREFIX_TYPE or descriptor['policy_id']!=p.policy_id:
            raise EvidenceSessionError('code_owned_prefix_policy_required')
        count=descriptor['prefix_length'];declared=descriptor['total_original_bytes']
        if (type(count) is not int or not 1<=count<=p.prefix_events
                or type(declared) is not int or not 0<declared<=p.prefix_bytes
                or any(not _hex(descriptor[key]) for key in ('activation_sha256','prefix_canonical_tail_sha256','prefix_raw_commitment'))):
            raise EvidenceSessionError('prefix_budget_or_binding_invalid')
        journal=descriptor['journal_relative_path'];_,journal_key,identity=self._path(journal)
        if self._prefix is None:
            self._prefix=dict(identity=identity,journal=journal_key,activation=descriptor['activation_sha256'],
                tails=[],roots=[],totals=[],clock=None,raw_root=raw_prefix_seed(journal,descriptor['activation_sha256']))
        prefix=self._prefix
        if (prefix['identity']!=identity or prefix['journal']!=journal
                or prefix['activation']!=descriptor['activation_sha256']):
            raise EvidenceSessionError('one_exact_journal_identity_required')
        encoded=_canonical(descriptor);key=_sha(encoded)
        if key not in self._descriptors:
            if len(self._descriptors)>=p.descriptors:raise EvidenceSessionError('prefix_descriptor_budget_exceeded')
            self._metadata_charge(len(encoded));self._descriptors[key]=encoded
        while len(prefix['tails'])<count:
            index=len(prefix['tails']);entry=self._original(f'{journal}/{index:08d}.json')
            total=(prefix['totals'][-1] if index else 0)+entry['bytes']
            if total>p.prefix_bytes:raise EvidenceSessionError('prefix_raw_byte_budget_exceeded')
            event=_decode(entry['raw'])
            if not isinstance(event,dict) or set(event)!=_EVENT_KEYS:raise EvidenceSessionError('exact_journal_event_required')
            digest=event.pop('sha256')
            if (not _hex(digest) or digest!=_sha(_canonical(event)) or type(event['sequence']) is not int
                    or event['sequence']!=index or event['artifact_type']!=EVENT_TYPE
                    or event['previous_sha256']!=(prefix['tails'][-1] if index else None)
                    or event['kind'] not in _KINDS or not isinstance(event['payload'],dict)
                    or (event['kind']=='activation')!=(index==0)):
                raise EvidenceSessionError('journal_hash_chain_invalid')
            if index==0 and digest!=prefix['activation']:raise EvidenceSessionError('activation_binding_mismatch')
            stamp=event['received_at']
            if not isinstance(stamp,str) or not stamp.endswith('Z') or 'T' not in stamp:
                raise EvidenceSessionError('explicit_utc_clock_required')
            try:clock=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            except ValueError:raise EvidenceSessionError('explicit_utc_clock_required') from None
            if clock.utcoffset()!=timedelta(0):raise EvidenceSessionError('explicit_utc_clock_required')
            if prefix['clock'] is not None and clock<prefix['clock']:raise EvidenceSessionError('journal_clock_regressed')
            prefix['clock']=clock;prefix['tails'].append(digest);prefix['totals'].append(total)
            prefix['raw_root']=raw_prefix_step(prefix['raw_root'],index,entry['raw']);prefix['roots'].append(prefix['raw_root'])
        if (prefix['tails'][count-1]!=descriptor['prefix_canonical_tail_sha256']
                or prefix['roots'][count-1]!=descriptor['prefix_raw_commitment']
                or prefix['totals'][count-1]!=declared):
            raise EvidenceSessionError('original_prefix_commitment_mismatch')
        child._prefixes.add(key)
        # No success token; obligations remain pending until commit.
        return None

    @_guarded
    def _snapshot_prefix(self,child,journal,activation,count):
        if type(count) is not int or not 1<=count<=self._policy.prefix_events:
            raise EvidenceSessionError('prefix_budget_or_binding_invalid')
        root=raw_prefix_seed(journal,activation);total=0;tail=None
        for index in range(count):
            item=self._original(f'{journal}/{index:08d}.json');total+=item['bytes']
            if total>self._policy.prefix_bytes:raise EvidenceSessionError('prefix_raw_byte_budget_exceeded')
            root=raw_prefix_step(root,index,item['raw']);tail=_decode(item['raw'])['sha256']
        descriptor=dict(dependency_type=PREFIX_TYPE,policy_id=self._policy.policy_id,
            journal_relative_path=journal,activation_sha256=activation,prefix_length=count,
            prefix_canonical_tail_sha256=tail,prefix_raw_commitment=root,total_original_bytes=total)
        return child.prefix_view(descriptor)

    @_guarded
    def _propose(self,child,value):
        if not child._refs and not child._prefixes and not child._heads:raise EvidenceSessionError('originals_required_before_proposal')
        raw=_canonical(value)
        if len(raw)>self._policy.per_file_bytes or self._output_bytes+len(raw)>self._policy.output_bytes:
            raise EvidenceSessionError('proposed_output_budget_exceeded')
        ticket=PendingResult(self._id,len(self._payloads));self._payloads.append(raw);self._output_bytes+=len(raw)
        return ticket

    @_guarded
    def commit(self):
        if not self._payloads:raise EvidenceSessionError('no_proposed_child_results')
        for original in self._originals.values():
            path,_,identity=self._path(original['path'])
            if self._originals.get(identity) is not original:raise EvidenceSessionError('original_path_identity_changed')
            raw=self._operation._read(self,path,self._policy.per_file_bytes,original['path'])
            if len(raw)!=original['bytes'] or _sha(raw)!=original['sha256']:
                raise EvidenceSessionError('original_changed_at_final_read')
        # Equality of every original raw byte also implies equality of all
        # previously derived prefix roots; no second recursive expansion needed.
        if self._implementation()!=self._binding:raise EvidenceSessionError('implementation_or_policy_changed')
        for name,item in self._catalog_code.items():
            raw=self._operation._read(self,_REPO/name,2_000_000,'@code/'+name)
            if len(raw)!=item['bytes'] or _sha(raw)!=item['sha256']:
                raise EvidenceSessionError('implementation_changed_at_final_read')
        for name,item in self._pm_documents.items():
            raw=self._operation._read(self,self._pm_document_path(name),self.policy.per_file_bytes,'@pm/'+name)
            if len(raw)!=item['bytes'] or _sha(raw)!=item['sha256']:
                raise EvidenceSessionError('actual_pm_document_changed_at_final_read')
        for journal,names in self._heads.items():
            if self._journal_names(journal)!=names:raise EvidenceSessionError('active_journal_head_changed')
        for journal,expected in self._guards.items():self.read_writer_guard(journal,expected)
        role=self._operation._pm_role()
        if role is not None:role.before_commit(self)
        record=dict(status='synthetic_originals_verified_at_read_boundary',binding=self._binding,
            code={name:dict(item) for name,item in self._catalog_code.items()},
            pm_documents=self.pm_document_pins(),
            active_journal_heads={journal:list(names) for journal,names in self._heads.items()},
            writer_guards_checked=list(self._guards),
            guard_metadata={journal:dict(self._read_metadata[journal+'/.writer.lock']) for journal in self._guards},
            measurements={**self.measurements(),'state':'committed'},prefix_dependencies=[_decode(raw) for raw in self._descriptors.values()],
            originals=[{key:item[key] for key in ('path','sha256','bytes')} for item in self._originals.values()],
            production_admission=False,qualification_granted=False,real_forward_days_added=0,
            transient_change_detection_claimed=False,post_boundary_integrity_guaranteed=False)
        encoded=_canonical(record)
        if len(encoded)>self._policy.metadata_bytes:raise EvidenceSessionError('final_record_metadata_budget_exceeded')
        result=VerifiedStage(self._id,tuple(self._payloads),encoded)
        self._state='committed';self._operation._active=None
        self._payloads.clear();self._originals.clear()
        return result

    def measurements(self):
        return dict(state=self._state,io_bytes_returned=self._bytes,open_attempts=self._opens,
            read_calls=self._reads,unique_original_files=self._unique_files,unique_original_bytes=self._unique_bytes,
            metadata_bytes=self._metadata,prefix_events=len(self._prefix['tails']) if self._prefix else 0,
            children=len(self._children),code_files=len(self._catalog_code),code_bytes=self._code_bytes,
            active_journal_lengths={journal:len(names) for journal,names in self._heads.items()},
            prefix_descriptors=len(self._descriptors),per_path=json.loads(json.dumps(self._per_path)))
