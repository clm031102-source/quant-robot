from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("configs/workstations.json")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {config_path}")
    return data


def recommend_branch(config: dict[str, Any], task: str | None) -> str | None:
    if not task:
        return None
    tasks = config.get("tasks", {})
    if not isinstance(tasks, dict):
        return None
    task_config = tasks.get(task, {})
    if not isinstance(task_config, dict):
        return None
    branch = task_config.get("branch")
    return str(branch) if branch else None


def build_context(
    config: dict[str, Any],
    *,
    current_branch: str | None = None,
    machine: str | None = None,
    task: str | None = None,
    branch: str | None = None,
    git_status: str | None = None,
    upstream_sync: str | None = None,
) -> dict[str, Any]:
    machines = _dict(config.get("machines"))
    tasks = _dict(config.get("tasks"))
    branch_policy = _dict(config.get("branch_policy"))
    data_policy = _dict(config.get("data_policy"))
    selected_machine = _dict(machines.get(machine)) if machine else {}
    recommended_branch = recommend_branch(config, task)
    questions = _startup_questions(
        machines=machines,
        tasks=tasks,
        machine=machine,
        task=task,
        branch=branch,
    )
    return {
        "selected": {
            "machine": machine,
            "task": task,
            "requested_branch": branch,
            "recommended_branch": recommended_branch,
            "machine_allowed_tasks": selected_machine.get("allowed_tasks", []),
        },
        "git": {
            "current_branch": current_branch,
            "status": git_status,
            "upstream_sync": upstream_sync,
        },
        "branch_policy": branch_policy,
        "data_policy": data_policy,
        "tasks": tasks,
        "machines": machines,
        "questions": questions,
        "safety": config.get("safety", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the project startup context before beginning work.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--machine", choices=None)
    parser.add_argument("--task", choices=None)
    parser.add_argument("--branch")
    args = parser.parse_args()
    config = load_config(args.config)
    current_branch = _git(["branch", "--show-current"])
    git_status = _git(["status", "--short", "--branch"])
    upstream_sync = _upstream_sync()
    context = build_context(
        config,
        current_branch=current_branch,
        machine=args.machine,
        task=args.task,
        branch=args.branch,
        git_status=git_status,
        upstream_sync=upstream_sync,
    )
    print(json.dumps(context, indent=2, sort_keys=True))


def _startup_questions(
    *,
    machines: dict[str, Any],
    tasks: dict[str, Any],
    machine: str | None,
    task: str | None,
    branch: str | None,
) -> list[str]:
    questions: list[str] = []
    if not machine:
        questions.append(f"Which machine are you using today? Options: {', '.join(sorted(machines))}.")
    if not task:
        questions.append(f"What task type are you starting? Options: {', '.join(sorted(tasks))}.")
    if not branch:
        questions.append("Which branch should this work use? Suggested task branches are listed in tasks.")
    return questions


def _git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return result.stderr.strip()
    return result.stdout.strip()


def _upstream_sync() -> str:
    result = subprocess.run(
        ["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "no upstream"
    return result.stdout.strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
