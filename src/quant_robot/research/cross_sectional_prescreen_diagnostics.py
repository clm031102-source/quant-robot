from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.research.cross_sectional_factor_prescreen import (
    assign_cross_sectional_quintiles,
)


def summarize_long_short_costs(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    horizons: tuple[int, ...],
    min_cross_section: int,
    one_way_costs_bps: tuple[float, ...],
) -> dict[str, Any]:
    factor_frame = _normalise_factor_frame(factors)
    label_frame = _normalise_labels(labels)
    _validate_common_inputs(
        candidate_names=candidate_names,
        horizons=horizons,
        min_cross_section=min_cross_section,
    )
    costs = tuple(float(value) for value in one_way_costs_bps)
    if not costs or any(not math.isfinite(value) or value < 0.0 for value in costs):
        raise ValueError("one_way_costs_bps must contain finite non-negative values")
    if len(set(costs)) != len(costs):
        raise ValueError("one_way_costs_bps must not contain duplicates")

    daily_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for candidate_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"].eq(candidate_name)]
        for horizon in horizons:
            merged = _merge_candidate_labels(candidate, label_frame, horizon=horizon)
            rows = _daily_long_short_rows(
                merged,
                factor_name=candidate_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
                costs_bps=costs,
            )
            daily_rows.extend(rows)
            summary_rows.append(
                _summarize_long_short_rows(
                    rows,
                    factor_name=candidate_name,
                    horizon=horizon,
                    costs_bps=costs,
                )
            )
    return {
        "cost_policy": {
            "one_way_costs_bps": list(costs),
            "initial_entry_turnover_per_side": 1.0,
            "average_transition_turnover_excludes_initial_entry": True,
        },
        "summary": summary_rows,
        "daily": daily_rows,
    }


def summarize_top_quantile_capacity_by_date(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    adv20: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    horizons: tuple[int, ...],
    min_cross_section: int,
    position_value_cny: float,
    max_one_way_participation_rate: float,
) -> dict[str, Any]:
    factor_frame = _normalise_factor_frame(factors)
    label_frame = _normalise_labels(labels)
    adv_frame = _normalise_adv(adv20)
    _validate_common_inputs(
        candidate_names=candidate_names,
        horizons=horizons,
        min_cross_section=min_cross_section,
    )
    position_value = float(position_value_cny)
    participation_limit = float(max_one_way_participation_rate)
    if not math.isfinite(position_value) or position_value <= 0.0:
        raise ValueError("position_value_cny must be finite and positive")
    if not math.isfinite(participation_limit) or not 0.0 < participation_limit <= 1.0:
        raise ValueError("max_one_way_participation_rate must be in (0, 1]")
    required_adv = position_value / participation_limit

    daily_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    constituent_rows: list[dict[str, Any]] = []
    for candidate_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"].eq(candidate_name)]
        for horizon in horizons:
            merged = _merge_candidate_labels(candidate, label_frame, horizon=horizon)
            rows, constituents = _daily_capacity_rows(
                merged,
                adv_frame,
                factor_name=candidate_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
                position_value_cny=position_value,
                max_participation_rate=participation_limit,
                required_adv20=required_adv,
            )
            daily_rows.extend(rows)
            constituent_rows.extend(constituents)
            summary_rows.append(
                _summarize_capacity_rows(
                    rows,
                    factor_name=candidate_name,
                    horizon=horizon,
                )
            )
    return {
        "capacity_policy": {
            "position_value_cny": position_value,
            "max_one_way_participation_rate": participation_limit,
            "required_adv20_cny": required_adv,
            "support_required_every_date": True,
        },
        "summary": summary_rows,
        "daily": daily_rows,
        "top_constituents": constituent_rows,
    }


