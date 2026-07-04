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


DEFAULT_OBSERVATION_SUFFICIENCY_PACK = Path(
    "data/reports/round478_observation_sufficiency_validated_latest_20260704/observation_sufficiency_pack.json"
)
TOPIC_BRANCH_PREFIX = "origin/codex/"


def build_completion_gate(
    *,
    current_branch: str,
    stable_branch: str,
    changed_paths: list[str],
    remote_topic_branches: list[dict[str, str]],
    branch_discovery_errors: list[str],
    observation_pack: dict[str, Any] | None,
) -> dict[str, Any]:
    observation = _summarize_observation(observation_pack)
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
        "next_actions": _next_actions(blockers),
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
    parser.add_argument("--observation-sufficiency-pack", default=str(DEFAULT_OBSERVATION_SUFFICIENCY_PACK))
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
    gate = build_completion_gate(
        current_branch=_git_stdout(["branch", "--show-current"]),
        stable_branch=stable_branch,
        changed_paths=_changed_paths(),
        remote_topic_branches=_remote_topic_branches(),
        branch_discovery_errors=[],
        observation_pack=_read_optional_json(Path(args.observation_sufficiency_pack)),
    )
    print(json.dumps(gate, indent=2, sort_keys=True))
    raise SystemExit(completion_gate_exit_code(gate, require_complete=args.require_complete))


def _summarize_observation(pack: dict[str, Any] | None) -> dict[str, Any]:
    if not pack:
        return {
            "pack_present": False,
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
        "status": status,
        "sufficiency_cleared": sufficiency_cleared,
        "observed_fills": fills.get("observed_fills"),
        "required_fills": fills.get("required_fills"),
        "fill_deficit": fills.get("fill_deficit"),
    }


def _next_actions(blockers: list[str]) -> list[dict[str, str]]:
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


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _git_stdout(args: list[str]) -> str:
    return _git(args).stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


if __name__ == "__main__":
    main()
