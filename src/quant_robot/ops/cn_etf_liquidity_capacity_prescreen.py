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
from quant_robot.factors.etf_liquidity_capacity import (
    ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
    ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
    compute_etf_adv20,
    compute_etf_liquidity_capacity_factors,
    compute_etf_liquidity_reference_factors,
)
from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_liquidity_capacity_prescreen"
DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_wide_history_2023_2026")
DEFAULT_LEGACY_PROMOTION_REPORT = Path(
    "data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json"
)
DEFAULT_ANALYSIS_START_DATE = "2020-01-02"
DEFAULT_ANALYSIS_END_DATE = "2024-06-28"
DEFAULT_HORIZONS = (5, 20)
SAFETY = "Research-to-paper only. No broker connection, account reads, order placement, or live trading."


def build_historical_liquidity_capacity_review() -> dict[str, Any]:
    return {
        "family_id": "cn_etf_liquidity_capacity",
        "review_status": "only_liquidity_change_persistence_and_distribution_subspace_remains",
        "closed_factor_names": [
            "liquidity_5",
            "liquidity_10",
            "liquidity_20",
            "liquidity_60",
            "liquidity_120",
            "high_liquidity_20",
            "high_liquidity_60",
            "liquidity_resilience_60",
            "amount_stability_20",
            "amount_stability_60",
            "average_amount_20",
            "average_amount_60",
            "volume_change_20",
            "volume_change_60",
            "demand_pressure_60",
            "quiet_accumulation_60",
        ],
        "closed_subfamilies": [
            "liquidity_level",
            "amount_level",
            "amount_acceleration",
            "amount_stability",
            "liquidity_gated_price_rotation",
            "trend_volume_capacity_repair",
        ],
        "legacy_candidate_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
        "legacy_gate_status": "superseded_by_current_strict_gate",
        "current_strict_gate_expected_candidate_count": 270,
        "current_strict_gate_expected_blocked": 270,
        "current_strict_gate_expected_paper_ready": 0,
        "legacy_candidate_reuse_allowed": False,
        "parameter_rescue_allowed": False,
        "window_tuning_allowed": False,
        "threshold_relaxation_allowed": False,
        "portfolio_grid_before_prescreen_lead_allowed": False,
        "source_reports": [
            "docs/research/highspec_desktop_cn_etf_rotation_seed_2026-06-17.md",
            "docs/research/cn_etf_liquid_defensive_lowvol_liquidity_round37_2026-06-21.md",
            "docs/research/cn_etf_public_trend_volume_capacity_strict_round45_2026-06-21.md",
        ],
    }


