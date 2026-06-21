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
        return _packet(trade_frame, [], [], [], threshold)
    if "gross_return" not in trade_frame.columns:
        raise ValueError("trades are missing columns: gross_return")
    trade_frame["gross_return"] = pd.to_numeric(trade_frame["gross_return"], errors="coerce")
    trade_frame["abs_gross_return"] = trade_frame["gross_return"].abs()
    trade_frame["participation_rate"] = pd.to_numeric(
        trade_frame.get("participation_rate", pd.Series(0.0, index=trade_frame.index)),
        errors="coerce",
    ).fillna(0.0)
    trade_frame["weighted_return"] = pd.to_numeric(
        trade_frame.get("weighted_return", pd.Series(0.0, index=trade_frame.index)),
        errors="coerce",
    ).fillna(0.0)
    trade_frame["abs_weighted_return"] = trade_frame["weighted_return"].abs()
    trade_frame["calendar_holding_days"] = [
        _calendar_holding_days(entry_date, exit_date)
        for entry_date, exit_date in zip(
            trade_frame.get("entry_date", pd.Series(None, index=trade_frame.index)),
            trade_frame.get("exit_date", pd.Series(None, index=trade_frame.index)),
        )
    ]
    capacity_mask = trade_frame.get("capacity_limited", pd.Series(False, index=trade_frame.index)).map(_bool)
    extreme = trade_frame[trade_frame["abs_gross_return"] > float(threshold)].copy()
    extreme = extreme.sort_values(["abs_gross_return", "asset_id"], ascending=[False, True]).head(top_n)
    capacity_limited = trade_frame[capacity_mask].copy()
    capacity_limited = capacity_limited.sort_values(
        ["participation_rate", "abs_gross_return", "asset_id"],
        ascending=[False, False, True],
    ).head(top_n)
    top_weighted_return = trade_frame[trade_frame["abs_weighted_return"] > 0.0].copy()
    top_weighted_return = top_weighted_return.sort_values(
        ["abs_weighted_return", "abs_gross_return", "asset_id"],
        ascending=[False, False, True],
    ).head(top_n)
    bar_lookup = _bar_lookup(bars) if bars is not None else {}
    rows = [_diagnostic_row(row, bar_lookup, threshold) for row in extreme.to_dict(orient="records")]
    capacity_rows = [
        _trade_context_row(row, bar_lookup, ["capacity_limited"])
        for row in capacity_limited.to_dict(orient="records")
    ]
    weighted_rows = [
        _trade_context_row(row, bar_lookup, ["top_abs_weighted_return"])
        for row in top_weighted_return.to_dict(orient="records")
    ]
    return _packet(trade_frame, rows, capacity_rows, weighted_rows, threshold)


