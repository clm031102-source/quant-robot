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

from scripts.run_event_factor_preregistration import TushareEventEndpointAdapter  # noqa: E402
from quant_robot.ops.event_factor_pit_ic_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    build_event_factor_pit_ic_prescreen,
    write_event_factor_pit_ic_prescreen,
)
from quant_robot.ops.event_factor_preregistration import (  # noqa: E402
    EventFactorCandidateSpec,
    default_event_factor_candidate_specs,
)
from quant_robot.storage.dataset_store import DatasetStore  # noqa: E402


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/event_factor_pit_ic_prescreen_round147_20260622")
DEFAULT_EVENT_START_YEAR = 2015
DEFAULT_EVENT_END_YEAR = 2025
DEFAULT_FORECAST_ANN_DAY_SUFFIXES = ("0131", "0430", "0731", "0831", "1031")


def run_event_factor_pit_ic_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
    event_cache_root: str | Path | None = None,
    adapter: Any | None = None,
    event_start_year: int = DEFAULT_EVENT_START_YEAR,
    event_end_year: int = DEFAULT_EVENT_END_YEAR,
    max_periods: int | None = None,
    candidate_names: tuple[str, ...] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    stock_basic = _load_frame(Path(stock_basic_path))
    specs = _candidate_specs(candidate_names)
    if event_frames is not None:
        frames = event_frames
    elif event_cache_root is not None:
        frames = load_cached_forecast_express_event_frames(
            event_cache_root,
            start_year=event_start_year,
            end_year=event_end_year,
            endpoints=_cacheable_endpoints(specs),
        )
        missing_specs = tuple(
            spec
            for spec in specs
            if any(endpoint not in {"forecast", "express"} for endpoint in spec.required_endpoints)
        )
        if missing_specs:
            frames.update(
                fetch_round147_event_frames(
                    adapter or TushareEventEndpointAdapter(),
                    start_year=event_start_year,
                    end_year=event_end_year,
                    max_periods=max_periods,
                    candidate_specs=missing_specs,
                )
            )
    else:
        frames = fetch_round147_event_frames(
            adapter or TushareEventEndpointAdapter(),
            start_year=event_start_year,
            end_year=event_end_year,
            max_periods=max_periods,
            candidate_specs=specs,
        )
    result = build_event_factor_pit_ic_prescreen(
        bars_roots=tuple(Path(path) for path in bars_roots),
        stock_basic=stock_basic,
        event_frames=frames,
        candidate_specs=specs,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    write_event_factor_pit_ic_prescreen(output_dir, result)
    return result


def fetch_round147_event_frames(
    adapter: Any,
    *,
    start_year: int,
    end_year: int,
    max_periods: int | None = None,
    candidate_specs: tuple[EventFactorCandidateSpec, ...] | None = None,
) -> dict[str, pd.DataFrame]:
    endpoints = {endpoint for spec in (candidate_specs or tuple(default_event_factor_candidate_specs())) for endpoint in spec.required_endpoints}
    periods = _quarter_periods(start_year, end_year)
    if max_periods is not None:
        periods = periods[-max_periods:]
    annual_end_dates = tuple(f"{year}1231" for year in range(start_year - 1, end_year + 1))
    frames: dict[str, pd.DataFrame] = {}
    if "forecast" in endpoints:
        frames["forecast"] = _fetch_concat(
            adapter,
            "forecast",
            ({"ann_date": f"{year}{suffix}"} for year in range(start_year, end_year + 1) for suffix in DEFAULT_FORECAST_ANN_DAY_SUFFIXES),
        )
    if "dividend" in endpoints:
        frames["dividend"] = _fetch_concat(adapter, "dividend", ({"end_date": end_date} for end_date in annual_end_dates))
    if "repurchase" in endpoints:
        frames["repurchase"] = _fetch_concat(
            adapter,
            "repurchase",
            ({"start_date": f"{year}0101", "end_date": f"{year}1231"} for year in range(start_year, end_year + 1)),
        )
    if "stk_holdernumber" in endpoints:
        frames["stk_holdernumber"] = _fetch_concat(adapter, "stk_holdernumber", ({"end_date": period} for period in periods))
    if "share_float" in endpoints:
        frames["share_float"] = _fetch_concat(
            adapter,
            "share_float",
            ({"start_date": f"{year}0101", "end_date": f"{year}1231"} for year in range(start_year, end_year + 1)),
        )
    if "top10_holders" in endpoints:
        frames["top10_holders"] = _fetch_concat(adapter, "top10_holders", ({"period": period} for period in periods))
    if "top10_floatholders" in endpoints:
        frames["top10_floatholders"] = _fetch_concat(adapter, "top10_floatholders", ({"period": period} for period in periods))
    if "pledge_stat" in endpoints:
        pledge_periods = _weekly_periods(start_year, end_year)
        if max_periods is not None:
            pledge_periods = pledge_periods[-max_periods:]
        frames["pledge_stat"] = _fetch_concat(adapter, "pledge_stat", ({"end_date": period} for period in pledge_periods))
    return frames


def load_cached_forecast_express_event_frames(
    event_cache_root: str | Path,
    *,
    start_year: int,
    end_year: int,
    endpoints: Sequence[str] = ("forecast", "express"),
    market: str = "CN",
) -> dict[str, pd.DataFrame]:
    store = DatasetStore(event_cache_root)
    frames: dict[str, pd.DataFrame] = {}
    for endpoint in endpoints:
        endpoint_name = str(endpoint).strip()
        dataset = {
            "forecast": "processed/event_forecast",
            "express": "processed/event_express",
        }.get(endpoint_name)
        if dataset is None:
            continue
        pieces = []
        for year in range(int(start_year), int(end_year) + 1):
            partitions = {"frequency": "event", "market": market.upper(), "year": str(year)}
            if store.exists(dataset, partitions):
                pieces.append(store.read_frame(dataset, partitions))
        frame = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
        frames[endpoint_name] = _normalise_cached_event_frame(frame)
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round147 CN stock event-factor PIT/IC prescreen.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--event-cache-root", default="")
    parser.add_argument("--event-start-year", type=int, default=DEFAULT_EVENT_START_YEAR)
    parser.add_argument("--event-end-year", type=int, default=DEFAULT_EVENT_END_YEAR)
    parser.add_argument("--max-periods", type=int, default=None)
    parser.add_argument("--candidate-names", default="")
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default="5,20")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    args = parser.parse_args()
    candidate_names = tuple(_split_csv(args.candidate_names)) or None
    result = run_event_factor_pit_ic_prescreen_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        event_cache_root=Path(args.event_cache_root) if args.event_cache_root else None,
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        max_periods=args.max_periods,
        candidate_names=candidate_names,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(int(item) for item in _split_csv(args.horizons)),
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "holdout_policy": result.get("holdout_policy", {}),
                "pit_policy": result.get("pit_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _fetch_concat(adapter: Any, endpoint: str, requests: Iterable[dict[str, str]]) -> pd.DataFrame:
    frames = []
    for kwargs in requests:
        try:
            frame = adapter.fetch_event_endpoint(endpoint, **kwargs)
        except Exception:  # pragma: no cover - live provider behavior
            continue
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)


