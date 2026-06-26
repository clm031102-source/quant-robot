from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    compute_capacity_safe_price_volume_factors,
    load_capacity_safe_bars,
)


STAGE = "capacity_safe_price_volume_lead_dedup"
DEFAULT_LEAD_FACTOR_NAME = "bollinger_reversal_lowvol_liquid_20"
DEFAULT_LEAD_HORIZON = 20
CORRELATION_COLUMNS = [
    "factor_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "redundancy_class",
    "blockers",
]
OBSERVATION_COLUMNS = ["factor_name", "date", "spearman_correlation", "cross_section"]
BRIDGE_NEXT_DIRECTION = "round104_bollinger_lead_cost_capacity_bridge_preregistration"
ROTATE_NEXT_DIRECTION = "round104_family_rotation_after_bollinger_redundancy"


def build_capacity_safe_price_volume_lead_dedup(
    *,
    bars_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    lead_horizon: int = DEFAULT_LEAD_HORIZON,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    report = _load_prescreen_report(prescreen_report)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_capacity_safe_price_volume_factors(
        bars,
        min_signal_date_amount=min_signal_date_amount,
    )
    sampled_factor_frame = _sample_factor_dates(factor_frame, sample_every_n_dates=sample_every_n_dates)
    result = summarize_capacity_safe_price_volume_lead_dedup(
        sampled_factor_frame,
        lead_factor_name=lead_factor_name,
        lead_horizon=lead_horizon,
        prescreen_report=report,
        min_cross_section=min_cross_section,
    )
    result["data_window"] = _data_window(bars, sampled_factor_frame)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "capacity_safe_factor_frame_reused": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_after_factor_computation": True,
    }
    result["markdown"] = render_capacity_safe_price_volume_lead_dedup_markdown(result)
    return result


def summarize_capacity_safe_price_volume_lead_dedup(
    factor_frame: pd.DataFrame,
    *,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    lead_horizon: int = DEFAULT_LEAD_HORIZON,
    prescreen_report: dict[str, Any] | None = None,
    min_cross_section: int = 30,
    moderate_corr_threshold: float = 0.70,
    high_corr_threshold: float = 0.85,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_mean_abs_corr_threshold: float = 0.70,
) -> dict[str, Any]:
    frame = _normalise_factor_frame(factor_frame)
    lead_evidence = _prescreen_lead_evidence(prescreen_report, lead_factor_name, lead_horizon)
    correlations, observations = _lead_correlations(
        frame,
        lead_factor_name=lead_factor_name,
        min_cross_section=min_cross_section,
        moderate_corr_threshold=moderate_corr_threshold,
        high_corr_threshold=high_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
    )
    summary = _summary(frame, correlations, observations, lead_factor_name)
    overall_redundancy = _overall_redundancy(correlations)
    blockers = _gate_blockers(frame, lead_evidence, overall_redundancy, lead_factor_name)
    next_direction = BRIDGE_NEXT_DIRECTION if not blockers and overall_redundancy != "highly_redundant" else ROTATE_NEXT_DIRECTION
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "lead_horizon": int(lead_horizon),
        "lead_evidence": lead_evidence,
        "summary": summary | {"lead_redundancy_class": overall_redundancy},
        "thresholds": {
            "moderate_corr_threshold": moderate_corr_threshold,
            "high_corr_threshold": high_corr_threshold,
            "moderate_mean_abs_corr_threshold": moderate_mean_abs_corr_threshold,
            "high_mean_abs_corr_threshold": high_mean_abs_corr_threshold,
            "min_cross_section": min_cross_section,
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "candidate_correlation_dedup_before_portfolio_grid",
                "bollinger_reversal_cost_capacity_bridge_before_walk_forward",
                "round101_103_three_round_review_before_new_family_expansion",
            ],
            "allowed_next_directions": [BRIDGE_NEXT_DIRECTION, ROTATE_NEXT_DIRECTION],
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Deduplication is a pre-portfolio audit only; promotion still requires cost, capacity, walk-forward, and regime gates.",
        },
        "next_direction": next_direction,
        "correlations": correlations,
        "correlation_observations": observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_capacity_safe_price_volume_lead_dedup_markdown(result)
    return result


def write_capacity_safe_price_volume_lead_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "capacity_safe_price_volume_lead_dedup.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "capacity_safe_price_volume_lead_dedup.md").write_text(
        render_capacity_safe_price_volume_lead_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "capacity_safe_price_volume_lead_correlations.csv", result.get("correlations", []), CORRELATION_COLUMNS)
    _write_csv(
        output_path / "capacity_safe_price_volume_lead_correlation_observations.csv",
        result.get("correlation_observations", []),
        OBSERVATION_COLUMNS,
    )


