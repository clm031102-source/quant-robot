"""Archive one current public macro curve page, after 18:05 China time."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.sources.chinabond_observation import capture_current_observation  # noqa: E402
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = capture_current_observation(repo_root=Path.cwd(), execute=args.execute,
            run_gate=lambda output: run_quant_pm_startup_gate(output_dir=output,
                machine=args.machine, task="factor_review", branch=args.branch))
    except (OSError, ValueError) as exc:
        result = {"status": "rejected", "failure_kind": type(exc).__name__,
                  "research_admission_granted": False}
    print(json.dumps(result, sort_keys=True, indent=2))
    benign = {"preview", "not_due", "observed_unqualified"}
    if result["status"] == "already_attempted":
        return 0 if result.get("previous_status") == "observed_unqualified" else 1
    return 0 if result["status"] in benign else 1


if __name__ == "__main__":
    raise SystemExit(main())
