"""Actual local PM/Git/UTC, fixed artificial evidence, no remote or account I/O."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import builtins
import io
import json
import os
from pathlib import Path
import stat
from time import perf_counter
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import paper_actual_pm_gate as actual
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_synthetic_capture_observe as pipeline
from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import tushare_live_transport as archive
from quant_robot.ops import tushare_daily_receipt as parser
from quant_robot.ops import paper_prospective_transport as v1
from tests.unit import test_frozen_candidate_deferred as fixtures
from tests.unit import test_paper_source_connection as source_fixtures
from tests.unit import test_paper_warmup_bundle as warmup_fixtures


def content_meter():
    """Count parent file I/O; allow only non-regular integer pipe descriptors.

    Git's bounded stdout pipe is IPC, not a document read. Its internal files and
    imports are excluded explicitly, not counted as zero physical filesystem I/O.
    """
    stack = ExitStack()
    counts = dict(opens=0, reads=0, bytes=0, confirmation_flushes=0, git_pipe_opens=0)
    raw_open, raw_read = os.open, os.read
    def opened(path, flags, *args, **kwargs):
        if not flags & getattr(os, 'O_DIRECTORY', 0):
            counts['opens'] += 1
        return raw_open(path, flags, *args, **kwargs)
    def read(*args, **kwargs):
        counts['reads'] += 1
        raw = raw_read(*args, **kwargs)
        counts['bytes'] += len(raw)
        return raw
    def buffered(original):
        def call(path, mode='r', *args, **kwargs):
            if 'r' in mode or '+' in mode:
                if isinstance(path, int) and not stat.S_ISREG(os.fstat(path).st_mode):
                    counts['git_pipe_opens'] += 1
                else:
                    raise AssertionError('unmetered buffered document read')
            return original(path, mode, *args, **kwargs)
        return call
    confirm = sessions._Child.confirm_durable
    def confirmed(*args, **kwargs):
        counts['confirmation_flushes'] += 1
        return confirm(*args, **kwargs)
    stack.enter_context(patch.object(os, 'open', side_effect=opened))
    stack.enter_context(patch.object(os, 'read', side_effect=read))
    stack.enter_context(patch.object(builtins, 'open', new=buffered(builtins.open)))
    stack.enter_context(patch.object(io, 'open', new=buffered(io.open)))
    stack.enter_context(patch.object(sessions._Child, 'confirm_durable', new=confirmed))
    return stack, counts


class ActualPMTests(TestCase):
    probes = []

    @classmethod
    def setUpClass(cls):
        from unittest import SkipTest
        try:
            actual._git_identity()
        except ValueError as exc:
            if str(exc) in {'actual_pm_independent_worktree_required', 'actual_pm_git_command_failed'}:
                raise SkipTest('Real-PM integration requires its actual isolated engineering branch') from None
            raise

    def fixture(self, deferred=True):
        # Author only artificial past prefix dates; the actual entry has no clock override.
        now = datetime.now(timezone.utc)
        day = (now + timedelta(hours=8)).date()
        while day.weekday() >= 5 or now < datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=8, minutes=2):
            day -= timedelta(days=1)
        observable = datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=7, minutes=30)
        if not observable <= now < observable + timedelta(days=1):
            self.skipTest('Actual UTC is outside this weekday-only artificial fixture window')
        anchor = day
        for _ in range(21):
            anchor -= timedelta(days=1)
            while anchor.weekday() >= 5:
                anchor -= timedelta(days=1)
        def fixture_date(*args):
            return anchor if args == (2020, 1, 2) else date(*args)
        case = source_fixtures.SourceConnectionTests()
        with patch.object(warmup_fixtures, 'date', side_effect=fixture_date):
            fixture = fixtures.G1Fixture(case, deferred=deferred)
        self.addCleanup(case.doCleanups)
        return fixture

    def ready(self):
        f = self.fixture()
        packet = f.packet(21)
        f.activate()
        f.decide(21)
        identity = actual._git_identity()
        scope = pipeline.prepare_synthetic_scope(f.journal, evidence_root=f.root,
            context=dict(machine='office_desktop', task='factor_review', branch=identity['branch']),
            now=forward._clock()[1])['result']
        f.f.save('capture_scope.json', scope)
        template = json.loads((f.root / packet['source_proof']['specification']['path']).read_bytes())
        del template['evidence']['price']
        f.f.save('capture_template.json', template)
        body = json.dumps(dict(code=0, msg=None, data=dict(fields=list(parser.FIELDS),
            items=[['510300.SH', f.f.days[21].replace('-', ''), 20.3, 21, 20, 20.3, 1000, 2030]]))).encode()
        return dict(f=f, scope=scope, template=f.ref('capture_template.json'),
                    response=pipeline.SyntheticResponse(body),
                    folder=f.root / v1.ARCHIVE / 'mock_requests' / v1.request_identity(scope))

    def operation(self, case):
        return sessions.EvidenceOperation(case['f'].root, policy=sessions.G1_SYNTHETIC_POLICY)

    def call(self, case, operation):
        return pipeline.capture_observe_actual_pm_synthetic(case['f'].root / 'capture_scope.json',
            evidence_root=case['f'].root, expected_scope_sha256=forward.digest(case['scope']),
            template_ref=case['template'], response=case['response'], operation=operation)

    def meter(self, label, op, counts, seconds):
        measured = op.measurements()
        self.assertEqual(counts['opens'], measured['open_attempts'])
        self.assertEqual(counts['reads'], measured['read_calls'])
        self.assertEqual(counts['bytes'], measured['io_bytes_returned'])
        self.probes.append(dict(label=label, seconds=seconds, external=dict(counts), internal=measured,
            actual_pm=op._pm_role().summary(), pm_application_content_io_measured=True,
            complete_capture_io_measured=False, python_import_io_measured=False,
            git_internal_file_io_measured=False))

    def test_actual_pm_five_stages_real_context_clocks_and_meter_account_parity(self):
        case = self.ready()
        old = self.fixture(False)
        packet = old.packet(21)
        old.activate()
        old.decide(21)
        expected = old.observe(21, packet)['payload']['account']
        op = self.operation(case)
        account = forward.run_allocation_account
        calls = []
        def counted(*args, **kwargs):
            calls.append(True)
            return account(*args, **kwargs)
        stack, counts = content_meter()
        started = perf_counter()
        with stack, patch.object(forward, 'run_allocation_account', side_effect=counted), \
             patch.object(archive, '_existing_token', side_effect=AssertionError('actual credentials')), \
             patch.object(archive, '_new_session', side_effect=AssertionError('actual HTTP')), \
             patch.object(pipeline, '_fixed_gate', side_effect=AssertionError('artificial PM')):
            result = self.call(case, op)
        self.meter('actual_pm_complete_one_day', op, counts, perf_counter() - started)
        self.assertEqual(result['result']['payload']['account'], expected)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result['actual_pm_executed'])
        self.assertEqual(result['actual_pm_calls'], 1)
        self.assertEqual(result['mock_gate_calls'], 0)
        self.assertEqual(result['mock_token_calls'], 1)
        self.assertEqual(result['mocked_requests_started'], 1)
        self.assertEqual(result['real_forward_days_added'], 0)
        self.assertFalse(result['production_admission'])
        self.assertFalse(result['complete_capture_io_measured'])
        self.assertFalse(result['pm_application_content_io_measured'])  # proof is the independent comparison above
        self.assertEqual(len(result['git_checks']), 10)
        self.assertEqual([r['stage'] for r in result['git_checks']], [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertEqual(len(op._stages), 5)
        for stage in result['measurements']['stages']:
            self.assertEqual(stage['state'], 'committed')
            for name in sessions._PM_DOCUMENTS:
                self.assertEqual(stage['per_path']['@pm/' + name]['opens'], 2)
            for name in sessions._PM_FILES:
                self.assertEqual(stage['per_path']['@code/' + name]['opens'], 2)
        self.assertFalse((case['f'].journal / '.writer.lock').exists())
        with self.assertRaisesRegex(ValueError, 'operation_stage_budget_exceeded'):
            op.stage()

    def test_signature_rejects_now_and_foreign_policy_before_content_reads(self):
        with self.assertRaises(TypeError):
            pipeline.capture_observe_actual_pm_synthetic('unused', evidence_root='unused',
                expected_scope_sha256='unused', template_ref={}, response=None, now='2020-01-01T00:00:00Z')
        case = self.ready()
        op = sessions.EvidenceOperation(case['f'].root)
        with self.assertRaisesRegex(ValueError, 'Exact five-stage'):
            self.call(case, op)
        self.assertEqual(op.measurements()['open_attempts'], 0)

    def test_changed_git_before_P1_commit_is_metered_and_has_no_claim(self):
        case = self.ready()
        op = self.operation(case)
        identity = actual._git_identity
        checks = []
        def changed():
            value = identity()
            checks.append(True)
            if len(checks) == 2:
                value['head'] = '0' * 40
            return value
        stack, counts = content_meter()
        started = perf_counter()
        with stack, patch.object(actual, '_git_identity', side_effect=changed), \
             patch.object(pipeline._Session, 'post', side_effect=AssertionError('request before stable Git')):
            with self.assertRaisesRegex(ValueError, 'actual_pm_git_authority_changed'):
                self.call(case, op)
        self.meter('P1_git_changed_before_claim', op, counts, perf_counter() - started)
        self.assertEqual(op.measurements()['state'], 'failed')
        self.assertFalse(case['folder'].exists())
        self.assertTrue((case['f'].journal / '.writer.lock').exists())

    def test_P5_git_change_preserves_publications_and_owned_guard(self):
        case = self.ready()
        op = self.operation(case)
        identity = actual._git_identity
        checks = []
        def changed():
            value = identity()
            checks.append(True)
            if len(checks) == 10:
                value['branch'] += '-changed'
            return value
        stack, counts = content_meter()
        started = perf_counter()
        with stack, patch.object(actual, '_git_identity', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'actual_pm_git_authority_changed'):
                self.call(case, op)
        self.meter('P5_git_changed_after_durability', op, counts, perf_counter() - started)
        self.assertEqual(op.measurements()['state'], 'failed')
        self.assertEqual(len(op._stages), 5)
        self.assertTrue((case['f'].journal / '00000004.json').exists())
        self.assertTrue((case['f'].journal / '.writer.lock').exists())
        with self.assertRaisesRegex(ValueError, 'operation_not_open'):
            op.stage()

    def test_pm_document_final_open_failure_is_charged_without_retry(self):
        case = self.ready()
        op = self.operation(case)
        opened = os.open
        seen = []
        target = actual._REPO / 'README.md'
        def failed(path, flags, *args, **kwargs):
            if Path(path).resolve() == target:
                seen.append(True)
                if len(seen) == 2:
                    raise OSError('injected PM final open failure')
            return opened(path, flags, *args, **kwargs)
        with patch.object(os, 'open', side_effect=failed):
            stack, counts = content_meter()
            started = perf_counter()
            with stack:
                with self.assertRaisesRegex(OSError, 'injected PM final open failure'):
                    self.call(case, op)
        self.meter('P1_pm_final_open_failure', op, counts, perf_counter() - started)
        final_file = op.measurements()['stages'][0]['per_path']['@pm/README.md']
        self.assertEqual(final_file['opens'], 2)
        self.assertEqual(final_file['bytes'], target.stat().st_size)
        self.assertEqual(op.measurements()['state'], 'failed')
        self.assertFalse(case['folder'].exists())

    def test_unknown_required_document_rejected_before_its_open_or_PM(self):
        case = self.ready()
        op = self.operation(case)
        read = sessions.EvidenceOperation._read
        labels = []
        def changed(current, stage, path, limit, label, **kwargs):
            labels.append(label)
            raw = read(current, stage, path, limit, label, **kwargs)
            if label == '@pm/configs/quant_pm_startup_gate_cn_etf.json':
                config = json.loads(raw)
                config['required_reading'].append(dict(path='data/raw/forbidden-extra.csv'))
                return json.dumps(config).encode()
            return raw
        with patch.object(sessions.EvidenceOperation, '_read', new=changed), \
             patch.object(actual.pm, 'build_quant_pm_startup_gate', side_effect=AssertionError('PM before closed graph')):
            with self.assertRaisesRegex(ValueError, 'actual_pm_dependency_outside_closed_graph'):
                self.call(case, op)
        self.assertFalse(any('forbidden-extra' in label for label in labels))
        self.assertFalse(case['folder'].exists())
        self.assertEqual(op.measurements()['state'], 'failed')

    def test_pm_raw_document_and_source_changes_fail_at_final_read(self):
        for target, failure in (('@pm/README.md', 'actual_pm_document_changed_at_final_read'),
                                ('@code/src/quant_robot/research/commodity_proxy_admission.py',
                                 'implementation_changed_at_final_read')):
            case = self.ready()
            op = self.operation(case)
            read = sessions.EvidenceOperation._read
            seen = []
            def changed(current, stage, path, limit, label, **kwargs):
                raw = read(current, stage, path, limit, label, **kwargs)
                if label == target:
                    seen.append(True)
                    if len(seen) == 2:
                        return raw + b' '
                return raw
            with self.subTest(target=target), patch.object(sessions.EvidenceOperation, '_read', new=changed):
                with self.assertRaisesRegex(ValueError, failure):
                    self.call(case, op)
            self.assertFalse(case['folder'].exists())
            self.assertTrue((case['f'].journal / '.writer.lock').exists())

    def test_stage_reopens_actual_documents_and_rejects_cross_stage_change(self):
        case = self.ready()
        op = self.operation(case)
        read = sessions.EvidenceOperation._read
        def changed(current, stage, path, limit, label, **kwargs):
            raw = read(current, stage, path, limit, label, **kwargs)
            if len(current._stages) == 2 and label == '@pm/README.md':
                return raw + b' '
            return raw
        with patch.object(sessions.EvidenceOperation, '_read', new=changed):
            with self.assertRaisesRegex(ValueError, 'actual_pm_inputs_or_code_changed_between_stages'):
                self.call(case, op)
        self.assertEqual([stage._state for stage in op._stages], ['committed', 'failed'])
        self.assertFalse(case['folder'].exists())

    def test_true_PM_blocker_and_expired_generated_clock_start_no_request(self):
        for mode in ('blocked', 'expired'):
            case = self.ready()
            op = self.operation(case)
            build = actual.pm.build_quant_pm_startup_gate
            def injected(*args, **kwargs):
                gate = build(*args, **kwargs)
                if mode == 'blocked':
                    gate.update(status='blocked', blockers=['injected-real-PM-blocker'])
                else:
                    gate['generated_at'] = (datetime.now(timezone.utc) - timedelta(seconds=121)).isoformat()
                return gate
            with self.subTest(mode=mode), patch.object(actual.pm, 'build_quant_pm_startup_gate', side_effect=injected), \
                 patch.object(pipeline._Session, 'post', side_effect=AssertionError('blocked or stale PM request')):
                with self.assertRaisesRegex(ValueError, 'fresh_project_startup_gate_blocked|startup_gate_not_fresh'):
                    self.call(case, op)
            self.assertFalse(case['folder'].exists())
            self.assertEqual(op.measurements()['state'], 'failed')

    def test_31_scopes_exit_without_financial_leaf_and_default_PM_matches(self):
        case = self.ready()
        op = self.operation(case)
        op._enable_actual_pm()
        stage = op.stage()
        from quant_robot.research import commodity_proxy_admission, commodity_proxy_repair_admission
        from quant_robot.research import crypto_monthly_admission, crypto_charge_monthly_admission
        with ExitStack() as stack:
            for module in (commodity_proxy_admission, commodity_proxy_repair_admission,
                           crypto_monthly_admission, crypto_charge_monthly_admission):
                stack.enter_context(patch.object(module, 'admitted_packet', side_effect=AssertionError('financial leaf')))
            measured = op._pm_role().run(stage, case['scope'])
            configs = [json.loads((actual._REPO / name).read_text(encoding='utf-8')) for name in
                ('configs/quant_pm_startup_gate_cn_etf.json', 'configs/workstations.json',
                 'configs/research_family_scheduler_cn_etf.json')]
            ordinary = actual.pm.build_quant_pm_startup_gate(gate_config=configs[0], workstations_config=configs[1],
                family_config=configs[2], repo_root=actual._REPO, machine='office_desktop', task='factor_review',
                branch=case['scope']['context']['branch'], current_branch=case['scope']['context']['branch'])
        def stable(value):
            if isinstance(value, dict):
                return {k: stable(v) for k, v in value.items() if k not in ('generated_at', 'actual_pm_execution')}
            if isinstance(value, list):
                return [stable(v) for v in value]
            return value
        self.assertEqual(stable(measured), stable(ordinary))
        self.assertEqual(measured['mode'], 'family_rotation_review_only')
        self.assertTrue(all(item['path'] in sessions._PM_DOCUMENTS for item in measured['required_reading']))
        op.close()

    def test_PM_text_normalization_and_raw_pins_remain_distinct(self):
        case = self.ready()
        op = self.operation(case)
        op._enable_actual_pm()
        stage = op.stage()
        # A small unit-only cached-byte fixture, not a physical document-I/O proof.
        raw = b'first\r\nsecond\rthird\n'
        stage._pm_documents['AGENTS.md'] = dict(raw=raw, sha256=forward.sha256(raw).hexdigest(), bytes=len(raw))
        row = actual.pm._reading_row(actual._REPO, dict(path='AGENTS.md'), _reader=op._pm_role())
        normalized = b'first\nsecond\nthird\n'
        self.assertEqual(row['sha256'], forward.sha256(normalized).hexdigest())
        self.assertEqual(row['bytes'], len(normalized))
        self.assertEqual(row['lines'], 3)
        self.assertNotEqual(row['sha256'], stage.pm_document_pins()['AGENTS.md']['sha256'])
        op.close()

    def test_financial_account_mode_is_blocked_before_comparison_reader(self):
        case = self.ready()
        op = self.operation(case)
        with patch.object(actual.pm, '_restricted_review_mode', return_value=dict(
                mode='injected_account_mode', scope=dict(net_account_allowed=True))), \
             patch.object(actual.pm, 'review_account_comparison', side_effect=AssertionError('financial comparison read')):
            with self.assertRaisesRegex(ValueError, 'actual_pm_financial_leaf_forbidden'):
                self.call(case, op)
        self.assertFalse(case['folder'].exists())
        self.assertFalse(op._pm_role().summary()['actual_pm_executed'])

    def test_consumed_request_is_metered_and_never_repeats_PM_or_mock_request(self):
        case = self.ready()
        self.call(case, self.operation(case))
        op = self.operation(case)
        stack, counts = content_meter()
        started = perf_counter()
        with stack, patch.object(actual.pm, 'build_quant_pm_startup_gate', side_effect=AssertionError('repeat PM')), \
             patch.object(pipeline._Session, 'post', side_effect=AssertionError('repeat request')):
            result = self.call(case, op)
        self.meter('existing_consumed_actual_pm', op, counts, perf_counter() - started)
        self.assertEqual(result['status'], 'already_consumed')
        self.assertFalse(result['actual_pm_executed'])
        self.assertEqual(result['mocked_requests_started'], 0)


class ActualPMBoundaryTests(TestCase):
    def test_foreign_import_origin_is_rejected_before_git_or_documents(self):
        import sys
        from types import SimpleNamespace
        with patch.dict(sys.modules, {'quant_robot.foreign_fixture': SimpleNamespace(__file__='C:/foreign/module.py')}):
            with self.assertRaisesRegex(ValueError, 'actual_pm_foreign_project_module'):
                actual._check_module_origins()

    def test_redirected_git_environment_fails_before_child(self):
        with patch.dict(os.environ, {'GIT_DIR': 'not-the-worktree'}), \
             patch.object(actual.subprocess, 'Popen', side_effect=AssertionError('redirected Git invoked')):
            with self.assertRaisesRegex(ValueError, 'actual_pm_git_environment_redirect_forbidden'):
                actual._git_command(['rev-parse', '--verify', 'HEAD'])

    def test_bounded_git_output_kills_child_without_retaining_unbounded_bytes(self):
        class Child:
            stdout = io.BytesIO(b'x' * 5000)
            killed = False
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def kill(self): self.killed = True
            def wait(self, **kwargs): return 0
        child = Child()
        with patch.object(actual.subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(ValueError, 'actual_pm_git_output_limit'):
                actual._git_command(['rev-parse', '--verify', 'HEAD'])
        self.assertTrue(child.killed)

    def test_git_timeout_kills_fixed_child(self):
        class Child:
            killed = False
            stdout = None
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def kill(self): self.killed = True
            def wait(self, **kwargs): return 0
        class Reader:
            joins = 0
            def __init__(self, **kwargs): pass
            def start(self): pass
            def join(self, *args): self.joins += 1
            def is_alive(self): return self.joins == 1
        child = Child()
        with patch.object(actual.subprocess, 'Popen', return_value=child), patch.object(actual, 'Thread', Reader):
            with self.assertRaisesRegex(ValueError, 'actual_pm_git_timeout'):
                actual._git_command(['rev-parse', '--verify', 'HEAD'])
        self.assertTrue(child.killed)

    def test_clock_regression_and_utc_monotonic_disagreement_fail(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            op = sessions.EvidenceOperation(directory, policy=sessions.G1_SYNTHETIC_POLICY)
            for shift, tick in ((-1, 1), (10, 1), (1, -1)):
                role = actual._ActualPMGate(op)
                now = datetime.now(timezone.utc)
                with patch.object(actual, '_utc', side_effect=[now, now + timedelta(seconds=shift)]), \
                     patch.object(actual.time, 'monotonic', side_effect=[100, 100 + tick]):
                    role._sample('first')
                    with self.assertRaisesRegex(ValueError, 'actual_pm_utc_monotonic_clock_violation'):
                        role._sample('second')
