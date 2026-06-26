from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.analyst_report_revision_prescreen import (  # noqa: E402
    build_analyst_report_revision_prescreen,
    write_analyst_report_revision_prescreen,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_OUTPUT_DIR = Path("data/reports/analyst_report_revision_prescreen")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PIT analyst report revision IC/neutral prescreen.")
    parser.add_argument("--report-root", action="append", required=True)
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default=",".join(str(horizon) for horizon in DEFAULT_HORIZONS))
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000.0)
    args = parser.parse_args()

    horizons = tuple(int(item.strip()) for item in str(args.horizons).split(",") if item.strip())
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    stock_basic = _load_frame(Path(args.stock_basic))
    result = build_analyst_report_revision_prescreen(
        report_roots=tuple(Path(path) for path in args.report_root),
        bars_roots=bars_roots,
        stock_basic=stock_basic,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=horizons,
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    write_analyst_report_revision_prescreen(Path(args.output_dir), result)
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
                "next_direction": result["summary"].get("next_direction"),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([*path.rglob("*.parquet"), *path.rglob("*.csv")])
        if not files:
            raise FileNotFoundError(f"No parquet/csv files found under {path}")
        return pd.concat([_load_frame(file) for file in files], ignore_index=True)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported frame path: {path}")


if __name__ == "__main__":
    main()
