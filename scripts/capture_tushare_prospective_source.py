"""Prepare, preview, capture or inspect one activated candidate's prospective source."""
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_prospective_transport as capture
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import tushare_live_transport as archive


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',default=str(Path(__file__).resolve().parents[1]))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    prepare=sub.add_parser('prepare')
    for name in ('journal','machine','task','branch','output'):prepare.add_argument('--'+name,required=True)
    preview=sub.add_parser('preview');preview.add_argument('--scope',required=True)
    execute=sub.add_parser('capture');execute.add_argument('--scope',required=True)
    execute.add_argument('--scope-sha256',required=True)
    inspect=sub.add_parser('inspect');inspect.add_argument('--receipt',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='status':
            result=dict(status='qualified_activated_original_bound_scope_required',
                production_profiles=sum(p.lineage=='recorded_observation' for p in connection.PROFILES.values()),
                credentials_read=False,network_requests_started=0,real_forward_days_added=0)
        elif args.command=='prepare':
            scope=scopes.prepare_scope(args.journal,repo_root=args.repo_root,
                context=dict(machine=args.machine,task=args.task,branch=args.branch))
            root=Path(args.repo_root).resolve(strict=True)
            target=capture._path(root,Path(args.output).resolve())
            target.parent.mkdir(parents=True,exist_ok=True)
            reference=archive._publish_json(target,scope)
            result=dict(status='scope_prepared',scope_path=str(target),file_sha256=reference['sha256'],
                        scope_sha256=capture.forward.digest(scope),network_requests_started=0)
        elif args.command=='inspect':
            receipt=capture.verify_prospective_receipt(args.receipt)
            result=dict(status=receipt['status'],receipt_sha256=receipt['sha256'],
                evidence_class=receipt['evidence_class'],network_requests_started=0,real_forward_days_added=0)
        else:
            result=capture.capture_prospective_source(args.scope,repo_root=args.repo_root,
                execute=args.command=='capture',expected_scope_sha256=getattr(args,'scope_sha256',None))
    except (ValueError,KeyError,TypeError,OSError,EOFError):
        print(json.dumps(dict(status='blocked',reason='prospective_authority_or_archive_validation_failed',
            credentials_read=False,real_forward_days_added=0)))
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if result['status'] in ('recovery_review_required','source_rejected') else 0


if __name__=='__main__':raise SystemExit(main())
