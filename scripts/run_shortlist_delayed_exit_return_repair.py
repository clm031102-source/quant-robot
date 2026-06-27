from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_delayed_exit_return_repair import (  # noqa: E402
    build_delayed_exit_return_repair,
    write_delayed_exit_return_repair,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_delayed_exit_return_repair")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute trade weighted returns by delaying blocked exits to the first sellable date."
    )
    parser.add_argument("--trades", required=True)
    parser.add_argument("--bars-source", action="append", required=True)
    parser.add_argument("--masks-source", action="append", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-exit-delay-days", type=int, default=10)
    parser.add_argument("--price-column", default="adj_close")
    parser.add_argument("--output-return-column", default="delayed_exit_weighted_return")
    parser.add_argument("--override-cost-rate", type=float, default=None)
    args = parser.parse_args()

    trades = _read_source(Path(args.trades))
    assets = set(trades["asset_id"].astype(str)) if "asset_id" in trades else set()
    date_start = pd.to_datetime(trades["entry_date"], errors="coerce").min() if "entry_date" in trades else None
    date_end = pd.to_datetime(trades["exit_date"], errors="coerce").max() if "exit_date" in trades else None
    if pd.notna(date_end):
        date_end = date_end + pd.Timedelta(days=int(args.max_exit_delay_days))

    bars = _read_sources(
        [Path(value) for value in args.bars_source],
        columns=("asset_id", "date", args.price_column),
        assets=assets,
        date_start=date_start,
        date_end=date_end,
    )
    masks = _read_sources(
        [Path(value) for value in args.masks_source],
        columns=("asset_id", "date", "can_sell", "exit_tradeable"),
        assets=assets,
        date_start=date_start,
        date_end=date_end,
        tolerate_missing_columns=True,
    )
    result = build_delayed_exit_return_repair(
        trades_source=trades,
        bars_source=bars,
        masks_source=masks,
        max_exit_delay_days=args.max_exit_delay_days,
        price_column=args.price_column,
        output_return_column=args.output_return_column,
        override_cost_rate=args.override_cost_rate,
    )
    write_delayed_exit_return_repair(args.output_dir, result)
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_sources(
    sources: list[Path],
    *,
    columns: tuple[str, ...],
    assets: set[str],
    date_start: pd.Timestamp | None,
    date_end: pd.Timestamp | None,
    tolerate_missing_columns: bool = False,
) -> pd.DataFrame:
    frames = []
    for source in sources:
        paths = sorted(source.rglob("*.parquet")) if source.is_dir() else [source]
        for path in paths:
            frame = _read_source(path, columns=columns, tolerate_missing_columns=tolerate_missing_columns)
            if assets and "asset_id" in frame:
                frame = frame[frame["asset_id"].astype(str).isin(assets)]
            if "date" in frame:
                dates = pd.to_datetime(frame["date"], errors="coerce")
                if date_start is not None and pd.notna(date_start):
                    frame = frame[dates >= date_start]
                    dates = pd.to_datetime(frame["date"], errors="coerce")
                if date_end is not None and pd.notna(date_end):
                    frame = frame[dates <= date_end]
            if not frame.empty:
                frames.append(frame)
    return pd.concat(frames, ignore_index=True).drop_duplicates() if frames else pd.DataFrame()


def _read_source(
    path: Path,
    *,
    columns: tuple[str, ...] | None = None,
    tolerate_missing_columns: bool = False,
) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(path, columns=list(columns) if columns else None)
        except Exception:
            if not tolerate_missing_columns:
                raise
            frame = pd.read_parquet(path)
            return frame[[column for column in columns or () if column in frame]]
    if suffix == ".csv":
        frame = pd.read_csv(path)
        if columns:
            keep = [column for column in columns if column in frame]
            return frame[keep] if keep else frame
        return frame
    raise ValueError(f"unsupported source file type: {path.suffix}")


if __name__ == "__main__":
    main()
