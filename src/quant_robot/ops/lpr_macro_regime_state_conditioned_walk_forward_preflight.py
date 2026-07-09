from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.lpr_macro_regime_factor_value_reconstruction_smoke import (
    rebuild_lpr_representative_residual_factor_values,
    _align_factor_values_to_lpr_states,
)
from quant_robot.ops.lpr_macro_regime_state_conditioned_reference_dedup import (
    STAGE as REFERENCE_DEDUP_STAGE,
    _reconstruction_preflight_from_smoke,
)
from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)


STAGE = "lpr_macro_regime_state_conditioned_walk_forward_preflight"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
NEXT_WALK_FORWARD_DIRECTION = "lpr_state_conditioned_walk_forward_cost_capacity_regime_validation"
NEXT_ROTATE_DIRECTION = "repair_or_rotate_lpr_state_conditioned_walk_forward_preflight"
DEFAULT_COST_BPS_VALUES = (5.0, 10.0, 20.0)
DEFAULT_PORTFOLIO_VALUES = (100_000.0, 500_000.0, 1_000_000.0)
DEFAULT_TOP_N_VALUES = (20, 50)
DEFAULT_REBALANCE_INTERVALS = (1, 5)
DEFAULT_EXECUTION_LAG = 1
DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD = 0.95
DEFAULT_MIN_PAIR_OBSERVATIONS = 20
DEFAULT_MIN_CORR_CROSS_SECTION = 30
DEFAULT_TRAIN_STATE_DATES = 60
DEFAULT_TEST_STATE_DATES = 20
DEFAULT_STEP_STATE_DATES = 20
DEFAULT_MIN_WALK_FORWARD_FOLDS = 2
CANDIDATE_COLUMNS = [
    "source_id",
    "factor_name",
    "base_factor_name",
    "horizon",
    "state",
    "state_dates",
    "median_cross_section",
    "reference_redundancy_class",
    "exposure_class",
    "max_exposure_name",
    "moderate_exposure_challenge_required",
    "candidate_max_abs_correlation",
    "cluster_id",
    "cluster_representative",
    "preflight_status",
    "walk_forward_frozen",
    "challenge_requirements",
    "blockers",
]
PAIR_COLUMNS = [
    "left_factor_name",
    "right_factor_name",
    "state",
    "pair_observations",
    "mean_spearman_corr",
    "mean_abs_spearman_corr",
    "max_abs_spearman_corr",
    "median_cross_section",
    "sufficient_observations",
    "similarity_class",
]
PLAN_COLUMNS = [
    "fold",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "train_state_dates",
    "test_state_dates",
    "purpose",
]


