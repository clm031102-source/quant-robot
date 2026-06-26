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

from quant_robot.ops.china_market_regime_control_gate import (
    build_china_market_regime_control_gate,
    write_china_market_regime_control_gate,
)


DEFAULT_CONFIG = Path("configs/china_market_regime_control_policy_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/china_market_regime_control_gate")


def run_china_market_regime_control_gate_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    result = build_china_market_regime_control_gate(config)
    write_china_market_regime_control_gate(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CN stock China-market regime control gate.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_china_market_regime_control_gate_cli(config_path=args.config, output_dir=args.output_dir)
    print(json.dumps(_sanitize(result), indent=2, sort_keys=True))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
