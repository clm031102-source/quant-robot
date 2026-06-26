from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    SAFETY,
    build_financial_pit_post_announcement_drift_preregistration,
)
from quant_robot.ops.profitability_quality_preregistration import _sanitize


STAGE = "financial_pit_post_announcement_gap_reversal_preregistration"
NEXT_ALLOWED_GATE = "round223_financial_pit_post_announcement_gap_reversal_matrix_label_smoke"


def build_financial_pit_post_announcement_gap_reversal_preregistration(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    candidate_seed_json: str | Path | None = None,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    min_assets: int = 50,
    min_signal_dates: int = 20,
    min_event_reaction_coverage: float = 0.80,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_drift_preregistration(
        financial_root=financial_root,
        bars_roots=bars_roots,
        candidate_seed_json=candidate_seed_json,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        min_assets=min_assets,
        min_signal_dates=min_signal_dates,
        min_event_reaction_coverage=min_event_reaction_coverage,
    )
    result["stage"] = STAGE
    result["generated_at"] = date.today().isoformat()
    result["summary"]["next_allowed_gate"] = NEXT_ALLOWED_GATE
    result["promotion_policy"]["next_allowed_action"] = NEXT_ALLOWED_GATE
    result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"] = False
    result["promotion_policy"]["promotion_allowed"] = False
    result["gap_reversal_policy"] = {
        "source_failure": "round222_pead_event_gap_underreaction_wrong_signed_after_residual_prescreen",
        "fresh_preregistration_required": True,
        "original_underreaction_sign_reuse_allowed": False,
        "inverse_gap_reversal_hypothesis": True,
    }
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_preregistration_markdown(result)
    return result


def write_financial_pit_post_announcement_gap_reversal_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "financial_pit_post_announcement_gap_reversal_preregistration.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_gap_reversal_preregistration.md").write_text(
        render_financial_pit_post_announcement_gap_reversal_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_candidates.csv",
        result.get("candidates", []) or [],
        ["factor_name", "family", "registration_status", "portfolio_backtest_allowed", "promotion_allowed"],
    )


def render_financial_pit_post_announcement_gap_reversal_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Gap Reversal Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Financial rows: {summary.get('financial_rows', 0)}",
        f"- Financial assets: {summary.get('financial_assets', 0)}",
        f"- Unique signal dates: {summary.get('unique_signal_dates', 0)}",
        f"- Event reaction coverage: {float(summary.get('event_reaction_coverage', 0.0)):.2%}",
        f"- Event reaction available rows: {summary.get('event_reaction_available_rows', 0)}",
        f"- Missing reaction-available rows: {summary.get('reaction_available_date_missing_rows', 0)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next allowed gate: `{summary.get('next_allowed_gate', NEXT_ALLOWED_GATE)}`",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidates",
        "",
        "| Factor | Status |",
        "|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(f"| `{candidate.get('factor_name', '')}` | {candidate.get('registration_status', '')} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is preregistration and event-availability evidence only.",
            "- The hypothesis is a fresh inverse-sign repair after Round222 rejected the original gap-underreaction direction.",
            "- No IC, portfolio grid, Sharpe, profit-rate claim, or promotion is allowed from this artifact.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
