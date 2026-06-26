from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize


STAGE = "financial_pit_post_announcement_drift_preregistration"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_ALLOWED_GATE = "round222_financial_pit_post_announcement_drift_matrix_label_smoke"
DEFAULT_CANDIDATES = [
    "pead_event_reaction_continuation_1_20",
    "pead_event_gap_underreaction_1_20",
    "pead_volume_disagreement_drift_1_20",
    "pead_late_announcer_risk_reversal_5_20",
    "pead_positive_fundamental_change_low_reaction_20",
    "pead_negative_surprise_reaction_avoidance_20",
    "pead_reaction_quality_residual_composite_20",
]
REQUIRED_FINANCIAL_COLUMNS = ("asset_id", "market", "ann_date", "end_date")
BAR_COLUMNS = ("date", "asset_id", "market", "open", "close", "adj_close", "volume", "amount")


def build_financial_pit_post_announcement_drift_preregistration(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    candidate_seed_json: str | Path | None = None,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    min_assets: int = 50,
    min_signal_dates: int = 20,
    min_event_reaction_coverage: float = 0.80,
) -> dict[str, Any]:
    financial_path = Path(financial_root)
    financial = _filter_date_window(
        _normalise_financial(_load_fina_indicator_inputs(financial_path)),
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
    seed = _load_json(candidate_seed_json)
    candidate_names = _candidate_names(seed)

    blockers: list[str] = []
    missing_financial_columns = [column for column in REQUIRED_FINANCIAL_COLUMNS if column not in financial.columns]
    if financial.empty:
        blockers.append("missing_financial_rows")
    if bars.empty:
        blockers.append("missing_bars")
    if missing_financial_columns:
        blockers.append("missing_required_financial_columns")

    coverage = _event_reaction_coverage(financial, bars) if not financial.empty and not bars.empty else _empty_coverage()
    coverage_frame = coverage.pop("coverage_frame", pd.DataFrame())
    if len(assets) < int(min_assets):
        blockers.append("financial_assets_below_threshold")
    if coverage["unique_signal_dates"] < int(min_signal_dates):
        blockers.append("signal_dates_below_threshold")
    if coverage["event_reaction_coverage"] < float(min_event_reaction_coverage):
        blockers.append("event_reaction_coverage_below_threshold")
    if coverage["signal_date_on_or_before_ann_date_rows"]:
        blockers.append("signal_date_on_or_before_ann_date")
    if coverage["reaction_available_before_or_on_ann_date_rows"]:
        blockers.append("reaction_available_before_or_on_ann_date")

    passes = not blockers
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "financial_root": str(financial_path),
        "bars_roots": [str(Path(root)) for root in bars_roots],
        "candidate_seed_json": str(Path(candidate_seed_json)) if candidate_seed_json else None,
        "summary": {
            "passes": passes,
            "blockers": _dedupe(blockers),
            "candidate_count": len(candidate_names),
            "financial_rows": int(len(financial)),
            "financial_assets": int(len(assets)),
            "bar_rows": int(len(bars)),
            "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
            "missing_required_financial_columns": missing_financial_columns,
            "min_assets": int(min_assets),
            "min_signal_dates": int(min_signal_dates),
            "min_event_reaction_coverage": float(min_event_reaction_coverage),
            **coverage,
            "next_allowed_gate": NEXT_ALLOWED_GATE,
        },
        "candidates": [_candidate_payload(name, passes, seed) for name in candidate_names],
        "event_coverage_sample_rows": _sample_rows(coverage_frame),
        "pit_policy": {
            "financial_signal_date_rule": "use signal_date/available_date if present; otherwise first trade date strictly after ann_date",
            "event_reaction_date_rule": "first tradable signal date after announcement",
            "reaction_available_date_rule": "first trade date strictly after event_reaction_date",
            "same_day_announcement_trading_allowed": False,
            "same_day_event_reaction_trading_allowed": False,
        },
        "holdout_policy": {
            "analysis_start_date": str(analysis_start_date),
            "analysis_end_date": str(analysis_end_date),
            "final_holdout_included": bool(include_final_holdout),
            "final_holdout_start": "2026-01-01",
            "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
        },
        "promotion_policy": {
            "portfolio_grid_allowed_before_residual_prescreen": False,
            "promotion_allowed": False,
            "profitability_claim_allowed": False,
            "requires_financial_coverage_audit": True,
            "requires_residual_ic_shape_prescreen": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "next_allowed_action": NEXT_ALLOWED_GATE,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_pit_post_announcement_drift_preregistration_markdown(result)
    return result


def write_financial_pit_post_announcement_drift_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "financial_pit_post_announcement_drift_preregistration.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_drift_preregistration.md").write_text(
        render_financial_pit_post_announcement_drift_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_drift_candidates.csv",
        result.get("candidates", []) or [],
        ["factor_name", "family", "registration_status", "portfolio_backtest_allowed", "promotion_allowed"],
    )


def render_financial_pit_post_announcement_drift_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Drift Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Financial rows: {summary.get('financial_rows', 0)}",
        f"- Financial assets: {summary.get('financial_assets', 0)}",
        f"- Unique signal dates: {summary.get('unique_signal_dates', 0)}",
        f"- Event reaction coverage: {float(summary.get('event_reaction_coverage', 0.0)):.2%}",
        f"- Event reaction available rows: {summary.get('event_reaction_available_rows', 0)}",
        f"- Missing reaction-available rows: {summary.get('reaction_available_date_missing_rows', 0)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next allowed gate: `{summary.get('next_allowed_gate', NEXT_ALLOWED_GATE)}`",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidates",
        "",
        "| Factor | Status |",
        "|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(f"| `{candidate.get('factor_name', '')}` | {candidate.get('registration_status', '')} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is preregistration and coverage evidence only.",
            "- Event-day reaction can only be used after a later tradable date.",
            "- No portfolio grid, Sharpe ranking, profit-rate claim, or promotion is allowed from this artifact.",
        ]
    )
    return "\n".join(lines) + "\n"


