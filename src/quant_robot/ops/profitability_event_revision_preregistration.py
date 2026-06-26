from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
)
from quant_robot.ops.profitability_quality_preregistration import (
    _dataset_quality,
    _load_fina_indicator_inputs,
    _sanitize,
)


STAGE = "profitability_event_revision_preregistration"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_REQUIRED_GATE = "round152_pit_profitability_event_revision_matrix_and_label_smoke"
SOURCE_AUDIT = "docs/research/cn_stock_lottery_extreme_upside_reversal_prescreen_round150_2026-06-23.md"
SOURCE_EVIDENCE_STATUS = "pit_profitability_event_revision_preregistered_not_empirical_alpha"
STATIC_ROUND96_NAMES = {
    "fina_roe_level",
    "fina_roa_level",
    "fina_net_margin_level",
    "fina_gross_margin_level",
    "fina_netprofit_yoy_growth",
    "fina_revenue_yoy_growth",
    "fina_profit_growth_quality_spread",
    "fina_cash_earnings_quality_ratio",
    "fina_profitability_quality_blend",
    "fina_growth_quality_blend",
    "fina_roe_persistence_4q",
    "fina_roa_persistence_4q",
    "fina_net_margin_improvement_yoy",
    "fina_ocfps_improvement_yoy",
}
DEFAULT_PIT_CONTROLS = (
    "ann_date_signal_availability",
    "next_trade_date_execution_required",
    "no_report_period_end_signal",
    "financial_revision_or_restated_row_dedup",
    "same_parameter_long_cycle_before_ic_claim",
)


