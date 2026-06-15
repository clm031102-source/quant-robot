from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (SRC_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quant_robot.data.readiness import check_tushare_readiness
from quant_robot.ops.tushare_alpha_factory_gate import (
    build_tushare_alpha_factory_gate_pack,
    write_tushare_alpha_factory_gate_pack,
)

try:
    from scripts.ingest_data import run_ingest
    from scripts.run_tushare_alpha_factory import run_alpha_factory_cli
except ModuleNotFoundError:  # pragma: no cover - exercised when run directly
    from ingest_data import run_ingest
    from run_tushare_alpha_factory import run_alpha_factory_cli


DEFAULT_REPORT_DIR = Path("data/reports/tushare_alpha_factory_gate")
DEFAULT_DATA_ROOT = Path("data/processed/tushare_alpha_factory_gate")


def run_tushare_alpha_factory_gate(
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    source: str = "tushare",
    market: str = "CN",
    start_date: str = "2024-01-02",
    end_date: str = "2024-01-31",
    execute: bool = False,
    top_n: int = 1,
    cost_bps: float = 5.0,
    execution_lag: int = 1,
    alpha: float = 0.05,
    readiness: dict[str, Any] | None = None,
    ingest_runner: Callable[..., dict[str, Any]] | None = None,
    alpha_factory_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_name = source.strip().lower()
    output_path = Path(report_dir)
    data_root_path = Path(data_root)
    readiness_pack = readiness if readiness is not None else _readiness_for_source(source_name)

    if _readiness_blocks(readiness_pack, source_name) or not execute:
        pack = build_tushare_alpha_factory_gate_pack(
            readiness=readiness_pack,
            source=source_name,
            market=market,
            execute=execute,
            data_root=data_root_path,
        )
        write_tushare_alpha_factory_gate_pack(output_path, pack)
        return pack

    ingest = ingest_runner or run_ingest
    factory = alpha_factory_runner or run_alpha_factory_cli
    ohlcv_pack: dict[str, Any] = {}
    factor_pack: dict[str, Any] = {}
    alpha_pack: dict[str, Any] = {}
    chain_error: dict[str, Any] | None = None
    ohlcv_dir = data_root_path / "ohlcv"
    factor_dir = data_root_path / "factor_inputs"
    alpha_dir = output_path / "alpha_factory"

    try:
        ohlcv_pack = ingest(
            source=_ohlcv_source(source_name),
            market=market,
            output_dir=ohlcv_dir,
            start_date=start_date,
            end_date=end_date,
        )
        factor_pack = ingest(
            source=_factor_source(source_name),
            market=market,
            output_dir=factor_dir,
            start_date=start_date,
            end_date=end_date,
        )
        alpha_pack = factory(
            source="processed-bars",
            data_root=data_root_path,
            market=market,
            factor_input_root=factor_dir,
            output_dir=alpha_dir,
            top_n=top_n,
            cost_bps=cost_bps,
            execution_lag=execution_lag,
            alpha=alpha,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:  # pragma: no cover - exact exception depends on provider or local data state
        chain_error = {"stage": "tushare_alpha_factory_downstream", "error": str(exc)}

    pack = build_tushare_alpha_factory_gate_pack(
        readiness=readiness_pack,
        source=source_name,
        market=market,
        execute=execute,
        data_root=data_root_path,
        ohlcv_ingest=ohlcv_pack,
        factor_input_ingest=factor_pack,
        alpha_factory=alpha_pack,
        chain_error=chain_error,
    )
    write_tushare_alpha_factory_gate_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local-only Tushare daily-basic alpha factory gate.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--start-date", default="2024-01-02")
    parser.add_argument("--end-date", default="2024-01-31")
    parser.add_argument("--top-n", default=1, type=int)
    parser.add_argument("--cost-bps", default=5.0, type=float)
    parser.add_argument("--execution-lag", default=1, type=int)
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--execute", action="store_true", help="Execute local ingest and alpha-factory steps after readiness passes.")
    args = parser.parse_args()
    pack = run_tushare_alpha_factory_gate(
        report_dir=Path(args.report_dir),
        data_root=Path(args.data_root),
        source=args.source,
        market=args.market,
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        execution_lag=args.execution_lag,
        alpha=args.alpha,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "mode": pack["mode"],
                "source": pack["source"],
                "decision": pack["decision"],
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _readiness_for_source(source: str) -> dict[str, Any]:
    if source == "tushare-fixture":
        return {"source": source, "ready": True, "missing": []}
    return check_tushare_readiness()


def _readiness_blocks(readiness: dict[str, Any], source: str) -> bool:
    return source == "tushare" and not bool(readiness.get("ready", False))


def _ohlcv_source(source: str) -> str:
    return "tushare-fixture" if source == "tushare-fixture" else "tushare"


def _factor_source(source: str) -> str:
    return "tushare-factor-fixture" if source == "tushare-fixture" else "tushare-factor"


if __name__ == "__main__":
    main()