def _event_reaction_coverage(financial: pd.DataFrame, bars: pd.DataFrame) -> dict[str, Any]:
    frame = financial.copy()
    frame["ann_date"] = pd.to_datetime(frame["ann_date"], errors="coerce")
    if "signal_date" in frame:
        frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce")
    elif "available_date" in frame:
        frame["signal_date"] = pd.to_datetime(frame["available_date"], errors="coerce")
    else:
        frame["signal_date"] = _next_trade_dates(frame, bars, "ann_date")
    frame["event_reaction_date"] = frame["signal_date"]
    frame["reaction_available_date"] = _next_trade_dates(frame, bars, "event_reaction_date")
    valid_signal = frame["signal_date"].notna() & (frame["signal_date"] > frame["ann_date"])
    valid_reaction = (
        valid_signal
        & frame["reaction_available_date"].notna()
        & (frame["reaction_available_date"] > frame["event_reaction_date"])
    )
    denominator = int(len(frame))
    coverage = float(valid_reaction.sum() / denominator) if denominator else 0.0
    reaction_before_ann = int(
        (
            frame["reaction_available_date"].notna()
            & frame["ann_date"].notna()
            & (frame["reaction_available_date"] <= frame["ann_date"])
        ).sum()
    )
    return {
        "unique_signal_dates": int(frame.loc[valid_signal, "signal_date"].nunique()),
        "event_reaction_available_rows": int(valid_reaction.sum()),
        "event_reaction_coverage": coverage,
        "signal_date_missing_rows": int(frame["signal_date"].isna().sum()),
        "signal_date_on_or_before_ann_date_rows": int(
            (frame["signal_date"].notna() & frame["ann_date"].notna() & (frame["signal_date"] <= frame["ann_date"])).sum()
        ),
        "reaction_available_date_missing_rows": int(frame["reaction_available_date"].isna().sum()),
        "reaction_available_before_or_on_ann_date_rows": reaction_before_ann,
        "min_signal_date": _date_min(frame, "signal_date"),
        "max_signal_date": _date_max(frame, "signal_date"),
        "min_reaction_available_date": _date_min(frame, "reaction_available_date"),
        "max_reaction_available_date": _date_max(frame, "reaction_available_date"),
        "coverage_frame": frame,
    }


