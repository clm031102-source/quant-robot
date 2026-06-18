from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.research.family_scheduler import (  # noqa: E402
    build_research_family_schedule,
    load_research_family_config,
    write_research_family_schedule,
)


DEFAULT_CONFIG = Path("configs/research_family_scheduler_cn_etf.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/research_family_scheduler")


def run_research_family_scheduler(
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    config = load_research_family_config(config_path)
    pack = build_research_family_schedule(config)
    write_research_family_schedule(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the research-family schedule before factor mining.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_research_family_scheduler(args.config, args.output_dir)
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "blockers": pack["blockers"],
                "warnings": pack["warnings"],
                "allocation": pack["allocation"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
