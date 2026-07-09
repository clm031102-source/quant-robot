from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from quant_robot.ops.lpr_macro_regime_state_prescreen import SAFETY


STAGE = "lpr_macro_regime_walk_forward_rejection_rotation_gate"
VALIDATION_STAGE = "lpr_macro_regime_state_conditioned_walk_forward_validation"
NEXT_SOURCE_GATE_DIRECTION = "rotate_to_non_lpr_orthogonal_family_source_gate"
LPR_REVISIT_DIRECTION = "new_lpr_macro_interaction_source_gate_only"

CANDIDATE_COLUMNS = [
    "factor_name",
    "state",
    "validation_status",
    "accepted_folds",
    "folds",
    "mean_test_ic",
    "mean_test_long_short_net_mean",
    "mean_test_long_short_net_total",
    "mean_test_long_short_net_positive_rate",
    "test_capacity_limited_dates",
    "max_test_participation_rate",
    "moderate_exposure_challenge_required",
    "moderate_exposure_challenge_passed",
    "failure_families",
    "retry_status",
    "same_candidate_retry_allowed",
    "parameter_tuning_allowed",
    "rejection_reasons",
]
REASON_COLUMNS = ["source", "factor_name", "fold", "reason", "failure_family"]


def run_lpr_macro_regime_walk_forward_rejection_rotation_gate(
    *,
    validation_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    validation = json.loads(Path(validation_path).read_text(encoding="utf-8"))
    result = summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate(
        validation,
        validation_path=validation_path,
    )
    write_lpr_macro_regime_walk_forward_rejection_rotation_gate(output_dir, result)
    return result


def summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate(
    validation: dict[str, Any],
    *,
    validation_path: str | Path | None = None,
) -> dict[str, Any]:
    candidates = _dict_rows(validation.get("candidate_results"))
    folds = _dict_rows(validation.get("fold_results"))
    candidate_rotation_table = [_candidate_rotation_row(row) for row in candidates]
    reason_rows = _reason_rows(candidates, folds)
    failure_diagnostics = _failure_diagnostics(candidates, folds, reason_rows)
    blockers = _validation_blockers(validation, candidates)
    status = "cleared" if not blockers else "blocked"
    rotation_allowed = status == "cleared"
    accepted_candidates = _accepted_candidate_count(validation, candidates)
    rejected_candidates = sum(1 for row in candidates if row.get("validation_status") == "rejected")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "validation_path": str(Path(validation_path)) if validation_path is not None else None,
        "validation_stage": validation.get("stage"),
        "validation_status": validation.get("status"),
        "summary": {
            "frozen_candidates": int(_dict(validation.get("summary")).get("frozen_candidates", len(candidates)) or 0),
            "accepted_candidates": int(accepted_candidates),
            "rejected_candidates": int(rejected_candidates),
            "candidate_rows": len(candidates),
            "fold_rows": len(folds),
            "common_failed_test_folds": failure_diagnostics["common_failed_test_folds"],
            "capacity_not_blocker": failure_diagnostics["capacity_not_blocker"],
            "exposure_challenge_not_blocker": failure_diagnostics["exposure_challenge_not_blocker"],
            "next_direction": NEXT_SOURCE_GATE_DIRECTION if rotation_allowed else LPR_REVISIT_DIRECTION,
        },
        "decision": {
            "blockers": blockers,
            "rotation_source_gate_allowed_next": rotation_allowed,
            "same_lpr_candidate_retry_allowed": False,
            "parameter_tuning_allowed": False,
            "statistical_reality_check_allowed_next": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "rotation_policy": {
            "lpr_gap_widening_residual_path_status": "rejected_pending_new_hypothesis" if rotation_allowed else "not_rotated",
            "next_direction": NEXT_SOURCE_GATE_DIRECTION if rotation_allowed else LPR_REVISIT_DIRECTION,
            "source_gate_allowed_next": rotation_allowed,
            "rerun_same_lpr_gap_widening_candidates_allowed": False,
            "parameter_tuning_allowed": False,
            "cost_threshold_relaxation_allowed": False,
            "fold_threshold_relaxation_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "final_holdout_access_allowed": False,
            "live_boundary_allowed": False,
            "revisit_requirements": [
                "new_hypothesis_required_before_lpr_gap_widening_revisit",
                "must_restart_from_source_gate_not_walk_forward_retry",
                "must_not_reduce_cost_or_fold_thresholds_to_rescue_failed_candidates",
            ],
        },
        "failure_diagnostics": failure_diagnostics,
        "candidate_rotation_table": candidate_rotation_table,
        "reason_table": reason_rows,
        "holdout_policy": {
            "final_holdout_included": False,
            "final_holdout_use": "blocked_after_lpr_walk_forward_rejection",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "walk_forward_validation_rejected",
                "statistical_reality_check_not_allowed",
                "final_holdout_not_read",
                "paper_lane_not_approved",
            ],
        },
        "live_boundary_allowed": False,
        "safety": validation.get("safety", SAFETY),
    }
    result["markdown"] = render_lpr_macro_regime_walk_forward_rejection_rotation_gate_markdown(result)
    return result


