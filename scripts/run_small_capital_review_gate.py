from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.small_capital_review import build_small_capital_review_gate, write_small_capital_review_gate


DEFAULT_REVIEW_PACKET = Path("data/reports/promotion_review/promotion_review_packet.json")
DEFAULT_MANUAL_REHEARSAL = Path("data/reports/manual_review_rehearsal/manual_review_rehearsal.json")
DEFAULT_PAPER_OBSERVATION = Path("data/reports/paper_observation/paper_observation_pack.json")
DEFAULT_PRE_API_READINESS = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_OBSERVATION_SUFFICIENCY = Path("data/reports/observation_sufficiency/observation_sufficiency_pack.json")
DEFAULT_MARKET_REGIME_COVERAGE = Path("data/reports/market_regime_coverage/market_regime_coverage_pack.json")
DEFAULT_POLICY = Path("configs/small_capital_review_policy.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/small_capital_review_gate")


def run_small_capital_review_gate(
    review_packet: str | Path = DEFAULT_REVIEW_PACKET,
    manual_rehearsal: str | Path | None = DEFAULT_MANUAL_REHEARSAL,
    paper_observation: str | Path | None = DEFAULT_PAPER_OBSERVATION,
    pre_api_readiness: str | Path | None = DEFAULT_PRE_API_READINESS,
    observation_sufficiency: str | Path | None = DEFAULT_OBSERVATION_SUFFICIENCY,
    market_regime_coverage: str | Path | None = DEFAULT_MARKET_REGIME_COVERAGE,
    policy: str | Path | None = DEFAULT_POLICY,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    reviewer: str | None = None,
) -> dict[str, Any]:
    gate = build_small_capital_review_gate(
        _read_json(review_packet),
        manual_rehearsal=_read_optional_json(manual_rehearsal),
        paper_observation=_read_optional_json(paper_observation),
        pre_api_readiness=_read_optional_json(pre_api_readiness),
        observation_sufficiency=_read_optional_json(observation_sufficiency),
        market_regime_coverage=_read_optional_json(market_regime_coverage),
        policy=_read_optional_json(policy),
        reviewer=reviewer,
    )
    write_small_capital_review_gate(output_dir, gate)
    return gate


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local small-capital manual-review gate without enabling live execution.")
    parser.add_argument("--review-packet", default=str(DEFAULT_REVIEW_PACKET))
    parser.add_argument("--manual-rehearsal", default=str(DEFAULT_MANUAL_REHEARSAL))
    parser.add_argument("--paper-observation", default=str(DEFAULT_PAPER_OBSERVATION))
    parser.add_argument("--pre-api-readiness", default=str(DEFAULT_PRE_API_READINESS))
    parser.add_argument("--observation-sufficiency", default=str(DEFAULT_OBSERVATION_SUFFICIENCY))
    parser.add_argument("--market-regime-coverage", default=str(DEFAULT_MARKET_REGIME_COVERAGE))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--reviewer", default=None)
    args = parser.parse_args()
    gate = run_small_capital_review_gate(
        review_packet=Path(args.review_packet),
        manual_rehearsal=Path(args.manual_rehearsal) if args.manual_rehearsal else None,
        paper_observation=Path(args.paper_observation) if args.paper_observation else None,
        pre_api_readiness=Path(args.pre_api_readiness) if args.pre_api_readiness else None,
        observation_sufficiency=Path(args.observation_sufficiency) if args.observation_sufficiency else None,
        market_regime_coverage=Path(args.market_regime_coverage) if args.market_regime_coverage else None,
        policy=Path(args.policy) if args.policy else None,
        output_dir=Path(args.output_dir),
        reviewer=args.reviewer,
    )
    print(
        json.dumps(
            {
                "stage": gate["stage"],
                "status": gate["status"],
                "summary": gate["summary"],
                "live_boundary_allowed": gate["decision"]["live_boundary_allowed"],
                "executable": gate["decision"]["executable"],
                "blockers": gate["decision"]["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return _read_json(target)


if __name__ == "__main__":
    main()
