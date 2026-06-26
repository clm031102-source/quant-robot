from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    FORMULA_COLUMNS,
    compute_financial_pit_post_announcement_drift_factor_frame,
    _split_candidates,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    SAFETY,
    _dedupe,
    _filter_date_window,
    _load_bars,
    _load_json,
)
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_residual_prescreen import (
    NEXT_DIRECTION_WITH_LEADS as EXPECTED_STARTUP_NEXT_DIRECTION,
)
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize


STAGE = "financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight"
NEXT_WALK_FORWARD_DIRECTION = "round225_financial_pit_post_announcement_gap_reversal_walk_forward_cost_capacity_regime_validation"
NEXT_ROTATE_DIRECTION = "round225_rotate_gap_reversal_after_reference_dedup_or_preflight_failure"
DEFAULT_COST_BPS_VALUES = (5.0, 10.0, 20.0)
DEFAULT_PORTFOLIO_VALUES = (100_000.0, 500_000.0, 1_000_000.0, 5_000_000.0)
DEFAULT_TOP_N_VALUES = (20, 50)
DEFAULT_HOLDING_PERIODS = (5,)
DEFAULT_REBALANCE_INTERVALS = (1, 5)
DEFAULT_EXECUTION_LAG = 1
DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD = 0.95
DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD = 0.90
DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD = 0.70
DEFAULT_MIN_IC_T_STAT = 2.0
DEFAULT_MIN_PAIR_OBSERVATIONS = 8
DEFAULT_MIN_CORR_CROSS_SECTION = 30
DEFAULT_REQUIRED_REGIME_CONTROLS = (
    "policy_liquidity_regime",
    "credit_cycle_proxy",
    "northbound_margin_turnover_temperature",
    "index_location_state",
)
DEFAULT_REQUIRED_METRIC_PACK = (
    "total_return",
    "annual_return",
    "sharpe",
    "max_drawdown",
    "win_rate",
    "capacity_usage",
)
CANDIDATE_COLUMNS = [
    "factor_name",
    "horizon",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "reference_max_abs_correlation",
    "reference_mean_abs_correlation",
    "reference_top_match",
    "candidate_max_abs_correlation",
    "cluster_representative",
    "factor_rows",
    "signal_dates",
    "min_factor_date",
    "max_factor_date",
    "preflight_status",
    "walk_forward_frozen",
    "blockers",
]
PAIR_COLUMNS = [
    "factor_name",
    "other_factor_name",
    "pair_observations",
    "mean_spearman_corr",
    "mean_abs_spearman_corr",
    "max_abs_spearman_corr",
    "median_cross_section",
    "sufficient_observations",
]
PLAN_COLUMNS = [
    "fold",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "purpose",
]


def build_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    residual_prescreen_json: str | Path,
    startup_gate_json: str | Path | None,
    portfolio_policy_json: str | Path | None,
    regime_policy_json: str | Path | None,
    candidate_plan_gate_json: str | Path | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    reference_high_corr_threshold: float = DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD,
    reference_mean_abs_corr_threshold: float = DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD,
    min_ic_t_stat: float = DEFAULT_MIN_IC_T_STAT,
) -> dict[str, Any]:
    residual_report = _load_json(residual_prescreen_json)
    financial = _filter_date_window(
        _load_fina_indicator_inputs(Path(financial_root)),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="signal_date",
    )
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial else []
    bars = _filter_date_window(
        _load_bars([Path(root) for root in bars_roots], assets),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="date",
    )
    preregistration = _load_json(preregistration_json)
    gate_packet = _load_json(candidate_plan_gate_json)
    active_candidates, _ = _split_candidates(preregistration, gate_packet)
    active_candidates = [candidate for candidate in active_candidates if candidate.get("factor_name") in FORMULA_COLUMNS]
    lead_names = {row["factor_name"] for row in _research_lead_rows(residual_report)}
    active_candidates = [candidate for candidate in active_candidates if str(candidate.get("factor_name", "")) in lead_names]
    factor_frame = compute_financial_pit_post_announcement_drift_factor_frame(financial, active_candidates, bars)
    result = summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
        residual_report=residual_report,
        factor_frame=factor_frame,
        startup_gate=_load_json(startup_gate_json),
        portfolio_policy=_load_json(portfolio_policy_json),
        regime_policy=_load_json(regime_policy_json),
        min_pair_observations=min_pair_observations,
        min_corr_cross_section=min_corr_cross_section,
        candidate_high_corr_threshold=candidate_high_corr_threshold,
        reference_high_corr_threshold=reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
        min_ic_t_stat=min_ic_t_stat,
    )
    result.update(
        {
            "financial_root": str(Path(financial_root)),
            "bars_roots": [str(Path(root)) for root in bars_roots],
            "preregistration_json": str(Path(preregistration_json)),
            "residual_prescreen_json": str(Path(residual_prescreen_json)),
            "startup_gate_json": str(Path(startup_gate_json)) if startup_gate_json else None,
            "portfolio_policy_json": str(Path(portfolio_policy_json)) if portfolio_policy_json else None,
            "regime_policy_json": str(Path(regime_policy_json)) if regime_policy_json else None,
            "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
            "data_window": _data_window(financial, bars, factor_frame),
            "holdout_policy": {
                "final_holdout_included": bool(include_final_holdout),
                "analysis_start_date": str(analysis_start_date),
                "analysis_end_date": str(analysis_end_date),
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_walk_forward_cost_capacity_regime_oos_clearance",
            },
        }
    )
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_markdown(result)
    return result


def summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
    *,
    residual_report: dict[str, Any],
    factor_frame: pd.DataFrame,
    startup_gate: dict[str, Any] | None,
    portfolio_policy: dict[str, Any] | None,
    regime_policy: dict[str, Any] | None,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    reference_high_corr_threshold: float = DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD,
    reference_mean_abs_corr_threshold: float = DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD,
    min_ic_t_stat: float = DEFAULT_MIN_IC_T_STAT,
) -> dict[str, Any]:
    lead_rows = _research_lead_rows(residual_report)
    lead_names = [row["factor_name"] for row in lead_rows]
    pair_correlations = build_candidate_pair_correlations(
        factor_frame,
        lead_names,
        min_corr_cross_section=min_corr_cross_section,
        min_pair_observations=min_pair_observations,
    )
    candidate_table = _candidate_table(
        lead_rows,
        factor_frame,
        pair_correlations,
        candidate_high_corr_threshold=candidate_high_corr_threshold,
        reference_high_corr_threshold=reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
        min_ic_t_stat=min_ic_t_stat,
    )
    frozen = [row for row in candidate_table if row["walk_forward_frozen"]]
    blockers = _top_level_blockers(
        residual_report=residual_report,
        lead_rows=lead_rows,
        pair_correlations=pair_correlations,
        frozen=frozen,
        startup_gate=startup_gate or {},
        portfolio_policy=portfolio_policy or {},
        regime_policy=regime_policy or {},
        min_pair_observations=min_pair_observations,
    )
    status = "cleared" if not blockers else "blocked"
    walk_forward_plan = _walk_forward_plan()
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "thresholds": {
            "candidate_high_corr_threshold": float(candidate_high_corr_threshold),
            "reference_high_corr_threshold": float(reference_high_corr_threshold),
            "reference_mean_abs_corr_threshold": float(reference_mean_abs_corr_threshold),
            "min_ic_t_stat": float(min_ic_t_stat),
            "min_pair_observations": int(min_pair_observations),
            "min_corr_cross_section": int(min_corr_cross_section),
        },
        "summary": {
            "residual_research_leads": int(len(lead_rows)),
            "candidate_pair_rows": int(len(pair_correlations)),
            "frozen_walk_forward_candidates": int(len(frozen)),
            "cluster_duplicate_candidates": int(sum(1 for row in candidate_table if row["preflight_status"] == "cluster_duplicate")),
            "blocked_candidates": int(sum(1 for row in candidate_table if row["preflight_status"] == "blocked")),
            "max_candidate_abs_correlation": _max_pair_abs_correlation(pair_correlations),
            "next_direction": NEXT_WALK_FORWARD_DIRECTION if status == "cleared" else NEXT_ROTATE_DIRECTION,
        },
        "decision": {
            "blockers": blockers,
            "walk_forward_preflight_cleared": status == "cleared",
        },
        "preflight_policy": {
            "walk_forward_preflight_cleared": status == "cleared",
            "next_direction": NEXT_WALK_FORWARD_DIRECTION if status == "cleared" else NEXT_ROTATE_DIRECTION,
            "frozen_factor_names": [row["factor_name"] for row in frozen],
            "scope": "freeze residual research leads after candidate-cluster dedup; no parameter expansion before walk-forward",
        },
        "portfolio_grid_policy": {
            "top_n_values": list(DEFAULT_TOP_N_VALUES),
            "holding_periods": list(DEFAULT_HOLDING_PERIODS),
            "rebalance_intervals": list(DEFAULT_REBALANCE_INTERVALS),
            "execution_lag": DEFAULT_EXECUTION_LAG,
            "cost_bps_values": list(DEFAULT_COST_BPS_VALUES),
            "portfolio_values": list(DEFAULT_PORTFOLIO_VALUES),
            "market_impact_bps": 10.0,
            "max_participation_rate": _float(_dict(portfolio_policy).get("risk_budget", {}).get("max_position_adv_participation"), 0.01),
            "drawdown_soft_tolerance": _float(_dict(portfolio_policy).get("drawdown_controls", {}).get("max_drawdown_soft_tolerance"), 0.30),
            "hard_stop_drawdown_threshold": _float(_dict(portfolio_policy).get("drawdown_controls", {}).get("hard_stop_drawdown_threshold"), 0.45),
            "parameter_expansion_allowed": False,
        },
        "regime_validation_policy": {
            "required_controls": list(DEFAULT_REQUIRED_REGIME_CONTROLS),
            "standalone_regime_alpha_claim_allowed": False,
            "must_report_allowed_and_blocked_dates": True,
        },
        "walk_forward_plan": walk_forward_plan,
        "candidate_table": candidate_table,
        "frozen_candidates": frozen,
        "candidate_pair_correlations": pair_correlations,
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": [
                "walk_forward_not_run",
                "cost_capacity_stress_not_run",
                "regime_coverage_not_run",
                "final_holdout_not_read",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_markdown(result)
    return result


