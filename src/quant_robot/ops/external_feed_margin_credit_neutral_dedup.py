from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    _sanitize,
    _write_csv,
    compute_capacity_safe_price_volume_factors,
    load_capacity_safe_bars,
)
from quant_robot.ops.external_feed_margin_credit_prescreen import (
    DEFAULT_MARGIN_CREDIT_HORIZONS,
    DEFAULT_SEED_CONFIG,
    MARGIN_CREDIT_FACTOR_NAMES,
    SAFETY,
    _read_processed_dataset,
    compute_external_feed_margin_credit_factors,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    YEARLY_IC_COLUMNS,
    _filter_dates,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _period_ic,
    _reference_correlations,
    _sample_dates,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "external_feed_margin_credit_neutral_dedup"
DEFAULT_OUTPUT_BASENAME = "external_feed_margin_credit_neutral_dedup"
DEFAULT_HORIZON = DEFAULT_MARGIN_CREDIT_HORIZONS[0]
STYLE_EXPOSURE_NAMES = (
    "log_adv20_amount",
    "log_amount",
    "momentum_20",
    "momentum_60",
    "reversal_5",
    "realized_vol_20",
    "amount_trend_20_60",
)
REFERENCE_CORRELATION_COLUMNS = [
    "lead_factor_name",
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
STYLE_EXPOSURE_CORRELATION_COLUMNS = [
    "lead_factor_name",
    "exposure_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "exposure_class",
    "blockers",
]
RESIDUAL_IC_COLUMNS = [
    "factor_name",
    "parent_factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "ic_std",
    "icir",
    "ic_t_stat",
    "positive_ic_rate",
    "median_cross_section",
    "minimum_observation_gate_passed",
]


def build_external_feed_margin_credit_neutral_dedup(
    *,
    bars_roots: Iterable[str | Path],
    processed_root: str | Path,
    prescreen_report: dict[str, Any] | str | Path,
    seed_config_path: str | Path = DEFAULT_SEED_CONFIG,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    lookback: int = 20,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    market: str = "CN",
) -> dict[str, Any]:
    report = _load_report(prescreen_report)
    bars = load_capacity_safe_bars(
        tuple(Path(path) for path in bars_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    margin_detail = _read_processed_dataset(Path(processed_root), "external_margin_detail", market)
    return build_external_feed_margin_credit_neutral_dedup_from_frames(
        bars=bars,
        margin_detail=margin_detail,
        prescreen_report=report,
        seed_config_path=seed_config_path,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizon=horizon,
        execution_lag=execution_lag,
        lookback=lookback,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
    )


def build_external_feed_margin_credit_neutral_dedup_from_frames(
    *,
    bars: pd.DataFrame,
    margin_detail: pd.DataFrame,
    prescreen_report: dict[str, Any] | None,
    seed_config_path: str | Path = DEFAULT_SEED_CONFIG,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    lookback: int = 20,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    style_exposure_names: Sequence[str] = STYLE_EXPOSURE_NAMES,
) -> dict[str, Any]:
    clean_bars = _normalise_bars_for_audit(bars)
    start = pd.Timestamp(analysis_start_date)
    end = clean_bars["date"].max() if include_final_holdout and not clean_bars.empty else pd.Timestamp(analysis_end_date)
    clean_bars = clean_bars[(clean_bars["date"] >= start) & (clean_bars["date"] <= end)].reset_index(drop=True)
    margin_factors = compute_external_feed_margin_credit_factors(
        bars=clean_bars,
        margin_detail=margin_detail,
        candidate_specs=_margin_specs_from_report_or_seed(prescreen_report, seed_config_path),
        lookback=lookback,
        min_signal_date_amount=min_signal_date_amount,
    )
    margin_factors = margin_factors[
        (pd.to_datetime(margin_factors["date"]) >= start) & (pd.to_datetime(margin_factors["date"]) <= end)
    ].reset_index(drop=True)
    style_exposures = _style_exposure_frame(clean_bars)
    reference_factors = compute_capacity_safe_price_volume_factors(
        clean_bars,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(int(horizon),),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= end].reset_index(drop=True)

    sampled_margin_factors = _sample_dates(margin_factors, sample_every_n_dates=sample_every_n_dates)
    sampled_references = _filter_dates(reference_factors, sorted(sampled_margin_factors["date"].dropna().unique()))
    factor_names = [name for name in MARGIN_CREDIT_FACTOR_NAMES if name in set(margin_factors.get("factor_name", []))]
    reference_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    residual_frames: list[pd.DataFrame] = []
    residual_ic_rows: list[dict[str, Any]] = []
    residual_ic_observations: list[dict[str, Any]] = []
    yearly_ic: list[dict[str, Any]] = []
    monthly_ic: list[dict[str, Any]] = []

    for factor_name in factor_names:
        factor_frame = margin_factors[margin_factors["factor_name"] == factor_name].reset_index(drop=True)
        sampled_factor = sampled_margin_factors[sampled_margin_factors["factor_name"] == factor_name].reset_index(drop=True)
        for row in _reference_correlations(
            sampled_factor,
            sampled_references,
            lead_factor_name=factor_name,
            min_cross_section=min_cross_section,
            high_corr_threshold=0.85,
            high_mean_abs_corr_threshold=0.55,
            moderate_corr_threshold=0.70,
            moderate_mean_abs_corr_threshold=0.35,
        ):
            row["lead_factor_name"] = factor_name
            reference_rows.append(row)

        merged_exposure = _merge_style_exposures(factor_frame, style_exposures)
        sampled_exposure = _sample_dates(merged_exposure, sample_every_n_dates=sample_every_n_dates)
        exposure_rows.extend(
            _style_exposure_correlations(
                sampled_exposure,
                lead_factor_name=factor_name,
                min_cross_section=min_cross_section,
            )
        )
        residual_name = f"{factor_name}__style_residual"
        residual_frame = _residualize_factor_frame(
            merged_exposure,
            residual_factor_name=residual_name,
            exposure_names=style_exposure_names,
            min_cross_section=min_cross_section,
        )
        residual_frame["parent_factor_name"] = factor_name
        residual_frames.append(residual_frame)
        observations = _lead_ic_observations(
            residual_frame,
            labels,
            lead_factor_name=residual_name,
            horizon=int(horizon),
            min_cross_section=min_cross_section,
        )
        residual_ic_observations.extend(observations)
        summary = _lead_ic_summary(observations, min_ic_observations=min_ic_observations)
        summary["factor_name"] = residual_name
        summary["parent_factor_name"] = factor_name
        summary["horizon"] = int(horizon)
        residual_ic_rows.append(summary)
        for row in _period_ic(observations, period="year"):
            row["factor_name"] = residual_name
            yearly_ic.append(row)
        for row in _period_ic(observations, period="month"):
            row["factor_name"] = residual_name
            monthly_ic.append(row)

    residual_factor_frame = (
        pd.concat(residual_frames, ignore_index=True)
        if residual_frames
        else pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "parent_factor_name"])
    )
    gate = _gate(
        margin_factors=margin_factors,
        reference_correlations=reference_rows,
        style_exposure_correlations=exposure_rows,
        residual_ic_summaries=residual_ic_rows,
        prescreen_report=prescreen_report,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "margin_credit_factor_count": int(len(factor_names)),
            "margin_credit_factor_rows": int(len(margin_factors)),
            "reference_factor_count": int(reference_factors["factor_name"].nunique()) if not reference_factors.empty else 0,
            "reference_factor_rows": int(len(reference_factors)),
            "residual_factor_count": int(residual_factor_frame["factor_name"].nunique())
            if not residual_factor_frame.empty
            else 0,
            "residual_factor_rows": int(len(residual_factor_frame)),
            "residual_ic_summary_count": int(len(residual_ic_rows)),
            "next_direction": "round194_margin_credit_walk_forward_only_if_residual_and_quantile_shape_clear_else_rotate_family",
        },
        "lead_factor_names": factor_names,
        "reference_factor_correlations": reference_rows,
        "style_exposure_correlations": exposure_rows,
        "residual_ic_summaries": residual_ic_rows,
        "residual_ic_observations": residual_ic_observations,
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "data_window": _data_window(clean_bars, margin_detail, margin_factors, reference_factors, residual_factor_frame, labels),
        "holdout_policy": {
            "final_holdout_included": bool(include_final_holdout),
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "final_holdout_start": "2026-01-01",
            "final_holdout_use": "blocked_until_oos_walk_forward_cost_capacity_regime_clearance",
        },
        "pit_policy": {
            "margin_join_date_column": "available_date",
            "margin_raw_date_must_be_before_signal_date": True,
            "execution_lag": int(execution_lag),
            "lookback_observations": int(lookback),
        },
        "sampling_policy": {
            "sample_every_n_dates": int(sample_every_n_dates),
            "sampling_used_for_correlations_only": True,
            "ic_uses_all_dates": True,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "requires_next_gate": "cost_capacity_walk_forward_regime_and_final_holdout_after_neutral_dedup",
            "blockers": gate["blockers"],
            "reason": "Round193 is a neutralization and redundancy audit. It cannot promote or portfolio-grid an IC-only signal.",
        },
        "gate": gate,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_external_feed_margin_credit_neutral_dedup_markdown(result)
    return result


def write_external_feed_margin_credit_neutral_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / f"{DEFAULT_OUTPUT_BASENAME}.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / f"{DEFAULT_OUTPUT_BASENAME}.md").write_text(
        render_external_feed_margin_credit_neutral_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "external_feed_margin_credit_reference_correlations.csv",
        result.get("reference_factor_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "external_feed_margin_credit_style_exposures.csv",
        result.get("style_exposure_correlations", []),
        STYLE_EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "external_feed_margin_credit_residual_ic.csv",
        result.get("residual_ic_summaries", []),
        RESIDUAL_IC_COLUMNS,
    )
    _write_csv(
        output_path / "external_feed_margin_credit_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "external_feed_margin_credit_residual_yearly_ic.csv",
        result.get("yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(
        output_path / "external_feed_margin_credit_residual_monthly_ic.csv",
        result.get("monthly_ic", []),
        ["factor_name", *MONTHLY_IC_COLUMNS],
    )


def render_external_feed_margin_credit_neutral_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    gate = result.get("gate", {})
    lines = [
        "# External Feed Margin Credit Neutral Dedup",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Margin factors: {summary.get('margin_credit_factor_count', 0)}",
        f"- Margin factor rows: {summary.get('margin_credit_factor_rows', 0)}",
        f"- Reference factors: {summary.get('reference_factor_count', 0)}",
        f"- Residual factors: {summary.get('residual_factor_count', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Gate blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
        "",
        "## Residual IC",
        "",
        "| Factor | Parent | Obs | Mean IC | ICIR | t | IC+ |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in result.get("residual_ic_summaries", []):
        lines.append(
            "| {factor_name} | {parent} | {obs} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} |".format(
                factor_name=row.get("factor_name", ""),
                parent=row.get("parent_factor_name", ""),
                obs=row.get("ic_observations", 0),
                ic=row.get("mean_spearman_ic", 0.0),
                icir=row.get("icir", 0.0),
                t=row.get("ic_t_stat", 0.0),
                pos=row.get("positive_ic_rate", 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Reference Correlation",
            "",
            "| Lead | Reference | Obs | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("reference_factor_correlations", []):
        lines.append(
            "| {lead} | {ref} | {obs} | {mean_abs:.3f} | {max_abs:.3f} | {klass} | {blockers} |".format(
                lead=row.get("lead_factor_name", ""),
                ref=row.get("factor_name", ""),
                obs=row.get("correlation_observations", 0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("redundancy_class", ""),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Style Exposure",
            "",
            "| Lead | Exposure | Obs | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("style_exposure_correlations", []):
        lines.append(
            "| {lead} | {exp} | {obs} | {mean_abs:.3f} | {max_abs:.3f} | {klass} | {blockers} |".format(
                lead=row.get("lead_factor_name", ""),
                exp=row.get("exposure_name", ""),
                obs=row.get("correlation_observations", 0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("exposure_class", ""),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "",
            f"- Sampling: {result.get('sampling_policy', {})}",
            f"- PIT: {result.get('pit_policy', {})}",
            f"- Safety: {result.get('safety', SAFETY)}",
            "",
        ]
    )
    return "\n".join(lines)


def _normalise_bars_for_audit(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "amount", "high", "low"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _style_exposure_frame(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", *STYLE_EXPOSURE_NAMES])
    pieces = []
    for _, group in bars.groupby("asset_id", sort=False):
        group = group.sort_values("date").copy()
        returns = group["adj_close"].pct_change()
        group["return_1d"] = returns
        group["adv20_amount"] = group["amount"].rolling(20, min_periods=5).mean()
        group["adv60_amount"] = group["amount"].rolling(60, min_periods=10).mean()
        group["log_adv20_amount"] = _safe_log(group["adv20_amount"])
        group["log_amount"] = _safe_log(group["amount"])
        group["momentum_20"] = group["adj_close"].pct_change(20)
        group["momentum_60"] = group["adj_close"].pct_change(60)
        group["reversal_5"] = -group["adj_close"].pct_change(5)
        group["realized_vol_20"] = returns.rolling(20, min_periods=5).std()
        group["amount_trend_20_60"] = group["adv20_amount"] / group["adv60_amount"].replace(0.0, np.nan) - 1.0
        pieces.append(group)
    output = pd.concat(pieces, ignore_index=True)
    columns = ["date", "asset_id", "market", *STYLE_EXPOSURE_NAMES]
    for name in STYLE_EXPOSURE_NAMES:
        output[name] = pd.to_numeric(output[name], errors="coerce")
        output[name] = _cross_sectional_zscore(output, name)
    return output[columns].replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def _safe_log(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.where(numeric > 0).map(lambda value: math.log(value) if pd.notna(value) else np.nan)


def _cross_sectional_zscore(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    mean = values.groupby(frame["date"]).transform("mean")
    std = values.groupby(frame["date"]).transform("std").replace(0.0, np.nan)
    return (values - mean) / std


def _merge_style_exposures(factor_frame: pd.DataFrame, style_exposures: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty:
        return factor_frame.copy()
    merged = factor_frame.merge(style_exposures, on=["date", "asset_id", "market"], how="left")
    return merged.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def _residualize_factor_frame(
    factor_frame: pd.DataFrame,
    *,
    residual_factor_name: str,
    exposure_names: Sequence[str],
    min_cross_section: int,
) -> pd.DataFrame:
    if factor_frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    exposures = [name for name in exposure_names if name in factor_frame]
    rows = []
    for _, group in factor_frame.groupby("date", sort=True):
        output = group[["date", "asset_id", "market", "factor_name", "factor_value"]].copy()
        output["factor_name"] = residual_factor_name
        output["factor_value"] = np.nan
        active_exposures = [
            name
            for name in exposures
            if pd.to_numeric(group[name], errors="coerce").replace([np.inf, -np.inf], np.nan).notna().sum()
            >= min_cross_section
        ]
        if not active_exposures:
            clean = group[["factor_value"]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(clean) < max(3, min_cross_section):
                rows.append(output)
                continue
            residual = clean["factor_value"].to_numpy(dtype=float) - float(clean["factor_value"].mean())
            if float(np.nanstd(residual)) <= 1e-12:
                rows.append(output)
                continue
            output.loc[clean.index, "factor_value"] = residual
            rows.append(output)
            continue
        clean = group[["factor_value", *active_exposures]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(clean) < max(3, min_cross_section):
            rows.append(output)
            continue
        x = clean[active_exposures].to_numpy(dtype=float)
        x = np.column_stack([np.ones(len(x)), x])
        y = clean["factor_value"].to_numpy(dtype=float)
        try:
            beta = np.linalg.lstsq(x, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            rows.append(output)
            continue
        residual = y - x @ beta
        if float(np.nanstd(residual)) <= 1e-12:
            rows.append(output)
            continue
        output.loc[clean.index, "factor_value"] = residual
        rows.append(output)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if result.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    return result.dropna(subset=["factor_value"]).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _style_exposure_correlations(
    factor_frame: pd.DataFrame,
    *,
    lead_factor_name: str,
    min_cross_section: int,
) -> list[dict[str, Any]]:
    rows = []
    for exposure_name in STYLE_EXPOSURE_NAMES:
        if exposure_name not in factor_frame:
            continue
        corr_values: list[float] = []
        cross_sections: list[int] = []
        for _, group in factor_frame.groupby("date", sort=True):
            group = group[["factor_value", exposure_name]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(group) < min_cross_section:
                continue
            corr = _spearman(group["factor_value"], group[exposure_name])
            if np.isfinite(corr):
                corr_values.append(corr)
                cross_sections.append(int(len(group)))
        if not corr_values:
            rows.append(
                {
                    "lead_factor_name": lead_factor_name,
                    "exposure_name": exposure_name,
                    "correlation_observations": 0,
                    "mean_correlation": 0.0,
                    "mean_abs_correlation": 0.0,
                    "median_abs_correlation": 0.0,
                    "max_abs_correlation": 0.0,
                    "positive_correlation_rate": 0.0,
                    "median_cross_section": 0.0,
                    "unique_dates": 0,
                    "exposure_class": "insufficient_overlap",
                    "blockers": ["insufficient_style_exposure_overlap"],
                }
            )
            continue
        series = pd.Series(corr_values, dtype=float)
        abs_series = series.abs()
        klass = _classify_exposure(float(abs_series.max()), float(abs_series.mean()))
        blockers = []
        if klass == "high_exposure":
            blockers.append("high_style_exposure_correlation")
        elif klass == "moderate_exposure":
            blockers.append("moderate_style_exposure_correlation")
        rows.append(
            {
                "lead_factor_name": lead_factor_name,
                "exposure_name": exposure_name,
                "correlation_observations": int(len(series)),
                "mean_correlation": float(series.mean()),
                "mean_abs_correlation": float(abs_series.mean()),
                "median_abs_correlation": float(abs_series.median()),
                "max_abs_correlation": float(abs_series.max()),
                "positive_correlation_rate": float((series > 0).mean()),
                "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
                "unique_dates": int(len(series)),
                "exposure_class": klass,
                "blockers": blockers,
            }
        )
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["exposure_name"]))


def _classify_exposure(max_abs_corr: float, mean_abs_corr: float) -> str:
    if max_abs_corr >= 0.85 or mean_abs_corr >= 0.55:
        return "high_exposure"
    if max_abs_corr >= 0.70 or mean_abs_corr >= 0.35:
        return "moderate_exposure"
    return "low_exposure"


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    ranked = aligned.rank(method="average")
    return float(ranked.iloc[:, 0].corr(ranked.iloc[:, 1]))


def _gate(
    *,
    margin_factors: pd.DataFrame,
    reference_correlations: list[dict[str, Any]],
    style_exposure_correlations: list[dict[str, Any]],
    residual_ic_summaries: list[dict[str, Any]],
    prescreen_report: dict[str, Any] | None,
) -> dict[str, Any]:
    blockers = [
        "industry_metadata_missing_or_not_pit",
        "portfolio_grid_blocked_before_cost_capacity_walk_forward",
        "requires_china_regime_stress_audit",
        "requires_final_holdout_clearance",
    ]
    if margin_factors.empty:
        blockers.append("margin_credit_factor_frame_empty")
    if _prescreen_has_monotonicity_blocker(prescreen_report):
        blockers.append("round192_quantile_monotonicity_blocker_not_cleared")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("margin_credit_highly_redundant_with_price_volume_reference")
    if any(row.get("redundancy_class") == "moderately_redundant" for row in reference_correlations):
        blockers.append("margin_credit_moderately_redundant_with_price_volume_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in style_exposure_correlations):
        blockers.append("margin_credit_high_style_exposure")
    if any(not row.get("minimum_observation_gate_passed", False) for row in residual_ic_summaries):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_ic_summaries and not any(_residual_ic_is_material(row) for row in residual_ic_summaries):
        blockers.append("style_residual_ic_not_material")
    blockers = sorted(dict.fromkeys(blockers))
    return {
        "passed": False,
        "blockers": blockers,
        "required_before": [
            "pit_industry_metadata_or_explicit_industry_blocker",
            "reference_factor_dedup",
            "style_residual_ic",
            "same_parameter_cost_capacity_walk_forward",
            "china_regime_stress_audit",
            "final_holdout_only_after_all_prior_gates",
        ],
        "allowed_next_stage": "controlled_walk_forward_preregistration_only_if_residual_quality_and_quantile_shape_clear",
    }


def _residual_ic_is_material(row: dict[str, Any]) -> bool:
    return bool(
        row.get("minimum_observation_gate_passed", False)
        and float(row.get("mean_spearman_ic", 0.0)) >= 0.02
        and float(row.get("ic_t_stat", 0.0)) >= 2.0
        and float(row.get("positive_ic_rate", 0.0)) >= 0.55
    )


def _prescreen_has_monotonicity_blocker(prescreen_report: dict[str, Any] | None) -> bool:
    for row in (prescreen_report or {}).get("results", []):
        blockers = row.get("blockers", [])
        if isinstance(blockers, str):
            blockers = [item.strip() for item in blockers.split(";") if item.strip()]
        if "quantile_monotonicity_weak" in blockers:
            return True
    return False


def _margin_specs_from_report_or_seed(
    prescreen_report: dict[str, Any] | None,
    seed_config_path: str | Path,
) -> list[dict[str, Any]]:
    report_names = [
        str(row.get("factor_name"))
        for row in (prescreen_report or {}).get("results", [])
        if str(row.get("factor_name")) in set(MARGIN_CREDIT_FACTOR_NAMES)
    ]
    if report_names:
        return [{"factor_name": name, "horizons": [DEFAULT_HORIZON]} for name in sorted(set(report_names))]
    path = Path(seed_config_path)
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))
        specs = [
            dict(seed)
            for seed in config.get("factor_seeds", [])
            if str(seed.get("factor_name")) in set(MARGIN_CREDIT_FACTOR_NAMES)
        ]
        if specs:
            return specs
    return [{"factor_name": name, "horizons": [DEFAULT_HORIZON]} for name in MARGIN_CREDIT_FACTOR_NAMES]


def _data_window(
    bars: pd.DataFrame,
    margin_detail: pd.DataFrame,
    margin_factors: pd.DataFrame,
    reference_factors: pd.DataFrame,
    residual_factors: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "min_margin_raw_date": _min_date(margin_detail, "date"),
        "max_margin_raw_date": _max_date(margin_detail, "date"),
        "margin_detail_rows": int(len(margin_detail)),
        "margin_detail_assets": int(margin_detail["asset_id"].nunique()) if "asset_id" in margin_detail else 0,
        "min_signal_date": _min_date(margin_factors, "date"),
        "max_signal_date": _max_date(margin_factors, "date"),
        "margin_factor_rows": int(len(margin_factors)),
        "reference_factor_rows": int(len(reference_factors)),
        "residual_factor_rows": int(len(residual_factors)),
        "label_rows": int(len(labels)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column]).dropna()
    if values.empty:
        return None
    return values.min().date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column]).dropna()
    if values.empty:
        return None
    return values.max().date().isoformat()
