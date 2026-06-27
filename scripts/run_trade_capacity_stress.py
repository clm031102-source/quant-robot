from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.trade_capacity_stress import (  # noqa: E402
    build_trade_capacity_stress,
    write_trade_capacity_stress,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/trade_capacity_stress")


def parse_float_tuple(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def parse_trade_sources(values: list[str]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--trade-source must use candidate_name=path")
        name, path = value.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError("--trade-source candidate_name cannot be empty")
        sources[name] = Path(path.strip())
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test trade CSV/Parquet participation rates under larger AUM.")
    parser.add_argument(
        "--trade-source",
        action="append",
        required=True,
        help="Candidate trade CSV/Parquet as candidate_name=path. Repeat for multiple candidates.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--multipliers", default="1,5,10,20,50,100")
    parser.add_argument("--max-participation-rate", type=float, default=0.05)
    args = parser.parse_args()

    audit = build_trade_capacity_stress(
        parse_trade_sources(args.trade_source),
        multipliers=parse_float_tuple(args.multipliers),
        max_participation_rate=args.max_participation_rate,
    )
    write_trade_capacity_stress(Path(args.output_dir), audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
