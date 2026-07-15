from __future__ import annotations

from datetime import date
import hashlib
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
from quant_robot.factors.etf_liquidity_capacity import compute_etf_adv20
from quant_robot.factors.etf_market_residual_volatility import (
    ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
    compute_etf_market_residual_volatility_factors,
    compute_etf_market_residual_volatility_references,
)
from quant_robot.research.cross_sectional_capacity import summarize_top_quantile_capacity
from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_market_residual_volatility_prescreen"
DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_wide_history_2023_2026")
DEFAULT_LEGACY_PROMOTION_REPORT = Path(
    "data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json"
)
DEFAULT_ANALYSIS_START_DATE = "2020-01-02"
DEFAULT_ANALYSIS_END_DATE = "2024-06-28"
DEFAULT_HORIZONS = (5, 20)
SAFETY = "Research-to-paper only. No broker connection, account reads, order placement, or live trading."


def build_historical_volatility_regime_review() -> dict[str, Any]:
    return {
        "family_id": "cn_etf_volatility_regime",
        "review_status": "only_market_residual_volatility_asymmetry_subspace_remains",
        "closed_factor_names": [
            "volatility_5",
            "volatility_10",
            "volatility_20",
            "volatility_60",
            "volatility_120",
            "low_volatility_20",
            "low_volatility_60",
            "low_downside_volatility_60",
            "drawdown_resilience_60",
            "defensive_reversal_60",
            "trend_resilience_60",
            "risk_confirmed_momentum_60",
            "crash_recovery_60",
            "recovery_quality_60",
            "state_adaptive_trend_defense_60",
            "state_stress_defensive_resilience_60",
            "state_stress_recovery_leadership_60",
            "formula_range_contraction_breakout_20",
            "formula_range_contraction_breakout_lowvol_20",
            "bollinger_reversal_20",
            "supertrend_volume_confirmed_10_3_20",
        ],
        "closed_subfamilies": [
            "raw_realized_volatility",
            "standalone_low_volatility",
            "raw_downside_volatility",
            "drawdown_resilience",
            "defensive_blends",
            "crash_recovery",
            "state_adaptive_defense",
            "hard_positive_momentum_regime_filter",
            "range_and_volatility_compression",
            "public_volatility_normalized_indicators",
        ],
        "remaining_candidate_names": list(ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES),
        "remaining_candidate_count": len(ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES),
        "last_chance_batch": True,
        "parameter_rescue_allowed": False,
        "window_tuning_allowed": False,
        "threshold_relaxation_allowed": False,
        "sign_flip_rescue_allowed": False,
        "regime_rescue_allowed": False,
        "portfolio_grid_before_prescreen_lead_allowed": False,
        "source_reports": [
            "docs/research/highspec_desktop_cn_etf_rotation_seed_2026-06-17.md",
            "docs/research/cn_etf_liquid_defensive_lowvol_liquidity_round37_2026-06-21.md",
            "docs/research/cn_etf_rounds37_39_audit_2026-06-21.md",
            "docs/research/cn_etf_rounds40_42_audit_2026-06-21.md",
            "docs/research/cn_etf_cn_stock_rounds44_46_audit_2026-06-21.md",
            "docs/research/cn_etf_volatility_regime_duplicate_stop_loss_audit_2026-07-16.md",
        ],
    }


