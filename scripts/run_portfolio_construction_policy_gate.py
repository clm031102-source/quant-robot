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

from quant_robot.ops.portfolio_construction_policy_gate import (  # noqa: E402
    build_portfolio_construction_policy_gate,
    default_cn_stock_portfolio_policy,
    write_portfolio_construction_policy_gate,
)


DEFAULT_CONFIG = Path("configs/portfolio_construction_policy_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/portfolio_construction_policy_gate")


def run_portfolio_construction_policy_gate_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    config = _load_config(Path(config_path))
    result = build_portfolio_construction_policy_gate(config)
    write_portfolio_construction_policy_gate(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Portfolio construction policy gate is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CN stock portfolio construction policy gate packet.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_portfolio_construction_policy_gate_cli(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir),
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "control_status": result["control_status"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_cn_stock_portfolio_policy()
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
