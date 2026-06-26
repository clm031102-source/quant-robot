from __future__ import annotations

from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "profitability_event_revision_matrix_label_smoke"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_ALLOWED_GATE = "round153_pit_profitability_event_revision_controlled_ic_neutral_prescreen"
FORMULA_COLUMNS: dict[str, tuple[str, ...]] = {
    "pit_fina_netprofit_yoy_revision_1q": ("netprofit_yoy",),
    "pit_fina_revenue_profit_revision_spread_1q": ("netprofit_yoy", "or_yoy"),
    "pit_fina_margin_revision_yoy_4q": ("netprofit_margin",),
    "pit_fina_roe_revision_persistence_4q": ("roe",),
    "pit_fina_cash_profit_revision_4q": ("ocfps", "netprofit_yoy", "or_yoy"),
    "pit_fina_cash_earnings_confirmation_1q": ("netprofit_yoy", "ocfps", "cfps"),
    "pit_fina_quality_surprise_blend_1q": ("roe", "netprofit_margin", "ocfps", "netprofit_yoy", "or_yoy"),
}


def build_profitability_event_revision_matrix_label_smoke(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.6,
) -> dict[str, Any]:
    financial = _load_fina_indicator_inputs(Path(financial_root))
    preregistration = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    gate_packet = _load_json(candidate_plan_gate_json)
    active_candidates, frozen_candidates = _split_candidates(preregistration, gate_packet)
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial.columns else []
    bars = _load_bars([Path(root) for root in bars_roots], assets)
    unknown_active = [candidate for candidate in active_candidates if candidate.get("factor_name") not in FORMULA_COLUMNS]
    factor_frame = compute_profitability_event_revision_factor_frame(financial, active_candidates, bars)
    labels = make_forward_returns(bars, horizons=tuple(horizons), execution_lag=execution_lag) if not bars.empty else _empty_labels()
    aligned = _align_factor_values_to_labels(factor_frame, labels)
    candidate_summaries = _candidate_summaries(active_candidates, factor_frame, aligned, tuple(horizons))
    signal_rows = int(len(factor_frame))
    denominator = signal_rows * len(horizons)
    label_coverage = int(len(aligned)) / denominator if denominator else 0.0
    alignment_violations = _alignment_violation_count(aligned)
    blockers: list[str] = []
    if financial.empty:
        blockers.append("missing_financial_rows")
    if bars.empty:
        blockers.append("missing_bars")
    if not active_candidates:
        blockers.append("missing_active_candidates")
    if unknown_active:
        blockers.append("unknown_active_candidate_formula")
    if label_coverage < min_label_coverage:
        blockers.append("label_coverage_below_threshold")
    if alignment_violations:
        blockers.append("alignment_violation_rows")
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(Path(financial_root)),
        "bars_roots": [str(Path(root)) for root in bars_roots],
        "preregistration_json": str(Path(preregistration_json)),
        "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
        "summary": {
            "passes": not blockers,
            "blockers": _dedupe(blockers),
            "active_candidate_count": len(active_candidates),
            "frozen_candidate_count": len(frozen_candidates),
            "unknown_active_candidate_count": len(unknown_active),
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
            "next_allowed_gate": NEXT_ALLOWED_GATE,
        },
        "active_candidates": [_candidate_brief(candidate) for candidate in active_candidates],
        "frozen_candidates": [_candidate_brief(candidate) for candidate in frozen_candidates],
        "unknown_active_candidates": [_candidate_brief(candidate) for candidate in unknown_active],
        "candidate_summaries": candidate_summaries,
        "alignment_policy": {
            "signal_date_rule": "first_trade_date_strictly_after_ann_date",
            "same_day_announcement_trading_allowed": False,
            "entry_date_rule": "forward label entry date must be strictly after signal date",
            "execution_lag": int(execution_lag),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed": False,
            "paper_ready_allowed": False,
            "profitability_claim_allowed": False,
            "next_allowed_action": NEXT_ALLOWED_GATE,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_profitability_event_revision_matrix_label_smoke_markdown(result)
    return result


def compute_profitability_event_revision_factor_frame(
    financial: pd.DataFrame,
    candidates: list[dict[str, Any]],
    bars: pd.DataFrame,
) -> pd.DataFrame:
    if financial.empty or bars.empty or not candidates:
        return _empty_factor_frame()
    frame = _normalise_financial(financial)
    signal_dates = _signal_dates_strictly_after_ann_date(frame, _normalise_bars(bars))
    frame["date"] = signal_dates
    frame = frame.dropna(subset=["date", "asset_id", "ann_date"]).reset_index(drop=True)
    if frame.empty:
        return _empty_factor_frame()
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
                "date": frame["date"],
                "ann_date": frame["ann_date"],
                "end_date": frame["end_date"],
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


def write_profitability_event_revision_matrix_label_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_event_revision_matrix_label_smoke.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_event_revision_matrix_label_smoke.md").write_text(
        render_profitability_event_revision_matrix_label_smoke_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "profitability_event_revision_matrix_candidate_summary.csv",
        result.get("candidate_summaries", []) or [],
    )


