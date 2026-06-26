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

from quant_robot.ops.alpha101_rank_pv_reversal_reference_dedup import (  # noqa: E402
    DEFAULT_HORIZON,
    DEFAULT_LEAD_FACTOR_NAME,
    build_alpha101_rank_pv_reversal_reference_dedup,
    build_alpha101_rank_pv_reversal_reference_dedup_from_frames,
    write_alpha101_rank_pv_reversal_reference_dedup,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_FACTOR_INPUT_ROOT = Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs")
DEFAULT_MONEYFLOW_INPUT_ROOT = Path("data/processed/office_desktop_20260616_combined_research")
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/public_reference_multi_family_prescreen_round128_20260622/public_reference_multi_family_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/alpha101_rank_pv_reversal_reference_dedup_round129_20260622")


def run_alpha101_rank_pv_reversal_reference_dedup_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    factor_input_root: str | Path = DEFAULT_FACTOR_INPUT_ROOT,
    moneyflow_input_root: str | Path = DEFAULT_MONEYFLOW_INPUT_ROOT,
    bars_path: str | Path | None = None,
    factor_input_path: str | Path | None = None,
    moneyflow_input_path: str | Path | None = None,
    prescreen_report: str | Path = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    if bars_path is not None:
        result = build_alpha101_rank_pv_reversal_reference_dedup_from_frames(
            bars=_read_frame(Path(bars_path)),
            factor_inputs=_read_frame(Path(factor_input_path)) if factor_input_path is not None else pd.DataFrame(),
            moneyflow_inputs=_read_frame(Path(moneyflow_input_path)) if moneyflow_input_path is not None else pd.DataFrame(),
            prescreen_report=json.loads(Path(prescreen_report).read_text(encoding="utf-8")),
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            lead_factor_name=lead_factor_name,
            horizon=horizon,
            execution_lag=execution_lag,
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_signal_date_amount=min_signal_date_amount,
        )
    else:
        result = build_alpha101_rank_pv_reversal_reference_dedup(
            bars_roots=bars_roots,
            factor_input_root=factor_input_root,
            moneyflow_input_root=moneyflow_input_root,
            prescreen_report=Path(prescreen_report),
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            lead_factor_name=lead_factor_name,
            horizon=horizon,
            execution_lag=execution_lag,
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_signal_date_amount=min_signal_date_amount,
        )
    write_alpha101_rank_pv_reversal_reference_dedup(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round129 Alpha101 rank PV reversal reference de-duplication audit."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--factor-input-root", default=str(DEFAULT_FACTOR_INPUT_ROOT))
    parser.add_argument("--moneyflow-input-root", default=str(DEFAULT_MONEYFLOW_INPUT_ROOT))
    parser.add_argument("--bars-path", default=None)
    parser.add_argument("--factor-input-path", default=None)
    parser.add_argument("--moneyflow-input-path", default=None)
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--lead-factor-name", default=DEFAULT_LEAD_FACTOR_NAME)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    args = parser.parse_args()
    result = run_alpha101_rank_pv_reversal_reference_dedup_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        factor_input_root=Path(args.factor_input_root),
        moneyflow_input_root=Path(args.moneyflow_input_root),
        bars_path=Path(args.bars_path) if args.bars_path else None,
        factor_input_path=Path(args.factor_input_path) if args.factor_input_path else None,
        moneyflow_input_path=Path(args.moneyflow_input_path) if args.moneyflow_input_path else None,
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        lead_factor_name=args.lead_factor_name,
        horizon=args.horizon,
        execution_lag=args.execution_lag,
        sample_every_n_dates=args.sample_every_n_dates,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    print(
        json.dumps(
            {
                "summary": result.get("summary", {}),
                "lead_evidence": result.get("lead_evidence", {}),
                "lead_ic_summary": result.get("lead_ic_summary", {}),
                "gate": result.get("gate", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "next_direction": result.get("next_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


if __name__ == "__main__":
    main()
