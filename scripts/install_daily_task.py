"""Register a single, reliable Windows Scheduled Task for daily paper-trading updates.

Points directly to the main repo checkout (never a temporary worktree) and runs with
fault-tolerant retries and automatic multi-day catch-up if the PC was offline.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register or remove Quant Robot Windows daily paper task.")
    parser.add_argument("--repo-root", default=r"F:\lhjqr", help="Main repository directory")
    parser.add_argument("--task-name", default=r"\QuantRobot\DailyPaperUpdate")
    parser.add_argument("--time", default="07:30", help="Daily local run time HH:MM (after US close & before CN open)")
    parser.add_argument("--remove", action="store_true", help="Unregister task instead of installing")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        raise SystemExit("Windows Task Scheduler registration is only supported on Windows.")

    if args.remove:
        res = subprocess.run(["schtasks", "/Delete", "/TN", args.task_name, "/F"], check=False)
        return res.returncode

    repo = Path(args.repo_root).resolve()
    python_exe = repo / ".venv" / "Scripts" / "python.exe"
    script_path = repo / "scripts" / "run_paper_daily.py"
    if not python_exe.is_file():
        raise SystemExit(f"Python venv not found: {python_exe}")
    if not script_path.is_file():
        raise SystemExit(f"Script not found: {script_path}")

    log_dir = repo / "data" / "reports" / "scheduled_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    launcher = log_dir / "run_daily_paper.ps1"
    launcher.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                f"Set-Location '{repo}'",
                f"$env:PYTHONPATH = '{repo / 'src'}'",
                f"$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'",
                f"$log = '{log_dir}\\' + $stamp + '.log'",
                f"& '{python_exe}' '{script_path}' *>&1 | Out-File -FilePath $log -Encoding utf8",
                "exit $LASTEXITCODE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tr = f'powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{launcher}"'
    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        args.task_name,
        "/TR",
        tr,
        "/SC",
        "DAILY",
        "/ST",
        args.time,
        "/F",
    ]
    res = subprocess.run(cmd, check=True)
    print(f"Registered Windows Scheduled Task {args.task_name} at {args.time} daily -> {launcher}")
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
