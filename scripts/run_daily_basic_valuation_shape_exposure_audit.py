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

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_valuation_shape_exposure_audit import (  # noqa: E402
    build_valuation_shape_exposure_audit_from_roots,
    write_valuation_shape_exposure_audit,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),)
DEFAULT_STOCK_BASIC = Path(
    "data/reports/round212_stock_basic_snapshot_20260624/metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-24/part-00000.parquet"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round212_daily_basic_valuation_shape_exposure_audit_20260624")


def run_daily_basic_valuation_shape_exposure_audit_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    stock_basic: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    horizons: tuple[int, ...] = (20,),
    execution_lag: int = 1,
    min_dates: int = 80,
    min_cross_section: int = 100,
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    candidate_plan_gate_packet: str | Path | None = Path(
        "data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json"
    ),
) -> dict[str, Any]:
    result = build_valuation_shape_exposure_audit_from_roots(
        bars_roots=tuple(Path(path) for path in bars_roots),
        daily_basic_roots=tuple(Path(path) for path in daily_basic_roots),
        stock_basic=_read_frame(stock_basic),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        horizons=horizons,
        execution_lag=execution_lag,
        min_dates=min_dates,
        min_cross_section=min_cross_section,
    )
    result = _attach_gate_packet_trace(
        result,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        candidate_plan_gate_packet=candidate_plan_gate_packet,
    )
    write_valuation_shape_exposure_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round212 valuation shape and exposure audit.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--horizons", default="20")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-dates", type=int, default=80)
    parser.add_argument("--min-cross-section", type=int, default=100)
    parser.add_argument(
        "--startup-gate-packet",
        default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json",
        help="CN stock factor-mining startup gate packet to record in the diagnostic output.",
    )
    parser.add_argument(
        "--data-manifest-packet",
        default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
        help="CN stock data manifest packet to record in the diagnostic output.",
    )
    parser.add_argument(
        "--candidate-plan-gate-packet",
        default="data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json",
        help="Candidate-plan gate packet to record in the diagnostic output.",
    )
    args = parser.parse_args()
    result = run_daily_basic_valuation_shape_exposure_audit_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        stock_basic=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        horizons=tuple(int(item.strip()) for item in args.horizons.split(",") if item.strip()),
        execution_lag=args.execution_lag,
        min_dates=args.min_dates,
        min_cross_section=args.min_cross_section,
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        candidate_plan_gate_packet=Path(args.candidate_plan_gate_packet) if args.candidate_plan_gate_packet else None,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "promotion_policy": result["promotion_policy"],
                "gate_packets": result.get("gate_packets", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _attach_gate_packet_trace(
    result: dict[str, Any],
    *,
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    candidate_plan_gate_packet: str | Path | None,
) -> dict[str, Any]:
    gate_packets = {
        "startup_gate_packet": _path_text(startup_gate_packet),
        "data_manifest_packet": _path_text(data_manifest_packet),
        "candidate_plan_gate_packet": _path_text(candidate_plan_gate_packet),
    }
    return {**result, "gate_packets": gate_packets}


def _path_text(path: str | Path | None) -> str | None:
    return str(path) if path is not None else None


def _read_frame(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)
    if input_path.suffix.lower() == ".parquet":
        return pd.read_parquet(input_path)
    return pd.read_csv(input_path)


if __name__ == "__main__":
    main()
