from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.pre_api_readiness_board import build_pre_api_readiness_board, write_pre_api_readiness_board


DEFAULT_REVIEW_PACKET = Path("data/reports/promotion_review/promotion_review_packet.json")
DEFAULT_DATA_QUALITY = Path("data/reports/data_quality_gap_audit/data_quality_gap_audit.json")
DEFAULT_DATA_GAP_RESOLUTION = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_PROVIDER_REMEDIATION = Path("data/reports/provider_remediation/provider_remediation_matrix.json")
DEFAULT_PAPER_OBSERVATION = Path("data/reports/paper_observation/paper_observation_pack.json")
DEFAULT_DUPLICATE_REGISTRY = Path("data/reports/duplicate_registry/duplicate_canonical_registry.json")
DEFAULT_MANUAL_REHEARSAL = Path("data/reports/manual_review_rehearsal/manual_review_rehearsal.json")
DEFAULT_EVIDENCE_REFRESH = Path("data/reports/evidence_refresh/evidence_refresh_plan.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/pre_api_readiness_board")


def run_pre_api_readiness_board(
    review_packet: str | Path = DEFAULT_REVIEW_PACKET,
    data_quality: str | Path | None = DEFAULT_DATA_QUALITY,
    data_gap_resolution: str | Path | None = DEFAULT_DATA_GAP_RESOLUTION,
    provider_evidence: str | Path | None = DEFAULT_PROVIDER_EVIDENCE,
    provider_remediation: str | Path | None = DEFAULT_PROVIDER_REMEDIATION,
    paper_observation: str | Path | None = DEFAULT_PAPER_OBSERVATION,
    duplicate_registry: str | Path | None = DEFAULT_DUPLICATE_REGISTRY,
    manual_rehearsal: str | Path | None = DEFAULT_MANUAL_REHEARSAL,
    evidence_refresh: str | Path | None = DEFAULT_EVIDENCE_REFRESH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    board = build_pre_api_readiness_board(
        review_packet=_read_json(review_packet),
        data_quality=_read_optional_json(data_quality),
        data_gap_resolution=_read_optional_json(data_gap_resolution),
        provider_evidence=_read_optional_json(provider_evidence),
        provider_remediation=_read_optional_json(provider_remediation),
        paper_observation=_read_optional_json(paper_observation),
        duplicate_registry=_read_optional_json(duplicate_registry),
        manual_rehearsal=_read_optional_json(manual_rehearsal),
        evidence_refresh=_read_optional_json(evidence_refresh),
    )
    write_pre_api_readiness_board(output_dir, board)
    return board


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.0 pre-API readiness board.")
    parser.add_argument("--review-packet", default=str(DEFAULT_REVIEW_PACKET))
    parser.add_argument("--data-quality", default=str(DEFAULT_DATA_QUALITY))
    parser.add_argument("--data-gap-resolution", default=str(DEFAULT_DATA_GAP_RESOLUTION))
    parser.add_argument("--provider-evidence", default=str(DEFAULT_PROVIDER_EVIDENCE))
    parser.add_argument("--provider-remediation", default=str(DEFAULT_PROVIDER_REMEDIATION))
    parser.add_argument("--paper-observation", default=str(DEFAULT_PAPER_OBSERVATION))
    parser.add_argument("--duplicate-registry", default=str(DEFAULT_DUPLICATE_REGISTRY))
    parser.add_argument("--manual-rehearsal", default=str(DEFAULT_MANUAL_REHEARSAL))
    parser.add_argument("--evidence-refresh", default=str(DEFAULT_EVIDENCE_REFRESH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    board = run_pre_api_readiness_board(
        review_packet=Path(args.review_packet),
        data_quality=Path(args.data_quality) if args.data_quality else None,
        data_gap_resolution=Path(args.data_gap_resolution) if args.data_gap_resolution else None,
        provider_evidence=Path(args.provider_evidence) if args.provider_evidence else None,
        provider_remediation=Path(args.provider_remediation) if args.provider_remediation else None,
        paper_observation=Path(args.paper_observation) if args.paper_observation else None,
        duplicate_registry=Path(args.duplicate_registry) if args.duplicate_registry else None,
        manual_rehearsal=Path(args.manual_rehearsal) if args.manual_rehearsal else None,
        evidence_refresh=Path(args.evidence_refresh) if args.evidence_refresh else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": board["stage"],
                "overall_status": board["overall_status"],
                "summary": board["summary"],
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
