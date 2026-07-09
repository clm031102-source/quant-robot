from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.analyst_report_source_extension_priority_gate import (  # noqa: E402
    run_analyst_report_source_extension_priority_gate,
)


DEFAULT_SOURCE_GATE = Path(
    "data/reports/round748_non_lpr_source_gate_after_source_queue_hibernation_20260709/"
    "cn_stock_non_lpr_orthogonal_source_gate.json"
)
DEFAULT_ANALYST_PRESCREEN = Path(
    "data/reports/round729_analyst_report_revision_jan_jun_local_prescreen_20260709/"
    "analyst_report_revision_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/round748_analyst_source_extension_priority_gate_after_source_queue_hibernation_20260709"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run analyst report source-extension priority gate.")
    parser.add_argument("--source-gate", default=str(DEFAULT_SOURCE_GATE))
    parser.add_argument("--analyst-prescreen", default=str(DEFAULT_ANALYST_PRESCREEN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    result = run_analyst_report_source_extension_priority_gate(
        source_gate_path=Path(args.source_gate),
        analyst_prescreen_path=Path(args.analyst_prescreen),
        output_dir=Path(args.output_dir),
    )
    if not args.allow_blocked and result.get("status") != "ready_to_cache_next_month":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"Analyst report source extension priority gate is not ready: {blockers}")
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
