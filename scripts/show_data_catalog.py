from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_robot.storage.catalog import build_storage_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Show local Quant Robot data catalog.")
    parser.add_argument("--root", default="data")
    args = parser.parse_args()
    print(json.dumps(build_storage_catalog(Path(args.root)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
