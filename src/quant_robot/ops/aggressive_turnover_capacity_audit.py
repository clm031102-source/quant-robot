from __future__ import annotations

import ast
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "aggressive_turnover_capacity_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_aggressive_turnover_capacity_audit(
    rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    source_report: str | None = None,
    target_factors: list[str] | None = None,
    repair_suffix: str = "_large_mv",
    user_max_drawdown_tolerance: float = 0.30,
    max_participation_rate: float = 0.01,
    min_raw_total_return: float = 1.0,
    min_raw_sharpe: float = 1.0,
    min_raw_overlap_sharpe: float = 0.7,
    min_repair_overlap_sharpe: float = 0.7,
    min_repair_relative_return: float = 0.0,
) -> dict[str, Any]:
    frame = _frame(rows)
    records = frame.to_dict(orient="records")
    factors = target_factors or _infer_target_factors(records, repair_suffix=repair_suffix)
    pair_audits = [
        _audit_pair(
            factor_name,
            raw_row=_best_row(_rows_for_factor(records, factor_name)),
            repair_row=_best_row(_rows_for_factor(records, f"{factor_name}{repair_suffix}")),
            repair_factor_name=f"{factor_name}{repair_suffix}",
            source_report=source_report,
            user_max_drawdown_tolerance=user_max_drawdown_tolerance,
            max_participation_rate=max_participation_rate,
            min_raw_total_return=min_raw_total_return,
            min_raw_sharpe=min_raw_sharpe,
            min_raw_overlap_sharpe=min_raw_overlap_sharpe,
            min_repair_overlap_sharpe=min_repair_overlap_sharpe,
            min_repair_relative_return=min_repair_relative_return,
        )
        for factor_name in factors
    ]
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "risk_profile": "aggressive_drawdown_tolerant_capacity_strict",
        "thresholds": {
            "user_max_drawdown_tolerance": user_max_drawdown_tolerance,
            "max_participation_rate": max_participation_rate,
            "min_raw_total_return": min_raw_total_return,
            "min_raw_sharpe": min_raw_sharpe,
            "min_raw_overlap_sharpe": min_raw_overlap_sharpe,
            "min_repair_overlap_sharpe": min_repair_overlap_sharpe,
            "min_repair_relative_return": min_repair_relative_return,
        },
        "summary": _summary(pair_audits),
        "recommended_next_actions": _recommended_next_actions(pair_audits),
        "pair_audits": pair_audits,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_aggressive_turnover_capacity_markdown(audit)
    return audit


def write_aggressive_turnover_capacity_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "aggressive_turnover_capacity_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "aggressive_turnover_capacity_audit.md").write_text(
        render_aggressive_turnover_capacity_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame([_flatten_pair(row) for row in audit.get("pair_audits", [])]).to_csv(
        output_path / "pair_audits.csv",
        index=False,
    )


def render_aggressive_turnover_capacity_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    lines = [
        "# Aggressive Turnover Capacity Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source report: {audit.get('source_report') or 'unknown'}",
        f"- Risk profile: {audit.get('risk_profile')}",
        f"- Pairs: {summary.get('pairs', 0)}",
        f"- Raw high-return leads: {summary.get('raw_high_return_leads', 0)}",
        f"- Raw capacity-blocked leads: {summary.get('raw_capacity_blocked_leads', 0)}",
        f"- Capacity repair failed pairs: {summary.get('capacity_repair_failed_pairs', 0)}",
        f"- Promotion review candidates: {summary.get('promotion_review_candidates', 0)}",
        f"- Live boundary allowed: {audit.get('live_boundary_allowed', False)}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Recommended Next Actions",
        "",
    ]
    actions = _list(audit.get("recommended_next_actions"))
    lines.extend(f"- `{action}`" for action in actions) if actions else lines.append("- none")
    lines.extend(["", "## Pair Status Counts", ""])
    status_counts = _dict(summary.get("pair_status_counts"))
    if status_counts:
        for status, count in sorted(status_counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Pair Audits",
            "",
            "| Raw Factor | Status | Raw Total | Raw Sharpe | Raw Overlap | Raw DD | Raw Cap Trades | Repair Factor | Repair Total | Repair Overlap | Repair Relative |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in _list(audit.get("pair_audits")):
        raw = _dict(row.get("raw"))
        repair = _dict(row.get("repair"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(raw.get("factor_name")),
                    _text(row.get("pair_status")),
                    _metric(raw.get("total_return")),
                    _metric(raw.get("sharpe")),
                    _metric(raw.get("overlap_autocorr_adjusted_sharpe")),
                    _metric(raw.get("max_drawdown")),
                    _text(raw.get("capacity_limited_trades")),
                    _text(repair.get("factor_name")),
                    _metric(repair.get("total_return")),
                    _metric(repair.get("overlap_autocorr_adjusted_sharpe")),
                    _metric(repair.get("relative_return")),
                ]
            )
            + " |"
        )
    lines.extend(["", "This audit cannot promote factors by itself. It separates drawdown tolerance from execution capacity."])
    return "\n".join(lines) + "\n"


