"""Supervise an existing synthetic journal from a local observation file."""
from __future__ import annotations

import argparse
from datetime import timedelta
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.execution.offline_intent_contract import instant
from quant_robot.execution.offline_runtime import OfflineRuntime, read_observation, run_loop, validate_loop_limits
from quant_robot.storage.atomic import atomic_write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--feed", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--fixture-clock-start")
    parser.add_argument("--fixture-step-seconds", type=float, default=1.0)
    args = parser.parse_args()
    try:
        validate_loop_limits(args.interval_seconds, args.max_ticks)
    except ValueError as exc:
        parser.error(str(exc))
    if args.journal.resolve() == args.feed.resolve():
        parser.error("journal and observation feed must be separate files")
    protected = {args.journal.resolve(), args.feed.resolve(), Path(str(args.journal.resolve()) + ".driver.lock")}
    if args.report and args.report.resolve() in protected:
        parser.error("the runtime report cannot replace an input or the driver lease")
    if args.fixture_clock_start and args.max_ticks is None:
        parser.error("a synthetic fixture clock requires a finite --max-ticks")
    if not 0 < args.fixture_step_seconds <= 86400:
        parser.error("fixture step must be positive and at most one day")
    logical = instant(args.fixture_clock_start) if args.fixture_clock_start else None

    def record(report):
        nonlocal logical
        report["clock_mode"] = "synthetic_fixture" if logical is not None else "system_utc"
        if args.report:
            atomic_write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        if logical is not None:
            logical += timedelta(seconds=args.fixture_step_seconds)

    with OfflineRuntime(args.journal, clock=(lambda: logical) if logical is not None else None) as runtime:
        run_loop(runtime, lambda: read_observation(args.feed), interval_seconds=args.interval_seconds,
            max_ticks=args.max_ticks, on_tick=record)


if __name__ == "__main__":
    main()