def _next_trade_dates(frame: pd.DataFrame, bars: pd.DataFrame, source_column: str) -> pd.Series:
    dates_by_asset = {
        asset_id: pd.DatetimeIndex(group["date"].sort_values().dropna().unique())
        for asset_id, group in bars.groupby("asset_id")
    }
    output = []
    for row in frame.itertuples(index=False):
        asset_id = str(getattr(row, "asset_id"))
        source_date = pd.Timestamp(getattr(row, source_column))
        dates = dates_by_asset.get(asset_id)
        if dates is None or pd.isna(source_date):
            output.append(pd.NaT)
            continue
        position = dates.searchsorted(source_date, side="right")
        output.append(dates[position] if position < len(dates) else pd.NaT)
    return pd.Series(output, index=frame.index)


def _normalise_financial(financial: pd.DataFrame) -> pd.DataFrame:
    frame = financial.copy()
    for column in ["date", "ann_date", "end_date", "available_date", "signal_date"]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ["asset_id", "market"]:
        if column not in frame:
            frame[column] = "CN" if column == "market" else ""
    if "asset_id" in frame:
        frame["asset_id"] = frame["asset_id"].astype(str)
    if "market" in frame:
        frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    return frame.sort_values([column for column in ["asset_id", "ann_date", "end_date"] if column in frame]).reset_index(drop=True)


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
    preferred_date_column: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    date_column = preferred_date_column if preferred_date_column in output else "ann_date" if "ann_date" in output else "date"
    if date_column not in output:
        return output
    dates = pd.to_datetime(output[date_column], errors="coerce")
    start = pd.Timestamp(start_date)
    end = dates.max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(dates >= start) & (dates <= end)].reset_index(drop=True)


def _load_bars(roots: list[Path], assets: list[str]) -> pd.DataFrame:
    frames = []
    asset_set = set(assets)
    for root in roots:
        dataset_root = root / "processed" / "bars" / "frequency=1d" / "market=CN"
        if not dataset_root.exists():
            dataset_root = root
        for path in _dataset_files(dataset_root):
            frame = _read_frame(path, list(BAR_COLUMNS))
            if not set(BAR_COLUMNS).issubset(frame.columns):
                continue
            if asset_set:
                frame = frame[frame["asset_id"].astype(str).isin(asset_set)]
            if not frame.empty:
                frames.append(frame[list(BAR_COLUMNS)])
    if not frames:
        return pd.DataFrame(columns=list(BAR_COLUMNS))
    return _normalise_bars(pd.concat(frames, ignore_index=True))


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    for column in ["date"]:
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["open", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & frame["date"].notna()]
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _candidate_names(seed: dict[str, Any]) -> list[str]:
    raw = seed.get("candidate_ideas") if isinstance(seed, dict) else None
    names = [str(name) for name in raw or DEFAULT_CANDIDATES if str(name)]
    return _dedupe(names)


def _candidate_payload(name: str, passes: bool, seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "factor_name": name,
        "family": str(seed.get("family", "financial_pit_post_announcement_drift") if isinstance(seed, dict) else "financial_pit_post_announcement_drift"),
        "registration_status": "pre_registered" if passes else "blocked_by_coverage",
        "mandatory_controls": list(seed.get("mandatory_controls", [])) if isinstance(seed, dict) else [],
        "portfolio_backtest_allowed": False,
        "promotion_allowed": False,
    }


def _sample_rows(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    sample = frame.head(limit).copy()
    for column in ["date", "ann_date", "end_date", "available_date", "signal_date", "event_reaction_date", "reaction_available_date"]:
        if column in sample:
            sample[column] = pd.to_datetime(sample[column], errors="coerce").dt.date.astype(str)
    return sample.to_dict(orient="records")


def _empty_coverage() -> dict[str, Any]:
    return {
        "unique_signal_dates": 0,
        "event_reaction_available_rows": 0,
        "event_reaction_coverage": 0.0,
        "signal_date_missing_rows": 0,
        "signal_date_on_or_before_ann_date_rows": 0,
        "reaction_available_date_missing_rows": 0,
        "reaction_available_before_or_on_ann_date_rows": 0,
        "min_signal_date": None,
        "max_signal_date": None,
        "min_reaction_available_date": None,
        "max_reaction_available_date": None,
        "coverage_frame": pd.DataFrame(),
    }


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


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


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
