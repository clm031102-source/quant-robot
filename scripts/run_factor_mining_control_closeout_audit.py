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

from quant_robot.ops.factor_mining_control_closeout_audit import (
    build_factor_mining_control_closeout_audit,
    write_factor_mining_control_closeout_audit,
)
from quant_robot.ops.factor_mining_quality_gate import build_factor_mining_quality_gate


DEFAULT_QUALITY_GATE_CONFIG = Path("configs/factor_mining_quality_gate_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/factor_mining_control_closeout_audit")


def run_factor_mining_control_closeout_audit(
    *,
    quality_gate: str | Path | None = None,
    quality_gate_config: str | Path = DEFAULT_QUALITY_GATE_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    quality_gate_packet = _load_quality_gate(
        quality_gate=quality_gate,
        quality_gate_config=quality_gate_config,
    )
    packet = build_factor_mining_control_closeout_audit(quality_gate_packet)
    write_factor_mining_control_closeout_audit(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CN stock factor-mining control closeout audit.")
    parser.add_argument("--quality-gate", help="Path to a generated factor_mining_quality_gate.json packet.")
    parser.add_argument("--quality-gate-config", default=str(DEFAULT_QUALITY_GATE_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    packet = run_factor_mining_control_closeout_audit(
        quality_gate=args.quality_gate,
        quality_gate_config=args.quality_gate_config,
        output_dir=args.output_dir,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))


def _load_quality_gate(
    *,
    quality_gate: str | Path | None,
    quality_gate_config: str | Path,
) -> dict[str, Any]:
    if quality_gate:
        return json.loads(Path(quality_gate).read_text(encoding="utf-8"))
    config = json.loads(Path(quality_gate_config).read_text(encoding="utf-8"))
    return build_factor_mining_quality_gate(config)


if __name__ == "__main__":
    main()
