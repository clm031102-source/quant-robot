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

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact
from quant_robot.ops.cn_stock_asset_session_integrity_audit import (
    build_cn_stock_asset_session_integrity_audit,
    write_cn_stock_asset_session_integrity_audit,
)
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_DATA_ROOT = Path("configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
DEFAULT_CALENDAR_PATH = Path("data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv")
DEFAULT_CALENDAR_MANIFEST_PATH = Path(
    "data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar_manifest.json"
)
DEFAULT_EVIDENCE_ROOT = Path("data/processed/round198_tradeability_long_cycle_official_backfill_20260623")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_asset_session_integrity")


def run_cn_stock_asset_session_integrity_audit(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    market: str = "CN",
    calendar_path: str | Path | None = DEFAULT_CALENDAR_PATH,
    calendar_manifest_path: str | Path | None = DEFAULT_CALENDAR_MANIFEST_PATH,
    evidence_root: str | Path | None = DEFAULT_EVIDENCE_ROOT,
    legacy_suspension_root: str | Path | None = None,
    bars: pd.DataFrame | None = None,
    expected_sessions: pd.DataFrame | None = None,
    stock_basic: pd.DataFrame | None = None,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    clean_bars = bars if bars is not None else _load_bars(root, market)
    sessions, calendar_provenance = (
        (expected_sessions.copy(), None)
        if expected_sessions is not None
        else _load_calendar(calendar_path, calendar_manifest_path)
    )
    evidence_path = Path(evidence_root) if evidence_root is not None else None
    lifecycle = stock_basic if stock_basic is not None else _load_evidence(
        evidence_path,
        "metadata/tushare_stock_basic",
        required=True,
    )
    daily = daily_suspension if daily_suspension is not None else _load_evidence(
        evidence_path,
        "processed/tradeability_suspension",
        required=True,
    )
    if legacy_suspension is not None:
        legacy = legacy_suspension
    elif legacy_suspension_root is not None:
        legacy = _load_evidence(
            Path(legacy_suspension_root),
            "processed/legacy_suspension",
            required=True,
        )
    else:
        legacy = None
    packet, classification = build_cn_stock_asset_session_integrity_audit(
        bars=clean_bars,
        expected_sessions=sessions,
        stock_basic=lifecycle,
        daily_suspension=daily,
        legacy_suspension=legacy,
        source_root=root,
        evidence_root=evidence_path,
        calendar_provenance=calendar_provenance,
    )
    write_cn_stock_asset_session_integrity_audit(output_dir, packet, classification)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CN stock asset-session gaps against official lifecycle evidence.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--calendar-path", default=str(DEFAULT_CALENDAR_PATH))
    parser.add_argument("--calendar-manifest-path", default=str(DEFAULT_CALENDAR_MANIFEST_PATH))
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--legacy-suspension-root")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Write and return blocked evidence without changing its blocked status.",
    )
    args = parser.parse_args()
    packet = run_cn_stock_asset_session_integrity_audit(
        data_root=args.data_root,
        market=args.market,
        calendar_path=args.calendar_path,
        calendar_manifest_path=args.calendar_manifest_path,
        evidence_root=args.evidence_root,
        legacy_suspension_root=args.legacy_suspension_root,
        output_dir=args.output_dir,
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


def _load_calendar(
    calendar_path: str | Path | None,
    manifest_path: str | Path | None,
) -> tuple[pd.DataFrame, dict[str, Any] | None]:
    if calendar_path is None:
        raise ValueError("asset-session integrity audit requires an explicit calendar_path")
    path = Path(calendar_path)
    if not path.is_file():
        raise FileNotFoundError(f"trading calendar does not exist: {path}")
    manifest = None
    provenance = None
    if manifest_path is not None:
        manifest = validate_cn_trading_calendar_artifact(path, manifest_path)
        artifact = manifest.get("artifact", {}) if isinstance(manifest.get("artifact"), dict) else {}
        provenance = {
            "calendar_path": str(path),
            "manifest_path": str(Path(manifest_path)),
            "artifact_sha256": artifact.get("sha256"),
        }
    frame = pd.read_csv(path)
    date_column = next(
        (column for column in ("date", "trade_date", "cal_date", "session_date") if column in frame),
        None,
    )
    if date_column is None:
        raise ValueError("trading calendar is missing a date column")
    if "is_open" in frame:
        frame = frame[frame["is_open"].astype(str).str.lower().isin({"1", "true", "yes", "open"})]
    return pd.DataFrame({"date": frame[date_column]}), provenance


def _load_evidence(root: Path | None, dataset: str, *, required: bool) -> pd.DataFrame:
    if root is None:
        if required:
            raise ValueError(f"asset-session integrity audit requires evidence dataset: {dataset}")
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
