from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.data.etf_point_in_time_universe import (
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.factors.etf_skip_momentum import (
    ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    ETF_SKIP_MOMENTUM_FACTOR_NAMES,
    compute_etf_price_rotation_reference_factors,
    compute_etf_skip_momentum_factors,
)
from quant_robot.ops.factor_statistical_reality_check import benjamini_hochberg
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.overlap import newey_west_mean_test
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_skip_momentum_prescreen"
DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_wide_history_2023_2026")
DEFAULT_ANALYSIS_START_DATE = "2020-01-02"
DEFAULT_ANALYSIS_END_DATE = "2024-06-28"
DEFAULT_HORIZONS = (5, 20)
SAFETY = "Research-to-paper only. No broker connection, account reads, order placement, or live trading."


def build_historical_price_rotation_stop_loss_review() -> dict[str, Any]:
    return {
        "family_id": "cn_etf_price_rotation",
        "review_status": "only_skip_momentum_subspace_remains",
        "closed_factor_names": [
            "momentum_20",
            "momentum_60",
            "risk_adjusted_momentum_20",
            "risk_adjusted_momentum_60",
            "market_relative_strength_60",
            "liquid_market_relative_strength_60",
            "theme_relative_strength_60",
            "theme_member_leadership_60",
        ],
        "closed_subfamilies": [
            "plain_momentum",
            "risk_adjusted_momentum",
            "relative_strength",
            "static_theme_relative_strength",
            "tail_guard_reversal",
            "defensive_reversal",
        ],
        "remaining_candidate_names": list(ETF_SKIP_MOMENTUM_FACTOR_NAMES),
        "parameter_rescue_allowed": False,
        "window_tuning_allowed": False,
        "threshold_relaxation_allowed": False,
        "portfolio_grid_before_prescreen_lead_allowed": False,
        "source_reports": [
            "docs/research/highspec_desktop_cn_etf_rotation_seed_2026-06-17.md",
            "docs/research/cn_etf_rounds27_29_audit_2026-06-21.md",
            "docs/research/cn_etf_rounds31_33_audit_2026-06-21.md",
        ],
    }


def build_cn_etf_skip_momentum_prescreen(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    metadata_root: str | Path | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    eligibility_policy: EtfEligibilityPolicy = EtfEligibilityPolicy(),
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_year_ic_observations: int = 20,
    min_usable_years: int = 3,
    alpha: float = 0.05,
    min_mean_rank_ic: float = 0.02,
    min_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    min_quantile_monotonicity: float = 0.70,
    max_top_quantile_turnover: float = 0.90,
    min_positive_year_rate: float = 0.60,
    max_abs_reference_correlation: float = 0.85,
) -> dict[str, Any]:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if end >= pd.Timestamp("2026-01-01"):
        raise ValueError("CN ETF skip-momentum prescreen cannot read the sealed 2026 final holdout")
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if not horizons or any(int(horizon) < 1 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    root = Path(data_root)
    bars = load_processed_bars(root, "CN_ETF").copy()
    bars["date"] = pd.to_datetime(bars["date"])
    source_window = _frame_window(bars)
    history = bars[bars["date"] <= end].copy()
    if history.empty:
        raise ValueError("No CN_ETF bars are available on or before analysis_end_date")
    official_root = Path(metadata_root) if metadata_root is not None else root / "metadata" / "tushare_fund_basic"
    lifecycle = load_official_etf_lifecycle(official_root)
    eligibility = build_point_in_time_etf_eligibility(history, lifecycle, policy=eligibility_policy)
    eligible = eligibility[
        eligibility["eligible"]
        & eligibility["date"].ge(start)
        & eligibility["date"].le(end)
    ].copy()
    eligible_keys = eligible[["date", "asset_id", "market"]].drop_duplicates()

    factors = compute_etf_skip_momentum_factors(history, eligible_keys=eligible_keys)
    references = compute_etf_price_rotation_reference_factors(history, eligible_keys=eligible_keys)
    labels = make_forward_returns(
        history[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(int(value) for value in horizons),
        execution_lag=int(execution_lag),
    )
    labels["date"] = pd.to_datetime(labels["date"])
    labels = labels[labels["date"].ge(start) & labels["date"].le(end)].reset_index(drop=True)

    result = summarize_cn_etf_skip_momentum_prescreen(
        factors,
        labels,
        references,
        expected_candidate_names=ETF_SKIP_MOMENTUM_FACTOR_NAMES,
        expected_reference_names=ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
        horizons=tuple(int(value) for value in horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_year_ic_observations=min_year_ic_observations,
        min_usable_years=min_usable_years,
        alpha=alpha,
        min_mean_rank_ic=min_mean_rank_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        min_quantile_monotonicity=min_quantile_monotonicity,
        max_top_quantile_turnover=max_top_quantile_turnover,
        min_positive_year_rate=min_positive_year_rate,
        max_abs_reference_correlation=max_abs_reference_correlation,
    )
    result["data_window"] = {
        "source": source_window,
        "analysis_start_date": start.date().isoformat(),
        "analysis_end_date": end.date().isoformat(),
        "history_rows": int(len(history)),
        "eligible_signal_rows": int(len(eligible_keys)),
        "eligible_assets": int(eligible_keys["asset_id"].nunique()),
        "eligible_dates": int(eligible_keys["date"].nunique()),
        "metadata_assets": int(len(lifecycle)),
    }
    result["eligibility_policy"] = {
        "point_in_time": True,
        "static_round25_universe_used": False,
        **eligibility_policy.__dict__,
    }
    result["holdout_policy"] = {
        "final_holdout_start": "2026-01-01",
        "final_holdout_included": False,
        "final_holdout_access_allowed": False,
    }
    result["source_paths"] = {
        "data_root": str(root),
        "metadata_root": str(official_root),
    }
    result["markdown"] = render_cn_etf_skip_momentum_prescreen_markdown(result)
    return result


def summarize_cn_etf_skip_momentum_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    *,
    expected_candidate_names: tuple[str, ...] | None = None,
    expected_reference_names: tuple[str, ...] | None = None,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_year_ic_observations: int = 20,
    min_usable_years: int = 3,
    alpha: float = 0.05,
    min_mean_rank_ic: float = 0.02,
    min_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    min_quantile_monotonicity: float = 0.70,
    max_top_quantile_turnover: float = 0.90,
    min_positive_year_rate: float = 0.60,
    max_abs_reference_correlation: float = 0.85,
) -> dict[str, Any]:
    factor_frame = _normalise_factor_frame(factors)
    label_frame = labels.copy()
    reference_frame = _normalise_factor_frame(references)
    label_frame["date"] = pd.to_datetime(label_frame["date"])
    candidate_names = tuple(expected_candidate_names or sorted(factor_frame["factor_name"].unique()))
    reference_names = tuple(expected_reference_names or sorted(reference_frame["factor_name"].unique()))
    missing_candidates = sorted(set(candidate_names) - set(factor_frame["factor_name"].unique()))
    missing_references = sorted(set(reference_names) - set(reference_frame["factor_name"].unique()))

    results: list[dict[str, Any]] = []
    ic_observations: list[dict[str, Any]] = []
    yearly_ic: list[dict[str, Any]] = []
    for factor_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"] == factor_name]
        for horizon in horizons:
            horizon_labels = label_frame[label_frame["horizon"].eq(int(horizon))]
            merged = candidate.merge(
                horizon_labels[["date", "asset_id", "market", "forward_return"]],
                on=["date", "asset_id", "market"],
                how="inner",
                validate="one_to_one",
            )
            row, observations, years = _summarize_factor_horizon(
                factor_name=factor_name,
                horizon=int(horizon),
                merged=merged,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
                min_year_ic_observations=min_year_ic_observations,
            )
            results.append(row)
            ic_observations.extend(observations)
            yearly_ic.extend(years)

    fdr_rows = benjamini_hochberg([row["ic_p_value"] for row in results], alpha=alpha)
    for row, fdr in zip(results, fdr_rows, strict=True):
        row["fdr_adjusted_p_value"] = float(fdr["adjusted_p_value"])
        row["fdr_significant"] = bool(fdr["significant"])

    correlation_rows = _reference_correlations(
        factor_frame,
        reference_frame,
        candidate_names=candidate_names,
        reference_names=reference_names,
        min_cross_section=min_cross_section,
    )
    correlation_by_factor: dict[str, list[dict[str, Any]]] = {}
    for row in correlation_rows:
        correlation_by_factor.setdefault(str(row["candidate_factor_name"]), []).append(row)

    for row in results:
        correlations = correlation_by_factor.get(str(row["factor_name"]), [])
        maximum = max(correlations, key=lambda item: abs(float(item["mean_daily_spearman"])), default=None)
        row["max_abs_reference_correlation"] = (
            abs(float(maximum["mean_daily_spearman"])) if maximum is not None else 0.0
        )
        row["max_reference_factor_name"] = maximum["reference_factor_name"] if maximum is not None else None
        research_blockers = _research_blockers(
            row,
            min_ic_observations=min_ic_observations,
            min_usable_years=min_usable_years,
            min_mean_rank_ic=min_mean_rank_ic,
            min_icir=min_icir,
            min_positive_ic_rate=min_positive_ic_rate,
            min_quantile_monotonicity=min_quantile_monotonicity,
            max_top_quantile_turnover=max_top_quantile_turnover,
            min_positive_year_rate=min_positive_year_rate,
            max_abs_reference_correlation=max_abs_reference_correlation,
            missing_reference_names=missing_references,
        )
        row["research_lead"] = not research_blockers
        row["promotion_allowed"] = False
        row["blockers"] = [
            *research_blockers,
            "promotion_requires_fresh_data_walk_forward_cost_capacity_regime_gates",
        ]

    lead_rows = [row for row in results if row["research_lead"]]
    lead_names = sorted({str(row["factor_name"]) for row in lead_rows})
    status = "research_leads_found" if lead_rows else "rejected"
    next_action = (
        "backfill_2024h2_2025_then_freeze_walk_forward"
        if lead_rows
        else "close_price_rotation_and_rotate_scheduler"
    )
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "candidate_count": len(candidate_names),
            "reference_count": len(reference_names),
            "test_count": len(results),
            "research_lead_count": len(lead_rows),
            "research_lead_factor_count": len(lead_names),
            "factor_rows": int(len(factor_frame)),
            "label_rows": int(len(label_frame)),
            "reference_rows": int(len(reference_frame)),
            "ic_observation_rows": len(ic_observations),
            "yearly_ic_rows": len(yearly_ic),
            "missing_candidate_names": missing_candidates,
            "missing_reference_names": missing_references,
        },
        "historical_stop_loss_review": build_historical_price_rotation_stop_loss_review(),
        "candidate_names": list(candidate_names),
        "reference_names": list(reference_names),
        "thresholds": {
            "alpha": alpha,
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "min_year_ic_observations": min_year_ic_observations,
            "min_usable_years": min_usable_years,
            "min_mean_rank_ic": min_mean_rank_ic,
            "min_icir": min_icir,
            "min_positive_ic_rate": min_positive_ic_rate,
            "min_quantile_monotonicity": min_quantile_monotonicity,
            "max_top_quantile_turnover": max_top_quantile_turnover,
            "min_positive_year_rate": min_positive_year_rate,
            "max_abs_reference_correlation": max_abs_reference_correlation,
        },
        "multiple_testing_policy": {
            "method": "Benjamini-Hochberg FDR across all frozen factor x horizon tests",
            "alpha": alpha,
            "test_count": len(results),
        },
        "results": sorted(results, key=lambda row: (not row["research_lead"], -float(row["mean_rank_ic"]))),
        "ic_observations": ic_observations,
        "yearly_ic": yearly_ic,
        "reference_correlations": correlation_rows,
        "decision": {
            "research_lead_count": len(lead_rows),
            "research_lead_names": lead_names,
            "walk_forward_preflight_candidate_count": len(lead_names),
            "walk_forward_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "next_action": next_action,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_etf_skip_momentum_prescreen_markdown(result)
    return result


def write_cn_etf_skip_momentum_prescreen(output_dir: str | Path, result: dict[str, Any]) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_skip_momentum_prescreen.json",
        "markdown": output / "cn_etf_skip_momentum_prescreen.md",
        "results": output / "cn_etf_skip_momentum_prescreen_results.csv",
        "ic_observations": output / "cn_etf_skip_momentum_ic_observations.csv",
        "yearly_ic": output / "cn_etf_skip_momentum_yearly_ic.csv",
        "reference_correlations": output / "cn_etf_skip_momentum_reference_correlations.csv",
    }
    paths["json"].write_text(json.dumps(_sanitize(result), indent=2, sort_keys=True), encoding="utf-8")
    paths["markdown"].write_text(render_cn_etf_skip_momentum_prescreen_markdown(result), encoding="utf-8")
    pd.DataFrame(result.get("results", [])).to_csv(paths["results"], index=False)
    pd.DataFrame(result.get("ic_observations", [])).to_csv(paths["ic_observations"], index=False)
    pd.DataFrame(result.get("yearly_ic", [])).to_csv(paths["yearly_ic"], index=False)
    pd.DataFrame(result.get("reference_correlations", [])).to_csv(paths["reference_correlations"], index=False)
    return paths


def render_cn_etf_skip_momentum_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    data_window = result.get("data_window", {})
    lines = [
        "# CN ETF Skip-Momentum Prescreen",
        "",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Candidates / tests: {summary.get('candidate_count', 0)} / {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Analysis end: {data_window.get('analysis_end_date', 'not_attached')}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next action: {decision.get('next_action', 'unknown')}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | Rank IC | ICIR | NW t | FDR q | IC>0 | Q5-Q1 | Mono | Turnover | Years | Positive years | Max reference corr | Lead |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {q:.4g} | {positive:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {years} | {positive_years:.1%} | {corr:.3f} | {lead} |".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                t=float(row.get("ic_t_stat", 0.0)),
                q=float(row.get("fdr_adjusted_p_value", 1.0)),
                positive=float(row.get("positive_ic_rate", 0.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                mono=float(row.get("quantile_monotonicity", 0.0)),
                turnover=float(row.get("avg_top_quantile_turnover", 1.0)),
                years=int(row.get("usable_years", 0)),
                positive_years=float(row.get("positive_year_rate", 0.0)),
                corr=float(row.get("max_abs_reference_correlation", 0.0)),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This packet cannot authorize walk-forward until the 2024-H2 through 2025 history gap is backfilled and audited.",
            "- It cannot authorize a portfolio grid, promotion, paper signal, broker access, account read, or order placement.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summarize_factor_horizon(
    *,
    factor_name: str,
    horizon: int,
    merged: pd.DataFrame,
    min_cross_section: int,
    min_ic_observations: int,
    min_year_ic_observations: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    daily_rows: list[dict[str, Any]] = []
    quantile_rows: list[list[float]] = []
    top_sets: list[set[str]] = []
    for signal_date, group in merged.groupby("date", sort=True):
        clean = group.dropna(subset=["factor_value", "forward_return"])
        if len(clean) < min_cross_section:
            continue
        rank_ic = _spearman(clean["factor_value"], clean["forward_return"])
        quantiles = _quintiles(clean["factor_value"])
        if not math.isfinite(rank_ic) or quantiles is None:
            continue
        quantile_means = [float(clean.loc[quantiles.eq(index), "forward_return"].mean()) for index in range(5)]
        top_assets = set(clean.loc[quantiles.eq(4), "asset_id"].astype(str))
        daily_rows.append(
            {
                "factor_name": factor_name,
                "horizon": horizon,
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "rank_ic": float(rank_ic),
                "cross_section": int(len(clean)),
            }
        )
        quantile_rows.append(quantile_means)
        top_sets.append(top_assets)

    ic_series = pd.Series([row["rank_ic"] for row in daily_rows], dtype=float)
    enough = len(ic_series) >= min_ic_observations
    mean_ic = float(ic_series.mean()) if enough else 0.0
    ic_std = float(ic_series.std(ddof=1)) if enough and len(ic_series) > 1 else 0.0
    icir = mean_ic / ic_std if ic_std > 0.0 else 0.0
    nw = newey_west_mean_test(ic_series, max_lag=max(0, horizon - 1)) if enough else {
        "t_stat": 0.0,
        "p_value": 1.0,
        "standard_error": 0.0,
        "max_lag": 0,
    }
    quantile_frame = pd.DataFrame(quantile_rows, columns=["q1", "q2", "q3", "q4", "q5"])
    spread = float((quantile_frame["q5"] - quantile_frame["q1"]).mean()) if enough else 0.0
    monotonicity = (
        _spearman(
            pd.Series(range(1, 6), dtype=float),
            quantile_frame.mean().reset_index(drop=True),
        )
        if enough and not quantile_frame.empty
        else 0.0
    )
    yearly_rows = _yearly_ic_rows(
        daily_rows,
        factor_name=factor_name,
        horizon=horizon,
        min_year_ic_observations=min_year_ic_observations,
    )
    usable = [row for row in yearly_rows if row["usable"]]
    positive_year_rate = float(sum(float(row["mean_rank_ic"]) > 0.0 for row in usable) / len(usable)) if usable else 0.0
    row = {
        "factor_name": factor_name,
        "horizon": horizon,
        "ic_observations": int(len(ic_series)),
        "mean_rank_ic": mean_ic,
        "ic_std": ic_std,
        "icir": float(icir),
        "ic_t_stat": float(nw["t_stat"]),
        "ic_p_value": float(nw["p_value"]),
        "newey_west_max_lag": int(nw["max_lag"]),
        "fdr_adjusted_p_value": 1.0,
        "fdr_significant": False,
        "positive_ic_rate": float((ic_series > 0.0).mean()) if enough else 0.0,
        "quantile_spread": spread,
        "quantile_monotonicity": float(monotonicity) if math.isfinite(monotonicity) else 0.0,
        "avg_top_quantile_turnover": _average_top_set_turnover(top_sets) if enough else 1.0,
        "usable_years": len(usable),
        "positive_year_rate": positive_year_rate,
        "max_abs_reference_correlation": 0.0,
        "max_reference_factor_name": None,
        "research_lead": False,
        "promotion_allowed": False,
        "blockers": [],
    }
    return row, daily_rows, yearly_rows


def _yearly_ic_rows(
    daily_rows: list[dict[str, Any]],
    *,
    factor_name: str,
    horizon: int,
    min_year_ic_observations: int,
) -> list[dict[str, Any]]:
    if not daily_rows:
        return []
    frame = pd.DataFrame(daily_rows)
    frame["year"] = pd.to_datetime(frame["date"]).dt.year
    rows = []
    for year, group in frame.groupby("year", sort=True):
        observations = int(len(group))
        rows.append(
            {
                "factor_name": factor_name,
                "horizon": horizon,
                "year": int(year),
                "ic_observations": observations,
                "mean_rank_ic": float(group["rank_ic"].mean()),
                "positive_ic_rate": float(group["rank_ic"].gt(0.0).mean()),
                "usable": observations >= min_year_ic_observations,
            }
        )
    return rows


def _reference_correlations(
    factors: pd.DataFrame,
    references: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    reference_names: tuple[str, ...],
    min_cross_section: int,
) -> list[dict[str, Any]]:
    rows = []
    for candidate_name in candidate_names:
        candidate = factors[factors["factor_name"] == candidate_name][
            ["date", "asset_id", "market", "factor_value"]
        ].rename(columns={"factor_value": "candidate_value"})
        for reference_name in reference_names:
            reference = references[references["factor_name"] == reference_name][
                ["date", "asset_id", "market", "factor_value"]
            ].rename(columns={"factor_value": "reference_value"})
            merged = candidate.merge(reference, on=["date", "asset_id", "market"], how="inner", validate="one_to_one")
            daily = []
            for _, group in merged.groupby("date", sort=True):
                clean = group.dropna(subset=["candidate_value", "reference_value"])
                if len(clean) < min_cross_section:
                    continue
                correlation = _spearman(clean["candidate_value"], clean["reference_value"])
                if math.isfinite(correlation):
                    daily.append(float(correlation))
            rows.append(
                {
                    "candidate_factor_name": candidate_name,
                    "reference_factor_name": reference_name,
                    "daily_observations": len(daily),
                    "mean_daily_spearman": float(pd.Series(daily).mean()) if daily else 0.0,
                    "mean_abs_daily_spearman": float(pd.Series(daily).abs().mean()) if daily else 0.0,
                    "max_abs_daily_spearman": max((abs(value) for value in daily), default=0.0),
                }
            )
    return rows


def _research_blockers(
    row: dict[str, Any],
    *,
    min_ic_observations: int,
    min_usable_years: int,
    min_mean_rank_ic: float,
    min_icir: float,
    min_positive_ic_rate: float,
    min_quantile_monotonicity: float,
    max_top_quantile_turnover: float,
    min_positive_year_rate: float,
    max_abs_reference_correlation: float,
    missing_reference_names: list[str],
) -> list[str]:
    blockers = []
    if int(row["ic_observations"]) < min_ic_observations:
        blockers.append("ic_observations_below_threshold")
    if not row["fdr_significant"]:
        blockers.append("not_fdr_significant_after_multiple_testing")
    if float(row["mean_rank_ic"]) < min_mean_rank_ic:
        blockers.append("mean_rank_ic_below_threshold")
    if float(row["icir"]) < min_icir:
        blockers.append("icir_below_threshold")
    if float(row["positive_ic_rate"]) < min_positive_ic_rate:
        blockers.append("positive_ic_rate_below_threshold")
    if float(row["quantile_spread"]) <= 0.0:
        blockers.append("top_minus_bottom_quantile_not_positive")
    if float(row["quantile_monotonicity"]) < min_quantile_monotonicity:
        blockers.append("quantile_monotonicity_below_threshold")
    if float(row["avg_top_quantile_turnover"]) > max_top_quantile_turnover:
        blockers.append("top_quantile_turnover_above_threshold")
    if int(row["usable_years"]) < min_usable_years:
        blockers.append("usable_years_below_threshold")
    if float(row["positive_year_rate"]) < min_positive_year_rate:
        blockers.append("positive_year_rate_below_threshold")
    if missing_reference_names:
        blockers.append("historical_reference_evidence_incomplete")
    if float(row["max_abs_reference_correlation"]) >= max_abs_reference_correlation:
        blockers.append("historical_reference_duplicate")
    return blockers


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Factor frame is missing columns: " + ", ".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["factor_name"] = result["factor_name"].astype(str)
    result["factor_value"] = pd.to_numeric(result["factor_value"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market", "factor_name"]).any():
        raise ValueError("Factor frame contains duplicate factor rows")
    return result


def _quintiles(values: pd.Series) -> pd.Series | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique() < 5:
        return None
    try:
        return pd.qcut(numeric.rank(method="first"), q=5, labels=False)
    except ValueError:
        return None


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2 or aligned.iloc[:, 0].nunique() < 2 or aligned.iloc[:, 1].nunique() < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


def _average_top_set_turnover(top_sets: list[set[str]]) -> float:
    if len(top_sets) < 2:
        return 1.0
    values = []
    for previous, current in zip(top_sets[:-1], top_sets[1:], strict=True):
        denominator = max(len(previous), len(current), 1)
        values.append(1.0 - len(previous & current) / denominator)
    return float(pd.Series(values).mean())


def _frame_window(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"rows": 0, "assets": 0, "dates": 0, "start_date": None, "end_date": None}
    dates = pd.to_datetime(frame["date"])
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "dates": int(dates.nunique()),
        "start_date": dates.min().date().isoformat(),
        "end_date": dates.max().date().isoformat(),
    }


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value
