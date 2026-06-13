from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.paper_observation import build_paper_observation_pack, write_paper_observation_pack


DEFAULT_PAPER_BATCH_SUMMARY = Path("data/reports/paper_batch_cn_etf_candidate_search/paper_batch_summary.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/paper_observation")


def run_paper_observation(
    paper_batch_summary: str | Path = DEFAULT_PAPER_BATCH_SUMMARY,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    summary_path = Path(paper_batch_summary)
    paper_batch = json.loads(summary_path.read_text(encoding="utf-8"))
    artifacts = _load_all_candidate_artifacts(paper_batch)
    pack = build_paper_observation_pack(paper_batch, artifacts)
    write_paper_observation_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.3 paper-observation evidence pack.")
    parser.add_argument("--paper-batch-summary", default=str(DEFAULT_PAPER_BATCH_SUMMARY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_paper_observation(
        paper_batch_summary=Path(args.paper_batch_summary),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_all_candidate_artifacts(paper_batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {}
    for row in paper_batch.get("candidates", []):
        if not isinstance(row, dict) or not row.get("case_id"):
            continue
        artifacts[str(row["case_id"])] = _load_candidate_artifacts(row)
    return artifacts


def _load_candidate_artifacts(row: dict[str, Any]) -> dict[str, Any]:
    output_dir = _candidate_output_dir(row)
    manifest_path = Path(str(row["manifest_path"])) if row.get("manifest_path") else output_dir / "manifest.json" if output_dir else None
    artifact: dict[str, Any] = {}
    if manifest_path is not None and manifest_path.exists():
        artifact["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if output_dir is not None:
        artifact["equity_curve"] = _read_csv_records(output_dir / "equity_curve.csv")
        artifact["guard_events"] = _read_csv_records(output_dir / "guard_events.csv")
        artifact["execution_events"] = _read_csv_records(output_dir / "execution_events.csv")
    return artifact


def _candidate_output_dir(row: dict[str, Any]) -> Path | None:
    if row.get("output_dir"):
        return Path(str(row["output_dir"]))
    if row.get("manifest_path"):
        return Path(str(row["manifest_path"])).parent
    return None


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return pd.read_csv(path).to_dict(orient="records")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return []


if __name__ == "__main__":
    main()
