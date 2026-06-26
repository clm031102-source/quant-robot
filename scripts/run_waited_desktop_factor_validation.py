from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

try:
    from scripts.run_desktop_factor_validation import run_desktop_factor_validation
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from run_desktop_factor_validation import run_desktop_factor_validation


DEFAULT_CONFIG_PATH = Path("configs/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json")
DEFAULT_DATA_ROOT = Path("configs/cn_stock_authority_bars_2015_2025.json")
DEFAULT_LOG_PATH = Path("data/reports/automation/waited_desktop_factor_validation.log")
DEFAULT_SUMMARY_PATH = Path("data/reports/automation/waited_desktop_factor_validation_summary.json")


def run_waited_desktop_factor_validation(
    *,
    wait_pids: Iterable[int] = (),
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    source: str = "processed-bars",
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path | None = None,
    require_accepted: bool = False,
    log_path: str | Path = DEFAULT_LOG_PATH,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    poll_seconds: float = 300.0,
    is_running: Callable[[int], bool] | None = None,
    sleep: Callable[[float], None] | None = None,
    runner: Callable[..., dict[str, object]] | None = None,
    timestamp: Callable[[], str] | None = None,
) -> dict[str, object]:
    is_running = is_running or _process_is_running
    sleep = sleep or time.sleep
    runner = runner or run_desktop_factor_validation
    timestamp = timestamp or _timestamp
    resolved_pids = [int(pid) for pid in wait_pids]
    resolved_config = Path(config_path)
    resolved_data_root = Path(data_root)
    resolved_output = Path(output_dir) if output_dir is not None else None
    resolved_log = Path(log_path)
    resolved_summary = Path(summary_path)
    _log(resolved_log, timestamp, f"queue_started wait_pids={resolved_pids} config={resolved_config}")

    for pid in resolved_pids:
        while is_running(pid):
            _log(resolved_log, timestamp, f"waiting_for_pid={pid}")
            sleep(poll_seconds)
        _log(resolved_log, timestamp, f"pid_finished={pid}")

    _log(resolved_log, timestamp, f"validation_started config={resolved_config}")
    result = runner(
        config_path=resolved_config,
        source=source,
        data_root=resolved_data_root,
        output_dir=resolved_output,
        require_accepted=require_accepted,
    )
    summary = {
        "config_path": str(resolved_config),
        "data_root": str(resolved_data_root),
        "generated_at": timestamp(),
        "output_dir": str(resolved_output) if resolved_output is not None else None,
        "source": source,
        "validation_summary": result.get("summary", {}) if isinstance(result, dict) else {},
        "waited_pids": resolved_pids,
    }
    resolved_summary.parent.mkdir(parents=True, exist_ok=True)
    resolved_summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    _log(resolved_log, timestamp, f"validation_finished summary_path={resolved_summary}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Wait for existing validation PIDs, then run desktop factor validation.")
    parser.add_argument("--wait-pid", dest="wait_pids", action="append", type=int, default=[])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output-dir")
    parser.add_argument("--require-accepted", action="store_true")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--poll-seconds", type=float, default=300.0)
    args = parser.parse_args()
    result = run_waited_desktop_factor_validation(
        wait_pids=args.wait_pids,
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        require_accepted=args.require_accepted,
        log_path=Path(args.log_path),
        summary_path=Path(args.summary_path),
        poll_seconds=args.poll_seconds,
    )
    print(json.dumps({"summary": result.get("summary", {})}, indent=2, sort_keys=True))


def _log(path: Path, timestamp: Callable[[], str], message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp()} {message}\n")


def _process_is_running(pid: int) -> bool:
    try:
        import psutil  # type: ignore

        return psutil.pid_exists(pid)
    except ImportError:  # pragma: no cover - fallback for minimal envs
        pass
    try:
        if hasattr(os, "kill"):
            os.kill(pid, 0)
            return True
    except OSError:
        if os.name == "nt":
            return _windows_pid_exists(pid)
        return False
    return _windows_pid_exists(pid) if os.name == "nt" else False


def _windows_pid_exists(pid: int) -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    if result.returncode != 0:
        return False
    needle = f'"{int(pid)}"'
    return any(needle in line for line in result.stdout.splitlines())


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
