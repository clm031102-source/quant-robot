from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.storage.catalog import build_storage_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Show local Quant Robot data catalog.")
    parser.add_argument("--root", default="data")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    print(render_catalog(build_storage_catalog(Path(args.root)), summary_only=args.summary_only))


def render_catalog(catalog: dict[str, object], summary_only: bool = False) -> str:
    payload = {key: value for key, value in catalog.items() if key != "datasets"} if summary_only else catalog
    return json.dumps(payload, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