def summarize_direct_exposure_correlations(
    factors: pd.DataFrame,
    exposures: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    exposure_names: tuple[str, ...],
    min_cross_section: int,
    min_daily_observations: int,
    max_abs_mean_daily_correlation: float,
) -> dict[str, Any]:
    factor_frame = _normalise_factor_frame(factors)
    exposure_frame = _normalise_factor_frame(exposures)
    if not candidate_names or not exposure_names:
        raise ValueError("candidate_names and exposure_names must not be empty")
    if len(set(candidate_names)) != len(candidate_names):
        raise ValueError("candidate_names must not contain duplicates")
    if len(set(exposure_names)) != len(exposure_names):
        raise ValueError("exposure_names must not contain duplicates")
    if min_cross_section < 2 or min_daily_observations < 1:
        raise ValueError("correlation observation minimums are invalid")
    ceiling = float(max_abs_mean_daily_correlation)
    if not math.isfinite(ceiling) or not 0.0 < ceiling <= 1.0:
        raise ValueError("max_abs_mean_daily_correlation must be in (0, 1]")

    available = set(exposure_frame["factor_name"].unique())
    missing = sorted(set(exposure_names) - available)
    rows: list[dict[str, Any]] = []
    for candidate_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"].eq(candidate_name)][
            ["date", "asset_id", "market", "factor_value"]
        ].rename(columns={"factor_value": "candidate_value"})
        for exposure_name in exposure_names:
            exposure = exposure_frame[exposure_frame["factor_name"].eq(exposure_name)][
                ["date", "asset_id", "market", "factor_value"]
            ].rename(columns={"factor_value": "exposure_value"})
            merged = candidate.merge(
                exposure,
                on=["date", "asset_id", "market"],
                how="inner",
                validate="one_to_one",
            )
            daily_values: list[float] = []
            for _, group in merged.groupby("date", sort=True):
                clean = group.dropna(subset=["candidate_value", "exposure_value"])
                if len(clean) < min_cross_section:
                    continue
                correlation = _spearman(clean["candidate_value"], clean["exposure_value"])
                if math.isfinite(correlation):
                    daily_values.append(float(correlation))
            observations = len(daily_values)
            mean_daily = float(pd.Series(daily_values, dtype=float).mean()) if daily_values else 0.0
            rows.append(
                {
                    "candidate_factor_name": candidate_name,
                    "exposure_name": exposure_name,
                    "daily_observations": observations,
                    "mean_daily_spearman": mean_daily,
                    "mean_abs_daily_spearman": (
                        float(pd.Series(daily_values, dtype=float).abs().mean())
                        if daily_values
                        else 0.0
                    ),
                    "max_abs_daily_spearman": max(
                        (abs(value) for value in daily_values),
                        default=0.0,
                    ),
                    "evidence_complete": observations >= min_daily_observations,
                }
            )
    incomplete = sorted(
        {
            str(row["exposure_name"])
            for row in rows
            if not bool(row["evidence_complete"])
        }
    )
    maximum = max(
        rows,
        key=lambda row: abs(float(row["mean_daily_spearman"])),
        default=None,
    )
    max_abs = abs(float(maximum["mean_daily_spearman"])) if maximum is not None else 0.0
    ceiling_passed = max_abs < ceiling
    evidence_complete = not missing and not incomplete
    return {
        "summary": {
            "candidate_count": len(candidate_names),
            "expected_exposure_count": len(exposure_names),
            "missing_exposure_names": missing,
            "incomplete_exposure_names": incomplete,
            "min_daily_observations": int(min_daily_observations),
            "max_abs_mean_daily_correlation": ceiling,
            "max_abs_mean_daily_spearman": max_abs,
            "max_exposure_name": maximum["exposure_name"] if maximum is not None else None,
            "strict_correlation_ceiling_passed": ceiling_passed,
            "evidence_complete": evidence_complete,
            "passed": evidence_complete and ceiling_passed,
        },
        "rows": rows,
    }


