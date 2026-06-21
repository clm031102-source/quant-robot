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

from quant_robot.ops.profitability_quality_family_rejection_audit import (  # noqa: E402
    build_profitability_quality_family_rejection_audit,
    write_profitability_quality_family_rejection_audit,
)


DEFAULT_CONTROLLED_IC_JSON = Path(
    "data/reports/profitability_quality_controlled_ic_screen_round98_20260622/profitability_quality_controlled_ic_screen.json"
)
DEFAULT_SOURCE_REPORT = Path("docs/research/cn_stock_profitability_quality_controlled_ic_screen_round98_2026-06-22.md")
DEFAULT_OUTPUT_DIR = Path("data/reports/profitability_quality_family_rejection_audit_round99_20260622")


def run_profitability_quality_family_rejection_audit_cli(
    *,
    controlled_ic_json: str | Path = DEFAULT_CONTROLLED_IC_JSON,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    source_report: str | Path = DEFAULT_SOURCE_REPORT,
    rounds: list[int] | tuple[int, ...] = (97, 98, 99),
) -> dict[str, Any]:
    audit = build_profitability_quality_family_rejection_audit(
        controlled_ic_screen=_read_json(controlled_ic_json),
        source_report=source_report,
        rounds=rounds,
    )
    write_profitability_quality_family_rejection_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit whether the profitability-quality factor family should be rejected and rotated.")
    parser.add_argument("--controlled-ic-json", default=str(DEFAULT_CONTROLLED_IC_JSON))
    parser.add_argument("--source-report", default=str(DEFAULT_SOURCE_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--round", action="append", type=int, default=[])
    args = parser.parse_args()
    audit = run_profitability_quality_family_rejection_audit_cli(
        controlled_ic_json=Path(args.controlled_ic_json),
        output_dir=Path(args.output_dir),
        source_report=Path(args.source_report),
        rounds=args.round or [97, 98, 99],
    )
    print(
        json.dumps(
            {
                "stage": audit["stage"],
                "status": audit["status"],
                "summary": audit["summary"],
                "decision": audit["decision"],
                "live_boundary_allowed": audit["live_boundary_allowed"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