def build_candidate_pair_correlations(
    factor_frame: pd.DataFrame,
    factor_names: Sequence[str],
    *,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
) -> list[dict[str, Any]]:
    names = _dedupe([str(name) for name in factor_names if str(name)])
    if len(names) < 2:
        return []
    frame = _prepare_factor_frame(factor_frame)
    rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            observations: list[dict[str, float]] = []
            for _, group in frame[frame["factor_name"].isin({left, right})].groupby("date", sort=True):
                pivot = group.pivot_table(
                    index="asset_id",
                    columns="factor_name",
                    values="factor_value",
                    aggfunc="last",
                )
                if left not in pivot.columns or right not in pivot.columns:
                    continue
                paired = pivot[[left, right]].dropna()
                if len(paired) < int(min_corr_cross_section):
                    continue
                corr = paired[left].rank(method="average").corr(paired[right].rank(method="average"))
                if pd.isna(corr):
                    continue
                observations.append({"corr": float(corr), "cross_section": float(len(paired))})
            abs_corrs = [abs(item["corr"]) for item in observations]
            corr_values = [item["corr"] for item in observations]
            rows.append(
                {
                    "factor_name": left,
                    "other_factor_name": right,
                    "pair_observations": int(len(observations)),
                    "mean_spearman_corr": float(sum(corr_values) / len(corr_values)) if corr_values else 0.0,
                    "mean_abs_spearman_corr": float(sum(abs_corrs) / len(abs_corrs)) if abs_corrs else 0.0,
                    "max_abs_spearman_corr": float(max(abs_corrs)) if abs_corrs else 0.0,
                    "median_cross_section": float(pd.Series([item["cross_section"] for item in observations]).median()) if observations else 0.0,
                    "sufficient_observations": bool(len(observations) >= int(min_pair_observations)),
                }
            )
    return rows


