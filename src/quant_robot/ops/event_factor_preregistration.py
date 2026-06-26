from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


STAGE = "event_factor_preregistration"
ROUND145_SOURCE_AUDIT = "docs/research/cn_stock_daily_basic_free_float_supply_quality_final_holdout_round145_2026-06-22.md"
ROUND146_NEXT_DIRECTION = "round147_event_factor_pit_coverage_ic_prescreen_for_available_candidates"
SOURCE_EVIDENCE_STATUS = "event_endpoint_preregistered_not_empirical_alpha"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

DEFAULT_EVENT_ENDPOINTS = (
    "forecast",
    "express",
    "dividend",
    "repurchase",
    "stk_holdernumber",
    "share_float",
    "top10_holders",
    "top10_floatholders",
    "pledge_stat",
)

DEFAULT_PIT_CONTROLS = (
    "ann_date_or_effective_date_lag",
    "next_trade_date_execution",
    "same_parameter_long_cycle_required",
    "walk_forward_required_before_portfolio",
    "final_holdout_result_gate_required",
)


class EventEndpointAdapter(Protocol):
    def fetch_event_endpoint(self, endpoint: str, **kwargs: object) -> pd.DataFrame:
        ...


@dataclass(frozen=True)
class EventFactorCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    required_endpoints: tuple[str, ...]
    required_fields: tuple[str, ...]
    event_date_fields: tuple[str, ...]
    windows: tuple[int, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    pit_controls: tuple[str, ...] = DEFAULT_PIT_CONTROLS
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_event_factor_candidate_specs() -> list[EventFactorCandidateSpec]:
    return [
        EventFactorCandidateSpec(
            factor_name="event_forecast_profit_revision_1q",
            family="earnings_forecast",
            formula_template="cs_z(mid(p_change_min,p_change_max)) + 0.5*cs_z(mid(net_profit_min,net_profit_max))",
            direction="higher_is_better",
            required_endpoints=("forecast",),
            required_fields=("ann_date", "end_date", "p_change_min", "p_change_max", "net_profit_min", "net_profit_max"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Positive profit forecast revisions are public earnings-news events with a clear post-announcement drift thesis.",
            public_reference_tags=("earnings_announcement_drift", "post_earnings_announcement_drift", "alphalens"),
            expected_failure_modes=("forecast_sparse_coverage", "announcement_date_lag_error", "earnings_season_concentration"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_express_profit_surprise_1q",
            family="earnings_express",
            formula_template="0.6*cs_z(yoy_net_profit)+0.4*cs_z(diluted_roe)",
            direction="higher_is_better",
            required_endpoints=("express",),
            required_fields=("ann_date", "end_date", "yoy_net_profit", "diluted_roe"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Earnings express growth and ROE can proxy early financial surprise before full statements are released.",
            public_reference_tags=("earnings_quality", "post_earnings_announcement_drift", "qlib"),
            expected_failure_modes=("express_sparse_coverage", "financial_restated_later", "industry_cycle_beta"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_disagreement_1q",
            family="forecast_express_disagreement_event",
            formula_template="express_yoy_net_profit - latest_prior_forecast_midpoint",
            direction="higher_is_better",
            required_endpoints=("forecast", "express"),
            required_fields=("ann_date", "end_date", "p_change_min", "p_change_max", "yoy_net_profit"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Earnings express releases can correct stale or inaccurate management forecast ranges; signal is tradable only after the express announcement.",
            public_reference_tags=("earnings_revision", "expectation_update", "event_study"),
            expected_failure_modes=("forecast_express_join_sparse", "industry_cycle_beta", "stale_forecast_noise"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_disagreement_industry_relative_1q",
            family="forecast_express_disagreement_event",
            formula_template="(express_yoy_net_profit - latest_prior_forecast_midpoint) - same_day_industry_median",
            direction="higher_is_better",
            required_endpoints=("forecast", "express"),
            required_fields=("ann_date", "end_date", "p_change_min", "p_change_max", "yoy_net_profit"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Industry-relative forecast/express disagreement targets within-industry expectation updates instead of raw industry-cycle beta.",
            public_reference_tags=("earnings_revision", "industry_neutral_event_study", "post_earnings_announcement_drift"),
            expected_failure_modes=("forecast_express_join_sparse", "small_industry_event_cohort", "industry_cycle_beta"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_express_stale_forecast_correction_1q",
            family="forecast_express_disagreement_event",
            formula_template="(express_yoy_net_profit - latest_prior_forecast_midpoint) * log1p(days_since_forecast)",
            direction="higher_is_better",
            required_endpoints=("forecast", "express"),
            required_fields=("ann_date", "end_date", "p_change_min", "p_change_max", "yoy_net_profit"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="A later express release that strongly revises an older forecast may contain a larger expectation update than a fresh forecast/express gap.",
            public_reference_tags=("earnings_revision", "stale_expectation_update", "event_study"),
            expected_failure_modes=("stale_forecast_noise", "forecast_express_join_sparse", "calendar_clustering"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_dividend_cash_yield_announced_1y",
            family="dividend_event",
            formula_template="cs_z(cash_div / prior_close) with ex_date and pay_date separated",
            direction="higher_is_better",
            required_endpoints=("dividend",),
            required_fields=("ann_date", "ex_date", "pay_date", "cash_div", "cash_div_tax"),
            event_date_fields=("ann_date", "ex_date"),
            windows=(252,),
            economic_rationale="Cash dividend announcements test a real shareholder-yield event rather than a daily-basic dividend proxy.",
            public_reference_tags=("dividend_yield", "shareholder_yield", "pyfolio"),
            expected_failure_modes=("ex_right_price_adjustment_error", "dividend_value_trap", "event_clustering"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_repurchase_amount_to_mv_20",
            family="buyback_event",
            formula_template="cs_z(repurchase_amount / lagged_total_mv)",
            direction="higher_is_better",
            required_endpoints=("repurchase",),
            required_fields=("ann_date", "amount", "vol", "high_limit", "low_limit"),
            event_date_fields=("ann_date",),
            windows=(20,),
            economic_rationale="Buyback announcements can signal undervaluation and shareholder-return intent when scaled by market value.",
            public_reference_tags=("buyback_anomaly", "shareholder_yield", "event_study"),
            expected_failure_modes=("announced_not_executed", "amount_unit_mismatch", "small_cap_capacity_tail"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_holder_number_contraction_2q",
            family="holder_crowding",
            formula_template="cs_z(-(holder_num / lag(holder_num,2)-1))",
            direction="higher_is_better",
            required_endpoints=("stk_holdernumber",),
            required_fields=("ann_date", "end_date", "holder_num"),
            event_date_fields=("ann_date",),
            windows=(2,),
            economic_rationale="A falling shareholder count can indicate ownership concentration and reduced retail crowding.",
            public_reference_tags=("ownership_concentration", "crowding", "alphalens"),
            expected_failure_modes=("stale_holder_dates", "microcap_crowding_artifact", "quarterly_sample_low_power"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_share_unlock_pressure_60",
            family="share_unlock_supply",
            formula_template="cs_z(-(float_share / lagged_circ_share))",
            direction="higher_is_better",
            required_endpoints=("share_float",),
            required_fields=("ann_date", "float_date", "float_share", "float_ratio", "share_type"),
            event_date_fields=("ann_date", "float_date"),
            windows=(60,),
            economic_rationale="Large upcoming float increases are supply shocks; avoiding them is an event-driven risk premia hypothesis.",
            public_reference_tags=("share_unlock", "supply_pressure", "event_study"),
            expected_failure_modes=("float_date_vs_ann_date_confusion", "low_frequency_events", "coverage_sparse"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_top_holder_concentration_change_1q",
            family="holder_concentration",
            formula_template="cs_z(sum_top10_hold_ratio - lag(sum_top10_hold_ratio,1))",
            direction="higher_is_better",
            required_endpoints=("top10_holders", "top10_floatholders"),
            required_fields=("ann_date", "end_date", "hold_ratio", "hold_change", "holder_type"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Increasing top-holder concentration can proxy informed accumulation, but must survive industry and size neutralization.",
            public_reference_tags=("institutional_ownership", "ownership_concentration", "event_study"),
            expected_failure_modes=("holder_name_dedup_error", "industry_concentration", "quarterly_reporting_lag"),
        ),
        EventFactorCandidateSpec(
            factor_name="event_pledge_ratio_relief_1q",
            family="pledge_risk",
            formula_template="cs_z(-(pledge_ratio - lag(pledge_ratio,1)))",
            direction="higher_is_better",
            required_endpoints=("pledge_stat",),
            required_fields=("end_date", "pledge_ratio", "pledge_count", "total_share"),
            event_date_fields=("end_date",),
            windows=(1,),
            economic_rationale="Falling pledge pressure can reduce crash-risk overhang; rising pledge pressure is treated as a risk exclusion candidate.",
            public_reference_tags=("pledge_risk", "crash_risk", "event_study"),
            expected_failure_modes=("no_ann_date_available", "risk_filter_not_alpha", "state_owned_enterprise_bias"),
        ),
    ]


def probe_event_endpoints(
    adapter: EventEndpointAdapter,
    *,
    sample_symbols: tuple[str, ...] = ("000001.SZ", "600519.SH", "300750.SZ"),
    start_date: str = "2024-01-01",
    end_date: str = "2026-06-15",
    ann_dates: tuple[str, ...] = ("20240105", "20240430", "20250829"),
    periods: tuple[str, ...] = ("20240331", "20240630", "20240930", "20241231"),
    endpoints: tuple[str, ...] = DEFAULT_EVENT_ENDPOINTS,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for endpoint in endpoints:
        results[endpoint] = _probe_single_endpoint(
            adapter,
            endpoint=endpoint,
            sample_symbols=sample_symbols,
            start_date=start_date,
            end_date=end_date,
            ann_dates=ann_dates,
            periods=periods,
        )
    return results


def probe_event_cross_section_patterns(
    adapter: EventEndpointAdapter,
    *,
    min_rows: int = 30,
    forecast_ann_date: str = "20240131",
    express_start_date: str = "2024-01-01",
    express_end_date: str = "2024-03-31",
    dividend_ann_date: str = "20240329",
    dividend_end_date: str = "20231231",
    holder_start_date: str = "2024-01-01",
    holder_end_date: str = "2024-03-31",
    top_holder_period: str = "20240331",
    repurchase_ann_dates: tuple[str, ...] = ("20240105", "20250829"),
) -> dict[str, dict[str, Any]]:
    probes: list[tuple[str, str, dict[str, str]]] = [
        ("forecast_ann_date", "forecast", {"ann_date": _date_to_tushare(forecast_ann_date)}),
        (
            "express_start_end",
            "express",
            {"start_date": _date_to_tushare(express_start_date), "end_date": _date_to_tushare(express_end_date)},
        ),
        ("dividend_ann_date", "dividend", {"ann_date": _date_to_tushare(dividend_ann_date)}),
        ("dividend_end_date", "dividend", {"end_date": _date_to_tushare(dividend_end_date)}),
        (
            "holdernumber_start_end",
            "stk_holdernumber",
            {"start_date": _date_to_tushare(holder_start_date), "end_date": _date_to_tushare(holder_end_date)},
        ),
        ("top10_holders_period", "top10_holders", {"period": _date_to_tushare(top_holder_period)}),
        ("top10_floatholders_period", "top10_floatholders", {"period": _date_to_tushare(top_holder_period)}),
    ]
    for ann_date in repurchase_ann_dates:
        probes.append((f"repurchase_ann_date_{_date_to_tushare(ann_date)}", "repurchase", {"ann_date": _date_to_tushare(ann_date)}))

    output: dict[str, dict[str, Any]] = {}
    for label, endpoint, kwargs in probes:
        output[label] = _probe_cross_section_pattern(
            adapter,
            endpoint=endpoint,
            kwargs=kwargs,
            min_rows=min_rows,
        )
    return output


def build_event_factor_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 5,
    min_available_endpoints: int = 5,
    min_available_candidates: int = 5,
    min_available_families: int = 5,
    candidate_specs: list[EventFactorCandidateSpec] | None = None,
    endpoint_probe_results: dict[str, dict[str, Any]] | None = None,
    cross_section_probe_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    specs = candidate_specs or default_event_factor_candidate_specs()
    endpoint_probe_results = endpoint_probe_results or {}
    available_endpoints = {
        endpoint
        for endpoint, result in endpoint_probe_results.items()
        if _is_endpoint_available(result)
    }
    candidates = [
        _candidate_to_dict(
            spec,
            available_endpoints=available_endpoints,
            endpoint_probe_results=endpoint_probe_results,
        )
        for spec in specs
    ]
    available_candidates = [
        candidate for candidate in candidates if candidate.get("endpoint_availability_status") == "available"
    ]
    blocked_candidates = [
        candidate for candidate in candidates if candidate.get("endpoint_availability_status") == "blocked"
    ]
    available_families = {str(candidate.get("family")) for candidate in available_candidates}
    families = {spec.family for spec in specs}
    blockers = _blockers(
        specs,
        min_candidates=min_candidates,
        min_families=min_families,
        min_available_endpoints=min_available_endpoints,
        min_available_candidates=min_available_candidates,
        min_available_families=min_available_families,
        available_candidate_count=len(available_candidates),
        available_family_count=len(available_families),
        available_endpoints=available_endpoints,
        endpoint_probe_results=endpoint_probe_results,
    )
    passes = not blockers
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": passes,
            "candidate_count": len(specs),
            "family_count": len(families),
            "available_endpoint_count": len(available_endpoints),
            "endpoint_count": len(endpoint_probe_results),
            "available_candidate_count": len(available_candidates),
            "available_family_count": len(available_families),
            "blocked_candidate_count": len(blocked_candidates),
            "portfolio_backtest_allowed_candidates": sum(1 for spec in specs if spec.portfolio_backtest_allowed),
            "promotion_allowed_candidates": sum(1 for spec in specs if spec.promotion_allowed),
            "next_required_gate": ROUND146_NEXT_DIRECTION,
            "blockers": blockers,
        },
        "family_rotation_context": {
            "source_audit": ROUND145_SOURCE_AUDIT,
            "hibernated_families": [
                "daily_basic_free_float_supply_quality",
                "daily_basic_free_float_supply_quality_parameter_expansion",
                "aggregate_walk_forward_without_final_holdout_result",
            ],
            "next_direction": ROUND146_NEXT_DIRECTION,
        },
        "event_endpoint_probe": endpoint_probe_results,
        "event_cross_section_probe": cross_section_probe_results or {},
        "available_endpoints": sorted(available_endpoints),
        "candidates": candidates,
        "available_candidates": available_candidates,
        "blocked_candidates": blocked_candidates,
        "evaluation_gate": {
            "required_metrics": [
                "event_endpoint_coverage",
                "point_in_time_ann_or_effective_date_alignment",
                "min_cross_section_per_event_date",
                "industry_size_neutral_ic",
                "quantile_monotonicity",
                "cost_capacity_walk_forward",
                "final_holdout_readiness_audit",
                "final_holdout_result_audit",
            ],
            "blocked_until": ROUND146_NEXT_DIRECTION,
        },
        "promotion_policy": {
            "portfolio_backtest_allowed_before_prescreen": False,
            "promotion_allowed": False,
            "reason": "Round146 is event-family preregistration and endpoint availability smoke only.",
        },
        "source_evidence_status": SOURCE_EVIDENCE_STATUS,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_markdown(result)
    return result


def write_event_factor_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_factor_preregistration.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_factor_preregistration.md").write_text(render_markdown(result), encoding="utf-8")
    _write_candidates_csv(output_path / "event_factor_candidates.csv", result.get("candidates", []))
    _write_endpoints_csv(output_path / "event_endpoint_probe.csv", _dict(result.get("event_endpoint_probe")))
    _write_cross_section_csv(output_path / "event_cross_section_probe.csv", _dict(result.get("event_cross_section_probe")))


def render_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    rotation = _dict(result.get("family_rotation_context"))
    promotion = _dict(result.get("promotion_policy"))
    lines = [
        "# CN Stock Event Factor Preregistration Round146",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Available endpoints: {summary.get('available_endpoint_count', 0)} / {summary.get('endpoint_count', 0)}",
        f"- Next gate: `{summary.get('next_required_gate', ROUND146_NEXT_DIRECTION)}`",
        f"- Source audit: {rotation.get('source_audit', ROUND145_SOURCE_AUDIT)}",
        f"- Promotion allowed: {promotion.get('promotion_allowed', False)}",
        f"- Portfolio before prescreen: {promotion.get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(summary.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Endpoint Probe", "", "| Endpoint | OK | Rows | Columns | Error |", "|---|---:|---:|---|---|"])
    for endpoint, probe in sorted(_dict(result.get("event_endpoint_probe")).items()):
        probe_dict = _dict(probe)
        columns = ",".join(_list(probe_dict.get("columns"))[:8])
        lines.append(
            f"| {endpoint} | {probe_dict.get('ok', False)} | {int(_number(probe_dict.get('rows')))} | {columns} | {probe_dict.get('error', '')} |"
        )
    lines.extend(["", "## Candidates", "", "| Factor | Family | Endpoints | Fields |", "|---|---|---|---|"])
    for candidate in _list_of_dicts(result.get("candidates")):
        lines.append(
            "| {name} | {family} | {endpoints} | {fields} |".format(
                name=candidate.get("factor_name", ""),
                family=candidate.get("family", ""),
                endpoints=",".join(_list(candidate.get("required_endpoints"))),
                fields=",".join(_list(candidate.get("required_fields"))),
            )
        )
    cross_section = _dict(result.get("event_cross_section_probe"))
    if cross_section:
        lines.extend(
            [
                "",
                "## Cross-Section Query Patterns",
                "",
                "| Pattern | Endpoint | Ready | Rows |",
                "|---|---|---:|---:|",
            ]
        )
        for label, probe in sorted(cross_section.items()):
            probe_dict = _dict(probe)
            lines.append(
                f"| {label} | {probe_dict.get('endpoint', '')} | {probe_dict.get('cross_section_ready', False)} | {int(_number(probe_dict.get('rows')))} |"
            )
    return "\n".join(lines) + "\n"


def _probe_single_endpoint(
    adapter: EventEndpointAdapter,
    *,
    endpoint: str,
    sample_symbols: tuple[str, ...],
    start_date: str,
    end_date: str,
    ann_dates: tuple[str, ...],
    periods: tuple[str, ...],
) -> dict[str, Any]:
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    requests = _endpoint_requests(
        endpoint,
        sample_symbols=sample_symbols,
        start_date=start_date,
        end_date=end_date,
        ann_dates=ann_dates,
        periods=periods,
    )
    for kwargs in requests:
        try:
            frame = adapter.fetch_event_endpoint(endpoint, **kwargs)
            if isinstance(frame, pd.DataFrame):
                frames.append(frame)
        except Exception as exc:  # pragma: no cover - live provider behavior
            errors.append(str(exc))
    if not frames:
        return {"ok": False, "rows": 0, "columns": [], "error": "; ".join(errors)}
    rows = int(sum(len(frame) for frame in frames))
    columns = _unique_preserving_order(column for frame in frames for column in frame.columns)
    return {
        "ok": not errors,
        "rows": rows,
        "columns": columns,
        "requests": len(requests),
        "error": "; ".join(errors),
    }


def _probe_cross_section_pattern(
    adapter: EventEndpointAdapter,
    *,
    endpoint: str,
    kwargs: dict[str, str],
    min_rows: int,
) -> dict[str, Any]:
    try:
        frame = adapter.fetch_event_endpoint(endpoint, **kwargs)
    except Exception as exc:  # pragma: no cover - live provider behavior
        return {
            "endpoint": endpoint,
            "kwargs": kwargs,
            "ok": False,
            "rows": 0,
            "columns": [],
            "cross_section_ready": False,
            "error": str(exc),
        }
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame()
    rows = int(len(frame))
    columns = [str(column) for column in frame.columns]
    return {
        "endpoint": endpoint,
        "kwargs": kwargs,
        "ok": True,
        "rows": rows,
        "columns": columns,
        "cross_section_ready": rows >= min_rows and "ts_code" in set(columns),
        "error": "",
    }


def _endpoint_requests(
    endpoint: str,
    *,
    sample_symbols: tuple[str, ...],
    start_date: str,
    end_date: str,
    ann_dates: tuple[str, ...],
    periods: tuple[str, ...],
) -> list[dict[str, str]]:
    start = _date_to_tushare(start_date)
    end = _date_to_tushare(end_date)
    if endpoint in {"forecast", "express", "stk_holdernumber", "share_float", "pledge_stat"}:
        return [{"ts_code": symbol, "start_date": start, "end_date": end} for symbol in sample_symbols]
    if endpoint == "dividend":
        return [{"ts_code": symbol} for symbol in sample_symbols]
    if endpoint == "repurchase":
        return [{"ann_date": ann_date} for ann_date in ann_dates]
    if endpoint in {"top10_holders", "top10_floatholders"}:
        return [{"ts_code": symbol, "period": period} for symbol in sample_symbols for period in periods]
    return [{"ts_code": symbol, "start_date": start, "end_date": end} for symbol in sample_symbols]


def _candidate_to_dict(
    spec: EventFactorCandidateSpec,
    *,
    available_endpoints: set[str] | None = None,
    endpoint_probe_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    available_endpoints = available_endpoints or set()
    endpoint_probe_results = endpoint_probe_results or {}
    missing_endpoints = [
        endpoint
        for endpoint in spec.required_endpoints
        if endpoint_probe_results and endpoint not in available_endpoints
    ]
    endpoint_status = "not_probed"
    if endpoint_probe_results:
        endpoint_status = "available" if not missing_endpoints else "blocked"
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "required_endpoints": list(spec.required_endpoints),
        "required_fields": list(spec.required_fields),
        "event_date_fields": list(spec.event_date_fields),
        "windows": list(spec.windows),
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "pit_controls": list(spec.pit_controls),
        "source_evidence_status": spec.source_evidence_status,
        "endpoint_availability_status": endpoint_status,
        "unavailable_endpoints": missing_endpoints,
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
        "next_required_gate": ROUND146_NEXT_DIRECTION,
        "market": "CN",
        "asset_type": "stock",
    }


def _blockers(
    specs: list[EventFactorCandidateSpec],
    *,
    min_candidates: int,
    min_families: int,
    min_available_endpoints: int,
    min_available_candidates: int,
    min_available_families: int,
    available_candidate_count: int,
    available_family_count: int,
    available_endpoints: set[str],
    endpoint_probe_results: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if len(specs) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({spec.family for spec in specs}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if endpoint_probe_results and len(available_endpoints) < min_available_endpoints:
        blockers.append("available_event_endpoints_below_minimum")
    if endpoint_probe_results and available_candidate_count < min_available_candidates:
        blockers.append("available_candidate_count_below_minimum")
    if endpoint_probe_results and available_family_count < min_available_families:
        blockers.append("available_candidate_family_breadth_below_minimum")
    if len({spec.factor_name for spec in specs}) != len(specs):
        blockers.append("duplicate_factor_names")
    if any(not spec.public_reference_tags for spec in specs):
        blockers.append("missing_public_reference_tags")
    if any(not spec.expected_failure_modes for spec in specs):
        blockers.append("missing_expected_failure_modes")
    if any(spec.portfolio_backtest_allowed for spec in specs):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(spec.promotion_allowed for spec in specs):
        blockers.append("promotion_allowed_before_prescreen")
    return _unique_preserving_order(blockers)


def _is_endpoint_available(result: dict[str, Any]) -> bool:
    return bool(result.get("ok")) and _number(result.get("rows")) > 0 and bool(_list(result.get("columns")))


def _write_candidates_csv(path: Path, candidates: Any) -> None:
    rows = _list_of_dicts(candidates)
    fieldnames = [
        "factor_name",
        "family",
        "direction",
        "required_endpoints",
        "required_fields",
        "event_date_fields",
        "windows",
        "source_evidence_status",
        "portfolio_backtest_allowed",
        "promotion_allowed",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ",".join(str(item) for item in row.get(key, []))
                    if isinstance(row.get(key), list)
                    else row.get(key, "")
                    for key in fieldnames
                }
            )


def _write_endpoints_csv(path: Path, endpoints: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["endpoint", "ok", "rows", "columns", "error"])
        writer.writeheader()
        for endpoint, probe in sorted(endpoints.items()):
            probe_dict = _dict(probe)
            writer.writerow(
                {
                    "endpoint": endpoint,
                    "ok": probe_dict.get("ok", False),
                    "rows": int(_number(probe_dict.get("rows"))),
                    "columns": ",".join(_list(probe_dict.get("columns"))),
                    "error": probe_dict.get("error", ""),
                }
            )


def _write_cross_section_csv(path: Path, probes: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["pattern", "endpoint", "cross_section_ready", "rows", "columns", "error"])
        writer.writeheader()
        for pattern, probe in sorted(probes.items()):
            probe_dict = _dict(probe)
            writer.writerow(
                {
                    "pattern": pattern,
                    "endpoint": probe_dict.get("endpoint", ""),
                    "cross_section_ready": probe_dict.get("cross_section_ready", False),
                    "rows": int(_number(probe_dict.get("rows"))),
                    "columns": ",".join(_list(probe_dict.get("columns"))),
                    "error": probe_dict.get("error", ""),
                }
            )


def _date_to_tushare(value: str) -> str:
    return str(value).replace("-", "")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _unique_preserving_order(values: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value)
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
