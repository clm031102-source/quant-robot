from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.external_feed_northbound_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_NORTHBOUND_HORIZONS,
    DEFAULT_SEED_CONFIG,
    build_external_feed_northbound_prescreen,
    write_external_feed_northbound_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_PROCESSED_ROOT = Path("data/processed/tushare_external_feeds_round172_long_cycle_monthly_20260623")
DEFAULT_OUTPUT_DIR = Path("data/reports/round191_external_northbound_prescreen_20260623")


def run_external_feed_northbound_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    processed_root: str | Path = DEFAULT_PROCESSED_ROOT,
    seed_config_path: str | Path = DEFAULT_SEED_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_NORTHBOUND_HORIZONS,
    execution_lag: int = 1,
    lookback: int = 20,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    result = build_external_feed_northbound_prescreen(
        bars_roots=tuple(Path(path) for path in bars_roots),
        processed_root=Path(processed_root),
        seed_config_path=Path(seed_config_path),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        lookback=lookback,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
    )
    write_external_feed_northbound_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round191 CN stock external northbound IC/quantile/turnover prescreen."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--seed-config", default=str(DEFAULT_SEED_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default=",".join(str(horizon) for horizon in DEFAULT_NORTHBOUND_HORIZONS))
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    args = parser.parse_args()
    result = run_external_feed_northbound_prescreen_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        processed_root=Path(args.processed_root),
        seed_config_path=Path(args.seed_config),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(int(item.strip()) for item in args.horizons.split(",") if item.strip()),
        execution_lag=args.execution_lag,
        lookback=args.lookback,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "holdout_policy": result.get("holdout_policy", {}),
                "pit_policy": result.get("pit_policy", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
