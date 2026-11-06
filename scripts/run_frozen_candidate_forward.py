"""Operate an explicitly qualified frozen candidate's local paper journal only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.frozen_candidate_forward import activate, decide, observe, status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', default='data/reports/frozen_candidate_forward')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    start = sub.add_parser('activate')
    start.add_argument('--manifest', required=True)
    start.add_argument('--qualification', required=True)
    start.add_argument('--mode', choices=('forward', 'synthetic', 'replay'), default='forward')
    sub.add_parser('decide')
    receive = sub.add_parser('observe')
    receive.add_argument('--packet', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'status':
            result = status(args.journal)
        elif args.command == 'activate':
            event = activate(args.journal, args.manifest, args.qualification, mode=args.mode)
            result = {'status': 'activation_recorded', 'event_sha256': event['sha256']}
        elif args.command == 'decide':
            event = decide(args.journal)
            result = {'status': 'decision_recorded', 'event_sha256': event['sha256']}
        else:
            packet = json.loads(Path(args.packet).read_text(encoding='utf-8-sig'))
            event = observe(args.journal, packet)
            result = {'status': 'observation_recorded', 'event_sha256': event['sha256']}
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc),
                          'live_trading_allowed': False}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
