from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.external_feed_factor_matrix_join_smoke import run_external_feed_factor_matrix_join_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test external-feed factor-matrix joins using available_date.")
    parser.add_argument("--processed-root", required=True)
    parser.add_argument("--seed-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--market", default="CN")
    parser.add_argument("--signal-start-date")
    parser.add_argument("--signal-end-date")
    args = parser.parse_args(argv)
    result = run_external_feed_factor_matrix_join_smoke(
        processed_root=Path(args.processed_root),
        seed_config_path=Path(args.seed_config),
        output_dir=Path(args.output_dir),
        signal_start_date=args.signal_start_date,
        signal_end_date=args.signal_end_date,
        market=args.market,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
