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

from quant_robot.ops.paper_ops_runbook import build_paper_ops_runbook_pack, write_paper_ops_runbook_pack


DEFAULT_GUARDRAIL_PACK = Path("data/reports/paper_ops_guardrail/paper_ops_guardrail_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/paper_ops_runbook")


def run_paper_ops_runbook(
    paper_ops_guardrail: str | Path = DEFAULT_GUARDRAIL_PACK,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    guardrail = _read_json(Path(paper_ops_guardrail))
    pack = build_paper_ops_runbook_pack(guardrail)
    write_paper_ops_runbook_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a paper-only daily operations runbook from the guardrail pack.")
    parser.add_argument("--paper-ops-guardrail", default=str(DEFAULT_GUARDRAIL_PACK))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_paper_ops_runbook(
        paper_ops_guardrail=Path(args.paper_ops_guardrail),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
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
