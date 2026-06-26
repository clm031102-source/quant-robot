from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.data.ingest.tushare_analyst_reports import ANALYST_REPORT_COLUMNS, _normalize_analyst_report_rc
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    _data_window,
    _sanitize,
    _write_csv,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import (
    RESULT_COLUMNS,
    render_event_factor_pit_ic_prescreen_markdown,
    summarize_event_factor_pit_ic_prescreen,
)
from quant_robot.ops.event_factor_preregistration import SAFETY
from quant_robot.research.labels import make_forward_returns


STAGE = "analyst_report_revision_pit_prescreen"
NEXT_DIRECTION_WITH_LEADS = "analyst_report_revision_reference_dedup_before_portfolio_conversion"
NEXT_DIRECTION_WITHOUT_LEADS = "rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads"


@dataclass(frozen=True)
class AnalystReportCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    required_fields: tuple[str, ...]
    windows: tuple[int, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_analyst_report_candidate_specs() -> list[AnalystReportCandidateSpec]:
    refs = ("analyst_revision", "earnings_forecast_revision", "event_study")
    return [
        AnalystReportCandidateSpec(
            factor_name="analyst_target_upside_60",
            family="analyst_expectation_revision",
            formula_template="latest_target_price / signal_close - 1",
            direction="higher_is_better",
            required_fields=("report_date", "tp", "min_price", "max_price"),
            windows=(60,),
            economic_rationale="Sell-side target-price upside is a direct external expectation signal, unlike old price-volume proxies.",
            public_reference_tags=refs,
            expected_failure_modes=("broker_optimism_bias", "target_price_staleness", "large_cap_coverage_bias"),
        ),
        AnalystReportCandidateSpec(
            factor_name="analyst_np_revision_90",
            family="analyst_expectation_revision",
            formula_template="change(latest_report_np) / max(abs(previous_report_np), 1)",
            direction="higher_is_better",
            required_fields=("report_date", "np"),
            windows=(90,),
            economic_rationale="Upward net-profit forecast revisions can proxy improving expectations before realized statements.",
            public_reference_tags=refs,
            expected_failure_modes=("sparse_report_history", "quarter_mismatch", "industry_earnings_cycle_beta"),
        ),
        AnalystReportCandidateSpec(
            factor_name="analyst_eps_revision_90",
            family="analyst_expectation_revision",
            formula_template="change(latest_report_eps) / max(abs(previous_report_eps), 0.01)",
            direction="higher_is_better",
            required_fields=("report_date", "eps"),
            windows=(90,),
            economic_rationale="EPS forecast revisions are a standard public expectation-revision anomaly test.",
            public_reference_tags=refs,
            expected_failure_modes=("eps_scale_noise", "broker_coverage_bias", "quarter_mismatch"),
        ),
        AnalystReportCandidateSpec(
            factor_name="analyst_revision_target_composite_90",
            family="analyst_expectation_revision",
            formula_template="cs_z(target_upside)+cs_z(np_revision)+cs_z(eps_revision)+cs_z(rating_delta)",
            direction="higher_is_better",
            required_fields=("report_date", "tp", "np", "eps", "rating"),
            windows=(90,),
            economic_rationale="Combines independent analyst report dimensions while still using one frozen formula before testing.",
            public_reference_tags=refs,
            expected_failure_modes=("coverage_bias", "style_exposure", "report_cluster_overfit"),
        ),
    ]


def build_analyst_report_revision_prescreen(
    *,
    report_roots: Iterable[str | Path],
    bars_roots: Iterable[str | Path],
    stock_basic: pd.DataFrame,
    candidate_specs: Sequence[AnalystReportCandidateSpec] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_signal_date_amount: float = 10_000_000.0,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_analyst_report_candidate_specs())
    reports = load_analyst_report_cache(report_roots)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_analyst_report_revision_factors(
        reports,
        bars,
        candidate_specs=specs,
        pit_lag_trade_days=pit_lag_trade_days,
        min_signal_date_amount=min_signal_date_amount,
    )
    factor_frame = _filter_factor_dates(
        factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        report_title="Analyst Report Revision PIT/IC Prescreen",
        next_direction_with_leads=NEXT_DIRECTION_WITH_LEADS,
        next_direction_without_leads=NEXT_DIRECTION_WITHOUT_LEADS,
    )
    result["stage"] = STAGE
    result["data_window"] = {
        **_data_window(bars, factor_frame, labels),
        "report_rows": int(len(reports)),
        "report_assets": int(reports["asset_id"].nunique()) if not reports.empty else 0,
        "min_report_date": _min_date(reports, "report_date"),
        "max_report_date": _max_date(reports, "report_date"),
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_oos_and_neutral_ic_clearance",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "report_signal_date_rule": "first_trade_date_strictly_after_report_date_plus_extra_lag",
        "execution_lag": int(execution_lag),
        "same_day_report_trading_allowed": False,
    }
    result["source_policy"] = {
        "source": "tushare_report_rc",
        "provider_frequency_limit_observed": "about_1_request_per_minute",
        "row_cap_warning_requires_smaller_window": True,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "analyst_report_revision_reference_dedup_walk_forward_cost_capacity_regime",
        "reason": "This is a source-backed PIT/IC prescreen, not portfolio evidence.",
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_analyst_report_revision_prescreen_markdown(result)
    return result


def compute_analyst_report_revision_factors(
    reports: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[AnalystReportCandidateSpec] | None = None,
    pit_lag_trade_days: int = 1,
    min_signal_date_amount: float = 10_000_000.0,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_analyst_report_candidate_specs())
    allowed = {spec.factor_name for spec in specs}
    reports = _normalize_analyst_report_rc(reports)
    if reports.empty or not allowed:
        return _empty_factor_frame()
    daily = _daily_report_snapshot(reports)
    daily = _attach_signal_dates(daily, bars, pit_lag_trade_days=pit_lag_trade_days)
    daily = _attach_bar_context(daily, bars)
    daily = daily[
        (daily["amount"] >= float(min_signal_date_amount))
        & (daily["adv20_amount"] >= float(min_signal_date_amount))
        & (daily["adj_close"] > 0)
    ].copy()
    if daily.empty:
        return _empty_factor_frame()
    daily = _add_revision_features(daily)
    values = {
        "analyst_target_upside_60": daily["target_upside"],
        "analyst_np_revision_90": daily["np_revision"],
        "analyst_eps_revision_90": daily["eps_revision"],
        "analyst_revision_target_composite_90": (
            _date_zscore(daily, "target_upside").fillna(0.0)
            + _date_zscore(daily, "np_revision").fillna(0.0)
            + _date_zscore(daily, "eps_revision").fillna(0.0)
            + _date_zscore(daily, "rating_delta").fillna(0.0)
        ),
    }
    pieces: list[pd.DataFrame] = []
    base_columns = [
        "date",
        "event_date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "log_adv20",
        "pit_lag_trade_days",
        "source_event_count",
    ]
    for factor_name, factor_values in values.items():
        if factor_name not in allowed:
            continue
        frame = daily[base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = factor_values
        frame = frame.dropna(subset=["factor_value"])
        pieces.append(frame)
    if not pieces:
        return _empty_factor_frame()
    return pd.concat(pieces, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def load_analyst_report_cache(roots: Iterable[str | Path]) -> pd.DataFrame:
    files: list[Path] = []
    for root in roots:
        root_path = Path(root)
        files.extend(sorted((root_path / "processed" / "analyst_report_rc").rglob("*.parquet")))
        files.extend(sorted((root_path / "processed" / "analyst_report_rc").rglob("*.csv")))
        files.extend(sorted((root_path / "processed" / "analyst_report_rc_window").rglob("*.parquet")))
        files.extend(sorted((root_path / "processed" / "analyst_report_rc_window").rglob("*.csv")))
        if not files:
            files.extend(sorted(root_path.rglob("*analyst_report_rc*.parquet")))
            files.extend(sorted(root_path.rglob("*analyst_report_rc*.csv")))
    frames = [_read_frame(file) for file in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=ANALYST_REPORT_COLUMNS)
    return _normalize_analyst_report_rc(pd.concat(frames, ignore_index=True))


def write_analyst_report_revision_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "analyst_report_revision_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "analyst_report_revision_prescreen.md").write_text(
        render_analyst_report_revision_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "analyst_report_revision_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "analyst_report_revision_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "analyst_report_revision_prescreen_neutral_observations.csv",
        result.get("neutral_observations", []),
        [
            "factor_name",
            "horizon",
            "date",
            "industry_neutral_rank_ic",
            "size_neutral_rank_ic",
            "cross_section",
            "industry_count",
        ],
    )


def render_analyst_report_revision_prescreen_markdown(result: dict[str, Any]) -> str:
    base = render_event_factor_pit_ic_prescreen_markdown(result)
    source = result.get("source_policy", {})
    return (
        base
        + "\n## Analyst Source Policy\n\n"
        + f"- Source: {source.get('source', 'tushare_report_rc')}\n"
        + f"- Observed provider limit: {source.get('provider_frequency_limit_observed', '')}\n"
        + "- Report rows are shifted to a later tradable signal date; same-day report trading is blocked.\n"
    )


def _daily_report_snapshot(reports: pd.DataFrame) -> pd.DataFrame:
    frame = reports.copy()
    frame["report_date"] = pd.to_datetime(frame["report_date"])
    frame["rating_score"] = frame["rating"].map(_rating_score)
    frame["target_price"] = pd.to_numeric(frame["tp"], errors="coerce").combine_first(
        (pd.to_numeric(frame["min_price"], errors="coerce") + pd.to_numeric(frame["max_price"], errors="coerce")) / 2.0
    )
    grouped = (
        frame.groupby(["asset_id", "symbol", "market", "report_date"], as_index=False)
        .agg(
            eps=("eps", "mean"),
            np=("np", "mean"),
            roe=("roe", "mean"),
            target_price=("target_price", "median"),
            rating_score=("rating_score", "mean"),
            source_event_count=("source", "size"),
        )
        .sort_values(["asset_id", "report_date"])
        .reset_index(drop=True)
    )
    grouped["event_date"] = grouped["report_date"]
    return grouped


def _attach_signal_dates(frame: pd.DataFrame, bars: pd.DataFrame, *, pit_lag_trade_days: int) -> pd.DataFrame:
    trade_dates = pd.Index(sorted(pd.to_datetime(bars["date"]).dropna().unique()))
    if trade_dates.empty or frame.empty:
        return frame.iloc[0:0].copy()
    output = frame.copy()
    signal_dates = []
    extra_lag = max(int(pit_lag_trade_days), 1) - 1
    for event_date in pd.to_datetime(output["event_date"], errors="coerce"):
        if pd.isna(event_date):
            signal_dates.append(pd.NaT)
            continue
        index = trade_dates.searchsorted(event_date, side="right") + extra_lag
        signal_dates.append(trade_dates[index] if index < len(trade_dates) else pd.NaT)
    output["date"] = pd.to_datetime(signal_dates)
    output["pit_lag_trade_days"] = int(pit_lag_trade_days)
    return output.dropna(subset=["date"]).reset_index(drop=True)


def _attach_bar_context(frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    context = bars.sort_values(["asset_id", "date"]).copy()
    context["date"] = pd.to_datetime(context["date"])
    context["asset_id"] = context["asset_id"].astype(str)
    context["market"] = context["market"].fillna("CN").astype(str).str.upper()
    context["amount"] = pd.to_numeric(context["amount"], errors="coerce")
    context["adj_close"] = pd.to_numeric(context["adj_close"], errors="coerce")
    context["adv20_amount"] = context.groupby("asset_id")["amount"].transform(lambda item: item.rolling(20, min_periods=5).mean())
    context["log_adv20"] = context["adv20_amount"].map(lambda value: math.log(value) if pd.notna(value) and value > 0 else pd.NA)
    return frame.merge(
        context[["date", "asset_id", "market", "adj_close", "amount", "adv20_amount", "log_adv20"]],
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )


def _add_revision_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.sort_values(["asset_id", "date"]).copy()
    for column in ("np", "eps", "target_price", "rating_score"):
        output[f"prev_{column}"] = output.groupby("asset_id")[column].shift(1)
    output["np_revision"] = _signed_revision(output["np"], output["prev_np"], floor=1.0)
    output["eps_revision"] = _signed_revision(output["eps"], output["prev_eps"], floor=0.01)
    output["target_revision"] = _signed_revision(output["target_price"], output["prev_target_price"], floor=0.01)
    output["rating_delta"] = output["rating_score"] - output["prev_rating_score"]
    output["target_upside"] = output["target_price"] / output["adj_close"].where(output["adj_close"] > 0) - 1.0
    return output


def _signed_revision(current: pd.Series, previous: pd.Series, *, floor: float) -> pd.Series:
    current = pd.to_numeric(current, errors="coerce")
    previous = pd.to_numeric(previous, errors="coerce")
    denominator = previous.abs().clip(lower=float(floor))
    return (current - previous) / denominator


def _date_zscore(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    mean = values.groupby(frame["date"]).transform("mean")
    std = values.groupby(frame["date"]).transform("std").replace(0.0, pd.NA)
    return (values - mean) / std


def _rating_score(value: Any) -> float:
    text = str(value).strip().lower()
    if not text:
        return float("nan")
    if any(token in text for token in ("买入", "strong buy", "buy", "增持", "推荐")):
        return 5.0
    if any(token in text for token in ("优于", "outperform", "overweight")):
        return 4.0
    if any(token in text for token in ("中性", "neutral", "持有", "hold")):
        return 3.0
    if any(token in text for token in ("减持", "underperform", "卖出", "sell")):
        return 1.0
    return float("nan")


def _filter_factor_dates(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.DataFrame()


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return pd.Timestamp(values.min()).date().isoformat() if not values.empty else None


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return pd.Timestamp(values.max()).date().isoformat() if not values.empty else None


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "event_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "pit_lag_trade_days",
            "source_event_count",
        ]
    )
