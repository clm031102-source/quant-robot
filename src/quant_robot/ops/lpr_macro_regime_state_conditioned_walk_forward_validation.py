from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.lpr_macro_regime_factor_value_reconstruction_smoke import (
    rebuild_lpr_representative_residual_factor_values,
    _align_factor_values_to_lpr_states,
)
from quant_robot.ops.lpr_macro_regime_state_conditioned_reference_dedup import (
    _reconstruction_preflight_from_smoke,
)
from quant_robot.ops.lpr_macro_regime_state_conditioned_walk_forward_preflight import (
    STAGE as PREFLIGHT_STAGE,
)
from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.public_trend_strength_state_residual_prescreen import (
    build_public_trend_strength_state_bar_features,
    build_public_trend_strength_state_exposure_frame,
    _stock_basic_frame,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "lpr_macro_regime_state_conditioned_walk_forward_validation"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
NEXT_REALITY_CHECK_DIRECTION = "lpr_state_conditioned_statistical_reality_check_and_final_holdout_readiness"
NEXT_REPAIR_OR_ROTATE_DIRECTION = "repair_or_rotate_lpr_state_conditioned_walk_forward_validation"
CANDIDATE_COLUMNS = [
    "factor_name",
    "state",
    "horizon",
    "validation_status",
    "accepted_folds",
    "folds",
    "positive_test_fold_rate",
    "mean_test_ic",
    "mean_test_ic_t_stat",
    "mean_test_long_short_net_mean",
    "mean_test_long_short_net_total",
    "mean_test_long_short_net_positive_rate",
    "max_test_participation_rate",
    "test_capacity_limited_dates",
    "moderate_exposure_challenge_required",
    "moderate_exposure_challenge_passed",
    "exposure_challenge_mean_abs_corr",
    "exposure_challenge_max_abs_corr",
    "rejection_reasons",
    "rank",
]
FOLD_COLUMNS = [
    "factor_name",
    "state",
    "fold",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "fold_status",
    "train_ic_observations",
    "test_ic_observations",
    "train_mean_ic",
    "test_mean_ic",
    "train_ic_t_stat",
    "test_ic_t_stat",
    "test_positive_ic_rate",
    "train_long_short_net_mean",
    "test_long_short_net_mean",
    "train_long_short_net_total",
    "test_long_short_net_total",
    "test_long_short_net_positive_rate",
    "test_selected_dates",
    "test_median_selected_assets",
    "test_capacity_limited_dates",
    "test_max_participation_rate",
    "exposure_challenge_mean_abs_corr",
    "exposure_challenge_max_abs_corr",
    "fold_rejection_reasons",
]
REGIME_COLUMNS = ["fold", "window", "state", "dates", "min_date", "max_date", "is_allowed_state"]


def run_lpr_macro_regime_state_conditioned_walk_forward_validation(
    *,
    processed_root: str | Path,
    preflight_path: str | Path,
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
    execution_lag: int = 1,
    cost_bps: float = 10.0,
    portfolio_value: float = 1_000_000.0,
    max_participation_rate: float = 0.01,
    quantiles: int = 5,
    min_ic_observations: int = 10,
    min_ic_cross_section: int = 30,
    min_selected_assets: int = 20,
    min_test_positive_ic_rate: float = 0.50,
    min_test_long_short_positive_rate: float = 0.50,
    min_accepted_folds: int = 2,
    min_regime_allowed_dates: int = 1,
    min_regime_blocked_dates: int = 1,
    max_exposure_challenge_mean_abs_corr: float = 0.45,
    max_exposure_challenge_max_abs_corr: float = 0.85,
) -> dict[str, Any]:
    preflight = json.loads(Path(preflight_path).read_text(encoding="utf-8"))
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
    candidates = _frozen_candidates(preflight)
    horizons = tuple(sorted({int(row["horizon"]) for row in candidates if int(row["horizon"]) > 0})) or (5,)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    features = build_public_trend_strength_state_bar_features(bars, horizons=horizons, execution_lag=execution_lag)
    exposure_frame = build_public_trend_strength_state_exposure_frame(features, _stock_basic_frame(stock_basic))
    result = summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
        preflight,
        factor_frame,
        bars,
        state_frame,
        exposure_frame=exposure_frame,
        processed_root=processed_root,
        preflight_path=preflight_path,
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
        execution_lag=execution_lag,
        cost_bps=cost_bps,
        portfolio_value=portfolio_value,
        max_participation_rate=max_participation_rate,
        quantiles=quantiles,
        min_ic_observations=min_ic_observations,
        min_ic_cross_section=min_ic_cross_section,
        min_selected_assets=min_selected_assets,
        min_test_positive_ic_rate=min_test_positive_ic_rate,
        min_test_long_short_positive_rate=min_test_long_short_positive_rate,
        min_accepted_folds=min_accepted_folds,
        min_regime_allowed_dates=min_regime_allowed_dates,
        min_regime_blocked_dates=min_regime_blocked_dates,
        max_exposure_challenge_mean_abs_corr=max_exposure_challenge_mean_abs_corr,
        max_exposure_challenge_max_abs_corr=max_exposure_challenge_max_abs_corr,
    )
    write_lpr_macro_regime_state_conditioned_walk_forward_validation(output_dir, result)
    return result


def summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
    preflight: dict[str, Any],
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    exposure_frame: pd.DataFrame | None = None,
    processed_root: str | Path | None = None,
    preflight_path: str | Path | None = None,
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
    execution_lag: int = 1,
    cost_bps: float = 10.0,
    portfolio_value: float = 1_000_000.0,
    max_participation_rate: float = 0.01,
    quantiles: int = 5,
    min_ic_observations: int = 10,
    min_ic_cross_section: int = 3,
    min_selected_assets: int = 20,
    min_test_positive_ic_rate: float = 0.50,
    min_test_long_short_positive_rate: float = 0.50,
    min_accepted_folds: int = 2,
    min_regime_allowed_dates: int = 1,
    min_regime_blocked_dates: int = 1,
    max_exposure_challenge_mean_abs_corr: float = 0.45,
    max_exposure_challenge_max_abs_corr: float = 0.85,
) -> dict[str, Any]:
    preflight_blockers = _preflight_blockers(preflight)
    candidates = _frozen_candidates(preflight)
    fold_plan = _fold_plan(preflight)
    if not candidates:
        preflight_blockers.append("no_frozen_lpr_candidates")
    if not fold_plan:
        preflight_blockers.append("walk_forward_plan_missing")
    prepared_factors = _analysis_window(
        _align_factor_values_to_lpr_states(_prepare_factor_frame(factor_frame), state_frame),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    prepared_bars = _prepare_bars(bars)
    labels = make_forward_returns(
        _analysis_window(prepared_bars, analysis_start_date=analysis_start_date, analysis_end_date=analysis_end_date),
        horizons=tuple(sorted({candidate["horizon"] for candidate in candidates if candidate["horizon"] > 0})) or (5,),
        execution_lag=execution_lag,
    )
    exposures = _prepare_exposure_frame(exposure_frame, prepared_bars)
    merged = _merge_validation_frame(prepared_factors, labels, exposures)
    regime_coverage = _regime_coverage_rows(
        state_frame,
        fold_plan,
        allowed_states={candidate["state"] for candidate in candidates},
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    coverage_summary = _regime_coverage_summary(regime_coverage)
    global_blockers = list(preflight_blockers)
    if coverage_summary["allowed_dates"] < int(min_regime_allowed_dates):
        global_blockers.append("lpr_allowed_state_dates_below_threshold")
    if coverage_summary["blocked_dates"] < int(min_regime_blocked_dates):
        global_blockers.append("lpr_blocked_state_dates_below_threshold")
    fold_results: list[dict[str, Any]] = []
    candidate_results: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_fold_rows = []
        for fold in fold_plan:
            row = _evaluate_fold(
                merged,
                candidate,
                fold,
                global_blockers=global_blockers,
                cost_bps=cost_bps,
                portfolio_value=portfolio_value,
                max_participation_rate=max_participation_rate,
                min_signal_date_amount=min_signal_date_amount,
                quantiles=quantiles,
                min_ic_observations=min_ic_observations,
                min_ic_cross_section=min_ic_cross_section,
                min_selected_assets=min_selected_assets,
                min_test_positive_ic_rate=min_test_positive_ic_rate,
                min_test_long_short_positive_rate=min_test_long_short_positive_rate,
                max_exposure_challenge_mean_abs_corr=max_exposure_challenge_mean_abs_corr,
                max_exposure_challenge_max_abs_corr=max_exposure_challenge_max_abs_corr,
            )
            candidate_fold_rows.append(row)
            fold_results.append(row)
        candidate_results.append(
            _candidate_result(
                candidate,
                candidate_fold_rows,
                min_accepted_folds=min_accepted_folds,
            )
        )
    candidate_results = _rank_candidates(candidate_results)
    accepted = [row for row in candidate_results if row["validation_status"] == "accepted"]
    decision_blockers = _unique(global_blockers)
    if not accepted:
        decision_blockers.append("no_accepted_lpr_walk_forward_candidates")
    status = "blocked" if preflight_blockers else ("accepted" if accepted else "rejected")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "preflight_path": str(Path(preflight_path)) if preflight_path is not None else None,
        "smoke_path": str(Path(smoke_path)) if smoke_path is not None else None,
        "bars_roots": [str(Path(path)) for path in bars_roots],
        "daily_basic_roots": [str(Path(path)) for path in daily_basic_roots],
        "stock_basic": str(stock_basic) if isinstance(stock_basic, (str, Path)) else None,
        "summary": {
            "frozen_candidates": len(candidates),
            "accepted_candidates": len(accepted),
            "rejected_candidates": len(candidate_results) - len(accepted),
            "fold_results": len(fold_results),
            "accepted_folds": sum(1 for row in fold_results if row["fold_status"] == "accepted"),
            "regime_allowed_dates": coverage_summary["allowed_dates"],
            "regime_blocked_dates": coverage_summary["blocked_dates"],
            "next_direction": NEXT_REALITY_CHECK_DIRECTION if accepted and not preflight_blockers else NEXT_REPAIR_OR_ROTATE_DIRECTION,
        },
        "thresholds": {
            "execution_lag": int(execution_lag),
            "cost_bps": float(cost_bps),
            "portfolio_value": float(portfolio_value),
            "max_participation_rate": float(max_participation_rate),
            "quantiles": int(quantiles),
            "min_signal_date_amount": float(min_signal_date_amount),
            "min_ic_observations": int(min_ic_observations),
            "min_ic_cross_section": int(min_ic_cross_section),
            "min_selected_assets": int(min_selected_assets),
            "min_test_positive_ic_rate": float(min_test_positive_ic_rate),
            "min_test_long_short_positive_rate": float(min_test_long_short_positive_rate),
            "min_accepted_folds": int(min_accepted_folds),
            "min_regime_allowed_dates": int(min_regime_allowed_dates),
            "min_regime_blocked_dates": int(min_regime_blocked_dates),
            "max_exposure_challenge_mean_abs_corr": float(max_exposure_challenge_mean_abs_corr),
            "max_exposure_challenge_max_abs_corr": float(max_exposure_challenge_max_abs_corr),
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
        },
        "data_window": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "first_factor_date": _min_date(prepared_factors, "date"),
            "last_factor_date": _max_date(prepared_factors, "date"),
            "label_rows": int(len(labels)),
            "validation_rows": int(len(merged)),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_included": False,
            "final_holdout_use": "blocked_until_statistical_reality_check_and_final_holdout_readiness",
        },
        "decision": {
            "blockers": _unique(decision_blockers),
            "statistical_reality_check_allowed_next": bool(accepted and not preflight_blockers),
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "portfolio_grid_policy": {
            "portfolio_grid_allowed": False,
            "parameter_expansion_allowed": False,
            "validated_single_policy_only": True,
        },
        "candidate_results": candidate_results,
        "fold_results": fold_results,
        "regime_coverage": regime_coverage,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "statistical_reality_check_not_run",
                "multiple_testing_haircut_not_run",
                "final_holdout_not_read",
                "paper_lane_not_approved",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_state_conditioned_walk_forward_validation_markdown(result)
    return result


def write_lpr_macro_regime_state_conditioned_walk_forward_validation(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_state_conditioned_walk_forward_validation.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_state_conditioned_walk_forward_validation.md").write_text(
        render_lpr_macro_regime_state_conditioned_walk_forward_validation_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "lpr_macro_regime_state_conditioned_walk_forward_candidates.csv", clean["candidate_results"], CANDIDATE_COLUMNS)
    _write_csv(output_path / "lpr_macro_regime_state_conditioned_walk_forward_folds.csv", clean["fold_results"], FOLD_COLUMNS)
    _write_csv(output_path / "lpr_macro_regime_state_conditioned_regime_coverage.csv", clean["regime_coverage"], REGIME_COLUMNS)


def render_lpr_macro_regime_state_conditioned_walk_forward_validation_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    lines = [
        "# LPR Macro Regime State-Conditioned Walk-Forward Validation",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Frozen candidates: {summary.get('frozen_candidates', 0)}",
        f"- Accepted candidates: {summary.get('accepted_candidates', 0)}",
        f"- Rejected candidates: {summary.get('rejected_candidates', 0)}",
        f"- Fold rows: {summary.get('fold_results', 0)}",
        f"- Accepted folds: {summary.get('accepted_folds', 0)}",
        f"- LPR allowed dates: {summary.get('regime_allowed_dates', 0)}",
        f"- LPR blocked dates: {summary.get('regime_blocked_dates', 0)}",
        f"- Statistical reality check allowed next: {decision.get('statistical_reality_check_allowed_next', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Results",
        "",
        "| Rank | Factor | State | Status | Folds | Test IC | Test Net Mean | Test Net Total | Cap Dates | Exposure Challenge | Reasons |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("candidate_results", []):
        lines.append(
            "| {rank} | {factor} | {state} | {status} | {accepted}/{folds} | {ic:.4f} | {net_mean:.4f} | {net_total:.4f} | {cap} | {challenge} | {reasons} |".format(
                rank=int(_number(row.get("rank"))),
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                status=row.get("validation_status", ""),
                accepted=int(_number(row.get("accepted_folds"))),
                folds=int(_number(row.get("folds"))),
                ic=_number(row.get("mean_test_ic")),
                net_mean=_number(row.get("mean_test_long_short_net_mean")),
                net_total=_number(row.get("mean_test_long_short_net_total")),
                cap=int(_number(row.get("test_capacity_limited_dates"))),
                challenge="pass" if row.get("moderate_exposure_challenge_passed", False) else "fail",
                reasons=", ".join(_as_list(row.get("rejection_reasons"))) or "none",
            )
        )
    lines.extend(["", "## Decision Blockers", ""])
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is walk-forward validation evidence only, not a promotion or paper-ready gate.",
            "- Portfolio grids, parameter expansion, final holdout, paper signals, and live boundaries remain closed.",
            "- Accepted candidates still require statistical reality checks and final-holdout readiness review.",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_fold(
    merged: pd.DataFrame,
    candidate: dict[str, Any],
    fold: dict[str, Any],
    *,
    global_blockers: Sequence[str],
    cost_bps: float,
    portfolio_value: float,
    max_participation_rate: float,
    min_signal_date_amount: float,
    quantiles: int,
    min_ic_observations: int,
    min_ic_cross_section: int,
    min_selected_assets: int,
    min_test_positive_ic_rate: float,
    min_test_long_short_positive_rate: float,
    max_exposure_challenge_mean_abs_corr: float,
    max_exposure_challenge_max_abs_corr: float,
) -> dict[str, Any]:
    frame = merged[
        (merged["factor_name"] == candidate["factor_name"])
        & (merged["horizon"] == int(candidate["horizon"]))
        & (merged[STATE_COLUMN] == candidate["state"])
    ].copy()
    train = _window_metrics(
        _slice_dates(frame, fold["train_start"], fold["train_end"]),
        candidate,
        cost_bps=cost_bps,
        portfolio_value=portfolio_value,
        max_participation_rate=max_participation_rate,
        min_signal_date_amount=min_signal_date_amount,
        quantiles=quantiles,
        min_ic_cross_section=min_ic_cross_section,
        min_selected_assets=min_selected_assets,
    )
    test = _window_metrics(
        _slice_dates(frame, fold["test_start"], fold["test_end"]),
        candidate,
        cost_bps=cost_bps,
        portfolio_value=portfolio_value,
        max_participation_rate=max_participation_rate,
        min_signal_date_amount=min_signal_date_amount,
        quantiles=quantiles,
        min_ic_cross_section=min_ic_cross_section,
        min_selected_assets=min_selected_assets,
    )
    reasons = list(global_blockers)
    if train["ic_observations"] < int(min_ic_observations):
        reasons.append("train_ic_observations_below_threshold")
    if test["ic_observations"] < int(min_ic_observations):
        reasons.append("test_ic_observations_below_threshold")
    if test["mean_ic"] <= 0.0:
        reasons.append("test_mean_ic_non_positive")
    if test["positive_ic_rate"] < float(min_test_positive_ic_rate):
        reasons.append("test_positive_ic_rate_below_threshold")
    if test["long_short_net_mean"] <= 0.0:
        reasons.append("test_long_short_net_mean_non_positive")
    if test["long_short_net_total"] <= 0.0:
        reasons.append("test_long_short_net_total_non_positive")
    if test["long_short_net_positive_rate"] < float(min_test_long_short_positive_rate):
        reasons.append("test_long_short_net_positive_rate_below_threshold")
    if test["capacity_limited_dates"] > 0:
        reasons.append("test_capacity_limited_dates_present")
    if _moderate_exposure_challenge_required(candidate):
        if test["exposure_challenge_observations"] <= 0:
            reasons.append("moderate_exposure_challenge_missing")
        if test["exposure_challenge_mean_abs_corr"] > float(max_exposure_challenge_mean_abs_corr):
            reasons.append("moderate_exposure_challenge_mean_abs_corr_above_limit")
        if test["exposure_challenge_max_abs_corr"] > float(max_exposure_challenge_max_abs_corr):
            reasons.append("moderate_exposure_challenge_max_abs_corr_above_limit")
    return {
        "factor_name": candidate["factor_name"],
        "state": candidate["state"],
        "fold": fold["fold"],
        "train_start": fold["train_start"],
        "train_end": fold["train_end"],
        "test_start": fold["test_start"],
        "test_end": fold["test_end"],
        "fold_status": "accepted" if not reasons else "rejected",
        "train_ic_observations": int(train["ic_observations"]),
        "test_ic_observations": int(test["ic_observations"]),
        "train_mean_ic": train["mean_ic"],
        "test_mean_ic": test["mean_ic"],
        "train_ic_t_stat": train["ic_t_stat"],
        "test_ic_t_stat": test["ic_t_stat"],
        "test_positive_ic_rate": test["positive_ic_rate"],
        "train_long_short_net_mean": train["long_short_net_mean"],
        "test_long_short_net_mean": test["long_short_net_mean"],
        "train_long_short_net_total": train["long_short_net_total"],
        "test_long_short_net_total": test["long_short_net_total"],
        "test_long_short_net_positive_rate": test["long_short_net_positive_rate"],
        "test_selected_dates": int(test["selected_dates"]),
        "test_median_selected_assets": test["median_selected_assets"],
        "test_capacity_limited_dates": int(test["capacity_limited_dates"]),
        "test_max_participation_rate": test["max_participation_rate"],
        "exposure_challenge_mean_abs_corr": test["exposure_challenge_mean_abs_corr"],
        "exposure_challenge_max_abs_corr": test["exposure_challenge_max_abs_corr"],
        "fold_rejection_reasons": _unique(reasons),
    }


def _window_metrics(
    frame: pd.DataFrame,
    candidate: dict[str, Any],
    *,
    cost_bps: float,
    portfolio_value: float,
    max_participation_rate: float,
    min_signal_date_amount: float,
    quantiles: int,
    min_ic_cross_section: int,
    min_selected_assets: int,
) -> dict[str, Any]:
    ic_values: list[float] = []
    long_short_net: list[float] = []
    selected_counts: list[int] = []
    participation_values: list[float] = []
    capacity_limited_dates = 0
    exposure_corrs: list[float] = []
    exposure_name = str(candidate.get("max_exposure_name", ""))
    for _, group in frame.groupby("date", sort=True):
        valid = group.dropna(subset=["factor_value", "forward_return"]).copy()
        if len(valid) >= int(min_ic_cross_section):
            corr = valid["factor_value"].rank(method="average").corr(valid["forward_return"].rank(method="average"))
            if _is_finite(corr):
                ic_values.append(float(corr))
        if exposure_name and exposure_name in valid and len(valid.dropna(subset=[exposure_name])) >= int(min_ic_cross_section):
            exposure_corr = valid["factor_value"].rank(method="average").corr(
                pd.to_numeric(valid[exposure_name], errors="coerce").rank(method="average")
            )
            if _is_finite(exposure_corr):
                exposure_corrs.append(float(exposure_corr))
        if valid.empty:
            continue
        ranks = valid["factor_value"].rank(method="first", pct=True)
        buckets = (ranks * int(quantiles)).apply(math.ceil).clip(lower=1, upper=int(quantiles))
        top = valid[buckets == int(quantiles)]
        bottom = valid[buckets == 1]
        selected = pd.concat([top, bottom], ignore_index=True)
        selected_count = int(len(selected))
        if selected_count < int(min_selected_assets) or top.empty or bottom.empty:
            continue
        gross = float(top["forward_return"].mean() - bottom["forward_return"].mean())
        net = gross - (2.0 * float(cost_bps) / 10_000.0)
        long_short_net.append(net)
        selected_counts.append(selected_count)
        amount = pd.to_numeric(selected.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        per_asset_trade_value = float(portfolio_value) / max(selected_count, 1)
        participation = amount.apply(lambda value: per_asset_trade_value / value if value > 0 else float("inf"))
        max_part = float(participation.max()) if not participation.empty else 0.0
        participation_values.append(max_part)
        if (participation > float(max_participation_rate)).any() or (amount < float(min_signal_date_amount)).any():
            capacity_limited_dates += 1
    ic_series = pd.Series(ic_values, dtype=float)
    ls_series = pd.Series(long_short_net, dtype=float)
    exposure_series = pd.Series(exposure_corrs, dtype=float).abs()
    return {
        "ic_observations": int(len(ic_series)),
        "mean_ic": float(ic_series.mean()) if not ic_series.empty else 0.0,
        "ic_t_stat": _t_stat(ic_series),
        "positive_ic_rate": float((ic_series > 0).mean()) if not ic_series.empty else 0.0,
        "long_short_net_mean": float(ls_series.mean()) if not ls_series.empty else 0.0,
        "long_short_net_total": float(ls_series.sum()) if not ls_series.empty else 0.0,
        "long_short_net_positive_rate": float((ls_series > 0).mean()) if not ls_series.empty else 0.0,
        "selected_dates": int(len(ls_series)),
        "median_selected_assets": float(pd.Series(selected_counts, dtype=float).median()) if selected_counts else 0.0,
        "capacity_limited_dates": int(capacity_limited_dates),
        "max_participation_rate": float(max(participation_values)) if participation_values else 0.0,
        "exposure_challenge_observations": int(len(exposure_series)),
        "exposure_challenge_mean_abs_corr": float(exposure_series.mean()) if not exposure_series.empty else 0.0,
        "exposure_challenge_max_abs_corr": float(exposure_series.max()) if not exposure_series.empty else 0.0,
    }


def _candidate_result(
    candidate: dict[str, Any],
    rows: Sequence[dict[str, Any]],
    *,
    min_accepted_folds: int,
) -> dict[str, Any]:
    accepted_folds = sum(1 for row in rows if row["fold_status"] == "accepted")
    reasons = _unique(reason for row in rows for reason in _as_list(row.get("fold_rejection_reasons")))
    if accepted_folds < int(min_accepted_folds):
        reasons.append("accepted_folds_below_threshold")
    exposure_required = _moderate_exposure_challenge_required(candidate)
    exposure_passed = True
    if exposure_required:
        exposure_passed = bool(rows) and not any(
            reason.startswith("moderate_exposure_challenge") for row in rows for reason in _as_list(row.get("fold_rejection_reasons"))
        )
    if exposure_required and not exposure_passed:
        reasons.append("moderate_exposure_challenge_failed")
    return {
        "factor_name": candidate["factor_name"],
        "state": candidate["state"],
        "horizon": int(candidate["horizon"]),
        "validation_status": "accepted" if not reasons else "rejected",
        "accepted_folds": int(accepted_folds),
        "folds": int(len(rows)),
        "positive_test_fold_rate": _positive_rate(rows, "test_long_short_net_total"),
        "mean_test_ic": _mean(rows, "test_mean_ic"),
        "mean_test_ic_t_stat": _mean(rows, "test_ic_t_stat"),
        "mean_test_long_short_net_mean": _mean(rows, "test_long_short_net_mean"),
        "mean_test_long_short_net_total": _mean(rows, "test_long_short_net_total"),
        "mean_test_long_short_net_positive_rate": _mean(rows, "test_long_short_net_positive_rate"),
        "max_test_participation_rate": max((_number(row.get("test_max_participation_rate")) for row in rows), default=0.0),
        "test_capacity_limited_dates": sum(int(_number(row.get("test_capacity_limited_dates"))) for row in rows),
        "moderate_exposure_challenge_required": exposure_required,
        "moderate_exposure_challenge_passed": exposure_passed,
        "exposure_challenge_mean_abs_corr": _mean(rows, "exposure_challenge_mean_abs_corr"),
        "exposure_challenge_max_abs_corr": max((_number(row.get("exposure_challenge_max_abs_corr")) for row in rows), default=0.0),
        "rejection_reasons": _unique(reasons),
    }


def _preflight_blockers(preflight: dict[str, Any]) -> list[str]:
    decision = _dict(preflight.get("decision"))
    blockers = []
    if preflight.get("stage") != PREFLIGHT_STAGE:
        blockers.append("walk_forward_preflight_stage_mismatch")
    if preflight.get("status") != "cleared":
        blockers.append("walk_forward_preflight_not_cleared")
    if decision.get("walk_forward_preflight_cleared") is not True:
        blockers.append("walk_forward_preflight_decision_not_cleared")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("walk_forward_preflight_policy_boundary_violation")
    if _dict(preflight.get("promotion_policy")).get("promotion_allowed") is not False:
        blockers.append("walk_forward_preflight_promotion_boundary_violation")
    if preflight.get("live_boundary_allowed") is not False:
        blockers.append("walk_forward_preflight_live_boundary_violation")
    return blockers


def _frozen_candidates(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    frozen_names = set(_as_list(_dict(preflight.get("preflight_policy")).get("frozen_factor_names")))
    rows = []
    for row in preflight.get("candidate_table", []):
        if not isinstance(row, dict) or row.get("walk_forward_frozen") is not True:
            continue
        factor_name = str(row.get("factor_name", ""))
        if frozen_names and factor_name not in frozen_names:
            continue
        rows.append(
            {
                "factor_name": factor_name,
                "base_factor_name": str(row.get("base_factor_name", "")),
                "horizon": int(row.get("horizon", 0)),
                "state": str(row.get("state", "")),
                "moderate_exposure_challenge_required": bool(row.get("moderate_exposure_challenge_required", False)),
                "challenge_requirements": _as_list(row.get("challenge_requirements")),
                "max_exposure_name": str(row.get("max_exposure_name", "")),
            }
        )
    return rows


def _fold_plan(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in preflight.get("walk_forward_plan", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "fold": row.get("fold"),
                "train_start": str(row.get("train_start")),
                "train_end": str(row.get("train_end")),
                "test_start": str(row.get("test_start")),
                "test_end": str(row.get("test_end")),
            }
        )
    return rows


def _merge_validation_frame(factors: pd.DataFrame, labels: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    if factors.empty or labels.empty:
        return pd.DataFrame()
    merged = factors.merge(labels, on=["date", "asset_id", "market"], how="inner", validate="many_to_many")
    if not exposure.empty:
        exposure_cols = [column for column in exposure.columns if column not in {"lpr_available_date", STATE_COLUMN}]
        merged = merged.merge(exposure[exposure_cols], on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    if "amount" not in merged:
        merged["amount"] = 0.0
    if "adv20_amount" not in merged:
        merged["adv20_amount"] = merged["amount"]
    return merged.dropna(subset=["factor_value", "forward_return"]).reset_index(drop=True)


def _prepare_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "asset_id", "market", "factor_name", "factor_value"]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=columns)
    output = frame[columns].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").astype("datetime64[ns]")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "factor_name", "factor_value"]).reset_index(drop=True)


def _prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "asset_id", "market", "adj_close"]
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[*columns, "amount"])
    output_columns = [column for column in [*columns, "amount"] if column in frame.columns]
    output = frame[output_columns].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").astype("datetime64[ns]")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["adj_close"] = pd.to_numeric(output["adj_close"], errors="coerce")
    if "amount" in output:
        output["amount"] = pd.to_numeric(output["amount"], errors="coerce")
    else:
        output["amount"] = 0.0
    return output.dropna(subset=["date", "asset_id", "adj_close"]).reset_index(drop=True)


def _prepare_exposure_frame(exposure_frame: pd.DataFrame | None, bars: pd.DataFrame) -> pd.DataFrame:
    if exposure_frame is None or exposure_frame.empty:
        base = bars[["date", "asset_id", "market", "amount"]].copy() if not bars.empty else pd.DataFrame()
        if base.empty:
            return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount"])
        base["adv20_amount"] = base["amount"]
        return base
    output = exposure_frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").astype("datetime64[ns]")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    for column in output.columns:
        if column not in {"date", "asset_id", "market", "industry"}:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    return output.dropna(subset=["date", "asset_id"]).drop_duplicates(["date", "asset_id", "market"], keep="last")


def _analysis_window(frame: pd.DataFrame, *, analysis_start_date: str, analysis_end_date: str) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame.copy()
    return frame[
        (frame["date"] >= pd.Timestamp(analysis_start_date))
        & (frame["date"] <= pd.Timestamp(analysis_end_date))
        & (frame["date"] < pd.Timestamp(FINAL_HOLDOUT_START))
    ].copy().reset_index(drop=True)


def _slice_dates(frame: pd.DataFrame, start: Any, end: Any) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame.copy()
    dates = pd.to_datetime(frame["date"], errors="coerce")
    return frame[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))].copy()


def _regime_coverage_rows(
    state_frame: pd.DataFrame,
    fold_plan: Sequence[dict[str, Any]],
    *,
    allowed_states: set[str],
    analysis_start_date: str,
    analysis_end_date: str,
) -> list[dict[str, Any]]:
    if state_frame is None or state_frame.empty or "available_date" not in state_frame or STATE_COLUMN not in state_frame:
        return []
    frame = state_frame[["available_date", STATE_COLUMN]].copy()
    frame["date"] = pd.to_datetime(frame["available_date"], errors="coerce").astype("datetime64[ns]")
    frame[STATE_COLUMN] = frame[STATE_COLUMN].astype(str)
    frame = frame[
        (frame["date"] >= pd.Timestamp(analysis_start_date))
        & (frame["date"] <= pd.Timestamp(analysis_end_date))
        & (frame["date"] < pd.Timestamp(FINAL_HOLDOUT_START))
    ].copy()
    rows = []
    for fold in fold_plan:
        for window in ("train", "test"):
            sliced = _slice_dates(frame, fold[f"{window}_start"], fold[f"{window}_end"])
            for state, group in sliced.groupby(STATE_COLUMN, sort=True):
                rows.append(
                    {
                        "fold": fold["fold"],
                        "window": window,
                        "state": str(state),
                        "dates": int(len(group)),
                        "min_date": _min_date(group, "date"),
                        "max_date": _max_date(group, "date"),
                        "is_allowed_state": str(state) in allowed_states,
                    }
                )
    return rows


def _regime_coverage_summary(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    allowed = sum(int(row.get("dates", 0) or 0) for row in rows if row.get("is_allowed_state") is True)
    blocked = sum(int(row.get("dates", 0) or 0) for row in rows if row.get("is_allowed_state") is not True)
    return {"allowed_dates": int(allowed), "blocked_dates": int(blocked)}


def _rank_candidates(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            row["validation_status"] != "accepted",
            -int(row.get("accepted_folds", 0)),
            -_number(row.get("mean_test_long_short_net_total")),
            -_number(row.get("mean_test_ic")),
            str(row.get("factor_name", "")),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _moderate_exposure_challenge_required(candidate: dict[str, Any]) -> bool:
    return bool(candidate.get("moderate_exposure_challenge_required")) or any(
        str(item).startswith("challenge_") for item in _as_list(candidate.get("challenge_requirements"))
    )


def _t_stat(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 2:
        return 0.0
    std = float(clean.std(ddof=1))
    if std <= 0.0 or not math.isfinite(std):
        return 0.0
    return float(clean.mean() / (std / math.sqrt(len(clean))))


def _mean(rows: Sequence[dict[str, Any]], key: str) -> float:
    values = [_number(row.get(key)) for row in rows]
    return float(sum(values) / len(values)) if values else 0.0


def _positive_rate(rows: Sequence[dict[str, Any]], key: str) -> float:
    values = [_number(row.get(key)) for row in rows]
    return float(sum(1 for value in values if value > 0.0) / len(values)) if values else 0.0


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


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


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            for field in ("rejection_reasons", "fold_rejection_reasons"):
                if isinstance(clean.get(field), list):
                    clean[field] = "|".join(str(item) for item in clean[field])
            writer.writerow(clean)


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
