from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any


STAGE = "final_holdout_readiness_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
DEFAULT_FINAL_HOLDOUT_START = "2026-01-01"


def build_final_holdout_readiness_audit(report: dict[str, Any]) -> dict[str, Any]:
    holdout_policy = _dict(report.get("holdout_policy"))
    data_window = _dict(report.get("data_window"))
    summary = _dict(report.get("summary"))
    final_holdout_start = str(holdout_policy.get("final_holdout_start") or DEFAULT_FINAL_HOLDOUT_START)
    final_holdout_included = bool(holdout_policy.get("final_holdout_included"))
    max_bar_date = _optional_date(data_window.get("max_bar_date"))
    max_signal_date = _optional_date(data_window.get("max_signal_date"))
    holdout_start_date = _optional_date(final_holdout_start)
    bars_cover = bool(max_bar_date and holdout_start_date and max_bar_date >= holdout_start_date)
    signals_cover = bool(max_signal_date and holdout_start_date and max_signal_date >= holdout_start_date)
    holdout_folds = _holdout_folds(report.get("folds"), final_holdout_start=final_holdout_start)
    accepted_candidates = int(_number(summary.get("walk_forward_accepted_candidates")))
    blockers = []
    if not final_holdout_included:
        blockers.append("final_holdout_not_requested")
    if not bars_cover:
        blockers.append("bars_do_not_cover_final_holdout")
    if not signals_cover:
        blockers.append("signals_do_not_cover_final_holdout")
    if not holdout_folds:
        blockers.append("no_test_fold_touches_final_holdout")
    if accepted_candidates <= 0:
        blockers.append("no_walk_forward_accepted_candidate")
    final_holdout_actual_read = not blockers
    next_direction = (
        "run_paper_gate_or_holdout_result_review"
        if final_holdout_actual_read
        else _blocked_next_direction(bars_cover=bars_cover, signals_cover=signals_cover)
    )
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_stage": report.get("stage"),
        "coverage": {
            "final_holdout_start": final_holdout_start,
            "final_holdout_requested": final_holdout_included,
            "max_bar_date": data_window.get("max_bar_date"),
            "max_signal_date": data_window.get("max_signal_date"),
            "bars_cover_final_holdout": bars_cover,
            "signals_cover_final_holdout": signals_cover,
            "holdout_fold_count": len(holdout_folds),
            "holdout_folds": holdout_folds,
            "walk_forward_accepted_candidates": accepted_candidates,
        },
        "decision": {
            "final_holdout_actual_read": final_holdout_actual_read,
            "blockers": blockers,
            "promotion_allowed": False,
            "reason": (
                "Final holdout can be treated as read only when bars, factor signals, and chronological "
                "test folds all touch the final holdout window."
            ),
        },
        "next_direction": next_direction,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_markdown(audit)
    return audit


def write_final_holdout_readiness_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "final_holdout_readiness_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "final_holdout_readiness_audit.md").write_text(render_markdown(audit), encoding="utf-8")


def render_markdown(audit: dict[str, Any]) -> str:
    coverage = _dict(audit.get("coverage"))
    decision = _dict(audit.get("decision"))
    lines = [
        "# Final Holdout Readiness Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source stage: {audit.get('source_stage')}",
        f"- Final holdout start: {coverage.get('final_holdout_start')}",
        f"- Final holdout requested: {coverage.get('final_holdout_requested', False)}",
        f"- Max bar date: {coverage.get('max_bar_date')}",
        f"- Max signal date: {coverage.get('max_signal_date')}",
        f"- Bars cover holdout: {coverage.get('bars_cover_final_holdout', False)}",
        f"- Signals cover holdout: {coverage.get('signals_cover_final_holdout', False)}",
        f"- Holdout folds: {coverage.get('holdout_fold_count', 0)}",
        f"- Accepted walk-forward candidates: {coverage.get('walk_forward_accepted_candidates', 0)}",
        f"- Final holdout actually read: {decision.get('final_holdout_actual_read', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{audit.get('next_direction')}`",
        f"- Blockers: {', '.join(decision.get('blockers', []) or []) or 'none'}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
    ]
    if decision.get("final_holdout_actual_read"):
        lines.append("- The frozen candidate has real final-holdout coverage and may proceed to holdout result review or paper gate.")
    else:
        lines.append(
            "- This is not a valid final-holdout result yet; treat it as a data/readiness blocker, not a candidate failure."
        )
    return "\n".join(lines) + "\n"


def _holdout_folds(value: Any, *, final_holdout_start: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    holdout_start = _optional_date(final_holdout_start)
    output = []
    for row in value:
        if not isinstance(row, dict):
            continue
        test_end = _optional_date(row.get("test_end_date"))
        if holdout_start and test_end and test_end >= holdout_start:
            output.append(
                {
                    "fold": row.get("fold"),
                    "test_start_date": row.get("test_start_date"),
                    "test_end_date": row.get("test_end_date"),
                    "case_id": row.get("case_id"),
                }
            )
    return output


def _blocked_next_direction(*, bars_cover: bool, signals_cover: bool) -> str:
    if bars_cover and not signals_cover:
        return "refresh_factor_inputs_for_final_holdout"
    if not bars_cover:
        return "refresh_bars_and_factor_inputs_for_final_holdout"
    return "rerun_final_holdout_with_chronological_test_folds"


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
