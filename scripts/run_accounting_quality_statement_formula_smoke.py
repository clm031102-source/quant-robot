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

from quant_robot.ops.accounting_quality_statement_formula_smoke import (  # noqa: E402
    audit_accounting_quality_statement_formula_smoke,
    write_accounting_quality_statement_formula_smoke,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/accounting_quality_statement_formula_smoke")


def run_accounting_quality_statement_formula_smoke_cli(
    *,
    roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    deduplicate: bool = True,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = audit_accounting_quality_statement_formula_smoke(roots, deduplicate=deduplicate)
    write_accounting_quality_statement_formula_smoke(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"accounting quality statement formula smoke is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an accounting-quality formula smoke on PIT statement inputs.")
    parser.add_argument("--root", action="append", default=[], help="Local processed statement root. Can be provided multiple times.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--no-deduplicate", action="store_true", help="Report duplicate statement keys as a blocker instead of dropping duplicates.")
    parser.add_argument("--allow-not-ready", action="store_true", help="Write a blocking report without returning a non-zero exit.")
    args = parser.parse_args()
    result = run_accounting_quality_statement_formula_smoke_cli(
        roots=[Path(root) for root in args.root],
        output_dir=Path(args.output_dir),
        deduplicate=not args.no_deduplicate,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
