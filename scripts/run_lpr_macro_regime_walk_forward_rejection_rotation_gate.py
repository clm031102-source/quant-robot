from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_walk_forward_rejection_rotation_gate import (  # noqa: E402
    run_lpr_macro_regime_walk_forward_rejection_rotation_gate,
)


DEFAULT_VALIDATION = Path(
    "data/reports/round737_lpr_macro_regime_state_conditioned_walk_forward_validation_20260709/"
    "lpr_macro_regime_state_conditioned_walk_forward_validation.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round738_lpr_macro_regime_walk_forward_rejection_rotation_gate_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR walk-forward rejection rotation gate.")
    parser.add_argument("--validation", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-not-cleared", action="store_true")
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_walk_forward_rejection_rotation_gate(
        validation_path=Path(args.validation),
        output_dir=Path(args.output_dir),
    )
    if not args.allow_not_cleared and result.get("status") != "cleared":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"LPR walk-forward rejection rotation gate is not cleared: {blockers}")
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "summary": result.get("summary", {}),
                "decision": result.get("decision", {}),
                "rotation_policy": result.get("rotation_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
