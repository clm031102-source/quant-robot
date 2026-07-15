from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def build_data_quality_gap_audit(
    bars: pd.DataFrame,
    expected_dates: list[object] | None = None,
    source_root: str | Path | None = None,
    max_examples_per_asset: int = 20,
    calendar_source: str | None = None,
    asset_gap_policy: str = "block",
    calendar_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _require_columns(bars, ["asset_id", "market", "date", "volume"])
    if max_examples_per_asset < 0:
        raise ValueError("max_examples_per_asset must be non-negative")
    if asset_gap_policy not in {"block", "review"}:
        raise ValueError("asset_gap_policy must be 'block' or 'review'")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    explicit_calendar = expected_dates is not None
    expected = _expected_dates(frame, expected_dates)
    markets = sorted(str(value) for value in frame["market"].dropna().unique())
    missing_dates = _missing_date_rows(frame, expected, max_examples_per_asset)
    coverage = _coverage_rows(frame, expected)
    missing_date_rows = sum(int(row["missing_dates"]) for row in coverage)
    assets_with_gaps = sum(1 for row in coverage if int(row["missing_dates"]) > 0)
    whole_market_missing_count, whole_market_missing_dates = _whole_market_missing_dates(
        frame,
        expected,
        max_examples_per_asset,
    )
    blockers = _gap_blockers(
        explicit_calendar=explicit_calendar,
        expected_dates=expected,
        missing_date_rows=missing_date_rows,
        whole_market_missing_dates=whole_market_missing_count,
        asset_gap_policy=asset_gap_policy,
    )
    review_reasons = _gap_review_reasons(
        missing_date_rows=missing_date_rows,
        asset_gap_policy=asset_gap_policy,
    )
    status = "blocked" if blockers else "review_required" if review_reasons else "cleared"
    provenance = calendar_provenance if isinstance(calendar_provenance, dict) else {}
    audit = {
        "stage": "phase_3_1_data_quality_gap_audit",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root) if source_root is not None else None,
        "safety": "Research only. Local data audit only; no broker connection, no account reads, no order placement, no live trading.",
        "summary": {
            "rows": int(len(frame)),
            "assets": int(frame["asset_id"].nunique()),
            "markets": markets,
            "start_date": str(frame["date"].min()) if len(frame) else None,
            "end_date": str(frame["date"].max()) if len(frame) else None,
            "expected_dates": len(expected),
            "calendar_source": (
                calendar_source or "explicit_dates_argument"
                if explicit_calendar
                else "observed_dates_diagnostic_only"
            ),
            "explicit_calendar_supplied": explicit_calendar,
            "asset_gap_policy": asset_gap_policy,
            "calendar_manifest": provenance.get("manifest_path"),
            "calendar_artifact_sha256": provenance.get("artifact_sha256"),
            "missing_date_rows": int(missing_date_rows),
            "missing_date_examples": int(len(missing_dates)),
            "missing_date_examples_truncated": bool(missing_date_rows > len(missing_dates)),
            "assets_with_gaps": int(assets_with_gaps),
            "whole_market_missing_dates": int(whole_market_missing_count),
            "whole_market_missing_date_examples": int(len(whole_market_missing_dates)),
            "whole_market_missing_date_examples_truncated": bool(
                whole_market_missing_count > len(whole_market_missing_dates)
            ),
            "zero_volume_rows": int((pd.to_numeric(frame["volume"], errors="coerce").fillna(0) == 0).sum()),
        },
        "missing_dates": missing_dates,
        "whole_market_missing_dates": whole_market_missing_dates,
        "coverage_by_asset": coverage,
        "decision": {
            "gap_audit_cleared": status == "cleared",
            "calendar_required_for_clearance": True,
            "blockers": blockers,
            "review_reasons": review_reasons,
        },
        "repair_actions": _repair_actions(source_root, _repair_market(markets)),
    }
    audit["markdown"] = render_data_quality_gap_audit_markdown(audit)
    return audit


def write_data_quality_gap_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "data_quality_gap_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    (output_path / "data_quality_gap_audit.md").write_text(str(audit.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(audit.get("missing_dates", [])).to_csv(output_path / "missing_dates.csv", index=False)
    pd.DataFrame(audit.get("whole_market_missing_dates", [])).to_csv(
        output_path / "whole_market_missing_dates.csv",
        index=False,
    )
    pd.DataFrame(audit.get("coverage_by_asset", [])).to_csv(output_path / "coverage_by_asset.csv", index=False)


