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
DEFAULT_INTEGRATION_MANIFEST = Path("configs/factor_branch_integration_manifest.json")
CORE_SYNC_TASKS = {"architecture_ops", "factor_integration", "project_sync"}
RESEARCH_BRANCH_PREFIXES = (
    "origin/codex/factor-",
    "origin/codex/tushare-",
)
TOPIC_BRANCH_PREFIX = "origin/codex/"
BRANCH_CLEANUP_STATUSES = {
    "absorbed_by_manifest",
    "ignored_by_manifest",
    "merged_to_stable_branch",
}


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
    pending_research_branches: list[dict[str, str]] | None = None,
    pending_topic_branches: list[dict[str, str]] | None = None,
    cleanup_topic_branches: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    classification = classify_changed_paths(changed_paths, config)
    pending_research_branches = pending_research_branches or []
    pending_topic_branches = pending_topic_branches or []
    cleanup_topic_branches = cleanup_topic_branches or []
    blockers = _sync_blockers(
        config=config,
        current_branch=current_branch,
        classification=classification,
        machine=machine,
        task=task,
        execute=execute,
        push=push,
        upstream_sync=upstream_sync,
        pending_research_branches=pending_research_branches,
        pending_topic_branches=pending_topic_branches,
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
        "research_branch_integration": {
            "pending": pending_research_branches,
        },
        "topic_branch_integration": {
            "pending": pending_topic_branches,
            "cleanup": cleanup_topic_branches,
        },
        "blockers": blockers,
        "actions": _recommended_actions(classification, blockers, execute, push),
    }


def audit_remote_research_branches(
    remote_branches: list[dict[str, str]],
    manifest: dict[str, Any],
    *,
    current_commits: set[str],
) -> list[dict[str, str]]:
    absorbed = _manifest_commit_keys(manifest, "absorbed_branches")
    ignored = _manifest_commit_keys(manifest, "ignored_branches")
    pending: list[dict[str, str]] = []
    for branch in remote_branches:
        name = str(branch.get("name", ""))
        commit = str(branch.get("commit", ""))
        if not name or not commit or not _is_research_branch(name):
            continue
        key = (name, commit)
        if commit in current_commits or key in absorbed or key in ignored:
            continue
        pending.append(
            {
                "branch": name,
                "commit": commit,
                "status": "pending_integration",
            }
        )
    return sorted(pending, key=lambda item: item["branch"])