def _audit_pair(
    raw_factor_name: str,
    *,
    raw_row: dict[str, Any] | None,
    repair_row: dict[str, Any] | None,
    repair_factor_name: str,
    source_report: str | None,
    user_max_drawdown_tolerance: float,
    max_participation_rate: float,
    min_raw_total_return: float,
    min_raw_sharpe: float,
    min_raw_overlap_sharpe: float,
    min_repair_overlap_sharpe: float,
    min_repair_relative_return: float,
) -> dict[str, Any]:
    raw = _audit_leg(
        raw_row,
        fallback_factor_name=raw_factor_name,
        source_report=source_report,
        user_max_drawdown_tolerance=user_max_drawdown_tolerance,
        max_participation_rate=max_participation_rate,
        min_overlap_sharpe=min_raw_overlap_sharpe,
        min_relative_return=None,
    )
    repair = _audit_leg(
        repair_row,
        fallback_factor_name=repair_factor_name,
        source_report=source_report,
        user_max_drawdown_tolerance=user_max_drawdown_tolerance,
        max_participation_rate=max_participation_rate,
        min_overlap_sharpe=min_repair_overlap_sharpe,
        min_relative_return=min_repair_relative_return,
    )
    raw_high_return_lead = (
        raw["total_return"] >= min_raw_total_return
        and raw["sharpe"] >= min_raw_sharpe
        and raw["overlap_autocorr_adjusted_sharpe"] >= min_raw_overlap_sharpe
    )
    raw_capacity_blocked = bool(raw["hard_blockers"])
    repair_exists = bool(repair_row)
    repair_quality_survived = repair["promotion_review_candidate"]

    raw_total = raw["total_return"]
    repair["total_return_capture_ratio"] = repair["total_return"] / raw_total if raw_total > 0 else 0.0
    raw_overlap = raw["overlap_autocorr_adjusted_sharpe"]
    repair["overlap_sharpe_capture_ratio"] = (
        repair["overlap_autocorr_adjusted_sharpe"] / raw_overlap if raw_overlap > 0 else 0.0
    )
    if repair_exists and raw_high_return_lead and repair["total_return_capture_ratio"] < 0.25:
        repair["soft_warnings"].append("repair_return_collapse")
    if repair_exists and raw_high_return_lead and repair["overlap_sharpe_capture_ratio"] < 0.5:
        repair["soft_warnings"].append("repair_overlap_sharpe_collapse")

    if repair_quality_survived:
        pair_status = "capacity_repaired_review_candidate"
    elif raw_high_return_lead and raw_capacity_blocked and repair_exists:
        pair_status = "research_lead_capacity_repair_failed"
    elif raw_high_return_lead and raw_capacity_blocked:
        pair_status = "research_lead_needs_capacity_repair"
    elif raw_high_return_lead and not raw_capacity_blocked:
        pair_status = "raw_capacity_clean_review_candidate"
    else:
        pair_status = "weak_or_unproven_turnover_signal"

    return {
        "raw_factor_name": raw_factor_name,
        "repair_factor_name": repair_factor_name,
        "pair_status": pair_status,
        "raw_high_return_lead": raw_high_return_lead,
        "raw_capacity_blocked": raw_capacity_blocked,
        "repair_exists": repair_exists,
        "repair_quality_survived": repair_quality_survived,
        "promotion_review_candidate": pair_status in {
            "capacity_repaired_review_candidate",
            "raw_capacity_clean_review_candidate",
        },
        "raw": raw,
        "repair": repair,
    }


