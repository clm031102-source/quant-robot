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

from quant_robot.ops.manual_review_rehearsal import build_manual_review_rehearsal, write_manual_review_rehearsal


DEFAULT_REVIEW_PACKET = Path("data/reports/promotion_review/promotion_review_packet.json")
DEFAULT_DATA_QUALITY = Path("data/reports/data_quality_gap_audit/data_quality_gap_audit.json")
DEFAULT_DATA_GAP_RESOLUTION = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_PAPER_OBSERVATION = Path("data/reports/paper_observation/paper_observation_pack.json")
DEFAULT_DUPLICATE_REGISTRY = Path("data/reports/duplicate_registry/duplicate_canonical_registry.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/manual_review_rehearsal")


def run_manual_review_rehearsal(
    review_packet: str | Path = DEFAULT_REVIEW_PACKET,
    data_quality: str | Path | None = DEFAULT_DATA_QUALITY,
    data_gap_resolution: str | Path | None = DEFAULT_DATA_GAP_RESOLUTION,
    provider_evidence: str | Path | None = DEFAULT_PROVIDER_EVIDENCE,
    paper_observation: str | Path | None = DEFAULT_PAPER_OBSERVATION,
    duplicate_registry: str | Path | None = DEFAULT_DUPLICATE_REGISTRY,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    rehearsal = build_manual_review_rehearsal(
        _read_json(review_packet),
        data_quality=_read_optional_json(data_quality),
        data_gap_resolution=_read_optional_json(data_gap_resolution),
        provider_evidence=_read_optional_json(provider_evidence),
        paper_observation=_read_optional_json(paper_observation),
        duplicate_registry=_read_optional_json(duplicate_registry),
    )
    write_manual_review_rehearsal(output_dir, rehearsal)
    return rehearsal


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.5 manual-review gate rehearsal.")
    parser.add_argument("--review-packet", default=str(DEFAULT_REVIEW_PACKET))
    parser.add_argument("--data-quality", default=str(DEFAULT_DATA_QUALITY))
    parser.add_argument("--data-gap-resolution", default=str(DEFAULT_DATA_GAP_RESOLUTION))
    parser.add_argument("--provider-evidence", default=str(DEFAULT_PROVIDER_EVIDENCE))
    parser.add_argument("--paper-observation", default=str(DEFAULT_PAPER_OBSERVATION))
    parser.add_argument("--duplicate-registry", default=str(DEFAULT_DUPLICATE_REGISTRY))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    rehearsal = run_manual_review_rehearsal(
        review_packet=Path(args.review_packet),
        data_quality=Path(args.data_quality) if args.data_quality else None,
        data_gap_resolution=Path(args.data_gap_resolution) if args.data_gap_resolution else None,
        provider_evidence=Path(args.provider_evidence) if args.provider_evidence else None,
        paper_observation=Path(args.paper_observation) if args.paper_observation else None,
        duplicate_registry=Path(args.duplicate_registry) if args.duplicate_registry else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": rehearsal["stage"],
                "gate_status": rehearsal["gate_status"],
                "summary": rehearsal["summary"],
                "blockers": rehearsal["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return _read_json(target)


if __name__ == "__main__":
    main()