def render_data_quality_gap_audit_markdown(audit: dict[str, Any]) -> str:
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    lines = [
        "# Data Quality Gap Audit",
        "",
        f"- Stage: {audit.get('stage', 'unknown')}",
        f"- Status: {audit.get('status', 'unknown')}",
        f"- Calendar source: {summary.get('calendar_source', 'unknown')}",
        f"- Calendar manifest: {summary.get('calendar_manifest', 'not_provided')}",
        f"- Asset gap policy: {summary.get('asset_gap_policy', 'block')}",
        f"- Missing date rows: {summary.get('missing_date_rows', 0)}",
        f"- Missing date examples: {summary.get('missing_date_examples', 0)}",
        f"- Assets with gaps: {summary.get('assets_with_gaps', 0)}",
        f"- Whole-market missing dates: {summary.get('whole_market_missing_dates', 0)}",
        f"- Window: {summary.get('start_date')} to {summary.get('end_date')}",
        f"- Safety: {audit.get('safety', '')}",
        "",
        "## Missing Dates",
        "",
        "| Asset | Symbol | Missing date |",
        "| --- | --- | --- |",
    ]
    missing = audit.get("missing_dates", [])
    for row in missing[:80]:
        if isinstance(row, dict):
            lines.append(f"| {row.get('asset_id', '')} | {row.get('symbol', '')} | {row.get('missing_date', '')} |")
    if not missing:
        lines.append("| none | none | none |")
    lines.extend(["", "## Whole-Market Missing Dates", "", "| Market | Missing date |", "| --- | --- |"])
    market_missing = audit.get("whole_market_missing_dates", [])
    for row in market_missing[:80]:
        if isinstance(row, dict):
            lines.append(f"| {row.get('market', '')} | {row.get('missing_date', '')} |")
    if not market_missing:
        lines.append("| none | none |")
    blockers = audit.get("decision", {}).get("blockers", []) if isinstance(audit.get("decision"), dict) else []
    review_reasons = (
        audit.get("decision", {}).get("review_reasons", []) if isinstance(audit.get("decision"), dict) else []
    )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Blockers: {', '.join(blockers) if blockers else 'none'}",
            f"- Review reasons: {', '.join(review_reasons) if review_reasons else 'none'}",
        ]
    )
    lines.extend(["", "## Repair Actions", ""])
    for action in audit.get("repair_actions", []):
        if isinstance(action, dict):
            lines.append(f"- `{action.get('command', '')}`")
            lines.append(f"  - {action.get('reason', '')}")
    return "\n".join(lines) + "\n"


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Gap audit bars are missing columns: {', '.join(missing)}")


def _expected_dates(frame: pd.DataFrame, expected_dates: list[object] | None) -> list[Any]:
    if expected_dates is not None:
        return sorted(set(pd.to_datetime(expected_dates).date))
    return sorted(set(frame["date"]))


