from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STAGE = "walk_forward_early_stop_audit"


def build_walk_forward_early_stop_audit(
    walk_forward_root: str | Path,
    *,
    min_completed_folds: int = 3,
    expected_rows_per_fold: int = 1,
    min_positive_relative_rows: int = 1,
    min_accepted_rows: int = 1,
    min_capacity_clean_rate: float = 0.95,
) -> dict[str, Any]:
    root = Path(walk_forward_root)
    folds = _fold_summaries(root, expected_rows_per_fold=expected_rows_per_fold)
    completed = [fold for fold in folds if fold["complete"]]
    inspected_rows = sum(fold["rows"] for fold in completed)
    accepted_rows = sum(fold["accepted_rows"] for fold in completed)
    positive_relative_rows = sum(fold["positive_relative_rows"] for fold in completed)
    capacity_clean_rows = sum(fold["capacity_clean_rows"] for fold in completed)
    capacity_clean_rate = capacity_clean_rows / inspected_rows if inspected_rows else 0.0
    reasons = _decision_reasons(
        completed_folds=len(completed),
        min_completed_folds=min_completed_folds,
        accepted_rows=accepted_rows,
        min_accepted_rows=min_accepted_rows,
        positive_relative_rows=positive_relative_rows,
        min_positive_relative_rows=min_positive_relative_rows,
        capacity_clean_rate=capacity_clean_rate,
        min_capacity_clean_rate=min_capacity_clean_rate,
    )
    early_stop = (
        len(completed) >= min_completed_folds
        and accepted_rows < min_accepted_rows
        and positive_relative_rows < min_positive_relative_rows
        and capacity_clean_rate >= min_capacity_clean_rate
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "walk_forward_root": str(root),
        "parameters": {
            "min_completed_folds": min_completed_folds,
            "expected_rows_per_fold": expected_rows_per_fold,
            "min_positive_relative_rows": min_positive_relative_rows,
            "min_accepted_rows": min_accepted_rows,
            "min_capacity_clean_rate": min_capacity_clean_rate,
        },
        "summary": {
            "folds_seen": len(folds),
            "completed_folds": len(completed),
            "inspected_rows": inspected_rows,
            "accepted_rows": accepted_rows,
            "positive_relative_rows": positive_relative_rows,
            "capacity_clean_rows": capacity_clean_rows,
            "capacity_clean_rate": capacity_clean_rate,
            "early_stop_recommended": early_stop,
        },
        "decision": {
            "next_action": "stop_validation_and_rotate" if early_stop else "continue_validation",
            "reasons": reasons,
        },
        "folds": folds,
    }
    result["markdown"] = render_walk_forward_early_stop_audit_markdown(result)
    return result


def write_walk_forward_early_stop_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in result.items() if key != "markdown"}
    (output_path / "walk_forward_early_stop_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "walk_forward_early_stop_audit.md").write_text(
        render_walk_forward_early_stop_audit_markdown(result),
        encoding="utf-8",
    )


def render_walk_forward_early_stop_audit_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# Walk-Forward Early Stop Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Walk-forward root: `{result.get('walk_forward_root', '')}`",
        f"- Completed folds: {summary.get('completed_folds', 0)}",
        f"- Inspected rows: {summary.get('inspected_rows', 0)}",
        f"- Accepted rows: {summary.get('accepted_rows', 0)}",
        f"- Positive-relative rows: {summary.get('positive_relative_rows', 0)}",
        f"- Capacity-clean rows: {summary.get('capacity_clean_rows', 0)}",
        f"- Capacity-clean rate: {summary.get('capacity_clean_rate', 0.0):.2%}",
        f"- Early stop recommended: {summary.get('early_stop_recommended', False)}",
        f"- Next action: {decision.get('next_action', '')}",
        f"- Reasons: {', '.join(decision.get('reasons', []) or []) or 'none'}",
        "",
        "## Fold Summaries",
        "",
        "| Fold | Complete | Rows | Accepted | Positive Relative | Capacity Clean | Best Overlap Sharpe | Best Relative |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fold in result.get("folds", []) or []:
        lines.append(
            "| {fold} | {complete} | {rows} | {accepted} | {positive} | {capacity} | {best_sharpe:.3f} | {best_relative:.4f} |".format(
                fold=fold["fold"],
                complete=fold["complete"],
                rows=fold["rows"],
                accepted=fold["accepted_rows"],
                positive=fold["positive_relative_rows"],
                capacity=fold["capacity_clean_rows"],
                best_sharpe=fold["best_overlap_sharpe"],
                best_relative=fold["best_relative_return"],
            )
        )
    return "\n".join(lines) + "\n"


def _fold_summaries(root: Path, *, expected_rows_per_fold: int) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for fold_dir in sorted(root.glob("fold_*")):
        rows = _read_jsonl(fold_dir / "test" / "partial_leaderboard.jsonl")
        if not rows:
            continue
        best = max(rows, key=lambda row: float(row.get("overlap_autocorr_adjusted_sharpe") or -999.0))
        summaries.append(
            {
                "fold": fold_dir.name,
                "rows": len(rows),
                "complete": len(rows) >= expected_rows_per_fold,
                "accepted_rows": sum(1 for row in rows if row.get("decision_status") == "approved"),
                "positive_relative_rows": sum(1 for row in rows if float(row.get("relative_return") or 0.0) > 0.0),
                "capacity_clean_rows": sum(1 for row in rows if int(row.get("capacity_limited_trades") or 0) == 0),
                "best_case_id": str(best.get("case_id", "")),
                "best_overlap_sharpe": float(best.get("overlap_autocorr_adjusted_sharpe") or 0.0),
                "best_relative_return": float(best.get("relative_return") or 0.0),
                "best_max_drawdown": float(best.get("max_drawdown") or 0.0),
            }
        )
    return summaries


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _decision_reasons(
    *,
    completed_folds: int,
    min_completed_folds: int,
    accepted_rows: int,
    min_accepted_rows: int,
    positive_relative_rows: int,
    min_positive_relative_rows: int,
    capacity_clean_rate: float,
    min_capacity_clean_rate: float,
) -> list[str]:
    reasons: list[str] = []
    if completed_folds < min_completed_folds:
        reasons.append("insufficient_completed_folds")
    if accepted_rows < min_accepted_rows:
        reasons.append("no_accepted_rows")
    if positive_relative_rows < min_positive_relative_rows:
        reasons.append("no_positive_relative_rows")
    if capacity_clean_rate >= min_capacity_clean_rate:
        reasons.append("capacity_issue_mostly_cleaned")
    else:
        reasons.append("capacity_issue_not_cleaned")
    return reasons
