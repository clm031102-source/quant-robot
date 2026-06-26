from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_tradeability_mask_cache import (  # noqa: E402
    STAGE,
    build_cn_stock_tradeability_mask_cache,
    render_markdown,
)


DEFAULT_OUTPUT_ROOT = Path("data/processed/cn_stock_tradeability_mask_cache")


def run_cn_stock_tradeability_mask_cache_cli(
    *,
    bars_path: str | Path | Iterable[str | Path],
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    market: str = "CN",
    years: Iterable[int] | None = None,
    stock_basic_path: str | Path | None = None,
    stk_limit_path: str | Path | None = None,
    suspension_path: str | Path | None = None,
    namechange_path: str | Path | None = None,
) -> dict[str, Any]:
    bars_paths = _as_paths(bars_path)
    selected_years = (
        tuple(int(year) for year in years)
        if years is not None
        else tuple(sorted({year for path in bars_paths for year in _discover_years(path)}))
    )
    if not selected_years:
        raise ValueError("No years discovered for bars_path")

    reports = []
    for year in selected_years:
        report = build_cn_stock_tradeability_mask_cache(
            bars=_read_bars_frame(bars_paths, year=year),
            stock_basic=_read_frame(stock_basic_path, year=year) if stock_basic_path is not None else None,
            stk_limit=_read_frame(stk_limit_path, year=year) if stk_limit_path is not None else None,
            suspension=_read_frame(suspension_path, year=year) if suspension_path is not None else None,
            namechange=_read_frame(namechange_path) if namechange_path is not None else None,
            output_root=output_root,
            market=market,
        )
        reports.append(report)

    aggregate = _aggregate_reports(reports, market=market)
    _write_aggregate(output_root, aggregate)
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reusable year-sliced CN stock official tradeability mask cache.")
    parser.add_argument("--bars-path", action="append", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--year", action="append", type=int, default=None)
    parser.add_argument("--stock-basic-path")
    parser.add_argument("--stk-limit-path")
    parser.add_argument("--suspension-path")
    parser.add_argument("--namechange-path")
    args = parser.parse_args()
    report = run_cn_stock_tradeability_mask_cache_cli(
        bars_path=tuple(Path(path) for path in args.bars_path),
        output_root=Path(args.output_root),
        market=args.market,
        years=tuple(args.year) if args.year else None,
        stock_basic_path=Path(args.stock_basic_path) if args.stock_basic_path else None,
        stk_limit_path=Path(args.stk_limit_path) if args.stk_limit_path else None,
        suspension_path=Path(args.suspension_path) if args.suspension_path else None,
        namechange_path=Path(args.namechange_path) if args.namechange_path else None,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def _aggregate_reports(reports: list[dict[str, Any]], *, market: str) -> dict[str, Any]:
    years: list[int] = []
    rows = 0
    entry_blocked = 0
    exit_blocked = 0
    official_hits = 0
    metadata_hits = 0
    stock_basic_supplied_flags: list[bool] = []
    flag_count_keys = [
        "suspended_official_rows",
        "limit_up_official_rows",
        "limit_down_official_rows",
        "st_flag_official_rows",
        "new_listing_flag_rows",
        "delisted_or_inactive_flag_rows",
        "board_permission_blocked_rows",
    ]
    flag_counts = {key: 0 for key in flag_count_keys}
    written: list[str] = []
    for report in reports:
        summary = report.get("summary", {})
        years.extend(int(year) for year in summary.get("years", []))
        rows += int(summary.get("rows", 0))
        entry_blocked += int(summary.get("entry_blocked_rows", 0))
        exit_blocked += int(summary.get("exit_blocked_rows", 0))
        official_hits += int(summary.get("official_mask_hit_rows", 0))
        metadata_hits += int(summary.get("metadata_mask_hit_rows", 0))
        stock_basic_supplied_flags.append(bool(summary.get("stock_basic_supplied", False)))
        for key in flag_count_keys:
            flag_counts[key] += int(summary.get(key, 0))
        written.extend(str(path) for path in report.get("written_files", []))
    return {
        "stage": STAGE,
        "market": market.upper(),
        "summary": {
            "rows": rows,
            "years": sorted(set(years)),
            "entry_blocked_rows": entry_blocked,
            "exit_blocked_rows": exit_blocked,
            "official_mask_hit_rows": official_hits,
            "metadata_mask_hit_rows": metadata_hits,
            "stock_basic_supplied_for_all_years": bool(stock_basic_supplied_flags)
            and all(stock_basic_supplied_flags),
            "written_files": len(written),
            **flag_counts,
        },
        "written_files": written,
        "live_boundary_allowed": False,
    }


def _write_aggregate(output_root: str | Path, report: dict[str, Any]) -> None:
    path = Path(output_root)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{STAGE}.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (path / f"{STAGE}.md").write_text(render_markdown(report), encoding="utf-8")


def _read_bars_frame(paths: Iterable[str | Path], *, year: int) -> pd.DataFrame:
    frames = [_read_frame(path, year=year) for path in paths]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    dedupe_keys = ["date", "asset_id"] if "asset_id" in frame.columns else ["date", "symbol"]
    if all(column in frame.columns for column in dedupe_keys):
        frame["_dedupe_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
        frame["_dedupe_key"] = frame[dedupe_keys[1]].astype(str)
        frame = (
            frame.drop_duplicates(subset=["_dedupe_date", "_dedupe_key"], keep="last")
            .drop(columns=["_dedupe_date", "_dedupe_key"])
            .reset_index(drop=True)
        )
    return frame


def _read_frame(path: str | Path | None, *, year: int | None = None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    source = Path(path)
    if source.is_dir():
        year_dirs = [source] if source.name == f"year={year}" else sorted(source.rglob(f"year={year}")) if year else []
        if year_dirs:
            files = [file for year_dir in year_dirs for file in sorted(year_dir.glob("*.parquet")) + sorted(year_dir.glob("*.csv"))]
        else:
            files = sorted(source.rglob("*.parquet")) or sorted(source.rglob("*.csv"))
        if not files:
            return pd.DataFrame()
        return pd.concat([_read_frame(file, year=year) for file in files], ignore_index=True)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(source)
    elif suffix == ".parquet":
        frame = pd.read_parquet(source)
    else:
        raise ValueError(f"Unsupported input file type for {source}")
    if year is not None and "date" in frame.columns:
        dates = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame[dates.dt.year == int(year)].reset_index(drop=True)
    return frame


def _discover_years(path: str | Path) -> list[int]:
    source = Path(path)
    years = sorted(
        {
            int(item.name.split("=", 1)[1])
            for item in source.rglob("year=*")
            if item.is_dir() and item.name.split("=", 1)[1].isdigit()
        }
    )
    if years:
        return years
    frame = _read_frame(source)
    if "date" not in frame.columns:
        return []
    return sorted(pd.to_datetime(frame["date"], errors="coerce").dropna().dt.year.astype(int).unique().tolist())


def _as_paths(path_or_paths: str | Path | Iterable[str | Path]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, (str, Path)):
        return (Path(path_or_paths),)
    return tuple(Path(path) for path in path_or_paths)


if __name__ == "__main__":
    main()
