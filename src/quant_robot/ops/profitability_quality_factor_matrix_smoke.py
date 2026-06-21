from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "profitability_quality_factor_matrix_smoke"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_profitability_quality_factor_matrix_smoke(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.6,
) -> dict[str, Any]:
    financial = _load_fina_indicator_inputs(Path(financial_root))
    preregistration = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [
        candidate
        for candidate in preregistration.get("candidates", []) or []
        if candidate.get("registration_status") == "pre_registered"
    ]
    assets = sorted(financial["asset_id"].dropna().unique()) if "asset_id" in financial.columns else []
    bars = _load_bars([Path(root) for root in bars_roots], assets)
    labels = make_forward_returns(bars, horizons=tuple(horizons), execution_lag=execution_lag) if not bars.empty else _empty_labels()
    event_frame = _event_frame(financial, bars)
    factor_values = _factor_values(financial, candidates)
    aligned = _align_factor_values_to_labels(factor_values, event_frame, labels)
    candidate_summaries = _candidate_summaries(candidates, factor_values, event_frame, aligned, horizons)
    label_denominator = int(event_frame["has_signal_date"].sum()) * len(candidates) * len(horizons)
    label_coverage = len(aligned) / label_denominator if label_denominator else 0.0
    alignment_violations = _alignment_violation_count(aligned)
    blockers: list[str] = []
    if financial.empty:
        blockers.append("missing_financial_rows")
    if not candidates:
        blockers.append("missing_preregistered_candidates")
    if bars.empty:
        blockers.append("missing_bars")
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
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "financial_event_rows": int(len(event_frame)),
            "events_with_signal_date": int(event_frame["has_signal_date"].sum()) if "has_signal_date" in event_frame else 0,
            "factor_value_rows": int(len(factor_values)),
            "label_aligned_rows": int(len(aligned)),
            "label_coverage": label_coverage,
            "min_label_coverage": min_label_coverage,
            "alignment_violation_rows": alignment_violations,
            "horizons": list(horizons),
            "execution_lag": execution_lag,
            "bar_rows": int(len(bars)),
            "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        },
        "candidate_summaries": candidate_summaries,
        "promotion_policy": {
            "promotion_allowed": False,
            "paper_ready_allowed": False,
            "backtest_claim_allowed": False,
            "next_allowed_action": "If this smoke passes, run a controlled IC screen with multiple-testing accounting.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_profitability_quality_factor_matrix_smoke_markdown(result)
    return result


def write_profitability_quality_factor_matrix_smoke(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_quality_factor_matrix_smoke.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_quality_factor_matrix_smoke.md").write_text(
        render_profitability_quality_factor_matrix_smoke_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("candidate_summaries", []) or []).to_csv(
        output_path / "profitability_quality_factor_matrix_candidate_summary.csv",
        index=False,
    )


def render_profitability_quality_factor_matrix_smoke_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Profitability Quality Factor Matrix Smoke",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Financial events: {summary.get('financial_event_rows', 0)}",
        f"- Events with signal date: {summary.get('events_with_signal_date', 0)}",
        f"- Factor value rows: {summary.get('factor_value_rows', 0)}",
        f"- Label aligned rows: {summary.get('label_aligned_rows', 0)}",
        f"- Label coverage: {float(summary.get('label_coverage', 0.0)):.2%}",
        f"- Alignment violations: {summary.get('alignment_violation_rows', 0)}",
        f"- Horizons: {', '.join(str(item) for item in summary.get('horizons', []) or [])}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidate Summary",
        "",
        "| Name | Factor Rows | Signal Rows | Label Rows | Label Coverage | Violations |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result.get("candidate_summaries", []) or []:
        lines.append(
            "| {name} | {factor_rows} | {signal_rows} | {label_rows} | {coverage:.2%} | {violations} |".format(
                name=row["name"],
                factor_rows=row["factor_value_rows"],
                signal_rows=row["signal_rows"],
                label_rows=row["label_aligned_rows"],
                coverage=float(row["label_coverage"]),
                violations=row["alignment_violation_rows"],
            )
        )
    return "\n".join(lines) + "\n"


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
                frame = frame[frame["asset_id"].isin(asset_set)]
            if not frame.empty:
                frames.append(frame[columns])
    if not frames:
        return pd.DataFrame(columns=columns)
    bars = pd.concat(frames, ignore_index=True)
    bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
    bars = bars.dropna(subset=["date", "asset_id", "adj_close"])
    bars = bars.drop_duplicates(["asset_id", "date"], keep="last")
    return bars.sort_values(["asset_id", "date"]).reset_index(drop=True)


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


def _event_frame(financial: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if financial.empty:
        return pd.DataFrame(columns=["event_id", "asset_id", "ann_date", "end_date", "signal_date", "has_signal_date"])
    events = financial[["asset_id", "ann_date", "end_date"]].copy()
    events["event_id"] = range(len(events))
    events["ann_date"] = pd.to_datetime(events["ann_date"], errors="coerce")
    events["end_date"] = pd.to_datetime(events["end_date"], errors="coerce")
    bar_dates = {
        asset_id: pd.DatetimeIndex(group["date"].sort_values().dropna().unique())
        for asset_id, group in bars.groupby("asset_id")
    }
    signal_dates = []
    for row in events.itertuples(index=False):
        dates = bar_dates.get(row.asset_id)
        if dates is None or pd.isna(row.ann_date):
            signal_dates.append(pd.NaT)
            continue
        position = dates.searchsorted(row.ann_date, side="left")
        signal_dates.append(dates[position] if position < len(dates) else pd.NaT)
    events["signal_date"] = signal_dates
    events["has_signal_date"] = events["signal_date"].notna()
    return events


def _factor_values(financial: pd.DataFrame, candidates: list[dict[str, Any]]) -> pd.DataFrame:
    if financial.empty or not candidates:
        return pd.DataFrame(columns=["event_id", "asset_id", "factor_name", "factor_value"])
    frame = financial.reset_index(drop=True).copy()
    frame["event_id"] = range(len(frame))
    rows = []
    for candidate in candidates:
        values = _calculate_candidate_values(frame, candidate["name"])
        candidate_frame = pd.DataFrame(
            {
                "event_id": frame["event_id"],
                "asset_id": frame["asset_id"],
                "factor_name": candidate["name"],
                "factor_value": values,
            }
        ).dropna(subset=["factor_value"])
        rows.append(candidate_frame)
    if not rows:
        return pd.DataFrame(columns=["event_id", "asset_id", "factor_name", "factor_value"])
    return pd.concat(rows, ignore_index=True)


def _calculate_candidate_values(frame: pd.DataFrame, name: str) -> pd.Series:
    if name == "fina_roe_level":
        return frame["roe"]
    if name == "fina_roa_level":
        return frame["roa"]
    if name == "fina_net_margin_level":
        return frame["netprofit_margin"]
    if name == "fina_gross_margin_level":
        return frame["grossprofit_margin"]
    if name == "fina_netprofit_yoy_growth":
        return frame["netprofit_yoy"]
    if name == "fina_revenue_yoy_growth":
        return frame["or_yoy"]
    if name == "fina_profit_growth_quality_spread":
        return frame["netprofit_yoy"] - frame["or_yoy"]
    if name == "fina_cash_earnings_quality_ratio":
        denominator = frame["cfps"].abs().replace(0, pd.NA)
        return frame["ocfps"] / denominator
    if name == "fina_profitability_quality_blend":
        return sum(_zscore_by_period(frame, column) for column in ["roe", "roa", "netprofit_margin", "grossprofit_margin"])
    if name == "fina_growth_quality_blend":
        return sum(_zscore_by_period(frame, column) for column in ["netprofit_yoy", "or_yoy", "ocfps"])
    if name == "fina_roe_persistence_4q":
        return _rolling_mean_std_score(frame, "roe", 4)
    if name == "fina_roa_persistence_4q":
        return _rolling_mean_std_score(frame, "roa", 4)
    if name == "fina_net_margin_improvement_yoy":
        return frame["netprofit_margin"] - frame.groupby("asset_id")["netprofit_margin"].shift(4)
    if name == "fina_ocfps_improvement_yoy":
        return frame["ocfps"] - frame.groupby("asset_id")["ocfps"].shift(4)
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _zscore_by_period(frame: pd.DataFrame, column: str) -> pd.Series:
    grouped = frame.groupby("end_date")[column]
    mean = grouped.transform("mean")
    std = grouped.transform("std").replace(0, pd.NA)
    return (frame[column] - mean) / std


def _rolling_mean_std_score(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    grouped = frame.groupby("asset_id")[column]
    rolling_mean = grouped.transform(lambda series: series.rolling(window, min_periods=window).mean())
    rolling_std = grouped.transform(lambda series: series.rolling(window, min_periods=window).std())
    return rolling_mean - rolling_std.fillna(0)


def _align_factor_values_to_labels(
    factor_values: pd.DataFrame,
    event_frame: pd.DataFrame,
    labels: pd.DataFrame,
) -> pd.DataFrame:
    if factor_values.empty or event_frame.empty or labels.empty:
        return pd.DataFrame()
    event_cols = ["event_id", "ann_date", "end_date", "signal_date"]
    values = factor_values.merge(event_frame[event_cols], on="event_id", how="left")
    values = values.dropna(subset=["signal_date"])
    labels = labels.rename(columns={"date": "signal_date"}).copy()
    labels["signal_date"] = pd.to_datetime(labels["signal_date"], errors="coerce")
    return values.merge(labels, on=["asset_id", "signal_date"], how="inner")


def _candidate_summaries(
    candidates: list[dict[str, Any]],
    factor_values: pd.DataFrame,
    event_frame: pd.DataFrame,
    aligned: pd.DataFrame,
    horizons: tuple[int, ...],
) -> list[dict[str, Any]]:
    event_signal_ids = set(event_frame.loc[event_frame["has_signal_date"], "event_id"]) if not event_frame.empty else set()
    rows = []
    for candidate in candidates:
        name = candidate["name"]
        factor_slice = factor_values[factor_values["factor_name"] == name] if not factor_values.empty else pd.DataFrame()
        signal_rows = int(factor_slice["event_id"].isin(event_signal_ids).sum()) if not factor_slice.empty else 0
        aligned_slice = aligned[aligned["factor_name"] == name] if not aligned.empty else pd.DataFrame()
        denominator = signal_rows * len(horizons)
        label_coverage = len(aligned_slice) / denominator if denominator else 0.0
        rows.append(
            {
                "name": name,
                "factor_value_rows": int(len(factor_slice)),
                "signal_rows": signal_rows,
                "label_aligned_rows": int(len(aligned_slice)),
                "label_coverage": label_coverage,
                "alignment_violation_rows": _alignment_violation_count(aligned_slice),
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
    violations = (signal_dates < ann_dates) | (entry_dates <= signal_dates) | (exit_dates <= entry_dates)
    return int(violations.sum())
