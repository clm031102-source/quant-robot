from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_EXTREME_TRADE_THRESHOLD = 5.0


def diagnose_extreme_trades(
    trades: pd.DataFrame,
    bars: pd.DataFrame | None = None,
    *,
    threshold: float = DEFAULT_EXTREME_TRADE_THRESHOLD,
    top_n: int = 20,
) -> dict[str, Any]:
    trade_frame = trades.copy()
    if trade_frame.empty:
        return _packet(trade_frame, [], threshold)
    if "gross_return" not in trade_frame.columns:
        raise ValueError("trades are missing columns: gross_return")
    trade_frame["gross_return"] = pd.to_numeric(trade_frame["gross_return"], errors="coerce")
    trade_frame["abs_gross_return"] = trade_frame["gross_return"].abs()
    extreme = trade_frame[trade_frame["abs_gross_return"] > float(threshold)].copy()
    extreme = extreme.sort_values(["abs_gross_return", "asset_id"], ascending=[False, True]).head(top_n)
    bar_lookup = _bar_lookup(bars) if bars is not None else {}
    rows = [_diagnostic_row(row, bar_lookup, threshold) for row in extreme.to_dict(orient="records")]
    return _packet(trade_frame, rows, threshold)


def render_extreme_trade_markdown(diagnostic: dict[str, Any]) -> str:
    summary = diagnostic["summary"]
    lines = [
        "# Extreme Trade Diagnostic",
        "",
        f"- trades: {summary['trades']}",
        f"- extreme trades: {summary['extreme_trades']}",
        f"- threshold: {summary['threshold']}",
        f"- max abs gross return: {summary['max_abs_gross_return']}",
        f"- p99 abs gross return: {summary['p99_abs_gross_return']}",
        "",
        "| asset | symbol | signal | entry | exit | gross return | entry adj close | exit adj close | reasons |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in diagnostic["extreme_trades"]:
        lines.append(
            "| "
            f"{row.get('asset_id', '')} | "
            f"{row.get('symbol', '')} | "
            f"{row.get('signal_date', '')} | "
            f"{row.get('entry_date', '')} | "
            f"{row.get('exit_date', '')} | "
            f"{row.get('gross_return', 0.0)} | "
            f"{row.get('entry_adj_close', '')} | "
            f"{row.get('exit_adj_close', '')} | "
            f"{', '.join(row.get('reasons', []))} |"
        )
    return "\n".join(lines) + "\n"


def write_extreme_trade_diagnostic(output_dir: str | Path, diagnostic: dict[str, Any]) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "extreme_trade_diagnostic.json"
    csv_path = output_path / "extreme_trade_diagnostic.csv"
    markdown_path = output_path / "extreme_trade_diagnostic.md"
    json_path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True), encoding="utf-8")
    pd.DataFrame(diagnostic["extreme_trades"]).to_csv(csv_path, index=False)
    markdown_path.write_text(render_extreme_trade_markdown(diagnostic), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def _packet(trades: pd.DataFrame, rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    gross = pd.to_numeric(trades.get("gross_return", pd.Series(dtype=float)), errors="coerce").dropna()
    abs_gross = gross.abs()
    return {
        "stage": "extreme_trade_diagnostic",
        "summary": {
            "trades": int(len(trades)),
            "extreme_trades": int(len(rows)),
            "threshold": float(threshold),
            "max_abs_gross_return": _float(abs_gross.max()) if not abs_gross.empty else 0.0,
            "p99_abs_gross_return": _float(abs_gross.quantile(0.99)) if not abs_gross.empty else 0.0,
        },
        "extreme_trades": rows,
    }


def _diagnostic_row(row: dict[str, Any], bar_lookup: dict[tuple[str, str], dict[str, Any]], threshold: float) -> dict[str, Any]:
    asset_id = str(row.get("asset_id", ""))
    entry_date = _date_text(row.get("entry_date"))
    exit_date = _date_text(row.get("exit_date"))
    entry = bar_lookup.get((asset_id, entry_date), {})
    exit_ = bar_lookup.get((asset_id, exit_date), {})
    symbol = str(entry.get("symbol") or exit_.get("symbol") or row.get("symbol") or "")
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": str(row.get("market", "")),
        "factor_name": str(row.get("factor_name", "")),
        "signal_date": _date_text(row.get("signal_date")),
        "entry_date": entry_date,
        "exit_date": exit_date,
        "gross_return": _float(row.get("gross_return")),
        "abs_gross_return": _float(row.get("abs_gross_return")),
        "target_weight": _float(row.get("target_weight")),
        "entry_adj_close": _float(entry.get("adj_close")),
        "exit_adj_close": _float(exit_.get("adj_close")),
        "entry_source": str(entry.get("source", "")),
        "exit_source": str(exit_.get("source", "")),
        "reasons": ["abs_gross_return_above_threshold"]
        if _float(row.get("abs_gross_return")) > float(threshold)
        else [],
    }


def _bar_lookup(bars: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    required = {"date", "asset_id", "adj_close"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"bars are missing columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    return {
        (str(row["asset_id"]), str(row["date"])): row
        for row in frame.to_dict(orient="records")
    }


def _date_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        return str(pd.to_datetime(value).date())
    except (TypeError, ValueError):
        return str(value)


def _float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0
