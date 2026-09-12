"""Run one independently monitored synthetic worker; no broker connection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.execution.offline_intent_contract import instant
from quant_robot.execution.offline_runtime import validate_loop_limits
from quant_robot.execution.offline_runtime_health import ensure_distinct_paths, protected_paths, seconds
from quant_robot.execution.offline_supervisor import launch_owned_python, supervise_worker, validate_supervisor_limits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--feed", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worker-report", type=Path)
    parser.add_argument("--health", type=Path)
    parser.add_argument("--permit", type=Path)
    parser.add_argument("--interval-seconds", type=float, default=1)
    parser.add_argument("--poll-seconds", type=float, default=.25)
    parser.add_argument("--startup-seconds", type=float, default=10)
    parser.add_argument("--stall-seconds", type=float, default=5)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--fixture-clock-start")
    parser.add_argument("--fixture-step-seconds", type=float, default=1)
    args = parser.parse_args()
    health = args.health or Path(str(args.report.resolve()) + ".worker.json")
    permit = args.permit or Path(str(args.report.resolve()) + ".permit.json")
    try:
        validate_loop_limits(args.interval_seconds, args.max_ticks)
        validate_supervisor_limits(args.interval_seconds, args.poll_seconds, args.startup_seconds, args.stall_seconds)
        seconds(args.fixture_step_seconds, "fixture step", maximum=86400)
        ensure_distinct_paths({**protected_paths(args.journal, args.feed), "report": args.report,
            "worker_report": args.worker_report, "health": health, "permit": permit})
        if args.fixture_clock_start:
            instant(args.fixture_clock_start)
            if args.max_ticks is None:
                raise ValueError("a synthetic fixture clock requires a finite --max-ticks")
    except ValueError as exc:
        parser.error(str(exc))

    def launch(binding):
        command = [sys.executable, str(Path(__file__).resolve().with_name("run_offline_runtime.py")),
            "--journal", str(args.journal.resolve()), "--feed", str(args.feed.resolve()),
            "--health", binding["health_path"], "--instance-id", binding["instance_id"],
            "--supervisor-permit", binding["permit_path"], "--supervisor-pid", str(binding["supervisor_pid"]),
            "--supervisor-genesis", binding["genesis_hash"], "--supervisor-max-age", str(binding["max_age_seconds"]),
            "--interval-seconds", str(args.interval_seconds)]
        if args.max_ticks is not None:
            command += ["--max-ticks", str(args.max_ticks)]
        if args.fixture_clock_start:
            command += ["--fixture-clock-start", args.fixture_clock_start, "--fixture-step-seconds", str(args.fixture_step_seconds)]
        if args.worker_report:
            command += ["--report", str(args.worker_report.resolve())]
        return launch_owned_python(command[1:])

    result = supervise_worker(args.journal, health_path=health, permit_path=permit, report_path=args.report,
        launch=launch, interval_seconds=args.interval_seconds, poll_seconds=args.poll_seconds,
        startup_seconds=args.startup_seconds, stall_seconds=args.stall_seconds)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["phase"] == "stopped" and not result.get("evidence_write_error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
