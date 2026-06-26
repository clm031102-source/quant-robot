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

from quant_robot.ops.cn_tradeability_limit_event_preregistration import (  # noqa: E402
    build_cn_tradeability_limit_event_preregistration,
    write_cn_tradeability_limit_event_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/cn_tradeability_limit_event_preregistration_round159_20260623")


def run_cn_tradeability_limit_event_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    min_families: int = 5,
) -> dict[str, Any]:
    result = build_cn_tradeability_limit_event_preregistration(
        min_candidates=min_candidates,
        min_families=min_families,
    )
    write_cn_tradeability_limit_event_preregistration(output_dir, result)
    if not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"CN tradeability limit-event preregistration blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round159 CN tradeability limit-event preregistration.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--min-families", type=int, default=5)
    args = parser.parse_args()
    result = run_cn_tradeability_limit_event_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
        min_families=args.min_families,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "rotation_context": result.get("rotation_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
