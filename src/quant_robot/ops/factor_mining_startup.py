from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "factor_mining_startup_gate"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_RESEARCH_OBJECTIVE = "cn_stock_cross_sectional_alpha"
DEFAULT_AUDIT_REPORT = "data/reports/cn_stock_factor_mining_20260617_batch_audit.md"
DEFAULT_NEXT_DIRECTION = "factor_validation_required_for_daily_champion_oos_candidates"
REQUIRED_LONG_CYCLE_STAGE = "long_cycle_replay"
REQUIRED_LONG_CYCLE_DESIGN_ITEMS = [
    "long_cycle_same_parameter_replay",
    "same_parameter_full_sample_diagnostic",
    "rolling_walk_forward_train_test_split",
    "market_regime_coverage",
    "lookahead_bias_audit",
    "overfit_multiple_testing_audit",
]
REQUIRED_LONG_CYCLE_CONFIRMATIONS = [
    "same_parameter_full_sample_enabled",
    "market_regime_coverage_enabled",
    "lookahead_bias_audit_enabled",
    "overfit_multiple_testing_audit_enabled",
]


def build_factor_mining_startup_gate(
    config: dict[str, Any],
    *,
    request: dict[str, Any],
    current_branch: str,
) -> dict[str, Any]:
    expected_market = str(config.get("market", "CN"))
    expected_asset_type = str(config.get("asset_type", "stock"))
    branch = str(request.get("branch", ""))
    confirmations = _dict(request.get("confirmations"))
    blockers = _blockers(config, request, current_branch=current_branch, confirmations=confirmations)
    status = "cleared" if not blockers else "blocked"
    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "scope_id": str(config.get("scope_id", "cn_stock_factor_mining")),
            "machine": request.get("machine"),
            "task": request.get("task"),
            "branch": branch,
            "current_branch": current_branch,
            "market": request.get("market", expected_market),
            "asset_type": request.get("asset_type", expected_asset_type),
            "expected_market": expected_market,
            "expected_asset_type": expected_asset_type,
            "excluded_markets": _list(config.get("forbidden_markets")),
            "commits_allowed": bool(request.get("commits_allowed", False)),
            "pushes_allowed": bool(request.get("pushes_allowed", False)),
        },
        "validation_windows": _dict(config.get("validation_windows")),
        "candidate_budget": _dict(config.get("candidate_budget")),
        "research_direction": _research_direction(config),
        "repeatable_mining_protocol": _repeatable_mining_protocol(config),
        "pre_run_checklist": _pre_run_checklist(config),
        "confirmation_questions": _confirmation_questions(config),
        "decision": {
            "startup_gate_cleared": not blockers,
            "blockers": blockers,
        },
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    return packet


def validate_cleared_startup_gate_packet(
    packet_path: str | Path | None,
    *,
    expected_market: str = "CN",
    expected_asset_type: str = "stock",
    context: str = "CN stock factor mining",
    require_generated_today: bool = True,
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a cleared startup gate packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a cleared startup gate packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} startup gate packet must be generated today: {path}")
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    if packet.get("status") != "cleared" or decision.get("startup_gate_cleared") is not True:
        raise ValueError(f"{context} startup gate is not cleared: {path}")
    if str(summary.get("market")).upper() != expected_market.upper() or str(summary.get("asset_type")).lower() != expected_asset_type.lower():
        raise ValueError(f"{context} startup gate scope mismatch: {path}")
    _validate_research_direction(packet, context=context, path=path)
    _validate_repeatable_mining_protocol(packet, context=context, path=path)
    return packet


def _validate_research_direction(packet: dict[str, Any], *, context: str, path: Path) -> None:
    research_direction = _dict(packet.get("research_direction"))
    if not research_direction:
        raise ValueError(f"{context} startup gate research direction is missing: {path}")
    objective = str(research_direction.get("objective", ""))
    if objective != REQUIRED_RESEARCH_OBJECTIVE:
        raise ValueError(f"{context} startup gate research direction mismatch: {path}")
    if not _list(research_direction.get("allowed_factor_families")):
        raise ValueError(f"{context} startup gate research direction lacks factor families: {path}")
    stage_policy = _dict(research_direction.get("stage_policy"))
    missing_stages = [stage for stage in ("discovery", "validation", "final_holdout") if stage not in stage_policy]
    if missing_stages:
        raise ValueError(f"{context} startup gate research direction lacks stage policy: {path}")
    if REQUIRED_LONG_CYCLE_STAGE not in stage_policy:
        raise ValueError(f"{context} startup gate lacks long-cycle replay stage policy: {path}")
    rotation = _dict(research_direction.get("factor_family_rotation"))
    if rotation.get("max_failed_batches_before_rotation") is None:
        raise ValueError(f"{context} startup gate research direction lacks rotation policy: {path}")


