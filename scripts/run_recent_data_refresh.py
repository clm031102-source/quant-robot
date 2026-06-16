from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.readiness import check_tushare_readiness
from quant_robot.ops.recent_data_refresh import (
    build_recent_data_refresh_pack,
    build_workstation_refresh_context,
    resolve_refresh_window,
    write_recent_data_refresh_pack,
)

try:
    from scripts.ingest_data import run_ingest
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from ingest_data import run_ingest


DEFAULT_PROFILE_OBSERVATION_PACK = Path("data/reports/profile_observation/profile_observation_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/tushare_etf_recent")
DEFAULT_REPORT_DIR = Path("data/reports/recent_data_refresh")
DEFAULT_WORKSTATIONS_CONFIG = Path("configs/workstations.json")


def run_recent_data_refresh(
    profile_observation_pack: str | Path = DEFAULT_PROFILE_OBSERVATION_PACK,
    source: str = "tushare",
    market: str = "CN_ETF",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    start_date: str | None = None,
    end_date: str | None = None,
    execute: bool = False,
    readiness: dict[str, Any] | None = None,
    ingest_runner: Callable[..., dict[str, Any]] | None = None,
    machine: str | None = None,
    workstation_config: dict[str, Any] | None = None,
    workstations_config_path: str | Path = DEFAULT_WORKSTATIONS_CONFIG,
) -> dict[str, Any]:
    profile_pack = _read_json(Path(profile_observation_pack))
    window = resolve_refresh_window(profile_pack, start_date=start_date, end_date=end_date)
    source_name = source.strip().lower()
    readiness_pack = readiness if readiness is not None else _readiness_for_source(source_name)
    resolved_workstation_config = workstation_config
    if machine and resolved_workstation_config is None:
        resolved_workstation_config = _read_json(Path(workstations_config_path))
    workstation = build_workstation_refresh_context(machine, resolved_workstation_config)
    can_run_data_pipeline = bool(workstation.get("can_run_data_pipeline", True))
    ingest_result = None
    can_execute = execute and can_run_data_pipeline and (source_name != "tushare" or bool(readiness_pack.get("ready", False)))
    if can_execute:
        runner = ingest_runner or run_ingest
        ingest_result = runner(
            source=source_name,
            market=market.upper(),
            output_dir=Path(output_dir),
            start_date=str(window["start_date"]),
            end_date=str(window["end_date"]),
        )
    pack = build_recent_data_refresh_pack(
        profile_pack,
        readiness=readiness_pack,
        ingest_result=ingest_result,
        execute=execute,
        machine=machine,
        workstation_config=resolved_workstation_config,
        source=source_name,
        market=market,
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
    )
    write_recent_data_refresh_pack(report_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or execute a Phase 5.7 Tushare recent-data refresh pack.")
    parser.add_argument("--profile-observation-pack", default=str(DEFAULT_PROFILE_OBSERVATION_PACK))
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--machine", help="Current workstation name from configs/workstations.json.")
    parser.add_argument("--workstations-config", default=str(DEFAULT_WORKSTATIONS_CONFIG))
    parser.add_argument("--execute", action="store_true", help="Actually run the selected data ingest after readiness passes.")
    args = parser.parse_args()
    pack = run_recent_data_refresh(
        profile_observation_pack=Path(args.profile_observation_pack),
        source=args.source,
        market=args.market,
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        start_date=args.start_date,
        end_date=args.end_date,
        execute=args.execute,
        machine=args.machine,
        workstations_config_path=Path(args.workstations_config),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "mode": pack["mode"],
                "will_download": pack["will_download"],
                "target_window": pack["target_window"],
                "workstation": pack.get("workstation", {}),
                "decision": pack["decision"],
                "coverage": pack["coverage"],
                "next_actions": pack.get("next_actions", []),
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


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
