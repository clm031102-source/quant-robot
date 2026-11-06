"""Prepare a paper candidate review packet without activating or qualifying it."""
from __future__ import annotations

import argparse
import json

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.frozen_candidate_manifest import prepare_manifest, read_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_manifest(read_request(args.request), args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(status='blocked', reason=str(exc), qualified=False,
                              real_forward_days=0, live_trading_allowed=False), ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
