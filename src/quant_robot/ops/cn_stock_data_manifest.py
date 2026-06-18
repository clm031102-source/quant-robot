from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "cn_stock_data_manifest"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_cn_stock_data_manifest(
    *,
    bars: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame | None,
    source_root: str | Path,
    extreme_return_threshold: float = 0.50,
) -> dict[str, Any]:
    clean_bars = _prepare_bars(bars)
    clean_moneyflow = _prepare_moneyflow(moneyflow_inputs)
    blockers = _blockers(clean_bars)
    warnings = _warnings(clean_bars, clean_moneyflow, extreme_return_threshold)
    status = "blocked" if blockers else "review_required" if warnings else "cleared"
    summary = _summary(clean_bars, clean_moneyflow, source_root)
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
        "symbol_coverage": _symbol_coverage(clean_bars, clean_moneyflow),
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
    status = str(packet.get("status", "unknown"))
    if status == "blocked" or blockers:
        raise ValueError(f"{context} data manifest is blocked: {path}")
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
        f"- Date range: {summary.get('date_start')} to {summary.get('date_end')}",
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


def _summary(bars: pd.DataFrame, moneyflow: pd.DataFrame, source_root: str | Path) -> dict[str, Any]:
    return {
        "source_root": str(source_root),
        "bar_rows": int(len(bars)),
        "bar_symbols": _nunique(bars, "symbol"),
        "bar_asset_ids": _nunique(bars, "asset_id"),
        "moneyflow_rows": int(len(moneyflow)),
        "moneyflow_symbols": _nunique(moneyflow, "symbol"),
        "moneyflow_asset_ids": _nunique(moneyflow, "asset_id"),
        "date_start": _date_value(bars["date"].min()) if "date" in bars else None,
        "date_end": _date_value(bars["date"].max()) if "date" in bars else None,
        "bar_years": _years(bars),
        "bar_trade_dates_by_year": _trade_dates_by_year(bars),
        "zero_volume_rows": _zero_count(bars, "volume"),
        "zero_amount_rows": _zero_count(bars, "amount"),
        "missing_adj_close_rows": _missing_count(bars, "adj_close"),
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


def _warnings(bars: pd.DataFrame, moneyflow: pd.DataFrame, extreme_return_threshold: float) -> list[str]:
    warnings = []
    if _zero_count(bars, "volume") > 0:
        warnings.append("zero_volume_rows_present")
    if _zero_count(bars, "amount") > 0:
        warnings.append("zero_amount_rows_present")
    if _missing_count(bars, "adj_close") > 0:
        warnings.append("missing_adj_close_rows_present")
    if _extreme_return_rows(bars, extreme_return_threshold) > 0:
        warnings.append("extreme_return_rows_present")
    if not moneyflow.empty and _nunique(moneyflow, "symbol") < _nunique(bars, "symbol"):
        warnings.append("moneyflow_symbol_coverage_below_bars")
    if moneyflow.empty:
        warnings.append("moneyflow_inputs_missing")
    return warnings


def _symbol_coverage(bars: pd.DataFrame, moneyflow: pd.DataFrame) -> list[dict[str, Any]]:
    if bars.empty or "symbol" not in bars:
        return []
    moneyflow_symbols = set(moneyflow["symbol"].dropna().astype(str)) if "symbol" in moneyflow else set()
    rows = []
    for symbol, group in bars.groupby("symbol", sort=True):
        rows.append(
            {
                "symbol": str(symbol),
                "bar_rows": int(len(group)),
                "date_start": _date_value(group["date"].min()) if "date" in group else None,
                "date_end": _date_value(group["date"].max()) if "date" in group else None,
                "has_moneyflow": str(symbol) in moneyflow_symbols,
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
