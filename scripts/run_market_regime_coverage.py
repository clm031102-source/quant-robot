from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.market_regime_coverage import build_market_regime_coverage_pack, write_market_regime_coverage_pack


DEFAULT_REGIME_CURVE = Path("data/reports/research_pipeline/regime_curve.csv")
DEFAULT_OUTPUT_DIR = Path("data/reports/market_regime_coverage")


def run_market_regime_coverage(
    regime_curve: str | Path = DEFAULT_REGIME_CURVE,
    regime_curve_glob: str | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_regimes: int = 2,
    min_rows_per_regime: int = 5,
    positive_threshold: float = 0.02,
    negative_threshold: float = -0.02,
    require_sufficient: bool = False,
) -> dict[str, Any]:
    rows = _read_regime_rows(regime_curve, regime_curve_glob)
    pack = build_market_regime_coverage_pack(
        rows,
        min_regimes=min_regimes,
        min_rows_per_regime=min_rows_per_regime,
        positive_threshold=positive_threshold,
        negative_threshold=negative_threshold,
    )
    write_market_regime_coverage_pack(output_dir, pack)
    if require_sufficient and pack["status"] != "sufficient":
        blockers = ", ".join(pack["decision"]["blockers"])
        raise RuntimeError(f"market regime coverage is insufficient: {blockers}")
    return pack


def _read_regime_rows(regime_curve: str | Path, regime_curve_glob: str | None) -> pd.DataFrame:
    if not regime_curve_glob:
        return pd.read_csv(regime_curve)
    paths = sorted(Path(path) for path in glob.glob(regime_curve_glob, recursive=True))
    if not paths:
        return pd.DataFrame(columns=["date", "regime_momentum", "regime_allowed"])
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        frame["source_file"] = str(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local market-regime coverage pack from a research regime_curve.csv.")
    parser.add_argument("--regime-curve", default=str(DEFAULT_REGIME_CURVE))
    parser.add_argument("--regime-curve-glob")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-regimes", default=2, type=int)
    parser.add_argument("--min-rows-per-regime", default=5, type=int)
    parser.add_argument("--positive-threshold", default=0.02, type=float)
    parser.add_argument("--negative-threshold", default=-0.02, type=float)
    parser.add_argument("--require-sufficient", action="store_true")
    args = parser.parse_args()
    try:
        pack = run_market_regime_coverage(
            regime_curve=Path(args.regime_curve),
            regime_curve_glob=args.regime_curve_glob,
            output_dir=Path(args.output_dir),
            min_regimes=args.min_regimes,
            min_rows_per_regime=args.min_rows_per_regime,
            positive_threshold=args.positive_threshold,
            negative_threshold=args.negative_threshold,
            require_sufficient=args.require_sufficient,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "summary": pack["summary"],
                "blockers": pack["decision"]["blockers"],
                "live_boundary_allowed": pack["live_boundary_allowed"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
