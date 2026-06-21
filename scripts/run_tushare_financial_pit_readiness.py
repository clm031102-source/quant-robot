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
) -> dict[str, Any]:
    result = audit_tushare_financial_pit_readiness(roots)
    write_tushare_financial_pit_readiness(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Tushare financial PIT readiness is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit local Tushare financial inputs for point-in-time profitability factor readiness.")
    parser.add_argument("--root", action="append", default=[], help="Local data root to scan. Can be provided multiple times.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-not-ready", action="store_true", help="Write a blocking readiness report without returning a non-zero exit.")
    args = parser.parse_args()
    result = run_tushare_financial_pit_readiness_cli(
        roots=[Path(root) for root in args.root],
        output_dir=Path(args.output_dir),
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
