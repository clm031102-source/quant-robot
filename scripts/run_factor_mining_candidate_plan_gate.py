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

from quant_robot.ops.factor_mining_candidate_plan_gate import (  # noqa: E402
    build_factor_mining_candidate_plan_gate,
    write_factor_mining_candidate_plan_gate,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/factor_mining_candidate_plan_gate")


def run_factor_mining_candidate_plan_gate(
    *,
    candidate_plan: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    quality_gate: str | Path | None = None,
    gate_stage: str = "discovery",
    allow_blocked: bool = False,
) -> dict[str, Any]:
    plan = _load_json(candidate_plan)
    quality_packet = _load_json(quality_gate) if quality_gate else None
    packet = build_factor_mining_candidate_plan_gate(
        plan,
        gate_stage=gate_stage,
        quality_gate=quality_packet,
    )
    write_factor_mining_candidate_plan_gate(output_dir, packet)
    if not allow_blocked and not packet["decision"]["candidate_plan_gate_cleared"]:
        blockers = ", ".join(packet["decision"].get("blockers", []) or [])
        raise RuntimeError(f"Factor mining candidate plan gate is blocked: {blockers}")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a pre-registered CN stock factor candidate plan before mining or promotion."
    )
    parser.add_argument("--candidate-plan", required=True)
    parser.add_argument("--quality-gate")
    parser.add_argument("--gate-stage", choices=["discovery", "portfolio", "promotion"], default="discovery")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    packet = run_factor_mining_candidate_plan_gate(
        candidate_plan=args.candidate_plan,
        quality_gate=args.quality_gate,
        gate_stage=args.gate_stage,
        output_dir=args.output_dir,
        allow_blocked=args.allow_blocked,
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
                "summary": packet["summary"],
                "decision": packet["decision"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