def write_lpr_macro_regime_walk_forward_rejection_rotation_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_walk_forward_rejection_rotation_gate.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_walk_forward_rejection_rotation_gate.md").write_text(
        render_lpr_macro_regime_walk_forward_rejection_rotation_gate_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lpr_macro_regime_walk_forward_rejection_rotation_candidates.csv",
        clean["candidate_rotation_table"],
        CANDIDATE_COLUMNS,
    )
    _write_csv(
        output_path / "lpr_macro_regime_walk_forward_rejection_rotation_reasons.csv",
        clean["reason_table"],
        REASON_COLUMNS,
    )


def render_lpr_macro_regime_walk_forward_rejection_rotation_gate_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    policy = _dict(result.get("rotation_policy"))
    diagnostics = _dict(result.get("failure_diagnostics"))
    lines = [
        "# LPR Macro Regime Walk-Forward Rejection Rotation Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Validation status: {result.get('validation_status', 'unknown')}",
        f"- Accepted candidates: {summary.get('accepted_candidates', 0)}",
        f"- Rejected candidates: {summary.get('rejected_candidates', 0)}",
        f"- Common failed test folds: {', '.join(str(item) for item in _as_list(summary.get('common_failed_test_folds'))) or 'none'}",
        f"- Capacity not blocker: {diagnostics.get('capacity_not_blocker', False)}",
        f"- Exposure challenge not blocker: {diagnostics.get('exposure_challenge_not_blocker', False)}",
        f"- Rotation source gate allowed next: {decision.get('rotation_source_gate_allowed_next', False)}",
        f"- Same LPR candidate retry allowed: {decision.get('same_lpr_candidate_retry_allowed', False)}",
        f"- Parameter tuning allowed: {decision.get('parameter_tuning_allowed', False)}",
        f"- Next direction: `{policy.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Rotation Table",
        "",
        "| Factor | State | Validation | Folds | Test IC | Test Net Mean | Cap Dates | Failure Families | Retry |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("candidate_rotation_table", []):
        lines.append(
            "| {factor} | {state} | {status} | {accepted}/{folds} | {ic:.4f} | {net:.4f} | {cap} | {families} | {retry} |".format(
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                status=row.get("validation_status", ""),
                accepted=int(_number(row.get("accepted_folds"))),
                folds=int(_number(row.get("folds"))),
                ic=_number(row.get("mean_test_ic")),
                net=_number(row.get("mean_test_long_short_net_mean")),
                cap=int(_number(row.get("test_capacity_limited_dates"))),
                families=", ".join(_as_list(row.get("failure_families"))) or "none",
                retry=row.get("retry_status", ""),
            )
        )
    lines.extend(["", "## Decision Blockers", ""])
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Rotation Policy",
            "",
            f"- LPR gap-widening residual path status: `{policy.get('lpr_gap_widening_residual_path_status', '')}`",
            "- Do not rerun the same LPR gap-widening candidates without a new hypothesis and a fresh source gate.",
            "- Do not rescue the rejected path by relaxing cost, fold-count, final-holdout, portfolio-grid, or promotion gates.",
            "- Rotate next to an orthogonal non-LPR source gate unless a genuinely new LPR macro interaction is specified first.",
        ]
    )
    return "\n".join(lines) + "\n"


