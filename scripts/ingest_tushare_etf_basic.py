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

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.storage.cn_etf_peer_mapping import build_cn_etf_peer_mapping_history  # noqa: E402
from quant_robot.storage.dataset_store import DatasetStore  # noqa: E402


class TushareEtfBasicAdapter(Protocol):
    def fetch_etf_basic(self, list_status: str = "") -> pd.DataFrame:
        ...


def run_tushare_etf_basic_ingest(
    adapter: TushareEtfBasicAdapter,
    output_dir: str | Path,
    *,
    snapshot: str | None = None,
) -> dict[str, object]:
    snapshot = snapshot or date.today().isoformat()
    snapshot_date = pd.Timestamp(snapshot).date().isoformat()
    output_path = Path(output_dir)
    frame = adapter.fetch_etf_basic(list_status="")
    if frame is None or frame.empty:
        raise ValueError("Tushare etf_basic returned no rows; refusing to write an empty authority snapshot")
    output_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(output_path)
    raw_path = store.write_frame(
        frame,
        "metadata/tushare_etf_basic",
        {"market": "CN_ETF", "snapshot": snapshot_date},
    )
    snapshots = _load_etf_basic_snapshots(output_path)
    peer_mapping = build_cn_etf_peer_mapping_history(snapshots)
    mapping_path = store.write_frame(
        peer_mapping,
        "metadata/cn_etf_peer_mapping",
        {"market": "CN_ETF"},
    )
    return {
        "source": "tushare",
        "dataset": "metadata/tushare_etf_basic",
        "snapshot": snapshot_date,
        "rows": int(len(frame)),
        "official_index_code_rows": int(frame["index_code"].fillna("").astype(str).str.strip().ne("").sum())
        if "index_code" in frame
        else 0,
        "peer_mapping_rows": int(len(peer_mapping)),
        "path": str(raw_path),
        "peer_mapping_path": str(mapping_path),
        "historical_backfill_allowed": False,
        "knowledge_policy": "Each official index assignment becomes usable no earlier than its captured snapshot date.",
    }


def _load_etf_basic_snapshots(root: Path) -> dict[str, pd.DataFrame]:
    base = root / "metadata/tushare_etf_basic/market=CN_ETF"
    store = DatasetStore(root)
    snapshots: dict[str, pd.DataFrame] = {}
    for path in sorted(base.glob("snapshot=*")):
        if not path.is_dir() or "=" not in path.name:
            continue
        snapshot = path.name.split("=", 1)[1]
        try:
            snapshots[snapshot] = store.read_frame(
                "metadata/tushare_etf_basic",
                {"market": "CN_ETF", "snapshot": snapshot},
            )
        except FileNotFoundError:
            continue
    return snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest official Tushare ETF tracking-index metadata.")
    parser.add_argument("--output-dir", default="data/processed/tushare_etf_wide_history_2023_2026")
    parser.add_argument("--snapshot")
    args = parser.parse_args()
    result = run_tushare_etf_basic_ingest(
        TushareAdapter(),
        args.output_dir,
        snapshot=args.snapshot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
