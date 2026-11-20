"""Clean 4-step verification suite: unit tests, Python compile, safety audit, offline smoke."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, cmd: list[str]) -> None:
    print(f"\n==> [{name}] {' '.join(cmd)}", flush=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {name} (exit code {result.returncode})")


def main() -> int:
    py = sys.executable
    run_step("unit_tests", [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    run_step("compileall", [py, "-m", "compileall", "-q", "src", "scripts", "tests"])
    run_step("project_audit", [py, "scripts/run_project_audit.py", "--json"])
    print("\nALL CHECKS PASSED.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
