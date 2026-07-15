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

from quant_robot.ops.cn_stock_price_integrity_audit import (
    build_cn_stock_price_integrity_audit,
    write_cn_stock_price_integrity_audit,
)
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_DATA_ROOT = Path("configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json")
DEFAULT_EVIDENCE_ROOT = Path("data/processed/round198_tradeability_long_cycle_official_backfill_20260623")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_price_integrity")


def run_cn_stock_price_integrity_audit(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    market: str = "CN",
    evidence_root: str | Path | None = DEFAULT_EVIDENCE_ROOT,
    legacy_suspension_root: str | Path | None = None,
    extreme_return_threshold: float = 0.50,
    adjusted_ratio_jump_threshold: float = 1.50,
    bars: pd.DataFrame | None = None,
    stock_basic: pd.DataFrame | None = None,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    clean_bars = bars if bars is not None else _load_bars(root, market)
    evidence_path = Path(evidence_root) if evidence_root is not None else None
    lifecycle = stock_basic if stock_basic is not None else _load_evidence(
        evidence_path, "metadata/tushare_stock_basic", required=True
    )
    daily = daily_suspension if daily_suspension is not None else _load_evidence(
        evidence_path, "processed/tradeability_suspension", required=False
    )
    if legacy_suspension is not None:
        legacy = legacy_suspension
    elif legacy_suspension_root is not None:
        legacy = _load_evidence(
            Path(legacy_suspension_root), "processed/legacy_suspension", required=True
        )
    else:
        legacy = None
    packet, rows = build_cn_stock_price_integrity_audit(
        bars=clean_bars,
        stock_basic=lifecycle,
        daily_suspension=daily,
        legacy_suspension=legacy,
        source_root=root,
        evidence_root=evidence_path,
        extreme_return_threshold=extreme_return_threshold,
        adjusted_ratio_jump_threshold=adjusted_ratio_jump_threshold,
    )
    write_cn_stock_price_integrity_audit(output_dir, packet, rows)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit extreme CN stock returns by price-integrity root cause.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--legacy-suspension-root")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--extreme-return-threshold", type=float, default=0.50)
    parser.add_argument("--adjusted-ratio-jump-threshold", type=float, default=1.50)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    packet = run_cn_stock_price_integrity_audit(
        data_root=args.data_root,
        market=args.market,
        evidence_root=args.evidence_root,
        legacy_suspension_root=args.legacy_suspension_root,
        output_dir=args.output_dir,
        extreme_return_threshold=args.extreme_return_threshold,
        adjusted_ratio_jump_threshold=args.adjusted_ratio_jump_threshold,
    )
    print(
        json.dumps(
            {
                "status": packet["status"],
                "summary": packet["summary"],
                "decision": packet["decision"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if packet["status"] == "blocked" and not args.allow_blocked:
        raise SystemExit(3)


def _load_bars(root: Path, market: str) -> pd.DataFrame:
    if root.is_file():
        return load_authority_processed_bars_from_config(root, (market,))
    return load_processed_bars(root, market)


def _load_evidence(root: Path | None, dataset: str, *, required: bool) -> pd.DataFrame:
    if root is None:
        if required:
            raise ValueError(f"price integrity audit requires evidence dataset: {dataset}")
        return pd.DataFrame()
    base = root / Path(dataset)
    files = sorted(base.rglob("*.parquet")) if base.exists() else []
    if not files:
        if required:
            raise FileNotFoundError(f"evidence dataset has no parquet files: {base}")
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)


if __name__ == "__main__":
    main()
