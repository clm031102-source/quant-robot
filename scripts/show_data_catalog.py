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


def run_data_catalog_cli(*, root: str | Path = "data", summary_only: bool = False) -> str:
    catalog = build_storage_catalog(
        Path(root),
        include_datasets=not summary_only,
        count_rows=not summary_only,
    )
    return render_catalog(catalog, summary_only=summary_only)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Show local Quant Robot data catalog.")
    parser.add_argument("--root", default="data")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    print(run_data_catalog_cli(root=args.root, summary_only=args.summary_only))


def render_catalog(catalog: dict[str, object], summary_only: bool = False) -> str:
    payload = {key: value for key, value in catalog.items() if key != "datasets"} if summary_only else catalog
    return json.dumps(payload, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
