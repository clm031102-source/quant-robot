from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.asset_session_integrity import (
    AssetSessionClassification,
    classify_asset_sessions,
)
from quant_robot.storage.atomic import atomic_write, atomic_write_json, atomic_write_text


STAGE = "cn_stock_asset_session_integrity_audit"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
UNRESOLVED_CLASSIFICATIONS = {"missing_lifecycle_metadata", "unresolved_active_session"}


def build_cn_stock_asset_session_integrity_audit(
    *,
    bars: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    stock_basic: pd.DataFrame,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
    source_root: str | Path | None = None,
    evidence_root: str | Path | None = None,
    calendar_provenance: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], AssetSessionClassification]:
    classification = classify_asset_sessions(
        bars=bars,
        expected_sessions=expected_sessions,
        stock_basic=stock_basic,
        daily_suspension=daily_suspension,
        legacy_suspension=legacy_suspension,
    )
    summary = classification.summary
    blockers = _blockers(summary)
    review_reasons = _review_reasons(summary, blockers)
    status = "blocked" if blockers else "review_required" if review_reasons else "cleared"
    packet = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_root": str(source_root) if source_root is not None else None,
        "evidence_root": str(evidence_root) if evidence_root is not None else None,
        "summary": summary,
        "gap_classification_counts": _classification_counts(classification.gaps),
        "decision": {
            "asset_session_integrity_cleared": status == "cleared",
            "blockers": blockers,
            "review_reasons": review_reasons,
        },
        "calendar": calendar_provenance,
        "evidence_policy": {
            "synthetic_bars_allowed": False,
            "missing_price_inference_allowed": False,
            "legacy_suspension_scope": "data_quality_only",
        },
        "samples": {
            "unresolved_asset_sessions": _records(_unresolved_sessions(classification.gaps).head(50)),
            "observed_outside_lifecycle": _records(classification.observed_outside_lifecycle.head(50)),
        },
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_cn_stock_asset_session_integrity_markdown(packet)
    return packet, classification


def write_cn_stock_asset_session_integrity_audit(
    output_dir: str | Path,
    packet: dict[str, Any],
    classification: AssetSessionClassification,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output / f"{STAGE}.json", packet)
    atomic_write_text(output / f"{STAGE}.md", str(packet.get("markdown", "")))
    _write_csv(output / "asset_session_gap_classifications.csv", classification.gaps)
    unresolved = _unresolved_sessions(classification.gaps)
    _write_csv(output / "unresolved_asset_sessions.csv", unresolved)
    _write_csv(output / "unresolved_assets.csv", _unresolved_assets(unresolved))
    _write_csv(output / "observed_outside_lifecycle.csv", classification.observed_outside_lifecycle)
    _write_csv(output / "coverage_by_asset.csv", classification.coverage_by_asset)


def render_cn_stock_asset_session_integrity_markdown(packet: dict[str, Any]) -> str:
    summary = packet.get("summary", {}) if isinstance(packet.get("summary"), dict) else {}
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    lines = [
        "# CN Stock Asset-Session Integrity Audit",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Assets: {summary.get('assets', 0)}",
        f"- Raw gap rows: {summary.get('raw_gap_rows', 0)}",
        f"- Before-list gap rows: {summary.get('before_official_list_date_rows', 0)}",
        f"- Daily suspension rows: {summary.get('official_daily_suspension_rows', 0)}",
        f"- Legacy suspension rows: {summary.get('official_legacy_suspension_rows', 0)}",
        f"- Unresolved active sessions: {summary.get('unresolved_active_session_rows', 0)}",
        f"- Assets missing lifecycle metadata: {summary.get('missing_lifecycle_metadata_assets', 0)}",
        f"- Observed rows outside lifecycle: {summary.get('observed_outside_lifecycle_rows', 0)}",
        "",
        "## Decision",
        "",
        f"- Blockers: {', '.join(decision.get('blockers', [])) if decision.get('blockers') else 'none'}",
        f"- Review reasons: {', '.join(decision.get('review_reasons', [])) if decision.get('review_reasons') else 'none'}",
        "",
        f"Safety: {packet.get('safety', SAFETY_TEXT)}",
        "",
    ]
    return "\n".join(lines)


def _blockers(summary: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    missing_assets = int(summary.get("missing_lifecycle_metadata_assets") or 0)
    outside_rows = int(summary.get("observed_outside_lifecycle_rows") or 0)
    unresolved_rows = int(summary.get("unresolved_active_session_rows") or 0)
    if missing_assets:
        blockers.append(f"missing_lifecycle_metadata_assets:{missing_assets}")
    if outside_rows:
        blockers.append(f"observed_outside_official_lifecycle:{outside_rows}")
    if unresolved_rows:
        blockers.append(f"unresolved_active_sessions:{unresolved_rows}")
    return blockers


def _review_reasons(summary: dict[str, Any], blockers: list[str]) -> list[str]:
    if blockers:
        return []
    if int(summary.get("official_legacy_suspension_rows") or 0):
        return ["retrospective_legacy_suspension_evidence"]
    return []


def _classification_counts(gaps: pd.DataFrame) -> dict[str, int]:
    if gaps.empty or "classification" not in gaps:
        return {}
    counts = gaps["classification"].astype(str).value_counts().sort_index()
    return {str(name): int(value) for name, value in counts.items()}


def _unresolved_sessions(gaps: pd.DataFrame) -> pd.DataFrame:
    if gaps.empty:
        return gaps.copy()
    return gaps[gaps["classification"].isin(UNRESOLVED_CLASSIFICATIONS)].reset_index(drop=True)


def _unresolved_assets(unresolved: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "asset_id",
        "symbol",
        "exchange",
        "unresolved_session_rows",
        "date_start",
        "date_end",
        "classifications",
    ]
    if unresolved.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for asset_id, group in unresolved.groupby("asset_id", sort=True):
        rows.append(
            {
                "asset_id": str(asset_id),
                "symbol": _first(group, "symbol"),
                "exchange": _first(group, "exchange"),
                "unresolved_session_rows": int(len(group)),
                "date_start": str(group["missing_date"].min()),
                "date_end": str(group["missing_date"].max()),
                "classifications": ",".join(sorted(set(group["classification"].astype(str)))),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _first(frame: pd.DataFrame, column: str) -> str:
    if column not in frame:
        return ""
    values = frame[column].dropna().astype(str)
    return values.iloc[0] if not values.empty else ""


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    atomic_write(path, lambda temporary: frame.to_csv(temporary, index=False))
