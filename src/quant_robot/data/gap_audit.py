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
) -> dict[str, Any]:
    _require_columns(bars, ["asset_id", "market", "date", "volume"])
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    expected = _expected_dates(frame, expected_dates)
    markets = sorted(str(value) for value in frame["market"].dropna().unique())
    missing_dates = _missing_date_rows(frame, expected, max_examples_per_asset)
    coverage = _coverage_rows(frame, expected)
    audit = {
        "stage": "phase_3_1_data_quality_gap_audit",
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
            "missing_date_rows": int(len(missing_dates)),
            "assets_with_gaps": int(len({row["asset_id"] for row in missing_dates})),
            "zero_volume_rows": int((pd.to_numeric(frame["volume"], errors="coerce").fillna(0) == 0).sum()),
        },
        "missing_dates": missing_dates,
        "coverage_by_asset": coverage,
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
    pd.DataFrame(audit.get("coverage_by_asset", [])).to_csv(output_path / "coverage_by_asset.csv", index=False)


def render_data_quality_gap_audit_markdown(audit: dict[str, Any]) -> str:
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    lines = [
        "# Data Quality Gap Audit",
        "",
        f"- Stage: {audit.get('stage', 'unknown')}",
        f"- Missing date rows: {summary.get('missing_date_rows', 0)}",
        f"- Assets with gaps: {summary.get('assets_with_gaps', 0)}",
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
        in_range = [date for date in expected_dates if min(observed) <= date <= max(observed)] if observed else []
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
            "command": f"python scripts\\run_data_quality_audit.py --data-root {data_root} --market {market} --output-dir data\\reports\\data_quality_gap_audit",
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
    return {
        "action": "refresh_tushare_data",
        "command": f"python scripts\\ingest_data.py --source tushare --market {market} --start-date <start-date> --end-date <end-date> --output-dir {data_root}",
        "reason": "Refresh the audited market through the local Tushare pipeline after confirming exact missing-date windows.",
    }
