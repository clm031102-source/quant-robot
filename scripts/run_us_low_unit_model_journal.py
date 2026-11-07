"""Create, append or inspect only an artificial four-scenario USD journal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.ops import us_low_unit_model_journal as journal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("create", "append", "status"))
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--event", type=Path)
    parser.add_argument("--recorded-at", help="Explicit invented UTC receipt-processing clock")
    args = parser.parse_args()
    if args.operation == "create":
        if args.manifest is None or args.event is not None or args.recorded_at is not None:
            parser.error("create requires only --manifest and --directory")
        answer = journal.create(args.directory, json.loads(args.manifest.read_bytes()))
    elif args.operation == "append":
        if args.event is None or args.recorded_at is None or args.manifest is not None:
            parser.error("append requires --event, --recorded-at and --directory")
        answer = journal.append(args.directory, json.loads(args.event.read_bytes()), recorded_at=args.recorded_at)
    else:
        if any(x is not None for x in (args.event, args.manifest, args.recorded_at)):
            parser.error("status requires only --directory")
        answer = journal.status(args.directory)
    print(json.dumps(answer, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
