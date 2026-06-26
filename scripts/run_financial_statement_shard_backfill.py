from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.ingest.tushare_financial_statements import (  # noqa: E402
    ENDPOINT_COLUMNS,
    REQUIRED_COLUMN_GROUPS,
    run_tushare_financial_statement_ingest,
)
from quant_robot.ops.tushare_financial_pit_readiness import audit_tushare_financial_pit_readiness  # noqa: E402


DEFAULT_PLAN_JSON = Path("data/reports/round236_financial_statement_symbol_shard_plan_20260625/financial_statement_symbol_shard_plan.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/round236_financial_statement_shard_backfill")
STAGE = "tushare_financial_statement_shard_backfill"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
GROUP_BLOCKER_PREFIX = "missing_required_financial_column_group:"


def run_financial_statement_shard_backfill_cli(
    *,
    plan_json: str | Path = DEFAULT_PLAN_JSON,
    shard_id: int,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    symbol_offset: int = 0,
    symbol_limit: int | None = None,
    max_endpoint_requests: int = 3000,
    adapter_max_retries: int = 3,
    adapter_retry_sleep_seconds: float = 1.0,
    adapter_request_sleep_seconds: float = 0.0,
    stock_basic_path: str | Path | None = None,
    adapter: object | None = None,
) -> dict[str, Any]:
    plan = _read_plan(plan_json)
    shard = _select_shard(plan, shard_id)
    periods = [str(period) for period in plan.get("periods", []) or []]
    symbols = _slice_symbols([str(symbol) for symbol in shard.get("symbols", []) or []], symbol_offset, symbol_limit)
    symbol_periods, skipped_symbol_periods = _filter_prelisting_symbol_periods(symbols, periods, stock_basic_path)
    active_symbol_period_count = sum(len(values) for values in symbol_periods.values())
    endpoint_request_count = active_symbol_period_count * len(ENDPOINT_COLUMNS)
    if endpoint_request_count > max_endpoint_requests:
        raise RuntimeError(
            "Financial statement shard endpoint request budget blocked: "
            f"{endpoint_request_count} exceeds {max_endpoint_requests}"
        )
    if not symbols:
        raise RuntimeError("Financial statement shard backfill has no symbols after offset/limit slicing")
    if not periods:
        raise RuntimeError("Financial statement shard backfill plan has no periods")
    if active_symbol_period_count <= 0:
        raise RuntimeError("Financial statement shard backfill has no symbol-periods after stock_basic filtering")

    output_path = Path(output_dir)
    active_adapter = adapter or TushareAdapter(
        max_retries=adapter_max_retries,
        retry_sleep_seconds=adapter_retry_sleep_seconds,
        request_sleep_seconds=adapter_request_sleep_seconds,
    )
    if skipped_symbol_periods:
        ingests = []
        for symbol in symbols:
            filtered_periods = symbol_periods.get(symbol, [])
            if not filtered_periods:
                continue
            ingests.append(
                run_tushare_financial_statement_ingest(
                    active_adapter,
                    filtered_periods,
                    output_path,
                    resume=True,
                    market="CN",
                    ts_codes=[symbol],
                    empty_response_policy="record",
                )
            )
        ingest = _combine_ingest_results(ingests)
    else:
        ingest = run_tushare_financial_statement_ingest(
            active_adapter,
            periods,
            output_path,
            resume=True,
            market="CN",
            ts_codes=symbols,
            empty_response_policy="record",
        )
    readiness = audit_tushare_financial_pit_readiness(
        [output_path],
        required_column_groups=REQUIRED_COLUMN_GROUPS,
    )
    readiness_summary = readiness["summary"]
    quality_summary = ingest.get("summary", {}) if isinstance(ingest.get("summary"), dict) else {}
    quality_blockers = [str(blocker) for blocker in quality_summary.get("blockers", []) or []]
    readiness_blockers = [str(blocker) for blocker in readiness_summary.get("blockers", []) or []]
    blockers = sorted(dict.fromkeys(quality_blockers + readiness_blockers))
    result = {
        "stage": STAGE,
        "plan_json": str(plan_json),
        "shard": _shard_without_symbols(shard),
        "selected_symbols": symbols,
        "periods": periods,
        "ingest": ingest,
        "readiness": _without_markdown(readiness),
        "summary": {
            "passes": bool(quality_summary.get("passes", False)) and bool(readiness_summary["passes"]),
            "blockers": blockers,
            "shard_id": shard_id,
            "symbol_offset": symbol_offset,
            "symbol_limit": symbol_limit,
            "symbol_count": len(symbols),
            "period_count": len(periods),
            "endpoint_count": len(ENDPOINT_COLUMNS),
            "endpoint_request_count": endpoint_request_count,
            "max_endpoint_requests": max_endpoint_requests,
            "processed_rows": ingest["processed_rows"],
            "empty_request_count": len(ingest.get("empty_requests", []) or []),
            "skipped_request_count": len(ingest.get("skipped_requests", []) or []),
            "planned_symbol_period_count": len(symbols) * len(periods),
            "active_symbol_period_count": active_symbol_period_count,
            "prelisting_skipped_symbol_period_count": len(skipped_symbol_periods),
            "prelisting_skipped_endpoint_request_count": len(skipped_symbol_periods) * len(ENDPOINT_COLUMNS),
            "required_column_group_count": quality_summary.get(
                "required_column_group_count",
                readiness_summary["required_column_group_count"],
            ),
            "required_column_groups_passing": quality_summary.get(
                "required_column_groups_passing",
                readiness_summary["required_column_groups_passing"],
            ),
            "quality_blockers": quality_blockers,
            "readiness_blockers": readiness_blockers,
        },
        "prelisting_skipped_symbol_periods": skipped_symbol_periods,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    _write_report(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Tushare financial statement backfill shard or subshard.")
    parser.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    parser.add_argument("--shard-id", type=int, required=True)
    parser.add_argument("--symbol-offset", type=int, default=0)
    parser.add_argument("--symbol-limit", type=int, default=0)
    parser.add_argument("--max-endpoint-requests", type=int, default=3000)
    parser.add_argument("--adapter-max-retries", type=int, default=3)
    parser.add_argument("--adapter-retry-sleep-seconds", type=float, default=1.0)
    parser.add_argument("--adapter-request-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--stock-basic-path", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_financial_statement_shard_backfill_cli(
        plan_json=Path(args.plan_json),
        shard_id=args.shard_id,
        symbol_offset=args.symbol_offset,
        symbol_limit=args.symbol_limit or None,
        max_endpoint_requests=args.max_endpoint_requests,
        adapter_max_retries=args.adapter_max_retries,
        adapter_retry_sleep_seconds=args.adapter_retry_sleep_seconds,
        adapter_request_sleep_seconds=args.adapter_request_sleep_seconds,
        stock_basic_path=Path(args.stock_basic_path) if args.stock_basic_path else None,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps({"summary": result["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


def _read_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _select_shard(plan: dict[str, Any], shard_id: int) -> dict[str, Any]:
    for shard in plan.get("shards", []) or []:
        if int(shard.get("shard_id", -1)) == shard_id:
            return dict(shard)
    raise RuntimeError(f"Financial statement shard id not found in plan: {shard_id}")


def _slice_symbols(symbols: list[str], offset: int, limit: int | None) -> list[str]:
    if offset < 0:
        raise ValueError("symbol_offset must be non-negative")
    sliced = symbols[offset:]
    if limit is not None:
        if limit < 0:
            raise ValueError("symbol_limit must be non-negative")
        sliced = sliced[:limit]
    return sliced


def _shard_without_symbols(shard: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in shard.items() if key != "symbols"}


def _filter_prelisting_symbol_periods(
    symbols: list[str],
    periods: list[str],
    stock_basic_path: str | Path | None,
) -> tuple[dict[str, list[str]], list[str]]:
    output = {symbol: list(periods) for symbol in symbols}
    if not stock_basic_path:
        return output, []
    list_dates = _load_stock_basic_list_dates(stock_basic_path)
    skipped: list[str] = []
    for symbol in symbols:
        list_date = list_dates.get(symbol)
        if pd.isna(list_date):
            continue
        kept = []
        for period in periods:
            period_date = pd.to_datetime(str(period), format="%Y%m%d", errors="coerce")
            if pd.isna(period_date) or period_date.date() >= list_date:
                kept.append(period)
            else:
                skipped.append(f"{symbol}:{period}:before_list_date:{list_date.isoformat()}")
        output[symbol] = kept
    return output, skipped


def _load_stock_basic_list_dates(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("*.parquet")) + sorted(root.rglob("*.csv"))
    frames = []
    for file in files:
        if file.suffix.lower() == ".parquet":
            frames.append(pd.read_parquet(file))
        elif file.suffix.lower() == ".csv":
            frames.append(pd.read_csv(file))
    if not frames:
        return {}
    frame = pd.concat(frames, ignore_index=True)
    symbol_column = "symbol" if "symbol" in frame else "ts_code" if "ts_code" in frame else None
    if not symbol_column or "list_date" not in frame:
        return {}
    frame = frame[[symbol_column, "list_date"]].rename(columns={symbol_column: "symbol"}).dropna(subset=["symbol"]).copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["list_date"] = _parse_stock_basic_list_date(frame["list_date"])
    frame = frame.dropna(subset=["list_date"]).drop_duplicates("symbol", keep="last")
    return dict(zip(frame["symbol"], frame["list_date"], strict=False))


def _parse_stock_basic_list_date(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.strip()
    parsed = pd.to_datetime(text, errors="coerce")
    ymd_mask = text.str.fullmatch(r"\d{8}").fillna(False)
    if ymd_mask.any():
        parsed.loc[ymd_mask] = pd.to_datetime(text.loc[ymd_mask], format="%Y%m%d", errors="coerce")
    return parsed.dt.date


def _combine_ingest_results(ingests: list[dict[str, Any]]) -> dict[str, Any]:
    if not ingests:
        return {
            "source": "tushare",
            "dataset": "financial_statement",
            "market": "CN",
            "downloaded_periods": [],
            "skipped_periods": [],
            "downloaded_requests": [],
            "skipped_requests": [],
            "empty_requests": [],
            "processed_rows": 0,
        }
    combined = dict(ingests[-1])
    for key in ["downloaded_periods", "skipped_periods", "downloaded_requests", "skipped_requests", "empty_requests"]:
        values: list[Any] = []
        for ingest in ingests:
            values.extend(ingest.get(key, []) or [])
        combined[key] = sorted(dict.fromkeys(values)) if key.endswith("_periods") else values
    combined["processed_rows"] = sum(int(ingest.get("processed_rows", 0)) for ingest in ingests)
    quality_report = _combine_quality_reports([ingest.get("quality_report", {}) for ingest in ingests])
    if quality_report:
        combined["quality_report"] = quality_report
        combined["summary"] = quality_report["summary"]
    return combined


def _combine_quality_reports(reports: list[Any]) -> dict[str, Any]:
    valid_reports = [report for report in reports if isinstance(report, dict) and isinstance(report.get("summary"), dict)]
    if not valid_reports:
        return {}
    combined = dict(valid_reports[-1])
    summaries = [report["summary"] for report in valid_reports]
    required_column_groups = _combine_required_column_groups(valid_reports)
    group_blockers = [
        f"{GROUP_BLOCKER_PREFIX}{group['group_id']}" for group in required_column_groups if not bool(group.get("passes"))
    ]
    other_blockers = [
        str(blocker)
        for summary in summaries
        for blocker in summary.get("blockers", []) or []
        if not str(blocker).startswith(GROUP_BLOCKER_PREFIX)
    ]
    blockers = sorted(dict.fromkeys(other_blockers + group_blockers))
    combined_summary = dict(summaries[-1])
    combined_summary.update(
        {
            "passes": not blockers,
            "blockers": blockers,
            "rows": sum(int(summary.get("rows", 0) or 0) for summary in summaries),
            "assets": sum(int(summary.get("assets", 0) or 0) for summary in summaries),
            "duplicate_rows": sum(int(summary.get("duplicate_rows", 0) or 0) for summary in summaries),
            "missing_asset_id_rows": sum(int(summary.get("missing_asset_id_rows", 0) or 0) for summary in summaries),
            "required_column_group_count": len(required_column_groups),
            "required_column_groups_passing": int(sum(1 for group in required_column_groups if group.get("passes"))),
            "ann_date_start": _min_optional_date(summary.get("ann_date_start") for summary in summaries),
            "ann_date_end": _max_optional_date(summary.get("ann_date_end") for summary in summaries),
            "report_period_start": _min_optional_date(summary.get("report_period_start") for summary in summaries),
            "report_period_end": _max_optional_date(summary.get("report_period_end") for summary in summaries),
        }
    )
    combined["required_column_groups"] = required_column_groups
    combined["summary"] = combined_summary
    return combined


def _combine_required_column_groups(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for report in reports:
        for group in report.get("required_column_groups", []) or []:
            if not isinstance(group, dict) or not group.get("group_id"):
                continue
            group_id = str(group["group_id"])
            if group_id not in groups:
                order.append(group_id)
                groups[group_id] = {
                    "group_id": group_id,
                    "required_columns": list(group.get("required_columns", []) or []),
                    "non_null_columns": set(),
                }
            if not groups[group_id]["required_columns"] and group.get("required_columns"):
                groups[group_id]["required_columns"] = list(group.get("required_columns", []) or [])
            groups[group_id]["non_null_columns"].update(str(column) for column in group.get("non_null_columns", []) or [])
    for group_id, columns in REQUIRED_COLUMN_GROUPS.items():
        if group_id not in groups:
            order.append(group_id)
            groups[group_id] = {
                "group_id": group_id,
                "required_columns": list(columns),
                "non_null_columns": set(),
            }
        elif not groups[group_id]["required_columns"]:
            groups[group_id]["required_columns"] = list(columns)
    combined_groups: list[dict[str, Any]] = []
    for group_id in order:
        group = groups[group_id]
        required_columns = [str(column) for column in group.get("required_columns", []) or []]
        non_null_columns = [column for column in required_columns if column in group["non_null_columns"]]
        missing_columns = [column for column in required_columns if column not in group["non_null_columns"]]
        combined_groups.append(
            {
                "group_id": group_id,
                "required_columns": required_columns,
                "passes": not missing_columns,
                "missing_columns": missing_columns,
                "non_null_columns": non_null_columns,
            }
        )
    return combined_groups


def _min_optional_date(values: Any) -> str | None:
    clean = [str(value) for value in values if value]
    return min(clean) if clean else None


def _max_optional_date(values: Any) -> str | None:
    clean = [str(value) for value in values if value]
    return max(clean) if clean else None


def _write_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_report = result.get("ingest", {}).get("quality_report", {})
    if isinstance(quality_report, dict) and quality_report:
        (output_dir / "financial_statement_quality_report.json").write_text(
            json.dumps(quality_report, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
    (output_dir / "financial_statement_shard_backfill.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (output_dir / "financial_statement_shard_backfill.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Financial Statement Shard Backfill",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Shard id: {summary['shard_id']}",
        f"- Symbol offset: {summary['symbol_offset']}",
        f"- Symbol limit: {summary['symbol_limit']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Endpoint requests: {summary['endpoint_request_count']}",
        f"- Max endpoint requests: {summary['max_endpoint_requests']}",
        f"- Processed rows: {summary['processed_rows']}",
        f"- Planned symbol-periods: {summary['planned_symbol_period_count']}",
        f"- Active symbol-periods: {summary['active_symbol_period_count']}",
        f"- Pre-listing skipped symbol-periods: {summary['prelisting_skipped_symbol_period_count']}",
        f"- Pre-listing skipped endpoint requests: {summary['prelisting_skipped_endpoint_request_count']}",
        f"- Required column groups passing: {summary['required_column_groups_passing']} / {summary['required_column_group_count']}",
        f"- Empty requests: {summary['empty_request_count']}",
        f"- Skipped requests: {summary['skipped_request_count']}",
        f"- Quality blockers: {', '.join(summary.get('quality_blockers', [])) or 'none'}",
        f"- Readiness blockers: {', '.join(summary.get('readiness_blockers', [])) or 'none'}",
        f"- Blockers: {', '.join(summary.get('blockers', [])) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## Selected Symbols",
        "",
    ]
    for symbol in result.get("selected_symbols", []) or []:
        lines.append(f"- `{symbol}`")
    if result.get("prelisting_skipped_symbol_periods"):
        lines.extend(["", "## Pre-Listing Skipped Symbol-Periods", ""])
        for item in result.get("prelisting_skipped_symbol_periods", []) or []:
            lines.append(f"- `{item}`")
    return "\n".join(lines) + "\n"


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}


if __name__ == "__main__":
    main()
