from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.promotion.gate import load_promotion_gate_config, run_promotion_gate


def run_promotion_report(
    config_path: str | Path = "configs/promotion_gate_cn_etf.json",
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    config = load_promotion_gate_config(config_path)
    if output_dir is not None:
        config = replace(config, output_dir=Path(output_dir))
    return run_promotion_gate(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pre-API strategy promotion gates.")
    parser.add_argument("--config", default="configs/promotion_gate_cn_etf.json")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    report = run_promotion_report(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"summary": report["summary"], "top": report["candidates"][:10]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