def audit_remote_topic_branches(
    remote_branches: list[dict[str, str]],
    manifest: dict[str, Any],
    *,
    current_commits: set[str],
    stable_commits: set[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    absorbed = _manifest_commit_keys(manifest, "absorbed_branches")
    ignored = _manifest_commit_keys(manifest, "ignored_branches")
    stable_commits = current_commits if stable_commits is None else stable_commits
    pending: list[dict[str, str]] = []
    cleanup: list[dict[str, str]] = []
    for branch in remote_branches:
        name = str(branch.get("name", ""))
        commit = str(branch.get("commit", ""))
        if not name or not commit or not _is_topic_branch(name):
            continue
        key = (name, commit)
        if commit in stable_commits:
            cleanup.append({"branch": name, "commit": commit, "status": "merged_to_stable_branch"})
        elif key in absorbed:
            cleanup.append({"branch": name, "commit": commit, "status": "absorbed_by_manifest"})
        elif key in ignored:
            cleanup.append({"branch": name, "commit": commit, "status": "ignored_by_manifest"})
        elif commit not in current_commits and not _is_research_branch(name):
            pending.append({"branch": name, "commit": commit, "status": "pending_integration"})
    return {
        "pending": sorted(pending, key=lambda item: item["branch"]),
        "cleanup": sorted(cleanup, key=lambda item: item["branch"]),
    }


def audit_local_topic_branches(
    local_branches: list[dict[str, str]],
    *,
    current_branch: str,
    stable_commits: set[str],
) -> list[dict[str, str]]:
    cleanup: list[dict[str, str]] = []
    for branch in local_branches:
        name = str(branch.get("name", ""))
        commit = str(branch.get("commit", ""))
        if not name or not commit or not _is_local_topic_branch(name) or name == current_branch:
            continue
        if commit in stable_commits:
            cleanup.append({"branch": name, "commit": commit, "status": "merged_to_stable_branch"})
    return sorted(cleanup, key=lambda item: item["branch"])


def build_topic_branch_cleanup_commands(
    *,
    remote_cleanup: list[dict[str, str]],
    local_cleanup: list[dict[str, str]],
    current_branch: str,
) -> list[list[str]]:
    commands: list[list[str]] = []
    for branch in sorted(remote_cleanup, key=lambda item: str(item.get("branch", ""))):
        name = str(branch.get("branch", ""))
        status = str(branch.get("status", ""))
        if status not in BRANCH_CLEANUP_STATUSES or not _is_topic_branch(name):
            continue
        local_name = name.removeprefix("origin/")
        if not _is_local_topic_branch(local_name) or local_name == current_branch:
            continue
        commands.append(["push", "origin", "--delete", local_name])

    for branch in sorted(local_cleanup, key=lambda item: str(item.get("branch", ""))):
        name = str(branch.get("branch", ""))
        status = str(branch.get("status", ""))
        if status not in BRANCH_CLEANUP_STATUSES or not _is_local_topic_branch(name):
            continue
        if name == current_branch:
            continue
        commands.append(["branch", "-d", name])
    return commands


def load_integration_manifest(path: str | Path = DEFAULT_INTEGRATION_MANIFEST) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {"absorbed_branches": [], "ignored_branches": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely sync project code/config/docs to GitHub.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--machine")
    parser.add_argument("--task")
    parser.add_argument("--message", default=DEFAULT_COMMIT_MESSAGE)
    parser.add_argument("--execute", action="store_true", help="Stage and commit syncable files if safe.")
    parser.add_argument("--push", action="store_true", help="Push after commit when safe. Requires --execute.")
    parser.add_argument(
        "--cleanup-topic-branches",
        action="store_true",
        help="Delete merged or manifest-absorbed codex topic branches after a safe execute plan.",
    )
    parser.add_argument("--skip-fetch", action="store_true", help="Do not fetch/prune before building the plan.")
    args = parser.parse_args()

    if args.push and not args.execute:
        raise SystemExit("--push requires --execute")
    if args.cleanup_topic_branches and not args.execute:
        raise SystemExit("--cleanup-topic-branches requires --execute")

    config = load_config(args.config)
    if not args.skip_fetch:
        _git(["fetch", "origin", "--prune"], check=False)

    current_branch = _git_stdout(["branch", "--show-current"])
    changed_paths = _changed_paths()
    upstream_sync = _upstream_sync()
    remote_topic_branches = _remote_topic_branches()
    local_topic_branches = _local_topic_branches()
    manifest = load_integration_manifest()
    current_commits = _current_history_commits(remote_topic_branches)
    stable_commits = _history_commits(remote_topic_branches + local_topic_branches, "origin/main")
    pending_research_branches = audit_remote_research_branches(
        remote_topic_branches,
        manifest,
        current_commits=current_commits,
    )
    topic_branch_audit = audit_remote_topic_branches(
        remote_topic_branches,
        manifest,
        current_commits=current_commits,
        stable_commits=stable_commits,
    )
    local_topic_cleanup = audit_local_topic_branches(
        local_topic_branches,
        current_branch=current_branch,
        stable_commits=stable_commits,
    )
    plan = build_sync_plan(
        config,
        current_branch=current_branch,
        changed_paths=changed_paths,
        machine=args.machine,
        task=args.task,
        execute=args.execute,
        push=args.push,
        upstream_sync=upstream_sync,
        pending_research_branches=pending_research_branches,
        pending_topic_branches=topic_branch_audit["pending"],
        cleanup_topic_branches=topic_branch_audit["cleanup"],
    )
    plan["research_branch_integration"]["remote_branch_count"] = len(
        [branch for branch in remote_topic_branches if _is_research_branch(str(branch.get("name", "")))]
    )
    plan["topic_branch_integration"]["remote_branch_count"] = len(remote_topic_branches)
    plan["local_topic_branch_cleanup"] = {
        "cleanup": local_topic_cleanup,
        "local_branch_count": len(local_topic_branches),
    }
    if args.cleanup_topic_branches:
        plan["topic_branch_integration"]["cleanup_requested"] = True

    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    if plan["blockers"]:
        print(json.dumps(plan, indent=2, sort_keys=True))
        raise SystemExit(2)

    syncable = plan["path_classification"]["syncable"]
    if not syncable:
        plan["actions"].append("nothing_to_commit")
        if should_push_existing_commits(upstream_sync, push=args.push):
            _push_current_branch(current_branch, upstream_sync)
            plan["actions"].append("pushed")
            plan["git"]["upstream_sync_after_push"] = _upstream_sync()
        _cleanup_topic_branches_when_requested(
            requested=args.cleanup_topic_branches,
            plan=plan,
            remote_cleanup=topic_branch_audit["cleanup"],
            local_cleanup=local_topic_cleanup,
            current_branch=current_branch,
        )
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
        _push_current_branch(current_branch, upstream_sync)
        plan["actions"].append("pushed")
        plan["git"]["upstream_sync_after_push"] = _upstream_sync()

    _cleanup_topic_branches_when_requested(
        requested=args.cleanup_topic_branches,
        plan=plan,
        remote_cleanup=topic_branch_audit["cleanup"],
        local_cleanup=local_topic_cleanup,
        current_branch=current_branch,
    )

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
    pending_research_branches: list[dict[str, str]],
    pending_topic_branches: list[dict[str, str]],
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
    if pending_research_branches and task in CORE_SYNC_TASKS:
        blockers.append("pending_research_branches_require_integration")
    if pending_topic_branches and task in CORE_SYNC_TASKS:
        blockers.append("pending_topic_branches_require_integration")
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


def _cleanup_topic_branches_when_requested(
    *,
    requested: bool,
    plan: dict[str, Any],
    remote_cleanup: list[dict[str, str]],
    local_cleanup: list[dict[str, str]],
    current_branch: str,
) -> None:
    if not requested:
        return
    commands = build_topic_branch_cleanup_commands(
        remote_cleanup=remote_cleanup,
        local_cleanup=local_cleanup,
        current_branch=current_branch,
    )
    cleaned: list[str] = []
    for command in commands:
        _git(command)
        if command[:3] == ["push", "origin", "--delete"]:
            cleaned.append(f"origin/{command[3]}")
        elif command[:2] == ["branch", "-d"]:
            cleaned.append(command[2])
    plan["topic_branch_integration"]["cleaned"] = cleaned
    plan["actions"].append("cleaned_topic_branches" if cleaned else "no_topic_branches_to_clean")


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


def _remote_topic_branches() -> list[dict[str, str]]:
    result = _git(
        [
            "for-each-ref",
            "--format=%(refname:short)|%(objectname)",
            "refs/remotes/origin/codex",
        ],
        check=False,
    )
    if result.returncode != 0:
        return []
    branches: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        name, commit = line.split("|", 1)
        if _is_topic_branch(name):
            branches.append({"name": name.strip(), "commit": commit.strip()})
    return branches


def _local_topic_branches() -> list[dict[str, str]]:
    result = _git(
        [
            "for-each-ref",
            "--format=%(refname:short)|%(objectname)",
            "refs/heads/codex",
        ],
        check=False,
    )
    if result.returncode != 0:
        return []
    branches: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        name, commit = line.split("|", 1)
        if _is_local_topic_branch(name):
            branches.append({"name": name.strip(), "commit": commit.strip()})
    return branches


def _current_history_commits(remote_branches: list[dict[str, str]]) -> set[str]:
    return _history_commits(remote_branches, "HEAD")


def _history_commits(remote_branches: list[dict[str, str]], ref: str) -> set[str]:
    commits: set[str] = set()
    for branch in remote_branches:
        commit = str(branch.get("commit", ""))
        if not commit:
            continue
        result = _git(["merge-base", "--is-ancestor", commit, ref], check=False)
        if result.returncode == 0:
            commits.add(commit)
    return commits


def _is_topic_branch(name: str) -> bool:
    return name.startswith(TOPIC_BRANCH_PREFIX)


def _is_local_topic_branch(name: str) -> bool:
    return name.startswith("codex/")


def _is_research_branch(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in RESEARCH_BRANCH_PREFIXES)


def _manifest_commit_keys(manifest: dict[str, Any], key: str) -> set[tuple[str, str]]:
    records = manifest.get(key, [])
    if not isinstance(records, list):
        return set()
    result: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        branch = str(record.get("branch", ""))
        commit = str(record.get("commit", ""))
        status = str(record.get("status", ""))
        if branch and commit and status in {"absorbed", "ignored"}:
            result.add((branch, commit))
    return result


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


def should_push_existing_commits(upstream_sync: str, *, push: bool) -> bool:
    if not push:
        return False
    if upstream_sync == "no upstream":
        return True
    parts = upstream_sync.replace("\t", " ").split()
    if len(parts) < 2:
        return False
    try:
        return int(parts[1]) > 0
    except ValueError:
        return False


def _push_current_branch(current_branch: str, upstream_sync: str) -> None:
    if upstream_sync == "no upstream":
        _git(["push", "-u", "origin", current_branch])
    else:
        _git(["push", "origin", current_branch])


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
