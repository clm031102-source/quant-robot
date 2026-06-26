from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.batch12_oos_validation import run_batch12_oos_validation
from quant_robot.storage.authority_bars import (
    load_authority_processed_bars_from_config,
    load_authority_processed_dataset_from_config,
)


DEFAULT_HANDOFF = Path("configs/cn_stock_batch12_validation_handoff_20260617.json")
DEFAULT_PREFLIGHT = Path("data/reports/cn_stock_batch12_validation_preflight_20260620_current/batch12_validation_preflight.json")
DEFAULT_BARS = Path("configs/cn_stock_authority_bars_2015_2025.json")
DEFAULT_DAILY_BASIC = Path("configs/cn_stock_authority_daily_basic_inputs_2015_2025.json")
DEFAULT_OUTPUT = Path("data/reports/cn_stock_batch12_oos_validation_20260620")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run locked 2025 OOS validation for Batch12 CN stock candidates.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    parser.add_argument("--preflight", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--authority-bars-config", default=str(DEFAULT_BARS))
    parser.add_argument("--daily-basic-config", default=str(DEFAULT_DAILY_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--feature-window-start", default="2024-10-01")
    parser.add_argument("--final-holdout-touched", action="store_true")
    args = parser.parse_args()
    handoff = json.loads(Path(args.handoff).read_text(encoding="utf-8"))
    preflight = json.loads(Path(args.preflight).read_text(encoding="utf-8"))
    bars = load_authority_processed_bars_from_config(args.authority_bars_config, markets=("CN",))
    daily_basic = load_authority_processed_dataset_from_config(
        args.daily_basic_config,
        market="CN",
        dataset="processed/factor_inputs",
    )
    packet = run_batch12_oos_validation(
        bars=bars,
        daily_basic_inputs=daily_basic,
        handoff=handoff,
        preflight=preflight,
        output_dir=Path(args.output_dir),
        final_holdout_touched=args.final_holdout_touched,
        feature_window_start=args.feature_window_start,
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
                "validation_window": packet["validation_window"],
                "summary": packet["summary"],
                "output_dir": packet["output_dir"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
