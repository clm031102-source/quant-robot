"""Inspect or advance the invented-session USD engineering journal; no live mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.us_allocation_paper_journal import advance, create, status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("status")
    actions.add_parser("create-artificial").add_argument("--manifest", required=True)
    actions.add_parser("advance-artificial").add_argument("--packet", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            result = status(args.journal)
        elif args.action == "create-artificial":
            result = create(args.journal, json.loads(Path(args.manifest).read_bytes()))
        else:
            result = advance(args.journal, json.loads(Path(args.packet).read_bytes()))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(status="blocked", reason=str(exc), real_forward_days=0,
                              live_trading_allowed=False), ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
