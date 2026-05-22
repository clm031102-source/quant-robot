from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: list[str]
    uses_network: bool = False


def build_check_plan(python_executable: str = sys.executable) -> list[CheckStep]:
    return [
        CheckStep("unit_and_integration_tests", [python_executable, "-m", "unittest", "discover", "-s", "tests"]),
        CheckStep("compile_python", [python_executable, "-m", "compileall", "-q", "src", "scripts", "tests"]),
        CheckStep("project_audit", [python_executable, "scripts/run_project_audit.py", "--json"]),
        CheckStep("readiness_check", [python_executable, "scripts/check_readiness.py"]),
        CheckStep("provider_status", [python_executable, "scripts/show_provider_status.py"]),
        CheckStep("data_catalog", [python_executable, "scripts/show_data_catalog.py", "--root", "data", "--summary-only"]),
        CheckStep("fixture_research", [python_executable, "scripts/run_fixture_research.py"]),
        CheckStep("research_pipeline", [python_executable, "scripts/run_research_pipeline.py", "--source", "fixture"]),
        CheckStep("experiment_grid", [python_executable, "scripts/run_experiment_grid.py", "--source", "fixture"]),
        CheckStep("walk_forward", [python_executable, "scripts/run_walk_forward.py", "--source", "fixture"]),
        CheckStep("signal_snapshot", [python_executable, "scripts/run_signal_snapshot.py", "--source", "fixture"]),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Quant Robot checks.")
    parser.add_argument("--execute", action="store_true", help="Run checks instead of printing the plan.")
    args = parser.parse_args()
    plan = build_check_plan()
    if not args.execute:
        print(json.dumps([asdict(step) for step in plan], indent=2))
        return
    for step in plan:
        print(f"==> {step.name}", flush=True)
        subprocess.run(step.command, check=True)


if __name__ == "__main__":
    main()
