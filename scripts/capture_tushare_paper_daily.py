"""Inspect or exercise synthetic fund_daily receipts; live capture is closed."""
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.tushare_daily_receipt import (
    MAX_BYTES, SOURCE_URL, capture_synthetic_receipt, verify_receipt,
)


class _FixtureResponse:
    def __init__(self, body, http_date):
        self.body, self.headers = body, {'Date': http_date} if http_date else {}
        self.url, self.status_code = SOURCE_URL, 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        yield self.body


class _FixtureTransport:
    def __init__(self, response):
        self.response = response

    def post(self, *args, **kwargs):
        return self.response


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('capture-live')
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--receipt', required=True)
    fixture = sub.add_parser('capture-fixture')
    fixture.add_argument('--body', required=True)
    fixture.add_argument('--archive', required=True)
    fixture.add_argument('--ts-code', required=True)
    fixture.add_argument('--trade-date', required=True)
    fixture.add_argument('--started-at', required=True)
    fixture.add_argument('--received-at', required=True)
    fixture.add_argument('--http-date')
    args = parser.parse_args(argv)
    if args.command in ('status', 'capture-live'):
        print(json.dumps(dict(status='blocked', reason='live_transport_not_implemented_or_reviewed',
                              detail='Real transport and complete source contract await implementation and review; 2026 prices remain sealed.',
                              real_forward_eligible=False, credentials_read=False,
                              network_requests=0)))
        return 2 if args.command == 'capture-live' else 0
    try:
        if args.command == 'inspect':
            receipt = verify_receipt(args.receipt)
            result = dict(status=receipt['status'], receipt_sha256=receipt['sha256'],
                          evidence_class=receipt['evidence_class'], real_forward_eligible=False)
        else:
            with Path(args.body).open('rb') as stream:
                body = stream.read(MAX_BYTES+1)
            clocks = iter((args.started_at, args.received_at))
            result = capture_synthetic_receipt(args.archive, ts_code=args.ts_code,
                trade_date=args.trade_date, token='synthetic-fixture-no-credential',
                transport=_FixtureTransport(_FixtureResponse(body, args.http_date)),
                clock=lambda: next(clocks))
    except (ValueError, KeyError, OSError, TypeError):
        print(json.dumps(dict(status='blocked', reason='fixture_or_receipt_validation_failed',
                              real_forward_eligible=False)))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result['status'] in ('capture_rejected', 'attempt_incomplete') else 0


if __name__ == '__main__':
    raise SystemExit(main())