def _quarter_periods(start_year: int, end_year: int) -> tuple[str, ...]:
    return tuple(
        f"{year}{suffix}"
        for year in range(start_year, end_year + 1)
        for suffix in ("0331", "0630", "0930", "1231")
    )


def _weekly_periods(start_year: int, end_year: int) -> tuple[str, ...]:
    return tuple(
        date.strftime("%Y%m%d")
        for date in pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="W-FRI")
    )


def _candidate_specs(candidate_names: tuple[str, ...] | None) -> tuple[EventFactorCandidateSpec, ...]:
    specs = tuple(default_event_factor_candidate_specs())
    if not candidate_names:
        return specs
    allowed = set(candidate_names)
    return tuple(spec for spec in specs if spec.factor_name in allowed)


def _cacheable_endpoints(specs: Sequence[EventFactorCandidateSpec]) -> tuple[str, ...]:
    endpoints = sorted(
        {
            endpoint
            for spec in specs
            for endpoint in spec.required_endpoints
            if endpoint in {"forecast", "express"}
        }
    )
    return tuple(endpoints or ("forecast", "express"))


def _normalise_cached_event_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    if "ann_date" not in output.columns and "event_date" in output.columns:
        output["ann_date"] = pd.to_datetime(output["event_date"], errors="coerce")
    if "ts_code" not in output.columns and "symbol" in output.columns:
        output["ts_code"] = output["symbol"].astype(str)
    if "market" not in output.columns:
        output["market"] = "CN"
    return output.reset_index(drop=True)


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
