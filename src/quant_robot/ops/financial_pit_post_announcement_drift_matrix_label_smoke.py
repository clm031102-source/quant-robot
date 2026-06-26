from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    SAFETY,
    _dedupe,
    _filter_date_window,
    _load_bars,
    _load_json,
    _next_trade_dates,
)
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "financial_pit_post_announcement_drift_matrix_label_smoke"
NEXT_ALLOWED_GATE = "round222_financial_pit_post_announcement_drift_residual_prescreen"
FORMULA_COLUMNS: dict[str, tuple[str, ...]] = {
    "pead_event_reaction_continuation_1_20": ("ann_date", "end_date", "signal_date"),
    "pead_event_gap_underreaction_1_20": ("ann_date", "end_date", "signal_date"),
    "pead_volume_disagreement_drift_1_20": ("ann_date", "end_date", "signal_date"),
    "pead_late_announcer_risk_reversal_5_20": ("ann_date", "end_date", "signal_date"),
    "pead_positive_fundamental_change_low_reaction_20": ("ann_date", "end_date", "signal_date", "netprofit_yoy"),
    "pead_negative_surprise_reaction_avoidance_20": ("ann_date", "end_date", "signal_date", "netprofit_yoy"),
    "pead_reaction_quality_residual_composite_20": ("ann_date", "end_date", "signal_date", "netprofit_yoy"),
    "pead_gap_overreaction_reversal_1_5": ("ann_date", "end_date", "signal_date"),
    "pead_gap_overreaction_reversal_volume_confirmed_1_5": ("ann_date", "end_date", "signal_date"),
    "pead_gap_overreaction_reversal_low_liquidity_penalized_1_5": ("ann_date", "end_date", "signal_date"),
    "pead_gap_overreaction_reversal_size_neutral_candidate_1_5": ("ann_date", "end_date", "signal_date"),
    "pead_gap_overreaction_reversal_quality_conditioned_1_5": ("ann_date", "end_date", "signal_date", "netprofit_yoy"),
}


