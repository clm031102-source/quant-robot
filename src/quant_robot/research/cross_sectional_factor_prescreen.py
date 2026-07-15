from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import pandas as pd

from quant_robot.ops.factor_statistical_reality_check import benjamini_hochberg
from quant_robot.research.overlap import newey_west_mean_test


@dataclass(frozen=True)
class CrossSectionalPrescreenThresholds:
    min_cross_section: int = 30
    min_ic_observations: int = 20
    min_year_ic_observations: int = 20
    min_usable_years: int = 3
    alpha: float = 0.05
    min_mean_rank_ic: float = 0.02
    min_icir: float = 0.30
    min_positive_ic_rate: float = 0.55
    min_quantile_monotonicity: float = 0.70
    max_top_quantile_turnover: float = 0.90
    min_positive_year_rate: float = 0.60
    max_abs_reference_correlation: float = 0.85


def summarize_cross_sectional_factor_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...] | None = None,
    reference_names: tuple[str, ...] | None = None,
    horizons: tuple[int, ...] = (5, 20),
    thresholds: CrossSectionalPrescreenThresholds = CrossSectionalPrescreenThresholds(),
) -> dict[str, Any]:
    factor_frame = _normalise_factor_frame(factors)
    reference_frame = _normalise_factor_frame(references)
    label_frame = labels.copy()
    label_frame["date"] = pd.to_datetime(label_frame["date"])
    selected_candidates = tuple(candidate_names or sorted(factor_frame["factor_name"].unique()))
    selected_references = tuple(reference_names or sorted(reference_frame["factor_name"].unique()))
    available_candidates = set(factor_frame["factor_name"].unique())
    available_references = set(reference_frame["factor_name"].unique())
    missing_candidates = sorted(set(selected_candidates) - available_candidates)
    missing_references = sorted(set(selected_references) - available_references)

    results: list[dict[str, Any]] = []
    ic_observations: list[dict[str, Any]] = []
    yearly_ic: list[dict[str, Any]] = []
    for factor_name in selected_candidates:
        candidate = factor_frame[factor_frame["factor_name"].eq(factor_name)]
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
                thresholds=thresholds,
            )
            results.append(row)
            ic_observations.extend(observations)
            yearly_ic.extend(years)

    fdr_rows = benjamini_hochberg([row["ic_p_value"] for row in results], alpha=thresholds.alpha)
    for row, fdr in zip(results, fdr_rows, strict=True):
        row["fdr_adjusted_p_value"] = float(fdr["adjusted_p_value"])
        row["fdr_significant"] = bool(fdr["significant"])

    correlation_rows = _reference_correlations(
        factor_frame,
        reference_frame,
        candidate_names=selected_candidates,
        reference_names=selected_references,
        min_cross_section=thresholds.min_cross_section,
    )
    correlations_by_factor: dict[str, list[dict[str, Any]]] = {}
    for correlation in correlation_rows:
        correlations_by_factor.setdefault(str(correlation["candidate_factor_name"]), []).append(correlation)

    for row in results:
        correlations = correlations_by_factor.get(str(row["factor_name"]), [])
        maximum = max(correlations, key=lambda item: abs(float(item["mean_daily_spearman"])), default=None)
        row["max_abs_reference_correlation"] = (
            abs(float(maximum["mean_daily_spearman"])) if maximum is not None else 0.0
        )
        row["max_reference_factor_name"] = maximum["reference_factor_name"] if maximum is not None else None
        reference_evidence_incomplete = bool(missing_references) or any(
            int(item["daily_observations"]) < thresholds.min_ic_observations
            for item in correlations
        )
        blockers = _research_blockers(
            row,
            thresholds=thresholds,
            reference_evidence_incomplete=reference_evidence_incomplete,
        )
        row["research_lead"] = not blockers
        row["blockers"] = blockers

    lead_rows = [row for row in results if row["research_lead"]]
    lead_names = sorted({str(row["factor_name"]) for row in lead_rows})
    return {
        "summary": {
            "candidate_count": len(selected_candidates),
            "reference_count": len(selected_references),
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
        "candidate_names": list(selected_candidates),
        "reference_names": list(selected_references),
        "thresholds": asdict(thresholds),
        "multiple_testing_policy": {
            "method": "Benjamini-Hochberg FDR across all frozen factor x horizon tests",
            "alpha": thresholds.alpha,
            "test_count": len(results),
        },
        "results": sorted(results, key=lambda row: (not row["research_lead"], -float(row["mean_rank_ic"]))),
        "ic_observations": ic_observations,
        "yearly_ic": yearly_ic,
        "reference_correlations": correlation_rows,
    }


def _summarize_factor_horizon(
    *,
    factor_name: str,
    horizon: int,
    merged: pd.DataFrame,
    thresholds: CrossSectionalPrescreenThresholds,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    daily_rows: list[dict[str, Any]] = []
    quantile_rows: list[list[float]] = []
    top_sets: list[set[str]] = []
    for signal_date, group in merged.groupby("date", sort=True):
        clean = group.dropna(subset=["factor_value", "forward_return"])
        if len(clean) < thresholds.min_cross_section:
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
    enough = len(ic_series) >= thresholds.min_ic_observations
    mean_ic = float(ic_series.mean()) if enough else 0.0
    ic_std = float(ic_series.std(ddof=1)) if enough and len(ic_series) > 1 else 0.0
    icir = mean_ic / ic_std if ic_std > 0.0 else 0.0
    nw = (
        newey_west_mean_test(ic_series, max_lag=max(0, horizon - 1))
        if enough
        else {"t_stat": 0.0, "p_value": 1.0, "standard_error": 0.0, "max_lag": 0}
    )
    quantile_frame = pd.DataFrame(quantile_rows, columns=["q1", "q2", "q3", "q4", "q5"])
    spread = float((quantile_frame["q5"] - quantile_frame["q1"]).mean()) if enough else 0.0
    monotonicity = (
        _spearman(pd.Series(range(1, 6), dtype=float), quantile_frame.mean().reset_index(drop=True))
        if enough and not quantile_frame.empty
        else 0.0
    )
    yearly_rows = _yearly_ic_rows(
        daily_rows,
        factor_name=factor_name,
        horizon=horizon,
        min_year_ic_observations=thresholds.min_year_ic_observations,
    )
    usable = [row for row in yearly_rows if row["usable"]]
    positive_year_rate = (
        float(sum(float(row["mean_rank_ic"]) > 0.0 for row in usable) / len(usable)) if usable else 0.0
    )
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
        candidate = factors[factors["factor_name"].eq(candidate_name)][
            ["date", "asset_id", "market", "factor_value"]
        ].rename(columns={"factor_value": "candidate_value"})
        for reference_name in reference_names:
            reference = references[references["factor_name"].eq(reference_name)][
                ["date", "asset_id", "market", "factor_value"]
            ].rename(columns={"factor_value": "reference_value"})
            merged = candidate.merge(
                reference,
                on=["date", "asset_id", "market"],
                how="inner",
                validate="one_to_one",
            )
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
    thresholds: CrossSectionalPrescreenThresholds,
    reference_evidence_incomplete: bool,
) -> list[str]:
    blockers = []
    if int(row["ic_observations"]) < thresholds.min_ic_observations:
        blockers.append("ic_observations_below_threshold")
    if not row["fdr_significant"]:
        blockers.append("not_fdr_significant_after_multiple_testing")
    if float(row["mean_rank_ic"]) < thresholds.min_mean_rank_ic:
        blockers.append("mean_rank_ic_below_threshold")
    if float(row["icir"]) < thresholds.min_icir:
        blockers.append("icir_below_threshold")
    if float(row["positive_ic_rate"]) < thresholds.min_positive_ic_rate:
        blockers.append("positive_ic_rate_below_threshold")
    if float(row["quantile_spread"]) <= 0.0:
        blockers.append("top_minus_bottom_quantile_not_positive")
    if float(row["quantile_monotonicity"]) < thresholds.min_quantile_monotonicity:
        blockers.append("quantile_monotonicity_below_threshold")
    if float(row["avg_top_quantile_turnover"]) > thresholds.max_top_quantile_turnover:
        blockers.append("top_quantile_turnover_above_threshold")
    if int(row["usable_years"]) < thresholds.min_usable_years:
        blockers.append("usable_years_below_threshold")
    if float(row["positive_year_rate"]) < thresholds.min_positive_year_rate:
        blockers.append("positive_year_rate_below_threshold")
    if reference_evidence_incomplete:
        blockers.append("historical_reference_evidence_incomplete")
    if float(row["max_abs_reference_correlation"]) >= thresholds.max_abs_reference_correlation:
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
