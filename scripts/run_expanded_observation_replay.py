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

from quant_robot.ops.expanded_observation_replay import (
    build_expanded_observation_replay_pack,
    write_expanded_observation_replay_pack,
)

try:
    from scripts.run_observation_sufficiency import run_observation_sufficiency
    from scripts.run_post_refresh_replay import run_post_refresh_replay
    from scripts.run_recent_data_refresh import run_recent_data_refresh
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_observation_sufficiency import run_observation_sufficiency
    from run_post_refresh_replay import run_post_refresh_replay
    from run_recent_data_refresh import run_recent_data_refresh


DEFAULT_OBSERVATION_SUFFICIENCY_PACK = Path("data/reports/observation_sufficiency/observation_sufficiency_pack.json")
DEFAULT_PROFILE_OBSERVATION_PACK = Path("data/reports/profile_observation/profile_observation_pack.json")
DEFAULT_REPORT_DIR = Path("data/reports/expanded_observation_replay")


def run_expanded_observation_replay(
    observation_sufficiency_pack: str | Path = DEFAULT_OBSERVATION_SUFFICIENCY_PACK,
    profile_observation_pack: str | Path = DEFAULT_PROFILE_OBSERVATION_PACK,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    source: str = "tushare",
    market: str = "CN_ETF",
    execute: bool = True,
    recent_data_refresh_runner: Callable[..., dict[str, Any]] | None = None,
    post_refresh_replay_runner: Callable[..., dict[str, Any]] | None = None,
    observation_sufficiency_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sufficiency = _read_json(Path(observation_sufficiency_pack))
    output_path = Path(report_dir)
    recent_report_dir = output_path / "recent_data_refresh"
    recent_output_dir = output_path / "processed"
    post_report_dir = output_path / "post_refresh_replay"
    final_sufficiency_dir = output_path / "observation_sufficiency"

    if not _can_extend(sufficiency):
        pack = build_expanded_observation_replay_pack(sufficiency)
        write_expanded_observation_replay_pack(output_path, pack)
        return pack

    recommendation = sufficiency.get("recommendation", {}) if isinstance(sufficiency.get("recommendation"), dict) else {}
    recent_runner = recent_data_refresh_runner or run_recent_data_refresh
    post_runner = post_refresh_replay_runner or run_post_refresh_replay
    sufficiency_runner = observation_sufficiency_runner or run_observation_sufficiency
    recent_pack: dict[str, Any] = {}
    post_pack: dict[str, Any] = {}
    final_sufficiency: dict[str, Any] = {}
    replay_error: dict[str, Any] | None = None
    suggested_start = str(recommendation.get("suggested_start_date"))
    suggested_end = str(recommendation.get("suggested_end_date"))
    try:
        recent_pack = recent_runner(
            profile_observation_pack=Path(profile_observation_pack),
            source=source,
            market=market,
            output_dir=recent_output_dir,
            report_dir=recent_report_dir,
            start_date=suggested_start,
            end_date=suggested_end,
            execute=execute,
        )
        post_pack = post_runner(
            recent_data_refresh_pack=recent_report_dir / "recent_data_refresh_pack.json",
            report_dir=post_report_dir,
            run_date=suggested_end,
        )
        final_sufficiency = sufficiency_runner(
            post_refresh_replay_pack=post_report_dir / "post_refresh_replay_pack.json",
            output_dir=final_sufficiency_dir,
        )
    except Exception as exc:  # pragma: no cover - exact exception depends on downstream workflow
        replay_error = {"stage": "expanded_observation_downstream", "error": str(exc)}

    pack = build_expanded_observation_replay_pack(
        sufficiency,
        recent_data_refresh=recent_pack,
        post_refresh_replay=post_pack,
        final_observation_sufficiency=final_sufficiency,
        replay_error=replay_error,
    )
    write_expanded_observation_replay_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an expanded-window paper observation replay from Phase 5.9 guidance.")
    parser.add_argument("--observation-sufficiency-pack", default=str(DEFAULT_OBSERVATION_SUFFICIENCY_PACK))
    parser.add_argument("--profile-observation-pack", default=str(DEFAULT_PROFILE_OBSERVATION_PACK))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--dry-run", action="store_true", help="Do not execute the expanded recent-data refresh.")
    args = parser.parse_args()
    pack = run_expanded_observation_replay(
        observation_sufficiency_pack=Path(args.observation_sufficiency_pack),
        profile_observation_pack=Path(args.profile_observation_pack),
        report_dir=Path(args.report_dir),
        source=args.source,
        market=args.market,
        execute=not args.dry_run,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "decision": pack["decision"],
                "window": pack["window"],
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _can_extend(pack: dict[str, Any]) -> bool:
    recommendation = pack.get("recommendation", {}) if isinstance(pack.get("recommendation"), dict) else {}
    return (
        pack.get("status") == "needs_more_observation_data"
        and recommendation.get("priority") == "extend_recent_data_window"
        and bool(recommendation.get("suggested_start_date"))
        and bool(recommendation.get("suggested_end_date"))
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