def write_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in result.items() if key != "markdown"}
    (output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.json").write_text(
        json.dumps(_sanitize(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.md").write_text(
        render_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_candidates.csv",
        result.get("candidate_table", []) or [],
        CANDIDATE_COLUMNS,
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_candidate_pair_correlations.csv",
        result.get("candidate_pair_correlations", []) or [],
        PAIR_COLUMNS,
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_walk_forward_plan.csv",
        result.get("walk_forward_plan", []) or [],
        PLAN_COLUMNS,
    )


def render_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    decision = result.get("decision", {}) or {}
    policy = result.get("preflight_policy", {}) or {}
    lines = [
        "# Financial PIT Gap Reversal Walk-Forward Preflight",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Residual research leads: {summary.get('residual_research_leads', 0)}",
        f"- Frozen walk-forward candidates: {summary.get('frozen_walk_forward_candidates', 0)}",
        f"- Cluster duplicates: {summary.get('cluster_duplicate_candidates', 0)}",
        f"- Max candidate abs corr: {float(summary.get('max_candidate_abs_correlation', 0.0)):.3f}",
        f"- Walk-forward preflight cleared: {policy.get('walk_forward_preflight_cleared', False)}",
        f"- Next direction: `{policy.get('next_direction', NEXT_ROTATE_DIRECTION)}`",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Freeze Table",
        "",
        "| Factor | IC | t | RefCorr | CandCorr | Status | Representative | Blockers |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for row in result.get("candidate_table", []) or []:
        lines.append(
            "| {factor} | {ic:.4f} | {t:.2f} | {ref:.3f} | {cand:.3f} | {status} | {rep} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                ic=_float(row.get("mean_spearman_ic")),
                t=_float(row.get("ic_t_stat")),
                ref=_float(row.get("reference_max_abs_correlation")),
                cand=_float(row.get("candidate_max_abs_correlation")),
                status=row.get("preflight_status", ""),
                rep=row.get("cluster_representative", ""),
                blockers=row.get("blockers", "") or "none",
            )
        )
    lines.extend(["", "## Walk-Forward Plan", ""])
    for fold in result.get("walk_forward_plan", []) or []:
        lines.append(
            "- {fold}: train {train_start} to {train_end}, test {test_start} to {test_end} ({purpose})".format(
                **fold
            )
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    blockers = decision.get("blockers", []) or []
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This gate freezes research leads for walk-forward validation only.",
            "- Highly correlated candidate variants are counted as one cluster representative, not multiple discoveries.",
            "- Portfolio Sharpe, profit rate, win rate, drawdown, and promotion remain unavailable until walk-forward, cost/capacity, regime, and final-holdout gates pass.",
        ]
    )
    return "\n".join(lines) + "\n"


def _research_lead_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in report.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        if _bool(row.get("research_lead")):
            rows.append(_normalise_result_row(row))
    return sorted(
        rows,
        key=lambda row: (
            -_float(row.get("mean_spearman_ic")),
            -_float(row.get("ic_t_stat")),
            -_float(row.get("quantile_monotonicity")),
            _float(row.get("reference_max_abs_correlation")),
            str(row.get("factor_name", "")),
        ),
    )


def _normalise_result_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "factor_name": str(row.get("factor_name", "")),
        "horizon": int(_float(row.get("horizon"), 0)),
        "mean_spearman_ic": _float(row.get("mean_spearman_ic")),
        "icir": _float(row.get("icir")),
        "ic_t_stat": _float(row.get("ic_t_stat")),
        "fdr_significant": _bool(row.get("fdr_significant")),
        "ic_positive_rate": _float(row.get("ic_positive_rate")),
        "quantile_spread": _float(row.get("quantile_spread")),
        "quantile_monotonicity": _float(row.get("quantile_monotonicity")),
        "reference_max_abs_correlation": _float(row.get("reference_max_abs_correlation")),
        "reference_mean_abs_correlation": _float(row.get("reference_mean_abs_correlation")),
        "reference_top_match": str(row.get("reference_top_match", "")),
    }


def _candidate_table(
    lead_rows: list[dict[str, Any]],
    factor_frame: pd.DataFrame,
    pair_correlations: list[dict[str, Any]],
    *,
    candidate_high_corr_threshold: float,
    reference_high_corr_threshold: float,
    reference_mean_abs_corr_threshold: float,
    min_ic_t_stat: float,
) -> list[dict[str, Any]]:
    coverage = _factor_coverage(factor_frame)
    frozen_names: list[str] = []
    rows: list[dict[str, Any]] = []
    for row in lead_rows:
        factor_name = row["factor_name"]
        blockers = _candidate_blockers(
            row,
            coverage.get(factor_name, {}),
            reference_high_corr_threshold=reference_high_corr_threshold,
            reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
            min_ic_t_stat=min_ic_t_stat,
        )
        representative = ""
        max_corr = 0.0
        if not blockers:
            representative, max_corr = _closest_frozen_candidate(factor_name, frozen_names, pair_correlations)
            if representative and max_corr > float(candidate_high_corr_threshold):
                blockers.append("candidate_cluster_high_corr_duplicate")
        status = "blocked" if blockers else "frozen_walk_forward_candidate"
        walk_forward_frozen = status == "frozen_walk_forward_candidate"
        if not blockers and walk_forward_frozen:
            frozen_names.append(factor_name)
            representative = factor_name
        elif "candidate_cluster_high_corr_duplicate" in blockers:
            status = "cluster_duplicate"
        factor_coverage = coverage.get(factor_name, {})
        rows.append(
            {
                **row,
                "candidate_max_abs_correlation": float(max_corr),
                "cluster_representative": representative,
                "factor_rows": int(factor_coverage.get("factor_rows", 0)),
                "signal_dates": int(factor_coverage.get("signal_dates", 0)),
                "min_factor_date": factor_coverage.get("min_factor_date"),
                "max_factor_date": factor_coverage.get("max_factor_date"),
                "preflight_status": status,
                "walk_forward_frozen": bool(walk_forward_frozen),
                "blockers": ",".join(_dedupe(blockers)),
            }
        )
    return rows