def _audit_leg(
    row: dict[str, Any] | None,
    *,
    fallback_factor_name: str,
    source_report: str | None,
    user_max_drawdown_tolerance: float,
    max_participation_rate: float,
    min_overlap_sharpe: float,
    min_relative_return: float | None,
) -> dict[str, Any]:
    row = row or {}
    max_drawdown = _number(_first(row, ("max_drawdown", "test_max_drawdown")))
    capacity_limited_trades = int(_number(_first(row, ("capacity_limited_trades", "test_capacity_limited_trades"))))
    participation = _number(_first(row, ("max_participation_rate", "test_max_participation_rate")))
    extreme_trade_return_flag = _bool(_first(row, ("extreme_trade_return_flag", "test_extreme_trade_return_flag")))
    total_return = _number(_first(row, ("total_return", "test_total_return")))
    relative_return = _number(_first(row, ("relative_return", "test_relative_return")))
    overlap_sharpe = _number(_first(row, ("overlap_autocorr_adjusted_sharpe", "test_overlap_autocorr_adjusted_sharpe")))

    hard_blockers: list[str] = []
    if capacity_limited_trades > 0:
        hard_blockers.append("capacity_limited_trades_present")
    if participation > max_participation_rate:
        hard_blockers.append("participation_rate_above_limit")
    if extreme_trade_return_flag:
        hard_blockers.append("extreme_trade_return_flag")

    soft_warnings: list[str] = []
    drawdown_within_tolerance = max_drawdown >= -abs(user_max_drawdown_tolerance)
    if not drawdown_within_tolerance:
        soft_warnings.append("drawdown_above_user_tolerance")
    if overlap_sharpe < min_overlap_sharpe:
        soft_warnings.append("overlap_adjusted_sharpe_below_floor")
    if min_relative_return is not None and relative_return < min_relative_return:
        soft_warnings.append("benchmark_relative_return_negative")
    if total_return <= 0:
        soft_warnings.append("non_positive_total_return")

    promotion_review_candidate = (
        bool(row)
        and not hard_blockers
        and overlap_sharpe >= min_overlap_sharpe
        and (min_relative_return is None or relative_return >= min_relative_return)
        and total_return > 0
        and drawdown_within_tolerance
    )
    return {
        "case_id": str(row.get("case_id") or ""),
        "factor_name": str(row.get("factor_name") or fallback_factor_name),
        "source_report": source_report,
        "decision_status": str(row.get("decision_status") or ""),
        "decision_reasons": _decision_reasons(row.get("decision_reasons")),
        "total_return": total_return,
        "annualized_return": _number(_first(row, ("annualized_return", "annual_return", "test_annualized_return"))),
        "sharpe": _number(_first(row, ("sharpe", "test_sharpe"))),
        "overlap_autocorr_adjusted_sharpe": overlap_sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": _number(_first(row, ("win_rate", "test_win_rate"))),
        "mean_rank_ic": _number(_first(row, ("mean_rank_ic", "rank_ic", "test_mean_rank_ic"))),
        "rank_ic_t_stat": _number(_first(row, ("rank_ic_t_stat", "test_rank_ic_t_stat"))),
        "capacity_limited_trades": capacity_limited_trades,
        "max_participation_rate": participation,
        "extreme_trade_return_flag": extreme_trade_return_flag,
        "relative_return": relative_return,
        "drawdown_within_user_tolerance": drawdown_within_tolerance,
        "hard_blockers": hard_blockers,
        "soft_warnings": _dedupe(soft_warnings),
        "promotion_review_candidate": promotion_review_candidate,
    }


def _summary(pair_audits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pairs": len(pair_audits),
        "raw_high_return_leads": sum(1 for row in pair_audits if row["raw_high_return_lead"]),
        "raw_capacity_blocked_leads": sum(1 for row in pair_audits if row["raw_capacity_blocked"]),
        "capacity_repair_failed_pairs": sum(
            1 for row in pair_audits if row["pair_status"] == "research_lead_capacity_repair_failed"
        ),
        "capacity_repair_missing_pairs": sum(
            1 for row in pair_audits if row["pair_status"] == "research_lead_needs_capacity_repair"
        ),
        "promotion_review_candidates": sum(1 for row in pair_audits if row["promotion_review_candidate"]),
        "pair_status_counts": dict(sorted(Counter(row["pair_status"] for row in pair_audits).items())),
    }


