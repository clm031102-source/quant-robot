from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (SRC_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quant_robot.data.archive_replay import replay_tushare_archive_to_processed


def run_archive_replay_cli(
    daily_roots: str,
    moneyflow_roots: str,
    output_dir: str | Path,
    market: str = "CN",
) -> dict[str, object]:
    return replay_tushare_archive_to_processed(
        daily_roots=_parse_roots(daily_roots),
        moneyflow_roots=_parse_roots(moneyflow_roots),
        output_dir=Path(output_dir),
        market=market,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay local Tushare raw archives into a processed research store.")
    parser.add_argument("--daily-roots", required=True, help="Semicolon-separated roots containing raw/tushare/daily.")
    parser.add_argument("--moneyflow-roots", required=True, help="Semicolon-separated roots containing raw/tushare/moneyflow.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--market", default="CN")
    args = parser.parse_args()
    result = run_archive_replay_cli(
        daily_roots=args.daily_roots,
        moneyflow_roots=args.moneyflow_roots,
        output_dir=Path(args.output_dir),
        market=args.market,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _parse_roots(value: str) -> list[Path]:
    return [Path(part.strip()) for part in value.split(";") if part.strip()]


if __name__ == "__main__":
    main()
