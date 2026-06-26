from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.external_feed_coverage_audit import run_external_feed_coverage_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit processed external-feed coverage before IC or portfolio work."
    )
    parser.add_argument("--processed-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--market", default="CN")
    parser.add_argument("--min-hk-hold-observation-dates", type=int, default=25)
    parser.add_argument("--max-hk-hold-median-gap-days", type=int, default=10)
    parser.add_argument("--min-macro-observation-dates", type=int, default=60)
    parser.add_argument("--min-lpr-non-null-ratio", type=float, default=0.8)
    args = parser.parse_args(argv)
    result = run_external_feed_coverage_audit(
        processed_root=Path(args.processed_root),
        output_dir=Path(args.output_dir),
        market=args.market,
        min_hk_hold_observation_dates=args.min_hk_hold_observation_dates,
        max_hk_hold_median_gap_days=args.max_hk_hold_median_gap_days,
        min_macro_observation_dates=args.min_macro_observation_dates,
        min_lpr_non_null_ratio=args.min_lpr_non_null_ratio,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