def _missing_date_rows(frame: pd.DataFrame, expected_dates: list[Any], max_examples_per_asset: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    symbol_by_asset = _symbol_by_asset(frame)
    for asset_id, group in frame.groupby("asset_id", sort=True):
        observed = set(group["date"])
        if not observed:
            continue
        start = min(observed)
        end = max(observed)
        in_range = [date for date in expected_dates if start <= date <= end]
        for missing_date in sorted(set(in_range) - observed)[:max_examples_per_asset]:
            rows.append(
                {
                    "asset_id": str(asset_id),
                    "symbol": symbol_by_asset.get(str(asset_id), ""),
                    "missing_date": str(missing_date),
                }
            )
    return rows


def _coverage_rows(frame: pd.DataFrame, expected_dates: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    symbol_by_asset = _symbol_by_asset(frame)
    for asset_id, group in frame.groupby("asset_id", sort=True):
        observed = set(group["date"])
        if observed:
            start = min(observed)
            end = max(observed)
            in_range = [date for date in expected_dates if start <= date <= end]
        else:
            in_range = []
        missing_count = len(set(in_range) - observed)
        rows.append(
            {
                "asset_id": str(asset_id),
                "symbol": symbol_by_asset.get(str(asset_id), ""),
                "rows": int(len(group)),
                "start_date": str(min(observed)) if observed else None,
                "end_date": str(max(observed)) if observed else None,
                "expected_rows": int(len(in_range)),
                "missing_dates": int(missing_count),
                "coverage_ratio": float((len(in_range) - missing_count) / len(in_range)) if in_range else 1.0,
            }
        )
    return rows


def _whole_market_missing_dates(
    frame: pd.DataFrame,
    expected_dates: list[Any],
    max_examples_per_market: int,
) -> tuple[int, list[dict[str, Any]]]:
    count = 0
    rows: list[dict[str, Any]] = []
    expected = set(expected_dates)
    for market, group in frame.groupby("market", sort=True):
        missing = sorted(expected - set(group["date"]))
        count += len(missing)
        rows.extend(
            {"market": str(market), "missing_date": str(missing_date)}
            for missing_date in missing[:max_examples_per_market]
        )
    return count, rows


def _gap_blockers(
    *,
    explicit_calendar: bool,
    expected_dates: list[Any],
    missing_date_rows: int,
    whole_market_missing_dates: int,
    asset_gap_policy: str,
) -> list[str]:
    blockers = []
    if not explicit_calendar:
        blockers.append("explicit_trading_calendar_required")
    elif not expected_dates:
        blockers.append("explicit_trading_calendar_empty")
    if missing_date_rows > 0 and asset_gap_policy == "block":
        blockers.append("asset_sessions_missing")
    if whole_market_missing_dates > 0:
        blockers.append("whole_market_sessions_missing")
    return blockers


def _gap_review_reasons(*, missing_date_rows: int, asset_gap_policy: str) -> list[str]:
    if missing_date_rows > 0 and asset_gap_policy == "review":
        return ["asset_sessions_require_suspension_review"]
    return []


def _symbol_by_asset(frame: pd.DataFrame) -> dict[str, str]:
    if "symbol" not in frame.columns:
        return {}
    rows = frame[["asset_id", "symbol"]].dropna().drop_duplicates("asset_id")
    return {str(row.asset_id): str(row.symbol) for row in rows.itertuples(index=False)}


def _repair_market(markets: list[str]) -> str:
    return markets[0] if len(markets) == 1 else "ALL"


def _repair_actions(source_root: str | Path | None, market: str = "CN_ETF") -> list[dict[str, str]]:
    data_root = str(source_root) if source_root is not None else "data/processed/etf_csv"
    return [
        {
            "action": "inspect_missing_dates",
            "command": f"python scripts\\run_data_quality_audit.py --data-root {data_root} --market {market} --calendar-path <calendar-path> --output-dir data\\reports\\data_quality_gap_audit",
            "reason": "Regenerate exact missing-date rows after any local data import.",
        },
        _refresh_action(data_root, market),
        {
            "action": "rebuild_promotion_ops",
            "command": "python scripts\\run_promotion_ops.py --output-dir data\\reports\\promotion_ops",
            "reason": "Refresh downstream promotion evidence after data quality changes.",
        },
    ]


def _refresh_action(data_root: str, market: str) -> dict[str, str]:
    if market.upper() == "CN_ETF":
        return {
            "action": "refresh_etf_csv",
            "command": "python scripts\\batch_import_etf_csv.py --input-dir data\\raw\\tradingview_etf_csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\processed\\etf_csv",
            "reason": "Refresh local TradingView ETF CSV coverage when missing dates are confirmed.",
        }
    output_root = _repair_output_root(data_root, market)
    return {
        "action": "refresh_tushare_data",
        "command": f"python scripts\\ingest_data.py --source tushare --market {market} --start-date <start-date> --end-date <end-date> --output-dir {output_root}",
        "reason": "Refresh the audited market through the local Tushare pipeline after confirming exact missing-date windows.",
    }


def _repair_output_root(data_root: str, market: str) -> str:
    source = Path(data_root)
    if source.suffix.lower() not in {".json", ".yaml", ".yml"} and not source.is_file():
        return data_root
    market_name = market.lower()
    suffix = "stock" if market.upper() == "CN" else "market"
    return f"data\\processed\\{market_name}_{suffix}_gap_repair"
