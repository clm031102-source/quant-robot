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
    walk_forward_folds_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_regimes: int = 2,
    min_rows_per_regime: int = 5,
    min_allowed_rows: int = 0,
    min_blocked_rows: int = 0,
    positive_threshold: float = 0.02,
    negative_threshold: float = -0.02,
    require_sufficient: bool = False,
) -> dict[str, Any]:
    rows, source_evidence = _read_regime_rows(
        regime_curve,
        regime_curve_glob,
        walk_forward_folds_path,
    )
    pack = build_market_regime_coverage_pack(
        rows,
        min_regimes=min_regimes,
        min_rows_per_regime=min_rows_per_regime,
        min_allowed_rows=min_allowed_rows,
        min_blocked_rows=min_blocked_rows,
        positive_threshold=positive_threshold,
        negative_threshold=negative_threshold,
    )
    pack["source_evidence"] = source_evidence
    write_market_regime_coverage_pack(output_dir, pack)
    if require_sufficient and pack["status"] != "sufficient":
        blockers = ", ".join(pack["decision"]["blockers"])
        raise RuntimeError(f"market regime coverage is insufficient: {blockers}")
    return pack


def _read_regime_rows(
    regime_curve: str | Path,
    regime_curve_glob: str | None,
    walk_forward_folds_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not regime_curve_glob:
        return pd.read_csv(regime_curve), {
            "mode": "single_curve",
            "expected_fold_cases": 0,
            "selected_curves": 1,
            "ignored_stale_curves": 0,
        }
    paths = sorted(Path(path) for path in glob.glob(regime_curve_glob, recursive=True))
    expected = _expected_fold_cases(walk_forward_folds_path) if walk_forward_folds_path is not None else None
    selected_paths = paths
    ignored = 0
    if expected is not None:
        paths_by_identity = {_curve_identity(path): path for path in paths}
        missing = sorted(expected.difference(paths_by_identity))
        if missing:
            examples = ", ".join(f"fold_{fold:02d}/{case_id}" for fold, case_id in missing[:5])
            raise RuntimeError(f"missing current walk-forward regime curves: {examples}")
        selected_paths = [paths_by_identity[identity] for identity in sorted(expected)]
        ignored = len(paths) - len(selected_paths)
    if not selected_paths:
        return pd.DataFrame(columns=["date", "regime_momentum", "regime_allowed"]), {
            "mode": "glob",
            "expected_fold_cases": len(expected or set()),
            "selected_curves": 0,
            "ignored_stale_curves": ignored,
        }
    frames = []
    for path in selected_paths:
        frame = pd.read_csv(path)
        frame["source_file"] = str(path)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True), {
        "mode": "walk_forward_bound" if expected is not None else "glob",
        "walk_forward_folds_path": str(walk_forward_folds_path) if walk_forward_folds_path is not None else None,
        "expected_fold_cases": len(expected or set()),
        "selected_curves": len(selected_paths),
        "ignored_stale_curves": ignored,
    }


def _expected_fold_cases(path: str | Path) -> set[tuple[int, str]]:
    frame = pd.read_csv(path)
    missing = [column for column in ("fold", "case_id") if column not in frame.columns]
    if missing:
        raise RuntimeError(f"walk-forward folds evidence is missing columns: {', '.join(missing)}")
    expected = {
        (int(row.fold), str(row.case_id))
        for row in frame[["fold", "case_id"]].dropna().itertuples(index=False)
    }
    if not expected:
        raise RuntimeError("walk-forward folds evidence contains no fold cases")
    return expected


def _curve_identity(path: Path) -> tuple[int, str]:
    fold = None
    for parent in path.parents:
        if parent.name.startswith("fold_"):
            try:
                fold = int(parent.name.split("_", 1)[1])
            except ValueError:
                break
            break
    if fold is None:
        raise RuntimeError(f"regime curve path has no fold identity: {path}")
    return fold, path.parent.name


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local market-regime coverage pack from a research regime_curve.csv.")
    parser.add_argument("--regime-curve", default=str(DEFAULT_REGIME_CURVE))
    parser.add_argument("--regime-curve-glob")
    parser.add_argument("--walk-forward-folds")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-regimes", default=2, type=int)
    parser.add_argument("--min-rows-per-regime", default=5, type=int)
    parser.add_argument("--min-allowed-rows", default=0, type=int)
    parser.add_argument("--min-blocked-rows", default=0, type=int)
    parser.add_argument("--positive-threshold", default=0.02, type=float)
    parser.add_argument("--negative-threshold", default=-0.02, type=float)
    parser.add_argument("--require-sufficient", action="store_true")
    args = parser.parse_args()
    try:
        pack = run_market_regime_coverage(
            regime_curve=Path(args.regime_curve),
            regime_curve_glob=args.regime_curve_glob,
            walk_forward_folds_path=(
                Path(args.walk_forward_folds) if args.walk_forward_folds else None
            ),
            output_dir=Path(args.output_dir),
            min_regimes=args.min_regimes,
            min_rows_per_regime=args.min_rows_per_regime,
            min_allowed_rows=args.min_allowed_rows,
            min_blocked_rows=args.min_blocked_rows,
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
