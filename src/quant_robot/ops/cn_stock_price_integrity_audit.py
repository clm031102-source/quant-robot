from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.storage.atomic import atomic_write, atomic_write_json, atomic_write_text


STAGE = "cn_stock_price_integrity_audit"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
BLOCKING_CLASSIFICATIONS = {
    "outside_official_lifecycle",
    "adjustment_ratio_discontinuity",
    "raw_price_discontinuity",
    "combined_price_adjustment_move",
}
REVIEW_CLASSIFICATIONS = {
    "official_initial_price_discovery",
    "official_post_suspension_repricing",
}
OUTPUT_COLUMNS = [
    "asset_id",
    "symbol",
    "exchange",
    "previous_date",
    "date",
    "calendar_gap_days",
    "previous_observed_session_number",
    "observed_session_number",
    "calendar_days_since_list",
    "previous_close",
    "close",
    "raw_return",
    "previous_adj_close",
    "adj_close",
    "adjusted_return",
    "previous_adjusted_ratio",
    "adjusted_ratio",
    "adjusted_ratio_jump",
    "classification",
    "outside_lifecycle_reason",
    "evidence_source",
    "suspend_date",
    "resume_date",
]


@dataclass(frozen=True)
class _Lifecycle:
    list_date: date
    delist_date: date | None


@dataclass(frozen=True)
class _SuspensionEvidence:
    source: str
    suspend_date: date
    resume_date: date | None


def build_cn_stock_price_integrity_audit(
    *,
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
    source_root: str | Path | None = None,
    evidence_root: str | Path | None = None,
    extreme_return_threshold: float = 0.50,
    adjusted_ratio_jump_threshold: float = 1.50,
) -> tuple[dict[str, Any], pd.DataFrame]:
    if extreme_return_threshold <= 0:
        raise ValueError("extreme_return_threshold must be positive")
    if adjusted_ratio_jump_threshold <= 1:
        raise ValueError("adjusted_ratio_jump_threshold must be greater than one")
    clean_bars = _prepare_bars(bars)
    lifecycles = _prepare_lifecycles(stock_basic)
    daily = _prepare_daily_suspensions(daily_suspension)
    legacy = _prepare_legacy_suspensions(legacy_suspension)
    extreme_rows, transition_rows = _extreme_return_rows(
        clean_bars,
        lifecycles,
        daily,
        legacy,
        extreme_return_threshold=float(extreme_return_threshold),
        adjusted_ratio_jump_threshold=float(adjusted_ratio_jump_threshold),
    )
    counts = Counter(extreme_rows["classification"].astype(str)) if not extreme_rows.empty else Counter()
    blockers = [
        f"{classification}_rows:{int(counts[classification])}"
        for classification in sorted(BLOCKING_CLASSIFICATIONS)
        if counts[classification]
    ]
    review_reasons = [
        f"{classification}_rows:{int(counts[classification])}"
        for classification in sorted(REVIEW_CLASSIFICATIONS)
        if counts[classification]
    ]
    status = "blocked" if blockers else "review_required" if review_reasons else "cleared"
    blocking_rows = extreme_rows[extreme_rows["classification"].isin(BLOCKING_CLASSIFICATIONS)]
    review_rows = extreme_rows[extreme_rows["classification"].isin(REVIEW_CLASSIFICATIONS)]
    summary = {
        "bar_rows": int(len(clean_bars)),
        "assets": int(clean_bars["asset_id"].nunique()),
        "transition_rows": int(transition_rows),
        "extreme_return_rows": int(len(extreme_rows)),
        "extreme_return_assets": int(extreme_rows["asset_id"].nunique()) if not extreme_rows.empty else 0,
        "blocking_rows": int(len(blocking_rows)),
        "blocking_assets": int(blocking_rows["asset_id"].nunique()) if not blocking_rows.empty else 0,
        "review_rows": int(len(review_rows)),
        "review_assets": int(review_rows["asset_id"].nunique()) if not review_rows.empty else 0,
        "classification_counts": {
            classification: int(counts[classification])
            for classification in sorted(BLOCKING_CLASSIFICATIONS | REVIEW_CLASSIFICATIONS)
        },
    }
    packet = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_root": str(source_root) if source_root is not None else None,
        "evidence_root": str(evidence_root) if evidence_root is not None else None,
        "thresholds": {
            "extreme_adjusted_return_abs_gt": float(extreme_return_threshold),
            "adjusted_ratio_jump_gt": float(adjusted_ratio_jump_threshold),
        },
        "summary": summary,
        "decision": {
            "price_integrity_cleared": status == "cleared",
            "blockers": blockers,
            "review_reasons": review_reasons,
        },
        "evidence_policy": {
            "official_daily_suspension_source": "tushare_suspend_d",
            "legacy_suspension_scope": "data_quality_only",
            "unexplained_price_moves_allowed": False,
        },
        "samples": {
            "blocking_rows": _records(blocking_rows.head(50)),
            "review_rows": _records(review_rows.head(50)),
        },
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_cn_stock_price_integrity_markdown(packet)
    return packet, extreme_rows


