from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_check import validate_simulation_shortlist_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a CN stock simulation shortlist config.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result = validate_simulation_shortlist_config(config, repo_root=Path(args.repo_root))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["blockers"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
