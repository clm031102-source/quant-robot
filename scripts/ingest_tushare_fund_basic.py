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
    snapshot = snapshot or date.today().isoformat()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    frame = adapter.fetch_fund_basic(market)
    store = DatasetStore(output_path)
    file_path = store.write_frame(
        frame,
        "metadata/tushare_fund_basic",
        {"market": market, "snapshot": snapshot},
    )
    return {
        "source": "tushare",
        "dataset": "metadata/tushare_fund_basic",
        "market": market,
        "snapshot": snapshot,
        "rows": int(len(frame)),
        "path": str(file_path),
    }


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
