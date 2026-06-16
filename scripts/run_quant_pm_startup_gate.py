from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from scripts.start_task_context import load_config  # noqa: E402
from quant_robot.research.pm_startup_gate import (  # noqa: E402
    build_quant_pm_startup_gate,
    load_quant_pm_gate_config,
    write_quant_pm_startup_gate,
)


DEFAULT_CONFIG = Path("configs/quant_pm_startup_gate_cn_etf.json")
DEFAULT_WORKSTATIONS_CONFIG = Path("configs/workstations.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/quant_pm_startup_gate")


def run_quant_pm_startup_gate(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    workstations_config_path: str | Path = DEFAULT_WORKSTATIONS_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    machine: str | None = None,
    task: str | None = None,
    branch: str | None = None,
) -> dict[str, object]:
    gate_config = load_quant_pm_gate_config(config_path)
    workstations_config = load_config(workstations_config_path)
    current_branch = _git(["branch", "--show-current"])
    pack = build_quant_pm_startup_gate(
        gate_config=gate_config,
        workstations_config=workstations_config,
        repo_root=Path("."),
        machine=machine,
        task=task,
        branch=branch,
        current_branch=current_branch,
    )
    write_quant_pm_startup_gate(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Quant PM startup gate before factor research.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--workstations-config", default=str(DEFAULT_WORKSTATIONS_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--branch")
    args = parser.parse_args()
    pack = run_quant_pm_startup_gate(
        config_path=args.config,
        workstations_config_path=args.workstations_config,
        output_dir=args.output_dir,
        machine=args.machine,
        task=args.task,
        branch=args.branch,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "selected": pack["selected"],
                "primary_market": pack["primary_market"],
                "reading_summary": pack["reading_summary"],
                "research_family_summary": pack["research_family_schedule"]["summary"],
                "blockers": pack["blockers"],
                "warnings": pack["warnings"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return result.stderr.strip()
    return result.stdout.strip()


if __name__ == "__main__":
    main()
