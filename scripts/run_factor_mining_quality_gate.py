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

from quant_robot.ops.factor_mining_quality_gate import build_factor_mining_quality_gate, render_markdown


DEFAULT_CONFIG = Path("configs/factor_mining_quality_gate_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/factor_mining_quality_gate")


def run_factor_mining_quality_gate(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    config = _load_config(config_path)
    packet = build_factor_mining_quality_gate(config)
    _write_packet(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CN stock factor-mining quality gate packet.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    packet = run_factor_mining_quality_gate(config_path=args.config, output_dir=args.output_dir)
    print(json.dumps(packet, indent=2, sort_keys=True))


def _load_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_packet(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "factor_mining_quality_gate.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_mining_quality_gate.md").write_text(render_markdown(packet), encoding="utf-8")


if __name__ == "__main__":
    main()
