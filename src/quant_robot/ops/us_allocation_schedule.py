"""Finite Windows task preparation; no prices, registration, or model execution."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import PureWindowsPath
import re
import subprocess
import xml.etree.ElementTree as ET

TASK_NAME = 'USDAllocationConditionalModel_20261109_20261207'
TASK_PATH = '\\QuantRobot\\'
NS = 'http://schemas.microsoft.com/windows/2004/02/mit/task'
ET.register_namespace('', NS)


def operation_dates():
    first, last = date(2026, 11, 9), date(2026, 12, 7)
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)
            if (first + timedelta(days=i)).weekday() < 5
            and (first + timedelta(days=i)).isoformat() != '2026-11-26']


def _windows_path(value):
    path = PureWindowsPath(value)
    if not path.is_absolute() or any(c in str(path) for c in '\r\n"'):
        raise ValueError('Absolute Windows path required')
    return str(path)


def _literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def build_task_files(*, checkout, python, scope_path, scope_sha, preparation_dir, user_sid):
    """Return reviewable text. This function cannot install or start a task."""
    checkout, python, scope_path, preparation_dir = map(_windows_path, (checkout, python, scope_path, preparation_dir))
    if not re.fullmatch('[0-9a-f]{64}', scope_sha) or not re.fullmatch(r'S-1-(?:\d+-)*\d+', user_sid):
        raise ValueError('Exact scope hash and Windows SID required')
    script = str(PureWindowsPath(checkout) / 'scripts/run_us_allocation_daily_model_observer.py')
    launcher = str(PureWindowsPath(preparation_dir) / 'launch_model.ps1')
    logs = str(PureWindowsPath(preparation_dir).parent / 'task_attempt_logs')
    arguments = subprocess.list2cmdline(['-P', script, 'observe', '--scope', scope_path, '--scope-sha', scope_sha])
    launch_text = '\n'.join([
        "$ErrorActionPreference = 'Stop'",
        '$python = ' + _literal(python),
        '$checkout = ' + _literal(checkout),
        '$scope = ' + _literal(scope_path),
        '$scopeHash = ' + _literal(scope_sha),
        "if ((Get-FileHash -LiteralPath $scope -Algorithm SHA256).Hash.ToLowerInvariant() -ne $scopeHash) { throw 'Scope changed' }",
        '$arguments = ' + _literal(arguments),
        '$logDir = ' + _literal(logs),
        "[System.IO.Directory]::CreateDirectory($logDir) | Out-Null",
        "$attempt = [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '_' + [guid]::NewGuid().ToString('N')",
        "$env:PYTHONPATH = Join-Path $checkout 'src'",
        "$env:PYTHONDONTWRITEBYTECODE = '1'",
        "$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $checkout -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir ($attempt + '.stdout.log')) -RedirectStandardError (Join-Path $logDir ($attempt + '.stderr.log'))",
        "if (-not $process.WaitForExit(270000)) { $process.Kill(); $process.WaitForExit(); exit 124 }",
        'exit $process.ExitCode', '',
    ])
    def child(parent, tag, value=None, **attrs):
        node = ET.SubElement(parent, '{'+NS+'}'+tag, attrs)
        if value is not None: node.text = value
        return node
    task = ET.Element('{'+NS+'}Task', version='1.4')
    registration = child(task, 'RegistrationInfo')
    child(registration, 'URI', TASK_PATH + TASK_NAME)
    child(registration, 'Description', '20 scheduled completed-day conditional model observations; no broker or orders; no missed-run catch-up.')
    triggers = child(task, 'Triggers')
    for day in operation_dates():
        clock = '18:15:00' if day == '2026-11-27' else '21:15:00'
        start = datetime.fromisoformat(day+'T'+clock).replace(tzinfo=timezone.utc)
        trigger = child(triggers, 'TimeTrigger')
        child(trigger, 'StartBoundary', start.isoformat().replace('+00:00', 'Z'))
        child(trigger, 'EndBoundary', (start+timedelta(minutes=5)).isoformat().replace('+00:00', 'Z'))
        child(trigger, 'Enabled', 'true')
    principal = child(child(task, 'Principals'), 'Principal', id='CurrentUser')
    child(principal, 'UserId', user_sid)
    child(principal, 'LogonType', 'InteractiveToken')
    child(principal, 'RunLevel', 'LeastPrivilege')
    settings = child(task, 'Settings')
    values = dict(MultipleInstancesPolicy='IgnoreNew', DisallowStartIfOnBatteries='false',
                  StopIfGoingOnBatteries='false', AllowHardTerminate='true', StartWhenAvailable='false',
                  RunOnlyIfNetworkAvailable='false', AllowStartOnDemand='false', Enabled='true',
                  Hidden='true', RunOnlyIfIdle='false', WakeToRun='false', ExecutionTimeLimit='PT5M', Priority='7')
    for tag, value in values.items(): child(settings, tag, value)
    action = child(child(task, 'Actions', Context='CurrentUser'), 'Exec')
    child(action, 'Command', 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe')
    child(action, 'Arguments', subprocess.list2cmdline(['-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',launcher]))
    child(action, 'WorkingDirectory', checkout)
    ET.indent(task, space='  ')
    return dict(task_name=TASK_NAME, task_path=TASK_PATH, dates=operation_dates(),
                launcher=launch_text, xml=ET.tostring(task, encoding='unicode', xml_declaration=True),
                scope_sha256=scope_sha, requires_user_session=True, missed_run_catch_up=False,
                launch_path=launcher, registration_performed=False)