def _validate_repeatable_mining_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    if not protocol:
        raise ValueError(f"{context} startup gate repeatable mining protocol is missing: {path}")
    if not str(protocol.get("source_audit", "")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks source audit: {path}")
    if not str(protocol.get("next_direction", "")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks next direction: {path}")
    if not _list(protocol.get("recently_rejected_directions")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks rejected directions: {path}")
    if not _list(protocol.get("required_experiment_design")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks experiment design: {path}")
    if not _list(protocol.get("confirm_before_each_run")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks per-run confirmations: {path}")
    design_items = set(_list(protocol.get("required_experiment_design")))
    missing_design_items = [item for item in REQUIRED_LONG_CYCLE_DESIGN_ITEMS if item not in design_items]
    if missing_design_items:
        raise ValueError(f"{context} startup gate lacks long-cycle experiment design: {path}")
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_confirmations = [item for item in REQUIRED_LONG_CYCLE_CONFIRMATIONS if item not in confirmations]
    if missing_confirmations:
        raise ValueError(f"{context} startup gate lacks long-cycle per-run confirmations: {path}")


def _blockers(
    config: dict[str, Any],
    request: dict[str, Any],
    *,
    current_branch: str,
    confirmations: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    machine = str(request.get("machine", ""))
    task = str(request.get("task", ""))
    branch = str(request.get("branch", ""))
    market = str(request.get("market", ""))
    asset_type = str(request.get("asset_type", ""))
    expected_market = str(config.get("market", "CN"))
    expected_asset_type = str(config.get("asset_type", "stock"))
    branch_prefixes = _branch_prefixes(config)

    if machine not in set(_list(config.get("allowed_machines"))):
        blockers.append("machine_not_allowed")
    if task not in set(_list(config.get("allowed_tasks"))):
        blockers.append("task_not_allowed")
    if branch_prefixes and not any(branch.startswith(prefix) for prefix in branch_prefixes):
        blockers.append("branch_prefix_mismatch")
    if current_branch and branch and current_branch != branch:
        blockers.append("current_branch_mismatch")
    if market != expected_market:
        blockers.append("market_scope_mismatch")
    if asset_type != expected_asset_type:
        blockers.append("asset_type_scope_mismatch")

    for name in _list(config.get("required_confirmations")):
        if confirmations.get(name) is not True:
            blockers.append(f"missing_confirmation:{name}")
    return blockers


def _pre_run_checklist(config: dict[str, Any]) -> list[str]:
    direction = _research_direction(config)
    protocol = _repeatable_mining_protocol(config)
    return [
        "Confirm CN stock scope before mining; do not mix ETF rotation evidence into this run.",
        "Confirm machine, task type, branch, and commit/push policy before starting.",
        f"Read the source audit before mining again: {protocol.get('source_audit')}.",
        f"Confirm the next mining direction: {protocol.get('next_direction')}.",
        f"Do not repeat rejected directions without a new thesis: {', '.join(_list(protocol.get('recently_rejected_directions')))}.",
        f"Confirm required experiment design items: {', '.join(_list(protocol.get('required_experiment_design')))}.",
        "Run data coverage and universe checks before candidate generation.",
        "Pre-register candidate names, expressions, directions, windows, fields, and economic rationale.",
        f"Confirm the pre-registered batch spans allowed factor families: {', '.join(_list(direction.get('allowed_factor_families')))}.",
        "Do not keep mining one failed family; rotate direction after the configured failed-batch limit.",
        "Do not treat positive IC alone as tradable; require top-N return, cost, capacity, drawdown, and tail-IC review.",
        "Use same-parameter long-cycle replay before treating any short-window result as evidence.",
        "Use walk-forward validation, regime coverage, realistic costs, capacity controls, overlap-aware statistics, and final holdout review.",
        "Do not tune parameters after reading final_holdout.",
        "Record rejected candidates and failed directions, not only winners.",
        f"Keep excluded markets out of the run: {', '.join(_list(config.get('forbidden_markets')))}.",
    ]


def _confirmation_questions(config: dict[str, Any]) -> list[str]:
    market = str(config.get("market", "CN"))
    asset_type = str(config.get("asset_type", "stock"))
    branch_prefixes = _branch_prefixes(config) or ["codex/factor-batch-cn-stock-"]
    protocol = _repeatable_mining_protocol(config)
    return [
        f"Confirm {market} {asset_type} scope and reject ETF rotation scope for this run.",
        "Confirm the machine is allowed for factor_batch or factor_validation.",
        f"Confirm the current branch starts with one of: {', '.join(branch_prefixes)}.",
        "Confirm whether commits are allowed and pushes are disabled unless manually approved.",
        f"Confirm the audit optimization plan was reviewed: {protocol.get('source_audit')}.",
        f"Confirm this run follows the next direction: {protocol.get('next_direction')}.",
        "Confirm historical candidates and parameters are replayed unchanged across the long cycle before new profitability claims.",
        "Confirm regime coverage, look-ahead audit, overfit/multiple-testing audit, overlap-aware return statistics, and cost/capacity stress are enabled.",
        "Confirm 2026 data, when available, is treated as final holdout rather than a tuning set.",
        "Confirm a pre-registered candidate plan exists before generating candidates.",
        "Confirm cost and capacity gates are required before any candidate can advance.",
        "Confirm failed single-family directions will be recorded and rotated away from.",
    ]


def _research_direction(config: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(config.get("research_direction"))
    allowed_families = _list(raw.get("allowed_factor_families")) or [
        "price_volume",
        "daily_basic",
        "moneyflow",
        "composite",
    ]
    return {
        "objective": str(raw.get("objective", REQUIRED_RESEARCH_OBJECTIVE)),
        "mandate": str(raw.get("mandate", "Mine tradable CN stock alpha factors, not ETF rotation signals.")),
        "target_market": str(config.get("market", "CN")),
        "target_asset_type": str(config.get("asset_type", "stock")),
        "allowed_factor_families": allowed_families,
        "forbidden_directions": _list(raw.get("forbidden_directions"))
        or ["cn_etf_rotation", "single_family_lockin", "oos_tuning"],
        "stage_policy": _dict(raw.get("stage_policy"))
        or {
            "discovery": "Design and filter candidates only.",
            "long_cycle_replay": "Replay historical candidates and parameters unchanged across the available long cycle before new mining claims.",
            "validation": "Run OOS only after discovery evidence clears.",
            "final_holdout": "Read once; never tune after reading.",
        },
        "factor_family_rotation": _dict(raw.get("factor_family_rotation"))
        or {
            "max_failed_batches_before_rotation": 1,
            "max_single_family_share": 0.5,
            "record_rejected_families": True,
        },
    }


def _repeatable_mining_protocol(config: dict[str, Any]) -> dict[str, Any]:
    direction = _dict(config.get("research_direction"))
    raw = _dict(direction.get("repeatable_mining_protocol")) or _dict(config.get("repeatable_mining_protocol"))
    return {
        "source_audit": str(raw.get("source_audit", DEFAULT_AUDIT_REPORT)),
        "next_direction": str(raw.get("next_direction", DEFAULT_NEXT_DIRECTION)),
        "recently_rejected_directions": _list(raw.get("recently_rejected_directions"))
        or [
            "single_factor_top50_daily_long_only",
            "liquid_trend_direct_long",
            "capacity_blind_microcap_tail",
            "moneyflow_only_lockin",
        ],
        "required_experiment_design": _list(raw.get("required_experiment_design"))
        or [
            "long_cycle_same_parameter_replay",
            "same_parameter_full_sample_diagnostic",
            "rolling_walk_forward_train_test_split",
            "market_regime_coverage",
            "lookahead_bias_audit",
            "overfit_multiple_testing_audit",
            "daily_champion_10bps_20bps_validation",
            "twenty_twenty_five_oos_only",
            "overlap_aware_return_statistics",
            "daily_vs_every2_every3_controls",
            "cost_capacity_turnover_stress",
            "cumulative_multiple_testing_accounting",
            "no_parameter_tuning_during_oos",
            "final_holdout_only_after_oos_clearance",
        ],
        "confirm_before_each_run": _list(raw.get("confirm_before_each_run"))
        or [
            "long_cycle_replay_plan_read",
            "same_parameter_full_sample_enabled",
            "market_regime_coverage_enabled",
            "lookahead_bias_audit_enabled",
            "overfit_multiple_testing_audit_enabled",
            "previous_audit_read",
            "latest_bootstrap_diagnostic_read",
            "latest_tailrankic_batch_read",
            "latest_monthly_persistence_batch_read",
            "latest_monthly_loss_control_batch_read",
            "latest_threshold_robustness_batch_read",
            "latest_rankic_enhancement_batch_read",
            "latest_champion_staggered_schedule_batch_read",
            "batch12_validation_handoff_read",
            "prev_month_neg1_gate_pre_registered",
            "downside_range_champion_pre_registered",
            "daily_champion_oos_candidates_pre_registered",
            "factor_validation_branch_confirmed",
            "oos_2025_only_validation_plan_registered",
            "overlap_adjusted_statistics_plan_enabled",
            "cumulative_multiple_testing_gate_enabled",
            "cost_capacity_turnover_stress_enabled",
            "daily_vs_every2_every3_controls_enabled",
            "cost_capacity_gate_enabled",
            "final_holdout_not_touched",
        ],
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _branch_prefixes(config: dict[str, Any]) -> list[str]:
    prefixes = _list(config.get("recommended_branch_prefixes"))
    if prefixes:
        return prefixes
    return _list(config.get("recommended_branch_prefix"))