def _validation_blockers(validation: dict[str, Any], candidates: Sequence[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    decision = _dict(validation.get("decision"))
    portfolio_policy = _dict(validation.get("portfolio_grid_policy"))
    promotion_policy = _dict(validation.get("promotion_policy"))
    if validation.get("stage") != VALIDATION_STAGE:
        blockers.append("unexpected_validation_stage")
    if validation.get("status") != "rejected":
        blockers.append("walk_forward_validation_not_rejected")
    if not candidates:
        blockers.append("candidate_results_missing")
    if _accepted_candidate_count(validation, candidates) > 0:
        blockers.append("accepted_lpr_candidates_present")
    if any(row.get("validation_status") not in {"rejected"} for row in candidates):
        blockers.append("non_rejected_candidate_status_present")
    if decision.get("statistical_reality_check_allowed_next") is not False:
        blockers.append("statistical_reality_check_unexpectedly_allowed")
    if decision.get("portfolio_grid_allowed") is not False or portfolio_policy.get("portfolio_grid_allowed") is not False:
        blockers.append("portfolio_grid_unexpectedly_allowed")
    if decision.get("promotion_allowed") is not False or promotion_policy.get("promotion_allowed") is not False:
        blockers.append("promotion_unexpectedly_allowed")
    if validation.get("live_boundary_allowed") is not False:
        blockers.append("live_boundary_unexpectedly_allowed")
    return _unique(blockers)


def _accepted_candidate_count(validation: dict[str, Any], candidates: Sequence[dict[str, Any]]) -> int:
    candidate_count = sum(1 for row in candidates if row.get("validation_status") == "accepted")
    summary_count = int(_number(_dict(validation.get("summary")).get("accepted_candidates")))
    return max(candidate_count, summary_count)


def _candidate_rotation_row(candidate: dict[str, Any]) -> dict[str, Any]:
    reasons = _as_list(candidate.get("rejection_reasons"))
    return {
        "factor_name": candidate.get("factor_name", ""),
        "state": candidate.get("state", ""),
        "validation_status": candidate.get("validation_status", ""),
        "accepted_folds": int(_number(candidate.get("accepted_folds"))),
        "folds": int(_number(candidate.get("folds"))),
        "mean_test_ic": _number(candidate.get("mean_test_ic")),
        "mean_test_long_short_net_mean": _number(candidate.get("mean_test_long_short_net_mean")),
        "mean_test_long_short_net_total": _number(candidate.get("mean_test_long_short_net_total")),
        "mean_test_long_short_net_positive_rate": _number(candidate.get("mean_test_long_short_net_positive_rate")),
        "test_capacity_limited_dates": int(_number(candidate.get("test_capacity_limited_dates"))),
        "max_test_participation_rate": _number(candidate.get("max_test_participation_rate")),
        "moderate_exposure_challenge_required": bool(candidate.get("moderate_exposure_challenge_required", False)),
        "moderate_exposure_challenge_passed": bool(candidate.get("moderate_exposure_challenge_passed", False)),
        "failure_families": _unique(_failure_family(reason) for reason in reasons),
        "retry_status": "retired_pending_new_hypothesis",
        "same_candidate_retry_allowed": False,
        "parameter_tuning_allowed": False,
        "rejection_reasons": reasons,
    }


def _failure_diagnostics(
    candidates: Sequence[dict[str, Any]],
    folds: Sequence[dict[str, Any]],
    reason_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    candidate_names = {str(row.get("factor_name", "")) for row in candidates if row.get("factor_name")}
    common_failed_folds: list[int] = []
    for fold in sorted({int(_number(row.get("fold"))) for row in folds if row.get("fold") is not None}):
        fold_rows = [row for row in folds if int(_number(row.get("fold"))) == fold]
        fold_names = {str(row.get("factor_name", "")) for row in fold_rows if row.get("factor_name")}
        if candidate_names and fold_names >= candidate_names and all(row.get("fold_status") != "accepted" for row in fold_rows):
            common_failed_folds.append(fold)
    reason_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for row in reason_rows:
        reason = str(row.get("reason", ""))
        family = str(row.get("failure_family", "other"))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
    capacity_reasons = [row for row in reason_rows if _failure_family(row.get("reason")) == "capacity"]
    exposure_reasons = [row for row in reason_rows if _failure_family(row.get("reason")) == "exposure_challenge"]
    capacity_limited_dates = sum(int(_number(row.get("test_capacity_limited_dates"))) for row in candidates) + sum(
        int(_number(row.get("test_capacity_limited_dates"))) for row in folds
    )
    failed_exposure_challenges = [
        row
        for row in candidates
        if bool(row.get("moderate_exposure_challenge_required", False))
        and not bool(row.get("moderate_exposure_challenge_passed", False))
    ]
    common_fold_reasons = [
        str(row.get("reason", ""))
        for row in reason_rows
        if row.get("source") == "fold"
        and int(_number(row.get("fold"))) in common_failed_folds
        and _failure_family(row.get("reason")) == "cost_adjusted_long_short"
    ]
    return {
        "reason_counts": dict(sorted(reason_counts.items())),
        "failure_family_counts": dict(sorted(family_counts.items())),
        "common_failed_test_folds": common_failed_folds,
        "capacity_limited_dates": int(capacity_limited_dates),
        "capacity_not_blocker": bool(capacity_limited_dates == 0 and not capacity_reasons),
        "exposure_challenge_not_blocker": bool(not exposure_reasons and not failed_exposure_challenges),
        "shared_oos_cost_failure": bool(common_failed_folds and common_fold_reasons),
    }


def _reason_rows(candidates: Sequence[dict[str, Any]], folds: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        for reason in _as_list(candidate.get("rejection_reasons")):
            rows.append(
                {
                    "source": "candidate",
                    "factor_name": candidate.get("factor_name", ""),
                    "fold": "",
                    "reason": reason,
                    "failure_family": _failure_family(reason),
                }
            )
    for fold in folds:
        for reason in _as_list(fold.get("fold_rejection_reasons")):
            rows.append(
                {
                    "source": "fold",
                    "factor_name": fold.get("factor_name", ""),
                    "fold": int(_number(fold.get("fold"))),
                    "reason": reason,
                    "failure_family": _failure_family(reason),
                }
            )
    return rows


def _failure_family(reason: object) -> str:
    text = str(reason)
    if "capacity" in text or "participation" in text:
        return "capacity"
    if "exposure_challenge" in text:
        return "exposure_challenge"
    if "long_short" in text or "net_" in text:
        return "cost_adjusted_long_short"
    if "ic" in text:
        return "ic"
    if "accepted_folds" in text:
        return "accepted_fold_count"
    return "other"


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


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
