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

from quant_robot.ops.walk_forward_early_stop_audit import (  # noqa: E402
    build_walk_forward_early_stop_audit,
    write_walk_forward_early_stop_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/walk_forward_early_stop_audit")


def run_walk_forward_early_stop_audit_cli(
    *,
    walk_forward_root: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_completed_folds: int = 3,
    expected_rows_per_fold: int = 1,
    min_positive_relative_rows: int = 1,
    min_accepted_rows: int = 1,
    min_capacity_clean_rate: float = 0.95,
) -> dict[str, Any]:
    result = build_walk_forward_early_stop_audit(
        walk_forward_root,
        min_completed_folds=min_completed_folds,
        expected_rows_per_fold=expected_rows_per_fold,
        min_positive_relative_rows=min_positive_relative_rows,
        min_accepted_rows=min_accepted_rows,
        min_capacity_clean_rate=min_capacity_clean_rate,
    )
    write_walk_forward_early_stop_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit partial walk-forward folds for budget early-stop evidence.")
    parser.add_argument("--walk-forward-root", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-completed-folds", type=int, default=3)
    parser.add_argument("--expected-rows-per-fold", type=int, default=1)
    parser.add_argument("--min-positive-relative-rows", type=int, default=1)
    parser.add_argument("--min-accepted-rows", type=int, default=1)
    parser.add_argument("--min-capacity-clean-rate", type=float, default=0.95)
    args = parser.parse_args()
    result = run_walk_forward_early_stop_audit_cli(
        walk_forward_root=Path(args.walk_forward_root),
        output_dir=Path(args.output_dir),
        min_completed_folds=args.min_completed_folds,
        expected_rows_per_fold=args.expected_rows_per_fold,
        min_positive_relative_rows=args.min_positive_relative_rows,
        min_accepted_rows=args.min_accepted_rows,
        min_capacity_clean_rate=args.min_capacity_clean_rate,
    )
    print(json.dumps({key: result[key] for key in ("summary", "decision")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