def _daily_long_short_rows(
    merged: pd.DataFrame,
    *,
    factor_name: str,
    horizon: int,
    min_cross_section: int,
    costs_bps: tuple[float, ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous_top: set[str] | None = None
    previous_bottom: set[str] | None = None
    for signal_date, group in merged.groupby("date", sort=True):
        clean = group.dropna(subset=["factor_value", "forward_return"])
        if len(clean) < min_cross_section:
            continue
        if clean["factor_value"].nunique() < 2 or clean["forward_return"].nunique() < 2:
            continue
        quantiles = assign_cross_sectional_quintiles(clean["factor_value"])
        if quantiles is None:
            continue
        top = clean.loc[quantiles.eq(4)]
        bottom = clean.loc[quantiles.eq(0)]
        top_set = set(top["asset_id"].astype(str))
        bottom_set = set(bottom["asset_id"].astype(str))
        top_turnover = 1.0 if previous_top is None else _set_turnover(previous_top, top_set)
        bottom_turnover = (
            1.0 if previous_bottom is None else _set_turnover(previous_bottom, bottom_set)
        )
        gross = float(top["forward_return"].mean() - bottom["forward_return"].mean())
        quantile_means = {
            f"q{index + 1}_return": float(clean.loc[quantiles.eq(index), "forward_return"].mean())
            for index in range(5)
        }
        row: dict[str, Any] = {
            "factor_name": factor_name,
            "horizon": int(horizon),
            "date": pd.Timestamp(signal_date).date().isoformat(),
            "cross_section": int(len(clean)),
            "top_count": int(len(top_set)),
            "bottom_count": int(len(bottom_set)),
            "top_turnover": float(top_turnover),
            "bottom_turnover": float(bottom_turnover),
            "gross_top_minus_bottom": gross,
            **quantile_means,
        }
        for cost_bps in costs_bps:
            row[_net_column(cost_bps)] = gross - (cost_bps / 10_000.0) * (
                top_turnover + bottom_turnover
            )
        rows.append(row)
        previous_top = top_set
        previous_bottom = bottom_set
    return rows


def _summarize_long_short_rows(
    rows: list[dict[str, Any]],
    *,
    factor_name: str,
    horizon: int,
    costs_bps: tuple[float, ...],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "factor_name": factor_name,
        "horizon": int(horizon),
        "evaluated_dates": len(rows),
        "avg_top_turnover": _mean_transition(rows, "top_turnover"),
        "avg_bottom_turnover": _mean_transition(rows, "bottom_turnover"),
        "mean_gross_top_minus_bottom": _mean_column(rows, "gross_top_minus_bottom"),
    }
    for cost_bps in costs_bps:
        summary[_mean_net_column(cost_bps)] = _mean_column(rows, _net_column(cost_bps))
    return summary


def _daily_capacity_rows(
    merged: pd.DataFrame,
    adv20: pd.DataFrame,
    *,
    factor_name: str,
    horizon: int,
    min_cross_section: int,
    position_value_cny: float,
    max_participation_rate: float,
    required_adv20: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    constituent_rows: list[dict[str, Any]] = []
    for signal_date, group in merged.groupby("date", sort=True):
        clean = group.dropna(subset=["factor_value", "forward_return"])
        if len(clean) < min_cross_section:
            continue
        if clean["factor_value"].nunique() < 2 or clean["forward_return"].nunique() < 2:
            continue
        quantiles = assign_cross_sectional_quintiles(clean["factor_value"])
        if quantiles is None:
            continue
        top = clean.loc[quantiles.eq(4), ["date", "asset_id", "market"]]
        top = top.merge(
            adv20,
            on=["date", "asset_id", "market"],
            how="left",
            validate="one_to_one",
        )
        finite_positive = pd.to_numeric(top["adv20"], errors="coerce").where(
            pd.to_numeric(top["adv20"], errors="coerce").gt(0.0)
        )
        count = int(finite_positive.notna().sum())
        complete = count == len(top)
        p10 = float(finite_positive.dropna().quantile(0.10)) if count else 0.0
        participation = position_value_cny / p10 if p10 > 0.0 else 0.0
        supported = (
            complete
            and p10 >= required_adv20
            and participation <= max_participation_rate
        )
        signal_iso = pd.Timestamp(signal_date).date().isoformat()
        rows.append(
            {
                "factor_name": factor_name,
                "horizon": int(horizon),
                "date": signal_iso,
                "top_count": int(len(top)),
                "finite_positive_adv_count": count,
                "complete_adv_coverage": complete,
                "daily_p10_adv20": p10,
                "position_value_cny": position_value_cny,
                "participation_rate_at_daily_p10": participation,
                "date_supported": supported,
            }
        )
        for constituent in top.itertuples(index=False):
            constituent_rows.append(
                {
                    "factor_name": factor_name,
                    "horizon": int(horizon),
                    "date": signal_iso,
                    "asset_id": str(constituent.asset_id),
                    "market": str(constituent.market),
                    "adv20": (
                        float(constituent.adv20)
                        if pd.notna(constituent.adv20) and float(constituent.adv20) > 0.0
                        else None
                    ),
                }
            )
    return rows, constituent_rows


def _summarize_capacity_rows(
    rows: list[dict[str, Any]],
    *,
    factor_name: str,
    horizon: int,
) -> dict[str, Any]:
    finite_p10 = [float(row["daily_p10_adv20"]) for row in rows if row["daily_p10_adv20"] > 0.0]
    finite_participation = [
        float(row["participation_rate_at_daily_p10"])
        for row in rows
        if row["daily_p10_adv20"] > 0.0
    ]
    worst = max(
        rows,
        key=lambda row: (
            not bool(row["complete_adv_coverage"]),
            float(row["participation_rate_at_daily_p10"]),
        ),
        default=None,
    )
    qualifying = sum(bool(row["date_supported"]) for row in rows)
    return {
        "factor_name": factor_name,
        "horizon": int(horizon),
        "evaluated_dates": len(rows),
        "qualifying_dates": qualifying,
        "every_date_supported": bool(rows) and qualifying == len(rows),
        "minimum_daily_p10_adv20": min(finite_p10, default=0.0),
        "maximum_daily_participation_rate": max(finite_participation, default=0.0),
        "worst_date": worst["date"] if worst is not None else None,
    }


def _merge_candidate_labels(
    candidate: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    horizon: int,
) -> pd.DataFrame:
    horizon_labels = labels[labels["horizon"].eq(int(horizon))]
    return candidate.merge(
        horizon_labels[["date", "asset_id", "market", "forward_return"]],
        on=["date", "asset_id", "market"],
        how="inner",
        validate="one_to_one",
    )


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Factor frame is missing columns: " + ", ".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["factor_name"] = result["factor_name"].astype(str)
    result["factor_value"] = pd.to_numeric(result["factor_value"], errors="coerce")
    if result["date"].isna().any():
        raise ValueError("Factor frame contains invalid dates")
    if result.duplicated(["date", "asset_id", "market", "factor_name"]).any():
        raise ValueError("Factor frame contains duplicate factor rows")
    return result


def _normalise_labels(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "horizon", "forward_return"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Label frame is missing columns: " + ", ".join(missing))
    result = frame[required].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["horizon"] = pd.to_numeric(result["horizon"], errors="coerce")
    result["forward_return"] = pd.to_numeric(result["forward_return"], errors="coerce")
    if result["date"].isna().any() or result["horizon"].isna().any():
        raise ValueError("Label frame contains invalid dates or horizons")
    result["horizon"] = result["horizon"].astype(int)
    if result.duplicated(["date", "asset_id", "market", "horizon"]).any():
        raise ValueError("Label frame contains duplicate label rows")
    return result


def _normalise_adv(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adv20"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("ADV20 frame is missing columns: " + ", ".join(missing))
    result = frame[required].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["adv20"] = pd.to_numeric(result["adv20"], errors="coerce")
    if result["date"].isna().any():
        raise ValueError("ADV20 frame contains invalid dates")
    if result.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("ADV20 frame contains duplicate asset-date rows")
    return result


def _validate_common_inputs(
    *,
    candidate_names: tuple[str, ...],
    horizons: tuple[int, ...],
    min_cross_section: int,
) -> None:
    if not candidate_names or not horizons:
        raise ValueError("candidate_names and horizons must not be empty")
    if len(set(candidate_names)) != len(candidate_names):
        raise ValueError("candidate_names must not contain duplicates")
    if len(set(horizons)) != len(horizons):
        raise ValueError("horizons must not contain duplicates")
    if min_cross_section < 5:
        raise ValueError("min_cross_section must be at least five")


def _set_turnover(previous: set[str], current: set[str]) -> float:
    denominator = max(len(previous), len(current), 1)
    return 1.0 - len(previous & current) / denominator


def _mean_transition(rows: list[dict[str, Any]], column: str) -> float:
    if len(rows) < 2:
        return 1.0
    return float(pd.Series([row[column] for row in rows[1:]], dtype=float).mean())


def _mean_column(rows: list[dict[str, Any]], column: str) -> float:
    if not rows:
        return 0.0
    return float(pd.Series([row[column] for row in rows], dtype=float).mean())


def _net_column(cost_bps: float) -> str:
    return f"net_top_minus_bottom_{_format_bps(cost_bps)}bps"


def _mean_net_column(cost_bps: float) -> str:
    return f"mean_net_top_minus_bottom_{_format_bps(cost_bps)}bps"


def _format_bps(cost_bps: float) -> str:
    if float(cost_bps).is_integer():
        return str(int(cost_bps))
    return format(cost_bps, "g").replace(".", "p")


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2 or aligned.iloc[:, 0].nunique() < 2 or aligned.iloc[:, 1].nunique() < 2:
        return float("nan")
    return float(
        aligned.iloc[:, 0]
        .rank(method="average")
        .corr(aligned.iloc[:, 1].rank(method="average"))
    )
