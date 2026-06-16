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

from quant_robot.ops.promotion_console import build_promotion_operations_console


DEFAULT_PROMOTION_REPORTS = (
    Path("data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json"),
    Path("data/reports/promotion_gate_cn_etf/promotion_report.json"),
)
DEFAULT_PROVIDER_STATUS = Path("data/reports/provider_status/provider_status.json")
DEFAULT_QUALITY_REPORT = Path("data/processed/etf_csv/quality_report_cn_etf.json")
DEFAULT_PAPER_OBSERVATION = Path("data/reports/paper_observation/paper_observation_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/promotion_ops")


def run_promotion_ops(
    promotion_report: str | Path | None = None,
    provider_status: str | Path | None = None,
    quality_report: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    paper_observation: str | Path | None = DEFAULT_PAPER_OBSERVATION,
) -> dict[str, Any]:
    report_path = Path(promotion_report) if promotion_report is not None else _first_existing(DEFAULT_PROMOTION_REPORTS)
    console = (
        build_promotion_operations_console(
            report_path,
            Path(provider_status) if provider_status is not None else DEFAULT_PROVIDER_STATUS,
            Path(quality_report) if quality_report is not None else DEFAULT_QUALITY_REPORT,
            _read_optional_json(paper_observation),
        )
        if report_path is not None
        else _missing_console()
    )
    _write_outputs(console, Path(output_dir))
    return console


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local Phase 2.8 promotion operations console artifact.")
    parser.add_argument("--promotion-report")
    parser.add_argument("--provider-status")
    parser.add_argument("--quality-report")
    parser.add_argument("--paper-observation")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_promotion_ops(
        promotion_report=Path(args.promotion_report) if args.promotion_report else None,
        provider_status=Path(args.provider_status) if args.provider_status else None,
        quality_report=Path(args.quality_report) if args.quality_report else None,
        output_dir=Path(args.output_dir),
        paper_observation=Path(args.paper_observation) if args.paper_observation else DEFAULT_PAPER_OBSERVATION,
    )
    print(json.dumps({"summary": result["summary"], "top_candidate": result["top_candidate"], "next_actions": result["next_actions"]}, indent=2, sort_keys=True))


def _write_outputs(console: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "promotion_ops.json").write_text(json.dumps(console, indent=2, sort_keys=True), encoding="utf-8")
    pd.DataFrame(console.get("candidates", [])).to_csv(output_dir / "promotion_ops_candidates.csv", index=False)
    pd.DataFrame(console.get("next_actions", [])).to_csv(output_dir / "promotion_ops_actions.csv", index=False)


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {target}")
    return data


def _first_existing(paths: tuple[Path, ...]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _missing_console() -> dict[str, Any]:
    return {
        "stage": "phase_2_8_promotion_operations",
        "generated_at": None,
        "source_report": None,
        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        "summary": {"candidates": 0, "blocked": 0, "research_only": 0, "paper_ready": 0, "manual_live_review": 0, "duplicates": 0},
        "live_review_allowed": False,
        "live_review_blockers": ["promotion_report_missing"],
        "top_candidate": None,
        "candidates": [],
        "duplicate_clusters": [],
        "duplicate_registry_summary": {"candidates": 0, "canonical_candidates": 0, "duplicate_members": 0, "clusters": 0, "suppressed_duplicates": 0},
        "duplicate_canonical_registry": [],
        "duplicate_members": [],
        "evidence": {"provider_status_present": False, "quality_report_present": False, "providers_ready": False},
        "next_actions": [{"action": "rerun_promotion_gate", "reason": "promotion report is missing"}],
    }


if __name__ == "__main__":
    main()
