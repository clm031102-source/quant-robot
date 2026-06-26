from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.alpha101_rank_pv_reversal_reference_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    _reference_value_series,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    _sanitize,
    _write_csv,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    YEARLY_IC_COLUMNS,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _period_ic,
)
from quant_robot.ops.public_reference_multi_family_preregistration import SAFETY
from quant_robot.ops.public_reference_multi_family_prescreen import (
    _add_cross_sectional_features,
    _candidate_value_series,
    _feature_frame,
    _normalise_bars,
    load_public_reference_multi_family_bars,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.factor_inputs import load_factor_inputs
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs


STAGE = "alpha101_rank_pv_reversal_residual_prescreen"
DEFAULT_HORIZON = 20
DEFAULT_RESIDUAL_FACTOR_NAME = "alpha101_rank_pv_reversal_residual_vs_pv_cluster_20"
ROUND129_SOURCE_AUDIT = "docs/research/cn_stock_alpha101_rank_pv_reversal_reference_dedup_round129_2026-06-22.md"
NEXT_RESIDUAL_WALK_FORWARD_PREREGISTRATION_DIRECTION = (
    "round131_alpha101_rank_pv_reversal_residual_walk_forward_cost_capacity_preregistration"
)
NEXT_HIBERNATE_OR_ROTATE_DIRECTION = "round131_rotate_to_non_price_volume_public_reference_or_daily_basic_family"
DEFAULT_REFERENCE_FACTOR_NAMES = (
    "pv_corr_reversal_capacity_safe_20",
    "pv_lowvol_reversal_blend_20",
    "raw_neg_pv_corr_20",
)
MONTHLY_IC_COLUMNS = ["month", "ic_observations", "mean_spearman_ic", "positive_ic_rate", "failure"]
RESIDUAL_DIAGNOSTIC_COLUMNS = [
    "date",
    "cross_section",
    "lead_std",
    "residual_std",
    "r_squared",
]


def build_alpha101_rank_pv_reversal_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    moneyflow_input_root: str | Path,
    round129_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    residual_factor_name: str = DEFAULT_RESIDUAL_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.30,
    min_residual_t_stat: float = 2.0,
    min_positive_ic_rate: float = 0.55,
    min_residual_std: float = 1e-6,
    max_yearly_failure_count: int = 1,
) -> dict[str, Any]:
    report = _load_report(round129_report)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_inputs = load_factor_inputs(factor_input_root, "CN")
    moneyflow_inputs = load_moneyflow_inputs(moneyflow_input_root, "CN")
    return build_alpha101_rank_pv_reversal_residual_prescreen_from_frames(
        bars=bars,
        factor_inputs=factor_inputs,
        moneyflow_inputs=moneyflow_inputs,
        round129_report=report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        lead_factor_name=lead_factor_name,
        residual_factor_name=residual_factor_name,
        reference_factor_names=reference_factor_names,
        horizon=horizon,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_t_stat=min_residual_t_stat,
        min_positive_ic_rate=min_positive_ic_rate,
        min_residual_std=min_residual_std,
        max_yearly_failure_count=max_yearly_failure_count,
    )


