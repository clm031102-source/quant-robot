from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.research.family_scheduler import build_research_family_schedule, load_research_family_config


STAGE = "quant_pm_startup_gate"


def load_quant_pm_gate_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {config_path}")
    return data


def build_quant_pm_startup_gate(
    *,
    gate_config: dict[str, Any],
    workstations_config: dict[str, Any],
    repo_root: str | Path = ".",
    machine: str | None = None,
    task: str | None = None,
    branch: str | None = None,
    current_branch: str | None = None,
    family_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    primary_market = str(gate_config.get("primary_market", "CN_ETF")).upper()
    reading = [_reading_row(root, row) for row in _list(gate_config.get("required_reading")) if isinstance(row, dict)]
    missing_reading = [row["path"] for row in reading if row.get("status") != "read"]
    selected_branch = branch or current_branch
    family_path = gate_config.get("research_family_config", "configs/research_family_scheduler_cn_etf.json")
    resolved_family_config = family_config or load_research_family_config(root / str(family_path))
    family_schedule = build_research_family_schedule(resolved_family_config)
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(_context_blockers(workstations_config, machine, task, selected_branch, current_branch))
    blockers.extend(f"required_reading_missing:{path}" for path in missing_reading)
    if str(resolved_family_config.get("primary_market", "")).upper() != primary_market:
        blockers.append("research_family_primary_market_mismatch")
    if _dict(family_schedule.get("summary")).get("scheduler_status") != "ready":
        blockers.append("research_family_scheduler_not_ready")
    blockers.extend(str(blocker) for blocker in _list(family_schedule.get("blockers")))
    blockers.extend(_direction_blockers(gate_config, family_schedule, primary_market))
    warnings.extend(str(warning) for warning in _list(family_schedule.get("warnings")))

    pack = {
        "stage": gate_config.get("stage", STAGE),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blockers else "ready",
        "selected": {
            "machine": machine,
            "task": task,
            "branch": selected_branch,
            "current_branch": current_branch,
        },
        "primary_market": primary_market,
        "required_skills": _list(gate_config.get("required_skills")),
        "required_reading": reading,
        "reading_summary": {
            "required": len(reading),
            "read": sum(1 for row in reading if row.get("status") == "read"),
            "missing": len(missing_reading),
        },
        "direction_rules": _dict(gate_config.get("direction_rules")),
        "research_family_schedule": {
            "stage": family_schedule.get("stage"),
            "summary": family_schedule.get("summary"),
            "allocation": family_schedule.get("allocation"),
            "blockers": family_schedule.get("blockers"),
            "warnings": family_schedule.get("warnings"),
        },
        "blockers": _unique(blockers),
        "warnings": _unique(warnings),
        "next_actions": _next_actions(blockers),
        "safety": {
            "research_only": True,
            "paper_only_next_step": True,
            "live_boundary_allowed": False,
            "token_storage": "environment_only",
        },
    }
    pack["markdown"] = render_quant_pm_startup_gate_markdown(pack)
    return _sanitize(pack)


def write_quant_pm_startup_gate(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "quant_pm_startup_gate_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "quant_pm_startup_gate_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("required_reading", [])).to_csv(output_path / "quant_pm_required_reading.csv", index=False)
    pd.DataFrame(pack.get("research_family_schedule", {}).get("allocation", [])).to_csv(
        output_path / "quant_pm_family_allocation.csv",
        index=False,
    )


def render_quant_pm_startup_gate_markdown(pack: dict[str, Any]) -> str:
    selected = _dict(pack.get("selected"))
    reading = _dict(pack.get("reading_summary"))
    schedule = _dict(pack.get("research_family_schedule"))
    schedule_summary = _dict(schedule.get("summary"))
    lines = [
        "# Quant PM Startup Gate",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Machine: {selected.get('machine')}",
        f"- Task: {selected.get('task')}",
        f"- Branch: {selected.get('branch')}",
        f"- Primary market: {pack.get('primary_market')}",
        f"- Required reading: {reading.get('read', 0)} / {reading.get('required', 0)}",
        f"- Research family scheduler: {schedule_summary.get('scheduler_status', 'unknown')}",
        f"- Active primary families: {schedule_summary.get('active_primary_families', 0)}",
        f"- Live boundary allowed: {_dict(pack.get('safety')).get('live_boundary_allowed', False)}",
        "",
        "## Required Reading",
        "",
    ]
    for row in _list(pack.get("required_reading")):
        if isinstance(row, dict):
            lines.append(f"- {row.get('status')}: {row.get('path')} sha256={row.get('sha256', '')}")
    lines.extend(["", "## Research Allocation", ""])
    allocation = _list(schedule.get("allocation"))
    if allocation:
        lines.extend(
            f"- {row.get('family_id')}: budget={_round(row.get('budget_share'))}, next={row.get('next_action')}"
            for row in allocation
            if isinstance(row, dict)
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = _list(pack.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    actions = _list(pack.get("next_actions"))
    lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict)) if actions else lines.append("- none")
    return "\n".join(lines) + "\n"


def _reading_row(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    path_text = str(row.get("path", ""))
    path = root / path_text
    result = {
        "path": path_text,
        "purpose": row.get("purpose"),
        "status": "missing",
        "bytes": 0,
        "lines": 0,
        "sha256": "",
    }
    if not path.exists() or not path.is_file():
        return result
    content = path.read_text(encoding="utf-8")
    result.update(
        {
            "status": "read",
            "bytes": len(content.encode("utf-8")),
            "lines": len(content.splitlines()),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
    )
    return result


def _context_blockers(
    config: dict[str, Any],
    machine: str | None,
    task: str | None,
    branch: str | None,
    current_branch: str | None,
) -> list[str]:
    blockers: list[str] = []
    machines = _dict(config.get("machines"))
    tasks = _dict(config.get("tasks"))
    if not machine:
        blockers.append("machine_not_confirmed")
    elif machine not in machines:
        blockers.append("unknown_machine")
    if not task:
        blockers.append("task_not_confirmed")
    elif task not in tasks:
        blockers.append("unknown_task")
    if machine in machines and task:
        allowed = _list(_dict(machines.get(machine)).get("allowed_tasks"))
        if task not in allowed:
            blockers.append("task_not_allowed_for_machine")
    if not branch:
        blockers.append("branch_not_confirmed")
    if (branch or current_branch) == "main" and task != "project_sync":
        blockers.append("non_sync_work_on_main")
    if branch and current_branch and branch != current_branch:
        blockers.append("requested_branch_not_current_branch")
    return blockers


def _direction_blockers(gate_config: dict[str, Any], family_schedule: dict[str, Any], primary_market: str) -> list[str]:
    blockers: list[str] = []
    rules = _dict(gate_config.get("direction_rules"))
    if str(rules.get("final_signal_market", primary_market)).upper() != primary_market:
        blockers.append("final_signal_market_not_primary_market")
    families = _list(family_schedule.get("families"))
    moneyflow = next(
        (row for row in families if isinstance(row, dict) and row.get("family_id") == "cn_stock_moneyflow_selection"),
        None,
    )
    if moneyflow is None:
        blockers.append("cn_stock_moneyflow_family_missing")
    else:
        if moneyflow.get("status") != "auxiliary_only":
            blockers.append("cn_stock_moneyflow_not_auxiliary_only")
        if _float(moneyflow.get("budget_share"), 0.0) != 0.0:
            blockers.append("cn_stock_moneyflow_budget_not_zero")
        if moneyflow.get("primary_allocation_allowed"):
            blockers.append("cn_stock_moneyflow_primary_allocation_allowed")
    if not _list(family_schedule.get("allocation")):
        blockers.append("no_primary_research_allocation")
    return blockers


def _next_actions(blockers: list[str]) -> list[dict[str, Any]]:
    if blockers:
        return [
            {
                "action": "stop_before_factor_mining",
                "reason": "Quant PM startup gate is blocked; fix direction, context, or required reading before running data or factor batches.",
            }
        ]
    return [
        {
            "action": "start_cn_etf_research",
            "reason": "Startup gate passed; proceed with CN_ETF data refresh, data-quality audit, and diversified factor-family mining.",
        }
    ]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _round(value: Any) -> float:
    return round(_float(value), 4)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value