def render_capacity_safe_price_volume_lead_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lead_evidence = result.get("lead_evidence", {})
    gate = result.get("gate", {})
    lines = [
        "# Capacity-Safe Price-Volume Lead Dedup",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Lead: {result.get('lead_factor_name', DEFAULT_LEAD_FACTOR_NAME)}",
        f"- Lead horizon: {result.get('lead_horizon', DEFAULT_LEAD_HORIZON)}",
        f"- Prescreen lead confirmed: {lead_evidence.get('prescreen_research_lead', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Compared candidates: {summary.get('compared_candidate_count', 0)}",
        f"- Highly redundant: {summary.get('highly_redundant_count', 0)}",
        f"- Lead redundancy class: {summary.get('lead_redundancy_class', 'unknown')}",
        f"- Next direction: {result.get('next_direction', ROTATE_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Correlations",
        "",
        "| Factor | Obs | Mean | Mean Abs | Max Abs | Positive | Median CS | Class | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("correlations", []):
        lines.append(
            "| {factor_name} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {pos:.1%} | {cs:.0f} | {klass} | {blockers} |".format(
                factor_name=row.get("factor_name", "unknown"),
                obs=row.get("correlation_observations", 0),
                mean=row.get("mean_correlation", 0.0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                pos=row.get("positive_correlation_rate", 0.0),
                cs=row.get("median_cross_section", 0.0),
                klass=row.get("redundancy_class", "unknown"),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
            "- This stage cannot promote a factor; it only decides whether a lead is worth the next cost/capacity bridge.",
        ]
    )
    return "\n".join(lines) + "\n"


def _lead_correlations(
    frame: pd.DataFrame,
    *,
    lead_factor_name: str,
    min_cross_section: int,
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if frame.empty or lead_factor_name not in set(frame.get("factor_name", [])):
        return [], []
    lead_frame = (
        frame[frame["factor_name"] == lead_factor_name][["date", "asset_id", "market", "factor_value"]]
        .rename(columns={"factor_value": "lead_value"})
        .copy()
    )
    rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for factor_name, factor_group in frame[frame["factor_name"] != lead_factor_name].groupby("factor_name", sort=True):
        group = factor_group[["date", "asset_id", "market", "factor_value"]].merge(
            lead_frame,
            on=["date", "asset_id", "market"],
            how="inner",
        )
        corr_values: list[float] = []
        cross_sections: list[int] = []
        dates: list[pd.Timestamp] = []
        for signal_date, date_frame in group.groupby("date", sort=True):
            date_frame = date_frame.dropna(subset=["factor_value", "lead_value"])
            if len(date_frame) < min_cross_section:
                continue
            corr = _spearman(date_frame["factor_value"], date_frame["lead_value"])
            if not _is_finite(corr):
                continue
            corr_values.append(float(corr))
            cross_sections.append(int(len(date_frame)))
            dates.append(pd.Timestamp(signal_date))
            observations.append(
                {
                    "factor_name": str(factor_name),
                    "date": pd.Timestamp(signal_date).date().isoformat(),
                    "spearman_correlation": float(corr),
                    "cross_section": int(len(date_frame)),
                }
            )
        rows.append(
            _correlation_row(
                factor_name=str(factor_name),
                group=group,
                corr_values=corr_values,
                cross_sections=cross_sections,
                dates=dates,
                moderate_corr_threshold=moderate_corr_threshold,
                high_corr_threshold=high_corr_threshold,
                moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
                high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
            )
        )
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["factor_name"])), observations


def _correlation_row(
    *,
    factor_name: str,
    group: pd.DataFrame,
    corr_values: list[float],
    cross_sections: list[int],
    dates: list[pd.Timestamp],
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> dict[str, Any]:
    if not corr_values:
        row = {
            "factor_name": factor_name,
            "correlation_observations": 0,
            "mean_correlation": 0.0,
            "mean_abs_correlation": 0.0,
            "median_abs_correlation": 0.0,
            "max_abs_correlation": 0.0,
            "positive_correlation_rate": 0.0,
            "median_cross_section": 0.0,
            "unique_dates": 0,
            "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
            "redundancy_class": "insufficient_overlap",
            "blockers": ["insufficient_overlap_with_lead"],
        }
        return row
    series = pd.Series(corr_values, dtype=float)
    abs_series = series.abs()
    redundancy_class = _redundancy_class(
        max_abs_corr=float(abs_series.max()),
        mean_abs_corr=float(abs_series.mean()),
        moderate_corr_threshold=moderate_corr_threshold,
        high_corr_threshold=high_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
    )
    blockers = []
    if redundancy_class == "highly_redundant":
        blockers.append("high_correlation_with_lead")
    elif redundancy_class == "moderately_redundant":
        blockers.append("moderate_correlation_with_lead")
    return {
        "factor_name": factor_name,
        "correlation_observations": int(len(series)),
        "mean_correlation": float(series.mean()),
        "mean_abs_correlation": float(abs_series.mean()),
        "median_abs_correlation": float(abs_series.median()),
        "max_abs_correlation": float(abs_series.max()),
        "positive_correlation_rate": float((series > 0).mean()),
        "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
        "unique_dates": int(len(set(dates))),
        "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
        "redundancy_class": redundancy_class,
        "blockers": blockers,
    }


def _redundancy_class(
    *,
    max_abs_corr: float,
    mean_abs_corr: float,
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> str:
    if max_abs_corr >= high_corr_threshold or mean_abs_corr >= high_mean_abs_corr_threshold:
        return "highly_redundant"
    if max_abs_corr >= moderate_corr_threshold or mean_abs_corr >= moderate_mean_abs_corr_threshold:
        return "moderately_redundant"
    return "unique"


def _overall_redundancy(correlations: list[dict[str, Any]]) -> str:
    classes = {row.get("redundancy_class") for row in correlations}
    if "highly_redundant" in classes:
        return "highly_redundant"
    if "moderately_redundant" in classes:
        return "moderately_redundant"
    if correlations:
        return "unique"
    return "unknown"


def _gate_blockers(
    frame: pd.DataFrame,
    lead_evidence: dict[str, Any],
    overall_redundancy: str,
    lead_factor_name: str,
) -> list[str]:
    blockers = []
    if frame.empty:
        blockers.append("factor_frame_empty")
    if lead_factor_name not in set(frame.get("factor_name", [])):
        blockers.append("lead_factor_missing")
    if not lead_evidence.get("prescreen_research_lead", False):
        blockers.append("prescreen_lead_not_confirmed")
    if overall_redundancy == "highly_redundant":
        blockers.append("lead_highly_redundant_with_existing_candidate")
    return blockers


def _summary(
    frame: pd.DataFrame,
    correlations: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    lead_factor_name: str,
) -> dict[str, Any]:
    classes = [row.get("redundancy_class") for row in correlations]
    return {
        "candidate_count": int(frame["factor_name"].nunique()) if not frame.empty else 0,
        "compared_candidate_count": int(len(correlations)),
        "correlation_observation_count": int(len(observations)),
        "highly_redundant_count": int(sum(1 for item in classes if item == "highly_redundant")),
        "moderately_redundant_count": int(sum(1 for item in classes if item == "moderately_redundant")),
        "unique_count": int(sum(1 for item in classes if item == "unique")),
        "lead_present": bool(not frame.empty and lead_factor_name in set(frame["factor_name"])),
    }


def _prescreen_lead_evidence(
    prescreen_report: dict[str, Any] | None,
    lead_factor_name: str,
    lead_horizon: int,
) -> dict[str, Any]:
    rows = prescreen_report.get("results", []) if isinstance(prescreen_report, dict) else []
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("factor_name") == lead_factor_name
        and int(float(row.get("horizon", lead_horizon))) == int(lead_horizon)
    ]
    lead_row = matches[0] if matches else {}
    return {
        "prescreen_report_provided": isinstance(prescreen_report, dict),
        "lead_factor_name": lead_factor_name,
        "lead_horizon": int(lead_horizon),
        "prescreen_row_found": bool(matches),
        "prescreen_research_lead": bool(lead_row.get("research_lead", False)),
        "prescreen_blockers": _normalise_blockers(lead_row.get("blockers")),
    }


def _normalise_blockers(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if value:
        return [item.strip() for item in str(value).split(",") if item.strip()]
    return []


def _normalise_factor_frame(factor_frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in factor_frame.columns]
    if missing:
        if factor_frame.empty:
            return pd.DataFrame(columns=required)
        raise ValueError(f"Factor frame is missing required columns: {', '.join(missing)}")
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    return frame.dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"])


def _sample_factor_dates(factor_frame: pd.DataFrame, *, sample_every_n_dates: int) -> pd.DataFrame:
    if factor_frame.empty or sample_every_n_dates <= 1:
        return factor_frame
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    dates = sorted(frame["date"].dropna().unique())
    sampled_dates = set(dates[::sample_every_n_dates])
    return frame[frame["date"].isin(sampled_dates)].reset_index(drop=True)


def _load_prescreen_report(value: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _data_window(bars: pd.DataFrame, factor_frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "factor_rows": int(len(factor_frame)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
