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

from quant_robot.ops.simulation_paper_ops_package import (
    build_simulation_paper_ops_package,
    write_simulation_paper_ops_package,
)
from quant_robot.ops.simulation_shortlist_paper_handoff import build_simulation_paper_handoff


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a research-to-paper simulation operations package.")
    parser.add_argument("--config", default="configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json")
    parser.add_argument("--paper-handoff")
    parser.add_argument("--capacity-stress")
    parser.add_argument("--extreme-trade-profile")
    parser.add_argument("--blend-audit")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="data/reports/simulation_paper_ops_package")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--max-user-drawdown", type=float, default=-0.30)
    parser.add_argument("--min-oos-strict-pass-rate", type=float, default=0.75)
    args = parser.parse_args()

    config = _read_json(Path(args.config))
    paper_handoff = (
        _read_json(Path(args.paper_handoff))
        if args.paper_handoff
        else build_simulation_paper_handoff(
            config,
            repo_root=Path(args.repo_root),
            periods_per_year=float(args.periods_per_year),
            holding_period=int(args.holding_period),
            max_user_drawdown=float(args.max_user_drawdown),
            min_oos_strict_pass_rate=float(args.min_oos_strict_pass_rate),
        )
    )
    package = build_simulation_paper_ops_package(
        config=config,
        paper_handoff=paper_handoff,
        capacity_stress=_maybe_read_json(args.capacity_stress),
        extreme_trade_profile=_maybe_read_json(args.extreme_trade_profile),
        blend_audit=_maybe_read_json(args.blend_audit) or _dict(config.get("round455_simulation_blend_audit")),
        max_user_drawdown=float(args.max_user_drawdown),
    )
    write_simulation_paper_ops_package(Path(args.output_dir), package)
    print(
        json.dumps(
            {
                "status": package["status"],
                "summary": package["summary"],
                "blockers": package["blockers"],
                "warnings": package["warnings"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _maybe_read_json(path: str | None) -> dict[str, Any] | None:
    return _read_json(Path(path)) if path else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
