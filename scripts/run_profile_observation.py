from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.profile_observation import build_profile_observation_pack, write_profile_observation_pack


DEFAULT_DAILY_OPS_PACK = Path("data/reports/daily_ops/daily_ops_pack.json")
DEFAULT_SIMULATION_DIR = Path("data/reports/daily_ops/paper_simulation")
DEFAULT_OUTPUT_DIR = Path("data/reports/profile_observation")


def run_profile_observation(
    daily_ops_pack: str | Path = DEFAULT_DAILY_OPS_PACK,
    simulation_dir: str | Path = DEFAULT_SIMULATION_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    run_date: str | None = None,
    max_signal_age_days: int = 7,
    min_fills: int = 20,
    guard_event_warning_ratio: float = 0.5,
) -> dict[str, Any]:
    daily_ops = _read_json(Path(daily_ops_pack))
    sim_dir = Path(simulation_dir)
    pack = build_profile_observation_pack(
        daily_ops,
        simulation_manifest=_read_optional_json(sim_dir / "manifest.json"),
        equity_curve=_read_csv_records(sim_dir / "equity_curve.csv"),
        guard_events=_read_csv_records(sim_dir / "guard_events.csv"),
        execution_events=_read_csv_records(sim_dir / "execution_events.csv"),
        run_date=run_date,
        max_signal_age_days=max_signal_age_days,
        min_fills=min_fills,
        guard_event_warning_ratio=guard_event_warning_ratio,
    )
    write_profile_observation_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Phase 5.6 profile observation ledger with stop rules.")
    parser.add_argument("--daily-ops-pack", default=str(DEFAULT_DAILY_OPS_PACK))
    parser.add_argument("--simulation-dir", default=str(DEFAULT_SIMULATION_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-date")
    parser.add_argument("--max-signal-age-days", default=7, type=int)
    parser.add_argument("--min-fills", default=20, type=int)
    parser.add_argument("--guard-event-warning-ratio", default=0.5, type=float)
    args = parser.parse_args()
    pack = run_profile_observation(
        daily_ops_pack=Path(args.daily_ops_pack),
        simulation_dir=Path(args.simulation_dir),
        output_dir=Path(args.output_dir),
        run_date=args.run_date,
        max_signal_age_days=args.max_signal_age_days,
        min_fills=args.min_fills,
        guard_event_warning_ratio=args.guard_event_warning_ratio,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "run_date": pack["run_date"],
                "decision": pack["decision"],
                "summary": pack["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return []
    return frame.to_dict(orient="records") if not frame.empty else []


if __name__ == "__main__":
    main()
