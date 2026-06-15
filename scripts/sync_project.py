from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.start_task_context import DEFAULT_CONFIG, load_config
except ModuleNotFoundError:
    from start_task_context import DEFAULT_CONFIG, load_config


DEFAULT_COMMIT_MESSAGE = "Sync project updates"


def classify_changed_paths(paths: list[str], config: dict[str, Any]) -> dict[str, list[str]]:
    syncable: list[str] = []
    blocked: list[str] = []
    ignored: list[str] = []
    for raw_path in paths:
        path = _normalize_path(raw_path)
        if not path:
            continue
        if is_forbidden_path(path, config):
            blocked.append(path)
        elif is_allowed_path(path, config):
            syncable.append(path)
        else:
            ignored.append(path)
    return {
        "syncable": syncable,
        "blocked": blocked,
        "ignored": ignored,
    }


def is_forbidden_path(path: str, config: dict[str, Any]) -> bool:
    normalized = _normalize_path(path)
    if normalized == ".env.example":
        return False
    forbidden = list(_sync_policy(config).get("forbidden_paths", []))
    forbidden.extend(_data_policy(config).get("ignored_paths", []))
    for pattern in forbidden:
        if _matches(normalized, str(pattern)):
            return True
    return False


def is_allowed_path(path: str, config: dict[str, Any]) -> bool:
    normalized = _normalize_path(path)
    for pattern in _sync_policy(config).get("allowed_paths", []):
        if _matches(normalized, str(pattern)):
            return True
    return False


def build_sync_plan(
    config: dict[str, Any],
    *,
    current_branch: str,
    changed_paths: list[str],
    machine: str | None,
    task: str | None,
    execute: bool,
    push: bool,
    upstream_sync: str,
) -> dict[str, Any]:
    classification = classify_changed_paths(changed_paths, config)
    blockers = _sync_blockers(
        config=config,
        current_branch=current_branch,
        classification=classification,
        machine=machine,
        task=task,
        execute=execute,
        push=push,
        upstream_sync=upstream_sync,
    )
    return {
        "mode": "execute" if execute else "audit",
        "can_execute": execute and not blockers,
        "can_push": execute and push and not blockers,
        "selected": {
            "machine": machine,
            "task": task,
        },
        "git": {
            "current_branch": current_branch,
            "upstream_sync": upstream_sync,
        },
        "path_classification": classification,
        "blockers": blockers,
        "actions": _recommended_actions(classification, blockers, execute, push),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely sync project code/config/docs to GitHub.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--machine")
    parser.add_argument("--task")
    parser.add_argument("--message", default=DEFAULT_COMMIT_MESSAGE)
    parser.add_argument("--execute", action="store_true", help="Stage and commit syncable files if safe.")
    parser.add_argument("--push", action="store_true", help="Push after commit when safe. Requires --execute.")
    parser.add_argument("--skip-fetch", action="store_true", help="Do not fetch/prune before building the plan.")
    args = parser.parse_args()

    if args.push and not args.execute:
        raise SystemExit("--push requires --execute")

    config = load_config(args.config)
    if not args.skip_fetch:
        _git(["fetch", "origin", "--prune"], check=False)

    current_branch = _git_stdout(["branch", "--show-current"])
    changed_paths = _changed_paths()
    upstream_sync = _upstream_sync()
    plan = build_sync_plan(
        config,
        current_branch=current_branch,
        changed_paths=changed_paths,
        machine=args.machine,
        task=args.task,
        execute=args.execute,
        push=args.push,
        upstream_sync=upstream_sync,
    )

    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    if plan["blockers"]:
        print(json.dumps(plan, indent=2, sort_keys=True))
        raise SystemExit(2)

    syncable = plan["path_classification"]["syncable"]
    if not syncable:
        plan["actions"].append("nothing_to_commit")
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    _git(["add", "--", *syncable])
    _git(["diff", "--cached", "--check"])
    staged = _git_stdout(["diff", "--cached", "--name-only"]).splitlines()
    if not staged:
        plan["actions"].append("nothing_staged")
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    _git(["commit", "-m", args.message])
    plan["actions"].append("committed")

    if args.push:
        _git(["push", "origin", current_branch])
        plan["actions"].append("pushed")
        plan["git"]["upstream_sync_after_push"] = _upstream_sync()

    print(json.dumps(plan, indent=2, sort_keys=True))


def _sync_blockers(
    *,
    config: dict[str, Any],
    current_branch: str,
    classification: dict[str, list[str]],
    machine: str | None,
    task: str | None,
    execute: bool,
    push: bool,
    upstream_sync: str,
) -> list[str]:
    blockers: list[str] = []
    if not execute:
        return blockers
    if not machine:
        blockers.append("machine_not_confirmed")
    if not task:
        blockers.append("task_not_confirmed")
    if classification["blocked"]:
        blockers.append("forbidden_paths_present")
    stable_branch = str(_branch_policy(config).get("stable_branch", "main"))
    if current_branch == stable_branch and task != "project_sync":
        blockers.append("main_requires_project_sync_or_manual_confirmation")
    if push and _behind_upstream(upstream_sync):
        blockers.append("branch_behind_upstream_pull_or_rebase_first")
    return blockers


def _recommended_actions(
    classification: dict[str, list[str]],
    blockers: list[str],
    execute: bool,
    push: bool,
) -> list[str]:
    if blockers:
        return ["stop_and_ask_user"]
    if not execute:
        return ["audit_only", "rerun_with_execute_when_ready"]
    actions = ["stage_syncable_files", "commit"]
    if push:
        actions.append("push")
    if classification["ignored"]:
        actions.append("leave_ignored_paths_unstaged")
    return actions


def _changed_paths() -> list[str]:
    status = _git(["status", "--porcelain"]).stdout
    paths: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            old_path, new_path = path.split(" -> ", 1)
            paths.extend([old_path.strip(), new_path.strip()])
        else:
            paths.append(path)
    return paths


def _matches(path: str, pattern: str) -> bool:
    normalized_pattern = _normalize_path(pattern)
    if normalized_pattern.endswith("/"):
        return path == normalized_pattern[:-1] or path.startswith(normalized_pattern)
    return path == normalized_pattern or fnmatch.fnmatch(path, normalized_pattern)


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().strip('"')


def _behind_upstream(upstream_sync: str) -> bool:
    parts = upstream_sync.replace("\t", " ").split()
    if len(parts) < 2:
        return False
    try:
        return int(parts[0]) > 0
    except ValueError:
        return False


def _git_stdout(args: list[str]) -> str:
    result = _git(args)
    return result.stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def _upstream_sync() -> str:
    result = _git(["rev-list", "--left-right", "--count", "@{upstream}...HEAD"], check=False)
    if result.returncode != 0:
        return "no upstream"
    return result.stdout.strip()


def _branch_policy(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("branch_policy")
    return value if isinstance(value, dict) else {}


def _data_policy(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("data_policy")
    return value if isinstance(value, dict) else {}


def _sync_policy(config: dict[str, Any]) -> dict[str, Any]:
    value = config.get("sync_policy")
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
