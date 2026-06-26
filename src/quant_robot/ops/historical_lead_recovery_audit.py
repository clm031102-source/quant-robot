from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable


STAGE = "historical_lead_recovery_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_DIRECTION_AFTER_ZERO_RECOVERY = (
    "round264_rotate_to_accessible_public_tradeable_indicator_family_with_regime_and_portfolio_gates"
)

SOFT_NEXT_GATE_BLOCKERS = {
    "costed_conversion_is_not_walk_forward",
    "final_holdout_not_read",
    "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
    "regime_coverage_not_yet_verified",
}

CSV_COLUMNS = [
    "rank",
    "factor_name",
    "source_round",
    "source_family",
    "source_stage",
    "evidence_type",
    "horizon",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "total_return",
    "annualized_return",
    "sharpe",
    "overlap_adjusted_sharpe",
    "newey_west_t_stat",
    "max_drawdown",
    "win_rate",
    "hard_blocked",
    "recovery_candidate",
    "promotion_allowed",
    "failure_class",
    "twenty_fifteen_risk",
    "blockers",
    "source_report",
]


def build_historical_lead_recovery_audit(
    *,
    turnover_conversion: dict[str, Any] | None = None,
    market_residual_dedup: dict[str, Any] | None = None,
    public_alpha101_dedup: dict[str, Any] | None = None,
    public_reference_replay: dict[str, Any] | None = None,
    source_reports: dict[str, str | Path] | None = None,
    user_drawdown_soft_floor: float = -0.30,
    public_reference_specs: Iterable[tuple[str, int, str, str]] | None = None,
) -> dict[str, Any]:
    reports = {key: str(value) for key, value in (source_reports or {}).items()}
    candidate_rows: list[dict[str, Any]] = []
    if turnover_conversion:
        candidate_rows.append(
            _turnover_conversion_row(
                turnover_conversion,
                source_round="round126",
                source_report=reports.get("turnover_conversion", ""),
                user_drawdown_soft_floor=user_drawdown_soft_floor,
            )
        )
    if market_residual_dedup:
        candidate_rows.append(
            _dedup_row(
                market_residual_dedup,
                source_round="round112",
                source_family="market_residual_public_technical",
                evidence_type="exposure_redundancy_stability_dedup",
                source_report=reports.get("market_residual_dedup", ""),
            )
        )
    if public_alpha101_dedup:
        candidate_rows.append(
            _dedup_row(
                public_alpha101_dedup,
                source_round="round116",
                source_family="qlib_alpha158_public_reference",
                evidence_type="exposure_redundancy_stability_dedup",
                source_report=reports.get("public_alpha101_dedup", ""),
            )
        )
    if public_reference_replay:
        for factor_name, horizon, source_round, source_family in public_reference_specs or _default_public_reference_specs():
            row = _public_reference_replay_row(
                public_reference_replay,
                factor_name=factor_name,
                preferred_horizon=horizon,
                source_round=source_round,
                source_family=source_family,
                source_report=reports.get("public_reference_replay", ""),
            )
            if row:
                candidate_rows.append(row)

    candidate_rows = [_finalize_row(row) for row in candidate_rows]
    candidate_rows.sort(key=_row_sort_key)
    for index, row in enumerate(candidate_rows, start=1):
        row["rank"] = index

    recovery_count = sum(1 for row in candidate_rows if row.get("recovery_candidate"))
    promotion_count = sum(1 for row in candidate_rows if row.get("promotion_allowed"))
    hard_blocked_count = sum(1 for row in candidate_rows if row.get("hard_blocked"))
    summary = {
        "candidate_count": len(candidate_rows),
        "recovery_candidate_count": recovery_count,
        "promotion_allowed_candidates": promotion_count,
        "hard_blocked_candidates": hard_blocked_count,
        "portfolio_conversion_failed_candidates": _count_failure(candidate_rows, "portfolio_conversion_failure"),
        "redundancy_or_exposure_blocked_candidates": _count_failure(candidate_rows, "redundancy_or_exposure"),
        "quantile_shape_blocked_candidates": _count_failure(candidate_rows, "quantile_shape_failure"),
        "twenty_fifteen_risk_candidates": sum(1 for row in candidate_rows if row.get("twenty_fifteen_risk")),
        "best_total_return": _max_numeric(candidate_rows, "total_return"),
        "best_overlap_adjusted_sharpe": _max_numeric(candidate_rows, "overlap_adjusted_sharpe"),
        "user_drawdown_soft_floor": user_drawdown_soft_floor,
    }
    status = "historical_leads_rejected_rotate_family" if recovery_count == 0 else "historical_leads_need_walk_forward_recovery"
    payload: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": summary,
        "candidate_rows": candidate_rows,
        "round126_failure_analysis": _round126_failure_analysis(candidate_rows, user_drawdown_soft_floor),
        "twenty_fifteen_redundancy_risk": _twenty_fifteen_redundancy_risk(candidate_rows),
        "decision": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": recovery_count > 0,
            "family_rotation_required": recovery_count == 0,
            "next_direction": (
                "walk_forward_recovery_for_nonblocked_historical_leads"
                if recovery_count
                else NEXT_DIRECTION_AFTER_ZERO_RECOVERY
            ),
            "blocked_reentry_families": _blocked_reentry_families(candidate_rows),
            "required_before_next_mining": [
                "use_accessible_pit_safe_long_cycle_source",
                "pre_register_public_indicator_family_before_factor_generation",
                "separate_ic_shape_gate_from_portfolio_gate",
                "report_2015_regime_contribution_and_reference_overlap",
                "do_not_claim_total_return_without_overlap_sharpe_drawdown_capacity_extreme_trade_gates",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    payload["markdown"] = render_historical_lead_recovery_audit_markdown(payload)
    return payload


def write_historical_lead_recovery_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(audit)
    (output_path / "historical_lead_recovery_audit.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "historical_lead_recovery_audit.md").write_text(
        render_historical_lead_recovery_audit_markdown(clean),
        encoding="utf-8",
    )
    with (output_path / "historical_lead_recovery_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in clean.get("candidate_rows", []) or []:
            writer.writerow({column: _csv_value(row.get(column, "")) for column in CSV_COLUMNS})


def render_historical_lead_recovery_audit_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    decision = _dict(audit.get("decision"))
    lines = [
        "# Historical Lead Recovery Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Status: {audit.get('status', 'unknown')}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Recovery candidates: {summary.get('recovery_candidate_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Hard-blocked candidates: {summary.get('hard_blocked_candidates', 0)}",
        f"- Portfolio conversion failures: {summary.get('portfolio_conversion_failed_candidates', 0)}",
        f"- Redundancy/exposure blocked: {summary.get('redundancy_or_exposure_blocked_candidates', 0)}",
        f"- Quantile-shape blocked: {summary.get('quantile_shape_blocked_candidates', 0)}",
        f"- 2015 risk candidates: {summary.get('twenty_fifteen_risk_candidates', 0)}",
        f"- User drawdown soft floor: {summary.get('user_drawdown_soft_floor', '')}",
        f"- Next direction: {decision.get('next_direction', '')}",
        f"- Live boundary allowed: {audit.get('live_boundary_allowed', False)}",
        "",
        "## Candidate Rows",
        "",
        "| Rank | Factor | Round | Evidence | IC | ICIR | Q spread | Total return | Overlap Sharpe | Max DD | Recovery | Failure class |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in audit.get("candidate_rows", []) or []:
        lines.append(
            "| {rank} | {factor} | {round_id} | {evidence} | {ic} | {icir} | {spread} | {total} | {overlap} | {dd} | {recovery} | {failure} |".format(
                rank=row.get("rank", ""),
                factor=_table_text(row.get("factor_name", "")),
                round_id=row.get("source_round", ""),
                evidence=_table_text(row.get("evidence_type", "")),
                ic=_fmt(row.get("mean_spearman_ic")),
                icir=_fmt(row.get("icir")),
                spread=_fmt(row.get("quantile_spread")),
                total=_fmt(row.get("total_return")),
                overlap=_fmt(row.get("overlap_adjusted_sharpe")),
                dd=_fmt(row.get("max_drawdown")),
                recovery=row.get("recovery_candidate", False),
                failure=_table_text(row.get("failure_class", "")),
            )
        )
    lines.extend(
        [
            "",
            "## Round126 Failure Analysis",
            "",
        ]
    )
    for note in _list(_dict(audit.get("round126_failure_analysis")).get("notes")):
        lines.append(f"- {note}")
    lines.extend(["", "## 2015 Redundancy Risk", ""])
    for note in _list(_dict(audit.get("twenty_fifteen_redundancy_risk")).get("notes")):
        lines.append(f"- {note}")
    lines.extend(["", "## Required Before Next Mining", ""])
    for item in _list(decision.get("required_before_next_mining")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _turnover_conversion_row(
    packet: dict[str, Any],
    *,
    source_round: str,
    source_report: str,
    user_drawdown_soft_floor: float,
) -> dict[str, Any]:
    best = _best_by_numeric(_list_of_dicts(packet.get("leaderboard")), "total_return")
    summary = _dict(packet.get("summary"))
    promotion = _dict(packet.get("promotion_policy"))
    blockers = _merge_blockers(best.get("blockers"), promotion.get("blockers"))
    if _int(summary.get("walk_forward_allowed_candidates")) <= 0:
        blockers.append("zero_walk_forward_allowed_candidates")
    max_drawdown = _float(best.get("max_drawdown"))
    if max_drawdown is not None and max_drawdown < user_drawdown_soft_floor:
        blockers.append("max_drawdown_below_user_soft_floor")
    if _float(best.get("extreme_trade_return_rate"), 0.0) > 0.0:
        blockers.append("extreme_trade_return_present")
    return {
        "factor_name": str(best.get("factor_name") or _first(_list(summary.get("factor_names"))) or "unknown"),
        "source_round": source_round,
        "source_family": "daily_basic_low_turnover_repair",
        "source_stage": str(packet.get("stage", "")),
        "evidence_type": "costed_portfolio_conversion",
        "horizon": best.get("holding_period", ""),
        "total_return": _float(best.get("total_return")),
        "annualized_return": _float(best.get("annualized_return")),
        "sharpe": _float(best.get("sharpe")),
        "overlap_adjusted_sharpe": _float(best.get("overlap_autocorr_adjusted_sharpe")),
        "newey_west_t_stat": _float(best.get("overlap_newey_west_t_stat_mean")),
        "max_drawdown": max_drawdown,
        "win_rate": _float(best.get("win_rate")),
        "hard_blocked": _bool(best.get("hard_blocked")) or bool(_hard_recovery_blockers(blockers)),
        "promotion_allowed": _bool(promotion.get("promotion_allowed")),
        "blockers": _unique(blockers),
        "source_report": source_report,
        "diagnostics": {
            "calendar_limited_trades": _int(best.get("calendar_limited_trades")),
            "capacity_limited_trades": _int(best.get("capacity_limited_trades")),
            "extreme_trade_return_rate": _float(best.get("extreme_trade_return_rate")),
            "max_abs_trade_gross_return": _float(best.get("max_abs_trade_gross_return")),
        },
    }


def _dedup_row(
    packet: dict[str, Any],
    *,
    source_round: str,
    source_family: str,
    evidence_type: str,
    source_report: str,
) -> dict[str, Any]:
    summary = _dict(packet.get("summary"))
    gate = _dict(packet.get("gate"))
    promotion = _dict(packet.get("promotion_policy"))
    lead_ic = _dict(packet.get("lead_ic_summary"))
    yearly = _list_of_dicts(packet.get("yearly_ic"))
    year_2015 = next((row for row in yearly if _int(row.get("year")) == 2015), {})
    blockers = _merge_blockers(gate.get("blockers"))
    if _bool(year_2015.get("failure")) and "twenty_fifteen_regime_failure_unexplained" not in blockers:
        blockers.append("twenty_fifteen_regime_failure_unexplained")
    return {
        "factor_name": str(packet.get("lead_factor_name", "unknown")),
        "source_round": source_round,
        "source_family": source_family,
        "source_stage": str(packet.get("stage", "")),
        "evidence_type": evidence_type,
        "horizon": packet.get("horizon", ""),
        "mean_spearman_ic": _float(lead_ic.get("mean_spearman_ic")),
        "icir": _float(lead_ic.get("icir")),
        "ic_t_stat": _float(lead_ic.get("ic_t_stat")),
        "ic_positive_rate": _float(lead_ic.get("positive_ic_rate")),
        "hard_blocked": bool(_hard_recovery_blockers(blockers)),
        "promotion_allowed": _bool(promotion.get("promotion_allowed")),
        "blockers": _unique(blockers),
        "source_report": source_report,
        "diagnostics": {
            "exposure_high_count": _int(summary.get("exposure_high_count")),
            "reference_highly_redundant_count": _int(summary.get("reference_highly_redundant_count")),
            "yearly_failure_count": _int(summary.get("yearly_failure_count")),
            "monthly_failure_count": _int(summary.get("monthly_failure_count")),
            "year_2015_mean_ic": _float(year_2015.get("mean_spearman_ic")),
            "year_2015_positive_ic_rate": _float(year_2015.get("positive_ic_rate")),
            "max_reference_correlation": _max_numeric(_list_of_dicts(packet.get("reference_correlations")), "max_abs_correlation"),
            "max_exposure_correlation": _max_numeric(_list_of_dicts(packet.get("exposure_correlations")), "max_abs_correlation"),
        },
    }


def _public_reference_replay_row(
    packet: dict[str, Any],
    *,
    factor_name: str,
    preferred_horizon: int,
    source_round: str,
    source_family: str,
    source_report: str,
) -> dict[str, Any] | None:
    rows = [row for row in _list_of_dicts(packet.get("results")) if str(row.get("factor_name")) == factor_name]
    if not rows:
        return None
    exact = [row for row in rows if _int(row.get("horizon")) == preferred_horizon]
    row = exact[0] if exact else _best_by_numeric(rows, "icir")
    blockers = _merge_blockers(row.get("blockers"))
    return {
        "factor_name": factor_name,
        "source_round": source_round,
        "source_family": source_family,
        "source_stage": str(packet.get("stage", "")),
        "evidence_type": "public_reference_full_sample_ic_shape_replay",
        "horizon": row.get("horizon", ""),
        "mean_spearman_ic": _float(row.get("mean_spearman_ic")),
        "icir": _float(row.get("icir")),
        "ic_t_stat": _float(row.get("ic_t_stat")),
        "ic_positive_rate": _float(row.get("ic_positive_rate")),
        "quantile_spread": _float(row.get("quantile_spread")),
        "quantile_monotonicity": _float(row.get("quantile_monotonicity")),
        "hard_blocked": bool(_hard_recovery_blockers(blockers)),
        "promotion_allowed": _bool(row.get("promotion_allowed")),
        "blockers": _unique(blockers),
        "source_report": source_report,
        "diagnostics": {
            "fdr_significant": _bool(row.get("fdr_significant")),
            "research_lead": _bool(row.get("research_lead")),
            "unique_dates": _int(row.get("unique_dates")),
            "unique_assets": _int(row.get("unique_assets")),
            "avg_top_quantile_turnover": _float(row.get("avg_top_quantile_turnover")),
            "median_amount": _float(row.get("median_amount")),
        },
    }


def _finalize_row(row: dict[str, Any]) -> dict[str, Any]:
    blockers = _merge_blockers(row.get("blockers"))
    hard_blockers = _hard_recovery_blockers(blockers)
    row["blockers"] = _unique(blockers)
    row["hard_blocked"] = bool(row.get("hard_blocked")) or bool(hard_blockers)
    row["recovery_candidate"] = not bool(row["hard_blocked"]) and not hard_blockers
    row["twenty_fifteen_risk"] = _has_twenty_fifteen_risk(row)
    row["failure_class"] = ";".join(_failure_classes(row, hard_blockers))
    return row


def _failure_classes(row: dict[str, Any], hard_blockers: list[str]) -> list[str]:
    blockers = set(hard_blockers)
    classes: list[str] = []
    if any(
        item in blockers
        for item in (
            "overlap_adjusted_sharpe_below_min",
            "calendar_holding_gate_filtered_trades",
            "extreme_trade_return_present",
            "max_drawdown_below_user_floor",
            "max_drawdown_below_user_soft_floor",
            "zero_walk_forward_allowed_candidates",
        )
    ):
        classes.append("portfolio_conversion_failure")
    if any("redundant" in item or "exposure" in item for item in blockers):
        classes.append("redundancy_or_exposure")
    if any("twenty_fifteen" in item or "yearly_ic_instability" in item for item in blockers):
        classes.append("twenty_fifteen_or_yearly_instability")
    if any("quantile" in item or "monotonicity" in item for item in blockers):
        classes.append("quantile_shape_failure")
    if any("icir_below" in item for item in blockers):
        classes.append("weak_statistical_strength")
    if not classes and _merge_blockers(row.get("blockers")):
        classes.append("next_gate_only")
    if not classes:
        classes.append("clean_recovery_candidate")
    return _unique(classes)


def _round126_failure_analysis(candidate_rows: list[dict[str, Any]], user_drawdown_soft_floor: float) -> dict[str, Any]:
    row = next((item for item in candidate_rows if item.get("source_round") == "round126"), {})
    if not row:
        return {"notes": ["Round126 evidence was not provided."]}
    diagnostics = _dict(row.get("diagnostics"))
    notes = [
        (
            "Round126 failed because total return did not survive the implementation gates: "
            f"overlap Sharpe={_fmt(row.get('overlap_adjusted_sharpe'))}, "
            f"Newey-West t={_fmt(row.get('newey_west_t_stat'))}, "
            f"max drawdown={_fmt(row.get('max_drawdown'))}, "
            f"extreme trade rate={_fmt(diagnostics.get('extreme_trade_return_rate'))}."
        ),
        (
            "The user's 30% drawdown tolerance still does not rescue the candidate: "
            f"the best row drawdown is {_fmt(row.get('max_drawdown'))}, below the soft floor {user_drawdown_soft_floor}."
        ),
        (
            "Extreme single-trade evidence is a hard data-quality and tradability warning: "
            f"max absolute gross trade return={_fmt(diagnostics.get('max_abs_trade_gross_return'))}, "
            f"calendar-limited trades={diagnostics.get('calendar_limited_trades', 0)}."
        ),
        "Round126 is therefore a costed conversion failure, not a profitable factor awaiting promotion.",
    ]
    return {"factor_name": row.get("factor_name", ""), "notes": notes}


def _twenty_fifteen_redundancy_risk(candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    notes = [
        "2015 is not just one bad year; it is a regime-overlap diagnostic for crash/rebound, suspension, liquidity segmentation, small-cap crowding, and low-turnover effects.",
        "A factor that wins by the same 2015 engine can look independent in full-sample averages while being redundant with low-volatility, reversal, liquidity, or low-turnover clusters.",
        "Future recovery work must report yearly contribution, 2015-specific IC/returns, reference overlap, and style exposure before any portfolio grid.",
    ]
    for row in candidate_rows:
        diagnostics = _dict(row.get("diagnostics"))
        if row.get("twenty_fifteen_risk"):
            notes.append(
                "{factor} carries 2015/redundancy risk: year_2015_mean_ic={year_ic}, "
                "max_reference_corr={ref_corr}, max_exposure_corr={exp_corr}.".format(
                    factor=row.get("factor_name", ""),
                    year_ic=_fmt(diagnostics.get("year_2015_mean_ic")),
                    ref_corr=_fmt(diagnostics.get("max_reference_correlation")),
                    exp_corr=_fmt(diagnostics.get("max_exposure_correlation")),
                )
            )
    return {"notes": notes}


def _blocked_reentry_families(candidate_rows: list[dict[str, Any]]) -> list[str]:
    families: list[str] = []
    for row in candidate_rows:
        if row.get("recovery_candidate"):
            continue
        family = str(row.get("source_family", ""))
        if family:
            families.append(family)
    return _unique(families)


def _has_twenty_fifteen_risk(row: dict[str, Any]) -> bool:
    blockers = _merge_blockers(row.get("blockers"))
    diagnostics = _dict(row.get("diagnostics"))
    if any("twenty_fifteen" in blocker for blocker in blockers):
        return True
    year_ic = _float(diagnostics.get("year_2015_mean_ic"))
    return year_ic is not None and year_ic < 0.0 and _int(diagnostics.get("yearly_failure_count")) > 0


def _hard_recovery_blockers(blockers: Iterable[str]) -> list[str]:
    return [blocker for blocker in _unique([str(item) for item in blockers if str(item)]) if blocker not in SOFT_NEXT_GATE_BLOCKERS]


def _default_public_reference_specs() -> list[tuple[str, int, str, str]]:
    return [
        ("alpha101_rank_pv_reversal_liquid_20", 20, "round252", "public_formula_alpha101"),
        ("main_force_divergence_reversal_5_20", 5, "round252", "smart_money_flow_public_reference"),
    ]


def _row_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    return (
        0 if row.get("recovery_candidate") else 1,
        -(_float(row.get("total_return"), _float(row.get("mean_spearman_ic"), 0.0)) or 0.0),
        str(row.get("factor_name", "")),
    )


def _count_failure(rows: list[dict[str, Any]], failure_class: str) -> int:
    return sum(1 for row in rows if failure_class in str(row.get("failure_class", "")).split(";"))


def _best_by_numeric(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: _float(row.get(key), float("-inf")) or float("-inf"))


def _max_numeric(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _merge_blockers(*values: Any) -> list[str]:
    blockers: list[str] = []
    for value in values:
        if isinstance(value, str):
            pieces = [piece.strip() for piece in value.replace(",", ";").split(";")]
            blockers.extend(piece for piece in pieces if piece)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                blockers.extend(_merge_blockers(item))
        elif value:
            blockers.append(str(value))
    return _unique(blockers)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _first(items: list[str]) -> str:
    return items[0] if items else ""


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _fmt(value: Any) -> str:
    numeric = _float(value)
    if numeric is None:
        return ""
    return f"{numeric:.4f}"


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
