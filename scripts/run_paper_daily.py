"""Run daily fault-tolerant paper-trading update across all enabled CN & US portfolios."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_robot.paper.runner import run_daily_paper_update


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update market bars and advance daily paper portfolios (paper-only).")
    parser.add_argument("--config", default=str(ROOT / "configs" / "portfolios.json"))
    parser.add_argument("--data-root", help="Override data directory")
    parser.add_argument("--skip-fetch", action="store_true", help="Use local market cache without calling network APIs")
    parser.add_argument("--portfolio", action="append", help="Optional specific portfolio_id(s) to update")
    args = parser.parse_args(argv)

    overview = run_daily_paper_update(
        config_path=args.config,
        data_root=args.data_root,
        skip_fetch=args.skip_fetch,
        portfolio_ids=args.portfolio,
    )
    print(json.dumps(overview, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
