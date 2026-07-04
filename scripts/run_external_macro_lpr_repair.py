from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.external_macro_lpr_repair import repair_external_macro_lpr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repair processed external_macro_rates LPR columns from a validated LPR cache.")
    parser.add_argument("--processed-root", required=True)
    parser.add_argument("--lpr-cache-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--market", default="CN")
    parser.add_argument("--copy-other-feeds", action="store_true")
    args = parser.parse_args(argv)
    report = repair_external_macro_lpr(
        processed_root=Path(args.processed_root),
        lpr_cache_path=Path(args.lpr_cache_path),
        output_root=Path(args.output_root),
        report_dir=Path(args.report_dir),
        market=args.market,
        copy_other_feeds=args.copy_other_feeds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
