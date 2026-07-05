from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.start_task_context import DEFAULT_CONFIG, load_config
    from scripts.sync_project import DEFAULT_INTEGRATION_MANIFEST, load_integration_manifest
except ModuleNotFoundError:
    from start_task_context import DEFAULT_CONFIG, load_config
    from sync_project import DEFAULT_INTEGRATION_MANIFEST, load_integration_manifest


TOPIC_BRANCH_PREFIX = "origin/codex/"
STABLE_BRANCH = "main"


def build_laptop_topic_integration_plan(
    *,
    machine: str | None,
    task: str | None,
    current_branch: str,
    worktree_clean: bool,
    main_upstream_sync: str,
    remote_topic_branches: list[dict[str, str]],
    stable_commits: set[str],
    manifest: dict[str, Any],
    is_ancestor: Callable[[str, str], bool],
    python_executable: str,
    branch_discovery_errors: list[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if machine != "laptop":
        blockers.append("machine_must_be_laptop")
    if task != "project_sync":
        blockers.append("task_must_be_project_sync")
    if current_branch != STABLE_BRANCH:
        blockers.append("current_branch_must_be_main")
    if not worktree_clean:
        blockers.append("working_tree_dirty")
    if _behind_upstream(main_upstream_sync):
        blockers.append("main_behind_origin_pull_first")
    if branch_discovery_errors:
        blockers.append("branch_discovery_failed")

    candidates, skipped = _select_merge_candidates(
        remote_topic_branches=remote_topic_branches,
        stable_commits=stable_commits,
        manifest=manifest,
    )
    merge_order = order_topic_branches_for_merge(candidates, is_ancestor=is_ancestor)
    status = "blocked" if blockers else "ready" if merge_order else "no_topic_branches"

    return {
        "status": status,
        "blockers": blockers,
        "handoff": _handoff_status(
            status=status,
            blockers=blockers,
            merge_order=merge_order,
            machine=machine,
            task=task,
            current_branch=current_branch,
        ),
        "selected": {
            "machine": machine,
            "task": task,
        },
        "git": {
            "current_branch": current_branch,
            "stable_branch": STABLE_BRANCH,
            "main_upstream_sync": main_upstream_sync,
        },
        "branch_discovery": {
            "errors": branch_discovery_errors or [],
        },
        "merge_order": merge_order,
        "skipped": skipped,
        "commands": _finish_commands(merge_order, python_executable=python_executable),
    }


def _handoff_status(
    *,
    status: str,
    blockers: list[str],
    merge_order: list[dict[str, str]],
    machine: str | None,
    task: str | None,
    current_branch: str,
) -> dict[str, Any]:
    if status == "blocked" and blockers == ["current_branch_must_be_main"] and merge_order:
        handoff_status = "ready_on_main"
        status_description = "handoff-ready only; rerun from laptop on main before executing"
    else:
        handoff_status = status
        status_description = status
    next_command = (
        "python scripts/run_laptop_topic_integration_plan.py "
        "--machine laptop --task project_sync --execute"
    )
    here_command = (
        "python scripts/run_laptop_topic_integration_plan.py "
        "--machine laptop --task project_sync --require-handoff-ready"
    )
    if status == "ready":
        recommended_command = next_command
        recommended_command_action = "execute_integration"
    elif handoff_status == "ready_on_main":
        recommended_command = here_command
        recommended_command_action = "check_handoff_ready"
    else:
        recommended_command = None
        recommended_command_action = "resolve_blockers"
    context_mismatch_reasons: list[str] = []
    if machine != "laptop":
        context_mismatch_reasons.append("machine_must_be_laptop")
    if task != "project_sync":
        context_mismatch_reasons.append("task_must_be_project_sync")
    if current_branch != STABLE_BRANCH:
        context_mismatch_reasons.append("current_branch_must_be_main")
    return {
        "status": handoff_status,
        "status_description": status_description,
        "ready_for_handoff": handoff_status in {"ready", "ready_on_main"},
        "blockers": list(blockers),
        "blocker_count": len(blockers),
        "executable_here": status == "ready",
        "current_machine": machine,
        "current_task": task,
        "current_branch": current_branch,
        "current_context_matches_required": (
            machine == "laptop" and task == "project_sync" and current_branch == STABLE_BRANCH
        ),
        "current_context_mismatch_reasons": context_mismatch_reasons,
        "required_machine": "laptop",
        "required_task": "project_sync",
        "required_branch": STABLE_BRANCH,
        "rerun_plan_before_execute": True,
        "merge_order_count": len(merge_order),
        "next_command": next_command,
        "next_command_context": "laptop main only",
        "next_command_allowed_here": status == "ready",
        "here_command": here_command,
        "recommended_command": recommended_command,
        "recommended_command_action": recommended_command_action,
    }


def execute_laptop_topic_integration_plan(
    plan: dict[str, Any],
    *,
    command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    commands = plan.get("commands", [])
    if plan.get("status") != "ready":
        return {
            "status": "blocked",
            "blockers": plan.get("blockers", []),
            "commands": [],
            "failed_command": None,
        }
    if not isinstance(commands, list):
        return {
            "status": "blocked",
            "blockers": ["commands_missing"],
            "commands": [],
            "failed_command": None,
        }

    records: list[dict[str, Any]] = []
    for command in commands:
        if not isinstance(command, list):
            failed = {"command": command, "returncode": None, "expected_returncodes": []}
            return {"status": "failed", "blockers": [], "commands": records, "failed_command": failed}
        expected = _expected_returncodes(command)
        result = command_runner([str(part) for part in command])
        record = {
            "command": command,
            "returncode": int(result.returncode),
            "expected_returncodes": sorted(expected),
        }
        records.append(record)
        if int(result.returncode) not in expected:
            return {"status": "failed", "blockers": [], "commands": records, "failed_command": record}

    return {"status": "executed", "blockers": [], "commands": records, "failed_command": None}


def plan_handoff_ready(plan: dict[str, Any]) -> bool:
    handoff = plan.get("handoff", {})
    if isinstance(handoff, dict) and isinstance(handoff.get("ready_for_handoff"), bool):
        return bool(handoff["ready_for_handoff"])
    if isinstance(handoff, dict) and handoff.get("status") == "ready_on_main":
        return True
    return plan.get("status") == "ready"


def order_topic_branches_for_merge(
    branches: list[dict[str, str]],
    *,
    is_ancestor: Callable[[str, str], bool],
) -> list[dict[str, str]]:
    remaining = sorted(_dedupe_branches(branches), key=lambda item: item["branch"])
    ordered: list[dict[str, str]] = []
    while remaining:
        ready = [
            branch
            for branch in remaining
            if not any(
                other["commit"] != branch["commit"] and is_ancestor(other["commit"], branch["commit"])
                for other in remaining
            )
        ]
        chosen = ready[0] if ready else remaining[0]
        ordered.append(chosen)
        remaining = [branch for branch in remaining if branch != chosen]
    return ordered


def _select_merge_candidates(
    *,
    remote_topic_branches: list[dict[str, str]],
    stable_commits: set[str],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    absorbed = _manifest_keys(manifest, "absorbed_branches")
    ignored = _manifest_keys(manifest, "ignored_branches")
    candidates: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for raw_branch in remote_topic_branches:
        branch = str(raw_branch.get("name") or raw_branch.get("branch") or "")
        commit = str(raw_branch.get("commit") or "")
        if not branch.startswith(TOPIC_BRANCH_PREFIX) or not commit:
            continue
        key = (branch, commit)
        if key in absorbed:
            skipped.append({"branch": branch, "commit": commit, "reason": "absorbed_by_manifest"})
        elif key in ignored:
            skipped.append({"branch": branch, "commit": commit, "reason": "ignored_by_manifest"})
        elif commit in stable_commits:
            skipped.append({"branch": branch, "commit": commit, "reason": "already_in_stable"})
        else:
            candidates.append({"branch": branch, "commit": commit})
    return (
        sorted(candidates, key=lambda item: item["branch"]),
        sorted(skipped, key=lambda item: item["branch"]),
    )


def _finish_commands(merge_order: list[dict[str, str]], *, python_executable: str) -> list[list[str]]:
    commands: list[list[str]] = [
        ["git", "fetch", "origin", "--prune"],
        ["git", "checkout", STABLE_BRANCH],
        ["git", "pull", "--ff-only", "origin", STABLE_BRANCH],
    ]
    for branch in merge_order:
        branch_name = branch["branch"]
        commands.append(
            [
                "git",
                "merge",
                "--no-ff",
                "-m",
                f"Merge {branch_name} for project sync",
                branch_name,
            ]
        )
    commands.extend(
        [
            [python_executable, "scripts/run_checks.py", "--profile", "laptop-integration", "--execute"],
            ["git", "push", "origin", STABLE_BRANCH],
            [
                python_executable,
                "scripts/sync_project.py",
                "--machine",
                "laptop",
                "--task",
                "project_sync",
                "--execute",
                "--cleanup-topic-branches",
            ],
            [python_executable, "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"],
        ]
    )
    return commands


def _expected_returncodes(command: list[str]) -> set[int]:
    if "scripts/run_checks.py" in command and "--profile" in command and "pre-alpha" in command:
        return {0, 2}
    return {0}


def _dedupe_branches(branches: list[dict[str, str]]) -> list[dict[str, str]]:
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for branch in branches:
        name = str(branch.get("branch") or branch.get("name") or "")
        commit = str(branch.get("commit") or "")
        if name and commit:
            by_key[(name, commit)] = {"branch": name, "commit": commit}
    return list(by_key.values())


def _manifest_keys(manifest: dict[str, Any], key: str) -> set[tuple[str, str]]:
    records = manifest.get(key, [])
    if not isinstance(records, list):
        return set()
    keys: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        branch = str(record.get("branch") or "")
        commit = str(record.get("commit") or "")
        status = str(record.get("status") or "")
        if branch and commit and status in {"absorbed", "ignored"}:
            keys.add((branch, commit))
    return keys


def _behind_upstream(upstream_sync: str) -> bool:
    parts = upstream_sync.replace("\t", " ").split()
    if len(parts) < 2:
        return False
    try:
        return int(parts[0]) > 0
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a laptop-owned topic-branch integration plan.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--integration-manifest", default=str(DEFAULT_INTEGRATION_MANIFEST))
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--skip-fetch", action="store_true", help="Do not refresh remote refs before planning.")
    parser.add_argument("--require-ready", action="store_true", help="Exit 2 unless the plan is ready.")
    parser.add_argument(
        "--require-handoff-ready",
        action="store_true",
        help="Exit 2 unless the plan is ready to execute on main or ready to hand off from a clean topic branch.",
    )
    parser.add_argument("--execute", action="store_true", help="Execute the ready laptop integration command sequence.")
    args = parser.parse_args()

    if not args.skip_fetch:
        _git(["fetch", "origin", "--prune"], check=False)

    config = load_config(args.config)
    stable_branch = str(config.get("branch_policy", {}).get("stable_branch", STABLE_BRANCH))
    if stable_branch != STABLE_BRANCH:
        raise SystemExit(f"unsupported stable branch for this plan: {stable_branch}")

    discovery = _remote_topic_branch_discovery()
    branch_discovery_errors = [discovery["error"]] if discovery.get("error") else []
    remote_topic_branches = discovery["branches"]
    stable_commits = _stable_commits(remote_topic_branches, f"origin/{STABLE_BRANCH}")
    manifest = load_integration_manifest(Path(args.integration_manifest))
    plan = build_laptop_topic_integration_plan(
        machine=args.machine,
        task=args.task,
        current_branch=_git_stdout(["branch", "--show-current"]),
        worktree_clean=_worktree_clean(),
        main_upstream_sync=_main_upstream_sync(),
        remote_topic_branches=remote_topic_branches,
        stable_commits=stable_commits,
        manifest=manifest,
        is_ancestor=_is_ancestor,
        python_executable=sys.executable,
        branch_discovery_errors=branch_discovery_errors,
    )
    output: dict[str, Any] = plan
    if args.execute:
        execution = execute_laptop_topic_integration_plan(
            plan,
            command_runner=lambda command: subprocess.run(command, capture_output=True, text=True),
        )
        output = {**plan, "execution": execution}
    print(json.dumps(output, indent=2, sort_keys=True))
    if args.execute and output.get("execution", {}).get("status") == "failed":
        failed_returncode = output["execution"].get("failed_command", {}).get("returncode")
        raise SystemExit(failed_returncode or 1)
    if args.execute and output.get("execution", {}).get("status") == "blocked":
        raise SystemExit(2)
    if args.require_ready and plan["status"] != "ready":
        raise SystemExit(2)
    if args.require_handoff_ready and not plan_handoff_ready(plan):
        raise SystemExit(2)


def _remote_topic_branch_discovery() -> dict[str, Any]:
    result = _git(
        ["for-each-ref", "--format=%(refname:short)|%(objectname)", "refs/remotes/origin/codex"],
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"git returned {result.returncode}"
        return {"branches": [], "error": f"remote_topic_branches: {detail}"}
    branches: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        name, commit = line.split("|", 1)
        if name.startswith(TOPIC_BRANCH_PREFIX):
            branches.append({"name": name.strip(), "commit": commit.strip()})
    return {"branches": branches, "error": None}


def _stable_commits(remote_topic_branches: list[dict[str, str]], stable_ref: str) -> set[str]:
    commits: set[str] = set()
    for branch in remote_topic_branches:
        commit = str(branch.get("commit") or "")
        if commit and _is_ancestor(commit, stable_ref):
            commits.add(commit)
    return commits


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    return _git(["merge-base", "--is-ancestor", ancestor, descendant], check=False).returncode == 0


def _main_upstream_sync() -> str:
    result = _git(["rev-list", "--left-right", "--count", f"origin/{STABLE_BRANCH}...{STABLE_BRANCH}"], check=False)
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def _worktree_clean() -> bool:
    return _git_stdout(["status", "--porcelain"]) == ""


def _git_stdout(args: list[str]) -> str:
    return _git(args).stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


if __name__ == "__main__":
    main()
