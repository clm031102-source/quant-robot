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
    build_event_contextual_underreaction_prescreen,
    default_event_contextual_underreaction_candidate_specs,
    write_event_contextual_underreaction_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/round248_event_contextual_underreaction_prescreen_20260625")
DEFAULT_EVENT_START_YEAR = 2015
DEFAULT_EVENT_END_YEAR = 2025


def run_event_contextual_underreaction_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
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
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    alpha: float = 0.05,
) -> dict[str, Any]:
    stock_basic = _load_frame(Path(stock_basic_path))
    specs = _candidate_specs(candidate_names)
    frames = event_frames if event_frames is not None else fetch_round147_event_frames(
        adapter or TushareEventEndpointAdapter(),
        start_year=event_start_year,
        end_year=event_end_year,
        max_periods=max_periods,
        candidate_specs=specs,
    )
    result = build_event_contextual_underreaction_prescreen(
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
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
    )
    write_event_contextual_underreaction_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round248 contextual event underreaction PIT/IC prescreen.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
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
    parser.add_argument("--min-neutral-rank-ic", type=float, default=0.01)
    parser.add_argument("--min-neutral-ic-t-stat", type=float, default=2.0)
    parser.add_argument("--min-neutral-retention", type=float, default=0.50)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    result = run_event_contextual_underreaction_prescreen_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        max_periods=args.max_periods,
        candidate_names=tuple(_split_csv(args.candidate_names)) or None,
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
        min_neutral_rank_ic=args.min_neutral_rank_ic,
        min_neutral_ic_t_stat=args.min_neutral_ic_t_stat,
        min_neutral_retention=args.min_neutral_retention,
        alpha=args.alpha,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "round_context": result.get("round_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _candidate_specs(candidate_names: tuple[str, ...] | None) -> tuple[Any, ...]:
    specs = tuple(default_event_contextual_underreaction_candidate_specs())
    if not candidate_names:
        return specs
    allowed = set(candidate_names)
    selected = tuple(spec for spec in specs if spec.factor_name in allowed)
    missing = sorted(allowed.difference({spec.factor_name for spec in selected}))
    if missing:
        raise ValueError(f"Unknown contextual event candidates: {', '.join(missing)}")
    return selected


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted(path.rglob("*.parquet")) + sorted(path.rglob("*.csv"))
        frames = [_load_frame(file) for file in files]
        frames = [frame for frame in frames if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


if __name__ == "__main__":
    main()
