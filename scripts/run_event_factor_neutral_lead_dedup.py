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

from scripts.run_event_factor_pit_ic_prescreen import (  # noqa: E402
    DEFAULT_BARS_ROOTS,
    DEFAULT_STOCK_BASIC,
    TushareEventEndpointAdapter,
    fetch_round147_event_frames,
)
from quant_robot.ops.event_factor_neutral_lead_dedup import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZON,
    DEFAULT_LEAD_FACTOR_NAME,
    build_event_factor_neutral_lead_dedup,
    summarize_event_factor_neutral_lead_dedup,
    write_event_factor_neutral_lead_dedup,
)
from quant_robot.ops.event_factor_preregistration import default_event_factor_candidate_specs  # noqa: E402


DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/event_factor_pit_ic_prescreen_round147_20260622/event_factor_pit_ic_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/event_factor_neutral_lead_dedup_round148_20260622")
DEFAULT_EVENT_START_YEAR = 2018
DEFAULT_EVENT_END_YEAR = 2025


def run_event_factor_neutral_lead_dedup_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    prescreen_report: str | Path = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
    adapter: Any | None = None,
    event_start_year: int = DEFAULT_EVENT_START_YEAR,
    event_end_year: int = DEFAULT_EVENT_END_YEAR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    lead_factor_frame: pd.DataFrame | None = None,
    labels: pd.DataFrame | None = None,
    reference_factor_frame: pd.DataFrame | None = None,
    exposure_frame: pd.DataFrame | None = None,
    prescreen_report_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lead_factor_frame is not None and labels is not None:
        result = summarize_event_factor_neutral_lead_dedup(
            lead_factor_frame,
            labels,
            reference_factor_frame=reference_factor_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report_payload or _load_report(Path(prescreen_report)),
            lead_factor_name=lead_factor_name,
            horizon=horizon,
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_icir=min_residual_icir,
            min_residual_positive_ic_rate=min_residual_positive_ic_rate,
        )
    else:
        stock_basic = _load_frame(Path(stock_basic_path))
        specs = tuple(spec for spec in default_event_factor_candidate_specs() if spec.factor_name == lead_factor_name)
        frames = event_frames if event_frames is not None else fetch_round147_event_frames(
            adapter or TushareEventEndpointAdapter(),
            start_year=event_start_year,
            end_year=event_end_year,
            candidate_specs=specs,
        )
        result = build_event_factor_neutral_lead_dedup(
            event_frames=frames,
            stock_basic=stock_basic,
            bars_roots=tuple(Path(path) for path in bars_roots),
            daily_basic_roots=tuple(Path(path) for path in daily_basic_roots),
            prescreen_report=prescreen_report_payload or Path(prescreen_report),
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            lead_factor_name=lead_factor_name,
            horizon=horizon,
            execution_lag=execution_lag,
            pit_lag_trade_days=pit_lag_trade_days,
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
        )
    write_event_factor_neutral_lead_dedup(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round148 CN stock event dividend lead public-reference/exposure dedup and residual IC audit."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--event-start-year", type=int, default=DEFAULT_EVENT_START_YEAR)
    parser.add_argument("--event-end-year", type=int, default=DEFAULT_EVENT_END_YEAR)
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--lead-factor-name", default=DEFAULT_LEAD_FACTOR_NAME)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-residual-mean-ic", type=float, default=0.02)
    parser.add_argument("--min-residual-icir", type=float, default=0.20)
    parser.add_argument("--min-residual-positive-ic-rate", type=float, default=0.55)
    args = parser.parse_args()
    result = run_event_factor_neutral_lead_dedup_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        lead_factor_name=args.lead_factor_name,
        horizon=args.horizon,
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        sample_every_n_dates=args.sample_every_n_dates,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_residual_mean_ic=args.min_residual_mean_ic,
        min_residual_icir=args.min_residual_icir,
        min_residual_positive_ic_rate=args.min_residual_positive_ic_rate,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "raw_ic_summary": result.get("raw_ic_summary", {}),
                "residual_ic_summary": result.get("residual_ic_summary", {}),
                "gate": result.get("gate", {}),
                "next_direction": result.get("next_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    main()
