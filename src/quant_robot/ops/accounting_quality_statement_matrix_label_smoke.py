from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.accounting_quality_statement_formula_smoke import (
    FORMULA_SPECS,
    STATEMENT_KEY_COLUMNS,
    _add_formula_values,
    _date_max,
    _date_min,
    _nunique,
    _prepare_statement_frame,
    _read_frame,
    _statement_files,
)
from quant_robot.ops.financial_pit_timing_audit import _load_bars, _signal_dates_strictly_after_ann_date
from quant_robot.research.labels import make_forward_returns


STAGE = "accounting_quality_statement_matrix_label_smoke"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_ALLOWED_GATE = "accounting_quality_statement_residual_ic_shape_prescreen"


def build_accounting_quality_statement_matrix_label_smoke(
    *,
    statement_roots: Iterable[str | Path],
    bars_roots: Iterable[str | Path],
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.60,
    deduplicate: bool = True,
) -> dict[str, Any]:
    statement_root_paths = [Path(root) for root in statement_roots]
    bars_root_paths = [Path(root) for root in bars_roots]
    statement = _load_statement_inputs(statement_root_paths, deduplicate=deduplicate)
    assets = sorted(statement["asset_id"].dropna().astype(str).unique()) if "asset_id" in statement else []
    bars = _load_bars(bars_root_paths, assets)
    factor_frame = _filter_date_window(
        _compute_factor_frame_from_inputs(statement, bars),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        date_column="date",
    )
    label_bars = _filter_date_window(
        bars,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        date_column="date",
    )
    labels = make_forward_returns(label_bars, horizons=tuple(horizons), execution_lag=int(execution_lag)) if not label_bars.empty else _empty_labels()
    aligned = _align_factor_values_to_labels(factor_frame, labels)
    signal_rows = int(len(factor_frame))
    denominator = signal_rows * len(horizons)
    label_coverage = float(len(aligned) / denominator) if denominator else 0.0
    alignment_violations = _alignment_violation_count(aligned)
    blockers = _blockers(
        statement=statement,
        bars=bars,
        factor_frame=factor_frame,
        label_coverage=label_coverage,
        min_label_coverage=min_label_coverage,
        alignment_violations=alignment_violations,
        duplicate_key_rows=int(statement.attrs.get("duplicate_key_rows_asset_end_ann_report_type", 0)),
        deduplicate=deduplicate,
        include_final_holdout=include_final_holdout,
        analysis_end_date=analysis_end_date,
        labels=labels,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "statement_roots": [str(root) for root in statement_root_paths],
        "bars_roots": [str(root) for root in bars_root_paths],
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "statement_rows": int(len(statement)),
            "statement_assets": _nunique(statement, "asset_id"),
            "duplicate_key_rows_asset_end_ann_report_type": int(
                statement.attrs.get("duplicate_key_rows_asset_end_ann_report_type", 0)
            ),
            "bar_rows": int(len(bars)),
            "bar_assets": _nunique(bars, "asset_id"),
            "factor_count": len(FORMULA_SPECS),
            "factor_value_rows": int(len(factor_frame)),
            "label_rows": int(len(labels)),
            "label_aligned_rows": int(len(aligned)),
            "label_coverage": label_coverage,
            "min_label_coverage": float(min_label_coverage),
            "alignment_violation_rows": int(alignment_violations),
            "horizons": list(horizons),
            "execution_lag": int(execution_lag),
            "min_ann_date": _date_min(factor_frame, "ann_date"),
            "max_ann_date": _date_max(factor_frame, "ann_date"),
            "min_signal_date": _date_min(factor_frame, "signal_date"),
            "max_signal_date": _date_max(factor_frame, "signal_date"),
            "min_label_date": _date_min(labels, "date"),
            "max_label_date": _date_max(labels, "date"),
            "next_allowed_gate": NEXT_ALLOWED_GATE,
        },
        "candidate_summaries": _candidate_summaries(factor_frame, aligned, tuple(horizons)),
        "factor_matrix_sample_rows": _sample_factor_rows(factor_frame),
        "alignment_policy": {
            "signal_date_rule": "first_trade_date_strictly_after_ann_date",
            "same_day_announcement_trading_allowed": False,
            "entry_date_rule": "forward label entry date must be strictly after signal_date",
            "execution_lag": int(execution_lag),
        },
        "holdout_policy": {
            "analysis_start_date": str(analysis_start_date),
            "analysis_end_date": str(analysis_end_date),
            "final_holdout_included": bool(include_final_holdout),
            "final_holdout_start": "2026-01-01",
            "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
        },
        "execution_policy": {
            "return_labels_used": True,
            "ic_calculated": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "final_holdout_touched": bool(include_final_holdout),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "paper_ready_allowed": False,
            "portfolio_backtest_allowed": False,
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
    result["markdown"] = render_accounting_quality_statement_matrix_label_smoke_markdown(result)
    return result


def compute_accounting_quality_statement_factor_frame(
    *,
    statement_roots: Iterable[str | Path],
    bars_roots: Iterable[str | Path],
    deduplicate: bool = True,
) -> pd.DataFrame:
    statement_root_paths = [Path(root) for root in statement_roots]
    bars_root_paths = [Path(root) for root in bars_roots]
    statement = _load_statement_inputs(statement_root_paths, deduplicate=deduplicate)
    assets = sorted(statement["asset_id"].dropna().astype(str).unique()) if "asset_id" in statement else []
    bars = _load_bars(bars_root_paths, assets)
    return _compute_factor_frame_from_inputs(statement, bars)


def write_accounting_quality_statement_matrix_label_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "accounting_quality_statement_matrix_label_smoke.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "accounting_quality_statement_matrix_label_smoke.md").write_text(
        render_accounting_quality_statement_matrix_label_smoke_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "accounting_quality_statement_matrix_candidate_summary.csv",
        result.get("candidate_summaries", []) or [],
    )


