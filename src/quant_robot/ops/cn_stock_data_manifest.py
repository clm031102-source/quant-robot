from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "cn_stock_data_manifest"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
CRITICAL_WARNINGS = {
    "adjusted_ratio_mass_jump_dates_present",
    "daily_basic_date_coverage_before_bars",
    "moneyflow_date_coverage_before_bars",
}


def build_cn_stock_data_manifest(
    *,
    bars: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame | None,
    daily_basic_inputs: pd.DataFrame | None = None,
    source_root: str | Path,
    extreme_return_threshold: float = 0.50,
    adjusted_ratio_jump_threshold: float = 2.0,
    adjusted_ratio_mass_jump_asset_threshold: int = 100,
    require_daily_basic_inputs: bool = False,
) -> dict[str, Any]:
    clean_bars = _prepare_bars(bars)
    clean_moneyflow = _prepare_moneyflow(moneyflow_inputs)
    clean_daily_basic = _prepare_daily_basic(daily_basic_inputs)
    adjusted_ratio_jumps = _adjusted_ratio_jump_summary(
        clean_bars,
        adjusted_ratio_jump_threshold,
        mass_jump_asset_threshold=adjusted_ratio_mass_jump_asset_threshold,
    )
    blockers = _blockers(clean_bars)
    warnings = _warnings(
        clean_bars,
        clean_moneyflow,
        clean_daily_basic,
        extreme_return_threshold,
        adjusted_ratio_jumps=adjusted_ratio_jumps,
        require_daily_basic_inputs=require_daily_basic_inputs,
    )
    status = "blocked" if blockers else "review_required" if warnings else "cleared"
    summary = _summary(clean_bars, clean_moneyflow, clean_daily_basic, source_root, adjusted_ratio_jumps)
    manifest = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": summary,
        "decision": {
            "data_manifest_cleared": status == "cleared",
            "blockers": blockers,
            "warnings": warnings,
        },
        "symbol_coverage": _symbol_coverage(clean_bars, clean_moneyflow, clean_daily_basic),
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    manifest["markdown"] = render_cn_stock_data_manifest_markdown(manifest)
    return manifest


