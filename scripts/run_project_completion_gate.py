from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.start_task_context import DEFAULT_CONFIG, load_config
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from start_task_context import DEFAULT_CONFIG, load_config


DEFAULT_OBSERVATION_REPORTS_ROOT = Path("data/reports")
TOPIC_BRANCH_PREFIX = "origin/codex/"


def build_completion_gate(
    *,
    current_branch: str,
    stable_branch: str,
    changed_paths: list[str],
    remote_topic_branches: list[dict[str, str]],
    branch_discovery_errors: list[str],
    observation_pack: dict[str, Any] | None,
    observation_pack_path: str | Path | None = None,
    recent_data_refresh_pack: dict[str, Any] | None = None,
    recent_data_refresh_pack_path: str | Path | None = None,
) -> dict[str, Any]:
    observation = _summarize_observation(observation_pack, observation_pack_path=observation_pack_path)
    recent_data_refresh = _summarize_recent_data_refresh(
        recent_data_refresh_pack,
        recent_data_refresh_pack_path=recent_data_refresh_pack_path,
    )
    blockers: list[str] = []
    if branch_discovery_errors:
        blockers.append("branch_discovery_failed")
    if current_branch != stable_branch:
        blockers.append("not_on_stable_branch")
    if remote_topic_branches:
        blockers.append("remote_topic_branches_remaining")
    if changed_paths:
        blockers.append("working_tree_dirty")
    if not observation["pack_present"]:
        blockers.append("observation_sufficiency_pack_missing")
    elif not observation["sufficiency_cleared"]:
        blockers.append("observation_sufficiency_not_cleared")

    factor_mining_allowed = not blockers
    return {
        "stage": "project_completion_gate",
        "status": "complete" if factor_mining_allowed else "blocked",
        "progress_estimate_percent": 100 if factor_mining_allowed else 98,
        "factor_mining_allowed": factor_mining_allowed,
        "blockers": blockers,
        "git": {
            "current_branch": current_branch,
            "stable_branch": stable_branch,
            "changed_paths": changed_paths,
            "remote_topic_branches": remote_topic_branches,
            "branch_discovery_errors": branch_discovery_errors,
        },
        "observation": observation,
        "recent_data_refresh": recent_data_refresh,
        "next_actions": _next_actions(blockers, recent_data_refresh=recent_data_refresh),
        "safety": {
            "research_to_paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_reads_allowed": False,
            "order_placement_allowed": False,
        },
    }


def completion_gate_exit_code(gate: dict[str, Any], *, require_complete: bool) -> int:
    if require_complete and not bool(gate.get("factor_mining_allowed")):
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate project completion before profit-factor mining starts.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--observation-sufficiency-pack",
        help="Observation sufficiency pack to use. Defaults to the latest non-fixture pack under data/reports.",
    )
    parser.add_argument("--observation-reports-root", default=str(DEFAULT_OBSERVATION_REPORTS_ROOT))
    parser.add_argument(
        "--recent-data-refresh-pack",
        help="Recent data refresh pack to refine observation-blocker next actions. Defaults to the latest non-fixture pack.",
    )
    parser.add_argument("--skip-fetch", action="store_true", help="Do not fetch/prune before reading remote branches.")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit with code 2 when project completion conditions do not allow profit-factor mining.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if not args.skip_fetch:
        _git(["fetch", "origin", "--prune"], check=False)
    stable_branch = str(config.get("branch_policy", {}).get("stable_branch", "main"))
    observation_path = (
        Path(args.observation_sufficiency_pack)
        if args.observation_sufficiency_pack
        else discover_latest_observation_sufficiency_pack(Path(args.observation_reports_root))
    )
    recent_data_refresh_path = (
        Path(args.recent_data_refresh_pack)
        if args.recent_data_refresh_pack
        else discover_latest_recent_data_refresh_pack(Path(args.observation_reports_root))
    )
    gate = build_completion_gate(
        current_branch=_git_stdout(["branch", "--show-current"]),
        stable_branch=stable_branch,
        changed_paths=_changed_paths(),
        remote_topic_branches=_remote_topic_branches(),
        branch_discovery_errors=[],
        observation_pack=_read_optional_json(observation_path),
        observation_pack_path=observation_path,
        recent_data_refresh_pack=_read_optional_json(recent_data_refresh_path),
        recent_data_refresh_pack_path=recent_data_refresh_path,
    )
    print(json.dumps(gate, indent=2, sort_keys=True))
    raise SystemExit(completion_gate_exit_code(gate, require_complete=args.require_complete))


