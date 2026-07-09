from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


STAGE = "tushare_hk_hold_source_audit"
CN_SUFFIXES = {"SZ", "SH", "BJ"}
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


class HkHoldSourceAuditAdapter(Protocol):
    def fetch_hk_hold_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...


def build_tushare_hk_hold_source_audit(
    adapter: HkHoldSourceAuditAdapter,
    *,
    trade_dates: list[str] | tuple[str, ...],
    market: str = "CN",
) -> dict[str, Any]:
    date_rows = []
    for trade_date in trade_dates:
        trade_date_key = _tushare_date_key(trade_date)
        raw = adapter.fetch_hk_hold_by_trade_date(trade_date_key)
        date_rows.append(_audit_date_frame(trade_date_key, raw))

    raw_row_count = sum(int(row["raw_rows"]) for row in date_rows)
    cn_row_count = sum(int(row["cn_rows"]) for row in date_rows)
    non_cn_row_count = sum(int(row["non_cn_rows"]) for row in date_rows)
    suffix_totals: dict[str, int] = {}
    for row in date_rows:
        for suffix, count in row["suffix_counts"].items():
            suffix_totals[suffix] = suffix_totals.get(suffix, 0) + int(count)

    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market.upper(),
        "summary": {
            "requested_date_count": len(date_rows),
            "raw_row_count": raw_row_count,
            "cn_row_count": cn_row_count,
            "non_cn_row_count": non_cn_row_count,
            "cn_row_ratio": cn_row_count / raw_row_count if raw_row_count else 0.0,
            "usable_cn_date_count": sum(1 for row in date_rows if row["status"] == "usable_cn_rows"),
            "empty_after_cn_filter_date_count": sum(
                1 for row in date_rows if row["status"] == "empty_after_cn_filter"
            ),
            "empty_raw_date_count": sum(1 for row in date_rows if row["status"] == "empty_raw_response"),
            "suffix_totals": dict(sorted(suffix_totals.items())),
        },
        "date_rows": date_rows,
        "promotion_allowed": False,
        "promotion_blockers": [
            "hk_hold_source_audit_is_not_ic_evidence",
            "candidate_plan_required_before_factor_generation",
            "no_portfolio_grid_or_promotion_from_source_audit",
        ],
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }


def write_tushare_hk_hold_source_audit(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_packet = _json_safe(packet)
    (output_path / "tushare_hk_hold_source_audit.json").write_text(
        json.dumps(clean_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_hk_hold_source_audit.md").write_text(
        render_tushare_hk_hold_source_audit_markdown(clean_packet),
        encoding="utf-8",
    )
    pd.DataFrame(clean_packet.get("date_rows", [])).to_csv(
        output_path / "tushare_hk_hold_source_audit_rows.csv",
        index=False,
    )


def render_tushare_hk_hold_source_audit_markdown(packet: dict[str, Any]) -> str:
    summary = packet.get("summary", {})
    lines = [
        "# Tushare HK-Hold Source Audit",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Generated at: {packet.get('generated_at', '')}",
        f"- Market: {packet.get('market', '')}",
        f"- Requested dates: {summary.get('requested_date_count', 0)}",
        f"- Raw rows: {summary.get('raw_row_count', 0)}",
        f"- CN rows: {summary.get('cn_row_count', 0)}",
        f"- Non-CN rows: {summary.get('non_cn_row_count', 0)}",
        f"- Usable CN dates: {summary.get('usable_cn_date_count', 0)}",
        f"- Empty after CN filter dates: {summary.get('empty_after_cn_filter_date_count', 0)}",
        f"- Empty raw dates: {summary.get('empty_raw_date_count', 0)}",
        f"- Promotion allowed: {packet.get('promotion_allowed', False)}",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Date Rows",
        "",
        "| Trade date | Status | Raw rows | CN rows | Non-CN rows | Suffix counts | Sample non-CN symbols |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in packet.get("date_rows", []):
        lines.append(
            "| {trade_date} | {status} | {raw_rows} | {cn_rows} | {non_cn_rows} | {suffix_counts} | {sample_non_cn_symbols} |".format(
                trade_date=row.get("trade_date", ""),
                status=row.get("status", ""),
                raw_rows=row.get("raw_rows", 0),
                cn_rows=row.get("cn_rows", 0),
                non_cn_rows=row.get("non_cn_rows", 0),
                suffix_counts=json.dumps(row.get("suffix_counts", {}), sort_keys=True),
                sample_non_cn_symbols=", ".join(row.get("sample_non_cn_symbols", []) or []),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _audit_date_frame(trade_date: str, raw: pd.DataFrame | None) -> dict[str, Any]:
    frame = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame()
    raw_rows = int(len(frame))
    if raw_rows == 0:
        return {
            "trade_date": trade_date,
            "status": "empty_raw_response",
            "raw_rows": 0,
            "cn_rows": 0,
            "non_cn_rows": 0,
            "suffix_counts": {},
            "sample_cn_symbols": [],
            "sample_non_cn_symbols": [],
        }
    symbols = _symbol_series(frame)
    suffixes = symbols.map(_suffix_bucket)
    cn_mask = suffixes.isin(CN_SUFFIXES)
    suffix_counts = suffixes.value_counts().sort_index().astype(int).to_dict()
    cn_rows = int(cn_mask.sum())
    non_cn_rows = int((~cn_mask).sum())
    status = "usable_cn_rows" if cn_rows else "empty_after_cn_filter"
    return {
        "trade_date": trade_date,
        "status": status,
        "raw_rows": raw_rows,
        "cn_rows": cn_rows,
        "non_cn_rows": non_cn_rows,
        "suffix_counts": suffix_counts,
        "sample_cn_symbols": [str(value) for value in symbols.loc[cn_mask].head(5)],
        "sample_non_cn_symbols": [str(value) for value in symbols.loc[~cn_mask].head(5)],
    }


def _symbol_series(frame: pd.DataFrame) -> pd.Series:
    if "ts_code" in frame.columns:
        return frame["ts_code"].astype(str).str.upper()
    if "symbol" in frame.columns:
        return frame["symbol"].astype(str).str.upper()
    return pd.Series(["<missing_symbol>"] * len(frame), index=frame.index)


def _suffix_bucket(symbol: str) -> str:
    text = str(symbol).strip().upper()
    if "." not in text:
        return "NO_SUFFIX"
    suffix = text.rsplit(".", 1)[-1]
    return suffix or "NO_SUFFIX"


def _tushare_date_key(value: str) -> str:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return text
    return pd.Timestamp(text).strftime("%Y%m%d")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value