def write_cn_stock_price_integrity_audit(
    output_dir: str | Path,
    packet: dict[str, Any],
    extreme_rows: pd.DataFrame,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output / f"{STAGE}.json", packet)
    atomic_write_text(output / f"{STAGE}.md", str(packet.get("markdown", "")))
    _write_csv(output / "extreme_return_rows.csv", extreme_rows)
    _write_csv(
        output / "blocking_extreme_return_rows.csv",
        extreme_rows[extreme_rows["classification"].isin(BLOCKING_CLASSIFICATIONS)],
    )
    _write_csv(
        output / "review_extreme_return_rows.csv",
        extreme_rows[extreme_rows["classification"].isin(REVIEW_CLASSIFICATIONS)],
    )


def render_cn_stock_price_integrity_markdown(packet: dict[str, Any]) -> str:
    summary = packet.get("summary", {}) if isinstance(packet.get("summary"), dict) else {}
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    counts = summary.get("classification_counts", {})
    lines = [
        "# CN Stock Price Integrity Audit",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Assets: {summary.get('assets', 0)}",
        f"- Extreme adjusted-return rows: {summary.get('extreme_return_rows', 0)}",
        f"- Blocking rows: {summary.get('blocking_rows', 0)}",
        f"- Review rows: {summary.get('review_rows', 0)}",
        "",
        "## Classifications",
        "",
    ]
    for classification in sorted(BLOCKING_CLASSIFICATIONS | REVIEW_CLASSIFICATIONS):
        lines.append(f"- {classification}: {counts.get(classification, 0)}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Blockers: {', '.join(decision.get('blockers', [])) if decision.get('blockers') else 'none'}",
            f"- Review reasons: {', '.join(decision.get('review_reasons', [])) if decision.get('review_reasons') else 'none'}",
            "",
            f"Safety: {packet.get('safety', SAFETY_TEXT)}",
            "",
        ]
    )
    return "\n".join(lines)


def _prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["asset_id", "date", "close", "adj_close"]
    _require_columns(frame, required, "bars")
    columns = [
        column
        for column in ["asset_id", "symbol", "exchange", "date", "close", "adj_close"]
        if column in frame
    ]
    bars = frame.loc[:, columns].copy()
    bars["asset_id"] = bars["asset_id"].astype(str)
    for column in ["symbol", "exchange"]:
        if column not in bars:
            bars[column] = ""
        bars[column] = bars[column].fillna("").astype(str)
    bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
    bars["close"] = pd.to_numeric(bars["close"], errors="coerce")
    bars["adj_close"] = pd.to_numeric(bars["adj_close"], errors="coerce")
    if bars[["date", "close", "adj_close"]].isna().any().any():
        raise ValueError("bars contain invalid dates or prices")
    if (bars[["close", "adj_close"]] <= 0).any().any():
        raise ValueError("bars contain non-positive prices")
    if bars.duplicated(["asset_id", "date"]).any():
        raise ValueError("bars contain duplicate asset-session rows")
    return bars.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _prepare_lifecycles(frame: pd.DataFrame) -> dict[str, _Lifecycle]:
    _require_columns(frame, ["asset_id", "list_date"], "stock_basic")
    metadata = frame.loc[:, [column for column in ["asset_id", "list_date", "delist_date"] if column in frame]].copy()
    metadata["asset_id"] = metadata["asset_id"].astype(str)
    if metadata.duplicated("asset_id").any():
        raise ValueError("stock_basic contains duplicate asset_id rows")
    metadata["list_date"] = pd.to_datetime(metadata["list_date"], errors="coerce").dt.date
    if "delist_date" not in metadata:
        metadata["delist_date"] = pd.NaT
    metadata["delist_date"] = pd.to_datetime(metadata["delist_date"], errors="coerce").dt.date
    output: dict[str, _Lifecycle] = {}
    for row in metadata.itertuples(index=False):
        if pd.isna(row.list_date):
            continue
        delist_date = None if pd.isna(row.delist_date) else row.delist_date
        if delist_date is not None and delist_date < row.list_date:
            raise ValueError(f"stock_basic delist_date precedes list_date: {row.asset_id}")
        output[str(row.asset_id)] = _Lifecycle(row.list_date, delist_date)
    return output


