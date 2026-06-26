from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_tradeability_data_readiness_audit import (
    build_cn_stock_tradeability_data_readiness_audit,
    write_cn_stock_tradeability_data_readiness_audit,
)


DEFAULT_DATA_ROOTS = [
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
    Path("data/processed/cn_stock_metadata"),
]
DEFAULT_OUTPUT_DIR = Path("data/reports/round196_tradeability_data_readiness_audit_20260623")


def run_cn_stock_tradeability_data_readiness_audit(
    *,
    data_roots: Sequence[str | Path] = DEFAULT_DATA_ROOTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    expected_start: str | None = "2015-01-01",
    expected_end: str | None = "2025-12-31",
) -> dict[str, Any]:
    packet = build_cn_stock_tradeability_data_readiness_audit(
        data_roots=data_roots,
        expected_start=expected_start,
        expected_end=expected_end,
    )
    write_cn_stock_tradeability_data_readiness_audit(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CN stock tradeability data readiness before factor mining.")
    parser.add_argument("--data-root", action="append", dest="data_roots")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expected-start", default="2015-01-01")
    parser.add_argument("--expected-end", default="2025-12-31")
    args = parser.parse_args()
    data_roots = [Path(path) for path in args.data_roots] if args.data_roots else DEFAULT_DATA_ROOTS
    packet = run_cn_stock_tradeability_data_readiness_audit(
        data_roots=data_roots,
        output_dir=args.output_dir,
        expected_start=args.expected_start,
        expected_end=args.expected_end,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
