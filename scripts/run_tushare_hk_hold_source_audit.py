from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.ops.tushare_hk_hold_source_audit import (  # noqa: E402
    build_tushare_hk_hold_source_audit,
    write_tushare_hk_hold_source_audit,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit raw Tushare hk_hold symbol composition for selected CN-stock research dates."
    )
    parser.add_argument("--trade-date", action="append", required=True, help="Trade date to audit. Repeatable.")
    parser.add_argument("--output-dir", default="data/reports/tushare_hk_hold_source_audit")
    parser.add_argument("--market", default="CN")
    args = parser.parse_args(argv)

    packet = build_tushare_hk_hold_source_audit(
        TushareAdapter(),
        trade_dates=list(args.trade_date),
        market=args.market,
    )
    write_tushare_hk_hold_source_audit(Path(args.output_dir), packet)
    print(
        json.dumps(
            {
                "stage": packet["stage"],
                "summary": packet["summary"],
                "output_dir": str(Path(args.output_dir)),
                "promotion_allowed": packet.get("promotion_allowed", False),
                "safety": packet.get("safety", ""),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