def render_accounting_quality_statement_matrix_label_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Accounting Quality Statement Matrix Label Smoke",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Statement rows: {summary.get('statement_rows', 0)}",
        f"- Statement assets: {summary.get('statement_assets', 0)}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Factor value rows: {summary.get('factor_value_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Label aligned rows: {summary.get('label_aligned_rows', 0)}",
        f"- Label coverage: {float(summary.get('label_coverage', 0.0)):.2%}",
        f"- Alignment violations: {summary.get('alignment_violation_rows', 0)}",
        f"- Max ann date: {summary.get('max_ann_date')}",
        f"- Max signal date: {summary.get('max_signal_date')}",
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
            "- It does not compute IC, Sharpe, total return, profit rate, win rate, drawdown, or promotion evidence.",
            "- Statement factors are dated on the first tradable date strictly after `ann_date`; same-day announcement trading is blocked.",
            "- Promotion and portfolio grids remain blocked until residual IC shape, walk-forward, cost, capacity, and regime gates pass.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_statement_inputs(roots: list[Path], *, deduplicate: bool) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for root in roots:
        for path in _statement_files(root):
            frames.append(_read_frame(path))
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    statement = _prepare_statement_frame(combined)
    duplicate_key_rows = int(statement.duplicated(STATEMENT_KEY_COLUMNS).sum()) if set(STATEMENT_KEY_COLUMNS).issubset(statement.columns) else 0
    if deduplicate and set(STATEMENT_KEY_COLUMNS).issubset(statement.columns):
        statement = statement.drop_duplicates(STATEMENT_KEY_COLUMNS, keep="last").reset_index(drop=True)
    statement.attrs["duplicate_key_rows_asset_end_ann_report_type"] = duplicate_key_rows
    return statement


