from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.paper_ops_guardrail import build_paper_ops_guardrail_pack, write_paper_ops_guardrail_pack


DEFAULT_HISTORY_PACK = Path("data/reports/paper_observation_history/paper_observation_history_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/paper_ops_guardrail")


def run_paper_ops_guardrail(
    paper_observation_history: str | Path = DEFAULT_HISTORY_PACK,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_live_readiness_runs: int = 20,
    provider_gap_warning_threshold: int = 0,
) -> dict[str, Any]:
    history = _read_json(Path(paper_observation_history))
    pack = build_paper_ops_guardrail_pack(
        history,
        min_live_readiness_runs=min_live_readiness_runs,
        provider_gap_warning_threshold=provider_gap_warning_threshold,
    )
    write_paper_ops_guardrail_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a paper-only operations guardrail pack from observation history.")
    parser.add_argument("--paper-observation-history", default=str(DEFAULT_HISTORY_PACK))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-live-readiness-runs", default=20, type=int)
    parser.add_argument("--provider-gap-warning-threshold", default=0, type=int)
    args = parser.parse_args()
    pack = run_paper_ops_guardrail(
        paper_observation_history=Path(args.paper_observation_history),
        output_dir=Path(args.output_dir),
        min_live_readiness_runs=args.min_live_readiness_runs,
        provider_gap_warning_threshold=args.provider_gap_warning_threshold,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "summary": pack["summary"],
                "decision": pack["decision"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
