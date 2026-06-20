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
    candidates = _load_candidates_with_source(candidates_csv)
    if manifest_json is not None:
        manifest = json.loads(Path(manifest_json).read_text(encoding="utf-8-sig"))
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


def _load_candidates_with_source(candidates_csv: str | Path) -> pd.DataFrame:
    path = Path(candidates_csv)
    candidates = pd.read_csv(path)
    candidates = _backfill_walk_forward_sidecar_fields(candidates, path)
    if "source_kind" not in candidates.columns:
        candidates["source_kind"] = "candidate_csv"
    else:
        missing_kind = candidates["source_kind"].isna() | (candidates["source_kind"].astype(str).str.strip() == "")
        candidates.loc[missing_kind, "source_kind"] = "candidate_csv"
    if "source_report" not in candidates.columns:
        candidates["source_report"] = str(path)
    else:
        missing_report = candidates["source_report"].isna() | (candidates["source_report"].astype(str).str.strip() == "")
        candidates.loc[missing_report, "source_report"] = str(path)
    return candidates


def _backfill_walk_forward_sidecar_fields(candidates: pd.DataFrame, path: Path) -> pd.DataFrame:
    frame = candidates.copy()
    manifest_path = path.parent / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            manifest = {}
        grid = _nested_dict(manifest, "config", "experiment_grid")
        _fill_missing_scalar(frame, "execution_lag", grid.get("execution_lag"))
        _fill_missing_scalar(frame, "forward_horizon", grid.get("forward_horizon"))

    folds_path = path.parent / "walk_forward_folds.csv"
    if folds_path.exists() and "case_id" in frame.columns:
        folds = pd.read_csv(folds_path)
        split_rows = _split_evidence_by_case(folds)
        if split_rows:
            split_frame = pd.DataFrame(split_rows).set_index("case_id")
            frame = frame.merge(
                split_frame,
                how="left",
                left_on="case_id",
                right_index=True,
                suffixes=("", "_sidecar"),
            )
            for column in split_frame.columns:
                sidecar_column = f"{column}_sidecar"
                if sidecar_column in frame.columns:
                    _fill_missing_from_column(frame, column, sidecar_column)
                    frame = frame.drop(columns=[sidecar_column])
    return frame


def _nested_dict(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _fill_missing_scalar(frame: pd.DataFrame, column: str, value: Any) -> None:
    if value is None:
        return
    if column not in frame.columns:
        frame[column] = value
        return
    missing = frame[column].isna() | (frame[column].astype(str).str.strip() == "")
    frame.loc[missing, column] = value


def _fill_missing_from_column(frame: pd.DataFrame, column: str, source_column: str) -> None:
    if column not in frame.columns:
        frame[column] = frame[source_column]
        return
    missing = frame[column].isna() | (frame[column].astype(str).str.strip() == "")
    frame.loc[missing, column] = frame.loc[missing, source_column]


def _split_evidence_by_case(folds: pd.DataFrame) -> list[dict[str, Any]]:
    required = {"case_id", "train_start_date", "train_end_date", "test_start_date", "test_end_date"}
    if folds.empty or not required.issubset(set(folds.columns)):
        return []
    rows: list[dict[str, Any]] = []
    for case_id, group in folds.groupby("case_id", sort=True):
        ordered = group.sort_values("fold") if "fold" in group.columns else group
        first = ordered.iloc[0]
        violations = 0
        for _, row in ordered.iterrows():
            train_end = pd.to_datetime(row["train_end_date"], errors="coerce")
            test_start = pd.to_datetime(row["test_start_date"], errors="coerce")
            if pd.isna(train_end) or pd.isna(test_start) or test_start.date() <= train_end.date():
                violations += 1
        rows.append(
            {
                "case_id": case_id,
                "train_start_date": str(first["train_start_date"])[:10],
                "train_end_date": str(first["train_end_date"])[:10],
                "test_start_date": str(first["test_start_date"])[:10],
                "test_end_date": str(first["test_end_date"])[:10],
                "strict_split_status": "pass" if violations == 0 else "block",
                "strict_split_violations": violations,
                "strict_split_folds": int(len(ordered)),
            }
        )
    return rows


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
