"""Actual review-only PM inside the existing synthetic evidence operation.

Only application document/code reads are routed through the file meter. Python
imports and Git's internal filesystem reads are explicitly outside that claim.
The Git subprocess is a bounded read-only authority, never a trading transport.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Thread
import time

from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.research import pm_startup_gate as pm


_REPO = Path(__file__).resolve().parents[3]
_BRANCH_PREFIX = 'codex/factor-review-paper-actual-pm-'
_READING = tuple(name for name in sessions._PM_DOCUMENTS
                 if name != 'configs/quant_pm_startup_gate_cn_etf.json')


def _utc():
    return datetime.now(timezone.utc)


def _git_command(arguments):
    """Retain at most 4096 output bytes; stop the fixed child on overflow/time."""
    harmless = {'GIT_PAGER', 'GIT_TERMINAL_PROMPT'}
    if any(name.upper().startswith('GIT_') and name.upper() not in harmless for name in os.environ):
        raise ValueError('actual_pm_git_environment_redirect_forbidden')
    executable = shutil.which('git')
    if executable is None:
        raise ValueError('actual_pm_git_unavailable')
    chunks = []
    failures = []
    environment = {name: value for name, value in os.environ.items() if not name.upper().startswith('GIT_')}
    with subprocess.Popen([executable, '--no-optional-locks', '-C', str(_REPO), *arguments],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
                          env=environment,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)) as child:
        def read_pipe():
            size = 0
            try:
                while True:
                    raw = child.stdout.read(512)
                    if not raw:
                        return
                    if size + len(raw) > 4096:
                        failures.append('actual_pm_git_output_limit')
                        return
                    chunks.append(raw)
                    size += len(raw)
            except (OSError, ValueError):
                failures.append('actual_pm_git_pipe_failed')
        reader = Thread(target=read_pipe, daemon=True)
        reader.start()
        reader.join(5)
        if reader.is_alive() or failures:
            child.kill()
            child.wait(timeout=2)
            reader.join(2)
            if reader.is_alive():
                raise ValueError('actual_pm_git_reader_termination_unconfirmed')
            raise ValueError(failures[0] if failures else 'actual_pm_git_timeout')
        try:
            code = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)
            raise ValueError('actual_pm_git_timeout') from None
        if code != 0:
            raise ValueError('actual_pm_git_command_failed')
    try:
        value = b''.join(chunks).decode('utf-8').strip()
    except UnicodeDecodeError:
        raise ValueError('actual_pm_git_output_invalid') from None
    if not value or '\n' in value or '\r' in value:
        raise ValueError('actual_pm_git_output_invalid')
    return value


def _git_identity():
    root = Path(_git_command(['rev-parse', '--show-toplevel'])).resolve(strict=True)
    branch = _git_command(['symbolic-ref', '--quiet', '--short', 'HEAD'])
    head = _git_command(['rev-parse', '--verify', 'HEAD'])
    if (root != _REPO or not branch.startswith(_BRANCH_PREFIX)
            or not re.fullmatch(r'[a-zA-Z0-9._/-]+', branch)
            or not re.fullmatch(r'[a-f0-9]{40}', head)):
        raise ValueError('actual_pm_independent_worktree_required')
    return dict(root=str(root), branch=branch, head=head)


def _check_module_origins():
    for name, module in tuple(sys.modules.items()):
        if name == 'quant_robot' or name.startswith('quant_robot.'):
            filename = getattr(module, '__file__', None)
            if filename is None or not Path(filename).resolve().is_relative_to(_REPO / 'src'):
                raise ValueError('actual_pm_foreign_project_module')


class _ActualPMGate:
    """Fixed private role, attached before the operation opens its first stage."""
    def __init__(self, operation):
        if (type(operation) is not sessions.EvidenceOperation
                or operation._policy is not sessions.G1_SYNTHETIC_POLICY):
            raise ValueError('actual_pm_exact_g1_operation_required')
        self.operation = operation
        self.stage = None
        self.identity = None
        self.inputs = None
        self.code = None
        self.gate = None
        self.scope = None
        self.calls = 0
        self.passed = False
        self.records = []
        self.clock_checks = []
        self.last_clock = None

    def _sample(self, label):
        utc, tick = _utc(), time.monotonic()
        if self.last_clock is not None:
            old_utc, old_tick = self.last_clock
            elapsed = tick - old_tick
            if elapsed < 0 or utc < old_utc or abs((utc - old_utc).total_seconds() - elapsed) > 5:
                raise ValueError('actual_pm_utc_monotonic_clock_violation')
        if len(self.clock_checks) >= 32:
            raise ValueError('actual_pm_clock_check_budget_exceeded')
        self.last_clock = (utc, tick)
        sample = dict(label=label, utc=utc.isoformat(), monotonic=tick)
        self.clock_checks.append(sample)
        return sample

    def _authority(self, stage, label):
        before = self._sample(label + '_start')
        identity = _git_identity()
        after = self._sample(label + '_end')
        if self.identity is not None and identity != self.identity:
            raise ValueError('actual_pm_git_authority_changed')
        self.identity = identity
        if len(self.records) >= 10:
            raise ValueError('actual_pm_git_check_budget_exceeded')
        self.records.append(dict(stage=len(self.operation._stages), boundary=label,
                                 identity=dict(identity), before=before, after=after))

    def stage_start(self, stage):
        if (stage._operation is not self.operation or self.operation._active is not stage
                or type(stage) is not sessions.VerificationSession):
            raise ValueError('actual_pm_same_stage_required')
        _check_module_origins()
        self.stage = stage
        self._authority(stage, 'stage_start')
        code = stage.bind_implementation(sessions.PM_CATALOG)
        values = {name: stage.read_pm_document(name) for name in sessions._PM_DOCUMENTS}
        if self.inputs is not None and (values != self.inputs or code != self.code):
            raise ValueError('actual_pm_inputs_or_code_changed_between_stages')
        self.inputs, self.code = values, code
        # Reject new paths before PM or any convenience loader can access them.
        config = json.loads(self.read_text(_REPO, 'configs/quant_pm_startup_gate_cn_etf.json'))
        rows = config.get('required_reading')
        if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
                or tuple(row.get('path') for row in rows) != _READING
                or config.get('research_family_config') != 'configs/research_family_scheduler_cn_etf.json'):
            raise ValueError('actual_pm_dependency_outside_closed_graph')

    def read_text(self, root, name):
        if Path(root).resolve() != _REPO or self.stage is not self.operation._active:
            raise ValueError('actual_pm_reader_context_changed')
        # Same UTF-8 universal-newline semantics as Path.read_text, separate raw pin.
        return self.stage.read_pm_document(name).decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')

    def validate_call(self, root, gate, workstations, family, machine, task, branch, current_branch):
        expected = dict(machine='office_desktop', task='factor_review', branch=self.identity['branch'])
        if (self.scope is None or self.scope['context'] != expected or Path(root).resolve() != _REPO
                or (machine, task, branch, current_branch) !=
                ('office_desktop', 'factor_review', self.identity['branch'], self.identity['branch'])):
            raise ValueError('actual_pm_context_mismatch')
        for value, name in ((gate, 'configs/quant_pm_startup_gate_cn_etf.json'),
                            (workstations, 'configs/workstations.json'),
                            (family, 'configs/research_family_scheduler_cn_etf.json')):
            if not isinstance(value, dict) or not value or value != json.loads(self.read_text(root, name)):
                raise ValueError('actual_pm_actual_configuration_required')

    def validate_mode(self, mode, scope):
        if '_account_' in mode or scope.get('net_account_allowed') is True:
            raise ValueError('actual_pm_financial_leaf_forbidden')

    def run(self, stage, scope):
        if self.calls or stage is not self.stage or stage is not self.operation._active:
            raise ValueError('actual_pm_one_real_call_required')
        self.scope = json.loads(json.dumps(scope))
        config, workstations, family = (json.loads(self.read_text(_REPO, name)) for name in
            ('configs/quant_pm_startup_gate_cn_etf.json', 'configs/workstations.json',
             'configs/research_family_scheduler_cn_etf.json'))
        started = self._sample('actual_pm_start')
        self.calls += 1
        gate = pm.build_quant_pm_startup_gate(gate_config=config, workstations_config=workstations,
            family_config=family, repo_root=_REPO, machine=scope['context']['machine'],
            task=scope['context']['task'], branch=scope['context']['branch'],
            current_branch=self.identity['branch'], _reader=self)
        finished = self._sample('actual_pm_end')
        gate['actual_pm_execution'] = dict(started=started, finished=finished,
            git_identity=dict(self.identity), raw_documents=stage.pm_document_pins(),
            pm_application_content_io_routed=True, python_import_io_measured=False,
            git_internal_file_io_measured=False, complete_capture_io_measured=False)
        self.gate = gate
        self._fresh()
        self.passed = True
        return gate

    def _fresh(self):
        if self.gate is not None:
            from quant_robot.ops import tushare_live_transport as archive
            sampled = self._sample('gate_fresh')
            archive._gate_ready(self.gate, self.scope, datetime.fromisoformat(sampled['utc']))

    def before_commit(self, stage):
        if stage is not self.stage:
            raise ValueError('actual_pm_same_stage_required')
        self._authority(stage, 'before_commit')
        self._fresh()

    def summary(self):
        return dict(actual_pm_executed=self.passed, actual_pm_calls=self.calls,
            actual_pm_returned=self.gate is not None,
            actual_pm_status=self.gate.get('status') if self.gate is not None else None,
            pm_application_content_io_routed=True, pm_application_content_io_measured=False,
            independent_meter_comparison_required=True, complete_capture_io_measured=False,
            python_import_io_measured=False, git_internal_file_io_measured=False,
            git_checks=json.loads(json.dumps(self.records)),
            actual_utc_monotonic_samples=json.loads(json.dumps(self.clock_checks)),
            actual_credentials=0, real_network_requests=0)