def build_cn_etf_market_residual_volatility_prescreen(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    metadata_root: str | Path | None = None,
    legacy_promotion_report: str | Path = DEFAULT_LEGACY_PROMOTION_REPORT,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    eligibility_policy: EtfEligibilityPolicy = EtfEligibilityPolicy(),
    market_proxy_min_cross_section: int = 30,
    beta_window: int = 120,
    beta_min_observations: int = 80,
    downside_beta_window: int = 120,
    downside_beta_min_observations: int = 24,
    residual_window: int = 60,
    residual_min_observations: int = 40,
    residual_model_lag: int = 1,
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
    portfolio_value_cny: float = 1_000_000.0,
    position_count: int = 10,
    max_one_way_participation_rate: float = 0.01,
) -> dict[str, Any]:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if end >= pd.Timestamp("2026-01-01"):
        raise ValueError("CN ETF residual-volatility prescreen cannot read the sealed 2026 final holdout")
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if not horizons or any(int(horizon) < 1 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    root = Path(data_root)
    bars = load_processed_bars(root, "CN_ETF", end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"])
    source_window = _frame_window(bars)
    if bars.empty:
        raise ValueError("No CN_ETF bars are available on or before analysis_end_date")
    official_root = Path(metadata_root) if metadata_root is not None else root / "metadata" / "tushare_fund_basic"
    lifecycle = load_official_etf_lifecycle(official_root)
    eligibility = build_point_in_time_etf_eligibility(bars, lifecycle, policy=eligibility_policy)
    eligible = eligibility[
        eligibility["eligible"]
        & eligibility["date"].ge(start)
        & eligibility["date"].le(end)
    ].copy()
    eligible_keys = eligible[["date", "asset_id", "market"]].drop_duplicates()

    factors = compute_etf_market_residual_volatility_factors(
        bars,
        eligible_keys=eligible_keys,
        market_proxy_min_cross_section=market_proxy_min_cross_section,
        beta_window=beta_window,
        beta_min_observations=beta_min_observations,
        downside_beta_window=downside_beta_window,
        downside_beta_min_observations=downside_beta_min_observations,
        residual_window=residual_window,
        residual_min_observations=residual_min_observations,
        residual_model_lag=residual_model_lag,
    )
    references = compute_etf_market_residual_volatility_references(
        bars,
        eligible_keys=eligible_keys,
    )
    adv20 = compute_etf_adv20(bars, eligible_keys=eligible_keys)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(int(value) for value in horizons),
        execution_lag=int(execution_lag),
    )
    labels["date"] = pd.to_datetime(labels["date"])
    labels = labels[labels["date"].ge(start) & labels["date"].le(end)].reset_index(drop=True)

    result = summarize_cn_etf_market_residual_volatility_prescreen(
        factors,
        labels,
        references,
        adv20,
        expected_candidate_names=ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
        expected_reference_names=ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
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
        portfolio_value_cny=portfolio_value_cny,
        position_count=position_count,
        max_one_way_participation_rate=max_one_way_participation_rate,
    )
    result["data_window"] = {
        "source": source_window,
        "analysis_start_date": start.date().isoformat(),
        "analysis_end_date": end.date().isoformat(),
        "history_rows": int(len(bars)),
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
    result["market_proxy_policy"] = {
        "method": "point_in_time_eligible_cross_sectional_median_return",
        "min_cross_section": int(market_proxy_min_cross_section),
    }
    result["candidate_parameters"] = {
        "beta_window": int(beta_window),
        "beta_min_observations": int(beta_min_observations),
        "downside_beta_window": int(downside_beta_window),
        "downside_beta_min_observations": int(downside_beta_min_observations),
        "residual_window": int(residual_window),
        "residual_min_observations": int(residual_min_observations),
        "residual_model_lag": int(residual_model_lag),
        "include_intercept": True,
    }
    result["holdout_policy"] = {
        "final_holdout_start": "2026-01-01",
        "final_holdout_included": False,
        "final_holdout_access_allowed": False,
        "later_year_partitions_skipped_before_read": True,
    }
    result["source_paths"] = {
        "data_root": str(root),
        "metadata_root": str(official_root),
        "legacy_promotion_report": str(Path(legacy_promotion_report)),
    }
    result["legacy_promotion_quarantine"] = load_legacy_volatility_quarantine(
        legacy_promotion_report
    )
    result["markdown"] = render_cn_etf_market_residual_volatility_prescreen_markdown(result)
    return result


def load_legacy_volatility_quarantine(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"Legacy CN ETF promotion report does not exist: {report_path}")
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid legacy CN ETF promotion report JSON: {report_path}") from exc
    summary = payload.get("summary") if isinstance(payload, dict) else None
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(summary, dict) or not isinstance(candidates, list):
        raise ValueError("Legacy CN ETF promotion report must contain summary and candidates")
    observed = {
        "candidates": int(summary.get("candidates", -1)),
        "blocked": int(summary.get("blocked", -1)),
        "paper_ready": int(summary.get("paper_ready", -1)),
    }
    if observed != {"candidates": 270, "blocked": 270, "paper_ready": 0}:
        raise ValueError("Legacy promotion quarantine must show 270 candidates, 270 blocked, and zero paper-ready")
    volatility_rows = [
        row
        for row in candidates
        if isinstance(row, dict) and str(row.get("factor_name", "")).startswith("volatility_")
    ]
    if len(volatility_rows) != 45:
        raise ValueError("Legacy promotion quarantine must contain exactly 45 raw-volatility rows")
    if any(row.get("promotion_status") != "blocked" for row in volatility_rows):
        raise ValueError("All legacy raw-volatility rows must be blocked")
    return {
        "path": str(report_path),
        "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "status": "quarantined_by_current_strict_gate",
        "summary": observed,
        "volatility_rows": len(volatility_rows),
        "blocked_volatility_rows": len(volatility_rows),
        "legacy_candidate_reuse_allowed": False,
    }


def summarize_cn_etf_market_residual_volatility_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    adv20: pd.DataFrame,
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
    portfolio_value_cny: float = 1_000_000.0,
    position_count: int = 10,
    max_one_way_participation_rate: float = 0.01,
) -> dict[str, Any]:
    thresholds = CrossSectionalPrescreenThresholds(
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
    core = summarize_cross_sectional_factor_prescreen(
        factors,
        labels,
        references,
        candidate_names=expected_candidate_names,
        reference_names=expected_reference_names,
        horizons=horizons,
        thresholds=thresholds,
    )
    capacity_rows = summarize_top_quantile_capacity(
        factors,
        labels,
        adv20,
        candidate_names=tuple(core["candidate_names"]),
        horizons=horizons,
        min_cross_section=min_cross_section,
        portfolio_value_cny=portfolio_value_cny,
        position_count=position_count,
        max_one_way_participation_rate=max_one_way_participation_rate,
    )
    capacity_by_key = {
        (str(row["factor_name"]), int(row["horizon"])): row for row in capacity_rows
    }
    for row in core["results"]:
        row.update(capacity_by_key[(str(row["factor_name"]), int(row["horizon"]))])
        capacity_blockers = []
        if int(row["top_quantile_asset_observations"]) == 0 or int(
            row["top_quantile_adv20_observations"]
        ) == 0:
            capacity_blockers.append("top_quantile_capacity_evidence_missing")
        elif float(row["top_quantile_adv20_coverage_rate"]) < 1.0:
            capacity_blockers.append("top_quantile_capacity_evidence_incomplete")
        participation = row["p10_one_way_participation_rate"]
        if participation is not None and float(participation) > max_one_way_participation_rate:
            capacity_blockers.append("top_quantile_capacity_below_threshold")
        row["blockers"] = [
            *row["blockers"],
            *capacity_blockers,
            "promotion_requires_fresh_data_walk_forward_cost_capacity_regime_gates",
        ]
        row["research_lead"] = bool(row["research_lead"] and not capacity_blockers)
        row["promotion_allowed"] = False

    core["results"] = sorted(
        core["results"],
        key=lambda row: (not row["research_lead"], -float(row["mean_rank_ic"])),
    )
    lead_rows = [row for row in core["results"] if row["research_lead"]]
    lead_names = sorted({str(row["factor_name"]) for row in lead_rows})
    core["summary"]["research_lead_count"] = len(lead_rows)
    core["summary"]["research_lead_factor_count"] = len(lead_names)
    core["summary"]["capacity_row_count"] = len(capacity_rows)
    status = "research_leads_found" if lead_rows else "rejected"
    next_action = (
        "backfill_2024h2_2025_then_freeze_walk_forward"
        if lead_rows
        else "stop_loss_volatility_regime_and_activate_peer_relative_value"
    )
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": core["summary"],
        "historical_stop_loss_review": build_historical_volatility_regime_review(),
        "candidate_names": core["candidate_names"],
        "reference_names": core["reference_names"],
        "thresholds": {
            **core["thresholds"],
            "portfolio_value_cny": portfolio_value_cny,
            "position_count": position_count,
            "max_one_way_participation_rate": max_one_way_participation_rate,
            "min_top_quantile_adv20_p10_cny": portfolio_value_cny
            / position_count
            / max_one_way_participation_rate,
            "required_top_quantile_adv20_coverage_rate": 1.0,
        },
        "capacity_policy": {
            "amount_unit": "CNY",
            "adv_window": 20,
            "portfolio_value_cny": portfolio_value_cny,
            "position_count": position_count,
            "position_notional_cny": portfolio_value_cny / position_count,
            "max_one_way_participation_rate": max_one_way_participation_rate,
            "percentile": 0.10,
            "missing_evidence_policy": "fail_closed",
        },
        "multiple_testing_policy": core["multiple_testing_policy"],
        "results": core["results"],
        "ic_observations": core["ic_observations"],
        "yearly_ic": core["yearly_ic"],
        "reference_correlations": core["reference_correlations"],
        "capacity_rows": capacity_rows,
        "decision": {
            "research_lead_count": len(lead_rows),
            "research_lead_names": lead_names,
            "walk_forward_preflight_candidate_count": len(lead_names),
            "walk_forward_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "last_chance_batch": True,
            "next_action": next_action,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }


def write_cn_etf_market_residual_volatility_prescreen(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_market_residual_volatility_prescreen.json",
        "markdown": output / "cn_etf_market_residual_volatility_prescreen.md",
        "results": output / "cn_etf_market_residual_volatility_prescreen_results.csv",
        "ic_observations": output / "cn_etf_market_residual_volatility_ic_observations.csv",
        "yearly_ic": output / "cn_etf_market_residual_volatility_yearly_ic.csv",
        "reference_correlations": output
        / "cn_etf_market_residual_volatility_reference_correlations.csv",
        "capacity": output / "cn_etf_market_residual_volatility_capacity.csv",
    }
    paths["json"].write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True), encoding="utf-8"
    )
    paths["markdown"].write_text(
        render_cn_etf_market_residual_volatility_prescreen_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("results", [])).to_csv(paths["results"], index=False)
    pd.DataFrame(result.get("ic_observations", [])).to_csv(paths["ic_observations"], index=False)
    pd.DataFrame(result.get("yearly_ic", [])).to_csv(paths["yearly_ic"], index=False)
    pd.DataFrame(result.get("reference_correlations", [])).to_csv(
        paths["reference_correlations"], index=False
    )
    pd.DataFrame(result.get("capacity_rows", [])).to_csv(paths["capacity"], index=False)
    return paths


