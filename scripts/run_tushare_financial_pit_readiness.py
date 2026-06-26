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

from quant_robot.ops.tushare_financial_pit_readiness import (  # noqa: E402
    audit_tushare_financial_pit_readiness,
    write_tushare_financial_pit_readiness,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/tushare_financial_pit_readiness")


def run_tushare_financial_pit_readiness_cli(
    *,
    roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    allow_not_ready: bool = False,
    required_column_groups: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    result = audit_tushare_financial_pit_readiness(roots, required_column_groups=required_column_groups)
    write_tushare_financial_pit_readiness(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Tushare financial PIT readiness is not ready: {blockers}")
    return result


def _parse_required_column_groups(items: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for item in items:
        if ":" not in item:
            raise ValueError(f"required column group must be group_id:col1,col2: {item}")
        group_id, raw_columns = item.split(":", 1)
        columns = [column.strip() for column in raw_columns.split(",") if column.strip()]
        if not group_id.strip() or not columns:
            raise ValueError(f"required column group must include a group id and at least one column: {item}")
        groups[group_id.strip()] = columns
    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit local Tushare financial inputs for point-in-time profitability factor readiness.")
    parser.add_argument("--root", action="append", default=[], help="Local data root to scan. Can be provided multiple times.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-not-ready", action="store_true", help="Write a blocking readiness report without returning a non-zero exit.")
    parser.add_argument(
        "--required-column-group",
        action="append",
        default=[],
        help="Required PIT-ready column group in the form group_id:col1,col2. Can be provided multiple times.",
    )
    args = parser.parse_args()
    result = run_tushare_financial_pit_readiness_cli(
        roots=[Path(root) for root in args.root],
        output_dir=Path(args.output_dir),
        allow_not_ready=args.allow_not_ready,
        required_column_groups=_parse_required_column_groups(args.required_column_group),
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
