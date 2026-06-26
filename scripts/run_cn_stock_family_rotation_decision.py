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

from quant_robot.ops.cn_stock_family_rotation_decision import (  # noqa: E402
    build_cn_stock_family_rotation_decision,
    write_cn_stock_family_rotation_decision,
)


DEFAULT_STARTUP_GATE = Path("data/reports/factor_mining_startup_gate_round160_post_review_20260623/factor_mining_startup_gate.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_family_rotation_decision_round161_20260623")


def run_cn_stock_family_rotation_decision(
    *,
    startup_gate: str | Path = DEFAULT_STARTUP_GATE,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    selected_family_id: str | None = None,
    expected_startup_next_direction: str | None = None,
    next_preregistration_direction: str | None = None,
    selected_required_controls: list[str] | None = None,
    family_candidates_json: str | Path | None = None,
    candidate_plan_seed_json: str | Path | None = None,
    startup_direction_blocker: str | None = None,
    allow_blocked: bool = False,
) -> dict[str, Any]:
    startup_packet = json.loads(Path(startup_gate).read_text(encoding="utf-8"))
    kwargs: dict[str, Any] = {}
    if selected_family_id:
        kwargs["selected_family_id"] = selected_family_id
    if expected_startup_next_direction:
        kwargs["expected_startup_next_direction"] = expected_startup_next_direction
    if next_preregistration_direction:
        kwargs["next_preregistration_direction"] = next_preregistration_direction
    if selected_required_controls:
        kwargs["selected_required_controls"] = list(selected_required_controls)
    if family_candidates_json:
        family_candidates = json.loads(Path(family_candidates_json).read_text(encoding="utf-8"))
        if not isinstance(family_candidates, list):
            raise ValueError("family_candidates_json must contain a JSON list")
        kwargs["family_candidates"] = family_candidates
    if candidate_plan_seed_json:
        candidate_plan_seed = json.loads(Path(candidate_plan_seed_json).read_text(encoding="utf-8"))
        if not isinstance(candidate_plan_seed, dict):
            raise ValueError("candidate_plan_seed_json must contain a JSON object")
        kwargs["candidate_plan_seed"] = candidate_plan_seed
    if startup_direction_blocker:
        kwargs["startup_direction_blocker"] = startup_direction_blocker
    result = build_cn_stock_family_rotation_decision(startup_packet, **kwargs)
    write_cn_stock_family_rotation_decision(output_dir, result)
    if not allow_blocked and not result["decision"]["rotation_decision_cleared"]:
        blockers = ", ".join(result["decision"].get("blockers", []) or [])
        raise RuntimeError(f"CN stock family rotation decision is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Choose the next CN stock factor family after a failed mining branch.")
    parser.add_argument("--startup-gate", default=str(DEFAULT_STARTUP_GATE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--selected-family-id")
    parser.add_argument("--expected-startup-next-direction")
    parser.add_argument("--next-preregistration-direction")
    parser.add_argument("--selected-required-control", action="append", default=[])
    parser.add_argument("--family-candidates-json")
    parser.add_argument("--candidate-plan-seed-json")
    parser.add_argument("--startup-direction-blocker")
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    result = run_cn_stock_family_rotation_decision(
        startup_gate=args.startup_gate,
        output_dir=args.output_dir,
        selected_family_id=args.selected_family_id,
        expected_startup_next_direction=args.expected_startup_next_direction,
        next_preregistration_direction=args.next_preregistration_direction,
        selected_required_controls=args.selected_required_control,
        family_candidates_json=args.family_candidates_json,
        candidate_plan_seed_json=args.candidate_plan_seed_json,
        startup_direction_blocker=args.startup_direction_blocker,
        allow_blocked=args.allow_blocked,
    )
    print(
        json.dumps(
            {
                "status": "cleared" if result["decision"]["rotation_decision_cleared"] else "blocked",
                "summary": result["summary"],
                "decision": result["decision"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
