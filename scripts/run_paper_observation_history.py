from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.paper_observation_history import (
    build_paper_observation_history_pack,
    write_paper_observation_history_pack,
)


DEFAULT_ACTIVATION_GATE_PACK = Path("data/reports/tushare_activation_gate/tushare_activation_gate_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/paper_observation_history")


def run_paper_observation_history(
    activation_gate_packs: list[str | Path] | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    paths = activation_gate_packs or [DEFAULT_ACTIVATION_GATE_PACK]
    packs = [_read_json(Path(path)) for path in paths if Path(path).exists()]
    pack = build_paper_observation_history_pack(packs)
    write_paper_observation_history_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a paper-only observation history ledger from activation gate packs.")
    parser.add_argument(
        "--activation-gate-pack",
        action="append",
        dest="activation_gate_packs",
        help="Activation gate pack to include. May be repeated.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_paper_observation_history(
        activation_gate_packs=[Path(item) for item in args.activation_gate_packs] if args.activation_gate_packs else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "decision": pack["decision"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