def run_lpr_macro_regime_state_conditioned_walk_forward_preflight(
    *,
    processed_root: str | Path,
    reference_dedup_path: str | Path,
    smoke_path: str | Path,
    bars_roots: Sequence[str | Path],
    daily_basic_roots: Sequence[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    output_dir: str | Path,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    train_state_dates: int = DEFAULT_TRAIN_STATE_DATES,
    test_state_dates: int = DEFAULT_TEST_STATE_DATES,
    step_state_dates: int = DEFAULT_STEP_STATE_DATES,
    min_walk_forward_folds: int = DEFAULT_MIN_WALK_FORWARD_FOLDS,
) -> dict[str, Any]:
    reference_dedup = json.loads(Path(reference_dedup_path).read_text(encoding="utf-8"))
    smoke = json.loads(Path(smoke_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    factor_frame = rebuild_lpr_representative_residual_factor_values(
        _reconstruction_preflight_from_smoke(smoke),
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_signal_date_amount=min_signal_date_amount,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    result = summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight(
        reference_dedup,
        factor_frame,
        state_frame,
        processed_root=processed_root,
        reference_dedup_path=reference_dedup_path,
        smoke_path=smoke_path,
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        market=market,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        min_signal_date_amount=min_signal_date_amount,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
        min_pair_observations=min_pair_observations,
        min_corr_cross_section=min_corr_cross_section,
        candidate_high_corr_threshold=candidate_high_corr_threshold,
        train_state_dates=train_state_dates,
        test_state_dates=test_state_dates,
        step_state_dates=step_state_dates,
        min_walk_forward_folds=min_walk_forward_folds,
    )
    write_lpr_macro_regime_state_conditioned_walk_forward_preflight(output_dir, result)
    return result


def summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight(
    reference_dedup: dict[str, Any],
    factor_frame: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    processed_root: str | Path | None = None,
    reference_dedup_path: str | Path | None = None,
    smoke_path: str | Path | None = None,
    bars_roots: Sequence[str | Path] = (),
    daily_basic_roots: Sequence[str | Path] = (),
    stock_basic: str | Path | pd.DataFrame | None = None,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    train_state_dates: int = DEFAULT_TRAIN_STATE_DATES,
    test_state_dates: int = DEFAULT_TEST_STATE_DATES,
    step_state_dates: int = DEFAULT_STEP_STATE_DATES,
    min_walk_forward_folds: int = DEFAULT_MIN_WALK_FORWARD_FOLDS,
) -> dict[str, Any]:
    global_blockers = _reference_dedup_blockers(reference_dedup)
    candidates = _candidate_inputs(reference_dedup)
    if not candidates:
        global_blockers.append("no_reference_dedup_candidates_for_walk_forward_preflight")
    aligned = _analysis_window(
        _align_factor_values_to_lpr_states(factor_frame, state_frame),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    pair_correlations = build_lpr_state_candidate_pair_correlations(
        aligned,
        candidates,
        min_corr_cross_section=min_corr_cross_section,
        min_pair_observations=min_pair_observations,
        candidate_high_corr_threshold=candidate_high_corr_threshold,
    )
    cluster_map = _cluster_candidates(candidates, pair_correlations, candidate_high_corr_threshold=candidate_high_corr_threshold)
    representatives = _cluster_representatives(candidates, cluster_map)
    candidate_table = _candidate_table(
        candidates,
        aligned,
        cluster_map=cluster_map,
        representatives=representatives,
        pair_correlations=pair_correlations,
        global_blockers=global_blockers,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
    )
    frozen = [row for row in candidate_table if row["walk_forward_frozen"]]
    walk_forward_plan = _walk_forward_plan(
        aligned,
        frozen,
        train_state_dates=train_state_dates,
        test_state_dates=test_state_dates,
        step_state_dates=step_state_dates,
    )
    decision_blockers = _unique(global_blockers)
    if not frozen:
        decision_blockers.append("no_frozen_lpr_walk_forward_candidates")
    if len(walk_forward_plan) < int(min_walk_forward_folds):
        decision_blockers.append("walk_forward_fold_count_below_threshold")
    status = "cleared" if not decision_blockers else "blocked"
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "reference_dedup_path": str(Path(reference_dedup_path)) if reference_dedup_path is not None else None,
        "smoke_path": str(Path(smoke_path)) if smoke_path is not None else None,
        "bars_roots": [str(Path(path)) for path in bars_roots],
        "daily_basic_roots": [str(Path(path)) for path in daily_basic_roots],
        "stock_basic": str(stock_basic) if isinstance(stock_basic, (str, Path)) else None,
        "thresholds": {
            "min_signal_date_amount": float(min_signal_date_amount),
            "min_state_dates": int(min_state_dates),
            "min_median_cross_section": int(min_median_cross_section),
            "min_pair_observations": int(min_pair_observations),
            "min_corr_cross_section": int(min_corr_cross_section),
            "candidate_high_corr_threshold": float(candidate_high_corr_threshold),
            "train_state_dates": int(train_state_dates),
            "test_state_dates": int(test_state_dates),
            "step_state_dates": int(step_state_dates),
            "min_walk_forward_folds": int(min_walk_forward_folds),
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
        },
        "summary": {
            "reference_dedup_candidates": len(candidates),
            "candidate_pair_rows": len(pair_correlations),
            "frozen_walk_forward_candidates": len(frozen),
            "cluster_duplicate_candidates": sum(1 for row in candidate_table if row["preflight_status"] == "cluster_duplicate"),
            "blocked_candidates": sum(1 for row in candidate_table if row["preflight_status"] == "blocked"),
            "walk_forward_folds": len(walk_forward_plan),
            "max_candidate_abs_correlation": _max_pair_abs_correlation(pair_correlations),
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": NEXT_WALK_FORWARD_DIRECTION if status == "cleared" else NEXT_ROTATE_DIRECTION,
        },
        "data_window": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "first_factor_date": _min_date(aligned, "date"),
            "last_factor_date": _max_date(aligned, "date"),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_use": "blocked_for_walk_forward_preflight",
        },
        "decision": {
            "blockers": _unique(decision_blockers),
            "walk_forward_preflight_cleared": status == "cleared",
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "preflight_policy": {
            "walk_forward_preflight_cleared": status == "cleared",
            "next_direction": NEXT_WALK_FORWARD_DIRECTION if status == "cleared" else NEXT_ROTATE_DIRECTION,
            "frozen_factor_names": [row["factor_name"] for row in frozen],
            "scope": "freeze LPR state-conditioned residual representatives; no parameter expansion before walk-forward",
            "candidate_parameter_expansion_allowed": False,
        },
        "portfolio_grid_policy": {
            "portfolio_grid_allowed": False,
            "top_n_values": list(DEFAULT_TOP_N_VALUES),
            "holding_periods": sorted({int(row.get("horizon", 0)) for row in frozen if int(row.get("horizon", 0)) > 0}) or [5],
            "rebalance_intervals": list(DEFAULT_REBALANCE_INTERVALS),
            "execution_lag": DEFAULT_EXECUTION_LAG,
            "cost_bps_values": list(DEFAULT_COST_BPS_VALUES),
            "portfolio_values": list(DEFAULT_PORTFOLIO_VALUES),
            "parameter_expansion_allowed": False,
        },
        "regime_validation_policy": {
            "must_report_allowed_and_blocked_lpr_state_dates": True,
            "standalone_lpr_macro_alpha_claim_allowed": False,
            "state_filter": "gap_widening representatives only unless later gates expand scope",
        },
        "candidate_table": candidate_table,
        "frozen_candidates": frozen,
        "candidate_pair_correlations": pair_correlations,
        "walk_forward_plan": walk_forward_plan,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "walk_forward_not_run",
                "cost_capacity_stress_not_run",
                "regime_coverage_not_run",
                "final_holdout_not_read",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_state_conditioned_walk_forward_preflight_markdown(result)
    return result


def build_lpr_state_candidate_pair_correlations(
    aligned_factor_frame: pd.DataFrame,
    candidates: Sequence[dict[str, Any]],
    *,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            state = left["state"] if left["state"] == right["state"] else f"{left['state']}|{right['state']}"
            frame = aligned_factor_frame[
                aligned_factor_frame["factor_name"].isin({left["factor_name"], right["factor_name"]})
                & aligned_factor_frame[STATE_COLUMN].isin({left["state"], right["state"]})
            ].copy()
            observations = []
            for _, group in frame.groupby("date", sort=True):
                pivot = group.pivot_table(index="asset_id", columns="factor_name", values="factor_value", aggfunc="last")
                if left["factor_name"] not in pivot.columns or right["factor_name"] not in pivot.columns:
                    continue
                paired = pivot[[left["factor_name"], right["factor_name"]]].dropna()
                if len(paired) < int(min_corr_cross_section):
                    continue
                corr = paired[left["factor_name"]].rank(method="average").corr(
                    paired[right["factor_name"]].rank(method="average")
                )
                if pd.isna(corr):
                    continue
                observations.append({"corr": float(corr), "cross_section": float(len(paired))})
            abs_corrs = [abs(item["corr"]) for item in observations]
            corr_values = [item["corr"] for item in observations]
            max_abs = float(max(abs_corrs)) if abs_corrs else 0.0
            sufficient = len(observations) >= int(min_pair_observations)
            rows.append(
                {
                    "left_factor_name": left["factor_name"],
                    "right_factor_name": right["factor_name"],
                    "state": state,
                    "pair_observations": int(len(observations)),
                    "mean_spearman_corr": float(sum(corr_values) / len(corr_values)) if corr_values else 0.0,
                    "mean_abs_spearman_corr": float(sum(abs_corrs) / len(abs_corrs)) if abs_corrs else 0.0,
                    "max_abs_spearman_corr": max_abs,
                    "median_cross_section": float(pd.Series([item["cross_section"] for item in observations]).median()) if observations else 0.0,
                    "sufficient_observations": bool(sufficient),
                    "similarity_class": _pair_similarity_class(
                        max_abs,
                        sufficient=sufficient,
                        candidate_high_corr_threshold=candidate_high_corr_threshold,
                    ),
                }
            )
    return rows


def write_lpr_macro_regime_state_conditioned_walk_forward_preflight(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_state_conditioned_walk_forward_preflight.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_state_conditioned_walk_forward_preflight.md").write_text(
        render_lpr_macro_regime_state_conditioned_walk_forward_preflight_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "lpr_macro_regime_state_conditioned_walk_forward_candidates.csv", clean["candidate_table"], CANDIDATE_COLUMNS)
    _write_csv(
        output_path / "lpr_macro_regime_state_conditioned_candidate_pair_correlations.csv",
        clean["candidate_pair_correlations"],
        PAIR_COLUMNS,
    )
    _write_csv(output_path / "lpr_macro_regime_state_conditioned_walk_forward_plan.csv", clean["walk_forward_plan"], PLAN_COLUMNS)


def render_lpr_macro_regime_state_conditioned_walk_forward_preflight_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    policy = result.get("preflight_policy", {})
    lines = [
        "# LPR Macro Regime State-Conditioned Walk-Forward Preflight",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Reference-dedup candidates: {summary.get('reference_dedup_candidates', 0)}",
        f"- Frozen walk-forward candidates: {summary.get('frozen_walk_forward_candidates', 0)}",
        f"- Cluster duplicates: {summary.get('cluster_duplicate_candidates', 0)}",
        f"- Walk-forward folds planned: {summary.get('walk_forward_folds', 0)}",
        f"- Max candidate abs corr: {float(summary.get('max_candidate_abs_correlation', 0.0) or 0.0):.3f}",
        f"- Walk-forward preflight cleared: {policy.get('walk_forward_preflight_cleared', False)}",
        f"- Portfolio grid allowed: {result.get('portfolio_grid_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{policy.get('next_direction', NEXT_ROTATE_DIRECTION)}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Freeze Table",
        "",
        "| Factor | State | Dates | CS | Exposure | Challenge | Corr | Cluster | Status | Frozen | Blockers |",
        "|---|---|---:|---:|---|---|---:|---:|---|---|---|",
    ]
    for row in result.get("candidate_table", []):
        lines.append(
            "| {factor} | {state} | {dates} | {cs:.1f} | {exp} | {challenge} | {corr:.3f} | {cluster} | {status} | {frozen} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                dates=row.get("state_dates", 0),
                cs=float(row.get("median_cross_section", 0.0) or 0.0),
                exp=row.get("exposure_class", ""),
                challenge="yes" if row.get("moderate_exposure_challenge_required", False) else "no",
                corr=float(row.get("candidate_max_abs_correlation", 0.0) or 0.0),
                cluster=row.get("cluster_id", 0),
                status=row.get("preflight_status", ""),
                frozen="yes" if row.get("walk_forward_frozen", False) else "no",
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
            )
        )
    lines.extend(["", "## Walk-Forward Plan", ""])
    for fold in result.get("walk_forward_plan", []):
        lines.append(
            "- Fold {fold}: train {train_start} to {train_end}, test {test_start} to {test_end} ({purpose})".format(
                **fold
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
            "- This preflight freezes candidates and walk-forward fold definitions only.",
            "- It does not run portfolio construction, profit validation, promotion gates, paper signals, or live signals.",
            "- Moderate exposure challenges must be explicitly reported in the later walk-forward validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_table(
    candidates: Sequence[dict[str, Any]],
    aligned: pd.DataFrame,
    *,
    cluster_map: dict[tuple[str, str], int],
    representatives: dict[int, tuple[str, str]],
    pair_correlations: Sequence[dict[str, Any]],
    global_blockers: Sequence[str],
    min_state_dates: int,
    min_median_cross_section: int,
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        key = _candidate_key(candidate)
        state_rows = aligned[(aligned["factor_name"] == candidate["factor_name"]) & (aligned[STATE_COLUMN] == candidate["state"])]
        cross_sections = state_rows.groupby("date")["asset_id"].nunique() if not state_rows.empty else pd.Series(dtype=float)
        median_cross_section = float(cross_sections.median()) if not cross_sections.empty else 0.0
        cluster_id = cluster_map.get(key, 0)
        representative = representatives.get(cluster_id) == key
        candidate_max_corr = _candidate_max_pair_corr(pair_correlations, candidate["factor_name"], candidate["state"])
        blockers = list(global_blockers)
        if int(candidate.get("state_dates", 0) or 0) < int(min_state_dates):
            blockers.append("reference_dedup_state_dates_below_threshold")
        if float(candidate.get("median_cross_section", 0.0) or 0.0) < float(min_median_cross_section):
            blockers.append("reference_dedup_median_cross_section_below_threshold")
        if state_rows["date"].nunique() < int(min_state_dates):
            blockers.append("factor_value_state_dates_below_threshold")
        if median_cross_section < float(min_median_cross_section):
            blockers.append("factor_value_median_cross_section_below_threshold")
        if not candidate.get("state_conditioned_reference_dedup_pass", False):
            blockers.append("state_conditioned_reference_dedup_candidate_not_passing")
        if not candidate.get("walk_forward_preflight_allowed_next", False):
            blockers.append("candidate_not_allowed_for_walk_forward_preflight")
        if not representative:
            blockers.append("factor_value_duplicate_or_high_similarity_with_lower_exposure_candidate")
        moderate_challenge = _moderate_exposure_challenge_required(candidate)
        challenge_requirements = []
        if moderate_challenge:
            exposure_name = str(candidate.get("max_exposure_name", "style_exposure") or "style_exposure")
            challenge_requirements.append(f"challenge_{exposure_name}_exposure_in_walk_forward")
        status = "blocked" if blockers else "frozen"
        if blockers == ["factor_value_duplicate_or_high_similarity_with_lower_exposure_candidate"]:
            status = "cluster_duplicate"
        elif "factor_value_duplicate_or_high_similarity_with_lower_exposure_candidate" in blockers and not global_blockers:
            status = "cluster_duplicate"
        rows.append(
            {
                **candidate,
                "state_dates": int(state_rows["date"].nunique()) if "date" in state_rows else 0,
                "median_cross_section": median_cross_section,
                "candidate_max_abs_correlation": candidate_max_corr,
                "cluster_id": int(cluster_id),
                "cluster_representative": representatives.get(cluster_id, key)[0] if cluster_id else "",
                "moderate_exposure_challenge_required": bool(moderate_challenge),
                "challenge_requirements": challenge_requirements,
                "preflight_status": status,
                "walk_forward_frozen": bool(status == "frozen"),
                "blockers": _unique(blockers),
            }
        )
    return rows


def _reference_dedup_blockers(reference_dedup: dict[str, Any]) -> list[str]:
    decision = _dict(reference_dedup.get("decision"))
    blockers = []
    if reference_dedup.get("stage") != REFERENCE_DEDUP_STAGE:
        blockers.append("reference_dedup_stage_mismatch")
    if _dict(reference_dedup.get("summary")).get("passes") is not True:
        blockers.append("reference_dedup_not_passing")
    if decision.get("walk_forward_preflight_allowed_next") is not True:
        blockers.append("reference_dedup_not_allowed_for_walk_forward_preflight")
    if decision.get("walk_forward_preflight_allowed") is not False:
        blockers.append("reference_dedup_walk_forward_boundary_violation")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("reference_dedup_policy_boundary_violation")
    if reference_dedup.get("live_boundary_allowed") is not False:
        blockers.append("reference_dedup_live_boundary_violation")
    return blockers


def _candidate_inputs(reference_dedup: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in reference_dedup.get("candidate_results", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "source_id": str(row.get("source_id", "")),
                "factor_name": str(row.get("factor_name", "")),
                "base_factor_name": str(row.get("base_factor_name", "")),
                "horizon": int(row.get("horizon", 0)),
                "state": str(row.get("state", "")),
                "state_dates": int(row.get("state_dates", 0) or 0),
                "median_cross_section": float(row.get("median_cross_section", 0.0) or 0.0),
                "reference_redundancy_class": str(row.get("reference_redundancy_class", "")),
                "exposure_class": str(row.get("exposure_class", "")),
                "max_reference_abs_correlation": float(row.get("max_reference_abs_correlation", 0.0) or 0.0),
                "max_exposure_abs_correlation": float(row.get("max_exposure_abs_correlation", 0.0) or 0.0),
                "max_exposure_name": str(row.get("max_exposure_name", "")),
                "state_conditioned_reference_dedup_pass": bool(row.get("state_conditioned_reference_dedup_pass", False)),
                "walk_forward_preflight_allowed_next": bool(row.get("walk_forward_preflight_allowed_next", False)),
                "requirements": _as_list(row.get("requirements")),
            }
        )
    return rows


def _cluster_candidates(
    candidates: Sequence[dict[str, Any]],
    pair_correlations: Sequence[dict[str, Any]],
    *,
    candidate_high_corr_threshold: float,
) -> dict[tuple[str, str], int]:
    keys = [_candidate_key(row) for row in candidates]
    parent = {key: key for key in keys}

    def find(key: tuple[str, str]) -> tuple[str, str]:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left: tuple[str, str], right: tuple[str, str]) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for row in pair_correlations:
        if row.get("sufficient_observations") is not True:
            continue
        if float(row.get("max_abs_spearman_corr", 0.0) or 0.0) < float(candidate_high_corr_threshold):
            continue
        left = (str(row["left_factor_name"]), str(row["state"]))
        right = (str(row["right_factor_name"]), str(row["state"]))
        if left in parent and right in parent:
            union(left, right)
    roots = {}
    cluster_map = {}
    for key in keys:
        root = find(key)
        if root not in roots:
            roots[root] = len(roots) + 1
        cluster_map[key] = roots[root]
    return cluster_map


def _cluster_representatives(
    candidates: Sequence[dict[str, Any]],
    cluster_map: dict[tuple[str, str], int],
) -> dict[int, tuple[str, str]]:
    by_cluster: dict[int, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_cluster.setdefault(cluster_map[_candidate_key(candidate)], []).append(candidate)
    reps = {}
    for cluster_id, rows in by_cluster.items():
        best = sorted(
            rows,
            key=lambda row: (
                _exposure_rank(row.get("exposure_class")),
                float(row.get("max_exposure_abs_correlation", 0.0) or 0.0),
                float(row.get("max_reference_abs_correlation", 0.0) or 0.0),
                str(row.get("factor_name", "")),
            ),
        )[0]
        reps[cluster_id] = _candidate_key(best)
    return reps


def _walk_forward_plan(
    aligned: pd.DataFrame,
    frozen: Sequence[dict[str, Any]],
    *,
    train_state_dates: int,
    test_state_dates: int,
    step_state_dates: int,
) -> list[dict[str, Any]]:
    names = {row["factor_name"] for row in frozen}
    states = {row["state"] for row in frozen}
    frame = aligned[aligned["factor_name"].isin(names) & aligned[STATE_COLUMN].isin(states)].copy()
    dates = sorted(pd.Timestamp(value) for value in frame["date"].dropna().unique()) if not frame.empty else []
    rows = []
    limit = len(dates) - int(train_state_dates) - int(test_state_dates) + 1
    if limit < 1:
        return rows
    fold = 1
    for start in range(0, limit, max(int(step_state_dates), 1)):
        train_slice = dates[start : start + int(train_state_dates)]
        test_slice = dates[start + int(train_state_dates) : start + int(train_state_dates) + int(test_state_dates)]
        if len(train_slice) < int(train_state_dates) or len(test_slice) < int(test_state_dates):
            continue
        rows.append(
            {
                "fold": int(fold),
                "train_start": train_slice[0].date().isoformat(),
                "train_end": train_slice[-1].date().isoformat(),
                "test_start": test_slice[0].date().isoformat(),
                "test_end": test_slice[-1].date().isoformat(),
                "train_state_dates": int(len(train_slice)),
                "test_state_dates": int(len(test_slice)),
                "purpose": "preflight_plan_only_no_validation_run",
            }
        )
        fold += 1
    return rows


def _analysis_window(frame: pd.DataFrame, *, analysis_start_date: str, analysis_end_date: str) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame.copy()
    output = frame[
        (frame["date"] >= pd.Timestamp(analysis_start_date))
        & (frame["date"] <= pd.Timestamp(analysis_end_date))
        & (frame["date"] < pd.Timestamp(FINAL_HOLDOUT_START))
    ].copy()
    return output.reset_index(drop=True)


def _pair_similarity_class(max_abs_corr: float, *, sufficient: bool, candidate_high_corr_threshold: float) -> str:
    if not sufficient:
        return "insufficient_overlap"
    if float(max_abs_corr) >= float(candidate_high_corr_threshold):
        return "high_factor_value_similarity"
    if float(max_abs_corr) >= 0.75:
        return "moderate_factor_value_similarity"
    return "distinct_factor_value"


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, str]:
    return (str(candidate["factor_name"]), str(candidate["state"]))


def _candidate_max_pair_corr(pair_correlations: Sequence[dict[str, Any]], factor_name: str, state: str) -> float:
    values = []
    for row in pair_correlations:
        if str(row.get("state")) != str(state):
            continue
        if factor_name in {row.get("left_factor_name"), row.get("right_factor_name")}:
            values.append(float(row.get("max_abs_spearman_corr", 0.0) or 0.0))
    return max(values) if values else 0.0


def _max_pair_abs_correlation(pair_correlations: Sequence[dict[str, Any]]) -> float:
    values = [float(row.get("max_abs_spearman_corr", 0.0) or 0.0) for row in pair_correlations]
    return max(values) if values else 0.0


def _moderate_exposure_challenge_required(candidate: dict[str, Any]) -> bool:
    if str(candidate.get("exposure_class", "")) == "moderate_exposure":
        return True
    return "state_conditioned_moderate_exposure_requires_walk_forward_challenge" in set(
        _as_list(candidate.get("requirements"))
    )


def _exposure_rank(value: Any) -> int:
    return {
        "low_exposure": 0,
        "moderate_exposure": 1,
        "high_exposure": 2,
        "insufficient_overlap": 3,
        "missing": 4,
    }.get(str(value), 4)


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            for field in ("blockers", "challenge_requirements", "requirements"):
                if isinstance(clean.get(field), list):
                    clean[field] = "|".join(str(item) for item in clean[field])
            writer.writerow(clean)


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _unique(values: Iterable[Any]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            output.append(text)
            seen.add(text)
    return output
