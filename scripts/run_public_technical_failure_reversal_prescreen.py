from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.public_technical_failure_reversal_prescreen import (  # noqa: E402
    build_public_technical_failure_reversal_prescreen,
    write_public_technical_failure_reversal_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_FACTOR_INPUT_ROOT = Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs")
DEFAULT_MONEYFLOW_INPUT_ROOT = Path("data/processed/office_desktop_20260616_combined_research")
DEFAULT_PREREGISTRATION_JSON = Path(
    "data/reports/public_technical_failure_reversal_preregistration_round154_20260623/public_technical_failure_reversal_preregistration.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/public_technical_failure_reversal_prescreen_round155_20260623")


def run_public_technical_failure_reversal_prescreen_cli(
    *,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    factor_input_root: str | Path = DEFAULT_FACTOR_INPUT_ROOT,
    moneyflow_input_root: str | Path = DEFAULT_MONEYFLOW_INPUT_ROOT,
    preregistration_json: str | Path | None = DEFAULT_PREREGISTRATION_JSON,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = (5, 10, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    alpha: float = 0.05,
) -> dict[str, Any]:
    result = build_public_technical_failure_reversal_prescreen(
        bars_roots=[Path(root) for root in bars_roots],
        factor_input_root=Path(factor_input_root),
        moneyflow_input_root=Path(moneyflow_input_root),
        preregistration_json=Path(preregistration_json) if preregistration_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        alpha=alpha,
    )
    write_public_technical_failure_reversal_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round155 public technical failure-reversal IC prescreen.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--factor-input-root", default=str(DEFAULT_FACTOR_INPUT_ROOT))
    parser.add_argument("--moneyflow-input-root", default=str(DEFAULT_MONEYFLOW_INPUT_ROOT))
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", type=int, action="append", dest="horizons")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    result = run_public_technical_failure_reversal_prescreen_cli(
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        factor_input_root=Path(args.factor_input_root),
        moneyflow_input_root=Path(args.moneyflow_input_root),
        preregistration_json=Path(args.preregistration_json) if args.preregistration_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(args.horizons or (5, 10, 20)),
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        alpha=args.alpha,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