def _candidate_blockers(
    row: dict[str, Any],
    coverage: dict[str, Any],
    *,
    reference_high_corr_threshold: float,
    reference_mean_abs_corr_threshold: float,
    min_ic_t_stat: float,
) -> list[str]:
    blockers: list[str] = []
    if not row.get("fdr_significant"):
        blockers.append("not_fdr_significant")
    if _float(row.get("mean_spearman_ic")) <= 0.0:
        blockers.append("non_positive_mean_ic")
    if _float(row.get("ic_t_stat")) < float(min_ic_t_stat):
        blockers.append("ic_t_stat_below_min")
    if _float(row.get("reference_max_abs_correlation")) > float(reference_high_corr_threshold):
        blockers.append("reference_max_abs_corr_too_high")
    if _float(row.get("reference_mean_abs_correlation")) > float(reference_mean_abs_corr_threshold):
        blockers.append("reference_mean_abs_corr_too_high")
    if int(coverage.get("factor_rows", 0)) <= 0:
        blockers.append("missing_factor_rows")
    return blockers


def _top_level_blockers(
    *,
    residual_report: dict[str, Any],
    lead_rows: list[dict[str, Any]],
    pair_correlations: list[dict[str, Any]],
    frozen: list[dict[str, Any]],
    startup_gate: dict[str, Any],
    portfolio_policy: dict[str, Any],
    regime_policy: dict[str, Any],
    min_pair_observations: int,
) -> list[str]:
    blockers: list[str] = []
    if not lead_rows:
        blockers.append("residual_report_has_no_research_leads")
    if _dict(residual_report.get("summary")).get("next_direction") != EXPECTED_STARTUP_NEXT_DIRECTION:
        blockers.append("residual_report_next_direction_mismatch")
    if _dict(residual_report.get("holdout_policy")).get("final_holdout_included") is True:
        blockers.append("residual_report_includes_final_holdout")
    if len(lead_rows) > 1:
        sufficient_pairs = [row for row in pair_correlations if row.get("sufficient_observations")]
        if not sufficient_pairs:
            blockers.append("candidate_pair_correlations_unavailable")
        elif any(int(row.get("pair_observations", 0)) < int(min_pair_observations) for row in pair_correlations):
            blockers.append("some_candidate_pair_correlations_insufficient")
    if not frozen:
        blockers.append("all_candidates_removed_by_dedup_or_candidate_blocks")
    blockers.extend(_startup_gate_blockers(startup_gate))
    blockers.extend(_portfolio_policy_blockers(portfolio_policy))
    blockers.extend(_regime_policy_blockers(regime_policy))
    return _dedupe(blockers)