def build_alpha101_rank_pv_reversal_residual_prescreen_from_frames(
    *,
    bars: pd.DataFrame,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    round129_report: dict[str, Any] | None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    residual_factor_name: str = DEFAULT_RESIDUAL_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.30,
    min_residual_t_stat: float = 2.0,
    min_positive_ic_rate: float = 0.55,
    min_residual_std: float = 1e-6,
    max_yearly_failure_count: int = 1,
) -> dict[str, Any]:
    bars = _normalise_bars(bars)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout and not bars.empty:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)].reset_index(drop=True)
    signal_frame, features = compute_alpha101_rank_pv_reversal_signal_frame(
        bars,
        factor_inputs=factor_inputs,
        moneyflow_inputs=moneyflow_inputs,
        lead_factor_name=lead_factor_name,
        reference_factor_names=reference_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )
    residual_frame, residual_diagnostics = residualize_alpha101_rank_pv_reversal_signal_frame(
        signal_frame,
        residual_factor_name=residual_factor_name,
        reference_factor_names=reference_factor_names,
        min_cross_section=min_cross_section,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_alpha101_rank_pv_reversal_residual_prescreen(
        residual_frame,
        labels,
        residual_diagnostics=residual_diagnostics,
        round129_report=round129_report,
        residual_factor_name=residual_factor_name,
        reference_factor_names=reference_factor_names,
        horizon=horizon,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_t_stat=min_residual_t_stat,
        min_positive_ic_rate=min_positive_ic_rate,
        min_residual_std=min_residual_std,
        max_yearly_failure_count=max_yearly_failure_count,
    )
    result["data_window"] = _data_window(bars, features, signal_frame, residual_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "amount_and_adv20_filters_enabled": True,
    }
    result["markdown"] = render_alpha101_rank_pv_reversal_residual_prescreen_markdown(result)
    return result


def compute_alpha101_rank_pv_reversal_signal_frame(
    bars: pd.DataFrame,
    *,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    min_signal_date_amount: float = 10_000_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = _feature_frame(bars, factor_inputs=factor_inputs, moneyflow_inputs=moneyflow_inputs)
    if features.empty:
        return _empty_signal_frame(reference_factor_names), features
    features = _add_cross_sectional_features(features)
    candidate_values = _candidate_value_series(features)
    if lead_factor_name not in candidate_values:
        raise ValueError(f"Unsupported lead factor: {lead_factor_name}")
    reference_values = _reference_value_series(features, candidate_values)
    missing = [name for name in reference_factor_names if name not in reference_values]
    if missing:
        raise ValueError(f"Unsupported reference factors: {', '.join(missing)}")
    capacity_mask = (
        (pd.to_numeric(features["amount"], errors="coerce") >= min_signal_date_amount)
        & (pd.to_numeric(features["adv20_amount"], errors="coerce") >= min_signal_date_amount)
        & (pd.to_numeric(features["return_1d"], errors="coerce").abs() <= 0.50)
    )
    frame = features.loc[capacity_mask, ["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    frame["lead_value"] = pd.to_numeric(candidate_values[lead_factor_name].loc[capacity_mask], errors="coerce")
    for reference_name in reference_factor_names:
        frame[reference_name] = pd.to_numeric(reference_values[reference_name].loc[capacity_mask], errors="coerce")
    return frame.dropna(subset=["date", "asset_id", "market", "lead_value", *reference_factor_names]), features


def residualize_alpha101_rank_pv_reversal_signal_frame(
    signal_frame: pd.DataFrame,
    *,
    residual_factor_name: str = DEFAULT_RESIDUAL_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    min_cross_section: int = 30,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if signal_frame.empty:
        return _empty_residual_frame(), []
    missing = [name for name in ("date", "asset_id", "market", "lead_value", *reference_factor_names) if name not in signal_frame]
    if missing:
        raise ValueError(f"Signal frame is missing required columns: {', '.join(missing)}")
    frame = signal_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    rows: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    base_columns = [column for column in ["date", "asset_id", "market", "amount", "adv20_amount"] if column in frame]
    for signal_date, group in frame.groupby("date", sort=True):
        valid = group.dropna(subset=["lead_value", *reference_factor_names]).copy()
        if len(valid) < min_cross_section:
            continue
        y = pd.to_numeric(valid["lead_value"], errors="coerce").to_numpy(dtype=float)
        x = valid[list(reference_factor_names)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(y) & np.isfinite(x).all(axis=1)
        if int(finite.sum()) < min_cross_section:
            continue
        valid = valid.loc[finite].copy()
        y = y[finite]
        x = x[finite]
        design = np.column_stack([np.ones(len(x)), x])
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        fitted = design @ beta
        residual = y - fitted
        ss_total = float(np.square(y - y.mean()).sum())
        ss_residual = float(np.square(residual).sum())
        r_squared = 1.0 - ss_residual / ss_total if ss_total > 1e-12 else 0.0
        output = valid[base_columns].copy()
        output["factor_name"] = residual_factor_name
        output["factor_value"] = residual
        rows.append(output)
        diagnostics.append(
            {
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "cross_section": int(len(valid)),
                "lead_std": float(np.std(y, ddof=0)),
                "residual_std": float(np.std(residual, ddof=0)),
                "r_squared": float(r_squared),
            }
        )
    if not rows:
        return _empty_residual_frame(), diagnostics
    residual_frame = (
        pd.concat(rows, ignore_index=True)
        .dropna(subset=["date", "asset_id", "market", "factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )
    return residual_frame, diagnostics


def summarize_alpha101_rank_pv_reversal_residual_prescreen(
    residual_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    residual_diagnostics: Sequence[dict[str, Any]] | pd.DataFrame,
    round129_report: dict[str, Any] | None,
    residual_factor_name: str = DEFAULT_RESIDUAL_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    horizon: int = DEFAULT_HORIZON,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.30,
    min_residual_t_stat: float = 2.0,
    min_positive_ic_rate: float = 0.55,
    min_residual_std: float = 1e-6,
    max_yearly_failure_count: int = 1,
) -> dict[str, Any]:
    residual_frame = _normalise_residual_frame(residual_frame)
    residual_frame = residual_frame[residual_frame["factor_name"] == residual_factor_name].reset_index(drop=True)
    ic_frame = _filter_low_variance_residual_dates(
        residual_frame,
        residual_diagnostics,
        min_residual_std=min_residual_std,
    )
    ic_observations = _lead_ic_observations(
        ic_frame,
        labels,
        lead_factor_name=residual_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    residual_ic_summary = _lead_ic_summary(ic_observations, min_ic_observations=min_ic_observations)
    yearly_ic = _period_ic(ic_observations, period="year")
    monthly_ic = _period_ic(ic_observations, period="month")
    diagnostics_summary = _residual_diagnostics_summary(residual_diagnostics)
    round129_evidence = _round129_evidence(round129_report)
    blockers = _gate_blockers(
        residual_frame=residual_frame,
        residual_ic_summary=residual_ic_summary,
        yearly_ic=yearly_ic,
        residual_diagnostics_summary=diagnostics_summary,
        round129_evidence=round129_evidence,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_t_stat=min_residual_t_stat,
        min_positive_ic_rate=min_positive_ic_rate,
        min_residual_std=min_residual_std,
        max_yearly_failure_count=max_yearly_failure_count,
    )
    walk_forward_allowed = not blockers
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": DEFAULT_LEAD_FACTOR_NAME,
        "residual_factor_name": residual_factor_name,
        "reference_factor_names": list(reference_factor_names),
        "horizon": int(horizon),
        "source_context": {
            "source_audit": ROUND129_SOURCE_AUDIT,
            "round129_required_before_residual_prescreen": True,
            "portfolio_grid_blocked_before_independent_residual_ic": True,
        },
        "round129_evidence": round129_evidence,
        "summary": {
            "residual_rows": int(len(residual_frame)),
            "residual_date_count": int(residual_frame["date"].nunique()) if not residual_frame.empty else 0,
            "yearly_failure_count": int(sum(1 for row in yearly_ic if row["failure"])),
            "monthly_failure_count": int(sum(1 for row in monthly_ic if row["failure"])),
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
        },
        "residual_diagnostics_summary": diagnostics_summary,
        "residual_ic_summary": residual_ic_summary,
        "thresholds": {
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "min_residual_mean_ic": min_residual_mean_ic,
            "min_residual_icir": min_residual_icir,
            "min_residual_t_stat": min_residual_t_stat,
            "min_positive_ic_rate": min_positive_ic_rate,
            "min_residual_std": min_residual_std,
            "max_yearly_failure_count": max_yearly_failure_count,
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round129_alpha101_rank_pv_reversal_reference_dedup_read",
                "round129_high_redundancy_cluster_confirmed",
                "residualize_against_high_redundancy_reference_cluster",
                "cost_capacity_regime_walk_forward_required_before_promotion",
            ],
            "drawdown_policy": "A higher drawdown tolerance can relax MaxDD screening only; it cannot waive redundancy, look-ahead, overfit, cost, capacity, or walk-forward gates.",
        },
        "residual_walk_forward_policy": {
            "residual_walk_forward_preregistration_allowed": walk_forward_allowed,
            "next_allowed_action": NEXT_RESIDUAL_WALK_FORWARD_PREREGISTRATION_DIRECTION,
            "portfolio_grid_allowed_before_preregistration": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "manual_live_allowed": False,
            "reason": "Round130 is an incremental residual IC audit only; promotion requires separate pre-registered walk-forward, cost, capacity, and regime validation.",
        },
        "next_direction": (
            NEXT_RESIDUAL_WALK_FORWARD_PREREGISTRATION_DIRECTION
            if walk_forward_allowed
            else NEXT_HIBERNATE_OR_ROTATE_DIRECTION
        ),
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "ic_observations": ic_observations,
        "residual_diagnostics": _normalise_diagnostics_rows(residual_diagnostics),
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_alpha101_rank_pv_reversal_residual_prescreen_markdown(result)
    return result


def write_alpha101_rank_pv_reversal_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "alpha101_rank_pv_reversal_residual_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "alpha101_rank_pv_reversal_residual_prescreen.md").write_text(
        render_alpha101_rank_pv_reversal_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_residual_ic_observations.csv",
        result.get("ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_residual_yearly_ic.csv",
        result.get("yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_residual_monthly_ic.csv",
        result.get("monthly_ic", []),
        MONTHLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_residual_diagnostics.csv",
        result.get("residual_diagnostics", []),
        RESIDUAL_DIAGNOSTIC_COLUMNS,
    )


def render_alpha101_rank_pv_reversal_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    ic = result.get("residual_ic_summary", {})
    diagnostics = result.get("residual_diagnostics_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Alpha101 Rank PV Reversal Residual Prescreen",
        "",
        "## Summary",
        "",
        f"- Residual factor: `{result.get('residual_factor_name', DEFAULT_RESIDUAL_FACTOR_NAME)}`",
        f"- Reference cluster: {', '.join(result.get('reference_factor_names', []))}",
        f"- Residual rows: {summary.get('residual_rows', 0)}",
        f"- Residual dates: {summary.get('residual_date_count', 0)}",
        f"- Median R-squared explained by references: {diagnostics.get('median_r_squared', 0.0):.4f}",
        f"- Median residual std: {diagnostics.get('median_residual_std', 0.0):.6f}",
        f"- IC observations: {ic.get('ic_observations', 0)}",
        f"- Mean residual IC: {ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Residual ICIR: {ic.get('icir', 0.0):.3f}",
        f"- Residual IC t-stat: {ic.get('ic_t_stat', 0.0):.2f}",
        f"- Positive residual IC rate: {ic.get('positive_ic_rate', 0.0):.1%}",
        f"- Yearly failures: {summary.get('yearly_failure_count', 0)}",
        f"- Residual walk-forward preregistration allowed: {result.get('residual_walk_forward_policy', {}).get('residual_walk_forward_preregistration_allowed', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        "",
        "## Yearly Residual IC",
        "",
        "| Year | Obs | Mean IC | IC+ | Failure |",
        "|---:|---:|---:|---:|---|",
    ]
    for row in result.get("yearly_ic", []):
        lines.append(
            f"| {row.get('year')} | {row.get('ic_observations', 0)} | {row.get('mean_spearman_ic', 0.0):.4f} | {row.get('positive_ic_rate', 0.0):.1%} | {row.get('failure', False)} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
            f"- Drawdown policy: {gate.get('drawdown_policy', '')}",
            f"- Promotion reason: {result.get('promotion_policy', {}).get('reason', '')}",
            f"- Safety: {result.get('safety', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _gate_blockers(
    *,
    residual_frame: pd.DataFrame,
    residual_ic_summary: dict[str, Any],
    yearly_ic: list[dict[str, Any]],
    residual_diagnostics_summary: dict[str, Any],
    round129_evidence: dict[str, Any],
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_t_stat: float,
    min_positive_ic_rate: float,
    min_residual_std: float,
    max_yearly_failure_count: int,
) -> list[str]:
    blockers: list[str] = []
    if residual_frame.empty:
        blockers.append("residual_factor_frame_empty")
    if not round129_evidence.get("round129_report_present", False):
        blockers.append("round129_report_missing")
    if round129_evidence.get("reference_highly_redundant_count", 0) < 1:
        blockers.append("round129_high_redundancy_cluster_not_confirmed")
    if residual_diagnostics_summary.get("median_residual_std", 0.0) <= min_residual_std:
        blockers.append("residual_signal_variance_too_low")
    if not residual_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_ic_summary.get("mean_spearman_ic", 0.0) < min_residual_mean_ic:
        blockers.append("residual_ic_below_threshold")
    if residual_ic_summary.get("icir", 0.0) < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_ic_summary.get("ic_t_stat", 0.0) < min_residual_t_stat:
        blockers.append("residual_t_stat_below_threshold")
    if residual_ic_summary.get("positive_ic_rate", 0.0) < min_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    yearly_failure_count = sum(1 for row in yearly_ic if row.get("failure"))
    if yearly_failure_count > max_yearly_failure_count:
        blockers.append("yearly_ic_instability")
    return blockers


def _filter_low_variance_residual_dates(
    residual_frame: pd.DataFrame,
    residual_diagnostics: Sequence[dict[str, Any]] | pd.DataFrame,
    *,
    min_residual_std: float,
) -> pd.DataFrame:
    if residual_frame.empty:
        return residual_frame
    rows = _normalise_diagnostics_rows(residual_diagnostics)
    keep_dates = {
        pd.Timestamp(row["date"])
        for row in rows
        if float(row.get("residual_std", 0.0)) > min_residual_std
    }
    if not keep_dates:
        return residual_frame.iloc[0:0].copy()
    return residual_frame[pd.to_datetime(residual_frame["date"]).isin(keep_dates)].reset_index(drop=True)


def _round129_evidence(round129_report: dict[str, Any] | None) -> dict[str, Any]:
    report = round129_report or {}
    summary = report.get("summary", {})
    gate = report.get("gate", {})
    return {
        "round129_report_present": bool(round129_report),
        "round129_stage": report.get("stage"),
        "reference_highly_redundant_count": int(summary.get("reference_highly_redundant_count", 0)),
        "reference_moderately_redundant_count": int(summary.get("reference_moderately_redundant_count", 0)),
        "round129_blockers": list(gate.get("blockers", [])),
        "round129_next_direction": report.get("next_direction"),
    }


def _residual_diagnostics_summary(residual_diagnostics: Sequence[dict[str, Any]] | pd.DataFrame) -> dict[str, Any]:
    rows = _normalise_diagnostics_rows(residual_diagnostics)
    if not rows:
        return {
            "diagnostic_dates": 0,
            "median_cross_section": 0.0,
            "median_r_squared": 0.0,
            "mean_r_squared": 0.0,
            "median_residual_std": 0.0,
            "mean_residual_std": 0.0,
            "median_lead_std": 0.0,
        }
    frame = pd.DataFrame(rows)
    return {
        "diagnostic_dates": int(len(frame)),
        "median_cross_section": float(frame["cross_section"].median()),
        "median_r_squared": float(frame["r_squared"].median()),
        "mean_r_squared": float(frame["r_squared"].mean()),
        "median_residual_std": float(frame["residual_std"].median()),
        "mean_residual_std": float(frame["residual_std"].mean()),
        "median_lead_std": float(frame["lead_std"].median()),
    }


def _normalise_diagnostics_rows(residual_diagnostics: Sequence[dict[str, Any]] | pd.DataFrame) -> list[dict[str, Any]]:
    if isinstance(residual_diagnostics, pd.DataFrame):
        rows = residual_diagnostics.to_dict("records")
    else:
        rows = list(residual_diagnostics or [])
    clean_rows = []
    for row in rows:
        clean_rows.append(
            {
                "date": str(row.get("date")),
                "cross_section": int(row.get("cross_section", 0)),
                "lead_std": float(row.get("lead_std", 0.0)),
                "residual_std": float(row.get("residual_std", 0.0)),
                "r_squared": float(row.get("r_squared", 0.0)),
            }
        )
    return clean_rows


def _normalise_residual_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_residual_frame()
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"Residual factor frame is missing required columns: {', '.join(missing)}")
    clean = frame.copy()
    clean["date"] = pd.to_datetime(clean["date"])
    clean["asset_id"] = clean["asset_id"].astype(str)
    clean["market"] = clean["market"].fillna("CN").astype(str)
    clean["factor_name"] = clean["factor_name"].astype(str)
    clean["factor_value"] = pd.to_numeric(clean["factor_value"], errors="coerce")
    return clean.dropna(subset=required).reset_index(drop=True)


def _data_window(
    bars: pd.DataFrame,
    features: pd.DataFrame,
    signal_frame: pd.DataFrame,
    residual_frame: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "feature_rows": int(len(features)),
        "signal_rows": int(len(signal_frame)),
        "residual_rows": int(len(residual_frame)),
        "label_rows": int(len(labels)),
        "min_signal_date": _min_date(signal_frame, "date"),
        "max_signal_date": _max_date(signal_frame, "date"),
        "min_residual_date": _min_date(residual_frame, "date"),
        "max_residual_date": _max_date(residual_frame, "date"),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _empty_signal_frame(reference_factor_names: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "amount", "adv20_amount", "lead_value", *reference_factor_names]
    )


def _empty_residual_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "amount", "adv20_amount", "factor_name", "factor_value"]
    )
