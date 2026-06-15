from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.duplicate_registry import build_duplicate_registry, write_duplicate_registry


DEFAULT_PROMOTION_REPORT = Path("data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/duplicate_registry")


def run_duplicate_registry(
    promotion_report: str | Path = DEFAULT_PROMOTION_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    report = json.loads(Path(promotion_report).read_text(encoding="utf-8"))
    registry = build_duplicate_registry(report)
    write_duplicate_registry(output_dir, registry)
    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.4 duplicate canonical registry.")
    parser.add_argument("--promotion-report", default=str(DEFAULT_PROMOTION_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    registry = run_duplicate_registry(
        promotion_report=Path(args.promotion_report),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": registry["stage"],
                "summary": registry["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
