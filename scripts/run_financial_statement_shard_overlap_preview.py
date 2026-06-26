from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_DIR = Path("data/reports/financial_statement_shard_overlap_preview")


def run_financial_statement_shard_overlap_preview(
    *,
    plan_json: str | Path,
    shard_id: int,
    symbol_offset: int,
    symbol_limit: int,
    financial_roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    plan = json.loads(Path(plan_json).read_text(encoding="utf-8"))
    symbols = _select_symbols(plan, shard_id=shard_id, symbol_offset=symbol_offset, symbol_limit=symbol_limit)
    existing_asset_ids = _collect_existing_asset_ids([Path(root) for root in financial_roots])
    existing_symbols = [symbol for symbol in symbols if _ts_code_to_asset_id(symbol) in existing_asset_ids]
    net_new_symbols = [symbol for symbol in symbols if symbol not in existing_symbols]
    result = {
        "stage": "financial_statement_shard_overlap_preview",
        "plan_json": str(plan_json),
        "shard_id": shard_id,
        "symbol_offset": symbol_offset,
        "symbol_limit": symbol_limit,
        "symbols": symbols,
        "existing_symbols": existing_symbols,
        "net_new_symbols": net_new_symbols,
        "summary": {
            "symbol_count": len(symbols),
            "existing_symbol_count": len(existing_symbols),
            "net_new_symbol_count": len(net_new_symbols),
            "net_new_ratio": (len(net_new_symbols) / len(symbols)) if symbols else 0.0,
            "financial_root_count": len(financial_roots),
        },
    }
    _write_outputs(result, Path(output_dir))
    return result


def _select_symbols(plan: dict[str, Any], *, shard_id: int, symbol_offset: int, symbol_limit: int) -> list[str]:
    shards = plan.get("shards", [])
    for shard in shards:
        if int(shard.get("shard_id", -1)) == int(shard_id):
            symbols = [str(symbol) for symbol in shard.get("symbols", [])]
            return symbols[symbol_offset : symbol_offset + symbol_limit]
    raise ValueError(f"shard_id {shard_id} not found in plan")


def _collect_existing_asset_ids(financial_roots: list[Path]) -> set[str]:
    existing: set[str] = set()
    for root in financial_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.parquet"):
            existing.update(_read_asset_ids(path))
    return existing


def _read_asset_ids(path: Path) -> set[str]:
    try:
        frame = pd.read_parquet(path, columns=["asset_id"])
        return set(frame["asset_id"].dropna().astype(str))
    except Exception:
        pass
    try:
        frame = pd.read_parquet(path, columns=["ts_code"])
        return {_ts_code_to_asset_id(symbol) for symbol in frame["ts_code"].dropna().astype(str)}
    except Exception:
        return set()


def _ts_code_to_asset_id(ts_code: str) -> str:
    code, _, suffix = ts_code.partition(".")
    suffix = suffix.upper()
    if suffix == "SZ":
        return f"CN_XSHE_{code}"
    if suffix == "SH":
        return f"CN_XSHG_{code}"
    if suffix == "BJ":
        return f"CN_XBSE_{code}"
    return ts_code


def _write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "financial_statement_shard_overlap_preview.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "financial_statement_shard_overlap_preview.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Financial Statement Shard Overlap Preview",
        "",
        f"- Shard: {result['shard_id']}",
        f"- Symbol offset: {result['symbol_offset']}",
        f"- Symbol limit: {result['symbol_limit']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Existing symbols: {summary['existing_symbol_count']}",
        f"- Net-new symbols: {summary['net_new_symbol_count']}",
        f"- Net-new ratio: {summary['net_new_ratio']:.2%}",
        "",
        "## Net-New Symbols",
        "",
        ", ".join(result["net_new_symbols"]) or "None",
        "",
        "## Already In Aggregate Sources",
        "",
        ", ".join(result["existing_symbols"]) or "None",
        "",
    ]
    return "\n".join(lines)


def _default_financial_roots(root: Path) -> list[Path]:
    processed = root / "data" / "processed"
    if not processed.exists():
        return []
    return [
        path
        for path in sorted(processed.iterdir())
        if path.is_dir() and ("financial_statement" in path.name or "financial_pit_signal" in path.name)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview net-new symbols before a financial statement shard backfill.")
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--shard-id", type=int, required=True)
    parser.add_argument("--symbol-offset", type=int, required=True)
    parser.add_argument("--symbol-limit", type=int, required=True)
    parser.add_argument("--financial-root", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    roots = [Path(root) for root in args.financial_root] or _default_financial_roots(Path("."))
    result = run_financial_statement_shard_overlap_preview(
        plan_json=args.plan_json,
        shard_id=args.shard_id,
        symbol_offset=args.symbol_offset,
        symbol_limit=args.symbol_limit,
        financial_roots=roots,
        output_dir=args.output_dir,
    )
    print(json.dumps({"summary": result["summary"], "net_new_symbols": result["net_new_symbols"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
