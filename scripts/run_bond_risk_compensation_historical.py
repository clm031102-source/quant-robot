"""Hash preview or one separately admitted, fixed bond diagnostic."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.research import bond_risk_compensation_admission as admission


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('fingerprint','preview','execute'))
    parser.add_argument('--registration-sha256')
    args=parser.parse_args(argv); root=Path(__file__).resolve().parents[1]
    if args.command=='fingerprint':
        print(json.dumps(dict(status='prospective_hash_packet_no_admission_created',
            packet=admission.build_registration(root),financial_values_decoded=False,qualified=False,real_forward=0)))
        return 0
    packet,_=admission.admitted_packet(root)
    if args.command=='preview':
        print(json.dumps(dict(status='reviewed_not_executed',registration_sha256=packet['registration_sha256'],
                             policy=admission.POLICY,financial_values_decoded=False,qualified=False,real_forward=0)))
        return 0
    from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
    outcome=admission.execute(root,expected_registration_sha256=args.registration_sha256,
        gate_supplier=lambda:run_quant_pm_startup_gate(machine='office_desktop',task='factor_review',
            branch=admission.BRANCH,output_dir=root/admission.DIRECTORY/'startup_gate'))
    print(json.dumps(outcome)); return 0


if __name__=='__main__': raise SystemExit(main())
