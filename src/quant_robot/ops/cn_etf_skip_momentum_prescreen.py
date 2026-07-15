from __future__ import annotations

from datetime import date
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
from quant_robot.factors.etf_skip_momentum import (
    ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    ETF_SKIP_MOMENTUM_FACTOR_NAMES,
    compute_etf_price_rotation_reference_factors,
    compute_etf_skip_momentum_factors,
)
from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_skip_momentum_prescreen"
DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_wide_history_2023_2026")
DEFAULT_ANALYSIS_START_DATE = "2020-01-02"
DEFAULT_ANALYSIS_END_DATE = "2024-06-28"
DEFAULT_HORIZONS = (5, 20)
SAFETY = "Research-to-paper only. No broker connection, account reads, order placement, or live trading."


def build_historical_price_rotation_stop_loss_review() -> dict[str, Any]:
    return {
        "family_id": "cn_etf_price_rotation",
        "review_status": "only_skip_momentum_subspace_remains",
        "closed_factor_names": [
            "momentum_20",
            "momentum_60",
            "risk_adjusted_momentum_20",
            "risk_adjusted_momentum_60",
            "market_relative_strength_60",
            "liquid_market_relative_strength_60",
            "theme_relative_strength_60",
            "theme_member_leadership_60",
        ],
        "closed_subfamilies": [
            "plain_momentum",
            "risk_adjusted_momentum",
            "relative_strength",
            "static_theme_relative_strength",
            "tail_guard_reversal",
            "defensive_reversal",
        ],
        "remaining_candidate_names": list(ETF_SKIP_MOMENTUM_FACTOR_NAMES),
        "parameter_rescue_allowed": False,
        "window_tuning_allowed": False,
        "threshold_relaxation_allowed": False,
        "portfolio_grid_before_prescreen_lead_allowed": False,
        "source_reports": [
            "docs/research/highspec_desktop_cn_etf_rotation_seed_2026-06-17.md",
            "docs/research/cn_etf_rounds27_29_audit_2026-06-21.md",
            "docs/research/cn_etf_rounds31_33_audit_2026-06-21.md",
        ],
    }