def discover_latest_observation_sufficiency_pack(root: str | Path = DEFAULT_OBSERVATION_REPORTS_ROOT) -> Path | None:
    root_path = Path(root)
    if not root_path.exists():
        return None
    patterns = (
        "observation_sufficiency/observation_sufficiency_pack.json",
        "round*_observation_sufficiency*/observation_sufficiency_pack.json",
        "round*/observation_sufficiency_pack.json",
        "round*/observation_sufficiency/observation_sufficiency_pack.json",
        "*/observation_sufficiency_pack.json",
        "*/observation_sufficiency/observation_sufficiency_pack.json",
    )
    candidates_by_path: dict[Path, Path] = {}
    for pattern in patterns:
        for path in root_path.glob(pattern):
            if path.is_file() and "fixture" not in path.as_posix().lower():
                candidates_by_path[path.resolve()] = path
    candidates = list(candidates_by_path.values())
    if not candidates:
        return None
    return max(candidates, key=_observation_pack_rank)


def discover_latest_recent_data_refresh_pack(root: str | Path = DEFAULT_OBSERVATION_REPORTS_ROOT) -> Path | None:
    root_path = Path(root)
    if not root_path.exists():
        return None
    patterns = (
        "recent_data_refresh/recent_data_refresh_pack.json",
        "round*_recent_data_refresh*/recent_data_refresh_pack.json",
        "round*/recent_data_refresh/recent_data_refresh_pack.json",
        "*/recent_data_refresh_pack.json",
        "*/recent_data_refresh/recent_data_refresh_pack.json",
    )
    candidates_by_path: dict[Path, Path] = {}
    for pattern in patterns:
        for path in root_path.glob(pattern):
            if path.is_file() and "fixture" not in path.as_posix().lower():
                candidates_by_path[path.resolve()] = path
    candidates = list(candidates_by_path.values())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _observation_pack_rank(path: Path) -> tuple[int, int, int, float]:
    pack = _read_optional_json(path)
    decision = pack.get("decision") if isinstance(pack, dict) and isinstance(pack.get("decision"), dict) else {}
    fills = pack.get("fills") if isinstance(pack, dict) and isinstance(pack.get("fills"), dict) else {}
    sufficient = bool(decision.get("observation_sufficiency_cleared")) or (isinstance(pack, dict) and pack.get("status") == "sufficient")
    provenance = _observation_pack_provenance_score(path)
    observed = _int(fills.get("observed_fills"), 0)
    return (provenance, 1 if sufficient else 0, observed, path.stat().st_mtime)


def _observation_pack_provenance_score(path: Path) -> int:
    text = path.as_posix().lower()
    return 1 if "validated" in text or "fund_basic" in text else 0


def _summarize_observation(
    pack: dict[str, Any] | None,
    *,
    observation_pack_path: str | Path | None = None,
) -> dict[str, Any]:
    source_path = str(observation_pack_path) if observation_pack_path else None
    if not pack:
        return {
            "pack_present": False,
            "source_path": source_path,
            "status": "missing",
            "sufficiency_cleared": False,
            "observed_fills": None,
            "required_fills": None,
            "fill_deficit": None,
        }
    decision = pack.get("decision") if isinstance(pack.get("decision"), dict) else {}
    fills = pack.get("fills") if isinstance(pack.get("fills"), dict) else {}
    status = str(pack.get("status", "unknown"))
    sufficiency_cleared = bool(decision.get("observation_sufficiency_cleared")) or status == "sufficient"
    return {
        "pack_present": True,
        "source_path": source_path,
        "status": status,
        "sufficiency_cleared": sufficiency_cleared,
        "observed_fills": fills.get("observed_fills"),
        "required_fills": fills.get("required_fills"),
        "fill_deficit": fills.get("fill_deficit"),
    }


