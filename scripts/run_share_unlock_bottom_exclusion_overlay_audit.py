from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from scripts.run_event_factor_pit_ic_prescreen import (  # noqa: E402
    DEFAULT_BARS_ROOTS,
    DEFAULT_EVENT_END_YEAR,
    DEFAULT_EVENT_START_YEAR,
    DEFAULT_STOCK_BASIC,
    fetch_round147_event_frames,
)
from scripts.run_event_factor_preregistration import TushareEventEndpointAdapter  # noqa: E402
from quant_robot.ops.share_unlock_bottom_exclusion_overlay import (  # noqa: E402
    FACTOR_NAME,
    build_share_unlock_bottom_exclusion_overlay_audit,
    write_share_unlock_bottom_exclusion_overlay_audit,
)
from quant_robot.ops.event_factor_preregistration import default_event_factor_candidate_specs  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/share_unlock_bottom_exclusion_overlay_audit")


def run_share_unlock_bottom_exclusion_overlay_audit(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
    adapter: Any | None = None,
    event_start_year: int = DEFAULT_EVENT_START_YEAR,
    event_end_year: int = DEFAULT_EVENT_END_YEAR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: Sequence[int] = (5, 20),
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    bottom_quantile: float = 0.2,
    rebalance_interval: int = 5,
    min_dates: int = 5,
    min_overlay_t_stat: float = 2.0,
    min_positive_overlay_rate: float = 0.55,
    min_mean_overlay_excess_return: float = 0.0,
) -> dict[str, Any]:
    stock_basic = _load_frame(Path(stock_basic_path))
    specs = tuple(spec for spec in default_event_factor_candidate_specs() if spec.factor_name == FACTOR_NAME)
    if event_frames is None:
        event_frames = fetch_round147_event_frames(
            adapter or TushareEventEndpointAdapter(),
            start_year=event_start_year,
            end_year=event_end_year,
            candidate_specs=specs,
        )
    audit = build_share_unlock_bottom_exclusion_overlay_audit(
        event_frames=event_frames,
        stock_basic=stock_basic,
        bars_roots=tuple(Path(path) for path in bars_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(int(value) for value in horizons),
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        bottom_quantile=bottom_quantile,
        rebalance_interval=rebalance_interval,
        min_dates=min_dates,
        min_overlay_t_stat=min_overlay_t_stat,
        min_positive_overlay_rate=min_positive_overlay_rate,
        min_mean_overlay_excess_return=min_mean_overlay_excess_return,
    )
    write_share_unlock_bottom_exclusion_overlay_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit share-unlock pressure as a bottom-exclusion overlay, not a direct alpha claim."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--event-start-year", type=int, default=DEFAULT_EVENT_START_YEAR)
    parser.add_argument("--event-end-year", type=int, default=DEFAULT_EVENT_END_YEAR)
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default="5,20")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--bottom-quantile", type=float, default=0.2)
    parser.add_argument("--rebalance-interval", type=int, default=5)
    parser.add_argument("--min-dates", type=int, default=5)
    parser.add_argument("--min-overlay-t-stat", type=float, default=2.0)
    parser.add_argument("--min-positive-overlay-rate", type=float, default=0.55)
    parser.add_argument("--min-mean-overlay-excess-return", type=float, default=0.0)
    args = parser.parse_args()

    audit = run_share_unlock_bottom_exclusion_overlay_audit(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(int(item) for item in _split_csv(args.horizons)),
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        bottom_quantile=args.bottom_quantile,
        rebalance_interval=args.rebalance_interval,
        min_dates=args.min_dates,
        min_overlay_t_stat=args.min_overlay_t_stat,
        min_positive_overlay_rate=args.min_positive_overlay_rate,
        min_mean_overlay_excess_return=args.min_mean_overlay_excess_return,
    )
    print(
        json.dumps(
            {
                "summary": audit.get("summary", {}),
                "recommended_next_actions": audit.get("recommended_next_actions", []),
                "top": audit.get("factor_summary", [])[:10],
                "promotion_policy": audit.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([*path.rglob("*.parquet"), *path.rglob("*.csv")])
        files = [file for file in files if "stock_basic" in str(file).replace("\\", "/")]
        if not files:
            raise FileNotFoundError(f"No stock_basic parquet/csv files found under {path}")
        return pd.concat([_load_frame(file) for file in files], ignore_index=True)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported frame path: {path}")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


if __name__ == "__main__":
    main()
