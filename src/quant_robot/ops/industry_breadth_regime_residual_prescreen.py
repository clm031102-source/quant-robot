from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.factors.industry_breadth_regime import (
    INDUSTRY_BREADTH_REGIME_FACTOR_NAMES,
    compute_industry_breadth_regime_factors,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.industry_leader_lag_residual_prescreen import (
    EXPOSURE_CORRELATION_COLUMNS,
    IC_OBSERVATION_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    RESULT_COLUMNS,
    YEARLY_IC_COLUMNS,
    _collect_stream_shard_observations,
    _data_window,
    _empty_factor_frame,
    _empty_label_frame,
    _empty_stream_data_stats,
    _empty_stream_state,
    _normalise_exposure_frame,
    _normalise_factor_frame,
    _sanitize,
    _stream_data_window,
    _trim_signal_window,
    _update_stream_data_stats,
    _write_csv,
    _year_signal_shards,
    build_industry_leader_lag_bar_features,
    build_industry_leader_lag_exposure_frame,
    build_industry_leader_lag_labels,
    build_industry_leader_lag_reference_frame,
    summarize_industry_leader_lag_residual_prescreen,
    summarize_industry_leader_lag_streaming_prescreen,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import _load_stock_basic


STAGE = "industry_breadth_regime_residual_prescreen"
FAMILY = "industry_breadth_dispersion_regime_translation"
ROUND261_SOURCE_REPORT = "docs/research/cn_stock_round260_official_tradeability_event_residual_prescreen_2026-06-26.md"
NEXT_DIRECTION_WITH_LEADS = "round262_industry_breadth_regime_reference_dedup_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round262_rotate_after_industry_breadth_regime_failure"


def build_industry_breadth_regime_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    candidate_factor_names: Sequence[str] = INDUSTRY_BREADTH_REGIME_FACTOR_NAMES,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    include_reference_factors: bool = True,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    features = build_industry_leader_lag_bar_features(
        bars,
        stock_basic_frame,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    exposure_frame = build_industry_leader_lag_exposure_frame(features, stock_basic_frame)
    factor_frame = build_industry_breadth_regime_factor_frame(
        bars,
        stock_basic_frame,
        exposure_frame,
        candidate_factor_names=candidate_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = (
        build_industry_leader_lag_reference_frame(bars, exposure_frame) if include_reference_factors else _empty_factor_frame()
    )
    labels = build_industry_leader_lag_labels(features, horizons=tuple(horizons))
    result = summarize_industry_breadth_regime_residual_prescreen(
        factor_frame,
        labels,
        reference_factor_frame=reference_frame,
        exposure_frame=exposure_frame,
        candidate_factor_names=candidate_factor_names,
        horizons=tuple(horizons),
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    result["bars_roots"] = [str(Path(root)) for root in bars_roots]
    result["stock_basic"] = str(stock_basic) if isinstance(stock_basic, (str, Path)) else None
    result["data_window"] = _data_window(bars, factor_frame, reference_frame, exposure_frame, labels)
    result["holdout_policy"] = _holdout_policy(analysis_start_date, analysis_end_date, include_final_holdout)
    result["capacity_policy"] = _capacity_policy(min_signal_date_amount)
    result["sampling_policy"] = _sampling_policy(sample_every_n_dates)
    result["markdown"] = render_industry_breadth_regime_residual_prescreen_markdown(result)
    return result


def build_industry_breadth_regime_sharded_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    candidate_factor_names: Sequence[str] = INDUSTRY_BREADTH_REGIME_FACTOR_NAMES,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    lookback_calendar_days: int = 140,
    forward_calendar_days: int | None = None,
    sample_every_n_dates: int = 5,
    include_reference_factors: bool = True,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    analysis_start = pd.Timestamp(analysis_start_date).normalize()
    analysis_end = pd.Timestamp(analysis_end_date).normalize()
    if analysis_end < analysis_start:
        raise ValueError("analysis_end_date must be on or after analysis_start_date")
    forward_days = int(forward_calendar_days) if forward_calendar_days is not None else int(max(horizons) + execution_lag + 10)
    if lookback_calendar_days < 0 or forward_days < 0:
        raise ValueError("lookback_calendar_days and forward_calendar_days must be non-negative")

    stock_basic_frame = _stock_basic_frame(stock_basic)
    shard_rows: list[dict[str, Any]] = []
    stream = _empty_stream_state(candidate_factor_names)
    data_stats = _empty_stream_data_stats()
    for shard_start, shard_end in _year_signal_shards(analysis_start, analysis_end):
        load_start = shard_start - pd.Timedelta(days=int(lookback_calendar_days))
        load_end = shard_end + pd.Timedelta(days=forward_days)
        bars = load_public_reference_multi_family_bars(
            bars_roots,
            analysis_start_date=load_start.date().isoformat(),
            analysis_end_date=load_end.date().isoformat(),
            include_final_holdout=include_final_holdout,
        )
        features = build_industry_leader_lag_bar_features(
            bars,
            stock_basic_frame,
            horizons=tuple(horizons),
            execution_lag=execution_lag,
        )
        exposure_frame = build_industry_leader_lag_exposure_frame(features, stock_basic_frame)
        factor_frame = build_industry_breadth_regime_factor_frame(
            bars,
            stock_basic_frame,
            exposure_frame,
            candidate_factor_names=candidate_factor_names,
            min_signal_date_amount=min_signal_date_amount,
        )
        reference_frame = (
            build_industry_leader_lag_reference_frame(bars, exposure_frame)
            if include_reference_factors
            else _empty_factor_frame()
        )
        labels = build_industry_leader_lag_labels(features, horizons=tuple(horizons))
        signal_bars = _trim_signal_window(bars, shard_start, shard_end)
        factor_frame = _trim_signal_window(factor_frame, shard_start, shard_end)
        reference_frame = _trim_signal_window(reference_frame, shard_start, shard_end)
        exposure_frame = _trim_signal_window(exposure_frame, shard_start, shard_end)
        labels = _trim_signal_window(labels, shard_start, shard_end)
        _update_stream_data_stats(
            data_stats,
            signal_bars=signal_bars,
            factor_frame=factor_frame,
            reference_frame=reference_frame,
            exposure_frame=exposure_frame,
            labels=labels,
        )
        _collect_stream_shard_observations(
            stream,
            factor_frame=factor_frame,
            labels=labels,
            reference_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=candidate_factor_names,
            horizons=tuple(horizons),
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
        )
        shard_rows.append(
            {
                "shard_id": f"{shard_start:%Y}",
                "signal_start_date": shard_start.date().isoformat(),
                "signal_end_date": shard_end.date().isoformat(),
                "load_start_date": load_start.date().isoformat(),
                "load_end_date": load_end.date().isoformat(),
                "loaded_bar_rows": int(len(bars)),
                "signal_bar_rows": int(len(signal_bars)),
                "factor_rows": int(len(factor_frame)),
                "reference_factor_rows": int(len(reference_frame)),
                "label_rows": int(len(labels)),
            }
        )

    result = summarize_industry_breadth_regime_streaming_prescreen(
        stream,
        candidate_factor_names=candidate_factor_names,
        horizons=tuple(horizons),
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    result["bars_roots"] = [str(Path(root)) for root in bars_roots]
    result["stock_basic"] = str(stock_basic) if isinstance(stock_basic, (str, Path)) else None
    result["data_window"] = _stream_data_window(data_stats)
    result["holdout_policy"] = _holdout_policy(analysis_start_date, analysis_end_date, include_final_holdout)
    result["capacity_policy"] = _capacity_policy(min_signal_date_amount)
    result["sampling_policy"] = _sampling_policy(sample_every_n_dates)
    result["sharding_policy"] = {
        "enabled": True,
        "frequency": "year",
        "shard_count": len(shard_rows),
        "streaming_summary": True,
        "lookback_calendar_days": int(lookback_calendar_days),
        "forward_calendar_days": int(forward_days),
        "signal_start_date": analysis_start.date().isoformat(),
        "signal_end_date": analysis_end.date().isoformat(),
        "padding_rows_used_for_features_only": True,
        "shards": shard_rows,
    }
    result["markdown"] = render_industry_breadth_regime_residual_prescreen_markdown(result)
    return result


def summarize_industry_breadth_regime_residual_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None,
    exposure_frame: pd.DataFrame | None,
    candidate_factor_names: Sequence[str],
    horizons: tuple[int, ...],
    sample_every_n_dates: int = 1,
    min_cross_section: int,
    min_ic_observations: int,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    result = summarize_industry_leader_lag_residual_prescreen(
        factor_frame,
        labels,
        reference_factor_frame=reference_factor_frame,
        exposure_frame=exposure_frame,
        candidate_factor_names=candidate_factor_names,
        horizons=tuple(horizons),
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    return _retitle_result(result, len(tuple(candidate_factor_names)))


def summarize_industry_breadth_regime_streaming_prescreen(
    stream: dict[str, Any],
    *,
    candidate_factor_names: Sequence[str],
    horizons: tuple[int, ...],
    min_ic_observations: int,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    result = summarize_industry_leader_lag_streaming_prescreen(
        stream,
        candidate_factor_names=candidate_factor_names,
        horizons=tuple(horizons),
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    return _retitle_result(result, len(tuple(candidate_factor_names)))


def build_industry_breadth_regime_factor_frame(
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame | None,
    exposure_frame: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    min_signal_date_amount: float,
) -> pd.DataFrame:
    factors = compute_industry_breadth_regime_factors(
        bars,
        stock_basic=stock_basic,
        factor_names=tuple(candidate_factor_names),
    )
    if factors.empty:
        return _empty_factor_frame()
    factors = _normalise_factor_frame(factors)
    exposure = _normalise_exposure_frame(exposure_frame)
    merged = factors.merge(
        exposure,
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )
    capacity_mask = (
        (merged["amount"] >= min_signal_date_amount)
        & (merged["adv20_amount"] >= min_signal_date_amount)
        & (merged["return_1d"].abs() <= 0.50)
    )
    merged["family"] = FAMILY
    return (
        merged.loc[capacity_mask]
        .dropna(subset=["factor_value", "amount", "adv20_amount", "industry"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_industry_breadth_regime_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "industry_breadth_regime_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "industry_breadth_regime_residual_prescreen.md").write_text(
        render_industry_breadth_regime_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "industry_breadth_regime_residual_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "industry_breadth_regime_reference_correlations.csv",
        result.get("reference_correlations", []),
        ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS],
    )
    _write_csv(
        output_path / "industry_breadth_regime_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS],
    )
    _write_csv(output_path / "industry_breadth_regime_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(
        output_path / "industry_breadth_regime_industry_neutral_yearly_ic.csv",
        result.get("industry_neutral_yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(
        output_path / "industry_breadth_regime_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(output_path / "industry_breadth_regime_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(
        output_path / "industry_breadth_regime_industry_neutral_ic_observations.csv",
        result.get("industry_neutral_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "industry_breadth_regime_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_industry_breadth_regime_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Industry Breadth-Regime Residual Prescreen Round261",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Source audit: {result.get('source_context', {}).get('source_audit', ROUND261_SOURCE_REPORT)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Industry-neutral rows: {summary.get('industry_neutral_rows', 0)}",
        f"- Residual rows: {summary.get('residual_rows', 0)}",
        f"- Residual research leads: {summary.get('residual_research_lead_count', 0)}",
        f"- Portfolio grid allowed candidates: {summary.get('portfolio_grid_allowed_candidates', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', '')}",
        "",
        "## Results",
        "",
        "| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | Ref High | Exposure High | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        blockers = ", ".join(row.get("blockers", []))
        lines.append(
            "| {factor_name} | {horizon} | {raw:.4f} | {neutral:.4f} | {residual:.4f} | {icir:.3f} | "
            "{ref_high} | {exposure_high} | {lead} | {blockers} |".format(
                factor_name=row.get("factor_name"),
                horizon=row.get("horizon"),
                raw=_csv_value(row.get("raw_mean_spearman_ic")),
                neutral=_csv_value(row.get("industry_neutral_mean_spearman_ic")),
                residual=_csv_value(row.get("residual_mean_spearman_ic")),
                icir=_csv_value(row.get("residual_icir")),
                ref_high=row.get("reference_highly_redundant_count", 0),
                exposure_high=row.get("style_exposure_high_count", 0),
                lead="yes" if row.get("residual_research_lead") else "no",
                blockers=blockers,
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is a residual IC and reference de-duplication prescreen, not a promotion or portfolio stage.",
            "- The family translates industry breadth and internal dispersion states into stock-level residual signals.",
            "- Short-window smoke signals must be replayed on the 2015-2025 long cycle before portfolio work.",
            "- Zero residual leads require family rotation instead of parameter or window tuning.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _retitle_result(result: dict[str, Any], candidate_count: int) -> dict[str, Any]:
    lead_count = int(result.get("summary", {}).get("residual_research_lead_count", 0))
    next_direction = NEXT_DIRECTION_WITH_LEADS if lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    result["stage"] = STAGE
    result["generated_at"] = date.today().isoformat()
    result["source_context"] = {
        "source_audit": ROUND261_SOURCE_REPORT,
        "candidate_family": FAMILY,
        "portfolio_grid_blocked_at_this_stage": True,
        "not_plain_industry_leader_lag": True,
        "uses_industry_breadth_and_dispersion_state": True,
    }
    result.setdefault("summary", {})["next_direction"] = next_direction
    result["multiple_testing_policy"] = {
        "method": "all Round261 industry breadth-regime candidate x horizon tests counted before any promotion claim",
        "round261_candidate_count": int(candidate_count),
        "test_count": int(result.get("summary", {}).get("test_count", 0)),
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_grid_allowed_before_residual_prescreen": False,
        "requires_next_gate": "reference_dedup_cost_capacity_walk_forward_after_residual_lead",
        "reason": "Round261 is an industry/style residual IC prescreen only.",
    }
    result["markdown"] = render_industry_breadth_regime_residual_prescreen_markdown(result)
    return result


def _holdout_policy(analysis_start_date: str, analysis_end_date: str, include_final_holdout: bool) -> dict[str, Any]:
    return {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_residual_prescreen_walk_forward_cost_capacity_clearance_only",
    }


def _capacity_policy(min_signal_date_amount: float) -> dict[str, Any]:
    return {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_grid_blocked_before_residual_prescreen": True,
    }


def _sampling_policy(sample_every_n_dates: int) -> dict[str, Any]:
    return {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }


def _stock_basic_frame(value: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return _load_stock_basic(value) if value is not None else pd.DataFrame()


def _csv_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")

