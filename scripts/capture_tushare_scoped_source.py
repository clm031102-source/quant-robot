"""Preview, execute or inspect a frozen one-attempt fund_daily source scope."""
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.tushare_live_transport import capture_scoped_source, verify_scoped_source_receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',default=str(Path(__file__).resolve().parents[1]))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    preview=sub.add_parser('preview');preview.add_argument('--scope',required=True)
    capture=sub.add_parser('capture');capture.add_argument('--scope',required=True)
    capture.add_argument('--scope-sha256',required=True)
    inspect=sub.add_parser('inspect');inspect.add_argument('--receipt',required=True)
    args=parser.parse_args(argv)
    if args.command=='status':
        print(json.dumps(dict(status='scope_required',source_observation_supported=True,
            ready_scope_not_inferred=True,holdout_2026_prices_closed=True,
            credentials_read=False,network_requests_started=0,candidate_qualification_required=False)))
        return 0
    try:
        if args.command=='inspect':
            receipt=verify_scoped_source_receipt(args.receipt)
            result=dict(status=receipt['status'],evidence_class=receipt['evidence_class'],
                        receipt_sha256=receipt['sha256'],strategy_forward_days_added=0)
        else:
            result=capture_scoped_source(args.scope,repo_root=args.repo_root,
                execute=args.command=='capture',expected_scope_sha256=getattr(args,'scope_sha256',None))
    except (ValueError,KeyError,TypeError,OSError):
        print(json.dumps(dict(status='blocked',reason='scope_or_receipt_validation_failed',
                              strategy_forward_days_added=0,candidate_qualification_granted=False)))
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status'] in ('preview','source_observed_unqualified','already_consumed') else 2


if __name__=='__main__':
    raise SystemExit(main())
