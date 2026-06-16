from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.provider_status import build_provider_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Show data provider and storage readiness status.")
    parser.add_argument("--output", help="Optional JSON output path for provider status.")
    args = parser.parse_args()
    status = build_provider_status()
    payload = json.dumps(status, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
