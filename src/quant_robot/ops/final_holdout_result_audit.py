from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any


STAGE = "final_holdout_result_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
DEFAULT_FINAL_HOLDOUT_START = "2026-01-01"


def build_final_holdout_result_audit(report: dict[str, Any]) -> dict[str, Any]:
    holdout_policy = _dict(report.get("holdout_policy"))
    final_holdout_start = str(holdout_policy.get("final_holdout_start") or DEFAULT_FINAL_HOLDOUT_START)
    leaderboard = _list_of_dicts(report.get("leaderboard"))
    aggregate_accepted = {
        str(row.get("case_id"))
        for row in leaderboard
        if str(row.get("validation_status", "")).lower() == "accepted"
    }
    holdout_rows = _holdout_rows(report.get("folds"), final_holdout_start=final_holdout_start)
    holdout_by_case: dict[str, list[dict[str, Any]]] = {}
    for row in holdout_rows:
        holdout_by_case.setdefault(str(row.get("case_id")), []).append(row)

    case_results = []
    for case_id in sorted(set(holdout_by_case) | aggregate_accepted):
        rows = sorted(holdout_by_case.get(case_id, []), key=lambda row: int(_number(row.get("fold"))))
        statuses = {str(row.get("fold_validation_status", "")).lower() for row in rows}
        blockers = _dedupe(
            blocker
            for row in rows
            for blocker in _split_blockers(row.get("fold_validation_blockers"))
        )
        holdout_status = "accepted" if rows and statuses == {"accepted"} and not blockers else "rejected"
        if not rows:
            holdout_status = "missing"
            blockers.append("missing_final_holdout_fold")
        if case_id not in aggregate_accepted:
            blockers.append("aggregate_case_not_accepted")
            holdout_status = "rejected"
        case_results.append(
            {
                "case_id": case_id,
                "aggregate_status": "accepted" if case_id in aggregate_accepted else "rejected",
                "holdout_status": holdout_status,
                "holdout_fold_count": len(rows),
                "holdout_total_return": _sum(rows, "test_total_return"),
                "mean_holdout_overlap_adjusted_sharpe": _mean(rows, "test_overlap_autocorr_adjusted_sharpe"),
                "max_holdout_extreme_trade_count": int(_max(rows, "extreme_trade_return_count")),
                "holdout_blockers": _dedupe(blockers),
            }
        )

    passed_cases = [row for row in case_results if row["holdout_status"] == "accepted"]
    blockers = []
    if not holdout_policy.get("final_holdout_included"):
        blockers.append("final_holdout_not_requested")
    if not holdout_rows:
        blockers.append("missing_final_holdout_folds")
    if aggregate_accepted and not passed_cases:
        blockers.append("no_case_passed_final_holdout_fold")
    if not aggregate_accepted:
        blockers.append("no_aggregate_accepted_case")
    paper_gate_allowed = bool(passed_cases) and not blockers
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_stage": report.get("stage"),
        "summary": {
            "final_holdout_start": final_holdout_start,
            "aggregate_accepted_cases": len(aggregate_accepted),
            "holdout_fold_rows": len(holdout_rows),
            "holdout_case_count": len(case_results),
            "holdout_passed_cases": len(passed_cases),
            "best_holdout_total_return": _max(case_results, "holdout_total_return"),
            "best_holdout_overlap_adjusted_sharpe": _max(case_results, "mean_holdout_overlap_adjusted_sharpe"),
            "max_holdout_extreme_trade_count": int(_max(case_results, "max_holdout_extreme_trade_count")),
        },
        "case_results": sorted(
            case_results,
            key=lambda row: (
                0 if row["holdout_status"] == "accepted" else 1,
                -_number(row.get("mean_holdout_overlap_adjusted_sharpe")),
                str(row.get("case_id")),
            ),
        ),
        "decision": {
            "paper_gate_allowed": paper_gate_allowed,
            "promotion_allowed": False,
            "blockers": blockers,
            "reason": (
                "Aggregate walk-forward acceptance is insufficient when the final-holdout fold is rejected. "
                "A candidate may proceed to paper review only if both aggregate and final-holdout folds pass."
            ),
        },
        "next_direction": (
            "run_paper_gate_for_holdout_survivors"
            if paper_gate_allowed
            else "hibernate_or_rotate_after_final_holdout_failure"
        ),
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_markdown(audit)
    return audit


def write_final_holdout_result_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "final_holdout_result_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "final_holdout_result_audit.md").write_text(render_markdown(audit), encoding="utf-8")


def render_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    decision = _dict(audit.get("decision"))
    lines = [
        "# Final Holdout Result Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source stage: {audit.get('source_stage')}",
        f"- Final holdout start: {summary.get('final_holdout_start')}",
        f"- Aggregate accepted cases: {summary.get('aggregate_accepted_cases', 0)}",
        f"- Holdout fold rows: {summary.get('holdout_fold_rows', 0)}",
        f"- Holdout passed cases: {summary.get('holdout_passed_cases', 0)}",
        f"- Best holdout total return: {_fmt_pct(summary.get('best_holdout_total_return'))}",
        f"- Best holdout overlap Sharpe: {_number(summary.get('best_holdout_overlap_adjusted_sharpe')):.3f}",
        f"- Max holdout extreme trades: {summary.get('max_holdout_extreme_trade_count', 0)}",
        f"- Paper gate allowed: {decision.get('paper_gate_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{audit.get('next_direction')}`",
        f"- Blockers: {', '.join(decision.get('blockers', []) or []) or 'none'}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Case Results",
        "",
        "| Case | Aggregate | Holdout | Holdout Return | Holdout Overlap | Extreme | Blockers |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in audit.get("case_results", []) or []:
        lines.append(
            "| {case} | {agg} | {holdout} | {ret:.2%} | {overlap:.3f} | {extreme} | {blockers} |".format(
                case=row.get("case_id", ""),
                agg=row.get("aggregate_status", ""),
                holdout=row.get("holdout_status", ""),
                ret=_number(row.get("holdout_total_return")),
                overlap=_number(row.get("mean_holdout_overlap_adjusted_sharpe")),
                extreme=int(_number(row.get("max_holdout_extreme_trade_count"))),
                blockers=";".join(row.get("holdout_blockers", []) or []) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _holdout_rows(value: Any, *, final_holdout_start: str) -> list[dict[str, Any]]:
    rows = _list_of_dicts(value)
    holdout_start = _optional_date(final_holdout_start)
    output = []
    for row in rows:
        test_end = _optional_date(row.get("test_end_date"))
        if holdout_start and test_end and test_end >= holdout_start:
            output.append(row)
    return output


def _split_blockers(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item for item in value.split(";") if item]
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def _dedupe(values: Any) -> list[str]:
    output = []
    seen = set()
    for value in values:
        item = str(value)
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sum(rows: list[dict[str, Any]], key: str) -> float:
    return float(sum(_number(row.get(key)) for row in rows))


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return float(sum(_number(row.get(key)) for row in rows) / len(rows)) if rows else 0.0


def _max(rows: list[dict[str, Any]], key: str) -> float:
    return float(max((_number(row.get(key)) for row in rows), default=0.0))


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _fmt_pct(value: Any) -> str:
    return f"{_number(value):.2%}"
