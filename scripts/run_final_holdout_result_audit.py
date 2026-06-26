from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.final_holdout_result_audit import (  # noqa: E402
    build_final_holdout_result_audit,
    write_final_holdout_result_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/final_holdout_result_audit")


def run_final_holdout_result_audit(
    *,
    report_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    audit = build_final_holdout_result_audit(report)
    write_final_holdout_result_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit final-holdout fold results for accepted factor candidates.")
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    audit = run_final_holdout_result_audit(report_path=args.report_path, output_dir=args.output_dir)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