@dataclass(frozen=True)
class ProfitabilityEventRevisionCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    required_financial_columns: tuple[str, ...]
    required_endpoints: tuple[str, ...]
    required_endpoint_fields: tuple[str, ...]
    event_date_fields: tuple[str, ...]
    windows: tuple[int, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    min_history_quarters: int = 1
    min_row_coverage: float = 0.55
    pit_controls: tuple[str, ...] = DEFAULT_PIT_CONTROLS
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_profitability_event_revision_candidate_specs() -> list[ProfitabilityEventRevisionCandidateSpec]:
    return [
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_netprofit_yoy_revision_1q",
            family="fina_revision_event",
            formula_template="cs_z(netprofit_yoy - lag(netprofit_yoy, 1)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("netprofit_yoy",),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Profit-growth acceleration announced at the PIT date can proxy fresh earnings information rather than a static quality level.",
            public_reference_tags=("earnings_revision", "post_earnings_announcement_drift", "alphalens"),
            expected_failure_modes=("quarterly_seasonality", "small_shard_false_positive", "industry_cycle_beta"),
            min_history_quarters=2,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_revenue_profit_revision_spread_1q",
            family="fina_revision_event",
            formula_template="cs_z((netprofit_yoy-or_yoy) - lag(netprofit_yoy-or_yoy, 1)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("netprofit_yoy", "or_yoy"),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Profit growth improving faster than revenue growth after announcement can mark operating leverage or cost control surprise.",
            public_reference_tags=("earnings_revision", "operating_leverage", "qlib"),
            expected_failure_modes=("margin_accounting_noise", "cyclical_sector_beta", "weak_cross_section"),
            min_history_quarters=2,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_margin_revision_yoy_4q",
            family="margin_revision",
            formula_template="cs_z(netprofit_margin - lag(netprofit_margin, 4)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("netprofit_margin",),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(4,),
            economic_rationale="Year-over-year margin improvement is a financial event signal and avoids using period-end information before release.",
            public_reference_tags=("margin_revision", "quality", "event_study"),
            expected_failure_modes=("inflation_cycle_beta", "accounting_policy_change", "late_reporter_bias"),
            min_history_quarters=5,
            min_row_coverage=0.45,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_roe_revision_persistence_4q",
            family="profitability_persistence_revision",
            formula_template="cs_z((roe-lag(roe,4)) + 0.5*rolling_mean(roe,4)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("roe",),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(4,),
            economic_rationale="ROE improvement is only useful if profitability persistence is present; this explicitly differs from the rejected static ROE level.",
            public_reference_tags=("profitability_revision", "quality_minus_junk", "event_study"),
            expected_failure_modes=("leverage_disguise", "state_owned_enterprise_bias", "weak_incremental_ic"),
            min_history_quarters=5,
            min_row_coverage=0.45,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_cash_profit_revision_4q",
            family="cash_quality_surprise",
            formula_template="cs_z((ocfps-lag(ocfps,4)) - 0.25*abs(netprofit_yoy-or_yoy)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("ocfps", "netprofit_yoy", "or_yoy"),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(4,),
            economic_rationale="Cash-flow improvement can confirm that reported growth is not purely accrual-driven.",
            public_reference_tags=("cash_earnings_quality", "accrual_anomaly", "alphalens"),
            expected_failure_modes=("cashflow_seasonality", "industry_working_capital_cycle", "coverage_sparse"),
            min_history_quarters=5,
            min_row_coverage=0.45,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_cash_earnings_confirmation_1q",
            family="cash_quality_surprise",
            formula_template="cs_z(netprofit_yoy) + cs_z(ocfps/abs(cfps)) at ann_date",
            direction="higher_is_better",
            required_financial_columns=("netprofit_yoy", "ocfps", "cfps"),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Profit growth accompanied by operating cash generation is more credible than static profit growth alone.",
            public_reference_tags=("cash_earnings_quality", "earnings_quality", "qlib"),
            expected_failure_modes=("cfps_denominator_noise", "bank_insurer_accounting_mismatch", "sector_concentration"),
            min_history_quarters=1,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_fina_quality_surprise_blend_1q",
            family="revision_confirmation_blend",
            formula_template="0.3*cs_z(delta_roe_1q)+0.3*cs_z(delta_margin_1q)+0.2*cs_z(delta_ocfps_1q)+0.2*cs_z(netprofit_yoy-or_yoy)",
            direction="higher_is_better",
            required_financial_columns=("roe", "netprofit_margin", "ocfps", "netprofit_yoy", "or_yoy"),
            required_endpoints=(),
            required_endpoint_fields=(),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="A compact blend tests whether several announced improvements agree before any return evidence is viewed.",
            public_reference_tags=("earnings_revision", "quality", "multiple_testing_control"),
            expected_failure_modes=("composite_overfit", "factor_crowding", "weak_monotonicity"),
            min_history_quarters=2,
            min_row_coverage=0.50,
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_forecast_profit_revision_event_1q",
            family="forecast_revision_event",
            formula_template="cs_z(mid(p_change_min,p_change_max)) + 0.5*cs_z(mid(net_profit_min,net_profit_max)) by ann_date",
            direction="higher_is_better",
            required_financial_columns=(),
            required_endpoints=("forecast",),
            required_endpoint_fields=("ann_date", "end_date", "p_change_min", "p_change_max"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Forecast revisions are explicit earnings-news events and should be tested separately from static accounting levels.",
            public_reference_tags=("earnings_forecast_revision", "post_earnings_announcement_drift", "event_study"),
            expected_failure_modes=("forecast_sparse_coverage", "announcement_cluster", "management_guidance_bias"),
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_express_profit_surprise_event_1q",
            family="forecast_revision_event",
            formula_template="0.6*cs_z(yoy_net_profit)+0.4*cs_z(diluted_roe) by ann_date",
            direction="higher_is_better",
            required_financial_columns=(),
            required_endpoints=("express",),
            required_endpoint_fields=("ann_date", "end_date", "yoy_net_profit", "diluted_roe"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="Earnings express data can arrive before full statements and may capture timely surprise.",
            public_reference_tags=("earnings_express", "quality_surprise", "qlib"),
            expected_failure_modes=("express_sparse_coverage", "restatement_drift", "industry_beta"),
        ),
        ProfitabilityEventRevisionCandidateSpec(
            factor_name="pit_forecast_express_quality_confirmation_1q",
            family="revision_confirmation_blend",
            formula_template="forecast_or_express_surprise confirmed by latest PIT cash-profit quality",
            direction="higher_is_better",
            required_financial_columns=("ocfps", "cfps", "netprofit_yoy"),
            required_endpoints=("forecast", "express"),
            required_endpoint_fields=("ann_date", "end_date"),
            event_date_fields=("ann_date",),
            windows=(1,),
            economic_rationale="A forecast or express surprise should be stronger when the latest PIT financials confirm cash-backed profit quality.",
            public_reference_tags=("earnings_revision", "cash_earnings_quality", "event_study"),
            expected_failure_modes=("endpoint_join_sparse", "confirmation_lag", "multiple_testing_noise"),
            min_history_quarters=1,
        ),
    ]


def build_profitability_event_revision_preregistration(
    *,
    input_root: str | Path,
    min_assets: int = 50,
    min_passed_candidates: int = 6,
    min_families: int = 3,
    candidate_specs: Iterable[ProfitabilityEventRevisionCandidateSpec | dict[str, Any]] | None = None,
    endpoint_probe_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_path = Path(input_root)
    frame = _load_fina_indicator_inputs(input_path)
    quality = _dataset_quality(frame)
    specs = [_coerce_spec(spec) for spec in (candidate_specs or default_profitability_event_revision_candidate_specs())]
    endpoint_probe_results = endpoint_probe_results or {}
    candidates = [
        _candidate_payload(
            spec,
            frame,
            endpoint_probe_results=endpoint_probe_results,
            min_assets=min_assets,
        )
        for spec in specs
    ]
    pre_registered = [candidate for candidate in candidates if candidate["registration_status"] == "pre_registered"]
    blockers = list(quality.get("blockers", []))
    blockers.extend(_global_blockers(specs, candidates, min_passed_candidates=min_passed_candidates, min_families=min_families))
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "input_root": str(input_path),
        "source_context": {
            "source_audit": SOURCE_AUDIT,
            "rotation_reason": "Round150 lottery/MAX-effect produced zero research leads; rotate to PIT financial information timing.",
            "hibernated_families": [
                "round96_static_profitability_quality",
                "round150_lottery_max_effect_direct_long_alpha",
            ],
        },
        "summary": {
            "passes": not blockers,
            "blockers": _dedupe(blockers),
            "candidate_count": len(candidates),
            "coverage_passed_candidates": len(pre_registered),
            "coverage_failed_candidates": len(candidates) - len(pre_registered),
            "family_count": len({candidate["family"] for candidate in candidates}),
            "pre_registered_family_count": len({candidate["family"] for candidate in pre_registered}),
            "min_assets": int(min_assets),
            "min_passed_candidates": int(min_passed_candidates),
            "min_families": int(min_families),
            "rows": int(quality.get("rows", 0)),
            "assets": int(quality.get("assets", 0)),
            "portfolio_backtest_allowed_candidates": sum(1 for candidate in candidates if candidate["portfolio_backtest_allowed"]),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "dataset_quality": quality,
        "endpoint_probe": endpoint_probe_results,
        "research_control_plan": default_cn_stock_pre_mining_control_plan(),
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "factor_matrix_label_alignment_after_ann_date",
                "minimum_cross_section_size",
                "multiple_testing_fdr",
                "industry_neutral_ic",
                "size_liquidity_neutral_ic",
                "quantile_monotonicity",
                "reference_correlation_vs_static_profitability_quality",
            ],
            "portfolio_backtest_allowed_after": "controlled_ic_and_neutral_prescreen_lead_only",
        },
        "promotion_policy": default_cn_stock_promotion_policy(),
        "candidates": candidates,
        "source_evidence_status": SOURCE_EVIDENCE_STATUS,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_profitability_event_revision_preregistration_markdown(result)
    return result


def write_profitability_event_revision_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_event_revision_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_event_revision_preregistration.md").write_text(
        render_profitability_event_revision_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "profitability_event_revision_candidates.csv", _candidate_csv_rows(result))


def render_profitability_event_revision_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    quality = result.get("dataset_quality", {})
    lines = [
        "# PIT Profitability Event Revision Preregistration Round151",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Input root: `{result.get('input_root', '')}`",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Assets: {summary.get('assets', 0)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Pre-registered candidates: {summary.get('coverage_passed_candidates', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next gate: `{summary.get('next_required_gate', NEXT_REQUIRED_GATE)}`",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Dataset Quality",
        "",
        f"- Duplicate financial keys: {quality.get('duplicate_rows', 0)}",
        f"- Missing PIT rows: {quality.get('missing_pit_date_rows', 0)}",
        f"- Announcement before report-period rows: {quality.get('ann_date_before_report_period_rows', 0)}",
        f"- Ann date range: {quality.get('ann_date_start')} to {quality.get('ann_date_end')}",
        f"- Report period range: {quality.get('report_period_start')} to {quality.get('report_period_end')}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Status | Required financial columns | Required endpoints | Coverage | Assets |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for candidate in result.get("candidates", []) or []:
        coverage = candidate.get("coverage", {})
        lines.append(
            "| {name} | {family} | {status} | `{cols}` | `{endpoints}` | {coverage:.2%} | {assets} |".format(
                name=candidate.get("factor_name", ""),
                family=candidate.get("family", ""),
                status=candidate.get("registration_status", ""),
                cols="`, `".join(candidate.get("required_financial_columns", []) or []),
                endpoints="`, `".join(candidate.get("required_endpoints", []) or []),
                coverage=float(coverage.get("row_coverage", 0.0)),
                assets=int(coverage.get("eligible_assets", 0)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This round pre-registers hypotheses only; it does not calculate IC, Sharpe, return, drawdown, or win rate.",
            "- Financial rows must be aligned by `ann_date`; report-period end dates are not signal dates.",
            "- Endpoint-dependent candidates remain blocked unless forecast/express availability is proven.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_payload(
    spec: ProfitabilityEventRevisionCandidateSpec,
    frame: pd.DataFrame,
    *,
    endpoint_probe_results: dict[str, dict[str, Any]],
    min_assets: int,
) -> dict[str, Any]:
    coverage = _candidate_coverage(spec, frame, min_assets=min_assets)
    endpoint_status = _endpoint_status(spec, endpoint_probe_results)
    status = "pre_registered"
    if not coverage["passes"]:
        status = "blocked_by_coverage"
    if not endpoint_status["passes"]:
        status = "blocked_by_endpoint_availability"
    payload = {
        **asdict(spec),
        "required_financial_columns": list(spec.required_financial_columns),
        "required_endpoints": list(spec.required_endpoints),
        "required_endpoint_fields": list(spec.required_endpoint_fields),
        "event_date_fields": list(spec.event_date_fields),
        "windows": list(spec.windows),
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "pit_controls": list(spec.pit_controls),
        "registration_status": status,
        "coverage": coverage,
        "endpoint_availability": endpoint_status,
        "market": "CN",
        "asset_type": "stock",
        "hypothesis_source": "public_reference:" + ",".join(spec.public_reference_tags),
        "next_required_gate": NEXT_REQUIRED_GATE,
        "lookahead_policy": "Use ann_date or explicit event effective date as signal availability; trade only after a later tradable bar.",
    }
    return payload


def _candidate_coverage(
    spec: ProfitabilityEventRevisionCandidateSpec,
    frame: pd.DataFrame,
    *,
    min_assets: int,
) -> dict[str, Any]:
    if frame.empty:
        return _blocked_coverage(["missing_input_rows"], frame, min_assets)
    missing = [column for column in spec.required_financial_columns if column not in frame.columns]
    if missing:
        return _blocked_coverage(["missing_required_financial_columns"], frame, min_assets, missing_columns=missing)
    if not spec.required_financial_columns:
        eligible_mask = pd.Series([True] * len(frame), index=frame.index)
    else:
        required_mask = frame[list(spec.required_financial_columns)].notna().all(axis=1)
        history_count = required_mask.astype(int).groupby(frame["asset_id"]).cumsum()
        eligible_mask = required_mask & (history_count >= spec.min_history_quarters)
    eligible_rows = int(eligible_mask.sum())
    total_rows = int(len(frame))
    row_coverage = eligible_rows / total_rows if total_rows else 0.0
    eligible_assets = int(frame.loc[eligible_mask, "asset_id"].nunique(dropna=True)) if "asset_id" in frame else 0
    eligible_periods = int(frame.loc[eligible_mask, "end_date"].nunique(dropna=True)) if "end_date" in frame else 0
    blockers: list[str] = []
    if row_coverage < spec.min_row_coverage:
        blockers.append("row_coverage_below_threshold")
    if eligible_assets < min_assets:
        blockers.append("eligible_assets_below_threshold")
    if spec.min_history_quarters > 1 and eligible_periods < spec.min_history_quarters:
        blockers.append("history_periods_below_threshold")
    return {
        "passes": not blockers,
        "blockers": blockers,
        "missing_required_financial_columns": [],
        "eligible_rows": eligible_rows,
        "total_rows": total_rows,
        "row_coverage": row_coverage,
        "eligible_assets": eligible_assets,
        "eligible_report_periods": eligible_periods,
        "min_row_coverage": spec.min_row_coverage,
        "min_assets": min_assets,
        "min_history_quarters": spec.min_history_quarters,
    }


def _endpoint_status(
    spec: ProfitabilityEventRevisionCandidateSpec,
    endpoint_probe_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing_endpoints = []
    missing_fields = []
    for endpoint in spec.required_endpoints:
        probe = endpoint_probe_results.get(endpoint, {})
        if probe.get("ok") is not True:
            missing_endpoints.append(endpoint)
            continue
        columns = {str(column) for column in probe.get("columns", []) or []}
        endpoint_missing = [field for field in spec.required_endpoint_fields if field not in columns]
        if endpoint_missing:
            missing_fields.extend(f"{endpoint}.{field}" for field in endpoint_missing)
    blockers: list[str] = []
    if missing_endpoints:
        blockers.append("missing_required_endpoints")
    if missing_fields:
        blockers.append("missing_required_endpoint_fields")
    return {
        "passes": not blockers,
        "blockers": blockers,
        "missing_required_endpoints": missing_endpoints,
        "missing_required_endpoint_fields": missing_fields,
        "required_endpoints": list(spec.required_endpoints),
        "required_endpoint_fields": list(spec.required_endpoint_fields),
    }


def _global_blockers(
    specs: list[ProfitabilityEventRevisionCandidateSpec],
    candidates: list[dict[str, Any]],
    *,
    min_passed_candidates: int,
    min_families: int,
) -> list[str]:
    blockers: list[str] = []
    names = [spec.factor_name for spec in specs]
    if len(names) != len(set(names)):
        blockers.append("duplicate_candidate_names")
    if any(name in STATIC_ROUND96_NAMES for name in names):
        blockers.append("round96_static_profitability_name_reused")
    pre_registered = [candidate for candidate in candidates if candidate["registration_status"] == "pre_registered"]
    if len(pre_registered) < min_passed_candidates:
        blockers.append("coverage_passed_candidates_below_minimum")
    if len({candidate["family"] for candidate in pre_registered}) < min_families:
        blockers.append("pre_registered_family_count_below_minimum")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    return blockers


def _blocked_coverage(
    blockers: list[str],
    frame: pd.DataFrame,
    min_assets: int,
    *,
    missing_columns: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "passes": False,
        "blockers": blockers,
        "missing_required_financial_columns": missing_columns or [],
        "eligible_rows": 0,
        "total_rows": int(len(frame)),
        "row_coverage": 0.0,
        "eligible_assets": 0,
        "eligible_report_periods": 0,
        "min_row_coverage": 0.0,
        "min_assets": min_assets,
        "min_history_quarters": 0,
    }


def _coerce_spec(value: ProfitabilityEventRevisionCandidateSpec | dict[str, Any]) -> ProfitabilityEventRevisionCandidateSpec:
    if isinstance(value, ProfitabilityEventRevisionCandidateSpec):
        return value
    payload = dict(value)
    for key in [
        "required_financial_columns",
        "required_endpoints",
        "required_endpoint_fields",
        "event_date_fields",
        "windows",
        "public_reference_tags",
        "expected_failure_modes",
        "pit_controls",
    ]:
        payload[key] = tuple(payload.get(key, ()))
    return ProfitabilityEventRevisionCandidateSpec(**payload)


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        coverage = candidate.get("coverage", {})
        endpoint = candidate.get("endpoint_availability", {})
        rows.append(
            {
                "factor_name": candidate.get("factor_name"),
                "family": candidate.get("family"),
                "registration_status": candidate.get("registration_status"),
                "row_coverage": coverage.get("row_coverage"),
                "eligible_rows": coverage.get("eligible_rows"),
                "total_rows": coverage.get("total_rows"),
                "eligible_assets": coverage.get("eligible_assets"),
                "required_financial_columns": ",".join(candidate.get("required_financial_columns", []) or []),
                "required_endpoints": ",".join(candidate.get("required_endpoints", []) or []),
                "endpoint_blockers": ",".join(endpoint.get("blockers", []) or []),
                "coverage_blockers": ",".join(coverage.get("blockers", []) or []),
                "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed"),
                "promotion_allowed": candidate.get("promotion_allowed"),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _dedupe(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
