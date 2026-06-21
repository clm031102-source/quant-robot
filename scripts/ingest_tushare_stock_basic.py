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


class TushareStockBasicAdapter(Protocol):
    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        ...


def run_tushare_stock_basic_ingest(
    adapter: TushareStockBasicAdapter,
    output_dir: str | Path,
    *,
    list_status: str = "L",
    snapshot: str | None = None,
) -> dict[str, object]:
    list_status = list_status.upper()
    snapshot = snapshot or date.today().isoformat()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    frame = adapter.fetch_stock_basic(list_status)
    store = DatasetStore(output_path)
    file_path = store.write_frame(
        frame,
        "metadata/tushare_stock_basic",
        {"list_status": list_status, "snapshot": snapshot},
    )
    return {
        "source": "tushare",
        "dataset": "metadata/tushare_stock_basic",
        "list_status": list_status,
        "snapshot": snapshot,
        "rows": int(len(frame)),
        "path": str(file_path),
    }


class _FixtureStockBasicAdapter:
    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        return pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHG_600000"],
                "symbol": ["000001.SZ", "600000.SH"],
                "market": ["CN", "CN"],
                "exchange": ["XSHE", "XSHG"],
                "asset_type": ["stock", "stock"],
                "currency": ["CNY", "CNY"],
                "timezone": ["Asia/Shanghai", "Asia/Shanghai"],
                "calendar": ["XSHE", "XSHG"],
                "name": ["Ping An Bank", "SPD Bank"],
                "is_active": [list_status.upper() == "L", list_status.upper() == "L"],
                "area": ["Shenzhen", "Shanghai"],
                "industry": ["Bank", "Bank"],
                "stock_market": ["Main Board", "Main Board"],
                "list_date": [pd.Timestamp("1991-04-03").date(), pd.Timestamp("1999-11-10").date()],
                "delist_date": [pd.NaT, pd.NaT],
                "is_hs": ["S", "H"],
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Tushare stock_basic metadata for CN stock industry research.")
    parser.add_argument("--source", choices=("tushare", "fixture"), default="tushare")
    parser.add_argument("--list-status", default="L")
    parser.add_argument("--output-dir", default="data/processed/cn_stock_metadata")
    parser.add_argument("--snapshot", default=None)
    args = parser.parse_args()
    adapter: TushareStockBasicAdapter = _FixtureStockBasicAdapter() if args.source == "fixture" else TushareAdapter()
    result = run_tushare_stock_basic_ingest(
        adapter,
        args.output_dir,
        list_status=args.list_status,
        snapshot=args.snapshot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
