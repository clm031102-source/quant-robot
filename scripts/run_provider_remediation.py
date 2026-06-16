from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.provider_remediation import build_provider_remediation_matrix, write_provider_remediation_matrix


DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/provider_remediation")
DEFAULT_REVIEW_FILENAME = "provider_remediation_review.csv"


def run_provider_remediation(
    provider_evidence: str | Path = DEFAULT_PROVIDER_EVIDENCE,
    review_file: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    evidence = _read_json(provider_evidence)
    output_path = Path(output_dir)
    selected_review_file = Path(review_file) if review_file is not None else _default_review_file(output_path)
    matrix = build_provider_remediation_matrix(evidence, review_rows=_read_optional_csv(selected_review_file))
    write_provider_remediation_matrix(output_path, matrix)
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.7 provider-remediation matrix.")
    parser.add_argument("--provider-evidence", default=str(DEFAULT_PROVIDER_EVIDENCE))
    parser.add_argument("--review-file", default="")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    matrix = run_provider_remediation(
        provider_evidence=Path(args.provider_evidence),
        review_file=Path(args.review_file) if args.review_file else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": matrix["stage"],
                "summary": matrix["summary"],
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


def _read_optional_csv(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    target = Path(path)
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _default_review_file(output_dir: Path) -> Path | None:
    review_path = output_dir / DEFAULT_REVIEW_FILENAME
    return review_path if review_path.exists() else None


if __name__ == "__main__":
    main()