def render_cn_etf_market_residual_volatility_prescreen_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    data_window = result.get("data_window", {})
    legacy = result.get("legacy_promotion_quarantine", {})
    lines = [
        "# CN ETF Market-Residual Volatility Prescreen",
        "",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Candidates / tests / references: {summary.get('candidate_count', 0)} / {summary.get('test_count', 0)} / {summary.get('reference_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Analysis window: {data_window.get('analysis_start_date', 'n/a')} to {data_window.get('analysis_end_date', 'n/a')}",
        f"- Eligible assets / dates: {data_window.get('eligible_assets', 0)} / {data_window.get('eligible_dates', 0)}",
        f"- Legacy raw-volatility rows quarantined: {legacy.get('volatility_rows', 0)}",
        f"- Next action: {decision.get('next_action', 'n/a')}",
        "- Final 2026 holdout included: no",
        "- Live boundary allowed: no",
        "",
        "## Results",
        "",
        "| Factor | H | Mean IC | ICIR | FDR q | IC>0 | Q5-Q1 | Mono | Turnover | Years+ | Max ref corr | ADV20 P10 | Participation | Lead |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {fdr:.4f} | {positive:.1%} | {spread:.5f} | {mono:.2f} | {turnover:.1%} | {years:.1%} | {corr:.4f} | {adv20} | {participation} | {lead} |".format(
                factor=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                fdr=float(row.get("fdr_adjusted_p_value", 1.0)),
                positive=float(row.get("positive_ic_rate", 0.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                mono=float(row.get("quantile_monotonicity", 0.0)),
                turnover=float(row.get("avg_top_quantile_turnover", 0.0)),
                years=float(row.get("positive_year_rate", 0.0)),
                corr=float(row.get("max_abs_reference_correlation", 0.0)),
                adv20=_format_optional_number(row.get("top_quantile_adv20_p10_cny"), decimals=0),
                participation=_format_optional_percent(row.get("p10_one_way_participation_rate")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is the final allowed batch for the volatility-regime family.",
            "- Zero leads require immediate family stop-loss and scheduler rotation.",
            "- A lead cannot authorize walk-forward until the 2024-H2 through 2025 gap is backfilled and audited.",
            "- No portfolio grid, promotion, paper signal, broker access, account read, order placement, or live trading is authorized.",
        ]
    )
    return "\n".join(lines) + "\n"


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


def _format_optional_number(value: Any, *, decimals: int) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    return f"{float(value):.{decimals}f}"


def _format_optional_percent(value: Any) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    return f"{float(value):.2%}"


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
