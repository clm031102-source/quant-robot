from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "factor_mining_candidate_plan_gate"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
INACTIVE_DISCOVERY_STATUSES = {
    "blocked_by_coverage",
    "blocked_by_endpoint_availability",
}
REQUIRED_PROMOTION_POLICY_KEYS = (
    "requires_data_source_availability_proof",
    "requires_long_cycle_replay",
    "requires_same_parameter_full_sample",
    "requires_full_sample_regime_coverage",
    "requires_walk_forward",
    "requires_cost_capacity_gate",
    "requires_regime_coverage",
    "requires_no_lookahead_audit",
    "requires_future_function_static_audit",
    "requires_overfit_multiple_testing_control",
    "requires_overlap_adjusted_statistics",
    "requires_parameter_sensitivity",
    "requires_parameter_sensitivity_heatmap",
    "requires_deflated_sharpe_or_fdr",
    "requires_cpcv_or_purged_walk_forward",
    "requires_white_reality_check_or_multiple_test_adjustment",
    "requires_profit_drawdown_winrate_report",
    "requires_final_holdout_read_once",
    "requires_tradeability_survivorship_audit",
    "requires_industry_style_neutralization",
    "requires_source_performance_evidence",
)

DEFAULT_CONTROL_AREAS: list[dict[str, Any]] = [
    {
        "area_id": "cn_stock_tradeability",
        "title": "A-share real trading constraints",
        "required_controls": [
            "limit_up_down_filter",
            "suspension_filter",
            "st_flag_filter",
            "new_listing_age_filter",
            "delisting_risk_filter",
            "board_permission_filter",
        ],
    },
    {
        "area_id": "financial_pit_timing",
        "title": "Point-in-time financial availability",
        "required_controls": [
            "ann_date_or_effective_date_lag",
            "financial_revision_announcement_handling",
            "report_release_lag_not_period_end",
            "no_period_end_only_financial_signal",
        ],
    },
    {
        "area_id": "source_sample_integrity",
        "title": "Source, sample, leakage, and multiple-test integrity",
        "required_controls": [
            "endpoint_permission_or_cache_manifest",
            "point_in_time_available_date_semantics",
            "full_sample_2015_2025_same_parameter_replay",
            "train_test_or_walk_forward_split_declared",
            "future_function_static_audit",
            "rejected_hypothesis_counting",
        ],
    },
    {
        "area_id": "industry_style_neutralization",
        "title": "Industry and style exposure separation",
        "required_controls": [
            "industry_exposure_report",
            "size_exposure_report",
            "value_lowvol_momentum_liquidity_decomposition",
            "neutralized_or_residual_factor_matrix",
        ],
    },
    {
        "area_id": "etf_rotation_scope_boundary",
        "title": "ETF rotation evidence boundary",
        "required_controls": [
            "stock_scope_confirmed",
            "etf_rotation_evidence_rejected_for_stock_factor",
            "cn_etf_dedicated_signal_pack_separate",
        ],
    },
    {
        "area_id": "portfolio_construction",
        "title": "Portfolio construction beyond raw TopN",
        "required_controls": [
            "risk_budget_position_sizing",
            "volatility_targeting_or_volatility_budget",
            "industry_weight_constraints",
            "turnover_constraints",
            "stop_loss_or_de_risk_rules",
        ],
    },
    {
        "area_id": "strict_statistics",
        "title": "Strict statistical reality checks",
        "required_controls": [
            "deflated_sharpe",
            "purged_cpcv",
            "white_reality_check_or_fdr",
            "parameter_sensitivity_heatmap",
            "multiple_testing_accounting",
        ],
    },
    {
        "area_id": "china_market_regime",
        "title": "China market regime coverage",
        "required_controls": [
            "policy_liquidity_regime",
            "credit_cycle_proxy",
            "northbound_margin_turnover_temperature",
            "index_location_state",
            "signal_window_regime_coverage",
        ],
    },
    {
        "area_id": "event_factors",
        "title": "Event factor or event contamination controls",
        "required_controls": [
            "earnings_forecast_or_statement_event_audit",
            "dividend_ex_right_event_audit",
            "buyback_holder_unlock_event_audit",
            "index_rebalance_event_audit",
            "event_contamination_extreme_return_audit",
        ],
    },
]


def default_cn_stock_pre_mining_control_plan() -> dict[str, Any]:
    return {
        "declared_controls": {
            area["area_id"]: list(area["required_controls"])
            for area in DEFAULT_CONTROL_AREAS
        },
        "policy": (
            "Every new CN stock candidate family must declare these controls before factor generation. "
            "Declaration permits research screening only; promotion still requires implemented evidence."
        ),
    }


