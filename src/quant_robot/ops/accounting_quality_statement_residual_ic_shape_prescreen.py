from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.accounting_quality_statement_formula_smoke import FORMULA_SPECS, _read_frame
from quant_robot.ops.accounting_quality_statement_matrix_label_smoke import (
    SAFETY,
    compute_accounting_quality_statement_factor_frame,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
)
from quant_robot.ops.financial_pit_timing_audit import _dataset_files
from quant_robot.ops.profitability_event_revision_controlled_ic_neutral_prescreen import (
    NEUTRAL_OBSERVATION_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    RESULT_COLUMNS,
    _attach_market_context,
    _load_daily_basic_context,
    _load_stock_basic,
    _sanitize,
    _write_csv,
    summarize_profitability_event_revision_controlled_ic_neutral_prescreen,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "accounting_quality_statement_residual_ic_shape_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round239_accounting_quality_statement_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round239_expand_or_repair_accounting_quality_statement_after_residual_ic_shape_failure"
NEXT_DIRECTION_NEW_SUBSTRUCTURE_WITH_LEADS = "round245_accounting_quality_new_substructure_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_NEW_SUBSTRUCTURE_WITHOUT_LEADS = "round245_accounting_quality_new_substructure_directional_audit_or_family_rotation"
NEXT_DIRECTION_DIRECTIONAL_AUDIT_WITH_LEADS = "round246_accounting_quality_directional_audit_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_DIRECTIONAL_AUDIT_WITHOUT_LEADS = "round246_accounting_quality_rotate_to_event_drift_or_profitability_revision"
NEXT_DIRECTION_STATEMENT_EVENT_DRIFT_WITH_LEADS = "round247_accounting_quality_statement_event_drift_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_STATEMENT_EVENT_DRIFT_WITHOUT_LEADS = "round247_accounting_quality_rotate_to_profitability_revision_or_event_context"
NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITH_LEADS = "round248_accounting_quality_statement_profitability_revision_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITHOUT_LEADS = "round248_rotate_to_external_revision_or_nonfinancial_event_context"
NEXT_DIRECTION_INDUSTRY_RELATIVE_SURPRISE_WITH_LEADS = "round254_industry_relative_surprise_walk_forward_cost_capacity_regime_preflight"
NEXT_DIRECTION_INDUSTRY_RELATIVE_SURPRISE_WITHOUT_LEADS = "round254_rotate_after_industry_relative_surprise_residual_ic_shape_failure"
REPAIRED_FACTOR_NAMES = (
    "aq_repaired_industry_relative_cash_accrual_quality",
    "aq_repaired_size_liquidity_residual_asset_growth_quality",
    "aq_repaired_balanced_cash_asset_quality",
)
RAW_CASH_ACCRUAL_FACTOR_NAMES = (
    "low_total_accruals_to_assets_raw",
    "cashflow_minus_netprofit_to_assets_raw",
    "low_asset_growth_quality_raw",
    "working_capital_accruals_to_assets_raw",
    "earnings_cash_conversion_improvement_yoy_raw",
)
NEW_SUBSTRUCTURE_FACTOR_NAMES = (
    "aq_abnormal_accrual_change_reversal",
    "aq_balance_sheet_stress_relief",
)
DIRECTIONAL_AUDIT_SOURCE_FACTOR_NAME = "aq_abnormal_accrual_change_reversal"
DIRECTIONAL_AUDIT_FACTOR_NAME = "aq_abnormal_accrual_change_reversal_sign_flip_audit"
STATEMENT_EVENT_DRIFT_SOURCE_FACTOR_NAME = "earnings_cash_conversion_improvement_yoy_raw"
STATEMENT_EVENT_DRIFT_FACTOR_NAME = "aq_cash_conversion_muted_reaction_drift"
STATEMENT_PROFITABILITY_REVISION_FACTOR_NAMES = (
    "aq_profitability_revision_cash_confirmed",
    "aq_profitability_revision_asset_disciplined",
)
INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES = (
    "aq_industry_relative_profitability_surprise",
    "aq_industry_relative_asset_disciplined_surprise",
    "aq_industry_relative_cash_conversion_surprise",
)


def build_accounting_quality_statement_residual_ic_shape_prescreen(
    *,
    statement_roots: Iterable[str | Path],
    bars_roots: Iterable[str | Path],
    stock_basic_path: str | Path | None = None,
    daily_basic_roots: Iterable[str | Path] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.35,
    alpha: float = 0.05,
    factor_mode: str = "raw",
) -> dict[str, Any]:
    valid_factor_modes = {
        "raw",
        "repaired",
        "new_substructure",
        "new_substructure_directional_audit",
        "statement_event_drift",
        "statement_profitability_revision",
        "industry_relative_surprise",
    }
    if factor_mode not in valid_factor_modes:
        raise ValueError(
            "factor_mode must be 'raw', 'repaired', 'new_substructure', "
            "'new_substructure_directional_audit', 'statement_event_drift', "
            "'statement_profitability_revision', or 'industry_relative_surprise'"
        )
    statement_root_paths = [Path(root) for root in statement_roots]
    bars_root_paths = [Path(root) for root in bars_roots]
    raw_factor_frame = compute_accounting_quality_statement_factor_frame(
        statement_roots=statement_root_paths,
        bars_roots=bars_root_paths,
        deduplicate=True,
    )
    assets = sorted(raw_factor_frame["asset_id"].dropna().astype(str).unique()) if not raw_factor_frame.empty else []
    bars = _filter_date_window(
        _load_context_bars(bars_root_paths, assets),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        date_column="date",
    )
    context_factor_frame = _attach_market_context(
        raw_factor_frame,
        bars,
        daily_basic=_load_daily_basic_context(daily_basic_roots),
    )
    stock_basic = _load_stock_basic(stock_basic_path)
    candidate_specs = _accounting_candidate_specs()
    expected_candidate_count = len(candidate_specs)
    if factor_mode == "repaired":
        context_factor_frame = build_accounting_quality_statement_repaired_factor_frame(
            context_factor_frame,
            stock_basic,
            min_cross_section=min_cross_section,
        )
        candidate_specs = _repaired_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    elif factor_mode == "new_substructure":
        context_factor_frame = _filter_factor_names(context_factor_frame, NEW_SUBSTRUCTURE_FACTOR_NAMES)
        candidate_specs = _new_substructure_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    elif factor_mode == "new_substructure_directional_audit":
        context_factor_frame = build_accounting_quality_statement_directional_audit_factor_frame(context_factor_frame)
        candidate_specs = _directional_audit_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    elif factor_mode == "statement_event_drift":
        context_factor_frame = build_accounting_quality_statement_event_drift_factor_frame(context_factor_frame, bars)
        candidate_specs = _statement_event_drift_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    elif factor_mode == "statement_profitability_revision":
        context_factor_frame = _filter_factor_names(context_factor_frame, STATEMENT_PROFITABILITY_REVISION_FACTOR_NAMES)
        candidate_specs = _statement_profitability_revision_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    elif factor_mode == "industry_relative_surprise":
        context_factor_frame = build_accounting_quality_statement_industry_relative_surprise_factor_frame(
            context_factor_frame,
            stock_basic,
            min_cross_section=min_cross_section,
        )
        candidate_specs = _industry_relative_surprise_candidate_specs()
        expected_candidate_count = len(candidate_specs)
    else:
        context_factor_frame = _filter_factor_names(context_factor_frame, RAW_CASH_ACCRUAL_FACTOR_NAMES)
    factor_frame = _filter_date_window(
        context_factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        date_column="date",
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(horizons),
        execution_lag=int(execution_lag),
    )
    if not include_final_holdout and not labels.empty:
        labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_accounting_quality_statement_residual_ic_shape_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=candidate_specs,
        horizons=tuple(horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    result.update(
        {
            "statement_roots": [str(root) for root in statement_root_paths],
            "bars_roots": [str(root) for root in bars_root_paths],
            "stock_basic_path": str(Path(stock_basic_path)) if stock_basic_path else None,
            "daily_basic_roots": [str(Path(root)) for root in daily_basic_roots] if daily_basic_roots else [],
            "factor_mode": factor_mode,
            "data_window": _data_window(bars, factor_frame, labels),
            "pit_policy": {
                "signal_date_rule": "first_trade_date_strictly_after_ann_date",
                "same_day_announcement_trading_allowed": False,
                "execution_lag": int(execution_lag),
            },
        }
    )
    result["summary"]["source_factor_rows_before_context"] = int(len(raw_factor_frame))
    if factor_mode == "repaired":
        result["source_context"]["candidate_family"] = "accounting_accruals_cashflow_quality_repaired"
        result["summary"]["source_raw_factor_rows_before_repair"] = int(len(raw_factor_frame))
    if factor_mode == "new_substructure":
        result["source_context"]["candidate_family"] = "accounting_quality_new_substructure"
        result["summary"]["source_raw_factor_rows_before_new_substructure_filter"] = int(len(raw_factor_frame))
        result["summary"]["next_direction"] = (
            NEXT_DIRECTION_NEW_SUBSTRUCTURE_WITH_LEADS
            if int(result["summary"].get("research_lead_count", 0))
            else NEXT_DIRECTION_NEW_SUBSTRUCTURE_WITHOUT_LEADS
        )
    if factor_mode == "new_substructure_directional_audit":
        result["source_context"]["candidate_family"] = "accounting_quality_new_substructure_directional_audit"
        result["source_context"]["audit_source_factor"] = DIRECTIONAL_AUDIT_SOURCE_FACTOR_NAME
        result["summary"]["source_raw_factor_rows_before_directional_audit"] = int(len(raw_factor_frame))
        result["summary"]["next_direction"] = (
            NEXT_DIRECTION_DIRECTIONAL_AUDIT_WITH_LEADS
            if int(result["summary"].get("research_lead_count", 0))
            else NEXT_DIRECTION_DIRECTIONAL_AUDIT_WITHOUT_LEADS
        )
    if factor_mode == "statement_event_drift":
        result["source_context"]["candidate_family"] = "accounting_quality_statement_event_drift"
        result["source_context"]["source_factor"] = STATEMENT_EVENT_DRIFT_SOURCE_FACTOR_NAME
        result["source_context"]["event_reaction_rule"] = "last close before ann_date to signal_date close; factor date remains signal_date"
        result["summary"]["source_raw_factor_rows_before_statement_event_drift"] = int(len(raw_factor_frame))
        result["summary"]["next_direction"] = (
            NEXT_DIRECTION_STATEMENT_EVENT_DRIFT_WITH_LEADS
            if int(result["summary"].get("research_lead_count", 0))
            else NEXT_DIRECTION_STATEMENT_EVENT_DRIFT_WITHOUT_LEADS
        )
    if factor_mode == "statement_profitability_revision":
        result["source_context"]["candidate_family"] = "accounting_quality_statement_profitability_revision"
        result["source_context"]["hypothesis_source"] = (
            "realized statement profitability acceleration, cash confirmation, and asset-expansion discipline; "
            "PIT signal date after ann_date"
        )
        result["summary"]["source_raw_factor_rows_before_statement_profitability_revision"] = int(len(raw_factor_frame))
        result["summary"]["next_direction"] = (
            NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITH_LEADS
            if int(result["summary"].get("research_lead_count", 0))
            else NEXT_DIRECTION_STATEMENT_PROFITABILITY_REVISION_WITHOUT_LEADS
        )
    if factor_mode == "industry_relative_surprise":
        result["source_context"]["candidate_family"] = "accounting_quality_industry_relative_surprise"
        result["source_context"]["hypothesis_source"] = (
            "PIT financial statement changes ranked against same-signal-date industry peers; "
            "designed as a fresh Round253 non-price-volume expectation-revision/industry-relative surprise family"
        )
        result["summary"]["source_raw_factor_rows_before_industry_relative_surprise"] = int(len(raw_factor_frame))
        result["summary"]["next_direction"] = (
            NEXT_DIRECTION_INDUSTRY_RELATIVE_SURPRISE_WITH_LEADS
            if int(result["summary"].get("research_lead_count", 0))
            else NEXT_DIRECTION_INDUSTRY_RELATIVE_SURPRISE_WITHOUT_LEADS
        )
    result["markdown"] = render_accounting_quality_statement_residual_ic_shape_prescreen_markdown(result)
    return result


def summarize_accounting_quality_statement_residual_ic_shape_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.35,
    alpha: float = 0.05,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> dict[str, Any]:
    specs = list(candidate_specs or _accounting_candidate_specs())
    result = summarize_profitability_event_revision_controlled_ic_neutral_prescreen(
        factor_frame,
        labels,
        stock_basic,
        reference_factor_frame=pd.DataFrame(),
        expected_candidate_count=expected_candidate_count if expected_candidate_count is not None else len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        reference_high_corr_threshold=1.01,
        reference_mean_abs_corr_threshold=1.01,
        alpha=alpha,
    )
    summary = result.get("summary", {})
    blockers = _summary_blockers(factor_frame, labels, stock_basic)
    research_lead_count = int(summary.get("research_lead_count", 0))
    summary["passes"] = not blockers
    summary["blockers"] = blockers
    summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS if research_lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    summary["promotion_allowed_candidates"] = 0
    result.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "source_context": {
                "candidate_family": "accounting_accruals_cashflow_quality",
                "matrix_label_smoke_required_before_this_stage": True,
                "portfolio_grid_blocked_at_this_stage": True,
            },
            "summary": summary,
            "candidate_specs": specs,
            "holdout_policy": {
                "final_holdout_included": bool(include_final_holdout),
                "analysis_start_date": str(analysis_start_date),
                "analysis_end_date": str(analysis_end_date),
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
            },
            "reference_dedup_policy": {
                "reference_family": "not_applied_in_115_symbol_accounting_quality_shape_prescreen",
                "reason": "This early accounting-quality pass checks IC shape and neutralization only; any surviving lead still needs broad-sample reference de-duplication.",
            },
            "multiple_testing_policy": {
                "alpha": float(alpha),
                "method": "Bonferroni and Benjamini-Hochberg FDR across accounting-quality statement factor x horizon tests",
                "candidate_count": int(expected_candidate_count if expected_candidate_count is not None else len(specs)),
                "test_count": int(summary.get("test_count", 0)),
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "paper_ready_allowed": False,
                "portfolio_backtest_allowed_before_prescreen": False,
                "requires_next_gate": "walk_forward_cost_capacity_regime_preflight_after_residual_ic_shape_lead",
                "reason": "This is a residual IC shape prescreen, not Sharpe, total return, win rate, drawdown, or portfolio evidence.",
            },
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    for row in result.get("results", []) or []:
        row["promotion_allowed"] = False
    result["markdown"] = render_accounting_quality_statement_residual_ic_shape_prescreen_markdown(result)
    return result


def build_accounting_quality_statement_repaired_factor_frame(
    raw_factor_frame: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    if raw_factor_frame.empty:
        return _empty_factor_frame()
    wide = _wide_raw_accounting_quality_frame(raw_factor_frame)
    if wide.empty:
        return _empty_factor_frame()
    metadata = _stock_basic_industry(stock_basic)
    wide = wide.merge(metadata, on="asset_id", how="left")
    wide["industry"] = wide["industry"].fillna("").astype(str)
    repaired_pieces = []
    for _, date_frame in wide.groupby("date", sort=True):
        if len(date_frame) < int(min_cross_section):
            continue
        working = date_frame.copy()
        working["cash_conversion_rank"] = _percentile_rank(working.get("cashflow_minus_netprofit_to_assets_raw"))
        working["wc_accrual_quality_rank"] = _percentile_rank(-pd.to_numeric(working.get("working_capital_accruals_to_assets_raw"), errors="coerce"))
        working["cash_conversion_improvement_rank"] = _percentile_rank(working.get("earnings_cash_conversion_improvement_yoy_raw"))
        working["asset_growth_quality_rank"] = _percentile_rank(working.get("low_asset_growth_quality_raw"))
        working["cash_accrual_composite"] = working[
            ["cash_conversion_rank", "wc_accrual_quality_rank", "cash_conversion_improvement_rank"]
        ].mean(axis=1)
        valid_industry = working["industry"].astype(str).str.strip() != ""
        industry_mean = working.loc[valid_industry].groupby("industry")["cash_accrual_composite"].transform("mean")
        industry_relative = pd.Series(index=working.index, dtype=float)
        industry_relative.loc[valid_industry] = working.loc[valid_industry, "cash_accrual_composite"] - industry_mean
        asset_growth_residual = _residualize_against_exposures(
            working["asset_growth_quality_rank"],
            working,
            ("log_circ_mv", "log_total_mv", "log_adv20", "log_adv20_amount", "turnover_rate_f", "turnover_rate"),
        )
        balanced = pd.concat([industry_relative, asset_growth_residual], axis=1).mean(axis=1)
        repaired_pieces.extend(
            [
                _repaired_piece(working, REPAIRED_FACTOR_NAMES[0], industry_relative),
                _repaired_piece(working, REPAIRED_FACTOR_NAMES[1], asset_growth_residual),
                _repaired_piece(working, REPAIRED_FACTOR_NAMES[2], balanced),
            ]
        )
    pieces = [piece for piece in repaired_pieces if not piece.empty]
    if not pieces:
        return _empty_factor_frame()
    return (
        pd.concat(pieces, ignore_index=True)
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_accounting_quality_statement_residual_ic_shape_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "accounting_quality_statement_residual_ic_shape_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "accounting_quality_statement_residual_ic_shape_prescreen.md").write_text(
        render_accounting_quality_statement_residual_ic_shape_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "accounting_quality_statement_residual_ic_results.csv",
        result.get("results", []) or [],
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "accounting_quality_statement_residual_ic_observations.csv",
        result.get("ic_observations", []) or [],
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "accounting_quality_statement_neutral_observations.csv",
        result.get("neutral_observations", []) or [],
        NEUTRAL_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "accounting_quality_statement_reference_correlations.csv",
        result.get("reference_correlations", []) or [],
        REFERENCE_CORRELATION_COLUMNS,
    )


def render_accounting_quality_statement_residual_ic_shape_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Accounting Quality Statement Residual IC Shape Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {size:.4f} | {liq:.4f} | {fdr} | {lead} |".format(
                factor=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                liq=_number(row.get("mean_liquidity_neutral_rank_ic")),
                fdr="yes" if row.get("fdr_significant") else "no",
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage computes IC shape, FDR, industry-neutral IC, size-neutral IC, and liquidity-neutral IC.",
            "- It does not compute Sharpe, total return, annual return, win rate, drawdown, or any portfolio claim.",
            "- Any lead still needs broad-sample reference de-duplication, walk-forward, cost/capacity, regime coverage, and final-holdout checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_context_bars(roots: list[Path], assets: Sequence[str]) -> pd.DataFrame:
    frames = []
    required = ["date", "asset_id", "market", "adj_close"]
    asset_set = set(str(asset) for asset in assets)
    for root in roots:
        dataset_root = root / "processed" / "bars" / "frequency=1d" / "market=CN"
        if not dataset_root.exists():
            dataset_root = root
        for path in _dataset_files(dataset_root):
            frame = _read_frame(path)
            missing = [column for column in required if column not in frame]
            if missing:
                continue
            keep = [column for column in [*required, "amount"] if column in frame]
            frame = frame[keep].copy()
            if "amount" not in frame:
                frame["amount"] = pd.NA
            if asset_set:
                frame = frame[frame["asset_id"].astype(str).isin(asset_set)]
            if not frame.empty:
                frames.append(frame[[*required, "amount"]])
    if not frames:
        return pd.DataFrame(columns=[*required, "amount"])
    output = pd.concat(frames, ignore_index=True)
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["adj_close"] = pd.to_numeric(output["adj_close"], errors="coerce")
    output["amount"] = pd.to_numeric(output["amount"], errors="coerce")
    return (
        output[(output["market"] == "CN") & (output["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
    date_column: str,
) -> pd.DataFrame:
    if frame.empty or date_column not in frame:
        return frame.copy()
    output = frame.copy()
    dates = pd.to_datetime(output[date_column], errors="coerce")
    start = pd.Timestamp(start_date)
    end = dates.max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(dates >= start) & (dates <= end)].reset_index(drop=True)


def _data_window(bars: pd.DataFrame, factor_frame: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
    }


def _accounting_candidate_specs() -> list[dict[str, Any]]:
    specs = []
    for spec in FORMULA_SPECS:
        if str(spec["factor_name"]) not in RAW_CASH_ACCRUAL_FACTOR_NAMES:
            continue
        specs.append(
            {
                "factor_name": str(spec["factor_name"]),
                "family": "accounting_accruals_cashflow_quality",
                "formula": str(spec.get("formula", "")),
                "hypothesis_source": "public accounting accruals and cash-conversion quality literature",
            }
        )
    return specs


def _new_substructure_candidate_specs() -> list[dict[str, Any]]:
    specs = []
    for spec in FORMULA_SPECS:
        if str(spec["factor_name"]) not in NEW_SUBSTRUCTURE_FACTOR_NAMES:
            continue
        specs.append(
            {
                "factor_name": str(spec["factor_name"]),
                "family": "accounting_quality_new_substructure",
                "formula": str(spec.get("formula", "")),
                "hypothesis_source": "round243 accounting-quality new substructure seed after stopping raw/repaired cash-accrual tuning",
            }
        )
    return specs


def _directional_audit_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": DIRECTIONAL_AUDIT_FACTOR_NAME,
            "family": "accounting_quality_new_substructure_directional_audit",
            "formula": f"-1 * {DIRECTIONAL_AUDIT_SOURCE_FACTOR_NAME}",
            "hypothesis_source": "round245 preregistered sign-direction audit after round244 negative raw IC clue; counted as a new hypothesis test",
        }
    ]


def _statement_event_drift_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": STATEMENT_EVENT_DRIFT_FACTOR_NAME,
            "family": "accounting_quality_statement_event_drift",
            "formula": (
                "0.5 * within-date rank(earnings_cash_conversion_improvement_yoy_raw) + "
                "0.5 * within-date rank(-abs(signal_close / pre_announcement_close - 1))"
            ),
            "hypothesis_source": (
                "round243 aq_post_statement_announcement_drift seed; PEAD and underreaction literature, "
                "with PIT announcement timing and next-label execution lag"
            ),
        }
    ]


def _statement_profitability_revision_candidate_specs() -> list[dict[str, Any]]:
    specs = []
    for spec in FORMULA_SPECS:
        if str(spec["factor_name"]) not in STATEMENT_PROFITABILITY_REVISION_FACTOR_NAMES:
            continue
        specs.append(
            {
                "factor_name": str(spec["factor_name"]),
                "family": "accounting_quality_statement_profitability_revision",
                "formula": str(spec.get("formula", "")),
                "hypothesis_source": (
                    "round247 realized statement profitability revision family after round246 event-drift failure; "
                    "uses only point-in-time statement fields after announcement"
                ),
            }
        )
    return specs


def _industry_relative_surprise_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[0],
            "family": "accounting_quality_industry_relative_surprise",
            "formula": (
                "within-date rank(aq_profitability_revision_cash_confirmed) minus same-industry mean rank; "
                "requires at least two same-industry announcers on the signal date"
            ),
            "hypothesis_source": (
                "Round253 fresh non-price-volume expectation-revision hypothesis: "
                "profitability acceleration confirmed by cashflow should matter more when it is surprising versus peers"
            ),
        },
        {
            "factor_name": INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[1],
            "family": "accounting_quality_industry_relative_surprise",
            "formula": (
                "within-date rank(aq_profitability_revision_asset_disciplined) minus same-industry mean rank; "
                "requires at least two same-industry announcers on the signal date"
            ),
            "hypothesis_source": (
                "Round253 fresh non-price-volume expectation-revision hypothesis: "
                "profitability revision is cleaner when not driven by balance-sheet expansion"
            ),
        },
        {
            "factor_name": INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[2],
            "family": "accounting_quality_industry_relative_surprise",
            "formula": (
                "within-date rank(earnings_cash_conversion_improvement_yoy_raw) minus same-industry mean rank; "
                "requires at least two same-industry announcers on the signal date"
            ),
            "hypothesis_source": (
                "Round253 fresh industry-relative surprise hypothesis: "
                "cash-conversion improvement is evaluated against peers reporting in the same timing cluster"
            ),
        },
    ]