def _recommended_next_actions(pair_audits: list[dict[str, Any]]) -> list[str]:
    if not pair_audits:
        return ["run_turnover_leaderboard_before_audit"]
    actions: list[str] = ["keep_drawdown_tolerance_separate_from_capacity_gate"]
    if any(row["pair_status"] == "research_lead_capacity_repair_failed" for row in pair_audits):
        actions.extend(
            [
                "capacity_repair_not_raw_promotion",
                "smaller_capital_and_adv_sensitivity_replay",
                "try_continuous_capacity_weight_not_binary_large_mv",
                "liquidity_calendar_data_quality_audit",
            ]
        )
    if any(row["pair_status"] == "research_lead_needs_capacity_repair" for row in pair_audits):
        actions.append("large_mv_or_adv_weighted_repair_preregistration")
    if any(row["promotion_review_candidate"] for row in pair_audits):
        actions.append("walk_forward_oos_validation_for_capacity_repair")
    if all(not row["raw_high_return_lead"] for row in pair_audits):
        actions.append("rotate_factor_family_with_public_hypothesis")
    return _dedupe(actions)


def _infer_target_factors(records: list[dict[str, Any]], *, repair_suffix: str) -> list[str]:
    factor_names = {str(row.get("factor_name") or "") for row in records}
    inferred = []
    for factor_name in sorted(factor_names):
        if not factor_name or factor_name.endswith(repair_suffix):
            continue
        if f"{factor_name}{repair_suffix}" in factor_names:
            inferred.append(factor_name)
    return inferred


def _rows_for_factor(records: list[dict[str, Any]], factor_name: str) -> list[dict[str, Any]]:
    return [row for row in records if str(row.get("factor_name") or "") == factor_name]


def _best_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            _number(_first(row, ("overlap_autocorr_adjusted_sharpe", "test_overlap_autocorr_adjusted_sharpe"))),
            _number(_first(row, ("sharpe", "test_sharpe"))),
            _number(_first(row, ("total_return", "test_total_return"))),
        ),
        reverse=True,
    )[0]


def _flatten_pair(row: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(row.get("raw"))
    repair = _dict(row.get("repair"))
    return {
        "raw_factor_name": row.get("raw_factor_name"),
        "repair_factor_name": row.get("repair_factor_name"),
        "pair_status": row.get("pair_status"),
        "promotion_review_candidate": row.get("promotion_review_candidate"),
        "raw_case_id": raw.get("case_id"),
        "raw_total_return": raw.get("total_return"),
        "raw_annualized_return": raw.get("annualized_return"),
        "raw_sharpe": raw.get("sharpe"),
        "raw_overlap_autocorr_adjusted_sharpe": raw.get("overlap_autocorr_adjusted_sharpe"),
        "raw_max_drawdown": raw.get("max_drawdown"),
        "raw_win_rate": raw.get("win_rate"),
        "raw_rank_ic_t_stat": raw.get("rank_ic_t_stat"),
        "raw_capacity_limited_trades": raw.get("capacity_limited_trades"),
        "raw_max_participation_rate": raw.get("max_participation_rate"),
        "raw_extreme_trade_return_flag": raw.get("extreme_trade_return_flag"),
        "raw_relative_return": raw.get("relative_return"),
        "raw_hard_blockers": ",".join(_list(raw.get("hard_blockers"))),
        "repair_case_id": repair.get("case_id"),
        "repair_total_return": repair.get("total_return"),
        "repair_annualized_return": repair.get("annualized_return"),
        "repair_sharpe": repair.get("sharpe"),
        "repair_overlap_autocorr_adjusted_sharpe": repair.get("overlap_autocorr_adjusted_sharpe"),
        "repair_max_drawdown": repair.get("max_drawdown"),
        "repair_win_rate": repair.get("win_rate"),
        "repair_rank_ic_t_stat": repair.get("rank_ic_t_stat"),
        "repair_capacity_limited_trades": repair.get("capacity_limited_trades"),
        "repair_max_participation_rate": repair.get("max_participation_rate"),
        "repair_relative_return": repair.get("relative_return"),
        "repair_total_return_capture_ratio": repair.get("total_return_capture_ratio"),
        "repair_overlap_sharpe_capture_ratio": repair.get("overlap_sharpe_capture_ratio"),
        "repair_soft_warnings": ",".join(_list(repair.get("soft_warnings"))),
    }


def _frame(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _decision_reasons(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        parsed = None
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [part.strip() for part in text.split(",") if part.strip()]


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and not _empty(row.get(key)):
            return row.get(key)
    return None


def _empty(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, float) and math.isnan(value))


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _metric(value: Any) -> str:
    return f"{_number(value):.4f}"


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return str(value)