def render_profitability_event_revision_matrix_label_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# PIT Profitability Event Revision Matrix Label Smoke Round152",
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
            "- Signal dates must be strictly after `ann_date`; same-day announcement trading is blocked.",
        ]
    )
    return "\n".join(lines) + "\n"


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


def _normalise_financial(financial: pd.DataFrame) -> pd.DataFrame:
    frame = financial.copy()
    for column in ["date", "ann_date", "end_date"]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ["asset_id", "market"]:
        if column not in frame:
            frame[column] = "CN" if column == "market" else ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    numeric_columns = sorted({column for columns in FORMULA_COLUMNS.values() for column in columns})
    for column in numeric_columns:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "adj_close"])
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns: {', '.join(missing)}")
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _signal_dates_strictly_after_ann_date(financial: pd.DataFrame, bars: pd.DataFrame) -> pd.Series:
    bar_dates = {
        asset_id: pd.DatetimeIndex(group["date"].sort_values().dropna().unique())
        for asset_id, group in bars.groupby("asset_id")
    }
    signal_dates = []
    for row in financial.itertuples(index=False):
        dates = bar_dates.get(str(getattr(row, "asset_id")))
        ann_date = pd.Timestamp(getattr(row, "ann_date"))
        if dates is None or pd.isna(ann_date):
            signal_dates.append(pd.NaT)
            continue
        position = dates.searchsorted(ann_date, side="right")
        signal_dates.append(dates[position] if position < len(dates) else pd.NaT)
    return pd.Series(signal_dates, index=financial.index)


def _formula_functions() -> dict[str, Callable[[pd.DataFrame], pd.Series]]:
    return {
        "pit_fina_netprofit_yoy_revision_1q": lambda frame: frame["netprofit_yoy"]
        - frame.groupby("asset_id")["netprofit_yoy"].shift(1),
        "pit_fina_revenue_profit_revision_spread_1q": _revenue_profit_revision_spread,
        "pit_fina_margin_revision_yoy_4q": lambda frame: frame["netprofit_margin"]
        - frame.groupby("asset_id")["netprofit_margin"].shift(4),
        "pit_fina_roe_revision_persistence_4q": _roe_revision_persistence,
        "pit_fina_cash_profit_revision_4q": _cash_profit_revision,
        "pit_fina_cash_earnings_confirmation_1q": _cash_earnings_confirmation,
        "pit_fina_quality_surprise_blend_1q": _quality_surprise_blend,
    }


def _revenue_profit_revision_spread(frame: pd.DataFrame) -> pd.Series:
    spread = frame["netprofit_yoy"] - frame["or_yoy"]
    return spread - spread.groupby(frame["asset_id"]).shift(1)


def _roe_revision_persistence(frame: pd.DataFrame) -> pd.Series:
    grouped = frame.groupby("asset_id")["roe"]
    return (frame["roe"] - grouped.shift(4)) + 0.5 * grouped.transform(lambda item: item.rolling(4, min_periods=4).mean())


def _cash_profit_revision(frame: pd.DataFrame) -> pd.Series:
    delta_cash = frame["ocfps"] - frame.groupby("asset_id")["ocfps"].shift(4)
    spread_penalty = (frame["netprofit_yoy"] - frame["or_yoy"]).abs() * 0.25
    return delta_cash - spread_penalty


