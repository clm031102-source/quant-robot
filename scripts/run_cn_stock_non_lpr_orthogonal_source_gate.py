from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_non_lpr_orthogonal_source_gate import (  # noqa: E402
    run_cn_stock_non_lpr_orthogonal_source_gate,
)


DEFAULT_ROUND738_ROTATION_GATE = Path(
    "data/reports/round738_lpr_macro_regime_walk_forward_rejection_rotation_gate_20260709/"
    "lpr_macro_regime_walk_forward_rejection_rotation_gate.json"
)
DEFAULT_READINESS_GATE = Path(
    "data/reports/round729_factor_batch_readiness_local_prescreen_gate_20260709/"
    "factor_batch_readiness_gate.json"
)
DEFAULT_ANALYST_PRESCREEN = Path(
    "data/reports/round729_analyst_report_revision_jan_jun_local_prescreen_20260709/"
    "analyst_report_revision_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round739_non_lpr_orthogonal_source_gate_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CN stock non-LPR orthogonal source selector gate.")
    parser.add_argument("--round738-rotation-gate", default=str(DEFAULT_ROUND738_ROTATION_GATE))
    parser.add_argument("--readiness-gate", default=str(DEFAULT_READINESS_GATE))
    parser.add_argument("--analyst-prescreen", default=str(DEFAULT_ANALYST_PRESCREEN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    result = run_cn_stock_non_lpr_orthogonal_source_gate(
        round738_rotation_gate_path=Path(args.round738_rotation_gate),
        readiness_gate_path=Path(args.readiness_gate),
        analyst_prescreen_path=Path(args.analyst_prescreen),
        output_dir=Path(args.output_dir),
    )
    if not args.allow_blocked and result.get("status") != "ready":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"CN stock non-LPR orthogonal source gate is not ready: {blockers}")
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "summary": result.get("summary", {}),
                "decision": result.get("decision", {}),
                "output_dir": str(Path(args.output_dir)),
                "safety": result.get("safety", ""),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
