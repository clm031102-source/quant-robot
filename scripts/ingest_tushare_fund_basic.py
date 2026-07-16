from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Protocol

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.storage.cn_etf_peer_mapping import build_cn_etf_peer_mapping_history_from_fund_basic
from quant_robot.storage.dataset_store import DatasetStore


class TushareFundBasicAdapter(Protocol):
    def fetch_fund_basic(self, market: str = "E") -> pd.DataFrame:
        ...


def run_tushare_fund_basic_ingest(
    adapter: TushareFundBasicAdapter,
    output_dir: str | Path,
    *,
    market: str = "E",
    snapshot: str | None = None,
) -> dict[str, object]:
    market = market.upper()
    snapshot = pd.Timestamp(snapshot or date.today().isoformat()).date().isoformat()
    output_path = Path(output_dir)
    frame = adapter.fetch_fund_basic(market)
    if frame is None or frame.empty:
        raise ValueError("Tushare fund_basic returned no rows; refusing to write an empty authority snapshot")
    output_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(output_path)
    file_path = store.write_frame(
        frame,
        "metadata/tushare_fund_basic",
        {"market": market, "snapshot": snapshot},
    )
    peer_mapping = build_cn_etf_peer_mapping_history_from_fund_basic(
        _load_fund_basic_snapshots(output_path, market)
    )
    peer_mapping_path = store.write_frame(
        peer_mapping,
        "metadata/cn_etf_peer_mapping",
        {"market": "CN_ETF"},
    )
    return {
        "source": "tushare",
        "dataset": "metadata/tushare_fund_basic",
        "market": market,
        "snapshot": snapshot,
        "rows": int(len(frame)),
        "path": str(file_path),
        "peer_mapping_rows": int(len(peer_mapping)),
        "peer_mapping_path": str(peer_mapping_path),
        "historical_backfill_allowed": False,
    }


def _load_fund_basic_snapshots(root: Path, market: str) -> dict[str, pd.DataFrame]:
    base = root / "metadata/tushare_fund_basic" / f"market={market}"
    store = DatasetStore(root)
    snapshots: dict[str, pd.DataFrame] = {}
    for path in sorted(base.glob("snapshot=*")):
        if not path.is_dir() or "=" not in path.name:
            continue
        snapshot = path.name.split("=", 1)[1]
        try:
            snapshots[snapshot] = store.read_frame(
                "metadata/tushare_fund_basic",
                {"market": market, "snapshot": snapshot},
            )
        except FileNotFoundError:
            continue
    return snapshots


class _FixtureFundBasicAdapter:
    def fetch_fund_basic(self, market: str = "E") -> pd.DataFrame:
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "512880.SH"],
                "name": ["CSI 300 ETF", "Securities ETF"],
                "market": [market, market],
                "status": ["L", "L"],
                "fund_type": ["ETF", "ETF"],
                "type": ["ETF", "ETF"],
                "invest_type": ["Passive", "Passive"],
                "is_etf": [True, True],
                "benchmark": ["CSI 300 Index Return x 100%", "CSI 300 Index Return x 100%"],
                "list_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
                "delist_date": [pd.NaT, pd.NaT],
                "found_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Tushare fund_basic metadata for CN ETF theme mapping.")
    parser.add_argument("--source", choices=("tushare", "fixture"), default="tushare")
    parser.add_argument("--market", default="E")
    parser.add_argument("--output-dir", default="data/processed/tushare_etf_wide_history_2023_2026")
    parser.add_argument("--snapshot", default=None)
    args = parser.parse_args()
    adapter: TushareFundBasicAdapter = _FixtureFundBasicAdapter() if args.source == "fixture" else TushareAdapter()
    result = run_tushare_fund_basic_ingest(
        adapter,
        args.output_dir,
        market=args.market,
        snapshot=args.snapshot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
