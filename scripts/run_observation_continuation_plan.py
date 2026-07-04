from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
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
    recent_data_refresh_pack: dict[str, Any] | None = None,
    recent_data_refresh_pack_path: str | Path | None = None,
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
    gap_recovery = build_gap_recovery_plan(
        recent_data_refresh_pack,
        recent_data_refresh_pack_path=recent_data_refresh_pack_path,
        machine=str(machine) if machine else None,
        current_branch=current_branch,
        profile_observation_pack_path=str(profile_observation_pack_path) if profile_observation_pack_path else None,
        python_executable=python_executable,
        output_root=Path(output_root),
        processed_output_dir=Path(processed_output_dir),
    )

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
        "gap_recovery": gap_recovery,
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
    parser.add_argument("--recent-data-refresh-pack")
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
    recent_refresh_path = Path(args.recent_data_refresh_pack) if args.recent_data_refresh_pack else None
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
        recent_data_refresh_pack=_read_optional_json(recent_refresh_path),
        recent_data_refresh_pack_path=recent_refresh_path,
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


def build_gap_recovery_plan(
    recent_data_refresh_pack: dict[str, Any] | None,
    *,
    recent_data_refresh_pack_path: str | Path | None = None,
    machine: str | None = None,
    current_branch: str | None = None,
    profile_observation_pack_path: str | None = None,
    python_executable: str | None = None,
    output_root: str | Path | None = None,
    processed_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    pack = recent_data_refresh_pack or {}
    missing_dates = _missing_required_trade_dates(pack)
    if not missing_dates:
        target_end_gap = _target_end_gap_recovery(pack)
        if target_end_gap:
            windows = [target_end_gap["window"]]
            return {
                "status": "target_end_gap_available",
                "source_path": _path_text(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else None,
                "missing_trade_dates": [],
                "windows": windows,
                "command_sets": _gap_recovery_command_sets(
                    windows,
                    machine=machine,
                    current_branch=current_branch,
                    profile_observation_pack_path=profile_observation_pack_path,
                    python_executable=python_executable,
                    output_root=Path(output_root) if output_root is not None else None,
                    processed_output_dir=Path(processed_output_dir) if processed_output_dir is not None else None,
                ),
                "next_actions": [target_end_gap["next_action"]],
            }
        return {
            "status": "not_applicable",
            "source_path": _path_text(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else None,
            "missing_trade_dates": [],
            "windows": [],
            "command_sets": [],
            "next_actions": [],
        }

    target = _dict(pack.get("target_window"))
    start_date = _date_text(target.get("start_date"))
    end_date = _date_text(target.get("end_date"))
    trade_dates = _expected_trade_dates(pack)
    windows: list[dict[str, str]] = []
    for missing_date in missing_dates:
        before_end = _previous_trade_date(trade_dates, missing_date)
        after_start = _next_trade_date(trade_dates, missing_date)
        if start_date and before_end and start_date <= before_end:
            windows.append(
                {
                    "label": "before_missing_trade_date",
                    "start_date": start_date,
                    "end_date": before_end,
                }
            )
        if end_date and after_start and after_start <= end_date:
            windows.append(
                {
                    "label": "after_missing_trade_date",
                    "start_date": after_start,
                    "end_date": end_date,
                }
            )

    unique_windows = _unique_windows(windows)
    return {
        "status": "gap_recovery_available" if windows else "blocked_no_recovery_window",
        "source_path": _path_text(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else None,
        "missing_trade_dates": missing_dates,
        "windows": unique_windows,
        "command_sets": _gap_recovery_command_sets(
            unique_windows,
            machine=machine,
            current_branch=current_branch,
            profile_observation_pack_path=profile_observation_pack_path,
            python_executable=python_executable,
            output_root=Path(output_root) if output_root is not None else None,
            processed_output_dir=Path(processed_output_dir) if processed_output_dir is not None else None,
        ),
        "next_actions": [],
    }


def _missing_required_trade_dates(pack: dict[str, Any]) -> list[str]:
    coverage = _dict(pack.get("coverage"))
    rows = coverage.get("required_asset_missing_trade_dates", [])
    if not isinstance(rows, list):
        return []
    dates: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = row.get("missing_trade_dates", [])
        if not isinstance(values, list):
            continue
        for value in values:
            parsed = _date_text(value)
            if parsed and parsed not in seen:
                dates.append(parsed)
                seen.add(parsed)
    return sorted(dates)


def _expected_trade_dates(pack: dict[str, Any]) -> list[str]:
    ingest = _dict(pack.get("ingest"))
    dates: list[str] = []
    seen: set[str] = set()
    for key in ("downloaded_trade_dates", "skipped_trade_dates"):
        values = ingest.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            parsed = _trade_date_text(value)
            if parsed and parsed not in seen:
                dates.append(parsed)
                seen.add(parsed)
    return sorted(dates)


def _target_end_gap_recovery(pack: dict[str, Any]) -> dict[str, Any] | None:
    coverage = _dict(pack.get("coverage"))
    if coverage.get("target_end_covered") is not False:
        return None

    target = _dict(pack.get("target_window"))
    start_date = _date_text(target.get("start_date"))
    target_end = _date_text(target.get("end_date"))
    if not start_date or not target_end:
        return None

    rows = coverage.get("required_asset_coverage", [])
    if not isinstance(rows, list):
        return None

    asset_ids: list[str] = []
    clean_end_dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("target_start_covered") is False or row.get("target_end_covered") is not False:
            continue
        clean_end = _date_text(row.get("end_date"))
        if not clean_end or clean_end >= target_end or clean_end < start_date:
            continue
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            asset_ids.append(asset_id)
        clean_end_dates.append(clean_end)

    if not asset_ids or not clean_end_dates:
        return None

    required_asset_ids = sorted(dict.fromkeys(asset_ids))
    latest_clean_end = min(clean_end_dates)
    asset_text = ", ".join(required_asset_ids)
    return {
        "window": {
            "label": "latest_required_asset_clean_window",
            "start_date": start_date,
            "end_date": latest_clean_end,
            "target_end_date": target_end,
            "required_asset_ids": required_asset_ids,
        },
        "next_action": {
            "action": "wait_for_required_asset_target_end",
            "reason": (
                "Required assets stop before the requested target end; "
                f"wait for {asset_text} to cover {target_end} or rerun only "
                f"through the latest clean end {latest_clean_end}."
            ),
        },
    }


def _previous_trade_date(trade_dates: list[str], missing_date: str) -> str | None:
    for value in reversed(trade_dates):
        if value < missing_date:
            return value
    try:
        return (date.fromisoformat(missing_date) - timedelta(days=1)).isoformat()
    except ValueError:
        return None


def _next_trade_date(trade_dates: list[str], missing_date: str) -> str | None:
    for value in trade_dates:
        if value > missing_date:
            return value
    try:
        return (date.fromisoformat(missing_date) + timedelta(days=1)).isoformat()
    except ValueError:
        return None


def _unique_windows(windows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for window in windows:
        key = (window["label"], window["start_date"], window["end_date"])
        if key not in seen:
            unique.append(window)
            seen.add(key)
    return unique


def _gap_recovery_command_sets(
    windows: list[dict[str, str]],
    *,
    machine: str | None,
    current_branch: str | None,
    profile_observation_pack_path: str | None,
    python_executable: str | None,
    output_root: Path | None,
    processed_output_dir: Path | None,
) -> list[dict[str, Any]]:
    if not (
        machine
        and current_branch
        and profile_observation_pack_path
        and python_executable
        and output_root
        and processed_output_dir
    ):
        return []
    command_sets: list[dict[str, Any]] = []
    for window in windows:
        label = window["label"]
        command_sets.append(
            {
                "label": label,
                "start_date": window["start_date"],
                "end_date": window["end_date"],
                "commands": _continuation_commands(
                    machine=machine,
                    current_branch=current_branch,
                    start_date=window["start_date"],
                    end_date=window["end_date"],
                    profile_observation_pack_path=profile_observation_pack_path,
                    python_executable=python_executable,
                    output_root=output_root / label,
                    processed_output_dir=processed_output_dir / label,
                ),
            }
        )
    return command_sets


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


def _trade_date_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return _date_text(text)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _git_stdout(args: list[str]) -> str:
    return _git(args).stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


if __name__ == "__main__":
    main()
