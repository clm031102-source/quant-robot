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

from quant_robot.ops.provider_remediation_rehearsal import (
    build_provider_remediation_rehearsal,
    write_provider_remediation_rehearsal,
)


DEFAULT_PROVIDER_EVIDENCE = Path("data/reports/provider_evidence/provider_evidence_pack.json")
DEFAULT_PROVIDER_REMEDIATION = Path("data/reports/provider_remediation/provider_remediation_matrix.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/provider_remediation_rehearsal")


def run_provider_remediation_rehearsal(
    provider_evidence: str | Path = DEFAULT_PROVIDER_EVIDENCE,
    provider_remediation: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    evidence = _read_json(provider_evidence)
    baseline = _read_optional_json(provider_remediation)
    rehearsal = build_provider_remediation_rehearsal(evidence, baseline_matrix=baseline)
    write_provider_remediation_rehearsal(output_dir, rehearsal)
    return rehearsal


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.11 provider-remediation review rehearsal pack.")
    parser.add_argument("--provider-evidence", default=str(DEFAULT_PROVIDER_EVIDENCE))
    parser.add_argument("--provider-remediation", default=str(DEFAULT_PROVIDER_REMEDIATION))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    rehearsal = run_provider_remediation_rehearsal(
        provider_evidence=Path(args.provider_evidence),
        provider_remediation=Path(args.provider_remediation) if args.provider_remediation else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": rehearsal["stage"],
                "summary": rehearsal["summary"],
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
