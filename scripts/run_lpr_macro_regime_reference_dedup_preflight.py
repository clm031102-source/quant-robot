from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_reference_dedup_preflight import (  # noqa: E402
    run_lpr_macro_regime_reference_dedup_preflight,
)


DEFAULT_PROCESSED_ROOT = Path("data/processed/round695_external_feeds_lpr_repaired_20260709")
DEFAULT_PAIRWISE_PRESCREEN = Path(
    "data/reports/round732_lpr_macro_regime_pairwise_residual_ic_prescreen_20260709/lpr_macro_regime_pairwise_residual_ic_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round733_lpr_macro_regime_reference_dedup_preflight_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR macro regime reference-dedup routing preflight.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--pairwise-prescreen", default=str(DEFAULT_PAIRWISE_PRESCREEN))
    parser.add_argument("--residual-ic", action="append", required=True, dest="residual_ic_paths")
    parser.add_argument("--reference-correlation", action="append", default=[], dest="reference_correlation_paths")
    parser.add_argument("--exposure-correlation", action="append", default=[], dest="exposure_correlation_paths")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-abs-gap-change", type=float, default=0.01)
    parser.add_argument("--cluster-abs-ic-corr", type=float, default=0.90)
    parser.add_argument("--duplicate-abs-ic-corr", type=float, default=0.98)
    parser.add_argument("--min-pair-overlap", type=int, default=20)
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_reference_dedup_preflight(
        processed_root=Path(args.processed_root),
        pairwise_prescreen_path=Path(args.pairwise_prescreen),
        residual_ic_paths=[Path(path) for path in args.residual_ic_paths],
        output_dir=Path(args.output_dir),
        reference_correlation_paths=[Path(path) for path in args.reference_correlation_paths],
        exposure_correlation_paths=[Path(path) for path in args.exposure_correlation_paths],
        market=args.market,
        lookback_days=args.lookback_days,
        min_abs_gap_change=args.min_abs_gap_change,
        cluster_abs_ic_corr=args.cluster_abs_ic_corr,
        duplicate_abs_ic_corr=args.duplicate_abs_ic_corr,
        min_pair_overlap=args.min_pair_overlap,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "decision": result.get("decision", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