def build_financial_pit_post_announcement_drift_matrix_label_smoke(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.60,
) -> dict[str, Any]:
    financial_path = Path(financial_root)
    financial = _prepare_financial(
        _filter_date_window(
            _load_fina_indicator_inputs(financial_path),
            start_date=analysis_start_date,
            end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            preferred_date_column="signal_date",
        )
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
    active_candidates, frozen_candidates = _split_candidates(preregistration, gate_packet)
    unknown_active = [candidate for candidate in active_candidates if candidate.get("factor_name") not in FORMULA_COLUMNS]
    factor_frame = compute_financial_pit_post_announcement_drift_factor_frame(financial, active_candidates, bars)
    label_input = _label_bars(bars)
    labels = make_forward_returns(label_input, horizons=tuple(horizons), execution_lag=execution_lag) if not label_input.empty else _empty_labels()
    aligned = _align_factor_values_to_labels(factor_frame, labels)
    alignment_violations = _alignment_violation_count(aligned)
    signal_rows = int(len(factor_frame))
    denominator = signal_rows * len(horizons)
    label_coverage = int(len(aligned)) / denominator if denominator else 0.0
    candidate_summaries = _candidate_summaries(active_candidates, factor_frame, aligned, tuple(horizons))

    blockers: list[str] = []
    if financial.empty:
        blockers.append("missing_financial_rows")
    if bars.empty:
        blockers.append("missing_bars")
    if not active_candidates:
        blockers.append("missing_active_candidates")
    if unknown_active:
        blockers.append("unknown_active_candidate_formula")
    if factor_frame.empty:
        blockers.append("missing_factor_values")
    if label_coverage < float(min_label_coverage):
        blockers.append("label_coverage_below_threshold")
    if alignment_violations:
        blockers.append("alignment_violation_rows")
    if not include_final_holdout and _after_end_date(factor_frame, "date", analysis_end_date):
        blockers.append("final_holdout_factor_dates_present")
    if not include_final_holdout and _after_end_date(labels, "date", analysis_end_date):
        blockers.append("final_holdout_label_dates_present")

    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(financial_path),
        "bars_roots": [str(Path(root)) for root in bars_roots],
        "preregistration_json": str(Path(preregistration_json)),
        "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
        "summary": {
            "passes": not blockers,
            "blockers": _dedupe(blockers),
            "active_candidate_count": int(len(active_candidates)),
            "frozen_candidate_count": int(len(frozen_candidates)),
            "unknown_active_candidate_count": int(len(unknown_active)),
            "financial_rows": int(len(financial)),
            "financial_assets": int(financial["asset_id"].nunique()) if "asset_id" in financial else 0,
            "bar_rows": int(len(bars)),
            "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
            "factor_value_rows": int(len(factor_frame)),
            "label_rows": int(len(labels)),
            "label_aligned_rows": int(len(aligned)),
            "label_coverage": float(label_coverage),
            "min_label_coverage": float(min_label_coverage),
            "alignment_violation_rows": int(alignment_violations),
            "horizons": list(horizons),
            "execution_lag": int(execution_lag),
            "min_signal_date": _date_min(factor_frame, "signal_date"),
            "max_signal_date": _date_max(factor_frame, "signal_date"),
            "min_factor_date": _date_min(factor_frame, "date"),
            "max_factor_date": _date_max(factor_frame, "date"),
            "min_label_date": _date_min(labels, "date"),
            "max_label_date": _date_max(labels, "date"),
            "next_allowed_gate": NEXT_ALLOWED_GATE,
        },
        "active_candidates": [_candidate_brief(candidate) for candidate in active_candidates],
        "frozen_candidates": [_candidate_brief(candidate) for candidate in frozen_candidates],
        "unknown_active_candidates": [_candidate_brief(candidate) for candidate in unknown_active],
        "candidate_summaries": candidate_summaries,
        "factor_matrix_sample_rows": _sample_factor_rows(factor_frame),
        "alignment_policy": {
            "announcement_signal_rule": "signal_date must be strictly after ann_date",
            "event_reaction_date_rule": "event reaction is measured on signal_date only after announcement availability",
            "factor_date_rule": "factor date equals first trade date strictly after event_reaction_date",
            "same_day_announcement_trading_allowed": False,
            "same_day_event_reaction_trading_allowed": False,
            "entry_date_rule": "forward label entry date must be strictly after factor date",
            "execution_lag": int(execution_lag),
        },
        "holdout_policy": {
            "analysis_start_date": str(analysis_start_date),
            "analysis_end_date": str(analysis_end_date),
            "final_holdout_included": bool(include_final_holdout),
            "final_holdout_start": "2026-01-01",
            "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed": False,
            "paper_ready_allowed": False,
            "profitability_claim_allowed": False,
            "next_allowed_action": NEXT_ALLOWED_GATE,
            "requires_residual_ic_shape_prescreen": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_post_announcement_drift_matrix_label_smoke_markdown(result)
    return result


def compute_financial_pit_post_announcement_drift_factor_frame(
    financial: pd.DataFrame,
    candidates: list[dict[str, Any]],
    bars: pd.DataFrame,
) -> pd.DataFrame:
    if financial.empty or bars.empty or not candidates:
        return _empty_factor_frame()
    frame = _prepare_financial(financial)
    bar_features = _event_bar_features(bars)
    frame["event_reaction_date"] = pd.to_datetime(frame["signal_date"], errors="coerce")
    frame["reaction_available_date"] = _next_trade_dates(frame, bar_features, "event_reaction_date")
    frame = frame.dropna(subset=["asset_id", "ann_date", "event_reaction_date", "reaction_available_date"]).copy()
    frame = frame[
        (frame["event_reaction_date"] > frame["ann_date"])
        & (frame["reaction_available_date"] > frame["event_reaction_date"])
    ].reset_index(drop=True)
    if frame.empty:
        return _empty_factor_frame()
    event_features = bar_features.rename(columns={"date": "event_reaction_date"})
    frame = frame.merge(
        event_features,
        on=["asset_id", "market", "event_reaction_date"],
        how="left",
    )
    frame = _add_financial_features(frame)
    pieces: list[pd.DataFrame] = []
    for candidate in candidates:
        name = str(candidate.get("factor_name", ""))
        formula = _formula_functions().get(name)
        if formula is None:
            continue
        required = FORMULA_COLUMNS[name]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            continue
        values = pd.to_numeric(formula(frame), errors="coerce")
        piece = pd.DataFrame(
            {
                "date": frame["reaction_available_date"],
                "ann_date": frame["ann_date"],
                "end_date": frame["end_date"],
                "signal_date": frame["signal_date"],
                "event_reaction_date": frame["event_reaction_date"],
                "reaction_available_date": frame["reaction_available_date"],
                "asset_id": frame["asset_id"],
                "market": frame["market"],
                "factor_name": name,
                "factor_value": values,
            }
        ).dropna(subset=["date", "ann_date", "asset_id", "factor_value"])
        pieces.append(piece)
    if not pieces:
        return _empty_factor_frame()
    output = pd.concat(pieces, ignore_index=True)
    return output.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def write_financial_pit_post_announcement_drift_matrix_label_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_pit_post_announcement_drift_matrix_label_smoke.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_drift_matrix_label_smoke.md").write_text(
        render_financial_pit_post_announcement_drift_matrix_label_smoke_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_drift_matrix_candidate_summary.csv",
        result.get("candidate_summaries", []) or [],
    )


def render_financial_pit_post_announcement_drift_matrix_label_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Drift Matrix Label Smoke",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Active candidates: {summary.get('active_candidate_count', 0)}",
        f"- Frozen candidates: {summary.get('frozen_candidate_count', 0)}",
        f"- Unknown active candidates: {summary.get('unknown_active_candidate_count', 0)}",
        f"- Financial rows: {summary.get('financial_rows', 0)}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Factor value rows: {summary.get('factor_value_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Label aligned rows: {summary.get('label_aligned_rows', 0)}",
        f"- Label coverage: {float(summary.get('label_coverage', 0.0)):.2%}",
        f"- Alignment violations: {summary.get('alignment_violation_rows', 0)}",
        f"- Max signal date: {summary.get('max_signal_date')}",
        f"- Max factor date: {summary.get('max_factor_date')}",
        f"- Max label date: {summary.get('max_label_date')}",
        f"- Horizons: {', '.join(str(item) for item in summary.get('horizons', []) or [])}",
        f"- Next allowed gate: `{summary.get('next_allowed_gate', NEXT_ALLOWED_GATE)}`",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Summary",
        "",
        "| Factor | Factor Rows | Label Rows | Label Coverage | Violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result.get("candidate_summaries", []) or []:
        lines.append(
            "| {factor} | {factor_rows} | {label_rows} | {coverage:.2%} | {violations} |".format(
                factor=row.get("factor_name", ""),
                factor_rows=int(row.get("factor_value_rows", 0)),
                label_rows=int(row.get("label_aligned_rows", 0)),
                coverage=float(row.get("label_coverage", 0.0)),
                violations=int(row.get("alignment_violation_rows", 0)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a factor-matrix and label-alignment smoke only.",
            "- It does not compute IC, Sharpe, profit rate, win rate, total return, or drawdown.",
            "- Event-day reaction is only used on the next tradable factor date; same-day event trading is blocked.",
            "- Promotion and portfolio grids remain blocked until residual IC shape, walk-forward, cost, capacity, and regime gates pass.",
        ]
    )
    return "\n".join(lines) + "\n"


def _prepare_financial(financial: pd.DataFrame) -> pd.DataFrame:
    if financial.empty:
        return financial.copy()
    frame = financial.copy()
    for column in ["date", "ann_date", "end_date", "available_date", "signal_date"]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "signal_date" not in frame and "available_date" in frame:
        frame["signal_date"] = frame["available_date"]
    for column in ["asset_id", "market"]:
        if column not in frame:
            frame[column] = "CN" if column == "market" else ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["netprofit_yoy", "or_yoy", "roe", "ocfps", "netprofit_margin"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)


def _event_bar_features(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "event_return",
                "event_gap",
                "volume_surprise",
                "event_amount",
            ]
        )
    required = ["date", "asset_id", "market", "open", "close", "adj_close", "volume", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for PEAD event features: {', '.join(missing)}")
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["open", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame[(frame["market"] == "CN") & frame["date"].notna()]
        .drop_duplicates(["asset_id", "date", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )
    grouped = frame.groupby("asset_id", sort=False)
    frame["prev_close"] = grouped["close"].shift(1)
    frame["volume_base"] = grouped["volume"].transform(lambda item: item.shift(1).rolling(20, min_periods=1).median())
    frame["event_return"] = frame["close"] / frame["open"] - 1.0
    frame["event_gap"] = frame["open"] / frame["prev_close"] - 1.0
    frame["volume_surprise"] = frame["volume"] / frame["volume_base"].where(frame["volume_base"] > 0) - 1.0
    frame["event_amount"] = frame["amount"]
    return frame[["date", "asset_id", "market", "event_return", "event_gap", "volume_surprise", "event_amount"]]


def _add_financial_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.sort_values(["asset_id", "end_date", "ann_date"]).copy()
    if "netprofit_yoy" in output:
        delta = output["netprofit_yoy"] - output.groupby("asset_id")["netprofit_yoy"].shift(1)
        output["fundamental_delta"] = delta.fillna(output["netprofit_yoy"])
    else:
        output["fundamental_delta"] = 0.0
    output["announcement_lag_days"] = (output["signal_date"] - output["end_date"]).dt.days
    output["event_amount_rank"] = output.groupby("event_reaction_date")["event_amount"].rank(pct=True).fillna(0.5)
    return output


def _formula_functions() -> dict[str, Callable[[pd.DataFrame], pd.Series]]:
    return {
        "pead_event_reaction_continuation_1_20": lambda frame: frame["event_return"],
        "pead_event_gap_underreaction_1_20": lambda frame: frame["event_gap"],
        "pead_volume_disagreement_drift_1_20": lambda frame: frame["event_return"]
        / (1.0 + frame["volume_surprise"].abs()),
        "pead_late_announcer_risk_reversal_5_20": lambda frame: -frame["announcement_lag_days"],
        "pead_positive_fundamental_change_low_reaction_20": lambda frame: _zscore_series_by_period(
            frame,
            frame["fundamental_delta"],
        )
        - frame["event_return"].abs(),
        "pead_negative_surprise_reaction_avoidance_20": lambda frame: frame["fundamental_delta"].clip(upper=0.0)
        + frame["event_return"].clip(upper=0.0),
        "pead_reaction_quality_residual_composite_20": _reaction_quality_residual_composite,
        "pead_gap_overreaction_reversal_1_5": lambda frame: -frame["event_gap"],
        "pead_gap_overreaction_reversal_volume_confirmed_1_5": lambda frame: -frame["event_gap"]
        * (1.0 + frame["volume_surprise"].abs()),
        "pead_gap_overreaction_reversal_low_liquidity_penalized_1_5": lambda frame: -frame["event_gap"]
        / (1.0 + frame["volume_surprise"].abs()),
        "pead_gap_overreaction_reversal_size_neutral_candidate_1_5": lambda frame: -frame["event_gap"]
        * (1.0 - 0.25 * (frame["event_amount_rank"] - 0.5)),
        "pead_gap_overreaction_reversal_quality_conditioned_1_5": lambda frame: -frame["event_gap"]
        + 0.2 * _zscore_series_by_period(frame, frame["fundamental_delta"]),
    }


def _reaction_quality_residual_composite(frame: pd.DataFrame) -> pd.Series:
    return (
        0.4 * _zscore_series_by_period(frame, frame["event_return"])
        + 0.4 * _zscore_series_by_period(frame, frame["fundamental_delta"])
        - 0.2 * _zscore_series_by_period(frame, frame["volume_surprise"].abs())
    )


def _zscore_series_by_period(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    grouped = values.groupby(frame["end_date"])
    mean = grouped.transform("mean")
    std = grouped.transform("std").replace(0, pd.NA)
    return (values - mean) / std


def _label_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "adj_close"])
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for forward returns: {', '.join(missing)}")
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["asset_id", "date", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _split_candidates(
    preregistration: dict[str, Any],
    gate_packet: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = [candidate for candidate in preregistration.get("candidates", []) or [] if isinstance(candidate, dict)]
    by_name = {str(candidate.get("factor_name", "")): candidate for candidate in candidates}
    gate_rows = [row for row in gate_packet.get("candidate_rows", []) or [] if isinstance(row, dict)]
    if gate_rows:
        active_names = {str(row.get("factor_name", "")) for row in gate_rows if row.get("active_for_gate") is True}
        frozen_names = {str(row.get("factor_name", "")) for row in gate_rows if row.get("active_for_gate") is not True}
        active = [by_name[name] for name in active_names if name in by_name]
        frozen = [by_name[name] for name in frozen_names if name in by_name]
        return sorted(active, key=lambda item: str(item.get("factor_name", ""))), sorted(
            frozen,
            key=lambda item: str(item.get("factor_name", "")),
        )
    active = [candidate for candidate in candidates if candidate.get("registration_status") in {"pre_registered", "registered"}]
    frozen = [candidate for candidate in candidates if candidate not in active]
    return active, frozen


def _align_factor_values_to_labels(factor_frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty or labels.empty:
        return pd.DataFrame()
    label_frame = labels.rename(columns={"date": "factor_date"}).copy()
    label_frame["factor_date"] = pd.to_datetime(label_frame["factor_date"], errors="coerce")
    factors = factor_frame.rename(columns={"date": "factor_date"}).copy()
    factors["factor_date"] = pd.to_datetime(factors["factor_date"], errors="coerce")
    return factors.merge(label_frame, on=["factor_date", "asset_id", "market"], how="inner")


def _candidate_summaries(
    candidates: list[dict[str, Any]],
    factor_frame: pd.DataFrame,
    aligned: pd.DataFrame,
    horizons: tuple[int, ...],
) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        name = str(candidate.get("factor_name", ""))
        factor_slice = factor_frame[factor_frame["factor_name"] == name] if not factor_frame.empty else pd.DataFrame()
        aligned_slice = aligned[aligned["factor_name"] == name] if not aligned.empty else pd.DataFrame()
        denominator = int(len(factor_slice)) * len(horizons)
        rows.append(
            {
                "factor_name": name,
                "registration_status": str(candidate.get("registration_status", "")),
                "formula_implemented": name in FORMULA_COLUMNS,
                "factor_value_rows": int(len(factor_slice)),
                "label_aligned_rows": int(len(aligned_slice)),
                "label_coverage": float(len(aligned_slice) / denominator) if denominator else 0.0,
                "alignment_violation_rows": int(_alignment_violation_count(aligned_slice)),
            }
        )
    return rows


def _alignment_violation_count(aligned: pd.DataFrame) -> int:
    if aligned.empty:
        return 0
    factor_dates = pd.to_datetime(aligned["factor_date"], errors="coerce")
    ann_dates = pd.to_datetime(aligned["ann_date"], errors="coerce")
    signal_dates = pd.to_datetime(aligned["signal_date"], errors="coerce")
    event_dates = pd.to_datetime(aligned["event_reaction_date"], errors="coerce")
    reaction_available_dates = pd.to_datetime(aligned["reaction_available_date"], errors="coerce")
    entry_dates = pd.to_datetime(aligned["entry_date"], errors="coerce")
    exit_dates = pd.to_datetime(aligned["exit_date"], errors="coerce")
    violations = (
        (signal_dates <= ann_dates)
        | (event_dates <= ann_dates)
        | (reaction_available_dates <= event_dates)
        | (factor_dates != reaction_available_dates)
        | (entry_dates <= factor_dates)
        | (exit_dates <= entry_dates)
    )
    return int(violations.sum())


def _empty_labels() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "horizon", "execution_lag", "forward_return", "entry_date", "exit_date"]
    )


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "ann_date",
            "end_date",
            "signal_date",
            "event_reaction_date",
            "reaction_available_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
        ]
    )


def _candidate_brief(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "factor_name": str(candidate.get("factor_name", "")),
        "family": str(candidate.get("family", "")),
        "registration_status": str(candidate.get("registration_status", "")),
        "portfolio_backtest_allowed": bool(candidate.get("portfolio_backtest_allowed")),
        "promotion_allowed": bool(candidate.get("promotion_allowed")),
    }


def _sample_factor_rows(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    sample = frame.head(limit).copy()
    for column in ["date", "ann_date", "end_date", "signal_date", "event_reaction_date", "reaction_available_date"]:
        if column in sample:
            sample[column] = pd.to_datetime(sample[column], errors="coerce").dt.date.astype(str)
    return sample.to_dict(orient="records")


def _after_end_date(frame: pd.DataFrame, column: str, end_date: str) -> bool:
    if frame.empty or column not in frame:
        return False
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return bool((values > pd.Timestamp(end_date)).any()) if not values.empty else False


def _date_min(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return values.min().date().isoformat() if not values.empty else None


def _date_max(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return values.max().date().isoformat() if not values.empty else None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