def _prepare_daily_suspensions(
    frame: pd.DataFrame | None,
) -> dict[str, list[_SuspensionEvidence]]:
    if frame is None or frame.empty:
        return {}
    _require_columns(frame, ["asset_id", "date"], "daily suspension")
    daily = frame.copy()
    daily["asset_id"] = daily["asset_id"].astype(str)
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.date
    if daily["date"].isna().any():
        raise ValueError("daily suspension contains invalid dates")
    if daily.duplicated(["asset_id", "date"]).any():
        raise ValueError("daily suspension contains duplicate asset-session rows")
    if "source" not in daily:
        daily["source"] = "tushare_suspend_d"
    output: dict[str, list[_SuspensionEvidence]] = {}
    for row in daily.itertuples(index=False):
        output.setdefault(str(row.asset_id), []).append(
            _SuspensionEvidence(str(row.source or "tushare_suspend_d"), row.date, None)
        )
    return output


def _prepare_legacy_suspensions(
    frame: pd.DataFrame | None,
) -> dict[str, list[_SuspensionEvidence]]:
    if frame is None or frame.empty:
        return {}
    _require_columns(frame, ["asset_id", "suspend_date"], "legacy suspension")
    legacy = frame.copy()
    legacy["asset_id"] = legacy["asset_id"].astype(str)
    legacy["suspend_date"] = pd.to_datetime(legacy["suspend_date"], errors="coerce").dt.date
    if "resume_date" not in legacy:
        legacy["resume_date"] = pd.NaT
    legacy["resume_date"] = pd.to_datetime(legacy["resume_date"], errors="coerce").dt.date
    if legacy["suspend_date"].isna().any():
        raise ValueError("legacy suspension contains invalid suspend_date")
    if "source" not in legacy:
        legacy["source"] = "tushare_suspend"
    output: dict[str, list[_SuspensionEvidence]] = {}
    for row in legacy.itertuples(index=False):
        resume_date = None if pd.isna(row.resume_date) else row.resume_date
        if resume_date is not None and resume_date <= row.suspend_date:
            raise ValueError(f"legacy suspension resume_date is not after suspend_date: {row.asset_id}")
        output.setdefault(str(row.asset_id), []).append(
            _SuspensionEvidence(
                str(row.source or "tushare_suspend"),
                row.suspend_date,
                resume_date,
            )
        )
    return output


