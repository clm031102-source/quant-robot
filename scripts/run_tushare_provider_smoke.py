from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (SRC_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quant_robot.data.readiness import check_tushare_readiness

try:
    from scripts.ingest_data import run_ingest
except ModuleNotFoundError:  # pragma: no cover - exercised when run directly
    from ingest_data import run_ingest


def run_tushare_provider_smoke(
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    source: str = "tushare",
    market: str = "CN",
    execute: bool = False,
    readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_name = source.strip().lower()
    if source_name not in {"tushare", "tushare-fixture"}:
        raise ValueError("source must be tushare or tushare-fixture")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    readiness_pack = readiness if readiness is not None else _readiness_for_source(source_name)
    if source_name == "tushare" and (not execute or not readiness_pack.get("ready", False)):
        pack = {
            "status": "ready" if readiness_pack.get("ready", False) else "blocked",
            "mode": "execute" if execute else "dry_run",
            "source": source_name,
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
            "readiness": readiness_pack,
            "interfaces": [],
        }
        _write_summary(output_path, pack)
        return pack

    source_map = _source_map(source_name)
    interfaces = [
        _run_interface("daily", source_map["daily"], market, output_path, start_date, end_date),
        _run_interface("daily_basic", source_map["daily_basic"], market, output_path, start_date, end_date),
        _run_interface("moneyflow", source_map["moneyflow"], market, output_path, start_date, end_date),
    ]
    pack = {
        "status": "completed",
        "mode": "execute",
        "source": source_name,
        "market": market,
        "start_date": start_date,
        "end_date": end_date,
        "readiness": readiness_pack,
        "interfaces": interfaces,
    }
    _write_summary(output_path, pack)
    return pack


def _run_interface(
    interface: str,
    source: str,
    market: str,
    output_path: Path,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    result = run_ingest(
        source=source,
        market=market,
        output_dir=output_path / interface,
        start_date=start_date,
        end_date=end_date,
    )
    return _compact_interface_result(interface, result)


def _compact_interface_result(interface: str, result: dict[str, Any]) -> dict[str, Any]:
    report = dict(result.get("quality_report", {}))
    compact = {
        "interface": interface,
        "rows": _int(report.get("rows", result.get("processed_rows", 0))),
        "assets": _int(report.get("assets", 0)),
        "start_date": report.get("start_date"),
        "end_date": report.get("end_date"),
        "downloaded_trade_dates": list(result.get("downloaded_trade_dates", [])),
        "skipped_trade_dates": list(result.get("skipped_trade_dates", [])),
        "duplicate_rows": _int(report.get("duplicate_rows", report.get("duplicate_bars", 0))),
        "missing_asset_id_rows": _int(report.get("missing_asset_id_rows", 0)),
        "missing_numeric_rows": _int(report.get("missing_numeric_rows", 0)),
        "missing_numeric_by_column": dict(report.get("missing_numeric_by_column", {})),
        "zero_volume_rows": _int(report.get("zero_volume_rows", 0)),
        "extreme_return_rows": _int(report.get("extreme_return_rows", 0)),
        "stale_price_rows": _int(report.get("stale_price_rows", 0)),
        "adj_close_jump_rows": _int(report.get("adj_close_jump_rows", 0)),
    }
    if "adjustment_report" in result:
        compact["adjustment_report"] = result["adjustment_report"]
    return compact


def _source_map(source: str) -> dict[str, str]:
    if source == "tushare-fixture":
        return {
            "daily": "tushare-fixture",
            "daily_basic": "tushare-factor-fixture",
            "moneyflow": "tushare-moneyflow-fixture",
        }
    return {
        "daily": "tushare",
        "daily_basic": "tushare-factor",
        "moneyflow": "tushare-moneyflow",
    }


def _readiness_for_source(source: str) -> dict[str, Any]:
    if source == "tushare-fixture":
        return {"source": source, "ready": True, "missing": []}
    return check_tushare_readiness()


def _write_summary(output_path: Path, pack: dict[str, Any]) -> None:
    (output_path / "provider_smoke_summary.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a compact Tushare daily/daily_basic/moneyflow provider smoke.")
    parser.add_argument("--start-date", default="2024-12-27")
    parser.add_argument("--end-date", default="2024-12-31")
    parser.add_argument("--output-dir", default="data/reports/tushare_provider_smoke")
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--execute", action="store_true", help="Call the live Tushare provider when readiness passes.")
    args = parser.parse_args()
    pack = run_tushare_provider_smoke(
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        source=args.source,
        market=args.market,
        execute=args.execute,
    )
    print(json.dumps(pack, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
