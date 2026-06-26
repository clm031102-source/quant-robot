from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from scripts.run_event_factor_pit_ic_prescreen import fetch_round147_event_frames  # noqa: E402
from scripts.run_event_factor_preregistration import TushareEventEndpointAdapter  # noqa: E402
from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.event_contextual_underreaction_prescreen import (  # noqa: E402
    default_event_contextual_underreaction_candidate_specs,
)
from quant_robot.ops.event_contextual_underreaction_reference_dedup import (  # noqa: E402
    DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
    build_event_contextual_underreaction_reference_dedup,
    write_event_contextual_underreaction_reference_dedup,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/round248_event_contextual_underreaction_prescreen_20260625/"
    "event_contextual_underreaction_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round249_event_contextual_underreaction_reference_dedup_20260625")
DEFAULT_EVENT_START_YEAR = 2015
DEFAULT_EVENT_END_YEAR = 2025


def run_event_contextual_underreaction_reference_dedup_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    prescreen_report: str | Path | dict[str, Any] = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
    adapter: Any | None = None,
    event_start_year: int = DEFAULT_EVENT_START_YEAR,
    event_end_year: int = DEFAULT_EVENT_END_YEAR,
    max_periods: int | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_reference_correlation_observations: int = 5,
    include_price_volume_references: bool = True,
    price_volume_reference_names: tuple[str, ...] = DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
) -> dict[str, Any]:
    stock_basic = _load_frame(Path(stock_basic_path))
    specs = tuple(default_event_contextual_underreaction_candidate_specs())
    frames = event_frames if event_frames is not None else fetch_round147_event_frames(
        adapter or TushareEventEndpointAdapter(),
        start_year=event_start_year,
        end_year=event_end_year,
        max_periods=max_periods,
        candidate_specs=specs,
    )
    result = build_event_contextual_underreaction_reference_dedup(
        event_frames=frames,
        stock_basic=stock_basic,
        bars_roots=tuple(Path(path) for path in bars_roots),
        prescreen_report=prescreen_report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_reference_correlation_observations=min_reference_correlation_observations,
        include_price_volume_references=include_price_volume_references,
        price_volume_reference_names=price_volume_reference_names,
    )
    write_event_contextual_underreaction_reference_dedup(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round249 contextual event reference de-duplication.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--event-start-year", type=int, default=DEFAULT_EVENT_START_YEAR)
    parser.add_argument("--event-end-year", type=int, default=DEFAULT_EVENT_END_YEAR)
    parser.add_argument("--max-periods", type=int, default=None)
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-reference-correlation-observations", type=int, default=5)
    parser.add_argument("--skip-price-volume-references", action="store_true")
    parser.add_argument("--price-volume-reference-names", default=",".join(DEFAULT_PRICE_VOLUME_REFERENCE_NAMES))
    args = parser.parse_args()
    result = run_event_contextual_underreaction_reference_dedup_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        max_periods=args.max_periods,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        sample_every_n_dates=args.sample_every_n_dates,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_reference_correlation_observations=args.min_reference_correlation_observations,
        include_price_volume_references=not args.skip_price_volume_references,
        price_volume_reference_names=tuple(_split_csv(args.price_volume_reference_names)),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "next_direction": result.get("next_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted(path.rglob("*.parquet")) + sorted(path.rglob("*.csv"))
        frames = [_load_frame(file) for file in files]
        frames = [frame for frame in frames if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


if __name__ == "__main__":
    main()
