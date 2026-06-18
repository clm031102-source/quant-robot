from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_data_manifest import build_cn_stock_data_manifest, write_cn_stock_data_manifest
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_DATA_ROOT = Path("data/processed")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_data_manifest")


def run_cn_stock_data_manifest(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    market: str = "CN",
    bars: pd.DataFrame | None = None,
    moneyflow_inputs: pd.DataFrame | None = None,
) -> dict[str, Any]:
    market_upper = market.upper()
    if market_upper != "CN":
        raise ValueError("CN stock data manifest only supports market='CN'")
    root = Path(data_root)
    bar_frame = bars if bars is not None else load_processed_bars(root, market_upper)
    moneyflow_frame = moneyflow_inputs if moneyflow_inputs is not None else _load_moneyflow_or_none(root, market_upper)
    manifest = build_cn_stock_data_manifest(bars=bar_frame, moneyflow_inputs=moneyflow_frame, source_root=root)
    write_cn_stock_data_manifest(output_dir, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CN stock data manifest required before factor mining.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    args = parser.parse_args()
    manifest = run_cn_stock_data_manifest(
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir),
        market=args.market,
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blockers": manifest["decision"]["blockers"],
                "warnings": manifest["decision"]["warnings"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_moneyflow_or_none(root: Path, market: str) -> pd.DataFrame | None:
    try:
        return load_moneyflow_inputs(root, market)
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    main()
