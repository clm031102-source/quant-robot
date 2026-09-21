"""Supervise an existing synthetic journal from a local observation file."""
from __future__ import annotations

import argparse
from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.execution.offline_intent_contract import instant
from quant_robot.execution.offline_runtime import OfflineRuntime, read_observation, run_loop, validate_loop_limits
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.execution.offline_runtime_health import (
    SupervisorPermit, WorkerHealth, ensure_distinct_paths, journal_identity, protected_paths, seconds,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--feed", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--health", type=Path)
    parser.add_argument("--instance-id")
    parser.add_argument("--supervisor-permit", type=Path)
    parser.add_argument("--supervisor-pid", type=int)
    parser.add_argument("--supervisor-genesis")
    parser.add_argument("--supervisor-max-age", type=float, default=5)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--fixture-clock-start")
    parser.add_argument("--fixture-step-seconds", type=float, default=1.0)
    args = parser.parse_args()
    try:
        validate_loop_limits(args.interval_seconds, args.max_ticks)
        seconds(args.supervisor_max_age, "supervisor max age")
        health_path = args.health or Path(str(args.journal.resolve()) + ".health.json")
        ensure_distinct_paths({**protected_paths(args.journal, args.feed), "report": args.report,
            "health": health_path, "supervisor_permit": args.supervisor_permit})
    except ValueError as exc:
        parser.error(str(exc))
    supervised = args.supervisor_permit is not None
    binding_requested = any(value is not None for value in (args.supervisor_permit, args.supervisor_pid, args.supervisor_genesis))
    if binding_requested and not all(value is not None for value in (args.supervisor_permit, args.supervisor_pid, args.supervisor_genesis, args.instance_id)):
        parser.error("supervision requires a complete process, instance and journal binding")
    if supervised and args.supervisor_pid <= 0:
        parser.error("supervisor process id must be positive")
    instance_id = args.instance_id or uuid4().hex
    if len(instance_id) != 32 or any(c not in "0123456789abcdef" for c in instance_id):
        parser.error("instance id must contain 32 lowercase hexadecimal characters")
    if args.fixture_clock_start and args.max_ticks is None:
        parser.error("a synthetic fixture clock requires a finite --max-ticks")
    if not 0 < args.fixture_step_seconds <= 86400:
        parser.error("fixture step must be positive and at most one day")
    logical = instant(args.fixture_clock_start) if args.fixture_clock_start else None
    identity = journal_identity(args.journal)
    if supervised and identity["genesis_hash"] != args.supervisor_genesis:
        parser.error("supervisor journal identity mismatch")
    guard = SupervisorPermit(args.supervisor_permit, instance_id=instance_id, **identity,
        process_id=args.supervisor_pid, max_age_seconds=args.supervisor_max_age) if supervised else None
    health = WorkerHealth(health_path, instance_id=instance_id, **identity)

    def record(report):
        nonlocal logical
        report["clock_mode"] = "synthetic_fixture" if logical is not None else "system_utc"
        if args.report:
            atomic_write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        health.complete_tick(report)
        if logical is not None:
            logical += timedelta(seconds=args.fixture_step_seconds)

    with OfflineRuntime(args.journal, clock=(lambda: logical) if logical is not None else None, admission_guard=guard) as runtime:
        try:
            health.publish("starting")
            run_loop(runtime, lambda: read_observation(args.feed), interval_seconds=args.interval_seconds,
                max_ticks=args.max_ticks, on_tick=record, on_tick_start=health.start_tick)
            health.publish("stopped")
        except BaseException as exc:
            runtime.book.note_runtime_supervision_fault("runtime or health publication failed: " + str(exc)[:400])
            try:
                health.publish("failed", error=str(exc)[:500])
            except OSError:
                pass
            raise


if __name__ == "__main__":
    main()
