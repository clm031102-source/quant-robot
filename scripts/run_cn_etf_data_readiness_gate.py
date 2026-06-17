from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_etf_data_readiness import (  # noqa: E402
    build_cn_etf_data_readiness_gate,
    write_cn_etf_data_readiness_gate,
)


DEFAULT_DATA_ROOT = Path("data/processed/tushare_etf_full")
DEFAULT_SYNC_REPORT_DIR = Path("data/reports/tushare_cn_etf_sync")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_etf_data_readiness_gate")


def run_cn_etf_data_readiness_gate(
    *,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    sync_report_dir: str | Path | None = DEFAULT_SYNC_REPORT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    require_etf_share_size: bool = True,
    require_etf_moneyflow_baskets: bool = True,
) -> dict[str, Any]:
    pack = build_cn_etf_data_readiness_gate(
        data_root=Path(data_root),
        sync_report_dir=Path(sync_report_dir) if sync_report_dir is not None else None,
        require_etf_share_size=require_etf_share_size,
        require_etf_moneyflow_baskets=require_etf_moneyflow_baskets,
    )
    write_cn_etf_data_readiness_gate(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate CN_ETF factor mining on local data readiness.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--sync-report-dir", default=str(DEFAULT_SYNC_REPORT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-missing-etf-share-size", action="store_true")
    parser.add_argument("--allow-missing-etf-moneyflow-baskets", action="store_true")
    args = parser.parse_args()
    pack = run_cn_etf_data_readiness_gate(
        data_root=Path(args.data_root),
        sync_report_dir=Path(args.sync_report_dir),
        output_dir=Path(args.output_dir),
        require_etf_share_size=not args.allow_missing_etf_share_size,
        require_etf_moneyflow_baskets=not args.allow_missing_etf_moneyflow_baskets,
    )
    print(
        json.dumps(
            {
                "stage": pack.get("stage"),
                "status": pack.get("status"),
                "primary_market": pack.get("primary_market"),
                "bars": pack.get("bars", {}),
                "data_quality": pack.get("data_quality", {}),
                "rotation_membership": pack.get("rotation_membership", {}),
                "sync_pack": pack.get("sync_pack", {}),
                "auxiliary_datasets": pack.get("auxiliary_datasets", {}),
                "blockers": pack.get("blockers", []),
                "warnings": pack.get("warnings", []),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