def default_cn_stock_promotion_policy() -> dict[str, bool]:
    return {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        **{key: True for key in REQUIRED_PROMOTION_POLICY_KEYS},
    }


def build_factor_mining_candidate_plan_gate(
    candidate_plan: dict[str, Any] | None,
    *,
    gate_stage: str = "discovery",
    quality_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = _dict(candidate_plan)
    stage = str(gate_stage or "discovery").lower()
    candidates = _list_of_dicts(plan.get("candidates"))
    declared_controls = _declared_controls(plan)
    family_rotation_policy = _family_rotation_policy(plan)
    area_rows = _control_area_rows(declared_controls)
    blockers = _blockers(
        plan,
        candidates=candidates,
        area_rows=area_rows,
        family_rotation_policy=family_rotation_policy,
        gate_stage=stage,
        quality_gate=quality_gate,
    )
    status = _status(blockers, gate_stage=stage)
    candidate_rows = _candidate_rows(candidates, gate_stage=stage)
    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "gate_stage": stage,
        "status": status,
        "source_plan_stage": str(plan.get("stage", "")),
        "summary": {
            "candidate_count": len(candidates),
            "active_candidate_count": sum(1 for row in candidate_rows if row["active_for_gate"]),
            "inactive_candidate_count": sum(1 for row in candidate_rows if not row["active_for_gate"]),
            "unique_candidate_names": len({str(candidate.get("factor_name", "")) for candidate in candidates}),
            "control_area_count": len(area_rows),
            "complete_control_area_count": sum(1 for row in area_rows if row["complete"]),
            "blocked_control_area_count": sum(1 for row in area_rows if not row["complete"]),
            "quality_gate_status": _dict(quality_gate).get("status", "not_provided"),
        },
        "required_promotion_policy_keys": list(REQUIRED_PROMOTION_POLICY_KEYS),
        "control_area_rows": area_rows,
        "candidate_rows": candidate_rows,
        "family_rotation_policy": family_rotation_policy,
        "decision": {
            "candidate_plan_gate_cleared": not blockers,
            "research_screen_allowed": not blockers,
            "portfolio_grid_allowed": (not blockers) and stage in {"portfolio", "promotion"},
            "promotion_allowed": (not blockers) and stage == "promotion",
            "blockers": blockers,
        },
        "promotion_policy": _dict(plan.get("promotion_policy")),
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    packet["markdown"] = render_factor_mining_candidate_plan_gate_markdown(packet)
    return packet


def write_factor_mining_candidate_plan_gate(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_packet = _sanitize(packet)
    (output_path / "factor_mining_candidate_plan_gate.json").write_text(
        json.dumps(clean_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_mining_candidate_plan_gate.md").write_text(
        render_factor_mining_candidate_plan_gate_markdown(clean_packet),
        encoding="utf-8",
    )


def validate_candidate_plan_gate_packet(
    packet_path: str | Path | None,
    *,
    require_generated_today: bool = True,
    context: str = "CN stock factor mining",
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a candidate plan gate packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a candidate plan gate packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} candidate plan gate packet must be generated today: {path}")
    decision = _dict(packet.get("decision"))
    if decision.get("candidate_plan_gate_cleared") is not True:
        raise ValueError(f"{context} candidate plan gate is not cleared: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} candidate plan gate violates live boundary: {path}")
    return packet


def render_factor_mining_candidate_plan_gate_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# Factor Mining Candidate Plan Gate",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Gate stage: {packet.get('gate_stage', '')}",
        f"- Status: {packet.get('status', '')}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Complete control areas: {summary.get('complete_control_area_count', 0)} / {summary.get('control_area_count', 0)}",
        f"- Research screen allowed: {decision.get('research_screen_allowed', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Promotion Policy",
            "",
            "| Requirement | Declared |",
            "|---|---:|",
        ]
    )
    promotion = _dict(packet.get("promotion_policy"))
    for key in _list(packet.get("required_promotion_policy_keys")):
        lines.append(f"| {key} | {promotion.get(key) is True} |")
    rotation = _dict(packet.get("family_rotation_policy"))
    lines.extend(
        [
            "",
            "## Family Rotation Policy",
            "",
            f"- Current family: `{rotation.get('current_family_id', '')}`",
            f"- Current family round count: {rotation.get('current_family_round_count', 0)}",
            f"- Max rounds before review: {rotation.get('max_rounds_before_review', 0)}",
            f"- Three-round review completed: {rotation.get('three_round_review_completed', False)}",
            f"- Hibernated families: {', '.join(_list(rotation.get('hibernated_families'))) or 'none'}",
            f"- Blocked families: {', '.join(_list(rotation.get('blocked_families'))) or 'none'}",
        ]
    )
    lines.extend(
        [
            "",
            "## Control Areas",
            "",
            "| Area | Complete | Missing controls |",
            "|---|---:|---|",
        ]
    )
    for row in _list_of_dicts(packet.get("control_area_rows")):
        lines.append(
            "| {area} | {complete} | {missing} |".format(
                area=row.get("area_id", ""),
                complete=row.get("complete", False),
                missing=", ".join(_list(row.get("missing_controls"))) or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Candidate Rows",
            "",
            "| Factor | Source | Market | Asset | Portfolio allowed | Promotion allowed |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    for row in _list_of_dicts(packet.get("candidate_rows")):
        lines.append(
            "| {factor} | {source} | {market} | {asset} | {portfolio} | {promotion} |".format(
                factor=row.get("factor_name", ""),
                source=row.get("hypothesis_source", ""),
                market=row.get("market", ""),
                asset=row.get("asset_type", ""),
                portfolio=row.get("portfolio_backtest_allowed", False),
                promotion=row.get("promotion_allowed", False),
            )
        )
    return "\n".join(lines) + "\n"


def _declared_controls(plan: dict[str, Any]) -> dict[str, set[str]]:
    control_plan = _dict(plan.get("research_control_plan"))
    declared = _dict(control_plan.get("declared_controls"))
    output: dict[str, set[str]] = {
        str(area_id): {str(item) for item in _list(items)}
        for area_id, items in declared.items()
    }
    # Backward-compatible inference for preregistration artifacts that already
    # state explicit next-gate metrics but do not yet carry research_control_plan.
    evaluation = _dict(plan.get("evaluation_gate"))
    metrics = {str(item) for item in _list(evaluation.get("required_metrics"))}
    if "limit_up_down_tradeability_audit" in metrics:
        output.setdefault("cn_stock_tradeability", set()).add("limit_up_down_filter")
    if "industry_neutral_ic" in metrics:
        output.setdefault("industry_style_neutralization", set()).add("industry_exposure_report")
    if "size_liquidity_neutral_ic" in metrics:
        output.setdefault("industry_style_neutralization", set()).add("neutralized_or_residual_factor_matrix")
    if evaluation.get("multiple_testing_accounting_required") is True:
        output.setdefault("strict_statistics", set()).add("multiple_testing_accounting")
    promotion = _dict(plan.get("promotion_policy"))
    if promotion.get("requires_cost_capacity_gate") is True:
        output.setdefault("portfolio_construction", set()).add("turnover_constraints")
    if promotion.get("requires_regime_coverage") is True:
        output.setdefault("china_market_regime", set()).add("signal_window_regime_coverage")
    return output


def _control_area_rows(declared_controls: dict[str, set[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for area in DEFAULT_CONTROL_AREAS:
        area_id = str(area["area_id"])
        required = [str(item) for item in area["required_controls"]]
        declared = sorted(declared_controls.get(area_id, set()))
        missing = [control for control in required if control not in set(declared)]
        rows.append(
            {
                "area_id": area_id,
                "title": str(area["title"]),
                "required_controls": required,
                "declared_controls": declared,
                "missing_controls": missing,
                "complete": not missing,
            }
        )
    return rows


def _family_rotation_policy(plan: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(plan.get("family_rotation_policy"))
    if not raw:
        return {
            "current_family_id": "",
            "current_family_round_count": 0,
            "max_rounds_before_review": 0,
            "three_round_review_completed": False,
            "hibernated_families": [],
            "blocked_families": [],
        }
    return {
        "current_family_id": str(raw.get("current_family_id", "")),
        "current_family_round_count": _int(raw.get("current_family_round_count"), default=0),
        "max_rounds_before_review": _int(raw.get("max_rounds_before_review"), default=0),
        "three_round_review_completed": bool(raw.get("three_round_review_completed")),
        "hibernated_families": sorted(_family_name_set(raw.get("hibernated_families"))),
        "blocked_families": sorted(_family_name_set(raw.get("blocked_families"))),
    }


def _blockers(
    plan: dict[str, Any],
    *,
    candidates: list[dict[str, Any]],
    area_rows: list[dict[str, Any]],
    family_rotation_policy: dict[str, Any],
    gate_stage: str,
    quality_gate: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    if not candidates:
        blockers.append("missing_candidates")
    active_candidates = [candidate for candidate in candidates if _active_for_gate(candidate, gate_stage=gate_stage)]
    if candidates and not active_candidates:
        blockers.append("missing_active_candidates")
    names = [str(candidate.get("factor_name", "")) for candidate in candidates]
    if len(names) != len(set(names)):
        blockers.append("duplicate_factor_names")
    for candidate in candidates:
        status = str(candidate.get("registration_status", ""))
        if str(candidate.get("market", "")).upper() != "CN":
            blockers.append("candidate_market_not_cn")
        if str(candidate.get("asset_type", "")).lower() != "stock":
            blockers.append("candidate_asset_type_not_stock")
        if status in INACTIVE_DISCOVERY_STATUSES and gate_stage == "discovery":
            if bool(candidate.get("portfolio_backtest_allowed")):
                blockers.append("inactive_candidate_portfolio_backtest_allowed")
            if bool(candidate.get("promotion_allowed")):
                blockers.append("inactive_candidate_promotion_allowed")
            continue
        if status not in {"pre_registered", "registered"}:
            blockers.append("candidate_not_pre_registered")
        if not str(candidate.get("hypothesis_source", "")).strip():
            blockers.append("candidate_missing_hypothesis_source")
        if not str(candidate.get("economic_rationale", "")).strip():
            blockers.append("candidate_missing_economic_rationale")
        if bool(candidate.get("portfolio_backtest_allowed")):
            blockers.append("candidate_portfolio_backtest_allowed_before_prescreen")
        if bool(candidate.get("promotion_allowed")):
            blockers.append("candidate_promotion_allowed_before_validation")
        family = str(candidate.get("family", "")).strip()
        if family in set(_list(family_rotation_policy.get("hibernated_families"))):
            blockers.append(f"candidate_family_hibernated:{family}")
        if family in set(_list(family_rotation_policy.get("blocked_families"))):
            blockers.append(f"candidate_family_blocked:{family}")
    for row in area_rows:
        if row["complete"]:
            continue
        area_id = str(row["area_id"])
        blockers.append(f"missing_control_area:{area_id}")
        blockers.append(f"missing_controls:{area_id}:{','.join(_list(row.get('missing_controls')))}")

    promotion = _dict(plan.get("promotion_policy"))
    if bool(promotion.get("promotion_allowed")):
        blockers.append("plan_promotion_allowed_before_validation")
    if bool(promotion.get("portfolio_backtest_allowed_before_prescreen")):
        blockers.append("plan_portfolio_backtest_allowed_before_prescreen")
    for key in REQUIRED_PROMOTION_POLICY_KEYS:
        if promotion and promotion.get(key) is not True:
            blockers.append(f"promotion_policy_missing:{key}")

    max_rounds = int(family_rotation_policy.get("max_rounds_before_review", 0) or 0)
    round_count = int(family_rotation_policy.get("current_family_round_count", 0) or 0)
    if max_rounds > 0 and round_count >= max_rounds and not family_rotation_policy.get("three_round_review_completed"):
        blockers.append("family_rotation_review_required_after_round_limit")

    if gate_stage == "promotion":
        quality_decision = _dict(_dict(quality_gate).get("decision"))
        if quality_decision.get("promotion_gate_cleared") is not True:
            blockers.append("quality_gate_not_promotion_ready")
    return _unique_preserving_order(blockers)


def _candidate_rows(candidates: list[dict[str, Any]], *, gate_stage: str) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": str(candidate.get("factor_name", "")),
            "family": str(candidate.get("family", "")),
            "hypothesis_source": str(candidate.get("hypothesis_source", "")),
            "market": str(candidate.get("market", "")),
            "asset_type": str(candidate.get("asset_type", "")),
            "registration_status": str(candidate.get("registration_status", "")),
            "active_for_gate": _active_for_gate(candidate, gate_stage=gate_stage),
            "portfolio_backtest_allowed": bool(candidate.get("portfolio_backtest_allowed")),
            "promotion_allowed": bool(candidate.get("promotion_allowed")),
        }
        for candidate in candidates
    ]


def _active_for_gate(candidate: dict[str, Any], *, gate_stage: str) -> bool:
    status = str(candidate.get("registration_status", ""))
    if status in {"pre_registered", "registered"}:
        return True
    return not (gate_stage == "discovery" and status in INACTIVE_DISCOVERY_STATUSES)


def _status(blockers: list[str], *, gate_stage: str) -> str:
    if blockers:
        return "blocked"
    if gate_stage == "promotion":
        return "promotion_ready"
    if gate_stage == "portfolio":
        return "portfolio_preflight_ready"
    return "research_ready"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, set):
        return [str(item) for item in sorted(value)]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _family_name_set(value: Any) -> set[str]:
    names: set[str] = set()
    items = value if isinstance(value, list) else ([] if value is None else [value])
    for item in items:
        if isinstance(item, dict):
            family = item.get("family", item.get("family_id", ""))
        else:
            family = item
        name = str(family).strip()
        if name:
            names.add(name)
    return names


def _int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
