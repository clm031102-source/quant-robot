from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.data.provider_status import build_provider_status
from quant_robot.ops.provider_evidence import build_provider_evidence_pack, write_provider_evidence_pack


DEFAULT_PROVIDER_STATUS = Path("data/reports/provider_status/provider_status.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/provider_evidence")


def run_provider_evidence(
    provider_status: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    status = _load_provider_status(provider_status)
    pack = build_provider_evidence_pack(status)
    write_provider_evidence_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.2 provider-readiness evidence pack.")
    parser.add_argument("--provider-status", help="Optional provider_status.json path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_provider_evidence(
        provider_status=Path(args.provider_status) if args.provider_status else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_provider_status(provider_status: str | Path | None) -> dict[str, Any]:
    path = Path(provider_status) if provider_status else DEFAULT_PROVIDER_STATUS
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_provider_status()


if __name__ == "__main__":
    main()
