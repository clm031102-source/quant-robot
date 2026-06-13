from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.evidence_refresh import build_evidence_refresh_plan, write_evidence_refresh_plan

try:
    from scripts.run_promotion_review import DEFAULT_OUTPUT_DIR as DEFAULT_REVIEW_DIR
    from scripts.run_promotion_review import run_promotion_review
except ModuleNotFoundError:
    from run_promotion_review import DEFAULT_OUTPUT_DIR as DEFAULT_REVIEW_DIR
    from run_promotion_review import run_promotion_review


DEFAULT_REVIEW_PACKET = DEFAULT_REVIEW_DIR / "promotion_review_packet.json"
DEFAULT_DATA_GAP_RESOLUTION = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_DUPLICATE_REGISTRY = Path("data/reports/duplicate_registry/duplicate_canonical_registry.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/evidence_refresh")


def run_evidence_refresh(
    review_packet: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    data_gap_resolution: str | Path | None = DEFAULT_DATA_GAP_RESOLUTION,
    provider_evidence: str | Path | None = DEFAULT_PROVIDER_EVIDENCE,
    duplicate_registry: str | Path | None = DEFAULT_DUPLICATE_REGISTRY,
) -> dict[str, Any]:
    review_path = Path(review_packet) if review_packet is not None else DEFAULT_REVIEW_PACKET
    packet = _read_packet_or_build(review_path)
    plan = build_evidence_refresh_plan(
        packet,
        data_gap_resolution=_read_optional_json(data_gap_resolution),
        provider_evidence=_read_optional_json(provider_evidence),
        duplicate_registry=_read_optional_json(duplicate_registry),
    )
    write_evidence_refresh_plan(output_dir, plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.0 evidence refresh plan from the promotion review packet.")
    parser.add_argument("--review-packet")
    parser.add_argument("--data-gap-resolution", default=str(DEFAULT_DATA_GAP_RESOLUTION))
    parser.add_argument("--provider-evidence", default=str(DEFAULT_PROVIDER_EVIDENCE))
    parser.add_argument("--duplicate-registry", default=str(DEFAULT_DUPLICATE_REGISTRY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    plan = run_evidence_refresh(
        review_packet=Path(args.review_packet) if args.review_packet else None,
        data_gap_resolution=Path(args.data_gap_resolution) if args.data_gap_resolution else None,
        provider_evidence=Path(args.provider_evidence) if args.provider_evidence else None,
        duplicate_registry=Path(args.duplicate_registry) if args.duplicate_registry else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "refresh_status": plan["refresh_status"],
                "selected_candidate": plan["selected_candidate"],
                "tracks": [{key: track[key] for key in ("track_id", "status", "evidence")} for track in plan["tracks"]],
                "ordered_actions": plan["ordered_actions"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_packet_or_build(path: Path) -> dict[str, Any]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {path}")
        return data
    return run_promotion_review(output_dir=path.parent)


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {target}")
    return data


if __name__ == "__main__":
    main()
