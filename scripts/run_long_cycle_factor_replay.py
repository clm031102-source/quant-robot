from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.long_cycle_replay import (
    build_long_cycle_coverage_from_manifest,
    build_long_cycle_replay_pack,
    build_long_cycle_replay_pack_from_coverage,
    write_long_cycle_replay_pack,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/long_cycle_factor_replay")


def run_long_cycle_factor_replay(
    *,
    candidates_csv: str | Path,
    bars_csv: str | Path | None = None,
    manifest_json: str | Path | None = None,
    market: str,
    required_start: str = "2015-01-01",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    candidates = pd.read_csv(candidates_csv)
    if manifest_json is not None:
        manifest = json.loads(Path(manifest_json).read_text(encoding="utf-8"))
        coverage = build_long_cycle_coverage_from_manifest(
            manifest,
            market=market,
            required_start=required_start,
        )
        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market=market,
            required_start=required_start,
        )
    else:
        if bars_csv is None:
            raise ValueError("either bars_csv or manifest_json is required")
        bars = pd.read_csv(bars_csv)
        pack = build_long_cycle_replay_pack(
            candidates,
            bars,
            market=market,
            required_start=required_start,
        )
    write_long_cycle_replay_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Run long-cycle factor replay coverage and audit gates.")
    parser.add_argument("--candidates-csv", required=True)
    parser.add_argument("--bars-csv")
    parser.add_argument("--manifest-json")
    parser.add_argument("--market", required=True)
    parser.add_argument("--required-start", default="2015-01-01")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_long_cycle_factor_replay(
        candidates_csv=Path(args.candidates_csv),
        bars_csv=Path(args.bars_csv) if args.bars_csv else None,
        manifest_json=Path(args.manifest_json) if args.manifest_json else None,
        market=args.market,
        required_start=args.required_start,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "coverage": pack["coverage"],
                "output_dir": str(Path(args.output_dir)),
                "live_boundary_allowed": pack["live_boundary_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