def build_cn_etf_liquidity_capacity_prescreen(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    metadata_root: str | Path | None = None,
    legacy_promotion_report: str | Path = DEFAULT_LEGACY_PROMOTION_REPORT,
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
    portfolio_value_cny: float = 1_000_000.0,
    position_count: int = 10,
    max_one_way_participation_rate: float = 0.01,
) -> dict[str, Any]:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if end >= pd.Timestamp("2026-01-01"):
        raise ValueError("CN ETF liquidity-capacity prescreen cannot read the sealed 2026 final holdout")
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    if not horizons or any(int(horizon) < 1 for horizon in horizons):
        raise ValueError("horizons must contain positive integers")

    root = Path(data_root)
    bars = load_processed_bars(root, "CN_ETF").copy()
    bars["date"] = pd.to_datetime(bars["date"])
    source_window = _frame_window(bars)
    history = bars[bars["date"].le(end)].copy()
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

    factors = compute_etf_liquidity_capacity_factors(history, eligible_keys=eligible_keys)
    references = compute_etf_liquidity_reference_factors(history, eligible_keys=eligible_keys)
    adv20 = compute_etf_adv20(history, eligible_keys=eligible_keys)
    labels = make_forward_returns(
        history[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(int(value) for value in horizons),
        execution_lag=int(execution_lag),
    )
    labels["date"] = pd.to_datetime(labels["date"])
    labels = labels[labels["date"].ge(start) & labels["date"].le(end)].reset_index(drop=True)

    result = summarize_cn_etf_liquidity_capacity_prescreen(
        factors,
        labels,
        references,
        adv20,
        expected_candidate_names=ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
        expected_reference_names=ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
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
        "legacy_promotion_report": str(Path(legacy_promotion_report)),
    }
    result["legacy_promotion_quarantine"] = load_legacy_promotion_quarantine(legacy_promotion_report)
    result["markdown"] = render_cn_etf_liquidity_capacity_prescreen_markdown(result)
    return result


def load_legacy_promotion_quarantine(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        raise FileNotFoundError(f"Legacy CN ETF promotion report does not exist: {report_path}")
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid legacy CN ETF promotion report JSON: {report_path}") from exc
    summary = payload.get("summary") if isinstance(payload, dict) else None
    if not isinstance(summary, dict):
        raise ValueError("Legacy CN ETF promotion report is missing a summary object")
    observed = {
        "candidates": int(summary.get("candidates", -1)),
        "blocked": int(summary.get("blocked", -1)),
        "paper_ready": int(summary.get("paper_ready", -1)),
        "research_only": int(summary.get("research_only", -1)),
    }
    expected = {"candidates": 270, "blocked": 270, "paper_ready": 0}
    if any(observed[key] != value for key, value in expected.items()):
        raise ValueError(
            "Legacy CN ETF promotion quarantine must show 270 candidates, 270 blocked, and zero paper-ready"
        )
    return {
        "path": str(report_path),
        "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "status": "quarantined_by_current_strict_gate",
        "legacy_candidate_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
        "legacy_candidate_reuse_allowed": False,
        "summary": observed,
    }


def summarize_cn_etf_liquidity_capacity_prescreen(
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
    if portfolio_value_cny <= 0.0:
        raise ValueError("portfolio_value_cny must be positive")
    if position_count < 1:
        raise ValueError("position_count must be positive")
    if not 0.0 < max_one_way_participation_rate <= 1.0:
        raise ValueError("max_one_way_participation_rate must be in (0, 1]")
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
    capacity_rows = _capacity_rows(
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
        (str(row["factor_name"]), int(row["horizon"])): row
        for row in capacity_rows
    }
    for row in core["results"]:
        capacity = capacity_by_key[(str(row["factor_name"]), int(row["horizon"]))]
        row.update(capacity)
        capacity_blockers = []
        if int(row["top_quantile_asset_observations"]) == 0 or int(row["top_quantile_adv20_observations"]) == 0:
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
        else "stop_loss_liquidity_capacity_and_rotate_scheduler"
    )
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": core["summary"],
        "historical_stop_loss_review": build_historical_liquidity_capacity_review(),
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
            "next_action": next_action,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }


def write_cn_etf_liquidity_capacity_prescreen(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_liquidity_capacity_prescreen.json",
        "markdown": output / "cn_etf_liquidity_capacity_prescreen.md",
        "results": output / "cn_etf_liquidity_capacity_prescreen_results.csv",
        "ic_observations": output / "cn_etf_liquidity_capacity_ic_observations.csv",
        "yearly_ic": output / "cn_etf_liquidity_capacity_yearly_ic.csv",
        "reference_correlations": output / "cn_etf_liquidity_capacity_reference_correlations.csv",
        "capacity": output / "cn_etf_liquidity_capacity_capacity.csv",
    }
    paths["json"].write_text(json.dumps(_sanitize(result), indent=2, sort_keys=True), encoding="utf-8")
    paths["markdown"].write_text(
        render_cn_etf_liquidity_capacity_prescreen_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("results", [])).to_csv(paths["results"], index=False)
    pd.DataFrame(result.get("ic_observations", [])).to_csv(paths["ic_observations"], index=False)
    pd.DataFrame(result.get("yearly_ic", [])).to_csv(paths["yearly_ic"], index=False)
    pd.DataFrame(result.get("reference_correlations", [])).to_csv(paths["reference_correlations"], index=False)
    pd.DataFrame(result.get("capacity_rows", [])).to_csv(paths["capacity"], index=False)
    return paths


def render_cn_etf_liquidity_capacity_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    data_window = result.get("data_window", {})
    legacy = result.get("legacy_promotion_quarantine", {}).get("summary", {})
    lines = [
        "# CN ETF Liquidity-Capacity Prescreen",
        "",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Candidates / tests / references: {summary.get('candidate_count', 0)} / {summary.get('test_count', 0)} / {summary.get('reference_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Analysis end: {data_window.get('analysis_end_date', 'not_attached')}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Legacy strict gate blocked / paper-ready: {legacy.get('blocked', 'not_attached')} / {legacy.get('paper_ready', 'not_attached')}",
        f"- Next action: {decision.get('next_action', 'unknown')}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | Rank IC | ICIR | FDR q | Q5-Q1 | Mono | Turnover | Years | Max ref corr | ADV20 P10 CNY | Participation | Capacity coverage | Lead |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {q:.4g} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {years} | {corr:.3f} | {adv20} | {participation} | {coverage:.1%} | {lead} |".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                q=float(row.get("fdr_adjusted_p_value", 1.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                mono=float(row.get("quantile_monotonicity", 0.0)),
                turnover=float(row.get("avg_top_quantile_turnover", 1.0)),
                years=int(row.get("usable_years", 0)),
                corr=float(row.get("max_abs_reference_correlation", 0.0)),
                adv20=_format_optional_number(row.get("top_quantile_adv20_p10_cny"), decimals=0),
                participation=_format_optional_percent(row.get("p10_one_way_participation_rate")),
                coverage=float(row.get("top_quantile_adv20_coverage_rate", 0.0)),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This packet cannot authorize walk-forward until the 2024-H2 through 2025 history gap is backfilled and audited.",
            "- It cannot authorize a portfolio grid, promotion, paper signal, broker access, account read, order placement, or live trading.",
        ]
    )
    return "\n".join(lines) + "\n"


def _capacity_rows(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    adv20: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    horizons: tuple[int, ...],
    min_cross_section: int,
    portfolio_value_cny: float,
    position_count: int,
    max_one_way_participation_rate: float,
) -> list[dict[str, Any]]:
    factor_frame = _normalise_factors(factors)
    label_frame = labels.copy()
    label_frame["date"] = pd.to_datetime(label_frame["date"])
    capacity_frame = _normalise_adv20(adv20)
    position_notional = portfolio_value_cny / position_count
    minimum_adv20 = position_notional / max_one_way_participation_rate
    rows = []
    for factor_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"].eq(factor_name)]
        for horizon in horizons:
            horizon_labels = label_frame[label_frame["horizon"].eq(int(horizon))]
            merged = candidate.merge(
                horizon_labels[["date", "asset_id", "market", "forward_return"]],
                on=["date", "asset_id", "market"],
                how="inner",
                validate="one_to_one",
            ).merge(
                capacity_frame,
                on=["date", "asset_id", "market"],
                how="left",
                validate="one_to_one",
            )
            top_asset_observations = 0
            top_adv20: list[float] = []
            for _, group in merged.groupby("date", sort=True):
                clean = group.dropna(subset=["factor_value", "forward_return"])
                if len(clean) < min_cross_section:
                    continue
                quantiles = _quintiles(clean["factor_value"])
                if quantiles is None:
                    continue
                top = clean.loc[quantiles.eq(4)]
                top_asset_observations += len(top)
                valid_adv20 = pd.to_numeric(top["adv20"], errors="coerce")
                valid_adv20 = valid_adv20[valid_adv20.gt(0.0) & valid_adv20.map(math.isfinite)]
                top_adv20.extend(float(value) for value in valid_adv20)
            series = pd.Series(top_adv20, dtype=float)
            p10 = float(series.quantile(0.10)) if not series.empty else None
            median = float(series.median()) if not series.empty else None
            coverage = len(series) / top_asset_observations if top_asset_observations else 0.0
            rows.append(
                {
                    "factor_name": factor_name,
                    "horizon": int(horizon),
                    "top_quantile_asset_observations": int(top_asset_observations),
                    "top_quantile_adv20_observations": int(len(series)),
                    "top_quantile_adv20_coverage_rate": float(coverage),
                    "top_quantile_adv20_median_cny": median,
                    "top_quantile_adv20_p10_cny": p10,
                    "position_notional_cny": float(position_notional),
                    "p10_one_way_participation_rate": float(position_notional / p10) if p10 else None,
                    "max_one_way_participation_rate": float(max_one_way_participation_rate),
                    "minimum_top_quantile_adv20_p10_cny": float(minimum_adv20),
                }
            )
    return rows


def _normalise_factors(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Factor frame is missing columns: " + ", ".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["factor_name"] = result["factor_name"].astype(str)
    result["factor_value"] = pd.to_numeric(result["factor_value"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market", "factor_name"]).any():
        raise ValueError("Factor frame contains duplicate factor rows")
    return result


def _normalise_adv20(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adv20"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("ADV20 frame is missing columns: " + ", ".join(missing))
    result = frame[required].copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["adv20"] = pd.to_numeric(result["adv20"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("ADV20 frame contains duplicate asset-date rows")
    return result


def _quintiles(values: pd.Series) -> pd.Series | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique() < 5:
        return None
    try:
        return pd.qcut(numeric.rank(method="first"), q=5, labels=False)
    except ValueError:
        return None


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
