from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.run_project_completion_gate import discover_latest_observation_sufficiency_pack
except ModuleNotFoundError:
    from run_project_completion_gate import discover_latest_observation_sufficiency_pack


DATA_PIPELINE_MACHINES = {"office_desktop", "highspec_desktop"}
DATA_PIPELINE_TASK = "data_pipeline"
DEFAULT_REPORTS_ROOT = Path("data/reports")
DEFAULT_PROCESSED_OUTPUT_DIR = Path("data/processed/tushare_etf_observation_continuation")


def build_observation_continuation_plan(
    *,
    observation_pack: dict[str, Any] | None,
    observation_pack_path: str | Path | None,
    profile_observation_pack_path: str | Path | None,
    machine: str | None,
    task: str | None,
    current_branch: str,
    python_executable: str,
    output_root: str | Path,
    processed_output_dir: str | Path,
) -> dict[str, Any]:
    pack = observation_pack or {}
    recommendation = _dict(pack.get("recommendation"))
    decision = _dict(pack.get("decision"))
    fills = _dict(pack.get("fills"))
    start_date = _date_text(recommendation.get("suggested_start_date"))
    end_date = _date_text(recommendation.get("suggested_end_date"))
    sufficiency_cleared = bool(decision.get("observation_sufficiency_cleared")) or pack.get("status") == "sufficient"

    blockers: list[str] = []
    if machine not in DATA_PIPELINE_MACHINES:
        blockers.append("machine_must_allow_data_pipeline")
    if task != DATA_PIPELINE_TASK:
        blockers.append("task_must_be_data_pipeline")
    if not pack:
        blockers.append("observation_sufficiency_pack_missing")
    if not profile_observation_pack_path:
        blockers.append("profile_observation_pack_missing")
    if not sufficiency_cleared and (not start_date or not end_date):
        blockers.append("observation_recommendation_dates_missing")

    if blockers:
        status = "blocked"
        commands: list[list[str]] = []
    elif sufficiency_cleared:
        status = "no_action_sufficient"
        commands = [[python_executable, "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"]]
    else:
        status = "ready"
        commands = _continuation_commands(
            machine=str(machine),
            current_branch=current_branch,
            start_date=str(start_date),
            end_date=str(end_date),
            profile_observation_pack_path=str(profile_observation_pack_path),
            python_executable=python_executable,
            output_root=Path(output_root),
            processed_output_dir=Path(processed_output_dir),
        )

    return {
        "status": status,
        "blockers": blockers,
        "selected": {
            "machine": machine,
            "task": task,
        },
        "git": {
            "current_branch": current_branch,
        },
        "observation": {
            "source_path": _path_text(observation_pack_path) if observation_pack_path else None,
            "status": pack.get("status", "missing") if pack else "missing",
            "priority": recommendation.get("priority"),
        },
        "fills": {
            "observed_fills": fills.get("observed_fills"),
            "required_fills": fills.get("required_fills"),
            "fill_deficit": fills.get("fill_deficit"),
        },
        "window": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "profile_observation_pack": _path_text(profile_observation_pack_path) if profile_observation_pack_path else None,
        "processed_output_dir": _path_text(processed_output_dir),
        "output_root": _path_text(output_root),
        "commands": commands,
        "safety": {
            "research_to_paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_reads_allowed": False,
            "order_placement_allowed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a safe paper-observation continuation plan.")
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", default=DATA_PIPELINE_TASK)
    parser.add_argument("--observation-sufficiency-pack")
    parser.add_argument("--post-refresh-replay-pack")
    parser.add_argument("--profile-observation-pack")
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--output-root")
    parser.add_argument("--processed-output-dir", default=str(DEFAULT_PROCESSED_OUTPUT_DIR))
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    observation_path = (
        Path(args.observation_sufficiency_pack)
        if args.observation_sufficiency_pack
        else discover_latest_observation_sufficiency_pack(Path(args.reports_root))
    )
    post_refresh_path = Path(args.post_refresh_replay_pack) if args.post_refresh_replay_pack else None
    profile_path = (
        Path(args.profile_observation_pack)
        if args.profile_observation_pack
        else default_profile_observation_pack_for_observation(observation_path)
        or default_profile_observation_pack_path(post_refresh_path or discover_latest_post_refresh_replay_pack(Path(args.reports_root)))
    )
    output_root = (
        Path(args.output_root)
        if args.output_root
        else DEFAULT_REPORTS_ROOT / f"round487_observation_continuation_validated_{date.today():%Y%m%d}"
    )

    plan = build_observation_continuation_plan(
        observation_pack=_read_optional_json(observation_path),
        observation_pack_path=observation_path,
        profile_observation_pack_path=profile_path if profile_path and profile_path.exists() else profile_path,
        machine=args.machine,
        task=args.task,
        current_branch=_git_stdout(["branch", "--show-current"]),
        python_executable=sys.executable,
        output_root=output_root,
        processed_output_dir=Path(args.processed_output_dir),
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    if args.require_ready and plan["status"] != "ready":
        raise SystemExit(2)


def discover_latest_post_refresh_replay_pack(root: str | Path = DEFAULT_REPORTS_ROOT) -> Path | None:
    root_path = Path(root)
    if not root_path.exists():
        return None
    candidates = [
        path
        for path in root_path.glob("**/post_refresh_replay_pack.json")
        if path.is_file() and "fixture" not in path.as_posix().lower()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def default_profile_observation_pack_path(post_refresh_pack_path: str | Path | None) -> Path | None:
    if not post_refresh_pack_path:
        return None
    pack = _read_optional_json(Path(post_refresh_pack_path))
    if not pack:
        return None
    output_dir = pack.get("profile_observation_output_dir")
    if output_dir:
        return Path(str(output_dir)) / "profile_observation_pack.json"
    return Path(post_refresh_pack_path).parent / "profile_observation" / "profile_observation_pack.json"


def default_profile_observation_pack_for_observation(observation_pack_path: str | Path | None) -> Path | None:
    if not observation_pack_path:
        return None
    observation_path = Path(observation_pack_path)
    round_dir = observation_path.parent.name
    if "observation_sufficiency" not in round_dir:
        return None
    candidate = observation_path.parent.parent / round_dir.replace("observation_sufficiency", "post_refresh_replay") / "profile_observation" / "profile_observation_pack.json"
    return candidate if candidate.exists() else None


def _continuation_commands(
    *,
    machine: str,
    current_branch: str,
    start_date: str,
    end_date: str,
    profile_observation_pack_path: str,
    python_executable: str,
    output_root: Path,
    processed_output_dir: Path,
) -> list[list[str]]:
    recent_report_dir = output_root / "recent_data_refresh"
    replay_report_dir = output_root / "post_refresh_replay"
    observation_output_dir = output_root / "observation_sufficiency"
    return [
        [
            python_executable,
            "scripts/run_quant_pm_startup_gate.py",
            "--machine",
            machine,
            "--task",
            DATA_PIPELINE_TASK,
            "--branch",
            current_branch,
        ],
        [
            python_executable,
            "scripts/run_recent_data_refresh.py",
            "--machine",
            machine,
            "--profile-observation-pack",
            _path_text(profile_observation_pack_path),
            "--start-date",
            start_date,
            "--end-date",
            end_date,
            "--output-dir",
            _path_text(processed_output_dir),
            "--report-dir",
            _path_text(recent_report_dir),
            "--execute",
        ],
        [
            python_executable,
            "scripts/run_post_refresh_replay.py",
            "--recent-data-refresh-pack",
            _path_text(recent_report_dir / "recent_data_refresh_pack.json"),
            "--report-dir",
            _path_text(replay_report_dir),
        ],
        [
            python_executable,
            "scripts/run_observation_sufficiency.py",
            "--post-refresh-replay-pack",
            _path_text(replay_report_dir / "post_refresh_replay_pack.json"),
            "--profile-observation-pack",
            _path_text(replay_report_dir / "profile_observation" / "profile_observation_pack.json"),
            "--output-dir",
            _path_text(observation_output_dir),
        ],
        [python_executable, "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"],
    ]


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    json_path = Path(path)
    if not json_path.exists():
        return None
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {json_path}")
    return data


def _path_text(path: str | Path) -> str:
    return Path(path).as_posix()


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _git_stdout(args: list[str]) -> str:
    return _git(args).stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


if __name__ == "__main__":
    main()
