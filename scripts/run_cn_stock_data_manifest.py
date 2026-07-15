from __future__ import annotations

import argparse
import hashlib
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
from quant_robot.ops.cn_stock_data_manifest import build_cn_stock_data_manifest, write_cn_stock_data_manifest
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_DATA_ROOT = Path("data/processed")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_data_manifest")


def run_cn_stock_data_manifest(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    moneyflow_root: str | Path | None = None,
    market: str = "CN",
    bars: pd.DataFrame | None = None,
    moneyflow_inputs: pd.DataFrame | None = None,
    calendar_path: str | Path | None = None,
    calendar_manifest_path: str | Path | None = None,
    session_integrity_packet_path: str | Path | None = None,
    price_integrity_packet_path: str | Path | None = None,
) -> dict[str, Any]:
    if (calendar_path is None) != (calendar_manifest_path is None):
        raise ValueError("calendar_path and calendar_manifest_path must be provided together")
    market_upper = market.upper()
    if market_upper != "CN":
        raise ValueError("CN stock data manifest only supports market='CN'")
    root = Path(data_root)
    effective_moneyflow_root = root if moneyflow_root is None else Path(moneyflow_root)
    if bars is not None:
        bar_frame = bars
    elif root.is_file():
        bar_frame = load_authority_processed_bars_from_config(root, (market_upper,))
    else:
        bar_frame = load_processed_bars(root, market_upper)
    moneyflow_frame = (
        moneyflow_inputs
        if moneyflow_inputs is not None
        else _load_moneyflow_or_none(effective_moneyflow_root, market_upper)
    )
    expected_sessions = None
    calendar_manifest = None
    if calendar_path is not None and calendar_manifest_path is not None:
        calendar_file = Path(calendar_path)
        manifest_file = Path(calendar_manifest_path)
        calendar_manifest = validate_cn_trading_calendar_artifact(calendar_file, manifest_file)
        expected_sessions = pd.read_csv(calendar_file)
    session_integrity_packet = _load_integrity_packet(session_integrity_packet_path)
    price_integrity_packet = _load_integrity_packet(price_integrity_packet_path)
    manifest = build_cn_stock_data_manifest(
        bars=bar_frame,
        moneyflow_inputs=moneyflow_frame,
        source_root=root,
        moneyflow_source_root=effective_moneyflow_root,
        expected_sessions=expected_sessions,
        calendar_manifest=calendar_manifest,
        session_integrity_packet=session_integrity_packet,
        price_integrity_packet=price_integrity_packet,
    )
    write_cn_stock_data_manifest(output_dir, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CN stock data manifest required before factor mining.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--moneyflow-root", help="Separate processed or authority-config moneyflow root")
    parser.add_argument("--calendar-path", help="Validated provider-backed CN trading calendar CSV")
    parser.add_argument("--calendar-manifest-path", help="Manifest for --calendar-path")
    parser.add_argument("--session-integrity-packet", help="Asset-session integrity audit JSON")
    parser.add_argument("--price-integrity-packet", help="Price integrity audit JSON")
    parser.add_argument("--market", default="CN")
    args = parser.parse_args()
    manifest = run_cn_stock_data_manifest(
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir),
        moneyflow_root=Path(args.moneyflow_root) if args.moneyflow_root else None,
        calendar_path=Path(args.calendar_path) if args.calendar_path else None,
        calendar_manifest_path=Path(args.calendar_manifest_path) if args.calendar_manifest_path else None,
        session_integrity_packet_path=(
            Path(args.session_integrity_packet) if args.session_integrity_packet else None
        ),
        price_integrity_packet_path=(
            Path(args.price_integrity_packet) if args.price_integrity_packet else None
        ),
        market=args.market,
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blockers": manifest["decision"]["blockers"],
                "warnings": manifest["decision"]["warnings"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_moneyflow_or_none(root: Path, market: str) -> pd.DataFrame | None:
    try:
        return load_moneyflow_inputs(root, market)
    except FileNotFoundError:
        return None


def _load_integrity_packet(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    packet_path = Path(path)
    if not packet_path.is_file():
        raise FileNotFoundError(f"integrity packet does not exist: {packet_path}")
    raw = packet_path.read_bytes()
    packet = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(packet, dict):
        raise ValueError(f"integrity packet must contain a JSON object: {packet_path}")
    packet["_provenance"] = {
        "path": str(packet_path),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return packet


if __name__ == "__main__":
    main()
