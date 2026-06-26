from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    build_financial_pit_post_announcement_drift_matrix_label_smoke,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import SAFETY
from quant_robot.ops.profitability_quality_preregistration import _sanitize


STAGE = "financial_pit_post_announcement_gap_reversal_matrix_label_smoke"
NEXT_ALLOWED_GATE = "round223_financial_pit_post_announcement_gap_reversal_residual_prescreen"


def build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5,),
    execution_lag: int = 1,
    min_label_coverage: float = 0.60,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
        financial_root=financial_root,
        bars_roots=bars_roots,
        preregistration_json=preregistration_json,
        candidate_plan_gate_json=candidate_plan_gate_json,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        min_label_coverage=min_label_coverage,
    )
    result["stage"] = STAGE
    result["summary"]["next_allowed_gate"] = NEXT_ALLOWED_GATE
    result["promotion_policy"]["next_allowed_action"] = NEXT_ALLOWED_GATE
    result["gap_reversal_policy"] = {
        "source_failure": "round222_pead_event_gap_underreaction_wrong_signed_after_residual_prescreen",
        "formula_family": "inverse_event_gap_reversal",
        "fresh_preregistration_required": True,
    }
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_markdown(result)
    return result


def write_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_pit_post_announcement_gap_reversal_matrix_label_smoke.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_gap_reversal_matrix_label_smoke.md").write_text(
        render_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_matrix_candidate_summary.csv",
        result.get("candidate_summaries", []) or [],
    )


def render_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Gap Reversal Matrix Label Smoke",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Active candidates: {summary.get('active_candidate_count', 0)}",
        f"- Frozen candidates: {summary.get('frozen_candidate_count', 0)}",
        f"- Unknown active candidates: {summary.get('unknown_active_candidate_count', 0)}",
        f"- Financial rows: {summary.get('financial_rows', 0)}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Factor value rows: {summary.get('factor_value_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Label aligned rows: {summary.get('label_aligned_rows', 0)}",
        f"- Label coverage: {float(summary.get('label_coverage', 0.0)):.2%}",
        f"- Alignment violations: {summary.get('alignment_violation_rows', 0)}",
        f"- Max signal date: {summary.get('max_signal_date')}",
        f"- Max factor date: {summary.get('max_factor_date')}",
        f"- Max label date: {summary.get('max_label_date')}",
        f"- Horizons: {', '.join(str(item) for item in summary.get('horizons', []) or [])}",
        f"- Next allowed gate: `{summary.get('next_allowed_gate', NEXT_ALLOWED_GATE)}`",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Summary",
        "",
        "| Factor | Factor Rows | Label Rows | Label Coverage | Violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result.get("candidate_summaries", []) or []:
        lines.append(
            "| {factor} | {factor_rows} | {label_rows} | {coverage:.2%} | {violations} |".format(
                factor=row.get("factor_name", ""),
                factor_rows=int(row.get("factor_value_rows", 0)),
                label_rows=int(row.get("label_aligned_rows", 0)),
                coverage=float(row.get("label_coverage", 0.0)),
                violations=int(row.get("alignment_violation_rows", 0)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a factor-matrix and label-alignment smoke only.",
            "- It tests the freshly pre-registered inverse event-gap reversal formulas after Round222 rejected the original sign.",
            "- It does not compute IC, Sharpe, win rate, profit rate, total return, or drawdown.",
            "- Portfolio grids and promotion remain blocked until residual IC shape, walk-forward, costs, capacity, and regime gates pass.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