def _startup_gate_blockers(startup_gate: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not startup_gate:
        return ["startup_gate_missing"]
    if startup_gate.get("status") != "cleared" or _dict(startup_gate.get("decision")).get("startup_gate_cleared") is not True:
        blockers.append("startup_gate_not_cleared")
    if _dict(startup_gate.get("repeatable_mining_protocol")).get("next_direction") != EXPECTED_STARTUP_NEXT_DIRECTION:
        blockers.append("startup_gate_next_direction_mismatch")
    if startup_gate.get("live_boundary_allowed") is not False:
        blockers.append("startup_gate_live_boundary_violation")
    return blockers


def _portfolio_policy_blockers(policy: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not policy:
        return ["portfolio_policy_missing"]
    if str(policy.get("market", "")).upper() != "CN":
        blockers.append("portfolio_policy_market_mismatch")
    if str(policy.get("asset_type", "")).lower() != "stock":
        blockers.append("portfolio_policy_asset_type_mismatch")
    if not isinstance(policy.get("risk_budget"), dict):
        blockers.append("portfolio_policy_missing_risk_budget")
    if not isinstance(policy.get("drawdown_controls"), dict):
        blockers.append("portfolio_policy_missing_drawdown_controls")
    metric_pack = set(_list(policy.get("required_metric_pack")))
    for metric in DEFAULT_REQUIRED_METRIC_PACK:
        if metric not in metric_pack:
            blockers.append(f"portfolio_policy_missing_metric:{metric}")
    return blockers


def _regime_policy_blockers(policy: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not policy:
        return ["regime_policy_missing"]
    if str(policy.get("market", "")).upper() != "CN":
        blockers.append("regime_policy_market_mismatch")
    if str(policy.get("asset_type", "")).lower() != "stock":
        blockers.append("regime_policy_asset_type_mismatch")
    controls = {
        str(item.get("control_id", ""))
        for item in policy.get("controls", []) or []
        if isinstance(item, dict)
    }
    for control in DEFAULT_REQUIRED_REGIME_CONTROLS:
        if control not in controls:
            blockers.append(f"regime_policy_missing_control:{control}")
    return blockers


def _closest_frozen_candidate(
    factor_name: str,
    frozen_names: list[str],
    pair_correlations: list[dict[str, Any]],
) -> tuple[str, float]:
    best_name = ""
    best_corr = 0.0
    for frozen in frozen_names:
        corr = _pair_abs_corr(factor_name, frozen, pair_correlations)
        if corr > best_corr:
            best_name = frozen
            best_corr = corr
    return best_name, float(best_corr)


def _pair_abs_corr(left: str, right: str, rows: list[dict[str, Any]]) -> float:
    for row in rows:
        names = {str(row.get("factor_name", "")), str(row.get("other_factor_name", ""))}
        if names == {left, right}:
            return _float(row.get("mean_abs_spearman_corr"))
    return 0.0


def _factor_coverage(factor_frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    frame = _prepare_factor_frame(factor_frame)
    coverage: dict[str, dict[str, Any]] = {}
    for factor_name, group in frame.groupby("factor_name", sort=True):
        dates = pd.to_datetime(group["date"], errors="coerce")
        coverage[str(factor_name)] = {
            "factor_rows": int(len(group)),
            "signal_dates": int(dates.nunique()),
            "min_factor_date": _date_min(group, "date"),
            "max_factor_date": _date_max(group, "date"),
        }
    return coverage


def _prepare_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "asset_id", "factor_name", "factor_value"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    output = frame[[column for column in ["date", "asset_id", "market", "factor_name", "factor_value"] if column in frame]].copy()
    if "market" not in output:
        output["market"] = "CN"
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output[(output["market"] == "CN") & output["date"].notna()].dropna(subset=["factor_value"]).reset_index(drop=True)


def _walk_forward_plan() -> list[dict[str, str]]:
    return [
        {
            "fold": "fold_1",
            "train_start": "2015-01-01",
            "train_end": "2018-12-31",
            "test_start": "2019-01-01",
            "test_end": "2020-12-31",
            "purpose": "early-cycle oos sanity",
        },
        {
            "fold": "fold_2",
            "train_start": "2015-01-01",
            "train_end": "2020-12-31",
            "test_start": "2021-01-01",
            "test_end": "2022-12-31",
            "purpose": "post-2020 regime shift",
        },
        {
            "fold": "fold_3",
            "train_start": "2015-01-01",
            "train_end": "2022-12-31",
            "test_start": "2023-01-01",
            "test_end": "2024-12-31",
            "purpose": "recent full-year oos",
        },
        {
            "fold": "fold_4",
            "train_start": "2015-01-01",
            "train_end": "2024-12-31",
            "test_start": "2025-01-01",
            "test_end": "2025-12-31",
            "purpose": "last in-sample oos before final holdout",
        },
    ]


def _data_window(financial: pd.DataFrame, bars: pd.DataFrame, factor_frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "financial_rows": int(len(financial)),
        "financial_assets": int(financial["asset_id"].nunique()) if "asset_id" in financial else 0,
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "factor_rows": int(len(factor_frame)),
        "factor_assets": int(factor_frame["asset_id"].nunique()) if "asset_id" in factor_frame else 0,
        "min_factor_date": _date_min(factor_frame, "date"),
        "max_factor_date": _date_max(factor_frame, "date"),
    }


def _max_pair_abs_correlation(rows: list[dict[str, Any]]) -> float:
    return max((_float(row.get("mean_abs_spearman_corr")) for row in rows), default=0.0)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return value


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else str(value.date())


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else str(value.date())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if pd.notna(number) else float(default)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)
