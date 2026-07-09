from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from quant_robot.ops.cn_stock_local_source_queue_audit import SAFETY


STAGE = "cn_stock_non_lpr_orthogonal_source_gate"
ROUND738_STAGE = "lpr_macro_regime_walk_forward_rejection_rotation_gate"
READINESS_STAGE = "factor_batch_readiness_gate"
ANALYST_STAGE = "analyst_report_revision_prescreen"
ANALYST_STAGE_ALIASES = {"", ANALYST_STAGE, "analyst_report_revision_pit_prescreen"}
EXPECTED_ROTATION_DIRECTION = "rotate_to_non_lpr_orthogonal_family_source_gate"
SELECTED_SOURCE = "analyst_report_revision"
WAIT_FOR_ANALYST_QUOTA_NEXT_ACTION = "wait_for_report_rc_quota_reset_then_cache_next_analyst_month"
CACHE_NEXT_ANALYST_MONTH_NEXT_ACTION = "cache_next_analyst_month_then_rerun_frozen_local_prescreen"

SOURCE_ROW_COLUMNS = [
    "source_id",
    "selection_status",
    "provider_required",
    "provider_request_allowed",
    "local_cached_prescreen_allowed",
    "full_factor_batch_allowed",
    "research_lead_count",
    "year_coverage_pass_count",
    "multiple_testing_lead_count",
    "neutral_gate_pass_count",
    "latest_report_date",
    "next_action",
    "blocked_actions",
    "rationale",
]