def _cash_earnings_confirmation(frame: pd.DataFrame) -> pd.Series:
    denominator = frame["cfps"].abs().where(frame["cfps"].abs() > 0)
    cash_ratio = frame["ocfps"] / denominator
    return _zscore_by_period(frame, "netprofit_yoy") + _zscore_series_by_period(frame, cash_ratio)


def _quality_surprise_blend(frame: pd.DataFrame) -> pd.Series:
    delta_roe = frame["roe"] - frame.groupby("asset_id")["roe"].shift(1)
    delta_margin = frame["netprofit_margin"] - frame.groupby("asset_id")["netprofit_margin"].shift(1)
    delta_ocfps = frame["ocfps"] - frame.groupby("asset_id")["ocfps"].shift(1)
    profit_spread = frame["netprofit_yoy"] - frame["or_yoy"]
    return (
        0.3 * _zscore_series_by_period(frame, delta_roe)
        + 0.3 * _zscore_series_by_period(frame, delta_margin)
        + 0.2 * _zscore_series_by_period(frame, delta_ocfps)
        + 0.2 * _zscore_series_by_period(frame, profit_spread)
    )


def _zscore_by_period(frame: pd.DataFrame, column: str) -> pd.Series:
    return _zscore_series_by_period(frame, frame[column])


def _zscore_series_by_period(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    grouped = values.groupby(frame["end_date"])
    mean = grouped.transform("mean")
    std = grouped.transform("std").replace(0, pd.NA)
    return (values - mean) / std


def _align_factor_values_to_labels(factor_frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty or labels.empty:
        return pd.DataFrame()
    label_frame = labels.rename(columns={"date": "signal_date"}).copy()
    label_frame["signal_date"] = pd.to_datetime(label_frame["signal_date"], errors="coerce")
    factors = factor_frame.rename(columns={"date": "signal_date"}).copy()
    return factors.merge(label_frame, on=["signal_date", "asset_id", "market"], how="inner")


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
    signal_dates = pd.to_datetime(aligned["signal_date"], errors="coerce")
    ann_dates = pd.to_datetime(aligned["ann_date"], errors="coerce")
    entry_dates = pd.to_datetime(aligned["entry_date"], errors="coerce")
    exit_dates = pd.to_datetime(aligned["exit_date"], errors="coerce")
    violations = (signal_dates <= ann_dates) | (entry_dates <= signal_dates) | (exit_dates <= entry_dates)
    return int(violations.sum())


def _load_bars(roots: list[Path], assets: list[str]) -> pd.DataFrame:
    frames = []
    columns = ["date", "asset_id", "market", "adj_close"]
    asset_set = set(assets)
    for root in roots:
        dataset_root = root / "processed" / "bars" / "frequency=1d" / "market=CN"
        if not dataset_root.exists():
            dataset_root = root
        for path in _dataset_files(dataset_root):
            frame = _read_frame(path, columns=columns)
            missing = [column for column in columns if column not in frame.columns]
            if missing:
                continue
            if asset_set:
                frame = frame[frame["asset_id"].astype(str).isin(asset_set)]
            if not frame.empty:
                frames.append(frame[columns])
    if not frames:
        return pd.DataFrame(columns=columns)
    return _normalise_bars(pd.concat(frames, ignore_index=True))


def _dataset_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() in {".parquet", ".csv"}:
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".parquet", ".csv"})


def _read_frame(path: Path, columns: list[str]) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        try:
            return pd.read_parquet(path, columns=columns)
        except Exception:
            return pd.read_parquet(path)
    return pd.read_csv(path)


def _empty_labels() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "horizon", "execution_lag", "forward_return", "entry_date", "exit_date"]
    )


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "ann_date", "end_date", "asset_id", "market", "factor_name", "factor_value"])


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate_brief(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "factor_name": str(candidate.get("factor_name", "")),
        "family": str(candidate.get("family", "")),
        "registration_status": str(candidate.get("registration_status", "")),
        "portfolio_backtest_allowed": bool(candidate.get("portfolio_backtest_allowed")),
        "promotion_allowed": bool(candidate.get("promotion_allowed")),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