def render_extreme_trade_markdown(diagnostic: dict[str, Any]) -> str:
    summary = diagnostic["summary"]
    lines = [
        "# Extreme Trade Diagnostic",
        "",
        f"- trades: {summary['trades']}",
        f"- extreme trades: {summary['extreme_trades']}",
        f"- capacity-limited trades: {summary.get('capacity_limited_trades', 0)}",
        f"- threshold: {summary['threshold']}",
        f"- max abs gross return: {summary['max_abs_gross_return']}",
        f"- p99 abs gross return: {summary['p99_abs_gross_return']}",
        f"- max participation rate: {summary.get('max_participation_rate', 0.0)}",
        f"- p99 participation rate: {summary.get('p99_participation_rate', 0.0)}",
        f"- max calendar holding days: {summary.get('max_calendar_holding_days', 0)}",
        f"- p99 calendar holding days: {summary.get('p99_calendar_holding_days', 0.0)}",
        f"- top weighted return abs share: {summary.get('top_weighted_return_abs_share', 0.0)}",
        "",
        "## Extreme Gross Return Trades",
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
    lines.extend(
        [
            "",
            "## Capacity-Limited Trades",
            "",
            "| asset | symbol | signal | entry | exit | participation | entry amount | weighted return | reasons |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in diagnostic.get("capacity_limited_trades", []):
        lines.append(_capacity_markdown_row(row))
    lines.extend(
        [
            "",
            "## Top Weighted Return Trades",
            "",
            "| asset | symbol | signal | entry | exit | gross return | weighted return | participation | reasons |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in diagnostic.get("top_weighted_return_trades", []):
        lines.append(_weighted_markdown_row(row))
    return "\n".join(lines) + "\n"


def write_extreme_trade_diagnostic(output_dir: str | Path, diagnostic: dict[str, Any]) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "extreme_trade_diagnostic.json"
    csv_path = output_path / "extreme_trade_diagnostic.csv"
    capacity_csv_path = output_path / "capacity_limited_trades.csv"
    weighted_csv_path = output_path / "top_weighted_return_trades.csv"
    markdown_path = output_path / "extreme_trade_diagnostic.md"
    json_path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True), encoding="utf-8")
    pd.DataFrame(diagnostic["extreme_trades"]).to_csv(csv_path, index=False)
    pd.DataFrame(diagnostic.get("capacity_limited_trades", [])).to_csv(capacity_csv_path, index=False)
    pd.DataFrame(diagnostic.get("top_weighted_return_trades", [])).to_csv(weighted_csv_path, index=False)
    markdown_path.write_text(render_extreme_trade_markdown(diagnostic), encoding="utf-8")
    return {
        "json": json_path,
        "csv": csv_path,
        "capacity_csv": capacity_csv_path,
        "weighted_csv": weighted_csv_path,
        "markdown": markdown_path,
    }


def _packet(
    trades: pd.DataFrame,
    rows: list[dict[str, Any]],
    capacity_rows: list[dict[str, Any]],
    weighted_rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    gross = pd.to_numeric(trades.get("gross_return", pd.Series(dtype=float)), errors="coerce").dropna()
    abs_gross = gross.abs()
    participation = pd.to_numeric(trades.get("participation_rate", pd.Series(dtype=float)), errors="coerce").dropna()
    weighted = pd.to_numeric(trades.get("weighted_return", pd.Series(dtype=float)), errors="coerce").dropna()
    abs_weighted = weighted.abs()
    calendar_holding_days = pd.to_numeric(
        trades.get("calendar_holding_days", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()
    capacity_limited = trades.get("capacity_limited", pd.Series(False, index=trades.index)).map(_bool)
    return {
        "stage": "extreme_trade_diagnostic",
        "summary": {
            "trades": int(len(trades)),
            "extreme_trades": int(len(rows)),
            "capacity_limited_trades": int(capacity_limited.sum()) if len(capacity_limited) else 0,
            "threshold": float(threshold),
            "max_abs_gross_return": _float(abs_gross.max()) if not abs_gross.empty else 0.0,
            "p99_abs_gross_return": _float(abs_gross.quantile(0.99)) if not abs_gross.empty else 0.0,
            "max_participation_rate": _float(participation.max()) if not participation.empty else 0.0,
            "p99_participation_rate": _float(participation.quantile(0.99)) if not participation.empty else 0.0,
            "top_weighted_return_abs_share": _top_abs_share(abs_weighted),
            "max_calendar_holding_days": int(_float(calendar_holding_days.max())) if not calendar_holding_days.empty else 0,
            "p99_calendar_holding_days": _float(calendar_holding_days.quantile(0.99)) if not calendar_holding_days.empty else 0.0,
        },
        "extreme_trades": rows,
        "capacity_limited_trades": capacity_rows,
        "top_weighted_return_trades": weighted_rows,
    }


def _diagnostic_row(row: dict[str, Any], bar_lookup: dict[tuple[str, str], dict[str, Any]], threshold: float) -> dict[str, Any]:
    reasons = ["abs_gross_return_above_threshold"] if _float(row.get("abs_gross_return")) > float(threshold) else []
    return _trade_context_row(row, bar_lookup, reasons)


def _trade_context_row(
    row: dict[str, Any],
    bar_lookup: dict[tuple[str, str], dict[str, Any]],
    reasons: list[str],
) -> dict[str, Any]:
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
        "weighted_return": _float(row.get("weighted_return")),
        "abs_weighted_return": _float(row.get("abs_weighted_return")),
        "target_weight": _float(row.get("target_weight")),
        "target_notional": _float(row.get("target_notional")),
        "entry_amount": _float(row.get("entry_amount")),
        "participation_rate": _float(row.get("participation_rate")),
        "capacity_limited": _bool(row.get("capacity_limited")),
        "calendar_holding_days": int(_float(row.get("calendar_holding_days"))),
        "entry_adj_close": _float(entry.get("adj_close")),
        "exit_adj_close": _float(exit_.get("adj_close")),
        "entry_source": str(entry.get("source", "")),
        "exit_source": str(exit_.get("source", "")),
        "reasons": reasons,
    }


def _capacity_markdown_row(row: dict[str, Any]) -> str:
    return (
        "| "
        f"{row.get('asset_id', '')} | "
        f"{row.get('symbol', '')} | "
        f"{row.get('signal_date', '')} | "
        f"{row.get('entry_date', '')} | "
        f"{row.get('exit_date', '')} | "
        f"{row.get('participation_rate', 0.0)} | "
        f"{row.get('entry_amount', 0.0)} | "
        f"{row.get('weighted_return', 0.0)} | "
        f"{', '.join(row.get('reasons', []))} |"
    )


def _weighted_markdown_row(row: dict[str, Any]) -> str:
    return (
        "| "
        f"{row.get('asset_id', '')} | "
        f"{row.get('symbol', '')} | "
        f"{row.get('signal_date', '')} | "
        f"{row.get('entry_date', '')} | "
        f"{row.get('exit_date', '')} | "
        f"{row.get('gross_return', 0.0)} | "
        f"{row.get('weighted_return', 0.0)} | "
        f"{row.get('participation_rate', 0.0)} | "
        f"{', '.join(row.get('reasons', []))} |"
    )


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


def _calendar_holding_days(entry_date: Any, exit_date: Any) -> int:
    try:
        entry = pd.to_datetime(entry_date).date()
        exit_ = pd.to_datetime(exit_date).date()
    except (TypeError, ValueError):
        return 0
    return max((exit_ - entry).days, 0)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    try:
        return bool(int(value))
    except (TypeError, ValueError, OverflowError):
        return bool(value)


def _top_abs_share(abs_values: pd.Series) -> float:
    if abs_values.empty:
        return 0.0
    total = float(abs_values.sum())
    if total <= 0.0:
        return 0.0
    return float(abs_values.max() / total)