def run_cn_stock_non_lpr_orthogonal_source_gate(
    *,
    round738_rotation_gate_path: str | Path,
    readiness_gate_path: str | Path,
    analyst_prescreen_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    rotation_gate = json.loads(Path(round738_rotation_gate_path).read_text(encoding="utf-8"))
    readiness_gate = json.loads(Path(readiness_gate_path).read_text(encoding="utf-8"))
    analyst_prescreen = json.loads(Path(analyst_prescreen_path).read_text(encoding="utf-8"))
    result = build_cn_stock_non_lpr_orthogonal_source_gate(
        round738_rotation_gate=rotation_gate,
        readiness_gate=readiness_gate,
        analyst_prescreen=analyst_prescreen,
        round738_rotation_gate_path=round738_rotation_gate_path,
        readiness_gate_path=readiness_gate_path,
        analyst_prescreen_path=analyst_prescreen_path,
    )
    write_cn_stock_non_lpr_orthogonal_source_gate(output_dir, result)
    return result


def build_cn_stock_non_lpr_orthogonal_source_gate(
    *,
    round738_rotation_gate: dict[str, Any],
    readiness_gate: dict[str, Any],
    analyst_prescreen: dict[str, Any],
    round738_rotation_gate_path: str | Path | None = None,
    readiness_gate_path: str | Path | None = None,
    analyst_prescreen_path: str | Path | None = None,
) -> dict[str, Any]:
    rotation_blockers = _rotation_blockers(round738_rotation_gate)
    source_gate_selected = not rotation_blockers
    selected_source = SELECTED_SOURCE if source_gate_selected else ""
    readiness_info = _readiness_info(readiness_gate)
    analyst_info = _analyst_info(analyst_prescreen)
    execution_blockers = _execution_blockers(
        source_gate_selected=source_gate_selected,
        readiness_info=readiness_info,
        analyst_info=analyst_info,
    )
    blockers = _unique([*rotation_blockers, *execution_blockers])
    source_gate_ready = source_gate_selected and not execution_blockers
    status = "ready" if source_gate_ready else "blocked"
    next_action = _next_action(
        source_gate_selected=source_gate_selected,
        provider_request_allowed=readiness_info["provider_request_allowed"],
        source_gate_ready=source_gate_ready,
    )
    source_rows = _source_rows(
        source_gate_selected=source_gate_selected,
        source_gate_ready=source_gate_ready,
        readiness_info=readiness_info,
        analyst_info=analyst_info,
        next_action=next_action,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "round738_rotation_gate_path": str(Path(round738_rotation_gate_path)) if round738_rotation_gate_path is not None else None,
        "readiness_gate_path": str(Path(readiness_gate_path)) if readiness_gate_path is not None else None,
        "analyst_prescreen_path": str(Path(analyst_prescreen_path)) if analyst_prescreen_path is not None else None,
        "summary": {
            "source_count": len(source_rows),
            "selected_source_count": 1 if selected_source else 0,
            "selected_source": selected_source,
            "analyst_candidate_count": analyst_info["candidate_count"],
            "analyst_multiple_testing_leads": analyst_info["multiple_testing_lead_count"],
            "analyst_neutral_gate_pass_count": analyst_info["neutral_gate_pass_count"],
            "analyst_year_coverage_pass_count": analyst_info["year_coverage_pass_count"],
            "analyst_research_lead_count": analyst_info["research_lead_count"],
            "latest_report_date": analyst_info["latest_report_date"],
            "next_action": next_action,
        },
        "decision": {
            "blockers": blockers,
            "selected_source": selected_source,
            "source_gate_selected": bool(source_gate_selected),
            "source_gate_ready": bool(source_gate_ready),
            "local_cached_prescreen_allowed": bool(readiness_info["local_cached_prescreen_allowed"]),
            "full_factor_batch_allowed": bool(readiness_info["full_factor_batch_allowed"]),
            "provider_request_allowed": bool(readiness_info["provider_request_allowed"]),
            "next_action": next_action,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "source_rows": source_rows,
        "holdout_policy": {
            "final_holdout_included": False,
            "final_holdout_use": "blocked_until_source_gate_and_later_walk_forward_clear",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "source_gate_not_ready",
                "walk_forward_not_run",
                "cost_capacity_regime_gate_not_run",
                "final_holdout_not_read",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_stock_non_lpr_orthogonal_source_gate_markdown(result)
    return result


def write_cn_stock_non_lpr_orthogonal_source_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "cn_stock_non_lpr_orthogonal_source_gate.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_stock_non_lpr_orthogonal_source_gate.md").write_text(
        render_cn_stock_non_lpr_orthogonal_source_gate_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_stock_non_lpr_orthogonal_source_rows.csv", clean["source_rows"], SOURCE_ROW_COLUMNS)


def render_cn_stock_non_lpr_orthogonal_source_gate_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    lines = [
        "# CN Stock Non-LPR Orthogonal Source Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Selected source: `{decision.get('selected_source', '')}`",
        f"- Source gate selected: {decision.get('source_gate_selected', False)}",
        f"- Source gate ready: {decision.get('source_gate_ready', False)}",
        f"- Local cached prescreen allowed: {decision.get('local_cached_prescreen_allowed', False)}",
        f"- Full factor batch allowed: {decision.get('full_factor_batch_allowed', False)}",
        f"- Provider request allowed: {decision.get('provider_request_allowed', False)}",
        f"- Analyst research leads: {summary.get('analyst_research_lead_count', 0)}",
        f"- Analyst year-coverage passes: {summary.get('analyst_year_coverage_pass_count', 0)}",
        f"- Latest report date: {summary.get('latest_report_date', '')}",
        f"- Next action: `{decision.get('next_action', '')}`",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Source Rows",
        "",
        "| Source | Status | Provider | Provider Allowed | Local Prescreen | Full Batch | Research Leads | Year Passes | Next Action |",
        "|---|---|---|---|---|---|---:|---:|---|",
    ]
    for row in result.get("source_rows", []):
        lines.append(
            "| {source} | {status} | {provider} | {provider_allowed} | {local} | {full} | {leads} | {years} | {next_action} |".format(
                source=row.get("source_id", ""),
                status=row.get("selection_status", ""),
                provider=row.get("provider_required", False),
                provider_allowed=row.get("provider_request_allowed", False),
                local=row.get("local_cached_prescreen_allowed", False),
                full=row.get("full_factor_batch_allowed", False),
                leads=int(_number(row.get("research_lead_count"))),
                years=int(_number(row.get("year_coverage_pass_count"))),
                next_action=row.get("next_action", ""),
            )
        )
    lines.extend(["", "## Blockers", ""])
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Round738 closed the failed LPR gap-widening retry path.",
            "- Analyst-report revision is the selected non-LPR PIT source, but only as a blocked source-extension path until quota and year coverage improve.",
            "- Local cached prescreen permission is not full factor-batch readiness and does not permit portfolio grids, promotion, paper signals, or live use.",
        ]
    )
    return "\n".join(lines) + "\n"


def _rotation_blockers(rotation_gate: dict[str, Any]) -> list[str]:
    decision = _dict(rotation_gate.get("decision"))
    policy = _dict(rotation_gate.get("rotation_policy"))
    blockers: list[str] = []
    if rotation_gate.get("stage") != ROUND738_STAGE:
        blockers.append("unexpected_round738_rotation_stage")
    if rotation_gate.get("status") != "cleared":
        blockers.append("round738_rotation_gate_not_cleared")
    if decision.get("rotation_source_gate_allowed_next") is not True:
        blockers.append("round738_rotation_source_gate_not_allowed")
    if policy.get("next_direction") != EXPECTED_ROTATION_DIRECTION:
        blockers.append("round738_not_pointing_to_non_lpr_source_gate")
    if decision.get("same_lpr_candidate_retry_allowed") is not False:
        blockers.append("same_lpr_candidate_retry_not_closed")
    if policy.get("rerun_same_lpr_gap_widening_candidates_allowed") is not False:
        blockers.append("lpr_gap_widening_rerun_not_closed")
    return _unique(blockers)


def _readiness_info(readiness_gate: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(readiness_gate.get("decision"))
    source_queue = _dict(readiness_gate.get("source_queue_decision"))
    candidate_gate = _dict(readiness_gate.get("candidate_plan_gate_decision"))
    quota = _dict(readiness_gate.get("provider_quota_preflight_decision"))
    provider_allowed = quota.get("request_allowed") is True or source_queue.get("provider_request_allowed") is True
    local_prescreen = source_queue.get("local_prescreen_allowed") is True and candidate_gate.get("local_prescreen_allowed") is True
    full_batch = decision.get("factor_batch_ready") is True
    return {
        "stage": readiness_gate.get("stage"),
        "provider_request_allowed": bool(provider_allowed),
        "local_cached_prescreen_allowed": bool(local_prescreen),
        "full_factor_batch_allowed": bool(full_batch),
        "quota_blockers": _as_list(quota.get("blockers")),
        "decision_blockers": _as_list(decision.get("blockers")),
        "source_next_action": source_queue.get("next_action", ""),
        "local_prescreen_next_action": source_queue.get("local_prescreen_next_action", ""),
    }


def _analyst_info(analyst_prescreen: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(analyst_prescreen.get("summary"))
    data_window = _dict(analyst_prescreen.get("data_window"))
    return {
        "stage": str(analyst_prescreen.get("stage", "") or ""),
        "candidate_count": int(_number(summary.get("candidate_count"))),
        "multiple_testing_lead_count": int(_number(summary.get("multiple_testing_lead_count"))),
        "neutral_gate_pass_count": int(_number(summary.get("neutral_gate_pass_count"))),
        "year_coverage_pass_count": int(_number(summary.get("year_coverage_pass_count"))),
        "research_lead_count": int(_number(summary.get("research_lead_count"))),
        "promotion_allowed_candidates": int(_number(summary.get("promotion_allowed_candidates"))),
        "latest_report_date": str(data_window.get("max_report_date", "")),
        "report_rows": int(_number(data_window.get("report_rows"))),
        "report_assets": int(_number(data_window.get("report_assets"))),
    }


def _execution_blockers(
    *,
    source_gate_selected: bool,
    readiness_info: dict[str, Any],
    analyst_info: dict[str, Any],
) -> list[str]:
    if not source_gate_selected:
        return []
    blockers: list[str] = []
    if readiness_info["stage"] != READINESS_STAGE:
        blockers.append("unexpected_readiness_gate_stage")
    if analyst_info["stage"] not in ANALYST_STAGE_ALIASES:
        blockers.append("unexpected_analyst_prescreen_stage")
    if not readiness_info["local_cached_prescreen_allowed"]:
        blockers.append("analyst_local_cached_prescreen_not_allowed")
    if not readiness_info["provider_request_allowed"]:
        blockers.append("provider_quota_preflight_blocked")
    if not readiness_info["full_factor_batch_allowed"]:
        blockers.append("full_factor_batch_readiness_blocked")
    if analyst_info["year_coverage_pass_count"] <= 0:
        blockers.append("analyst_year_coverage_below_gate")
    if analyst_info["research_lead_count"] <= 0:
        blockers.append("analyst_research_lead_count_zero")
    if analyst_info["promotion_allowed_candidates"] > 0:
        blockers.append("analyst_promotion_unexpectedly_allowed")
    return _unique(blockers)


def _next_action(*, source_gate_selected: bool, provider_request_allowed: bool, source_gate_ready: bool) -> str:
    if not source_gate_selected:
        return "blocked_until_round738_rotation_gate_clears"
    if source_gate_ready:
        return "run_full_factor_batch_readiness_before_any_fresh_prescreen"
    if not provider_request_allowed:
        return WAIT_FOR_ANALYST_QUOTA_NEXT_ACTION
    return CACHE_NEXT_ANALYST_MONTH_NEXT_ACTION


def _source_rows(
    *,
    source_gate_selected: bool,
    source_gate_ready: bool,
    readiness_info: dict[str, Any],
    analyst_info: dict[str, Any],
    next_action: str,
) -> list[dict[str, Any]]:
    if not source_gate_selected:
        analyst_status = "not_selected_rotation_blocked"
    elif source_gate_ready:
        analyst_status = "selected_ready_for_full_source_gate"
    else:
        analyst_status = "selected_blocked_waiting_for_quota_and_year_coverage"
    return [
        {
            "source_id": SELECTED_SOURCE,
            "selection_status": analyst_status,
            "provider_required": True,
            "provider_request_allowed": readiness_info["provider_request_allowed"],
            "local_cached_prescreen_allowed": readiness_info["local_cached_prescreen_allowed"],
            "full_factor_batch_allowed": readiness_info["full_factor_batch_allowed"],
            "research_lead_count": analyst_info["research_lead_count"],
            "year_coverage_pass_count": analyst_info["year_coverage_pass_count"],
            "multiple_testing_lead_count": analyst_info["multiple_testing_lead_count"],
            "neutral_gate_pass_count": analyst_info["neutral_gate_pass_count"],
            "latest_report_date": analyst_info["latest_report_date"],
            "next_action": next_action,
            "blocked_actions": [
                "portfolio_grid_before_year_coverage_and_walk_forward",
                "promotion_before_cost_capacity_regime_final_holdout",
                "provider_request_when_quota_preflight_blocks",
            ],
            "rationale": "Only active non-LPR PIT source after local queue closeout, but Jan-Jun evidence has zero research leads and one IC year.",
        },
        {
            "source_id": "lpr_gap_widening_residual",
            "selection_status": "closed_by_round738_rejection",
            "provider_required": False,
            "provider_request_allowed": False,
            "local_cached_prescreen_allowed": False,
            "full_factor_batch_allowed": False,
            "research_lead_count": 0,
            "year_coverage_pass_count": 0,
            "multiple_testing_lead_count": 0,
            "neutral_gate_pass_count": 0,
            "latest_report_date": "",
            "next_action": "do_not_rerun_without_new_lpr_macro_interaction_source_gate",
            "blocked_actions": [
                "same_lpr_candidate_retry",
                "cost_threshold_relaxation",
                "fold_threshold_relaxation",
            ],
            "rationale": "Round737 rejected both frozen candidates and Round738 forbids same-path rescue.",
        },
        {
            "source_id": "local_no_provider_closed_queue",
            "selection_status": "closed_or_hibernated_by_round703_queue",
            "provider_required": False,
            "provider_request_allowed": False,
            "local_cached_prescreen_allowed": False,
            "full_factor_batch_allowed": False,
            "research_lead_count": 0,
            "year_coverage_pass_count": 0,
            "multiple_testing_lead_count": 0,
            "neutral_gate_pass_count": 0,
            "latest_report_date": "",
            "next_action": "no_no_provider_factor_batch_from_closed_local_queue",
            "blocked_actions": [
                "public_technical_reentry_without_new_mechanism",
                "daily_basic_direct_grid",
                "moneyflow_direct_stock_selection",
            ],
            "rationale": "Round703/Round704 found no fresh no-provider local source ready for factor batch.",
        },
    ]


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    return [value]


def _unique(values: Iterable[object]) -> list:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _number(value: object) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in columns})


def _csv_value(value: object) -> object:
    if isinstance(value, (list, tuple, set)):
        return ";".join(str(item) for item in value)
    return value


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
