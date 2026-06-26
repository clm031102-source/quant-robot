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

from quant_robot.ops.capacity_safe_price_volume_lead_dedup import (  # noqa: E402
    DEFAULT_LEAD_FACTOR_NAME,
    DEFAULT_LEAD_HORIZON,
    build_capacity_safe_price_volume_lead_dedup,
    write_capacity_safe_price_volume_lead_dedup,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/capacity_safe_price_volume_prescreen_round102_20260622/capacity_safe_price_volume_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/capacity_safe_price_volume_lead_dedup")


def run_capacity_safe_price_volume_lead_dedup_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    prescreen_report: str | Path = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    lead_horizon: int = DEFAULT_LEAD_HORIZON,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    result = build_capacity_safe_price_volume_lead_dedup(
        bars_roots=bars_roots,
        prescreen_report=prescreen_report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        lead_factor_name=lead_factor_name,
        lead_horizon=lead_horizon,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_signal_date_amount=min_signal_date_amount,
    )
    write_capacity_safe_price_volume_lead_dedup(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round103 correlation dedup for the capacity-safe CN stock price-volume research lead."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--lead-factor-name", default=DEFAULT_LEAD_FACTOR_NAME)
    parser.add_argument("--lead-horizon", type=int, default=DEFAULT_LEAD_HORIZON)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    args = parser.parse_args()
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    result = run_capacity_safe_price_volume_lead_dedup_cli(
        bars_roots=bars_roots,
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        lead_factor_name=args.lead_factor_name,
        lead_horizon=args.lead_horizon,
        sample_every_n_dates=args.sample_every_n_dates,
        min_cross_section=args.min_cross_section,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "lead_evidence": result.get("lead_evidence", {}),
                "next_direction": result.get("next_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
