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

from quant_robot.ops.round266_direction_optimization_gate import (  # noqa: E402
    SELECTED_DIRECTION_ID,
    build_round266_direction_optimization_gate,
    write_round266_direction_optimization_gate,
)


DEFAULT_STARTUP_GATE = Path("data/reports/round266_startup_gate_after_round265_three_round_review_20260626/factor_mining_startup_gate.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/round266_direction_optimization_gate_20260626")


def run_round266_direction_optimization_gate_cli(
    *,
    startup_gate: str | Path = DEFAULT_STARTUP_GATE,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    selected_direction_id: str = SELECTED_DIRECTION_ID,
    allow_blocked: bool = False,
) -> dict[str, Any]:
    startup_path = Path(startup_gate)
    startup_packet = json.loads(startup_path.read_text(encoding="utf-8"))
    result = build_round266_direction_optimization_gate(
        startup_packet,
        selected_direction_id=selected_direction_id,
    )
    write_round266_direction_optimization_gate(output_dir, result)
    if not allow_blocked and not result["decision"]["direction_gate_cleared"]:
        blockers = ", ".join(result["decision"].get("blockers", []) or [])
        raise RuntimeError(f"Round266 direction optimization gate is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Round266 CN stock direction optimization gate.")
    parser.add_argument("--startup-gate", default=str(DEFAULT_STARTUP_GATE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--selected-direction-id", default=SELECTED_DIRECTION_ID)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    result = run_round266_direction_optimization_gate_cli(
        startup_gate=args.startup_gate,
        output_dir=args.output_dir,
        selected_direction_id=args.selected_direction_id,
        allow_blocked=args.allow_blocked,
    )
    print(
        json.dumps(
            {
                "status": "cleared" if result["decision"]["direction_gate_cleared"] else "blocked",
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