def build_cn_etf_skip_momentum_prescreen(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    metadata_root: str | Path | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    eligibility_policy: EtfEligibilityPolicy = EtfEligibilityPolicy(),
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
) -> dict[str, Any]:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if end >= pd.Timestamp("2026-01-01"):
        raise ValueError("CN ETF skip-momentum prescreen cannot read the sealed 2026 final holdout")
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if not horizons or any(int(horizon) < 1 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    root = Path(data_root)
    bars = load_processed_bars(root, "CN_ETF").copy()
    bars["date"] = pd.to_datetime(bars["date"])
    source_window = _frame_window(bars)
    history = bars[bars["date"] <= end].copy()
    if history.empty:
        raise ValueError("No CN_ETF bars are available on or before analysis_end_date")
    official_root = Path(metadata_root) if metadata_root is not None else root / "metadata" / "tushare_fund_basic"
    lifecycle = load_official_etf_lifecycle(official_root)
    eligibility = build_point_in_time_etf_eligibility(history, lifecycle, policy=eligibility_policy)
    eligible = eligibility[
        eligibility["eligible"]
        & eligibility["date"].ge(start)
        & eligibility["date"].le(end)
    ].copy()
    eligible_keys = eligible[["date", "asset_id", "market"]].drop_duplicates()

    factors = compute_etf_skip_momentum_factors(history, eligible_keys=eligible_keys)
    references = compute_etf_price_rotation_reference_factors(history, eligible_keys=eligible_keys)
    labels = make_forward_returns(
        history[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(int(value) for value in horizons),
        execution_lag=int(execution_lag),
    )
    labels["date"] = pd.to_datetime(labels["date"])
    labels = labels[labels["date"].ge(start) & labels["date"].le(end)].reset_index(drop=True)

    result = summarize_cn_etf_skip_momentum_prescreen(
        factors,
        labels,
        references,
        expected_candidate_names=ETF_SKIP_MOMENTUM_FACTOR_NAMES,
        expected_reference_names=ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
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
    )
    result["data_window"] = {
        "source": source_window,
        "analysis_start_date": start.date().isoformat(),
        "analysis_end_date": end.date().isoformat(),
        "history_rows": int(len(history)),
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
    result["holdout_policy"] = {
        "final_holdout_start": "2026-01-01",
        "final_holdout_included": False,
        "final_holdout_access_allowed": False,
    }
    result["source_paths"] = {
        "data_root": str(root),
        "metadata_root": str(official_root),
    }
    result["markdown"] = render_cn_etf_skip_momentum_prescreen_markdown(result)
    return result


def summarize_cn_etf_skip_momentum_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
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
) -> dict[str, Any]:
    core = summarize_cross_sectional_factor_prescreen(
        factors,
        labels,
        references,
        candidate_names=expected_candidate_names,
        reference_names=expected_reference_names,
        horizons=horizons,
        thresholds=CrossSectionalPrescreenThresholds(
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
        ),
    )
    for row in core["results"]:
        row["promotion_allowed"] = False
        row["blockers"] = [
            *row["blockers"],
            "promotion_requires_fresh_data_walk_forward_cost_capacity_regime_gates",
        ]

    lead_rows = [row for row in core["results"] if row["research_lead"]]
    lead_names = sorted({str(row["factor_name"]) for row in lead_rows})
    status = "research_leads_found" if lead_rows else "rejected"
    next_action = (
        "backfill_2024h2_2025_then_freeze_walk_forward"
        if lead_rows
        else "close_price_rotation_and_rotate_scheduler"
    )
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": core["summary"],
        "historical_stop_loss_review": build_historical_price_rotation_stop_loss_review(),
        "candidate_names": core["candidate_names"],
        "reference_names": core["reference_names"],
        "thresholds": core["thresholds"],
        "multiple_testing_policy": core["multiple_testing_policy"],
        "results": core["results"],
        "ic_observations": core["ic_observations"],
        "yearly_ic": core["yearly_ic"],
        "reference_correlations": core["reference_correlations"],
        "decision": {
            "research_lead_count": len(lead_rows),
            "research_lead_names": lead_names,
            "walk_forward_preflight_candidate_count": len(lead_names),
            "walk_forward_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "next_action": next_action,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_etf_skip_momentum_prescreen_markdown(result)
    return result


def write_cn_etf_skip_momentum_prescreen(output_dir: str | Path, result: dict[str, Any]) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_skip_momentum_prescreen.json",
        "markdown": output / "cn_etf_skip_momentum_prescreen.md",
        "results": output / "cn_etf_skip_momentum_prescreen_results.csv",
        "ic_observations": output / "cn_etf_skip_momentum_ic_observations.csv",
        "yearly_ic": output / "cn_etf_skip_momentum_yearly_ic.csv",
        "reference_correlations": output / "cn_etf_skip_momentum_reference_correlations.csv",
    }
    paths["json"].write_text(json.dumps(_sanitize(result), indent=2, sort_keys=True), encoding="utf-8")
    paths["markdown"].write_text(render_cn_etf_skip_momentum_prescreen_markdown(result), encoding="utf-8")
    pd.DataFrame(result.get("results", [])).to_csv(paths["results"], index=False)
    pd.DataFrame(result.get("ic_observations", [])).to_csv(paths["ic_observations"], index=False)
    pd.DataFrame(result.get("yearly_ic", [])).to_csv(paths["yearly_ic"], index=False)
    pd.DataFrame(result.get("reference_correlations", [])).to_csv(paths["reference_correlations"], index=False)
    return paths


def render_cn_etf_skip_momentum_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    data_window = result.get("data_window", {})
    lines = [
        "# CN ETF Skip-Momentum Prescreen",
        "",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Candidates / tests: {summary.get('candidate_count', 0)} / {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Analysis end: {data_window.get('analysis_end_date', 'not_attached')}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next action: {decision.get('next_action', 'unknown')}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | Rank IC | ICIR | NW t | FDR q | IC>0 | Q5-Q1 | Mono | Turnover | Years | Positive years | Max reference corr | Lead |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {q:.4g} | {positive:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {years} | {positive_years:.1%} | {corr:.3f} | {lead} |".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                t=float(row.get("ic_t_stat", 0.0)),
                q=float(row.get("fdr_adjusted_p_value", 1.0)),
                positive=float(row.get("positive_ic_rate", 0.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                mono=float(row.get("quantile_monotonicity", 0.0)),
                turnover=float(row.get("avg_top_quantile_turnover", 1.0)),
                years=int(row.get("usable_years", 0)),
                positive_years=float(row.get("positive_year_rate", 0.0)),
                corr=float(row.get("max_abs_reference_correlation", 0.0)),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This packet cannot authorize walk-forward until the 2024-H2 through 2025 history gap is backfilled and audited.",
            "- It cannot authorize a portfolio grid, promotion, paper signal, broker access, account read, or order placement.",
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