def _compute_factor_frame_from_inputs(statement: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if statement.empty or bars.empty:
        return _empty_factor_frame()
    frame = _add_formula_values(statement)
    frame["signal_date"] = _signal_dates_strictly_after_ann_date(frame, bars)
    frame = frame.dropna(subset=["asset_id", "ann_date", "signal_date"]).copy()
    frame = frame[pd.to_datetime(frame["signal_date"], errors="coerce") > pd.to_datetime(frame["ann_date"], errors="coerce")]
    if frame.empty:
        return _empty_factor_frame()
    pieces: list[pd.DataFrame] = []
    for spec in FORMULA_SPECS:
        name = str(spec["factor_name"])
        if name not in frame:
            continue
        values = pd.to_numeric(frame[name], errors="coerce").replace([float("inf"), float("-inf")], pd.NA)
        piece = pd.DataFrame(
            {
                "date": frame["signal_date"],
                "ann_date": frame["ann_date"],
                "end_date": frame["end_date"],
                "signal_date": frame["signal_date"],
                "asset_id": frame["asset_id"],
                "market": frame.get("market", "CN"),
                "factor_name": name,
                "factor_value": values,
            }
        ).dropna(subset=["date", "ann_date", "asset_id", "factor_value"])
        pieces.append(piece)
    if not pieces:
        return _empty_factor_frame()
    output = pd.concat(pieces, ignore_index=True)
    for column in ["date", "ann_date", "end_date", "signal_date"]:
        output[column] = pd.to_datetime(output[column], errors="coerce")
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["asset_id"] = output["asset_id"].astype(str)
    return output.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _align_factor_values_to_labels(factor_frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty or labels.empty:
        return pd.DataFrame()
    label_frame = labels.rename(columns={"date": "factor_date"}).copy()
    label_frame["factor_date"] = pd.to_datetime(label_frame["factor_date"], errors="coerce")
    factors = factor_frame.rename(columns={"date": "factor_date"}).copy()
    factors["factor_date"] = pd.to_datetime(factors["factor_date"], errors="coerce")
    return factors.merge(label_frame, on=["factor_date", "asset_id", "market"], how="inner")


def _candidate_summaries(factor_frame: pd.DataFrame, aligned: pd.DataFrame, horizons: tuple[int, ...]) -> list[dict[str, Any]]:
    rows = []
    for spec in FORMULA_SPECS:
        name = str(spec["factor_name"])
        factor_slice = factor_frame[factor_frame["factor_name"] == name] if not factor_frame.empty else pd.DataFrame()
        aligned_slice = aligned[aligned["factor_name"] == name] if not aligned.empty else pd.DataFrame()
        denominator = int(len(factor_slice)) * len(horizons)
        rows.append(
            {
                "factor_name": name,
                "factor_value_rows": int(len(factor_slice)),
                "label_aligned_rows": int(len(aligned_slice)),
                "label_coverage": float(len(aligned_slice) / denominator) if denominator else 0.0,
                "alignment_violation_rows": _alignment_violation_count(aligned_slice),
            }
        )
    return rows


def _alignment_violation_count(aligned: pd.DataFrame) -> int:
    if aligned.empty:
        return 0
    factor_dates = pd.to_datetime(aligned["factor_date"], errors="coerce")
    ann_dates = pd.to_datetime(aligned["ann_date"], errors="coerce")
    signal_dates = pd.to_datetime(aligned["signal_date"], errors="coerce")
    entry_dates = pd.to_datetime(aligned["entry_date"], errors="coerce")
    exit_dates = pd.to_datetime(aligned["exit_date"], errors="coerce")
    violations = (signal_dates <= ann_dates) | (factor_dates != signal_dates) | (entry_dates <= signal_dates) | (exit_dates <= entry_dates)
    return int(violations.sum())


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


def _blockers(
    *,
    statement: pd.DataFrame,
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    label_coverage: float,
    min_label_coverage: float,
    alignment_violations: int,
    duplicate_key_rows: int,
    deduplicate: bool,
    include_final_holdout: bool,
    analysis_end_date: str,
    labels: pd.DataFrame,
) -> list[str]:
    blockers: list[str] = []
    if statement.empty:
        blockers.append("missing_statement_rows")
    if bars.empty:
        blockers.append("missing_bars")
    if factor_frame.empty:
        blockers.append("missing_factor_values")
    if duplicate_key_rows and not deduplicate:
        blockers.append("duplicate_statement_keys")
    if label_coverage < float(min_label_coverage):
        blockers.append("label_coverage_below_threshold")
    if alignment_violations:
        blockers.append("alignment_violation_rows")
    if not include_final_holdout and _after_end_date(factor_frame, "date", analysis_end_date):
        blockers.append("final_holdout_factor_dates_present")
    if not include_final_holdout and _after_end_date(labels, "date", analysis_end_date):
        blockers.append("final_holdout_label_dates_present")
    return _dedupe(blockers)


def _after_end_date(frame: pd.DataFrame, column: str, end_date: str) -> bool:
    if frame.empty or column not in frame:
        return False
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return bool((values > pd.Timestamp(end_date)).any()) if not values.empty else False


def _empty_labels() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "horizon", "execution_lag", "forward_return", "entry_date", "exit_date"]
    )


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "ann_date", "end_date", "signal_date", "asset_id", "market", "factor_name", "factor_value"]
    )


def _sample_factor_rows(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    sample = frame.head(limit).copy()
    for column in ["date", "ann_date", "end_date", "signal_date"]:
        if column in sample:
            sample[column] = pd.to_datetime(sample[column], errors="coerce").dt.date.astype(str)
    return sample.to_dict(orient="records")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
