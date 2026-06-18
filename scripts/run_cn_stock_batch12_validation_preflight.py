from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.batch12_validation_preflight import (
    build_batch12_validation_preflight,
    write_batch12_validation_preflight,
)


DEFAULT_HANDOFF = Path("configs/cn_stock_batch12_validation_handoff_20260617.json")
DEFAULT_STARTUP_GATE = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_batch12_validation_preflight")


def run_cn_stock_batch12_validation_preflight(
    *,
    handoff_path: str | Path = DEFAULT_HANDOFF,
    startup_gate_packet: str | Path = DEFAULT_STARTUP_GATE,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    machine: str,
    task: str,
    branch: str,
    current_branch: str | None = None,
    market: str = "CN",
    asset_type: str = "stock",
    final_holdout_touched: bool = False,
) -> dict[str, Any]:
    handoff = _load_json(handoff_path)
    startup_gate = _load_json(startup_gate_packet)
    packet = build_batch12_validation_preflight(
        handoff=handoff,
        startup_gate=startup_gate,
        request={
            "machine": machine,
            "task": task,
            "branch": branch,
            "current_branch": current_branch or _current_branch(),
            "market": market,
            "asset_type": asset_type,
            "final_holdout_touched": final_holdout_touched,
        },
    )
    write_batch12_validation_preflight(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight the Batch 12 CN stock validation handoff before any 2025 OOS read.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    parser.add_argument("--startup-gate-packet", default=str(DEFAULT_STARTUP_GATE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--current-branch")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--asset-type", default="stock")
    parser.add_argument("--final-holdout-touched", action="store_true")
    args = parser.parse_args()
    packet = run_cn_stock_batch12_validation_preflight(
        handoff_path=Path(args.handoff),
        startup_gate_packet=Path(args.startup_gate_packet),
        output_dir=Path(args.output_dir),
        machine=args.machine,
        task=args.task,
        branch=args.branch,
        current_branch=args.current_branch,
        market=args.market,
        asset_type=args.asset_type,
        final_holdout_touched=args.final_holdout_touched,
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
                "summary": packet["summary"],
                "blockers": packet["decision"]["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


if __name__ == "__main__":
    main()

