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

from quant_robot.ops.profitability_event_revision_preregistration import (  # noqa: E402
    build_profitability_event_revision_preregistration,
    write_profitability_event_revision_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/profitability_event_revision_preregistration_round151_20260623")


def run_profitability_event_revision_preregistration_cli(
    *,
    input_root: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_assets: int = 50,
    min_passed_candidates: int = 6,
    min_families: int = 3,
    endpoint_probe_json: str | Path | None = None,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    endpoint_probe_results = _load_endpoint_probe(endpoint_probe_json)
    result = build_profitability_event_revision_preregistration(
        input_root=Path(input_root),
        min_assets=min_assets,
        min_passed_candidates=min_passed_candidates,
        min_families=min_families,
        endpoint_probe_results=endpoint_probe_results,
    )
    write_profitability_event_revision_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"PIT profitability event-revision preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register Round151 PIT profitability event/revision candidates from local fina_indicator inputs."
    )
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-assets", type=int, default=50)
    parser.add_argument("--min-passed-candidates", type=int, default=6)
    parser.add_argument("--min-families", type=int, default=3)
    parser.add_argument("--endpoint-probe-json")
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_profitability_event_revision_preregistration_cli(
        input_root=Path(args.input_root),
        output_dir=Path(args.output_dir),
        min_assets=args.min_assets,
        min_passed_candidates=args.min_passed_candidates,
        min_families=args.min_families,
        endpoint_probe_json=args.endpoint_probe_json,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "source_context": result.get("source_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_endpoint_probe(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Endpoint probe JSON must contain an object keyed by endpoint name")
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


if __name__ == "__main__":
    main()