def _repaired_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": REPAIRED_FACTOR_NAMES[0],
            "family": "accounting_accruals_cashflow_quality_repaired",
            "formula": "within-date industry-relative rank composite of cash conversion, working-capital accrual quality, and cash-conversion improvement",
            "hypothesis_source": "accrual anomaly repaired by industry-relative normalization",
        },
        {
            "factor_name": REPAIRED_FACTOR_NAMES[1],
            "family": "accounting_accruals_cashflow_quality_repaired",
            "formula": "rank(low_asset_growth_quality_raw) residualized against size and liquidity exposures",
            "hypothesis_source": "asset-growth anomaly repaired by size/liquidity exposure control",
        },
        {
            "factor_name": REPAIRED_FACTOR_NAMES[2],
            "family": "accounting_accruals_cashflow_quality_repaired",
            "formula": "equal-weight average of industry-relative cash/accrual quality and size/liquidity residual asset-growth quality",
            "hypothesis_source": "simple two-sleeve accounting-quality composite with exposure repair",
        },
    ]


def build_accounting_quality_statement_event_drift_factor_frame(frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or bars.empty or "factor_name" not in frame:
        return _empty_factor_frame()
    source = frame[frame["factor_name"].astype(str) == STATEMENT_EVENT_DRIFT_SOURCE_FACTOR_NAME].copy()
    if source.empty:
        return _empty_factor_frame()
    for column in ["date", "ann_date", "end_date", "signal_date"]:
        if column in source:
            source[column] = pd.to_datetime(source[column], errors="coerce")
    for column in ["asset_id", "market"]:
        if column not in source:
            source[column] = "CN" if column == "market" else ""
    source["asset_id"] = source["asset_id"].astype(str)
    source["market"] = source["market"].fillna("CN").astype(str).str.upper()
    source["factor_value"] = pd.to_numeric(source["factor_value"], errors="coerce")
    source = source.dropna(subset=["date", "ann_date", "signal_date", "asset_id", "factor_value"]).copy()
    source = source[source["signal_date"] > source["ann_date"]].copy()
    if source.empty:
        return _empty_factor_frame()

    source["announcement_reaction"] = _announcement_reaction_from_bars(source, bars)
    source = source.dropna(subset=["announcement_reaction"]).copy()
    if source.empty:
        return _empty_factor_frame()

    quality_rank = source.groupby("date")["factor_value"].rank(pct=True, method="average")
    muted_reaction_rank = (-source["announcement_reaction"].abs()).groupby(source["date"]).rank(pct=True, method="average")
    source["cash_conversion_rank"] = quality_rank
    source["muted_reaction_rank"] = muted_reaction_rank
    source["factor_name"] = STATEMENT_EVENT_DRIFT_FACTOR_NAME
    source["factor_value"] = 0.5 * quality_rank + 0.5 * muted_reaction_rank
    source = source.dropna(subset=["factor_value"]).reset_index(drop=True)
    return source.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_accounting_quality_statement_directional_audit_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "factor_name" not in frame:
        return _empty_factor_frame()
    source = frame[frame["factor_name"].astype(str) == DIRECTIONAL_AUDIT_SOURCE_FACTOR_NAME].copy()
    if source.empty:
        return _empty_factor_frame()
    source["factor_name"] = DIRECTIONAL_AUDIT_FACTOR_NAME
    source["factor_value"] = -pd.to_numeric(source["factor_value"], errors="coerce")
    source = source.dropna(subset=["date", "ann_date", "signal_date", "asset_id", "factor_value"]).reset_index(drop=True)
    return source


def build_accounting_quality_statement_industry_relative_surprise_factor_frame(
    raw_factor_frame: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    if raw_factor_frame.empty:
        return _empty_factor_frame()
    wide = _wide_raw_accounting_quality_frame(raw_factor_frame)
    if wide.empty:
        return _empty_factor_frame()
    metadata = _stock_basic_industry(stock_basic)
    wide = wide.merge(metadata, on="asset_id", how="left")
    wide["industry"] = wide["industry"].fillna("").astype(str)
    source_map = [
        (INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[0], "aq_profitability_revision_cash_confirmed"),
        (INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[1], "aq_profitability_revision_asset_disciplined"),
        (INDUSTRY_RELATIVE_SURPRISE_FACTOR_NAMES[2], "earnings_cash_conversion_improvement_yoy_raw"),
    ]
    pieces: list[pd.DataFrame] = []
    for _, date_frame in wide.groupby("date", sort=True):
        if len(date_frame) < int(min_cross_section):
            continue
        working = date_frame.copy()
        valid_industry = working["industry"].astype(str).str.strip() != ""
        same_industry_counts = pd.Series(index=working.index, dtype=float)
        if valid_industry.any():
            same_industry_counts.loc[valid_industry] = (
                working.loc[valid_industry].groupby("industry")["asset_id"].transform("count")
            )
        valid_peer_group = valid_industry & (same_industry_counts >= 2)
        if not valid_peer_group.any():
            continue
        for factor_name, source_name in source_map:
            if source_name not in working:
                continue
            source_rank = _percentile_rank(working[source_name])
            industry_mean_rank = pd.Series(index=working.index, dtype=float)
            industry_mean_rank.loc[valid_peer_group] = (
                source_rank.loc[valid_peer_group]
                .groupby(working.loc[valid_peer_group, "industry"])
                .transform("mean")
            )
            industry_relative = source_rank - industry_mean_rank
            industry_relative.loc[~valid_peer_group] = pd.NA
            pieces.append(_repaired_piece(working, factor_name, industry_relative))
    pieces = [piece for piece in pieces if not piece.empty]
    if not pieces:
        return _empty_factor_frame()
    return (
        pd.concat(pieces, ignore_index=True)
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def _announcement_reaction_from_bars(source: pd.DataFrame, bars: pd.DataFrame) -> pd.Series:
    required = ["date", "asset_id", "market", "adj_close"]
    if bars.empty or any(column not in bars for column in required):
        return pd.Series(pd.NA, index=source.index, dtype="Float64")
    bar_frame = bars[required].copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"], errors="coerce")
    bar_frame["asset_id"] = bar_frame["asset_id"].astype(str)
    bar_frame["market"] = bar_frame["market"].fillna("CN").astype(str).str.upper()
    bar_frame["adj_close"] = pd.to_numeric(bar_frame["adj_close"], errors="coerce")
    bar_frame = (
        bar_frame[(bar_frame["market"] == "CN") & (bar_frame["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "market", "date"])
        .reset_index(drop=True)
    )
    bar_lookup = {}
    for key, group in bar_frame.groupby(["asset_id", "market"], sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        bar_lookup[key] = {
            "dates": pd.DatetimeIndex(group["date"]),
            "closes": group["adj_close"].to_numpy(dtype=float),
        }

    reactions: list[float] = []
    for _, row in source.iterrows():
        key = (str(row["asset_id"]), str(row["market"]).upper())
        data = bar_lookup.get(key)
        if data is None:
            reactions.append(float("nan"))
            continue
        dates: pd.DatetimeIndex = data["dates"]
        closes = data["closes"]
        ann_date = pd.Timestamp(row["ann_date"])
        signal_date = pd.Timestamp(row["signal_date"])
        pre_position = int(dates.searchsorted(ann_date, side="left")) - 1
        signal_position = int(dates.searchsorted(signal_date, side="left"))
        if pre_position < 0 or signal_position >= len(dates) or dates[signal_position] != signal_date:
            reactions.append(float("nan"))
            continue
        pre_close = float(closes[pre_position])
        signal_close = float(closes[signal_position])
        if not math.isfinite(pre_close) or not math.isfinite(signal_close) or pre_close <= 0:
            reactions.append(float("nan"))
            continue
        reactions.append(signal_close / pre_close - 1.0)
    return pd.Series(reactions, index=source.index, dtype=float)


def _filter_factor_names(frame: pd.DataFrame, factor_names: Sequence[str]) -> pd.DataFrame:
    if frame.empty or "factor_name" not in frame:
        return frame.copy()
    allowed = {str(name) for name in factor_names}
    output = frame[frame["factor_name"].astype(str).isin(allowed)].copy()
    return output.reset_index(drop=True)


def _wide_raw_accounting_quality_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    if frame.empty or any(column not in frame for column in required):
        return pd.DataFrame()
    output = frame.copy()
    for column in ["date", "ann_date", "end_date", "signal_date"]:
        if column in output:
            output[column] = pd.to_datetime(output[column], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    index_columns = [
        column
        for column in [
            "date",
            "asset_id",
            "market",
            "ann_date",
            "end_date",
            "signal_date",
            "amount",
            "adv20_amount",
            "log_adv20",
            "log_adv20_amount",
            "log_total_mv",
            "log_circ_mv",
            "turnover_rate",
            "turnover_rate_f",
        ]
        if column in output
    ]
    wide = output.pivot_table(
        index=index_columns,
        columns="factor_name",
        values="factor_value",
        aggfunc="last",
    ).reset_index()
    wide.columns.name = None
    return wide


def _stock_basic_industry(stock_basic: pd.DataFrame) -> pd.DataFrame:
    if stock_basic.empty:
        return pd.DataFrame(columns=["asset_id", "industry"])
    frame = stock_basic.copy()
    for column in ["asset_id", "industry"]:
        if column not in frame:
            frame[column] = ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["industry"] = frame["industry"].fillna("").astype(str)
    return frame[["asset_id", "industry"]].drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def _percentile_rank(values: Any) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce")
    return series.rank(pct=True, method="average")


def _residualize_against_exposures(y: pd.Series, frame: pd.DataFrame, exposure_columns: Sequence[str]) -> pd.Series:
    y_rank = pd.to_numeric(y, errors="coerce").rank(method="average")
    exposure_data = {}
    for column in exposure_columns:
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().sum() >= 3 and values.nunique(dropna=True) >= 2:
            exposure_data[column] = values.rank(method="average")
    output = pd.Series(index=frame.index, dtype=float)
    if not exposure_data:
        output.loc[y_rank.dropna().index] = y_rank.dropna() - y_rank.dropna().mean()
        return output
    design = pd.DataFrame(exposure_data, index=frame.index)
    design["y"] = y_rank
    valid = design.dropna()
    if len(valid) < 3:
        output.loc[y_rank.dropna().index] = y_rank.dropna() - y_rank.dropna().mean()
        return output
    x = valid.drop(columns=["y"]).to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(x)), x])
    y_values = valid["y"].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(x, y_values, rcond=None)
    fitted = x @ beta
    output.loc[valid.index] = y_values - fitted
    return output


def _repaired_piece(base: pd.DataFrame, factor_name: str, values: pd.Series) -> pd.DataFrame:
    piece = base[["date", "ann_date", "end_date", "signal_date", "asset_id", "market"]].copy()
    piece["factor_name"] = factor_name
    piece["factor_value"] = pd.to_numeric(values, errors="coerce")
    for column in [
        "amount",
        "adv20_amount",
        "log_adv20",
        "log_amount",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "total_mv",
        "circ_mv",
        "log_total_mv",
        "log_circ_mv",
    ]:
        if column in base:
            piece[column] = base[column]
    return piece.dropna(subset=["date", "ann_date", "signal_date", "asset_id", "factor_value"]).reset_index(drop=True)


def _summary_blockers(factor_frame: pd.DataFrame, labels: pd.DataFrame, stock_basic: pd.DataFrame) -> list[str]:
    blockers = []
    if factor_frame.empty:
        blockers.append("missing_factor_rows")
    if labels.empty:
        blockers.append("missing_label_rows")
    if stock_basic.empty:
        blockers.append("missing_stock_basic_industry_context")
    return blockers


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "ann_date", "end_date", "signal_date", "asset_id", "market", "factor_name", "factor_value"]
    )


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


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0
