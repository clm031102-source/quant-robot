"""One separately released monthly-breadth diagnostic over retained Study23 inputs.

Only the old source normalizer is reused. Its quarterly method is a source/date
contract, never the economic method here. No old admission or account runner is
called. Import, fingerprint and preview do not decode financial payloads.
"""
from __future__ import annotations

import csv
import io
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import localcontext
from pathlib import Path

from quant_robot.research import equity_gold_constant_mix_admission as retained
from quant_robot.research import equity_gold_constant_mix_historical as normalizer
from quant_robot.research.monthly_diagnostic_registration import canonical as persisted_bytes

DIRECTORY = 'data/reports/campaign_72h_20261106/monthly_breadth_accounts'
REGISTRATION = DIRECTORY + '/registration.json'
RELEASE = DIRECTORY + '/release.json'
MANAGER_REVIEW = DIRECTORY + '/manager_review.json'
ROOT_REVIEW = DIRECTORY + '/root_review.json'
METHOD = 'data/reports/campaign_72h_20261106/manager/monthly_breadth_design_20261107/contract_v1.json'
METHOD_SHA = 'f3d77564288628ebd67e37bd36735197d7f49f9fab63d65398ee28a1a9d16a89'
BRANCH = 'codex/factor-review-72h-campaign-20261106'
MODE = 'single_campaign_monthly_breadth_28_account_only'
SOURCE = retained.SOURCE
ASSETS = normalizer.ASSETS
MANIFEST = retained.MANIFEST
MANIFEST_SHA = '0480972b713d1c745d620ec81edc6aa722dbe749a37c3dcc7f6293294d8ce913'
PM_INPUTS = dict(retained.PM_INPUTS)
NEW_FILES = (
    'src/quant_robot/research/monthly_breadth.py',
    'src/quant_robot/research/monthly_breadth_historical.py',
    'scripts/run_monthly_breadth_historical.py',
    'tests/unit/test_monthly_breadth.py',
    'tests/unit/test_monthly_breadth_historical.py',
    'src/quant_robot/research/monthly_breadth_verification.py',
    'tests/unit/test_monthly_breadth_verification.py',
)
# Existing, explicitly maintained PM closure; no new hook is installed.
from quant_robot.ops.paper_evidence_session import _PM_FILES
CODE_FILES = tuple(sorted(set(retained.CODE_FILES) | set(_PM_FILES) | set(NEW_FILES)))
POLICIES = ('breadth', 'monthly_50_50', 'own_trend')
POLICY = dict(
    assets=list(ASSETS), symbols=['510300.SH', '518880.SH'],
    source_start='2013-12-05', source_end='2024-01-02', sessions=2454,
    first_signal='2014-12-31', first_sell='2015-01-05', first_buy='2015-01-06',
    terminal_plan='2023-12-29', terminal_open='2024-01-02',
    month_end_points=13, lookback_months=12, prior_capacity_sessions=20,
    initial_cash_CNY='10000', commission_rate='0.0001',
    cost_cases=[[m, s] for m in (0, 5, 10) for s in (0, 10, 30)],
    primary='min5_slip10', policies=list(POLICIES), strategy_accounts=27,
    cash_controls=1, account_count=28, max_executions=1,
    annual_years=list(range(2015, 2024)), bootstrap_replications=5000,
    bootstrap_seed=20261107, bootstrap_generator='PCG64',
    bootstrap_block_length=2, bootstrap_draws=5, bootstrap_truncate=9,
    statistical_endpoints=27, lower_quantile='0.05/27', quantile_method='linear',
    source_nature=SOURCE, conditional_only=True, qualification_granted=False,
    ordinary_research_allowed=False, final_holdout_allowed=False,
    live_boundary_allowed=False, source_year_2026_allowed=False,
)
canonical, digest = retained.canonical, retained.digest
read_bound, resolve_path = retained.read_bound, retained.resolve_path
write_exclusive_json = retained.write_exclusive_json


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _now():
    return datetime.now(timezone.utc)


