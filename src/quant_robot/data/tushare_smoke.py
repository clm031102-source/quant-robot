from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness


def build_tushare_smoke_plan(start_date: str, end_date: str, output_dir: Path, execute: bool = False) -> dict[str, Any]:
    return {
        "source": "tushare",
        "market": "CN",
        "start_date": start_date,
        "end_date": end_date,
        "output_dir": str(output_dir),
        "mode": "execute" if execute else "dry_run",
        "will_download": bool(execute),
        "safety": "Dry-run does not download data. Execute mode uses Tushare only after readiness passes.",
    }


def run_tushare_smoke(
    start_date: str,
    end_date: str,
    output_dir: Path,
    execute: bool = False,
    readiness: dict[str, Any] | None = None,
    ingest_runner: Callable[[str, str, Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    plan = build_tushare_smoke_plan(start_date, end_date, output_dir, execute=execute)
    readiness = readiness or _combined_readiness()
    if not execute:
        return {
            **plan,
            "status": "ready" if readiness["ready"] else "blocked",
            "readiness": readiness,
        }
    if not readiness["ready"]:
        return {
            **plan,
            "will_download": False,
            "status": "blocked",
            "readiness": readiness,
        }
    runner = ingest_runner or _real_tushare_ingest
    result = runner(start_date, end_date, output_dir)
    return {
        **plan,
        "status": "completed",
        "readiness": readiness,
        "ingest": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan or run a safe Tushare A-share smoke ingest.")
    parser.add_argument("--start-date", default="2024-01-02")
    parser.add_argument("--end-date", default="2024-01-06")
    parser.add_argument("--output-dir", default="data/raw/tushare_smoke")
    parser.add_argument("--execute", action="store_true", help="Actually call Tushare after readiness passes.")
    args = parser.parse_args()
    result = run_tushare_smoke(
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        execute=args.execute,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _combined_readiness() -> dict[str, Any]:
    tushare = check_tushare_readiness()
    parquet = check_parquet_readiness()
    missing = list(tushare["missing"]) + list(parquet["missing"])
    return {
        "ready": bool(tushare["ready"] and parquet["ready"]),
        "missing": missing,
        "tushare": tushare,
        "parquet": parquet,
    }


def _real_tushare_ingest(start_date: str, end_date: str, output_dir: Path) -> dict[str, Any]:
    return run_tushare_daily_ingest(TushareAdapter(), start_date, end_date, output_dir)


if __name__ == "__main__":
    main()
