from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.review_packet import build_promotion_review_packet, write_promotion_review_packet

try:
    from scripts.run_promotion_ops import DEFAULT_OUTPUT_DIR as DEFAULT_OPS_DIR
    from scripts.run_promotion_ops import run_promotion_ops
except ModuleNotFoundError:
    from run_promotion_ops import DEFAULT_OUTPUT_DIR as DEFAULT_OPS_DIR
    from run_promotion_ops import run_promotion_ops


DEFAULT_PROMOTION_OPS = DEFAULT_OPS_DIR / "promotion_ops.json"
DEFAULT_OUTPUT_DIR = Path("data/reports/promotion_review")


def run_promotion_review(
    promotion_ops: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    ops_path = Path(promotion_ops) if promotion_ops is not None else DEFAULT_PROMOTION_OPS
    console = _read_console_or_build(ops_path)
    packet = build_promotion_review_packet(console, candidate_id=candidate_id)
    write_promotion_review_packet(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 2.9 promotion candidate review packet.")
    parser.add_argument("--promotion-ops")
    parser.add_argument("--candidate-id")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    packet = run_promotion_review(
        promotion_ops=Path(args.promotion_ops) if args.promotion_ops else None,
        output_dir=Path(args.output_dir),
        candidate_id=args.candidate_id,
    )
    print(
        json.dumps(
            {
                "review_status": packet["review_status"],
                "selected_candidate": packet["selected_candidate"],
                "manual_review_gate": packet["manual_review_gate"],
                "next_actions": packet["next_actions"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_console_or_build(path: Path) -> dict[str, Any]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {path}")
        return data
    return run_promotion_ops(output_dir=path.parent)


if __name__ == "__main__":
    main()