def _time(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require(t.tzinfo is not None, 'Timezone-aware clock required')
    return t.astimezone(timezone.utc)


def _json(raw):
    return retained._json(raw)


def _ref(root, relative):
    return dict(path=relative, sha256=retained.file_digest(resolve_path(root, relative)))


def _branch(root):
    return subprocess.run(['git', 'symbolic-ref', '--short', 'HEAD'], cwd=root,
        check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def _execution_modules(root):
    for module, path in ((retained, 'src/quant_robot/research/equity_gold_constant_mix_admission.py'),
                         (normalizer, 'src/quant_robot/research/equity_gold_constant_mix_historical.py')):
        _require(Path(module.__file__).resolve() == resolve_path(root, path), 'Loaded normalizer code root mismatch')
    _require(Path(__file__).resolve() == resolve_path(root, 'src/quant_robot/research/monthly_breadth_historical.py'),
             'Loaded controller code root mismatch')


def _protocol_paths(root):
    config = _json(read_bound(root, _ref(root, PM_INPUTS['pm_policy']), return_bytes=True))
    rows = config['required_reading']
    _require(len(rows) == 7, 'Exact seven PM reading documents required')
    paths = [row['path'] for row in rows]
    _require(len(set(paths)) == 7, 'Duplicate PM reading path')
    return paths


def _original_inputs(root):
    """Hash only: preserve all 175 existing roles, aliases and original bytes."""
    manifest = _json(read_bound(root, dict(path=MANIFEST, sha256=MANIFEST_SHA), return_bytes=True))
    rows = manifest['inputs']
    _require(manifest.get('artifact_type') == 'constant_mix_historical_input_manifest_v1'
             and manifest.get('source_nature') == SOURCE and len(rows) == 175
             and manifest.get('input_count') == 175, 'Exact retained 175-role input manifest required')
    pins = {}
    paths = set()
    for row in rows:
        _require(set(row) == {'role', 'path', 'sha256', 'bytes'}
                 and row['role'] not in pins, 'Original role identity changed')
        pin = dict(path=row['path'], sha256=row['sha256'])
        target = resolve_path(root, pin['path'])
        _require(type(row['bytes']) is int and target.stat().st_size == row['bytes'], 'Original input size changed')
        read_bound(root, pin)
        identity = str(target).casefold()
        _require(identity not in paths, 'One input role per actual path required')
        paths.add(identity)
        pins[row['role']] = pin
    return pins


def build_registration(root, *, method_sha256, study_number):
    """Return a hash-only packet; never write a registration or release."""
    _require(type(study_number) is int and study_number > 24, 'Root must assign a new study number')
    _require(method_sha256 == METHOD_SHA, 'Exact prospective method hash required')
    pins = _original_inputs(root)
    pins['monthly_method'] = dict(path=METHOD, sha256=method_sha256)
    read_bound(root, pins['monthly_method'])
    pins.update({role: _ref(root, p) for role, p in PM_INPUTS.items()})
    packet = dict(artifact_type='monthly_breadth_registration_v1', branch=BRANCH,
        input_manifest=dict(path=MANIFEST, sha256=MANIFEST_SHA), inputs=pins,
        implementation={p: _ref(root, p) for p in CODE_FILES},
        protocols={p: _ref(root, p) for p in _protocol_paths(root)},
        environment=retained.runtime_environment(), policy=dict(POLICY, study_number=study_number))
    packet['registration_sha256'] = digest(canonical(packet))
    return validate_registration(root, packet)


def validate_registration(root, packet):
    _require(type(packet) is dict and set(packet) == {
        'artifact_type', 'branch', 'input_manifest', 'inputs', 'implementation',
        'protocols', 'environment', 'policy', 'registration_sha256'}, 'Exact registration schema required')
    _require(packet['artifact_type'] == 'monthly_breadth_registration_v1' and packet['branch'] == BRANCH
             and packet['input_manifest'] == dict(path=MANIFEST, sha256=MANIFEST_SHA), 'New exact registration identity required')
    _require(packet['registration_sha256'] == digest(canonical({k: v for k, v in packet.items()
              if k != 'registration_sha256'})), 'Registration digest changed')
    number = packet['policy'].get('study_number')
    _require(type(number) is int and number > 24
             and packet['policy'] == dict(POLICY, study_number=number), 'Fixed monthly policy required')
    inputs = _original_inputs(root)
    _require(set(packet['inputs']) == set(inputs) | set(PM_INPUTS) | {'monthly_method'}, 'Input role set changed')
    for role, pin in packet['inputs'].items():
        if role in inputs:
            _require(pin == inputs[role], 'Original 175-role input changed')
        elif role == 'monthly_method':
            _require(pin == dict(path=METHOD, sha256=METHOD_SHA), 'New method changed')
        else:
            _require(pin['path'] == PM_INPUTS[role], 'PM configuration path changed')
        read_bound(root, pin)
    _require(len({str(resolve_path(root, p['path'])).casefold() for p in packet['inputs'].values()})
             == len(packet['inputs']), 'Input role alias forbidden')
    _require(set(packet['implementation']) == set(CODE_FILES), 'Exact implementation closure required')
    _require(set(packet['protocols']) == set(_protocol_paths(root)), 'Exact PM reading set required')
    for group in ('implementation', 'protocols'):
        for path, pin in packet[group].items():
            _require(pin['path'] == path, 'Code or protocol alias forbidden')
            read_bound(root, pin)
    env = retained.runtime_environment()
    _require(packet['environment'] == env and env['python'] == '3.12.13', 'Frozen exact runtime required')
    campaign = _json(read_bound(root, packet['inputs']['campaign'], return_bytes=True))
    _require(campaign.get('campaign_id') == 'quant_manager_72h_20261106'
             and campaign.get('status') == 'active' and campaign.get('machine') == 'office_desktop'
             and campaign.get('task_branch') == BRANCH
             and campaign.get('delivery_deadline') == '2026-11-09T16:21:39Z'
             and campaign.get('old_consumed_scopes_remain_closed') is True
             and campaign.get('holdout_unsealing_authorized') is False
             and campaign.get('live_boundary_allowed') is False, 'Campaign boundary changed')
    return packet


def require_unused(root):
    folder = resolve_path(root, DIRECTORY)
    _require(not any((folder / name).exists() for name in (
        'attempt_claim.json', 'financial_decode_started.json', 'decoded_input.json',
        'accounts', 'statistics.json', 'result.json', 'outcome.json', 'guard_checks')),
        'Monthly attempt reserved or consumed; no resume')


def _admitted(root, *, unused=True):
    release_ref = _ref(root, RELEASE)
    release = _json(read_bound(root, release_ref, return_bytes=True))
    _require(set(release) == {'artifact_type', 'status', 'mode', 'registration', 'manager_review',
        'root_review', 'valid_from', 'expires_at'} and release['artifact_type'] == 'monthly_breadth_release_v1'
        and release['status'] == 'authorized_once' and release['mode'] == MODE, 'Separate monthly release required')
    for name, path in [('registration', REGISTRATION), ('manager_review', MANAGER_REVIEW), ('root_review', ROOT_REVIEW)]:
        _require(release[name]['path'] == path, 'Release reference path changed')
    packet = validate_registration(root, _json(read_bound(root, release['registration'], return_bytes=True)))
    _require(_time('2026-11-06T16:21:39Z') <= _time(release['valid_from']) <= _now()
             < _time(release['expires_at']) <= _time('2026-11-09T16:21:39Z'), 'Release expired or outside campaign')
    for name, reviewer in [('manager_review', 'quant_manager_72h'), ('root_review', 'root')]:
        r = _json(read_bound(root, release[name], return_bytes=True))
        _require(r.get('artifact_type') == 'monthly_breadth_exact_review_v1'
                 and r.get('status') == 'accepted_for_one_conditional_monthly_breadth'
                 and r.get('reviewer') == reviewer and r.get('mode') == MODE
                 and r.get('registration_sha256') == packet['registration_sha256']
                 and r.get('method_sha256') == packet['inputs']['monthly_method']['sha256']
                 and r.get('financial_execution_authorized') is True
                 and r.get('qualified') is False and type(r.get('real_forward')) is int
                 and r['real_forward'] == 0, 'Exact root and manager acceptance required')
    if unused:
        require_unused(root)
    return packet, release, release_ref


def _check_gate(root, packet, gate):
    age = (_now() - _time(gate['generated_at'])).total_seconds()
    safety = gate['safety']
    _require(0 <= age <= 120 and gate['status'] == 'ready' and not gate['blockers']
             and gate['primary_market'] == 'CN_ETF'
             and gate['selected'] == dict(machine='office_desktop', task='factor_review', branch=BRANCH, current_branch=BRANCH)
             and all(safety.get(k) is False for k in ('factor_batch_allowed', 'final_holdout_allowed', 'live_boundary_allowed')),
             'Fresh closed-boundary factor-review PM required')
    _require(not any(value is True for key, value in safety.items() if key.endswith('_allowed')),
             'Other source or financial scope must remain closed')
    reading = {r['path']: r for r in gate['required_reading']}
    _require(len(gate['required_reading']) == 7 and set(reading) == set(packet['protocols'])
             and all(r.get('status') == 'read' for r in reading.values()), 'PM reading set changed')
    for path, pin in packet['protocols'].items():
        raw = read_bound(root, pin, return_bytes=True)
        # Match PM's read_text universal-newline hash, while keeping raw pins.
        normalized = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
        _require(reading[path].get('sha256') == digest(normalized), 'PM normalized/raw reading binding mismatch')


def _persist(root, path, value):
    return normalizer._persist(root, path, value)


_TOKEN = object()


class _Claim:
    def __init__(self, root, packet, release, release_ref, claim_ref, token):
        _require(token is _TOKEN, 'Only durable new execution can issue a claim')
        self.root = Path(root).resolve()
        self.packet, self.release = packet, release
        self.release_ref, self.claim_ref = release_ref, claim_ref
        self.active, self.decoding_started, self.guard_count = True, False, 0

    def guard(self, phase, identity):
        _require(self.active, 'Claim closed')
        for ref in (self.release_ref, self.claim_ref):
            read_bound(self.root, dict(path=ref['path'], sha256=ref['sha256']))
        _require(_branch(self.root) == BRANCH, 'Execution branch changed')
        packet, release, release_ref = _admitted(self.root, unused=False)
        _require(canonical(packet) == canonical(self.packet) and canonical(release) == canonical(self.release)
                 and release_ref == self.release_ref, 'Frozen monthly admission changed')
        self.guard_count += 1
        _persist(self.root, resolve_path(self.root, DIRECTORY + f'/guard_checks/{self.guard_count:03}.json'),
                 dict(at=_now().isoformat(), phase=phase, identity=identity, all_frozen_refs_checked=True))

    def read(self, role):
        _require(self.active, 'Claim closed')
        return read_bound(self.root, self.packet['inputs'][role], return_bytes=True)

    def begin_financial_decode(self):
        _require(self.active and not self.decoding_started, 'One financial parser entry only')
        self.guard('before', 'numeric_marker')
        _persist(self.root, resolve_path(self.root, DIRECTORY + '/financial_decode_started.json'),
            dict(at=_now().isoformat(), registration_sha256=self.packet['registration_sha256'],
                 study_number=self.packet['policy']['study_number'], meaning='before_first_numeric_conversion',
                 old_study23_resumed=False, qualified=False, real_forward=0))
        self.decoding_started = True


@dataclass(frozen=True)
class LoadedInputs:
    fixture: dict
    provenance: dict
    context: object


def _month_ends(claim, dates):
    calendar = set()
    for role in ('retained_old_calendar', 'retained_calendar'):
        for row in csv.DictReader(io.StringIO(claim.read(role).decode('utf-8-sig'))):
            if row['is_open'] == '1':
                calendar.add(row['date'])
    all_days = sorted(calendar)
    _require([d for d in all_days if dates[0] <= d <= dates[-1]] == dates, 'Exact common calendar required')
    months = {}
    for d in all_days:
        months[d[:7]] = d
    ends = [d for _, d in sorted(months.items()) if d in dates]
    _require(len(ends) == 121 and ends[0] == '2013-12-31' and ends[12] == '2014-12-31'
             and ends[-1] == '2023-12-29', 'Exact completed month-end boundary required')
    i = dates.index(ends[12])
    _require(dates[i + 1:i + 3] == ['2015-01-05', '2015-01-06']
             and dates[-2:] == ['2023-12-29', '2024-01-02'], 'D+1/D+2 or terminal boundary changed')
    return ends


def load_claimed_inputs(claim):
    _require(type(claim) is _Claim and claim.active, 'Exact new production claim required')
    from quant_robot.research import monthly_breadth as kernel
    _require(Path(kernel.__file__).resolve() == resolve_path(claim.root, 'src/quant_robot/research/monthly_breadth.py'),
             'Loaded monthly kernel code root mismatch')
    _require(kernel.METHOD_SHA == METHOD_SHA, 'Kernel/economic method mismatch')
    dates = _json(claim.read('sessions'))
    ends = _month_ends(claim, dates)
    # Explicitly reuse only the private source normalization, under THIS claim.
    # Its marker is called immediately before its first _number conversion.
    data = normalizer._load_core(claim)
    _require(claim.decoding_started, 'Source normalizer must enter new numeric marker')
    fixture = dict(data.fixture)
    fixture.pop('event_indices')
    decisions = [dates.index(d) for d in ends[12:-1]]
    fixture.update(artifact_type='admitted_monthly_breadth_fixture_v1', month_end_sessions=ends,
        first_signal_index=dates.index(ends[12]), monthly_decision_indices=decisions,
        event_indices=[i + 1 for i in decisions], actions_complete=True)
    provenance = dict(data.provenance,
        old_source_normalizer=claim.packet['implementation']['src/quant_robot/research/equity_gold_constant_mix_historical.py'],
        source_method=claim.packet['inputs']['method'], economic_method=claim.packet['inputs']['monthly_method'],
        action_completeness_meaning='fixed_retrospective_conditional_table_not_all_vintage_certification',
        old_account_or_admission_called=False, old_study23_resumed=False)
    context = kernel._KnownHistoryContext(ASSETS, SOURCE, claim.packet['registration_sha256'],
        kernel.digest(fixture), kernel.digest(provenance))
    claim.guard('after', 'monthly_fixture_adapter')
    return LoadedInputs(fixture, provenance, context)


def _run_loaded(claim, data):
    from quant_robot.research import monthly_breadth as kernel
    frozen = digest(canonical(dict(fixture=data.fixture, provenance=data.provenance)))
    folder = resolve_path(claim.root, DIRECTORY)

    def guard(phase, identity):
        claim.guard(phase, identity)
        _require(digest(canonical(dict(fixture=data.fixture, provenance=data.provenance))) == frozen
                 and kernel.digest(data.fixture) == data.context.normalized_input_sha256
                 and kernel.digest(data.provenance) == data.context.provenance_sha256, 'Loaded snapshot changed')

    guard('before', 'decoded_snapshot')
    decoded = _persist(claim.root, folder / 'decoded_input.json', dict(fixture=data.fixture, provenance=data.provenance))
    accounts, annual = {}, {}
    jobs = [(f'min{m}_slip{s}/{p}', p, m, s) for m, s in POLICY['cost_cases'] for p in POLICIES]
    jobs.append(('cash', 'cash', 0, 0))
    for identity, policy, minimum, slip in jobs:
        guard('before', identity)
        target = folder / 'accounts' / identity
        _persist(claim.root, target / 'started.json', dict(at=_now().isoformat(), identity=identity))
        try:
            with localcontext(kernel.CONTEXT):
                prepared = kernel._prepare(data.fixture, context=data.context)
                result = kernel._run_prepared(prepared, policy, minimum, slip, context=data.context)
            artifact = _persist(claim.root, target / 'complete.json', result)
        except BaseException as exc:
            _persist(claim.root, target / 'failed.json', dict(error_type=type(exc).__name__, account_complete=False, qualified=False))
            raise
        guard('after', identity)
        accounts[identity] = dict(artifact=artifact, summary=result['summary'])
        if policy != 'cash':
            annual.setdefault(f'min{minimum}_slip{slip}', {})[policy] = result['annual_contributions']
    guard('before', 'statistics')
    statistics = kernel.paired_annual_bootstrap(annual, context=data.context)
    _require(statistics['N'] == 9 and statistics['replications'] == 5000
             and len(statistics['endpoint_keys']) == 27, 'Fixed monthly statistics shape required')
    stats_ref = _persist(claim.root, folder / 'statistics.json', statistics)
    guard('after', 'statistics')
    return dict(artifact_type=data.context.artifact('matrix'),
        registration_sha256=claim.packet['registration_sha256'], study_number=claim.packet['policy']['study_number'],
        source_nature=data.context.source_nature, test_injected_values=data.context.test_values,
        historical_returns_computed=data.context.returns_computed,
        old_study23_resumed=False, strategy_accounts=27, cash_controls=1, account_count=28,
        accounts=accounts, statistics=stats_ref, decoded_input_artifact=decoded,
        decoded_input_sha256=frozen, fixture_sha256=data.context.normalized_input_sha256,
        provenance_sha256=data.context.provenance_sha256, independently_verified=False,
        conditional_method_checks='pending_independent_saved_output_review',
        financial_verdict=data.context.verdict, qualified=False, real_forward=0)


def _final_artifacts(root, result):
    expected = {f'min{m}_slip{s}/{p}' for m, s in POLICY['cost_cases'] for p in POLICIES} | {'cash'}
    _require(set(result['accounts']) == expected, 'Exact 27 strategies plus one cash required')
    refs = [(DIRECTORY + '/accounts/' + i + '/complete.json', v['artifact']) for i, v in result['accounts'].items()]
    refs += [(DIRECTORY + '/statistics.json', result['statistics']), (DIRECTORY + '/decoded_input.json', result['decoded_input_artifact'])]
    for path, pin in refs:
        _require(pin['path'] == path and resolve_path(root, path).stat().st_size == pin['bytes'], 'Output path/size changed')
        read_bound(root, dict(path=path, sha256=pin['sha256']))


def execute(root, *, expected_registration_sha256, gate_supplier):
    root = Path(root).resolve()
    _execution_modules(root)
    packet, release, release_ref = _admitted(root)
    _require(_branch(root) == BRANCH and expected_registration_sha256 == packet['registration_sha256'], 'Exact branch and digest required')
    gate = gate_supplier()
    _check_gate(root, packet, gate)
    again = _admitted(root)
    _require(canonical(again) == canonical((packet, release, release_ref)), 'Admission changed during PM')
    folder = resolve_path(root, DIRECTORY)
    claim_ref = _persist(root, folder / 'attempt_claim.json', dict(at=_now().isoformat(),
        registration_sha256=expected_registration_sha256, reserved_study_number=packet['policy']['study_number'],
        gate=gate, mode=MODE, consumed_even_if_failed=True, new_release=release_ref, old_study23_resumed=False))
    claim = _Claim(root, packet, release, release_ref, claim_ref, _TOKEN)
    outcome = dict(status='failed_consumed', reserved_study_number=packet['policy']['study_number'],
        qualified=False, real_forward=0, historical_returns_computed=False, old_study23_resumed=False)
    try:
        claim.guard('before', 'source_normalization')
        result = _run_loaded(claim, load_claimed_inputs(claim))
        _require(claim.decoding_started and result['artifact_type'] == 'conditional_historical_monthly_breadth_matrix_v1'
                 and result['registration_sha256'] == expected_registration_sha256 and result['source_nature'] == SOURCE
                 and result['test_injected_values'] is False and result['qualified'] is False
                 and type(result['real_forward']) is int and result['real_forward'] == 0, 'Exact conditional result identity required')
        claim.guard('final', 'all_outputs')
        _final_artifacts(root, result)
        out_ref = _persist(root, folder / 'result.json', result)
        outcome.update(status='completed_conditional_accounts', account_count=28, historical_returns_computed=True, result=out_ref)
    except BaseException as exc:
        outcome['error_type'] = type(exc).__name__
        raise
    finally:
        outcome.update(financial_decode_started=claim.decoding_started, research_study_consumed=claim.decoding_started,
            study_number=packet['policy']['study_number'] if claim.decoding_started else None,
            registration_sha256=expected_registration_sha256, guard_checks=claim.guard_count, finished_at=_now().isoformat())
        claim.active = False
        _persist(root, folder / 'outcome.json', outcome)
    return outcome
