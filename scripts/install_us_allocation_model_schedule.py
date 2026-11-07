"""Prepare or register the exact finite USD model task, without starting it."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.ops.us_allocation_schedule import build_task_files, operation_dates

CHECKOUT = Path(__file__).resolve().parents[1]
DATA = Path('F:/lhjqr/data/reports/us_allocation_model_20261109_20261207')
PREPARATION = DATA / 'scheduled_task_preparation'
PYTHON = Path('F:/lhjqr/.venv/Scripts/python.exe')
POWERSHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def save(path, text):
    with path.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)
    return ref(path)


def literal(value): return "'" + str(value).replace("'", "''") + "'"


def prepare(scope_sha):
    scope = DATA / 'capture_scope.json'
    if ref(scope)['sha256'] != scope_sha:
        raise ValueError('Final capture scope changed')
    content = json.loads(scope.read_bytes())
    if content['operation_dates'] != operation_dates():
        raise ValueError('Only the fixed20scheduled sessions can be installed')
    sid = subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-Command',
        '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
        capture_output=True, text=True, check=True).stdout.strip()
    built = build_task_files(checkout=str(CHECKOUT), python=str(PYTHON), scope_path=str(scope),
                             scope_sha=scope_sha, preparation_dir=str(PREPARATION), user_sid=sid)
    PREPARATION.mkdir(parents=True, exist_ok=False)
    launcher = save(PREPARATION/'launch_model.ps1', built['launcher'])
    definition = save(PREPARATION/'model.task.xml', built['xml'])
    cli = ref(CHECKOUT/'scripts/run_us_allocation_daily_model_observer.py')
    receipt = PREPARATION/'registration_receipt.json'
    register = '\n'.join([
        "$ErrorActionPreference = 'Stop'",
        '$taskName = ' + literal(built['task_name']), '$taskPath = ' + literal(built['task_path']),
        "if (Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue) { throw 'Task already exists; no overwrite' }",
        "if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse('2026-11-09T14:30:00Z')) { throw 'Pre-opening installation window passed' }",
        "if ([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value -ne " + literal(sid) + ") { throw 'User SID changed' }",
        *["if ((Get-FileHash -LiteralPath " + literal(x['path']) + " -Algorithm SHA256).Hash.ToLowerInvariant() -ne " + literal(x['sha256']) + ") { throw 'Reviewed installation input changed' }" for x in (ref(scope), launcher, definition, cli)],
        '$xml = [System.IO.File]::ReadAllText(' + literal(definition['path']) + ')',
        '$task = Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Xml $xml -ErrorAction Stop',
        '$export = Export-ScheduledTask -TaskName $taskName -TaskPath $taskPath',
        '[System.IO.File]::WriteAllText(' + literal(PREPARATION/'registered.utf16.xml') + ',$export,[System.Text.Encoding]::Unicode)',
        '$exportPath = ' + literal(PREPARATION/'registered.utf16.xml'),
        "$exportRef = @{path=$exportPath;sha256=(Get-FileHash -LiteralPath $exportPath -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $exportPath).Length}",
        "@{schema='us_allocation_model_schedule_v1';installed=$true;task_name=$taskName;capture_scope_sha256=" + literal(scope_sha) + ";registered_at=[DateTimeOffset]::UtcNow.ToString('o');actual_export=$exportRef} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath " + literal(DATA/'schedule_registration.json') + ' -Encoding UTF8',
        '$info = Get-ScheduledTaskInfo -TaskName $taskName -TaskPath $taskPath',
        "[pscustomobject]@{at=[DateTimeOffset]::UtcNow.ToString('o');task_name=$taskName;task_path=$taskPath;state=$task.State.ToString();next_run_local=$info.NextRunTime.ToString('o');last_result=$info.LastTaskResult;registration_only=$true;source_requests=0;scheduled_sessions=20;requires_user_session=$true;missed_run_catch_up=$false;scope_sha256=" + literal(scope_sha) + '} | ConvertTo-Json | Set-Content -LiteralPath ' + literal(receipt) + ' -Encoding UTF8',
        'Get-Content -LiteralPath ' + literal(receipt) + ' -Encoding UTF8', '',
    ])
    register_ref = save(PREPARATION/'register_model.ps1', register)
    manifest = dict(schema='us_model_schedule_preparation_v1', at=datetime.now(timezone.utc).isoformat(),
                    task_name=built['task_name'], task_path=built['task_path'], user_sid=sid,
                    operation_dates=built['dates'], scope=ref(scope), python=ref(PYTHON),
                    files=[launcher, definition, cli, register_ref], register_script=register_ref['path'],
                    registration_performed=False, source_requests=0, requires_user_session=True)
    result = save(PREPARATION/'preparation.json', json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(preparation=result, registration_performed=False)))


def register(preparation_sha):
    manifest_path = PREPARATION/'preparation.json'
    if ref(manifest_path)['sha256'] != preparation_sha:
        raise ValueError('Reviewed preparation changed')
    manifest = json.loads(manifest_path.read_bytes())
    for item in manifest['files'] + [manifest['scope'], manifest['python']]:
        if ref(Path(item['path'])) != item:
            raise ValueError('Prepared file changed')
    subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
                    '-ExecutionPolicy', 'Bypass', '-File', manifest['register_script']], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare').add_argument('--scope-sha', required=True)
    commands.add_parser('register').add_argument('--preparation-sha', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.scope_sha)
    else: register(args.preparation_sha)


if __name__ == '__main__': main()
