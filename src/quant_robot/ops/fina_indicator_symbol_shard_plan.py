from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "tushare_fina_indicator_symbol_universe_shard_plan"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_fina_indicator_symbol_shard_plan(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    symbols_per_shard: int = 100,
    max_requests_per_shard: int = 5000,
    exclude_suffixes: list[str] | None = None,
    symbol_metadata: pd.DataFrame | None = None,
    stratify_by: list[str] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_symbols(symbols)
    excluded_suffix_set = {suffix.upper().lstrip(".") for suffix in (exclude_suffixes or [])}
    included = [symbol for symbol in normalized if _suffix(symbol) not in excluded_suffix_set]
    excluded = [symbol for symbol in normalized if _suffix(symbol) in excluded_suffix_set]
    metadata = _normalize_symbol_metadata(symbol_metadata)
    requested_strata = _normalize_strata_columns(stratify_by)
    ordered_symbols = _stratified_symbol_order(included, metadata=metadata, stratify_by=requested_strata)
    periods = _quarter_end_periods(start_period, end_period)
    shards = _build_shards(ordered_symbols, periods, symbols_per_shard, metadata=metadata)
    blockers = _blockers(
        symbols=included,
        periods=periods,
        symbols_per_shard=symbols_per_shard,
        max_requests_per_shard=max_requests_per_shard,
        shards=shards,
        stratify_by=requested_strata,
        symbol_metadata=metadata,
    )
    stratification = _stratification_summary(
        ordered_symbols,
        metadata=metadata,
        stratify_by=requested_strata,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "symbol_count": len(included),
            "excluded_symbol_count": len(excluded),
            "period_count": len(periods),
            "total_request_count": len(included) * len(periods),
            "shard_count": len(shards),
            "symbols_per_shard": symbols_per_shard,
            "max_requests_per_shard": max_requests_per_shard,
            "stratification": stratification,
        },
        "periods": periods,
        "excluded_symbols": excluded,
        "shards": shards,
        "execution_policy": {
            "planner_calls_tushare": False,
            "commit_data_allowed": False,
            "requires_resume": True,
            "requires_empty_response_recording": True,
            "requires_duplicate_row_gate": True,
            "requires_pit_readiness_after_each_shard": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_fina_indicator_symbol_shard_plan_markdown(result)
    return result


def write_fina_indicator_symbol_shard_plan(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "fina_indicator_symbol_shard_plan.json").write_text(
        json.dumps(_without_markdown(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "fina_indicator_symbol_shard_plan.md").write_text(
        render_fina_indicator_symbol_shard_plan_markdown(result),
        encoding="utf-8",
    )


def render_fina_indicator_symbol_shard_plan_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Fina Indicator Symbol Universe Shard Plan",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Excluded symbols: {summary['excluded_symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Total requests: {summary['total_request_count']}",
        f"- Shards: {summary['shard_count']}",
        f"- Symbols per shard: {summary['symbols_per_shard']}",
        f"- Max requests per shard: {summary['max_requests_per_shard']}",
        f"- Stratification enabled: {_dict(summary.get('stratification')).get('enabled', False)}",
        f"- Stratification columns: {', '.join(_list(_dict(summary.get('stratification')).get('columns'))) or 'none'}",
        f"- Strata: {_dict(summary.get('stratification')).get('stratum_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## First Shards",
        "",
    ]
    for shard in result.get("shards", [])[:10]:
        lines.append(
            "- shard {shard_id}: symbols={symbol_count}, requests={request_count}, industries={industry_count}, exchanges={exchange_count}, list_years={list_year_count}, first={first_symbol}, last={last_symbol}".format(
                **shard
            )
        )
    return "\n".join(lines) + "\n"


def _normalize_symbols(symbols: list[str]) -> list[str]:
    seen = set()
    normalized = []
    for symbol in symbols:
        value = str(symbol).strip().upper()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return sorted(normalized)


def _quarter_end_periods(start_period: str, end_period: str) -> list[str]:
    quarters = pd.period_range(start=pd.to_datetime(start_period), end=pd.to_datetime(end_period), freq="Q")
    return [period.end_time.strftime("%Y%m%d") for period in quarters]


def _build_shards(
    symbols: list[str],
    periods: list[str],
    symbols_per_shard: int,
    *,
    metadata: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    if symbols_per_shard < 1:
        return []
    shards = []
    metadata_by_symbol = _metadata_by_symbol(metadata)
    for index in range(0, len(symbols), symbols_per_shard):
        shard_symbols = symbols[index : index + symbols_per_shard]
        shard_metadata = _metadata_for_symbols(shard_symbols, metadata_by_symbol)
        shards.append(
            {
                "shard_id": len(shards) + 1,
                "symbol_count": len(shard_symbols),
                "period_count": len(periods),
                "request_count": len(shard_symbols) * len(periods),
                "first_symbol": shard_symbols[0] if shard_symbols else "",
                "last_symbol": shard_symbols[-1] if shard_symbols else "",
                "industry_count": _nunique(shard_metadata, "industry"),
                "exchange_count": _nunique(shard_metadata, "exchange"),
                "list_year_count": _nunique(shard_metadata, "list_year"),
                "symbols": shard_symbols,
            }
        )
    return shards


def _blockers(
    *,
    symbols: list[str],
    periods: list[str],
    symbols_per_shard: int,
    max_requests_per_shard: int,
    shards: list[dict[str, Any]],
    stratify_by: list[str],
    symbol_metadata: pd.DataFrame | None,
) -> list[str]:
    blockers: list[str] = []
    if not symbols:
        blockers.append("missing_symbols")
    if not periods:
        blockers.append("missing_periods")
    if symbols_per_shard < 1:
        blockers.append("invalid_symbols_per_shard")
    if max_requests_per_shard < 1:
        blockers.append("invalid_max_requests_per_shard")
    if any(shard["request_count"] > max_requests_per_shard for shard in shards):
        blockers.append("shard_request_count_exceeds_budget")
    if stratify_by and (symbol_metadata is None or symbol_metadata.empty):
        blockers.append("stratification_requested_without_symbol_metadata")
    return blockers


def _suffix(symbol: str) -> str:
    parts = symbol.split(".")
    return parts[-1].upper() if len(parts) > 1 else ""


def _normalize_symbol_metadata(symbol_metadata: pd.DataFrame | None) -> pd.DataFrame | None:
    if symbol_metadata is None or symbol_metadata.empty:
        return None
    frame = symbol_metadata.copy()
    if "symbol" not in frame.columns and "ts_code" in frame.columns:
        frame = frame.rename(columns={"ts_code": "symbol"})
    if "symbol" not in frame.columns:
        return None
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    for column in ("industry", "exchange", "market", "stock_market"):
        if column in frame.columns:
            frame[column] = frame[column].fillna("unknown").astype(str).str.strip().replace("", "unknown")
    if "exchange" not in frame.columns and "stock_market" in frame.columns:
        frame["exchange"] = frame["stock_market"]
    if "list_year" not in frame.columns and "list_date" in frame.columns:
        dates = pd.to_datetime(frame["list_date"], errors="coerce")
        frame["list_year"] = dates.dt.year.astype("Int64").astype(str).replace("<NA>", "unknown")
    for column in ("industry", "exchange", "list_year"):
        if column not in frame.columns:
            frame[column] = "unknown"
    return frame.drop_duplicates("symbol", keep="last").reset_index(drop=True)


def _normalize_strata_columns(stratify_by: list[str] | None) -> list[str]:
    columns = []
    for item in stratify_by or []:
        column = str(item).strip()
        if column and column not in columns:
            columns.append(column)
    return columns


def _stratified_symbol_order(
    symbols: list[str],
    *,
    metadata: pd.DataFrame | None,
    stratify_by: list[str],
) -> list[str]:
    if not stratify_by or metadata is None or metadata.empty:
        return symbols
    metadata_by_symbol = _metadata_by_symbol(metadata)
    primary_column = stratify_by[0]
    buckets: dict[str, list[tuple[tuple[str, ...], str]]] = {}
    for symbol in symbols:
        row = metadata_by_symbol.get(symbol)
        primary_key = _metadata_value(row, primary_column)
        full_key = tuple(_metadata_value(row, column) for column in stratify_by)
        buckets.setdefault(primary_key, []).append((full_key, symbol))
    for bucket_symbols in buckets.values():
        bucket_symbols.sort()
    ordered = []
    keys = sorted(buckets)
    while any(buckets[key] for key in keys):
        for key in keys:
            if buckets[key]:
                _, symbol = buckets[key].pop(0)
                ordered.append(symbol)
    return ordered


def _stratification_summary(
    symbols: list[str],
    *,
    metadata: pd.DataFrame | None,
    stratify_by: list[str],
) -> dict[str, Any]:
    if not stratify_by:
        return {"enabled": False, "columns": [], "stratum_count": 0}
    if metadata is None or metadata.empty:
        return {"enabled": True, "columns": stratify_by, "stratum_count": 0}
    metadata_by_symbol = _metadata_by_symbol(metadata)
    strata = {
        tuple(_metadata_value(metadata_by_symbol.get(symbol), column) for column in stratify_by)
        for symbol in symbols
    }
    return {"enabled": True, "columns": stratify_by, "stratum_count": len(strata)}


def _metadata_by_symbol(metadata: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if metadata is None or metadata.empty:
        return {}
    return {str(row["symbol"]): dict(row) for row in metadata.to_dict(orient="records")}


def _metadata_for_symbols(symbols: list[str], metadata_by_symbol: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = [metadata_by_symbol[symbol] for symbol in symbols if symbol in metadata_by_symbol]
    return pd.DataFrame(rows)


def _metadata_value(row: dict[str, Any] | None, column: str) -> str:
    if row is None:
        return "unknown"
    value = row.get(column, "unknown")
    if pd.isna(value):
        return "unknown"
    text = str(value).strip()
    return text or "unknown"


def _nunique(frame: pd.DataFrame, column: str) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    return int(frame[column].dropna().astype(str).nunique())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}
