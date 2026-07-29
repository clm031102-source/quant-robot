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
    restricted = _restricted_review_mode(task, resolved_family_config, family_schedule)
    restricted_mode = str(restricted.get("mode", "")) if restricted else ""
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(_context_blockers(workstations_config, machine, task, selected_branch, current_branch))
    blockers.extend(f"required_reading_missing:{path}" for path in missing_reading)
    if str(resolved_family_config.get("primary_market", "")).upper() != primary_market:
        blockers.append("research_family_primary_market_mismatch")
    if _dict(family_schedule.get("summary")).get("scheduler_status") != "ready" and not restricted_mode:
        blockers.append("research_family_scheduler_not_ready")
    if restricted_mode == "source_repair_only":
        warnings.append("research_family_scheduler_source_repair_mode")
    elif restricted_mode == "preregistration_only":
        warnings.append("research_family_scheduler_preregistration_mode")
    elif restricted_mode == "single_prescreen_only":
        warnings.append("research_family_scheduler_single_prescreen_mode")
    elif restricted_mode == "family_rotation_review_only":
        warnings.append("research_family_scheduler_family_rotation_review_mode")
    else:
        blockers.extend(str(blocker) for blocker in _list(family_schedule.get("blockers")))
    blockers.extend(
        _direction_blockers(
            gate_config,
            family_schedule,
            primary_market,
            allow_no_primary_allocation=bool(restricted_mode),
        )
    )
    warnings.extend(str(warning) for warning in _list(family_schedule.get("warnings")))

    pack = {
        "stage": gate_config.get("stage", STAGE),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blockers else "ready",
        "mode": restricted_mode or "standard_research",
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
        "next_actions": _next_actions(blockers, restricted_mode=restricted_mode),
        "safety": {
            "research_only": True,
            "paper_only_next_step": True,
            "factor_batch_allowed": bool(
                not blockers
                and (not restricted_mode or restricted_mode == "single_prescreen_only")
            ),
            "factor_batch_scope": _dict(restricted.get("scope")) if restricted else {},
            "single_prescreen_authorization_required": restricted_mode == "single_prescreen_only",
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "final_holdout_allowed": False,
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
        f"- Mode: {pack.get('mode', 'standard_research')}",
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


def _direction_blockers(
    gate_config: dict[str, Any],
    family_schedule: dict[str, Any],
    primary_market: str,
    *,
    allow_no_primary_allocation: bool = False,
) -> list[str]:
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
    if not allow_no_primary_allocation and not _list(family_schedule.get("allocation")):
        blockers.append("no_primary_research_allocation")
    return blockers


def _restricted_review_mode(
    task: str | None,
    family_config: dict[str, Any],
    family_schedule: dict[str, Any],
) -> dict[str, Any] | None:
    decision = _dict(family_config.get("last_decision"))
    decision_name = str(decision.get("decision", ""))
    if decision_name == "source_blocked_no_factor_batch":
        allowed_tasks = {"data_pipeline", "factor_review"}
        mode = "source_repair_only"
    elif decision_name == "source_ready_preregistration_required_no_factor_batch":
        allowed_tasks = {"factor_review"}
        mode = "preregistration_only"
    elif decision_name == "prescreen_preregistered_single_batch_only":
        return _single_prescreen_mode(task, decision, family_schedule)
    elif decision_name == "prescreen_rejected_family_rotation_review_only":
        if (
            decision.get("family_rotation_review_allowed") is not True
            or decision.get("primary_passed") is not False
            or decision.get("execution_count") != 1
            or _float(decision.get("unallocated_budget_share"), -1.0) != 1.0
        ):
            return None
        for key in (
            "single_prescreen_allowed",
            "portfolio_grid_allowed",
            "walk_forward_allowed",
            "final_holdout_allowed",
            "promotion_allowed",
            "paper_signal_allowed",
            "broker_connection_allowed",
            "account_read_allowed",
            "order_placement_allowed",
            "live_boundary_allowed",
        ):
            if decision.get(key) is not False:
                return None
        allowed_tasks = {"factor_review"}
        mode = "family_rotation_review_only"
    else:
        return None
    if task not in allowed_tasks:
        return None
    if decision.get("factor_batch_allowed") is not False:
        return None
    schedule_blockers = {str(item) for item in _list(family_schedule.get("blockers"))}
    if schedule_blockers != {"insufficient_active_research_families"}:
        return None
    summary = _dict(family_schedule.get("summary"))
    allowed = (
        _float(summary.get("primary_budget_share"), -1.0) == 0.0
        and int(summary.get("active_primary_families", -1)) == 0
    )
    return {"mode": mode, "scope": {}} if allowed else None


def _single_prescreen_mode(
    task: str | None,
    decision: dict[str, Any],
    family_schedule: dict[str, Any],
) -> dict[str, Any] | None:
    if task != "factor_batch":
        return None
    schedule_blockers = {str(item) for item in _list(family_schedule.get("blockers"))}
    if schedule_blockers != {"insufficient_active_research_families"}:
        return None
    summary = _dict(family_schedule.get("summary"))
    if (
        _float(summary.get("primary_budget_share"), -1.0) != 0.0
        or int(summary.get("active_primary_families", -1)) != 0
        or _float(decision.get("unallocated_budget_share"), -1.0) != 1.0
    ):
        return None
    allowed_scopes = {
        "etf_dynamic_peer_residual_dislocation_reversal_5_60": (
            "cn_etf_dynamic_peer_dislocation_prescreen",
            "mapping_sha256",
            2,
            5,
            20,
        ),
        "etf_residual_share_creation_crowding_reversal_20": (
            "cn_etf_fund_structure_crowding_prescreen",
            "canonical_data_sha256",
            2,
            5,
            20,
        ),
        "etf_residual_margin_financing_growth_reversal_20": (
            "cn_etf_margin_positioning_prescreen",
            "canonical_data_sha256",
            2,
            5,
            20,
        ),
        "etf_delayed_nav_premium_innovation_reversal_60": (
            "cn_etf_delayed_nav_premium_prescreen",
            "canonical_data_sha256",
            1,
            1,
            5,
        ),
    }
    factor_name = decision.get("factor_name")
    if factor_name not in allowed_scopes:
        return None
    (
        allowed_stage,
        source_identity_key,
        hypothesis_count,
        primary_horizon,
        diagnostic_horizon,
    ) = allowed_scopes[factor_name]
    for key in (
        "preregistration_config_sha256",
        "preregistration_result_sha256",
        "authorization_sha256",
        "source_config_sha256",
        "source_result_sha256",
        source_identity_key,
    ):
        if not _is_sha256(decision.get(key)):
            return None
    if (
        decision.get("hypothesis_count") != hypothesis_count
        or decision.get("primary_horizon") != primary_horizon
        or decision.get("diagnostic_horizon") != diagnostic_horizon
        or decision.get("single_prescreen_run_limit") != 1
        or decision.get("execution_count") != 0
        or decision.get("execution_ledger_required") is not True
        or decision.get("factor_batch_allowed") is not True
        or decision.get("single_prescreen_allowed") is not True
        or decision.get("allowed_stage") != allowed_stage
    ):
        return None
    ledger_path = decision.get("execution_ledger_path")
    if not isinstance(ledger_path, str) or not ledger_path.strip():
        return None
    for key in (
        "portfolio_grid_allowed",
        "walk_forward_allowed",
        "final_holdout_allowed",
        "promotion_allowed",
        "paper_signal_allowed",
        "broker_connection_allowed",
        "account_read_allowed",
        "order_placement_allowed",
        "live_boundary_allowed",
    ):
        if decision.get(key) is not False:
            return None
    return {
        "mode": "single_prescreen_only",
        "scope": {
            "factor_name": decision["factor_name"],
            "config_sha256": decision["preregistration_config_sha256"],
            "preregistration_result_sha256": decision["preregistration_result_sha256"],
            "authorization_sha256": decision["authorization_sha256"],
            "source_config_sha256": decision["source_config_sha256"],
            "source_result_sha256": decision["source_result_sha256"],
            source_identity_key: decision[source_identity_key],
            "allowed_stage": decision["allowed_stage"],
            "max_executions": 1,
            "execution_count": 0,
            "execution_ledger_path": ledger_path,
        },
    }


def _next_actions(
    blockers: list[str],
    *,
    restricted_mode: str | None = None,
) -> list[dict[str, Any]]:
    if blockers:
        return [
            {
                "action": "stop_before_factor_mining",
                "reason": "Quant PM startup gate is blocked; fix direction, context, or required reading before running data or factor batches.",
            }
        ]
    if restricted_mode == "source_repair_only":
        return [
            {
                "action": "repair_cn_etf_source_readiness",
                "reason": "Source-repair mode is ready for metadata or data backfill only; factor batches remain disabled until the scheduler has audited primary allocations.",
            }
        ]
    if restricted_mode == "preregistration_only":
        return [
            {
                "action": "preregister_cn_etf_source_prescreen",
                "reason": "The source-readiness gate passed, but only a frozen prescreen preregistration is allowed; factor generation and batches remain disabled.",
            }
        ]
    if restricted_mode == "single_prescreen_only":
        return [
            {
                "action": "run_hash_bound_single_prescreen",
                "reason": "Exactly one authorization-bound dynamic-peer dislocation prescreen is allowed; all portfolio, walk-forward, holdout, paper, and live actions remain disabled.",
            }
        ]
    if restricted_mode == "family_rotation_review_only":
        return [
            {
                "action": "review_next_orthogonal_cn_etf_family",
                "reason": "The authorized dynamic-peer prescreen was rejected and closed; review one new point-in-time-safe orthogonal family before any further factor batch.",
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


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


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