def _summarize_recent_data_refresh(
    pack: dict[str, Any] | None,
    *,
    recent_data_refresh_pack_path: str | Path | None = None,
) -> dict[str, Any]:
    source_path = str(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else None
    if not pack:
        return {
            "pack_present": False,
            "source_path": source_path,
            "status": "missing",
            "target_end_gap": None,
        }
    return {
        "pack_present": True,
        "source_path": source_path,
        "status": str(pack.get("status", "unknown")),
        "target_end_gap": _recent_target_end_gap(pack, source_path=source_path),
    }


def _recent_target_end_gap(pack: dict[str, Any], *, source_path: str | None) -> dict[str, Any] | None:
    coverage = pack.get("coverage") if isinstance(pack.get("coverage"), dict) else {}
    if coverage.get("target_end_covered") is not False:
        return None
    target = pack.get("target_window") if isinstance(pack.get("target_window"), dict) else {}
    target_start = _date_text(target.get("start_date"))
    target_end = _date_text(target.get("end_date"))
    if not target_start or not target_end:
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
        if not clean_end or clean_end >= target_end or clean_end < target_start:
            continue
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            asset_ids.append(asset_id)
        clean_end_dates.append(clean_end)
    if not asset_ids or not clean_end_dates:
        return None
    return {
        "source_path": source_path,
        "target_start_date": target_start,
        "target_end_date": target_end,
        "latest_clean_end_date": min(clean_end_dates),
        "required_asset_ids": sorted(dict.fromkeys(asset_ids)),
    }


def _next_actions(blockers: list[str], *, recent_data_refresh: dict[str, Any] | None = None) -> list[dict[str, str]]:
    if not blockers:
        return [
            {
                "action": "start_profit_factor_mining",
                "command": "python scripts/run_factor_mining_startup_gate.py && python scripts/run_checks.py --profile laptop-integration --execute",
                "reason": "main integration, branch cleanup, and observation sufficiency are clear",
            }
        ]
    actions: list[dict[str, str]] = []
    if "not_on_stable_branch" in blockers or "remote_topic_branches_remaining" in blockers:
        actions.append(
            {
                "action": "run_laptop_project_sync",
                "command": "python scripts/run_checks.py --profile laptop-integration --execute",
                "reason": "merge topic branches into main, verify merged main, push main, then clean topic branches",
            }
        )
    if "observation_sufficiency_not_cleared" in blockers or "observation_sufficiency_pack_missing" in blockers:
        target_end_gap = _dict((recent_data_refresh or {}).get("target_end_gap"))
        if target_end_gap:
            source_path = str(target_end_gap.get("source_path") or "<recent-data-refresh-pack>")
            asset_text = ", ".join(str(item) for item in target_end_gap.get("required_asset_ids", []))
            actions.append(
                {
                    "action": "wait_for_required_asset_target_end",
                    "command": (
                        "python scripts/run_required_asset_target_end_check.py "
                        f"--machine <data_pipeline_machine> --task data_pipeline --recent-data-refresh-pack {source_path} --execute"
                    ),
                    "reason": (
                        f"paper observation waits for {asset_text} to cover target end "
                        f"{target_end_gap.get('target_end_date')}; latest clean end is "
                        f"{target_end_gap.get('latest_clean_end_date')}"
                    ),
                }
            )
        else:
            actions.append(
                {
                    "action": "continue_paper_observation",
                    "command": "python scripts/run_observation_sufficiency.py",
                    "reason": "paper observation must clear the fill-count gate before profit-factor mining starts",
                }
            )
    if "working_tree_dirty" in blockers:
        actions.append(
            {
                "action": "sync_or_clean_worktree",
                "command": "python scripts/sync_project.py --machine <machine> --task <task>",
                "reason": "completion gate requires a clean worktree",
            }
        )
    if "branch_discovery_failed" in blockers:
        actions.append(
            {
                "action": "repair_branch_discovery",
                "command": "git fetch origin --prune",
                "reason": "remote branch state must be trustworthy before completion can be claimed",
            }
        )
    return actions


def _remote_topic_branches() -> list[dict[str, str]]:
    result = _git(
        ["for-each-ref", "--format=%(refname:short)|%(objectname)", "refs/remotes/origin/codex"],
        check=False,
    )
    if result.returncode != 0:
        return []
    branches: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        name, commit = line.split("|", 1)
        name = name.strip()
        if name.startswith(TOPIC_BRANCH_PREFIX):
            branches.append({"name": name, "commit": commit.strip()})
    return sorted(branches, key=lambda item: item["name"])


def _changed_paths() -> list[str]:
    status = _git(["status", "--porcelain"], check=False).stdout
    paths: list[str] = []
    for line in status.splitlines():
        if line:
            paths.append(line[3:].strip())
    return paths


def _read_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        from datetime import date

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