def write_cn_stock_data_manifest(output_dir: str | Path, manifest: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_stock_data_manifest.json").write_text(
        json.dumps(_json_manifest(manifest), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_stock_data_manifest.md").write_text(str(manifest.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(manifest.get("symbol_coverage", [])).to_csv(output_path / "cn_stock_symbol_coverage.csv", index=False)


def validate_cn_stock_data_manifest_packet(
    packet_path: str | Path | None,
    *,
    expected_source_root: str | Path | None = None,
    allow_review_required: bool = False,
    context: str = "CN stock factor mining",
    require_generated_today: bool = True,
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a CN stock data manifest packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a CN stock data manifest packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} data manifest packet must be generated today: {path}")
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    blockers = _list(decision.get("blockers"))
    warnings = _list(decision.get("warnings"))
    status = str(packet.get("status", "unknown"))
    if status == "blocked" or blockers:
        raise ValueError(f"{context} data manifest is blocked: {path}")
    critical_warnings = sorted(set(warnings).intersection(CRITICAL_WARNINGS))
    if critical_warnings:
        raise ValueError(
            f"{context} critical data manifest warning: "
            + ", ".join(critical_warnings)
            + f" in {path}"
        )
    if status == "review_required" and not allow_review_required:
        raise ValueError(f"{context} data manifest review required: {path}")
    if status not in {"cleared", "review_required"}:
        raise ValueError(f"{context} data manifest status is not usable: {path}")
    if status == "cleared" and decision.get("data_manifest_cleared") is not True:
        raise ValueError(f"{context} data manifest cleared flag mismatch: {path}")
    if int(summary.get("bar_rows") or 0) <= 0 or int(summary.get("bar_symbols") or 0) <= 0:
        raise ValueError(f"{context} data manifest has no CN stock bars: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} data manifest violates live boundary: {path}")
    if expected_source_root is not None and _path_text(summary.get("source_root")) != _path_text(expected_source_root):
        raise ValueError(f"{context} data manifest source root mismatch: {path}")
    return packet


def render_cn_stock_data_manifest_markdown(manifest: dict[str, Any]) -> str:
    summary = _dict(manifest.get("summary"))
    decision = _dict(manifest.get("decision"))
    lines = [
        "# CN Stock Data Manifest",
        "",
        f"- Stage: {manifest.get('stage', STAGE)}",
        f"- Status: {manifest.get('status', 'unknown')}",
        f"- Source root: {summary.get('source_root')}",
        f"- Bar rows: {summary.get('bar_rows', 0)}",
        f"- Bar symbols: {summary.get('bar_symbols', 0)}",
        f"- Moneyflow rows: {summary.get('moneyflow_rows', 0)}",
        f"- Moneyflow symbols: {summary.get('moneyflow_symbols', 0)}",
        f"- Moneyflow date range: {summary.get('moneyflow_date_start')} to {summary.get('moneyflow_date_end')}",
        f"- Daily-basic rows: {summary.get('daily_basic_rows', 0)}",
        f"- Daily-basic symbols: {summary.get('daily_basic_symbols', 0)}",
        f"- Daily-basic date range: {summary.get('daily_basic_date_start')} to {summary.get('daily_basic_date_end')}",
        f"- Date range: {summary.get('date_start')} to {summary.get('date_end')}",
        f"- Adjusted ratio jump rows: {summary.get('adjusted_ratio_jump_rows', 0)}",
        f"- Adjusted ratio jump assets: {summary.get('adjusted_ratio_jump_assets', 0)}",
        f"- Adjusted ratio jump max: {summary.get('adjusted_ratio_jump_max', 0.0)}",
        f"- Adjusted ratio mass jump dates: {len(_dict(summary.get('adjusted_ratio_mass_jump_dates')))}",
        f"- Live boundary allowed: {manifest.get('live_boundary_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    warnings = _list(decision.get("warnings"))
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- none")
    lines.extend(["", f"Safety: {manifest.get('safety', SAFETY_TEXT)}", ""])
    return "\n".join(lines)


def _prepare_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def _prepare_moneyflow(moneyflow_inputs: pd.DataFrame | None) -> pd.DataFrame:
    if moneyflow_inputs is None:
        return pd.DataFrame()
    frame = moneyflow_inputs.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def _prepare_daily_basic(daily_basic_inputs: pd.DataFrame | None) -> pd.DataFrame:
    if daily_basic_inputs is None:
        return pd.DataFrame()
    frame = daily_basic_inputs.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def _summary(
    bars: pd.DataFrame,
    moneyflow: pd.DataFrame,
    daily_basic: pd.DataFrame,
    source_root: str | Path,
    adjusted_ratio_jumps: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_root": str(source_root),
        "bar_rows": int(len(bars)),
        "bar_symbols": _nunique(bars, "symbol"),
        "bar_asset_ids": _nunique(bars, "asset_id"),
        "moneyflow_rows": int(len(moneyflow)),
        "moneyflow_symbols": _nunique(moneyflow, "symbol"),
        "moneyflow_asset_ids": _nunique(moneyflow, "asset_id"),
        "moneyflow_date_start": _date_value(moneyflow["date"].min()) if "date" in moneyflow else None,
        "moneyflow_date_end": _date_value(moneyflow["date"].max()) if "date" in moneyflow else None,
        "daily_basic_rows": int(len(daily_basic)),
        "daily_basic_symbols": _nunique(daily_basic, "symbol"),
        "daily_basic_asset_ids": _nunique(daily_basic, "asset_id"),
        "daily_basic_date_start": _date_value(daily_basic["date"].min()) if "date" in daily_basic else None,
        "daily_basic_date_end": _date_value(daily_basic["date"].max()) if "date" in daily_basic else None,
        "date_start": _date_value(bars["date"].min()) if "date" in bars else None,
        "date_end": _date_value(bars["date"].max()) if "date" in bars else None,
        "bar_years": _years(bars),
        "bar_trade_dates_by_year": _trade_dates_by_year(bars),
        "zero_volume_rows": _zero_count(bars, "volume"),
        "zero_amount_rows": _zero_count(bars, "amount"),
        "missing_adj_close_rows": _missing_count(bars, "adj_close"),
        "adjusted_ratio_jump_rows": int(adjusted_ratio_jumps.get("rows", 0)),
        "adjusted_ratio_jump_assets": int(adjusted_ratio_jumps.get("assets", 0)),
        "adjusted_ratio_jump_max": float(adjusted_ratio_jumps.get("max_jump", 0.0)),
        "adjusted_ratio_jump_threshold": float(adjusted_ratio_jumps.get("threshold", 0.0)),
        "adjusted_ratio_jump_dates": dict(adjusted_ratio_jumps.get("dates", {})),
        "adjusted_ratio_mass_jump_asset_threshold": int(adjusted_ratio_jumps.get("mass_jump_asset_threshold", 0)),
        "adjusted_ratio_mass_jump_dates": dict(adjusted_ratio_jumps.get("mass_dates", {})),
    }


def _blockers(bars: pd.DataFrame) -> list[str]:
    blockers = []
    if bars.empty:
        blockers.append("bars_missing")
        return blockers
    required = {"date", "asset_id", "symbol", "market", "asset_type", "adj_close", "volume", "amount"}
    missing = sorted(required.difference(bars.columns))
    blockers.extend(f"missing_bar_column:{column}" for column in missing)
    if "market" in bars and any(str(value).upper() != "CN" for value in bars["market"].dropna().unique()):
        blockers.append("non_cn_rows_present")
    if "asset_type" in bars and any(str(value).lower() != "stock" for value in bars["asset_type"].dropna().unique()):
        blockers.append("non_stock_rows_present")
    return blockers


def _warnings(
    bars: pd.DataFrame,
    moneyflow: pd.DataFrame,
    daily_basic: pd.DataFrame,
    extreme_return_threshold: float,
    *,
    adjusted_ratio_jumps: dict[str, Any],
    require_daily_basic_inputs: bool,
) -> list[str]:
    warnings = []
    if _zero_count(bars, "volume") > 0:
        warnings.append("zero_volume_rows_present")
    if _zero_count(bars, "amount") > 0:
        warnings.append("zero_amount_rows_present")
    if _missing_count(bars, "adj_close") > 0:
        warnings.append("missing_adj_close_rows_present")
    if _extreme_return_rows(bars, extreme_return_threshold) > 0:
        warnings.append("extreme_return_rows_present")
    if int(adjusted_ratio_jumps.get("rows", 0)) > 0:
        warnings.append("adjusted_ratio_jump_rows_present")
    if adjusted_ratio_jumps.get("mass_dates"):
        warnings.append("adjusted_ratio_mass_jump_dates_present")
    if not moneyflow.empty and _nunique(moneyflow, "symbol") < _nunique(bars, "symbol"):
        warnings.append("moneyflow_symbol_coverage_below_bars")
    if _date_ends_before(moneyflow, bars):
        warnings.append("moneyflow_date_coverage_before_bars")
    if moneyflow.empty:
        warnings.append("moneyflow_inputs_missing")
    if not daily_basic.empty and _nunique(daily_basic, "symbol") < _nunique(bars, "symbol"):
        warnings.append("daily_basic_symbol_coverage_below_bars")
    if _date_ends_before(daily_basic, bars):
        warnings.append("daily_basic_date_coverage_before_bars")
    if require_daily_basic_inputs and daily_basic.empty:
        warnings.append("daily_basic_inputs_missing")
    return warnings


def _symbol_coverage(bars: pd.DataFrame, moneyflow: pd.DataFrame, daily_basic: pd.DataFrame) -> list[dict[str, Any]]:
    if bars.empty or "symbol" not in bars:
        return []
    moneyflow_symbols = set(moneyflow["symbol"].dropna().astype(str)) if "symbol" in moneyflow else set()
    daily_basic_symbols = set(daily_basic["symbol"].dropna().astype(str)) if "symbol" in daily_basic else set()
    rows = []
    for symbol, group in bars.groupby("symbol", sort=True):
        rows.append(
            {
                "symbol": str(symbol),
                "bar_rows": int(len(group)),
                "date_start": _date_value(group["date"].min()) if "date" in group else None,
                "date_end": _date_value(group["date"].max()) if "date" in group else None,
                "has_moneyflow": str(symbol) in moneyflow_symbols,
                "has_daily_basic": str(symbol) in daily_basic_symbols,
            }
        )
    return rows


def _extreme_return_rows(bars: pd.DataFrame, threshold: float) -> int:
    if "adj_close" not in bars or "asset_id" not in bars or "date" not in bars:
        return 0
    count = 0
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        returns = pd.to_numeric(group["adj_close"], errors="coerce").pct_change().abs()
        count += int((returns > threshold).sum())
    return count


def _adjusted_ratio_jump_summary(
    bars: pd.DataFrame,
    threshold: float,
    *,
    mass_jump_asset_threshold: int,
) -> dict[str, Any]:
    required = {"date", "asset_id", "close", "adj_close"}
    if bars.empty or not required.issubset(bars.columns):
        return _empty_adjusted_ratio_jump_summary(threshold, mass_jump_asset_threshold)
    frame = bars.loc[:, ["date", "asset_id", "close", "adj_close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    adj_close = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["adjusted_ratio"] = adj_close / close.where(close > 0)
    frame = frame.replace([float("inf"), float("-inf")], pd.NA)
    frame = frame.dropna(subset=["date", "asset_id", "adjusted_ratio"]).sort_values(["asset_id", "date"])
    if frame.empty:
        return _empty_adjusted_ratio_jump_summary(threshold, mass_jump_asset_threshold)
    previous = frame.groupby("asset_id", sort=False)["adjusted_ratio"].shift(1)
    ratio_change = frame["adjusted_ratio"] / previous
    ratio_change = pd.to_numeric(ratio_change, errors="coerce")
    reciprocal = 1.0 / ratio_change.where(ratio_change != 0)
    frame["adjusted_ratio_jump"] = pd.concat([ratio_change, reciprocal], axis=1).abs().max(axis=1)
    jumps = frame[pd.to_numeric(frame["adjusted_ratio_jump"], errors="coerce") > float(threshold)]
    if jumps.empty:
        return _empty_adjusted_ratio_jump_summary(threshold, mass_jump_asset_threshold)
    date_counts = jumps.groupby(jumps["date"].dt.date)["asset_id"].nunique().sort_index()
    mass_dates = date_counts[date_counts >= int(mass_jump_asset_threshold)]
    return {
        "rows": int(len(jumps)),
        "assets": int(jumps["asset_id"].nunique()),
        "max_jump": float(pd.to_numeric(jumps["adjusted_ratio_jump"], errors="coerce").max()),
        "threshold": float(threshold),
        "mass_jump_asset_threshold": int(mass_jump_asset_threshold),
        "dates": {str(day): int(count) for day, count in date_counts.items()},
        "mass_dates": {str(day): int(count) for day, count in mass_dates.items()},
    }


def _empty_adjusted_ratio_jump_summary(threshold: float, mass_jump_asset_threshold: int) -> dict[str, Any]:
    return {
        "rows": 0,
        "assets": 0,
        "max_jump": 0.0,
        "threshold": float(threshold),
        "mass_jump_asset_threshold": int(mass_jump_asset_threshold),
        "dates": {},
        "mass_dates": {},
    }


def _zero_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame:
        return 0
    values = pd.to_numeric(frame[column], errors="coerce")
    return int((values == 0).sum())


def _missing_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame:
        return 0
    return int(frame[column].isna().sum())


def _nunique(frame: pd.DataFrame, column: str) -> int:
    if column not in frame:
        return 0
    return int(frame[column].dropna().nunique())


def _date_value(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)[:10]


def _date_ends_before(candidate: pd.DataFrame, bars: pd.DataFrame) -> bool:
    if candidate.empty or bars.empty or "date" not in candidate or "date" not in bars:
        return False
    candidate_end = pd.to_datetime(candidate["date"], errors="coerce").max()
    bars_end = pd.to_datetime(bars["date"], errors="coerce").max()
    if pd.isna(candidate_end) or pd.isna(bars_end):
        return False
    return bool(candidate_end < bars_end)


def _years(frame: pd.DataFrame) -> list[int]:
    if "date" not in frame or frame.empty:
        return []
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return [int(year) for year in sorted(dates.dt.year.unique())]


def _trade_dates_by_year(frame: pd.DataFrame) -> dict[str, int]:
    if "date" not in frame or frame.empty:
        return {}
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.date
    if dates.empty:
        return {}
    grouped = pd.Series(dates).groupby(pd.Series(dates).map(lambda value: value.year)).nunique()
    return {str(int(year)): int(count) for year, count in grouped.sort_index().items()}


def _json_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "markdown"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _path_text(value: Any) -> str:
    if value is None:
        return ""
    return Path(str(value)).as_posix()