def _extreme_return_rows(
    bars: pd.DataFrame,
    lifecycles: dict[str, _Lifecycle],
    daily: dict[str, list[_SuspensionEvidence]],
    legacy: dict[str, list[_SuspensionEvidence]],
    *,
    extreme_return_threshold: float,
    adjusted_ratio_jump_threshold: float,
) -> tuple[pd.DataFrame, int]:
    grouped = bars.groupby("asset_id", sort=False)
    session_number = grouped.cumcount() + 1
    previous_date = grouped["date"].shift(1)
    previous_close = grouped["close"].shift(1)
    previous_adj_close = grouped["adj_close"].shift(1)
    ratio = bars["adj_close"] / bars["close"]
    previous_ratio = ratio.groupby(bars["asset_id"], sort=False).shift(1)
    adjusted_return = bars["adj_close"] / previous_adj_close - 1.0
    raw_return = bars["close"] / previous_close - 1.0
    ratio_change = ratio / previous_ratio
    ratio_reciprocal = 1.0 / ratio_change
    ratio_jump = pd.concat([ratio_change, ratio_reciprocal], axis=1).abs().max(axis=1)
    has_previous = previous_date.notna()
    extreme_mask = has_previous & adjusted_return.abs().gt(extreme_return_threshold)
    transition_rows = int(has_previous.sum())
    if not extreme_mask.any():
        return pd.DataFrame(columns=OUTPUT_COLUMNS), transition_rows
    extreme = bars.loc[extreme_mask, ["asset_id", "symbol", "exchange", "date", "close", "adj_close"]].copy()
    extreme["previous_date"] = previous_date.loc[extreme_mask]
    extreme["previous_close"] = previous_close.loc[extreme_mask]
    extreme["raw_return"] = raw_return.loc[extreme_mask]
    extreme["previous_adj_close"] = previous_adj_close.loc[extreme_mask]
    extreme["adjusted_return"] = adjusted_return.loc[extreme_mask]
    extreme["previous_adjusted_ratio"] = previous_ratio.loc[extreme_mask]
    extreme["adjusted_ratio"] = ratio.loc[extreme_mask]
    extreme["adjusted_ratio_jump"] = ratio_jump.loc[extreme_mask]
    extreme["calendar_gap_days"] = (extreme["date"] - extreme["previous_date"]).dt.days
    extreme["observed_session_number"] = session_number.loc[extreme_mask].astype(int)
    extreme["previous_observed_session_number"] = extreme["observed_session_number"] - 1
    classifications = []
    outside_reasons = []
    sources = []
    suspend_dates = []
    resume_dates = []
    days_since_list = []
    for row in extreme.itertuples(index=False):
        previous = row.previous_date.date()
        current = row.date.date()
        outside_reason = _outside_lifecycle_reason(
            lifecycles.get(str(row.asset_id)), previous, current
        )
        lifecycle = lifecycles.get(str(row.asset_id))
        calendar_days_since_list = (
            (current - lifecycle.list_date).days if lifecycle is not None else None
        )
        evidence = _suspension_evidence(
            str(row.asset_id), previous, current, daily, legacy
        )
        raw_extreme = abs(float(row.raw_return)) > extreme_return_threshold
        ratio_extreme = float(row.adjusted_ratio_jump) > adjusted_ratio_jump_threshold
        if outside_reason:
            classification = "outside_official_lifecycle"
        elif ratio_extreme and raw_extreme:
            classification = "combined_price_adjustment_move"
        elif ratio_extreme:
            classification = "adjustment_ratio_discontinuity"
        elif raw_extreme and evidence is not None:
            classification = "official_post_suspension_repricing"
        elif raw_extreme and _is_initial_price_discovery(
            lifecycle,
            current,
            int(row.observed_session_number),
        ):
            classification = "official_initial_price_discovery"
        elif raw_extreme:
            classification = "raw_price_discontinuity"
        else:
            classification = "combined_price_adjustment_move"
        classifications.append(classification)
        outside_reasons.append(outside_reason)
        source = evidence.source if evidence is not None else ""
        if classification == "official_initial_price_discovery":
            source = "tushare_stock_basic"
        sources.append(source)
        suspend_dates.append(evidence.suspend_date.isoformat() if evidence is not None else "")
        resume_dates.append(
            evidence.resume_date.isoformat()
            if evidence is not None and evidence.resume_date is not None
            else ""
        )
        days_since_list.append(calendar_days_since_list)
    extreme["classification"] = classifications
    extreme["outside_lifecycle_reason"] = outside_reasons
    extreme["evidence_source"] = sources
    extreme["suspend_date"] = suspend_dates
    extreme["resume_date"] = resume_dates
    extreme["calendar_days_since_list"] = days_since_list
    extreme["previous_date"] = extreme["previous_date"].dt.strftime("%Y-%m-%d")
    extreme["date"] = extreme["date"].dt.strftime("%Y-%m-%d")
    return extreme.loc[:, OUTPUT_COLUMNS].reset_index(drop=True), transition_rows


def _is_initial_price_discovery(
    lifecycle: _Lifecycle | None,
    current_date: date,
    observed_session_number: int,
) -> bool:
    if lifecycle is None or current_date < lifecycle.list_date:
        return False
    return observed_session_number <= 5 and (current_date - lifecycle.list_date).days <= 30


def _outside_lifecycle_reason(
    lifecycle: _Lifecycle | None,
    previous_date: date,
    current_date: date,
) -> str:
    if lifecycle is None:
        return "missing_lifecycle_metadata"
    if previous_date < lifecycle.list_date:
        return "previous_bar_before_list_date"
    if current_date < lifecycle.list_date:
        return "current_bar_before_list_date"
    if lifecycle.delist_date is not None and previous_date > lifecycle.delist_date:
        return "previous_bar_after_delist_date"
    if lifecycle.delist_date is not None and current_date > lifecycle.delist_date:
        return "current_bar_after_delist_date"
    return ""


def _suspension_evidence(
    asset_id: str,
    previous_date: date,
    current_date: date,
    daily: dict[str, list[_SuspensionEvidence]],
    legacy: dict[str, list[_SuspensionEvidence]],
) -> _SuspensionEvidence | None:
    for evidence in daily.get(asset_id, []):
        if previous_date < evidence.suspend_date < current_date:
            return evidence
    for evidence in legacy.get(asset_id, []):
        if (
            previous_date < evidence.suspend_date < current_date
            and evidence.resume_date is not None
            and previous_date < evidence.resume_date <= current_date
        ):
            return evidence
    return None


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records"))


def _require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(missing)}")


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    atomic_write(path, lambda temporary: frame.to_csv(temporary, index=False))
